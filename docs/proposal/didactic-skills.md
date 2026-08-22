# Didactic Skills

The Didactic Skills layer provides domain-agnostic orchestration for Primer
engagements. It resolves declaratively registered skills, executes them through
the workflow runner, exposes synchronous and streaming execution surfaces, and
coordinates lifecycle hooks, memory write-back, and schema-defined follow-up
behavior.

The orchestration layer is intentionally domain independent. Education and
coop-finance engagements use the same `EngagementOrchestrator`, hook registry,
streaming protocol, and memory interfaces; domain-specific behavior is supplied
through schemas, registered skills, and workflow definitions.

## Engagement Orchestration

`EngagementOrchestrator` is the primary execution boundary for registered
engagements.

The public engagement contract is:

`run_engagement(skill_name, subject_id, thread_id, input_data=None)`

A skill name is resolved through `SkillRegistry` to its workflow identifier.
The orchestrator constructs a `RunWorkflowRequest` and delegates execution to
the configured `RunWorkflowPort`.

The non-streaming path returns the runner's `RunWorkflowResponse`. When hooks
are configured, the same `HookContext` is shared across the engagement
lifecycle so handlers can observe the original input, workflow outcome,
execution status, and run identifier.

The orchestration package does not contain education- or finance-specific
routing logic. Domain behavior remains declarative through the domain schema
and registered WDF skills.

## Hooks and Triggers

Primer defines six lifecycle hook events:

- `BEFORE_ENGAGEMENT`
- `AFTER_ENGAGEMENT`
- `ON_MASTERY_CHANGE`
- `ON_STRUGGLE_DETECTED`
- `ON_SESSION_START`
- `ON_SESSION_END`

Handlers are registered through `HookRegistry` and execute sequentially in
registration order. This ordering is deterministic.

`BEFORE_ENGAGEMENT` runs before workflow execution and
`AFTER_ENGAGEMENT` runs after engagement execution or streaming cleanup.
Additional events allow orchestration policy to react to learner-state
transitions without embedding those policies directly in individual skills.

For example, the current struggle handler can select a simpler
schema-defined engagement when the current workflow reports that the learner
is struggling.

### Hook Failure Policy

Hook failures use an isolate-and-log policy.

Each registered handler is invoked independently. If one handler raises an
exception, the failure is logged with its exception information and remaining
handlers continue executing in registration order.

This prevents secondary lifecycle behavior from aborting an otherwise valid
engagement while preserving observability of hook failures.

The registry intentionally remains sequential rather than executing handlers
concurrently so hook ordering remains deterministic.

## Streaming and AG-UI Protocol

`run_engagement_streaming` exposes workflow execution as typed `AGUIEvent`
instances.

Events are yielded directly to the caller and may also be forwarded through an
`EventStreamPort`. The orchestrator does not redefine or replace the AG-UI
event vocabulary produced by the workflow runner.

Streaming engagements use the same hook lifecycle as synchronous engagements.
`BEFORE_ENGAGEMENT` runs before workflow execution, while
`AFTER_ENGAGEMENT` runs after successful non-streaming execution or from the 
streaming cleanup path.

The cleanup path is protected with `try/finally`, which guarantees that the
after-engagement lifecycle runs when:

- the stream completes normally;
- the consumer closes the stream before consuming every event; or
- the underlying runner raises during streaming.

Runner exceptions are not swallowed by the orchestrator. Cleanup executes and
the original exception continues to propagate to the caller.

## Streaming Write-Back Contract

Structured workflow outcomes and AG-UI event traces have different semantics
and are represented separately in the hook payload.

For synchronous engagements:

- `payload["outcome"]` contains the structured workflow output.

For streaming engagements:

- `payload["streamed_events"]` contains the `AGUIEvent` instances observed
  during the stream.

A list of protocol events is therefore never treated as a structured workflow
outcome.

`write_back_outcome` persists a write-back mapping when one is supplied by a
structured engagement outcome. A streaming engagement that contains only
`streamed_events` and no structured write-back is a valid no-op rather than an
error.

Malformed explicit write-back data remains an error. This preserves contract
validation while allowing streaming engagements to participate safely in the
same `AFTER_ENGAGEMENT` hook lifecycle.

## Knowledge-Base Failure Policy

Retrieval distinguishes between an empty successful result and a failed
retrieval operation.

If the knowledge base successfully returns no relevant chunks, the interaction
continues normally with an empty retrieved context.

If retrieval raises `KnowledgeBaseUnavailable`, `InteractionAgent` logs the
outage and degrades to a no-context interaction. Learner working memory is
still assembled and the model can still produce a response.

Only the typed `KnowledgeBaseUnavailable` failure receives this degradation
behavior. Unexpected exceptions are allowed to propagate rather than being
silently converted into successful interactions.

This distinction preserves availability during known knowledge-service
outages without hiding unrelated implementation failures.

## Memory Write-Back

Engagement outcomes can provide a schema-aligned `writeback` mapping containing
a target dimension and structured content.

The `AFTER_ENGAGEMENT` write-back handler converts valid write-back data into a
`PreferenceSignal` and persists it through `MemoryCore`.

This keeps workflow execution separated from persistence: skills describe the
outcome, lifecycle hooks decide when that outcome is committed to memory, and
the memory layer owns storage behavior.

## Evaluation Mapping

The Didactic Skills implementation contributes to the Primer evaluation
dimensions for `declarative_orchestration` and `protocol_compliance`.

### `declarative_orchestration`

The `declarative_orchestration` metric verifies that the evaluated engagement
for each requested domain resolves to a WDF definition through the domain
pack.

A passing result means the evaluated engagements have WDF YAML definitions
rather than requiring their engagement definitions to be encoded directly in
the orchestration engine.

### `protocol_compliance`

The `protocol_compliance` metric executes each domain through
`run_engagement_streaming` and verifies that every emitted item is an
`AGUIEvent`.

A passing result means the streaming surface preserves the typed AG-UI
protocol expected by downstream consumers. The W7 streaming hardening
operates around this protocol surface without changing the emitted event
contract.