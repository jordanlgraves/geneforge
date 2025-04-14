import os
import json
import logging
from typing import Dict, List, Optional, Union, Any
from pathlib import Path

import dotenv

CELLO_UCF_ROOT = os.getenv("CELLO_UCF_ROOT")

# Import the module functions directly instead of the class
import src.library.part_library_customizer as part_library_customizer

logger = logging.getLogger("library_manager")

DEBUG_MODEL = True

class LibraryManager:
    """
    Manages the selection, loading, and customization of UCF libraries.
    Provides a unified interface for working with different library types.
    """
    
    def __init__(self):
        """
        Initialize the library manager. Scans for available libraries
        but does not load a default one initially.
        """        
        # Scan available libraries
        self.available_libraries = self._scan_libraries()
        
        # Set initial state - no library selected by default
        self.current_library_id: Optional[str] = None
        self.current_ucf_data: Optional[List[Dict]] = None
        self.current_ucf_path: Optional[str] = None
        self.current_input_path: Optional[str] = None
        self.current_output_path: Optional[str] = None

        if not self.available_libraries:
            logger.warning("No libraries found during scan.")
        else:
            logger.info(f"Library manager initialized. Found {len(self.available_libraries)} potential libraries.")
    
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
    
    def describe_available_libraries(self) -> Dict[str, Dict[str, str]]:
        """
        Describe the available libraries.
        """
        # attempt to get the headers from the UCF file
        library_metadata = dict()
        for lib_id in self.available_libraries:
            ucf_path = self.available_libraries[lib_id]["ucf"]
            with open(ucf_path, 'r') as f:
                header = [item for item in json.load(f) if item.get('collection','') == 'header'].pop()
                library_metadata[lib_id] = header
        return library_metadata

    def select_library(self, library_id: str) -> bool:
        """
        Select a library by ID and load its data.
        
        Args:
            library_id: ID of the library to select
            
        Returns:
            True if the library was successfully selected, False otherwise
        """
        if library_id not in self.available_libraries:
            logger.error(f"Library {library_id} not found in available libraries: {list(self.available_libraries.keys())}")
            # Clear current state if selection fails
            self.current_library_id = None
            self.current_ucf_data = None
            self.current_ucf_path = None
            self.current_input_data = None
            self.current_input_path = None
            self.current_output_data = None
            self.current_output_path = None
            return False
        
        # Get the library info
        library_info = self.available_libraries[library_id]
        
        # Check if the UCF file exists
        ucf_path = library_info.get("ucf")
        if not ucf_path or not os.path.exists(ucf_path):
            logger.error(f"UCF file path not found or file does not exist for library {library_id}: {ucf_path}")
            # Clear current state if essential file missing
            self.current_library_id = None
            self.current_ucf_data = None
            self.current_ucf_path = None
            self.current_input_data = None
            self.current_input_path = None
            self.current_output_data = None
            self.current_output_path = None
            return False
        
        # Store the UCF path
        self.current_ucf_path = ucf_path
        
        # Load the UCF file - store raw UCF data
        try:
            with open(self.current_ucf_path, 'r') as f:
                self.current_ucf_data = json.load(f)
            
            logger.info(f"Loaded raw UCF data from {self.current_ucf_path}")
            
            # Load the input file - store raw input data
            input_path = library_info.get("input")
            if input_path and os.path.exists(input_path):
                with open(input_path, 'r') as f:
                    self.current_input_data = json.load(f)
                    logger.info(f"Loaded raw input data from {input_path}")

            # Load the output file - store raw output data
            output_path = library_info.get("output")
            if output_path and os.path.exists(output_path):
                with open(output_path, 'r') as f:
                    self.current_output_data = json.load(f)
                    logger.info(f"Loaded raw output data from {output_path}")
                    

        except Exception as e:
            logger.error(f"Failed to load or parse UCF library '{library_id}' from {self.current_ucf_path}: {e}")
            # Clear current state on load failure
            self.current_library_id = None
            self.current_ucf_data = None
            self.current_ucf_path = None
            self.current_input_path = None
            self.current_output_path = None
            if DEBUG_MODEL:
                raise e # Reraise in debug mode
            return False
        
        # Store input and output file paths if available
        self.current_input_path = library_info.get("input")
        if self.current_input_path:
             logger.info(f"Registered input file: {self.current_input_path}")
        else:
             logger.info(f"No input file found for library {library_id}")
        
        self.current_output_path = library_info.get("output")
        if self.current_output_path:
            logger.info(f"Registered output file: {self.current_output_path}")
        else:
            logger.info(f"No output file found for library {library_id}")
        
        # Set the current library ID *after* successful loading
        self.current_library_id = library_id
        logger.info(f"Successfully selected library: {library_id}")
        
        return True
    
    def get_ucf_data(self) -> Optional[List[Dict]]:
        """
        Get the raw UCF data for the current library.
        
        Returns:
            Raw UCF data or None if no library is loaded
        """
        return self.current_ucf_data
    
    def get_input_sensor_data(self) -> Optional[List[Dict]]:
        """
        Get the raw input sensor data for the current library.
        """
        return self.current_input_data
    
    def get_output_device_data(self) -> Optional[List[Dict]]:
        """
        Get the raw output device data for the current library.
        """
        return self.current_output_data
    
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
        
        # Use the module function directly instead of calling through a class instance
        custom_ucf_path = part_library_customizer.create_custom_ucf(
            ucf_data=self.current_ucf_data,
            selected_gates=selected_gates,
            selected_parts=processed_parts,
            modified_parts=modified_parts,
            new_parts=new_parts,
            ucf_name=ucf_name,
            output_dir=output_dir
        )
        self.current_ucf_path = custom_ucf_path
        return custom_ucf_path
    
    def create_custom_input_sensors_file(self,
                                       selected_sensors: List[str] = None,
                                       modified_models: List[Dict] = None,
                                       new_sensors: List[Dict] = None,
                                       output_filename: str = None,
                                       output_dir: str = None) -> Optional[str]:
        """
        Create a custom input sensors file with selected sensors and modifications.
        
        Args:
            selected_sensors: List of sensor names to include
            modified_models: List of model objects with modified parameters
            new_sensors: List of new sensor definitions to add
            output_filename: Optional name for the output file
            output_dir: Optional directory to save the output file
            
        Returns:
            Path to the created input sensor file or None if creation failed
        """
        if not self.current_input_data:
            logger.error("No input sensor data loaded, cannot create custom input sensors file")
            return None
        
        # Process selected_sensors to ensure they exist in the input data
        if selected_sensors:
            available_sensors = [item.get("name") for item in self.current_input_data 
                                if item.get("collection") == "input_sensors"]
            
            for sensor in selected_sensors:
                if sensor not in available_sensors:
                    logger.warning(f"Sensor {sensor} not found in input sensor data")
        
        # Default output directory
        if not output_dir:
            output_dir = "outputs/custom_sensors"
        
        # Use the module function directly
        try:
            custom_input_path = part_library_customizer.create_custom_input_sensors_file(
                input_sensor_data=self.current_input_data,
                selected_sensors=selected_sensors,
                modified_models=modified_models,
                new_sensors=new_sensors,
                output_filename=output_filename,
                output_dir=output_dir
            )
            
            # Update the current input path to use the custom file
            self.current_input_path = custom_input_path
            logger.info(f"Created custom input sensors file: {custom_input_path}")
            
            # Reload the input sensor data from the new file
            with open(custom_input_path, 'r') as f:
                self.current_input_data = json.load(f)
            
            return custom_input_path
        
        except Exception as e:
            logger.error(f"Failed to create custom input sensors file: {str(e)}")
            if DEBUG_MODEL:
                raise e  # Reraise in debug mode
            return None

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