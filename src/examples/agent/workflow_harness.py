#!/usr/bin/env python3
import logging
import json
from typing import Optional, List, Dict, Any, Union
from dotenv import load_dotenv

from src.llm_module import get_llm_client, run_assistant
from src.prompt_manager import get_system_prompt
from src.session_state import SessionState
# Import tool registry elements, including function schemas for ChatCompletion
from src.tool_registry import ToolIntegration, tool_functions

# NEW: import event handler base from OpenAI
from openai import AssistantEventHandler

class WorkflowRunner:
    """
    Reusable harness for running example circuits with LLM-based design.
    Encapsulates common functionality for setup, execution, and result handling.
    """
    
    def __init__(self, 
                 example_name: str, 
                 prompt: str, 
                 max_rounds: int = 15, 
                 max_attempts: int = 4, 
                 system_prompt: str = None,
                 user_reasoning_model: bool = False):
        """
        Initialize the example runner with the given parameters.
        
        Args:
            example_name: Name of the example for logging and weave tracking
            prompt: The prompt to send to the LLM
            max_rounds: Maximum number of conversation rounds per attempt
            max_attempts: Maximum number of attempts to run the example
        """
        self.example_name = example_name
        self.prompt = prompt
        self.max_rounds = max_rounds
        self.max_attempts = max_attempts
        self.system_prompt = system_prompt
        # Configure logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(f"Example-{example_name}")
        
        # Set up session state and other components
        self.session_state = SessionState()
        self.session_state.set_design_spec(self.prompt)

        self.tool_integration = ToolIntegration(self.session_state)
        self.client = None
        self.model = None
        self.messages = []
        self.rounds_seen = 0        # ❶ counter
        
        self.user_reasoning_model = user_reasoning_model
        
    def setup(self):
        """Set up the LLM client and initial messages."""
        self.logger.info(f"--- Running {self.example_name} Example ---")
        
        # Load environment variables
        load_dotenv()
        
        # Initialize LLM client
        self.client, self.model = get_llm_client(client_type="openai", reasoning=self.user_reasoning_model)
        self.logger.info(f"Using LLM Client: {type(self.client).__name__}, Model: {self.model}")
        
        # Initialise messages list and record snapshots for each
        self.messages = []
        if self.system_prompt is None:
            self.system_prompt = get_system_prompt()
        self._add_message("system", self.system_prompt)
        self._add_message("user", self.prompt)
        
    def run(self) -> Optional[str]:
        """
        Run the example conversation with the LLM using the streaming assistant API.

        The method automatically executes any required tool calls and will retry
        up to `self.max_attempts` times until `check_success()` returns True.

        Returns:
            The final assistant response text (last assistant message) or None
            if an unrecoverable error occurred.
        """
        # Prepare LLM client and initial state
        self.setup()
        self.logger.info("Starting LLM interaction...")

        # ------------------------------------------------------------------
        #  Nested event-handler class definition (uses closure over `self`)
        # ------------------------------------------------------------------
        class _RunnerEventHandler(AssistantEventHandler):
            """Streaming handler that auto-executes tool calls."""
            def __init__(self, runner: "WorkflowRunner", run_id: str | None = None, thread_id: str | None = None):
                super().__init__()
                self.runner = runner
                self.client = runner.client
                self.tool_integration = runner.tool_integration
                self.run_id = run_id
                self.thread_id = thread_id
                self._buffer: str = ""

            # ------------- OpenAI streaming callbacks ----------------------
            def on_event(self, event):  # type: ignore[override]
                if event.event == "thread.run.created":
                    self.run_id = event.data.id
                    self.thread_id = event.data.thread_id
                elif event.event == "thread.run.requires_action":
                    self._finalise_buffer()
                    self._handle_requires_action(event.data)
                elif event.event == "thread.run.failed":
                    err = getattr(event.data, "last_error", None)
                    self.runner.logger.error(f"Run failed: {err}")

            def on_text_delta(self, delta, snapshot):  # type: ignore[override]
                self._buffer += delta.value

            # ----------------- helper functions ----------------------------
            def _finalise_buffer(self):
                text = self._buffer.strip()
                if text:
                    self.runner._add_message("assistant", text)
                self._buffer = ""

            def _handle_requires_action(self, data):
                tool_outputs = []
                seen_call_ids: set[str] = set()
                for tool_call in data.required_action.submit_tool_outputs.tool_calls:
                    if tool_call.id in seen_call_ids:
                        continue
                    seen_call_ids.add(tool_call.id)
                    fn_name = tool_call.function.name
                    try:
                        fn_args = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError as e:
                        self.runner.logger.error(f"Invalid JSON for {fn_name}: {e}")
                        tool_outputs.append({"tool_call_id": tool_call.id, "output": json.dumps({"error": str(e)})})
                        continue

                    # NEW: attach this tool invocation to the *previous* assistant message
                    # so that the record looks like:
                    # {
                    #   "role": "assistant",
                    #   "content": "... prior assistant text ...",
                    #   "tool_calls": [{...}]
                    # }
                    if self.runner.messages and self.runner.messages[-1]["role"] == "assistant":
                        last_msg = self.runner.messages[-1]
                    else:
                        # If for some reason no assistant text was captured, create a stub
                        self.runner._add_message("assistant", "")
                        last_msg = self.runner.messages[-1]

                    tool_call_entry = {
                        "id": tool_call.id,
                        "type": "function",
                        "function": {
                            "name": fn_name,
                            "arguments": json.dumps(fn_args),
                        },
                    }
                    last_msg.setdefault("tool_calls", []).append(tool_call_entry)

                    try:
                        result = self.tool_integration.call_tool_function(fn_name, fn_args)
                        # Record tool *response* with linkage back to the call id
                        self.runner._add_message(
                            "tool",
                            json.dumps(result),
                            name=fn_name,
                            tool_call_id=tool_call.id,
                        )
                        tool_outputs.append({"tool_call_id": tool_call.id, "output": json.dumps(result)})
                    except Exception as e:
                        self.runner.logger.error(f"Error executing tool {fn_name}: {e}")
                        tool_outputs.append({"tool_call_id": tool_call.id, "output": json.dumps({"error": str(e)})})

                continuation_handler = _RunnerEventHandler(self.runner)
                with self.client.beta.threads.runs.submit_tool_outputs_stream(
                    thread_id=data.thread_id,
                    run_id=data.id,
                    tool_outputs=tool_outputs,
                    event_handler=continuation_handler,
                ) as stream:
                    stream.until_done()
                # After continuation completes, capture any trailing assistant text
                continuation_handler._finalise_buffer()

        # ------------------------------------------------------------------
        #  Conversation loop – retry until success or attempts exhausted
        # ------------------------------------------------------------------
        final_response: Optional[str] = None
        attempt = 0
        try:
            while attempt < self.max_attempts:
                user_prompt = self.prompt if attempt == 0 else "Please use the tools to complete the task."
                if attempt > 0:
                    self._add_message("user", user_prompt)

                handler = _RunnerEventHandler(self)
                run_assistant(
                    client=self.client,
                    session_state=self.session_state,
                    user_prompt=user_prompt,
                    system_prompt=self.system_prompt,
                    event_handler=handler,
                )
                handler._finalise_buffer()

                # Capture the latest assistant message as the final_response
                if self.messages and self.messages[-1]["role"] == "assistant":
                    final_response = self.messages[-1]["content"]

                # if self.check_success():
                #     self.logger.info("Successfully completed task")
                #     break
                
                attempt += 1
                self.rounds_seen += 1
            else:
                self.logger.warning("Failed to complete task after maximum attempts")

            # Persist chat rounds count and ensure final snapshot (already taken
            # when the last assistant message was appended)
            self.session_state.chat_rounds = len(self.messages)
            return final_response

        except Exception as e:
            self.logger.error(f"Conversation failed: {e}", exc_info=True)
            return None
    
    def check_success(self) -> bool:
        """
        Returns:
            True if the example run was successful, False otherwise
        """
        return True
    
    def log_results(self, final_response: Optional[str]):
        """
        Log the final results of the example run.

        Args:
            final_response: The final assistant response text.
        """
        self.logger.info("--- LLM Interaction Complete ---")

        # Display full conversation history
        self.logger.info("--- Full Conversation History ---")
        for msg in self.messages:
            role = msg.get("role", "?").upper()
            content = msg.get("content", "")
            self.logger.info(f"{role}: {content}")

        # Display final response separately for convenience
        if final_response is not None:
            self.logger.info("--- Final Assistant Response ---\n%s", final_response)
        else:
            self.logger.warning("No assistant response captured.")

        # Log final session state for inspection
        self.logger.info("--- Final Session State ---")
        self.logger.info(f"Selected Library: {self.session_state.to_dict()}")
        
    def session_state_history(self):
        """Return the SessionState history wrapped in a lightweight proxy.

        The proxy exposes a ``to_dict()`` helper for ease of JSON serialisation
        (maintaining compatibility with existing notebooks that may do
        ``runner.session_state_history().to_dict()``).
        """

        class _HistoryProxy(list):
            def __init__(self, history):
                super().__init__(history)

            def to_dict(self):  # type: ignore[override]
                return {"history": list(self)}

        return _HistoryProxy(self.session_state.get_history())

    # ------------------------------------------------------------------
    #  Internal helper – keeps chat ↔ snapshot alignment
    # ------------------------------------------------------------------

    def _add_message(self, role: str, content: str, name: str | None = None, **kwargs):
        """Append *content* as a new chat message and snapshot the state.

        Additional keyword arguments are merged into the message dict so callers can
        store extra metadata such as `tool_calls` or `tool_call_id`.
        """
        msg = {"role": role, "content": content}
        if name is not None:
            msg["name"] = name
        if kwargs:
            msg.update(kwargs)
        self.messages.append(msg)
        # Keep the session-state snapshot aligned with message index
        self.session_state.record_snapshot(msg_index=len(self.messages) - 1)

    # ------------------------------------------------------------------
    #  New functionality – generate (preferred, rejected) pairs for DPO
    # ------------------------------------------------------------------

    def run_collect_dpo_pairs(
        self,
        *,
        max_tool_retry: int = 5,
        stop_on_first_failure: bool = False,
    ) -> List[Dict[str, Any]]:
        """Run the workflow and collect (preferred, rejected) response pairs.

        The algorithm is similar to :py:meth:`run` but **synchronous** and uses
        the Chat Completions API so we can intercept each assistant turn and
        inspect tool-call results.  Whenever a tool invocation reports
        ``{"success": False}`` we:

        1.   Record the assistant *failure* message as the *rejected* output.
        2.   Roll back the conversation context to *before* this assistant
             turn and re-query the model up to ``max_tool_retry`` times until a
             tool call succeeds.  The first successful assistant message is
             captured as the *preferred* output.
        3.   We emit a DPO training sample::

                {"input": {"messages": context},
                 "preferred_output": [preferred_msg],
                 "non_preferred_output": [rejected_msg]}

        The conversation then continues **with** the successful assistant and
        its tool response so the overall workflow can still complete.

        Args:
            max_tool_retry:   Maximum attempts to obtain a successful tool
                              call after a failure.
            stop_on_first_failure:  If *True* the run stops after generating
                              the first pair (useful for debugging).

        Returns:
            List of dataset rows suitable for OpenAI DPO fine-tuning.
        """

        # ----------- Initialise client, state and starting messages ----------
        self.setup()

        dpo_samples: List[Dict[str, Any]] = []

        # ChatCompletion parameters (deterministic behaviour)
        chat_kwargs = {
            "model": self.model,
            "tools": tool_functions,
            "tool_choice": "auto",
            "temperature": 0.0,
        }

        rounds = 0
        while rounds < self.max_rounds:
            # ----------------------------------------------------------------
            #  Ask the model for the next assistant turn
            # ----------------------------------------------------------------
            response = self.client.chat.completions.create(
                messages=self.messages,
                **chat_kwargs,  # type: ignore[arg-type]
            )

            raw_assistant = response.choices[0].message  # OpenAI object

            assistant_msg = {
                "role": "assistant",
                "content": raw_assistant.content or "",
            }

            # Convert any tool calls to the familiar chat-history structure
            if getattr(raw_assistant, "tool_calls", None):
                tc_list = []
                for tc in raw_assistant.tool_calls:
                    tc_list.append({
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    })
                assistant_msg["tool_calls"] = tc_list

            # Append assistant message to the conversation
            self._add_message(**assistant_msg)

            # ----------------------------------------------------------------
            #  If the assistant requested tool calls, execute them
            # ----------------------------------------------------------------
            if "tool_calls" in assistant_msg:
                any_failure = False
                tool_results_messages: List[Dict[str, Any]] = []

                for tc in assistant_msg["tool_calls"]:
                    fn_name = tc["function"]["name"]
                    try:
                        fn_args = json.loads(tc["function"]["arguments"])
                    except json.JSONDecodeError as e:
                        fn_args = {}
                        self.logger.error(f"Invalid JSON for tool '{fn_name}': {e}")

                    result = self.tool_integration.call_tool_function(fn_name, fn_args)

                    tool_msg = {
                        "role": "tool",
                        "content": json.dumps(result),
                        # "name": fn_name,
                        "tool_call_id": tc["id"],
                    }
                    tool_results_messages.append(tool_msg)
                    self._add_message(**tool_msg)

                    if result.get("error", False):
                        any_failure = True

                # ---------------- Handle failures with retries ----------------
                if any_failure:
                    # Roll back context to *before* the failing assistant turn
                    #     messages[:-len(tool_results_messages)-1]
                    rollback_count = len(tool_results_messages) + 1
                    context_messages = self.messages[:-rollback_count]

                    rejected_assistant = assistant_msg

                    preferred_assistant: Dict[str, Any] | None = None
                    preferred_tool_msg: Dict[str, Any] | None = None

                    retry = 0
                    while retry < max_tool_retry and preferred_assistant is None:
                        retry += 1
                        retry_response = self.client.chat.completions.create(
                            messages=context_messages, **chat_kwargs  # type: ignore[arg-type]
                        )
                        raw_retry_asst = retry_response.choices[0].message

                        retry_asst_msg = {
                            "role": "assistant",
                            "content": raw_retry_asst.content or "",
                        }

                        if getattr(raw_retry_asst, "tool_calls", None):
                            tc_retry_list = []
                            for tc in raw_retry_asst.tool_calls:
                                tc_retry_list.append({
                                    "id": tc.id,
                                    "type": "function",
                                    "function": {
                                        "name": tc.function.name,
                                        "arguments": tc.function.arguments,
                                    },
                                })
                            retry_asst_msg["tool_calls"] = tc_retry_list

                            # Execute tool(s)
                            first_call = tc_retry_list[0]
                            fn_name_r = first_call["function"]["name"]
                            try:
                                fn_args_r = json.loads(first_call["function"]["arguments"])
                            except json.JSONDecodeError:
                                fn_args_r = {}

                            result_r = self.tool_integration.call_tool_function(fn_name_r, fn_args_r)

                            tool_msg_r = {
                                "role": "tool",
                                "content": json.dumps(result_r),
                                # "name": fn_name_r,
                                "tool_call_id": first_call["id"],
                            }

                            if result_r.get("error", False):
                                preferred_assistant = retry_asst_msg
                                preferred_tool_msg = tool_msg_r
                            else:
                                # Add failing attempt to context for subsequent retry
                                context_messages = context_messages + [retry_asst_msg, tool_msg_r]
                        else:
                            # Retry assistant produced no tool call – give up
                            context_messages = context_messages + [retry_asst_msg]

                    if preferred_assistant is not None and preferred_tool_msg is not None:
                        # Record DPO sample
                        dpo_samples.append({
                            "input": {"messages": list(context_messages)},
                            "preferred_output": [preferred_assistant],
                            "non_preferred_output": [rejected_assistant],
                        })

                        # Merge preferred path into main conversation while keeping
                        # SessionState ↔ chat history alignment.
                        self.messages = list(context_messages)  # reset to rolled-back context
                        # Re-append the assistant & tool messages so that the
                        # internal snapshot mechanism records them correctly.
                        self._add_message(**preferred_assistant)
                        self._add_message(**preferred_tool_msg)

                        if stop_on_first_failure:
                            break
                    else:
                        self.logger.warning("Failed to recover from tool call failure after retries.")

            rounds += 1

            # Optional early exit: stop when workflow signals success
            if self.check_success():
                break

        return dpo_samples
