from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from capillary_actions_sdk.models.student_model import MemoryEntry
from capillary_actions_sdk.ports.memory import MemoryStorePort
from capillary_actions_sdk.reference.in_memory_memory_store import InMemoryMemoryStore

from primer_core.adapters.capillary.file_memory_store import FileMemoryStore


@pytest.fixture(params=["in_memory", "file"])
def store(request, tmp_path: Path) -> MemoryStorePort:
    if request.param == "in_memory":
        return InMemoryMemoryStore()
    return FileMemoryStore(path=tmp_path / "mem.json")


def _match(l1: list[MemoryEntry], l2: list[MemoryEntry]) -> bool:
    return sorted(l1, key=lambda e: e.id) == sorted(l2, key=lambda e: e.id)


async def test_store_get_round_trips_entry_unchanged(store: MemoryStorePort):
    test_subject_id = uuid4()
    test_entry = MemoryEntry(
        id=uuid4(),
        tier="long_term",
        dimension="history",
        content={"courses_completed": ["test-course"]},
    )

    await store.store(subject_id=test_subject_id, entry=test_entry)
    retrieved_entry: MemoryEntry = (await store.get(subject_id=test_subject_id))[0]

    assert test_entry == retrieved_entry


async def test_get_on_unknown_subject_returns_empty_list(store: MemoryStorePort):
    test_subject_id = uuid4()
    test_entry = MemoryEntry(
        id=uuid4(),
        tier="long_term",
        dimension="history",
        content={"courses_completed": ["test-course"]},
    )

    await store.store(subject_id=test_subject_id, entry=test_entry)
    retrieved_entries: list[MemoryEntry] = await store.get(subject_id=uuid4())

    assert retrieved_entries == []


async def test_multiple_entries_for_one_subject_all_come_back(store: MemoryStorePort):
    test_subject_id = uuid4()

    test_entry_1 = MemoryEntry(
        id=uuid4(),
        tier="long_term",
        dimension="history",
        content={"courses_completed": ["test-history-course"]},
    )
    test_entry_2 = MemoryEntry(
        id=uuid4(),
        tier="short_term",
        dimension="affinities",
        content={"courses_enjoyed": ["test-affinity-course"]},
    )

    test_entries: list[MemoryEntry] = [test_entry_1, test_entry_2]
    for test_entry in test_entries:
        await store.store(subject_id=test_subject_id, entry=test_entry)

    retrieved_entries: list[MemoryEntry] = await store.get(subject_id=test_subject_id)

    assert len(retrieved_entries) == 2
    assert _match(test_entries, retrieved_entries)


async def test_dimension_and_tier_filters_on_get_work_and_AND_combined(store: MemoryStorePort):
    test_subject_id = uuid4()

    test_entry_1 = MemoryEntry(
        id=uuid4(),
        tier="long_term",
        dimension="history",
        content={"courses_completed": ["test-history-course"]},
    )
    test_entry_2 = MemoryEntry(
        id=uuid4(),
        tier="short_term",
        dimension="affinities",
        content={"courses_enjoyed": ["test-affinity-course"]},
    )
    test_entry_3 = MemoryEntry(
        id=uuid4(), tier="working", dimension="aspirations", content={"dream_jobs": ["test-job"]}
    )
    test_entry_4 = MemoryEntry(
        id=uuid4(), tier="short_term", dimension="regula", content={"patterns": ["test-pattern"]}
    )

    entries: list[MemoryEntry] = [test_entry_1, test_entry_2, test_entry_3, test_entry_4]
    for test_entry in entries:
        await store.store(subject_id=test_subject_id, entry=test_entry)

    assert (await store.get(subject_id=test_subject_id, dimension="history"))[0] == test_entry_1
    assert (await store.get(subject_id=test_subject_id, tier="working"))[0] == test_entry_3
    assert _match(
        [test_entry_2, test_entry_4], await store.get(subject_id=test_subject_id, tier="short_term")
    )
    assert (await store.get(subject_id=test_subject_id, dimension="regula", tier="short_term")) == [
        test_entry_4
    ]


async def test_entries_from_diff_subjects_do_not_leak(store: MemoryStorePort):
    test_subject_1, test_subject_2 = uuid4(), uuid4()

    test_entry_1 = MemoryEntry(
        id=uuid4(),
        tier="long_term",
        dimension="history",
        content={"courses_completed": ["test-history-course"]},
    )
    test_entry_2 = MemoryEntry(
        id=uuid4(),
        tier="short_term",
        dimension="affinities",
        content={"courses_enjoyed": ["test-affinity-course"]},
    )
    test_entry_3 = MemoryEntry(
        id=uuid4(), tier="working", dimension="aspirations", content={"dream_jobs": ["test-job"]}
    )
    test_entry_4 = MemoryEntry(
        id=uuid4(), tier="short_term", dimension="regula", content={"patterns": ["test-pattern"]}
    )

    await store.store(subject_id=test_subject_1, entry=test_entry_1)
    await store.store(subject_id=test_subject_1, entry=test_entry_3)

    await store.store(subject_id=test_subject_2, entry=test_entry_2)
    await store.store(subject_id=test_subject_2, entry=test_entry_4)

    assert _match(await store.get(subject_id=test_subject_1), [test_entry_1, test_entry_3])
    assert _match(await store.get(subject_id=test_subject_2), [test_entry_2, test_entry_4])
