import os
import json
import logging
from typing import Dict, List, Optional, Any, Tuple

from .llm_file_selector import LLMFileSelector
from .llm_part_selector import LLMPartSelector

class LLMCelloDesigner:
    """
    A class that integrates file selection and part selection for Cello,
    providing a unified interface for LLM-based circuit design.
    """
    
    def __init__(self, 
                 ucf_dir: str, 
                 input_dir: str, 
                 output_dir: str,
                 organism_prefixes: Optional[Dict[str, str]] = None):
        """
        Initialize the Cello designer with paths to UCF, input, and output directories.
        
        Args:
            ucf_dir: Directory containing UCF files
            input_dir: Directory containing input files
            output_dir: Directory containing output files
            organism_prefixes: Optional dictionary mapping organism names to their file prefixes
        """
        self.ucf_dir = ucf_dir
        self.input_dir = input_dir
        self.output_dir = output_dir
        
        # Initialize file selector
        self.file_selector = LLMFileSelector(
            ucf_dir=ucf_dir,
            input_dir=input_dir,
            output_dir=output_dir,
            organism_prefixes=organism_prefixes
        )
        
        # Part selector will be initialized when a UCF file is selected
        self.part_selector = None
        
        self.logger = logging.getLogger(__name__)
        
        # Store selected files and parts
        self.selected_files = None
        self.selected_parts = None
    
    def process_user_request(self, user_request: str, llm_reasoning: Optional[str] = None) -> Dict[str, Any]:
        """
        Process a user request to select appropriate files and parts for Cello.
        
        Args:
            user_request: User's request describing the desired circuit behavior
            llm_reasoning: Optional reasoning from an LLM about file and part selection
            
        Returns:
            Dictionary containing selected files and parts
        """
        # Step 1: Select appropriate files based on user request
        self.selected_files = self.file_selector.select_files(user_request, llm_reasoning)
        
        # Step 2: Initialize part selector with the selected UCF file
        if self.selected_files and "ucf" in self.selected_files:
            ucf_path = self.selected_files["ucf"]
            self.part_selector = LLMPartSelector(ucf_path)
            
            # Step 3: Select appropriate parts based on user request
            self.selected_parts = self.part_selector.select_parts(user_request, llm_reasoning)
        else:
            self.logger.warning("No UCF file selected, cannot select parts")
            self.selected_parts = {
                "gates": [],
                "sensors": [],
                "reporters": []
            }
        
        # Return combined results
        return {
            "selected_files": self.selected_files,
            "selected_parts": self.selected_parts
        }
    
    def get_available_files(self) -> Dict[str, Any]:
        """
        Get information about all available files.
        
        Returns:
            Dictionary with information about available files
        """
        return self.file_selector.get_available_files()
    
    def get_available_parts(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get information about all available parts from the selected UCF file.
        
        Returns:
            Dictionary with information about available parts
        """
        if self.part_selector:
            return self.part_selector.get_available_parts()
        else:
            self.logger.warning("Part selector not initialized, no UCF file selected")
            return {
                "gates": [],
                "sensors": [],
                "reporters": [],
                "other_parts": []
            }
    
    def explain_selection(self, user_request: str) -> Dict[str, str]:
        """
        Generate explanations for why specific files and parts were selected.
        
        Args:
            user_request: Original user request
            
        Returns:
            Dictionary containing explanations for file and part selection
        """
        explanations = {}
        
        # Get file selection explanation
        if self.selected_files:
            file_explanation = self._explain_file_selection(user_request)
            explanations["file_selection"] = file_explanation
        
        # Get part selection explanation
        if self.selected_parts and self.part_selector:
            part_explanation = self.part_selector.explain_selection(self.selected_parts, user_request)
            explanations["part_selection"] = part_explanation
        
        return explanations
    
    def _explain_file_selection(self, user_request: str) -> str:
        """
        Generate an explanation for why specific files were selected.
        
        Args:
            user_request: Original user request
            
        Returns:
            Explanation string
        """
        explanation = "File Selection Explanation:\n\n"
        
        if not self.selected_files:
            return explanation + "No files were selected."
        
        # Explain UCF file selection
        if "ucf" in self.selected_files:
            ucf_path = self.selected_files["ucf"]
            ucf_filename = os.path.basename(ucf_path)
            
            # Extract organism information if available
            organism = "unknown organism"
            try:
                with open(ucf_path, 'r') as f:
                    ucf_data = json.load(f)
                    if "organism" in ucf_data:
                        organism = ucf_data["organism"]
            except Exception as e:
                self.logger.error(f"Error reading UCF file: {str(e)}")
            
            explanation += f"UCF File: Selected '{ucf_filename}' for {organism}.\n"
            
            # Check if organism was mentioned in the request
            if organism.lower() in user_request.lower():
                explanation += f"  Reason: You specifically mentioned {organism} in your request.\n"
            else:
                explanation += "  Reason: This UCF file contains the necessary parts for your circuit design.\n"
        else:
            explanation += "UCF File: No UCF file was selected.\n"
        
        # Explain input file selection
        if "input" in self.selected_files:
            input_path = self.selected_files["input"]
            input_filename = os.path.basename(input_path)
            explanation += f"\nInput File: Selected '{input_filename}'.\n"
            explanation += "  Reason: This input file contains the necessary circuit specifications.\n"
        else:
            explanation += "\nInput File: No input file was selected.\n"
        
        # Explain output file selection
        if "output" in self.selected_files:
            output_path = self.selected_files["output"]
            output_filename = os.path.basename(output_path)
            explanation += f"\nOutput File: Selected '{output_filename}'.\n"
            explanation += "  Reason: This output file will store the results of your circuit design.\n"
        else:
            explanation += "\nOutput File: No output file was selected.\n"
        
        return explanation
    
    def generate_verilog(self, user_request: str) -> str:
        """
        Generate Verilog code based on the selected parts and user request.
        
        Args:
            user_request: User's request describing the desired circuit behavior
            
        Returns:
            Generated Verilog code as a string
        """
        if not self.selected_parts:
            self.logger.warning("No parts selected, cannot generate Verilog")
            return "// No parts selected, cannot generate Verilog"
        
        # Extract circuit requirements
        if self.part_selector:
            requirements = self.part_selector._extract_requirements(user_request)
        else:
            self.logger.warning("Part selector not initialized, using basic requirements")
            requirements = {
                "inputs": [],
                "outputs": [],
                "logic_functions": []
            }
        
        # Generate Verilog module name
        module_name = "cello_circuit"
        
        # Generate input and output declarations
        inputs = []
        outputs = []
        
        # Add inputs from sensors
        for sensor in self.selected_parts.get("sensors", []):
            sensor_name = sensor.get("name", "unknown_sensor").lower().replace(" ", "_")
            inputs.append(sensor_name)
        
        # If no sensors were found, use requirements
        if not inputs and requirements.get("inputs"):
            for input_req in requirements["inputs"]:
                input_name = input_req.lower().replace(" ", "_")
                inputs.append(input_name)
        
        # Add outputs from reporters
        for reporter in self.selected_parts.get("reporters", []):
            reporter_name = reporter.get("name", "unknown_reporter").lower().replace(" ", "_")
            outputs.append(reporter_name)
        
        # If no reporters were found, use requirements
        if not outputs and requirements.get("outputs"):
            for output_req in requirements["outputs"]:
                output_name = output_req.lower().replace(" ", "_")
                outputs.append(output_name)
        
        # Ensure we have at least one input and output
        if not inputs:
            inputs = ["input_signal"]
        if not outputs:
            outputs = ["output_signal"]
        
        # Start building Verilog code
        verilog_code = f"// Cello Circuit: Generated from user request\n"
        verilog_code += f"// Request: {user_request}\n\n"
        
        # Module declaration
        verilog_code += f"module {module_name}(\n"
        
        # Input declarations
        for i, input_name in enumerate(inputs):
            verilog_code += f"    input {input_name}"
            if i < len(inputs) - 1 or outputs:
                verilog_code += ","
            verilog_code += "\n"
        
        # Output declarations
        for i, output_name in enumerate(outputs):
            verilog_code += f"    output {output_name}"
            if i < len(outputs) - 1:
                verilog_code += ","
            verilog_code += "\n"
        
        verilog_code += ");\n\n"
        
        # Generate wire declarations for intermediate signals
        if len(self.selected_parts.get("gates", [])) > 0:
            verilog_code += "    // Wire declarations for intermediate signals\n"
            for i in range(len(self.selected_parts.get("gates", []))):
                verilog_code += f"    wire w{i};\n"
            verilog_code += "\n"
        
        # Generate gate instantiations
        if self.selected_parts.get("gates"):
            verilog_code += "    // Gate instantiations\n"
            
            # Determine the logic based on selected gates and requirements
            logic_functions = requirements.get("logic_functions", [])
            gates = self.selected_parts.get("gates", [])
            
            # Simple case: direct mapping of inputs to outputs through gates
            if len(gates) == 1:
                gate = gates[0]
                gate_type = gate.get("gate_type", "").upper()
                
                if "NOT" in gate_type:
                    verilog_code += f"    not gate0({outputs[0]}, {inputs[0]});\n"
                elif "AND" in gate_type:
                    if len(inputs) >= 2:
                        verilog_code += f"    and gate0({outputs[0]}, {inputs[0]}, {inputs[1]});\n"
                    else:
                        verilog_code += f"    // Not enough inputs for AND gate\n"
                        verilog_code += f"    assign {outputs[0]} = {inputs[0]};\n"
                elif "OR" in gate_type:
                    if len(inputs) >= 2:
                        verilog_code += f"    or gate0({outputs[0]}, {inputs[0]}, {inputs[1]});\n"
                    else:
                        verilog_code += f"    // Not enough inputs for OR gate\n"
                        verilog_code += f"    assign {outputs[0]} = {inputs[0]};\n"
                else:
                    verilog_code += f"    // Unsupported gate type: {gate_type}\n"
                    verilog_code += f"    assign {outputs[0]} = {inputs[0]};\n"
            
            # More complex case: multiple gates
            elif len(gates) > 1:
                # Create a simple chain of gates
                for i, gate in enumerate(gates):
                    gate_type = gate.get("gate_type", "").upper()
                    
                    # First gate connects to inputs
                    if i == 0:
                        if "NOT" in gate_type:
                            verilog_code += f"    not gate{i}(w{i}, {inputs[0]});\n"
                        elif "AND" in gate_type:
                            if len(inputs) >= 2:
                                verilog_code += f"    and gate{i}(w{i}, {inputs[0]}, {inputs[1]});\n"
                            else:
                                verilog_code += f"    assign w{i} = {inputs[0]};\n"
                        elif "OR" in gate_type:
                            if len(inputs) >= 2:
                                verilog_code += f"    or gate{i}(w{i}, {inputs[0]}, {inputs[1]});\n"
                            else:
                                verilog_code += f"    assign w{i} = {inputs[0]};\n"
                        else:
                            verilog_code += f"    // Unsupported gate type: {gate_type}\n"
                            verilog_code += f"    assign w{i} = {inputs[0]};\n"
                    
                    # Last gate connects to outputs
                    elif i == len(gates) - 1:
                        if "NOT" in gate_type:
                            verilog_code += f"    not gate{i}({outputs[0]}, w{i-1});\n"
                        elif "AND" in gate_type:
                            if len(inputs) >= 3:
                                verilog_code += f"    and gate{i}({outputs[0]}, w{i-1}, {inputs[2]});\n"
                            else:
                                verilog_code += f"    assign {outputs[0]} = w{i-1};\n"
                        elif "OR" in gate_type:
                            if len(inputs) >= 3:
                                verilog_code += f"    or gate{i}({outputs[0]}, w{i-1}, {inputs[2]});\n"
                            else:
                                verilog_code += f"    assign {outputs[0]} = w{i-1};\n"
                        else:
                            verilog_code += f"    // Unsupported gate type: {gate_type}\n"
                            verilog_code += f"    assign {outputs[0]} = w{i-1};\n"
                    
                    # Middle gates connect to wires
                    else:
                        if "NOT" in gate_type:
                            verilog_code += f"    not gate{i}(w{i}, w{i-1});\n"
                        elif "AND" in gate_type:
                            if i+1 < len(inputs):
                                verilog_code += f"    and gate{i}(w{i}, w{i-1}, {inputs[i+1]});\n"
                            else:
                                verilog_code += f"    assign w{i} = w{i-1};\n"
                        elif "OR" in gate_type:
                            if i+1 < len(inputs):
                                verilog_code += f"    or gate{i}(w{i}, w{i-1}, {inputs[i+1]});\n"
                            else:
                                verilog_code += f"    assign w{i} = w{i-1};\n"
                        else:
                            verilog_code += f"    // Unsupported gate type: {gate_type}\n"
                            verilog_code += f"    assign w{i} = w{i-1};\n"
            
            # No gates selected
            else:
                verilog_code += f"    // No gates selected\n"
                verilog_code += f"    assign {outputs[0]} = {inputs[0]};\n"
        
        # Close module
        verilog_code += "\nendmodule\n"
        
        return verilog_code 