# Learning Data Evidence and Exit Metrics

The Learning Data stream claims that users' interactions with the Primer can be accurately recorded as **entries** (`MemoryEntry` objects) stored
either in the current session's memory or in a file for future reference. The stream claims to achieve this via

* **ports** (`MemoryStorePort` and its subclasses `InMemoryMemoryStore` and `FileMemoryStore`) that store and categorize entries based on users' unique IDs,
* **domain schemas** (`DomainSchema`), characterized by the user/subject, dimensions (with their respective fields), knowledge base, and engagements/skills relevant to a certain domain, and
* **memory cores** (`MemoryCore`) that tie ports and domain schemas together, validating entries against a particular domain schema before storing the entries in a designated port.

The eval suite turns that claim into three named transition metrics. `tests/test_eval_suite.py::test_all_five_transition_metrics_pass_and_aggregate_into_report`
requires all three metrics below (among others) to pass together for `education` and `coop-finance`.

## Transition Metrics

| Metric | What it proves for the LD and DomainSchema/MemoryCore/ports design | Enforcement |
| --- | --- | --- |
| `typed_models` | When a `MemoryCore` object is created with a particular domain schema, an entry with any of that schema's declared dimensions will be properly validated and written into memory. An entry with a dimension that has not been declared by the schema is caught and raises a ValueError. | `run_transition_metrics` in `src/primer_core/eval/metrics.py`, aggregated by `tests/test_eval_suite.py::test_all_five_transition_metrics_pass_and_aggregate_into_report` |
| `port_conformance` | Both `InMemoryMemoryStore` objects and `FileMemoryStore` objects are capable of storing entries in working memory to be referred back to in the same session. Given the same entries, the working memory created by an `InMemoryMemoryStore` object is indistinguishable from the working memory created by a `FileMemoryStore` object. | `run_transition_metrics` in `src/primer_core/eval/metrics.py`, aggregated by `tests/test_eval_suite.py::test_all_five_transition_metrics_pass_and_aggregate_into_report` |
| `stateless_agents` | The `EngagementOrchestrator` objects that manage engagements with the user have no trace of the entries they write back into memory; entries are only stored in ports.  | `run_transition_metrics` in `src/primer_core/eval/metrics.py`, aggregated by `tests/test_eval_suite.py::test_all_five_transition_metrics_pass_and_aggregate_into_report` |



## Memory Path End-to-End Demonstration

`demos/demo_education.py` packages this evidence for the program-exit demonstration.
It loads two distinct sessions with `FileMemoryStore` objects pointing to the same memory
file. The first session runs an engagement to completion, and the second session refers to
the memory file to pick up where the first session left off. It exits non-zero if session
1's outcome differs from session 2's working memory and prints `"Running assemble_working_memory on session 2 precisely surfaces the first session's outcome. --> DEMO SUCCESS"` only when the two are identical.
