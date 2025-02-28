"""
Cello Setup Module

This module sets up the Python path to include the Cello-v2-1-Core directory,
allowing imports from the core_algorithm module to work correctly.
"""

import os
import sys
from pathlib import Path

def setup_cello_path():
    """
    Add the Cello-v2-1-Core directory to the Python path.
    This allows imports from the core_algorithm module to work correctly.
    
    Returns:
        bool: True if the path was added successfully, False otherwise
    """
    # Get the current working directory
    cwd = os.getcwd()
    
    # Define the path to the Cello-v2-1-Core directory
    cello_core_path = os.path.join(cwd, "ext_repos", "Cello-v2-1-Core")
    
    # Check if the directory exists
    if not os.path.exists(cello_core_path):
        print(f"Error: Cello-v2-1-Core directory not found at {cello_core_path}")
        return False
    
    # Check if the core_algorithm module exists
    core_algorithm_path = os.path.join(cello_core_path, "core_algorithm")
    if not os.path.exists(core_algorithm_path):
        print(f"Error: core_algorithm directory not found at {core_algorithm_path}")
        return False
    
    # Check if the celloAlgo.py file exists
    cello_algo_path = os.path.join(core_algorithm_path, "celloAlgo.py")
    if not os.path.exists(cello_algo_path):
        print(f"Error: celloAlgo.py not found at {cello_algo_path}")
        return False
    
    # Add the Cello-v2-1-Core directory to the Python path
    if cello_core_path not in sys.path:
        sys.path.insert(0, cello_core_path)
        print(f"Added {cello_core_path} to Python path")
    
    return True

# Run the setup function when this module is imported
is_setup_successful = setup_cello_path() 