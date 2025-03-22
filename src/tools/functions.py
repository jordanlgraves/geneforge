# tools/functions.py

import json
import os
import glob
import re
from typing import Dict, List
from src.library.ucf_retrieval import choose_repressor, get_dna_part_by_name, get_gate_by_id, get_gates_by_type, list_misc_items, list_promoters, list_terminators
from src.library.ucf_customizer import UCFCustomizer
from src.tools.gpro_integration import PromoterOptimizer, RepressorOptimizer
from src.library.llm_library_selector import RuleBasedLibrarySelector, LLMBasedLibrarySelector
from src.library.library_manager import LibraryManager
from src.tools.cello_integration import CelloIntegration
from src.tools.deepseed_integration import DeepSeedIntegration
tool_functions = [
    {
        "name": "find_gates_by_type",
        "description": "Find all gates in the library that match a certain type (e.g. NOR, AND, NOT). IMPORTANT: You must first select a library using analyze_and_select_library before using this function.",
        "parameters": {
            "type": "object",
            "properties": {
                "gate_type": {
                    "type": "string",
                    "description": "The type of gate to lookup."
                }
            },
            "required": ["gate_type"]
        }
    },
    {
        "name": "get_gate_info",
        "description": "Retrieve metadata for a specific gate by ID. IMPORTANT: You must first select a library using analyze_and_select_library before using this function.",
        "parameters": {
            "type": "object",
            "properties": {
                "gate_id": {
                    "type": "string",
                    "description": "Unique ID of the gate."
                }
            },
            "required": ["gate_id"]
        }
    },
    {
        "name": "simulate_circuit",
        "description": "Stub for simulating a circuit design. Provide a circuit specification in JSON.",
        "parameters": {
            "type": "object",
            "properties": {
                "circuit_spec": {
                    "type": "string",
                    "description": "A JSON string describing the circuit (list of gates, connections, etc.)."
                }
            },
            "required": ["circuit_spec"]
        }
    },
    {
        "name": "list_promoters",
        "description": "Return a list of promoter parts from the selected library. IMPORTANT: You must first select a library using analyze_and_select_library before using this function.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "choose_repressor",
        "description": "Return a list of possible repressors. Optionally filter by family. IMPORTANT: You must first select a library using analyze_and_select_library before using this function.",
        "parameters": {
            "type": "object",
            "properties": {
                "family": {
                    "type": "string",
                    "description": "Name of a repressor family, e.g. TetR, if desired. Otherwise omit."
                }
            },
            "required": []
        }
    },
    {
        "name": "get_dna_part_by_name",
        "description": "Get a specific DNA part by name (like 'pTet'). IMPORTANT: You must first select a library using analyze_and_select_library before using this function.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name or ID of the DNA part to retrieve."
                }
            },
            "required": ["name"]
        }
    },
    {
        "name": "list_terminators",
        "description": "Return a list of terminator parts from the selected library. IMPORTANT: You must first select a library using analyze_and_select_library before using this function.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "list_misc_items",
        "description": "Return a list of miscellaneous items from the selected library. IMPORTANT: You must first select a library using analyze_and_select_library before using this function.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
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
        "description": "Create a customized UCF file with selected parts. IMPORTANT: You must first select a library using the analyze_and_select_library function before using this function.",
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
        "name": "find_ucf_file",
        "description": "Find the appropriate UCF file based on user specifications.",
        "parameters": {
            "type": "object",
            "properties": {
                "organism": {
                    "type": "string",
                    "description": "Organism for the circuit (e.g., 'E. coli', 'yeast')"
                },
                "inducers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of inducers to use (e.g., 'arabinose', 'IPTG', 'aTc')"
                },
                "gate_types": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of gate types needed (e.g., 'NOT', 'NOR', 'AND')"
                }
            },
            "required": ["organism"]
        }
    },
    {
        "name": "design_circuit",
        "description": "Design a genetic circuit with automatic UCF file selection based on requirements.",
        "parameters": {
            "type": "object",
            "properties": {
                "verilog_code": {
                    "type": "string",
                    "description": "The Verilog code representing the circuit design"
                },
                "organism": {
                    "type": "string",
                    "description": "Organism for the circuit (e.g., 'E. coli', 'yeast')"
                },
                "inducers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of inducers to use (e.g., 'arabinose', 'IPTG', 'aTc')"
                },
                "outputs": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of outputs required (e.g., 'GFP', 'RFP')"
                },
                "gate_types": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of gate types needed (e.g., 'NOT', 'NOR', 'AND')"
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
            "required": ["verilog_code", "organism"]
        }
    },
    {
        "name": "analyze_and_select_library",
        "description": "Analyze a user request and select the most appropriate library based on the requirements.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_request": {
                    "type": "string",
                    "description": "The user's request describing their circuit design needs, including organism, parts, gates, etc."
                }
            },
            "required": ["user_request"]
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
    def __init__(self, library_data):
        self.library_data = library_data

    def find_gates_by_type_func(self, gate_type: str):
        """
        Query the library for gates of a specified type.
        Returns a list of gate objects with ID, type, and description.
        """
        results = get_gates_by_type(self.library_data, gate_type)
        gate_list = []
        for g in results:
            gate_list.append({
                "id": g["id"],
                "gate_type": g.get("gate_type", ""),
                "notes": g["raw_data"].get("description", None)
            })
        return gate_list
    
    def design_with_cello_func(self, verilog_code: str, config: dict = None):
        """
        Interface with Cello to design genetic circuits from Verilog specifications.
        """
        from src.tools.cello_integration import CelloIntegration
        
        # Initialize Cello with optional custom config
        cello = CelloIntegration(cello_config=config)
        
        # Run Cello and get results
        results = cello.run_cello(verilog_code)
        
        if not results['success']:
            return {
                "error": f"Cello design failed: {results.get('error', 'Unknown error')}",
                "log": results['log']
            }
        
        return {
            "success": True,
            "dna_design": results['results']['dna_design'],
            "log": results['log']
        }

    def get_gate_info_func(self, gate_id: str):
        """Retrieve raw data for a specific gate by ID."""
        gate = get_gate_by_id(self.library_data, gate_id)
        if not gate:
            return {"error": f"No gate found with id={gate_id}"}
        # We can return the full raw_data or a condensed version
        return {
            "id": gate["id"],
            "gate_type": gate.get("gate_type", ""),
            "raw_data": gate["raw_data"]
        }

    def simulate_circuit_func(self, circuit_spec: str):
        """
        Stub for circuit simulation. For now, just return a dummy result.
        """
        # parse the circuit_spec if needed
        try:
            spec_data = json.loads(circuit_spec)
            # We do no real simulation, just pretend
            return {
                "success": True,
                "log": "Circuit simulated successfully. (Stub)",
                "circuit_spec": spec_data
            }
        except Exception as e:
            return {"error": f"Failed to parse circuit_spec as JSON: {e}"}

    def find_ucf_file_func(self, organism: str, inducers: list = None, gate_types: list = None):
        """
        Find the appropriate UCF file based on user specifications.
        
        Args:
            organism: Organism for the circuit (e.g., 'E. coli', 'yeast')
            inducers: List of inducers to use (e.g., 'arabinose', 'IPTG', 'aTc')
            gate_types: List of gate types needed (e.g., 'NOT', 'NOR', 'AND')
            
        Returns:
            Dict containing matching UCF files and their properties
        """
        # Map organism names to directory prefixes
        organism_map = {
            "e. coli": "Eco",
            "e.coli": "Eco",
            "ecoli": "Eco",
            "eco": "Eco",
            "yeast": "SC",
            "s. cerevisiae": "SC",
            "bacillus": "Bth",
            "b. subtilis": "Bth"
        }
        
        # Map inducer names to search terms
        inducer_map = {
            "arabinose": ["arabinose", "AraC", "pBAD"],
            "iptg": ["IPTG", "LacI", "pTac"],
            "atc": ["aTc", "TetR", "pTet"],
            "tetracycline": ["aTc", "TetR", "pTet"],
            "3oxoc6hsl": ["3OC6HSL", "LuxR", "pLux"],
            "hsl": ["HSL", "LuxR", "pLux"]
        }
        
        # Map gate types to search terms
        gate_type_map = {
            "not": ["NOT", "inverter"],
            "nor": ["NOR"],
            "and": ["AND"],
            "or": ["OR"],
            "nand": ["NAND"],
            "xor": ["XOR"]
        }
        
        # Normalize organism input
        org_key = organism.lower().strip()
        if org_key not in organism_map:
            return {
                "error": f"Unsupported organism: {organism}. Supported organisms are: E. coli, S. cerevisiae, B. subtilis"
            }
        
        org_prefix = organism_map[org_key]
        
        # Get all UCF files for the specified organism
        ucf_dir = "ext_repos/Cello-UCF/files/v2/ucf"
        ucf_files = glob.glob(f"{ucf_dir}/{org_prefix}/*.UCF.json")
        
        if not ucf_files:
            return {
                "error": f"No UCF files found for organism: {organism}"
            }
        
        # If no specific requirements, return all available UCF files
        if not inducers and not gate_types:
            return {
                "ucf_files": [os.path.basename(f) for f in ucf_files],
                "message": f"Found {len(ucf_files)} UCF files for {organism}. No specific requirements provided."
            }
        
        # Prepare search terms
        search_terms = []
        
        if inducers:
            for inducer in inducers:
                inducer_key = inducer.lower().strip()
                if inducer_key in inducer_map:
                    search_terms.extend(inducer_map[inducer_key])
                else:
                    return {
                        "error": f"Unsupported inducer: {inducer}. Supported inducers are: arabinose, IPTG, aTc, 3OC6HSL"
                    }
        
        if gate_types:
            for gate_type in gate_types:
                gate_key = gate_type.lower().strip()
                if gate_key in gate_type_map:
                    search_terms.extend(gate_type_map[gate_key])
                else:
                    return {
                        "error": f"Unsupported gate type: {gate_type}. Supported gate types are: NOT, NOR, AND, OR, NAND, XOR"
                    }
        
        # Check each UCF file for the search terms
        matching_files = []
        
        for ucf_file in ucf_files:
            file_name = os.path.basename(ucf_file)
            
            # Use grep to search for terms in the file
            matches = {}
            for term in search_terms:
                try:
                    # Use grep to search for the term
                    result = os.popen(f"grep -i '{term}' '{ucf_file}' | wc -l").read().strip()
                    count = int(result)
                    if count > 0:
                        matches[term] = count
                except Exception as e:
                    print(f"Error searching for {term} in {file_name}: {e}")
            
            if matches:
                matching_files.append({
                    "file": file_name,
                    "path": ucf_file,
                    "matches": matches
                })
        
        if not matching_files:
            return {
                "error": f"No UCF files found matching the specified requirements: organism={organism}, inducers={inducers}, gate_types={gate_types}",
                "available_files": [os.path.basename(f) for f in ucf_files]
            }
        
        # Sort matching files by number of matches
        matching_files.sort(key=lambda x: sum(x["matches"].values()), reverse=True)
        
        return {
            "matching_files": matching_files,
            "message": f"Found {len(matching_files)} UCF files matching your requirements."
        }

    def analyze_and_select_library_func(self, user_request: str):
        """
        Analyze a user request and select the most appropriate library.
        
        Args:
            user_request: The user's request describing their circuit design needs
            
        Returns:
            Dict containing the selected library and analysis results
        """
        # Create a library selector
        library_selector = LLMBasedLibrarySelector()
        
        # Analyze the request and select a library
        result = library_selector.select_library(user_request)
        
        # If a library was selected, get its metadata
        if result["success"]:
            library_id = result["library_id"]
            metadata = library_selector.get_library_metadata(library_id)
            result["metadata"] = metadata
            
            # Update the library in the Cello integration if available
            if hasattr(self, "cello_integration") and self.cello_integration:
                self.cello_integration.select_library(library_id)
        
        return result
    
    def create_custom_ucf_func(self, selected_gates: List[str], selected_parts: List[str], modified_parts: Dict[str, Dict], ucf_name: str):
        """
        Create a customized UCF file with selected parts.
        
        Args:
            selected_gates: List of gate IDs to include in the UCF
            selected_parts: List of part IDs to include in the UCF
            modified_parts: Dictionary of parts to modify in the UCF
            ucf_name: Name of the UCF file to create
        
        Returns:
            Dict containing the path to the created UCF file
        """
        # Create a library manager to access the selected library
        self.library_data
        ucf_customizer = UCFCustomizer(base_ucf=self.library_data)
        custom_ucf_path = ucf_customizer.create_custom_ucf(selected_gates, selected_parts, modified_parts, ucf_name)
        return {
            "success": True,
            "custom_ucf_path": custom_ucf_path
        }
        
        
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
        if function_name == "find_gates_by_type":
            gate_type = function_args["gate_type"]
            return self.find_gates_by_type_func(gate_type)
        elif function_name == "get_gate_info":
            gate_id = function_args["gate_id"]
            return self.get_gate_info_func(gate_id)
        elif function_name == "simulate_circuit":
            circuit_spec = function_args["circuit_spec"]
            return self.simulate_circuit_func(circuit_spec)
        elif function_name == "list_promoters":
            return self.list_promoters_func()
        elif function_name == "choose_repressor":
            family = function_args.get("family", None)
            return self.choose_repressor_func(family)
        elif function_name == "get_dna_part_by_name":
            name = function_args["name"]
            return self.get_dna_part_by_name_func(name)
        elif function_name == "list_terminators":
            return self.list_terminators_func()
        elif function_name == "list_misc_items":
            return self.list_misc_items_func()
        elif function_name == "design_with_cello":
            verilog_code = function_args["verilog_code"]
            config = function_args.get("config", None)
            return self.design_with_cello_func(verilog_code, config)
        elif function_name == "create_custom_ucf":
            selected_gates = function_args.get("selected_gates", None)
            selected_parts = function_args.get("selected_parts", None)
            modified_parts = function_args.get("modified_parts", None)
            ucf_name = function_args.get("ucf_name", "")
            return self.create_custom_ucf_func(selected_gates, selected_parts, modified_parts, ucf_name)
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
        elif function_name == "find_ucf_file":
            organism = function_args["organism"]
            inducers = function_args.get("inducers", None)
            gate_types = function_args.get("gate_types", None)
            return self.find_ucf_file_func(organism, inducers, gate_types)
        elif function_name == "design_circuit":
            verilog_code = function_args["verilog_code"]
            organism = function_args["organism"]
            inducers = function_args.get("inducers", None)
            outputs = function_args.get("outputs", None)
            gate_types = function_args.get("gate_types", None)
            config = function_args.get("config", None)
            return self.design_circuit_func(verilog_code, organism, inducers, outputs, gate_types, config)
        elif function_name == "analyze_and_select_library":
            user_request = function_args["user_request"]
            return self.analyze_and_select_library_func(user_request)
        elif function_name == "get_ucf_metadata":
            return self.get_ucf_metadata_func()
        elif function_name == "llm_select_ucf":
            user_request = function_args["user_request"]
            llm_reasoning = function_args["llm_reasoning"]
            return self.llm_select_ucf_func(user_request, llm_reasoning)
        elif function_name == "evaluate_circuit_performance":
            output_path = function_args["output_path"]
            return self.evaluate_circuit_performance_func(output_path)
        else:
            return {"error": f"No such function: {function_name}"}

    def design_circuit_func(self, verilog_code: str, organism: str, inducers: list = None, 
                           outputs: list = None, gate_types: list = None, config: dict = None):
        """
        Design a genetic circuit with automatic UCF file selection based on requirements.
        
        Args:
            verilog_code: Verilog code for the circuit
            organism: Target organism (e.g., 'E. coli')
            inducers: List of inducers required (e.g., ['arabinose', 'IPTG'])
            outputs: List of outputs required (e.g., ['GFP', 'RFP'])
            gate_types: List of gate types required (e.g., ['NOT', 'NOR'])
            config: Optional Cello configuration
            
        Returns:
            Dict with design results or error
        """
        from src.design_module import DesignOrchestrator
        
        # Initialize the design orchestrator
        orchestrator = DesignOrchestrator(self)
        
        # Design the circuit with automatic UCF selection
        return orchestrator.design_circuit(
            verilog_code=verilog_code,
            organism=organism,
            inducers=inducers,
            outputs=outputs,
            gate_types=gate_types,
            cello_config=config
        )

    def list_promoters_func(self):
        """
        Return a list of promoter parts from the selected library.
        """
        try:
            from src.library.ucf_retrieval import list_promoters
            promoters = list_promoters(self.library_data)
            return {
                "promoters": [
                    {
                        "id": p.get("id", "unknown"),
                        "type": p.get("type", "promoter"),
                        "sequence": p.get("sequence", "")[:50] + "..." if p.get("sequence") and len(p.get("sequence")) > 50 else p.get("sequence", "")
                    } 
                    for p in promoters
                ],
                "count": len(promoters)
            }
        except Exception as e:
            return {"error": f"Error listing promoters: {str(e)}"}

    def choose_repressor_func(self, family=None):
        """
        Return a list of possible repressors. Optionally filter by family.
        """
        try:
            from src.library.ucf_retrieval import choose_repressor
            repressors = choose_repressor(self.library_data, family)
            return {
                "repressors": [
                    {
                        "id": r.get("id", "unknown"),
                        "type": r.get("type", "repressor"),
                        "sequence": r.get("sequence", "")[:50] + "..." if r.get("sequence") and len(r.get("sequence")) > 50 else r.get("sequence", "")
                    }
                    for r in repressors
                ],
                "count": len(repressors)
            }
        except Exception as e:
            return {"error": f"Error choosing repressor: {str(e)}"}

    def get_dna_part_by_name_func(self, name):
        """
        Get a specific DNA part by name.
        """
        try:
            from src.library.ucf_retrieval import get_dna_part_by_name
            part = get_dna_part_by_name(self.library_data, name)
            if part:
                return {
                    "id": part.get("id", "unknown"),
                    "type": part.get("type", "dna_part"),
                    "sequence": part.get("sequence", ""),
                    "raw_data": part.get("raw_data", {})
                }
            else:
                return {"error": f"DNA part with name '{name}' not found"}
        except Exception as e:
            return {"error": f"Error getting DNA part: {str(e)}"}

    def list_terminators_func(self):
        """
        Return a list of terminator parts from the selected library.
        """
        try:
            from src.library.ucf_retrieval import list_terminators
            terminators = list_terminators(self.library_data)
            return {
                "terminators": [
                    {
                        "id": t.get("id", "unknown"),
                        "type": t.get("type", "terminator"),
                        "sequence": t.get("sequence", "")[:50] + "..." if t.get("sequence") and len(t.get("sequence")) > 50 else t.get("sequence", "")
                    }
                    for t in terminators
                ],
                "count": len(terminators)
            }
        except Exception as e:
            return {"error": f"Error listing terminators: {str(e)}"}

    def list_misc_items_func(self):
        """
        Return a list of miscellaneous items from the selected library.
        """
        try:
            from src.library.ucf_retrieval import list_misc_items
            items = list_misc_items(self.library_data)
            return {
                "items": [
                    {
                        "id": item.get("id", f"item_{i}"),
                        "type": item.get("type", "unknown"),
                        "category": item.get("category", "misc")
                    }
                    for i, item in enumerate(items)
                ],
                "count": len(items)
            }
        except Exception as e:
            return {"error": f"Error listing misc items: {str(e)}"}

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

