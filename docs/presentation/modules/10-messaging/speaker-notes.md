# Agent messaging — speaker notes

Implementation baseline: `bfb0ec8856c932dc2bcbc05b8949c957da8d72cd`.
Evidence snapshot: `3dc6c1146601a0d0aa8785e61884970ec84a57c6`.
Suggested delivery: 12–15 minutes for 12 slides; follow the notes for technical discussion.
Source snapshot: 494df69a1ac401c3d3b2cf79dbfde07f74b5e277. Current M5 regressions and historical observations retain distinct source labels. No runtime or performance tests are rerun by this presentation build. Proposed benchmarks/future directions are unrun.

## 01 — Agent messaging

Open with the analogy, then state the technical responsibility: Own scoped mailbox acceptance, committed inbox ordering, repeated polling and acknowledgment replay. A lost reply must not lose accepted work or imply delivery that never happened. Separate mailbox ownership lets execution retry completion safely. Do not treat the analogy as an additional experiment. This is a standalone talk about one responsibility, not a claim that every module is a separate service or repository.

Evidence and implementation: [messaging.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/messaging.py), [execution.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/execution.py), [test_contract.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/tests/test_contract.py), [test_m11.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/tests/test_m11.py), [m11-swap-demo.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m1_2/m11-swap-demo.json), [same-artifact.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/evidence/m4/final/same-artifact.json).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `Agent messaging · M5 source bfb0ec8`.

## 02 — One module in a system of fifteen

Locate Agent messaging in the bounded fifteen-family inventory. The grey groups are explanatory categories, not deployment units. RevisionMath, the evidence relay, native plugins and transport bindings are supporting seams rather than additional module families. Registry and Resolver are separate responsibilities even though both are implemented in registry.py. Fifteen represented families is not full Omega requirements coverage. MessagingSession.send reads AtomStorage before enqueue. MessageOwner owns only acceptance/delivery state. Execution uses the narrow trusted CompletionDelivery.accept port, not public mutation routes.

Evidence and implementation: [messaging.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/messaging.py), [execution.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/execution.py), [test_contract.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/tests/test_contract.py), [test_m11.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/tests/test_m11.py), [m11-swap-demo.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m1_2/m11-swap-demo.json), [same-artifact.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/evidence/m4/final/same-artifact.json).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `Agent messaging · M5 source bfb0ec8`.

## 03 — Dependencies explain the boundary

MessagingSession.send reads AtomStorage before enqueue. MessageOwner owns only acceptance/delivery state. Execution uses the narrow trusted CompletionDelivery.accept port, not public mutation routes. The left node is a caller or caller class; the right nodes distinguish foreign ports, pure helpers, local state and runtime internals. There is no implied shared transaction. AtomStorage owns bytes; Execution owns terminal job/outbox state.

Evidence and implementation: [messaging.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/messaging.py), [execution.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/execution.py), [test_contract.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/tests/test_contract.py), [test_m11.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/tests/test_m11.py), [m11-swap-demo.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m1_2/m11-swap-demo.json), [same-artifact.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/evidence/m4/final/same-artifact.json).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `Agent messaging · M5 source bfb0ec8`.

## 04 — Responsibility, state and scope

State ownership is the key contract, not the file layout. Inbox + ordering: Durable accepted message, scope/route and committed local sequence. Acknowledgment replay: Recipient acknowledgment identity and stable response. Result payloads and jobs: AtomStorage owns bytes; Execution owns terminal job/outbox state. Exactly-once delivery: Poll may repeat; no global ordering or guaranteed remote arrival. Explicit compatibility: durable-mailbox/2 · explicit legacy profile retained · wire 1.0.0. Limits: Finite configured unacknowledged-route capacity; replay records retained for journal lifetime.

