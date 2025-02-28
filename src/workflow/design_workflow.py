import os
import json
import uuid
from typing import Dict, List, Optional, Tuple, Union

class CircuitDesignWorkflow:
    """
    Manages the workflow for multi-stage genetic circuit design.
    """
    def __init__(self, output_dir: str = "outputs/circuit_designs"):
        """Initialize with output directory."""
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate a unique session ID
        self.session_id = str(uuid.uuid4())
        self.session_dir = os.path.join(output_dir, self.session_id)
        os.makedirs(self.session_dir, exist_ok=True)
        
        # Initialize session state
        self.state = {
            "session_id": self.session_id,
            "current_stage": "initialization",
            "selected_parts": {},
            "custom_ucf_path": None,
            "verilog_code": None,
            "cello_results": None,
            "simulations": [],
            "iterations": 0,
            "final_design": None
        }
        
        # Save initial state
        self._save_state()
    
    def _save_state(self):
        """Save the current workflow state."""
        state_path = os.path.join(self.session_dir, "workflow_state.json")
        with open(state_path, 'w') as f:
            json.dump(self.state, f, indent=2)
    
    def update_stage(self, stage: str):
        """Update the current workflow stage."""
        self.state["current_stage"] = stage
        self.state["iterations"] += 1
        self._save_state()
        
        return {
            "session_id": self.session_id,
            "current_stage": stage,
            "iterations": self.state["iterations"],
            "message": f"Workflow advanced to stage: {stage}"
        }
    
    def select_parts(self, 
                    promoters: List[str] = None, 
                    repressors: List[str] = None,
                    terminators: List[str] = None,
                    other_parts: Dict[str, List[str]] = None):
        """
        Select parts for the circuit design.
        
        Args:
            promoters: List of promoter IDs
            repressors: List of repressor IDs
            terminators: List of terminator IDs
            other_parts: Dict of category -> list of part IDs
        """
        if promoters:
            self.state["selected_parts"]["promoters"] = promoters
        
        if repressors:
            self.state["selected_parts"]["repressors"] = repressors
            
        if terminators:
            self.state["selected_parts"]["terminators"] = terminators
            
        if other_parts:
            for category, parts in other_parts.items():
                self.state["selected_parts"][category] = parts
        
        self._save_state()
        
        return {
            "session_id": self.session_id,
            "selected_parts": self.state["selected_parts"],
            "message": "Parts selection updated"
        }
    
    def set_custom_ucf(self, ucf_path: str):
        """Set the path to a custom UCF file."""
        self.state["custom_ucf_path"] = ucf_path
        self._save_state()
        
        return {
            "session_id": self.session_id,
            "custom_ucf_path": ucf_path,
            "message": "Custom UCF path set"
        }
    
    def set_verilog_code(self, code: str):
        """Set the Verilog code for the circuit."""
        # Save the Verilog to a file
        verilog_path = os.path.join(self.session_dir, "circuit.v")
        with open(verilog_path, 'w') as f:
            f.write(code)
            
        self.state["verilog_code"] = code
        self.state["verilog_path"] = verilog_path
        self._save_state()
        
        return {
            "session_id": self.session_id,
            "verilog_path": verilog_path,
            "message": "Verilog code set and saved"
        }
    
    def save_cello_results(self, results: Dict):
        """Save results from a Cello run."""
        self.state["cello_results"] = results
        
        # Save the full results to a separate file
        results_path = os.path.join(self.session_dir, f"cello_results_{self.state['iterations']}.json")
        with open(results_path, 'w') as f:
            json.dump(results, f, indent=2)
            
        self._save_state()
        
        return {
            "session_id": self.session_id,
            "results_path": results_path,
            "message": "Cello results saved"
        }
    
    def add_simulation_result(self, simulation: Dict):
        """Add a simulation result to the workflow."""
        self.state["simulations"].append(simulation)
        self._save_state()
        
        return {
            "session_id": self.session_id,
            "simulation_count": len(self.state["simulations"]),
            "message": "Simulation result added"
        }
    
    def finalize_design(self, design: Dict):
        """Finalize the circuit design."""
        self.state["final_design"] = design
        self.state["current_stage"] = "completed"
        
        # Save the final design to a separate file
        design_path = os.path.join(self.session_dir, "final_design.json")
        with open(design_path, 'w') as f:
            json.dump(design, f, indent=2)
            
        self._save_state()
        
        return {
            "session_id": self.session_id,
            "design_path": design_path,
            "message": "Circuit design finalized"
        }
    
    def get_workflow_summary(self):
        """Get a summary of the current workflow state."""
        return {
            "session_id": self.session_id,
            "current_stage": self.state["current_stage"],
            "iterations": self.state["iterations"],
            "parts_selected": bool(self.state["selected_parts"]),
            "custom_ucf_created": bool(self.state["custom_ucf_path"]),
            "verilog_defined": bool(self.state["verilog_code"]),
            "cello_run": bool(self.state["cello_results"]),
            "simulations_count": len(self.state["simulations"]),
            "design_finalized": bool(self.state["final_design"]),
            "session_dir": self.session_dir
        } 