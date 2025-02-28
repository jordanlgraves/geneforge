#!/usr/bin/env python3
"""
LLM-based Library Selection Example

This script demonstrates how to use the LLMBasedLibrarySelector compared to the RuleBasedLibrarySelector.
"""

import os
import sys
import json
import logging
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.library.llm_library_selector import LLMBasedLibrarySelector, RuleBasedLibrarySelector
from src.tools.cello_integration import CelloIntegration

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("llm_library_selection_example")

def print_section(title):
    """Print a section title with decorative formatting."""
    print("\n" + "=" * 80)
    print(f" {title} ".center(80, "="))
    print("=" * 80 + "\n")

def print_json(data):
    """Print JSON data with nice formatting."""
    print(json.dumps(data, indent=2))

def main():
    """Run the LLM-based library selection example."""
    print_section("LLM-based Library Selection Example")
    
    # Check if OpenAI API key is set
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    if not openai_api_key:
        print("WARNING: OPENAI_API_KEY environment variable not set.")
        print("The LLM-based selection will not work without an API key.")
        print("Please set the OPENAI_API_KEY environment variable and try again.\n")
        
        # If no API key, still show how the rule-based selector works
        print("Continuing with rule-based selection only...\n")
    
    # Create both library selectors
    rule_based_selector = RuleBasedLibrarySelector()
    llm_based_selector = LLMBasedLibrarySelector(model="gpt-3.5-turbo")  # Use cheaper model for the example
    
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
        
        # Rule-based selection
        print("Rule-based Library Selection:")
        rule_result = rule_based_selector.select_library(request)
        print_json(rule_result)
        
        # LLM-based selection (if API key is available)
        if openai_api_key:
            print("\nLLM-based Library Selection:")
            llm_result = llm_based_selector.select_library(request)
            print_json(llm_result)
            
            # Compare the results
            if "library_id" in rule_result and "library_id" in llm_result:
                if rule_result["library_id"] == llm_result["library_id"]:
                    print("\nBoth methods selected the same library!")
                else:
                    print("\nThe methods selected different libraries:")
                    print(f"Rule-based: {rule_result['library_id']}")
                    print(f"LLM-based: {llm_result['library_id']}")
                    print("\nLLM reasoning:")
                    print(llm_result["reasoning"])
    
    # Demonstrate actual integration with Cello (if available)
    try:
        print_section("Integration with Cello")
        
        # Select a library for E. coli
        result = rule_based_selector.select_library("I want to design a NOT gate for E. coli")
        
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
            
            # Run Cello with the selected library
            print("\nRunning Cello with the selected library...")
            result = cello.run_cello(verilog_code=verilog_code)
            
            if result["success"]:
                print("\nCello run successful!")
                print(f"Output path: {result['results']['output_path']}")
                
                # List generated files
                output_path = result['results']['output_path']
                if os.path.exists(output_path):
                    print("\nGenerated files:")
                    for file in os.listdir(output_path):
                        print(f"  - {file}")
                else:
                    print(f"\nOutput directory not found: {output_path}")
            else:
                print("\nCello run failed!")
                print(f"Error: {result.get('error', 'Unknown error')}")
                
                # Print a portion of the log for debugging
                log_lines = result.get('log', '').split('\n')
                if log_lines:
                    print("\nLog excerpt (last 10 lines):")
                    for line in log_lines[-10:]:
                        print(f"  {line}")
    except Exception as e:
        print(f"Error demonstrating Cello integration: {e}")
        
        # Check if the error is related to Yosys
        if "yosys" in str(e).lower() or "command not found" in str(e).lower():
            print("\nThis error is likely due to the missing Yosys dependency.")
            print("Yosys is required for Cello's logic synthesis.")
            print("Installation instructions:")
            print("  - macOS: brew install yosys")
            print("  - Ubuntu/Debian: sudo apt-get install yosys")
            print("  - Windows: Follow instructions at https://github.com/YosysHQ/yosys")

if __name__ == "__main__":
    main() 