#!/usr/bin/env python3
import logging
from src.scenarios.scenario import Scenario
from src.prompt_manager import get_system_prompt
# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("MinimalSimpleCircuitExample")

PROMPT = """Design and simulate in Cello a NOT gate circuit for E. coli using the minimal number of parts possible.
Start by selecting a library. List the parts in the library's default user constraints file. 
Select the parts you need to create the circuit and use them to create a custom minimal user constraint file.
After creating the custom file, use Cello to design and simulate the circuit. 
After the simulation is complete, read the circuit score from the output file and return it as a JSON object with the key 'circuit_score'."""

SYSTEM_PROMPT = get_system_prompt()
class MinimalUCFScenario(Scenario):
    """Extension of ExampleRunner to check for both custom input sensors file and Cello results."""
    
    def check_finished(self) -> bool:
        """
        Check if both a custom input sensors file was created and Cello results were obtained.
        
        Returns:
            True if custom input file created and Cello results obtained, False otherwise
        """
        has_custom_input = hasattr(self.session_state, 'custom_input_path') and self.session_state.custom_input_path is not None
        has_cello_results = self.session_state.get_cello_results() is not None
        
        return has_custom_input and has_cello_results