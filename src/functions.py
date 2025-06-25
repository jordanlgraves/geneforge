# tools/functions.py

import os
from typing import Dict, List, Any, ClassVar, Optional
import src.library.part_library_customizer as part_library_customizer
import logging
from src.session_state import SessionState
import traceback
import logging
import inspect


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
    description = "Return a description of the available libraries which includes the header which contains the organism name among other details, the UCF path, the input sensor file path and the output file path."
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
                "message": f"Session selected library {library_id}",
            }
        else:
            available = list(self.session_state.get_library_manager().get_available_libraries().keys())
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
                "matched_libraries": self.session_state.get_library_manager().get_available_libraries().keys()
            }
            return response
        else:
            available = list(self.session_state.get_library_manager().get_available_libraries().keys())
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

        # Use active context paths (handles base, custom, or draft automatically)
        ucf_path = library_manager.get_active_ucf_path()
        input_path = library_manager.get_active_input_path()
        output_path = library_manager.get_active_output_path()
        
        # Get context info for logging
        context_info = library_manager.get_active_context_info()
        logger.info(f"Using library context: {context_info}")

        if not ucf_path or not input_path:
             return {"error": f"Missing UCF ({ucf_path}) or Input ({input_path}) file path for library {library_manager.current_library_id}."}

        from src.integrations.cello_integration import CelloIntegration

        # Pass the library_manager from the session state
        cello = CelloIntegration(
            cello_config=config or {},
            library_manager=library_manager
        )

        output_dir = f"outputs/cello_run_{library_manager.current_library_id}"
    
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
            "library_id": library_manager.current_library_id,
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
                library_manager.load_custom_ucf(custom_ucf_path)
                self.session_state.custom_ucf_path = custom_ucf_path
                return {
                    "success": True,
                    "library_id": library_manager.current_library_id,
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
#  ProD helper base (lazy session-level ProDIntegration)
# ---------------------------------------------------------------------------

from src.integrations.pro_d_integration import ProDIntegration, class_to_rpu, extract_id_ecoli_spacer


class _ProDToolBase(Tool):
    """Mixin that provides a per-session ProDIntegration instance."""

    def _get_prod(self) -> ProDIntegration:
        if not hasattr(self.session_state, "prod_integration"):
            setattr(self.session_state, "prod_integration", ProDIntegration())
        return getattr(self.session_state, "prod_integration")



# ---------------------------------------------------------------------------
#  NEW Promoter library generation tools (split from deprecated GeneratePromoterLibraryWithProDTool)
# ---------------------------------------------------------------------------

class _ProDPromoterToolBase(_ProDToolBase):
    """Helper mix-in providing common promoter-centric utilities."""

    _dna_chars: ClassVar[set[str]] = set("ATGCRYSWKMBDHVNatgcryswkmbdhvn")

    def _resolve_promoter_sequence(self, promoter: str, file_type: str = "ucf") -> Optional[str]:
        """Return full promoter DNA sequence from ID or sequence.

        If *promoter* already looks like DNA (≥17 bp consisting only of IUPAC
        characters) it is returned (upper-cased). Otherwise it is treated as a
        part ID and resolved via `LibraryManager` using *file_type* to select
        the JSON (ucf / input / output).
        """
        if set(promoter).issubset(self._dna_chars) and len(promoter) >= 17:
            return promoter.upper()

        lm = self.session_state.get_library_manager()
        if not lm.current_library_id:
            return None
        if file_type == "ucf":
            lib_data = lm.get_ucf_data()
        elif file_type == "input":
            lib_data = lm.get_input_sensor_data()
        else:
            lib_data = lm.get_output_device_data()
        import src.library.part_library_customizer as plc
        part = plc.get_part_by_name(lib_data, promoter)
        if not part:
            return None
        return part.get("dnasequence") or part.get("sequence")
    

    # ------------------------------------------------------------------
    #  Helper to auto-save variants into a custom UCF
    # ------------------------------------------------------------------

    def _auto_save_variants(
        self,
        parent_promoter: str | None,
        upstream: str,
        downstream: str,
        variants_dict: dict,
        save_to_library: str | None,
    ) -> dict:
        """Write the generated variants to a new custom UCF when requested.

        Currently only the *ucf* target is implemented.  Returns a dict that
        will be merged into the tool's success payload.
        """

        if not save_to_library:
            return {}

        if save_to_library != "ucf":
            return {"warning": f"Automatic save for '{save_to_library}' not yet supported."}

        if not parent_promoter:
            return {"error": "Parameter 'parent_promoter' is required when save_to_library is set."}

        lm = self.session_state.get_library_manager()
        if not lm.current_library_id:
            return {"error": "No library selected. Use select_library first."}

        # Build list of variant dicts with spacer & ymax
        variants_list = []
        for spacer_seq, props in variants_dict.items():
            variants_list.append({
                "spacer": spacer_seq,
                "ymax": props.get("ymax") or props.get("strength") or 1.0,
            })

        try:
            added_items = lm.add_promoter_variants(parent_promoter, variants_list)
            return {"draft_ucf_pending": True, "variants_saved": added_items}
        except Exception as exc:
            return {"error": str(exc)}

    @staticmethod
    def _split_flanks(promoter_seq: str, spacer: str) -> tuple[str, str]:
        """Return (upstream, downstream) regions flanking *spacer* inside *promoter_seq*."""
        idx = promoter_seq.find(spacer)
        if idx == -1:
            return "", ""
        return promoter_seq[:idx], promoter_seq[idx + 17:]

# ---------------------------------------------------------------------------
#  EstimatePromoterStrengthWithProD
# ---------------------------------------------------------------------------


class EstimatePromoterStrengthWithProDTool(_ProDToolBase):
    name = "estimate_promoter_strength_with_pro_d"
    description = "Return ProD class and calibrated ymax for a promoter ID or DNA sequence. If an ID is given the currently selected library is searched."
    parameters = {
        "type": "object",
        "properties": {
            "promoter": {"type": "string", "description": "Promoter name/id from the selected library or full DNA sequence or 17-bp spacer."},
            "file_type": {"type": "string", "enum": ["ucf", "input", "output"], "description": "Which library JSON to search when an ID is supplied", "default": "ucf"}
        },
        "required": ["promoter"]
    }

    def execute(self, promoter: str, file_type: str = "ucf") -> Dict[str, Any]:
        prod = self._get_prod()

        # Determine if string looks like DNA
        dna_chars = set("ATGCRYSWKMBDHVNatgcryswkmbdhvn")
        is_dna = set(promoter).issubset(dna_chars) and len(promoter) >= 17

        sequence = None
        library_manager = self.session_state.get_library_manager()

        if is_dna:
            sequence = promoter.upper()
        else:
            # treat as part ID
            if not library_manager.current_library_id:
                return {"error": "No library selected. Use select_library first."}

            if file_type == "ucf":
                lib_data = library_manager.get_ucf_data()
            elif file_type == "input":
                lib_data = library_manager.get_input_sensor_data()
            else:
                lib_data = library_manager.get_output_device_data()

            import src.library.part_library_customizer as plc
            part = plc.get_part_by_name(lib_data, promoter)
            if not part:
                return {"error": f"Promoter ID '{promoter}' not found in {file_type} file."}
            sequence = part.get("dnasequence") or part.get("sequence")
            if not sequence:
                return {"error": f"Promoter part '{promoter}' lacks dna sequence field."}

        # Evaluate via ProD
        result = prod.evaluate_spacers([sequence])
        if not result:
            return {"error": "ProD evaluation returned no result."}

        cls_val = int(result[sequence])
        ymax = result.get(sequence + "_ymax", class_to_rpu(cls_val))
        spacer = extract_id_ecoli_spacer(sequence)

        return {
            "promoter_sequence": sequence,
            "spacer": spacer,
            "class": cls_val,
            "ymax": ymax,
            "success": True
        }


class GetSpacerFromPromoterTool(_ProDPromoterToolBase):
    name = "get_spacer_from_promoter"
    description = "Extract the 17-bp spacer from a full promoter sequence or part id/name from the selected library."
    parameters = {
        "type": "object",
        "properties": {"promoter": {"type": "string", "description": "Full promoter sequence or part id/name from the selected library."},
                       "file_type": {"type": "string", "enum": ["ucf", "input", "output"], "default": "ucf"}},
        "required": ["promoter"]
    }
    
    def execute(self, promoter: str, file_type: str = "ucf") -> Dict[str, Any]:
        prod = self._get_prod()

        # if promoter is a part id/name, resolve the sequence
        sequence = self._resolve_promoter_sequence(promoter, file_type)
        if not sequence:
            return {"error": f"Error in promoter id/name or sequence: '{promoter}'."}
        
        spacer = prod.extract_spacer(sequence)
        if spacer:
            return {"spacer": spacer, "success": True}

        else:
            return {"error": "Could not extract spacer from the provided promoter sequence."}



class GeneratePromoterLibraryFromSpacerTool(_ProDPromoterToolBase):
    name = "generate_library_from_spacer"
    description = (
        "Use ProD to generate promoter spacer variants from a **17-nt degenerate spacer blueprint**. "
        "The `blueprint` string *must be exactly 17 nucleotides long* **and must contain at least one degenerate IUPAC code** (e.g. N, R, Y, S, K, M, W, B, D, H or V); supplying a fully specified 17-mer will raise an error. "
        "If `parent_promoter` is supplied, the tool stitches every newly generated spacer between the upstream and downstream flanks of that promoter and returns complete promoter sequences together with calibrated `ymax` values."
    )
    parameters = {
        "type": "object",
        "properties": {
            "blueprint": {"type": "string", "description": "Degenerate 17-bp spacer (must contain ≥1 IUPAC ambiguity code)."},
            "desired_strengths": {"type": "array", "items": {"type": "integer"}, "description": "Strength classes ranging from 0 to 10."},
            "sequences_per_class": {"type": "integer", "default": 5},
            "parent_promoter": {"type": "string", "description": "Optional promoter ID or sequence providing flanks."},
            "file_type": {"type": "string", "enum": ["ucf", "input", "output"], "default": "ucf"},
            "save_to_library": {"type": "string", "enum": ["ucf", "input", "output"], "description": "Automatically write the generated variants to the selected library (valid only for 'ucf' file type for now)."}
        },
        "required": ["blueprint"],
    }

    def execute(
        self,
        blueprint: str,
        desired_strengths: List[int] | None = None,
        sequences_per_class: int = 5,
        parent_promoter: str | None = None,
        file_type: str = "ucf",
        save_to_library: str | None = None,
    ) -> Dict[str, Any]:
        prod = self._get_prod()
        if len(blueprint) != 17:
            return {"error": "Blueprint must be exactly 17 bp."}

        upstream = downstream = None
        if parent_promoter:
            parent_seq = self._resolve_promoter_sequence(parent_promoter, file_type)
            if not parent_seq:
                return {"error": f"Could not resolve parent promoter '{parent_promoter}'."}
            from src.integrations.pro_d_integration import extract_id_ecoli_spacer
            spacer_parent = extract_id_ecoli_spacer(parent_seq)
            if spacer_parent and spacer_parent in parent_seq:
                upstream, downstream = self._split_flanks(parent_seq, spacer_parent)

        try:
            variants_dict = prod.generate_library(
                blueprint,
                desired_strengths=desired_strengths,
                library_size=sequences_per_class,
            )
        except Exception as exc:
            return {"error": f"Error generating promoter library: {exc}"}

        if upstream is not None and downstream is not None:
            for spacer_seq, props in variants_dict.items():
                props["promoter_sequence"] = f"{upstream.upper()}{spacer_seq}{downstream.upper()}"

        return {
            "blueprint": blueprint,
            "variants": [{"spacer": s, **p} for s, p in variants_dict.items()],
            **(self._auto_save_variants(parent_promoter, upstream, downstream, variants_dict, save_to_library) if save_to_library else {}),
            "success": True,
        }



class GeneratePromoterLibraryFromPromoterTool(_ProDPromoterToolBase):
    name = "generate_library_from_promoter"
    description = (
        "Use ProD to create spacer variants by mutating an existing promoter. "
        "`mutable_positions` must be a dictionary whose *keys are spacer indices 0–16* (0 is the first base) and whose *values are IUPAC ambiguity codes* such as N, R, Y, S, K, M, W, B, D, H or V. "
        "If `promoter` is supplied as a part name/id from the selected library, `mutable_positions` is *required* so that at least one degenerate base is introduced; without it the blueprint would be non-degenerate and ProD will abort. "
        "If `promoter` is supplied as a full DNA sequence and its spacer already contains ≥ 1 ambiguity code, `mutable_positions` may be omitted. "
        "The tool returns a list of variants with their spacer sequence, predicted class/strength, calibrated `ymax`, and full promoter sequence (flanks from the parent promoter)."
    )
    parameters = {
        "type": "object",
        "properties": {
            "promoter": {"type": "string", "description": "Promoter ID/name from the selected library or a full promoter sequence."},
            "mutable_positions": {"type": "object", "description": "Dict spacer_index to IUPAC ambiguity code (0-16)."},
            "desired_strengths": {"type": "array", "items": {"type": "integer"}, "description": "Strength classes (0-10)."},
            "sequences_per_class": {"type": "integer", "default": 5},
            "file_type": {"type": "string", "enum": ["ucf", "input", "output"], "default": "ucf"},
            "save_to_library": {"type": "string", "enum": ["ucf", "input", "output"], "description": "Automatically write the generated variants to a custom library file (valid only for 'ucf' for now)."},
        },
        "required": ["promoter"],
    }

    def execute(
        self,
        promoter: str,
        mutable_positions: Dict[str, str] | None = None,
        desired_strengths: List[int] | None = None,
        sequences_per_class: int = 5,
        file_type: str = "ucf",
        save_to_library: str | None = None,
    ) -> Dict[str, Any]:
        from src.integrations.pro_d_integration import extract_id_ecoli_spacer
        prod = self._get_prod()

        parent_seq = self._resolve_promoter_sequence(promoter, file_type)
        if not parent_seq:
            return {"error": f"Could not resolve promoter '{promoter}' as a DNA sequence or a name/id."}

        spacer_parent = extract_id_ecoli_spacer(parent_seq)
        if not spacer_parent:
            return {"error": f"Failed to extract 17-bp spacer from promoter sequence: {parent_seq}."}

        spacer_chars = list(spacer_parent.upper())

        # If mutable_positions is provided, mutate the spacer
        if mutable_positions:       
            for pos_str, iupac in mutable_positions.items():
                try:
                    idx = int(pos_str)
                except ValueError:
                    return {"error": f"Index '{pos_str}' is not an integer."}
                if idx < 0 or idx > 16:
                    return {"error": "Mutable indices must be between 0 and 16."}
                spacer_chars[idx] = iupac.upper()
        else:
            # If mutable_positions is not provided, check that the spacer contains at least one IUPAC ambiguity code
            if not any(c in "N" for c in spacer_chars):
                return {"error": """The algorithm requires that the spacer sequence contain at least one IUPAC ambiguity code in order to \
                        determine the blueprint sequence. Please provide `mutable_positions` to mutate the spacer or provide `promoter` \
                        as DNA sequence containing at least one IUPAC ambiguity code within a spacer region."""}

        blueprint = "".join(spacer_chars)

        try:
            variants_dict = prod.generate_library(
                blueprint,
                desired_strengths=desired_strengths,
                library_size=sequences_per_class,
            )
            if "error" in variants_dict:
                return {"error": variants_dict["error"]}
        except Exception as exc:
            return {"error": f"Error generating promoter library: {exc}"}

        upstream, downstream = self._split_flanks(parent_seq, spacer_parent)
        for spacer_seq, props in variants_dict.items():
            props["promoter_sequence"] = f"{upstream.upper()}{spacer_seq}{downstream.upper()}"

        return {
            "blueprint": blueprint,
            "parent_promoter": promoter,
            "variants": [{"spacer": s, **p} for s, p in variants_dict.items()],
            **(self._auto_save_variants(promoter, upstream, downstream, variants_dict, save_to_library) if save_to_library else {}),
            "success": True,
        }

# ---------------------------------------------------------------------------
#  PatchUcfWithPromotersTool – wraps LibraryManager.create_custom_ucf
# ---------------------------------------------------------------------------

class PatchUcfWithPromotersTool(Tool):
    name = "patch_ucf_with_promoters"
    description = (
        "Duplicate or replace a promoter part in the current library UCF with supplied spacer variants (each spacer must be 17 nt) and their calibrated `ymax` values. "
        "Returns the file path of the newly written custom UCF."
    )
    parameters = {
        "type": "object",
        "properties": {
            "parent_promoter_id": {"type": "string", "description": "ID of the promoter part to duplicate / replace."},
            "variants": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "spacer": {"type": "string"},
                        "ymax": {"type": "number"}
                    },
                    "required": ["spacer", "ymax"]
                },
                "description": "List of new spacer variants with calibrated ymax values."
            },
            "replace_parent": {"type": "boolean", "default": False, "description": "If true, parent promoter is replaced; otherwise duplicated with _varN suffix."}
        },
        "required": ["parent_promoter_id", "variants"]
    }

    def execute(self, parent_promoter_id: str, variants: List[Dict[str, Any]], replace_parent: bool = False):
        import copy
        from src.integrations.pro_d_integration import extract_id_ecoli_spacer
        import src.library.part_library_customizer as plc

        lm = self.session_state.get_library_manager()
        if not lm.current_library_id:
            return {"error": "No library selected. Use select_library first."}

        base_ucf = lm.get_ucf_data()
        if not base_ucf:
            return {"error": "Failed to retrieve current UCF data."}
        
        parent_part = plc.get_part_by_name(base_ucf, parent_promoter_id)
        if not parent_part:
            return {"error": f"Parent promoter {parent_promoter_id} not found in UCF."}

        parent_seq = parent_part.get("dnasequence") or parent_part.get("sequence")
        spacer_parent = extract_id_ecoli_spacer(parent_seq)
        if not spacer_parent:
            return {"error": "Could not extract spacer from parent promoter sequence."}

        idx = parent_seq.find(spacer_parent)
        upstream = parent_seq[:idx]
        downstream = parent_seq[idx+17:]

        modified_parts = {}

        for i, var in enumerate(variants):
            spacer = var.get("spacer")
            ymax = var.get("ymax")
            if not spacer or len(spacer) != 17:
                continue
            new_seq = f'{upstream.upper()}{spacer}{downstream.upper()}'
            new_part = copy.deepcopy(parent_part)
            new_id = parent_promoter_id if (replace_parent and i == 0) else f"{parent_promoter_id}_var{i+1}"
            new_part["name"] = new_id
            if "dnasequence" in new_part:
                new_part["dnasequence"] = new_seq
            else:
                new_part["sequence"] = new_seq

            # Update ymax parameter
            updated = False
            for p in new_part.get("parameters", []):
                if p.get("parameter", "").lower() in ("ymax", "y_max"):
                    p["value"] = ymax
                    updated = True
                    break
            if not updated:
                new_part.setdefault("parameters", []).append({
                    "parameter": "ymax",
                    "value": ymax
                })
            modified_parts[new_id] = new_part

        # Call LibraryManager to write custom UCF
        try:
            path = lm.create_custom_ucf(
                selected_gates=None,
                selected_parts=list(modified_parts.keys()),
                modified_parts=list(modified_parts.values()),
                ucf_name=f"custom_{lm.current_library_id}_{parent_promoter_id}_variants.UCF.json",
            )
            self.session_state.custom_ucf_path = path
            return {"success": True, "custom_ucf_path": path, "n_variants": len(modified_parts)}
        except Exception as e:
            if DEBUG_MODE:
                traceback.print_exc()
                raise e
            else:
                return {"error": f"Failed to patch UCF: {e}"}



