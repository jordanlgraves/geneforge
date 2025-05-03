import os
import logging
import json
from openai import OpenAI
from typing import List, Dict, Any, Tuple, Optional

from src.tools.functions import ToolIntegration, tool_functions
from src.session_state import SessionState


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DEBUG_MODEL = True

def get_llm_client(client_type: str = None, reasoning: bool = False) -> Optional[Tuple[OpenAI, str]]:
    """Gets the LLM client and model name based on environment variables."""
    openai_api_key = os.getenv("OPENAI_API_KEY")
    deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
    deepseek_base_url = os.getenv("DEEPSEEK_BASE_URL")

    client: Optional[OpenAI] = None
    model: Optional[str] = None

    # Prioritize DeepSeek if configured
    if client_type == "deepseek" or client_type is None:
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
    # Fallback to OpenAI
    elif client_type == "openai":
        logger.info("Using OpenAI API")
        try:
            client = OpenAI(api_key=openai_api_key)
            model = "gpt-4o-mini"  if not reasoning else "o3-mini"
            # Test connection (optional but recommended)
            client.models.list()
            logger.info(f"Successfully connected to OpenAI with model {model}")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            client = None
            model = None
    # No keys found
    else:
        logger.error("No API keys found for OpenAI or DeepSeek in environment variables.")
        return None

    if client and model:
        return client, model
    else:
        logger.error("LLM Client initialization failed.")
        return None

def _check_for_repeated_errors(messages):
    """
    Checks for repeated errors in function calls and adds a system message if the same error 
    is detected multiple times for the same function.
    
    Args:
        messages (list): The conversation history
        
    Returns:
        bool: True if a special message was added, False otherwise
    """
    if len(messages) < 4:
        return False
    
    error_count = 0
    last_error = None
    last_function = None
    
    for j in range(len(messages) - 1, 0, -2):  # Check every other message (function responses)
        if j < 3:  # Make sure we don't go out of bounds
            break
            
        if messages[j].get("role") == "function" and messages[j-1].get("role") == "assistant":
            try:
                content = json.loads(messages[j].get("content", "{}"))
                function_name = messages[j-1].get("function_call", {}).get("name")
                
                if "error" in content and function_name:
                    current_error = content["error"]
                    
                    # If this is the same function and error as before
                    if last_error == current_error and last_function == function_name:
                        error_count += 1
                    
                    last_error = current_error
                    last_function = function_name
                    
                    # If we see the same error 3 times in a row for the same function,
                    # add a special message to break the loop
                    if error_count >= 2:  # We've seen it 3 times (this one + 2 previous)
                        logging.warning(f"Same error detected {error_count+1} times for function {function_name}: {current_error}")
                        
                        # Add a special message to help the model understand it should stop trying this function
                        messages.append({
                            "role": "system",
                            "content": f"IMPORTANT: The function '{function_name}' is consistently returning the error: '{current_error}'. Please stop attempting to use this function and provide an alternative solution or a helpful response without it."
                        })
                        return True
            except Exception as e:
                logging.error(f"Error checking for repeated errors: {e}")
    
    return False

