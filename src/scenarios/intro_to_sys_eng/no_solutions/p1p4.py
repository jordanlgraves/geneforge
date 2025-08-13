import json
from src.scenarios.report_answer_scenario import ReportAnswerScenario


PROMPT = """Cascades: Consider a cascade of three activators, X → Y → Z. Protein X is initially present in
the cell in an inactive form. The input signal S_x appears at time t = 0. As a result, X rapidly becomes
active and binds the promoter of gene Y, so that protein Y starts to be produced at rate \\beta. When Y
levels exceed a threshold K_y, gene Z begins to be transcribed. All proteins have the same removal rate \\alpha.

Tasks:
- Provide the concentration Z(t) (latex).
- Provide the response time of Z relative to the addition of S_x (latex or short text).
- Briefly describe how the answers change for a cascade of three repressors.

Use the `report_answer` tool to submit your answer as JSON:
{
  "Z_of_t": "...",              # latex for Z(t)
  "response_time": "...",       # latex or short text
  "repressors_case": "..."      # short text
}
"""


RUBRIC = None


class IntroToSysEng1p4(ReportAnswerScenario):
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
            has_all = all(k in ans for k in ["Z_of_t", "response_time", "repressors_case"])
            return {"gave_answer": True, "has_all_fields": has_all, **super().get_metrics()}
        except Exception:
            return super().get_metrics()


if __name__ == "__main__":
    from src.adapters.art_adapter import ArtAdapter
    import asyncio

    workflow = IntroToSysEng1p4(
        example_name="IntroToSysEng1p4",
        prompt=PROMPT,
        use_reasoning_model=True,
    )
    adapter = ArtAdapter(workflow, step=0)
    asyncio.run(adapter.rollout())
    print(adapter.workflow.get_metrics())
    print("Done")

