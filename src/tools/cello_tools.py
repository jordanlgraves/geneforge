from __future__ import annotations

from typing import Dict, List, Any
import os
import traceback
import logging

import src.library.cello_utils as cello_utils

from src.tools.base_tool import Tool

logger = logging.getLogger(__name__)

import dotenv
dotenv.load_dotenv()
DEBUG_MODE = os.getenv("DEBUG_MODE", "False").lower() == "true"
# ---------------------------------------------------------------------------
#  Cello library exploration / management tools
# ---------------------------------------------------------------------------

class ListPromotersTool(Tool):
    name = "list_promoters"
    description = "Return a list of promoter parts from the selected library. IMPORTANT: You must first select a library using select_library before using this function."
    parameters = {
        "type": "object",
        "properties": {
            "file_type": {
                "type": "string",
                "description": "The type of file to list parts from, must be 'input', 'output', or 'ucf'"
            }
        },
        "required": ["file_type"]
    }
    
    def execute(self, file_type: str) -> Dict[str, Any]:
        """Return a list of promoter parts from the currently selected library."""
        if file_type == "input":    
            library_data, error = self._get_current_library_input_data()
        elif file_type == "output":
            library_data, error = self._get_current_library_output_data()
        elif file_type == "ucf":
            library_data, error = self._get_current_library_ucf_data()
        else:
            return {"error": f"Invalid file type: {file_type}, must be 'input', 'output', or 'ucf'"}

        if error:
            return error

        try:
            promoters = cello_utils.get_parts_by_type(library_data, "promoter")
            return {
                "success": True,
                "library_id": self.session_state.cello_library.current_library_id,
                "promoters": promoters
            }
        except Exception as e:
            if DEBUG_MODE:
                traceback.print_exc()
                raise e
            else:
                return {"error": f"Error listing promoters: {str(e)}"}
    
    def _get_current_library_ucf_data(self):
        """Helper to get structured data for the currently selected library."""
        cello_library = self.session_state.cello_library
        if not cello_library.current_library_id:
             return None, {"error": "No library selected. Please use 'select_library' first."}
        library_data = cello_library.get_ucf_data()
        if not library_data:
             return None, {"error": f"Could not load structured data for library {cello_library.current_library_id}."}
        return library_data, None

    def _get_current_library_input_data(self):
        """Helper to get structured data for the currently selected library."""
        cello_library = self.session_state.cello_library
        if not cello_library.current_library_id:
             return None, {"error": "No library selected. Please use 'select_library' first."}
        library_data = cello_library.get_input_sensor_data()
        if not library_data:
             return None, {"error": f"Could not load structured data for library {cello_library.current_library_id}."}
        return library_data, None

    def _get_current_library_output_data(self):
        """Helper to get structured data for the currently selected library."""
        cello_library = self.session_state.cello_library
        if not cello_library.current_library_id:
             return None, {"error": "No library selected. Please use 'select_library' first."}
        library_data = cello_library.get_output_device_data()
        if not library_data:
             return None, {"error": f"Could not load structured data for library {cello_library.current_library_id}."}
        return library_data, None

class ListInputSensorsTool(Tool):
    name = "list_input_sensors"
    description = "Return a list of input sensors from the selected library. IMPORTANT: You must first select a library using select_library before using this function."
    parameters = {
        "type": "object",
        "properties": {},
        "required": []
    }
    
    def execute(self) -> Dict[str, Any]:
        """Return a list of input sensors from the currently selected library."""
        library_data = self.session_state.cello_library.get_input_sensor_data()
        
        try:
            sensors = cello_utils.get_input_sensors(library_data)
            return {
                "success": True,
                "library_id": self.session_state.cello_library.current_library_id,
                "input_sensors": sensors
            }
        except Exception as e:
            if DEBUG_MODE:
                traceback.print_exc()
                raise e
            else:
                return {"error": f"Error listing input sensors: {str(e)}"}


class DescribeAvailableLibrariesTool(Tool):
    name = "describe_available_libraries"
    description = "Return a description of the available libraries which includes the header which contains the organism name among other details, the UCF path, the input sensor file path and the output file path."
    parameters = {
        "type": "object",
        "properties": {},
        "required": []
    }
    
    def execute(self) -> Dict[str, Any]:
        """Return a description of the available libraries found by the session's LibraryManager."""
        cello_library = self.session_state.cello_library
        return {
            "success": True,
            "libraries": cello_library.describe_available_libraries()
        }

