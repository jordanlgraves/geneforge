import json
import math
from src.latex_utils import get_latex_expr, compare_latex
from src.scenarios.report_answer_scenario import ReportAnswerScenario


PROMPT = """Speedup for incoherent type-1 FFL (I1-FFL):

Consider an I1-FFL where production of Z is β_{1} if Y^* < K and β_{2} if Y^* ≥ K. 
Compare response time to simple regulation with production β_{2}. Assume equal removal rates.

Use the `report_answer` tool to submit JSON:
{
  "T_simple": "...",       # latex for simple response time to reach half steady-state
  "T_I1FFL": "...",       # latex for I1-FFL response time
  "speedup": "..."        # latex for ratio T_simple / T_I1FFL
}
"""
REFERENCE_T_SIMPLE = r"log(2)/\alpha"
REFERENCE_T_I1FFL = r"\frac{\beta_{2}}{2\beta_{1}\alpha}"
REFERENCE_SPEEDUP = r"2log(2) \frac{\beta_{1}}{\beta_{2}}"

class IntroToSysEng3p13(ReportAnswerScenario):
    def _process_prompt(self, prompt: str):
        return PROMPT

    def check_finished(self) -> bool:
        return self._is_answer_reported() or super().check_finished()

    def get_metrics(self):
        reported_answer = self.get_reported_answer_content()
        if not reported_answer:
            return {"gave_answer": False, **super().get_metrics()}
        try:
            answer_json = json.loads(reported_answer)
            answer = answer_json.get("answer", {})
            answer = json.loads(answer)
            
            t_simple = answer.get("T_simple", None)
            t_i1ffl = answer.get("T_I1FFL", None)
            speedup = answer.get("speedup", None)
            t_simple_expr = get_latex_expr(t_simple)
            t_i1ffl_expr = get_latex_expr(t_i1ffl)
            speedup_expr = get_latex_expr(speedup)
            
            reference_t_simple = get_latex_expr(REFERENCE_T_SIMPLE)
            reference_t_i1ffl = get_latex_expr(REFERENCE_T_I1FFL)
            reference_speedup = get_latex_expr(REFERENCE_SPEEDUP)
            
            t_simple_correct = compare_latex(t_simple_expr, reference_t_simple)
            t_i1ffl_correct = compare_latex(t_i1ffl_expr, reference_t_i1ffl)
            speedup_correct = compare_latex(speedup_expr, reference_speedup)
            is_correct = t_simple_correct and t_i1ffl_correct and speedup_correct
            return {
                "is_correct": is_correct,
                "gave_answer": True,
                "T_simple_correct": t_simple_correct,
                "T_I1FFL_correct": t_i1ffl_correct,
                "speedup_correct": speedup_correct,
                **super().get_metrics(),
            }
        except Exception as e:
            print(f'Error parsing answer: {reported_answer}')
            print(e)
            return super().get_metrics()



if __name__ == "__main__":
    from src.adapters.art_adapter import ArtAdapter
    import asyncio

    scenario = IntroToSysEng3p13(
        scenario_name="IntroToSysEng3p13",
        prompt=PROMPT,
        use_reasoning_model=True,
    )
    adapter = ArtAdapter(scenario, step=0)
    asyncio.run(adapter.rollout())
    print(adapter.scenario.get_metrics())
    print("Done")

