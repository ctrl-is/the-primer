"""
Every input the harness needs is available — both packs
(`load_domain_pack('education'|'coop-finance')`, `a0d2c0e`), memory proven domain-agnostic
through your own `tests/memory/test_finance_dimensions.py` (`98a84d9`), corrective
retrieval covered (`cdd3e63`), hooks/write-back on `main` since `b01cc41`, real finance
engagements + `AllocationSuggestion` from DS-W5
"""

from __future__ import annotations

import asyncio
import sys
from typing import Any

from pydantic import BaseModel

from primer_core.eval.determinism import assert_orchestrator_deterministic
from primer_core.eval.metrics import TransitionMetricReport, run_transition_metrics
from primer_core.eval.swap_test import SwapParityResult, run_swap_parity


class EvalReport(BaseModel):
    results: dict[str, Any]
    passed: bool


async def run_eval_suite(domains: list[str]) -> EvalReport:
    assert_orchestrator_deterministic(domains)

    swap_results: list[SwapParityResult] = await run_swap_parity(domains)
    metrics_report: TransitionMetricReport = await run_transition_metrics(domains)

    if metrics_report.passed and all(result.passed for result in swap_results):
        passed = True
    else:
        passed = False

    return EvalReport(
        results={"swap_test": swap_results, "transition_metrics": metrics_report}, passed=passed
    )


def format_report(report: EvalReport) -> str:
    passed_cases, total_cases = 0, 0
    for result in report.results["swap_test"]:
        if result.passed:
            passed_cases += 1
        total_cases += 1
    for result in report.results["transition_metrics"].metrics:
        if result.passed:
            passed_cases += 1
        total_cases += 1

    formatted = f"""
=====================================================================
The primer_core.eval suite passed {passed_cases}/{total_cases} cases.
=====================================================================

Details:

"""

    for result in report.results["transition_metrics"].metrics:
        formatted += f"""
--------------
Test: {result.name}
--------------
{result.detail}

"""

        # f"\n{result.detail}\n"

    formatted += "\n\n"

    for result in report.results["swap_test"]:
        formatted += f"""
Domain '{result.domain}' yielded the following module set:
\t{"\n\t".join(result.engine_modules_touched)}

"""

    base_modules: list[str] = report.results["swap_test"][0].engine_modules_touched

    if not all(
        result.engine_modules_touched == base_modules for result in report.results["swap_test"]
    ):
        formatted += "These module sets are not identical."
    else:
        formatted += "These module sets are identical."

    return formatted


def main() -> None:
    """
    Console-script entrypoint for `primer-eval` (see [project.scripts]).
    """
    report = asyncio.run(run_eval_suite(["education", "coop-finance"]))
    print(format_report(report))
    sys.exit(0 if report.passed else 1)
