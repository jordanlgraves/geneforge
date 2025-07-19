#!/usr/bin/env python3
import json
import logging
from src.examples.agent.workflows import WorkflowRunner

from src.tools.promoter_tools import EstimatePromoterStrengthWithProDTool

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("MaximizePromoterStrengthExample")


PROMPT = """You will be given an E. coli promoter sequence and a set of tools to use. 
Your task is to use the tools to maximize the strength of a given promoter sequence while preserving the original sequence as much as possible.

Use as many rounds as you need to determine an optimal promoter sequence.

Once you have determined an optimal promoter sequence, use the `report_answer` tool to submit the promoter sequence as you answer as a json string in the following format:
{
    "promoter_sequence": (string)
}

The promoter sequence is: {promoter_sequence}
"""

class MaximizePromoterStrengthWorkflow(WorkflowRunner):
    def __init__(self, promoter_sequence: str, *args, **kwargs):
        self.promoter_sequence = promoter_sequence
        super().__init__(*args, **kwargs)  # Inherit parent arguments using **kwargs
    
    def check_finished(self) -> bool:
        # check for the final answer in the tool call response
        for message in self.messages:
            if message.get("role") == "tool" and message.get('name') == "report_answer":
                return True
        return False
    
    def _process_prompt(self, prompt):
        """
        # called by parent class to set self.prompt
        """
        return PROMPT.replace("{promoter_sequence}", self.promoter_sequence)
    
    def get_metrics(self):
        for message in self.messages:
            if message.get("role") == "tool" and message.get('name') == "report_answer":
                answer = json.loads(message.get("content"))
                answer_promoter_sequence = json.loads(answer.get("answer", {})).get("promoter_sequence" ) or answer.get("promoter_sequence")
                estimated_answer_strength = self.tool_integration.tools['estimate_promoter_strength_with_pro_d'].execute(answer_promoter_sequence)
                reference_answer_strength = self.tool_integration.tools['estimate_promoter_strength_with_pro_d'].execute(self.promoter_sequence)
                
                # calculate the difference between the answer and reference strength
                difference = estimated_answer_strength.get("ymax") - reference_answer_strength.get("ymax")
                reference_class = reference_answer_strength.get("class")
                estimated_class = estimated_answer_strength.get("class")
                
                # string similarity between the answer and reference promoter sequence
                similarity = self.tool_integration.tools['sequence_similarity'].execute(answer_promoter_sequence, self.promoter_sequence).get("similarity")
                
                return {
                    "answer_promoter_sequence": answer_promoter_sequence,
                    "reference_promoter_sequence": self.promoter_sequence,
                    "answer_strength": estimated_answer_strength.get("ymax"),
                    "reference_strength": reference_answer_strength.get("ymax"),
                    "difference": difference,
                    "reference_class": reference_class,
                    "answer_class": estimated_class,
                    "sequence_similarity": similarity,
                    "num_rounds": len(self.messages)
                }
                
        return None


def score_run(messages, session_state_history):
    return NotImplementedError("Not implemented")


def run_example(sequence: str):
    """
    Uses the LLM modules with session state to execute a design workflow
    that involves creating and using promoter variants.
    """
    
    # Create and run the example using the customized runner
    runner = MaximizePromoterStrengthWorkflow(
        example_name="MaximizePromoterStrength",
        promoter_sequence=sequence,
        use_reasoning_model=True
    )
    
    final_result = runner.run(max_rounds=25, num_retries=3)
    runner.log_results(final_result)
    
    return runner





if __name__ == "__main__":
    sequence = 'CTTGTCCAACCAAATGATTCGTTACCAATTGACAGTTTCTATCGATCTATAGATAATGCTAGC'
    run_example(sequence)   
