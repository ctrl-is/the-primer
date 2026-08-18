from __future__ import annotations

import pytest
from capillary_actions_sdk.ports.knowledge import KnowledgeBasePort

from primer_core.adapters.capillary import KnowledgeBaseUnavailable, PgVectorKnowledgeBase


class FakeSearchClient:
    """Records calls and returns a canned response, standing in for the real pgvector client."""

    def __init__(self, rows: list[dict]) -> None:
        self._rows = rows
        self.calls: list[tuple[str, list[str], int]] = []

    async def search(self, query: str, kb_names: list[str], top_k: int) -> list[dict]:
        self.calls.append((query, list(kb_names), top_k))
        return self._rows


class TimeoutSearchClient:
    async def search(self, query: str, kb_names: list[str], top_k: int) -> list[dict]:
        raise TimeoutError


async def test_is_a_real_knowledge_base_port():
    kb = PgVectorKnowledgeBase(FakeSearchClient([]))
    assert isinstance(kb, KnowledgeBasePort)


async def test_retrieve_maps_chunk_and_distance_to_text_and_score():
    client = FakeSearchClient(
        [{"chunk": "A derivative measures rate of change.", "distance": 0.12}]
    )
    kb = PgVectorKnowledgeBase(client)

    chunks = await kb.retrieve("what is a derivative?", ["primer-education-kb"], top_k=2)

    assert len(chunks) == 1
    assert chunks[0].text == "A derivative measures rate of change."
    assert chunks[0].score == pytest.approx(0.88)


async def test_retrieve_passes_pre_scored_row_through_unchanged():
    client = FakeSearchClient([{"text": "pre-scored", "score": 0.9}])
    kb = PgVectorKnowledgeBase(client)

    chunks = await kb.retrieve("q", ["primer-education-kb"])

    assert chunks[0].text == "pre-scored"
    assert chunks[0].score == pytest.approx(0.9)


async def test_score_is_clamped_into_unit_interval():
    client = FakeSearchClient([{"chunk": "far", "distance": 1.7}])
    kb = PgVectorKnowledgeBase(client)

    chunks = await kb.retrieve("q", ["primer-education-kb"])

    assert chunks[0].score == 0.0


async def test_retrieve_forwards_query_kb_names_and_top_k():
    client = FakeSearchClient([])
    kb = PgVectorKnowledgeBase(client)

    await kb.retrieve("q", ["primer-education-kb", "extra-kb"], top_k=7)

    assert client.calls == [("q", ["primer-education-kb", "extra-kb"], 7)]


async def test_top_k_defaults_to_five():
    client = FakeSearchClient([])
    kb = PgVectorKnowledgeBase(client)

    await kb.retrieve("q", ["primer-education-kb"])

    assert client.calls[0][2] == 5


async def test_empty_client_response_returns_empty_list():
    client = FakeSearchClient([])
    kb = PgVectorKnowledgeBase(client)

    chunks = await kb.retrieve("q", ["primer-education-kb"])

    assert chunks == []


async def test_timeout_is_translated_to_typed_domain_error():
    kb = PgVectorKnowledgeBase(TimeoutSearchClient())

    with pytest.raises(KnowledgeBaseUnavailable, match="retrieval timed out"):
        await kb.retrieve("q", ["primer-education-kb"])


async def test_malformed_rows_are_logged_and_skipped(caplog: pytest.LogCaptureFixture):
    rows = [
        None,
        {"score": 0.8},
        {"text": 42, "score": 0.8},
        {"text": "bad score", "score": "high"},
        {"text": "valid", "score": 0.7},
    ]
    kb = PgVectorKnowledgeBase(FakeSearchClient(rows))  # type: ignore[arg-type]

    chunks = await kb.retrieve("q", ["primer-education-kb"])

    assert [(chunk.text, chunk.score) for chunk in chunks] == [("valid", 0.7)]
    assert "Skipping malformed knowledge-base row" in caplog.text


async def test_all_malformed_rows_raise_typed_domain_error():
    kb = PgVectorKnowledgeBase(FakeSearchClient([{"text": "missing score"}, {"score": 0.8}]))

    with pytest.raises(KnowledgeBaseUnavailable, match=r"no usable rows \(2 malformed\)"):
        await kb.retrieve("q", ["primer-education-kb"])


async def test_non_finite_distance_rows_are_skipped_as_malformed(caplog: pytest.LogCaptureFixture):
    rows = [
        {"chunk": "nan distance", "distance": float("nan")},
        {"chunk": "inf distance", "distance": float("inf")},
        {"chunk": "valid", "distance": 0.3},
    ]
    kb = PgVectorKnowledgeBase(FakeSearchClient(rows))

    chunks = await kb.retrieve("q", ["primer-education-kb"])

    assert [(chunk.text, chunk.score) for chunk in chunks] == [("valid", pytest.approx(0.7))]
    assert "Skipping malformed knowledge-base row" in caplog.text


async def test_non_list_response_raises_typed_domain_error():
    for bad_response in ({"rows": []}, "not a list", ""):
        kb = PgVectorKnowledgeBase(FakeSearchClient(bad_response))  # type: ignore[arg-type]

        with pytest.raises(KnowledgeBaseUnavailable, match="malformed response"):
            await kb.retrieve("q", ["primer-education-kb"])


async def test_empty_query_returns_empty_list_without_searching():
    client = FakeSearchClient([{"text": "unused", "score": 0.9}])
    kb = PgVectorKnowledgeBase(client)

    assert await kb.retrieve("", ["primer-education-kb"]) == []
    assert client.calls == []


async def test_top_k_zero_returns_empty_list_without_searching():
    client = FakeSearchClient([{"text": "unused", "score": 0.9}])
    kb = PgVectorKnowledgeBase(client)

    assert await kb.retrieve("q", ["primer-education-kb"], top_k=0) == []
    assert client.calls == []


async def test_negative_top_k_returns_empty_list_without_searching():
    client = FakeSearchClient([{"text": "unused", "score": 0.9}])
    kb = PgVectorKnowledgeBase(client)

    assert await kb.retrieve("q", ["primer-education-kb"], top_k=-3) == []
    assert client.calls == []


async def test_top_k_larger_than_response_returns_all_rows():
    client = FakeSearchClient([{"text": "first", "score": 0.9}, {"text": "second", "score": 0.8}])
    kb = PgVectorKnowledgeBase(client)

    chunks = await kb.retrieve("q", ["primer-education-kb"], top_k=20)

    assert [chunk.text for chunk in chunks] == ["first", "second"]
    assert client.calls[0][2] == 20


async def test_duplicate_rows_are_collapsed_preserving_first_seen_order():
    duplicate = {"text": "same chunk", "score": 0.9}
    client = FakeSearchClient([duplicate, duplicate, {"text": "other", "score": 0.8}])
    kb = PgVectorKnowledgeBase(client)

    chunks = await kb.retrieve("q", ["primer-education-kb"])

    assert [chunk.text for chunk in chunks] == ["same chunk", "other"]
