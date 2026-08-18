"""PgVectorKnowledgeBase — KnowledgeBasePort adapter over the platform's pgvector KB.

The pgvector search client is injected at construction time; this module has
no httpx/network import on the call path (the real HTTP client is constructed
at the application edge and exercised only in DS-W3's manual live smoke).
"""

from __future__ import annotations

import logging
import math
from numbers import Real
from typing import Protocol

from capillary_actions_sdk.models.knowledge import RetrievedChunk
from capillary_actions_sdk.ports.knowledge import KnowledgeBasePort

from primer_core.errors import KnowledgeBaseUnavailable

logger = logging.getLogger(__name__)


class PgVectorSearchClient(Protocol):
    """Injected client that performs the actual pgvector similarity search."""

    async def search(self, query: str, kb_names: list[str], top_k: int) -> list[dict]: ...


def _row_to_chunk(row: object) -> RetrievedChunk:
    if not isinstance(row, dict):
        raise ValueError("row is not a dictionary")

    if "text" in row:
        text = row["text"]
    elif "chunk" in row:
        text = row["chunk"]
    else:
        raise ValueError("row has no text or chunk field")
    if not isinstance(text, str):
        raise ValueError("row text is not a string")

    if "score" in row:
        score = row["score"]
    elif "distance" in row:
        distance = row["distance"]
        if not isinstance(distance, Real) or isinstance(distance, bool):
            raise ValueError("row distance is not numeric")
        if not math.isfinite(float(distance)):
            raise ValueError("row distance is not a finite number")
        score = max(0.0, min(1.0, 1.0 - float(distance)))
    else:
        raise ValueError("row has no score or distance field")

    if not isinstance(score, Real) or isinstance(score, bool) or not math.isfinite(score):
        raise ValueError("row score is not a finite number")
    return RetrievedChunk(text=text, score=float(score))


class PgVectorKnowledgeBase(KnowledgeBasePort):
    """KnowledgeBasePort backed by the platform's pgvector KB via an injected client."""

    def __init__(self, client: PgVectorSearchClient) -> None:
        self._client = client

    async def retrieve(
        self, query: str, kb_names: list[str], top_k: int = 5
    ) -> list[RetrievedChunk]:
        if not query.strip() or top_k <= 0:
            return []

        try:
            rows = await self._client.search(query, kb_names, top_k)
        except TimeoutError as exc:
            raise KnowledgeBaseUnavailable("knowledge-base retrieval timed out") from exc

        if not isinstance(rows, list):
            raise KnowledgeBaseUnavailable("knowledge base returned a malformed response")
        if not rows:
            return []

        chunks: list[RetrievedChunk] = []
        seen: set[tuple[str, float]] = set()
        malformed_count = 0
        for index, row in enumerate(rows):
            try:
                chunk = _row_to_chunk(row)
            except (TypeError, ValueError) as exc:
                malformed_count += 1
                logger.warning("Skipping malformed knowledge-base row %d: %s", index, exc)
                continue

            key = (chunk.text, chunk.score)
            if key not in seen:
                seen.add(key)
                chunks.append(chunk)

        if not chunks and malformed_count:
            raise KnowledgeBaseUnavailable(
                f"knowledge base returned no usable rows ({malformed_count} malformed)"
            )
        return chunks
