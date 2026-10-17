# PLNKernel — speaker notes

Implementation baseline: `bfb0ec8856c932dc2bcbc05b8949c957da8d72cd`.
Evidence snapshot: `3dc6c1146601a0d0aa8785e61884970ec84a57c6`.
Suggested delivery: 12–15 minutes for 12 slides; follow the notes for technical discussion.
Source snapshot: 494df69a1ac401c3d3b2cf79dbfde07f74b5e277. Current M5 regressions and historical observations retain distinct source labels. No runtime or performance tests are rerun by this presentation build. Proposed benchmarks/future directions are unrun.

## 01 — PLNKernel

Open with the analogy, then state the technical responsibility: Apply the existing guarded five-premise grounded deduction implementation under exact source/runtime profiles. Separating numerical proposals from admission prevents a runtime or formula replacement from silently acquiring authority over beliefs, budgets or search. Do not treat the analogy as an additional experiment. This is a standalone talk about one responsibility, not a claim that every module is a separate service or repository.

Evidence and implementation: [pln_deduction.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/adapters/pln_deduction.py), [test_deduction.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/integration/pln/test_deduction.py), [deduction-sources.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/integration/pln/deduction-sources.json), [m3-evidence.md](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/m3-evidence.md), [verification.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m3/final/verification.json).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `PLNKernel · M5 source bfb0ec8`.

## 02 — One module in a system of fifteen

Locate PLNKernel in the bounded fifteen-family inventory. The grey groups are explanatory categories, not deployment units. RevisionMath, the evidence relay, native plugins and transport bindings are supporting seams rather than additional module families. Registry and Resolver are separate responsibilities even though both are implemented in registry.py. Fifteen represented families is not full Omega requirements coverage. PLNKernel has no domain journal, AtomStorage, Attention, C1 or scheduler dependency. RevisionMath is a separate pure revision port; neither is a general inference controller.

Evidence and implementation: [pln_deduction.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/adapters/pln_deduction.py), [test_deduction.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/integration/pln/test_deduction.py), [deduction-sources.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/integration/pln/deduction-sources.json), [m3-evidence.md](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/m3-evidence.md), [verification.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m3/final/verification.json).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `PLNKernel · M5 source bfb0ec8`.

## 03 — Dependencies explain the boundary

PLNKernel has no domain journal, AtomStorage, Attention, C1 or scheduler dependency. RevisionMath is a separate pure revision port; neither is a general inference controller. The left node is a caller or caller class; the right nodes distinguish foreign ports, pure helpers, local state and runtime internals. There is no implied shared transaction. C2 validates exact claim/lineage and commits the result.

Evidence and implementation: [pln_deduction.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/adapters/pln_deduction.py), [test_deduction.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/integration/pln/test_deduction.py), [deduction-sources.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/integration/pln/deduction-sources.json), [m3-evidence.md](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/m3-evidence.md), [verification.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m3/final/verification.json).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `PLNKernel · M5 source bfb0ec8`.

## 04 — Responsibility, state and scope

State ownership is the key contract, not the file layout. No mutable domain state: A pure proposal interface; selected runtime identity is explicit. Guarded execution boundary: Validate inputs, source/profile compatibility and returned proposal. Admission and provenance authority: C2 validates exact claim/lineage and commits the result. Search and work budgets: No PLN.Query/Derive loop, agenda, task generation or attention mutation. Explicit compatibility: grounded-five-premise-deduction/1 · fusion-petta-swi-10.1.14-deduction/1. Limits: One bounded grounded rule; heuristic truth model; no belief, budget or agenda state.

Evidence and implementation: [pln_deduction.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/adapters/pln_deduction.py), [test_deduction.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/integration/pln/test_deduction.py), [deduction-sources.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/integration/pln/deduction-sources.json), [m3-evidence.md](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/m3-evidence.md), [verification.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m3/final/verification.json).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `PLNKernel · M5 source bfb0ec8`.

## 05 — The executable surface

Walk the contract from inputs to effects. profile: Identify model, rule, runtime and pinned sources; Compatibility is explicit before use. applyRule: Evaluate P, Q, R, P⇒Q, Q⇒R; One grounded proposal for P⇒R. RevisionMath.revise: Separate narrow revision dependency; Not an extra kernel method or general inference loop. Operation groups on this slide are not a new coverage denominator. The evidence ledger distinguishes new operations from inherited dependencies. Supporting internal helpers are labelled as seams and are not advertised remote services.

Evidence and implementation: [pln_deduction.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/adapters/pln_deduction.py), [test_deduction.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/integration/pln/test_deduction.py), [deduction-sources.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/integration/pln/deduction-sources.json), [m3-evidence.md](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/m3-evidence.md), [verification.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m3/final/verification.json).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `PLNKernel · M5 source bfb0ec8`.

## 06 — A worked example through the boundary

Use this example to connect the responsibility to observable behavior. 1. Bind premises: Exact historical supports for five grounded roles. 2. Validate: Check domains, bindings and probability consistency. 3. Execute native: Run unchanged guarded Truth_Deduction. 4. Return proposal: C2 rechecks authority and decides admission. Evidence classification: REAL native PeTTa / PLN · generated exact premises; no replacement mathematics. Do not infer performance, broad production readiness or extra runtime integrations from this example.

Evidence and implementation: [pln_deduction.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/adapters/pln_deduction.py), [test_deduction.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/integration/pln/test_deduction.py), [deduction-sources.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/integration/pln/deduction-sources.json), [m3-evidence.md](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/m3-evidence.md), [verification.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m3/final/verification.json).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `PLNKernel · M5 source bfb0ec8`.

## 07 — Four invariants to preserve

