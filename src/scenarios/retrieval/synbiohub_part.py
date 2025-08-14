#!/usr/bin/env python3
import logging
from src.scenarios.scenario import Scenario

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("GeneticToggleSwitchExample")

PROMPT = """Find a part in SynBioHub for the pBad promoter, download it, and report its sequence.

Use the `report_answer` tool to submit the sequence in latex format. 

For example, if the sequence is "AATTCCGG":

{ 
    "answer": "AATTCCGG"
}
"""


class SynBioHubPartScenario(ReportAnswerScenario):
    """Extension of Scenario to check for both custom input sensors file and Cello results."""

    def check_finished(self) -> bool:
        # Should check for a SBML file in the session state
        return False
    
    def _process_prompt(self, prompt):
        """
        # called by parent class to set self.prompt
        """
        return PROMPT
    
    def get_metrics(self) -> dict:
        return {
            "success": True,
            "message": "SynBioHub part retrieved successfully",
        }

if __name__ == "__main__":
    scenario = SynBioHubPartScenario(scenario_name="SynBioHubPart", model_name="o3")
    scenario.run()
    print(scenario.get_metrics())