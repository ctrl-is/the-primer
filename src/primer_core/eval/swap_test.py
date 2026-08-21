from __future__ import annotations

import json
from pathlib import Path
from sys import settrace
from types import FrameType
from typing import Any

from pydantic import BaseModel

from primer_core.eval.cases import EngagementEvalCase
from primer_core.eval.metrics import find_eval_case


class SwapParityResult(BaseModel):
    domain: str
    passed: bool  # per-domain sanity: >= 1 engine module ran & eval layer excluded
    engine_modules_touched: list[str]  # sorted primer_core.* modules


async def run_swap_parity(domains: list[str]) -> list[SwapParityResult]:
    """
    run_swap_parity is the "swap test" the executable proof
    that the engine is domain-agnostic. For each domain it loads
    the DomainPack and runs the identical orchestrator flow under
    a sys.settrace tracer that records which primer_core.* modules
    actually execute (excluding primer_core.eval.*). One SwapParityResult
    per domain, in input order.

    The payoff: if the module set is identical for education vs coop-finance,
    then all domain differences lived in the DomainPack (manifest + KB wiring + WDF),
    zero engine lines. That cross-domain set == set assertion is done by the caller/headline
    test, not inside the function.
    """
    FILE_PATH = Path(__file__).parent / "eval_memories" / "port_conformance_memory.json"

    results: list[SwapParityResult] = []

    for domain in domains:
        engine_modules_touched: set[str] = set()

        def tracer(frame: FrameType, event: str, arg: Any = None):
            if event != "call":
                return tracer
            file_name = frame.f_code.co_filename
            if "primer_core/eval" not in file_name and "primer_core" in file_name:
                folder_list = file_name.split("/")
                primer_core_index = folder_list.index("primer_core")
                shortened = "/".join(folder_list[primer_core_index:])
                engine_modules_touched.add(shortened)
            return tracer

        case: EngagementEvalCase = find_eval_case(domain)

        settrace(tracer)

        await case.orchestrator.run_engagement(
            skill_name=case.skill_name,
            subject_id=case.subject_id,
            thread_id=case.thread_id,
        )

        settrace(None)
        with open(FILE_PATH, "w") as temp_file:
            json.dump({}, temp_file)

        result = SwapParityResult(
            domain=domain, passed=False, engine_modules_touched=sorted(engine_modules_touched)
        )

        if engine_modules_touched and all(
            "primer_core/eval" not in module for module in engine_modules_touched
        ):
            result.passed = True

        results.append(result)

    return results
