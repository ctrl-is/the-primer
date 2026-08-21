"""
demos/demo_education.py — the memory path end-to-end: run an education engagement,
write the outcome back through MemoryCore.ingest → FileMemoryStore, start a “second
session” over the same store path, and print that assemble_working_memory surfaces
the first session's outcome (your LD-W4 proof, now as a narrated demo). Follow the
pattern KG-W8 established: repo-root demos/, deterministic fakes only, exit 0 on
success / non-zero on failure, one subprocess pytest with a timeout=.
"""

from __future__ import annotations

import asyncio
import json
from copy import deepcopy
from pathlib import Path

from capillary_actions_sdk.models.student_model import MemoryEntry
from capillary_actions_sdk.schema.domain_schema import DomainSchema

from primer_core.adapters.capillary.file_memory_store import FileMemoryStore
from primer_core.domains import DomainPack, load_domain_pack
from primer_core.eval.cases import EngagementEvalCase
from primer_core.eval.metrics import find_eval_case
from primer_core.memory.core import MemoryCore
from primer_core.orchestrator.engagement import EngagementOrchestrator
from primer_core.orchestrator.hooks import HookEvent, HookRegistry
from primer_core.orchestrator.writeback import write_back_outcome
from primer_core.skills import SkillRegistry
from primer_core.testing.fakes import FakeRunWorkflowPort


async def run_demo() -> int:
    domain = "education"
    FILE_PATH = Path(__file__).parent / "demo_memories" / "demo_memory.json"

    # Session 1
    case: EngagementEvalCase = find_eval_case(domain)

    hooks = HookRegistry()
    hooks.register(event=HookEvent.AFTER_ENGAGEMENT, fn=write_back_outcome)

    case.orchestrator.memory.store = FileMemoryStore(path=FILE_PATH)
    case.orchestrator.hooks = hooks

    case.orchestrator.runner.response.output["writeback"] = {
        "dimension": case.orchestrator.schema.dimension_names[0],
        "content": {"courses": ["demo_course"]},
    }

    await case.orchestrator.run_engagement(
        skill_name=case.skill_name, subject_id=case.subject_id, thread_id=case.thread_id
    )

    # Session 2
    pack: DomainPack = load_domain_pack(domain)
    schema: DomainSchema = pack.schema
    skills: SkillRegistry = pack.skills

    second_response: FakeRunWorkflowPort = deepcopy(case.orchestrator.runner.response)

    second_memory = MemoryCore(schema=schema, store=FileMemoryStore(path=FILE_PATH))
    second_orchestrator = EngagementOrchestrator(
        schema=schema,
        runner=FakeRunWorkflowPort(second_response),
        memory=second_memory,
        skills=skills,
    )

    session_1_outcome_entries: list[MemoryEntry] = await case.orchestrator.memory.store.get(
        subject_id=case.subject_id
    )
    session_2_working_memory_entries: list[MemoryEntry] = (
        await second_orchestrator.memory.assemble_working_memory(subject_id=case.subject_id)
    ).entries

    # Clear demo_memory.json for the next run
    with open(FILE_PATH, "w") as temp_file:
        json.dump({}, temp_file)

    print(f"""
Session 1 outcome (MemoryCore.ingest -> FileMemoryStore(path={FILE_PATH}))
---------------------------------------------------------
{session_1_outcome_entries}

Session 2 working memory (same FileMemoryStore path at {FILE_PATH})
---------------------------------------------------------
{session_2_working_memory_entries}

""")
    if session_1_outcome_entries == session_2_working_memory_entries != []:
        print(
            (
                f"{'=' * 110}\n"
                "Running assemble_working_memory on session 2 precisely "
                "surfaces the first session's outcome. --> DEMO SUCCESS"
                f"\n{'=' * 110}"
            )
        )
        return 0
    elif session_1_outcome_entries == [] or session_2_working_memory_entries == []:
        print(
            (
                f"{'=' * 110}\n"
                "Either session 1's outcome or session 2's working memory is empty. "
                "--> DEMO FAILURE"
                f"\n{'=' * 110}"
            )
        )
        return 1
    elif session_1_outcome_entries != session_2_working_memory_entries:
        print(
            (
                f"{'=' * 110}\n"
                "Running assemble_working_memory on session 2 does not "
                "match the first session's outcome. --> DEMO FAILURE"
                f"\n{'=' * 110}"
            )
        )
        return 1


def main() -> int:
    return asyncio.run(run_demo())


if __name__ == "__main__":
    raise SystemExit(main())
