import logging
import json
import os
from openai import OpenAI      

from tools.functions import ToolIntegration, tool_functions
from library.ucf_retrieval import get_gate_by_id, get_gates_by_type, load_ecoli_library
from design_module import DesignOrchestrator

LIBRARY_JSON_PATH = "libs/parsed/Eco1C1G1T0_parsed.json"
library_data = load_ecoli_library(LIBRARY_JSON_PATH)
library = ToolIntegration(library_data)

# Initialize the design orchestrator
design_orchestrator = DesignOrchestrator(library)

def chat_with_tool(client, messages, i=0, model="gpt-4o-mini"):
    logging.info(f"Message round: {i}")
    
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
        
        logging.info(f"Calling function: {fn_name} with args: {fn_args}")
        
        try:
            tool_result = library.call_tool_function(fn_name, fn_args)
            logging.info(f"Tool result: {json.dumps(tool_result)[:500]}...")  # Log first 500 chars to avoid huge logs
            
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
            
            return chat_with_tool(client, messages, i + 1, model)
            
        except Exception as e:
            logging.error(f"Error calling function {fn_name}: {str(e)}")
            error_result = {"error": f"Function execution failed: {str(e)}"}
            
            messages.append({
                "role": "function",
                "name": fn_name,
                "content": json.dumps(error_result)
            })
            
            return chat_with_tool(client, messages, i + 1, model)
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
