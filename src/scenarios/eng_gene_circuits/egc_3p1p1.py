import json
from src.scenarios.report_answer_scenario import ReportAnswerScenario
from src.latex_utils import compare_latex, get_latex_expr

PROMPT = """Consider the following reactions:

2S_1 \\xrightarrow{0.1} 2S_2 \\\\
S_1 + S_2 \\xrightarrow{0.2} 2S_1

Determine the reaction rate equations for [S_1] and [S_2]

Use the `report_answer` tool to output your answer as json with the following format:

{
    "d[S_1]/dt": "```latex
        equation for [S_1]
    ```",
    "d[S_2]/dt": "```latex
        equation for [S_2]
    ```"
}
"""

reference_answer = {
    "d[S_1]/dt": "0.2[S_1][S_2] - 0.2[S_1]^2",
    "d[S_2]/dt": "0.2[S_1]^2 - 0.2[S_1][S_2]"
}

RUBRIC = None
class EGCProblem3p1p1Scenario(ReportAnswerScenario):
    def __init__(self, *args, **kwargs):
        self.reference_answer = reference_answer
        super().__init__(*args, **kwargs)
    
    def _process_prompt(self, prompt: str):
        return PROMPT
    
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
            if message['role'] == 'tool' and message['tool_call_id'] == answer_tool_id:
                return True
        return super().check_finished()
    
    def get_metrics(self):
        reported_answer = self.get_reported_answer_content()
        if not reported_answer:
            return {"gave_answer": False, **super().get_metrics()}
        
        try:
            answer_json = json.loads(reported_answer)
            answer = answer_json.get("answer")
            if isinstance(answer, str):
                answer = json.loads(answer)
            answer_dS1dt = get_latex_expr(answer.get("d[S_1]/dt"))
            answer_dS2dt = get_latex_expr(answer.get("d[S_2]/dt"))
            reference_dS1dt = get_latex_expr(self.reference_answer.get("d[S_1]/dt"))
            reference_dS2dt = get_latex_expr(self.reference_answer.get("d[S_2]/dt"))

            
            dS1dt_correct = compare_latex(answer_dS1dt, reference_dS1dt)
            dS2dt_correct = compare_latex(answer_dS2dt, reference_dS2dt)
            is_correct = dS1dt_correct and dS2dt_correct
            return {
                "gave_answer": True,
                "correct": is_correct,
                "dS1dt_correct": dS1dt_correct,
                "dS2dt_correct": dS2dt_correct,
                **super().get_metrics()
            }
        except Exception:
            print(f'Error parsing answer: {reported_answer}')
            return super().get_metrics()
    
    def get_nl_rubric(self):
        return RUBRIC

if __name__ == "__main__":
    scenario = EGCProblem3p1p1Scenario(
        scenario_name="EGCProblem3p1p1",
        prompt=PROMPT,
        use_reasoning_model=True,
    )
    scenario.run()
    
    # get the report_answer tool call
    for message in scenario.messages:
        if message["role"] == "tool" and message.get("function", {}).get("name", None) == "report_answer": # Why would this ever be None?
            answer_message = message
            break
    
    sample = {
        "output_text": scenario.messages[-1]["content"], 
        "reference_answer": reference_answer,
    }
    item = {
        "reference_answer": reference_answer,
    }
    