import json
from src.scenarios.report_answer_scenario import ReportAnswerScenario


PROMPT = r"""Parameter sensitivity for autorepression steady state:

Given X_st = K [1 + (β/(αK))]^{1/(n+1)}, compute the parameter sensitivity S(X_st, β) = (β/X_st) dX_st/dβ.
Report the expression and describe its trend with Hill coefficient n.

Hint: The parameter sensitivity coefficient of property A with respect to parameter B, denoted S(A, B), 
is defined as the relative change in A for a given small relative change in B, that is, S:

S(A,B)=\frac{\Delta A}{A} / \frac{\Delta B}{B} = \frac{B}{A}\frac{dA}{dB}

Use the `report_answer` tool to submit JSON:
{
  "sensitivity": "...",      # latex equation for S(X_st, β)
  "interpretation": "..."   # short text on robustness vs n
}
"""


REFERENCE_SENSITIVITY = r"\frac{1}{n+1}"


class IntroToSysEng2p4(ReportAnswerScenario):
    def _process_prompt(self, prompt: str):
        return PROMPT

    def check_finished(self) -> bool:
        return self._is_answer_reported() or super().check_finished()

    def get_metrics(self):
        reported = self.get_reported_answer_content()
        if not reported:
            return {"gave_answer": False, **super().get_metrics()}
        try:
            ans = json.loads(reported)
        except Exception:
            return super().get_metrics()

        has_expr = isinstance(ans.get("sensitivity", None), str) and len(ans.get("sensitivity").strip()) > 0
        has_interp = isinstance(ans.get("interpretation", None), str) and len(ans.get("interpretation").strip()) > 0

        return {
            "gave_answer": True,
            "provided_sensitivity": has_expr,
            "provided_interpretation": has_interp,
            **super().get_metrics(),
        }


if __name__ == "__main__":
    from src.adapters.art_adapter import ArtAdapter
    import asyncio

    workflow = IntroToSysEng2p4(
        example_name="IntroToSysEng2p4",
        prompt=PROMPT,
        use_reasoning_model=True,
    )
    adapter = ArtAdapter(workflow, step=0)
    asyncio.run(adapter.rollout())
    print(adapter.workflow.get_metrics())
    print("Done")

