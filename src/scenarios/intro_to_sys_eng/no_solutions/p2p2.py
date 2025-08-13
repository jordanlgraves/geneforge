import json
import math
from src.scenarios.report_answer_scenario import ReportAnswerScenario


PROMPT = """Self-arrows in random networks with transcription factors (modified-ER, MER):

Model: N nodes, but only N_1 nodes can send arrows (the TFs). Each arrow selects a source uniformly from these N_1, and a target uniformly from all N nodes (including its source), allowing self-arrows.

a. Write a program to generate MER networks.
b. Generate 100 MER networks with A = 500, N = 400, N_1 = 100. Report the mean and standard deviation of the number of self-arrows.
c. Give a formula for the average number of self-arrows as a function of A, N, N_1. Compare to ER.
d. Are there more there more or less self-arrows than in an ER network? 

Hints: For each arrow, P(self) = 1/N (since target is uniform on N including source). Thus E[self] = A/N, Var[self] = A p (1-p) with p = 1/N, same as ER for self-arrows.

Use the `report_answer` tool to submit JSON:
{
  "mean_formula": "latex string",
  "std_formula": "latex string",
  "mean": (float),
  "std": (float),
  "comparison_to_ER": "more | less | same"
}
"""

class IntroToSysEng2p2(ReportAnswerScenario):
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

        # mean_numeric = float(ans.get("mean_numeric", "nan") or float("nan"))
        # std_numeric = float(ans.get("std_numeric", "nan") or float("nan"))

        # mean_close = abs(mean_numeric - REFERENCE_MEAN_NUMERIC) <= 1e-2
        # std_close = abs(std_numeric - REFERENCE_STD_NUMERIC) <= 5e-2

        # has_cmp = isinstance(ans.get("comparison_to_ER", None), str) and len(ans.get("comparison_to_ER").strip()) > 0

        # return {
        #     "gave_answer": True,
        #     "mean_formula_ok": mean_formula_ok,
        #     "std_formula_ok": std_formula_ok,
        #     "mean_numeric_close": mean_close,
        #     "std_numeric_close": std_close,
        #     "has_comparison": has_cmp,
        #     **super().get_metrics(),
        # }
        return super().get_metrics()


if __name__ == "__main__":
    from src.adapters.art_adapter import ArtAdapter
    import asyncio

    workflow = IntroToSysEng2p2(
        example_name="IntroToSysEng2p2",
        prompt=PROMPT,
        use_reasoning_model=True,
    )
    adapter = ArtAdapter(workflow, step=0)
    asyncio.run(adapter.rollout())
    print(adapter.workflow.get_metrics())
    print("Done")

