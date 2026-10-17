# Attention · C3 — speaker notes

Implementation baseline: `bfb0ec8856c932dc2bcbc05b8949c957da8d72cd`.
Evidence snapshot: `3dc6c1146601a0d0aa8785e61884970ec84a57c6`.
Suggested delivery: 12–15 minutes for 12 slides; follow the notes for technical discussion.
Source snapshot: 494df69a1ac401c3d3b2cf79dbfde07f74b5e277. Current M5 regressions and historical observations retain distinct source labels. No runtime or performance tests are rerun by this presentation build. Proposed benchmarks/future directions are unrun.

## 01 — Attention · C3

Open with the analogy, then state the technical responsibility: Own bounded integer short-term importance, explicit logical time and causal feedback receipts/retirement. Limited work budgets make ordering observable. Keeping attention independent allows policy/provider experiments without changing belief mathematics or task admission. Do not treat the analogy as an additional experiment. This is a standalone talk about one responsibility, not a claim that every module is a separate service or repository.

Evidence and implementation: [attention.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/attention.py), [attention_contracts.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/attention_contracts.py), [fixture_attention.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/adapters/fixture_attention.py), [test_m3_1_attention.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/tests/test_m3_1_attention.py), [comparison.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m3/final/comparison.json), [verification.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m3_1/final/verification.json).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `Attention · C3 · M5 source bfb0ec8`.

## 02 — One module in a system of fifteen

Locate Attention · C3 in the bounded fifteen-family inventory. The grey groups are explanatory categories, not deployment units. RevisionMath, the evidence relay, native plugins and transport bindings are supporting seams rather than additional module families. Registry and Resolver are separate responsibilities even though both are implemented in registry.py. Fifteen represented families is not full Omega requirements coverage. Attention has no PLN, AtomStorage/DA, Hive or C1/C2 dependency. It ranks only the eligible targets supplied by a consumer, with explicit policy/profile identity.

Evidence and implementation: [attention.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/attention.py), [attention_contracts.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/attention_contracts.py), [fixture_attention.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/adapters/fixture_attention.py), [test_m3_1_attention.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/tests/test_m3_1_attention.py), [comparison.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m3/final/comparison.json), [verification.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m3_1/final/verification.json).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `Attention · C3 · M5 source bfb0ec8`.

## 03 — Dependencies explain the boundary

Attention has no PLN, AtomStorage/DA, Hive or C1/C2 dependency. It ranks only the eligible targets supplied by a consumer, with explicit policy/profile identity. The left node is a caller or caller class; the right nodes distinguish foreign ports, pure helpers, local state and runtime internals. There is no implied shared transaction. STI is not belief confidence and does not alter formula inputs.

Evidence and implementation: [attention.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/attention.py), [attention_contracts.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/attention_contracts.py), [fixture_attention.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/adapters/fixture_attention.py), [test_m3_1_attention.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/tests/test_m3_1_attention.py), [comparison.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m3/final/comparison.json), [verification.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m3_1/final/verification.json).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `Attention · C3 · M5 source bfb0ec8`.

## 04 — Responsibility, state and scope

State ownership is the key contract, not the file layout. Priority and logical clock: STI per target/context, revision and generation watermark. Causal outcome ledger: Command replay, feedback application and no-credit retirement. Truth values: STI is not belief confidence and does not alter formula inputs. Cognition/search: No task creation, ECAN, LTI, wages/funds or hidden inference dependency. Explicit compatibility: sti-additive-linear-decay/1; fresh closure profile sti-additive-linear-decay-closure/1. Limits: Default 16 targets/context, 8 contexts; finite cause/command capacity; explicit logical steps.

Evidence and implementation: [attention.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/attention.py), [attention_contracts.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/attention_contracts.py), [fixture_attention.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/adapters/fixture_attention.py), [test_m3_1_attention.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/tests/test_m3_1_attention.py), [comparison.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m3/final/comparison.json), [verification.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m3_1/final/verification.json).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `Attention · C3 · M5 source bfb0ec8`.

## 05 — The executable surface

