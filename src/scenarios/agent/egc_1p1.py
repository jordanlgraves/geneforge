import json
from src.scenarios.agent.workflows import WorkflowRunner


PROMPT = """Consider the first part of the enzymatic reaction:

E + S \\overset{k_1}{\\underset{k_2}{\\rightleftharpoons}} ES

Assume the following parameters for an enzymatic reaction:
	•	k_1 = 0.01 \\,\\text{s}^{-1}\\,\\text{nM}^{-1}
	•	k_{-1} = 0.1 \\,\\text{s}^{-1}
	•	[E] = 35 \\,\\text{nM}
	•	[S] = 100 \\,\\text{nM}
	•	[ES] = 50 \\,\\text{nM}
	•	RT = 0.5961 \\,\\text{kcal mol}^{-1} (i.e., T = 300\\,\\text{K})

Task:
Determine the change in Gibbs Free Energy (\\Delta G) for the forward reaction.
Is the forward or reverse reaction favored?
Then, using trial-and-error, find the concentrations of [E], [S], and [ES] that result in steady state (i.e., \\Delta G = 0).
Note: Every nM added to [ES] must be subtracted equally from both [E] and [S].

Use the `report_answer` tool to output your answer as a json string in the following format:

{
    "dG": (float), # the change in Gibbs Free Energy (kcal/mol) for the forward reaction	
    "reaction_favored": (string), # either "forward" or "reverse"
    "explanation": (string), # a short explanation of your answer
    "ES": (float), # the concentration of [ES] that results in steady state (i.e., \\Delta G = 0)
    "S": (float), # the concentration of [S] that results in steady state (i.e., \\Delta G = 0)
    "E": (float), # the concentration of [E] that results in steady state (i.e., \\Delta G = 0)
}
"""

reference_answer = {
    "dG": -1.16,
    "reaction_favored": "forward",
    "explanation": "We use the standard thermodynamic equation: \\Delta G = RT \\ln\\left(\\frac{k_{-1} [ES]}{k_1 [E][S]}\\right). Substituting values: \\Delta G = 0.5961 \\cdot \\ln\\left(\\frac{0.1 \\cdot 50}{0.01 \\cdot 35 \\cdot 100}\\right). \\Delta G = 0.5961 \\cdot \\ln\\left(\\frac{5}{35}\\right) = 0.5961 \\cdot \\ln(0.142857). \\Delta G \\approx 0.5961 \\cdot (-1.9459) = -1.16 \\,\\text{kcal/mol}. Since \\Delta G < 0, the forward reaction is favored. At steady state (\\Delta G = 0), trial-and-error shows that: \\\\[ES] = 75 \\,\\text{nM}\\\\ [S] = 75 \\,\\text{nM}\\\\ [E] = 10 \\,\\text{nM}\\\\ This satisfies the condition that the total amount of enzyme and substrate is conserved, and results in \\Delta G = 0.",
    "ES": 75,
    "S": 75,
    "E": 10
}

RUBRIC = None
class EGCProblem1p1Workflow(WorkflowRunner):
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
        last_message = self.messages[-1]
        if last_message["role"] == "tool" and last_message.get("function", {}).get("name", None) == "report_answer": # Why would this ever be None?
            answer = json.loads(last_message["content"])
            ES_correct = abs(answer.get("ES", 0) - self.reference_answer["ES"]) < 0.01
            S_correct = abs(answer.get("S", 0) - self.reference_answer["S"]) < 0.01
            E_correct = abs(answer.get("E", 0) - self.reference_answer["E"]) < 0.01
            reaction_direction_correct = answer.get("reaction_favored", "").lower() == self.reference_answer["reaction_favored"].lower()
            dg_correct = abs(answer["dG"] - self.reference_answer["dG"]) < 0.01
            is_correct = ES_correct and S_correct and E_correct and reaction_direction_correct and dg_correct
            return {
                "num_rounds": len(self.messages),
                "correct": is_correct,
                "ES_correct": ES_correct,
                "S_correct": S_correct,
                "E_correct": E_correct,
                "reaction_direction_correct": reaction_direction_correct,
                "dg_correct": dg_correct,
            }
        return {}

if __name__ == "__main__":
    from src.adapters.art_adapter import ArtAdapter
    import asyncio
    
    trajectories = []
    for i in range(3):
        workflow = EGCProblem1p1Workflow(
            example_name="EGCProblem1p1",
            prompt=PROMPT,
            use_reasoning_model=True,
        )
        adapter = ArtAdapter(workflow, step=0)
        trajectory = asyncio.run(adapter.rollout())
        trajectories.append(trajectory)
    
    from art import TrajectoryGroup
    trajectory_group = TrajectoryGroup(trajectories)
    from art.rewards.ruler import ruler_score_group
    score = asyncio.run(ruler_score_group(trajectory_group))
    print(score)
    
    # get the report_answer tool call
    for message in workflow.messages:
        if message["role"] == "tool" and message.get("function", {}).get("name", None) == "report_answer": # Why would this ever be None?
            answer_message = message
            break
    
    sample = {
        "output_text": workflow.messages[-1]["content"], 
        "reference_answer": reference_answer,
    }
    item = {
        "reference_answer": reference_answer,
    }
    from src.rl.graders.grade_egc_promblem1p1 import grade
    score = grade(sample, item)
    print(score)