class SelectLibraryTool(Tool):
    name = "select_library"
    description = "Select a library using a library ID."
    parameters = {
        "type": "object",
        "properties": {
            "library_id": {
                "type": "string",
                "description": "The ID of the library to select."
            }
        },
        "required": ["library_id"]
    }
    
    def execute(self, library_id: str) -> Dict[str, Any]:
        """Select a library using a library ID within the current session."""
        success = self.session_state.select_library(library_id)
        if success:
            return {
                "success": True,
                "message": f"Session selected library {library_id}",
            }
        else:
            available = list(self.session_state.cello_library.get_available_libraries().keys())
            return {
                "success": False,
                "error": f"Failed to select library {library_id}. Available libraries: {available}",
                "available_libraries": available
            }



class QueryLibrariesByOrganismTool(Tool):
    name = "query_libraries_by_organism"
    description = "Query the available libraries by organism. The organism field in the library metadata must match the organism name exactly (case-insensitive)."
    parameters = {
        "type": "object",
        "properties": {
            "organism": {
                "type": "string",
                "description": "The exact 'organism' field in the library metadata to filter libraries by."
            }
        },
        "required": ["organism"]
    }
    
    def execute(self, organism: str) -> Dict[str, Any]:
        """Query the available libraries by organism."""
        success = self.session_state.query_libraries_by_organism(organism)
        if success:
            response = {
                "success": True,
                "message": f"Session queried libraries by organism {organism}",
                "matched_libraries": self.session_state.cello_library.get_available_libraries().keys()
            }
            return response
        else:
            available = list(self.session_state.cello_library.get_available_libraries().keys())
            return {
                "success": False,
                    "error": f"Failed to query libraries by organism {organism}. Available libraries: {available}",
                "available_libraries": available
            }

class ListRepressorsTool(Tool):
    name = "list_repressors"
    description = "Return a list of possible repressors from the selected library. Optionally filter by family. IMPORTANT: You must first select a library using select_library before using this function."
    parameters = {
        "type": "object",
        "properties": {
            "file_type": {
                "type": "string",
                "description": "The type of file to list parts from, must be 'input', 'output', or 'ucf'"
            }
        },
        "required": ["file_type"]
    }
    
    def execute(self, file_type: str) -> Dict[str, Any]:
        """Return a list of possible repressors from the currently selected library."""
        if file_type == "ucf":
            library_data, error = self._get_current_library_ucf_data()
        elif file_type == "input":
            library_data, error = self._get_current_library_input_data()
        elif file_type == "output":
            library_data, error = self._get_current_library_output_data()
        else:
            return {"error": f"Invalid file type: {file_type}, must be 'ucf', 'input', or 'output'"}

        if error:
            return error

        try:
            repressors = cello_utils.get_parts_by_type(library_data, "repressor")
            return {
                "success": True,
                "library_id": self.session_state.cello_library.current_library_id,
                "repressors": repressors
            }
        except Exception as e:
            return {"error": f"Error listing repressors: {str(e)}"}
    
    def _get_current_library_ucf_data(self):
        """Helper to get structured data for the currently selected library."""
        cello_library = self.session_state.cello_library
        if not cello_library.current_library_id:
             return None, {"error": "No library selected. Please use 'select_library' first."}
        library_data = cello_library.get_ucf_data()
        if not library_data:
             return None, {"error": f"Could not load structured data for library {cello_library.current_library_id}."}
        return library_data, None


    def _get_current_library_input_data(self):
        """Helper to get structured data for the currently selected library."""
        cello_library = self.session_state.cello_library
        if not cello_library.current_library_id:
             return None, {"error": "No library selected. Please use 'select_library' first."}
        library_data = cello_library.get_input_sensor_data()
        if not library_data:
             return None, {"error": f"Could not load structured data for library {cello_library.current_library_id}."}
        return library_data, None

    def _get_current_library_output_data(self):
        """Helper to get structured data for the currently selected library."""
        cello_library = self.session_state.cello_library
        if not cello_library.current_library_id:
             return None, {"error": "No library selected. Please use 'select_library' first."}
        library_data = cello_library.get_output_device_data()
        if not library_data:
             return None, {"error": f"Could not load structured data for library {cello_library.current_library_id}."}
        return library_data, None

