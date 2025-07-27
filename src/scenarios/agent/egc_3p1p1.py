import json
from src.scenarios.agent.workflows import WorkflowRunner


PROMPT = """Consider the following reactions:

2S_1 &\xrightarrow{0.1} 2S_2 \\
S_1 + S_2 &\xrightarrow{0.2} 2S_1

Determine the reaction rate equations for [S_1] and [S_2]

Use the `report_answer` tool to output your answer as markdown with the following format:

\\frac{d[S_1]}{dt} &= equation for [S_1] \\
\\frac{d[S_2]}{dt} &= equation for [S_2]
"""

reference_answer = """
\\frac{d[S_1]}{dt} &= 0.2[S_1][S_2] - 0.2[S_1]^2 \\
\\frac{d[S_2]}{dt} &= 0.2[S_1]^2 - 0.2[S_1][S_2]
"""

RUBRIC = None
class EGCProblem3p1p1Workflow(WorkflowRunner):
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
            # Here we need to parse the answer and check if it is correct
            # We can do this by converting the answer to a sympy expression and checking if it is equal to the reference answer
            return {}
        return {}

if __name__ == "__main__":
    workflow = EGCProblem3p1p1Workflow(
        example_name="EGCProblem3p1p1",
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
    