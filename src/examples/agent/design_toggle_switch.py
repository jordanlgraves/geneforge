#!/usr/bin/env python3
import logging
from src.examples.agent.example_harness import ExampleRunner

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SimpleCircuitExample")

PROMPT = """Design and simulate a genetic toggle switch in E. coli that turns on when two different signals are present (X and Y). It should turn off whenever a third, separate signal (Z) is present. 
Use the provided tools to simulate the circuit in Cello with exhaustive set to False.
After the simulation is complete, read the circuit score from the output file and return it as a JSON object with the key 'circuit_score'."""

class SimpleCircuitRunner(ExampleRunner):
    """Extension of ExampleRunner to check for both custom input sensors file and Cello results and store the initial design spec."""
    def check_success(self) -> bool:
        """
        Check if both a custom input sensors file was created and Cello results were obtained.
        
        Returns:
            True if custom input file created and Cello results obtained, False otherwise
        """
        has_cello_results = self.session_state.get_cello_results() is not None
        
        return has_cello_results


def run_example():
    """
    Uses the LLM modules with session state to execute the design of a simple circuit.
    """
    # Create and run the example using the reusable harness
    runner = SimpleCircuitRunner(
        example_name="Simple Circuit",
        prompt=PROMPT,
        max_rounds=15,
        max_attempts=2
    )
    
    final_result = runner.run()
    runner.log_results(final_result)

if __name__ == "__main__":
    run_example()