class GetDnaPartByNameTool(Tool):
    name = "get_dna_part_by_name"
    description = "Get a specific DNA part by name (like 'pTet') from the selected library in the user constraints file. IMPORTANT: You must first select a library using select_library before using this function."
    parameters = {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Name or ID of the DNA part to retrieve."
            },
            "file_type": {
                "type": "string",
                "description": "The type of file to list parts from, must be 'input', 'output', or 'ucf'"
            }
        },
        "required": ["name", "file_type"]
    }
    
    def execute(self, name: str, file_type: str) -> Dict[str, Any]:
        """Get a specific DNA part by name from the currently selected library."""
        if file_type == "ucf":
            library_data, error = self._get_current_library_ucf_data()
        elif file_type == "input":
            library_data, error = self._get_current_library_input_data()
        elif file_type == "output":
            library_data, error = self._get_current_library_output_data()
        else:
            return {"error": f"Invalid file type: {file_type}, must be 'ucf', 'input', or 'output'"}

        if error:
            return error

        try:
            part = cello_utils.get_part_by_name(library_data, name)
            if part:
                 return {
                    "success": True,
                    "library_id": self.session_state.cello_library.current_library_id,
                    "part": part
                }
            else:
                return {"error": f"DNA part with name '{name}' not found in library {self.session_state.cello_library.current_library_id}"}
        except Exception as e:
            return {"error": f"Error getting DNA part: {str(e)}"}
    
    def _get_current_library_ucf_data(self):
        """Helper to get structured data for the currently selected library."""
        cello_library = self.session_state.cello_library
        if not cello_library.current_library_id:
             return None, {"error": "No library selected. Please use 'select_library' first."}
        library_data = cello_library.get_ucf_data()
        if not library_data:
             return None, {"error": f"Could not load structured data for library {cello_library.current_library_id}."}
        return library_data, None


    def _get_current_library_input_data(self):
        """Helper to get structured data for the currently selected library."""
        cello_library = self.session_state.cello_library
        if not cello_library.current_library_id:
             return None, {"error": "No library selected. Please use 'select_library' first."}
        library_data = cello_library.get_input_sensor_data()
        if not library_data:
             return None, {"error": f"Could not load structured data for library {cello_library.current_library_id}."}
        return library_data, None

    def _get_current_library_output_data(self):
        """Helper to get structured data for the currently selected library."""
        cello_library = self.session_state.cello_library
        if not cello_library.current_library_id:
             return None, {"error": "No library selected. Please use 'select_library' first."}
        library_data = cello_library.get_output_device_data()
        if not library_data:
             return None, {"error": f"Could not load structured data for library {cello_library.current_library_id}."}
        return library_data, None

class ListTerminatorsTool(Tool):
    name = "list_terminators"
    description = "Return a list of terminator parts from the selected library. IMPORTANT: You must first select a library using select_library before using this function."
    parameters = {
        "type": "object",
        "properties": {
            "file_type": {
                "type": "string",
                "description": "The type of file to list parts from, must be 'input', 'output', or 'ucf'"
            }
        },
        "required": ["file_type"]
    }
    
    def execute(self, file_type: str) -> Dict[str, Any]:
        """Return a list of terminator parts from the currently selected library."""
        if file_type == "ucf":
            library_data, error = self._get_current_library_ucf_data()
        elif file_type == "input":
            library_data, error = self._get_current_library_input_data()
        elif file_type == "output":
            library_data, error = self._get_current_library_output_data()
        else:
            return {"error": f"Invalid file type: {file_type}, must be 'ucf', 'input', or 'output'"}

        if error:
            return error

        try:
            terminators = cello_utils.get_parts_by_type(library_data, "terminator")
            return {
                "success": True,
                "library_id": self.session_state.cello_library.current_library_id,
                "terminators": terminators
            }
        except Exception as e:
            return {"error": f"Error listing terminators: {str(e)}"}
    
    def _get_current_library_ucf_data(self):
        """Helper to get structured data for the currently selected library."""
        cello_library = self.session_state.cello_library
        if not cello_library.current_library_id:
             return None, {"error": "No library selected. Please use 'select_library' first."}
        library_data = cello_library.get_ucf_data()
        if not library_data:
             return None, {"error": f"Could not load structured data for library {cello_library.current_library_id}."}
        return library_data, None


    def _get_current_library_input_data(self):
        """Helper to get structured data for the currently selected library."""
        cello_library = self.session_state.cello_library
        if not cello_library.current_library_id:
             return None, {"error": "No library selected. Please use 'select_library' first."}
        library_data = cello_library.get_input_sensor_data()
        if not library_data:
             return None, {"error": f"Could not load structured data for library {cello_library.current_library_id}."}
        return library_data, None

    def _get_current_library_output_data(self):
        """Helper to get structured data for the currently selected library."""
        cello_library = self.session_state.cello_library
        if not cello_library.current_library_id:
             return None, {"error": "No library selected. Please use 'select_library' first."}
        library_data = cello_library.get_output_device_data()
        if not library_data:
             return None, {"error": f"Could not load structured data for library {cello_library.current_library_id}."}
        return library_data, None

