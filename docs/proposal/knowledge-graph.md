# Knowledge Graph and Domain Packs

The Primer treats retrieval as domain data flowing through a domain-neutral engine. A
`DomainPack` is the isolation boundary: it bundles a domain manifest (`DomainSchema`), the
knowledge-base names declared by that manifest, and a `SkillRegistry` populated from packaged
Workflow Definition Format (WDF) YAML. Both `education` and `coop-finance` are loaded through
`load_domain_pack`; engine construction consumes the resulting pack without inspecting the
domain name.

## Domain Isolation

The manifest owns memory dimensions, subject semantics, engagements, and KB wiring. WDF files
own engagement orchestration. The pack loader validates that every declared engagement has a
packaged workflow and copies `schema.knowledge_base.kb_names` into `DomainPack.kb_names`.
Consequently, application wiring passes `pack.kb_names` to retrieval rather than hardcoding a
deployment name. Adding a domain changes its package and loader registration, not the memory,
orchestration, or retrieval engines.

This separation also makes the domain swap test meaningful: equivalent engine entrypoints can
load different packs and execute the same modules. Domain differences remain declarative in
the manifest, KB corpus, and WDF documents.

## Retrieval Port and Adapter

Engine code depends on the SDK's frozen `KnowledgeBasePort`. Its result is a list of
`RetrievedChunk` values containing only `text` and `score`. `PgVectorKnowledgeBase` implements
that port over an injected `PgVectorSearchClient`, keeping network construction at the
application edge and making adapter behavior deterministic in tests.

The adapter translates pgvector rows with either `text` or `chunk` content. A supplied `score`
is preserved; a `distance` is converted to a score in the unit interval. Ranking order is
preserved. Exact duplicate `(text, score)` results are collapsed in first-seen order because
the frozen chunk contract exposes no stable row identifier.

## Failure Policy

Retrieval distinguishes a legitimate lack of evidence from infrastructure or response
failure:

- A blank query, non-positive `top_k`, or empty client response returns `[]`.
- Backend `TimeoutError` (including `asyncio.TimeoutError`) becomes the typed domain error
  `KnowledgeBaseUnavailable`. It is not silently degraded because an engagement may need to
  distinguish "no relevant evidence" from "retrieval did not run."
- A response that is not a list at all (regardless of truthiness) raises
  `KnowledgeBaseUnavailable` — a malformed whole response is an infrastructure failure, never
  a zero-match result.
- Malformed rows are logged and skipped. Valid rows in the same response are still returned,
  so one corrupt record cannot discard useful context.
- If a non-empty response has no valid rows, `KnowledgeBaseUnavailable` is raised. Returning
  `[]` there would misrepresent corruption as a valid zero-match result.

Rows are malformed when they are not dictionaries, lack text or scoring data, or contain
wrong or non-finite value types. These checks happen at the adapter boundary before SDK model
construction, preventing transport details and validation failures from leaking into engine
code.

## Corrective Retrieval

Corrective retrieval starts with pack-derived KB routing and a query produced for the active
engagement. The retriever ranks only chunks from the requested KBs and returns up to `top_k`
evidence items. The orchestrator can then ground or revise the engagement using those chunks;
an empty result is a normal signal that no supporting evidence was found.

Offline corpus fakes model the same port and lexical ranking path for both domains. This gives
tests and demos deterministic corrective-retrieval evidence without a live database while the
pgvector adapter remains independently contract-tested for mapping and failure behavior. The
result is one retrieval interface and one engine flow, with corpus selection and instructional
workflow supplied entirely by the active `DomainPack`.
