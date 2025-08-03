import json
from src.scenarios.agent.workflows import WorkflowRunner


PROMPT = """Below are the chemical reactions involved in a competitive enzymatic
reaction in which two substrates compete for a single enzyme

E + S_1 &\\xleftrightarrow{k_1} ES_1 & \\xrightarrow{k_3} E + P_1 \\\\
E + S_2 &\\xleftrightarrow{k_2} ES_2 & \\xrightarrow{k_4} E + P_2 \\\\

Using the law of mass action, write down the equations for the
rates of change of [S_1], [S_2], [ES_1], [ES_2], [P_1], and [P_2]

Use the `report_answer` tool to output your answer as a json string in the following format. Ensure that YOUR_ANSWER is a valid latex equation.

{
    "answer": "{YOUR_ANSWER}"
}
"""

reference_answer = """
\\frac{d[S_1]}{dt} &= k_{2}[ES_1] - k_{1}[E][S_1] \\\\
\\frac{d[S_2]}{dt} &= k_{5}[ES_2] - k_{4}[E][S_2] \\\\
\\frac{d[ES_1]}{dt} &= k_{1}[E][S_1] - k_{2}[ES_1] - k_{3}[ES_1] \\\\
\\frac{d[ES_2]}{dt} &= k_{4}[E][S_2] - k_{5}[ES_2] - k_{6}[ES_2] \\\\
\\frac{d[P_1]}{dt} &= k_{3}[ES_1] \\\\
\\frac{d[P_2]}{dt} &= k_{6}[ES_2]
"""

RUBRIC = f"""
The reference answer is:
{reference_answer}


- Reward responses that correctly define the rate of change functions of [S_1], [S_2], [ES_1], [ES_2], [P_1], and [P_2]
- Reward responses that are close to the reference answer
- Penalize responses that are not valid latex equations
"""
class EGCProblem5p1p1Workflow(WorkflowRunner):
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
        # last_message = self.messages[-1]
        # if last_message["role"] == "tool" and last_message.get("function", {}).get("name", None) == "report_answer": # Why would this ever be None?
        #     try:
        #         answer = json.loads(last_message["content"])
        #     except json.JSONDecodeError:
        #         print(f'Answer is not a valid json string: {last_message["content"]}')
        #         return {}
            
        #     # Use sympy to parse the answer and check if it is correct
        #     # We can do this by converting the answer to a sympy expression and checking if it is equal to the reference answer
        #     return {}
        # return {}
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
        adapter = ArtAdapter(EGCProblem5p1p1Workflow(
            example_name="EGCProblem5p1p1",
            prompt=PROMPT,
            use_reasoning_model=True,
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
    