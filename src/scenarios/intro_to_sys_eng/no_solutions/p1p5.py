import json
from src.scenarios.report_answer_scenario import ReportAnswerScenario


PROMPT = """Fan out: Transcription factor X regulates two genes, Y_1 and Y_2 (fan-out with two targets).
Activation thresholds are K_1 and K_2. The activator X is produced from t = 0 at rate \\beta and removed at
rate \\alpha. The input signal S_x is present throughout.

Task: Provide the times at which the (stable) proteins Y_1 and Y_2 reach halfway to their maximal expression.
State clearly any assumptions. Provide final expressions in latex.

Use the `report_answer` tool to submit JSON in this format:
{
  "t_half_Y1": "...",   # latex expression for the half-max time of Y_1
  "t_half_Y2": "..."    # latex expression for the half-max time of Y_2
}
"""


RUBRIC = None


class IntroToSysEng1p5(ReportAnswerScenario):
    def __init__(self, *args, **kwargs):
        self.reference_answer = None
        super().__init__(*args, **kwargs)

    def _process_prompt(self, prompt: str):
        return PROMPT

    def check_finished(self) -> bool:
        return self._is_answer_reported() or super().check_finished()

    # def get_metrics(self):
    #     reported_answer = self.get_reported_answer_content()
    #     if not reported_answer:
    #         return {"gave_answer": False, **super().get_metrics()}
    #     try:
    #         ans = json.loads(reported_answer)
    #         t_half_Y1 = ans.get("t_half_Y1", None)
    #         t_half_Y2 = ans.get("t_half_Y2", None)
    #         t_half_Y1_expr = parse_latex(t_half_Y1)
    #         t_half_Y2_expr = parse_latex(t_half_Y2)
    #         t_half_Y1_correct = t_half_Y1_expr.equals(REFERENCE_T_HALF_Y1)
    #         t_half_Y2_correct = t_half_Y2_expr.equals(REFERENCE_T_HALF_Y2)
            
            
    #         return {"gave_answer": True, "has_all_fields": has_all, **super().get_metrics()}
    #     except Exception:
    #         return super().get_metrics()


if __name__ == "__main__":
    from src.adapters.art_adapter import ArtAdapter
    import asyncio

    workflow = IntroToSysEng1p5(
        example_name="IntroToSysEng1p5",
        prompt=PROMPT,
        use_reasoning_model=True,
    )
    adapter = ArtAdapter(workflow, step=0)
    asyncio.run(adapter.rollout())
    print(adapter.workflow.get_metrics())
    print("Done")

