# tests/test_runner.py

import os
import json
import logging
from openai import OpenAI

from src.geneforge_config import Config
from src.tools.functions import ToolIntegration
from src.llm_module import chat_with_tool

def run_test_1_find_nor_gates(client):
    user_request = "Could you show me all the NOR gates in the library?"
    messages = [
        {"role": "system", 
         "content": "You are an AI that helps with synthetic biology gate retrieval."},
        {"role": "user", "content": user_request}
    ]
    final_answer = chat_with_tool(client, messages)
    print("=== Test 1 Output ===")
    print(final_answer.content)

def run_test_2_gate_info(client):
    user_request = "I'd like more details about a gate with ID 'AmtR'."
    messages = [
        {"role": "system",
         "content": "You are an AI that helps with synthetic biology gate retrieval."},
        {"role": "user", "content": user_request}
    ]
    final_answer = chat_with_tool(client, messages)
    print("=== Test 2 Output ===")
    print(final_answer.content)

def run_test_3_simulate_circuit(client):
    # We'll ask the LLM to simulate a circuit with 2 gates
    circuit_request = {
        "gates": [
            {"id": "SrpR_NOR", "type": "NOR"},
            {"id": "AmtR", "type": "repressor"}
        ],
        "connections": [
            # example placeholders
        ]
    }
    user_request = f"Here is a circuit: {json.dumps(circuit_request)}. Could you simulate it?"
    messages = [
        {"role": "system", "content": "You are an AI that can also simulate circuits."},
        {"role": "user", "content": user_request}
    ]
    final_answer = chat_with_tool(client, messages)
    print("=== Test 3 Output ===")
    print(final_answer.content)

def test_single_input_not_design(client):
    """
    We want the LLM to pick a promoter, repressor, terminator, etc. 
    Then provide a final arrangement or partial DNA design.
    """
    user_prompt = (
        "I want you to design a single-input NOT gate in E. coli. "
        "Choose a suitable promoter, repressor, and terminator from the library. "
        "Output a recommended DNA arrangement. Then let's see if we can simulate it."
    )
    messages = [
        {"role": "system", "content": "You are a synthetic biology design assistant."},
        {"role": "user", "content": user_prompt}
    ]
    final_msg = chat_with_tool(client, messages)
    print("=== Single-Input NOT Gate Design Result ===")
    print(final_msg.content)

def test_cello_basic_circuit(client):
    """
    Test the LLM's ability to design a simple circuit using Cello.
    Uses a basic NOT gate as an example.
    """
    user_prompt = """
    Design a NOT gate circuit in E. coli where:
    1. Input: arabinose (AraC)
    2. Output: GFP (should be ON when input is OFF)
    
    Please create the Verilog code and use Cello to design the DNA circuit.
    Make sure to set reasonable parameters for the design process.
    """
    
    messages = [
        {"role": "system", "content": "You are a synthetic biology design assistant."},
        {"role": "user", "content": user_prompt}
    ]
    
    final_msg = chat_with_tool(client, messages)
    print("\n=== Basic Cello Circuit Design Result ===")
    print(final_msg.content)
    return final_msg

def test_cello_advanced_circuit(client):
    """
    Test the LLM's ability to design a more complex circuit and configure Cello parameters.
    Uses a 2-input AND gate with specific performance requirements.
    """
    user_prompt = """
    Design a 2-input AND gate circuit in E. coli where:
    1. Inputs: IPTG (LacI) and aTc (TetR)
    2. Output: GFP (should be ON only when both inputs are present)
    3. Requirements:
       - Minimal leak in OFF state (<5% of ON state)
       - Fast response time
       
    Please:
    1. Create the Verilog code
    2. Configure Cello for thorough optimization (use exhaustive search)
    3. Analyze the results and suggest improvements if needed
    """
    
    messages = [
        {"role": "system", "content": "You are a synthetic biology design assistant."},
        {"role": "user", "content": user_prompt}
    ]
    
    final_msg = chat_with_tool(client, messages)
    print("\n=== Advanced Cello Circuit Design Result ===")
    print(final_msg.content)
    return final_msg

def test_cello_iterative_design(client):
    """
    Test the LLM's ability to iterate on a design based on Cello's output.
    This demonstrates multi-step interaction and optimization.
    """
    # First design attempt
    initial_prompt = """
    Design a genetic toggle switch in E. coli with:
    1. Set input: aTc
    2. Reset input: IPTG
    3. Output: GFP (state indicator)
    
    Start with a basic design and we'll optimize based on the results.
    """
    
    messages = [
        {"role": "system", "content": "You are a synthetic biology design assistant."},
        {"role": "user", "content": initial_prompt}
    ]
    
    # Get initial design
    first_attempt = chat_with_tool(client, messages)
    print("\n=== Initial Toggle Switch Design ===")
    print(first_attempt.content)
    
    # Simulate user reviewing results and requesting optimization
    optimization_prompt = """
    Based on the Cello results above, please optimize the design:
    1. Adjust promoter strengths if needed
    2. Consider adding degradation tags
    3. Try alternative repressor pairs
    4. Use exhaustive search to find optimal parameters
    """
    
    messages.extend([
        {"role": "assistant", "content": first_attempt.content},
        {"role": "user", "content": optimization_prompt}
    ])
    
    # Get optimized design
    optimized_attempt = chat_with_tool(client, messages)
    print("\n=== Optimized Toggle Switch Design ===")
    print(optimized_attempt.content)
    return optimized_attempt

def main():
    logging.basicConfig(level=logging.INFO)

    config = Config()
    client = OpenAI(api_key=config.openai_api_key)

    print("\n-- Running Basic Tests --")
    # run_test_1_find_nor_gates(client)
    # run_test_2_gate_info(client)

    print("\n-- Running Cello Integration Tests --")
    print("\n1. Testing Basic Circuit Design")
    test_cello_basic_circuit(client)
    
    # print("\n2. Testing Advanced Circuit Design")
    # test_cello_advanced_circuit(client)
    
    # print("\n3. Testing Iterative Design Process")
    # test_cello_iterative_design(client)

if __name__ == "__main__":
    main()
