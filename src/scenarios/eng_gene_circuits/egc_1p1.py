import json
from typing import Any, Dict, Tuple

from src.scenarios.report_answer_scenario import ReportAnswerScenario
from src.scenarios.scenario import FailureCode
from src.utils.answer_parsing import coerce_answer_object  # robust, fence-tolerant


PROMPT = """Consider the first part of the enzymatic reaction:

E + S \\overset{k_1}{\\underset{k_2}{\\rightleftharpoons}} ES

Assume the following parameters for an enzymatic reaction:
\t•\tk_1 = 0.01 \\,\\text{s}^{-1}\\,\\text{nM}^{-1}
\t•\tk_{-1} = 0.1 \\,\\text{s}^{-1}
\t•\t[E] = 35 \\,\\text{nM}
\t•\t[S] = 100 \\,\\text{nM}
\t•\t[ES] = 50 \\,\\text{nM}
\t•\tRT = 0.5961 \\,\\text{kcal mol}^{-1} (i.e., T = 300\\,\\text{K})

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
    "ES": (float), # the concentration of [ES] at steady state (\\Delta G = 0)
    "S": (float),  # the concentration of [S] at steady state (\\Delta G = 0)
    "E": (float)   # the concentration of [E] at steady state (\\Delta G = 0)
}
"""

reference_answer = {
    "dG": -1.16,
    "reaction_favored": "forward",
    "explanation": "We use the standard thermodynamic equation: \\Delta G = RT \\ln\\left(\\frac{k_{-1} [ES]}{k_1 [E][S]}\\right). Substituting values: \\Delta G = 0.5961 \\cdot \\ln\\left(\\frac{0.1 \\cdot 50}{0.01 \\cdot 35 \\cdot 100}\\right). \\Delta G = 0.5961 \\cdot \\ln\\left(\\frac{5}{35}\\right) = 0.5961 \\cdot \\ln(0.142857). \\Delta G \\approx 0.5961 \\cdot (-1.9459) = -1.16 \\,\\text{kcal/mol}. Since \\Delta G < 0, the forward reaction is favored. At steady state (\\Delta G = 0), trial-and-error shows that: \\\\[ES] = 75 \\,\\text{nM}\\\\ [S] = 75 \\,\\text{nM}\\\\ [E] = 10 \\,\\text{nM}\\\\ This satisfies the condition that the total amount of enzyme and substrate is conserved, and results in \\Delta G = 0.",
    "ES": 75.0,
    "S": 75.0,
    "E": 10.0,
}

RUBRIC = None


class EGCProblem1p1Scenario(ReportAnswerScenario):
    def __init__(self, *args, **kwargs):
        self.reference_answer = reference_answer
        super().__init__(*args, **kwargs)

    def _process_prompt(self, prompt: str):
        return PROMPT

    def check_finished(self) -> bool:
        # Finish when report_answer tool result is present (or fall back to base)
        answer_tool_id = None
        for message in self.messages:
            if message["role"] == "assistant" and message.get("tool_calls"):
                for tc in message["tool_calls"]:
                    if tc.get("function", {}).get("name") == "report_answer":
                        answer_tool_id = tc["id"]
                        break
            if message["role"] == "tool" and message.get("tool_call_id") == answer_tool_id:
                return True
        return super().check_finished()

    def _close(self, a: Any, b: Any, tol: float = 1e-2) -> bool:
        try:
            return abs(float(a) - float(b)) <= tol
        except Exception:
            return False

    def get_metrics(self):
        base = super().get_metrics()
        reported = self.get_reported_answer_content()

        if not reported:
            self.record_failure(FailureCode.ANSWER_NOT_PROVIDED, "No `report_answer` payload to grade")
            base.update({"correct": False, "gave_answer": False, "failure_report": self.get_failure_report()})
            return base

        # Parse outer tool payload
        try:
            outer = json.loads(reported)
        except Exception as e:
            self.record_failure(FailureCode.BAD_JSON, "Tool payload not valid JSON",
                                payload_preview=str(reported)[:400], error=str(e))
            base.update({"correct": False, "gave_answer": True, "failure_report": self.get_failure_report()})
            return base

        # Robustly coerce inner "answer" (handles stringified/escaped)
        ans_obj, warns = coerce_answer_object(outer.get("answer"))
        if not isinstance(ans_obj, dict):
            self.record_failure(FailureCode.ANSWER_PARSE_ERROR, "`answer` not parseable into object",
                                parse_warnings=warns, payload_preview=str(outer.get("answer"))[:400])
            base.update({"correct": False, "gave_answer": True, "failure_report": self.get_failure_report()})
            return base

        # Validate presence
        required = ["dG", "reaction_favored", "ES", "S", "E"]
        missing = [k for k in required if k not in ans_obj]
        if missing:
            self.record_failure(FailureCode.ANSWER_PARSE_ERROR, "Missing required keys", missing_keys=missing,
                                parse_warnings=warns)
            base.update({"correct": False, "gave_answer": True, "failure_report": self.get_failure_report()})
            return base

        # Compare numerics (tolerant) + direction
        ref = self.reference_answer
        dG_ok = self._close(ans_obj.get("dG"), ref["dG"])
        ES_ok = self._close(ans_obj.get("ES"), ref["ES"])
        S_ok = self._close(ans_obj.get("S"), ref["S"])
        E_ok = self._close(ans_obj.get("E"), ref["E"])
        dir_ok = str(ans_obj.get("reaction_favored", "")).strip().lower() == ref["reaction_favored"].lower()

        is_correct = dG_ok and ES_ok and S_ok and E_ok and dir_ok
        if not is_correct:
            self.record_failure(
                FailureCode.WRONG_ANSWER,
                "One or more fields deviate beyond tolerance",
                details={"dG": dG_ok, "ES": ES_ok, "S": S_ok, "E": E_ok, "direction": dir_ok},
                parse_warnings=warns,
            )

        base.update({
            "gave_answer": True,
            "correct": is_correct,
            "dG_correct": dG_ok,
            "ES_correct": ES_ok,
            "S_correct": S_ok,
            "E_correct": E_ok,
            "direction_correct": dir_ok,
            "parse_warnings": warns,
            "failure_report": self.get_failure_report(),
        })
        return base


if __name__ == "__main__":
    from src.adapters.art_adapter import ArtAdapter
    import asyncio

    scenario = EGCProblem1p1Scenario(
        scenario_name="EGCProblem1p1",
        prompt=PROMPT,
        model_name="gemini/gemini-2.5-flash",
    )
    adapter = ArtAdapter(scenario, step=0)
    trajectory = asyncio.run(adapter.rollout())
    print(trajectory)
