import json
from src.scenarios.report_answer_scenario import ReportAnswerScenario


PROMPT = """Pulse of activation: Consider the cascade from Exercise 1.4. The input signal S_x appears at
time t = 0 for a pulse of duration D, and then vanishes.

Tasks:
a. Provide Y(t) (latex).
b. Provide the minimal pulse duration D required for activation of gene Z (use a logic input function if needed).
c. Plot or describe the maximal level of Z as a function of pulse duration D.

Use the `report_answer` tool to submit your answer as JSON:
{
  "Y_of_t": "...",         # latex for Y(t)
  "D_min": "...",          # latex or short text
  "Z_max_of_D": "..."      # latex or short text
}
"""


RUBRIC = None


class IntroToSysEng1p6(ReportAnswerScenario):
    def __init__(self, *args, **kwargs):
        self.reference_answer = None
        super().__init__(*args, **kwargs)

    def _process_prompt(self, prompt: str):
        return PROMPT

    def check_finished(self) -> bool:
        return self._is_answer_reported() or super().check_finished()

    def get_metrics(self):
        reported_answer = self.get_reported_answer_content()
        if not reported_answer:
            return {"gave_answer": False, **super().get_metrics()}
        try:
            ans = json.loads(reported_answer)
            
            return {"gave_answer": True, **super().get_metrics()}
        except Exception:
            return super().get_metrics()


if __name__ == "__main__":
    from src.adapters.art_adapter import ArtAdapter
    import asyncio

    scenario = IntroToSysEng1p6(
        workflow_name="IntroToSysEng1p6",
        prompt=PROMPT,
        use_reasoning_model=True,
    )
    adapter = ArtAdapter(scenario, step=0)
    asyncio.run(adapter.rollout())
    print(adapter.scenario.get_metrics())
    print("Done")

