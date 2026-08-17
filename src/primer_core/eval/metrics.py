from __future__ import annotations

import json
from collections.abc import AsyncIterator
from pathlib import Path
from uuid import uuid4

from capillary_actions_sdk.events import AGUIEvent
from capillary_actions_sdk.models.student_model import MemoryEntry
from capillary_actions_sdk.schema.domain_schema import DomainSchema
from pydantic import BaseModel

from primer_core.adapters.capillary.file_memory_store import FileMemoryStore
from primer_core.domains.domain_pack import load_domain_pack
from primer_core.eval.cases import (
    EngagementEvalCase,
    build_education_eval_case,
    build_finance_eval_case,
)
from primer_core.memory.core import MemoryCore
from primer_core.orchestrator.engagement import EngagementOrchestrator


class MetricResult(BaseModel):
    name: str
    passed: bool
    detail: str | None = None


class TransitionMetricReport(BaseModel):
    metrics: list[MetricResult]
    passed: bool


async def run_transition_metrics(domains: list[str]) -> TransitionMetricReport:
    metric_functions = (
        declarative_orchestration,
        typed_models,
        port_conformance,
        protocol_compliance,
        stateless_agents,
    )
    metrics: list[MetricResult] = [(await func(domains)) for func in metric_functions]

    return TransitionMetricReport(metrics=metrics, passed=all(metric.passed for metric in metrics))


def find_eval_case(domain: str) -> EngagementEvalCase:
    eval_case = {
        "education": build_education_eval_case(),
        "coop-finance": build_finance_eval_case(),
    }
    assert domain in eval_case.keys(), f"Domain {domain} was not found."
    return eval_case.get(domain)


async def declarative_orchestration(domains: list[str]) -> MetricResult:
    bad_engagements: list[tuple[str, str]] = []
    for domain in domains:
        case: EngagementEvalCase = find_eval_case(domain)

        if load_domain_pack(domain).workflow_definition(case.skill_name) is None:
            bad_engagements.append((domain, case.skill_name))

    if bad_engagements:
        detail = ""
        for domain, engagement in bad_engagements:
            detail += f"Domain: {domain}, engagement: {engagement} |"
        return MetricResult(
            name="declarative_orchestration",
            passed=False,
            detail=(f"There were no WDF paths found for the following engagements: {detail}"),
        )
    else:
        return MetricResult(
            name="declarative_orchestration",
            passed=True,
            detail=(
                "Engagements are WDF YAML, not code. "
                f"WDF YAML files were found for all\nenegagements under domains {domains}."
            ),
        )


async def typed_models(domains: list[str]) -> MetricResult:
    declared_dimensions: set[tuple[str, str]] = set()
    undeclared_dimensions: set[tuple[str, str]] = set()
    all_dimensions: set[tuple[str, str]] = set()

    for domain in domains:
        case: EngagementEvalCase = find_eval_case(domain)

        schema: DomainSchema = case.orchestrator.schema
        memory: MemoryCore = case.orchestrator.memory

        for dimension in schema.dimension_names + ["TEST_undeclared_dimension"]:
            entry = MemoryEntry(id=uuid4(), tier="long_term", dimension=dimension, content={})
            try:
                await memory.write(subject_id=uuid4(), entry=entry)
                declared_dimensions.add((domain, dimension))
            except ValueError:
                undeclared_dimensions.add((domain, dimension))
            all_dimensions.add((domain, dimension))

    detail = "The following dimensions were validated against the domain's schema:\n"
    for dom, dimen in declared_dimensions:
        detail += f"\tDomain: '{dom}' | Dimension: '{dimen}'\n"

    detail += "\nThe following dimensions were undeclared and caught by validate_memory_entry:\n"
    for dom, dimen in undeclared_dimensions:
        detail += f"\tDomain: '{dom}' | Dimension: '{dimen}'\n"

    if declared_dimensions | undeclared_dimensions == all_dimensions:
        return MetricResult(name="typed_models", passed=True, detail=detail)
    else:
        detail += "\nThe following dimensions were not properly validated:\n"
        for dom, dimen in declared_dimensions ^ undeclared_dimensions:
            detail += f"\tDomain: '{dom}' | Dimension: '{dimen}'\n"

        return MetricResult(name="typed_models", passed=False, detail=detail)


