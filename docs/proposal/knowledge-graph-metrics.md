# Knowledge Graph Evidence and Exit Metrics

The Knowledge Graph stream claims that domain differences are declarative and that retrieval
can change corpus and workflow without changing engine behavior. The eval suite turns that
claim into five named transition metrics, a retrieval-quality gate, and a dual-domain swap
headline. `tests/test_eval_suite.py::test_all_five_transition_metrics_pass_and_aggregate_into_report`
requires all five metrics below to pass together for `education` and `coop-finance`.

## Transition Metrics

| Metric | What it proves for the KG and DomainPack design | Enforcement |
| --- | --- | --- |
| `declarative_orchestration` | Each evaluated engagement resolves to a packaged WDF YAML document through its `DomainPack`; orchestration differences do not require engine branches. | `run_transition_metrics` in `src/primer_core/eval/metrics.py`, aggregated by `tests/test_eval_suite.py::test_all_five_transition_metrics_pass_and_aggregate_into_report` |
| `typed_models` | Each pack's manifest controls valid memory dimensions. Both domains accept declared dimensions and reject an undeclared dimension, so domain data remains schema-bound rather than inferred in agent code. | The aggregate test above also asserts the undeclared-dimension negative path reported by `typed_models`. |
| `port_conformance` | Domain flows remain behind ports: swapping in-memory and file `MemoryStore` implementations produces identical working memory. This is the same dependency direction used by `KnowledgeBasePort`, allowing fake and pgvector retrieval adapters without changing the engine. | `src/primer_core/eval/metrics.py::port_conformance`, run by the aggregate transition-metric test |
| `protocol_compliance` | Streaming the pack-selected engagement emits only SDK AG-UI events. Domain-specific WDF and retrieval context therefore do not alter the engine's external event protocol. | `src/primer_core/eval/metrics.py::protocol_compliance`, run by the aggregate transition-metric test; focused AG-UI coverage also lives in `tests/eval/test_agui_protocol.py`. |
| `stateless_agents` | Engagement execution does not retain persistent learner or member state in the orchestrator. Retrieved evidence and memory move through ports, making a domain swap independent of prior in-process state. | `src/primer_core/eval/metrics.py::stateless_agents`, run by the aggregate transition-metric test |

## Retrieval Quality Gate

The frozen record `tests/eval/fixtures/retrieval_golden.json` contains both domain corpora,
manifest KB names, queries, ranked IDs, and relevant IDs. The gate is precision@k with `k=2`
and threshold `1.0`: for every case, both relevant IDs must occupy the first two ranked
positions. `tests/test_eval_suite.py::test_retrieval_quality_is_scored_from_golden_fixtures`
applies the shared `precision_at_k` implementation. The fixture contract and live lexical
ranking are independently checked by `tests/eval/test_retrieval_golden_fixtures.py`, including
manifest-derived KB routing and cross-domain bleed bait. The imperfect-ranking case in
`tests/eval/test_retrieval_golden_failure_path.py` proves the threshold can fail rather than
passing vacuously.

The SDK's `RetrievedChunk` exposes only `text` and `score`, so fixture IDs are joined at the
fixture adapter layer and are not added to the frozen SDK model.

## Swap-Parity Headline

`tests/eval/test_swap_test.py::test_identical_engine_module_set_across_domains` runs the same
orchestrator flow once per pack under a module tracer. It requires a non-empty engine-module
set, excludes eval modules, and requires the education and coop-finance module sequences to be
identical. The headline means all observed differences came from the pack's manifest, KB
wiring, and WDF rather than conditional engine code.

`demos/kb_domain_swap.py` packages this evidence for the program-exit demonstration. It loads
both packs, derives each KB name from its manifest, runs both seeded retrievals through one
function, and reuses the swap-parity tracer. It exits non-zero if retrieval wiring or engine
module parity fails and prints `Zero engine branching: PASS` only when both checks succeed.
