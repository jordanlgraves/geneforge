import logging
import json
from typing import Dict, List, Optional, Any

from src.tools.functions import ToolIntegration
from src.library.ucf_customizer import UCFCustomizer

class DesignOrchestrator:
    """
    Main orchestrator for the automated genetic circuit design system.
    Handles UCF file selection, circuit design, and validation.
    """
    
    def __init__(self, tool_integration: ToolIntegration):
        """
        Initialize the design orchestrator with a tool integration instance.
        
        Args:
            tool_integration: ToolIntegration instance for accessing tools
        """
        self.tools = tool_integration
        self.logger = logging.getLogger("design_orchestrator")
        self.logger.setLevel(logging.INFO)
    
    def select_ucf_file(self, organism: str, inducers: List[str] = None, 
                        outputs: List[str] = None, gate_types: List[str] = None) -> Dict:
        """
        Select an appropriate UCF file based on user requirements.
        
        Args:
            organism: Target organism (e.g., 'E. coli')
            inducers: List of inducers required (e.g., ['arabinose', 'IPTG'])
            outputs: List of outputs required (e.g., ['GFP', 'RFP'])
            gate_types: List of gate types required (e.g., ['NOT', 'NOR'])
            
        Returns:
            Dict containing selected UCF file information or error
        """
        # First, find matching UCF files based on organism and inducers
        ucf_result = self.tools.find_ucf_file_func(organism, inducers, gate_types)
        
        # Check if there was an error
        if "error" in ucf_result:
            self.logger.error(f"UCF file selection failed: {ucf_result['error']}")
            return ucf_result
        
        # If no matching files found
        if "matching_files" not in ucf_result or not ucf_result["matching_files"]:
            self.logger.warning(f"No matching UCF files found for {organism} with inducers {inducers} and gate types {gate_types}")
            return {
                "error": "No matching UCF files found for the specified requirements",
                "available_files": ucf_result.get("available_files", [])
            }
        
        # Get the best matching UCF file (first in the sorted list)
        best_match = ucf_result["matching_files"][0]
        self.logger.info(f"Selected UCF file: {best_match['file']}")
        
        # If outputs are specified, verify they are in the UCF file
        if outputs:
            # Validate that the UCF file contains the required outputs
            ucf_path = best_match["path"]
            output_validation = self._validate_outputs_in_ucf(ucf_path, outputs)
            
            if not output_validation["valid"]:
                self.logger.warning(f"Selected UCF file does not contain all required outputs: {output_validation['missing']}")
                return {
                    "warning": f"Selected UCF file does not contain all required outputs: {output_validation['missing']}",
                    "ucf_file": best_match,
                    "recommendation": "Consider creating a custom UCF file with the required outputs"
                }
        
        return {
            "success": True,
            "ucf_file": best_match,
            "message": f"Selected UCF file {best_match['file']} matches your requirements"
        }
    
    def select_ucf_with_llm(self, user_request: str, llm_reasoning: str = None) -> Dict:
        """
        Select an appropriate UCF file based on LLM reasoning.
        This method uses the LLM to analyze both the user request and UCF metadata
        to make a more informed decision.
        
        Args:
            user_request: The user's request describing their circuit design needs
            llm_reasoning: Optional LLM reasoning for selecting a particular library.
                          If not provided, the method will use the default selection process.
            
        Returns:
            Dict containing selected UCF file information or error
        """
        self.logger.info(f"Selecting UCF file with LLM for request: {user_request}")
        
        # If LLM reasoning is provided, use it directly
        if llm_reasoning:
            self.logger.info("Using provided LLM reasoning")
            result = self.tools.llm_select_ucf_func(user_request, llm_reasoning)
            return result
        
        # Otherwise, we need to call the LLM to generate reasoning
        try:
            import os
            from openai import OpenAI
            
            # Get API key and determine which client to use
            openai_api_key = os.getenv("OPENAI_API_KEY")
            deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
            deepseek_base_url = os.getenv("DEEPSEEK_BASE_URL")
            
            if deepseek_api_key and deepseek_base_url:
                self.logger.info("Using DeepSeek API")
                client = OpenAI(api_key=deepseek_api_key, base_url=deepseek_base_url)
                model = "deepseek-reasoner"
            elif openai_api_key:
                self.logger.info("Using OpenAI API")
                client = OpenAI(api_key=openai_api_key)
                model = "gpt-4o-mini"  # Use a smaller model for cost efficiency
            else:
                self.logger.error("No API keys found for OpenAI or DeepSeek")
                return {
                    "success": False,
                    "message": "No API keys found for LLM services"
                }
            
            # Get metadata for all available UCF libraries
            ucf_metadata = self.tools.get_ucf_metadata_func()
            
            # Create a system message that explains the task
            system_message = """
            You are an expert in synthetic biology and genetic circuit design.
            Your task is to select the most appropriate UCF (User Constraint File) library for a genetic circuit design request.
            
            A UCF library contains parts, gates, and other components needed for genetic circuit design.
            Each library is specialized for a particular organism (e.g., E. coli, yeast) and contains specific parts and gates.
            
            You will be provided with:
            1. A user request describing their circuit design needs
            2. Metadata for all available UCF libraries
            
            You must analyze the request and select the most appropriate library based on:
            - The organism mentioned in the request
            - The types of gates needed (e.g., NOT, AND, OR)
            - The reporters/outputs needed (e.g., GFP, RFP)
            - The inducers mentioned (e.g., arabinose, IPTG)
            
            Provide your reasoning and clearly state which library you recommend using.
            Your response should follow this format:
            
            REASONING: [Your detailed reasoning for selecting this library]
            SELECTED_LIBRARY: [Library ID, e.g., Eco1C1G1T0]
            """
            
            # Create a user message that includes the request and library metadata
            user_message = f"""
            USER REQUEST: {user_request}
            
            AVAILABLE LIBRARIES:
            {json.dumps(ucf_metadata, indent=2)}
            
            Based on this information, which UCF library would you recommend?
            """
            
            # Call the LLM
            self.logger.info("Calling LLM to select UCF library")
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.2  # Lower temperature for more deterministic responses
            )
            
            # Extract the LLM's response
            llm_response = response.choices[0].message.content
            self.logger.info(f"LLM response: {llm_response}")
            
            # Extract the selected library and reasoning
            import re
            
            # Extract reasoning
            reasoning_match = re.search(r'REASONING:\s*(.*?)(?=SELECTED_LIBRARY:|$)', llm_response, re.DOTALL)
            reasoning = reasoning_match.group(1).strip() if reasoning_match else llm_response
            
            # Extract selected library
            library_match = re.search(r'SELECTED_LIBRARY:\s*([A-Za-z0-9]+)', llm_response)
            selected_library = library_match.group(1) if library_match else None
            
            if not selected_library:
                # Try to find any library ID in the response
                library_pattern = r'\b([A-Za-z]{2,3}\d+[A-Za-z]\d+[A-Za-z]\d+[A-Za-z]\d+)\b'
                matches = re.findall(library_pattern, llm_response)
                if matches:
                    selected_library = matches[0]
            
            # If we found a library, use it
            if selected_library:
                self.logger.info(f"LLM selected library: {selected_library}")
                result = self.tools.llm_select_ucf_func(user_request, reasoning)
                
                # If the selection failed, try again with the extracted library ID
                if not result.get("success", False) and selected_library:
                    self.logger.info(f"Trying again with extracted library ID: {selected_library}")
                    
                    # Create a new reasoning that explicitly mentions the library ID
                    explicit_reasoning = f"Based on the user request, I recommend using {selected_library}. {reasoning}"
                    result = self.tools.llm_select_ucf_func(user_request, explicit_reasoning)
                
                return result
            else:
                self.logger.warning("LLM did not select a specific library")
                # Fall back to the default selection process
                return self.tools.analyze_and_select_library_func(user_request)
                
        except Exception as e:
            self.logger.error(f"Error using LLM to select UCF library: {e}")
            # Fall back to the default selection process
            return self.tools.analyze_and_select_library_func(user_request)
    
    def _validate_outputs_in_ucf(self, ucf_path: str, outputs: List[str]) -> Dict:
        """
        Validate that a UCF file contains the required outputs.
        
        Args:
            ucf_path: Path to the UCF file
            outputs: List of required outputs
            
        Returns:
            Dict with validation results
        """
        try:
            # Load the UCF file
            with open(ucf_path, 'r') as f:
                ucf_data = json.load(f)
            
            # Check if the UCF file contains the required outputs
            missing_outputs = []
            for output in outputs:
                output_found = False
                
                # Search for the output in the UCF file
                # This is a simplified search - in a real implementation, you would
                # need to check specific collections based on the output type
                for item in ucf_data:
                    if not isinstance(item, dict):
                        continue
                    
                    # Check in parts collection
                    if item.get("collection") == "parts" and "parts" in item:
                        for part in item["parts"]:
                            if output.lower() in part.get("name", "").lower():
                                output_found = True
                                break
                
                if not output_found:
                    missing_outputs.append(output)
            
            return {
                "valid": len(missing_outputs) == 0,
                "missing": missing_outputs
            }
        except Exception as e:
            self.logger.error(f"Error validating outputs in UCF file: {e}")
            return {
                "valid": False,
                "error": str(e)
            }
    
    def design_circuit(self, verilog_code: str, organism: str = None, inducers: List[str] = None,
                      outputs: List[str] = None, gate_types: List[str] = None,
                      cello_config: Dict = None, user_request: str = None, 
                      llm_reasoning: str = None, use_llm: bool = False) -> Dict:
        """
        Design a genetic circuit using Cello with appropriate UCF file selection.
        
        Args:
            verilog_code: Verilog code for the circuit
            organism: Target organism (optional if using LLM selection)
            inducers: List of inducers required (optional if using LLM selection)
            outputs: List of outputs required (optional if using LLM selection)
            gate_types: List of gate types required (optional if using LLM selection)
            cello_config: Optional Cello configuration
            user_request: User's original request (required if using LLM selection)
            llm_reasoning: LLM's reasoning for selecting a particular library (optional)
            use_llm: Whether to use LLM-based UCF selection
            
        Returns:
            Dict with design results or error
        """
        # Initialize configuration
        config = cello_config or {}
        
        # Ensure we have a constraints_path
        if "constraints_path" not in config:
            config["constraints_path"] = "ext_repos/Cello-UCF/files/v2/ucf/Eco"
            self.logger.info(f"Using default constraints path: {config['constraints_path']}")
        
        # Determine which UCF selection method to use
        if use_llm:
            if not user_request:
                return {
                    "error": "User request is required for LLM-based UCF selection",
                    "message": "Please provide a user_request parameter when use_llm is True"
                }
            
            # Use LLM-based UCF selection
            self.logger.info(f"Using LLM-based UCF selection for request: {user_request}")
            ucf_result = self.select_ucf_with_llm(user_request, llm_reasoning)
            
            # Check if there was an error
            if not ucf_result.get("success", False):
                return ucf_result
            
            # Get the selected library ID
            library_id = ucf_result.get("library_id")
            
            # We need to convert the library ID to a UCF file name
            # This assumes that the library ID corresponds to a UCF file name
            ucf_file = f"{library_id}.UCF.json"
            
            # Determine the organism prefix from the library ID to find the correct directory
            if library_id.startswith("Eco"):
                organism_dir = "Eco"
            elif library_id.startswith("SC"):
                organism_dir = "SC"
            elif library_id.startswith("Bth"):
                organism_dir = "Bth"
            else:
                organism_dir = "Eco"  # Default to E. coli
            
            # Update the constraints path to point to the correct organism directory
            config["constraints_path"] = f"ext_repos/Cello-UCF/files/v2/ucf/{organism_dir}"
            
            # Add UCF file information to the result
            ucf_result["ucf_file"] = {"file": ucf_file}
        else:
            # Use traditional UCF selection
            if not organism:
                return {
                    "error": "Organism is required for traditional UCF selection",
                    "message": "Please provide an organism parameter when use_llm is False"
                }
                
            self.logger.info(f"Using traditional UCF selection for organism: {organism}")
            ucf_result = self.select_ucf_file(organism, inducers, outputs, gate_types)
            
            # Check if there was an error or warning
            if "error" in ucf_result:
                return ucf_result
        
        # Get the selected UCF file
        ucf_file = ucf_result["ucf_file"]["file"]
        
        # Update Cello configuration with the selected UCF file
        config.update({
            "ucf_name": ucf_file
        })
        
        # Check if the UCF file exists
        import os
        ucf_path = os.path.join(config["constraints_path"], ucf_file)
        if not os.path.exists(ucf_path):
            self.logger.error(f"Selected UCF file does not exist: {ucf_path}")
            return {
                "error": f"Selected UCF file does not exist: {ucf_path}",
                "message": "Please check that the UCF file exists in the specified directory"
            }
        else:
            self.logger.info(f"Verified UCF file exists: {ucf_path}")
        
        # Run Cello with the selected UCF file
        self.logger.info(f"Running Cello with UCF file: {ucf_file}")
        design_result = self.tools.design_with_cello_func(verilog_code, config)
        
        # Add UCF file information to the result
        if "success" in design_result and design_result["success"]:
            design_result["ucf_file"] = ucf_file
            
            # If we used LLM selection, add the LLM reasoning to the result
            if use_llm:
                if llm_reasoning:
                    design_result["llm_reasoning"] = llm_reasoning
                
                # Add the library ID to the result
                if "library_id" in ucf_result:
                    design_result["library_id"] = ucf_result["library_id"]
        
        return design_result 