import json
from typing import Dict, Any

from src.scenarios.report_answer_scenario import ReportAnswerScenario
from src.latex_utils import compare_latex, get_latex_expr
from src.scenarios.scenario import FailureCode
from src.utils.answer_parsing import coerce_answer_object, clean_math


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

reference_answer = {
    "d[S_1]/dt": "k_{2}[ES_1] - k_{1}[E][S_1]",
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
        self.reference_answer = reference_answer
        super().__init__(*args, **kwargs)

    def _process_prompt(self, prompt: str):
        return PROMPT

    def check_finished(self) -> bool:
        answer_tool_id = None
        for message in self.messages:
            if message["role"] == "assistant" and message.get("tool_calls"):
                for tc in message["tool_calls"]:
                    if tc.get("function", {}).get("name") == "report_answer":
                        answer_tool_id = tc["id"]; break
            if message["role"] == "tool" and message.get("tool_call_id") == answer_tool_id:
                return True
        return super().check_finished()

    def _compare_field(self, ans: Dict[str, Any], key: str) -> bool:
        try:
            text = clean_math(ans.get(key))
            a = get_latex_expr(text)
            b = get_latex_expr(self.reference_answer.get(key))
            return compare_latex(a, b)
        except Exception:
            return False

    def get_metrics(self):
        base = super().get_metrics()
        reported_answer = self.get_reported_answer_content()
        if not reported_answer:
            self.record_failure(FailureCode.ANSWER_NOT_PROVIDED, "No `report_answer` payload to grade")
            base.update({"gave_answer": False, "failure_report": self.get_failure_report()})
            return base

        # Parse outer tool payload
        try:
            outer = json.loads(reported_answer)
        except Exception as e:
            self.record_failure(FailureCode.BAD_JSON, "Tool payload not valid JSON",
                                payload_preview=str(reported_answer)[:400], error=str(e))
            base.update({"gave_answer": True, "failure_report": self.get_failure_report()})
            return base

        # Inner "answer" may be dict or stringified; coerce robustly
        ans_obj, warns = coerce_answer_object(outer.get("answer"))
        if not isinstance(ans_obj, dict):
            self.record_failure(FailureCode.ANSWER_PARSE_ERROR, "`answer` not parseable into object",
                                parse_warnings=warns, payload_preview=str(outer.get("answer"))[:400])
            base.update({"gave_answer": True, "failure_report": self.get_failure_report()})
            return base

        # Required keys
        required = ["d[S_1]/dt","d[S_2]/dt","d[ES_1]/dt","d[ES_2]/dt","d[P_1]/dt","d[P_2]/dt"]
        missing = [k for k in required if k not in ans_obj]
        if missing:
            self.record_failure(FailureCode.ANSWER_PARSE_ERROR, "Missing required key(s)",
                                missing_keys=missing, parse_warnings=warns)
            base.update({"gave_answer": True, "failure_report": self.get_failure_report()})
            return base

        # Per-field comparisons
        flags = { f"{k}_correct": self._compare_field(ans_obj, k) for k in required }
        is_correct = all(flags.values())
        if not is_correct:
            self.record_failure(FailureCode.WRONG_ANSWER, "One or more rate equations differ",
                                details=flags, parse_warnings=warns)

        base.update({
            "gave_answer": True,
            "correct": is_correct,
            **flags,
            "parse_warnings": warns,
            "failure_report": self.get_failure_report(),
        })
        return base

    def get_nl_rubric(self):
        return RUBRIC


if __name__ == "__main__":
    import asyncio
    from src.adapters.art_adapter import ArtAdapter

    adapter = ArtAdapter(EGCProblem5p1p1Scenario(
        scenario_name="EGCProblem5p1p1",
        prompt=PROMPT
    ), step=0)
    traj = asyncio.run(adapter.rollout())
    print(traj)
