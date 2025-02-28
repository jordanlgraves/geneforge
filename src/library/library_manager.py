import os
import json
import logging
from typing import Dict, List, Optional, Union, Any
from pathlib import Path

from src.library.ucf_retrieval import load_ecoli_library
from src.library.ucf_customizer import UCFCustomizer

logger = logging.getLogger("library_manager")

class LibraryManager:
    """
    Manages the selection, loading, and customization of UCF libraries.
    Provides a unified interface for working with different library types.
    """
    
    # Define standard library locations
    LIBRARY_PATHS = {
        "ext_ucf": "ext_repos/Cello-UCF/files/v2/ucf",
        "ext_input": "ext_repos/Cello-UCF/files/v2/input",
        "ext_output": "ext_repos/Cello-UCF/files/v2/output",
    }
    
    # Define organism prefixes for easier selection
    ORGANISM_PREFIXES = {
        "ecoli": "Eco",
        "e_coli": "Eco",
        "e.coli": "Eco",
        "eco": "Eco",
        "sc": "SC",
        "yeast": "SC",
        "s.cerevisiae": "SC",
        "bth": "Bth",
        "b.subtilis": "Bth",
        "bacillus": "Bth"
    }
    
    def __init__(self, default_library: str = "Eco1C1G1T1"):
        """
        Initialize the library manager with default settings.
        
        Args:
            default_library: Default library identifier (e.g., "Eco1C1G1T1")
        """
        self.default_library = default_library
        self.available_libraries = self._scan_libraries()
        self.current_library_id = default_library
        self.current_library_path = None
        self.current_input_path = None
        self.current_output_path = None
        self.current_parsed_path = None
        self.current_library_data = None
        self.current_customizer = None
        
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
        
        # Get the absolute project root path for reliable file access
        project_root = self._get_project_root()
        
        # First, prioritize scanning the ext_repos/Cello-UCF structure
        for path_key in ["ext_ucf", "ext_input", "ext_output"]:
            # Convert to absolute path
            rel_path = self.LIBRARY_PATHS[path_key]
            path_value = os.path.join(project_root, rel_path)
            
            if not os.path.exists(path_value):
                logger.warning(f"Library path {rel_path} does not exist")
                continue
            
            # Process organism directories
            for organism_dir in os.listdir(path_value):
                organism_path = os.path.join(path_value, organism_dir)
                if os.path.isdir(organism_path):
                    # Process files in organism directory
                    for filename in os.listdir(organism_path):
                        # Determine file type and extract library ID
                        if path_key == "ext_ucf" and filename.endswith(".UCF.json"):
                            library_id = filename.replace(".UCF.json", "")
                            if library_id not in libraries:
                                libraries[library_id] = {}
                            libraries[library_id]["ucf"] = os.path.join(organism_path, filename)
                            
                        elif path_key == "ext_input" and filename.endswith(".input.json"):
                            library_id = filename.replace(".input.json", "")
                            if library_id not in libraries:
                                libraries[library_id] = {}
                            libraries[library_id]["input"] = os.path.join(organism_path, filename)
                            
                        elif path_key == "ext_output" and filename.endswith(".output.json"):
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
        
        # Navigate up to the project root (src/library -> src -> project_root)
        project_root = os.path.abspath(os.path.join(current_dir, "../.."))
        
        return project_root
    
    def _scan_directory_for_libraries(self, directory: str, libraries: Dict[str, Dict[str, str]]):
        """
        Scan a directory for UCF library files.
        
        Args:
            directory: Directory to scan
            libraries: Dictionary to update with found libraries
        """
        for filename in os.listdir(directory):
            if filename.endswith(".UCF.json"):
                # Extract library ID (e.g., "Eco1C1G1T1" from "Eco1C1G1T1.UCF.json")
                library_id = filename.replace(".UCF.json", "")
                full_path = os.path.join(directory, filename)
                
                if library_id not in libraries:
                    libraries[library_id] = {}
                    
                libraries[library_id]["ucf"] = full_path
    
    def get_available_libraries(self) -> List[str]:
        """
        Get a list of all available library IDs.
        
        Returns:
            List of library IDs
        """
        return list(self.available_libraries.keys())
    
    def select_library(self, library_identifier: str) -> bool:
        """
        Select a library by its identifier or description.
        
        Args:
            library_identifier: Library ID or description (e.g., "Eco1C1G1T1" or "ecoli")
            
        Returns:
            True if library was successfully selected, False otherwise
        """
        # Check if this is a direct library ID
        if library_identifier in self.available_libraries:
            return self._load_library(library_identifier)
        
        # Check if this is an organism prefix
        normalized_id = library_identifier.lower().strip()
        if normalized_id in self.ORGANISM_PREFIXES:
            prefix = self.ORGANISM_PREFIXES[normalized_id]
            
            # Find libraries matching this prefix
            matching_libraries = [
                lib_id for lib_id in self.available_libraries.keys()
                if lib_id.startswith(prefix)
            ]
            
            if matching_libraries:
                # Sort by complexity (assuming format like Eco1C1G1T1 where higher numbers = more complex)
                matching_libraries.sort()
                return self._load_library(matching_libraries[0])
        
        # If we get here, no matching library was found
        logger.warning(f"No matching library found for '{library_identifier}'")
        return False
    
    def _load_library(self, library_id: str) -> bool:
        """
        Load a library by its ID.
        
        Args:
            library_id: Library ID to load
            
        Returns:
            True if library was successfully loaded, False otherwise
        """
        if library_id not in self.available_libraries:
            logger.error(f"Library '{library_id}' not found")
            return False
        
        library_info = self.available_libraries[library_id]
        
        # Reset current library data
        self.current_library_data = None
        self.current_customizer = None
        self.current_library_path = None
        self.current_input_path = None
        self.current_output_path = None
        self.current_parsed_path = None
        
        # Try to load parsed data if available
        if "parsed" in library_info:
            try:
                self.current_parsed_path = library_info["parsed"]
                self.current_library_data = load_ecoli_library(self.current_parsed_path)
                logger.info(f"Loaded parsed library data from {self.current_parsed_path}")
            except Exception as e:
                logger.error(f"Failed to load parsed library: {e}")
                self.current_parsed_path = None
                self.current_library_data = None
        
        # Try to load UCF data if available
        if "ucf" in library_info:
            try:
                self.current_library_path = library_info["ucf"]
                self.current_customizer = UCFCustomizer(self.current_library_path)
                logger.info(f"Loaded UCF library from {self.current_library_path}")
                
                # If we don't have parsed data, try to extract basic data from the UCF
                if self.current_library_data is None:
                    self.current_library_data = {
                        "metadata": {"library_id": library_id},
                        "parts": [],
                        "gates": [],
                        "interactions": [],
                        "experimental_data": [],
                        "misc": [],
                        "unrecognized": {"items": [], "fields": []}
                    }
                    
                    # Extract parts and gates from the UCF
                    for collection_name, items in self.current_customizer.collections.items():
                        if collection_name == "parts":
                            self.current_library_data["parts"] = items
                        elif collection_name == "gates":
                            self.current_library_data["gates"] = items
            except Exception as e:
                logger.error(f"Failed to load UCF library: {e}")
                if self.current_library_data is None:
                    return False
        
        # Store input and output file paths if available
        if "input" in library_info:
            self.current_input_path = library_info["input"]
            logger.info(f"Registered input file: {self.current_input_path}")
            
        if "output" in library_info:
            self.current_output_path = library_info["output"]
            logger.info(f"Registered output file: {self.current_output_path}")
        
        # If we have either parsed data or a customizer, consider it a success
        if self.current_library_data is not None or self.current_customizer is not None:
            self.current_library_id = library_id
            return True
        
        return False
    
    def get_library_data(self) -> Optional[Dict[str, Any]]:
        """
        Get the current library data.
        
        Returns:
            Library data dictionary or None if no library is loaded
        """
        return self.current_library_data
    
    def get_customizer(self) -> Optional[UCFCustomizer]:
        """
        Get the UCF customizer for the current library.
        
        Returns:
            UCFCustomizer instance or None if no UCF is loaded
        """
        return self.current_customizer
    
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
                         selected_parts: List[str] = None,
                         modified_parts: Dict[str, Dict] = None,
                         new_parts: List[Dict] = None,
                         ucf_name: str = None,
                         output_dir: str = None) -> Optional[str]:
        """
        Create a custom UCF file with selected parts and modifications.
        
        Args:
            selected_gates: List of gate IDs to include
            selected_parts: List of part IDs to include
            modified_parts: Dict of part_id -> modified properties
            new_parts: List of new part definitions to add
            ucf_name: Optional name for the UCF file
            output_dir: Optional directory to save the UCF file
            
        Returns:
            Path to the created UCF file or None if creation failed
        """
        if self.current_customizer is None:
            logger.error("No UCF library loaded, cannot create custom UCF")
            return None
        
        try:
            return self.current_customizer.create_custom_ucf(
                selected_gates=selected_gates,
                selected_parts=selected_parts,
                modified_parts=modified_parts,
                new_parts=new_parts,
                ucf_name=ucf_name,
                output_dir=output_dir
            )
        except Exception as e:
            logger.error(f"Failed to create custom UCF: {e}")
            return None
    
    def get_current_library_info(self) -> Dict[str, Any]:
        """
        Get information about the currently selected library.
        
        Returns:
            Dictionary with library information
        """
        info = {
            "library_id": self.current_library_id,
            "ucf_path": self.current_library_path,
            "input_path": self.current_input_path,
            "output_path": self.current_output_path,
            "parsed_path": self.current_parsed_path,
            "has_library_data": self.current_library_data is not None,
            "has_customizer": self.current_customizer is not None
        }
        
        # Add some statistics if we have library data
        if self.current_library_data is not None:
            info["num_parts"] = len(self.current_library_data.get("parts", []))
            info["num_gates"] = len(self.current_library_data.get("gates", []))
        
        return info 