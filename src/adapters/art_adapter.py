from __future__ import annotations

import art  # type: ignore
from src.scenarios.scenario import Scenario

class ArtAdapter:
    """Bridge between a Scenario and the *art* RL framework.

    This adapter executes a synchronous ``Scenario`` inside a background
    thread so that multiple scenarios can be launched **concurrently** via
    ``asyncio``.  After completion the full chat transcript is returned as an
    :class:`art.Trajectory` while the original ``Scenario`` instance
    remains accessible via :pyattr:`scenario`.
    """
    
    def __init__(
        self,
        scenario: Scenario,
        step: int,
    ) -> None:
        self.scenario = scenario
        self.step = step

    # ------------------------------------------------------------------
    # Rollout helpers
    # ------------------------------------------------------------------

    @art.retry()
    async def rollout(self, **scenario_run_kwargs) -> art.Trajectory:  # type: ignore[name-defined]
        """Execute the underlying scenario asynchronously and capture a trajectory."""
        await self.scenario.run_async(**scenario_run_kwargs)
        return self.trajectory_from_scenario(self.scenario, self.step)

    @staticmethod
    def trajectory_from_scenario(scenario: Scenario, step: int) -> art.Trajectory:
        trajectory = art.Trajectory(
            messages_and_choices=scenario.messages_and_choices,
            metadata=None if step is None else dict(step=step),
            reward=0,  # reward to be set by caller
            metrics=scenario.get_metrics(),
            tools=scenario.tool_integration.tool_functions
        )

        # ------------------------------------------------------------------
        # This first block specifically targets the 'tool_calls'
        # attribute and is less likely to cause unintended side effects.
        # ------------------------------------------------------------------
        for msg in trajectory.messages_and_choices:
            if getattr(msg, 'tool_calls', None) is not None:
                tc = msg.tool_calls
                if not isinstance(tc, list):
                    try:
                        realised = list(tc)
                        setattr(msg, 'tool_calls', realised)
                    except Exception:
                        pass
        
        return trajectory