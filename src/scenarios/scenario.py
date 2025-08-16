#!/usr/bin/env python3
import logging
import json
import asyncio
import re
import uuid
from typing import Optional, List, Dict, Any, Union
from dotenv import load_dotenv
import os
from glob import glob
from litellm import acompletion, completion

from src.llm_module import get_llm_params
from src.prompt_manager import get_system_prompt
from src.session_state import SessionState
from src.tool_registry import ToolIntegration, tool_functions

try:
    import art
except ModuleNotFoundError:
    art = None


SYSTEM_PROMPT = get_system_prompt()

class Scenario:
    """
    Reusable harness for running scenarios with LLM-based design.
    Encapsulates common functionality for setup, execution, and result handling.
    """
    
    def __init__(
        self,
        scenario_name: str,
        prompt: str = None,
        system_prompt: str = None,
        *,
        art_model = None,
        model_name: str = None,
        preexecuted_tool_calls: Optional[List[Dict[str, Any]]] = None,
        include_pre_calls_in_chat: bool = True,
    ):
        """
        Initialize the example runner with the given parameters.
        
        Args:
            scenario_name: Name of the scenario for logging and weave tracking
            prompt: The prompt to send to the LLM
            max_rounds: Maximum number of conversation rounds per attempt
            max_attempts: Maximum number of attempts to run the example
        """
        self.scenario_name = scenario_name
        self.prompt = self._process_prompt(prompt)
        self.system_prompt = self._process_system_prompt(system_prompt)
        # Configure logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(f"Scenario-{scenario_name}")
        
        # Set up session state and other components
        self.session_state = SessionState()
        self.session_state.set_design_spec(self.prompt)

        self.tool_integration = ToolIntegration(self.session_state)
        self.client = None
        self.model = None
        self.llm_params = {}
        self.messages = []
        self.messages_and_choices: List[Any] = []

        self.model_name = model_name
        self.art_model = art_model
        self.preexecuted_tool_calls = preexecuted_tool_calls
        self.include_pre_calls_in_chat = include_pre_calls_in_chat
        self._is_art_backend = False
        
        
    
    def _parse_art_tool_calls(self, content: str) -> tuple[Optional[List[Dict[str, Any]]], Optional[str], Optional[str]]:
        if "<tool_call>" not in content:
            return None, None, content

        tool_calls = []
        errors = []
        
        # Regex to find all JSON blobs inside <tool_call>...</tool_call> blocks
        pattern = r"<tool_call>.*?({.*?}).*?</tool_call>"
        matches = re.findall(pattern, content, re.DOTALL)
        
        # Get the text outside of the tool calls
        text_content = re.sub(pattern, '', content, flags=re.DOTALL).strip()

        for match in matches:
            # The regex captures only the JSON part.
            try:
                tool_data = json.loads(match)
                tool_calls.append({
                    "id": str(uuid.uuid4()),
                    "type": "function",
                    "function": {
                        "name": tool_data.get("name"),
                        "arguments": json.dumps(tool_data.get("arguments", {})),
                    },
                })
            except json.JSONDecodeError as e:
                errors.append(f"Invalid JSON in tool call: {e}. Malformed JSON: ```json\n{match}\n```")

        if errors:
            return None, "\n".join(errors), text_content

        return tool_calls, None, text_content

    # ------------------------------------------------------------------
    #  Helpers to normalize assistant messages and execute tool calls
    # ------------------------------------------------------------------
    def _build_assistant_message(self, raw_assistant: Any) -> tuple[Dict[str, Any], Optional[str]]:
        """
        Normalize a provider-specific assistant message into our dict format and
        extract tool calls (ART XML or standard OpenAI style).

        Returns (assistant_msg, error_message). If using ART backend and the
        response contains malformed JSON inside <tool_call>, error_message is a
        string and assistant_msg retains original content.
        """
        assistant_msg: Dict[str, Any] = {
            "role": "assistant",
            "content": getattr(raw_assistant, "content", None) or "",
        }

        error_message: Optional[str] = None

        # ART XML-format handling
        if self._is_art_backend:
            parsed_tool_calls, parse_error, text_content = self._parse_art_tool_calls(assistant_msg["content"])
            if parse_error:
                error_message = parse_error
            else:
                assistant_msg["content"] = text_content
                if parsed_tool_calls:
                    assistant_msg["tool_calls"] = parsed_tool_calls

        # Standard OpenAI tool calls
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

        return assistant_msg, error_message

    def _execute_tool_calls(self, assistant_msg: Dict[str, Any]) -> bool:
        """
        Execute tool calls present in assistant_msg, append corresponding tool
        messages, and update internal counters.

        Returns True if any tool calls were executed.
        """
        if "tool_calls" not in assistant_msg:
            return False

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

            self._add_message(
                "tool",
                json.dumps(result),
                name=fn_name,
                tool_call_id=tc["id"],
            )

        return True

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
    
    def get_metrics(self):
        """
        Get the metrics for the workflow run.
        """
        # get number of tool calls, number of tool call failures,
        
        tool_calls = 0
        tool_call_failures = 0
        tool_call_successes = 0
        for message in self.messages:
            if message.get("role") == "tool":
                tool_response = message.get("content")
                tool_response_json = json.loads(tool_response)
                if tool_response_json.get("success", False) is False:
                    tool_call_failures += 1
                if tool_response_json.get("success", False) is True:
                    tool_call_successes += 1
                
            if message.get("role") == "assistant" and message.get("tool_calls"):
                tool_calls += len(message.get("tool_calls"))
            
        gave_answer = self._is_answer_reported()
        return {
            "num_rounds": len(self.messages), 
            "tool_calls": tool_calls, 
            "tool_call_failures": tool_call_failures, 
            "tool_call_successes": tool_call_successes,
            "gave_answer": gave_answer,
        }
    
    def get_metadata(self):
        """
        Get the metadata for the workflow run.
        """
        return {"scenario_name": self.scenario_name}
    
    def _reset(self):
        """Set up the LLM client and initial messages (Chat Completions)."""
        # Load environment variables
        load_dotenv()
        
        # Initialize session state and tool integration
        self.session_state = SessionState()
        self.session_state.set_design_spec(self.prompt)

        self.tool_integration = ToolIntegration(self.session_state)
        self.messages_and_choices = []
        
        # Initialize LLM client
        self.llm_params = get_llm_params(
            model=self.model_name,
            art_model=self.art_model,
        )

        self.model = self.llm_params.get("model")
        # Determine if using local ART backend based on model prefix
        self._is_art_backend = isinstance(self.model, str) and self.model.startswith("hosted_vllm/")
        self.logger.info(f"Using LLM with params: {self.llm_params}")
        # Initialise messages list and record snapshots for each
        self.messages = []
        if self.system_prompt is not None:
            self._add_message("system", self.system_prompt)
        self._add_message("user", self.prompt)
        
    async def run_async(
        self,
        max_rounds: int = 15, 
        num_retries: int = 1,
        temperature: float = None
    ) -> Optional[str]:
        """
        Run the example conversation with the LLM using the streaming assistant API.

        The method automatically executes any required tool calls and will retry
        up to `max_attempts` times until `check_success()` returns True.

        Returns:
            The final assistant response text (last assistant message) or None
            if an unrecoverable error occurred.
        """
        if temperature is not None:
            self.llm_params["temperature"] = temperature
        
        # Prepare LLM client and initial state
        self._reset()

        # --------------------------------------------------------------
        #  Optionally replay pre-executed tool calls to prime session state
        # --------------------------------------------------------------
        if self.preexecuted_tool_calls:
            for msg in self.preexecuted_tool_calls:
                role = msg.get("role")
                # Handle assistant messages that request tool calls
                if role == "assistant" and msg.get("tool_calls"):
                    # Optionally add assistant message to chat history
                    if self.include_pre_calls_in_chat:
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

                        if self.include_pre_calls_in_chat:
                            tool_msg = {
                                "role": "tool",
                                "content": json.dumps(result),
                                "tool_call_id": tc["id"],
                            }
                            self._add_message(**tool_msg)
                else:
                    # For non-assistant messages, optionally record them
                    if self.include_pre_calls_in_chat:
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
                max_inner_attempt = 3
                rounds = 0
                while rounds < max_rounds:

                    response = await acompletion(
                        messages=self.messages,
                        tools=tool_functions,
                        **self.llm_params
                    )
                    if len(response.choices) == 0:
                        max_inner_attempt -= 1
                        self.logger.error(f"No response from model, trying again... {max_inner_attempt} attempts left")
                        if max_inner_attempt == 0:
                            self.logger.error("No response from model, giving up...")
                            return None
                        continue
                    
                    assistant_choice = response.choices[0]
                    raw_assistant = assistant_choice.message
                    assistant_msg, error_message = self._build_assistant_message(raw_assistant)

                    if self._is_art_backend and error_message:
                        # Keep original content when parsing fails so user can see the malformed request
                        self._add_message(**assistant_msg)
                        self._add_message("user", f"Error parsing your response: {error_message}. Please correct the JSON and try again.")
                        continue

                    self._add_message(choice=assistant_choice, **assistant_msg)

                    # ---------------- Execute tool calls if any ---------------
                    if self._execute_tool_calls(assistant_msg):
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

            # outside attempts loop
            self.session_state.chat_rounds = len(self.messages)
            return final_response

        except Exception as e:
            self.logger.error(f"Conversation failed: {e}", exc_info=True)
            return None

    # ------------------------------------------------------------------
    #  Synchronous wrapper for legacy callers
    # ------------------------------------------------------------------
    def run(self, *args, **kwargs):
        """Blocking wrapper around :pymeth:`run_async`.

        This keeps backward-compatibility with code that expected a synchronous
        ``WorkflowRunner.run``.  Internally it spins up an event-loop just once
        and delegates to the real coroutine.
        """
        return asyncio.run(self.run_async(*args, **kwargs))

    def get_retry_message(self):
        return "Please use the tools to complete the task."
    
    def check_finished(self) -> bool:
        """
        Returns:
            True if the example is finished, False otherwise. Useful for stopping the workflow when a condition is met.
        """
        return True
    
    def _is_answer_reported(self) -> bool:
        """
        Check if the answer was reported by the assistant.
        """
        answer_tool_id = None
        for message in self.messages:
            if message["role"] == "assistant" and message.get("tool_calls", []) != []:
                for tool_call in message["tool_calls"]:
                    if tool_call.get("function", {}).get("name", None) == "report_answer": # Why would this ever be None?
                        answer_tool_id = tool_call["id"]
                        break
            if message['role'] == 'tool' and message['tool_call_id'] == answer_tool_id:
                return True
        return False

    
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

    def _add_message(self, role: str, content: str, name: str | None = None, choice: Optional[Any] = None, **kwargs):
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
        
        if choice:
            try:
                from art.utils.litellm import convert_litellm_choice_to_openai
                openai_choice = convert_litellm_choice_to_openai(choice)
                self.messages_and_choices.append(openai_choice)
            except ImportError:
                # Fallback if art.utils.litellm is not available
                self.messages_and_choices.append(msg)
        else:
            self.messages_and_choices.append(msg)

        # Keep the session-state snapshot aligned with message index
        self.session_state.record_snapshot(msg_index=len(self.messages) - 1)

    async def _find_dpo_preferred_assistant(self, context_messages: List[Dict[str, Any]], chat_kwargs: Dict[str, Any], max_tool_retry: int) -> tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """
        Retry logic to find a successful tool call after a failure.
        """
        preferred_assistant: Optional[Dict[str, Any]] = None
        preferred_tool_msg: Optional[Dict[str, Any]] = None
        
        retry_context = list(context_messages)
        retry = 0
        while retry < max_tool_retry and preferred_assistant is None:
            retry += 1
            
            retry_response = await acompletion(messages=retry_context, 
                                               **chat_kwargs, 
                                               **self.llm_params)
            raw_retry_asst = retry_response.choices[0].message

            retry_asst_msg = {
                "role": "assistant",
                "content": raw_retry_asst.content or "",
            }

            # Handle ART model's XML format
            if self._is_art_backend:
                parsed_tool_calls, error_message, text_content = self._parse_art_tool_calls(retry_asst_msg["content"])

                if error_message:
                    # Parsing failed on retry, add error and continue to next retry
                    retry_context.append(retry_asst_msg)
                    retry_context.append({
                        "role": "tool", 
                        "content": json.dumps({"error": error_message}), 
                        "tool_call_id": str(uuid.uuid4())
                    })
                    continue
                
                # Only update content if parsing succeeded
                retry_asst_msg["content"] = text_content
                if parsed_tool_calls:
                    retry_asst_msg["tool_calls"] = parsed_tool_calls
            
            # Handle standard OpenAI tool calls
            if getattr(raw_retry_asst, "tool_calls", None):
                tc_retry_list = []
                for tc in raw_retry_asst.tool_calls:
                    tc_retry_list.append({
                        "id": tc.id,
                        "type": "function",
                        "function": { "name": tc.function.name, "arguments": tc.function.arguments },
                    })
                retry_asst_msg["tool_calls"] = tc_retry_list

            if "tool_calls" in retry_asst_msg:
                # Execute first tool call to check for success
                first_call = retry_asst_msg["tool_calls"][0]
                fn_name_r = first_call["function"]["name"]
                try:
                    fn_args_r = json.loads(first_call["function"]["arguments"])
                except json.JSONDecodeError:
                    fn_args_r = {}

                result_r = self.tool_integration.call_tool_function(fn_name_r, fn_args_r)

                tool_msg_r = {
                    "role": "tool",
                    "content": json.dumps(result_r),
                    "tool_call_id": first_call["id"],
                }

                if not result_r.get("error", False):
                    preferred_assistant = retry_asst_msg
                    preferred_tool_msg = tool_msg_r
                else:
                    # Add failing attempt to context for subsequent retry
                    retry_context.extend([retry_asst_msg, tool_msg_r])
            else:
                # Retry assistant produced no tool call – add to context and retry
                retry_context.append(retry_asst_msg)
                
        return preferred_assistant, preferred_tool_msg

    # ------------------------------------------------------------------
    #  New functionality – generate (preferred, rejected) pairs for DPO
    # ------------------------------------------------------------------

    async def run_generate_preference_pair_on_tool_failures_async(
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
            "tools": tool_functions,
            "tool_choice": "auto",
            "temperature": 0.0,
        }

        rounds = 0
        while rounds < max_rounds:
            # ----------------------------------------------------------------
            #  Ask the model for the next assistant turn
            # ----------------------------------------------------------------
            response = await acompletion(
                messages=self.messages,
                **chat_kwargs,  # type: ignore[arg-type]
                **self.llm_params
            )

            raw_assistant = response.choices[0].message  # OpenAI object

            assistant_msg = {
                "role": "assistant",
                "content": raw_assistant.content or "",
            }

            rejected_assistant = assistant_msg
            
            # Handle ART model's XML format
            if self._is_art_backend:
                parsed_tool_calls, error_message, text_content = self._parse_art_tool_calls(assistant_msg["content"])
                
                if error_message:
                    self.logger.warning(f"DPO: Malformed XML or JSON response from ART model: {error_message}")
                    
                    context_messages = list(self.messages)
                    preferred_assistant, preferred_tool_msg = await self._find_dpo_preferred_assistant(context_messages, chat_kwargs, max_tool_retry)

                    if preferred_assistant and preferred_tool_msg:
                        dpo_samples.append({
                            "input": {"messages": context_messages},
                            "preferred_output": [preferred_assistant],
                            "non_preferred_output": [rejected_assistant],
                        })
                        self.messages = context_messages
                        self._add_message(**preferred_assistant)
                        self._add_message(**preferred_tool_msg)
                    else:
                        self.logger.error("Failed to recover from malformed response.")
                        self._add_message(**assistant_msg) # Log the bad response and continue
                    
                    if stop_on_first_failure: break
                    continue

                # Only update content if parsing succeeded
                assistant_msg["content"] = text_content
                if parsed_tool_calls:
                    assistant_msg["tool_calls"] = parsed_tool_calls

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

                    preferred_assistant, preferred_tool_msg = await self._find_dpo_preferred_assistant(context_messages, chat_kwargs, max_tool_retry)

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

    # ------------------------------------------------------------------
    #  Synchronous wrapper for legacy callers
    # ------------------------------------------------------------------
    def run_generate_preference_pair_on_tool_failures(self, *args, **kwargs):
        """Blocking wrapper around :pymeth:`run_generate_preference_pair_on_tool_failures_async`.

        This keeps backward-compatibility with code that expected a synchronous
        method.  Internally it spins up an event-loop just once
        and delegates to the real coroutine.
        """
        return asyncio.run(self.run_generate_preference_pair_on_tool_failures_async(*args, **kwargs))

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
    
    def get_tool_usage(self):
        tool_usage = dict()
        for message in self.messages:
            if message.get("role") == "assistant" and message.get("tool_calls"):
                # This is an assistant message that requested tool calls.
                for tool_call in message.get("tool_calls"):
                    tool_name = tool_call.get("function", {}).get("name")
                    if tool_name not in tool_usage:
                        tool_usage[tool_name] = {'uses': 0, 'errors': 0}
                    tool_usage[tool_name]['uses'] += 1
            if message.get("role") == "tool":
                # This is a tool call response.
                content = json.loads(message.get("content"))
                if content.get("error"):
                    tool_name = message.get("name")
                    if tool_name not in tool_usage:
                        tool_usage[tool_name] = {'uses': 0, 'errors': 0}
                    tool_usage[tool_name]['errors'] += 1
        return tool_usage
    
    
    def get_nl_rubric(self):
        """
        Get the natural language rubric for the example.
        """
        return None
    
    def get_answer_tool_id(self):
        answer_tool_id = None
        for message in self.messages:
            if message["role"] == "assistant" and message.get("tool_calls", []) != []:
                for tool_call in message["tool_calls"]:
                    if tool_call.get("function", {}).get("name", None) == "report_answer": # Why would this ever be None?
                        answer_tool_id = tool_call["id"]
                        return answer_tool_id
        return None
        
    def get_reported_answer_content(self):
        """
        Fetch the content of the tool response that corresponds to the `report_answer`
        tool call. Returns None if no such response has been recorded.
        """
        answer_tool_id = self.get_answer_tool_id()
        if answer_tool_id is None:
            return None
        for message in self.messages:
            if message.get("role") == "tool" and message.get("tool_call_id") == answer_tool_id:
                return message.get("content")
        return None