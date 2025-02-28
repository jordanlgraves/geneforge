#!/usr/bin/env python3
"""
Library Selection Example

This script demonstrates how to use the RuleBasedLibrarySelector to analyze user requests
and select appropriate libraries for genetic circuit design.
"""

import os
import sys
import json
import logging
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.library.llm_library_selector import RuleBasedLibrarySelector
from src.tools.cello_integration import CelloIntegration

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

def main():
    """Run the library selection example."""
    print_section("Library Selection Example")
    
    # Create a library selector
    library_selector = RuleBasedLibrarySelector()
    
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
        
        # Analyze the request
        print("Analyzing request...")
        analysis = library_selector.analyze_user_request(request)
        print("Analysis results:")
        print_json(analysis)
        
        # Select a library
        print("\nSelecting library...")
        result = library_selector.select_library(request)
        print("Selection results:")
        print_json(result)
        
        # If a library was selected, get its metadata
        if result["success"]:
            library_id = result["library_id"]
            print(f"\nGetting metadata for library: {library_id}")
            metadata = library_selector.get_library_metadata(library_id)
            print("Library metadata:")
            print_json(metadata)
            
            # Show how to use the selected library with Cello
            print("\nExample of using the selected library with Cello:")
            print(f"cello = CelloIntegration(library_id='{library_id}')")
            print("result = cello.run_cello(verilog_code='module main(input a, output y); assign y = !a; endmodule')")
            
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
        else:
            print("\nFailed to select a library.")
            if "message" in result:
                print(f"Reason: {result['message']}")
    
    # Demonstrate actual integration with Cello (if available)
    try:
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
    except Exception as e:
        print(f"Error demonstrating Cello integration: {e}")

if __name__ == "__main__":
    main() 