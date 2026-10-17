# DA storage — speaker notes

Implementation baseline: `bfb0ec8856c932dc2bcbc05b8949c957da8d72cd`.
Evidence snapshot: `3dc6c1146601a0d0aa8785e61884970ec84a57c6`.
Suggested delivery: 12–15 minutes for 12 slides; follow the notes for technical discussion.
Source snapshot: 494df69a1ac401c3d3b2cf79dbfde07f74b5e277. Current M5 regressions and historical observations retain distinct source labels. No runtime or performance tests are rerun by this presentation build. Proposed benchmarks/future directions are unrun.

## 01 — DA storage

Open with the analogy, then state the technical responsibility: Opaque persistence, retrieval and local availability through the DeTTa DA and FileStorage libraries. Every higher-level receipt depends on retrieving the same bytes. Keeping domain semantics outside DA makes the backend replaceable. Do not treat the analogy as an additional experiment. This is a standalone talk about one responsibility, not a claim that every module is a separate service or repository.

Evidence and implementation: [detta.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/adapters/detta.py), [main.rs](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/adapters/detta/src/main.rs), [m1_2-evidence.md](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/m1_2-evidence.md), [m1_2-verification.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/evidence/m5/legacy/m1_2-verification.json).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `DA storage · M5 source bfb0ec8`.

## 02 — One module in a system of fifteen

Locate DA storage in the bounded fifteen-family inventory. The grey groups are explanatory categories, not deployment units. RevisionMath, the evidence relay, native plugins and transport bindings are supporting seams rather than additional module families. Registry and Resolver are separate responsibilities even though both are implemented in registry.py. Fifteen represented families is not full Omega requirements coverage. The application owner calls the opaque Storage port. The external Rust adapter translates it to DeTTa; Hive and cognition are upstream consumers, not DA dependencies.

Evidence and implementation: [detta.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/adapters/detta.py), [main.rs](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/adapters/detta/src/main.rs), [m1_2-evidence.md](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/m1_2-evidence.md), [m1_2-verification.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/evidence/m5/legacy/m1_2-verification.json).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `DA storage · M5 source bfb0ec8`.

## 03 — Dependencies explain the boundary

The application owner calls the opaque Storage port. The external Rust adapter translates it to DeTTa; Hive and cognition are upstream consumers, not DA dependencies. The left node is a caller or caller class; the right nodes distinguish foreign ports, pure helpers, local state and runtime internals. There is no implied shared transaction. No episode identity, belief, attention, job or query semantics.

Evidence and implementation: [detta.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/adapters/detta.py), [main.rs](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/adapters/detta/src/main.rs), [m1_2-evidence.md](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/m1_2-evidence.md), [m1_2-verification.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/evidence/m5/legacy/m1_2-verification.json).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `DA storage · M5 source bfb0ec8`.

## 04 — Responsibility, state and scope

State ownership is the key contract, not the file layout. Payload and share files: Local encoded bytes and reconstruction metadata. Persistence receipts: Evidence of the selected local storage behavior. Application interpretation: No episode identity, belief, attention, job or query semantics. Distributed custody: No validator network, indefinite retention or global availability claim. Explicit compatibility: opaque-local-rs/1 · receipt detta-local-rs/1. Limits: Local files and trusted host; recovery does not imply distributed durability.

Evidence and implementation: [detta.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/adapters/detta.py), [main.rs](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/adapters/detta/src/main.rs), [m1_2-evidence.md](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/m1_2-evidence.md), [m1_2-verification.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/evidence/m5/legacy/m1_2-verification.json).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `DA storage · M5 source bfb0ec8`.

## 05 — The executable surface

Walk the contract from inputs to effects. put: Persist opaque bytes at generic coordinates; Returns a provider receipt. get: Recover and verify the requested bytes; Unavailable/corrupt data fails explicitly. availability: Describe observed local availability; Does not prove future retention. Operation groups on this slide are not a new coverage denominator. The evidence ledger distinguishes new operations from inherited dependencies. Supporting internal helpers are labelled as seams and are not advertised remote services.

Evidence and implementation: [detta.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/adapters/detta.py), [main.rs](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/adapters/detta/src/main.rs), [m1_2-evidence.md](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/m1_2-evidence.md), [m1_2-verification.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/evidence/m5/legacy/m1_2-verification.json).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `DA storage · M5 source bfb0ec8`.

## 06 — A worked example through the boundary

Use this example to connect the responsibility to observable behavior. 1. Write: Store generated bytes via the real adapter. 2. Remove: Delete the cached payload and two erasure shares. 3. Recover: Reconstruct identical bytes from four remaining shares. 4. Refuse: With a third share missing, report unavailable. Evidence classification: REAL LOCAL PROVIDER · generated payload and injected missing files. Do not infer performance, broad production readiness or extra runtime integrations from this example.

Evidence and implementation: [detta.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/adapters/detta.py), [main.rs](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/adapters/detta/src/main.rs), [m1_2-evidence.md](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/m1_2-evidence.md), [m1_2-verification.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/evidence/m5/legacy/m1_2-verification.json).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `DA storage · M5 source bfb0ec8`.

## 07 — Four invariants to preserve