Walk the contract from inputs to effects. submitStimulus / readAttention: Ingress plus explicit read; Reads do not allocate or decay state. select: Rank positive eligible STI; deterministic tie-break; No discovery of new tasks. advance: Explicit expected-step logical decay; Stale clocks fail; replay does not retime. submitFeedback / resolveFeedback: Apply causal credit or account for prior outcome; Closure cannot newly apply eligible feedback. Operation groups on this slide are not a new coverage denominator. The evidence ledger distinguishes new operations from inherited dependencies. Supporting internal helpers are labelled as seams and are not advertised remote services.

Evidence and implementation: [attention.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/attention.py), [attention_contracts.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/attention_contracts.py), [fixture_attention.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/adapters/fixture_attention.py), [test_m3_1_attention.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/tests/test_m3_1_attention.py), [comparison.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m3/final/comparison.json), [verification.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m3_1/final/verification.json).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `Attention · C3 · M5 source bfb0ec8`.

## 06 — A worked example through the boundary

Use this example to connect the responsibility to observable behavior. 1. Prefer B: Scores A=10, B=20; one attempt available. 2. Select: B runs first; C2 admits one conclusion. 3. Credit once: C3 records one causal feedback outcome. 4. Replay / swap: Both providers retain outcome; no extra native call. Evidence classification: HISTORICAL M3 CONTROLLED COMPARISON · SQLite + independent file fixture. Do not infer performance, broad production readiness or extra runtime integrations from this example.

Evidence and implementation: [attention.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/attention.py), [attention_contracts.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/attention_contracts.py), [fixture_attention.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/adapters/fixture_attention.py), [test_m3_1_attention.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/tests/test_m3_1_attention.py), [comparison.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m3/final/comparison.json), [verification.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m3_1/final/verification.json).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `Attention · C3 · M5 source bfb0ec8`.

## 07 — Four invariants to preserve

These invariants should survive provider substitution and future optimization. Policy is explicit: Integer saturation, context budget and decay are part of identity. Causal uniqueness: Replay cannot apply the same logical feedback twice. Strict logical time: Feedback is never retimed to make stale work admissible. One authoritative outcome: Application and retirement serialize at the attention owner. The supporting tests and runtime evidence are in the linked sources; this slide does not claim a formal proof or a production security audit.

Evidence and implementation: [attention.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/attention.py), [attention_contracts.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/attention_contracts.py), [fixture_attention.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/adapters/fixture_attention.py), [test_m3_1_attention.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/tests/test_m3_1_attention.py), [comparison.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m3/final/comparison.json), [verification.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m3_1/final/verification.json).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `Attention · C3 · M5 source bfb0ec8`.

## 08 — Failure is part of the interface

State the owner boundary before the recovery claim. Feedback applied; response lost: Return original application receipt even after expiry/decay. No second credit. Clock advanced / feedback expired: Retire without credit when permitted. Do not manufacture application. Eligible/unavailable or finite capacity: Resolution remains pending. Reconciliation is not a scheduler. A fixture can position the failure while a real process is killed. Local replay semantics do not imply exactly-once physical execution, a distributed transaction, or global failover. For pure/static modules the relevant failure is selection/refusal, not invented journal recovery.

Evidence and implementation: [attention.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/attention.py), [attention_contracts.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/attention_contracts.py), [fixture_attention.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/adapters/fixture_attention.py), [test_m3_1_attention.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/tests/test_m3_1_attention.py), [comparison.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m3/final/comparison.json), [verification.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m3_1/final/verification.json).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `Attention · C3 · M5 source bfb0ec8`.

## 09 — Measurements and benchmark gaps

Read every number with its unit and source class. 4 Controlled provider/preference runs: Same policy, tasks and one-attempt budget. 1 / 0 Native call / replay calls per run: Whole inference-step observation. 100 / 300 / 1 Target cap / context budget / decay: Default STI policy parameters. Historical full-step timings span 0.641150–0.744361 s, one observation per case. They include native inference and cannot rank attention-provider speed or cognitive quality. Proposed: fix eligible sets and causal schedule; vary target count, replay ratio and feedback contention. Measure select/update p50/p95 while checking exact ranking and once-only outcomes. No new benchmark is executed for this presentation. Do not compare overlapping suite times or use a one-run workflow measurement as a latency percentile.

