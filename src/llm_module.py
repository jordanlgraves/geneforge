import os
import logging
import json
from openai import OpenAI
from typing import List, Dict, Any, Tuple, Optional

from src.tool_registry import ToolIntegration, tool_functions
from src.session_state import SessionState


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DEBUG_MODEL = True

def get_llm_client(client_type: str = None, reasoning: bool = False) -> Optional[Tuple[OpenAI, str]]:
    """Initialise an LLM client.

    The caller may supply credentials via *environment variables* **or** by
    setting them dynamically in ``os.environ`` *before* calling this
    function.  The Streamlit UI does the latter so that users can paste keys
    at runtime.

    Returns:
        (OpenAI client instance, model_name)  – or ``None`` on failure.
    """

    # The UI stores (or updates) credentials in the process environment so we
    # always read from ``os.environ`` here.  This keeps the public API simple
    # and avoids passing sensitive strings around unnecessarily.
    openai_api_key = os.getenv("OPENAI_API_KEY", "")
    deepseek_api_key = os.getenv("DEEPSEEK_API_KEY", "")
    deepseek_base_url = os.getenv("DEEPSEEK_BASE_URL", "")
    openai_model = os.getenv("OPENAI_MODEL", "")
    openai_model_reasoning = os.getenv("OPENAI_MODEL_REASONING", "")

    client: Optional[OpenAI] = None
    model: Optional[str] = None

    if client_type == "openai":
        logger.info("Using OpenAI API")
        try:
            client = OpenAI(api_key=openai_api_key)
            model = openai_model if not reasoning else openai_model_reasoning
            # Test connection (optional but recommended)
            client.models.list()
            logger.info(f"Successfully connected to OpenAI with model {model}")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            client = None
            model = None
    elif client_type == "deepseek" or client_type is None:
        logger.info("Using DeepSeek API")
        try:
            client = OpenAI(api_key=deepseek_api_key, base_url=deepseek_base_url)
            model = "deepseek-reasoner" if reasoning else "deepseek-coder"
            client.models.list()
            logger.info(f"Successfully connected to DeepSeek with model {model}")
        except Exception as e:
            logger.error(f"Failed to initialize DeepSeek client: {e}")
            client = None # Ensure client is None on failure
            model = None
    else:
        logger.error("No API keys found for OpenAI or DeepSeek in environment variables.")
        return None

    if client and model:
        return client, model
    else:
        logger.error("LLM Client initialization failed.")
        return None

def get_or_create_assistant(client: OpenAI, session_state: SessionState, system_prompt: str) -> str:
    """Get existing assistant or create a new one."""
    if session_state.assistant_id:
        logger.info(f"Using existing assistant: {session_state.assistant_id}")
        return session_state.assistant_id

    logger.info("Creating new assistant...")
    import dotenv
    dotenv.load_dotenv()
    openai_model = os.getenv("OPENAI_MODEL", "")
    
    assistant = client.beta.assistants.create(
        name="GeneForge Assistant",
        instructions=system_prompt,
        model=openai_model,
        tools=tool_functions,
        temperature=0.0
    )
    session_state.assistant_id = assistant.id
    logger.info(f"Created new assistant: {assistant.id}")
    return assistant.id

def get_or_create_thread(client: OpenAI, session_state: SessionState) -> str:
    """Get existing thread or create a new one."""
    if session_state.thread_id:
        logger.info(f"Using existing thread: {session_state.thread_id}")
        return session_state.thread_id

    logger.info("Creating new thread...")
    thread = client.beta.threads.create()
    session_state.thread_id = thread.id
    logger.info(f"Created new thread: {thread.id}")
    return thread.id
        
def run_assistant(
    client: OpenAI,
    session_state: SessionState,
    user_prompt: str,
    system_prompt: str,
    event_handler: "AssistantEventHandler"
):
    """
    Streams an assistant run and delegates event handling to the provided handler.
    """
    assistant_id = get_or_create_assistant(client, session_state, system_prompt)
    thread_id = get_or_create_thread(client, session_state)

    # Add the user's message to the thread
    client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=user_prompt
    )
    logger.info(f"Added user message to thread {thread_id}")

    # Stream the run
    with client.beta.threads.runs.stream(
        thread_id=thread_id,
        assistant_id=assistant_id,
        event_handler=event_handler
    ) as stream:
        stream.until_done()

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
