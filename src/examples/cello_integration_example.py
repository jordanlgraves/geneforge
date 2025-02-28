#!/usr/bin/env python3
"""
Example script demonstrating the updated CelloIntegration class and its ability to handle
UCF, input, and output files from the library manager.
"""

import os
import sys
import logging
import json
import shutil
from pathlib import Path

# Ensure the project root is in the Python path
# Dynamically determine the project root based on the script location
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent
sys.path.insert(0, str(project_root))

# Make sure the current working directory is the project root
# This is critical as Cello expects certain paths relative to the project root
os.chdir(project_root)

# Now we can safely import from the project
from src.tools.cello_integration import CelloIntegration
from src.library.library_manager import LibraryManager


def print_section(title):
    """Print a section title with decorative borders."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_json(data):
    """Print JSON data in a formatted way."""
    print(json.dumps(data, indent=2))


def main():
    """Main function to demonstrate CelloIntegration with LibraryManager."""
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    print_section("CELLO INTEGRATION EXAMPLE")
    
    # Check if Cello directories exist
    cello_core_path = os.path.join(project_root, "ext_repos", "Cello-v2-1-Core")
    if not os.path.exists(cello_core_path):
        print(f"WARNING: Cello core directory not found at {cello_core_path}")
        print("Some functionality may be limited. Full Cello integration requires proper setup.")
    
    # First demonstrate the LibraryManager capabilities
    print_section("LIBRARY MANAGER CAPABILITIES")
    manager = LibraryManager()
    
    # Show available libraries
    libraries = manager.get_available_libraries()
    print(f"Available libraries ({len(libraries)}):")
    for lib_id in sorted(libraries):
        print(f"  - {lib_id}")
    
    # Try loading a specific E. coli library
    print_section("LOADING LIBRARY DATA")
    eco_lib = next((lib for lib in libraries if lib.startswith("Eco")), None)
    
    if eco_lib:
        print(f"Loading library: {eco_lib}")
        manager.select_library(eco_lib)
        lib_info = manager.get_current_library_info()
        print_json(lib_info)
    
    # Try initializing CelloIntegration
    print_section("INITIALIZING CELLO INTEGRATION")
    try:
        print("Attempting to initialize CelloIntegration...")
        integration = CelloIntegration(library_id=eco_lib if eco_lib else None)
        
        # Show available libraries through CelloIntegration
        print("\nAvailable libraries through CelloIntegration:")
        cello_libraries = integration.get_available_libraries()
        for lib_id in sorted(cello_libraries):
            print(f"  - {lib_id}")
        
        # Try selecting different libraries to verify path handling
        test_libraries = ["Eco1C1G1T1", "Eco1C2G2T2", "SC1C1G1T1", "Bth1C1G1T1"]
        for lib_id in test_libraries:
            print_section(f"TESTING LIBRARY: {lib_id}")
            success = integration.select_library(lib_id)
            
            if success:
                print(f"Successfully selected library: {lib_id}")
                
                # Get current library info through the library manager
                lib_info = integration.library_manager.get_current_library_info()
                print("\nLibrary information:")
                print(f"UCF Path: {lib_info.get('ucf_path', 'None')}")
                print(f"Input Path: {lib_info.get('input_path', 'None')}")
                print(f"Output Path: {lib_info.get('output_path', 'None')}")
                
                # Show Cello arguments that would be used
                print("\nCello arguments updated:")
                for key, value in integration.cello_args.items():
                    if key in ["input_ucf", "input_file", "output_file"]:
                        print(f"  {key}: {value}")
                
                # Verify the files exist in the appropriate Cello directory
                cello_constraints_dir = os.path.join(project_root, "ext_repos", "Cello-v2-1-Core", "input", "constraints")
                if os.path.exists(cello_constraints_dir):
                    print("\nFiles in Cello constraints directory:")
                    constraints_files = os.listdir(cello_constraints_dir)
                    for cf in constraints_files:
                        if lib_id in cf:
                            print(f"  - {cf}")
            else:
                print(f"Failed to select library: {lib_id}")
                
        # Show a simple Verilog example
        print_section("VERILOG EXAMPLE")
        print("Example Verilog code for a NOT gate:")
        verilog_code = "module NOT(input a, output y); assign y = !a; endmodule"
        print(verilog_code)
        
        print("\nTo run this circuit in Cello, you would use:")
        print("result = integration.run_cello(verilog_code)")
        print("Note: This example does not actually run Cello to avoid long computation.")
            
    except Exception as e:
        print(f"Error initializing CelloIntegration: {e}")
        print(f"This is expected if Cello is not properly set up.")
        print(f"You can still use the LibraryManager functionality.")


if __name__ == "__main__":
    main() 