class DesignWithCelloTool(Tool):
    name = "design_with_cello"
    description = "Design genetic circuits using Cello. Accepts Verilog code and optional configuration."
    parameters = {
        "type": "object",
        "properties": {
            "run_name": {
                "type": "string",
                "description": "The name of the run to use for the Cello design"
            },
            "verilog_code": {
                "type": "string",
                "description": "The Verilog code representing the circuit design"
            },
            "config": {
                "type": "object",
                "description": "Optional Cello configuration parameters",
                "properties": {
                    "exhaustive": {"type": "boolean"},
                    "total_iters": {"type": "integer"},
                    "verbose": {"type": "boolean"}
                }
            }
        },
        "required": ["run_name", "verilog_code"]
    }
    
    def execute(self, run_name: str, verilog_code: str, config: dict = None) -> Dict[str, Any]:
        """Interface with Cello using the currently selected library context."""
        cello_library = self.session_state.cello_library
        if not cello_library.current_library_id:
            return {"error": "No library selected. Please use 'select_library' first."}

        # Use active context paths (handles base, custom, or draft automatically)
        ucf_path = cello_library.get_active_ucf_path()
        input_path = cello_library.get_active_input_path()
        output_path = cello_library.get_active_output_path()
        
        # Get context info for logging
        context_info = cello_library.get_active_context_info()
        logger.info(f"Using library context: {context_info}")

        if not ucf_path or not input_path:
             return {"error": f"Missing UCF ({ucf_path}) or Input ({input_path}) file path for library {cello_library.current_library_id}."}

        from src.integrations.cello_integration import CelloIntegration

        # Pass the library_manager from the session state
        cello = CelloIntegration(
            cello_config=config or {},
            library_manager=cello_library,
            output_root=str(self.session_state.output_directory) if self.session_state.output_directory else None
        )

    
        self.session_state.set_verilog_code(verilog_code) # let's update the sessions state's verilog_code with the new verilog code
        results = cello.run_cello(run_name=run_name, verilog_code=verilog_code, custom_ucf=os.path.basename(ucf_path))

        if not results['success']:
            return {
                "error": f"Cello design failed: {results.get('error', 'Unknown error')}",
                "log": results.get('log', 'No log available.')
            }

        self.session_state.cello_results = results

        return {
            "success": True,
            "library_id": cello_library.current_library_id,
            "context_type": context_info["context_type"],
            "active_ucf": ucf_path,
            "output_directory": results.get('output_dir'),
            "dna_design": results.get('results', {}).get('dna_design'),
            "log": results.get('log')
        }

