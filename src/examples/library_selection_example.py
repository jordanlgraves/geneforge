#!/usr/bin/env python3
"""
Library Selection Example

This script demonstrates different approaches to library selection for genetic circuit design:
1. Rule-based selection using pattern matching
2. LLM-based selection using AI reasoning
3. Integration with Cello for circuit design

Each approach is demonstrated with the same set of example requests for comparison.
"""

import os
import sys
import json
import logging
import argparse
from pathlib import Path
from typing import Dict, Any, List

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.library.llm_library_selector import RuleBasedLibrarySelector, LLMBasedLibrarySelector
from src.tools.cello_integration import CelloIntegration
from src.tools.functions import ToolIntegration

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("library_selection_example")

def print_section(title):
    """Print a section title with decorative formatting."""
    print("\n" + "=" * 80)
    print(f" {title} ".center(80, "="))
    print("=" * 80 + "\n")

def print_json(data):
    """Print JSON data with nice formatting."""
    print(json.dumps(data, indent=2))

def simulate_llm_reasoning(user_request: str, ucf_metadata: Dict[str, Any]) -> str:
    """
    Simulate LLM reasoning for UCF selection.
    This function is used when real LLM calls are not available or desired.
    
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

def demonstrate_rule_based_selection(library_selector: RuleBasedLibrarySelector, 
                                    requests: List[str],
                                    detailed: bool = False):
    """Demonstrate the rule-based library selection approach."""
    print_section("Rule-based Library Selection")
    
    for i, request in enumerate(requests):
        print_section(f"Example {i+1}: {request}")
        
        # Analyze the request
        if detailed:
            print("Analyzing request...")
            analysis = library_selector.analyze_user_request(request)
            print("Analysis results:")
            print_json(analysis)
            print()
        
        # Select a library
        print("Selecting library...")
        result = library_selector.select_library(request)
        print("Selection results:")
        print_json(result)
        
        # If a library was selected, get its metadata
        if result["success"] and detailed:
            library_id = result["library_id"]
            print(f"\nGetting metadata for library: {library_id}")
            metadata = library_selector.get_library_metadata(library_id)
            print("Library metadata:")
            print_json(metadata)
            
            # If there are missing features, suggest alternatives
            if "missing_features" in result and result["missing_features"]:
                print("\nWarning: The selected library is missing some requested features:")
                for feature in result["missing_features"]:
                    print(f"  - {feature}")
                
                if "alternatives" in result and result["alternatives"]:
                    print("\nAlternative libraries that might be suitable:")
                    for alt in result["alternatives"]:
                        print(f"  - {alt['library_id']}")
                        if alt["missing_features"]:
                            print(f"    Missing: {', '.join(alt['missing_features'])}")

def demonstrate_llm_based_selection(llm_selector: LLMBasedLibrarySelector, 
                                  requests: List[str]):
    """Demonstrate the LLM-based library selection approach."""
    print_section("LLM-based Library Selection")
    
    # Check if OpenAI API key is set
    if not os.environ.get("OPENAI_API_KEY"):
        print("WARNING: OPENAI_API_KEY environment variable not set.")
        print("The LLM-based selection requires an API key.")
        print("Please set the OPENAI_API_KEY environment variable and try again.\n")
        return False
    
    for i, request in enumerate(requests):
        print_section(f"Example {i+1}: {request}")
        
        # Select a library using LLM
        print("Selecting library with LLM reasoning...")
        llm_result = llm_selector.select_library(request)
        print("LLM-based selection results:")
        print_json(llm_result)
        
        if "reasoning" in llm_result:
            print("\nLLM reasoning:")
            print(llm_result["reasoning"])
    
    return True

def demonstrate_tool_based_selection(tool_integration: ToolIntegration, 
                                   requests: List[str],
                                   use_real_llm: bool = False):
    """Demonstrate the tool-based approach to library selection."""
    print_section("Tool-based Library Selection")
    
    for i, request in enumerate(requests):
        print_section(f"Example {i+1}: {request}")
        
        # Step 1: Get metadata for all available UCF libraries
        print("Getting UCF metadata...")
        ucf_metadata = tool_integration.get_ucf_metadata_func()
        print(f"Found {len(ucf_metadata['available_libraries'])} available libraries:")
        for lib_id in ucf_metadata['available_libraries']:
            print(f"  - {lib_id}")
        
        # Step 2: Generate LLM reasoning (simulated or real)
        if use_real_llm and os.environ.get("OPENAI_API_KEY"):
            # In a real implementation, this would call an LLM API
            print("\nNOTE: Using simulated LLM reasoning rather than real LLM call")
            llm_reasoning = simulate_llm_reasoning(request, ucf_metadata)
        else:
            llm_reasoning = simulate_llm_reasoning(request, ucf_metadata)
        
        print("\nLLM reasoning:")
        print(llm_reasoning)
        
        # Step 3: Use the LLM's reasoning to select a UCF
        print("\nSelecting UCF based on LLM reasoning...")
        result = tool_integration.llm_select_ucf_func(request, llm_reasoning)
        print("Selection result:")
        print_json(result)
        
        # For comparison, show the result from the original method
        print("\nFor comparison, using the rule-based method:")
        original_result = tool_integration.analyze_and_select_library_func(request)
        print_json(original_result)

def demonstrate_cello_integration(library_selector: RuleBasedLibrarySelector):
    """Demonstrate integration with Cello using the selected library."""
    print_section("Integration with Cello")
    
    # Select a library for E. coli
    result = library_selector.select_library("I want to design a NOT gate for E. coli")
    
    if result["success"]:
        library_id = result["library_id"]
        print(f"Selected library: {library_id}")
        
        # Create a Cello integration with the selected library
        print(f"Creating Cello integration with library: {library_id}")
        cello = CelloIntegration(library_id=library_id)
        
        # Show available libraries
        print("\nAvailable libraries:")
        available_libraries = cello.get_available_libraries()
        print(", ".join(available_libraries))
        
        # Create a simple Verilog module
        verilog_code = "module main(input a, output y); assign y = !a; endmodule"
        print(f"\nVerilog code: {verilog_code}")
        
        # Note: We're not actually running Cello here to avoid long computation
        print("\nTo run Cello with this library, you would use:")
        print(f"result = cello.run_cello(verilog_code='{verilog_code}')")
        print("The result would include the DNA sequence and implementation details.")

def main():
    """Run the comprehensive library selection example."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Library Selection Example")
    parser.add_argument("--llm", action="store_true", help="Use real LLM-based selection (requires OPENAI_API_KEY)")
    parser.add_argument("--detailed", action="store_true", help="Show detailed analysis and metadata")
    parser.add_argument("--method", choices=["all", "rule", "llm", "tool"], default="all", 
                        help="Which selection method to demonstrate")
    args = parser.parse_args()
    
    print_section("COMPREHENSIVE LIBRARY SELECTION EXAMPLE")
    
    # Example user requests (used for all methods)
    example_requests = [
        "I want to design a genetic circuit for E. coli that produces GFP when arabinose is present.",
        "Can you help me create a NOT gate in yeast that responds to tetracycline?",
        "I need a genetic circuit for B. subtilis with RFP output and IPTG induction.",
        "Design a genetic AND gate that uses two inputs: arabinose and IPTG, with YFP as the output."
    ]
    
    # Create selectors and tools
    rule_based_selector = RuleBasedLibrarySelector()
    llm_based_selector = LLMBasedLibrarySelector(
        model="gpt-3.5-turbo" if not args.llm else "gpt-4"
    )
    tool_integration = ToolIntegration({})  # Empty library data for example purposes
    
    # Demonstrate selected methods
    if args.method in ["all", "rule"]:
        demonstrate_rule_based_selection(rule_based_selector, example_requests, args.detailed)
    
    if args.method in ["all", "llm"]:
        llm_success = demonstrate_llm_based_selection(llm_based_selector, example_requests)
        if not llm_success:
            print("Skipping LLM-based selection due to missing API key")
    
    if args.method in ["all", "tool"]:
        demonstrate_tool_based_selection(tool_integration, example_requests, args.llm)
    
    # Demonstrate Cello integration
    demonstrate_cello_integration(rule_based_selector)
    
    print_section("CONCLUSION")
    print("This example demonstrated different approaches to library selection:")
    print("1. Rule-based selection: Fast but limited pattern matching")
    print("2. LLM-based selection: Sophisticated reasoning but requires API key")
    print("3. Tool-based selection: Flexible interface for different backends")
    print("\nThe appropriate method depends on your specific requirements.")

if __name__ == "__main__":
    main() 