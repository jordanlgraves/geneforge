import json
from typing import Any, Dict, List

from src.scenarios.report_answer_scenario import ReportAnswerScenario
from src.scenarios.scenario import FailureCode
from src.utils.answer_parsing import coerce_answer_object


PROMPT = r"""Consider the following reactions:

2S_1 \xrightarrow{0.1} 2S_2
S_1 + S_2 \xrightarrow{0.2} 2S_1

The reaction rate equations are:

\frac{d[S_1]}{dt} = 0.2[S_1][S_2] - 0.2[S_1]^2
\frac{d[S_2]}{dt} = 0.2[S_1]^2 - 0.2[S_1][S_2]

Simulate using the Fourth-Order Runge–Kutta (RK4) method these ODEs for 1 second with
a time step of 0.2 seconds, starting with initial concentrations [S_1] = 3.0 and [S_2] = 5.0.

Use the `report_answer` tool to output a JSON string with time rows.
You may include t=0.0, but it is not required. This format is acceptable:

{
    "t=0.2": { "S_1": (float), "S_2": (float) },
    "t=0.4": { "S_1": (float), "S_2": (float) },
    "t=0.6": { "S_1": (float), "S_2": (float) },
    "t=0.8": { "S_1": (float), "S_2": (float) },
    "t=1.0": { "S_1": (float), "S_2": (float) }
}
"""

REFERENCE_JSON = """{
    "t=0.0": { "S_1": 3.0, "S_2": 5.0 },
    "t=0.2": { "S_1": 3.22, "S_2": 4.78 },
    "t=0.4": { "S_1": 3.40, "S_2": 4.60 },
    "t=0.6": { "S_1": 3.55, "S_2": 4.45 },
    "t=0.8": { "S_1": 3.66, "S_2": 4.34 },
    "t=1.0": { "S_1": 3.75, "S_2": 4.25 }
}"""

RUBRIC = None
INITIAL_S1 = 3.0
INITIAL_S2 = 5.0
REQUIRED_ROWS = ["t=0.2", "t=0.4", "t=0.6", "t=0.8", "t=1.0"]  # t=0.0 optional


class EGCProblem3p1p3Scenario(ReportAnswerScenario):
    def __init__(self, *args, **kwargs):
        self.reference_table: Dict[str, Dict[str, float]] = json.loads(REFERENCE_JSON)
        super().__init__(*args, **kwargs)

    def _process_prompt(self, prompt: str):
        return PROMPT

    def check_finished(self) -> bool:
        answer_tool_id = None
        for msg in self.messages:
            if msg["role"] == "assistant" and msg.get("tool_calls"):
                for tc in msg["tool_calls"]:
                    if tc.get("function", {}).get("name") == "report_answer":
                        answer_tool_id = tc["id"]; break
            if msg["role"] == "tool" and msg.get("tool_call_id") == answer_tool_id:
                return True
        return super().check_finished()

    @staticmethod
    def _close(a: Any, b: Any, tol: float = 1e-2) -> bool:
        try:
            return abs(float(a) - float(b)) <= tol
        except Exception:
            return False

    def _ensure_initial_row(self, ans: Dict[str, Any], parse_warnings: List[str]) -> None:
        if "t=0.0" not in ans:
            ans["t=0.0"] = {"S_1": INITIAL_S1, "S_2": INITIAL_S2}
            parse_warnings.append("synthesized_t0_from_initials")

    def get_metrics(self):
        base = super().get_metrics()
        reported = self.get_reported_answer_content()
        if not reported:
            self.record_failure(FailureCode.ANSWER_NOT_PROVIDED, "No `report_answer` payload to grade")
            base.update({"gave_answer": False, "failure_report": self.get_failure_report()})
            return base

        # Outer tool payload
        try:
            payload = json.loads(reported)
        except Exception as e:
            self.record_failure(FailureCode.BAD_JSON, "Tool payload not valid JSON",
                                payload_preview=str(reported)[:400], error=str(e))
            base.update({"gave_answer": True, "failure_report": self.get_failure_report()})
            return base

        # Inner answer (robust)
        ans_obj, parse_warnings = coerce_answer_object(payload.get("answer"))
        if not isinstance(ans_obj, dict):
            self.record_failure(FailureCode.ANSWER_PARSE_ERROR, "`answer` not parseable into object",
                                payload_preview=str(payload.get("answer"))[:400],
                                parse_warnings=parse_warnings)
            base.update({"gave_answer": True, "failure_report": self.get_failure_report()})
            return base

        # Optional t=0.0
        self._ensure_initial_row(ans_obj, parse_warnings)

        # Require only the rows we asked for
        missing = [k for k in REQUIRED_ROWS if k not in ans_obj]
        if missing:
            self.record_failure(FailureCode.ANSWER_PARSE_ERROR, "Missing required timepoints",
                                missing_timepoints=missing, parse_warnings=parse_warnings)
            base.update({"gave_answer": True, "failure_report": self.get_failure_report()})
            return base

        # Compare table
        ref = self.reference_table
        flags: Dict[str, bool] = {}
        ok = True
        check_rows = ["t=0.0"] + REQUIRED_ROWS
        for t in check_rows:
            try:
                a1 = ans_obj[t]["S_1"]; a2 = ans_obj[t]["S_2"]
                r1 = ref[t]["S_1"];     r2 = ref[t]["S_2"]
            except Exception as e:
                self.record_failure(FailureCode.ANSWER_PARSE_ERROR, "Missing S_1/S_2 in row",
                                    timepoint=t, error=str(e), parse_warnings=parse_warnings)
                base.update({"gave_answer": True, "failure_report": self.get_failure_report()})
                return base
            flags[f"{t}_S1_correct"] = self._close(a1, r1)
            flags[f"{t}_S2_correct"] = self._close(a2, r2)
            ok = ok and flags[f"{t}_S1_correct"] and flags[f"{t}_S2_correct"]

        if not ok:
            self.record_failure(FailureCode.WRONG_ANSWER, "RK4 table values deviate beyond tolerance",
                                details=flags, parse_warnings=parse_warnings)

        base.update({
            "gave_answer": True,
            "correct": ok,
            **flags,
            "parse_warnings": parse_warnings,
            "failure_report": self.get_failure_report(),
        })
        return base

    def get_nl_rubric(self):
        return RUBRIC


if __name__ == "__main__":
    ref = json.loads(REFERENCE_JSON)
    assert "t=0.0" in ref
    print("egc_3p1p3 ready.")
