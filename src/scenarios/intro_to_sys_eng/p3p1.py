import json
from src.scenarios.report_answer_scenario import ReportAnswerScenario
from src.latex_utils import get_latex_expr, compare_latex

PROMPT = """Sparseness of biological networks (directed ER model):

In a directed Erdős–Rényi (ER) network, A arrows are placed at random between N nodes (allowing self-arrows).

a. Give the formula for the number of places to put an arrow, including self-arrows.
b. What is the sparseness p (number of actual arrows divided by number of places) for A = 500 and N = 400?

Use the `report_answer` tool to submit JSON (latex allowed in strings):
{
  "num_places_formula": "latex equation for number of directed edges including self-loops",
  "sparseness_numeric": (float)
}
"""

REFERENCE_NUM_PLACES_FORMULA = r"N^2"
REFERENCE_SPARSENESS_NUMERIC = 0.002

class IntroToSysEng3p1(ReportAnswerScenario):
    
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
            
            num_places_expr = answer.get("num_places_formula", None)
            num_places_expr = get_latex_expr(num_places_expr)
            num_places_ref_expr = get_latex_expr(REFERENCE_NUM_PLACES_FORMULA)
            num_places_formula_correct = compare_latex(num_places_expr, num_places_ref_expr)
            
            sparseness = float(answer.get("sparseness_numeric", None))
            sparseness_close = abs(sparseness - REFERENCE_SPARSENESS_NUMERIC) <= 1e-2
            
            is_correct = num_places_formula_correct and sparseness_close
            return {
                "gave_answer": True,
                "correct": is_correct,
                "num_places_formula_correct": num_places_formula_correct,
                "sparseness_close": sparseness_close,
                **super().get_metrics(),
            }
        except Exception as e:
            print(f'Error parsing answer: {reported}')
            print(e)
            return super().get_metrics()

        
        


if __name__ == "__main__":
    from src.adapters.art_adapter import ArtAdapter
    import asyncio

    scenario = IntroToSysEng3p1(
        scenario_name="IntroToSysEng3p1",
        prompt=PROMPT,
        use_reasoning_model=True,
    )
    adapter = ArtAdapter(scenario, step=0)
    asyncio.run(adapter.rollout())
    print(adapter.scenario.get_metrics())
    print("Done")