# RBS Calculator Tools
class PredictInitiationRateWithRbsCalculatorTool(Tool):
    name = "predict_initiation_rate_with_rbs_calculator"
    description = (
        "Predict translation initiation metrics (ΔG_total, expression level) for an "
        "mRNA sequence using the Salis-lab RBS Calculator."
    )
    parameters = {
        "type": "object",
        "properties": {
            "mrna_sequence": {
                "type": "string",
                "description": "Full mRNA (or DNA) sequence containing at least one start codon.",
            },
            "start_range": {
                "type": "array",
                "items": {"type": "integer"},
                "description": "Optional [start, end] indices delimiting the scan window for start codons (0-based).",
            },
            "name": {"type": "string", "description": "Optional identifier for the sequence."},
            "verbose": {"type": "boolean", "description": "Set to true to print the legacy calculator output."},
        },
        "required": ["mrna_sequence"],
    }

    def execute(
        self,
        mrna_sequence: str,
        start_range: Optional[list] = None,
        name: Optional[str] = None,
        verbose: bool = False,
    ) -> Dict[str, Any]:
        # RBS Calculator integration
        from src.integrations.rbs_calculator_integration import RBSCalculatorIntegration

        # Convert start_range to tuple[int, int] if provided.
        sr_tuple = tuple(start_range) if start_range else None  # type: ignore[arg-type]
        return RBSCalculatorIntegration.predict_initiation_rate(
            mrna_sequence=mrna_sequence,
            start_range=sr_tuple,  # type: ignore[arg-type]
            name=name,
            verbose=verbose,
        )


