"""Failure-path coverage for the retrieval golden harness (KG-W6).

The golden fixtures (``test_retrieval_golden_fixtures.py``) all sit exactly on
threshold: every case's top-``PROPOSED_K`` ranking equals its ``relevant_ids``,
so ``precision_at_k`` is 1.0 everywhere. Nothing there exercises the *other*
direction — a genuinely imperfect ranking whose ``precision_at_k`` drops below
the threshold. Without that, a harness that always returned 1.0 (or a scorer
that never subtracts a miss) would pass every golden case unnoticed.

This test proves the metric fails when it should, using the SAME primitives the
golden test uses — the real ``CorpusKnowledgeBase`` ranking, the text->id join,
and the frozen ``PROPOSED_K`` scoring depth — never the frozen golden set. The
imperfect ranking is *produced by the real ranker*, not hand-asserted: a
distractor chunk that shares fewer query tokens than the top relevant chunk but
more than a second, deeper relevant chunk lexically outranks that second
relevant chunk, pushing it to position 3 (outside the top-``PROPOSED_K``).
"""

from __future__ import annotations

from capillary_actions_sdk.models.knowledge import RetrievedChunk

from tests.domains.fakes import CorpusKnowledgeBase, ranking_tokens
from tests.eval.test_retrieval_golden_fixtures import CONTRACT_TOP_K, PROPOSED_K

KB_NAME = "primer-negative-path-kb"

# A purpose-built corpus (NOT the frozen golden set) with strictly distinct
# query-token overlaps, so the ranking is score-independent and unambiguous:
#   A shares 4 tokens, B shares 2, C shares 1  ->  order is always [A, B, C].
QUERY = "photosynthesis chloroplast sunlight glucose"

CORPUS = [
    {
        # Relevant + lexically strongest: 4 shared tokens -> rank 1.
        "id": "neg-photosynthesis-basics",
        "text": "Photosynthesis basics: a chloroplast captures sunlight to build glucose.",
        "score": 0.50,
    },
    {
        # A distractor: 2 shared tokens but NOT relevant. It outranks the deeper
        # relevant chunk on lexical overlap alone despite the lowest score.
        "id": "neg-ocean-tides-distractor",
        "text": "Sunlight and glucose also come up in a lesson about ocean tides.",
        "score": 0.10,
    },
    {
        # Relevant but lexically sparse: only 1 shared token -> rank 3, outside
        # the top-PROPOSED_K. Its high score cannot rescue it: overlap dominates
        # the rank key, so the relevant item is genuinely missed.
        "id": "neg-photosynthesis-advanced",
        "text": "Photosynthesis advanced: thylakoid membranes drive electron transport chains.",
        "score": 0.99,
    },
]

# The fixture-layer designation of which ids are relevant to QUERY. As in the
# golden set, relevance is declared here, not inferred from lexical overlap —
# the metric measures whether the RANKING surfaces the relevant ids in top-k.
RELEVANT_IDS = {"neg-photosynthesis-basics", "neg-photosynthesis-advanced"}


def _kb() -> tuple[CorpusKnowledgeBase, dict[str, str]]:
    corpus_by_kb = {KB_NAME: [RetrievedChunk(text=c["text"], score=c["score"]) for c in CORPUS]}
    text_to_id = {c["text"]: c["id"] for c in CORPUS}
    return CorpusKnowledgeBase(corpus_by_kb), text_to_id


def _precision_at_k(retrieved_ids: list[str], relevant_ids: set[str], k: int) -> float:
    """LD-W6's documented ``precision_at_k`` contract (README): fraction of the
    top-``k`` retrieved ids that are relevant. Defined here only because that
    scorer lives in the external LD-W6 harness, not this repo.
    """
    top_k = retrieved_ids[:k]
    return len(set(top_k) & relevant_ids) / k


def test_construction_is_a_real_ranker_output_not_hand_asserted() -> None:
    """Sanity-pin the imperfect ranking: distinct, strictly-decreasing overlaps.

    If corpus wording ever drifts into a tie, the failure below could flip on
    the score tiebreak instead of on overlap — so pin the designed structure
    (4 > 2 > 1) with the same tokenizer the fake ranks by.
    """
    query_tokens = ranking_tokens(QUERY)
    overlaps = [len(query_tokens & ranking_tokens(chunk["text"])) for chunk in CORPUS]
    assert overlaps == [4, 2, 1]


async def test_precision_at_k_drops_below_threshold_on_an_imperfect_ranking() -> None:
    """A relevant chunk ranked at position 3 makes precision@PROPOSED_K < 1.0.

    Mirrors the golden pipeline: run the real ``CorpusKnowledgeBase`` ranking,
    join ``RetrievedChunk`` back to fixture ids by text, then score. The deeper
    relevant chunk lands outside the top-``PROPOSED_K``, so the harness's
    pass/fail gate must flag it — this is the failure path the golden set never
    exercises.
    """
    kb, text_to_id = _kb()

    retrieved = await kb.retrieve(QUERY, [KB_NAME], top_k=CONTRACT_TOP_K)
    retrieved_ids = [text_to_id[chunk.text] for chunk in retrieved]

    # The real ranker produced the imperfect order: the second relevant chunk is
    # pushed to position 3 by a non-relevant distractor with more token overlap.
    assert retrieved_ids == [
        "neg-photosynthesis-basics",
        "neg-ocean-tides-distractor",
        "neg-photosynthesis-advanced",
    ]
    assert retrieved_ids[PROPOSED_K] in RELEVANT_IDS  # a relevant id sits at position 3

    # The golden self-check's pass gate (set(top-k) == relevant) now FAILS — the
    # exact primitive every golden case satisfies, here proven to reject a miss.
    assert set(retrieved_ids[:PROPOSED_K]) != RELEVANT_IDS

    # And the documented precision_at_k contract quantifies the miss: 1 of the 2
    # top-PROPOSED_K ids is relevant -> 0.5, strictly below the frozen 1.0
    # threshold. The metric detects the regression the golden cases never trip.
    precision = _precision_at_k(retrieved_ids, RELEVANT_IDS, PROPOSED_K)
    assert precision == 0.5
    assert precision < 1.0


async def test_same_ranker_still_scores_a_perfect_case_at_1_0() -> None:
    """Control: the scorer is not simply always-below-1.0.

    A perfectly-ranked query over the same corpus (both relevant ids leading)
    scores exactly 1.0, so the sub-threshold result above is a property of the
    imperfect ranking, not of the metric or fixture wiring.
    """
    kb, text_to_id = _kb()

    # This query shares tokens only with the two relevant photosynthesis chunks,
    # so they lead and the distractor is filtered out (zero overlap).
    retrieved = await kb.retrieve(
        "photosynthesis chloroplast thylakoid", [KB_NAME], top_k=CONTRACT_TOP_K
    )
    retrieved_ids = [text_to_id[chunk.text] for chunk in retrieved]

    assert set(retrieved_ids[:PROPOSED_K]) == RELEVANT_IDS
    assert _precision_at_k(retrieved_ids, RELEVANT_IDS, PROPOSED_K) == 1.0
