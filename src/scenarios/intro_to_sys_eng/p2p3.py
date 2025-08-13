import json
from src.scenarios.report_answer_scenario import ReportAnswerScenario
from src.latex_utils import get_latex_expr, compare_latex


PROMPT = """Autorepression with Hill input function: A repressor X represses its own promoter with Hill
coefficient n.

Dynamics:
  dX/dt = β / (1 + (X/K)^n) − α X.

Tasks:
  - Provide the response time T_{1/2} under strong autorepression. Use the approximation (  (X/K)^n >> 1 ).
  - Provide the ratio of response time for autoregulated circuits to non-autoregulated (simple) circuits for n=1, n=2 and n=3.

Use the `report_answer` tool to submit JSON:
{
  "T_half": string,              # latex for T_{1/2} as a function of n and α (alpha)
  "ratio_n1": float,             # ratio of response time for autoregulated to non-autoregulated circuits for n=1
  "ratio_n2": float,             # ratio of response time for autoregulated to non-autoregulated circuits for n=2
  "ratio_n3": float             # ratio of response time for autoregulated to non-autoregulated circuits for n=3
}
"""


# Reference (from solutions text in PDF):
REFERENCE_T_HALF = r"\frac{1}{(n+1)\,\alpha} \log\left( \frac{2^{n+1}}{2^{n+1}-1} \right)"
REFERENCE_RATIO_N1 = 0.2
REFERENCE_RATIO_N2 = 0.06
REFERENCE_RATIO_N3 = 0.02

class IntroToSysEng2p3(ReportAnswerScenario):
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

            try:
                t_half = answer.get("T_half", None)
                t_half_expr = get_latex_expr(t_half)
                t_half_ref_expr = get_latex_expr(REFERENCE_T_HALF)
                t_half_correct = compare_latex(t_half_expr, t_half_ref_expr)
            except Exception as e:
                print(f'Error parsing T_half: {t_half}')
                print(e)
                t_half_correct = False

            try:
                n1_ratio = answer.get("ratio_n1", None)
                n2_ratio = answer.get("ratio_n2", None)
                n3_ratio = answer.get("ratio_n3", None)
                n1_ratio_close = abs(n1_ratio - REFERENCE_RATIO_N1) <= 1e-2
                n2_ratio_close = abs(n2_ratio - REFERENCE_RATIO_N2) <= 1e-2
                n3_ratio_close = abs(n3_ratio - REFERENCE_RATIO_N3) <= 1e-2
            except Exception as e:
                print(f'Error parsing ratios: {answer}')
                print(e)
                n1_ratio_close = False
                n2_ratio_close = False
                n3_ratio_close = False

            is_correct = t_half_correct and n1_ratio_close and n2_ratio_close and n3_ratio_close

            return {
                "gave_answer": True,
                "T_half_correct": t_half_correct,
                "provided_n1_ratio": n1_ratio_close,
                "provided_n2_ratio": n2_ratio_close,
                "provided_n3_ratio": n3_ratio_close,
                "correct": is_correct,
                **super().get_metrics(),
            }
        except Exception as e:
            print(f'Error parsing answer: {reported}')
            print(e)
            return super().get_metrics()


if __name__ == "__main__":
    from src.adapters.art_adapter import ArtAdapter
    import asyncio

    scenario = IntroToSysEng2p3(
        scenario_name="IntroToSysEng2p3",
        prompt=PROMPT,
        use_reasoning_model=True,
    )
    adapter = ArtAdapter(scenario, step=0)
    asyncio.run(adapter.rollout())
    print(adapter.scenario.get_metrics())
    print("Done")

