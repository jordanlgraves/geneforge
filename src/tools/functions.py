# tools/functions.py

import json
import os
import glob
import re
from typing import Dict, List, Any, Optional, Type, ClassVar
import src.library.part_library_customizer as part_library_customizer
from src.tools.gpro_integration import PromoterOptimizer, RepressorOptimizer
from src.library.library_manager import LibraryManager
from src.tools.deepseed_integration import DeepSeedIntegration
from src.session_state import SessionState
import traceback
import logging

from langchain_community.tools import ReadFileTool
from langchain_core.utils.function_calling import convert_to_openai_function

DEBUG_MODE = True

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Tool:
    """Base class for all tools."""
    name: ClassVar[str]
    description: ClassVar[str]
    parameters: ClassVar[Dict[str, Any]]

    def __init__(self, session_state: SessionState):
        self.session_state = session_state
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the tool function with provided arguments."""
        raise NotImplementedError("Tool subclasses must implement execute method")
    
    @classmethod
    def get_openai_schema(cls) -> Dict[str, Any]:
        """Generate the OpenAI function schema for this tool."""
        return {
            "name": cls.name,
            "description": cls.description,
            "parameters": cls.parameters,
        }

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
            promoters = part_library_customizer.get_parts_by_type(library_data, "promoter")
            return {
                "success": True,
                "library_id": self.session_state.get_current_library_id(),
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
        library_manager = self.session_state.get_library_manager()
        if not library_manager.current_library_id:
             return None, {"error": "No library selected. Please use 'select_library' first."}
        library_data = library_manager.get_ucf_data()
        if not library_data:
             return None, {"error": f"Could not load structured data for library {library_manager.current_library_id}."}
        return library_data, None


    def _get_current_library_input_data(self):
        """Helper to get structured data for the currently selected library."""
        library_manager = self.session_state.get_library_manager()
        if not library_manager.current_library_id:
             return None, {"error": "No library selected. Please use 'select_library' first."}
        library_data = library_manager.get_input_sensor_data()
        if not library_data:
             return None, {"error": f"Could not load structured data for library {library_manager.current_library_id}."}
        return library_data, None

    def _get_current_library_output_data(self):
        """Helper to get structured data for the currently selected library."""
        library_manager = self.session_state.get_library_manager()
        if not library_manager.current_library_id:
             return None, {"error": "No library selected. Please use 'select_library' first."}
        library_data = library_manager.get_output_device_data()
        if not library_data:
             return None, {"error": f"Could not load structured data for library {library_manager.current_library_id}."}
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
        library_data = self.session_state.get_library_manager().get_input_sensor_data()
        
        try:
            sensors = part_library_customizer.get_input_sensors(library_data)
            return {
                "success": True,
                "library_id": self.session_state.get_current_library_id(),
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
    description = "Return a description of the available libraries."
    parameters = {
        "type": "object",
        "properties": {},
        "required": []
    }
    
    def execute(self) -> Dict[str, Any]:
        """Return a description of the available libraries found by the session's LibraryManager."""
        library_manager = self.session_state.get_library_manager()
        return {
            "success": True,
            "libraries": library_manager.describe_available_libraries()
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
                "message": f"Session selected library {library_id}"
            }
        else:
            available = list(self.session_state.get_library_manager().get_available_libraries().keys())
            return {
                "success": False,
                "error": f"Failed to select library {library_id}. Available libraries: {available}",
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
            repressors = part_library_customizer.get_parts_by_type(library_data, "repressor")
            return {
                "success": True,
                "library_id": self.session_state.get_current_library_id(),
                "repressors": repressors
            }
        except Exception as e:
            return {"error": f"Error listing repressors: {str(e)}"}
    
    def _get_current_library_ucf_data(self):
        """Helper to get structured data for the currently selected library."""
        library_manager = self.session_state.get_library_manager()
        if not library_manager.current_library_id:
             return None, {"error": "No library selected. Please use 'select_library' first."}
        library_data = library_manager.get_ucf_data()
        if not library_data:
             return None, {"error": f"Could not load structured data for library {library_manager.current_library_id}."}
        return library_data, None


    def _get_current_library_input_data(self):
        """Helper to get structured data for the currently selected library."""
        library_manager = self.session_state.get_library_manager()
        if not library_manager.current_library_id:
             return None, {"error": "No library selected. Please use 'select_library' first."}
        library_data = library_manager.get_input_sensor_data()
        if not library_data:
             return None, {"error": f"Could not load structured data for library {library_manager.current_library_id}."}
        return library_data, None

    def _get_current_library_output_data(self):
        """Helper to get structured data for the currently selected library."""
        library_manager = self.session_state.get_library_manager()
        if not library_manager.current_library_id:
             return None, {"error": "No library selected. Please use 'select_library' first."}
        library_data = library_manager.get_output_device_data()
        if not library_data:
             return None, {"error": f"Could not load structured data for library {library_manager.current_library_id}."}
        return library_data, None



class GetDnaPartByNameTool(Tool):
    name = "get_dna_part_by_name"
    description = "Get a specific DNA part by name (like 'pTet') from the selected library in the user contrainsts file. IMPORTANT: You must first select a library using select_library before using this function."
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
            part = part_library_customizer.get_part_by_name(library_data, name)
            if part:
                 return {
                    "success": True,
                    "library_id": self.session_state.get_current_library_id(),
                    "part": part
                }
            else:
                return {"error": f"DNA part with name '{name}' not found in library {self.session_state.get_current_library_id()}"}
        except Exception as e:
            return {"error": f"Error getting DNA part: {str(e)}"}
    
    def _get_current_library_ucf_data(self):
        """Helper to get structured data for the currently selected library."""
        library_manager = self.session_state.get_library_manager()
        if not library_manager.current_library_id:
             return None, {"error": "No library selected. Please use 'select_library' first."}
        library_data = library_manager.get_ucf_data()
        if not library_data:
             return None, {"error": f"Could not load structured data for library {library_manager.current_library_id}."}
        return library_data, None


    def _get_current_library_input_data(self):
        """Helper to get structured data for the currently selected library."""
        library_manager = self.session_state.get_library_manager()
        if not library_manager.current_library_id:
             return None, {"error": "No library selected. Please use 'select_library' first."}
        library_data = library_manager.get_input_sensor_data()
        if not library_data:
             return None, {"error": f"Could not load structured data for library {library_manager.current_library_id}."}
        return library_data, None

    def _get_current_library_output_data(self):
        """Helper to get structured data for the currently selected library."""
        library_manager = self.session_state.get_library_manager()
        if not library_manager.current_library_id:
             return None, {"error": "No library selected. Please use 'select_library' first."}
        library_data = library_manager.get_output_device_data()
        if not library_data:
             return None, {"error": f"Could not load structured data for library {library_manager.current_library_id}."}
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
            terminators = part_library_customizer.get_parts_by_type(library_data, "terminator")
            return {
                "success": True,
                "library_id": self.session_state.get_current_library_id(),
                "terminators": terminators
            }
        except Exception as e:
            return {"error": f"Error listing terminators: {str(e)}"}
    
    def _get_current_library_ucf_data(self):
        """Helper to get structured data for the currently selected library."""
        library_manager = self.session_state.get_library_manager()
        if not library_manager.current_library_id:
             return None, {"error": "No library selected. Please use 'select_library' first."}
        library_data = library_manager.get_ucf_data()
        if not library_data:
             return None, {"error": f"Could not load structured data for library {library_manager.current_library_id}."}
        return library_data, None


    def _get_current_library_input_data(self):
        """Helper to get structured data for the currently selected library."""
        library_manager = self.session_state.get_library_manager()
        if not library_manager.current_library_id:
             return None, {"error": "No library selected. Please use 'select_library' first."}
        library_data = library_manager.get_input_sensor_data()
        if not library_data:
             return None, {"error": f"Could not load structured data for library {library_manager.current_library_id}."}
        return library_data, None

    def _get_current_library_output_data(self):
        """Helper to get structured data for the currently selected library."""
        library_manager = self.session_state.get_library_manager()
        if not library_manager.current_library_id:
             return None, {"error": "No library selected. Please use 'select_library' first."}
        library_data = library_manager.get_output_device_data()
        if not library_data:
             return None, {"error": f"Could not load structured data for library {library_manager.current_library_id}."}
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
        library_manager = self.session_state.get_library_manager()
        if not library_manager.current_library_id:
            return {"error": "No library selected. Please use 'select_library' first."}

        ucf_path = library_manager.current_ucf_path
        input_path = library_manager.current_input_path
        output_path = library_manager.current_output_path

        if not ucf_path or not input_path:
             return {"error": f"Missing UCF ({ucf_path}) or Input ({input_path}) file path for library {library_manager.current_library_id}."}

        from src.tools.cello_integration import CelloIntegration

        # Pass the library_manager from the session state
        cello = CelloIntegration(
            cello_config=config or {},
            library_manager=library_manager
        )

        output_dir = f"outputs/cello_run_{library_manager.current_library_id}"
        results = cello.run_cello(run_name=run_name, verilog_code=verilog_code, custom_ucf=os.path.basename(ucf_path))

        if not results['success']:
            return {
                "error": f"Cello design failed: {results.get('error', 'Unknown error')}",
                "log": results.get('log', 'No log available.')
            }

        self.session_state.cello_results = results

        return {
            "success": True,
            "library_id": library_manager.current_library_id,
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
                "description": "List of part IDs to include in the custom UCF"
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
    
    def execute(self, selected_gates: List[str] = None, selected_parts: List[str] = None, modified_parts: Dict[str, Dict] = None, ucf_name: str = None) -> Dict[str, Any]:
        """Create a customized UCF file based on the currently selected library."""
        library_manager = self.session_state.get_library_manager()
        if not library_manager.current_library_id:
            return {"error": "No library selected as base for custom UCF. Please use 'select_library' first."}

        base_ucf_data = library_manager.get_ucf_data()
        if not base_ucf_data:
             return {"error": f"Could not retrieve base UCF data for library {library_manager.current_library_id}."}

        output_dir = "outputs/custom_ucf"
        custom_ucf_name = ucf_name or f"custom_{library_manager.current_library_id}.UCF.json"

        try:
            custom_ucf_path = library_manager.create_custom_ucf(
                selected_gates=selected_gates,
                selected_parts=selected_parts,
                modified_parts=modified_parts,
                ucf_name=custom_ucf_name,
                output_dir=output_dir
            )

            if custom_ucf_path:
                self.session_state.custom_ucf_path = custom_ucf_path
                return {
                    "success": True,
                    "library_id_base": library_manager.current_library_id,
                    "custom_ucf_path": custom_ucf_path
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
        library_manager = self.session_state.get_library_manager()
        if not library_manager.current_library_id:
            return {"error": "No library selected as base for custom input sensors file. Please use 'select_library' first."}

        input_sensor_data = library_manager.get_input_sensor_data()
        if not input_sensor_data:
             return {"error": f"Could not retrieve input sensor data for library {library_manager.current_library_id}."}

        output_dir = "outputs/custom_sensors"
        custom_filename = output_filename or f"custom_{library_manager.current_library_id}.input.json"

        try:
            custom_file_path = library_manager.create_custom_input_sensors_file(
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
                    "library_id_base": library_manager.current_library_id,
                    "custom_input_sensors_path": custom_file_path
                }
            else:
                 return {"error": "Input sensors file customization process failed to return a path."}

        except Exception as e:
             logger.error(f"Error creating custom input sensors file: {e}", exc_info=True)
             return {"error": f"Error creating custom input sensors file: {str(e)}"}

class PredictPromoterStrengthTool(Tool):
    name = "predict_promoter_strength"
    description = "Predict the strength of a promoter sequence."
    parameters = {
        "type": "object",
        "properties": {
            "sequence": {
                "type": "string",
                "description": "DNA sequence of the promoter"
            }
        },
        "required": ["sequence"]
    }
    
    def execute(self, sequence: str) -> Dict[str, Any]:
        """Predict the strength of a promoter sequence."""
        try:
            promoter_optimizer = PromoterOptimizer()
            result = promoter_optimizer.predict_strength(sequence)
            return {
                "sequence": sequence,
                "predicted_strength": result["strength"],
                "confidence": result.get("confidence", None)
            }
        except Exception as e:
            return {"error": f"Error predicting promoter strength: {str(e)}"}

class OptimizePromoterTool(Tool):
    name = "optimize_promoter"
    description = "Optimize a promoter to reach a target strength."
    parameters = {
        "type": "object",
        "properties": {
            "seed_sequence": {
                "type": "string",
                "description": "Starting sequence for optimization"
            },
            "target_strength": {
                "type": "number",
                "description": "Desired promoter strength"
            },
            "iterations": {
                "type": "integer",
                "description": "Number of optimization iterations"
            }
        },
        "required": ["seed_sequence", "target_strength"]
    }
    
    def execute(self, seed_sequence: str, target_strength: float, iterations: int = 100) -> Dict[str, Any]:
        """Optimize a promoter to reach a target strength."""
        try:
            promoter_optimizer = PromoterOptimizer()
            result = promoter_optimizer.optimize_promoter(
                seed_sequence=seed_sequence,
                target_strength=target_strength,
                iterations=iterations
            )
            return {
                "original_sequence": seed_sequence,
                "optimized_sequence": result["sequence"],
                "original_strength": result["original_strength"],
                "final_strength": result["final_strength"],
                "iterations_performed": result["iterations"]
            }
        except Exception as e:
            return {"error": f"Error optimizing promoter: {str(e)}"}

class GeneratePromotersTool(Tool):
    name = "generate_promoters"
    description = "Generate novel promoter sequences with optional strength filtering."
    parameters = {
        "type": "object",
        "properties": {
            "count": {
                "type": "integer",
                "description": "Number of promoters to generate"
            },
            "min_strength": {
                "type": "number",
                "description": "Minimum acceptable strength (optional)"
            },
            "max_strength": {
                "type": "number",
                "description": "Maximum acceptable strength (optional)"
            }
        },
        "required": ["count"]
    }
    
    def execute(self, count: int, min_strength: float = None, max_strength: float = None) -> Dict[str, Any]:
        """Generate novel promoter sequences with optional strength filtering."""
        try:
            deepseed = DeepSeedIntegration()
            promoters = deepseed.generate_promoters(
                count=count,
                min_strength=min_strength,
                max_strength=max_strength
            )
            return {
                "promoters": [
                    {
                        "sequence": p["sequence"],
                        "predicted_strength": p["strength"]
                    }
                    for p in promoters
                ],
                "count": len(promoters)
            }
        except Exception as e:
            return {"error": f"Error generating promoters: {str(e)}"}

class OptimizeBindingSiteTool(Tool):
    name = "optimize_binding_site"
    description = "Optimize a repressor binding site for target repression level."
    parameters = {
        "type": "object",
        "properties": {
            "repressor_id": {
                "type": "string",
                "description": "ID of the repressor protein"
            },
            "starting_site": {
                "type": "string",
                "description": "Starting binding site sequence"
            },
            "target_repression": {
                "type": "number",
                "description": "Desired repression level (0-1)"
            }
        },
        "required": ["repressor_id", "starting_site", "target_repression"]
    }
    
    def execute(self, repressor_id: str, starting_site: str, target_repression: float) -> Dict[str, Any]:
        """Optimize a repressor binding site for target repression level."""
        try:
            repressor_optimizer = RepressorOptimizer()
            result = repressor_optimizer.optimize_binding_site(
                repressor_id=repressor_id,
                starting_site=starting_site,
                target_repression=target_repression
            )
            return {
                "original_site": starting_site,
                "optimized_site": result["sequence"],
                "repressor_id": repressor_id,
                "original_repression": result["original_repression"],
                "final_repression": result["final_repression"]
            }
        except Exception as e:
            return {"error": f"Error optimizing binding site: {str(e)}"}

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
        from src.tools.cello_integration import CelloIntegration
        
        # Initialize Cello integration
        cello = CelloIntegration()
        
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

# Update the TOOL_REGISTRY to include all the new tools
TOOL_REGISTRY: Dict[str, Type[Tool]] = {
    ListPromotersTool.name: ListPromotersTool,
    DescribeAvailableLibrariesTool.name: DescribeAvailableLibrariesTool,
    SelectLibraryTool.name: SelectLibraryTool,
    ListRepressorsTool.name: ListRepressorsTool,
    ListInputSensorsTool.name: ListInputSensorsTool,
    GetDnaPartByNameTool.name: GetDnaPartByNameTool,
    ListTerminatorsTool.name: ListTerminatorsTool,
    DesignWithCelloTool.name: DesignWithCelloTool,
    CreateCustomUcfTool.name: CreateCustomUcfTool,
    CreateCustomInputSensorsFileTool.name: CreateCustomInputSensorsFileTool,
    PredictPromoterStrengthTool.name: PredictPromoterStrengthTool,
    OptimizePromoterTool.name: OptimizePromoterTool,
    GeneratePromotersTool.name: GeneratePromotersTool,
    OptimizeBindingSiteTool.name: OptimizeBindingSiteTool,
    EvaluateCircuitPerformanceTool.name: EvaluateCircuitPerformanceTool,
}

# Generate OpenAI function schemas from tools
tool_functions = [
    convert_to_openai_function(ReadFileTool()),
    *[tool_class.get_openai_schema() for tool_class in TOOL_REGISTRY.values()]
]

class ToolIntegration:
    def __init__(self, session_state: SessionState):
        self.session_state = session_state
        self.tools = {
            tool_name: tool_class(session_state) 
            for tool_name, tool_class in TOOL_REGISTRY.items()
        }

    def call_tool_function(self, function_name, function_args):
        """
        Call a tool function with the provided arguments.
        
        Args:
            function_name: Name of the function to call
            function_args: Arguments for the function
            
        Returns:
            Result of the function call
        """
        # Handle ReadFileTool separately as it's from langchain
        if function_name == "read_file":
            return ReadFileTool().run(function_args["file_path"])
        
        # Use the tool from the registry if available
        if function_name in self.tools:
            return self.tools[function_name].execute(**function_args)
        
        # If no tool found, return error
        return {"error": f"No such function: {function_name}"}
        