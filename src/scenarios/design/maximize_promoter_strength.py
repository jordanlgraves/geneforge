#!/usr/bin/env python3
import json
import logging
from src.scenarios.report_answer_scenario import ReportAnswerScenario

from src.tools.cello_tools import SelectLibraryTool

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("MaximizePromoterStrengthExample")


PROMPT = """You will be given an E. coli promoter sequence and a set of tools to use. 
Your task is to use the tools to maximize the strength of a given promoter sequence while preserving the original sequence as much as possible.

Use as many rounds as you need to determine an optimal promoter sequence.

The `promoter_or_spacer` argument is the sequence to estimate the strength of.

Once you have determined an optimal promoter sequence, use the `report_answer` tool to submit the promoter sequence as you answer in json using the `promoter_sequence` argument in the following format:
{
    "promoter_sequence": (string)
}

The promoter sequence is: {promoter_sequence}
"""

GRADING_RUBRIC = """
- Reward responses that rapidly converge to an optimal answer and demonstrate an understanding of which positions to mutate based on the given sequence.
- Reward responses that demonstrate reasoning and reasoning steps.
- Compute the reward based on the following metrics, in priority order:
    - difference: the difference between the answer and reference promoter strengths (ymax)
    - sequence_similarity: the similarity between the answer and reference promoter sequences
    - num_rounds: the number of rounds the agent took to find the answer
- Solutions with the maximize difference (ymax) and maximal sequence_similarity should be the best.
- Reward responses that significantly increase the strength of the promoter sequence while preserving the original sequence as much as possible.
- Lightly penalize responses that take too many rounds to converge.
- Penalize responses with low sequence similarity to the reference promoter sequence.
- Penalize responses that use inappropiate tools such as cello, synbiohub, as these are not needed to maximize promoter strength.
"""

train_promoters = {
    "pPhlF": "CGACGTACGGTGGAATCTGATTCGTTACCAATTGACATGATACGAAACGTACCGTATCGTTAAGGT",
    "pIcaRA": "GTCAACTCATAAGATtctgattcgttaccaattgacaaTTCACCTACCTTTCGTTAGgTTAGGTTGT",
    "pBetI": "AGCGCGGGTGAGAGGGATTCGTTACCAATTGACAATTGATTGGACGTTCAATATAATGCTAGC",
    "pBM3R1": "AATCCGCGTGATAGGTCTGATTCGTTACCAATTGACGGAATGAACGTTCATTCCGATAATGCTAGC",
    "pSrpR": "TCTATGATTGGTCCAGATTCGTTACCAATTGACAGCTAGCTCAGTCCTAGGTATATACATACATGCTTGTTTGTTTGTAAAC",
    "pHlyIIR": "ACCAGGAATCTGAACGATTCGTTACCAATTGACATATTTAAAATTCTTGTTTAAAatgctagc",
    "pLmrA": "CGCTCATTCACTAGGTCTGATTCGTTACCAATTGACAACTGGTGGTCGAATCAAGATAATAGACCAGTCACTATATTT",
    "pAmeR": "TCGTCACTAGAGGGCGATAGTGACAAACTTGACAACTCATCACTTCCTAGGTATAATGCTAGC",
    "pLitR": "CGAGCGTAGAGCTTAgattcgttaccaatTGACAAATTTATAAATTGTCAgtacagtcctagc"
}

eval_promoters = {
    "pPsrA": "TGATCGAACGCTTCAAGGAACAAACGTTTGAttgacagctagctcagtcctaggtagagtgctagc",
    "pQacR": "GGTATGGAAGCTATACGTTACCAATTGACAGCTAGCTCAGTCCTACTTTAGTATATAGACCGTGCGATCGGTCTATA",
    "pAmtR": "CTTGTCCAACCAAATGATTCGTTACCAATTGACAGTTTCTATCGATCTATAGATAATGCTAGC",
}

