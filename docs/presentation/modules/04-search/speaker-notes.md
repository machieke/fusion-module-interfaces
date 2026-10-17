# Search projection — speaker notes

Implementation baseline: `bfb0ec8856c932dc2bcbc05b8949c957da8d72cd`.
Evidence snapshot: `3dc6c1146601a0d0aa8785e61884970ec84a57c6`.
Suggested delivery: 12–15 minutes for 12 slides; follow the notes for technical discussion.
Source snapshot: 494df69a1ac401c3d3b2cf79dbfde07f74b5e277. Current M5 regressions and historical observations retain distinct source labels. No runtime or performance tests are rerun by this presentation build. Proposed benchmarks/future directions are unrun.

## 01 — Search projection

Open with the analogy, then state the technical responsibility: Maintain an exact-attribute projection and return references with explicit prefix, page and freshness semantics. Consumers must discover answers without receiving answer references. A replayable source and explicit watermark make that discovery inspectable and rebuildable. Do not treat the analogy as an additional experiment. This is a standalone talk about one responsibility, not a claim that every module is a separate service or repository.

Evidence and implementation: [search.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/search.py), [fixture_search.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/adapters/fixture_search.py), [lookup_contracts.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/lookup_contracts.py), [test_m5_boundaries.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/tests/test_m5_boundaries.py), [lookup-trace-1.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/evidence/m5/traces/lookup-trace-1.json), [native-payload-comparison.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/evidence/m5/native-payload-comparison.json).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `Search projection · M5 source bfb0ec8`.

## 02 — One module in a system of fifteen

Locate Search projection in the bounded fifteen-family inventory. The grey groups are explanatory categories, not deployment units. RevisionMath, the evidence relay, native plugins and transport bindings are supporting seams rather than additional module families. Registry and Resolver are separate responsibilities even though both are implemented in registry.py. Fifteen represented families is not full Omega requirements coverage. Maintenance consumes only declared source ports. Query does not ingest or poll the current head. Neither implementation reads foreign owner SQL or the test oracle.

Evidence and implementation: [search.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/search.py), [fixture_search.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/adapters/fixture_search.py), [lookup_contracts.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/lookup_contracts.py), [test_m5_boundaries.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/tests/test_m5_boundaries.py), [lookup-trace-1.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/evidence/m5/traces/lookup-trace-1.json), [native-payload-comparison.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/evidence/m5/native-payload-comparison.json).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `Search projection · M5 source bfb0ec8`.

## 03 — Dependencies explain the boundary

Maintenance consumes only declared source ports. Query does not ingest or poll the current head. Neither implementation reads foreign owner SQL or the test oracle. The left node is a caller or caller class; the right nodes distinguish foreign ports, pure helpers, local state and runtime internals. There is no implied shared transaction. Acceptance and immutable bytes belong to AtomStorage.

Evidence and implementation: [search.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/search.py), [fixture_search.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/adapters/fixture_search.py), [lookup_contracts.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/lookup_contracts.py), [test_m5_boundaries.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/tests/test_m5_boundaries.py), [lookup-trace-1.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/evidence/m5/traces/lookup-trace-1.json), [native-payload-comparison.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/evidence/m5/native-payload-comparison.json).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `Search projection · M5 source bfb0ec8`.

## 04 — Responsibility, state and scope

State ownership is the key contract, not the file layout. Derived projection: Extracted exact attributes; disposable and rebuildable. Progress and generation: Atomic index/checkpoint updates, rebuild intent and cursor generation. Authoritative source: Acceptance and immutable bytes belong to AtomStorage. Semantic cognition: No embeddings, scoring, inferred tasks or general knowledge search. Explicit compatibility: exact-attributes/1 · knowledge-attributes/1 · contract 2.0.0. Limits: 256 indexed records; page/batch ≤8; query ≤1024 bytes; no automatic repair.

Evidence and implementation: [search.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/search.py), [fixture_search.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/adapters/fixture_search.py), [lookup_contracts.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/lookup_contracts.py), [test_m5_boundaries.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/tests/test_m5_boundaries.py), [lookup-trace-1.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/evidence/m5/traces/lookup-trace-1.json), [native-payload-comparison.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/evidence/m5/native-payload-comparison.json).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `Search projection · M5 source bfb0ec8`.

