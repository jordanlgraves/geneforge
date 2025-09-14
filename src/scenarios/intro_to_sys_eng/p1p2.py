import json
from src.latex_utils import compare_latex, get_latex_expr
from src.scenarios.scenario import FailureCode
from src.scenarios.report_answer_scenario import ReportAnswerScenario
from src.utils.answer_parsing import coerce_answer_object

PROMPT = """mRNA dynamics: Consider activation of transcription where protein Y is produced via mRNA.

Let Y_m be the mRNA of gene Y. mRNA is produced at rate \\beta_m and degraded at rate \\alpha_m. Each mRNA produces, on average, p protein molecules per unit time. Protein Y is removed at rate \\alpha.

a. Derive dynamical equations for dY_m/dt and dY/dt.
b. Assuming \\alpha_m \\gg \\alpha (mRNA reaches steady state quickly), express the effective protein production rate \\beta in terms of \\beta_m, \\alpha_m, and p.

Use the `report_answer` tool to submit your answer as a JSON string with this format (latex only, no prose):

{
  "dYm_dt": (string, latex for dY_m/dt),
  "dY_dt": (string, latex for dY/dt),
  "beta_effective": (string, latex for \\beta)
}
"""

REF_dYm_dt = r"\beta_m - \alpha_m Y_m"
REF_dY_dt = r"p Y_m - \alpha Y"
REF_beta = r"\frac{p \beta_m}{\alpha_m}"
RUBRIC = None


class IntroToSysEng1p2(ReportAnswerScenario):
    def __init__(self, *args, **kwargs):
        self.reference_answer = {
            "dYm_dt": REF_dYm_dt,
            "dY_dt": REF_dY_dt,
            "beta_effective": REF_beta,
        }
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
        except Exception as e:
            self.record_failure(FailureCode.BAD_JSON, "Reported payload is not valid JSON",
                                payload_preview=str(reported)[:400], error=str(e))
            base.update({"gave_answer": True, "failure_report": self.get_failure_report()})
            return base

        ans_obj, warnings = coerce_answer_object(payload.get("answer"))
        if not isinstance(ans_obj, dict):
            self.record_failure(FailureCode.ANSWER_PARSE_ERROR, "`answer` must be an object",
                                payload_preview=str(payload.get("answer"))[:400],
                                parse_warnings=warnings)
            base.update({"gave_answer": True, "failure_report": self.get_failure_report()})
            return base

        # latex checks
        def check(key, ref):
            try:
                return compare_latex(get_latex_expr(ans_obj.get(key, "")),
                                     get_latex_expr(ref))
            except Exception as e:
                self.record_failure(FailureCode.ANSWER_PARSE_ERROR, f"LaTeX parse failed for {key}", error=str(e))
                return False

        dYm_ok = check("dYm_dt", REF_dYm_dt)
        dY_ok = check("dY_dt", REF_dY_dt)
        beta_ok = check("beta_effective", REF_beta)

        ok = dYm_ok and dY_ok and beta_ok
        if not ok:
            self.record_failure(FailureCode.WRONG_ANSWER, "One or more equations incorrect",
                                details={"dYm_dt_eq_correct": dYm_ok, "dY_dt_eq_correct": dY_ok, "beta_eff_eq_correct": beta_ok})

        base.update({
            "num_rounds": len(self.messages),
            "dYm_dt_eq_correct": dYm_ok,
            "dY_dt_eq_correct": dY_ok,
            "beta_eff_eq_correct": beta_ok,
            "correct": ok,
            "gave_answer": True,
            "parse_warnings": warnings,
            "failure_report": self.get_failure_report(),
        })
        return base


if __name__ == "__main__":
    from src.adapters.art_adapter import ArtAdapter
    import asyncio

    scenario = IntroToSysEng1p2(
        scenario_name="IntroToSysEng1p2",
        prompt=PROMPT,
    )
    adapter = ArtAdapter(scenario, step=0)
    asyncio.run(adapter.rollout())
    print(adapter.scenario.get_metrics())
    print("Done")
