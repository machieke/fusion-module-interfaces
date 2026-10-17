# BeliefRevision · C2 — speaker notes

Implementation baseline: `bfb0ec8856c932dc2bcbc05b8949c957da8d72cd`.
Evidence snapshot: `3dc6c1146601a0d0aa8785e61884970ec84a57c6`.
Suggested delivery: 12–15 minutes for 12 slides; follow the notes for technical discussion.
Source snapshot: 494df69a1ac401c3d3b2cf79dbfde07f74b5e277. Current M5 regressions and historical observations retain distinct source labels. No runtime or performance tests are rerun by this presentation build. Proposed benchmarks/future directions are unrun.

## 01 — BeliefRevision · C2

Open with the analogy, then state the technical responsibility: Own evidence/support admission, historical belief snapshots, semantic attempts and derived-support decisions. Numerical revision is meaningful only when the system tracks which evidence contributed, which assumptions were made and which alternatives remain. Do not treat the analogy as an additional experiment. This is a standalone talk about one responsibility, not a claim that every module is a separate service or repository.

Evidence and implementation: [beliefs.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/beliefs.py), [derived_beliefs.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/derived_beliefs.py), [cognition_contracts.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/cognition_contracts.py), [test_m2.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/tests/test_m2.py), [demo.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m2/final/demo.json), [m3-evidence.md](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/m3-evidence.md).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `BeliefRevision · C2 · M5 source bfb0ec8`.

## 02 — One module in a system of fifteen

Locate BeliefRevision · C2 in the bounded fifteen-family inventory. The grey groups are explanatory categories, not deployment units. RevisionMath, the evidence relay, native plugins and transport bindings are supporting seams rather than additional module families. Registry and Resolver are separate responsibilities even though both are implemented in registry.py. Fifteen represented families is not full Omega requirements coverage. C2 invokes mathematics and then performs authority, binding and CAS checks before its own commit. C4 requests admission; it never writes beliefs or calls the kernel directly.

Evidence and implementation: [beliefs.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/beliefs.py), [derived_beliefs.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/derived_beliefs.py), [cognition_contracts.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/cognition_contracts.py), [test_m2.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/tests/test_m2.py), [demo.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m2/final/demo.json), [m3-evidence.md](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/m3-evidence.md).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `BeliefRevision · C2 · M5 source bfb0ec8`.

## 03 — Dependencies explain the boundary

C2 invokes mathematics and then performs authority, binding and CAS checks before its own commit. C4 requests admission; it never writes beliefs or calls the kernel directly. The left node is a caller or caller class; the right nodes distinguish foreign ports, pure helpers, local state and runtime internals. There is no implied shared transaction. C1 owns episodes and evidence-delivery intent.

Evidence and implementation: [beliefs.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/beliefs.py), [derived_beliefs.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/derived_beliefs.py), [cognition_contracts.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/cognition_contracts.py), [test_m2.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/tests/test_m2.py), [demo.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m2/final/demo.json), [m3-evidence.md](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/m3-evidence.md).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `BeliefRevision · C2 · M5 source bfb0ec8`.

## 04 — Responsibility, state and scope

State ownership is the key contract, not the file layout. Support + observation ledger: Accepted occurrence lineage, alternatives and historical snapshots. Semantic attempts: Exact input bindings and durable admission decisions. Original event history: C1 owns episodes and evidence-delivery intent. Pure math and task scheduling: Providers calculate; Attention ranks; C4 budgets work. Explicit compatibility: M2 pln-revision-private/1; fresh M3 pln-derived-private/1 · local v3. Limits: Bounded local support history; aggregate covers admitted supports, not every retained observation.

Evidence and implementation: [beliefs.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/beliefs.py), [derived_beliefs.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/derived_beliefs.py), [cognition_contracts.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/cognition_contracts.py), [test_m2.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/tests/test_m2.py), [demo.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m2/final/demo.json), [m3-evidence.md](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/m3-evidence.md).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `BeliefRevision · C2 · M5 source bfb0ec8`.

