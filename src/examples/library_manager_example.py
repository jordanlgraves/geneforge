#!/usr/bin/env python3
"""
Example script to demonstrate the usage of the updated LibraryManager
with the Cello-UCF files in ext_repos/Cello-UCF/files/v2.
"""

import os
import sys
import logging
import json

# Add the project root to the Python path to allow imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, project_root)

from src.library.library_manager import LibraryManager

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("library_manager_example")

def print_section(title):
    """Print a section title with separator lines."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def print_json(data):
    """Print JSON data in a formatted way."""
    print(json.dumps(data, indent=2))

def main():
    print_section("LIBRARY MANAGER EXAMPLE")
    
    # Initialize the library manager with the default library
    manager = LibraryManager()
    
    # Display available libraries
    print_section("Available Libraries")
    libraries = manager.get_available_libraries()
    print(f"Found {len(libraries)} libraries:")
    for lib in sorted(libraries):
        print(f"  - {lib}")
    
    # Get info about the current (default) library
    print_section("Current Library Info")
    info = manager.get_current_library_info()
    print_json(info)
    
    # Try loading each E. coli library and show its info
    eco_libraries = [lib for lib in libraries if lib.startswith("Eco")]
    for lib in eco_libraries:
        print_section(f"Loading Library: {lib}")
        if manager.select_library(lib):
            info = manager.get_current_library_info()
            print_json(info)
            
            # Print file paths if available
            if info["ucf_path"]:
                print(f"\nUCF File: {info['ucf_path']}")
            if info["input_path"]:
                print(f"Input File: {info['input_path']}")
            if info["output_path"]:
                print(f"Output File: {info['output_path']}")
            
            # Print some statistics about the library
            if info["has_library_data"]:
                lib_data = manager.get_library_data()
                num_parts = len(lib_data.get("parts", []))
                num_gates = len(lib_data.get("gates", []))
                print(f"\nLibrary contains {num_parts} parts and {num_gates} gates")
        else:
            print(f"Failed to load library {lib}")
    
    # Demonstrate selecting a library by organism name
    print_section("Selecting Library by Organism")
    for organism in ["ecoli", "yeast", "bacillus"]:
        print(f"\nTrying to select organism: {organism}")
        success = manager.select_library(organism)
        if success:
            print(f"Successfully selected library: {manager.current_library_id}")
            print(f"UCF path: {manager.current_library_path}")
        else:
            print(f"Failed to select a library for organism: {organism}")

if __name__ == "__main__":
    main() 