def _handle_tool_call(
    client: OpenAI,
    messages: List[Dict[str, Any]],
    fn_call: Any,
    tool_integration: ToolIntegration,
    model: str
) -> Tuple[List[Dict[str, Any]], bool]:
    """
    Handles executing a tool function call using the provided ToolIntegration instance.
    """
    fn_name = fn_call.name
    fn_args_json = fn_call.arguments or "{}"

    try:
        fn_args = json.loads(fn_args_json)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode function arguments for {fn_name}: {fn_args_json}. Error: {e}")
        error_result = {"error": f"Invalid JSON arguments provided: {e}"}
        
        # Append error message back to the conversation for the LLM
        messages.append({
            "role": "assistant", 
            "function_call": {"name": fn_name, "arguments": fn_args_json},
            "content": None
        })
        
        # Use the correct format based on the model type
        if "deepseek" in model.lower():
            # DeepSeek format
            messages.append({
                "role": "tool",
                "tool_call_id": fn_call.id if hasattr(fn_call, 'id') else "call_id",
                "content": json.dumps(error_result)
            })
        else:
            # OpenAI format (newer API)
            messages.append({
                "role": "assistant",
                "content": json.dumps(error_result)
            })
        
        return messages, True  # Function was attempted but failed

    logging.info(f"Calling function: {fn_name} with args: {fn_args}")

    try:
        # Use the passed tool_integration instance to call the function
        tool_result = tool_integration.call_tool_function(fn_name, fn_args)
        
        # Log result concisely
        result_str = json.dumps(tool_result)
        log_msg = f"Tool result: {result_str[:500]}{'...' if len(result_str) > 500 else ''}"
        if isinstance(tool_result, dict) and tool_result.get("success") is False:
             logger.warning(log_msg) # Log failures as warnings
        elif isinstance(tool_result, dict) and "error" in tool_result:
             logger.error(log_msg) # Log explicit errors as errors
        else:
             logger.info(log_msg) # Log success as info

        # Append the function call attempt and its result
        messages.append({
            "role": "assistant",
            "function_call": {"name": fn_name, "arguments": fn_args_json},
            "content": None # Important: Content is null for function calls
        })
        
        # Use the correct format based on the model type
        if "deepseek" in model.lower():
            # DeepSeek format
            messages.append({
                "role": "tool",
                "tool_call_id": fn_call.id if hasattr(fn_call, 'id') else "call_id",
                "content": json.dumps(tool_result)
            })
        else:
            # OpenAI format (newer API)
            messages.append({
                "role": "assistant",
                "content": json.dumps(tool_result)
            })

        return messages, True  # Function was called successfully

    except Exception as e:
        logger.error(f"Unexpected error calling function {fn_name} via ToolIntegration: {e}", exc_info=True)
        error_result = {"error": f"Internal error executing function {fn_name}: {str(e)}"}

        # Append the failed attempt and the error result
        messages.append({
            "role": "assistant",
            "function_call": {"name": fn_name, "arguments": fn_args_json},
            "content": None
        })
        
        # Use the correct format based on the model type
        if "deepseek" in model.lower():
            # DeepSeek format
            messages.append({
                "role": "tool",
                "tool_call_id": fn_call.id if hasattr(fn_call, 'id') else "call_id",
                "content": json.dumps(error_result)
            })
        else:
            # OpenAI format (newer API)
            messages.append({
                "role": "assistant",
                "content": json.dumps(error_result)
            })

        if DEBUG_MODEL:
            raise e # Reraise in debug mode for easier debugging

        return messages, True  # Function was attempted but failed
        
def chat_with_tool(
    client: OpenAI,
    messages: List[Dict[str, Any]],
    tool_integration: ToolIntegration, # Pass ToolIntegration instance
    i: int = 0,
    model: str = "gpt-4o-mini", # Default model
    max_rounds: int = 10
) -> Dict[str, Any]:
    """
    Main chat loop that interacts with the LLM, handling function calls via ToolIntegration.
    """
    logger.info(f"\n\n--- Message round: {i} ---\n\n")
    # Log current messages (optional, can be verbose)
    for mi, message in enumerate(messages):
        logger.info(f"\nMessage {mi}: {message}")

    # Safety check
    if i >= max_rounds:
        logger.warning(f"Maximum number of rounds ({max_rounds}) reached. Aborting.")
        # Return a structured error message
        return {
            "role": "assistant",
            "content": f"Processing aborted after {max_rounds} rounds to prevent infinite loops. The task may be incomplete.",
            "finish_reason": "max_rounds_exceeded"
        }

    # Check for repeated errors (only needs messages)
    if i >= 3: # Start checking after a few rounds
        if _check_for_repeated_errors(messages):
             logger.warning("Repeated error detected. System message added to guide the LLM.")
             # The system message is now part of 'messages', proceed to the API call

    # Determine if we're using DeepSeek reasoning model and adjust parameters accordingly
    is_reasoning_model = "deepseek-reasoner" in model
    
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        functions=tool_functions,
        function_call="auto",
        reasoning_effort="low"
    )

    response_message = response.choices[0].message
    logger.info(f"\nResponse message: {response_message}")
    finish_reason = response.choices[0].finish_reason

    # The reason the model stopped generating tokens. This will be stop if the model hit a natural stop point or a provided stop sequence, length if the maximum number of tokens specified in the request was reached, content_filter if content was omitted due to a flag from our content filters, tool_calls if the model called a tool
    logger.info(f"Finish reason: {finish_reason}")

    if finish_reason == "stop":
        logger.info("Model stopped generating tokens. Returning final response.")
        return response_message

    if finish_reason == "length":
        logger.info("Maximum number of tokens reached. Returning final response.")
        return response_message

    if finish_reason == "content_filter":
        logger.info("Content was omitted due to a flag from our content filters. Returning final response.")
        return response_message
    
    # Log reasoning content if available (for deepseek-reasoner)
    if hasattr(response_message, 'reasoning_content') and response_message.reasoning_content:
        logger.info(f"Reasoning content: {response_message.reasoning_content[:500]}...")
    
    # Check if the model wants to call a function
    if response_message.function_call or finish_reason == "tool_calls" or finish_reason == "function_call":
        logger.info(f"LLM requested function call: {response_message.function_call.name}")
        
        # Execute the function call without recursive chat_with_tool call
        updated_messages, function_called = _handle_tool_call(
            client,
            messages,
            response_message.function_call,
            tool_integration,
            model
        )
        
        # Continue the conversation with the updated messages
        if function_called:
            return chat_with_tool(
                client,
                updated_messages,
                tool_integration,
                i + 1,
                model,
                max_rounds
            )
        else:
            # If function couldn't be called, return the current response
            return response_message
    else:
        # No function call, return the final response
        logger.info("LLM provided final response.")
        
        # For multi-round conversations with reasoning models,
        # exclude the reasoning_content when appending to messages
        # but keep it in the returned response
        if hasattr(response_message, 'reasoning_content') and response_message.reasoning_content:
            logger.info("Response includes reasoning content which will be returned but not included in future messages")
        
        return response_message

