#!/usr/bin/env python3
import logging
import json
from dotenv import load_dotenv
import weave

from src.llm_module import get_llm_client, chat_with_tool
from src.prompt_manager import get_system_prompt
from src.session_state import SessionState
from src.tools.functions import ToolIntegration

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("DesignSimpleCircuitExample")

PROMPT = """Design and simulate in Cello a NOT gate circuit for E. coli that produces GFP when arabinose is absent. Use the provided tools to simulate the circuit in Cello. After the simulation is complete, read the circuit score from the output file and return it as a JSON object with the key 'circuit_score'."""

def run_example():
    """
    Uses the LLM modules with session state to execute the design of a simple circuit.
    """
    logger.info("--- Running Simple Circuit Design Example ---")

    # 1. Load environment variables (like API keys)
    load_dotenv()

    # 2. Initialize LLM Client
    client, model = get_llm_client(client_type="openai", reasoning=True)
    logger.info(f"Using LLM Client: {type(client).__name__}, Model: {model}")

    # 3. Create a SessionState for this design task
    session_state = SessionState()
    logger.info("SessionState created.")

    # 4. Create ToolIntegration linked to this session's state
    tool_integration = ToolIntegration(session_state)
    logger.info("ToolIntegration created for the session.")

    # 5. Prepare the initial messages for the LLM
    system_prompt = get_system_prompt()
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": PROMPT}
    ]
    logger.info(f"Initial User Prompt: {PROMPT}")

    # 6. Run the chat process (let llm_module handle rounds internally)
    logger.info("Starting LLM interaction...")
    try:
        weave.init('design-simple-circuit')
        final_result_msg = chat_with_tool(
            client=client,
            messages=messages,
            tool_integration=tool_integration,
            model=model,
            max_rounds=15  # Let the module handle round counting
        )

        # Sometimes the LLM will return without with a breakdown of the reasoning process without using the tools.
        # check if session_state.cello_results is empty
        if not session_state.get_cello_results():
            logger.info("LLM did not use the tools. Adding a tool call to the messages.")
            messages.append({
                "role": "user",
                "content": "Please use the tools to design the circuit."
            })
            final_result_msg = chat_with_tool(
                client=client,
                messages=messages,
                tool_integration=tool_integration,
                model=model,
                max_rounds=15  # Let the module handle round counting
            )
    except Exception as e:
        logger.error(f"Conversation failed: {str(e)}")
        return

    # 7. Handle final outcome
    logger.info("--- LLM Interaction Complete ---")
    if isinstance(final_result_msg, dict):  # Error case
        logger.error(f"Failed with reason: {final_result_msg.get('finish_reason', 'unknown')}")
        logger.error(f"Error details: {final_result_msg.get('content', 'No details')}")
    else:
        # Display full conversation history
        logger.info("--- Full Conversation History ---")
        for msg in messages:
            logger.info(f"{msg['role'].upper()}: {msg.get('content', '')}")
        
        # Display final response
        if hasattr(final_result_msg, 'reasoning_content'):
            logger.info("--- Reasoning Process ---\n%s", final_result_msg.reasoning_content)
        logger.info("--- Final Answer ---\n%s", final_result_msg.content)

    # 8. Log final session state for inspection
    logger.info("--- Final Session State ---")
    logger.info(f"Selected Library: {session_state.get_current_library_id()}")
    logger.info(f"Custom UCF Path: {session_state.custom_ucf_path}")
    if session_state.get_cello_results():
        logger.info(f"Cello Results: {json.dumps(session_state.cello_results, indent=2)}")

if __name__ == "__main__":
    run_example()