class CreateCustomUcfTool(Tool):
    name = "create_custom_ucf"
    description = "Create a customized library file with selected parts. Parts referencing the selected parts will be included in the custom library. IMPORTANT: You must first select a library using the select_library function before using this function."
    parameters = {
        "type": "object",
        "properties": {
            "selected_gates": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of gate IDs to include in the custom UCF"
            },
            "selected_parts": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of part names or IDs to include in the custom UCF"
            },
            "modified_parts": {
                "type": "object",
                "description": "Dict of part_id -> modified properties"
            },
            "ucf_name": {
                "type": "string",
                "description": "Optional name for the UCF file"
            }
        },
        "required": []
    }

    def _is_dna(self, part: str) -> bool:
        """Check if a part is a DNA sequence."""
        dna_chars = set("ATGCRYSWKMBDHVNatgcryswkmbdhvn")
        is_dna = set(part).issubset(dna_chars)
        return is_dna
    
    def execute(self, selected_gates: List[str] = None, 
                selected_parts: List[str] = None, 
                modified_parts: Dict[str, Dict] = None, 
                ucf_name: str = None) -> Dict[str, Any]:
        """Create a customized UCF file based on the currently selected library."""
        cello_library = self.session_state.cello_library
        from src.library.cello_utils import get_part_by_name
        if not cello_library.current_library_id:
            return {"error": "No library selected as base for custom UCF. Please use 'select_library' first."}

        base_ucf_data = cello_library.get_ucf_data()
        if not base_ucf_data:
             return {"error": f"Could not retrieve base UCF data for library {cello_library.current_library_id}."}

        custom_ucf_name = ucf_name or f"custom_{cello_library.current_library_id}.UCF.json"

        try:
            # Check if the parts are DNA sequences or names
            part_ids = []
            for part_id_or_sequence in selected_parts:
                if get_part_by_name(base_ucf_data, part_id_or_sequence):
                    part_ids.append(part_id_or_sequence)
                    continue

                if self._is_dna(part_id_or_sequence) and len(part_id_or_sequence) >= 16:
                    part_id = cello_library.find_part_by_sequence(part_id_or_sequence)
                    if not part_id:
                        # The sequence may be a spacer sequence, so we need to find the promoter
                        collections = cello_library.get_ucf_data()
                        for col in collections:
                            if col.get("collection") == "promoter":
                                promoter_seq = col.get("dnasequence")
                                if promoter_seq and part_id_or_sequence.lower() in promoter_seq.lower():
                                    # Could be this one
                                    from src.utils import extract_id_ecoli_spacer
                                    spacer = extract_id_ecoli_spacer(part_id_or_sequence)
                                    if spacer:
                                        part_id = col.get("name")
                                        break # found the part, break out of the loop
                            elif col.get("collection") == "promoter_variants":
                                for variant in col.get("promoter_variants"):
                                    if variant.get("dnasequence") and variant.get("dnasequence").lower() == part_id_or_sequence.lower():
                                        part_id = variant.get("name")
                                        break # found the part, break out of the loop
                        if not part_id:
                            return {"error": f"Part {part_id_or_sequence} is not a DNA sequence. Please provide a list of part names or IDs."}
                    part_ids.append(part_id)
                else:   
                    part_ids.append(part_id_or_sequence)

            custom_ucf_path = cello_library.create_custom_ucf(
                selected_gates=selected_gates,
                selected_parts=part_ids,
                modified_parts=modified_parts,
                ucf_name=custom_ucf_name,
                output_dir=self.session_state.output_directory
            )

            if custom_ucf_path:
                cello_library.load_custom_ucf(custom_ucf_path)
                self.session_state.custom_ucf_path = custom_ucf_path
                return {
                    "success": True,
                    "library_id": cello_library.current_library_id,
                    # "custom_ucf_path": custom_ucf_path
                }
            else:
                 return {"error": "UCF customization process failed to return a path."}

        except Exception as e:
             logger.error(f"Error creating custom UCF: {e}", exc_info=True)
             return {"error": f"Error creating custom UCF: {str(e)}"}

class CreateCustomInputSensorsFileTool(Tool):
    name = "create_custom_input_sensors_file"
    description = "Create a customized input sensors file with selected sensors. Dependencies such as models, structures, parts, and functions used by the selected sensors will be included. IMPORTANT: You must first select a library using the select_library function before using this function."
    parameters = {
        "type": "object",
        "properties": {
            "selected_sensors": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of sensor names to include in the custom input sensors file"
            },
            "modified_models": {
                "type": "array",
                "items": {"type": "object"},
                "description": "List of model objects with modified parameters"
            },
            "new_sensors": {
                "type": "array",
                "items": {"type": "object"},
                "description": "List of new sensor definitions to add to the file"
            },
            "output_filename": {
                "type": "string",
                "description": "Optional name for the output file"
            }
        },
        "required": ["selected_sensors"]
    }
    
    def execute(self, selected_sensors: List[str], modified_models: List[Dict] = None, new_sensors: List[Dict] = None, output_filename: str = None) -> Dict[str, Any]:
        """Create a customized input sensors file based on the currently selected library."""
        cello_library = self.session_state.cello_library
        if not cello_library.current_library_id:
            return {"error": "No library selected as base for custom input sensors file. Please use 'select_library' first."}

        input_sensor_data = cello_library.get_input_sensor_data()
        if not input_sensor_data:
             return {"error": f"Could not retrieve input sensor data for library {cello_library.current_library_id}."}

        output_dir = "outputs/custom_sensors"
        custom_filename = output_filename or f"custom_{cello_library.current_library_id}.input.json"

        try:
            custom_file_path = cello_library.create_custom_input_sensors_file(
                selected_sensors=selected_sensors,
                modified_models=modified_models,
                new_sensors=new_sensors,
                output_filename=custom_filename,
                output_dir=output_dir
            )

            if custom_file_path:
                self.session_state.custom_input_path = custom_file_path
                return {
                    "success": True,
                    "library_id_base": cello_library.current_library_id,
                    "custom_input_sensors_path": custom_file_path
                }
            else:
                 return {"error": "Input sensors file customization process failed to return a path."}

        except Exception as e:
             logger.error(f"Error creating custom input sensors file: {e}", exc_info=True)
             return {"error": f"Error creating custom input sensors file: {str(e)}"}