class DesignRbsWithRbsCalculatorTool(Tool):
    name = "design_rbs_with_rbs_calculator"
    description = (
        "Design a synthetic ribosome-binding site achieving a desired translation initiation rate "
        "or ΔG_total using the Salis-lab Monte Carlo optimiser."
    )
    parameters = {
        "type": "object",
        "properties": {
            "pre_sequence": {"type": "string", "description": "Sequence upstream of the RBS (5′ UTR)."},
            "post_sequence": {"type": "string", "description": "Sequence starting with the start codon and into the CDS."},
            "target_tir": {"type": "number", "description": "Desired translation initiation rate (arbitrary units)."},
            "target_delta_g": {"type": "number", "description": "Desired ΔG_total (kcal/mol)."},
            "max_iterations": {"type": "integer", "description": "Maximum optimisation iterations.", "default": 10000},
            "verbose": {"type": "boolean", "description": "Return verbose legacy output."},
        },
        "required": ["pre_sequence", "post_sequence"],
    }

    def execute(
        self,
        pre_sequence: str,
        post_sequence: str,
        target_tir: Optional[float] = None,
        target_delta_g: Optional[float] = None,
        max_iterations: int = 10000,
        verbose: bool = False,
    ) -> Dict[str, Any]:
        # RBS Calculator integration
        from src.integrations.rbs_calculator_integration import RBSCalculatorIntegration

        return RBSCalculatorIntegration.design_rbs(
            pre_sequence=pre_sequence,
            post_sequence=post_sequence,
            target_tir=target_tir,
            target_delta_g=target_delta_g,
            max_iterations=max_iterations,
            verbose=verbose,
        )


