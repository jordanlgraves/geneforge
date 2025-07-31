from __future__ import annotations

import asyncio
import uuid
from typing import Any, Dict, List, Optional, Sequence

import art  # type: ignore

from src.scenarios.agent.workflows import WorkflowRunner

from src.tool_registry import tool_functions # Need to change this. Makes no sense to do this here. Should get from workflow

class ArtAdapter:
    """Bridge between a WorkflowRunner and the *art* RL framework.

    This adapter executes a synchronous ``WorkflowRunner`` inside a background
    thread so that multiple workflows can be launched **concurrently** via
    ``asyncio``.  After completion the full chat transcript is returned as an
    :class:`art.Trajectory` while the original ``WorkflowRunner`` instance
    remains accessible via :pyattr:`workflow`.
    """

    def __init__(
        self,
        workflow: WorkflowRunner,
        step: int,
    ) -> None:
        self.workflow = workflow
        self.step = step

    # ------------------------------------------------------------------
    # Rollout helpers
    # ------------------------------------------------------------------

    @art.retry()
    async def rollout(self, **workflow_run_kwargs) -> art.Trajectory:  # type: ignore[name-defined]
        """Execute the underlying workflow asynchronously and capture a trajectory."""
        await self.workflow.run_async(**workflow_run_kwargs)
        return self.trajectory_from_workflow(self.workflow, self.step)

    @staticmethod
    def trajectory_from_workflow(workflow=None, step=None):
        trajectory = art.Trajectory(
            messages_and_choices=workflow.messages_and_choices,
            metadata=None if step is None else dict(step=step),
            reward=0,  # reward to be set by caller
            metrics=workflow.get_metrics(),
            tools=workflow.tool_integration.tool_functions
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
        
        return trajectory`