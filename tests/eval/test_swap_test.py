"""
Goal: load and save different memories across diff. domains
    - load_domain_pack
    - Schema of the memory may change
    - From domain that is given (finance or education), engine should be able to handle it
"""

from __future__ import annotations

import pytest

from primer_core.eval.swap_test import SwapParityResult, run_swap_parity


@pytest.mark.eval
async def test_identical_engine_module_set_across_domains() -> None:
    """
    BDD Scenario #1
    ---------------
    Scenario: THE HEADLINE — identical engine-module set across domains

    Given run_swap_parity(['education', 'coop-finance']) over deterministic fakes
    When the identical orchestrator flow runs once per DomainPack under the module tracer
    Then each SwapParityResult records a non-empty engine-module set,
        excluding primer_core.eval itself
    And the two sets are identical — everything that differed was the pack
        (manifest + KB wiring + WDF)
    """
    results: list[SwapParityResult] = await run_swap_parity(["education", "coop-finance"])

    assert len(results) > 0 and all(result.passed for result in results)
    # Indicates non-empty engine-module set that excludes primer_core.eval

    assert results[0].engine_modules_touched == results[1].engine_modules_touched
