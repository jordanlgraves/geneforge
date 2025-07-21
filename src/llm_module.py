import os
import logging
import json
from openai import OpenAI
from typing import List, Dict, Any, Tuple, Optional
import asyncio

# New abstraction imports
from src.model_client import BaseModelClient, OpenAIModelClient, ArtModelClient

try:
    import art  # type: ignore
except ModuleNotFoundError:
    art = None  # type: ignore

from src.tool_registry import ToolIntegration, tool_functions
from src.session_state import SessionState


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DEBUG_MODEL = True

def get_llm_client(client_type: str = None, 
                   reasoning: bool = False, 
                   *, 
                   art_model: "art.TrainableModel" = None,
                   model_name: str = None):
    """Initialise a model client wrapper.

    Args:
        client_type: One of ``openai``, ``deepseek`` or ``art``.
        reasoning:   When *True* select the reasoning-optimised model variant
                      for providers that differentiate (e.g. OpenAI, DeepSeek).
        art_model:   Pre-initialised :class:`art.TrainableModel` instance when
                      ``client_type='art'``.  The caller is responsible for
                      having registered the model with a backend already.
        model_name:  The name of the model to use.  If not provided, the default
                      model for the client type will be used.
    Returns:
        Tuple ``(client_wrapper, model_name)`` where *client_wrapper* exposes
        the familiar ``chat.completions.create`` interface.  ``None`` is
        returned if initialisation fails.
    """

    # ------------------------------------------------------------------
    # Environment-provided credentials & defaults
    # ------------------------------------------------------------------
    openai_api_key = os.getenv("OPENAI_API_KEY", "")
    deepseek_api_key = os.getenv("DEEPSEEK_API_KEY", "")
    deepseek_base_url = os.getenv("DEEPSEEK_BASE_URL", "")
    openai_model_env = os.getenv("OPENAI_MODEL", "")
    openai_model_reasoning_env = os.getenv("OPENAI_MODEL_REASONING", "")

    client: Optional[BaseModelClient] = None
    model_name: Optional[str] = None

    # Default to deepseek if nothing specified (keeps previous behaviour)
    client_type = client_type or "deepseek"

    # ------------------------------------------------------------------
    # OpenAI or compatible endpoints
    # ------------------------------------------------------------------
    if client_type == "openai":
        logger.info("Initialising OpenAI backend")
        try:
            sdk_client = OpenAI(api_key=openai_api_key, webhook_secret=None)
            model_name = openai_model_env if not reasoning else openai_model_reasoning_env
            # Lightweight probe to ensure creds are valid
            sdk_client.models.list()
            client = OpenAIModelClient(sdk_client, model_name)
            logger.info("Connected to OpenAI with model %s", model_name)
        except Exception as exc:
            logger.error("Failed to initialise OpenAI client: %s", exc, exc_info=True)
            return None

    # ------------------------------------------------------------------
    # DeepSeek
    # ------------------------------------------------------------------
    elif client_type == "deepseek":
        logger.info("Initialising DeepSeek backend")
        try:
            sdk_client = OpenAI(api_key=deepseek_api_key, base_url=deepseek_base_url)  # type: ignore[arg-type]
            model_name = "deepseek-reasoner" if reasoning else "deepseek-coder"
            sdk_client.models.list()
            client = OpenAIModelClient(sdk_client, model_name)
            logger.info("Connected to DeepSeek with model %s", model_name)
        except Exception as exc:
            logger.error("Failed to initialise DeepSeek client: %s", exc, exc_info=True)
            return None

    # ------------------------------------------------------------------
    # Local *art* model
    # ------------------------------------------------------------------
    elif client_type == "art":
        if art is None:
            logger.error("Requested 'art' backend but package not available")
            return None
        if art_model is None:
            logger.error("'art_model' parameter is required for client_type='art'")
            return None
        try:
            client = ArtModelClient(art_model)
            model_name = client.model_name
            logger.info("Using local art model '%s'", model_name)
        except Exception as exc:
            logger.error("Failed to initialise art model client: %s", exc, exc_info=True)
            return None

    else:
        logger.error("Unknown client_type '%s'", client_type)
        return None

    return (client, model_name) if client and model_name else None

def main():
    """Example demonstrating the session-based workflow."""
    logger.info("Starting GeneForge example...")

    # 1. Initialize LLM Client
    client_info = get_llm_client()
    if not client_info:
        print("Failed to initialize LLM client. Check API keys and environment variables.")
        return
    client, _ = client_info
    print(f"Using LLM Client: {type(client).__name__}")

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

    # 5. Start the conversation loop - This main function won't stream, so it's not a great example anymore
    print("\nStarting LLM conversation...")
    # The run_assistant function is now designed for streaming and requires an event handler,
    # so we cannot easily call it here in this synchronous example.
    # We would need a simple console-based event handler to run this.
    print("Main function cannot run streaming assistant directly. Run the UI with `streamlit run src/ui/app.py`")
    

if __name__ == "__main__":
    # Load .env file if present
    from dotenv import load_dotenv
    load_dotenv()
    main()
