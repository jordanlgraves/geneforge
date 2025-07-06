import os
import json
import logging
from typing import Dict, List, Optional, Union, Any
from pathlib import Path
from datetime import datetime
import shutil
import tempfile

import dotenv

CELLO_UCF_ROOT = os.getenv("CELLO_UCF_ROOT")

# Import the module functions directly instead of the class
import src.library.cello_utils as cello_utils

logger = logging.getLogger("library_manager")

DEBUG_MODEL = True
USE_LLM_FOR_LIBRARY_FILTERING = True

def _read_cello_config_file(config_file_path: str) -> Dict[str, Any]:
    """
    Read the Cello config file and return the config as a dictionary.
    """
    with open(config_file_path, 'r') as f:
        return json.load(f)

class CelloLibrary:
    """
    Manages the selection, loading, and customization of UCF libraries.
    Provides a unified interface for working with different library types.
    """
    
    def __init__(self):
        """
        Initialize the CelloLibrary. Scans for available libraries
        but does not load a default one initially.
        """        
        # Scan available libraries
        self.available_libraries = self._scan_libraries()
        
        # Set initial state - no library selected by default
        self.current_library_id: Optional[str] = None
        self.user_constraints: Optional[List[Dict]] = None
        self.user_constraints_path: Optional[str] = None
        self.inputs_path: Optional[str] = None
        self.outputs_path: Optional[str] = None

        self.current_input_data: Optional[List[Dict]] = None
        self.current_output_data: Optional[List[Dict]] = None
        self.current_ucf_data: Optional[List[Dict]] = None
        
        # NOTE: Draft behaviour removed – we now always operate on a **working
        # copy** of the selected library (see `select_library`).  The attribute
        # is kept (always None) for backwards-compatibility with callers that
        # may still check `has_draft`.
        self._draft_ucf: Optional[List[Dict]] = None

        # Active library context - tracks which files are currently "active"
        self._active_context: Dict[str, str] = {
            "ucf_path": None,
            "input_path": None, 
            "output_path": None,
            "context_type": "base"  # "base", "custom", or "draft"
        }

        if not self.available_libraries:
            logger.warning("No libraries found during scan.")
        else:
            logger.info(f"Library manager initialized. Found {len(self.available_libraries)} potential libraries.")
    

    def get_library_specs(self, library_id: str) -> Dict[str, Any]:
        """
        Get the specs for a library.
        """
        return {"library_data": f"Library: {library_id}"} # TODO: Add promoter, gates, parts, input sensors, output devices    
        

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
    
    def filter_libraries_by_organism(self, organism: str) -> Dict[str, Dict[str, str]]:
        """
        Filter the available libraries by organism.
        """
        matched_libraries = list()
        for lib_id in self.available_libraries:
            ucf_path = self.available_libraries[lib_id]["ucf"]
            with open(ucf_path, 'r') as f:
                header = [item for item in json.load(f) if item.get('collection','') == 'header'].pop()
                organism_of_library = header.get('organism','')
                if organism.lower() == organism_of_library.lower():
                    matched_libraries.append(lib_id)
        return matched_libraries
    
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
            self.user_constraints = None
            self.user_constraints_path = None
            self.current_input_data = None
            self.inputs_path = None
            self.current_output_data = None
            self.outputs_path = None
            return False
        
        # Get the library info
        library_info = self.available_libraries[library_id]
        
        # --------------------------------------------------------------
        #  Create isolated working copies inside a timestamped temp dir
        # --------------------------------------------------------------
        temp_root = os.getenv("CELLO_LIB_TEMP") or tempfile.gettempdir()
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        work_dir = Path(temp_root) / "cello_lib_temp" / library_id / ts
        work_dir.mkdir(parents=True, exist_ok=True)

        def _copy(src: str) -> Optional[str]:
            if src and os.path.exists(src):
                dst = work_dir / Path(src).name
                shutil.copy(src, dst)
                return str(dst)
            return None

        ucf_path_original = library_info.get("ucf")
        ucf_path = _copy(ucf_path_original)
        if not ucf_path or not os.path.exists(ucf_path):
            logger.error(f"UCF file path not found or file does not exist for library {library_id}: {ucf_path}")
            # Clear current state if essential file missing
            self.current_library_id = None
            self.user_constraints = None
            self.user_constraints_path = None
            self.current_input_data = None
            self.inputs_path = None
            self.current_output_data = None
            self.outputs_path = None
            return False
        
        # Store the UCF path
        self.user_constraints_path = ucf_path
        
        # Load the UCF file - store raw UCF data
        try:
            self.user_constraints = _read_cello_config_file(self.user_constraints_path)
            logger.info(f"Loaded raw UCF data from {self.user_constraints_path}")
            
            # Load the input file - store raw input data
            input_path_original = library_info.get("input")
            input_path = _copy(input_path_original)
            if input_path and os.path.exists(input_path):
                self.current_input_data = _read_cello_config_file(input_path)
                logger.info(f"Loaded raw input data from {input_path}")

            # Load the output file - store raw output data
            output_path_original = library_info.get("output")
            output_path = _copy(output_path_original)
            if output_path and os.path.exists(output_path):
                self.current_output_data = _read_cello_config_file(output_path)
                logger.info(f"Loaded raw output data from {output_path}")
                    

        except Exception as e:
            logger.error(f"Failed to load or parse UCF library '{library_id}' from {self.user_constraints_path}: {e}")
            # Clear current state on load failure
            self.current_library_id = None
            self.user_constraints = None
            self.user_constraints_path = None
            self.inputs_path = None
            self.outputs_path = None
            if DEBUG_MODEL:
                raise e # Reraise in debug mode
            return False
        
        # Store input and output file paths if available
        self.inputs_path = input_path
        if self.inputs_path:
             logger.info(f"Registered input file: {self.inputs_path}")
        else:
             logger.info(f"No input file found for library {library_id}")
        
        self.outputs_path = output_path
        if self.outputs_path:
            logger.info(f"Registered output file: {self.outputs_path}")
        else:
            logger.info(f"No output file found for library {library_id}")
        
        # Set the current library ID *after* successful loading
        self.current_library_id = library_id
        logger.info(f"Successfully selected library: {library_id}")
        
        # Update active context to use working copy
        self._active_context = {
            "ucf_path": self.user_constraints_path,
            "input_path": self.inputs_path,
            "output_path": self.outputs_path,
            "context_type": "working_copy"
        }
        
        return True
    
    def get_ucf_data(self) -> Optional[List[Dict]]:
        """
        Get the raw UCF data for the currently active library context.
        
        Returns:
            Raw UCF data from the active context (base, custom, or draft)
        """
        # If we have a draft, return that
        if self._draft_ucf is not None:
            return self._draft_ucf
        
        # If we're using a custom UCF, load it fresh
        if self._active_context["context_type"] == "custom" and self._active_context["ucf_path"]:
            try:
                return _read_cello_config_file(self._active_context["ucf_path"])
            except Exception as e:
                logger.error(f"Failed to load custom UCF: {e}")
                # Fall back to base library
                return self.user_constraints
        
        # Default to base library data
        return self.user_constraints
    
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
        return self.inputs_path
    
    def get_output_file_path(self) -> Optional[str]:
        """
        Get the path to the current output file.
        
        Returns:
            Path to the output file or None if no output file is available
        """
        return self.outputs_path
    
    def create_custom_ucf(self, 
                         selected_gates: List[str] = None,
                         selected_parts: List = None,
                         modified_parts: List = None,
                         new_parts: List[Dict] = None,
                         ucf_name: str = None,
                         output_dir: str = None,
                         ucf_data: List[Dict] | None = None) -> Optional[str]:
        """
        Create a custom UCF file with selected parts and modifications.
        
        Args:
            selected_gates: List of gate IDs to include
            selected_parts: List of part objects or IDs to include
            modified_parts: Dict of part_id -> modified properties
            new_parts: List of new part definitions to add
            ucf_name: Optional name for the UCF file
            output_dir: Optional directory to save the UCF file
            ucf_data: Optional existing UCF data to use for the custom UCF
            
        Returns:
            Path to the created UCF file or None if creation failed
        """
        base_data = ucf_data if ucf_data is not None else self.user_constraints
        if not base_data:
            logger.error("No UCF data available, cannot create custom UCF")
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
                    
                    for item in base_data:
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
        custom_ucf_path = cello_utils.create_custom_ucf(
            ucf_data=base_data,
            selected_gates=selected_gates,
            selected_parts=processed_parts,
            modified_parts=modified_parts,
            new_parts=new_parts,
            ucf_name=ucf_name,
            output_dir=output_dir
        )
        self.user_constraints_path = custom_ucf_path
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
            custom_input_path = cello_utils.create_custom_input_sensors_file(
                input_sensor_data=self.current_input_data,
                selected_sensors=selected_sensors,
                modified_models=modified_models,
                new_sensors=new_sensors,
                output_filename=output_filename,
                output_dir=output_dir
            )
            
            # Update the current input path to use the custom file
            self.inputs_path = custom_input_path
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
            "ucf_path": self.user_constraints_path,
            "input_path": self.inputs_path,
            "output_path": self.outputs_path,
            "has_ucf_data": self.user_constraints is not None
        }
        
        # Add some statistics about the UCF if data is available
        if self.user_constraints:
            # Count parts and gates in the raw UCF
            parts_count = sum(1 for item in self.user_constraints if item.get("collection") == "parts")
            gates_count = sum(1 for item in self.user_constraints if item.get("collection") == "gates")
            
            info["num_parts"] = parts_count
            info["num_gates"] = gates_count
        
        return info 

    def load_custom_ucf(self, ucf_path: str) -> bool:
        """
        Loads a custom UCF file into the manager's current state,
        overwriting the previously selected library's UCF data.
        """
        if not os.path.exists(ucf_path):
            logger.error(f"Cannot load custom UCF: file not found at {ucf_path}")
            return False
        
        try:
            self.user_constraints_path = ucf_path
            self.user_constraints = _read_cello_config_file(ucf_path)
            # Mark the library ID to show it's a custom version
            if self.current_library_id and not self.current_library_id.startswith("custom_"):
                self.current_library_id = f"custom_{self.current_library_id}"
            elif not self.current_library_id:
                self.current_library_id = f"custom_{Path(ucf_path).stem}"

            logger.info(f"LibraryManager context updated to custom UCF: {ucf_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to load or parse custom UCF from {ucf_path}: {e}")
            return False 

    # ------------------------------------------------------------------
    #  High-level modification helpers
    # ------------------------------------------------------------------

    def add_promoter_variants(
        self, parent_promoter: str, variants: List[Dict[str, Any]]
    ) -> int:
        """Duplicate *parent_promoter* with each spacer/ymax variant.

        Parameters
        ----------
        parent_promoter : str
            Name/ID of existing promoter in the current library.
        variants : list of {"spacer": str, "ymax": float}

        Returns
        -------
        int – number of new items added to the draft UCF.
        """
        from src.library.cello_utils import duplicate_promoter_dependencies

        if self.user_constraints is None:
            raise RuntimeError("No library selected.")

        successfully_saved_variants = []
        new_items_total: int = 0
        for i, var in enumerate(variants, start=1):
            spacer = var.get("spacer")
            ymax = var.get("ymax")
            if not spacer or len(spacer) != 17:
                continue

            new_promoter_id = f"{parent_promoter}Var{i}"

            # Re-create promoter sequence using parent sequence flanks
            from src.utils import extract_id_ecoli_spacer

            parent_part = next(
                (p for p in self.user_constraints if p.get("collection") == "parts" and p.get("name") == parent_promoter),
                None,
            )
            if not parent_part:
                raise ValueError(f"Parent promoter '{parent_promoter}' not found.")

            parent_seq = parent_part.get("dnasequence") or parent_part.get("sequence")
            spacer_parent = extract_id_ecoli_spacer(parent_seq)
            if not spacer_parent:
                raise ValueError("Could not extract spacer from parent promoter.")
            idx = parent_seq.find(spacer_parent)
            new_seq = f"{parent_seq[:idx].upper()}{spacer.upper()}{parent_seq[idx+17:].upper()}"

            # Use helper to duplicate deps into *new_items*
            new_items, _gate_map = duplicate_promoter_dependencies(
                self.user_constraints, parent_promoter, new_promoter_id, new_seq, ymax
            )
            self.user_constraints.extend(new_items)
            new_items_total += len(new_items)
            var['name'] = new_promoter_id
            successfully_saved_variants.append(var)

        # Persist the updated UCF to disk immediately (no draft stage)
        if self.user_constraints_path:
            try:
                with open(self.user_constraints_path, "w") as fh:
                    json.dump(self.user_constraints, fh, indent=2)
                logger.info("Saved %s new promoter variants to %s", new_items_total, self.user_constraints_path)
            except Exception as exc:
                logger.error("Failed to write updated UCF: %s", exc)

        return successfully_saved_variants

    # ------------------------------------------------------------------
    #  Commit draft
    # ------------------------------------------------------------------

    # (commit_draft_ucf removed – working copy is always saved immediately via
    #  create_custom_ucf / load_custom_ucf workflows. No draft stage.)

    def get_active_ucf_path(self) -> Optional[str]:
        """Get the path to the currently active UCF file."""
        return self._active_context["ucf_path"]
    
    def get_active_input_path(self) -> Optional[str]:
        """Get the path to the currently active input file."""
        return self._active_context["input_path"]
    
    def get_active_output_path(self) -> Optional[str]:
        """Get the path to the currently active output file."""
        return self._active_context["output_path"]
    
    def get_active_context_info(self) -> Dict[str, Any]:
        """Get information about the currently active library context."""
        return {
            **self._active_context,
            "library_id": self.current_library_id,
            "has_draft": False
        }

    def switch_to_custom_context(self, ucf_path: str, input_path: str = None, output_path: str = None) -> bool:
        """Switch the active context to use custom library files.
        
        This method allows tools to explicitly switch to using custom files
        without modifying the base library state.
        """
        if not os.path.exists(ucf_path):
            logger.error(f"Custom UCF file not found: {ucf_path}")
            return False
        
        self._active_context = {
            "ucf_path": ucf_path,
            "input_path": input_path or self.inputs_path,
            "output_path": output_path or self.outputs_path,
            "context_type": "custom"
        }
        
        logger.info(f"Switched to custom library context: {ucf_path}")
        return True
    
    def reset_to_base_context(self) -> None:
        """Reset the active context to use the base library files."""
        self._active_context = {
            "ucf_path": self.user_constraints_path,
            "input_path": self.inputs_path,
            "output_path": self.outputs_path,
            "context_type": "base"
        }
        logger.info("Reset to base library context") 

    def find_part_by_sequence(self, sequence: str) -> Optional[str]:
        """Find a part by sequence."""
        for part in self.user_constraints:
            if part.get("collection") == "parts":
                if 'dnasequence' in part and part.get("dnasequence") and part.get("dnasequence").lower() == sequence.lower():
                    return part.get("name")
                elif 'sequence' in part and part.get("sequence") and part.get("sequence").lower() == sequence.lower():
                    return part.get("name")
                
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the library to a dictionary."""
        return {
            "current_library_id": self.current_library_id,
            "user_constraints": self.get_ucf_data(),
            "inputs": self.get_input_sensor_data(),
            "outputs": self.get_output_device_data(),
            "current_library_id": self.current_library_id,
        }