#!/usr/bin/env python3
import logging
from src.scenarios.scenario import Scenario

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SimpleCircuitExample")

PROMPT = """Design and simulate in Cello a NOT gate circuit for E. coli that produces GFP when arabinose is absent. 
            
            Use SynbioHub to search for parts and components.
            """

class SimpleCircuitScenario(Scenario):
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

