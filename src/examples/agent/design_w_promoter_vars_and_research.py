#!/usr/bin/env python3
import logging
import json
from src.examples.agent.workflows import WorkflowRunner
from src.prompt_manager import get_system_prompt
import src.library.cello_utils as cello_utils

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("DesignWithPromoterVarsWResearchExample")

PROMPT = """Your task is to design a simple genetic circuit, a NOT gate, for E. coli. However, for this exercise, you must use custom promoters. 
Please start by selecting the 'Eco1C1G1T1' library. Then, take a random promoter from the library and generate three new promoter variants using the Pro D tool.
Before using the tool, use the research tool to determine the most optimal spacer position positions to mutate. Your goal is to maximize the y_max value for the new promoter with the least number of mutations.
After generating the new variants, create a new, minimal genetic library that contains *only* these three new variants and their necessary dependencies. 
Finally, use this new custom library to design and simulate the NOT gate with Cello. 
Report the name of the final DNA sequence design if successful."""

SYSTEM_PROMPT = get_system_prompt()


class DesignWithPromoterVarsWResearchRunner(WorkflowRunner):
    """
    Extension of ExampleRunner to check for a custom UCF file where the original
    promoter has been replaced by variants, and Cello results are present.
    """
    def check_finished(self) -> bool:
        """
        Check if:
        1. A custom UCF file was created.
        2. Cello results were obtained.
        3. The custom UCF contains the new variants and not the original.
        """
        has_custom_ucf = hasattr(self.session_state, 'cello_library.user_constraints_path') and self.session_state.cello_library.user_constraints_path is not None
        has_cello_results = self.session_state.cello_results is not None

        if not (has_custom_ucf and has_cello_results):
            return False

        # Extra validation: check the content of the final UCF
        try:
            with open(self.session_state.cello_library.user_constraints_path) as f:
                ucf_data = json.load(f)
            
            # Check that the original promoter is gone
            original_gone = cello_utils.get_part_by_name(ucf_data, "pTet") is None
            
            # Check that at least one variant exists
            variants_exist = any("pTetvar" in p.get("name", "") for p in ucf_data if p.get("collection") == "parts")

            if not (original_gone and variants_exist):
                self.logger.warning(f"Final UCF validation failed: original_gone={original_gone}, variants_exist={variants_exist}")

            return original_gone and variants_exist
        except Exception as e:
            self.logger.error(f"Failed to validate final UCF content: {e}")
            return False


def run_example():
    """
    Uses the LLM modules with session state to execute a design workflow
    that involves creating and using promoter variants.
    """
    # Create and run the example using the customized runner
    runner = DesignWithPromoterVarsWResearchRunner(
        example_name="DesignWithPromoterVarsWResearch",
        prompt=PROMPT,
        system_prompt=SYSTEM_PROMPT,
        max_rounds=25,
        max_attempts=3
    )
    
    final_result = runner.run()
    runner.log_results(final_result)


if __name__ == "__main__":
    run_example()
