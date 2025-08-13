#!/usr/bin/env python3
import logging
from src.scenarios.scenario import Scenario

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SimpleCircuitExample")

PROMPT = """I want to create and simulate a kinetic model with the following description: 

In E. coli, the repressor LacI decays in the cytoplasm at 37 °C, pH 7.0.

Please create the model, use bionumbers or scientific search to find appropriate parameters, then run the simulation."""


class KMEColiLacIDecayScenario(Scenario):
    """Extension of Scenario to check for both custom input sensors file and Cello results."""

    def check_finished(self) -> bool:
        # Should check for a SBML file in the session state
        return False