## 05 — The executable surface

Walk the contract from inputs to effects. submitEvidence: Validate C1 evidence or existing support; Admit/duplicate separately from numerical outcome. readBelief: Read exact historical or current snapshot; Aggregate states its admitted coverage. submitDerivation: Bind exact historical premise vector; v3 tagged support; no new observation. readDerivation: Recover a saved semantic decision; Replay does not force another calculation. Operation groups on this slide are not a new coverage denominator. The evidence ledger distinguishes new operations from inherited dependencies. Supporting internal helpers are labelled as seams and are not advertised remote services.

Evidence and implementation: [beliefs.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/beliefs.py), [derived_beliefs.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/derived_beliefs.py), [cognition_contracts.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/cognition_contracts.py), [test_m2.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/tests/test_m2.py), [demo.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m2/final/demo.json), [m3-evidence.md](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/m3-evidence.md).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `BeliefRevision · C2 · M5 source bfb0ec8`.

## 06 — A worked example through the boundary

Use this example to connect the responsibility to observable behavior. 1. Retain reports: Store original and contrary observations. 2. Check lineage: Copied/ancestor support cannot create independent roots. 3. Run guarded revision: Eligible exact pair uses the pinned native formula. 4. Commit decision: Keep alternatives and explicit aggregate coverage. Evidence classification: M2 REAL native PLN + DeTTa · generated observations and explicit independence assumptions. Do not infer performance, broad production readiness or extra runtime integrations from this example.

Evidence and implementation: [beliefs.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/beliefs.py), [derived_beliefs.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/derived_beliefs.py), [cognition_contracts.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/cognition_contracts.py), [test_m2.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/tests/test_m2.py), [demo.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m2/final/demo.json), [m3-evidence.md](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/m3-evidence.md).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `BeliefRevision · C2 · M5 source bfb0ec8`.

## 07 — Four invariants to preserve

These invariants should survive provider substitution and future optimization. Admission ≠ aggregation: A report may be processed without changing a numerical truth. No double evidence: New key or speaker cannot manufacture an independent origin. Derived support inherits: Deduction carries original roots and ancestry; no fresh observation count. Owner commits last: Recheck exact bindings, current authority and expected revision before committing. The supporting tests and runtime evidence are in the linked sources; this slide does not claim a formal proof or a production security audit.

Evidence and implementation: [beliefs.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/beliefs.py), [derived_beliefs.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/derived_beliefs.py), [cognition_contracts.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/cognition_contracts.py), [test_m2.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/tests/test_m2.py), [demo.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m2/final/demo.json), [m3-evidence.md](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/m3-evidence.md).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `BeliefRevision · C2 · M5 source bfb0ec8`.

## 08 — Failure is part of the interface

State the owner boundary before the recovery claim. Proposal computed; owner commit lost: Recover/retry exact attempt under its budget semantics. Physical calculation may repeat where allowed. Decision saved; relay reply lost: Return the original decision through declared ports. Duplicate-safe admission. Stale revision / malformed provider response: Refuse or retain explicit outcome; never silently rebind. CAS and hostile-response tests. A fixture can position the failure while a real process is killed. Local replay semantics do not imply exactly-once physical execution, a distributed transaction, or global failover. For pure/static modules the relevant failure is selection/refusal, not invented journal recovery.

Evidence and implementation: [beliefs.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/beliefs.py), [derived_beliefs.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/derived_beliefs.py), [cognition_contracts.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/cognition_contracts.py), [test_m2.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/tests/test_m2.py), [demo.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m2/final/demo.json), [m3-evidence.md](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/m3-evidence.md).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `BeliefRevision · C2 · M5 source bfb0ec8`.

## 09 — Measurements and benchmark gaps

