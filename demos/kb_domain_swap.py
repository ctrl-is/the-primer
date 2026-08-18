"""Offline proof that one retrieval flow serves both DomainPacks."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from capillary_actions_sdk.models.knowledge import RetrievedChunk

from primer_core.domains import load_domain_pack
from primer_core.eval.swap_test import run_swap_parity
from primer_core.testing.fakes import FakeKnowledgeBase


@dataclass(frozen=True)
class DemoCase:
    domain: str
    query: str
    chunk: RetrievedChunk


@dataclass(frozen=True)
class RetrievalSummary:
    domain: str
    kb_names: str
    top_hit: str
    passed: bool


CASES = (
    DemoCase(
        domain="education",
        query="What does a derivative measure?",
        chunk=RetrievedChunk(
            text="A derivative measures the instantaneous rate of change.", score=0.92
        ),
    ),
    DemoCase(
        domain="coop-finance",
        query="What is a share certificate?",
        chunk=RetrievedChunk(
            text="A share certificate locks savings for a fixed term.", score=0.91
        ),
    ),
)


async def run_retrieval(case: DemoCase) -> RetrievalSummary:
    """Run the identical pack-driven retrieval path for any demo case."""
    pack = load_domain_pack(case.domain)
    kb = FakeKnowledgeBase([case.chunk])
    chunks = await kb.retrieve(case.query, pack.kb_names, top_k=1)
    expected_call = (case.query, list(pack.kb_names), 1)
    passed = bool(chunks) and kb.calls == [expected_call]
    return RetrievalSummary(
        domain=case.domain,
        kb_names=", ".join(pack.kb_names),
        top_hit=chunks[0].text if chunks else "<none>",
        passed=passed,
    )


async def run_demo() -> int:
    summaries = [await run_retrieval(case) for case in CASES]
    swap_results = await run_swap_parity([case.domain for case in CASES])
    base_modules = swap_results[0].engine_modules_touched
    module_parity = all(result.passed for result in swap_results) and all(
        result.engine_modules_touched == base_modules for result in swap_results
    )
    retrieval_parity = all(summary.passed for summary in summaries)

    print("Domain swap retrieval (one shared run_retrieval function)")
    print(f"{'domain':<14} | {'manifest KB':<26} | top hit")
    print("-" * 88)
    for summary in summaries:
        print(f"{summary.domain:<14} | {summary.kb_names:<26} | {summary.top_hit}")
    print(f"Retrieval wiring: {'PASS' if retrieval_parity else 'FAIL'}")
    print(f"Engine module parity: {'PASS' if module_parity else 'FAIL'}")
    print(f"Zero engine branching: {'PASS' if retrieval_parity and module_parity else 'FAIL'}")

    return 0 if retrieval_parity and module_parity else 1


def main() -> int:
    return asyncio.run(run_demo())


if __name__ == "__main__":
    raise SystemExit(main())
