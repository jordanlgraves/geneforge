from typing import Dict, Any, Optional

from src.session_state import SessionState
from src.rl.cello_results_reader import get_circuit_score


class RewardEvaluator:
    """Convert artifacts stored in ``SessionState`` into scalar rewards
    suitable for reinforcement-learning loops.

    The logic is intentionally simple for the first proof-of-concept and can
    be extended later with task-specific checks (custom sensor file exists,
    organism matches, etc.).
    """

    def __init__(self, max_circuit_score: float = 400.0, 
                 success_bonus: float = 1.0,
                 library_bonus: float = 0.0,
                 scenario: str | None = None, 
                 step_penalty: float = 0.0):
        """
        Parameters
        ----------
        max_circuit_score : float, default 500.0
            Value used to normalize the circuit score into the [0,1] range.
            Adjust once we have empirical score distribution.
        success_bonus : float, default 1.0
            Additive bonus if all mandatory success criteria are met.
        library_bonus : float, default 0.0
            Additive bonus if a library is selected.
        scenario : str | None, default None
            Name of the scenario to evaluate the reward for.
        step_penalty : float, default 0.0
            Penalty for each step taken to minimize the number of steps.
        """
        self.max_circuit_score = max_circuit_score
        self.success_bonus = success_bonus
        self.scenario = scenario
        self.step_penalty = step_penalty
        self.library_bonus = library_bonus

    def evaluate(self, session_state: SessionState) -> Dict[str, Any]:
        """Return a dictionary with individual reward components and total.

        Keys
        ----
        success : float
            1.0 if mandatory outputs are present, else 0.0.
        circuit_score_norm : Optional[float]
            Overall circuit score mapped to [0,1] (None if unavailable).
        total : float
            Weighted sum: ``success * success_bonus + circuit_score_norm``.
        details : Dict[str, Any]
            Pass-through of raw values for debugging.
        """
        cello_results = session_state.get_cello_results() or {}
        circuit_score = get_circuit_score(cello_results)

        # Penalize for each step taken to minimize the number of steps
        steps = getattr(session_state, "chat_rounds", 0)
        step_cost = steps * self.step_penalty

        # Normalize circuit score if present
        circuit_score_norm: Optional[float]
        if circuit_score is not None and self.max_circuit_score > 0:
            circuit_score_norm = max(0.0, min(float(circuit_score) / self.max_circuit_score, 1.0))
        else:
            circuit_score_norm = None

        # Basic success criteria: Cello ran and produced a score
        success_flag = 1.0 if circuit_score is not None else 0.0

        has_library = session_state.cello_library.current_library_id is not None

        # Examples of scenario-specific reward calculation
        if self.scenario == "single_sensor":
            # session_state.custom_input_path or session_state.get_cello_results()["key to constraints/input_sensors.json"]
            # count number of sensors in the input sensors file
            # penalize for each extra sensor in the input sensors file
            raise NotImplementedError("Single sensor scenario not implemented")
        elif self.scenario == "optimize_part_count":
            # TODO: Count number of parts in the circuit
            raise NotImplementedError("Optimize part count scenario not implemented")
        elif self.scenario == "specific_sensor":
            # TODO: Check if the circuit uses the specific sensor
            # Need to figure out how to check against the design spec. Maybe an extra 
            # argument to the reward evaluator. Something like 
            # "design_spec": {"specific_sensor": "sensor_name"}
            #  or something.
            raise NotImplementedError("Specific sensor scenario not implemented")
        else:
            total_reward = success_flag * self.success_bonus + (circuit_score_norm or 0.0) - step_cost

        total_reward += has_library * self.library_bonus

        return {
            "success": success_flag,
            "circuit_score_norm": circuit_score_norm,
            "total": total_reward,
            "details": {
                "circuit_score": circuit_score, # effectively a ratio of the transcription in the ON and OFF states for every output of the circuit
                "library": session_state.cello_library.current_library_id,
                "custom_input_path": session_state.cello_library.inputs_path,
                "custom_output_path": session_state.cello_library.outputs_path,
                # TODO: Add design spec, verilog code, etc...probably just save the session state
                # probably just save the Cello results in total
            },
        } 