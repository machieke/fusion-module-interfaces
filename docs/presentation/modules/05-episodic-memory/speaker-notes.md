# EpisodicMemory · C1 — speaker notes

Implementation baseline: `bfb0ec8856c932dc2bcbc05b8949c957da8d72cd`.
Evidence snapshot: `3dc6c1146601a0d0aa8785e61884970ec84a57c6`.
Suggested delivery: 12–15 minutes for 12 slides; follow the notes for technical discussion.
Source snapshot: 494df69a1ac401c3d3b2cf79dbfde07f74b5e277. Current M5 regressions and historical observations retain distinct source labels. No runtime or performance tests are rerun by this presentation build. Proposed benchmarks/future directions are unrun.

## 01 — EpisodicMemory · C1

Open with the analogy, then state the technical responsibility: Own episode identity, ordered event acceptance, occurrence replay and evidence-delivery intents. Later belief changes need a durable history of occurrences and provenance. Processing receipts must work even when no numerical belief can be formed. Do not treat the analogy as an additional experiment. This is a standalone talk about one responsibility, not a claim that every module is a separate service or repository.

Evidence and implementation: [episodes.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/episodes.py), [delivery_contracts.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/delivery_contracts.py), [evidence_relay.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/evidence_relay.py), [test_m3_1_delivery.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/tests/test_m3_1_delivery.py), [verification.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m3_1/final/verification.json), [non-numeric-processing.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m3_1/non-numeric-processing.json).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `EpisodicMemory · C1 · M5 source bfb0ec8`.

## 02 — One module in a system of fifteen

Locate EpisodicMemory · C1 in the bounded fifteen-family inventory. The grey groups are explanatory categories, not deployment units. RevisionMath, the evidence relay, native plugins and transport bindings are supporting seams rather than additional module families. Registry and Resolver are separate responsibilities even though both are implemented in registry.py. Fifteen represented families is not full Omega requirements coverage. C1 has no PLN, C2 or Hive runtime requirement. The relay calls C1 and C2 through ports, but owns only handoff progress; C1 validates completion identity, not belief snapshots.

Evidence and implementation: [episodes.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/episodes.py), [delivery_contracts.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/delivery_contracts.py), [evidence_relay.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/evidence_relay.py), [test_m3_1_delivery.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/tests/test_m3_1_delivery.py), [verification.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m3_1/final/verification.json), [non-numeric-processing.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m3_1/non-numeric-processing.json).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `EpisodicMemory · C1 · M5 source bfb0ec8`.

## 03 — Dependencies explain the boundary

C1 has no PLN, C2 or Hive runtime requirement. The relay calls C1 and C2 through ports, but owns only handoff progress; C1 validates completion identity, not belief snapshots. The left node is a caller or caller class; the right nodes distinguish foreign ports, pure helpers, local state and runtime internals. There is no implied shared transaction. C2 owns admission; RevisionMath/PLN supply proposals.

Evidence and implementation: [episodes.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/episodes.py), [delivery_contracts.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/delivery_contracts.py), [evidence_relay.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/evidence_relay.py), [test_m3_1_delivery.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/tests/test_m3_1_delivery.py), [verification.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m3_1/final/verification.json), [non-numeric-processing.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m3_1/non-numeric-processing.json).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `EpisodicMemory · C1 · M5 source bfb0ec8`.

## 04 — Responsibility, state and scope

State ownership is the key contract, not the file layout. Episode ledger: Identity/head, accepted events, occurrence semantics and replay. Delivery intent: Pending evidence and trusted model-independent completion. Belief and numeric ownership: C2 owns admission; RevisionMath/PLN supply proposals. Foreign owner state: No C2 SQL reads and no interpretation of PLN snapshot internals. Explicit compatibility: episode-local-sequence/2; M3.1 local 3.0.0 adds episode-delivery-completion/1. Limits: 256 events/episode; 16 pending deliveries; bounded pages; trusted local placement.

