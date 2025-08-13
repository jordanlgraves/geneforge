import json
from src.scenarios.report_answer_scenario import ReportAnswerScenario


PROMPT = """Autoregulated cascade: Gene X represses Y; both X and Y repress their own promoters (negative
autoregulation). Assume logic input functions with thresholds K_XX (X on itself), K_XY (X on Y), K_YY (Y on
itself). Consider two cases:

a. At t = 0, X begins to be produced at rate β from X=0. Provide the dynamics and response times for X and Y.
b. At t = 0, production of X stops after a long period of production; X decays from steady state. Provide dynamics and response times for X and Y.

Provide concise expressions or piecewise definitions using logic input functions, and the key response times in terms of α and thresholds.

Use the `report_answer` tool to submit JSON:
{
  "part_a": {
    "X_of_t": "...", 
    "Y_of_t": "...", 
    "T_half_X": "...", 
    "T_half_Y": "..."
  },
  "part_b": {
    "X_of_t": "...", 
    "Y_of_t": "...", 
    "T_half_X": "...", 
    "T_half_Y": "..."
  }
}
"""


class IntroToSysEng2p5(ReportAnswerScenario):
    def _process_prompt(self, prompt: str):
        return PROMPT

    def check_finished(self) -> bool:
        return self._is_answer_reported() or super().check_finished()

    # def get_metrics(self):
    #     reported = self.get_reported_answer_content()
    #     if not reported:
    #         return {"gave_answer": False, **super().get_metrics()}
    #     try:
    #         ans = json.loads(reported)
    #     except Exception:
    #         return super().get_metrics()

    #     part_a = ans.get("part_a", None)
    #     part_b = ans.get("part_b", None)
        
        


if __name__ == "__main__":
    from src.adapters.art_adapter import ArtAdapter
    import asyncio

    workflow = IntroToSysEng2p5(
        example_name="IntroToSysEng2p5",
        prompt=PROMPT,
        use_reasoning_model=True,
    )
    adapter = ArtAdapter(workflow, step=0)
    asyncio.run(adapter.rollout())
    print(adapter.workflow.get_metrics())
    print("Done")