Evidence and implementation: [attention.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/attention.py), [attention_contracts.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/attention_contracts.py), [fixture_attention.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/adapters/fixture_attention.py), [test_m3_1_attention.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/tests/test_m3_1_attention.py), [comparison.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m3/final/comparison.json), [verification.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m3_1/final/verification.json).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `Attention · C3 · M5 source bfb0ec8`.

## 10 — Current state: what is real, what is not

Implemented local code is not automatically a production provider. Real: Persistent SQLite reference STI provider; real native inference consumes its selections. Fixture: Independent atomic-file attention, generated tasks, grants and deterministic fault positions. Blocked or unsupported: No required supported gate blocked; old pending stores need their original profile. Unrun: ECAN/LTI, learned policy quality, production scaling and populated-state migration. All required M5 gates passed in the recorded final run, including legacy M1–M4 behavior; this presentation does not rerun those integrations. Human maintainers remain unassigned.

Evidence and implementation: [attention.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/attention.py), [attention_contracts.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/attention_contracts.py), [fixture_attention.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/adapters/fixture_attention.py), [test_m3_1_attention.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/tests/test_m3_1_attention.py), [comparison.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m3/final/comparison.json), [verification.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m3_1/final/verification.json).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `Attention · C3 · M5 source bfb0ec8`.

## 11 — Future directions need acceptance criteria

Discuss future work as conditional engineering proposals. Benchmark independent providers requires Identical logical schedule and durability semantics; success means Performance without ranking or receipt drift. Evaluate ranking usefulness requires Declared task objective and fixed inference budget; success means Outcome quality separate from conformance. Qualify another policy requires New profile with clock/causal semantics; success means No hidden adoption of LTI or coupled attention state. No new cognition, scheduler, migration or chain capability is implemented by this series. Any changed numerical semantics, placement or replay lifetime requires separate design and verification rather than a presentation claim.

Evidence and implementation: [attention.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/attention.py), [attention_contracts.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/attention_contracts.py), [fixture_attention.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/adapters/fixture_attention.py), [test_m3_1_attention.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/tests/test_m3_1_attention.py), [comparison.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m3/final/comparison.json), [verification.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m3_1/final/verification.json).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `Attention · C3 · M5 source bfb0ec8`.

## 12 — Evidence you can inspect and reproduce

Conclude with: Priority selects work; causal receipts prevent repeated reward. The reproduction entrypoint is uv run --python 3.11 --locked python scripts/verify_m3_1.py <env> --output <fresh>. Uses fresh closure-profile stores and both providers. Historical comparison retains its own source label; M5 reruns legacy behavior without adding attention work. Build/export checks for this series are separate from runtime tests. Exact upstream pins remain in integration/hive/sources.json, integration/pln/sources.json, integration/pln/deduction-sources.json and the M4/M5 source manifests. Commands use fresh output/state; raw provider environments, credentials, journals and private IDs should not be published.

Evidence and implementation: [attention.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/attention.py), [attention_contracts.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/attention_contracts.py), [fixture_attention.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/fusion/adapters/fixture_attention.py), [test_m3_1_attention.py](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/tests/test_m3_1_attention.py), [comparison.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m3/final/comparison.json), [verification.json](https://github.com/machieke/fusion-module-interfaces/blob/494df69a1ac401c3d3b2cf79dbfde07f74b5e277/docs/module-interfaces/evidence/m3_1/final/verification.json).

Scope: repository snapshot 494df69a1ac401c3d3b2cf79dbfde07f74b5e277; tested M5 runtime bfb0ec8856c932dc2bcbc05b8949c957da8d72cd. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. Future directions and proposed benchmark designs are not implemented work or measured results.

Source: `Attention · C3 · M5 source bfb0ec8`.
