import json
from src.scenarios.report_answer_scenario import ReportAnswerScenario
from src.latex_utils import compare_latex, get_latex_expr
from src.scenarios.scenario import FailureCode
from src.utils.answer_parsing import coerce_answer_object, clean_math

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
        answer_tool_id = None
        for message in self.messages:
            if message["role"] == "assistant" and message.get("tool_calls"):
                for tool_call in message["tool_calls"]:
                    if tool_call.get("function", {}).get("name") == "report_answer":
                        answer_tool_id = tool_call["id"]; break
            if message["role"] == "tool" and message.get("tool_call_id") == answer_tool_id:
                return True
        return super().check_finished()

    def get_metrics(self):
        base = super().get_metrics()
        reported = self.get_reported_answer_content()
        if not reported:
            self.record_failure(FailureCode.ANSWER_NOT_PROVIDED, "No `report_answer` payload to grade")
            base.update({"gave_answer": False, "failure_report": self.get_failure_report()})
            return base

        # Parse outer tool payload
        try:
            answer_json = json.loads(reported)
        except Exception as e:
            self.record_failure(FailureCode.BAD_JSON, "Reported payload is not valid JSON",
                                payload_preview=str(reported)[:400], error=str(e))
            base.update({"gave_answer": True, "failure_report": self.get_failure_report()})
            return base

        # Robust coercion for inner answer
        raw_answer = answer_json.get("answer")
        ans_obj, warnings = coerce_answer_object(raw_answer)
        if ans_obj is None:
            self.record_failure(FailureCode.ANSWER_PARSE_ERROR, "`answer` could not be coerced into an object",
                                payload_preview=str(raw_answer)[:400], parse_warnings=warnings)
            base.update({"gave_answer": True, "failure_report": self.get_failure_report()})
            return base

        # Required keys
        required = ["d[S_1]/dt", "d[S_2]/dt"]
        missing = [k for k in required if k not in ans_obj]
        if missing:
            self.record_failure(FailureCode.ANSWER_PARSE_ERROR, "Missing required key(s)",
                                missing_keys=missing, parse_warnings=warnings)
            base.update({"gave_answer": True, "failure_report": self.get_failure_report()})
            return base

        # Clean + LaTeX compare
        s1_text = clean_math(ans_obj.get("d[S_1]/dt"))
        s2_text = clean_math(ans_obj.get("d[S_2]/dt"))

        try:
            ans_s1 = get_latex_expr(s1_text)
            ans_s2 = get_latex_expr(s2_text)
            ref_s1 = get_latex_expr(self.reference_answer.get("d[S_1]/dt"))
            ref_s2 = get_latex_expr(self.reference_answer.get("d[S_2]/dt"))
        except Exception as e:
            self.record_failure(FailureCode.ANSWER_PARSE_ERROR, "LaTeX parsing failed", error=str(e),
                                submitted={"d[S_1]/dt": s1_text, "d[S_2]/dt": s2_text},
                                parse_warnings=warnings)
            base.update({"gave_answer": True, "failure_report": self.get_failure_report()})
            return base

        dS1_ok = compare_latex(ans_s1, ref_s1)
        dS2_ok = compare_latex(ans_s2, ref_s2)
        is_correct = dS1_ok and dS2_ok
        if not is_correct:
            self.record_failure(FailureCode.WRONG_ANSWER, "Rate equations do not match reference",
                                details={"dS_1": dS1_ok, "dS_2": dS2_ok},
                                parse_warnings=warnings)

        base.update({
            "gave_answer": True,
            "correct": is_correct,
            "dS1dt_correct": dS1_ok,
            "dS2dt_correct": dS2_ok,
            "failure_report": self.get_failure_report(),
            "parse_warnings": warnings,
        })
        return base

    def get_nl_rubric(self):
        return RUBRIC


if __name__ == "__main__":
    scenario = EGCProblem3p1p1Scenario(
        scenario_name="EGCProblem3p1p1",
        prompt=PROMPT,
    )
    # scenario.run()
    
    answer = "{\\n    \\\"d[S_1]/dt\\\": \\\"```latex\\n        \\\\\\\\frac{d[S_1]}{dt} = -0.2[S_1]^2 + 0.2[S_1][S_2]\\n    ```\\\",\\n    \\\"d[S_2]/dt\\\": \\\"```latex\\n        \\\\\\\\frac{d[S_2]}{dt} = 0.2[S_1]^2 - 0.2[S_1][S_2]\\n    ```\\\"\\n}\"}"
    print(coerce_answer_object(answer))
    print('\n')
    print(json.loads(answer))
    print('\n')
    print(get_latex_expr(answer))
    print('\n')
    print(get_latex_expr(reference_answer.get("d[S_1]/dt")))
    print('\n')
    print(get_latex_expr(reference_answer.get("d[S_2]/dt")))

