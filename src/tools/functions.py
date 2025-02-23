# tools/functions.py

import json
from src.library.ucf_retrieval import choose_repressor, get_dna_part_by_name, get_gate_by_id, get_gates_by_type, list_misc_items, list_promoters, list_terminators


tool_functions = [
    {
        "name": "find_gates_by_type",
        "description": "Find all gates in the library that match a certain type (e.g. NOR, AND, NOT).",
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
        "description": "Retrieve metadata for a specific gate by ID.",
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
        "description": "Return a list of promoter parts from the library.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "choose_repressor",
        "description": "Return a list of possible repressors. Optionally filter by family.",
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
        "description": "Get a specific DNA part by name (like 'pTet').",
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
        "description": "Return a list of terminator parts from the library.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "list_misc_items",
        "description": "Return a list of miscellaneous items from the library.",
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
        from tools.cello_integration import CelloIntegration
        
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


    def call_tool_function(self, function_name, function_args):
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
            return list_promoters(self.library_data)
        elif function_name == "choose_repressor":
            fam = function_args.get("family", None)
            return choose_repressor(self.library_data, fam)
        elif function_name == "get_dna_part_by_name":
            return get_dna_part_by_name(self.library_data, function_args["name"])
        elif function_name == "list_terminators":
            return list_terminators(self.library_data)
        elif function_name == "list_misc_items":
            return list_misc_items(self.library_data)
        elif function_name == "design_with_cello":
            verilog = function_args["verilog_code"]
            config = function_args.get("config", None)
            return self.design_with_cello_func(verilog, config)
        else:
            return {"error": f"No such function: {function_name}"}

