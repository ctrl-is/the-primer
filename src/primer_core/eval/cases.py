"""Canonical eval-case builders for the primer_core.eval suite.

These builders are consumed at runtime by primer_core.eval itself (metrics.py,
swap_test.py, determinism.py, harness.py) -- including via the primer-eval
console script, which runs outside pytest and has no access to the tests
package. The implementation therefore lives here in the shipped package;
tests/eval/cases.py re-exports these names to keep existing test imports
(`from tests.eval.cases import ...`) working.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import NamedTuple
from uuid import UUID

from capillary_actions_sdk.ports.platform import RunWorkflowResponse
from capillary_actions_sdk.reference.in_memory_memory_store import InMemoryMemoryStore

from primer_core.domains import load_domain_pack
from primer_core.memory.core import MemoryCore
from primer_core.orchestrator import EngagementOrchestrator
from primer_core.testing.fakes import FakeRunWorkflowPort


class EngagementEvalCase(NamedTuple):
    orchestrator: EngagementOrchestrator
    runner: FakeRunWorkflowPort
    skill_name: str
    subject_id: UUID
    thread_id: str
    input_data: dict[str, object]


CaseBuilder = Callable[[], EngagementEvalCase]


EDUCATION_SUBJECT_ID = UUID("11111111-1111-1111-1111-111111111111")
FINANCE_SUBJECT_ID = UUID("22222222-2222-2222-2222-222222222222")

EDUCATION_THREAD_ID = "eval-education-thread"
FINANCE_THREAD_ID = "eval-finance-thread"

EDUCATION_SKILL = "tutor-concept"
FINANCE_SKILL = "suggest-allocation"

EDUCATION_INPUT = {"topic": "demo"}

FINANCE_INPUT = {
    "member_profile": {
        "financial_history": "stable",
        "risk_appetite": "moderate",
        "goals": "long-term savings",
    },
}


def _build_eval_case(
    domain: str,
    skill_name: str,
    subject_id: UUID,
    thread_id: str,
    input_data: dict[str, object],
    response: RunWorkflowResponse,
) -> EngagementEvalCase:
    pack = load_domain_pack(domain)

    # MemoryCore is required by the real orchestrator construction.
    # No hooks are registered: DS-W6 covers routing and protocol surfaces only.
    store = InMemoryMemoryStore()
    memory = MemoryCore(schema=pack.schema, store=store)

    runner = FakeRunWorkflowPort(response)

    orchestrator = EngagementOrchestrator(
        schema=pack.schema,
        runner=runner,
        memory=memory,
        skills=pack.skills,
    )

    return EngagementEvalCase(
        orchestrator=orchestrator,
        runner=runner,
        skill_name=skill_name,
        subject_id=subject_id,
        thread_id=thread_id,
        input_data=input_data,
    )


def build_education_eval_case() -> EngagementEvalCase:
    return _build_eval_case(
        domain="education",
        skill_name=EDUCATION_SKILL,
        subject_id=EDUCATION_SUBJECT_ID,
        thread_id=EDUCATION_THREAD_ID,
        input_data=EDUCATION_INPUT,
        response=RunWorkflowResponse(
            run_id="run-education-eval",
            status="completed",
            output={"answer": "ok"},
        ),
    )


def build_finance_eval_case() -> EngagementEvalCase:
    return _build_eval_case(
        domain="coop-finance",
        skill_name=FINANCE_SKILL,
        subject_id=FINANCE_SUBJECT_ID,
        thread_id=FINANCE_THREAD_ID,
        input_data=FINANCE_INPUT,
        response=RunWorkflowResponse(
            run_id="run-finance-eval",
            status="completed",
            output={
                "suggestion": {
                    "recommendation": (
                        "Maintain sufficient liquidity before increasing long-term allocation."
                    ),
                    "rationale": (
                        "The member has moderate risk tolerance and long-term savings "
                        "goals, so the allocation should preserve near-term liquidity "
                        "while supporting long-term growth."
                    ),
                    "confidence": 0.8,
                },
                "suggestion_sources": [
                    "finance-kb-allocation-001",
                    "finance-kb-allocation-002",
                    "finance-kb-allocation-003",
                    "finance-kb-allocation-004",
                ],
            },
        ),
    )


CASE_BUILDERS: tuple[CaseBuilder, ...] = (
    build_education_eval_case,
    build_finance_eval_case,
)
