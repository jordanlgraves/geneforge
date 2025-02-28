# tests/test_runner.py

import os
import sys
import json
import logging
from pathlib import Path
from openai import OpenAI
import unittest

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, project_root)

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
    
    IMPORTANT: If you encounter errors related to 'yosys: command not found' or missing files with '_yosys.json',
    please inform the user that Yosys (a required dependency for Cello's logic synthesis) is not installed
    or not in the system PATH. Suggest installation methods for different operating systems.
    """
    
    user_prompt = """
    I want to design a NOT gate circuit in E. coli that is induced by arabinose and 
    produces GFP when arabinose is absent. Please design this circuit for me.
    """
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    try:
        final_answer = chat_with_tool(client, messages)
        print("=== Cello Basic Circuit Design Result ===")
        print(final_answer.content)
        return final_answer
    except Exception as e:
        print("=== Cello Basic Circuit Design Error ===")
        print(f"Error: {str(e)}")
        if "yosys" in str(e).lower():
            print("\nThis error is likely due to the missing Yosys dependency.")
            print("Yosys is required for Cello's logic synthesis.")
        return None

def test_cello_advanced_circuit(client):
    """
    Test the LLM's ability to design a more complex circuit using Cello.
    Uses a 2-input NOR gate as an example.
    
    The system should automatically select an appropriate UCF file based on:
    1. Organism: E. coli
    2. Inputs: arabinose (AraC) and IPTG (LacI)
    3. Output: RFP
    4. Gate type: NOR
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
    
    IMPORTANT: If you encounter errors related to 'yosys: command not found' or missing files with '_yosys.json',
    please inform the user that Yosys (a required dependency for Cello's logic synthesis) is not installed
    or not in the system PATH. Suggest installation methods for different operating systems.
    """
    
    user_prompt = """
    I want to design a NOR gate circuit in E. coli that takes arabinose and IPTG as inputs
    and produces RFP only when both inputs are absent. Please design this circuit for me.
    """
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    try:
        final_answer = chat_with_tool(client, messages)
        print("=== Cello Advanced Circuit Design Result ===")
        print(final_answer.content)
        return final_answer
    except Exception as e:
        print("=== Cello Advanced Circuit Design Error ===")
        print(f"Error: {str(e)}")
        if "yosys" in str(e).lower():
            print("\nThis error is likely due to the missing Yosys dependency.")
            print("Yosys is required for Cello's logic synthesis.")
        return None

def test_cello_iterative_design(client):
    """
    Test the LLM's ability to iteratively design and refine a circuit using Cello.
    This simulates a conversation where the user asks for a circuit and then
    requests modifications to the design.
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
    
    IMPORTANT: If you encounter errors related to 'yosys: command not found' or missing files with '_yosys.json',
    please inform the user that Yosys (a required dependency for Cello's logic synthesis) is not installed
    or not in the system PATH. Suggest installation methods for different operating systems.
    """
    
    # Initial request for a simple circuit
    user_prompt_1 = """
    I want to design a NOT gate circuit in E. coli that is induced by arabinose and 
    produces GFP when arabinose is absent. Please design this circuit for me.
    """
    
    # Follow-up request to modify the circuit
    user_prompt_2 = """
    That looks good, but I'd like to modify it to use IPTG instead of arabinose as the input.
    Can you redesign the circuit with this change?
    """
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt_1}
    ]
    
    try:
        # First design iteration
        response_1 = chat_with_tool(client, messages)
        print("=== Cello Iterative Design - Initial Circuit ===")
        print(response_1.content)
        
        # Add the response and follow-up request to the conversation
        messages.append({"role": "assistant", "content": response_1.content})
        messages.append({"role": "user", "content": user_prompt_2})
        
        # Second design iteration
        response_2 = chat_with_tool(client, messages)
        print("\n=== Cello Iterative Design - Modified Circuit ===")
        print(response_2.content)
        
        return response_1, response_2
    except Exception as e:
        print("=== Cello Iterative Design Error ===")
        print(f"Error: {str(e)}")
        if "yosys" in str(e).lower():
            print("\nThis error is likely due to the missing Yosys dependency.")
            print("Yosys is required for Cello's logic synthesis.")
        return None, None

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
    
    IMPORTANT: If you encounter errors related to 'yosys: command not found' or missing files with '_yosys.json',
    please inform the user that Yosys (a required dependency for Cello's logic synthesis) is not installed
    or not in the system PATH. Suggest installation methods for different operating systems.
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
    try:
        result_1 = chat_with_tool(client, messages_1)
        print(result_1.content)
    except Exception as e:
        print(f"Error: {str(e)}")
        if "yosys" in str(e).lower():
            print("\nThis error is likely due to the missing Yosys dependency.")
            print("Yosys is required for Cello's logic synthesis.")
        result_1 = None
    
    # Run the second test
    messages_2 = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt_2}
    ]
    
    print("\n=== Testing design_circuit with NOR gate ===")
    try:
        result_2 = chat_with_tool(client, messages_2)
        print(result_2.content)
    except Exception as e:
        print(f"Error: {str(e)}")
        if "yosys" in str(e).lower():
            print("\nThis error is likely due to the missing Yosys dependency.")
            print("Yosys is required for Cello's logic synthesis.")
        result_2 = None
    
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

def check_yosys_dependency():
    """
    Check if Yosys is installed and available in the system PATH.
    
    Returns:
        bool: True if Yosys is available, False otherwise
    """
    import shutil
    yosys_available = shutil.which("yosys") is not None
    
    if not yosys_available:
        print("\n" + "=" * 80)
        print(" WARNING: Yosys Dependency Missing ".center(80, "!"))
        print("=" * 80)
        print("Yosys is required for Cello's logic synthesis but was not found in your PATH.")
        print("Cello-related tests will likely fail at the logic synthesis step.")
        print("To install Yosys:")
        print("  - macOS: brew install yosys")
        print("  - Ubuntu/Debian: sudo apt-get install yosys")
        print("  - Windows: Download from http://www.clifford.at/yosys/download.html")
        print("=" * 80 + "\n")
    
    return yosys_available

def main():
    logging.basicConfig(level=logging.INFO)
    
    # Check for Yosys dependency
    yosys_available = check_yosys_dependency()
    
    # Set up the client
    client = setup_client()
    
    print("\n-- Running Basic Tests --")
    test_find_gates(client)
    test_get_gate_info(client)
    
    print("\n-- Running UCF File Selection Tests --")
    test_ucf_file_selection(client)
    test_ucf_file_selection_with_inducers(client)
    test_ucf_file_selection_unsupported(client)
    
    # Only run Cello-related tests if Yosys is available or user wants to proceed anyway
    if yosys_available or input("\nYosys is missing. Run Cello tests anyway? (y/n): ").lower() == 'y':
        print("\n-- Running Design Circuit Function Tests --")
        test_design_circuit_function(client)
        
        print("\n-- Running Cello Circuit Design Tests --")
        test_cello_basic_circuit(client)
        test_cello_advanced_circuit(client)
        test_cello_iterative_design(client)
    else:
        print("\nSkipping Cello-related tests due to missing Yosys dependency.")

if __name__ == "__main__":
    main()
