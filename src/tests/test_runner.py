# tests/test_runner.py

import os
import json
import logging
from openai import OpenAI
import unittest

from src.geneforge_config import Config
from src.tools.functions import ToolIntegration
from src.llm_module import chat_with_tool
from src.tests.test_ucf_customization import TestUCFCustomization

def setup_client():
    """
    Set up and return an OpenAI client for testing.
    Uses environment variables for API keys.
    """
    # Check if we should use OpenAI or DeepSeek
    client_mode = os.getenv("CLIENT_MODE", "OPENAI")
    
    if client_mode == "OPENAI":
        return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    else:
        # DeepSeek
        return OpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"), 
            base_url=os.getenv("DEEPSEEK_BASE_URL")
        )

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
    
    The system should automatically select an appropriate UCF file based on:
    1. Organism: E. coli
    2. Input: arabinose (AraC)
    3. Output: GFP
    4. Gate type: NOT
    """
    # Enhanced system prompt that instructs the LLM to select appropriate UCF files
    system_prompt = """
    You are a synthetic biology design assistant that can design genetic circuits.
    
    When designing circuits with Cello:
    1. First analyze the user's requirements to identify:
       - Target organism (e.g., E. coli, yeast)
       - Required inputs/inducers (e.g., arabinose, IPTG)
       - Required outputs (e.g., GFP, RFP)
       - Required gate types (e.g., NOT, NOR, AND)
    
    2. Use the design_circuit function to automatically select an appropriate UCF file
       and design the circuit based on these requirements.
    
    3. Explain your design choices and the results to the user.
    """
    
    user_prompt = """
    I want to design a NOT gate circuit in E. coli that is induced by arabinose and 
    produces GFP when arabinose is absent. Please design this circuit for me.
    """
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    final_answer = chat_with_tool(client, messages)
    print("=== Cello Basic Circuit Design Result ===")
    print(final_answer.content)

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

def test_custom_design_workflow(client):
    """
    Test the custom design workflow with part selection and optimization.
    """
    # Start with a higher level request that requires part selection
    user_prompt = """
    I want to design a two-input AND gate in E. coli where:
    1. First input is IPTG (inducible by LacI)
    2. Second input is arabinose (inducible by AraC)
    3. Output is GFP
    
    Let's design this step by step:
    1. First, let's select appropriate promoters, repressors, and other parts
    2. Then create a custom UCF with these parts
    3. Next, write the Verilog code for the AND gate
    4. Design and simulate the circuit
    5. If needed, optimize the promoter strengths
    """
    
    messages = [
        {"role": "system", "content": "You are a synthetic biology design assistant."},
        {"role": "user", "content": user_prompt}
    ]
    
    # This should trigger multiple tool calls and a multi-step conversation
    final_msg = chat_with_tool(client, messages)
    print("\n=== Custom Design Workflow Result ===")
    print(final_msg.content)
    return final_msg

def test_promoter_optimization(client):
    """
    Test the ability to optimize promoters for specific strength targets.
    """
    user_prompt = """
    I have a circuit design where I need a promoter with approximately 40% of the strength 
    of the standard pBAD promoter. Can you help me optimize a promoter sequence to achieve 
    this target strength? Start with the pBAD sequence and modify it.
    """
    
    messages = [
        {"role": "system", "content": "You are a synthetic biology design assistant."},
        {"role": "user", "content": user_prompt}
    ]
    
    final_msg = chat_with_tool(client, messages)
    print("\n=== Promoter Optimization Result ===")
    print(final_msg.content)
    return final_msg

def test_ucf_file_selection(client):
    """Test the LLM's ability to select an appropriate UCF file."""
    user_request = "I need a UCF file for E. coli. What options do I have?"
    messages = [
        {"role": "system", "content": "You are a helpful assistant with knowledge of genetic gates and genetic circuit design."},
        {"role": "user", "content": user_request}
    ]
    
    final_msg = chat_with_tool(client, messages)
    print("=== UCF File Selection Result ===")
    print(final_msg.content)
    return final_msg

