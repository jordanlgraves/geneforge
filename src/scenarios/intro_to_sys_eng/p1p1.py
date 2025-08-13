

import json
import random
from src.scenarios.report_answer_scenario import ReportAnswerScenario
from sympy import simplify
from src.latex_utils import compare_latex, get_latex_expr

PROMPT = """A change in production rate: A gene Y with simple regulation is produced at a constant
rate β1. The production rate suddenly shifts to a different rate β2.
a. Calculate and plot the gene product concentration Y(t).

Use the `report_answer` tool to submit your answer as a string in the following format:

{
    "answer": (string), # the equation for Y(t) as latex with no preamble, explanation, or other text
}
"""

# Y(t) = β2/α + (β1/α − β2/α)e−αt
reference_answer = r"\frac{\beta_2}{\alpha} + \left(\frac{\beta_1}{\alpha} - \frac{\beta_2}{\alpha}\right)e^{-\alpha t}"

RUBRIC = None

class IntroToSysEng1p1(ReportAnswerScenario):
    def __init__(self, *args, **kwargs):
        self.reference_answer = reference_answer
        super().__init__(*args, **kwargs)
    
    def _process_prompt(self, prompt: str):
        return PROMPT
    
    def check_finished(self) -> bool:
        """
        Returns:
            True if the example is finished, False otherwise. Useful for stopping the workflow when a condition is met.
        """
        return self._is_answer_reported() or super().check_finished()
    
    def get_metrics(self):
        reported_answer = self.get_reported_answer_content()
        if not reported_answer:
            return {"gave_answer": False, **super().get_metrics()}

        is_correct = False
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
    
    scenario = IntroToSysEng1p1(
        scenario_name="IntroToSysEng1p1",
        model_name="gemini/gemini-2.5-pro",
        prompt=PROMPT
    )
    adapter = ArtAdapter(scenario, step=0)
    asyncio.run(adapter.rollout(temperature=1.0))
    
    print(adapter.scenario.get_metrics())
    print('Done')  