class AddPromoterVariantTool(Tool):
    name = "add_promoter_variant"
    description = (
        "Create a new promoter variant by copying an existing promoter (and all dependent structures/gates/models) and replacing its 17-bp spacer with a new 17-bp spacer sequence. "
        "`ymax` (calibrated RPU) is mandatory so that associated models remain consistent."
    )
    parameters = {
        "type": "object",
        "properties": {
            "parent_promoter_id": {"type": "string", "description": "ID of the reference promoter part from the selected library."},
            "spacer_sequence": {"type": "string", "description": "17-bp spacer sequence to use in replacement of the 17-bp spacer sequence of the parent promoter"},
            "ymax": {"type": "number", "description": "Calibrated RPU (ymax) for the new promoter. Can be found in the output from the ProD tool."},
            "new_promoter_id": {"type": "string", "description": "Optional name for the new promoter. Alphanumeric characters only, no spaces or special characters."},
        },
        "required": ["parent_promoter_id", "spacer_sequence", "ymax"],
    }

    def execute(
        self,
        parent_promoter_id: str,
        spacer_sequence: str,
        ymax: float,
        new_promoter_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        import copy
        from src.integrations.pro_d_integration import extract_id_ecoli_spacer
        import src.library.part_library_customizer as plc
        

        lm = self.session_state.get_library_manager()
        if not lm.current_library_id:
            return {"error": "No library selected. Use select_library first."}

        ucf_data = lm.get_ucf_data()
        if not ucf_data:
            return {"error": "Could not load UCF data."}

        parent_part = plc.get_part_by_name(ucf_data, parent_promoter_id)
        if not parent_part:
            return {"error": f"Parent promoter {parent_promoter_id} not found."}

        parent_seq = parent_part.get("dnasequence") or parent_part.get("sequence")
        spacer_parent = extract_id_ecoli_spacer(parent_seq)
        if not spacer_parent:
            return {"error": "Unable to extract spacer from parent promoter."}
        if len(spacer_sequence) != 17:
            return {"error": "Provided spacer must be 17 bp."}

        # Build new promoter sequence
        idx = parent_seq.find(spacer_parent)
        new_sequence = f"{parent_seq[:idx].upper()}{spacer_sequence.upper()}{parent_seq[idx+17:].upper()}"

        # Determine new promoter id
        if not new_promoter_id:
            base = parent_promoter_id.rstrip("\n")
            new_promoter_id = f"{base}var1"
            i = 1
            while plc.get_part_by_name(ucf_data, new_promoter_id):
                i += 1
                new_promoter_id = f"{base}var{i}"
        else: # Check that new_promoter_id is alphanumeric only
            if not new_promoter_id.isalnum():
                return {"error": "new_promoter_id must be alphanumeric only."}
        
        # Duplicate dependencies
        new_items, gate_map = plc.duplicate_promoter_dependencies(
            ucf_data, parent_promoter_id, new_promoter_id, new_sequence, ymax
        )

        # Update ymax inside associated models
        for item in new_items:
            if item.get("collection") == "models":
                # update / insert parameter
                updated = False
                for p in item.get("parameters", []):
                    if p.get("name").lower() in ("ymax", "y_max"):
                        p["value"] = ymax
                        updated = True
                        break
                if not updated:
                    item.setdefault("parameters", []).append({"name": "ymax", "value": ymax})

        # Assemble new custom UCF
        try:
            path = lm.create_custom_ucf(
                selected_gates=None,
                selected_parts=None,
                modified_parts=None,
                new_parts=new_items,
                ucf_name=f"custom_{lm.current_library_id}_{new_promoter_id}.UCF.json",
            )
            lm.load_custom_ucf(path)
            self.session_state.custom_ucf_path = path
            return {
                "success": True,
                # "custom_ucf_path": path,
                "new_promoter_id": new_promoter_id,
                "added_items": new_items,
            }
        except Exception as exc:
            if DEBUG_MODE:
                traceback.print_exc()
            return {"error": str(exc)}


class RemovePromoterTool(Tool):
    name = "remove_promoter"
    description = "Remove a promoter part and all dependent structures, gates and models from the current UCF and write a custom UCF file."
    parameters = {
        "type": "object",
        "properties": {
            "promoter_id": {"type": "string", "description": "ID of the promoter to remove."},
        },
        "required": ["promoter_id"],
    }

    def execute(self, promoter_id: str) -> Dict[str, Any]:
        import src.library.part_library_customizer as plc
        import json
        import os
        lm = self.session_state.get_library_manager()
        if not lm.current_library_id:
            return {"error": "No library selected. Use select_library first."}

        ucf = lm.get_ucf_data()
        if not ucf:
            return {"error": "Could not load UCF data."}

        if not plc.get_part_by_name(ucf, promoter_id):
            return {"error": f"Promoter {promoter_id} not found."}

        # Use the correct utility function to remove the part and its dependencies
        new_ucf_data, summary = plc.remove_part_and_dependencies(ucf, promoter_id)

        # Write the new custom UCF to a file
        try:
            output_dir = "outputs/custom_ucf"
            os.makedirs(output_dir, exist_ok=True)
            ucf_name = f"custom_{lm.current_library_id}_without_{promoter_id}.UCF.json"
            path = os.path.join(output_dir, ucf_name)

            with open(path, "w") as f:
                json.dump(new_ucf_data, f, indent=2)

            # Update the library manager's state
            lm.load_custom_ucf(path)
            self.session_state.custom_ucf_path = path

            return {
                "success": True,
                # "custom_ucf_path": path,
                "removed_items_summary": summary,
            }
        except Exception as exc:
            if DEBUG_MODE:
                traceback.print_exc()
            return {"error": str(exc)}

# ---------------------------------------------------------------------------
#  SynBioHub tools
# ---------------------------------------------------------------------------

class SynBioHubSearchTool(Tool):
    name = "synbiohub_search"
    description = (
        "Search the SynBioHub public repository (https://synbiohub.org) for SBOL objects such as parts, collections, or entire designs. "
        "Provide exactly the key–value query string that would follow the '/search/' endpoint (e.g. 'objectType=ComponentDefinition&name=pLac'). "
        "This helper is read-only and returns the raw JSON/XML text emitted by the server so that downstream code—or the LLM—can parse it."
        " Example: query='objectType=ComponentDefinition&dcterms:title=pTet&offset=0&limit=25'."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query path, e.g. 'objectType=ComponentDefinition&pLac'."},
            "offset": {"type": "integer", "description": "Result offset", "default": 0},
            "limit": {"type": "integer", "description": "Maximum results", "default": 20},
        },
        "required": ["query"],
    }

    def execute(self, query: str, offset: int = 0, limit: int = 20):
        sbh = self.session_state.get_synbiohub_client()
        try:
            text = sbh.search(query, offset=offset, limit=limit)
            return {"success": True, "raw": text}
        except Exception as exc:
            return {"error": str(exc)}


