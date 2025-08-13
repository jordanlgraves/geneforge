import json
from src.latex_utils import compare_latex, get_latex_expr
from src.scenarios.report_answer_scenario import ReportAnswerScenario


PROMPT = """mRNA dynamics: Consider activation of transcription where protein Y is produced via mRNA.

Let Y_m be the mRNA of gene Y. mRNA is produced at rate \\beta_m and degraded at rate \\alpha_m. Each mRNA produces, on average, p protein molecules per unit time. Protein Y is removed at rate \\alpha.

a. Derive dynamical equations for dY_m/dt and dY/dt.
b. Assuming \\alpha_m \\gg \\alpha (mRNA reaches steady state quickly), express the effective protein production rate \\beta in terms of \\beta_m, \\alpha_m, and p.

Use the `report_answer` tool to submit your answer as a JSON string with this format (latex only, no prose):

{
"dYm_dt": (string, latex equation for dY_m/dt),
"dY_dt": (string, latex equation for dY/dt),
"beta_effective": (string, latex equation for \\beta)  
}
"""


reference_dYm_dt = r"\beta_m - \alpha_m Y_m"
reference_dY_dt = r"p Y_m - \alpha Y"
reference_beta = r"\frac{p \beta_m}{\alpha_m}"


RUBRIC = None


class IntroToSysEng1p2(ReportAnswerScenario):
    def __init__(self, *args, **kwargs):
        self.reference_answer = {
            "dYm_dt": reference_dYm_dt,
            "dY_dt": reference_dY_dt,
            "beta_effective": reference_beta,
        }
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
            answer_json = json.loads(reported_answer)
            answer = answer_json.get("answer", {})
            answer = json.loads(answer)
            
            dYm_dt_eq = answer.get("dYm_dt", "")
            dY_dt_eq = answer.get("dY_dt", "")
            beta_eff_eq = answer.get("beta_effective", "")

            try:
                dYm_dt_eq = get_latex_expr(dYm_dt_eq)
                reference_dYm_dt_eq = get_latex_expr(reference_dYm_dt)
                dYm_dt_eq_correct = compare_latex(dYm_dt_eq, reference_dYm_dt_eq)
            except Exception as e:
                print(f'Error parsing dYm_dt_eq: {dYm_dt_eq}')
                print(e)
                dYm_dt_eq_correct = False
            
            try:
                dY_dt_eq = get_latex_expr(dY_dt_eq)
                reference_dY_dt_eq = get_latex_expr(reference_dY_dt)
                dY_dt_eq_correct = compare_latex(dY_dt_eq, reference_dY_dt_eq)
            except Exception as e:
                print(f'Error parsing dY_dt_eq: {dY_dt_eq}')
                print(e)
                dY_dt_eq_correct = False
            
            try:
                beta_eff_eq = get_latex_expr(beta_eff_eq)
                reference_beta_eff_eq = get_latex_expr(reference_beta)
                beta_eff_eq_correct = compare_latex(beta_eff_eq, reference_beta_eff_eq)
            except Exception as e:
                print(f'Error parsing beta_eff_eq: {beta_eff_eq}')
                print(e)
                beta_eff_eq_correct = False
                
            is_correct = dYm_dt_eq_correct and dY_dt_eq_correct and beta_eff_eq_correct
            
            return {
               "num_rounds": len(self.messages),
                "dYm_dt_eq_correct": dYm_dt_eq_correct,
                "dY_dt_eq_correct": dY_dt_eq_correct,
                "beta_eff_eq_correct": beta_eff_eq_correct,
                "correct": is_correct,
                "gave_answer": True,
                **super().get_metrics(),
            }
        except Exception as e:
            print(f'Error parsing answer: {reported_answer}')
            print(e)
            return super().get_metrics()

        


if __name__ == "__main__":
    from src.adapters.art_adapter import ArtAdapter
    import asyncio

    scenario = IntroToSysEng1p2(
        scenario_name="IntroToSysEng1p2",
        prompt=PROMPT,
        use_reasoning_model=True,
    )
    adapter = ArtAdapter(scenario, step=0)
    asyncio.run(adapter.rollout())
    print(adapter.scenario.get_metrics())
    print("Done")

