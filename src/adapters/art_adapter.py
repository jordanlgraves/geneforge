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
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: self.workflow.run(**workflow_run_kwargs))
        # print(f'Messages: {self.workflow.messages}')
        # filter out values that are not numbers
        # self.metadata = {k: v for k, v in self.metadata.items() if isinstance(v, (int, float))}
        # metadata["step"] = self.step
        # messages_and_choices=[msg.copy() for msg in self.workflow.messages], 
        return self.trajectory_from_workflow(self.workflow, self.step)

    @staticmethod
    def trajectory_from_workflow(workflow=None, step=None):
        trajectory = art.Trajectory(  # type: ignore[attr-defined]
            messages_and_choices=workflow.messages_and_choices,
            metadata=None if step is None else dict(step=step),
            reward=0,  # reward to be set by caller
            metrics=workflow.get_metrics(),
            # tools=tool_functions
            )

        # ------------------------------------------------------------------
        # For some reason ART/Pydantic fuck up this serialization. there is some ValidationIterator that  causes issues downstream.
        # This is the only solution I have found. It is a dumb and annoying problem and someone should fix this.
        
        # Pydantic 2 performs *lazy* validation for list fields.  For the
        # OpenAI chat schema this means the ``tool_calls`` attribute on an
        # assistant message is often a ``ValidatorIterator`` – an internal
        # object that *cannot* be pickled.  Down-stream components such as
        # ``trajectory.model_copy(deep=True)`` therefore raise
        # ``TypeError: cannot pickle 'ValidatorIterator'``.
        #
        # We eagerly materialise any such iterators _once_ here so the
        # trajectory becomes safe to deepcopy or serialise later on.
        # ------------------------------------------------------------------
        for msg in trajectory.messages_and_choices:
            # Only assistant messages *may* include tool calls
            if getattr(msg, 'tool_calls', None) is not None:
                tc = msg.tool_calls  # type: ignore[attr-defined]
                # If ``tool_calls`` is not yet a concrete list, realise it.
                if not isinstance(tc, list):
                    try:
                        realised = list(tc)  # Consume ValidatorIterator
                        # Re-assign so the concrete list is stored.
                        setattr(msg, 'tool_calls', realised)
                    except Exception:
                        # Fallback – even if realisation fails we continue
                        # so that the adapter never breaks rollout.
                        pass

        # ------------------------------------------------------------------
        # Some ValidatorIterator objects may still hide deeper inside the
        # nested message structure (e.g. within each tool-call item).  We
        # recursively traverse the tree and turn *all* such iterators into
        # concrete lists so that ``copy.deepcopy`` (used by
        # ``model_copy(deep=True)``) succeeds.
        # ------------------------------------------------------------------

        from pydantic import BaseModel

        def _is_validator_iterator(obj):
            """Return True when *obj* is the internal Pydantic iterator."""
            return obj.__class__.__name__ == "ValidatorIterator"

        def _resolve_lazy(obj):  # noqa: C901  – complexity ok for utility
            """Recursively convert ValidatorIterator → list & BaseModel → dict."""
            if _is_validator_iterator(obj):
                # Materialise the iterator first, then resolve within.
                obj = list(obj)

            if isinstance(obj, list):
                return [_resolve_lazy(item) for item in obj]

            if isinstance(obj, dict):
                return {k: _resolve_lazy(v) for k, v in obj.items()}

            if isinstance(obj, BaseModel):
                return _resolve_lazy(obj.model_dump(mode="python"))

            # Primitive – nothing to do
            return obj

        cleaned_messages = [_resolve_lazy(msg) for msg in trajectory.messages_and_choices]

        # Replace the original list with the cleaned, picklable version.
        try:
            object.__setattr__(trajectory, "messages_and_choices", cleaned_messages)
        except Exception:
            # In case the attribute is frozen, fall back to private attr name
            try:
                setattr(trajectory, "messages_and_choices", cleaned_messages)  # type: ignore[attr-defined]
            except Exception:
                # Last-ditch – we tried but keep going to avoid breaking rollouts
                pass

        return trajectory