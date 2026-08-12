from __future__ import annotations

from collections.abc import Callable

import pytest
from capillary_actions_sdk.events import (
    AGUIEvent,
    RunFinishedEvent,
    RunStartedEvent,
)

from tests.eval.cases import (
    EngagementEvalCase,
    build_education_eval_case,
    build_finance_eval_case,
)

CaseBuilder = Callable[[], EngagementEvalCase]

CASE_BUILDERS: tuple[CaseBuilder, ...] = (
    build_education_eval_case,
    build_finance_eval_case,
)


async def _consume_stream(case: EngagementEvalCase) -> list[AGUIEvent]:
    events: list[AGUIEvent] = []

    stream = case.orchestrator.run_engagement_streaming(
        skill_name=case.skill_name,
        subject_id=case.subject_id,
        thread_id=case.thread_id,
        input_data=case.input_data,
    )

    async for event in stream:
        events.append(event)

    return events


@pytest.mark.parametrize("case_builder", CASE_BUILDERS)
async def test_stream_emits_typed_agui_events_in_protocol_order(
    case_builder: CaseBuilder,
) -> None:
    case = case_builder()
    events = await _consume_stream(case)

    assert events
    assert isinstance(events[0], RunStartedEvent)
    assert isinstance(events[-1], RunFinishedEvent)
    assert all(isinstance(event, AGUIEvent) for event in events)
