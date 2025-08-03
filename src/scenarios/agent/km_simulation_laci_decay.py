#!/usr/bin/env python3
import logging
from src.scenarios.agent.workflows import WorkflowRunner

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SimpleCircuitExample")

PROMPT = """I want to create and simulate a kinetic model with the following description: 

In E. coli, the repressor LacI decays in the cytoplasm at 37 °C, pH 7.0.

Please create the model, use bionumbers or scientific search to find appropriate parameters, then run the simulation."""


class KMEColiLacIDecayExample(WorkflowRunner):
    """Extension of ExampleRunner to check for both custom input sensors file and Cello results."""

    def check_finished(self) -> bool:
        # Should check for a SBML file in the session state
        return False


def run_example():
    """
    Uses the LLM modules with session state to execute the design of a simple circuit.
    """
    # Create and run the example using the reusable harness
    runner = KMEColiLacIDecayExample(
        example_name="Kinetic Modeling E. coli LacI Decay",
        prompt=PROMPT,
        max_rounds=15,
        max_attempts=2
    )
    
    final_result = runner.run()
    runner.log_results(final_result)

if __name__ == "__main__":
    run_example()