import json
from src.latex_utils import get_latex_expr, compare_latex
from src.scenarios.report_answer_scenario import ReportAnswerScenario
from src.scenarios.scenario import FailureCode
from src.utils.answer_parsing import coerce_answer_object

PROMPT = """Speedup for incoherent type-1 FFL (I1-FFL):

Consider an I1-FFL where production of Z is β_{1} if Y^* < K and β_{2} if Y^* ≥ K. 
Compare response time to simple regulation with production β_{2}. Assume equal removal rates.

Use the `report_answer` tool to submit JSON:
{
  "T_simple": "...",   # latex for simple response time (half steady-state)
  "T_I1FFL": "...",    # latex for I1-FFL response time
  "speedup": "..."     # latex for ratio T_simple / T_I1FFL
}
"""

REFERENCE_T_SIMPLE = r"log(2)/\alpha"
REFERENCE_T_I1FFL = r"\frac{\beta_{2}}{2\beta_{1}\alpha}"
REFERENCE_SPEEDUP = r"2log(2) \frac{\beta_{1}}{\beta_{2}}"
RUBRIC = None


class IntroToSysEng3p13(ReportAnswerScenario):
    def _process_prompt(self, prompt: str):
        return PROMPT

    def check_finished(self) -> bool:
        return self._is_answer_reported() or super().check_finished()

    def get_metrics(self):
        base = super().get_metrics()
        reported_answer = self.get_reported_answer_content()
        if not reported_answer:
            self.record_failure(FailureCode.ANSWER_NOT_PROVIDED, "No `report_answer` payload to grade")
            base.update({"gave_answer": False, "failure_report": self.get_failure_report()})
            return base

        # Parse outer tool payload
        try:
            payload = json.loads(reported_answer)
        except Exception as e:
            self.record_failure(FailureCode.BAD_JSON, "Tool payload not valid JSON",
                                payload_preview=str(reported_answer)[:400], error=str(e))
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

        # Compare LaTeX expressions
        def check(key, ref):
            try:
                return compare_latex(get_latex_expr(ans_obj.get(key)), get_latex_expr(ref))
            except Exception as e:
                self.record_failure(FailureCode.ANSWER_PARSE_ERROR,
                                    f"LaTeX parse failed for {key}", error=str(e))
                return False

        t_simple_ok = check("T_simple", REFERENCE_T_SIMPLE)
        t_i1ffl_ok = check("T_I1FFL", REFERENCE_T_I1FFL)
        speedup_ok = check("speedup", REFERENCE_SPEEDUP)

        ok = t_simple_ok and t_i1ffl_ok and speedup_ok
        if not ok:
            self.record_failure(FailureCode.WRONG_ANSWER, "I1-FFL timing/speedup expressions incorrect",
                                details={"T_simple_correct": t_simple_ok,
                                         "T_I1FFL_correct": t_i1ffl_ok,
                                         "speedup_correct": speedup_ok})

        base.update({
            "is_correct": ok,
            "gave_answer": True,
            "T_simple_correct": t_simple_ok,
            "T_I1FFL_correct": t_i1ffl_ok,
            "speedup_correct": speedup_ok,
            "parse_warnings": warnings,
            "failure_report": self.get_failure_report(),
        })
        return base


if __name__ == "__main__":
    from src.adapters.art_adapter import ArtAdapter
    import asyncio

    scenario = IntroToSysEng3p13(
        scenario_name="IntroToSysEng3p13",
        prompt=PROMPT,
    )
    adapter = ArtAdapter(scenario, step=0)
    asyncio.run(adapter.rollout())
    print(adapter.scenario.get_metrics())
    print("Done")
