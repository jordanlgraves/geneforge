#!/usr/bin/env python3
import logging
from src.scenarios.agent.workflows import WorkflowRunner
from src.prompt_manager import get_system_prompt

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SimpleCircuitExample")

PROMPT = """Design and simulate a simple not gate in E. coli. Use the provided tools to create the circuit design with Cello with exhaustive set to False.
After the Cello design is complete, generate an SBML model using the conversion tool.
After the SBML is created, use various tools to fill in the parameters for the SBML model.
After the parameters are filled in, run the simulation with parameters that will demonstrate the not gate functionality.
"""

SYSTEM_PROMPT = get_system_prompt()
class SimpleNotGateSimulationRunner(WorkflowRunner):
    def check_finished(self) -> bool:
        has_cello_results = self.session_state.get_cello_results() is not None
        
        return has_cello_results


def run_example():
    """
    Uses the LLM modules with session state to execute the design of a simple circuit.
    """
    # Create and run the example using the reusable harness
    runner = SimpleNotGateSimulationRunner(
        example_name="Simple Not Gate Simulation",
        prompt=PROMPT,
        system_prompt=SYSTEM_PROMPT,
        max_rounds=15,
        max_attempts=2
    )
    
    final_result = runner.run()
    runner.log_results(final_result)

if __name__ == "__main__":
    run_example()