class SynBioHubDownloadPartTool(Tool):
    name = "synbiohub_download_part"
    description = (
        "Download a single SynBioHub object identified by its URI and return it in the requested format "
        "('sbol', 'fasta', 'gb', 'gff', 'metadata', or 'sbolnr'). The binary response is UTF-8-decoded and truncated to the first 5 kB so the assistant can preview it."
        " Example: uri='https://synbiohub.org/public/igem/BBa_R0010/1', format='gb'."
    )
    parameters = {
        "type": "object",
        "properties": {
            "uri": {"type": "string", "description": "Full URI of the SBH object."},
            "format": {"type": "string", "enum": ["sbol", "fasta", "gb", "gff", "metadata", "sbolnr"], "default": "sbol"},
        },
        "required": ["uri"],
    }

    def execute(self, uri: str, format: str = "sbol"):
        sbh = self.session_state.get_synbiohub_client()
        try:
            content = sbh.download_part(uri, fmt=format)
            return {
                "success": True,
                "format": format,
                "bytes": len(content),
                "content_base64": content.decode("utf-8", errors="ignore")[:5000],  # truncate
            }
        except Exception as exc:
            return {"error": str(exc)}


class SynBioHubSubmitTool(Tool):
    name = "synbiohub_submit"
    description = (
        "Upload an SBOL/GenBank/FASTA file—or a zip archive of multiple files—to SynBioHub as a new collection. "
        "Requires valid SynBioHub user credentials configured in the SessionState client. "
        "Use 'overwrite_merge' = 0 (keep), 1 (overwrite), 2 or 3 (merge) to control how existing records are handled. Returns the raw server response text."
        " Example: file_path='my_part.xml', submission_id='MyPart', version='1', name='My Test', description='Demo submission', overwrite_merge=0."
    )
    parameters = {
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "Path to file to upload."},
            "submission_id": {"type": "string", "description": "ID for the submission (alphanumeric & underscore)."},
            "version": {"type": "string", "description": "Version string (e.g. '1')."},
            "name": {"type": "string", "description": "Human-readable name."},
            "description": {"type": "string", "description": "Description of the submission."},
            "citations": {"type": "string", "description": "Comma-separated PubMed IDs", "default": ""},
            "overwrite_merge": {"type": "integer", "description": "0 keep, 1 overwrite, 2/3 merge", "default": 0},
        },
        "required": ["file_path", "submission_id", "version", "name", "description"],
    }

    def execute(self, file_path: str, submission_id: str, version: str, name: str, description: str, citations: str = "", overwrite_merge: int = 0):
        sbh = self.session_state.get_synbiohub_client()
        try:
            resp_text = sbh.submit(
                file_path=file_path,
                submission_id=submission_id,
                version=version,
                name=name,
                description=description,
                citations=citations,
                overwrite_merge=overwrite_merge,
            )
            return {"success": True, "response": resp_text}
        except Exception as exc:
            return {"error": str(exc)}

class SynBioHubSequenceSearchTool(Tool):
    name = "synbiohub_sequence_search"
    description = (
        "Run a sequence-similarity search against SynBioHub by supplying the full parameter string starting with 'sequence=' or 'globalsequence=' (e.g. 'globalsequence=ATGC...&similarity=0.9'). "
        "Maps directly to the '/search/' API and returns the raw tab-delimited text/JSON provided by the server. Example: search_params='globalsequence=ATGCGTACGTAGCTAG&id=0.9&maxaccepts=50'."
    )
    parameters = {
        "type": "object",
        "properties": {
            "search_params": {"type": "string", "description": "Key/value search parameters beginning with sequence= or globalsequence= ..."},
        },
        "required": ["search_params"],
    }

    def execute(self, search_params: str):
        sbh = self.session_state.get_synbiohub_client()
        try:
            out = sbh.sequence_search(search_params)
            return {"success": True, "raw": out}
        except Exception as exc:
            return {"error": str(exc)}


class SynBioHubGetRelatedTool(Tool):
    name = "synbiohub_get_related"
    description = (
        "Retrieve objects related to a given SynBioHub URI using the '/related/<relation>/' endpoint. "
        "Supported relations: 'uses' (components referenced by the design), 'twins' (alternate versions), and 'similar' (homologous parts). "
        "Returns the raw JSON payload from the server. Example: uri='https://synbiohub.org/public/igem/BBa_R0010/1', relation='twins'."
    )
    parameters = {
        "type": "object",
        "properties": {
            "uri": {"type": "string", "description": "Full URI of the SBH object."},
            "relation": {"type": "string", "enum": ["uses", "twins", "similar"], "description": "Type of relation to fetch."},
        },
        "required": ["uri", "relation"],
    }

    def execute(self, uri: str, relation: str):
        sbh = self.session_state.get_synbiohub_client()
        try:
            text = sbh.get_related(uri, relation)
            return {"success": True, "relation": relation, "raw": text}
        except Exception as exc:
            return {"error": str(exc)}

# ---------------------------------------------------------------------------
#  Scientific search & utility tools
# ---------------------------------------------------------------------------

class ScientificSearchTool(Tool):
    name = "scientific_search"
    description = "Search scientific literature (Semantic Scholar) and return up-to-date paper metadata."
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Free-text search string."},
            "max_results": {"type": "integer", "description": "Maximum number of results", "default": 5},
        },
        "required": ["query"],
    }

    def execute(self, query: str, max_results: int = 5):
        from src.integrations.scientific_search_integration import scientific_search
        try:
            papers = scientific_search(query, max_results=max_results)
            return {"success": True, "papers": papers}
        except Exception as exc:
            return {"error": str(exc)}


