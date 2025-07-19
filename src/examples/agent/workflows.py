#!/usr/bin/env python3
import logging
import json
from typing import Optional, List, Dict, Any, Union
from dotenv import load_dotenv
import os
from glob import glob

from src.llm_module import get_llm_client
from src.prompt_manager import get_system_prompt
from src.session_state import SessionState

from src.tool_registry import ToolIntegration, tool_functions

SYSTEM_PROMPT = get_system_prompt()

class WorkflowRunner:
    """
    Reusable harness for running example circuits with LLM-based design.
    Encapsulates common functionality for setup, execution, and result handling.
    """
    
    def __init__(self, 
                 example_name: str, 
                 prompt: str = None, 
                 system_prompt: str = None,
                 use_reasoning_model: bool = False):
        """
        Initialize the example runner with the given parameters.
        
        Args:
            example_name: Name of the example for logging and weave tracking
            prompt: The prompt to send to the LLM
            max_rounds: Maximum number of conversation rounds per attempt
            max_attempts: Maximum number of attempts to run the example
        """
        self.example_name = example_name
        self.prompt = self._process_prompt(prompt)
        self.system_prompt = self._process_system_prompt(system_prompt)
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
        
        self.use_reasoning_model = use_reasoning_model
        
    
    def _process_prompt(self, prompt: str):  
        """
        Get the prompt for the example.
        """
        return prompt
    
    def _process_system_prompt(self, system_prompt: str):
        """
        Get the system prompt for the example.
        """
        return system_prompt or SYSTEM_PROMPT
    
    def _reset(self):
        """Set up the LLM client and initial messages (Chat Completions)."""
        # Load environment variables
        load_dotenv()
        
        # Initialize session state and tool integration
        self.session_state = SessionState()
        self.session_state.set_design_spec(self.prompt)

        self.tool_integration = ToolIntegration(self.session_state)
        self.rounds_seen = 0
        
        # Initialize LLM client
        self.client, self.model = get_llm_client(client_type="openai", reasoning=self.use_reasoning_model)
        self.logger.info(f"Using LLM Client: {type(self.client).__name__}, Model: {self.model}")
        
        # Initialise messages list and record snapshots for each
        self.messages = []
        if self.system_prompt is not None:
            self._add_message("system", self.system_prompt)
        self._add_message("user", self.prompt)
        
    def run(
        self,
        max_rounds: int = 15, 
        num_retries: int = 1,
        temperature: float = None,
        *,
        preexecuted_tool_calls: Optional[List[Dict[str, Any]]] = None,
        include_pre_calls_in_chat: bool = True,
    ) -> Optional[str]:
        """
        Run the example conversation with the LLM using the streaming assistant API.

        The method automatically executes any required tool calls and will retry
        up to `max_attempts` times until `check_success()` returns True.

        Returns:
            The final assistant response text (last assistant message) or None
            if an unrecoverable error occurred.
        """
        if temperature is None and self.use_reasoning_model:
            temperature = 1.0
        
        # Prepare LLM client and initial state
        self._reset()

        # --------------------------------------------------------------
        #  Optionally replay pre-executed tool calls to prime session state
        # --------------------------------------------------------------
        if preexecuted_tool_calls:
            for msg in preexecuted_tool_calls:
                role = msg.get("role")
                # Handle assistant messages that request tool calls
                if role == "assistant" and msg.get("tool_calls"):
                    # Optionally add assistant message to chat history
                    if include_pre_calls_in_chat:
                        # Shallow copy to avoid later mutation
                        asst_stub = {
                            "role": "assistant",
                            "content": msg.get("content", ""),
                            "tool_calls": msg["tool_calls"],
                        }
                        self._add_message(**asst_stub)

                    # Execute each tool call
                    for tc in msg["tool_calls"]:
                        fn_name = tc["function"]["name"]
                        try:
                            fn_args = json.loads(tc["function"]["arguments"])
                        except json.JSONDecodeError:
                            fn_args = {}

                        result = self.tool_integration.call_tool_function(fn_name, fn_args)

                        if include_pre_calls_in_chat:
                            tool_msg = {
                                "role": "tool",
                                "content": json.dumps(result),
                                "tool_call_id": tc["id"],
                            }
                            self._add_message(**tool_msg)
                else:
                    # For non-assistant messages, optionally record them
                    if include_pre_calls_in_chat:
                        self._add_message(msg.get("role", "user"), msg.get("content", ""))
        
        self.logger.info("Starting LLM interaction via Chat Completions API…")

        final_response: Optional[str] = None

        attempt = 0
        try:
            while attempt < num_retries:
                # ------------------------------------------------------------------
                #  Prepare user prompt (first attempt vs retry)
                # ------------------------------------------------------------------
                user_prompt = self.prompt if attempt == 0 else self.get_retry_message()
                if attempt > 0:
                    self._add_message("user", user_prompt)

                rounds = 0
                while rounds < max_rounds:
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=self.messages,
                        tools=tool_functions,
                        tool_choice="auto",
                        temperature=temperature,
                    )

                    raw_assistant = response.choices[0].message

                    assistant_msg: Dict[str, Any] = {
                        "role": "assistant",
                        "content": raw_assistant.content or "",
                    }

                    # ---------------- Convert any tool calls --------------------
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

                    self._add_message(**assistant_msg)

                    # ---------------- Execute tool calls if any ---------------
                    if "tool_calls" in assistant_msg:
                        for tc in assistant_msg["tool_calls"]:
                            fn_name = tc["function"]["name"]
                            try:
                                fn_args = json.loads(tc["function"]["arguments"])
                            except json.JSONDecodeError:
                                fn_args = {}

                            try:
                                result = self.tool_integration.call_tool_function(fn_name, fn_args)
                            except Exception as e:
                                result = {"error": str(e)}
                                self.logger.error("Error executing tool %s: %s", fn_name, e)

                            # Record tool response
                            self._add_message(
                                "tool",
                                json.dumps(result),
                                name=fn_name,
                                tool_call_id=tc["id"],
                            )

                        # After executing tools, continue to next assistant round
                        rounds += 1
                        
                        continue  # inner while – ask model again with updated context

                    # ---------------- No tool call – final assistant text -----
                    final_response = assistant_msg["content"]
                    # Stop if the conversation is finished
                    if self.check_finished():
                        return final_response
                    break  # exit inner rounds loop – no further tool calls
                
                    
                # End of conversation for this attempt
                attempt += 1
                self.rounds_seen += 1

            # outside attempts loop
            self.session_state.chat_rounds = len(self.messages)
            return final_response

        except Exception as e:
            self.logger.error(f"Conversation failed: {e}", exc_info=True)
            return None

    def get_retry_message(self):
        return "Please use the tools to complete the task."
    
    def check_finished(self) -> bool:
        """
        Returns:
            True if the example is finished, False otherwise. Useful for stopping the workflow when a condition is met.
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

    def run_generate_preference_pair_on_tool_failures(
        self,
        max_rounds: int = 15, 
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
        self._reset()

        dpo_samples: List[Dict[str, Any]] = []

        # ChatCompletion parameters (deterministic behaviour)
        chat_kwargs = {
            "model": self.model,
            "tools": tool_functions,
            "tool_choice": "auto",
            "temperature": 0.0,
        }

        rounds = 0
        while rounds < max_rounds:
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

                            if not result_r.get("error", False):
                                preferred_assistant = retry_asst_msg
                                preferred_tool_msg = tool_msg_r
                            else:
                                # Add failing attempt to context for subsequent retry
                                context_messages = context_messages + [retry_asst_msg, tool_msg_r]
                        else:
                            # Retry assistant produced no tool call – give up
                            context_messages = context_messages + [retry_asst_msg]

                    if preferred_assistant is not None and preferred_tool_msg is not None:
                        # Make sure that the tool function as well as the arguments are actually different. 
                        # across the two assistant messages. Some tools may be internally stochastic, 
                        # returning different results for the same arguments. 
                        # We need to make sure that the tool function is different, and the arguments are different.
                        # If the tool function is the same, and the arguments are identical, we can skip the DPO sample.
                        
                        
                        # ---------------- Deduplicate stochastic calls ----------------
                        # Skip if the preferred & rejected assistant messages invoke
                        # *the same* tool *or* use identical arguments (simple string
                        # equality on the JSON blob).  This guards against tools that
                        # exhibit internal randomness even when called with the same
                        # parameters, which would yield poor training signals.

                        def _first_tool_call(msg: Dict[str, Any]):
                            tc_list = msg.get("tool_calls", [])
                            return tc_list[0] if tc_list else None

                        rej_tc = _first_tool_call(rejected_assistant)
                        pref_tc = _first_tool_call(preferred_assistant)

                        skip_pair = False
                        if rej_tc and pref_tc:
                            same_fn = rej_tc["function"]["name"] == pref_tc["function"]["name"]
                            same_args = rej_tc["function"]["arguments"] == pref_tc["function"]["arguments"]
                            # If either the function name is the same AND the arguments
                            # are identical, we consider this pair uninformative (some tools 
                            # are stochastic and return different results for the same arguments).
                            if same_fn and same_args:
                                skip_pair = True

                        if not skip_pair:
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
            if self.check_finished():
                break

        return dpo_samples

    def generate_chat_histories(self, output_dir, num_runs, base_run_name, start_index=0):
        for run_index in range(start_index, start_index + num_runs):
            run_id = f"{base_run_name}_{run_index}"
            self.run()
            messages, session_state_history = self.messages, self.session_state_history().to_dict()
            
            os.makedirs(f"{output_dir}/{self.model}/{run_id}", exist_ok=True)
            with open(f"{output_dir}/{self.model}/{run_id}/chat_history.json", "w") as f:
                json.dump(messages, f)
            with open(f"{output_dir}/{self.model}/{run_id}/session_state.json", "w") as f:
                json.dump(session_state_history, f)
            
    def score_run_from_directory(self, directory):
        with open(f"{directory}/chat_history.json", "r") as f:
            messages = json.load(f)
        with open(f"{directory}/session_state.json", "r") as f:
            session_state = json.load(f)
        score = self.score_run(messages, session_state['history'])
        return score

    def score_runs_from_directory(self, directory):
        scores = {}
        for chat_history_file in glob(f"{directory}/*/chat_history.json"):
            with open(chat_history_file, "r") as f:
                messages = json.load(f)
            with open(chat_history_file.replace("chat_history.json", "session_state.json"), "r") as f:
                session_state = json.load(f)
            score = self.score_run(messages, session_state['history'])
            scores[chat_history_file] = score
        return scores