These invariants should survive provider substitution and future optimization. Pinned mathematics: No alternative formula is substituted to obtain a desired result. Exact premise vector: Historical support identities are not replaced by latest beliefs. Refuse invalid domains: Nonfinite or inconsistent inputs fail guarded checks. No owner writes: A successful formula result alone changes no belief or attention state. The supporting tests and runtime evidence are in the linked sources; this slide does not claim a formal proof or a production security audit.

Evidence and implementation: [pln_deduction.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/adapters/pln_deduction.py), [test_deduction.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/integration/pln/test_deduction.py), [deduction-sources.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/integration/pln/deduction-sources.json), [m3-evidence.md](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/m3-evidence.md), [verification.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m3/final/verification.json).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `PLNKernel · M5 source bfb0ec8`.

## 08 — Failure is part of the interface

State the owner boundary before the recovery claim. Native process unavailable: Return explicit unavailable/failed attempt semantics. No fixture fallback for real gate. Crash around formula return: C2/C4 journals govern recovery and spent attempts. Kernel is not the recovery owner. Source/runtime mismatch: Reject incompatible selection before admission. Historical SWI 10.0.1 is unrun. A fixture can position the failure while a real process is killed. Local replay semantics do not imply exactly-once physical execution, a distributed transaction, or global failover. For pure/static modules the relevant failure is selection/refusal, not invented journal recovery.

Evidence and implementation: [pln_deduction.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/adapters/pln_deduction.py), [test_deduction.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/integration/pln/test_deduction.py), [deduction-sources.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/integration/pln/deduction-sources.json), [m3-evidence.md](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/m3-evidence.md), [verification.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m3/final/verification.json).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `PLNKernel · M5 source bfb0ec8`.

## 09 — Measurements and benchmark gaps

Read every number with its unit and source class. 5 → 1 Premises → grounded proposal: One rule, not general inference. 0.68 / 0.3136 Recorded deduction strength / confidence: Generated golden; tolerance 1e−12. 0 Mutable domain owners in kernel: Architectural invariant, not performance. The numerical golden checks implementation agreement, not probabilistic calibration or theorem validity. No isolated native-call latency or large-rule benchmark is recorded. Proposed: separate process startup from warm native calls; fix exact valid vectors and refusal cases; report p50/p95, guard cost and timeout behavior without changing the formula. No new benchmark is executed for this presentation. Do not compare overlapping suite times or use a one-run workflow measurement as a latency percentile.

Evidence and implementation: [pln_deduction.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/adapters/pln_deduction.py), [test_deduction.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/integration/pln/test_deduction.py), [deduction-sources.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/integration/pln/deduction-sources.json), [m3-evidence.md](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/m3-evidence.md), [verification.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m3/final/verification.json).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `PLNKernel · M5 source bfb0ec8`.

## 10 — Current state: what is real, what is not

Implemented local code is not automatically a production provider. Real: Pinned Reachability, PLN, PeTTa, SWI 10.1.14 and Janus execute the native formula. Fixture: Generated premise vectors and independent expected numerical goldens. Blocked or unsupported: No required supported gate blocked; historical SWI 10.0.1 compatibility remains unrun. Unrun: General rule search, calibration, broad rule coverage and cross-runtime numerical equivalence. All required M5 gates passed in the recorded final run, including legacy M1–M4 behavior; this presentation does not rerun those integrations. Human maintainers remain unassigned.

Evidence and implementation: [pln_deduction.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/adapters/pln_deduction.py), [test_deduction.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/integration/pln/test_deduction.py), [deduction-sources.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/integration/pln/deduction-sources.json), [m3-evidence.md](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/m3-evidence.md), [verification.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m3/final/verification.json).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `PLNKernel · M5 source bfb0ec8`.

## 11 — Future directions need acceptance criteria

Discuss future work as conditional engineering proposals. Measure the runtime boundary requires Warm/cold fixed-vector experiments; success means Separate startup, guards and native evaluation. Qualify a new runtime pin requires Golden, refusal and source compatibility matrix; success means No silent numerical or exception changes. Add another rule deliberately requires Explicit rule profile and lineage/admission review; success means Each new rule has independent goldens and refusal tests. No new cognition, scheduler, migration or chain capability is implemented by this series. Any changed numerical semantics, placement or replay lifetime requires separate design and verification rather than a presentation claim.

Evidence and implementation: [pln_deduction.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/adapters/pln_deduction.py), [test_deduction.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/integration/pln/test_deduction.py), [deduction-sources.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/integration/pln/deduction-sources.json), [m3-evidence.md](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/m3-evidence.md), [verification.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m3/final/verification.json).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `PLNKernel · M5 source bfb0ec8`.

## 12 — Evidence you can inspect and reproduce

Conclude with: Reusing mathematics requires preserving its assumptions and boundary. The reproduction entrypoint is uv run --python 3.11 --locked python scripts/verify_m3.py <env> --output <fresh>. Build pinned providers with build_m3.py first; use a fresh source checkout and explicit runtime selection. The wrapper includes both guard and actual-native suites. Build/export checks for this series are separate from runtime tests. Exact upstream pins remain in integration/hive/sources.json, integration/pln/sources.json, integration/pln/deduction-sources.json and the M4/M5 source manifests. Commands use fresh output/state; raw provider environments, credentials, journals and private IDs should not be published.

Evidence and implementation: [pln_deduction.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/adapters/pln_deduction.py), [test_deduction.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/integration/pln/test_deduction.py), [deduction-sources.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/integration/pln/deduction-sources.json), [m3-evidence.md](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/m3-evidence.md), [verification.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m3/final/verification.json).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `PLNKernel · M5 source bfb0ec8`.
