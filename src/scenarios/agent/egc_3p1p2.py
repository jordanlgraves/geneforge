import json
from src.scenarios.agent.workflows import WorkflowRunner


PROMPT = """Consider the following reactions:

2S_1 \\xrightarrow{0.1} 2S_2 \\
S_1 + S_2 \\xrightarrow{0.2} 2S_1

The reaction rate equations are for [S_1] and [S_2] as follows:

\\frac{d[S_1]}{dt} &= 0.2[S_1][S_2] - 0.2[S_1]^2 \\
\\frac{d[S_2]}{dt} &= 0.2[S_1]^2 - 0.2[S_1][S_2]

Simulate using Euler’s method the given set of differential 
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
        "S_2": 5.0
    },
    "t=0.2": {
        "S_1": 3.24,
        "S_2": 4.76
    },  
    "t=0.4": {
        "S_1": 3.44,
        "S_2": 4.56
    },
    "t=0.6": {
        "S_1": 3.59,
        "S_2": 4.41
    },
    "t=0.8": {
        "S_1": 3.71,
        "S_2": 4.29
    },
    "t=1.0": {
        "S_1": 3.8,
        "S_2": 4.2
    }
}
"""

RUBRIC = None
class EGCProblem3p1p2Workflow(WorkflowRunner):
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
            answer = json.loads(reported_answer)
        except Exception:
            print(f'Error parsing answer: {reported_answer}')
            return super().get_metrics()
        
        # Check if the answer is correct
        reference_json = json.loads(self.reference_answer)
        threshold = 0.01
        num_correct = 0
        num_incorrect = 0
        for time_key, concentrations in reference_json.items():
            if time_key not in answer:
                num_incorrect += 2
                continue            
            for species, answer_value in concentrations.items():
                if species not in answer[time_key]:
                    num_incorrect += 1
                    continue
                if abs(answer[time_key][species] - answer_value) > threshold:
                    num_incorrect += 1
                    continue
                num_correct += 1
            
        return {
            "gave_answer": True,
            "correct": num_incorrect <= 0,
            "num_correct": num_correct,
            "num_incorrect": num_incorrect,
            **super().get_metrics()
        }
    
    def get_nl_rubric(self):
        return RUBRIC

if __name__ == "__main__":
    # workflow = EGCProblem3p1p2Workflow(
    #     example_name="EGCProblem3p1p2",
    #     prompt=PROMPT,
    #     use_reasoning_model=True,
    # )
    # workflow.run()
    
    # # get the report_answer tool call
    # for message in workflow.messages:
    #     if message["role"] == "tool" and message.get("function", {}).get("name", None) == "report_answer": # Why would this ever be None?
    #         answer_message = message
    #         break
    
    # sample = {
    #     "output_text": workflow.messages[-1]["content"], 
    #     "reference_answer": reference_answer,
    # }
    # item = {
    #     "reference_answer": reference_answer,
    # }
    
    print(json.loads(reference_answer))