Evidence and implementation: [episodes.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/episodes.py), [delivery_contracts.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/delivery_contracts.py), [evidence_relay.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/evidence_relay.py), [test_m3_1_delivery.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/tests/test_m3_1_delivery.py), [verification.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m3_1/final/verification.json), [non-numeric-processing.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m3_1/non-numeric-processing.json).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `EpisodicMemory · C1 · M5 source bfb0ec8`.

## 05 — The executable surface

Walk the contract from inputs to effects. recordEpisode / appendEvent: Create identity; append at expected sequence; Event + delivery intent commit atomically. readEpisode / readEvidence: Read ordered accepted history; Observed time is metadata, not ordering authority. pendingEvidence: Return bounded pending deliveries; Backpressure prevents dropped evidence. acknowledgeDelivery: Accept trusted processing completion; M3.1 local v3; old v2 remains explicit. Operation groups on this slide are not a new coverage denominator. The evidence ledger distinguishes new operations from inherited dependencies. Supporting internal helpers are labelled as seams and are not advertised remote services.

Evidence and implementation: [episodes.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/episodes.py), [delivery_contracts.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/delivery_contracts.py), [evidence_relay.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/evidence_relay.py), [test_m3_1_delivery.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/tests/test_m3_1_delivery.py), [verification.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m3_1/final/verification.json), [non-numeric-processing.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m3_1/non-numeric-processing.json).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `EpisodicMemory · C1 · M5 source bfb0ec8`.

## 06 — A worked example through the boundary

Use this example to connect the responsibility to observable behavior. 1. Append 16: Accept a full batch of observations. 2. Drain 16: Relay validates C2 receipts; C1 clears pending. 3. Repeat: Append and drain another sixteen. 4. Finish 1: 33 retained events; zero pending after each drain. Evidence classification: M3.1 REAL DeTTa / native PLN · generated observations; historical source labelled. Do not infer performance, broad production readiness or extra runtime integrations from this example.

Evidence and implementation: [episodes.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/episodes.py), [delivery_contracts.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/delivery_contracts.py), [evidence_relay.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/evidence_relay.py), [test_m3_1_delivery.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/tests/test_m3_1_delivery.py), [verification.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m3_1/final/verification.json), [non-numeric-processing.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m3_1/non-numeric-processing.json).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `EpisodicMemory · C1 · M5 source bfb0ec8`.

## 07 — Four invariants to preserve

These invariants should survive provider substitution and future optimization. One occurrence: Same occurrence/body replays; altered meaning conflicts. Ordered acceptance: Expected-head CAS controls append order; observed time cannot retime it. Atomic intent: An accepted evidence event has a delivery intent in the same C1 commit. Independent completion: Processing may finish with no numerical truth value; history remains retained. The supporting tests and runtime evidence are in the linked sources; this slide does not claim a formal proof or a production security audit.

Evidence and implementation: [episodes.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/episodes.py), [delivery_contracts.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/delivery_contracts.py), [evidence_relay.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/evidence_relay.py), [test_m3_1_delivery.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/tests/test_m3_1_delivery.py), [verification.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m3_1/final/verification.json), [non-numeric-processing.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m3_1/non-numeric-processing.json).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `EpisodicMemory · C1 · M5 source bfb0ec8`.

## 08 — Failure is part of the interface

State the owner boundary before the recovery claim. Payload saved; append not committed: Retry through AtomStorage, then commit episode state. No cross-owner transaction. C2 decision committed; acknowledgment lost: Relay recovers exact decision and retries trusted completion. No manufactured acknowledgment. Capacity or malformed receipt: Pause with pending evidence; never drop or falsely complete. Repeated-drain and hostile-receipt tests. A fixture can position the failure while a real process is killed. Local replay semantics do not imply exactly-once physical execution, a distributed transaction, or global failover. For pure/static modules the relevant failure is selection/refusal, not invented journal recovery.

Evidence and implementation: [episodes.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/episodes.py), [delivery_contracts.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/delivery_contracts.py), [evidence_relay.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/evidence_relay.py), [test_m3_1_delivery.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/tests/test_m3_1_delivery.py), [verification.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m3_1/final/verification.json), [non-numeric-processing.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m3_1/non-numeric-processing.json).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `EpisodicMemory · C1 · M5 source bfb0ec8`.

## 09 — Measurements and benchmark gaps

