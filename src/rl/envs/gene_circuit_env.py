import numpy as np
import gymnasium as gym
from gymnasium import spaces
from typing import Tuple, Dict, Any

from src.rl.reward_evaluator import RewardEvaluator
from src.session_state import SessionState
from src.functions import ToolIntegration

# ------------------------------------------------------------
# Helper constants for action ids
# ------------------------------------------------------------
ACT_DESCRIBE_LIBS = 0
ACT_SELECT_LIB  = 1
ACT_GENERATE_VERILOG = 2
ACT_RUN_CELLO   = 3
ACT_STOP        = 4


class GeneCircuitMacroEnv(gym.Env):
    """Gymnasium environment where the agent chooses tool calls step-by-step."""

    metadata = {"render_modes": []}

    def __init__(self, prompt: str,
                 max_steps: int = 10,
                 reward_evaluator: RewardEvaluator | None = None,
                 # Reward-shaping parameters
                 shaping: bool = True,
                 lib_bonus: float = 0.2,
                 verilog_bonus: float = 0.3,
                 cello_bonus: float = 0.7,
                 repeat_penalty: float = 0.0,
                 describe_bonus: float = 0.05):
        super().__init__()
        self.prompt = prompt
        self.max_steps = max_steps
        self.reward_evaluator = reward_evaluator or RewardEvaluator(
            scenario="single_sensor",
            step_penalty=0.05,
            success_bonus=1.0,
        )
        self.step_penalty = 0.05

        # Discrete choice of tool (no args for now)
        self.action_space = spaces.Discrete(5)
        # Observation: [library_selected, has_verilog, has_cello_results]
        self.observation_space = spaces.Box(0.0, 1.0, shape=(3,), dtype=np.float32)

        self.tool_integration: ToolIntegration | None = None
        self.session_state: SessionState | None = None
        self.steps_taken: int = 0
        self._obs = np.zeros((3,), dtype=np.float32)

        # ---------------- Reward shaping config ----------------
        self.shaping_enabled = shaping
        self.lib_bonus = lib_bonus
        self.verilog_bonus = verilog_bonus
        self.cello_bonus = cello_bonus
        self.repeat_penalty = repeat_penalty
        self.describe_bonus = describe_bonus

    def _build_obs(self) -> np.ndarray:
        lib_sel = 1.0 if self.session_state.get_current_library_id() else 0.0
        has_verilog = 1.0 if getattr(self.session_state, "verilog_code", None) else 0.0
        has_results = 1.0 if self.session_state.get_cello_results() else 0.0
        self._obs[:] = (lib_sel, has_verilog, has_results)
        return self._obs.copy()

    def reset(self, *, seed: int | None = None, options=None):  # noqa: D401
        super().reset(seed=seed)
        self.steps_taken = 0
        # fresh session state
        self.session_state = SessionState()
        self.session_state.set_design_spec(self.prompt)
        self.tool_integration = ToolIntegration(self.session_state)
        return self._build_obs(), {}

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:  # noqa: D401
        assert self.session_state is not None and self.tool_integration is not None, "env.reset() must be called first"
        terminated = False
        truncated = False
        info: Dict[str, Any] = {}

        # Store previous observation for shaping
        prev_obs = self._obs.copy()
        prev_session_state = self.session_state.to_dict()

        # ---------------- Dispatch tool -------------------
        if action == ACT_DESCRIBE_LIBS:
            self.tool_integration.call_tool_function("describe_available_libraries", {})

        elif action == ACT_SELECT_LIB:
            libs = self.session_state.get_library_manager().get_available_libraries()
            if libs:
                # select first library that starts with "Eco"
                first_lib_id = next((lib_id for lib_id in libs if lib_id.startswith("Eco")), list(libs.keys())[0])
                self.tool_integration.call_tool_function("select_library", {"library_id": first_lib_id})
            else:
                info["error"] = "No libraries available"

        elif action == ACT_GENERATE_VERILOG:
            self.tool_integration.call_tool_function("generate_verilog", {"spec": self.prompt})

        elif action == ACT_RUN_CELLO:
            verilog = self.session_state.get_verilog_code()
            if verilog:
                try:
                    cello_results = self.tool_integration.call_tool_function(
                        "design_with_cello",
                        {
                        "run_name": "rl_run",
                        "verilog_code": verilog,
                    },
                    )
                    print(f"Cello run results: {cello_results}")
                except Exception as e:
                    info["error"] = f"Cello run failed: {str(e)}"
            else:
                info["error"] = "No verilog available"

        elif action == ACT_STOP:
            terminated = True
        # --------------------------------------------------

        self.steps_taken += 1
        obs = self._build_obs()

        # Reward evaluation after every step
        reward_dict = self.reward_evaluator.evaluate(self.session_state)

        # Base reward (end-state + step penalty)
        reward = float(reward_dict["total"] - self.step_penalty)

        # --------------------------------------------------
        # Reward shaping – milestone bonuses
        # --------------------------------------------------
        shaping_bonus = 0.0
        if self.shaping_enabled:
            # Small bonus for describing libraries
            if action == ACT_DESCRIBE_LIBS and prev_session_state.get('library_manager', dict()).get('current_library_id') is None:
                shaping_bonus += self.describe_bonus
            
            # Library selected first time
            if action == ACT_SELECT_LIB and prev_obs[0] == 0 and obs[0] == 1:
                shaping_bonus += self.lib_bonus
            elif self.repeat_penalty > 0 and action == ACT_SELECT_LIB and prev_obs[0] == 1 and obs[0] == 1:
                shaping_bonus -= self.repeat_penalty

            # Verilog generated first time
            if action == ACT_GENERATE_VERILOG and prev_obs[1] == 0 and obs[1] == 1:
                shaping_bonus += self.verilog_bonus
            elif self.repeat_penalty > 0 and action == ACT_GENERATE_VERILOG and prev_obs[1] == 1 and obs[1] == 1:
                shaping_bonus -= self.repeat_penalty

            # Cello results obtained first time
            if action == ACT_RUN_CELLO and prev_obs[2] == 0 and obs[2] == 1:
                shaping_bonus += self.cello_bonus
            elif self.repeat_penalty > 0 and action == ACT_RUN_CELLO and prev_obs[2] == 1 and obs[2] == 1:
                shaping_bonus -= self.repeat_penalty

        reward += shaping_bonus

        # Expose details for debugging/tracking
        info["raw_reward"] = reward_dict
        if self.shaping_enabled:
            info["shaping_bonus"] = shaping_bonus

        # Terminate if max steps reached
        if self.steps_taken >= self.max_steps:
            truncated = True

        return obs, reward, terminated, truncated, info

if __name__ == "__main__":
    env = GeneCircuitMacroEnv(
        prompt="""Design and simulate in Cello a NOT gate circuit for E. coli that uses only a single input sensor.
Start by selecting a library. List the available input sensors in the library's default input sensors file.
Choose one input sensor (like the arabinose sensor) and create a custom minimal input sensors file containing just that sensor.
Use Cello to design the circuit with your custom input sensor file.
After the simulation is complete, read the circuit score from the output file and return it as a JSON object with the key 'circuit_score'.""",
        reward_evaluator=RewardEvaluator(
            step_penalty=0.05,
            success_bonus=1.0)
    )
    env.reset()
    env.step(0)
    print(env.observation_space)
    print(env.action_space)
    print(env.reward_evaluator)