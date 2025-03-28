import os
import json
import logging
from typing import Dict, List, Optional, Union, Any
from pathlib import Path

import dotenv

CELLO_UCF_ROOT = os.getenv("CELLO_UCF_ROOT")

from src.library.ucf_customizer import CelloUCFCustomizer

logger = logging.getLogger("library_manager")

DEBUG_MODEL = True

class LibraryManager:
    """
    Manages the selection, loading, and customization of UCF libraries.
    Provides a unified interface for working with different library types.
    """
    
    def __init__(self, default_library: str = "Eco1C1G1T1"):
        """
        Initialize the library manager with default settings.
        
        Args:
            default_library: Default library identifier (e.g., "Eco1C1G1T1")
        """
        # Initialize the UCF customizer
        self.ucf_customizer = CelloUCFCustomizer()
        
        # Scan available libraries
        self.available_libraries = self._scan_libraries()
        
        # Set initial state
        self.default_library = default_library
        self.current_library_id = None
        self.current_ucf_data = None  # Store raw UCF data
        self.current_ucf_path = None
        self.current_input_path = None
        self.current_output_path = None

        # Try to load the default library
        if self.available_libraries:
            # If default library not available, use the first available one
            if default_library not in self.available_libraries:
                self.default_library = next(iter(self.available_libraries))
                logger.info(f"Default library '{default_library}' not found. Using '{self.default_library}' instead.")
            
            self.select_library(self.default_library)
        else:
            logger.warning("No libraries found. Library manager initialized without active library.")
    
    def _scan_libraries(self) -> Dict[str, Dict[str, str]]:
        """
        Scan all library directories to find available UCF, input, and output files.
        
        Returns:
            Dict mapping library IDs to their file paths
        """
        libraries = {}
        
        library_root = CELLO_UCF_ROOT
        if not library_root:
            # Get the absolute project root path for reliable file access
            project_root = self._get_project_root()
            library_root = os.path.join(project_root, "ext_repos/Cello-UCF/files/v2")
        else:
            library_root = os.path.join(library_root, "files/v2")

        for file_type in ["input", "output", "ucf"]:
            # Convert to absolute path
            path_value = os.path.join(library_root, file_type)
            
            if not os.path.exists(path_value):
                logger.warning(f"Library path {path_value} does not exist")
                continue
            
            # Process organism directories
            for organism_dir in os.listdir(path_value):
                organism_path = os.path.join(path_value, organism_dir)
                if os.path.isdir(organism_path):
                    # Process files in organism directory
                    for filename in os.listdir(organism_path):
                        # Determine file type and extract library ID
                        if file_type == "ucf" and filename.endswith(".UCF.json"):
                            library_id = filename.replace(".UCF.json", "")
                            if library_id not in libraries:
                                libraries[library_id] = {}
                            libraries[library_id]["ucf"] = os.path.join(organism_path, filename)
                            
                        elif file_type == "input" and filename.endswith(".input.json"):
                            library_id = filename.replace(".input.json", "")
                            if library_id not in libraries:
                                libraries[library_id] = {}
                            libraries[library_id]["input"] = os.path.join(organism_path, filename)
                            
                        elif file_type == "output" and filename.endswith(".output.json"):
                            library_id = filename.replace(".output.json", "")
                            if library_id not in libraries:
                                libraries[library_id] = {}
                            libraries[library_id]["output"] = os.path.join(organism_path, filename)
        
        if not libraries:
            logger.warning("No libraries found in any of the configured paths")
        else:
            logger.info(f"Found {len(libraries)} libraries")
            for lib_id in libraries:
                components = []
                if "ucf" in libraries[lib_id]:
                    components.append("UCF")
                if "input" in libraries[lib_id]:
                    components.append("input")
                if "output" in libraries[lib_id]:
                    components.append("output")
                logger.info(f"Library {lib_id}: {', '.join(components)}")
        
        return libraries
    
    def _get_project_root(self) -> str:
        """
        Get the absolute path to the project root directory.
        
        Returns:
            Absolute path to the project root
        """
        # Start with the current file's directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Go up to the src directory
        parent_dir = os.path.dirname(current_dir)
        # Go up one more level to the project root
        project_root = os.path.dirname(parent_dir)
        return project_root
    
    def get_available_libraries(self) -> Dict[str, Dict[str, str]]:
        """
        Get the available libraries.
        """
        return self.available_libraries
    
    def select_library(self, library_id: str) -> bool:
        """
        Select a library by ID.
        
        Args:
            library_id: ID of the library to select
            
        Returns:
            True if the library was successfully selected, False otherwise
        """
        if library_id not in self.available_libraries.keys():
            logger.error(f"Library {library_id} not found")
            return False
        
        # Get the library info
        library_info = self.available_libraries[library_id]
        
        # Check if the UCF file exists
        if "ucf" not in library_info:
            logger.error(f"Library {library_id} does not have a UCF file")
            return False
        
        # Store the UCF path
        self.current_ucf_path = library_info["ucf"]
        
        # Load the UCF file - store raw UCF data
        try:
            with open(self.current_ucf_path, 'r') as f:
                self.current_ucf_data = json.load(f)
            
            logger.info(f"Loaded raw UCF data from {self.current_ucf_path}")
            
        except Exception as e:
            if DEBUG_MODEL:
                # reraise so we can see the error in the debugger
                raise e
            
            logger.error(f"Failed to load UCF library: {e}")
            return False
        
        # Store input and output file paths if available
        if "input" in library_info:
            self.current_input_path = library_info["input"]
            logger.info(f"Registered input file: {self.current_input_path}")
            
        if "output" in library_info:
            self.current_output_path = library_info["output"]
            logger.info(f"Registered output file: {self.current_output_path}")
        
        # Set the current library ID
        self.current_library_id = library_id
        logger.info(f"Selected library: {library_id}")
        
        return True
    
    def get_library_data(self) -> Optional[Dict[str, Any]]:
        """
        Get the current library data in a structured format.
        This method converts raw UCF data to a structured format for easier querying.
        
        Returns:
            Structured library data or None if no library is loaded
        """
        if not self.current_ucf_data:
            return None
            
        # Convert raw UCF data to a structured format on-demand
        structured_data = {
            "parts": [],
            "gates": []
        }
        
        # Process parts and gates
        for item in self.current_ucf_data:
            if "collection" not in item:
                continue
                
            collection = item["collection"]
            
            if collection == "parts":
                part_data = {
                    "id": item.get("name", ""),
                    "name": item.get("name", ""),
                    "type": item.get("type", ""),
                    "sequence": item.get("dnasequence", ""),
                    "raw_data": item
                }
                
                # Process parameters
                for param in item.get("parameters", []):
                    param_name = param.get("name", "").lower()
                    param_value = param.get("value", 0)
                    part_data[param_name] = param_value
                
                structured_data["parts"].append(part_data)
                
            elif collection == "gates":
                gate_data = {
                    "id": item.get("name", ""),
                    "name": item.get("name", ""),
                    "type": item.get("type", ""),
                    "raw_data": item
                }
                structured_data["gates"].append(gate_data)
            
            # Add other collections as needed
        
        return structured_data
    
    def get_ucf_data(self) -> Optional[List[Dict]]:
        """
        Get the raw UCF data for the current library.
        
        Returns:
            Raw UCF data or None if no library is loaded
        """
        return self.current_ucf_data
    
    def get_input_file_path(self) -> Optional[str]:
        """
        Get the path to the current input file.
        
        Returns:
            Path to the input file or None if no input file is available
        """
        return self.current_input_path
    
    def get_output_file_path(self) -> Optional[str]:
        """
        Get the path to the current output file.
        
        Returns:
            Path to the output file or None if no output file is available
        """
        return self.current_output_path
    
    def create_custom_ucf(self, 
                         selected_gates: List[str] = None,
                         selected_parts: List = None,
                         modified_parts: List = None,
                         new_parts: List[Dict] = None,
                         ucf_name: str = None,
                         output_dir: str = None) -> Optional[str]:
        """
        Create a custom UCF file with selected parts and modifications.
        
        Args:
            selected_gates: List of gate IDs to include
            selected_parts: List of part objects or IDs to include
            modified_parts: Dict of part_id -> modified properties
            new_parts: List of new part definitions to add
            ucf_name: Optional name for the UCF file
            output_dir: Optional directory to save the UCF file
            
        Returns:
            Path to the created UCF file or None if creation failed
        """
        if not self.current_ucf_data:
            logger.error("No UCF data loaded, cannot create custom UCF")
            return None
        
        # Process selected_parts to ensure we have a list of part dictionaries
        processed_parts = []
        if selected_parts:
            for part in selected_parts:
                if isinstance(part, dict) and ("id" in part or "name" in part):
                    # If it's already a part object with id/name, use it directly
                    processed_parts.append(part)
                else:
                    # Otherwise, try to find the part in the raw UCF data
                    part_name = part if isinstance(part, str) else part.get("id", part.get("name", ""))
                    found = False
                    
                    for item in self.current_ucf_data:
                        if item.get("collection") == "parts" and item.get("name") == part_name:
                            processed_parts.append(item)
                            found = True
                            break
                    
                    if not found:
                        logger.warning(f"Part {part_name} not found in UCF")
        
        # Default output directory
        if not output_dir:
            output_dir = "outputs/custom_ucf"
        
        # Create the custom UCF using our raw UCF data
        return self.ucf_customizer.create_custom_ucf(
            ucf_data=self.current_ucf_data,
            selected_gates=selected_gates,
            selected_parts=processed_parts,
            modified_parts=modified_parts,
            new_parts=new_parts,
            ucf_name=ucf_name,
            output_dir=output_dir
        )

    
    def get_current_library_info(self) -> Dict[str, Any]:
        """
        Get information about the currently selected library.
        
        Returns:
            Dictionary with library information
        """
        info = {
            "library_id": self.current_library_id,
            "ucf_path": self.current_ucf_path,
            "input_path": self.current_input_path,
            "output_path": self.current_output_path,
            "has_ucf_data": self.current_ucf_data is not None
        }
        
        # Add some statistics about the UCF if data is available
        if self.current_ucf_data:
            # Count parts and gates in the raw UCF
            parts_count = sum(1 for item in self.current_ucf_data if item.get("collection") == "parts")
            gates_count = sum(1 for item in self.current_ucf_data if item.get("collection") == "gates")
            
            info["num_parts"] = parts_count
            info["num_gates"] = gates_count
        
        return info 