class ToolDocsQueryTool(Tool):
    name = "query_tool_docs"
    description = "Ask a question about a tool (e.g., 'cello', 'prod') and get an answer extracted from local documentation PDFs/texts."
    parameters = {
        "type": "object",
        "properties": {
            "tool_name": {"type": "string", "description": "Tool identifier (cello, prod, rbs_calculator, etc.) to provide context for the query."},
            "query": {"type": "string", "description": "Natural language question to ask."},
        },
        "required": ["tool_name", "query"],
    }

    def _get_all_doc_paths(self) -> List[str]:
        """Finds all available tool documentation files in the 'docs/tools' directory."""
        doc_dir = "docs/tools"
        supported_ext = (".pdf", ".md", ".txt")
        paths = []
        if not os.path.isdir(doc_dir):
            return []
        for filename in os.listdir(doc_dir):
            if filename.endswith(supported_ext):
                paths.append(os.path.join(doc_dir, filename))
        return paths

    def execute(self, tool_name: str, query: str):
        """Delegates Q&A to a single, dynamically-created OpenAI Assistant with all docs."""
        import os
        from openai import OpenAI

        client = OpenAI()

        # Use session_state to cache a single assistant for all tool docs
        cache_key = "tooldoc_assistant"
        if hasattr(self.session_state, cache_key):
            assistant_id = getattr(self.session_state, cache_key)
        else:
            doc_paths = self._get_all_doc_paths()
            if not doc_paths:
                return {"error": "No documentation files found in docs/tools/."}

            try:
                # 1. Create a single vector store for all tool docs
                vector_store = client.vector_stores.create(name="Tool Documentation Store")

                # 2. Upload all files and add them to the vector store
                file_streams = [open(path, "rb") for path in doc_paths]
                try:
                    file_batch = client.vector_stores.file_batches.upload_and_poll(
                        vector_store_id=vector_store.id, files=file_streams
                    )
                finally:
                    for f in file_streams:
                        f.close()
                
                if file_batch.status != 'completed':
                    return {"error": f"File upload failed with status: {file_batch.status}"}

                # 3. Create a single assistant for all docs
                assistant = client.beta.assistants.create(
                    name="Tool Documentation Assistant",
                    instructions="You are an expert Q&A bot. You answer questions about various software tools by consulting the documentation files provided to you. When answering, cite the relevant file.",
                    model="gpt-4o-mini",
                    tools=[{"type": "file_search"}],
                    tool_resources={"file_search": {"vector_store_ids": [vector_store.id]}},
                )
                assistant_id = assistant.id
                
                # Cache the single assistant for subsequent calls
                setattr(self.session_state, cache_key, assistant_id)

            except Exception as e:
                if DEBUG_MODE:
                    traceback.print_exc()
                return {"error": f"Failed to create OpenAI Assistant: {e}"}

        try:
            # Create a thread with the user's message
            thread = client.beta.threads.create(
                messages=[
                    {
                        "role": "user",
                        "content": f"Using the provided documents, please answer the following question about the '{tool_name}' tool: {query}",
                    }
                ]
            )

            # Run the assistant and poll for completion
            run = client.beta.threads.runs.create_and_poll(
                thread_id=thread.id,
                assistant_id=assistant_id,
            )

            if run.status == "completed":
                messages = client.beta.threads.messages.list(thread_id=thread.id)
                if messages.data and messages.data[0].role == 'assistant':
                    msg_content = messages.data[0].content[0]
                    if hasattr(msg_content, 'text'):
                        answer = msg_content.text.value
                        citations = []
                        if hasattr(msg_content.text, 'annotations'):
                            for ann in msg_content.text.annotations:
                                if getattr(ann, 'type', '') == 'file_citation':
                                    citations.append(getattr(ann.file_citation, 'file_id', ''))
                        return {"success": True, "answer": answer, "citations": citations}
                return {"error": "Assistant finished but returned no message."}
            else:
                return {"error": f"Assistant run failed with status: {run.status}, reason: {getattr(run.last_error, 'message', 'Unknown')}"}

        except Exception as e:
            if DEBUG_MODE:
                traceback.print_exc()
            return {"error": f"An error occurred during assistant execution: {e}"}


# ------------------- Small utility tools -----------------------------

class TranslateDnaTool(Tool):
    name = "translate_dna"
    description = "Translate a DNA sequence to protein using standard genetic code (frame 1 unless specified)."
    parameters = {
        "type": "object",
        "properties": {
            "seq_dna": {"type": "string", "description": "DNA sequence (A/T/C/G)."},
            "frame": {"type": "integer", "description": "Reading frame offset 0-2", "default": 0},
        },
        "required": ["seq_dna"],
    }

    def execute(self, seq_dna: str, frame: int = 0):
        try:
            from Bio.Seq import Seq  # type: ignore
            from Bio.SeqUtils import seq3
        except ImportError:
            return {"error": "Biopython not installed. Please add biopython to requirements."}

        seq = Seq(seq_dna.upper().replace("\n", "").replace(" ", ""))
        if frame not in (0, 1, 2):
            return {"error": "Frame must be 0, 1 or 2."}

        trimmed_len = (len(seq) - frame) // 3 * 3
        sub_seq = seq[frame : frame + trimmed_len]
        protein = sub_seq.translate(to_stop=False)
        return {"success": True, "protein": str(protein)}


class GcContentTool(Tool):
    name = "gc_content"
    description = "Calculate GC percentage of a sequence (optionally sliding window)."
    parameters = {
        "type": "object",
        "properties": {
            "seq": {"type": "string", "description": "DNA sequence."},
            "window": {"type": "integer", "description": "Window size for sliding calculation"},
        },
        "required": ["seq"],
    }

    def execute(self, seq: str, window: int | None = None):
        seq = seq.upper().replace("\n", "").replace(" ", "")
        if not seq:
            return {"error": "Sequence empty"}
        def gc(s):
            return round((s.count("G") + s.count("C")) / len(s) * 100, 2)
        if window and window > 0 and window < len(seq):
            values = [gc(seq[i:i+window]) for i in range(0, len(seq)-window+1)]
            return {"success": True, "window": window, "gc_values": values}
        else:
            return {"success": True, "gc_percent": gc(seq)}


        
# ---------------------------------------------------------------------------
#  CommitCustomLibraryTool – finalises draft UCF
# ---------------------------------------------------------------------------


class CommitCustomLibraryTool(Tool):
    name = "commit_custom_library"
    description = "Write the current draft UCF (if any) to disk, load it, and set it as the active library. Optionally specify the filename."
    parameters = {
        "type": "object",
        "properties": {
            "ucf_name": {"type": "string", "description": "Filename for the custom UCF (must end with .UCF.json)", "default": None},
        },
        "required": [],
    }

    def execute(self, ucf_name: str | None = None):
        lm = self.session_state.get_library_manager()
        try:
            path = lm.commit_draft_ucf(ucf_name)
            self.session_state.custom_ucf_path = path
            
            # Get updated context info
            context_info = lm.get_active_context_info()
            
            return {
                "success": True, 
                # "custom_ucf_path": path,
                "active_context": context_info,
                "message": f"Custom library committed and activated. Context: {context_info['context_type']}"
            }
        except Exception as exc:
            return {"error": str(exc)}


class GetCelloLibraryStatusTool(Tool):
    name = "get_cello_library_status"
    description = "Get the current Cello library status including active context, base library, and any pending drafts."
    parameters = {
        "type": "object",
        "properties": {},
        "required": [],
    }

    def execute(self):
        lm = self.session_state.get_library_manager()
        
        if not lm.current_library_id:
            return {"error": "No library selected"}
        
        context_info = lm.get_active_context_info()
        base_info = lm.get_current_library_info()
        
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
                "ucf_path": lm.get_active_ucf_path(),
                "input_path": lm.get_active_input_path(),
                "output_path": lm.get_active_output_path()
            }
        }


# ---------------------------------------------------------------------------
#  SBOL → SBML conversion & parameter template tools
# ---------------------------------------------------------------------------