def main():
    """Example demonstrating the session-based workflow."""
    logger.info("Starting GeneForge example...")

    # 1. Initialize LLM Client
    client_info = get_llm_client()
    if not client_info:
        print("Failed to initialize LLM client. Check API keys and environment variables.")
        return
    client, model = client_info
    print(f"Using LLM Client: {type(client).__name__}, Model: {model}")

    # 2. Create a SessionState for this request
    session_state = SessionState()
    print(f"Initial Session State: Library Manager ready, {len(session_state.library_manager.get_available_libraries())} libraries found.")

    # 3. Create ToolIntegration linked to this session's state
    tool_integration = ToolIntegration(session_state)
    print("Tool Integration initialized for the session.")

    # 4. Define the initial user request and messages
    # Example: A multi-step request that requires state
    user_request = (
        "First, please select the 'Eco1C1G1T1' library. "
        "Then, list the available promoters in that library."
    )
    messages = [
        {"role": "system", "content": "You are a helpful assistant for genetic circuit design. Use the available tools to fulfill user requests step-by-step. Always confirm library selection before listing parts."},
        {"role": "user", "content": user_request}
    ]
    print(f"\nUser Request: {user_request}")

    # 5. Start the conversation loop, passing the client and session-specific tool integration
    print("\nStarting LLM conversation...")
    final_answer_msg = chat_with_tool(
        client=client,
        messages=messages, # The message list will be modified in place
        tool_integration=tool_integration, # Pass the session's tool integration
        model=model,
        max_rounds=15 # Allow more rounds for multi-step tasks
    )

    # 6. Print the final result
    print("\n--- LLM Conversation Ended ---")
    if isinstance(final_answer_msg, dict): # Handle potential error messages from chat_with_tool
        print(f"Final Status: {final_answer_msg.get('finish_reason', 'unknown')}")
        print(f"Assistant Final Output:\n{final_answer_msg.get('content', 'No content available.')}")
    else: # Assuming it's a ChatCompletionMessage object
        # Check if there's reasoning content (for deepseek-reasoner)
        if hasattr(final_answer_msg, 'reasoning_content') and final_answer_msg.reasoning_content:
            print(f"Reasoning Process:\n{final_answer_msg.reasoning_content}")
        
        print(f"Final Status: {final_answer_msg.finish_reason}")
        print(f"Assistant Final Output:\n{final_answer_msg.content}")

    # 7. Inspect final session state (optional)
    print("\n--- Final Session State ---")
    print(f"Selected Library ID: {session_state.get_current_library_id()}")
    print(f"Custom UCF Path: {session_state.custom_ucf_path}")
    # print(f"Cello Results: {session_state.cello_results}") # If stored

if __name__ == "__main__":
    # Load .env file if present
    from dotenv import load_dotenv
    load_dotenv()
    main()
