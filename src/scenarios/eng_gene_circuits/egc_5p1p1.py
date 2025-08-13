import json
from src.scenarios.report_answer_scenario import ReportAnswerScenario
from src.latex_utils import compare_latex, get_latex_expr

PROMPT = """Below are the chemical reactions involved in a competitive enzymatic
reaction in which two substrates compete for a single enzyme

E + S_1 &\\xleftrightarrow{k_1} ES_1 & \\xrightarrow{k_3} E + P_1 \\\\
E + S_2 &\\xleftrightarrow{k_2} ES_2 & \\xrightarrow{k_4} E + P_2 \\\\

Using the law of mass action, write down the equations for the
rates of change of [S_1], [S_2], [ES_1], [ES_2], [P_1], and [P_2]

Use the `report_answer` tool to output your answer as a json string in the following format. Ensure that YOUR_ANSWER is a valid latex equation.

{
    "answer": {
        "d[S_1]/dt": "```latex
            YOUR_ANSWER
        ```",
        "d[S_2]/dt": "```latex
            YOUR_ANSWER
        ```"
        "d[ES_1]/dt": "```latex
            YOUR_ANSWER
        ```",
        "d[ES_2]/dt": "```latex
            YOUR_ANSWER
        ```",
        "d[P_1]/dt": "```latex
            YOUR_ANSWER
        ```",
        "d[P_2]/dt": "```latex
            YOUR_ANSWER
        ```"
    }
}
"""

reference_answer = {"d[S_1]/dt": "k_{2}[ES_1] - k_{1}[E][S_1]",
                    "d[S_2]/dt": "k_{5}[ES_2] - k_{4}[E][S_2]",
                    "d[ES_1]/dt": "k_{1}[E][S_1] - k_{2}[ES_1] - k_{3}[ES_1]",
                    "d[ES_2]/dt": "k_{4}[E][S_2] - k_{5}[ES_2] - k_{6}[ES_2]",
                    "d[P_1]/dt": "k_{3}[ES_1]",
                    "d[P_2]/dt": "k_{6}[ES_2]"
                    }

RUBRIC = f"""
The reference answer is:
{reference_answer}


- Reward responses that correctly define the rate of change functions of [S_1], [S_2], [ES_1], [ES_2], [P_1], and [P_2]
- Reward responses that are close to the reference answer
- Penalize responses that are not valid latex equations
"""
class EGCProblem5p1p1Scenario(ReportAnswerScenario):
    def __init__(self, *args, **kwargs):
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
            d_S1_dt = get_latex_expr(answer.get("d[S_1]/dt"))
            d_S2_dt = get_latex_expr(answer.get("d[S_2]/dt"))
            d_ES1_dt = get_latex_expr(answer.get("d[ES_1]/dt"))
            d_ES2_dt = get_latex_expr(answer.get("d[ES_2]/dt"))
            d_P1_dt = get_latex_expr(answer.get("d[P_1]/dt"))
            d_P2_dt = get_latex_expr(answer.get("d[P_2]/dt"))
            d_S1_dt_ref = get_latex_expr(reference_answer.get("d[S_1]/dt"))
            d_S2_dt_ref = get_latex_expr(reference_answer.get("d[S_2]/dt"))
            d_ES1_dt_ref = get_latex_expr(reference_answer.get("d[ES_1]/dt"))
            d_ES2_dt_ref = get_latex_expr(reference_answer.get("d[ES_2]/dt"))
            d_P1_dt_ref = get_latex_expr(reference_answer.get("d[P_1]/dt"))
            d_P2_dt_ref = get_latex_expr(reference_answer.get("d[P_2]/dt"))
            
            is_correct = compare_latex(d_S1_dt, d_S1_dt_ref) and compare_latex(d_S2_dt, d_S2_dt_ref) and compare_latex(d_ES1_dt, d_ES1_dt_ref) and compare_latex(d_ES2_dt, d_ES2_dt_ref) and compare_latex(d_P1_dt, d_P1_dt_ref) and compare_latex(d_P2_dt, d_P2_dt_ref)
            
            return {
                "gave_answer": True,
                "correct": is_correct,
                "d_S1_dt_correct": compare_latex(d_S1_dt, d_S1_dt_ref),
                "d_S2_dt_correct": compare_latex(d_S2_dt, d_S2_dt_ref),
                "d_ES1_dt_correct": compare_latex(d_ES1_dt, d_ES1_dt_ref),
                "d_ES2_dt_correct": compare_latex(d_ES2_dt, d_ES2_dt_ref),
                "d_P1_dt_correct": compare_latex(d_P1_dt, d_P1_dt_ref),
                "d_P2_dt_correct": compare_latex(d_P2_dt, d_P2_dt_ref),
                **super().get_metrics()
            }
        except Exception:
            print(f'Error parsing answer: {reported_answer}')
            return super().get_metrics()

    def get_nl_rubric(self):
        return RUBRIC

if __name__ == "__main__":
    import asyncio
    from art.rewards.ruler import ruler_score_group
    from art import Trajectory, TrajectoryGroup
    from src.adapters.art_adapter import ArtAdapter
    
    trajectories = []
    for i in range(3):
        adapter = ArtAdapter(EGCProblem5p1p1Scenario(
            scenario_name="EGCProblem5p1p1",
            prompt=PROMPT
        ), step=i)
        trajectory = asyncio.run(adapter.rollout())
        trajectories.append(trajectory)
        
    group = TrajectoryGroup(trajectories=trajectories)
    scored_groups = asyncio.run(ruler_score_group(group, rubric=RUBRIC))

    for trajectory in scored_groups.trajectories:
        print('-'*100)
        print(trajectory.logs)
        print(trajectory.reward)
        print('-'*100)
    