class ConvertSbolToSbmlTool(Tool):
    name = "convert_sbol_to_sbml"
    description = (
        "Convert an SBOL design file to SBML, extract a parameter template (species/parameters → value/unit/source), "
        "store it in the session's DesignState, and return the template so the assistant can fill it."
    )
    parameters = {
        "type": "object",
        "properties": {
            "sbol_path": {"type": "string", "description": "Path to the SBOL (.xml/.rdf) file."},
        },
        "required": ["sbol_path"],
    }

    def execute(self, sbol_path: str) -> Dict[str, Any]:
        import os
        from pathlib import Path
        from datetime import datetime
        # 'outputs/cello_run/not_gate_design/output/main.v/main.v_ucf._pySBOl...'
        # ------------------------------------------------------------------
        #  1) Validate input & prepare paths
        # ------------------------------------------------------------------
        sbol_path_p = Path(sbol_path)
        if not sbol_path_p.exists():
            return {"error": f"SBOL file not found: {sbol_path}"}

        # get the output directory from the session state
        output_directory = self.session_state.output_directory
        sbml_filename = sbol_path_p.stem + "_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".xml"
        sbml_output_zip_path = os.path.join(output_directory,  sbml_filename + ".zip")

        # ------------------------------------------------------------------
        #  2) Run conversion 
        # ------------------------------------------------------------------
        try:
            from src.convert import SBOL2SBMLConverter  # remote Java service
            import dotenv
            dotenv.load_dotenv()
            base_url = os.getenv("IBIOSIM_URL")
            converter = SBOL2SBMLConverter(base_url)

            sbml_output_zip_path = converter.convert_sbol_to_sbml(str(sbol_path_p), str(sbml_output_zip_path))
            if not sbml_output_zip_path:
                raise RuntimeError("Converter returned None – see logs above")
            sbml_output_zip_path = Path(sbml_output_zip_path)
        except Exception as exc_local:
            return {"error": f"Converter failed: {exc_local}"}

        # ------------------------------------------------------------------
        #  3) Build parameter template
        # ------------------------------------------------------------------
        try:
            import libsbml
            import zipfile
            from src.simulate.param_template import build_param_template

            with zipfile.ZipFile(sbml_output_zip_path, "r") as zip_ref:
                zip_ref.extractall(output_directory)

            # Go through the files in the manifest and find the first SBML file
            with open(f"{output_directory}/manifest.xml", "r") as manifest_file:
                manifest_content = manifest_file.read()

            # Find the first SBML file in the manifest
            sbml_file_path = None
            for line in manifest_content.split("\n"):
                if "http://identifiers.org/combine.specifications/sbml" in line:
                    sbml_file_path = line.split("location=")[1].split(" ")[0].strip("\"")
                    full_path = os.path.join(output_directory, sbml_file_path)
                    break
            
            if not sbml_file_path:
                # raise RuntimeError("No SBML file found in the manifest")
                return {"error": "No SBML file found in the manifest"}
            
            sbml_doc = libsbml.SBMLReader().readSBML(full_path)
            template = build_param_template(sbml_doc)
            
        except Exception as exc:
            return {"error": f"SBML parsing failed. Path: {sbml_output_zip_path}. Error: {exc}"}

        # ------------------------------------------------------------------
        #  4) Persist inside session state
        # ------------------------------------------------------------------
        self.session_state.design_state.sbol_file = sbol_path_p
        self.session_state.design_state.sbml_file = sbml_output_zip_path
        self.session_state.initialise_parameter_template(template)

        return {
            "success": True,
            "sbml_path": str(sbml_output_zip_path),
            "parameter_template": template,
        }


class SetParameterValueTool(Tool):
    name = "set_parameter_value"
    description = (
        "Bulk-update values inside the current parameter template for the loaded kinetic model. "
        "Supply an *updates* JSON object that mirrors the parameter template hierarchy. "
        "Missing keys are ignored. Example::\n\n"
        "    {\"species\": {\"AraC\": 1.0}, \"parameters\": {\"k_syn\": 0.05}}"
    )
    parameters = {
        "type": "object",
        "properties": {
            "updates": {
                "type": "object",
                "description": "Nested mapping matching the parameter template (species/parameters → IDs). Values can be number or string.",
                "additionalProperties": True,
            }
        },
        "required": ["updates"],
    }

    def execute(self, updates: Dict[str, Any]):
        if not self.session_state.design_state.parameter_template:
            return {"error": "No parameter template initialized. Run convert_sbol_to_sbml first."}

        template = self.session_state.design_state.parameter_template
        changes: Dict[str, Dict[str, Any]] = {}

        for section, inner in updates.items():
            if section not in template:
                continue  # silently ignore unknown top-level keys
            if not isinstance(inner, dict):
                continue
            for key, value in inner.items():
                if key not in template[section]:
                    continue  # unknown ID → ignore
                old = template[section][key]["value"]
                template[section][key]["value"] = value
                template[section][key]["source"] = "agent"
                changes.setdefault(section, {})[key] = {"old": old, "new": value}

        return {"success": True, "changes": changes, "parameter_template": template}

class GetParameterTemplateTool(Tool):
    name = "get_parameter_template"
    description = "Return the current kinetic model parameters stored in the session."
    parameters = {"type": "object", "properties": {}, "required": []}

    def execute(self):
        template = self.session_state.design_state.parameter_template
        if not template:
            return {"error": "No parameter template initialized yet."}
        return {"success": True, "parameter_template": template}



class GenerateKineticModelFromNaturalLanguageTool(Tool):
    """
    https://github.com/kmaeda16/KinModGPT/
    """
    name = "generate_model_from_natural_language"
    description = "Create a kinetic model from a natural language description of biochemical reactions. This tool creates a kinetic model and returns the various parameters and species. The model is stored in the session state for further use."
    parameters = { "type": "object",
                   "properties": { 
                       "spec": 
                        {
                           "type": "string",
                           "description": "A description of the biochemical reactions to model (e.g. 'Protein P decays. The initial concentration is 1 uM.', 'mRNA_s32 is upregurated by Pg_s70_RNAP. Similarly, mRNA_DnaK and mRNA_FtsH are positively regulated by Ph_RNAP_s32. mRNA_Protein is transcribed without regulation. s32, FtsH, DnaK, and Pfold are translated from mRNA_s32, mRNA_FtsH, mRNA_DnaK, and mRNA_Protein, respectively. All the mRNAs (mRNA_s32, mRNA_DnaK, mRNA_FtsH, and mRNA_Protein) decay. s32, s32_DnaK, s32_FtsH, s32_DnaK_FtsH, FtsH, DnaK, Punfold_DnaK, Pfold, and Punfold decay. RNAP_s32 is degraded into RNAP. Similarly, Ph_RNAP_s32 is degraded into Ph and RNAP. D_RNAP_s32 is degraded into RNAP_D.')"
                        }, 
                    },
                   "required": ["spec"] }

    def execute(self, spec: str):
        from src.integrations.kinmod_gpt_integration import KineticModelingGPTIntegration
        import tellurium as te, libsbml, os, uuid

        gpt = KineticModelingGPTIntegration()
        antimony = gpt.generate_kinetic_model(spec)

        try:
            sbml_xml = te.antimonyToSBML(antimony)
            sbml_doc = libsbml.readSBMLFromString(sbml_xml)
        except Exception as exc:
            return {"error": f"Antimony→SBML conversion failed: {exc}"}

        from src.simulate.param_template import build_param_template
        template = build_param_template(sbml_doc)

        # Persist in session
        self.session_state.design_state.antimony  = antimony
        self.session_state.design_state.sbml_doc  = sbml_doc

        outdir = self.session_state.output_directory or Path("uploads")
        outdir.mkdir(exist_ok=True, parents=True)
        fn = outdir / f"model_{uuid.uuid4().hex[:8]}.xml"
        libsbml.writeSBMLToFile(sbml_doc, str(fn))
        self.session_state.design_state.sbml_file = fn
        self.session_state.initialise_parameter_template(template)
        return {"success": True,
                "sbml_path": str(fn),
                "antimony": antimony,
                "parameter_template": template}

