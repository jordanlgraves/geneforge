#!/usr/bin/env python3
import logging
import json
from typing import Optional, List, Dict, Any, Union
from dotenv import load_dotenv

from src.llm_module import get_llm_client, run_assistant
from src.prompt_manager import get_system_prompt
from src.session_state import SessionState
from src.functions import ToolIntegration

# NEW: import event handler base from OpenAI
from openai import AssistantEventHandler

class ExampleRunner:
    """
    Reusable harness for running example circuits with LLM-based design.
    Encapsulates common functionality for setup, execution, and result handling.
    """
    
    def __init__(self, example_name: str, prompt: str, max_rounds: int = 15, max_attempts: int = 4, system_prompt: str = None):
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
        
    def setup(self):
        """Set up the LLM client and initial messages."""
        self.logger.info(f"--- Running {self.example_name} Example ---")
        
        # Load environment variables
        load_dotenv()
        
        # Initialize LLM client
        self.client, self.model = get_llm_client(client_type="openai", reasoning=True)
        self.logger.info(f"Using LLM Client: {type(self.client).__name__}, Model: {self.model}")
        
        # Prepare initial messages
        if self.system_prompt is None:
            self.system_prompt = get_system_prompt()
        self.messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": self.prompt}
        ]
        self.logger.info(f"Initial User Prompt: {self.prompt}")
        
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
            def __init__(self, runner: "ExampleRunner", run_id: str | None = None, thread_id: str | None = None):
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
                    self.runner.messages.append({"role": "assistant", "content": text})
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
                    try:
                        result = self.tool_integration.call_tool_function(fn_name, fn_args)
                        # Record tool call in messages for export
                        self.runner.messages.append({"role": "tool", "name": fn_name, "content": json.dumps(result)})
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
                    self.messages.append({"role": "user", "content": user_prompt})

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

                if self.check_success():
                    self.logger.info("Successfully completed task")
                    break

                attempt += 1
                self.rounds_seen += 1
            else:
                self.logger.warning("Failed to complete task after maximum attempts")

            # Persist chat rounds count
            self.session_state.chat_rounds = len(self.messages)
            return final_response

        except Exception as e:
            self.logger.error(f"Conversation failed: {e}", exc_info=True)
            return None
    
    def check_success(self) -> bool:
        """
        Check if the example run was successful.
        Default implementation checks for Cello results.
        Override this method for different success criteria.
        
        Returns:
            True if the example run was successful, False otherwise
        """
        return self.session_state.get_cello_results() is not None
    
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
        self.logger.info(f"Selected Library: {self.session_state.get_current_library_id()}")
        self.logger.info(f"Custom UCF Path: {getattr(self.session_state, 'custom_ucf_path', None)}")
        if hasattr(self.session_state, 'custom_input_path'):
            self.logger.info(f"Custom Input Sensors Path: {getattr(self.session_state, 'custom_input_path', None)}")
        if self.session_state.get_cello_results():
            self.logger.info(f"Cello Results: {json.dumps(self.session_state.cello_results, indent=2)}")