## 05 — The executable surface

Walk the contract from inputs to effects. query: Exact conjunction of 1–3 distinct attributes; kind/topic/label; equality only. catchUp: Process ≤8 new source entries; Checkpoint advances only after complete batch. beginRebuild: Capture source head; create generation; Queries unavailable until captured prefix complete. Operation groups on this slide are not a new coverage denominator. The evidence ledger distinguishes new operations from inherited dependencies. Supporting internal helpers are labelled as seams and are not advertised remote services.

Evidence and implementation: [search.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/search.py), [fixture_search.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/adapters/fixture_search.py), [lookup_contracts.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/lookup_contracts.py), [test_m5_boundaries.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/tests/test_m5_boundaries.py), [lookup-trace-1.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/evidence/m5/traces/lookup-trace-1.json), [native-payload-comparison.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/evidence/m5/native-payload-comparison.json).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `Search projection · M5 source bfb0ec8`.

## 06 — A worked example through the boundary

Use this example to connect the responsibility to observable behavior. 1. Initial discovery: Five matches, three pages at limit two. 2. Append a match: Requested barrier exceeds the indexed prefix. 3. Signal lag: query returns NOT_AVAILABLE; no ingestion. 4. Catch up / rebuild: Six roots and nine payloads; replacement agrees. Evidence classification: REAL HIVE + SQLITE / DeTTa · independent file Search remains a fixture. Do not infer performance, broad production readiness or extra runtime integrations from this example.

Evidence and implementation: [search.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/search.py), [fixture_search.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/adapters/fixture_search.py), [lookup_contracts.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/lookup_contracts.py), [test_m5_boundaries.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/tests/test_m5_boundaries.py), [lookup-trace-1.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/evidence/m5/traces/lookup-trace-1.json), [native-payload-comparison.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/evidence/m5/native-payload-comparison.json).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `Search projection · M5 source bfb0ec8`.

## 07 — Four invariants to preserve

These invariants should survive provider substitution and future optimization. Exact matching: Case/Unicode preserved; missing attributes never match. Complete prefix: No advance across gaps, unavailable bytes or forged metadata. Bound continuation: Cursor fixes query, principal, source, snapshot and generation. Honest freshness: Prefix completeness, page completion, requested minimum and observed head are distinct. The supporting tests and runtime evidence are in the linked sources; this slide does not claim a formal proof or a production security audit.

Evidence and implementation: [search.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/search.py), [fixture_search.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/adapters/fixture_search.py), [lookup_contracts.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/lookup_contracts.py), [test_m5_boundaries.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/tests/test_m5_boundaries.py), [lookup-trace-1.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/evidence/m5/traces/lookup-trace-1.json), [native-payload-comparison.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/evidence/m5/native-payload-comparison.json).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `Search projection · M5 source bfb0ec8`.

## 08 — Failure is part of the interface

State the owner boundary before the recovery claim. Before/after checkpoint commit: Rows and checkpoint recover together. Both providers; four direct kills. During rebuild intent: Resume bounded rebuild; reject old-generation cursor. Both providers; two direct kills. Native page/result crash: Resume caller progress without seeded answers. Both providers; four native kills. A fixture can position the failure while a real process is killed. Local replay semantics do not imply exactly-once physical execution, a distributed transaction, or global failover. For pure/static modules the relevant failure is selection/refusal, not invented journal recovery.

Evidence and implementation: [search.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/search.py), [fixture_search.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/adapters/fixture_search.py), [lookup_contracts.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/lookup_contracts.py), [test_m5_boundaries.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/tests/test_m5_boundaries.py), [lookup-trace-1.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/evidence/m5/traces/lookup-trace-1.json), [native-payload-comparison.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/evidence/m5/native-payload-comparison.json).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `Search projection · M5 source bfb0ec8`.

## 09 — Measurements and benchmark gaps

