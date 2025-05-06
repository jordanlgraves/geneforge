import numpy as np
import gymnasium as gym
from gymnasium import spaces
from typing import Tuple, Dict, Any

from src.rl.reward_evaluator import RewardEvaluator
from src.session_state import SessionState
from src.tools.functions import ToolIntegration

# ------------------------------------------------------------
# Helper constants for action ids
# ------------------------------------------------------------
ACT_DESCRIBE_LIBS = 0
ACT_SELECT_LIB  = 1
ACT_GENERATE_VERILOG = 2
ACT_RUN_CELLO   = 3
ACT_STOP        = 4


class GeneCircuitEnv(gym.Env):
    """Gymnasium environment where the agent chooses tool calls step-by-step."""

    metadata = {"render_modes": []}

    def __init__(self, prompt: str,
                 max_steps: int = 10,
                 reward_evaluator: RewardEvaluator | None = None):
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
            verilog = self.session_state.verilog_code
            if verilog:
                self.tool_integration.call_tool_function(
                    "design_with_cello",
                    {
                        "run_name": "rl_run",
                        "verilog_code": verilog,
                    },
                )
            else:
                info["error"] = "No verilog available"

        elif action == ACT_STOP:
            terminated = True
        # --------------------------------------------------

        self.steps_taken += 1
        obs = self._build_obs()

        # Reward evaluation after every step
        reward_dict = self.reward_evaluator.evaluate(self.session_state)
        reward = float(reward_dict["total"] - self.step_penalty)
        info["raw_reward"] = reward_dict

        # Terminate if Cello results obtained or max steps
        if obs[2] == 1.0:
            terminated = True
        if self.steps_taken >= self.max_steps:
            truncated = True

        return obs, reward, terminated, truncated, info

if __name__ == "__main__":
    env = GeneCircuitEnv(
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