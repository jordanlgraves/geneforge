from __future__ import annotations

import json
from typing import Any, Dict, Optional

from litellm import acompletion

from src.scenarios.scenario import FailureCode, Scenario
from src.tool_registry import tool_functions


class ReportAnswerScenario(Scenario):
    """
    Scenario variant that ensures a final follow-up prompt is sent when the
    assistant does not call the `report_answer` tool.

    This class keeps the base behaviour intact and adds a minimal post-run
    step: after the normal run completes, if no `report_answer` tool call is
    present in the transcript, it appends a single follow-up message asking the
    model to submit the answer via the tool and processes that one response.

    Intended for benchmarking scenarios where consistent tool usage is required.
    """

    def __init__(
        self,
        *args,
        followup_prompt: Optional[str] = None,
        max_followup_rounds: int = 1,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.followup_prompt: str = (
            followup_prompt or "Please use the `report_answer` tool to submit the answer."
        )
        self.max_followup_rounds: int = max_followup_rounds

    async def run_async(
        self,
        max_rounds: int = 15,
        num_retries: int = 1,
        temperature: float | None = None,
    ) -> Optional[str]:
        final_response = await super().run_async(
            max_rounds=max_rounds, num_retries=num_retries, temperature=temperature
        )

        if not self._is_answer_reported():
            final_response = await self._request_report_answer_followup()
        
        if not self._is_answer_reported():
            self.record_failure(
                FailureCode.NO_REPORT_ANSWER,
                "No `report_answer` call even after follow-up",
                followup_prompt=self.followup_prompt
            )
        
        self._on_finished()
        return final_response

    async def _request_report_answer_followup(self) -> Optional[str]:
        """
        Send a single follow-up asking the assistant to use `report_answer` and
        process at most one assistant turn with any tool calls.
        """
        rounds = 0
        while rounds < self.max_followup_rounds and not self._is_answer_reported():
            self._add_message("user", self.followup_prompt)

            response = await acompletion(
                messages=self.messages,
                tools=tool_functions,
                **self.llm_params,
            )

            assistant_choice = response.choices[0]
            raw_assistant = assistant_choice.message

            assistant_msg, _ = self._build_assistant_message(raw_assistant)

            self._add_message(choice=assistant_choice, **assistant_msg)

            # Execute any tool calls
            self._execute_tool_calls(assistant_msg)

            rounds += 1
        if not self._is_answer_reported():
            self.record_failure(FailureCode.NO_REPORT_ANSWER,
                                "Follow-up completed but no `report_answer` tool call present")
        return self.get_reported_answer_content()


