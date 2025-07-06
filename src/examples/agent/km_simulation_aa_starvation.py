#!/usr/bin/env python3
import logging
from src.examples.agent.workflow_harness import WorkflowRunner

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SimpleCircuitExample")

PROMPT = """I want to create and simulate a kinetic model with the following description: 
In E. coli K-12 MG1655 growing at 37 °C, pH 7.0, uncharged tRNA binds the ribosomal A-site and activates the ribosome-bound synthetase RelA. Activated RelA synthesises ppGpp from GTP and ATP with a reported kcat ≈ 110 s⁻¹ and Km(GTP) ≈ 0.15 mM.
The bifunctional enzyme SpoT hydrolyses ppGpp to GDP (ppGpp + H₂O → GDP + PPi) with kcat ≈ 4 s⁻¹, Km(ppGpp) ≈ 18 µM. SpoT can also synthesise ppGpp at a lower rate (kcat ≈ 1 s⁻¹).
Intracellular GTP concentration is 1 mM at time zero; ppGpp starts at 0.1 µM.

Please create the model, use bionumbers or scientific search to find appropriate parameters, then run the simulation
"""

# Expected parameters to search for:
# | Reaction                                | Parameter set                                      |
# | --------------------------------------- | -------------------------------------------------- |
# | RelA synthase: GTP + ATP → ppGpp + AMP  | kcat, Km(GTP), Km(ATP)                             |
# | SpoT hydrolase: ppGpp → GDP + PPi       | kcat, Km(ppGpp)                                    |
# | SpoT synthase (optional)                | kcat, Km(GTP), Km(ATP)                             |
# | Basal GTP turnover                      | Growth-rate-dependent production/consumption rates |
# | ppGpp degradation by NudG (if modelled) | kcat, Km                                           |

class KMAminoAcidStarvationExample(WorkflowRunner):
    """Extension of ExampleRunner to check for both custom input sensors file and Cello results."""

    def check_success(self) -> bool:
        # Should check for a SBML file in the session state
        return False


def run_example():
    """
    Uses the LLM modules with session state to execute the design of a simple circuit.
    """
    # Create and run the example using the reusable harness
    runner = KMAminoAcidStarvationExample(
        example_name="Kinetic Modeling Amino Acid Starvation",
        prompt=PROMPT,
        max_rounds=15,
        max_attempts=2
    )
    
    final_result = runner.run()
    runner.log_results(final_result)

if __name__ == "__main__":
    run_example()