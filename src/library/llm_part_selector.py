import os
import json
import re
import logging
from typing import Dict, List, Optional, Any, Tuple, Set

class LLMPartSelector:
    """
    A class for selecting appropriate genetic parts (gates, sensors, reporters) for Cello
    based on user requests and LLM reasoning.
    """
    
    def __init__(self, ucf_path: str):
        """
        Initialize the part selector with the path to the UCF file.
        
        Args:
            ucf_path: Path to the UCF file containing part information
        """
        self.ucf_path = ucf_path
        self.parts_data = self._load_parts_from_ucf()
        self.logger = logging.getLogger(__name__)
    
    def _load_parts_from_ucf(self) -> Dict[str, Any]:
        """
        Load and parse parts information from the UCF file.
        
        Returns:
            Dictionary containing categorized parts data
        """
        try:
            if not os.path.exists(self.ucf_path):
                self.logger.error(f"UCF file not found: {self.ucf_path}")
                return {
                    "gates": [],
                    "sensors": [],
                    "reporters": [],
                    "other_parts": []
                }
            
            with open(self.ucf_path, 'r') as f:
                ucf_data = json.load(f)
            
            # Extract and categorize parts
            parts_data = {
                "gates": [],
                "sensors": [],
                "reporters": [],
                "other_parts": []
            }
            
            # Process collection elements
            for collection in ucf_data.get("collection", []):
                if collection.get("type") == "gate":
                    parts_data["gates"].append(collection)
                elif collection.get("type") == "sensor":
                    parts_data["sensors"].append(collection)
                elif collection.get("type") == "reporter":
                    parts_data["reporters"].append(collection)
                else:
                    parts_data["other_parts"].append(collection)
            
            return parts_data
            
        except Exception as e:
            self.logger.error(f"Error loading parts from UCF: {str(e)}")
            return {
                "gates": [],
                "sensors": [],
                "reporters": [],
                "other_parts": []
            }
    
    def get_available_parts(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get information about all available parts categorized by type.
        
        Returns:
            Dictionary with categorized parts and their metadata
        """
        result = {}
        
        for category, parts in self.parts_data.items():
            result[category] = []
            for part in parts:
                part_info = {
                    "name": part.get("name", "Unknown"),
                    "description": self._extract_part_description(part),
                    "properties": self._extract_part_properties(part)
                }
                result[category].append(part_info)
        
        return result
    
    def _extract_part_description(self, part: Dict[str, Any]) -> str:
        """
        Extract a human-readable description from a part.
        
        Args:
            part: Part data dictionary
            
        Returns:
            Human-readable description of the part
        """
        # Try to extract meaningful description from part data
        if "description" in part:
            return part["description"]
        
        # For gates, include information about the gate type
        if part.get("type") == "gate":
            gate_type = part.get("gate_type", "")
            if gate_type:
                return f"{gate_type} gate: {part.get('name', '')}"
        
        # For sensors, include information about what they sense
        if part.get("type") == "sensor":
            sensing = part.get("sensing", "")
            if sensing:
                return f"Sensor for {sensing}: {part.get('name', '')}"
        
        # For reporters, include information about the reporter type
        if part.get("type") == "reporter":
            reporter_type = part.get("reporter_type", "")
            if reporter_type:
                return f"{reporter_type} reporter: {part.get('name', '')}"
        
        return part.get("name", "Unknown part")
    
    def _extract_part_properties(self, part: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract relevant properties from a part.
        
        Args:
            part: Part data dictionary
            
        Returns:
            Dictionary of relevant properties
        """
        properties = {}
        
        # Common properties
        if "type" in part:
            properties["type"] = part["type"]
        
        # Gate-specific properties
        if part.get("type") == "gate":
            if "gate_type" in part:
                properties["gate_type"] = part["gate_type"]
            if "gate_toxicity" in part:
                properties["toxicity"] = part["gate_toxicity"]
            if "gate_function" in part:
                properties["function"] = part["gate_function"]
        
        # Sensor-specific properties
        if part.get("type") == "sensor":
            if "sensing" in part:
                properties["senses"] = part["sensing"]
            if "sensitivity" in part:
                properties["sensitivity"] = part["sensitivity"]
        
        # Reporter-specific properties
        if part.get("type") == "reporter":
            if "reporter_type" in part:
                properties["reporter_type"] = part["reporter_type"]
            if "output" in part:
                properties["output"] = part["output"]
        
        return properties
    
    def select_parts(self, user_request: str, llm_reasoning: str = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Select appropriate parts based on user request and LLM reasoning.
        
        Args:
            user_request: User's request describing the desired circuit behavior
            llm_reasoning: Optional reasoning from an LLM about part selection
            
        Returns:
            Dictionary with selected parts categorized by type
        """
        # Extract requirements from user request
        requirements = self._extract_requirements(user_request)
        
        # If LLM reasoning is provided, extract additional requirements
        if llm_reasoning:
            llm_requirements = self._extract_requirements(llm_reasoning)
            # Merge requirements, with LLM requirements taking precedence
            for key, value in llm_requirements.items():
                if key in requirements and isinstance(requirements[key], list) and isinstance(value, list):
                    # Merge lists without duplicates
                    requirements[key] = list(set(requirements[key] + value))
                else:
                    requirements[key] = value
        
        # Select parts based on requirements
        selected_parts = {
            "gates": self._select_gates(requirements),
            "sensors": self._select_sensors(requirements),
            "reporters": self._select_reporters(requirements)
        }
        
        return selected_parts
    
    def _extract_requirements(self, text: str) -> Dict[str, Any]:
        """
        Extract circuit requirements from text.
        
        Args:
            text: Text to extract requirements from
            
        Returns:
            Dictionary of extracted requirements
        """
        requirements = {
            "inputs": [],
            "outputs": [],
            "logic_functions": [],
            "gate_types": [],
            "constraints": []
        }
        
        # Extract inputs (what the circuit should sense)
        input_patterns = [
            r'sense\s+([a-zA-Z0-9\s,]+)',
            r'detect\s+([a-zA-Z0-9\s,]+)',
            r'input\s+(?:is|are|:)?\s+([a-zA-Z0-9\s,]+)'
        ]
        
        for pattern in input_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                inputs = [inp.strip() for inp in re.split(r'(?:,|\sand\s)', match) if inp.strip()]
                requirements["inputs"].extend(inputs)
        
        # Extract outputs (what the circuit should produce)
        output_patterns = [
            r'produce\s+([a-zA-Z0-9\s,]+)',
            r'output\s+(?:is|are|:)?\s+([a-zA-Z0-9\s,]+)',
            r'express\s+([a-zA-Z0-9\s,]+)'
        ]
        
        for pattern in output_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                outputs = [out.strip() for out in re.split(r'(?:,|\sand\s)', match) if out.strip()]
                requirements["outputs"].extend(outputs)
        
        # Extract logic functions
        logic_patterns = [
            r'(AND|OR|NOT|NOR|NAND|XOR|XNOR)\s+gate',
            r'(AND|OR|NOT|NOR|NAND|XOR|XNOR)\s+logic',
            r'logic\s+(?:is|:)?\s+(AND|OR|NOT|NOR|NAND|XOR|XNOR)'
        ]
        
        for pattern in logic_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            requirements["logic_functions"].extend([match.upper() for match in matches])
        
        # Extract constraints
        constraint_patterns = [
            r'low\s+toxicity',
            r'high\s+sensitivity',
            r'minimal\s+leakage',
            r'robust\s+performance'
        ]
        
        for pattern in constraint_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                requirements["constraints"].append(pattern.strip())
        
        # Remove duplicates
        for key in requirements:
            if isinstance(requirements[key], list):
                requirements[key] = list(set(requirements[key]))
        
        return requirements
    
    def _select_gates(self, requirements: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Select appropriate gates based on requirements.
        
        Args:
            requirements: Dictionary of circuit requirements
            
        Returns:
            List of selected gates
        """
        selected_gates = []
        available_gates = self.parts_data["gates"]
        
        # Filter gates based on logic functions
        if requirements.get("logic_functions"):
            for logic_function in requirements["logic_functions"]:
                matching_gates = [
                    gate for gate in available_gates
                    if logic_function.upper() in gate.get("gate_type", "").upper()
                ]
                
                if matching_gates:
                    # Sort by relevance (e.g., toxicity if that's a constraint)
                    if "low toxicity" in requirements.get("constraints", []):
                        matching_gates.sort(key=lambda g: g.get("gate_toxicity", 1.0))
                    
                    # Add the best matching gate
                    selected_gates.append(matching_gates[0])
        
        # If no specific logic functions are requested, select a default set
        if not selected_gates:
            # Include at least one NOT gate and one AND gate as a basic set
            not_gates = [gate for gate in available_gates if "NOT" in gate.get("gate_type", "").upper()]
            and_gates = [gate for gate in available_gates if "AND" in gate.get("gate_type", "").upper()]
            
            if not_gates:
                selected_gates.append(not_gates[0])
            if and_gates:
                selected_gates.append(and_gates[0])
        
        return selected_gates
    
    def _select_sensors(self, requirements: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Select appropriate sensors based on requirements.
        
        Args:
            requirements: Dictionary of circuit requirements
            
        Returns:
            List of selected sensors
        """
        selected_sensors = []
        available_sensors = self.parts_data["sensors"]
        
        # Match sensors to requested inputs
        for input_req in requirements.get("inputs", []):
            matching_sensors = []
            
            for sensor in available_sensors:
                sensing = sensor.get("sensing", "").lower()
                if input_req.lower() in sensing or any(word in sensing for word in input_req.lower().split()):
                    matching_sensors.append(sensor)
            
            if matching_sensors:
                # Sort by relevance (e.g., sensitivity if that's a constraint)
                if "high sensitivity" in requirements.get("constraints", []):
                    matching_sensors.sort(key=lambda s: s.get("sensitivity", 0.0), reverse=True)
                
                # Add the best matching sensor
                selected_sensors.append(matching_sensors[0])
        
        # If no sensors were selected but inputs are required, select default sensors
        if not selected_sensors and requirements.get("inputs"):
            # Select the first available sensor as a fallback
            if available_sensors:
                selected_sensors.append(available_sensors[0])
        
        return selected_sensors
    
    def _select_reporters(self, requirements: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Select appropriate reporters based on requirements.
        
        Args:
            requirements: Dictionary of circuit requirements
            
        Returns:
            List of selected reporters
        """
        selected_reporters = []
        available_reporters = self.parts_data["reporters"]
        
        # Match reporters to requested outputs
        for output_req in requirements.get("outputs", []):
            matching_reporters = []
            
            for reporter in available_reporters:
                output = reporter.get("output", "").lower()
                reporter_type = reporter.get("reporter_type", "").lower()
                
                if (output_req.lower() in output or 
                    output_req.lower() in reporter_type or
                    any(word in output for word in output_req.lower().split()) or
                    any(word in reporter_type for word in output_req.lower().split())):
                    matching_reporters.append(reporter)
            
            if matching_reporters:
                # Add the best matching reporter
                selected_reporters.append(matching_reporters[0])
        
        # If no reporters were selected but outputs are required, select default reporters
        if not selected_reporters and requirements.get("outputs"):
            # Select the first available reporter as a fallback
            if available_reporters:
                selected_reporters.append(available_reporters[0])
        
        return selected_reporters
    
    def explain_selection(self, selected_parts: Dict[str, List[Dict[str, Any]]], user_request: str) -> str:
        """
        Generate an explanation for why specific parts were selected.
        
        Args:
            selected_parts: Dictionary of selected parts
            user_request: Original user request
            
        Returns:
            Explanation string
        """
        explanation = "Part Selection Explanation:\n\n"
        
        # Extract requirements for reference
        requirements = self._extract_requirements(user_request)
        
        # Explain gate selection
        explanation += "Gates:\n"
        if selected_parts.get("gates"):
            for gate in selected_parts["gates"]:
                gate_type = gate.get("gate_type", "Unknown type")
                gate_name = gate.get("name", "Unknown")
                explanation += f"- Selected {gate_type} gate '{gate_name}' "
                
                # Explain why this gate was selected
                if gate_type.upper() in [logic.upper() for logic in requirements.get("logic_functions", [])]:
                    explanation += f"because you requested {gate_type} logic functionality.\n"
                else:
                    explanation += "as a basic component for your circuit.\n"
        else:
            explanation += "- No gates were selected.\n"
        
        # Explain sensor selection
        explanation += "\nSensors:\n"
        if selected_parts.get("sensors"):
            for sensor in selected_parts["sensors"]:
                sensor_name = sensor.get("name", "Unknown")
                sensing = sensor.get("sensing", "Unknown")
                explanation += f"- Selected sensor '{sensor_name}' that detects {sensing} "
                
                # Explain why this sensor was selected
                matching_inputs = [inp for inp in requirements.get("inputs", []) 
                                  if inp.lower() in sensing.lower() or 
                                  any(word in sensing.lower() for word in inp.lower().split())]
                
                if matching_inputs:
                    explanation += f"because you requested to sense {', '.join(matching_inputs)}.\n"
                else:
                    explanation += "as a default sensor for your circuit.\n"
        else:
            explanation += "- No sensors were selected.\n"
        
        # Explain reporter selection
        explanation += "\nReporters:\n"
        if selected_parts.get("reporters"):
            for reporter in selected_parts["reporters"]:
                reporter_name = reporter.get("name", "Unknown")
                output = reporter.get("output", "Unknown")
                reporter_type = reporter.get("reporter_type", "")
                
                explanation += f"- Selected reporter '{reporter_name}' that produces {output} "
                
                # Explain why this reporter was selected
                matching_outputs = [out for out in requirements.get("outputs", []) 
                                   if out.lower() in output.lower() or 
                                   out.lower() in reporter_type.lower() or
                                   any(word in output.lower() for word in out.lower().split()) or
                                   any(word in reporter_type.lower() for word in out.lower().split())]
                
                if matching_outputs:
                    explanation += f"because you requested to produce {', '.join(matching_outputs)}.\n"
                else:
                    explanation += "as a default reporter for your circuit.\n"
        else:
            explanation += "- No reporters were selected.\n"
        
        return explanation 