Read every number with its unit and source class. 5 → 6 Matching roots before/after catch-up: Native discovery counts, not a relevance score. 2 Independent Search providers: SQLite owner + atomic-file fixture. 256 / 8 Indexed records / max page or batch: Finite contract limits, not scaling results. Native tests compare complete reference sets and canonical payload bytes across four transitions. No query-latency, ingestion-rate or relevance benchmark is recorded. Proposed: vary corpus size, selectivity, page size and index lag; report p50/p95 query latency, catch-up rate and rebuild time with explicit freshness barriers. No new benchmark is executed for this presentation. Do not compare overlapping suite times or use a one-run workflow measurement as a latency percentile.

Evidence and implementation: [search.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/search.py), [fixture_search.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/adapters/fixture_search.py), [lookup_contracts.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/lookup_contracts.py), [test_m5_boundaries.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/tests/test_m5_boundaries.py), [lookup-trace-1.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/evidence/m5/traces/lookup-trace-1.json), [native-payload-comparison.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/evidence/m5/native-payload-comparison.json).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `Search projection · M5 source bfb0ec8`.

## 10 — Current state: what is real, what is not

Implemented local code is not automatically a production provider. Real: SQLite SearchOwner over accepted real DeTTa bytes; actual native Hive query path. Fixture: Independent atomic-file Search with its own predicate evaluator; generated corpus/oracle. Blocked or unsupported: No required M5 gate blocked; general search and migration are outside this profile. Unrun: Embedding relevance, large-corpus scale, distributed indexing, compaction and live migration. All required M5 gates passed in the recorded final run, including legacy M1–M4 behavior; this presentation does not rerun those integrations. Human maintainers remain unassigned.

Evidence and implementation: [search.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/search.py), [fixture_search.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/adapters/fixture_search.py), [lookup_contracts.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/lookup_contracts.py), [test_m5_boundaries.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/tests/test_m5_boundaries.py), [lookup-trace-1.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/evidence/m5/traces/lookup-trace-1.json), [native-payload-comparison.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/evidence/m5/native-payload-comparison.json).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `Search projection · M5 source bfb0ec8`.

## 11 — Future directions need acceptance criteria

Discuss future work as conditional engineering proposals. Measure freshness/latency tradeoff requires Frozen corpus, source barriers and controlled lag; success means Latency and staleness reported together. Broaden query language deliberately requires New explicit profile and sound cursor semantics; success means No silent change to exact equality. Scale rebuild machinery requires Capacity/retention contract before optimization; success means No skipped source ranges or query-time ingestion. No new cognition, scheduler, migration or chain capability is implemented by this series. Any changed numerical semantics, placement or replay lifetime requires separate design and verification rather than a presentation claim.

Evidence and implementation: [search.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/search.py), [fixture_search.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/adapters/fixture_search.py), [lookup_contracts.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/lookup_contracts.py), [test_m5_boundaries.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/tests/test_m5_boundaries.py), [lookup-trace-1.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/evidence/m5/traces/lookup-trace-1.json), [native-payload-comparison.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/evidence/m5/native-payload-comparison.json).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `Search projection · M5 source bfb0ec8`.

## 12 — Evidence you can inspect and reproduce

Conclude with: An answer is useful only when its freshness means something precise. The reproduction entrypoint is uv run --python 3.11 --locked python scripts/verify_m5.py --gates hive --environment <env> --output <fresh>. Requires pinned native providers. The writer exits and the oracle is removed before native lookup. Fresh replacement rebuilds derived state; it is not migration. Build/export checks for this series are separate from runtime tests. Exact upstream pins remain in integration/hive/sources.json, integration/pln/sources.json, integration/pln/deduction-sources.json and the M4/M5 source manifests. Commands use fresh output/state; raw provider environments, credentials, journals and private IDs should not be published.

Evidence and implementation: [search.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/search.py), [fixture_search.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/adapters/fixture_search.py), [lookup_contracts.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/lookup_contracts.py), [test_m5_boundaries.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/tests/test_m5_boundaries.py), [lookup-trace-1.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/evidence/m5/traces/lookup-trace-1.json), [native-payload-comparison.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/evidence/m5/native-payload-comparison.json).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `Search projection · M5 source bfb0ec8`.