class RunKineticModelSimulationTool(Tool):
    name = "run_kinetic_model_simulation"
    description = "Simulate the currently loaded kinetic model with the current parameters."
    parameters = {"type": "object", "properties": {}, "required": []}

    def execute(self):
        from src.simulate.run import run_kinetic_model_tellurium
        template = self.session_state.design_state.parameter_template
        result = run_kinetic_model_tellurium(self.session_state.design_state.sbml_doc, 
                                             template['parameters'],
                                             template['species'])

        return {"success": True, "result": result.tolist()}


class SearchBioNumbersTool(Tool):
    name = "search_bio_numbers"
    description = "Search the BioNumbers database of useful biological numbers for parameters, constants and other values to complete and enrich biological models"
    parameters = {
        "type": "object", 
        "properties": {
            "query": {
                "type": "string", 
                "description": "The query to search for."
            }
        }, 
        "required": ["query"]
    }

    def execute(self, query: str):
        from src.integrations.bionumbers_integration import search_bionumbers   
        results = search_bionumbers(query)
        return {"success": True, "results": results}

# ---------------------------------------------------------------------------
#  Register in existing TOOL_REGISTRY and expose schemas
# ---------------------------------------------------------------------------

TOOL_REGISTRY = {}

# Library management tools
TOOL_REGISTRY[DescribeAvailableLibrariesTool.name] = DescribeAvailableLibrariesTool
TOOL_REGISTRY[SelectLibraryTool.name] = SelectLibraryTool
TOOL_REGISTRY[QueryLibrariesByOrganismTool.name] = QueryLibrariesByOrganismTool

# Library query tools
TOOL_REGISTRY[ListPromotersTool.name] = ListPromotersTool
TOOL_REGISTRY[ListRepressorsTool.name] = ListRepressorsTool
TOOL_REGISTRY[ListInputSensorsTool.name] = ListInputSensorsTool
TOOL_REGISTRY[GetDnaPartByNameTool.name] = GetDnaPartByNameTool
TOOL_REGISTRY[ListTerminatorsTool.name] = ListTerminatorsTool

# Library modification tools
TOOL_REGISTRY[AddPromoterVariantTool.name] = AddPromoterVariantTool
TOOL_REGISTRY[RemovePromoterTool.name] = RemovePromoterTool
TOOL_REGISTRY[CommitCustomLibraryTool.name] = CommitCustomLibraryTool
TOOL_REGISTRY[GetCelloLibraryStatusTool.name] = GetCelloLibraryStatusTool
TOOL_REGISTRY[CreateCustomUcfTool.name] = CreateCustomUcfTool
TOOL_REGISTRY[CreateCustomInputSensorsFileTool.name] = CreateCustomInputSensorsFileTool


# Cello design tools
TOOL_REGISTRY[GenerateVerilogToolLLM.name] = GenerateVerilogToolLLM
TOOL_REGISTRY[DesignWithCelloTool.name] = DesignWithCelloTool
TOOL_REGISTRY[EvaluateCircuitPerformanceTool.name] = EvaluateCircuitPerformanceTool

# RBS Calculator tools
TOOL_REGISTRY[PredictInitiationRateWithRbsCalculatorTool.name] = PredictInitiationRateWithRbsCalculatorTool
TOOL_REGISTRY[DesignRbsWithRbsCalculatorTool.name] = DesignRbsWithRbsCalculatorTool

# Promoter design/generation tools
TOOL_REGISTRY[GeneratePromoterLibraryFromSpacerTool.name] = GeneratePromoterLibraryFromSpacerTool
TOOL_REGISTRY[GeneratePromoterLibraryFromPromoterTool.name] = GeneratePromoterLibraryFromPromoterTool
TOOL_REGISTRY[EstimatePromoterStrengthWithProDTool.name] = EstimatePromoterStrengthWithProDTool
TOOL_REGISTRY[GetSpacerFromPromoterTool.name] = GetSpacerFromPromoterTool


# Register SynBioHub tools
TOOL_REGISTRY[SynBioHubSearchTool.name] = SynBioHubSearchTool
TOOL_REGISTRY[SynBioHubDownloadPartTool.name] = SynBioHubDownloadPartTool
TOOL_REGISTRY[SynBioHubSubmitTool.name] = SynBioHubSubmitTool
TOOL_REGISTRY[SynBioHubSequenceSearchTool.name] = SynBioHubSequenceSearchTool
TOOL_REGISTRY[SynBioHubGetRelatedTool.name] = SynBioHubGetRelatedTool

# Simulation & parameter template tools
# TOOL_REGISTRY[ConvertSbolToSbmlTool.name] = ConvertSbolToSbmlTool TODO:  Not Working
TOOL_REGISTRY[SetParameterValueTool.name] = SetParameterValueTool
TOOL_REGISTRY[GetParameterTemplateTool.name] = GetParameterTemplateTool
TOOL_REGISTRY[GenerateKineticModelFromNaturalLanguageTool.name] = GenerateKineticModelFromNaturalLanguageTool
TOOL_REGISTRY[RunKineticModelSimulationTool.name] = RunKineticModelSimulationTool   

TOOL_REGISTRY[ScientificSearchTool.name] = ScientificSearchTool
TOOL_REGISTRY[ToolDocsQueryTool.name] = ToolDocsQueryTool
TOOL_REGISTRY[TranslateDnaTool.name] = TranslateDnaTool
TOOL_REGISTRY[GcContentTool.name] = GcContentTool
TOOL_REGISTRY[SearchBioNumbersTool.name] = SearchBioNumbersTool

# Generate OpenAI function schemas from tools
_tool_schemas = [
    convert_to_openai_function(ReadFileTool()),
    *[tool_class.get_openai_schema() for tool_class in TOOL_REGISTRY.values()]
]
tool_functions = [{"type": "function", "function": schema} for schema in _tool_schemas]

class ToolIntegration:
    def __init__(self, session_state: SessionState, tool_registry: dict = TOOL_REGISTRY):
        self.session_state = session_state
        self.tools = {
            tool_name: tool_class(session_state) 
            for tool_name, tool_class in tool_registry.items()
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
            return ReadFileTool().run(function_args.get("file_path", function_args))
        
        # Use the tool from the registry if available
        if function_name in self.tools:
            tool_instance = self.tools[function_name]
            try:
                return tool_instance.execute(**function_args)
            except TypeError as e:
                if "missing" in str(e) and "required positional argument" in str(e):
                    sig = inspect.signature(tool_instance.execute)
                    required = [
                        p.name for p in sig.parameters.values()
                        if p.default is inspect.Parameter.empty and p.name != 'self'
                    ]
                    missing = [p for p in required if p not in function_args]
                    return {
                        "error": (
                            f"Invalid arguments for tool '{function_name}'. "
                            f"Missing required arguments: {missing}. "
                            f"Please provide all required arguments: {required}."
                        )
                    }
                else:
                    # Re-raise other TypeErrors or unexpected errors
                    raise e
        
        # If no tool found, return error
        return {"error": f"No such function: {function_name}"}