import json
from src.latex_utils import get_latex_expr, compare_latex
from src.scenarios.report_answer_scenario import ReportAnswerScenario
from src.scenarios.scenario import FailureCode
from src.utils.answer_parsing import coerce_answer_object

PROMPT = """Autorepression with Hill input function: A repressor X represses its own promoter with Hill
coefficient n.

Dynamics:
  dX/dt = β / (1 + (X/K)^n) − α X.

Tasks:
  - Provide the response time T_{1/2} under strong autorepression. Use the approximation ( (X/K)^n >> 1 ).
  - Provide the ratio of response time for autoregulated circuits to non-autoregulated (simple) circuits for n=1, n=2 and n=3.

Use the `report_answer` tool to submit JSON:
{
  "T_half": string,   # latex
  "ratio_n1": float,
  "ratio_n2": float,
  "ratio_n3": float
}
"""

REFERENCE_T_HALF = r"\frac{1}{(n+1)\,\alpha} \log\left( \frac{2^{n+1}}{2^{n+1}-1} \right)"
REFERENCE_RATIO_N1 = 0.2
REFERENCE_RATIO_N2 = 0.06
REFERENCE_RATIO_N3 = 0.02


class IntroToSysEng2p3(ReportAnswerScenario):
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

        def close(a, b, tol=1e-2):
            try:
                return abs(float(a) - float(b)) <= tol
            except Exception:
                return False

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

        # T_half latex
        try:
            t_half_ok = compare_latex(get_latex_expr(ans_obj.get("T_half", None)),
                                      get_latex_expr(REFERENCE_T_HALF))
        except Exception as e:
            self.record_failure(FailureCode.ANSWER_PARSE_ERROR, "LaTeX parse failed for T_half", error=str(e))
            t_half_ok = False

        n1_ok = close(ans_obj.get("ratio_n1"), REFERENCE_RATIO_N1)
        n2_ok = close(ans_obj.get("ratio_n2"), REFERENCE_RATIO_N2)
        n3_ok = close(ans_obj.get("ratio_n3"), REFERENCE_RATIO_N3)

        ok = t_half_ok and n1_ok and n2_ok and n3_ok
        if not ok:
            self.record_failure(FailureCode.WRONG_ANSWER, "Autorepression metrics incorrect",
                                details={"T_half_correct": t_half_ok,
                                         "provided_n1_ratio": n1_ok,
                                         "provided_n2_ratio": n2_ok,
                                         "provided_n3_ratio": n3_ok})

        base.update({
            "gave_answer": True,
            "T_half_correct": t_half_ok,
            "provided_n1_ratio": n1_ok,
            "provided_n2_ratio": n2_ok,
            "provided_n3_ratio": n3_ok,
            "correct": ok,
            "parse_warnings": warnings,
            "failure_report": self.get_failure_report()
        })
        return base


if __name__ == "__main__":
    from src.adapters.art_adapter import ArtAdapter
    import asyncio

    scenario = IntroToSysEng2p3(
        scenario_name="IntroToSysEng2p3",
        prompt=PROMPT,
    )
    adapter = ArtAdapter(scenario, step=0)
    asyncio.run(adapter.rollout())
    print(adapter.scenario.get_metrics())
    print("Done")
