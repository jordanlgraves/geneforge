#!/usr/bin/env python3
import logging
import json
from typing import Optional, List, Dict, Any, Union
from dotenv import load_dotenv

from src.llm_module import get_llm_client, run_assistant
from src.prompt_manager import get_system_prompt
from src.session_state import SessionState
from src.functions import ToolIntegration

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
        
    def run(self) -> Optional[Any]:
        """
        Run the example conversation with the LLM.
        
        Returns:
            The final result message from the LLM or None if an error occurred
        """
        self.setup()
        self.logger.info("Starting LLM interaction...")
        
        try:            
            attempt = 0
            final_result_msg = None
            
            # Make multiple attempts if needed
            while attempt < self.max_attempts:
                self.logger.info(f"Attempt {attempt + 1} of {self.max_attempts}")
                
                if attempt > 0:
                    # Add a nudge message if this isn't the first attempt
                    self.messages.append({
                        "role": "user",
                        "content": "Please use the tools to complete the task."
                    })
                
                final_result_msg = run_assistant(
                    client=self.client,
                    session_state=self.session_state,   
                    tool_integration=self.tool_integration,
                    user_prompt=self.prompt,
                    system_prompt=self.system_prompt
                )
                
                # Add the response to messages for context in case of another attempt
                if not isinstance(final_result_msg, dict):
                    self.messages.append({"role": "assistant", "content": final_result_msg.content})
                
                # Check if we got results from Cello or another success condition
                if self.check_success():
                    self.logger.info("Successfully completed task")
                    break
                    
                attempt += 1
                self.rounds_seen += 1    # ❷ increment after each model call
                
            if attempt == self.max_attempts and not self.check_success():
                self.logger.warning("Failed to complete task after maximum attempts")
                
            # Persist chat_rounds for reward calculation
            self.session_state.chat_rounds = self.rounds_seen
            
            return final_result_msg
                
        except Exception as e:
            self.logger.error(f"Conversation failed: {str(e)}", exc_info=True)
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
    
    def log_results(self, final_result_msg: Any):
        """
        Log the final results of the example run.
        
        Args:
            final_result_msg: The final message from the LLM
        """
        self.logger.info("--- LLM Interaction Complete ---")
        
        if isinstance(final_result_msg, dict):  # Error case
            self.logger.error(f"Failed with reason: {final_result_msg.get('finish_reason', 'unknown')}")
            self.logger.error(f"Error details: {final_result_msg.get('content', 'No details')}")
            return
            
        # Display full conversation history
        self.logger.info("--- Full Conversation History ---")
        for msg in self.messages:
            self.logger.info(f"{msg['role'].upper()}: {msg.get('content', '')}")
        
        # Display final response
        if hasattr(final_result_msg, 'reasoning_content'):
            self.logger.info("--- Reasoning Process ---\n%s", final_result_msg.reasoning_content)
        self.logger.info("--- Final Answer ---\n%s", final_result_msg.content)

        # Log final session state for inspection
        self.logger.info("--- Final Session State ---")
        self.logger.info(f"Selected Library: {self.session_state.get_current_library_id()}")
        self.logger.info(f"Custom UCF Path: {self.session_state.custom_ucf_path}")
        if hasattr(self.session_state, 'custom_input_path'):
            self.logger.info(f"Custom Input Sensors Path: {self.session_state.custom_input_path}")
        if self.session_state.get_cello_results():
            self.logger.info(f"Cello Results: {json.dumps(self.session_state.cello_results, indent=2)}")
