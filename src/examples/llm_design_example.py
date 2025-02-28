#!/usr/bin/env python3
"""
LLM-based Design Example

This script demonstrates how to use the LLM-based UCF selection in the design process.
It shows the complete workflow from user request to circuit design.
"""

import os
import sys
import json
import logging
import glob
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.tools.functions import ToolIntegration
from src.design_module import DesignOrchestrator

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("llm_design_example")

def print_section(title):
    """Print a section title with decorative formatting."""
    print("\n" + "=" * 80)
    print(f" {title} ".center(80, "="))
    print("=" * 80 + "\n")

def print_json(data):
    """Print JSON data with nice formatting."""
    print(json.dumps(data, indent=2))

def main():
    """Run the LLM-based design example."""
    print_section("LLM-based Design Example")
    
    # Check available UCF files
    ucf_dir = "ext_repos/Cello-UCF/files/v2/ucf/Eco"
    available_ucf_files = glob.glob(f"{ucf_dir}/*.UCF.json")
    print(f"Available UCF files: {[os.path.basename(f) for f in available_ucf_files]}")
    
    if not available_ucf_files:
        print("Error: No UCF files found in the expected directory.")
        print(f"Please ensure UCF files exist in: {ucf_dir}")
        return
    
    # Use the first available UCF file as a fallback
    default_ucf = os.path.basename(available_ucf_files[0])
    print(f"Using default UCF file: {default_ucf}")
    
    # Create a tool integration instance with custom configuration
    tool_integration = ToolIntegration({})
    
    # Create a design orchestrator
    design_orchestrator = DesignOrchestrator(tool_integration)
    
    # Example user request
    user_request = "I want to design a NOT gate circuit for E. coli that produces GFP when arabinose is absent."
    print(f"User request: {user_request}")
    
    # Step 1: Generate Verilog code for the circuit
    print_section("Step 1: Generate Verilog Code")
    verilog_code = """
module NOT_gate (input a, output out);
    assign out = ~a;
endmodule
"""
    print(verilog_code)
    
    # Configure Cello with the correct paths
    cello_config = {
        "constraints_path": "ext_repos/Cello-UCF/files/v2/ucf/Eco",  # Path to UCF files
        "ucf_name": default_ucf,  # Default UCF file
        "output_path": "outputs/cello_outputs"  # Output directory
    }
    
    # Step 2: Design the circuit using LLM-based UCF selection
    print_section("Step 2: Design Circuit with LLM-based UCF Selection")
    print("Calling the LLM to select the appropriate UCF library...")
    
    design_result = design_orchestrator.design_circuit(
        verilog_code=verilog_code,
        user_request=user_request,
        use_llm=True,  # This will use the LLM to select the UCF library
        cello_config=cello_config  # Pass the configuration
    )
    
    print("Design result:")
    print_json(design_result)
    
    # For comparison, design the circuit using traditional UCF selection
    print_section("For Comparison: Design Circuit with Traditional UCF Selection")
    traditional_result = design_orchestrator.design_circuit(
        verilog_code=verilog_code,
        organism="E. coli",
        inducers=["arabinose"],
        outputs=["GFP"],
        gate_types=["NOT"],
        use_llm=False,
        cello_config=cello_config  # Pass the same configuration
    )
    print("Traditional design result:")
    print_json(traditional_result)
    
    # Compare the results
    print_section("Comparison of Results")
    llm_ucf = design_result.get("ucf_file", "Unknown")
    traditional_ucf = traditional_result.get("ucf_file", "Unknown")
    
    print(f"LLM-selected UCF: {llm_ucf}")
    print(f"Traditional UCF: {traditional_ucf}")
    
    if llm_ucf == traditional_ucf:
        print("Both methods selected the same UCF library.")
    else:
        print("The methods selected different UCF libraries.")
        print("This demonstrates how the LLM can make more nuanced selections based on the full context of the request.")

if __name__ == "__main__":
    main() 