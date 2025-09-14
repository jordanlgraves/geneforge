from __future__ import annotations
import json, math
from typing import Dict, Any, Optional, List
from src.scenarios.report_answer_scenario import ReportAnswerScenario
import numpy as np

def extract_series(sim_out, species_label, session_state):
    """Return time array and the series for a given species label.
       species_label can be an SBML id (e.g. 'PX') or a pretty name (e.g. 'LacI protein')."""
    cols = sim_out["columns"]
    mat  = np.array(sim_out["result"], dtype=float)
    # Resolve pretty → id if available
    species_map = getattr(session_state, "species_pretty_map", {}) or {}
    rev_map     = {v: k for k, v in species_map.items()}
    wanted_id   = species_label if species_label in cols else rev_map.get(species_label, species_label)
    if wanted_id not in cols:
        raise ValueError(f"Species '{species_label}' not found. Available: {cols[1:]}")
    j = cols.index(wanted_id)
    t = mat[:, 0]
    y = mat[:, j]
    return t, y

PROMPT = """You can use these tools:
- download_biomodel_sbml(model_id)  # new tool (or load file path provided)
- run_kinetic_model_simulation(sbml_path, t0, t1, steps, observe)
- set_parameter_value(section="parameters", key, value)
Goal: Adjust parameters in {model_id} (SBML) so the dominant oscillation period of {species_label}
is {target_period}±{pct}% minutes while amplitude stays within ±{amp_pct}% of baseline.
When satisfied, call report_answer with:
{{
  "changed_parameters": [{{"key": <param_id>, "value": <float>}}, ...]
}}
"""

class SBMLPeriodTargetScenario(ReportAnswerScenario):
    def __init__(self, model_id: str, species_label: str, target_period: float,
                 period_tolerance_pct: float = 10.0, amp_tolerance_pct: float = 15.0, *args, **kwargs):
        self.model_id = model_id
        self.species_label = species_label
        self.target_period = float(target_period)
        self.period_tol = float(period_tolerance_pct)
        self.amp_tol = float(amp_tolerance_pct)
        super().__init__(*args, **kwargs)

    def _process_prompt(self, prompt: Optional[str]):
        return PROMPT.format(
            model_id=self.model_id,
            species_label=self.species_label,
            target_period=self.target_period,
            pct=int(self.period_tol),
            amp_pct=int(self.amp_tol),
        )

    # ---- numeric oracle (simulator-based) ----
    def get_metrics(self) -> Dict[str, Any]:
        base = super().get_metrics()  # keeps num_rounds, tool stats, gave_answer
        reported = self.get_reported_answer_content()  # tool payload JSON
        if not reported:
            return {"reward": -1.0, **base}
        try:
            payload = json.loads(reported.replace("'", '"'))
            changes = payload.get("changed_parameters", [])
        except Exception:
            return {"reward": -1.0, **base}

        # 1) Locate SBML from session (download tool or prior step)
        sbml_path = self.session_state.sbml_file  # set by the download tool
        if not sbml_path:
            return {"reward": -1.0, **base}

        # 2) Run baseline & tuned sims via your kinetic tools
        # Tools already registered in TOOL_REGISTRY
        # - RunKineticModelSimulationTool
        # - SetParameterValueTool
        # (Names match tool_registry.) :contentReference[oaicite:9]{index=9}
        sim_tool = self.tool_integration.tools['run_kinetic_model_simulation']
        set_tool = self.tool_integration.tools['set_parameter_value']

        # Baseline
        baseline = baseline = sim_tool.execute(start=0.0, end=2000.0, steps=2001)
        if baseline.get("error"):
            return {"reward": -1.0, **base}

        # Apply changes
        for c in changes:
            set_tool.execute(section="parameters", key=c["key"], value=float(c["value"]))

        tuned    = sim_tool.execute(start=0.0, end=2000.0, steps=2001)
        
        if tuned.get("error"):
            return {"reward": -1.0, **base}

        # 3) Compute features
        import numpy as np
        def period_fft(t, y):
            y0 = y - y.mean()
            fy = np.abs(np.fft.rfft(y0)); fk = np.fft.rfftfreq(len(y0), d=(t[1]-t[0]))
            pk = np.argmax(fy[1:]) + 1
            return (1.0/fk[pk]) if fk[pk] > 0 else float("nan")

        # baseline arrays
        t0, y0   = extract_series(baseline, self.species_label, self.session_state)
        tb = np.array(t0); yb = np.array(y0)[:,0]
        tt = np.array(tuned["t"]); 
        yt = np.array(tuned["y"])[:,0]
        
        # tuned arrays
        t1, y1   = extract_series(tuned, self.species_label, self.session_state)

        base_amp = float(yb.max() - yb.min())
        amp = float(yt.max() - yt.min())
        per = float(period_fft(tt, yt))
        amp_err = abs(amp - base_amp) / (base_amp + 1e-9)

        # 4) Reward: Gaussian on period error * soft penalty for amplitude drift
        rel = (per - self.target_period) / self.target_period
        r_period = math.exp(- (rel / (self.period_tol/100.0))**2)
        r_amp    = math.exp(- max(0.0, amp_err - self.amp_tol/100.0) / 0.10)
        reward = float(r_period * r_amp)

        return {"reward": reward, "tuned_period": per, "amp_err": amp_err, **base}


if __name__ == "__main__":
    from src.session_state import SessionState
    session_state = SessionState()
    scenario = SBMLPeriodTargetScenario(scenario_name="SBMLPeriodTarget",
                                        model_id="BIOMD0000000012", 
                                        species_label="P", 
                                        target_period=10.0)
    print(scenario._process_prompt(PROMPT))