import os
import logging
import json
from typing import List, Dict, Any, Tuple, Optional
import asyncio
from litellm import acompletion, completion

try:
    import art
except ModuleNotFoundError:
    art = None

from src.tool_registry import ToolIntegration, tool_functions
from src.session_state import SessionState

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DEBUG_MODEL = True

def get_llm_params(
    client_type: str = None, 
    reasoning: bool = False, 
    *, 
    art_model: "art.TrainableModel" = None,
    model_name_str: str = None
) -> Dict[str, Any]:
    """Get parameters for litellm completion.

    Args:
        client_type: One of ``openai``, ``deepseek`` or ``art``.
        reasoning:   When *True* select the reasoning-optimised model variant
                      for providers that differentiate (e.g. OpenAI, DeepSeek).
        art_model:   Pre-initialised :class:`art.TrainableModel` instance when
                      ``client_type='art'``.
        model_name_str:  The name of the model to use.

    Returns:
        Dictionary of parameters for litellm.completion.
    """
    client_type = client_type or "deepseek"
    params = {}

    if client_type == "art":
        if art_model:
            params["model"] = f"hosted_vllm/{art_model.name}"
            params["api_base"] = art_model.inference_base_url
            params["api_key"] = art_model.inference_api_key
            params["logprobs"] = True
        else:
            raise ValueError("'art_model' is required for client_type='art'")
    elif client_type == "openai":
        model_name = os.getenv("OPENAI_MODEL_REASONING") if reasoning else os.getenv("OPENAI_MODEL")
        params["model"] = f"openai/{model_name}"
    elif client_type == "deepseek":
        model_name = "deepseek-reasoner" if reasoning else "deepseek-coder"
        params["model"] = f"deepseek/{model_name}"
    else:
        raise ValueError(f"Unknown client_type '{client_type}'")

    if model_name_str:
        params["model"] = model_name_str

    logger.info("Using LLM with params: %s", params)
    return params

def main():
    """Example demonstrating the session-based workflow."""
    logger.info("Starting GeneForge example...")

    # 1. Initialize LLM
    llm_params = get_llm_params()
    print(f"Using LLM with params: {llm_params}")

    # 2. Create a SessionState for this request
    session_state = SessionState()
    print(f"Initial Session State: Library Manager ready, {len(session_state.cello_library.get_available_libraries())} libraries found.")

    # 3. Create ToolIntegration linked to this session's state
    tool_integration = ToolIntegration(session_state)
    print("Tool Integration initialized for the session.")

    # 4. Define the initial user request and system prompt
    system_prompt = "You are a helpful assistant for genetic circuit design. Use the available tools to fulfill user requests step-by-step. Always confirm library selection before listing parts."
    user_request = (
        "First, please select the 'Eco1C1G1T1' library. "
        "Then, list the available promoters in that library."
    )
    print(f"\nUser Request: {user_request}")

    # 5. Start the conversation loop
    print("\nStarting LLM conversation...")
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_request},
    ]

    try:
        response = completion(
            **llm_params,
            messages=messages,
            tools=tool_functions
        )
        print("Response from LLM:")
        print(response)
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    main()
