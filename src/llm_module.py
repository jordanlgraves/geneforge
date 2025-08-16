import os
import logging
from typing import Dict, Any
from litellm import completion

try:
    import art
except ModuleNotFoundError:
    art = None

from src.tool_registry import ToolIntegration, tool_functions
from src.session_state import SessionState

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DEBUG_MODEL = True

models = [
    "gemini/gemini-2.5-pro", 
    "gpt-4o-mini",
    "gpt-5-nano-2025-08-07",
    "o3",
    "deepseek-chat",
]

def get_llm_params(
    model: str | None = None,
    *,
    art_model: Any | None = None,
) -> Dict[str, Any]:
    """Build LiteLLM params from a human-friendly model string.

    Args:
        model:       Desired model, e.g. ``"gpt-4o"``, ``"deepseek-reasoner"``,
                     ``"google/gemini-1.5-pro"`` or fully-qualified like
                     ``"openai/gpt-4o"``. If omitted, a sensible default is
                     chosen (DeepSeek coder vs reasoner) unless ``art_model``
                     is provided.

        art_model:   Local ART backend; when provided and ``model`` is omitted
                     or refers to this backend, use ``hosted_vllm/<name>`` with
                     the provided credentials.

    Returns:
        Dictionary of parameters for ``litellm.completion``/``acompletion``.
    """

    def _infer_provider(model_name: str) -> str:
        if "/" in model_name:
            return model_name.split("/", 1)[0]
        if model_name.startswith("hosted_vllm/"):
            return "hosted_vllm"
        lowered = model_name.lower()
        if lowered.startswith(("gpt-", "o1", "o3", "o4", "gpt4", "gpt3")):
            return "openai"
        if lowered.startswith("deepseek"):
            return "deepseek"
        if lowered.startswith("gemini") or lowered.startswith("models/gemini"):
            return "google"
        if lowered.startswith(("claude", "anthropic")):
            return "anthropic"
        return "openai"  # conservative default

    params: Dict[str, Any] = {}
    params["tool_choice"] = "auto"
    # other options:
    # params["stream"] = True

    # ART backend handling
    if art_model is not None and (model is None or model == art_model.name or str(model).startswith("hosted_vllm/")):
        params["model"] = model if (model and model.startswith("hosted_vllm/")) else f"hosted_vllm/{art_model.name}"
        params["api_base"] = art_model.inference_base_url
        params["api_key"] = art_model.inference_api_key
        params["logprobs"] = True
        logger.info("Using LLM with params: %s", params)
        return params

    # If model not provided, choose provider-specific defaults
    if model is None:
        # Prefer DeepSeek defaults if no explicit preference given
        default_model = "gpt-4o"
        provider = _infer_provider(default_model)
        params["model"] = f"{provider}/{default_model}"
        logger.info("Using LLM with params: %s", params)
        return params

    provider = _infer_provider(model)

    # Fully-qualified already provided
    if "/" in model or model.startswith("hosted_vllm/"):
        params["model"] = model
    else:
        params["model"] = f"{provider}/{model}"

    if provider == "google":
        assert os.getenv("GEMINI_API_KEY"), "GEMINI_API_KEY is not set"
        params["logprobs"] = True
        # if "gemini-2.5" in model:
        #     params["reasoning_effort"] = "high"
    elif provider == "openai":    
        assert os.getenv("OPENAI_API_KEY"), "OPENAI_API_KEY is not set"
        if not any(x in model for x in ("gpt-4o-mini", "gpt-5-nano")):
            params["logprobs"] = True
        if "o3" in model:                   # openai does not support parameters: ['logprobs'], for model=o3            
            if "logprobs" in params: 
                del params["logprobs"]
            params["temperature"] = 1       # 'temperature' does not support 0.0 with this model. Only the default (1) value is supported.
        if 'gpt-5' in model:
            params["temperature"] = 1       # 'temperature' does not support 0.0 with this model. Only the default (1) value is supported.
    elif provider == "deepseek":
        assert os.getenv("DEEPSEEK_API_KEY"), "DEEPSEEK_API_KEY is not set"

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