These invariants should survive provider substitution and future optimization. Opaque boundary: No domain identifiers or numerical meaning enter the DA core. Exact bytes: Successful retrieval must match the committed payload identity. Honest availability: Insufficient reconstruction material is not a successful read. Explicit evidence: A local restart receipt never becomes a custody certificate. The supporting tests and runtime evidence are in the linked sources; this slide does not claim a formal proof or a production security audit.

Evidence and implementation: [detta.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/adapters/detta.py), [main.rs](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/adapters/detta/src/main.rs), [m1_2-evidence.md](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/m1_2-evidence.md), [m1_2-verification.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/evidence/m5/legacy/m1_2-verification.json).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `DA storage · M5 source bfb0ec8`.

## 08 — Failure is part of the interface

State the owner boundary before the recovery claim. Missing cache + two shares: Four of six shares recover the exact payload. Reconstruction test. Three missing shares / corruption: Fail explicitly; do not return fabricated bytes. Negative storage test. Process restart: Reopen local files under the same profile. Intact-file scope only. A fixture can position the failure while a real process is killed. Local replay semantics do not imply exactly-once physical execution, a distributed transaction, or global failover. For pure/static modules the relevant failure is selection/refusal, not invented journal recovery.

Evidence and implementation: [detta.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/adapters/detta.py), [main.rs](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/adapters/detta/src/main.rs), [m1_2-evidence.md](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/m1_2-evidence.md), [m1_2-verification.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/evidence/m5/legacy/m1_2-verification.json).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `DA storage · M5 source bfb0ec8`.

## 09 — Measurements and benchmark gaps

Read every number with its unit and source class. 4 + 2 Data + parity shares: Configured erasure profile, not measured throughput. 2 lost Shares recovered without cache: Observed reconstruction boundary. 62 + 38 Upstream library tests: Clean DeTTa regression; overlapping with larger runs. No isolated read/write latency, throughput or durability benchmark is recorded. Share counts are a conformance result. Suite counts measure test execution, not performance. Proposed: vary payload size, missing-share count and cold/warm cache; report read/write p50/p95, bytes stored and reconstruction CPU on fixed hardware. No new benchmark is executed for this presentation. Do not compare overlapping suite times or use a one-run workflow measurement as a latency percentile.

Evidence and implementation: [detta.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/adapters/detta.py), [main.rs](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/adapters/detta/src/main.rs), [m1_2-evidence.md](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/m1_2-evidence.md), [m1_2-verification.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/evidence/m5/legacy/m1_2-verification.json).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `DA storage · M5 source bfb0ec8`.

## 10 — Current state: what is real, what is not

Implemented local code is not automatically a production provider. Real: Pinned DeTTa DA/FileStorage and external adapter run locally. Fixture: Generated payloads, deleted shares, corruption and injected process faults. Blocked or unsupported: No required current local gate blocked; historical dirty-source additions are outside the clean baseline. Unrun: Power loss, distributed custody, remote replicas, long-term retention and production load. All required M5 gates passed in the recorded final run, including legacy M1–M4 behavior; this presentation does not rerun those integrations. Human maintainers remain unassigned.

Evidence and implementation: [detta.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/adapters/detta.py), [main.rs](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/adapters/detta/src/main.rs), [m1_2-evidence.md](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/m1_2-evidence.md), [m1_2-verification.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/evidence/m5/legacy/m1_2-verification.json).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `DA storage · M5 source bfb0ec8`.

## 11 — Future directions need acceptance criteria

Discuss future work as conditional engineering proposals. Measure storage tradeoffs requires Controlled size/cache/failure matrix; success means Latency distribution and amplification per payload. Specify retention explicitly requires New custody/retention contract and evidence; success means Expired retention cannot masquerade as availability. Explore another DA provider requires Same opaque port and explicit profile; success means Equivalent byte/integrity conformance before adoption. No new cognition, scheduler, migration or chain capability is implemented by this series. Any changed numerical semantics, placement or replay lifetime requires separate design and verification rather than a presentation claim.

Evidence and implementation: [detta.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/adapters/detta.py), [main.rs](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/adapters/detta/src/main.rs), [m1_2-evidence.md](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/m1_2-evidence.md), [m1_2-verification.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/evidence/m5/legacy/m1_2-verification.json).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `DA storage · M5 source bfb0ec8`.

## 12 — Evidence you can inspect and reproduce

Conclude with: Availability has a failure model. Preserve it in every receipt. The reproduction entrypoint is uv run --python 3.11 --locked python scripts/verify_m11.py. Requires the pinned clean DeTTa source and built adapter; this is a suite command, not a microbenchmark. Build/export checks for this series are separate from runtime tests. Exact upstream pins remain in integration/hive/sources.json, integration/pln/sources.json, integration/pln/deduction-sources.json and the M4/M5 source manifests. Commands use fresh output/state; raw provider environments, credentials, journals and private IDs should not be published.

Evidence and implementation: [detta.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/adapters/detta.py), [main.rs](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/adapters/detta/src/main.rs), [m1_2-evidence.md](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/m1_2-evidence.md), [m1_2-verification.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/evidence/m5/legacy/m1_2-verification.json).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `DA storage · M5 source bfb0ec8`.