Read every number with its unit and source class. 33 Observations in one episode: Historical M3.1 repeated-drain observation. 16 / 16 / 1 Three drain batches: Pending returned to zero after every batch. 256 / 16 Lifetime events / pending limit: Contract bounds; distinct from observed 33. This is a delivery/liveness scenario with generated evidence. No append latency, sustained ingestion, storage growth or long-duration retention benchmark is recorded. Proposed: vary append/drain ratio, provenance size and injected relay outage; measure p50/p95 append latency, backlog age and bytes/event without dropping history. No new benchmark is executed for this presentation. Do not compare overlapping suite times or use a one-run workflow measurement as a latency percentile.

Evidence and implementation: [episodes.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/episodes.py), [delivery_contracts.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/delivery_contracts.py), [evidence_relay.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/evidence_relay.py), [test_m3_1_delivery.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/tests/test_m3_1_delivery.py), [verification.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m3_1/final/verification.json), [non-numeric-processing.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m3_1/non-numeric-processing.json).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `EpisodicMemory · C1 · M5 source bfb0ec8`.

## 10 — Current state: what is real, what is not

Implemented local code is not automatically a production provider. Real: Private SQLite episode owner over real DeTTa; native episode and inference actions. Fixture: Generated reports, operator origins/grants and hostile completion responses. Blocked or unsupported: No required current gate blocked. Pre-existing M3-format pending work is not repaired by new profiles. Unrun: Long-lived production histories, distributed writers, deletion/retention policy and migration. All required M5 gates passed in the recorded final run, including legacy M1–M4 behavior; this presentation does not rerun those integrations. Human maintainers remain unassigned.

Evidence and implementation: [episodes.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/episodes.py), [delivery_contracts.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/delivery_contracts.py), [evidence_relay.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/evidence_relay.py), [test_m3_1_delivery.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/tests/test_m3_1_delivery.py), [verification.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m3_1/final/verification.json), [non-numeric-processing.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m3_1/non-numeric-processing.json).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `EpisodicMemory · C1 · M5 source bfb0ec8`.

## 11 — Future directions need acceptance criteria

Discuss future work as conditional engineering proposals. Measure backlog behavior requires Rate-controlled append/drain and outages; success means No loss; bounded backpressure and recovery age. Add explicit retention policy requires Provenance and replay obligations first; success means Deletion cannot silently invalidate accepted evidence. Improve inspection tools requires Authorized read-only views with privacy controls; success means Explain event order and delivery state without exposing identifiers. No new cognition, scheduler, migration or chain capability is implemented by this series. Any changed numerical semantics, placement or replay lifetime requires separate design and verification rather than a presentation claim.

Evidence and implementation: [episodes.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/episodes.py), [delivery_contracts.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/delivery_contracts.py), [evidence_relay.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/evidence_relay.py), [test_m3_1_delivery.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/tests/test_m3_1_delivery.py), [verification.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m3_1/final/verification.json), [non-numeric-processing.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m3_1/non-numeric-processing.json).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `EpisodicMemory · C1 · M5 source bfb0ec8`.

## 12 — Evidence you can inspect and reproduce

Conclude with: Processing completion is not the same as numerical agreement. The reproduction entrypoint is uv run --python 3.11 --locked python scripts/verify_m3_1.py <env> --output <fresh>. Fresh explicit closure profiles; full wrapper includes older regressions. Historical 33-event evidence remains tied to its own tested revision. Build/export checks for this series are separate from runtime tests. Exact upstream pins remain in integration/hive/sources.json, integration/pln/sources.json, integration/pln/deduction-sources.json and the M4/M5 source manifests. Commands use fresh output/state; raw provider environments, credentials, journals and private IDs should not be published.

Evidence and implementation: [episodes.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/episodes.py), [delivery_contracts.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/delivery_contracts.py), [evidence_relay.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/evidence_relay.py), [test_m3_1_delivery.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/tests/test_m3_1_delivery.py), [verification.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m3_1/final/verification.json), [non-numeric-processing.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m3_1/non-numeric-processing.json).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `EpisodicMemory · C1 · M5 source bfb0ec8`.
