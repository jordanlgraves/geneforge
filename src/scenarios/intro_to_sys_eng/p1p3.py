import json
import re
from src.scenarios.report_answer_scenario import ReportAnswerScenario
from src.latex_utils import get_latex_expr, compare_latex
from src.scenarios.scenario import FailureCode

PROMPT = """Time-dependent production and decay: A gene Y with simple regulation has a time-dependent
production rate \\beta(t) and a time-dependent degradation/dilution rate \\alpha(t). Solve for its
concentration Y(t) as a function of time.

Use the `report_answer` tool to submit your answer in this JSON format, with a single latex expression for Y(t):

{
  "answer": latex expression for Y(t)
}
"""

REFERENCE = r"e^{-\int_0^t \alpha(t')\,dt'}\,\left( Y(0) + \int_0^t \beta(t')\,e^{\int_{0}^{t} \alpha(t'')\,dt''}\,dt' \right)"
RUBRIC = None


def _strip_code_fences(s: str) -> str:
    if not isinstance(s, str):
        return s
    m = re.match(r"^\s*```(?:latex)?\s*([\s\S]*?)\s*```\s*$", s)
    return m.group(1) if m else s.strip()


class IntroToSysEng1p3(ReportAnswerScenario):
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

    scenario = IntroToSysEng1p3(
        scenario_name="IntroToSysEng1p3",
        prompt=PROMPT,
    )
    adapter = ArtAdapter(scenario, step=0)
    asyncio.run(adapter.rollout())
    print(adapter.scenario.get_metrics())
    print("Done")
