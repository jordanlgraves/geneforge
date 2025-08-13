import json
from src.scenarios.report_answer_scenario import ReportAnswerScenario
from sympy.parsing.latex import parse_latex
from src.latex_utils import get_latex_expr, compare_latex

PROMPT = """Time-dependent production and decay: A gene Y with simple regulation has a time-dependent
production rate \\beta(t) and a time-dependent degradation/dilution rate \\alpha(t). Solve for its
concentration Y(t) as a function of time.

Use the `report_answer` tool to submit your answer in this JSON format, with a single latex expression for Y(t):

{
  "answer": latex expression for Y(t)   
}
"""


reference_answer = r"e^{-\int_0^t \alpha(t')\,dt'}\,\left( Y(0) + \int_0^t \beta(t')\,e^{\int_{0}^{t} \alpha(t'')\,dt''}\,dt' \right)"


RUBRIC = None


class IntroToSysEng1p3(ReportAnswerScenario):
    def __init__(self, *args, **kwargs):
        self.reference_answer = reference_answer
        super().__init__(*args, **kwargs)

    def _process_prompt(self, prompt: str):
        return PROMPT

    def check_finished(self) -> bool:
        return self._is_answer_reported() or super().check_finished()

    def get_metrics(self):
        # Keep simple: only check that an answer was reported
        reported_answer = self.get_reported_answer_content()
        if not reported_answer:
            return {"gave_answer": False, **super().get_metrics()}
        try:
            answer_json = json.loads(reported_answer)
            answer = answer_json.get("answer")
            expr1 = get_latex_expr(answer)
            expr2 = get_latex_expr(self.reference_answer)
            is_correct = compare_latex(expr1, expr2)
            
            return {
                "num_rounds": len(self.messages),
                "correct": is_correct,
                "gave_answer": True,
                **super().get_metrics()
            }
        except Exception as e:
            print(f'Error parsing answer: {reported_answer}')
            print(e)
            return super().get_metrics()


if __name__ == "__main__":
    from src.adapters.art_adapter import ArtAdapter
    import asyncio

    scenario = IntroToSysEng1p3(
        scenario_name="IntroToSysEng1p3",
        prompt=PROMPT,
        use_reasoning_model=True,
    )
    adapter = ArtAdapter(scenario, step=0)
    asyncio.run(adapter.rollout())
    print(adapter.scenario.get_metrics())
    print("Done")