Evidence and implementation: [messaging.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/messaging.py), [execution.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/execution.py), [test_contract.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/tests/test_contract.py), [test_m11.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/tests/test_m11.py), [m11-swap-demo.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m1_2/m11-swap-demo.json), [same-artifact.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/evidence/m4/final/same-artifact.json).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `Agent messaging · M5 source bfb0ec8`.

## 05 — The executable surface

Walk the contract from inputs to effects. send: Validate reference and registered routes; accept; Acceptance reports delivery not-observed. poll: Return oldest unacknowledged message for owner; Repeats until acknowledged. ack: Commit recipient acknowledgment and replay; Current route ownership still checked. Trusted accept: CompletionDelivery.accept: execution-to-mailbox handoff; Return after mailbox commit; not public dispatch. Operation groups on this slide are not a new coverage denominator. The evidence ledger distinguishes new operations from inherited dependencies. Supporting internal helpers are labelled as seams and are not advertised remote services.

Evidence and implementation: [messaging.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/messaging.py), [execution.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/execution.py), [test_contract.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/tests/test_contract.py), [test_m11.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/tests/test_m11.py), [m11-swap-demo.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m1_2/m11-swap-demo.json), [same-artifact.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/evidence/m4/final/same-artifact.json).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `Agent messaging · M5 source bfb0ec8`.

## 06 — A worked example through the boundary

Use this example to connect the responsibility to observable behavior. 1. Finish job: Execution has a durable completion outbox row. 2. Accept mailbox: Mailbox commits that completion independently. 3. Lose marking: Worker dies before marking its outbox sent. 4. Retry handoff: Same message is accepted once; recipient polls and acks. Evidence classification: REAL owner persistence + separate worker process · protocol counterparty is a fixture. Do not infer performance, broad production readiness or extra runtime integrations from this example.

Evidence and implementation: [messaging.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/messaging.py), [execution.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/execution.py), [test_contract.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/tests/test_contract.py), [test_m11.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/tests/test_m11.py), [m11-swap-demo.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m1_2/m11-swap-demo.json), [same-artifact.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/evidence/m4/final/same-artifact.json).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `Agent messaging · M5 source bfb0ec8`.

## 07 — Four invariants to preserve

These invariants should survive provider substitution and future optimization. Acceptance before reply: A success receipt follows the mailbox commit. Repeat until acknowledgment: Poll observation does not consume the delivery. Scoped recipient control: Only the registered owner can poll/ack its route. Semantic replay: Same delivery identity/body replays; changed meaning conflicts. The supporting tests and runtime evidence are in the linked sources; this slide does not claim a formal proof or a production security audit.

Evidence and implementation: [messaging.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/messaging.py), [execution.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/execution.py), [test_contract.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/tests/test_contract.py), [test_m11.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/tests/test_m11.py), [m11-swap-demo.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m1_2/m11-swap-demo.json), [same-artifact.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/evidence/m4/final/same-artifact.json).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `Agent messaging · M5 source bfb0ec8`.

## 08 — Failure is part of the interface

State the owner boundary before the recovery claim. Mailbox accepted; outbox not marked: Execution retries trusted accept with the same identity. No duplicate logical message. Acknowledgment reply lost: Retry recovers durable acknowledgment after reauthorization. No resurrection of consumed delivery. Full / revoked reply route: Outbox remains pending until a valid retry can succeed. No dropped completion. A fixture can position the failure while a real process is killed. Local replay semantics do not imply exactly-once physical execution, a distributed transaction, or global failover. For pure/static modules the relevant failure is selection/refusal, not invented journal recovery.

Evidence and implementation: [messaging.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/messaging.py), [execution.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/execution.py), [test_contract.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/tests/test_contract.py), [test_m11.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/tests/test_m11.py), [m11-swap-demo.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m1_2/m11-swap-demo.json), [same-artifact.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/evidence/m4/final/same-artifact.json).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `Agent messaging · M5 source bfb0ec8`.

## 09 — Measurements and benchmark gaps

