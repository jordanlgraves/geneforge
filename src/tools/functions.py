# tools/functions.py

import os
from typing import Dict, List, Any, ClassVar, Optional
import src.library.part_library_customizer as part_library_customizer
import logging
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
                library_manager.load_custom_ucf(custom_ucf_path)
                self.session_state.custom_ucf_path = custom_ucf_path
                return {
                    "success": True,
                    "library_id": library_manager.current_library_id,
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

from src.tools.pro_d_integration import ProDIntegration, class_to_rpu, extract_id_ecoli_spacer


class _ProDToolBase(Tool):
    """Mixin that provides a per-session ProDIntegration instance."""

    def _get_prod(self) -> ProDIntegration:
        if not hasattr(self.session_state, "prod_integration"):
            setattr(self.session_state, "prod_integration", ProDIntegration())
        return getattr(self.session_state, "prod_integration")


# ---------------------------------------------------------------------------
#  EstimatePromoterStrengthWithProD
# ---------------------------------------------------------------------------


class EstimatePromoterStrengthWithProDTool(_ProDToolBase):
    name = "estimate_promoter_strength_with_pro_d"
    description = "Return ProD class and calibrated ymax for a promoter ID or DNA sequence. If an ID is given the currently selected library is searched."
    parameters = {
        "type": "object",
        "properties": {
            "promoter": {"type": "string", "description": "Promoter ID (e.g. 'pTet') or full DNA sequence or 17-bp spacer."},
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

        spacer = extract_id_ecoli_spacer(sequence) or sequence[:17]
        cls_val = int(result[spacer])
        ymax = result.get(spacer + "_ymax", class_to_rpu(cls_val))

        return {
            "promoter_sequence": sequence,
            "spacer": spacer,
            "class": cls_val,
            "ymax": ymax,
            "success": True
        }


# ---------------------------------------------------------------------------
#  GeneratePromoterLibraryWithProD
# ---------------------------------------------------------------------------


class GeneratePromoterLibraryWithProDTool(_ProDToolBase):
    name = "generate_promoter_library_with_pro_d"
    description = "Use ProD to generate spacer variants at desired strength classes and, if a parent promoter is supplied, return full promoter sequences too."
    parameters = {
        "type": "object",
        "properties": {
            "blueprint": {"type": "string", "description": "Degenerate 17-bp spacer blueprint or full promoter blueprint."},
            "desired_strengths": {
                "type": "array", "items": {"type": "integer"},
                "description": "List of desired strength classes (0-10)"
            },
            "sequences_per_class": {"type": "integer", "default": 5},
            "parent_promoter": {"type": "string", "description": "Optional promoter ID or full promoter sequence to supply flanking regions."},
            "file_type": {"type": "string", "enum": ["ucf", "input", "output"], "default": "ucf"}
        },
        "required": ["blueprint"]
    }

    def execute(self, blueprint: str, desired_strengths: List[int] = None, sequences_per_class: int = 5,
                parent_promoter: str = None, file_type: str = "ucf") -> Dict[str, Any]:
        prod = self._get_prod()

        if len(blueprint) != 17:
            # assume the blueprint is a full promoter
            spacer = prod.extract_spacer(blueprint)
            if not spacer:
                return {"error": "Could not extract spacer from full promoter sequence."}
            parent_seq = blueprint
            blueprint = spacer
            idx = parent_seq.find(spacer)
            upstream = parent_seq[:idx]
            downstream = parent_seq[idx+17:]
        else:
            upstream = downstream = None

        if parent_promoter:
            library_manager = self.session_state.get_library_manager()
            dna_chars = set("ATGCRYSWKMBDHVNatgcryswkmbdhvn")
            is_dna = set(parent_promoter).issubset(dna_chars) and len(parent_promoter) >= 17
            parent_seq = None
            if is_dna:
                parent_seq = parent_promoter.upper()
            else:
                if not library_manager.current_library_id:
                    return {"error": "No library selected. Use select_library first."}
                if file_type == "ucf":
                    lib_data = library_manager.get_ucf_data()
                elif file_type == "input":
                    lib_data = library_manager.get_input_sensor_data()
                else:
                    lib_data = library_manager.get_output_device_data()
                import src.library.part_library_customizer as plc
                part = plc.get_part_by_name(lib_data, parent_promoter)
                if not part:
                    return {"error": f"Parent promoter '{parent_promoter}' not found."}
                parent_seq = part.get("dnasequence") or part.get("sequence")

            spacer_parent = extract_id_ecoli_spacer(parent_seq)
            if spacer_parent and spacer_parent in parent_seq:
                idx = parent_seq.find(spacer_parent)
                upstream = parent_seq[:idx]
                downstream = parent_seq[idx+17:]

        # Call ProD
        try:
            lib_dict = prod.generate_library(
                blueprint,
                    desired_strengths=desired_strengths,
                    library_size=sequences_per_class,
                )
        except Exception as e:
            return {"error": f"Error generating promoter library: {str(e)}"}

        # Enrich with full promoter sequences if we know flanks
        if upstream is not None and downstream is not None:
            for spacer_seq, properties in lib_dict.items():
                properties["promoter_sequence"] = f"{upstream.upper()}{spacer_seq}{downstream.upper()}" 

        return {
            "blueprint": blueprint,
            "variants": [
                {
                    "spacer": k,
                    **v
                } for k, v in lib_dict.items()
            ],
            "success": True
        }


# ---------------------------------------------------------------------------
#  PatchUcfWithPromotersTool – wraps LibraryManager.create_custom_ucf
# ---------------------------------------------------------------------------

class PatchUcfWithPromotersTool(Tool):
    name = "patch_ucf_with_promoters"
    description = "Duplicate or replace a promoter part in the currently selected library UCF with supplied spacer variants and their calibrated ymax values. Returns path to the new custom UCF file."
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
        from src.tools.pro_d_integration import extract_id_ecoli_spacer
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
        from src.tools.rbs_calculator_integration import RBSCalculatorIntegration

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
        from src.tools.rbs_calculator_integration import RBSCalculatorIntegration

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
        "Create a new promoter variant (new spacer and ymax) by duplicating the dependencies of an existing promoter "
        "within the currently selected library and writing a custom UCF file."
    )
    parameters = {
        "type": "object",
        "properties": {
            "parent_promoter_id": {"type": "string", "description": "ID of the reference promoter part."},
            "spacer": {"type": "string", "description": "17-bp spacer sequence to use in replacement of the 17-bp spacer sequence of the parent promoter"},
            "ymax": {"type": "number", "description": "Calibrated RPU (ymax) for the new promoter. Can be found in the output from the ProD tool."},
            "new_promoter_id": {"type": "string", "description": "Optional name for the new promoter. Alphanumeric characters only, no spaces or special characters."},
        },
        "required": ["parent_promoter_id", "spacer", "ymax"],
    }

    def execute(
        self,
        parent_promoter_id: str,
        spacer: str,
        ymax: float,
        new_promoter_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        import copy
        from src.tools.pro_d_integration import extract_id_ecoli_spacer
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
        if len(spacer) != 17:
            return {"error": "Provided spacer must be 17 bp."}

        # Build new promoter sequence
        idx = parent_seq.find(spacer_parent)
        new_sequence = f"{parent_seq[:idx].upper()}{spacer.upper()}{parent_seq[idx+17:].upper()}"

        # Determine new promoter id
        if not new_promoter_id:
            base = parent_promoter_id.rstrip("\n")
            new_promoter_id = f"{base}var1"
            i = 1
            while plc.get_part_by_name(ucf_data, new_promoter_id):
                i += 1
                new_promoter_id = f"{base}var{i}"

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
                "custom_ucf_path": path,
                "new_promoter_id": new_promoter_id,
                "n_new_items": len(new_items),
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
                "custom_ucf_path": path,
                "removed_items_summary": summary,
            }
        except Exception as exc:
            if DEBUG_MODE:
                traceback.print_exc()
            return {"error": str(exc)}

        
# ---------------------------------------------------------------------------
#  Register in existing TOOL_REGISTRY and expose schemas
# ---------------------------------------------------------------------------

TOOL_REGISTRY = {}

TOOL_REGISTRY[DescribeAvailableLibrariesTool.name] = DescribeAvailableLibrariesTool
TOOL_REGISTRY[SelectLibraryTool.name] = SelectLibraryTool
TOOL_REGISTRY[QueryLibrariesByOrganismTool.name] = QueryLibrariesByOrganismTool

TOOL_REGISTRY[ListPromotersTool.name] = ListPromotersTool
TOOL_REGISTRY[ListRepressorsTool.name] = ListRepressorsTool
TOOL_REGISTRY[ListInputSensorsTool.name] = ListInputSensorsTool
TOOL_REGISTRY[GetDnaPartByNameTool.name] = GetDnaPartByNameTool
TOOL_REGISTRY[ListTerminatorsTool.name] = ListTerminatorsTool

TOOL_REGISTRY[GenerateVerilogToolLLM.name] = GenerateVerilogToolLLM
TOOL_REGISTRY[DesignWithCelloTool.name] = DesignWithCelloTool
TOOL_REGISTRY[EvaluateCircuitPerformanceTool.name] = EvaluateCircuitPerformanceTool

TOOL_REGISTRY[CreateCustomUcfTool.name] = CreateCustomUcfTool
TOOL_REGISTRY[CreateCustomInputSensorsFileTool.name] = CreateCustomInputSensorsFileTool

TOOL_REGISTRY[EstimatePromoterStrengthWithProDTool.name] = EstimatePromoterStrengthWithProDTool
TOOL_REGISTRY[GeneratePromoterLibraryWithProDTool.name] = GeneratePromoterLibraryWithProDTool
# Deprecated PatchUcfWithPromotersTool is no longer registered.
# New promoter management tools will be registered below.

# RBS Calculator tools
TOOL_REGISTRY[PredictInitiationRateWithRbsCalculatorTool.name] = PredictInitiationRateWithRbsCalculatorTool
TOOL_REGISTRY[DesignRbsWithRbsCalculatorTool.name] = DesignRbsWithRbsCalculatorTool

# Promoter variant tools
TOOL_REGISTRY[AddPromoterVariantTool.name] = AddPromoterVariantTool
TOOL_REGISTRY[RemovePromoterTool.name] = RemovePromoterTool

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
        