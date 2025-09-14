import json
from src.latex_utils import get_latex_expr, compare_latex
from src.scenarios.report_answer_scenario import ReportAnswerScenario
from src.scenarios.scenario import FailureCode
from src.utils.answer_parsing import coerce_answer_object

PROMPT = """Coherent type-1 FFL (C1-FFL) with OR logic at Z:

Analyze the Coherent type-1 FFL with OR logic at the Z promoter.

Tasks:
- Provide delay lengths following ON (T_ON) and OFF (T_OFF) steps of Sx.
- Briefly state a biological use-case of this design.

Use the `report_answer` tool to submit JSON:
{
  "T_ON": "...",      # latex expression for T_ON
  "T_OFF": "...",     # expression for T_OFF in terms of Y_{m}^* level and K_YZ
  "use_case": "..."   # short text (any short text is acceptable)
}
"""

REF_T_ON = r"0"
REF_T_OFF = r"\frac{1}{\alpha}log(\frac{Y^*_{m}}{K_{YZ}})"
RUBRIC = None


class IntroToSysEng3p7(ReportAnswerScenario):
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

        # Parse outer tool payload
        try:
            payload = json.loads(reported)
        except Exception as e:
            self.record_failure(FailureCode.BAD_JSON, "Tool payload not valid JSON",
                                payload_preview=str(reported)[:400], error=str(e))
            base.update({"gave_answer": True, "failure_report": self.get_failure_report()})
            return base

        # Robustly parse inner "answer"
        ans_obj, warnings = coerce_answer_object(payload.get("answer"))
        if not isinstance(ans_obj, dict):
            self.record_failure(FailureCode.ANSWER_PARSE_ERROR, "`answer` not parseable into object",
                                payload_preview=str(payload.get("answer"))[:400],
                                parse_warnings=warnings)
            base.update({"gave_answer": True, "failure_report": self.get_failure_report()})
            return base

        # Compare LaTeX
        try:
            t_on_ok = compare_latex(get_latex_expr(ans_obj.get("T_ON")),
                                    get_latex_expr(REF_T_ON))
        except Exception as e:
            self.record_failure(FailureCode.ANSWER_PARSE_ERROR, "LaTeX parse failed for T_ON", error=str(e))
            t_on_ok = False

        try:
            t_off_ok = compare_latex(get_latex_expr(ans_obj.get("T_OFF")),
                                     get_latex_expr(REF_T_OFF))
        except Exception as e:
            self.record_failure(FailureCode.ANSWER_PARSE_ERROR, "LaTeX parse failed for T_OFF", error=str(e))
            t_off_ok = False

        ok = t_on_ok and t_off_ok
        if not ok:
            self.record_failure(FailureCode.WRONG_ANSWER, "C1-FFL delay expressions incorrect",
                                details={"T_ON_correct": t_on_ok, "T_OFF_correct": t_off_ok})

        base.update({
            "gave_answer": True,
            "correct": ok,
            "T_ON_correct": t_on_ok,
            "T_OFF_correct": t_off_ok,
            "parse_warnings": warnings,
            "failure_report": self.get_failure_report(),
        })
        return base


if __name__ == "__main__":
    from src.adapters.art_adapter import ArtAdapter
    import asyncio

    scenario = IntroToSysEng3p7(
        scenario_name="IntroToSysEng3p7",
        prompt=PROMPT,
    )
    adapter = ArtAdapter(scenario, step=0)
    asyncio.run(adapter.rollout())
    print(adapter.scenario.get_metrics())
    print("Done")