class MaximizePromoterStrengthScenario(ReportAnswerScenario):
    def __init__(self, promoter_sequence: str, *args, **kwargs):
        self.promoter_sequence = promoter_sequence
        super().__init__(*args, **kwargs)
        
        # pre-execute the select_library tool
        self.include_pre_calls_in_chat = False
        self.preexecuted_tool_calls = [{
            "role": "assistant",
            "tool_calls": [
                {
                    "id": "select_library_tool",
                    "function": {
                        "name": SelectLibraryTool.name,
                        "arguments": json.dumps({
                            "library_id": "Eco1C1G1T1"
                        })
                    }
                }
            ]
        }]
        
    
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
        
    def get_metrics(self):
        
        reported_answer = self.get_reported_answer_content()
        if not reported_answer:
            return {"gave_answer": False, **super().get_metrics()}
        
        try:
            answer = json.loads(reported_answer)
        except Exception:
            print(f'Error parsing answer: {reported_answer}')
            return super().get_metrics()
        try:
            # Extract the promoter sequence from the answer payload
            answer_promoter_sequence = None
            nested_answer = answer.get("answer")
            if nested_answer:
                if isinstance(nested_answer, str):
                    nested_answer_json = json.loads(nested_answer)
                elif isinstance(nested_answer, dict):
                    nested_answer_json = nested_answer
                else:
                    nested_answer_json = {}
                answer_promoter_sequence = nested_answer_json.get("promoter_sequence")

            
            if not answer_promoter_sequence:
                answer_promoter_sequence = answer.get("promoter_sequence")
            
            # If we still can't find a sequence, fall back to parent metrics
            if not answer_promoter_sequence:
                return {"gave_answer": False, **super().get_metrics()}
            
            
            estimated_answer_strength = self.tool_integration.tools['estimate_promoter_strength_with_pro_d'].execute(answer_promoter_sequence)
            reference_answer_strength = self.tool_integration.tools['estimate_promoter_strength_with_pro_d'].execute(self.promoter_sequence)
            difference = estimated_answer_strength.get("ymax") - reference_answer_strength.get("ymax")
            
            reference_class = reference_answer_strength.get("class") if reference_answer_strength else None
            estimated_class = estimated_answer_strength.get("class") if estimated_answer_strength else None
            
            # string similarity between the answer and reference promoter sequence
            if answer_promoter_sequence and self.promoter_sequence:
                similarity = self.tool_integration.tools['sequence_similarity'].execute(answer_promoter_sequence, self.promoter_sequence).get("similarity")
            else:
                similarity = None
            
            return {
                "answer_strength": estimated_answer_strength.get("ymax") if estimated_answer_strength else None,
                "reference_strength": reference_answer_strength.get("ymax") if reference_answer_strength else None,
                "difference": difference,
                "reference_class": reference_class,
                "answer_class": estimated_class,
                "sequence_similarity": similarity,
                "gave_answer": True,
                "promoter_sequence": self.promoter_sequence,
                **super().get_metrics()
            }
        except Exception as e:
            print(f'Error getting metrics: {e}')
            return {"gave_answer": False, **super().get_metrics(), "promoter_sequence": self.promoter_sequence}


if __name__ == "__main__":
    models = [
        "gemini/gemini-2.5-pro", 
        "gemini/gemini-2.5-flash",
        "gpt-4o-mini",
        "gpt-5-nano-2025-08-07",
        "o3",
        "deepseek-chat",
    ]
    all_metrics = {}
    for model in models:
        sequence = 'CTTGTCCAACCAAATGATTCGTTACCAATTGACAGTTTCTATCGATCTATAGATAATGCTAGC'
        runner = MaximizePromoterStrengthScenario(
            scenario_name=f"MaximizePromoterStrength_{model}",
            promoter_sequence=sequence,
            model_name=model
        )
        runner.run()
        all_metrics[model] = runner.get_metrics()
        print(all_metrics[model])
        print('Done')
        
    print(all_metrics)
    with open('outputs/maximize_promoter_strength_metrics.json', 'w') as f:
        json.dump(all_metrics, f)
