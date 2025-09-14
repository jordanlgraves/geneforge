import json
from typing import Any, Dict, List

from src.scenarios.scenario import FailureCode
from src.scenarios.report_answer_scenario import ReportAnswerScenario
from src.utils.answer_parsing import coerce_answer_object


PROMPT = r"""Consider the following reactions:

2S_1 \xrightarrow{0.1} 2S_2
S_1 + S_2 \xrightarrow{0.2} 2S_1

The reaction rate equations are:

\frac{d[S_1]}{dt} = 0.2[S_1][S_2] - 0.2[S_1]^2
\frac{d[S_2]}{dt} = 0.2[S_1]^2 - 0.2[S_1][S_2]

Simulate using Euler’s method these ODEs for 1 second with a time step of 0.2 seconds,
starting with initial concentrations [S_1] = 3.0 and [S_2] = 5.0.

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

REFERENCE_JSON = """
{
    "t=0.0": { "S_1": 3.0,  "S_2": 5.0  },
    "t=0.2": { "S_1": 3.24, "S_2": 4.76 },
    "t=0.4": { "S_1": 3.44, "S_2": 4.56 },
    "t=0.6": { "S_1": 3.59, "S_2": 4.41 },
    "t=0.8": { "S_1": 3.71, "S_2": 4.29 },
    "t=1.0": { "S_1": 3.8,  "S_2": 4.2  }
}
"""

RUBRIC = None
INITIAL_S1 = 3.0
INITIAL_S2 = 5.0
REQUIRED_ROWS = ["t=0.2", "t=0.4", "t=0.6", "t=0.8", "t=1.0"]  # t=0.0 is optional


class EGCProblem3p1p2Scenario(ReportAnswerScenario):
    def __init__(self, *args, **kwargs):
        self.reference_table: Dict[str, Dict[str, float]] = json.loads(REFERENCE_JSON)
        super().__init__(*args, **kwargs)

    def _process_prompt(self, prompt: str):
        return PROMPT

    def check_finished(self) -> bool:
        # Finish when report_answer result is present
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
        """Inject t=0.0 from initial conditions if it is absent."""
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

        # Optional t=0.0 handling (don’t fail for missing; synthesize)
        self._ensure_initial_row(ans_obj, parse_warnings)

        # Require the rows we actually asked for in the prompt
        missing = [k for k in REQUIRED_ROWS if k not in ans_obj]
        if missing:
            self.record_failure(FailureCode.ANSWER_PARSE_ERROR, "Missing required timepoints",
                                missing_timepoints=missing, parse_warnings=parse_warnings)
            base.update({"gave_answer": True, "failure_report": self.get_failure_report()})
            return base

        # Compare with reference
        ref = self.reference_table
        flags: Dict[str, bool] = {}
        ok = True
        check_rows = ["t=0.0"] + REQUIRED_ROWS  # we’ll check t=0.0 too (synthesized if needed)
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
            self.record_failure(FailureCode.WRONG_ANSWER, "Euler table values deviate beyond tolerance",
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
    # quick sanity
    ref = json.loads(REFERENCE_JSON)
    assert "t=0.0" in ref
    print("egc_3p1p2 ready.")
