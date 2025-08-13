import json
from src.scenarios.report_answer_scenario import ReportAnswerScenario


PROMPT = """Subgraphs in random networks (ER):

A subgraph is a pattern of nodes and arrows, found inside a network.

Given a directed ER network of size N and mean connectivity λ = A/N.

a. Compute the expected number of subgraphs G with n nodes and g arrows, ⟨N_G⟩.
b. How many FFLs and three-node feedback loops (FBLs) are there on average?
c. How many fan-in subgraphs (two nodes regulating a third)?
d. How many cliques (fully connected triads)?

Use the `report_answer` tool to submit JSON with formulas (latex allowed):
{
  "general": "⟨N_G⟩ = a^{-1} N^{n-g} λ^g",
  "FFL": "N_FFL = 3 λ^3",
  "FBL": "N_FBL = (1/3) λ^3",
  "fan_in": "N_V = (1/2) N^2 λ^2",
  "clique": "N_clique = (1/6) N λ^6"
}
"""


class IntroToSysEng3p2(ReportAnswerScenario):
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

        required = ["general", "FFL", "FBL", "fan_in", "clique"]
        ok = all(isinstance(ans.get(k, None), str) and len(ans.get(k).strip()) > 0 for k in required)

        return {
            "gave_answer": True,
            "has_all_fields": ok,
            **super().get_metrics(),
        }


if __name__ == "__main__":
    from src.adapters.art_adapter import ArtAdapter
    import asyncio

    workflow = IntroToSysEng3p2(
        example_name="IntroToSysEng3p2",
        prompt=PROMPT,
        use_reasoning_model=True,
    )
    adapter = ArtAdapter(workflow, step=0)
    asyncio.run(adapter.rollout())
    print(adapter.workflow.get_metrics())
    print("Done")

