#!/usr/bin/env python3
import json
import logging
from src.scenarios.agent.workflows import WorkflowRunner

from src.tools.promoter_tools import EstimatePromoterStrengthWithProDTool

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("MaximizePromoterStrengthExample")


PROMPT = """You will be given an E. coli promoter sequence and a set of tools to use. 
Your task is to use the tools to maximize the strength of a given promoter sequence while preserving the original sequence as much as possible.

Use as many rounds as you need to determine an optimal promoter sequence.

Call tools by using xml tags. For example, to call the `estimate_promoter_strength_with_pro_d` tool, you would use the following xml tag:
<tool_call>
    {"name": "estimate_promoter_strength_with_pro_d", "arguments": {"promoter_or_spacer: "example promoter sequence"}} 
</tool_call>

The `promoter_or_spacer` argument is the sequence to estimate the strength of.

Once you have determined an optimal promoter sequence, use the `report_answer` tool to submit the promoter sequence as you answer as a json string in the following format:
{
    "promoter_sequence": (string)
}

The promoter sequence is: {promoter_sequence}
"""

GRADING_RUBRIC = """
- Reward responses that rapidly converge to an optimal answer and demonstrate an understanding of which positions to mutate based on the given sequence.
- Compute the reward based on the following metrics, in priority order:
    - difference: the difference between the answer and reference promoter strengths (ymax)
    - sequence_similarity: the similarity between the answer and reference promoter sequences
    - num_rounds: the number of rounds the agent took to find the answer
- Reward responses that significantly increase the strength of the promoter sequence while preserving the original sequence as much as possible.
- Lightly penalize responses that take too many rounds to converge.
- Penalize responses with low sequence similarity to the reference promoter sequence.
- Penalize responses that do not use the tools provided.
"""

class MaximizePromoterStrengthWorkflow(WorkflowRunner):
    def __init__(self, promoter_sequence: str, *args, **kwargs):
        self.promoter_sequence = promoter_sequence
        super().__init__(*args, **kwargs)
    
    def check_finished(self) -> bool:
        """
        Returns:
            True if the example is finished, False otherwise. Useful for stopping the workflow when a condition is met.
        """
        answer_tool_id = None
        for message in self.messages:
            if message["role"] == "assistant" and message.get("tool_calls", []) != []:
                for tool_call in message["tool_calls"]:
                    if tool_call.get("function", {}).get("name", None) == "report_answer": # Why would this ever be None?
                        answer_tool_id = tool_call["id"]
                        break
            # This is the tool call that results that we need to check for the answer
            if message['role'] == 'tool' and message['tool_call_id'] == answer_tool_id:
                return True
        return False
    
    def _process_prompt(self, prompt):
        """
        # called by parent class to set self.prompt
        """
        return PROMPT.replace("{promoter_sequence}", self.promoter_sequence)
    
    def get_metrics(self, messages=None):
        if messages is None:
            messages = self.messages
        
        def get_answer_tool_id():
            answer_tool_id = None
            for message in self.messages:
                
                if message["role"] == "assistant" and message.get("tool_calls", []) != []:
                    for tool_call in message["tool_calls"]:
                        if tool_call.get("function", {}).get("name", None) == "report_answer": # Why would this ever be None?
                            answer_tool_id = tool_call["id"]
                            return answer_tool_id
            return None
        
        answer_tool_id = get_answer_tool_id()
        if answer_tool_id is None:
            return dict()
        
        for message in self.messages:
            if message.get("role") == "tool" and message.get('tool_call_id') == answer_tool_id:
                answer = json.loads(message.get("content"))
                answer_promoter_sequence = json.loads(answer.get("answer", {})).get("promoter_sequence" ) or answer.get("promoter_sequence")
                estimated_answer_strength = self.tool_integration.tools['estimate_promoter_strength_with_pro_d'].execute(answer_promoter_sequence)
                reference_answer_strength = self.tool_integration.tools['estimate_promoter_strength_with_pro_d'].execute(self.promoter_sequence)
                
                # calculate the difference between the answer and reference strength
                try:
                    difference = estimated_answer_strength.get("ymax") - reference_answer_strength.get("ymax")
                except:
                    difference = None
                
                reference_class = reference_answer_strength.get("class")
                estimated_class = estimated_answer_strength.get("class")
                
                # string similarity between the answer and reference promoter sequence
                if answer_promoter_sequence and self.promoter_sequence:
                    similarity = self.tool_integration.tools['sequence_similarity'].execute(answer_promoter_sequence, self.promoter_sequence).get("similarity")
                else:
                    similarity = None
                
                return {
                    # "answer_promoter_sequence": answer_promoter_sequence,
                    # "reference_promoter_sequence": self.promoter_sequence,
                    "answer_strength": estimated_answer_strength.get("ymax"),
                    "reference_strength": reference_answer_strength.get("ymax"),
                    "difference": difference,
                    "reference_class": reference_class,
                    "answer_class": estimated_class,
                    "sequence_similarity": similarity,
                    "num_rounds": len(self.messages)
                }
                
        return dict()


    @staticmethod
    def _score_trajectory(trajectory):
        metrics = MaximizePromoterStrengthWorkflow.get_metrics(trajectory.messages_and_choices)
        # larger difference is better, larger sequence similarity is better, smaller num_rounds is better (negative weight)
        # These weights are based on the mean of the metrics for several runs
        if 'difference' not in metrics or 'num_rounds' not in metrics or 'sequence_similarity' not in metrics:
            return -1
        
        weights = {'difference': 0.021787418910884617, 'num_rounds': -0.9606398999917061, 'sequence_similarity': 0.017572681097409257}
        return sum([metrics[metric] * weights[metric] for metric in metrics])

    @staticmethod
    def _get_metrics(messages):
        metrics = MaximizePromoterStrengthWorkflow._score_trajectory(messages)
        return metrics.get("difference", 0)

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
