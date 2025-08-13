#!/usr/bin/env python3
import logging
from src.scenarios.scenario import Scenario

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("GeneticToggleSwitchExample")

PROMPT = """I want to design and simulate a kinetic model of a genetic toggle switch in E coli. 

Please create the model, use bionumbers or scientific search to find appropriate parameters.
Then run the simulation to demonstrate the switching behavior. 
The simulation should show that output (e.g. GFP) is zero until the ON inducer is turned up at some time t=t_on, resulting in an increase in output. 
The simulation should show that setting the ON inducer to zero at some later time t=t_off maintains the output at a steady value afterwards.
The simulation should show that the output then decreases to zero at some later time t=t_off_2 when the OFF inducer is turned up.
The simulation should show the concentrations of the ON and OFF inducers, and the output over time.

The model should be designed to be robust to parameter variation.
"""


class GeneticToggleSwitchScenario(Scenario):
    """Extension of Scenario to check for both custom input sensors file and Cello results."""

    def check_finished(self) -> bool:
        # Should check for a SBML file in the session state
        return False

