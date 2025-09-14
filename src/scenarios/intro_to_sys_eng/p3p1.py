import json
from src.scenarios.report_answer_scenario import ReportAnswerScenario
from src.latex_utils import get_latex_expr, compare_latex
from src.scenarios.scenario import FailureCode
from src.utils.answer_parsing import coerce_answer_object

PROMPT = """Sparseness of biological networks (directed ER model):

In a directed Erdős–Rényi (ER) network, A arrows are placed at random between N nodes (allowing self-arrows).

a. Give the formula for the number of places to put an arrow, including self-arrows.
b. What is the sparseness p (number of actual arrows divided by number of places) for A = 500 and N = 400?

Use the `report_answer` tool to submit JSON (latex allowed in strings):
{
  "num_places_formula": "latex equation for number of directed edges including self-loops",
  "sparseness_numeric": (float)
}
"""

REFERENCE_NUM_PLACES_FORMULA = r"N^2"
REFERENCE_SPARSENESS_NUMERIC = 0.002


class IntroToSysEng3p1(ReportAnswerScenario):

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
        except Exception as e:
            self.record_failure(FailureCode.BAD_JSON, "Tool payload not valid JSON",
                                payload_preview=str(reported)[:400], error=str(e))
            base.update({"gave_answer": True, "failure_report": self.get_failure_report()})
            return base

        ans_obj, warnings = coerce_answer_object(payload.get("answer"))
        if not isinstance(ans_obj, dict):
            self.record_failure(FailureCode.ANSWER_PARSE_ERROR, "`answer` not parseable into object",
                                payload_preview=str(payload.get("answer"))[:400],
                                parse_warnings=warnings)
            base.update({"gave_answer": True, "failure_report": self.get_failure_report()})
            return base

        try:
            num_places_expr = get_latex_expr(ans_obj.get("num_places_formula", None))
            num_places_ref = get_latex_expr(REFERENCE_NUM_PLACES_FORMULA)
            num_places_ok = compare_latex(num_places_expr, num_places_ref)
        except Exception as e:
            self.record_failure(FailureCode.ANSWER_PARSE_ERROR, "LaTeX parse failed for num_places_formula", error=str(e))
            num_places_ok = False

        try:
            sparseness = float(ans_obj.get("sparseness_numeric"))
            sparseness_ok = abs(sparseness - REFERENCE_SPARSENESS_NUMERIC) <= 1e-2
        except Exception:
            sparseness_ok = False

        ok = num_places_ok and sparseness_ok
        if not ok:
            self.record_failure(FailureCode.WRONG_ANSWER, "ER sparseness answers incorrect",
                                details={"num_places_formula_correct": num_places_ok, "sparseness_close": sparseness_ok})

        base.update({
            "gave_answer": True,
            "correct": ok,
            "num_places_formula_correct": num_places_ok,
            "sparseness_close": sparseness_ok,
            "parse_warnings": warnings,
            "failure_report": self.get_failure_report(),
        })
        return base


if __name__ == "__main__":
    from src.adapters.art_adapter import ArtAdapter
    import asyncio

    scenario = IntroToSysEng3p1(
        scenario_name="IntroToSysEng3p1",
        prompt=PROMPT,
    )
    adapter = ArtAdapter(scenario, step=0)
    asyncio.run(adapter.rollout())
    print(adapter.scenario.get_metrics())
    print("Done")