async def port_conformance(domains: list[str]) -> MetricResult:
    mismatched_memories: list[tuple[str, tuple[list[MemoryEntry], list[MemoryEntry]]]] = []

    for domain in domains:
        case: EngagementEvalCase = find_eval_case(domain)

        FILE_PATH = Path(__file__).parent / "eval_memories" / "port_conformance_memory.json"

        in_memory_memory = case.orchestrator.memory  # InMemoryMemoryStore object by default
        file_memory_memory = MemoryCore(
            schema=case.orchestrator.schema,
            store=FileMemoryStore(path=FILE_PATH),
        )

        for dimension in case.orchestrator.schema.dimension_names:
            entry = MemoryEntry(id=uuid4(), tier="long_term", dimension=dimension, content={})
            await in_memory_memory.write(subject_id=case.subject_id, entry=entry)
            await file_memory_memory.write(subject_id=case.subject_id, entry=entry)

        in_working_memory_entries = (
            await in_memory_memory.assemble_working_memory(subject_id=case.subject_id)
        ).entries
        file_working_memory_entries = (
            await file_memory_memory.assemble_working_memory(subject_id=case.subject_id)
        ).entries

        if in_working_memory_entries != file_working_memory_entries:
            mismatched_memories.append(
                (domain, (in_working_memory_entries, file_working_memory_entries))
            )

    # Clear port_conformance_memory.json for the next run
    with open(FILE_PATH, "w") as temp_file:
        json.dump({}, temp_file)

    if not mismatched_memories:
        return MetricResult(
            name="port_conformance",
            passed=True,
            detail="Swap in-memory <-> file MemoryStore, identical working memory.",
        )
    else:
        detail = (
            "Entries stored in working in-memory do not match "
            "entries stored in working file memory.\n\n"
        )
        for domain, entry_list in mismatched_memories:
            detail += f"""
Domain: {domain}
Working in-memory: {entry_list[0]}
File working memory: {entry_list[1]}

"""
        return MetricResult(name="port_conformance", passed=False, detail=detail)


async def protocol_compliance(domains: list[str]) -> MetricResult:
    agui_events: list[tuple[str, AGUIEvent]] = []
    all_events: list[tuple[str, AGUIEvent]] = []

    for domain in domains:
        case: EngagementEvalCase = find_eval_case(domain)

        iterator: AsyncIterator[AGUIEvent] = case.orchestrator.run_engagement_streaming(
            skill_name=case.skill_name,
            subject_id=case.subject_id,
            thread_id=case.thread_id,
            input_data=case.input_data,
        )
        try:
            events: list[AGUIEvent] = [event async for event in iterator]
        except KeyError as e:
            missing_skill = str(e).split()[-1]
            return MetricResult(
                name="protocol_compliance",
                passed=False,
                detail=(
                    f"[CRITICAL ERROR] The following skill was not registered "
                    f"in the {domain} domain, "
                    f"causing a KeyError: {missing_skill}"
                ),
            )

        for event in events:
            if isinstance(event, AGUIEvent):
                agui_events.append((domain, event))
            all_events.append((domain, event))

    if agui_events == all_events:
        return MetricResult(
            name="protocol_compliance",
            passed=True,
            detail="Streaming surface emits only AG-UI events.",
        )
    else:
        return MetricResult(
            name="protocol_compliance",
            passed=False,
            detail=(
                "The streaming surface emitted the following non-AG-UI events: "
                f"{[event for event in all_events if event not in agui_events]}"
            ),
        )


async def stateless_agents(domains: list[str]) -> MetricResult:
    """
    stateless_agents is attribute-set inspection in eval/ —
    the INDEX explicitly rejected the plan doc's has_in_process_state() engine method.
    Snapshot the orchestrator's (and agent's) attribute sets across fresh constructions/runs;
    the engine stays clean.

    no in-process state; persistence flows only through ports
    """
    failed_orchestrators: list[tuple[str, EngagementOrchestrator]] = []

    for domain in domains:
        case: EngagementEvalCase = find_eval_case(domain)

        await case.orchestrator.run_engagement(
            skill_name=case.skill_name,
            subject_id=case.subject_id,
            thread_id=case.thread_id,
        )

        persistent_entries = await case.orchestrator.memory.store.get(subject_id=case.subject_id)

        for object in vars(case.orchestrator).values():
            try:
                if object == persistent_entries:
                    failed_orchestrators.append((domain, case.orchestrator))
            except TypeError:
                raise AssertionError(f"Orchestrator: {vars(case.orchestrator)}")

    if failed_orchestrators:
        return MetricResult(
            name="stateless_agents",
            passed=False,
            detail=(
                "The following orchestrators were found to contain the persistent entries: "
                f"{failed_orchestrators}"
            ),
        )
    else:
        return MetricResult(
            name="stateless_agents",
            passed=True,
            detail="No in-process state; persistence flows only through ports.",
        )


def precision_at_k(fixture: dict, k_threshold: int) -> MetricResult:
    short_relevant_ids: list[tuple[str, dict]] = []
    misranked_retrieved_ids: list[tuple[str, dict]] = []

    for domain, data in fixture.items():
        for case in data["cases"]:
            if len(case["relevant_ids"]) != k_threshold:
                short_relevant_ids.append((domain, case["query"]))
            elif set(case["retrieved_ids"][:k_threshold]) != set(case["relevant_ids"]):
                misranked_retrieved_ids.append((domain, case["query"]))

    fail_details = ""
    for domain, query in short_relevant_ids:
        fail_details += (
            f"Domain: {domain} | Length of 'relevant_ids' list did not meet "
            f"the proposed k threshold of {k_threshold} under the query '{query}'\n"
        )

    for domain, query in misranked_retrieved_ids:
        fail_details += (
            f"Domain: {domain} | The first K={k_threshold} ids in 'retrieved_ids' did not match"
            f"the ids in 'relevant_ids' under the query '{query}'\n"
        )

    if fail_details:
        return MetricResult(name="precision_at_k", passed=False, detail=fail_details)
    else:
        return MetricResult(
            name="precision_at_k",
            passed=True,
            detail=(
                f"Every case meets agreed k threshold of {k_threshold}; "
                "both domains share one scoring path"
            ),
        )
