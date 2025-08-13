import json
from src.scenarios.report_answer_scenario import ReportAnswerScenario

PROMPT = """Consider the following reactions:

2S_1 &\\xrightarrow{0.1} 2S_2 \\
S_1 + S_2 &\\xrightarrow{0.2} 2S_1

The reaction rate equations are for [S_1] and [S_2] as follows:

\\frac{d[S_1]}{dt} &= 0.2[S_1][S_2] - 0.2[S_1]^2 \\
\\frac{d[S_2]}{dt} &= 0.2[S_1]^2 - 0.2[S_1][S_2]

Simulate using the Fourth-Order Runge-Kutta method the given set of differential 
equations for 1 second with a time step of 0.2 seconds starting with
initial concentrations of [S_1] = 3 .0 and [S_2] = 5 .0.

Use the `report_answer` tool to output your answer as a json string in the following format:

{
    "t=0.0": {
        "S_1": (float), # the concentration of [S_1] at t=0.0
        "S_2": (float), # the concentration of [S_2] at t=0.0
    },
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

reference_answer = """{
    "t=0.0": {
        "S_1": 3.0,
        "S_2": 5.0
    },
    "t=0.2": {
        "S_1": 3.22,
        "S_2": 4.78
    },
    "t=0.4": {
        "S_1": 3.40,
        "S_2": 4.60
    },
    "t=0.6": {
        "S_1": 3.55,
        "S_2": 4.45
    },
    "t=0.8": {
        "S_1": 3.66,
        "S_2": 5.34
    },
    "t=1.0": {
        "S_1": 3.75,
        "S_2": 4.25
    }
}"""

RUBRIC = None
class EGCProblem3p1p3Scenario(ReportAnswerScenario):
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
        except Exception:
            print(f'Error parsing answer: {reported_answer}')
            return super().get_metrics()
        
        # Check if the answer is correct
        t0p0_S1 = answer.get("t=0.0").get("S_1")
        t0p0_S2 = answer.get("t=0.0").get("S_2")
        t0p2_S1 = answer.get("t=0.2").get("S_1")
        t0p2_S2 = answer.get("t=0.2").get("S_2")
        t0p4_S1 = answer.get("t=0.4").get("S_1")
        t0p4_S2 = answer.get("t=0.4").get("S_2")
        t0p6_S1 = answer.get("t=0.6").get("S_1")
        t0p6_S2 = answer.get("t=0.6").get("S_2")
        t0p8_S1 = answer.get("t=0.8").get("S_1")
        t0p8_S2 = answer.get("t=0.8").get("S_2")
        t1_S1 = answer.get("t=1.0").get("S_1")
        t1_S2 = answer.get("t=1.0").get("S_2")
        reference_json = json.loads(self.reference_answer)
        t0p0_S1_ref = reference_json.get("t=0.0").get("S_1")
        t0p0_S2_ref = reference_json.get("t=0.0").get("S_2")
        t0p2_S1_ref = reference_json.get("t=0.2").get("S_1")
        t0p2_S2_ref = reference_json.get("t=0.2").get("S_2")
        t0p4_S1_ref = reference_json.get("t=0.4").get("S_1")
        t0p4_S2_ref = reference_json.get("t=0.4").get("S_2")
        t0p6_S1_ref = reference_json.get("t=0.6").get("S_1")
        t0p6_S2_ref = reference_json.get("t=0.6").get("S_2")
        t0p8_S1_ref = reference_json.get("t=0.8").get("S_1")
        t0p8_S2_ref = reference_json.get("t=0.8").get("S_2")
        t1_S1_ref = reference_json.get("t=1.0").get("S_1")
        t1_S2_ref = reference_json.get("t=1.0").get("S_2")
        
        is_correct = abs(t0p0_S1 - t0p0_S1_ref) < 0.01 and abs(t0p0_S2 - t0p0_S2_ref) < 0.01 and abs(t0p2_S1 - t0p2_S1_ref) < 0.01 and abs(t0p2_S2 - t0p2_S2_ref) < 0.01 and abs(t0p4_S1 - t0p4_S1_ref) < 0.01 and abs(t0p4_S2 - t0p4_S2_ref) < 0.01 and abs(t0p6_S1 - t0p6_S1_ref) < 0.01 and abs(t0p6_S2 - t0p6_S2_ref) < 0.01 and abs(t0p8_S1 - t0p8_S1_ref) < 0.01 and abs(t0p8_S2 - t0p8_S2_ref) < 0.01 and abs(t1_S1 - t1_S1_ref) < 0.01 and abs(t1_S2 - t1_S2_ref) < 0.01
        
        return {
            "gave_answer": True,
            "correct": is_correct,
            "t0p0_S1_correct": abs(t0p0_S1 - t0p0_S1_ref) < 0.01,
            "t0p0_S2_correct": abs(t0p0_S2 - t0p0_S2_ref) < 0.01,
            "t0p2_S1_correct": abs(t0p2_S1 - t0p2_S1_ref) < 0.01,
            "t0p2_S2_correct": abs(t0p2_S2 - t0p2_S2_ref) < 0.01,
            "t0p4_S1_correct": abs(t0p4_S1 - t0p4_S1_ref) < 0.01,
            "t0p4_S2_correct": abs(t0p4_S2 - t0p4_S2_ref) < 0.01,
            "t0p6_S1_correct": abs(t0p6_S1 - t0p6_S1_ref) < 0.01,
            "t0p6_S2_correct": abs(t0p6_S2 - t0p6_S2_ref) < 0.01,
            "t0p8_S1_correct": abs(t0p8_S1 - t0p8_S1_ref) < 0.01,
            "t0p8_S2_correct": abs(t0p8_S2 - t0p8_S2_ref) < 0.01,
            "t1_S1_correct": abs(t1_S1 - t1_S1_ref) < 0.01,
            "t1_S2_correct": abs(t1_S2 - t1_S2_ref) < 0.01,
            **super().get_metrics()
        }
    
        
    def get_nl_rubric(self):
        return RUBRIC

if __name__ == "__main__":
    # workflow = EGCProblem3p1p3Workflow(
    #     scenario_name="EGCProblem3p1p3",
    #     prompt=PROMPT
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
    
    import json
    print(json.loads(reference_answer))