class EvaluateCircuitPerformanceTool(Tool):
    name = "evaluate_circuit_performance"
    description = "Evaluate the performance of a designed genetic circuit by analyzing Cello output files"
    parameters = {
        "type": "object",
        "properties": {
            "output_path": {
                "type": "string",
                "description": "Path to the Cello output directory for the circuit"
            }
        },
        "required": ["output_path"]
    }
    
    def execute(self, output_path: str) -> Dict[str, Any]:
        """Evaluate circuit performance by extracting metrics from Cello output files."""
        from src.integrations.cello_integration import CelloIntegration
        
        # Initialize Cello integration
        cello_library = self.session_state.cello_library
        cello = CelloIntegration(
            output_root=self.session_state.output_directory,
            library_manager=cello_library
        )
        
        # Evaluate circuit performance
        metrics = cello.evaluate_circuit_performance(output_path)
        
        return {
            "success": metrics['success'],
            "overall_score": metrics.get('overall_score'),
            "on_off_ratios": metrics.get('on_off_ratios', {}),
            "leakage": metrics.get('leakage', {}),
            "dynamic_range": metrics.get('dynamic_range', {}),
            "average_on_off_ratio": metrics.get('average_on_off_ratio'),
            "average_leakage": metrics.get('average_leakage'),
            "meets_performance_standards": metrics.get('meets_performance_standards', {}),
            "error": metrics.get('error')
        }

class GenerateVerilogToolLLM(Tool):
    name = "generate_verilog"
    description = (
        "Generate Verilog code for the current design specification. "
        "If a 'spec' argument is supplied it will be used, otherwise the tool "
        "will look for a `design_spec` attribute on the current SessionState."
    )
    parameters = {
        "type": "object",
        "properties": {
            "spec": {
                "type": "string",
                "description": "Optional free-text specification of the circuit to implement. If omitted, the tool will use session_state.design_spec if available."
            }
        },
        "required": []
    }

    def execute(self, spec: str = None) -> Dict[str, Any]:
        """Generate Verilog code by delegating to an LLM (OpenAI chat API)."""
        # Determine which specification to use
        if not spec:
            spec = getattr(self.session_state, "design_spec", None)
        if not spec:
            return {"error": "No specification provided and none found in session_state.design_spec."}

        try:
            from openai import OpenAI  # Local import to avoid mandatory dependency at import time
            import os

            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are an expert digital logic designer. "
                        "Generate synthesizable Verilog-2001 code that meets the user's specification. "
                        "Only return the Verilog code, no explanation."
                    ),
                },
                {"role": "user", "content": spec},
            ]

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.7,
            )
            verilog_code = response.choices[0].message.content.strip()

            if '```verilog' in verilog_code: # remove the ```verilog tags
                verilog_code = verilog_code.split('```verilog')[1].split('```')[0]
                
            # Persist for downstream tools
            self.session_state.verilog_code = verilog_code

            return {
                "success": True,
                "verilog_code": verilog_code,
            }
        except Exception as e:
            return {"error": f"Error generating Verilog: {str(e)}"}


# ---------------------------------------------------------------------------
#  GetCelloLibraryStatusTool
# ---------------------------------------------------------------------------

class GetCelloLibraryStatusTool(Tool):
    name = "get_cello_library_status"
    description = "Get the current Cello library status including active context, base library, and any pending drafts."
    parameters = {
        "type": "object",
        "properties": {},
        "required": [],
    }

    def execute(self):
        cello_library = self.session_state.cello_library
        
        if not cello_library.current_library_id:
            return {"error": "No library selected"}
        
        context_info = cello_library.get_active_context_info()
        base_info = cello_library.get_current_library_info()
        
        return {
            "success": True,
            "base_library": {
                "library_id": base_info["library_id"],
                "ucf_path": base_info["ucf_path"],
                "input_path": base_info["input_path"],
                "output_path": base_info["output_path"],
                "num_parts": base_info.get("num_parts"),
                "num_gates": base_info.get("num_gates")
            },
            "active_context": context_info,
            "currently_using": {
                "ucf_path": cello_library.get_active_ucf_path(),
                "input_path": cello_library.get_active_input_path(),
                "output_path": cello_library.get_active_output_path()
            }
        }
