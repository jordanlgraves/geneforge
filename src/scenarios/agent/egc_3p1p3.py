import json
from src.scenarios.agent.workflows import WorkflowRunner


PROMPT = """Consider the following reactions:

2S_1 &\xrightarrow{0.1} 2S_2 \\
S_1 + S_2 &\xrightarrow{0.2} 2S_1

The reaction rate equations are for [S_1] and [S_2] as follows:

\\frac{d[S_1]}{dt} &= 0.2[S_1][S_2] - 0.2[S_1]^2 \\
\\frac{d[S_2]}{dt} &= 0.2[S_1]^2 - 0.2[S_1][S_2]

Simulate using the Fourth-Order Runge-Kutta method the given set of differential 
equations for 1 second with a time step of 0.2 seconds starting with
initial concentrations of [S_1] = 3 .0 and [S_2] = 5 .0.

Use the `report_answer` tool to output your answer as a json string in the following format:

{
    "t=0.2": {
        "S_1": (float), # the concentration of [S_1] at t=0.2
        "S_2": (float), # the concentration of [S_2] at t=0.2
    },
    "t=0.4": {
        "S_1": (float), # the concentration of [S_1] at t=0.4
        "S_2": (float), # the concentration of [S_2] at t=0.4
    },
    
    "t=0.6": {
        "S_1": (float), # the concentration of [S_1] at t=0.6
        "S_2": (float), # the concentration of [S_2] at t=0.6
    },
    "t=0.8": {
        "S_1": (float), # the concentration of [S_1] at t=0.8
        "S_2": (float), # the concentration of [S_2] at t=0.8
    },
    
    "t=1.0": {
        "S_1": (float), # the concentration of [S_1] at t=1.0
        "S_2": (float), # the concentration of [S_2] at t=1.0
    }
}
"""

reference_answer = """
{
    "t=0.0": {
        "S_1": 3.0,
        "S_2": 5.0,
    },
    "t=0.2": {
        "S_1": 3.22,
        "S_2": 4.78,
    },
    "t=0.4": {
        "S_1": 3.40
        "S_2": 4.60,
    },
    "t=0.6": {
        "S_1": 3.55,
        "S_2": 4.45,
    },
    "t=0.8": {
        "S_1": 3.66,
        "S_2": 5.34,
    },
    "t=1.0": {
        "S_1": 3.75,
        "S_2": 4.25,
    }

"""

RUBRIC = None
class EGCProblem3p1p3Workflow(WorkflowRunner):
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
            try:
                answer = json.loads(last_message["content"])
            except json.JSONDecodeError:
                print(f'Answer is not a valid json string: {last_message["content"]}')
                return {}
            
            reference_answer_obj = json.loads(self.reference_answer)
            keys = reference_answer_obj.keys()
            num_correct = 0
            num_incorrect = 0
            for key in keys:
                if key not in answer:
                    num_incorrect += 1
                else:
                    answer_value = answer[key]
                    reference_value = reference_answer_obj[key]
                    if abs(answer_value - reference_value) < 0.0001:
                        num_correct += 1
                    else:
                        num_incorrect += 1
            return {
                "correct": num_correct == len(keys),
                "num_correct": num_correct,
                "num_incorrect": num_incorrect,
            }
        return {}

if __name__ == "__main__":
    workflow = EGCProblem3p1p3Workflow(
        example_name="EGCProblem3p1p3",
        prompt=PROMPT,
        use_reasoning_model=True,
    )
    workflow.run()
    
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
    