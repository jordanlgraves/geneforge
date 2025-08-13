import json
import math
from src.scenarios.report_answer_scenario import ReportAnswerScenario


PROMPT = """Random networks (Erdős–Rényi, directed):

a. Write a program that produces a random ER network with N nodes and A arrows (directed edges), where each arrow chooses a random source node (uniform in {1..N}) and a random target node (uniform in {1..N}, allowing self-arrows).

b. Generate 100 ER networks with A = 500 and N = 400. Report the mean and standard deviation of the number of self-arrows (arrows whose source equals their target).

Hints: In the directed ER model described, the number of self-arrows is Binomial(A, p) with p = 1/N.

Use the `report_answer` tool to submit JSON with the mean and standard deviation of the number of self-arrows:
{
  "mean": (float),
  "std": (float),
}
"""


class IntroToSysEng2p1(ReportAnswerScenario):
    def _process_prompt(self, prompt: str):
        return PROMPT

    def check_finished(self) -> bool:
        return self._is_answer_reported() or super().check_finished()

    def get_metrics(self):
        # reported = self.get_reported_answer_content()
        # if not reported:
        #     return {"gave_answer": False, **super().get_metrics()}
        # try:
        #     ans = json.loads(reported)
        # except Exception:
        #     return super().get_metrics()

        # mean_numeric = float(ans.get("mean", "nan") or float("nan"))
        # std_numeric = float(ans.get("std", "nan") or float("nan"))

        # mean_close = abs(mean_numeric - REFERENCE_MEAN_NUMERIC) <= 1e-2
        # std_close = abs(std_numeric - REFERENCE_STD_NUMERIC) <= 5e-2

        # return {
        #     "gave_answer": True,
        #     "mean_numeric_close": mean_close,
        #     "std_numeric_close": std_close,
        #     **super().get_metrics(),
        # }
        return super().get_metrics()


if __name__ == "__main__":
    from src.adapters.art_adapter import ArtAdapter
    import asyncio

    workflow = IntroToSysEng2p1(
        example_name="IntroToSysEng2p1",
        prompt=PROMPT,
        use_reasoning_model=True,
    )
    adapter = ArtAdapter(workflow, step=0)
    asyncio.run(adapter.rollout())
    print(adapter.workflow.get_metrics())
    print("Done")