Read every number with its unit and source class. 0.5 / ⅔ Native revision strength / confidence: Recorded M2 generated example; model-specific. 2 Retained alternatives in M2 story: Disagreement remains visible. 0 new Observations from derived support: M3 admission invariant, not an accuracy score. These are numerical goldens and lineage/admission results. They do not measure calibrated confidence, predictive accuracy, source independence or per-admission latency. Proposed: fix support lineage and premise snapshots; vary duplicate ratio, alternatives and CAS contention. Measure admission p50/p95 and verify unchanged evidence-root accounting. No new benchmark is executed for this presentation. Do not compare overlapping suite times or use a one-run workflow measurement as a latency percentile.

Evidence and implementation: [beliefs.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/beliefs.py), [derived_beliefs.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/derived_beliefs.py), [cognition_contracts.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/cognition_contracts.py), [test_m2.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/tests/test_m2.py), [demo.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m2/final/demo.json), [m3-evidence.md](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/m3-evidence.md).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `BeliefRevision · C2 · M5 source bfb0ec8`.

## 10 — Current state: what is real, what is not

Implemented local code is not automatically a production provider. Real: Private SQLite owners, actual guarded native revision/deduction and real DeTTa bytes. Fixture: Generated claims, declared independence assumptions, malformed proposals and injected crashes. Blocked or unsupported: No required supported gate blocked. Existing v2/v3 journals are not migrated or silently widened. Unrun: Retraction, arbitrary rule libraries, calibration, hidden-copy detection and distributed belief writers. All required M5 gates passed in the recorded final run, including legacy M1–M4 behavior; this presentation does not rerun those integrations. Human maintainers remain unassigned.

Evidence and implementation: [beliefs.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/beliefs.py), [derived_beliefs.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/derived_beliefs.py), [cognition_contracts.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/cognition_contracts.py), [test_m2.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/tests/test_m2.py), [demo.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m2/final/demo.json), [m3-evidence.md](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/m3-evidence.md).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `BeliefRevision · C2 · M5 source bfb0ec8`.

## 11 — Future directions need acceptance criteria

Discuss future work as conditional engineering proposals. Measure admission costs requires Controlled lineage/duplicate/CAS workloads; success means Latency reported with duplicate and conflict rates. Specify retraction semantics requires Versioned provenance and historical-read contract; success means No erased history or unaccounted evidence. Evaluate numerical usefulness requires External task dataset and calibration protocol; success means Accuracy/calibration separated from conformance. No new cognition, scheduler, migration or chain capability is implemented by this series. Any changed numerical semantics, placement or replay lifetime requires separate design and verification rather than a presentation claim.

Evidence and implementation: [beliefs.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/beliefs.py), [derived_beliefs.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/derived_beliefs.py), [cognition_contracts.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/cognition_contracts.py), [test_m2.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/tests/test_m2.py), [demo.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m2/final/demo.json), [m3-evidence.md](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/m3-evidence.md).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `BeliefRevision · C2 · M5 source bfb0ec8`.

## 12 — Evidence you can inspect and reproduce

Conclude with: The owner decides what counts; the calculator only proposes. The reproduction entrypoint is uv run --python 3.11 --locked python scripts/verify_m3.py <env> --output <fresh>. Uses explicit private profiles and pinned native providers. Historical M2 demo is a CLI observation; separate native Hive cases establish the real-caller gate. Build/export checks for this series are separate from runtime tests. Exact upstream pins remain in integration/hive/sources.json, integration/pln/sources.json, integration/pln/deduction-sources.json and the M4/M5 source manifests. Commands use fresh output/state; raw provider environments, credentials, journals and private IDs should not be published.

Evidence and implementation: [beliefs.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/beliefs.py), [derived_beliefs.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/derived_beliefs.py), [cognition_contracts.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/cognition_contracts.py), [test_m2.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/tests/test_m2.py), [demo.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m2/final/demo.json), [m3-evidence.md](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/m3-evidence.md).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `BeliefRevision · C2 · M5 source bfb0ec8`.
