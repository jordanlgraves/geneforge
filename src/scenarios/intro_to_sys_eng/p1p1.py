import json
import re
from src.scenarios.report_answer_scenario import ReportAnswerScenario
from src.latex_utils import compare_latex, get_latex_expr
from src.scenarios.scenario import FailureCode

PROMPT = """A change in production rate: A gene Y with simple regulation is produced at a constant
rate β1. The production rate suddenly shifts to a different rate β2.
a. Calculate and plot the gene product concentration Y(t).

Use the `report_answer` tool to submit your answer as a string in the following format:

{
    "answer": (string), # the equation for Y(t) as latex with no preamble, explanation, or other text
}
"""

# Reference: Y(t) = β2/α + (β1/α − β2/α)e−αt
REFERENCE = r"\frac{\beta_2}{\alpha} + \left(\frac{\beta_1}{\alpha} - \frac{\beta_2}{\alpha}\right)e^{-\alpha t}"
RUBRIC = None


def _strip_code_fences(s: str) -> str:
    if not isinstance(s, str):
        return s
    # remove surrounding ```...``` or ```latex ... ``` if present
    m = re.match(r"^\s*```(?:latex)?\s*([\s\S]*?)\s*```\s*$", s)
    return m.group(1) if m else s.strip()


class IntroToSysEng1p1(ReportAnswerScenario):
    def __init__(self, *args, **kwargs):
        self.reference_answer = REFERENCE
        super().__init__(*args, **kwargs)

    def _process_prompt(self, prompt: str):
        return PROMPT

    def check_finished(self) -> bool:
        return self._is_answer_reported() or super().check_finished()

    def get_metrics(self):
        base = super().get_metrics()
        reported = self.get_reported_answer_content()
        if not reported:
            self.record_failure(FailureCode.ANSWER_NOT_PROVIDED, "No `report_answer` payload to grade")
            base.update({"gave_answer": False, "failure_report": self.get_failure_report()})
            return base

        try:
            payload = json.loads(reported)
            raw = payload.get("answer")
            if raw is None:
                raise ValueError("Missing `answer`")

            # tolerate odd wrapping / code fences
            if not isinstance(raw, str):
                raw = str(raw)
            expr_text = _strip_code_fences(raw)

            expr_model = get_latex_expr(expr_text)
            expr_ref = get_latex_expr(self.reference_answer)
            ok = compare_latex(expr_model, expr_ref)

            if not ok:
                self.record_failure(FailureCode.WRONG_ANSWER, "Closed-form Y(t) does not match reference",
                                    details={"submitted": str(expr_model), "reference": str(expr_ref)})

            base.update({
                "num_rounds": len(self.messages),
                "correct": ok,
                "gave_answer": True,
                "failure_report": self.get_failure_report(),
            })
            return base

        except Exception as e:
            self.record_failure(FailureCode.ANSWER_PARSE_ERROR, "Failed to parse reported answer",
                                payload_preview=str(reported)[:400], error=str(e))
            base.update({"gave_answer": True, "failure_report": self.get_failure_report()})
            return base


if __name__ == "__main__":
    from src.adapters.art_adapter import ArtAdapter
    import asyncio

    scenario = IntroToSysEng1p1(
        scenario_name="IntroToSysEng1p1",
        prompt=PROMPT
    )
    adapter = ArtAdapter(scenario, step=0)
    asyncio.run(adapter.rollout(temperature=1.0))
    print(adapter.scenario.get_metrics())
    print('Done')