Read every number with its unit and source class. 2 Messages in the preserved inspect workflow: One reference share + one completion. 0 Pending outbox after recovery demos: Observed logical handoff completion. FIFO Committed inbox sequence per route: Ordering contract, not global message order. These are delivery/replay observations from shared workflows. No isolated mailbox throughput, delivery p95, multi-consumer scale or network-loss benchmark is recorded. Proposed: vary backlog, ack delay, replay ratio and route capacity; measure send/poll/ack p50/p95, backlog age and duplicate physical deliveries under fixed semantics. No new benchmark is executed for this presentation. Do not compare overlapping suite times or use a one-run workflow measurement as a latency percentile.

Evidence and implementation: [messaging.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/messaging.py), [execution.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/execution.py), [test_contract.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/tests/test_contract.py), [test_m11.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/tests/test_m11.py), [m11-swap-demo.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m1_2/m11-swap-demo.json), [same-artifact.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/evidence/m4/final/same-artifact.json).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `Agent messaging · M5 source bfb0ec8`.

## 10 — Current state: what is real, what is not

Implemented local code is not automatically a production provider. Real: SQLite mailbox owner and actual native caller binding; real process restarts. Fixture: Protocol peer/counterparty, generated messages, local route policy and injected faults. Blocked or unsupported: No required current gate blocked; a full or revoked route intentionally delays completion. Unrun: Two production agents, remote brokers, distributed ordering, power loss and general messaging federation. All required M5 gates passed in the recorded final run, including legacy M1–M4 behavior; this presentation does not rerun those integrations. Human maintainers remain unassigned.

Evidence and implementation: [messaging.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/messaging.py), [execution.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/execution.py), [test_contract.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/tests/test_contract.py), [test_m11.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/tests/test_m11.py), [m11-swap-demo.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m1_2/m11-swap-demo.json), [same-artifact.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/evidence/m4/final/same-artifact.json).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `Agent messaging · M5 source bfb0ec8`.

## 11 — Future directions need acceptance criteria

Discuss future work as conditional engineering proposals. Measure backlog and replay costs requires Rate-controlled sends/acks with fixed capacity; success means No loss while reporting tail latency and queue age. Qualify a remote transport requires Preserve authority, acceptance and acknowledgment meanings; success means Failure injection across actual network partitions. Specify retention/compaction requires Replay lifetime and acknowledgment contract first; success means No duplicate acceptance after tombstone expiry. No new cognition, scheduler, migration or chain capability is implemented by this series. Any changed numerical semantics, placement or replay lifetime requires separate design and verification rather than a presentation claim.

Evidence and implementation: [messaging.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/messaging.py), [execution.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/execution.py), [test_contract.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/tests/test_contract.py), [test_m11.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/tests/test_m11.py), [m11-swap-demo.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m1_2/m11-swap-demo.json), [same-artifact.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/evidence/m4/final/same-artifact.json).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `Agent messaging · M5 source bfb0ec8`.

## 12 — Evidence you can inspect and reproduce

Conclude with: A durable receipt must say which delivery fact was observed. The reproduction entrypoint is uv run --python 3.11 --locked python scripts/verify_m11.py. Runs the provider/binding conformance matrix and real DeTTa gate when available. Fixture-only is a distinct mode; it is not native Hive proof. Build/export checks for this series are separate from runtime tests. Exact upstream pins remain in integration/hive/sources.json, integration/pln/sources.json, integration/pln/deduction-sources.json and the M4/M5 source manifests. Commands use fresh output/state; raw provider environments, credentials, journals and private IDs should not be published.

Evidence and implementation: [messaging.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/messaging.py), [execution.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/execution.py), [test_contract.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/tests/test_contract.py), [test_m11.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/tests/test_m11.py), [m11-swap-demo.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m1_2/m11-swap-demo.json), [same-artifact.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/evidence/m4/final/same-artifact.json).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `Agent messaging · M5 source bfb0ec8`.
