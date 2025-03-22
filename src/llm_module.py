import os
import logging
import json
import time
from typing import List, Dict, Any, Optional, Callable, Tuple, Union
from openai import OpenAI

from src.tools.functions import ToolIntegration, tool_functions
from src.library.ucf_retrieval import get_gate_by_id, get_gates_by_type, load_ecoli_library
from src.design_module import DesignOrchestrator

LIBRARY_JSON_PATH = "libs/parsed/Eco1C1G1T0_parsed.json"
library_data = load_ecoli_library(LIBRARY_JSON_PATH)
library = ToolIntegration(library_data)

# Initialize the design orchestrator
design_orchestrator = DesignOrchestrator(library)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEBUG_MODEL = True

def chat_with_tool(client, messages, i=0, model="gpt-4o-mini", max_rounds=10):
    logging.info(f"Message round: {i}")
    
    # Safety check to prevent infinite loops
    if i >= max_rounds:
        logging.warning(f"Maximum number of rounds ({max_rounds}) reached. Breaking out of the loop.")
        return {
            "role": "assistant",
            "content": "I apologize, but I seem to be having trouble completing this task. I've attempted to use several functions but encountered persistent errors. Please check if the required functionality is available or try a different approach."
        }
    
    # Check for repeated errors
    if i >= 3 and len(messages) >= 4:
        # Check the last three function calls
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
                            break
                except Exception as e:
                    logging.error(f"Error checking for repeated errors: {e}")
    
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        functions=tool_functions,
        function_call="auto"
    )
    
    # If the model's response indicates a function call...
    if response.choices[0].finish_reason == "function_call":
        fn_call = response.choices[0].message.function_call
        fn_name = fn_call.name
        fn_args_json = fn_call.arguments or "{}"
        fn_args = json.loads(fn_args_json)
        
        logging.info(f"\n\nCalling function: {fn_name} with args: {fn_args}")
        
        try:
            tool_result = library.call_tool_function(fn_name, fn_args)
            logging.info(f"Tool result: {json.dumps(tool_result)[:500]}...\n\n")  # Log first 500 chars to avoid huge logs
            
            # Check if there was an error in the tool result
            if isinstance(tool_result, dict) and "error" in tool_result:
                logging.error(f"Tool error: {tool_result['error']}")
            
            # Append the function's result to the conversation history
            messages.append({
                "role": "assistant",
                "function_call": {"name": fn_name, "arguments": fn_args_json},
                "content": None
            })
            
            messages.append({
                "role": "function",
                "name": fn_name,
                "content": json.dumps(tool_result)
            })
            
            return chat_with_tool(client, messages, i + 1, model, max_rounds)
            
        except Exception as e:
            if DEBUG_MODEL:
                # reraise so we can see the error in the debugger
                raise e
            else:
                logging.error(f"Error calling function {fn_name}: {str(e)}")
                error_result = {"error": f"Function execution failed: {str(e)}"}
                
                messages.append({
                    "role": "function",
                    "name": fn_name,
                    "content": json.dumps(error_result)
                })
                
                return chat_with_tool(client, messages, i + 1, model, max_rounds)
    else:
        logging.info("No function call made; returning the model's response.")
        return response.choices[0].message

def main():
    CLIENT_MODE = "DEEPSEEK"

    # OPENAI
    if CLIENT_MODE == "OPENAI":
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    else:
        # DEEPSEEK
        client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url=os.getenv("DEEPSEEK_BASE_URL"))

    user_request = "Hi, can you find me any NOR gates in the library?"
    messages = [
        {"role": "system", "content": "You are a helpful assistant with knowledge of genetic gates and genetic circuit design."},
        {"role": "user", "content": user_request}
    ]
    
    answer_msg = chat_with_tool(client, messages, model="deepseek-reasoner")
    print("Assistant final answer:")
    print(answer_msg.content)

if __name__ == "__main__":
    main()
