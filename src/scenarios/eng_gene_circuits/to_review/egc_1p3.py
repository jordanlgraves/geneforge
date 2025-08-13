

import json
from src.scenarios.report_answer_scenario import ReportAnswerScenario


PROMPT = """Construct a reaction-based SBML model for the genetic circuit shown below using iBioSim or any other tool that includes an SBML editor. Use the parameter values provided and assume that CI dimerizes before acting as a transcription factor.
Genetic Circuit Description:
- CI represses LacI via promoter P_1
- LacI represses TetR via promoter P_2
- TetR represses CI via promoter P_3

Parameter Values:
```latex
\\text{RNAP}_0 = 30\, \\text{nM}  
K_d = 0.05\, \\text{M}^{-1}  
K_o = 0.033\, \\text{M}^{-1}  
K_r = 0.25\, \\text{M}^{-1}  
k_o = 0.05\, \\text{s}^{-1}  
k_d = 0.0075\, \\text{s}^{-1}  
n_p = 10  
n_c = 2
```

Use the `report_answer` tool to submit your answer in latex format. 

For example, if you answer is "MY SOLUTION":

{ 
    "answer": "```latex
        MY SOLUTION
    ```"
}
"""

reference_answer = """```latex
\\text{CI} & \\xrightarrow{k_d} ()\\
\\text{LacI} & \\xrightarrow{k_d} () \\
\\text{TetR} & \\xrightarrow{k_d} () \\
P_1 + \\text{RNAP} & \\xrightleftharpoons{K_o} S_1 \\
S_1 & \\xrightarrow{k_o} S_1 + np \\cdot \\text{LacI} \\
P_2 + \\text{RNAP} & \\xrightleftharpoons{K_o} S_2 \\
S_2 & \\xrightarrow{k_o} S_2 + np \\cdot \\text{TetR} \\
P_3 + \\text{RNAP} & \\xrightleftharpoons{K_o} S_3 \\
S_3 & \\xrightarrow{k_o} S_3 + np \\cdot \\text{CI} \\
2\\text{CI} & \\xrightleftharpoons{K_d} \\text{CI}_2 \\
P_1 + nc \\cdot \\text{CI}_2 & \\xrightleftharpoons{K_r} S_4 \\
P_2 + nc \\cdot \\text{LacI} & \\xrightleftharpoons{K_r} S_5 \\
P_3 + nc \\cdot \\text{TetR} & \\xrightleftharpoons{K_r} S_6 \\
```"""

RUBRIC = None

class EGCProblem1p3Scenario(ReportAnswerScenario):
    def __init__(self, *args, **kwargs):
        self.reference_answer = reference_answer
        super().__init__(*args, **kwargs)
    
    def _process_prompt(self, prompt: str):
        return PROMPT
    
    def get_metrics(self):
        # last_message = self.messages[-1]
        # if last_message["role"] == "tool" and last_message["name"] == "report_answer":
        #     answer = json.loads(last_message["content"])
        #     return {
        #         "num_rounds": len(self.messages),
        #         "dg_correct": abs(answer["dG"] - self.reference_answer["dG"]) < 0.01,
        #         "reaction_direction_correct": int(answer.get("reaction_favored", "").lower() == self.reference_answer["reaction_favored"].lower()),
        #         "ES_correct": abs(answer.get("ES", 0) - self.reference_answer["ES"]) < 0.01,
        #         "S_correct": abs(answer.get("S", 0) - self.reference_answer["S"]) < 0.01,
        #         "E_correct": abs(answer.get("E", 0) - self.reference_answer["E"]) < 0.01,
        #     }
        return super().get_metrics()
    
    def get_nl_rubric(self):
        return RUBRIC

if __name__ == "__main__":
    scenario = EGCProblem1p3Scenario(
        scenario_name="EGCProblem1p3",
        prompt=PROMPT,
        use_reasoning_model=True,
    )
    scenario.run()
    
    # get the report_answer tool call
    for message in scenario.messages:
        if message["role"] == "tool" and message["name"] == "report_answer":
            answer_message = message
            break
    
    sample = {
        "output_text": scenario.messages[-1]["content"], 
        "reference_answer": reference_answer,
    }
    item = {
        "reference_answer": reference_answer,
    }
    from src.rl.graders.grade_egc_promblem1p1 import grade
    score = grade(sample, item)
    print(score)
    
    