def test_ucf_file_selection_with_inducers(client):
    """Test the LLM's ability to select a UCF file with specific inducer requirements."""
    user_request = "I need a UCF file for E. coli that works with arabinose and IPTG inducers."
    messages = [
        {"role": "system", "content": "You are a helpful assistant with knowledge of genetic gates and genetic circuit design."},
        {"role": "user", "content": user_request}
    ]
    
    final_msg = chat_with_tool(client, messages)
    print("=== UCF File Selection with Inducers Result ===")
    print(final_msg.content)
    return final_msg

def test_ucf_file_selection_unsupported(client):
    """Test the LLM's handling of unsupported organism requests."""
    user_request = "I need a UCF file for Pseudomonas aeruginosa."
    messages = [
        {"role": "system", "content": "You are a helpful assistant with knowledge of genetic gates and genetic circuit design."},
        {"role": "user", "content": user_request}
    ]
    
    final_msg = chat_with_tool(client, messages)
    print("=== UCF File Selection Unsupported Result ===")
    print(final_msg.content)
    return final_msg

def test_design_circuit_function(client):
    """
    Test the design_circuit function directly with different circuit types.
    This test verifies that the function can handle various circuit designs
    and properly select UCF files based on requirements.
    """
    system_prompt = """
    You are a synthetic biology design assistant that specializes in genetic circuit design.
    Use the design_circuit function to create genetic circuits based on user requirements.
    """
    
    # Test 1: Simple NOT gate
    user_prompt_1 = """
    Design a NOT gate circuit in E. coli with the following specifications:
    - Input: arabinose
    - Output: GFP
    - The circuit should produce GFP when arabinose is absent
    """
    
    # Test 2: NOR gate
    user_prompt_2 = """
    Design a NOR gate circuit in E. coli with the following specifications:
    - Inputs: arabinose and IPTG
    - Output: RFP
    - The circuit should produce RFP only when both inputs are absent
    """
    
    # Run the first test
    messages_1 = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt_1}
    ]
    
    print("\n=== Testing design_circuit with NOT gate ===")
    result_1 = chat_with_tool(client, messages_1)
    print(result_1.content)
    
    # Run the second test
    messages_2 = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt_2}
    ]
    
    print("\n=== Testing design_circuit with NOR gate ===")
    result_2 = chat_with_tool(client, messages_2)
    print(result_2.content)
    
    return result_1, result_2

def test_find_gates(client):
    """Test the LLM's ability to find gates by type."""
    user_request = "Could you show me all the NOR gates in the library?"
    messages = [
        {"role": "system", "content": "You are a helpful assistant with knowledge of genetic gates and genetic circuit design."},
        {"role": "user", "content": user_request}
    ]
    
    final_msg = chat_with_tool(client, messages)
    print("=== Find Gates Result ===")
    print(final_msg.content)
    return final_msg

def test_get_gate_info(client):
    """Test the LLM's ability to get detailed information about a specific gate."""
    user_request = "Can you tell me more about the gate with ID 'P1_PhlF'?"
    messages = [
        {"role": "system", "content": "You are a helpful assistant with knowledge of genetic gates and genetic circuit design."},
        {"role": "user", "content": user_request}
    ]
    
    final_msg = chat_with_tool(client, messages)
    print("=== Gate Info Result ===")
    print(final_msg.content)
    return final_msg

def main():
    logging.basicConfig(level=logging.INFO)
    
    # Set up the client
    client = setup_client()
    
    print("\n-- Running Basic Tests --")
    test_find_gates(client)
    test_get_gate_info(client)
    
    print("\n-- Running UCF File Selection Tests --")
    test_ucf_file_selection(client)
    test_ucf_file_selection_with_inducers(client)
    test_ucf_file_selection_unsupported(client)
    
    print("\n-- Running Design Circuit Function Tests --")
    test_design_circuit_function(client)
    
    print("\n-- Running Cello Circuit Design Tests --")
    test_cello_basic_circuit(client)

if __name__ == "__main__":
    main()
