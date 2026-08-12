from __future__ import annotations

import json
from collections.abc import Callable

import pytest
from capillary_actions_sdk.ports.platform import RunWorkflowResponse

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


def _canonicalize_response(response: RunWorkflowResponse) -> str:
    """Return a stable representation of a workflow response."""
    return json.dumps(
        vars(response),
        sort_keys=True,
    )


@pytest.mark.parametrize("case_builder", CASE_BUILDERS)
async def test_same_input_produces_same_route_and_response(
    case_builder: CaseBuilder,
) -> None:
    case = case_builder()

    responses = []

    for _ in range(3):
        response = await case.orchestrator.run_engagement(
            case.skill_name,
            case.subject_id,
            case.thread_id,
            case.input_data,
        )
        responses.append(response)

    assert len(case.runner.requests) == 3

    workflow_ids = {request.workflow_id for request in case.runner.requests}
    assert len(workflow_ids) == 1

    canonical_responses = {_canonicalize_response(response) for response in responses}
    assert len(canonical_responses) == 1

    for request in case.runner.requests:
        assert request.thread_id == case.thread_id
        assert request.input_data == case.input_data
