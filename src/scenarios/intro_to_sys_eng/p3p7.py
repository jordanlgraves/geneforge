import json
from src.latex_utils import get_latex_expr, compare_latex
from src.scenarios.report_answer_scenario import ReportAnswerScenario


PROMPT = """Coherent type-1 FFL (C1-FFL) with OR logic at Z:

Analyze the Coherent type-1 FFL with OR logic at the Z promoter.

Tasks:
- Provide delay lengths following ON (T_ON) and OFF (T_OFF) steps of Sx.
- Briefly state a biological use-case of this design.

Use the `report_answer` tool to submit JSON:
{
  "T_ON": "...",      # latex expression for T_ON
  "T_OFF": "...",     # expression for T_OFF in terms of Y_{m}^* level and K_YZ
  "use_case": "..."   # short text
}
"""

REF_T_ON = r"0"
REF_T_OFF = r"\frac{1}{\alpha}log(\frac{Y^*_{m}}{K_{YZ}})"


class IntroToSysEng3p7(ReportAnswerScenario):
    def _process_prompt(self, prompt: str):
        return PROMPT

    def check_finished(self) -> bool:
        return self._is_answer_reported() or super().check_finished()

    def get_metrics(self):
        reported = self.get_reported_answer_content()
        if not reported:
            return {"gave_answer": False, **super().get_metrics()}
        try:
            answer_json = json.loads(reported)
            answer = answer_json.get("answer", {})
            answer = json.loads(answer)
            
            t_on = answer.get("T_ON", None)
            t_off = answer.get("T_OFF", None)
            use_case = answer.get("use_case", None)
            
            t_on_expr = get_latex_expr(t_on)
            t_off_expr = get_latex_expr(t_off)
            reference_t_on = get_latex_expr(REF_T_ON)
            reference_t_off = get_latex_expr(REF_T_OFF)
            
            t_on_correct = compare_latex(t_on_expr, reference_t_on)
            t_off_correct = compare_latex(t_off_expr, reference_t_off)
            
            return {
                "gave_answer": True,
                "correct": t_on_correct and t_off_correct,
                "T_ON_correct": t_on_correct,
                "T_OFF_correct": t_off_correct,
                **super().get_metrics(),
            }
            
        except Exception as e:
            print(f'Error parsing answer: {reported}')
            print(e)
            return super().get_metrics()

       


if __name__ == "__main__":
    from src.adapters.art_adapter import ArtAdapter
    import asyncio

    scenario = IntroToSysEng3p7(
        scenario_name="IntroToSysEng3p7",
        prompt=PROMPT,
        use_reasoning_model=True,
    )
    adapter = ArtAdapter(scenario, step=0)
    asyncio.run(adapter.rollout())
    print(adapter.scenario.get_metrics())
    print("Done")

