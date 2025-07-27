#!/usr/bin/env python3
import logging
from src.scenarios.agent.workflows import WorkflowRunner

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SimpleCircuitExample")

PROMPT = """I want to create and simulate a kinetic model with the following description: 

'Molecules of M bind to form E, and E dissociates back into two Ms. Additionally, E and S can bind to form ES, which then dissociates back into E and S, while E and P can bind to form EP, which dissociates back into E and P. Furthermore, ES can be converted into E and P. E and I can also bind to form EI, which dissociates back into E and I. Finally, EI is converted into EJ.
Please create the model and simulate it with whatever parameters you think are appropriate.
"""


class KineticModelingSimulationRunner(WorkflowRunner):
    """Extension of ExampleRunner to check for both custom input sensors file and Cello results."""

    def check_finished(self) -> bool:
        # Should check for a SBML file in the session state
        return False


def run_example():
    """
    Uses the LLM modules with session state to execute the design of a simple circuit.
    """
    # Create and run the example using the reusable harness
    runner = KineticModelingSimulationRunner(
        example_name="Kinetic Modeling Simulation",
        prompt=PROMPT,
        max_rounds=15,
        max_attempts=2
    )
    
    final_result = runner.run()
    runner.log_results(final_result)

if __name__ == "__main__":
    run_example()