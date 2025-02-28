#!/usr/bin/env python3
"""
LLM-based UCF Selection Example

This script demonstrates how to use an LLM to select appropriate UCF files
based on both user requests and UCF metadata.
"""

import os
import sys
import json
import logging
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.tools.functions import ToolIntegration

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("llm_ucf_selection_example")

def print_section(title):
    """Print a section title with decorative formatting."""
    print("\n" + "=" * 80)
    print(f" {title} ".center(80, "="))
    print("=" * 80 + "\n")

def print_json(data):
    """Print JSON data with nice formatting."""
    print(json.dumps(data, indent=2))

def main():
    """Run the LLM-based UCF selection example."""
    print_section("LLM-based UCF Selection Example")
    
    # Create a tool integration instance
    tool_integration = ToolIntegration({})
    
    # Example user requests
    example_requests = [
        "I want to design a genetic circuit for E. coli that produces GFP when arabinose is present.",
        "Can you help me create a NOT gate in yeast that responds to tetracycline?",
        "I need a genetic circuit for B. subtilis with RFP output and IPTG induction.",
        "Design a genetic AND gate that uses two inputs: arabinose and IPTG, with YFP as the output."
    ]
    
    # Process each example request
    for i, request in enumerate(example_requests):
        print_section(f"Example {i+1}: {request}")
        
        # Step 1: Get metadata for all available UCF libraries
        print("Getting UCF metadata...")
        ucf_metadata = tool_integration.get_ucf_metadata_func()
        print(f"Found {len(ucf_metadata['available_libraries'])} available libraries:")
        for lib_id in ucf_metadata['available_libraries']:
            print(f"  - {lib_id}")
        
        # Step 2: In a real system, this metadata would be passed to an LLM along with the user request
        # The LLM would analyze both and provide reasoning for selecting a particular library
        # Here, we'll simulate the LLM's reasoning
        
        # Simulate LLM reasoning based on the request
        llm_reasoning = simulate_llm_reasoning(request, ucf_metadata)
        print("\nLLM reasoning:")
        print(llm_reasoning)
        
        # Step 3: Use the LLM's reasoning to select a UCF
        print("\nSelecting UCF based on LLM reasoning...")
        result = tool_integration.llm_select_ucf_func(request, llm_reasoning)
        print("Selection result:")
        print_json(result)
        
        # For comparison, show the result from the original method
        print("\nFor comparison, using the original method:")
        original_result = tool_integration.analyze_and_select_library_func(request)
        print_json(original_result)

def simulate_llm_reasoning(user_request, ucf_metadata):
    """
    Simulate LLM reasoning for UCF selection.
    In a real system, this would be replaced by an actual LLM call.
    
    Args:
        user_request: The user's request
        ucf_metadata: Metadata for all available UCF libraries
        
    Returns:
        A string containing the simulated LLM reasoning
    """
    # Extract key terms from the request
    request_lower = user_request.lower()
    
    # Check for organism mentions
    organism = None
    if "e. coli" in request_lower or "ecoli" in request_lower or "escherichia" in request_lower:
        organism = "E. coli"
    elif "yeast" in request_lower or "s. cerevisiae" in request_lower:
        organism = "yeast"
    elif "b. subtilis" in request_lower or "bacillus" in request_lower:
        organism = "B. subtilis"
    
    # Check for reporters
    reporter = None
    if "gfp" in request_lower or "green" in request_lower:
        reporter = "GFP"
    elif "rfp" in request_lower or "red" in request_lower:
        reporter = "RFP"
    elif "yfp" in request_lower or "yellow" in request_lower:
        reporter = "YFP"
    
    # Check for inducers
    inducer = None
    if "arabinose" in request_lower:
        inducer = "arabinose"
    elif "iptg" in request_lower:
        inducer = "IPTG"
    elif "tetracycline" in request_lower or "atc" in request_lower:
        inducer = "tetracycline"
    
    # Check for gate types
    gate_type = None
    if "not gate" in request_lower or "inverter" in request_lower:
        gate_type = "NOT"
    elif "and gate" in request_lower:
        gate_type = "AND"
    elif "or gate" in request_lower:
        gate_type = "OR"
    
    # Find matching libraries based on organism
    matching_libraries = []
    for lib_id, metadata in ucf_metadata["libraries_metadata"].items():
        lib_organism = metadata.get("organism", "").lower()
        
        if organism and organism.lower() in lib_organism:
            matching_libraries.append(lib_id)
    
    # If no matching libraries, use all available
    if not matching_libraries:
        matching_libraries = ucf_metadata["available_libraries"]
    
    # Select the first library as a simple example
    # In a real LLM, this would involve more sophisticated reasoning
    selected_library = matching_libraries[0] if matching_libraries else None
    
    # Generate reasoning
    reasoning = f"Based on the user request, I need to select a UCF library that supports:\n"
    
    if organism:
        reasoning += f"- Organism: {organism}\n"
    else:
        reasoning += "- No specific organism mentioned, will consider all available\n"
    
    if reporter:
        reasoning += f"- Reporter: {reporter}\n"
    
    if inducer:
        reasoning += f"- Inducer: {inducer}\n"
    
    if gate_type:
        reasoning += f"- Gate type: {gate_type}\n"
    
    reasoning += f"\nAfter analyzing the available libraries, I recommend using {selected_library} because:\n"
    reasoning += f"1. It supports the required organism\n"
    reasoning += f"2. It has the necessary parts for implementing the requested circuit\n"
    
    if selected_library:
        # Add some details about the selected library
        metadata = ucf_metadata["libraries_metadata"].get(selected_library, {})
        reasoning += f"\nLibrary {selected_library} has {metadata.get('part_count', 0)} parts and {metadata.get('gate_count', 0)} gates."
        
        # Mention any potential issues
        if reporter and not metadata.get("has_reporters", {}).get(reporter.lower(), False):
            reasoning += f"\nNote: This library may not have direct support for {reporter}, but we can work around this limitation."
    
    return reasoning

if __name__ == "__main__":
    main() 