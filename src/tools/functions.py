# tools/functions.py

import json
import os
import glob
import re
from typing import Dict, List
import src.library.part_library_customizer as part_library_customizer
from src.tools.gpro_integration import PromoterOptimizer, RepressorOptimizer
from src.library.library_manager import LibraryManager
from src.tools.deepseed_integration import DeepSeedIntegration
from src.session_state import SessionState
import traceback

DEBUG_MODE = True

from langchain_community.tools import ReadFileTool
from langchain_core.utils.function_calling import convert_to_openai_function



tool_functions = [convert_to_openai_function(ReadFileTool()),
    {
        "name": "list_promoters",
        "description": "Return a list of promoter parts from the selected library. IMPORTANT: You must first select a library using select_library before using this function.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_type": {
                    "type": "string",
                    "description": "The type of file to list parts from, must be 'input', 'output', or 'ucf'"
                }
            },
            "required": ["file_type"]
        }
    },
    {   
        "name": "describe_available_libraries",
        "description": "Return a description of the available libraries.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "select_library",
        "description": "Select a library using a library ID.",
        "parameters": {
            "type": "object",
            "properties": {
                "library_id": {
                    "type": "string",
                    "description": "The ID of the library to select."
                }
            },
            "required": ["library_id"]
        }
    },
    {
        "name": "list_repressors",
        "description": "Return a list of possible repressors from the selected library. Optionally filter by family. IMPORTANT: You must first select a library using select_library before using this function.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_type": {
                    "type": "string",
                    "description": "The type of file to list parts from, must be 'input', 'output', or 'ucf'"
                }
            },
            "required": ["file_type"]
        }
    },
    {
        "name": "get_dna_part_by_name",
        "description": "Get a specific DNA part by name (like 'pTet') from the selected library in the user contrainsts file. IMPORTANT: You must first select a library using select_library before using this function.",
        "parameters": {
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
    },
    {
        "name": "list_terminators",
        "description": "Return a list of terminator parts from the selected library. IMPORTANT: You must first select a library using select_library before using this function.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_type": {
                    "type": "string",
                    "description": "The type of file to list parts from, must be 'input', 'output', or 'ucf'"
                }
            },
            "required": ["file_type"]
        }
    },
    {
        "name": "design_with_cello",
        "description": "Design genetic circuits using Cello. Accepts Verilog code and optional configuration.",
        "parameters": {
            "type": "object",
            "properties": {
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
            "required": ["verilog_code"]
        }
    },
    {
        "name": "create_custom_ucf",
        "description": "Create a customized library file with selected parts. Parts referencing the selected parts will be included in the custom library. IMPORTANT: You must first select a library using the select_library function before using this function.",
        "parameters": {
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
    },
    {
        "name": "predict_promoter_strength",
        "description": "Predict the strength of a promoter sequence.",
        "parameters": {
            "type": "object",
            "properties": {
                "sequence": {
                    "type": "string",
                    "description": "DNA sequence of the promoter"
                }
            },
            "required": ["sequence"]
        }
    },
    {
        "name": "optimize_promoter",
        "description": "Optimize a promoter to reach a target strength.",
        "parameters": {
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
    },
    {
        "name": "generate_promoters",
        "description": "Generate novel promoter sequences with optional strength filtering.",
        "parameters": {
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
    },
    {
        "name": "optimize_binding_site",
        "description": "Optimize a repressor binding site for target repression level.",
        "parameters": {
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
    },
    {
        "name": "evaluate_circuit_performance",
        "description": "Evaluate the performance of a designed genetic circuit by analyzing Cello output files",
        "parameters": {
            "type": "object",
            "properties": {
                "output_path": {
                    "type": "string",
                    "description": "Path to the Cello output directory for the circuit"
                }
            },
            "required": ["output_path"]
        }
    }
]


class ToolIntegration:
    def __init__(self, session_state: SessionState):
        self.session_state = session_state

    def select_library_func(self, library_id: str):
        """
        Select a library using a library ID *within the current session*.
        """
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
    
    def describe_available_libraries_func(self):
        """
        Return a description of the available libraries found by the session's LibraryManager.
        """
        library_manager = self.session_state.get_library_manager()
        return  {
            "success": True,
            "libraries": library_manager.describe_available_libraries()
        }
    
    def design_with_cello_func(self, verilog_code: str, config: dict = None):
        """
        Interface with Cello using the *currently selected* library context.
        """
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
        results = cello.run_cello(verilog_code)

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

    
    def create_custom_ucf_func(self, selected_gates: List[str] = None, selected_parts: List[str] = None, modified_parts: Dict[str, Dict] = None, ucf_name: str = None):
        """
        Create a customized UCF file based on the *currently selected* library.
        The custom UCF path will be stored in the session state.
        """
        library_manager = self.session_state.get_library_manager()
        if not library_manager.current_library_id:
            return {"error": "No library selected as base for custom UCF. Please use 'select_library' first."}

        base_ucf_data = library_manager.get_ucf_data()
        if not base_ucf_data:
             return {"error": f"Could not retrieve base UCF data for library {library_manager.current_library_id}."}

        output_dir = "outputs/custom_ucf"
        custom_ucf_name = ucf_name or f"custom_{library_manager.current_library_id}"

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
        
    def get_ucf_metadata_func(self):
        """
        Get metadata for all available UCF libraries.
        This function extracts key information from each UCF file to help the LLM make an informed decision.
        
        Returns:
            Dict containing metadata for all available UCF libraries
        """
        # Create a library manager to access all libraries
        library_manager = LibraryManager()
        
        # Get all available libraries
        available_libraries = library_manager.get_available_libraries()
        
        # Create a library selector to get detailed metadata
        library_selector = LLMBasedLibrarySelector(library_manager)
        
        # Collect metadata for each library
        libraries_metadata = {}
        for library_id in available_libraries:
            # Select the library
            library_manager.select_library(library_id)
            
            # Get metadata
            metadata = library_selector.get_library_metadata(library_id)
            
            # Add to collection
            libraries_metadata[library_id] = metadata
        
        return {
            "available_libraries": available_libraries,
            "libraries_metadata": libraries_metadata
        }
    
    def llm_select_ucf_func(self, user_request: str, llm_reasoning: str):
        """
        Select a UCF library based on LLM reasoning.
        This function is designed to be called after the LLM has analyzed the user request
        and UCF metadata, and has provided its reasoning for selecting a particular library.
        
        Args:
            user_request: The original user request
            llm_reasoning: The LLM's reasoning for selecting a particular library,
                           including the library ID to select
        
        Returns:
            Dict containing the selected library and metadata
        """
        # Extract the library ID from the LLM reasoning
        # This is a simple implementation - in practice, you might want to use regex or more sophisticated parsing
        library_id = None
        
        # Look for library IDs in the reasoning (assuming they follow the format like Eco1C1G1T0)
        import re
        library_pattern = r'\b([A-Za-z]{2,3}\d+[A-Za-z]\d+[A-Za-z]\d+[A-Za-z]\d+)\b'
        matches = re.findall(library_pattern, llm_reasoning)
        
        if matches:
            library_id = matches[0]
        else:
            # Try to find any mention of a library ID
            library_manager = LibraryManager()
            available_libraries = library_manager.get_available_libraries()
            
            for lib_id in available_libraries:
                if lib_id in llm_reasoning:
                    library_id = lib_id
                    break
        
        # If no library ID was found, try to extract organism information and select based on that
        if not library_id:
            # Create a library selector
            library_selector = LLMBasedLibrarySelector()
            
            # Analyze the user request
            analysis = library_selector.analyze_user_request(user_request)
            
            # Try to select based on organism
            if analysis["organisms"]:
                library_manager = LibraryManager()
                for organism in analysis["organisms"]:
                    if library_manager.select_library(organism):
                        library_id = library_manager.current_library_id
                        break
            
            # If still no library ID, default to the first available
            if not library_id:
                library_manager = LibraryManager()
                available_libraries = library_manager.get_available_libraries()
                if available_libraries:
                    library_id = available_libraries[0]
        
        # If we have a library ID, get its metadata and select it
        if library_id:
            library_manager = LibraryManager()
            success = library_manager.select_library(library_id)
            
            if success:
                # Get metadata
                library_selector = LLMBasedLibrarySelector(library_manager)
                metadata = library_selector.get_library_metadata(library_id)
                
                # Update the library in the Cello integration if available
                if hasattr(self, "cello_integration") and self.cello_integration:
                    self.cello_integration.select_library(library_id)
                
                return {
                    "success": True,
                    "library_id": library_id,
                    "metadata": metadata,
                    "message": f"Selected library {library_id} based on LLM reasoning"
                }
        
        # If we couldn't select a library, return an error
        return {
            "success": False,
            "message": "Could not select a library based on LLM reasoning",
            "user_request": user_request,
            "llm_reasoning": llm_reasoning
        }

    def evaluate_circuit_performance_func(self, output_path: str):
        """
        Evaluate circuit performance by extracting metrics from Cello output files.
        
        Args:
            output_path: Path to Cello output directory
            
        Returns:
            Dict with performance metrics including ON/OFF ratios, leakage, etc.
        """
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

    def call_tool_function(self, function_name, function_args):
        """
        Call a tool function with the provided arguments.
        
        Args:
            function_name: Name of the function to call
            function_args: Arguments for the function
            
        Returns:
            Result of the function call
        """
        # Library functions
        if function_name == "select_library":
            library_id = function_args["library_id"]
            return self.select_library_func(library_id)
        elif function_name == "read_file":
            return ReadFileTool().run(function_args["file_path"])
        elif function_name == "describe_available_libraries":
            return self.describe_available_libraries_func()
        elif function_name == "list_promoters":
            return self.list_promoters_func(function_args["file_type"])
        elif function_name == "list_repressors":
            return self.list_repressors_func(function_args["file_type"])
        elif function_name == "get_dna_part_by_name":
            name = function_args["name"]
            return self.get_dna_part_by_name_func(name, function_args["file_type"])
        elif function_name == "list_terminators":
            return self.list_terminators_func(function_args["file_type"])
        elif function_name == "create_custom_ucf":
            selected_gates = function_args.get("selected_gates", None)
            selected_parts = function_args.get("selected_parts", None)
            modified_parts = function_args.get("modified_parts", None)
            ucf_name = function_args.get("ucf_name", "")
            return self.create_custom_ucf_func(selected_gates, selected_parts, modified_parts, ucf_name)
        elif function_name == "get_ucf_metadata":
            return self.get_ucf_metadata_func()
        elif function_name == "llm_select_ucf":
            user_request = function_args["user_request"]
            llm_reasoning = function_args["llm_reasoning"]
            return self.llm_select_ucf_func(user_request, llm_reasoning)
        
        # Design functions        
        elif function_name == "design_with_cello":
            verilog_code = function_args["verilog_code"]
            config = function_args.get("config", None)
            return self.design_with_cello_func(verilog_code, config)
        elif function_name == "predict_promoter_strength":
            sequence = function_args["sequence"]
            return self.predict_promoter_strength_func(sequence)
        elif function_name == "optimize_promoter":
            seed_sequence = function_args["seed_sequence"]
            target_strength = function_args["target_strength"]
            iterations = function_args.get("iterations", 100)
            return self.optimize_promoter_func(seed_sequence, target_strength, iterations)
        elif function_name == "generate_promoters":
            count = function_args["count"]
            min_strength = function_args.get("min_strength", None)
            max_strength = function_args.get("max_strength", None)
            return self.generate_promoters_func(count, min_strength, max_strength)
        elif function_name == "optimize_binding_site":
            repressor_id = function_args["repressor_id"]
            starting_site = function_args["starting_site"]
            target_repression = function_args["target_repression"]
            return self.optimize_binding_site_func(repressor_id, starting_site, target_repression)
        elif function_name == "evaluate_circuit_performance":
            output_path = function_args["output_path"]
            return self.evaluate_circuit_performance_func(output_path)
        else:
            return {"error": f"No such function: {function_name}"}

    
    def list_promoters_func(self, file_type: str):
        """
        Return a list of promoter parts from the *currently selected* library.
        """
        if file_type == "input":    
            library_data, error = self._get_current_library_input_data()
        elif file_type == "output":
            library_data, error = self._get_current_library_output_data()
        elif file_type == "ucf":
            library_data, error = self._get_current_library_ucf_data()
        else:
            return {"error": f"Invalid file type: {file_type}, must be 'input', 'output', or 'ucf'"}

        try:
            promoters = part_library_customizer.get_parts_by_type(library_data, "promoter")
            return {
                "success": True,
                "library_id": self.session_state.get_current_library_id(),
                "promoters": promoters}
        except Exception as e:
            if DEBUG_MODE:
                traceback.print_exc()
                raise e
            else:
                return {"error": f"Error listing promoters: {str(e)}"}

    def list_repressors_func(self, file_type: str):
        """
        Return a list of possible repressors from the *currently selected* library. Optionally filter by family.
        """
        if file_type == "ucf":
            library_data, error = self._get_current_library_ucf_data()
        elif file_type == "input":
            library_data, error = self._get_current_library_input_data()
        elif file_type == "output":
            library_data, error = self._get_current_library_output_data()
        else:
            return {"error": f"Invalid file type: {file_type}, must be 'ucf', 'input', or 'output'"}

        try:
            repressors = part_library_customizer.get_parts_by_type(library_data, "repressor")
            return {
                "success": True,
                "library_id": self.session_state.get_current_library_id(),
                "repressors": repressors
            }
        except Exception as e:
            return {"error": f"Error listing repressors: {str(e)}"}

    def get_dna_part_by_name_func(self, name, file_type: str):
        """
        Get a specific DNA part by name from the *currently selected* library.
        """
        if file_type == "ucf":
            library_data, error = self._get_current_library_ucf_data()
        elif file_type == "input":
            library_data, error = self._get_current_library_input_data()
        elif file_type == "output":
            library_data, error = self._get_current_library_output_data()
        else:
            return {"error": f"Invalid file type: {file_type}, must be 'ucf', 'input', or 'output'"}

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

    def list_terminators_func(self, file_type: str):
        """
        Return a list of terminator parts from the *currently selected* library.
        """
        if file_type == "ucf":
            library_data, error = self._get_current_library_ucf_data()
        elif file_type == "input":
            library_data, error = self._get_current_library_input_data()
        elif file_type == "output":
            library_data, error = self._get_current_library_output_data()
        else:
            return {"error": f"Invalid file type: {file_type}, must be 'ucf', 'input', or 'output'"}

        try:
            terminators = part_library_customizer.get_parts_by_type(library_data, "terminator")
            return {
                "success": True,
                "library_id": self.session_state.get_current_library_id(),
                "terminators": terminators
            }
        except Exception as e:
            return {"error": f"Error listing terminators: {str(e)}"}

    def predict_promoter_strength_func(self, sequence):
        """
        Predict the strength of a promoter sequence.
        """
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

    def optimize_promoter_func(self, seed_sequence, target_strength, iterations=100):
        """
        Optimize a promoter to reach a target strength.
        """
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

    def generate_promoters_func(self, count, min_strength=None, max_strength=None):
        """
        Generate novel promoter sequences with optional strength filtering.
        """
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

    def optimize_binding_site_func(self, repressor_id, starting_site, target_repression):
        """
        Optimize a repressor binding site for target repression level.
        """
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
        