from __future__ import annotations

import json

import pytest
from capillary_actions_sdk.ports.platform import RunWorkflowResponse

from tests.eval.cases import (
    CASE_BUILDERS,
    CaseBuilder,
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
    responses: list[RunWorkflowResponse] = []
    workflow_ids = []

    for _ in range(3):
        case = case_builder()

        response = await case.orchestrator.run_engagement(
            case.skill_name,
            case.subject_id,
            case.thread_id,
            case.input_data,
        )

        responses.append(response)

        assert len(case.runner.requests) == 1
        request = case.runner.requests[0]

        workflow_ids.append(request.workflow_id)

        assert request.thread_id == case.thread_id
        assert request.input_data == case.input_data

    assert len(set(workflow_ids)) == 1
    assert len({_canonicalize_response(response) for response in responses}) == 1
    assert len({id(response) for response in responses}) == 3
