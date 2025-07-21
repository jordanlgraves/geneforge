#!/usr/bin/env python3
import logging
from src.examples.agent.workflows import WorkflowRunner
from src.prompt_manager import get_system_prompt

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("MinimalInputSensorsExample")

PROMPT = """Design and simulate in Cello a NOR gate circuit for E. coli that uses only a single input sensor.
Start by selecting a library. List the available input sensors in the library's default input sensors file.
Choose one input sensor (like the arabinose sensor) and create a custom minimal input sensors file containing just that sensor.
Use Cello to design the circuit with your custom input sensor file.
After the simulation is complete, read the circuit score from the output file and return it as a JSON object with the key 'circuit_score'."""

SYSTEM_PROMPT = get_system_prompt()
class MinimalInputSensorsRunner(WorkflowRunner):
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

def run_example():
    """
    Uses the LLM modules with session state to execute the design of a circuit
    with a minimal set of input sensors.
    """
    # Create and run the example using the customized runner
    runner = MinimalInputSensorsRunner(
        example_name="Minimal Input Sensors",
        prompt=PROMPT,
        system_prompt=SYSTEM_PROMPT,
        max_rounds=20,
        max_attempts=4
    )
    
    final_result = runner.run()
    runner.log_results(final_result)

if __name__ == "__main__":
    run_example() 