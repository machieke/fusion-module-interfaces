# Codex handoff — Fusion M3: independent STI attention and one bounded PLN inference loop

## 1. Objective and stop boundary

Continue `machieke/fusion-module-interfaces` from the pushed M2 revision
`f0cee24`, or record its exact descendant, full SHA and relevant changes. Read
applicable `AGENTS.md`, the original architecture brief, M2 handoff, contracts,
ADRs, source locks and evidence before editing. Preserve unrelated worktrees.

**Objective:** implement C3 short-term attention and C4 bounded inference control,
using one grounded native PLN deduction rule and the existing private memory
owners. Demonstrate that attention changes which eligible task is selected, while
only the belief owner admits derived support and only Attention changes STI.
Prove an independent attention-provider replacement under the same declared
behavioral profile. Keep the actual Hive integration and M1/M2 regressions.

**Stop after M3.** No LTI, promotion, summarization, semantic parsing, variable
matching, general graph/query service, adaptive pressure-field research, complete
ECAN economics, new distributed scheduler, new transport, external tool effects,
chain work or live state migration. Do not call a toy score policy a full ECAN
implementation or a deterministic integration example an AGI benchmark result.

This is a proposed engineering increment, not a mathematical or product decision
already agreed by the meeting participants. The initial attention policy below
is explicitly a reference profile, not a claim of equivalence to classic ECAN,
fluid attention or smoothed-particle-hydrodynamics attention.

## 2. Review basis and baseline

The reviewer inspected commit-specific public source, owners, ports, native tests
and checked-in M2 evidence. The reviewer did **not independently execute** the
suites or inspect the private Hive dependency checkout. Verify findings locally.

The final comprehensive M2 run was recorded at clean detached
`d9e75773c34987d5791a9207190fcbf0a8c1fd7b`; `f0cee24` adds evidence/documentation,
not changes to that tested implementation. Historical passes are not new passes.
M2 records the original 90 conformance cases plus 16 M2 fixtures (106 discovered),
the separately exercised original 51-fixture subset, 8 upstream guard cases,
12 native-revision-suite cases, 6 recovery/privacy cases and 7 new Hive cases.
The 16 fixtures are also run separately; do not count them twice. Native-suite
malformed-output injections remain fixtures, not extra native formula executions.

Run the applicable M2 baseline before editing and again at completion. Preserve
separate real DeTTa, native PLN, native Hive and fixture classifications. Empty-cache
builds and chain remain NOT_RUN unless a separately authorized task executes them.
Observed durability remains same-host process restart with intact files.

### Source ledger

| Source | Reuse / inspect |
|---|---|
| `fusion/ports.py` | Specified `Attention`, `Stimulus`, `AttentionSnapshot`, `PLNKernel`, `Derivation`, `WorkBudget`, `InferenceControl`, `StepReceipt`. |
| `fusion/memory_types.py`, `memory_contracts.py` | Implemented C1/C2 v2 shapes and restrictive same-claim revision semantics. |
| `fusion/episodes.py`, `beliefs.py`, `evidence_relay.py` | Ownership, immutable revisions, exact semantic replay, CAS and separate commits. |
| `fusion/private.py`, registry/policy modules | Private composition, live authority, descriptor/profile binding. |
| `fusion/adapters/pln_revision.py`, `integration/pln/sources.json` | Source-checked reuse and revision-only runtime rebaseline. |
| `integration/pln/test_revision.py`, `test_recovery.py` | Native numerical oracles, guard cases, process-kill and privacy coverage. |
| `integration/hive/episode_program/`, `test_m2_integration.py` | Actual native private caller; preserve the existing action. |
| `docs/module-interfaces/m2-evidence.md`, `evidence/m2/final/` | Exact commands, source state, failures/corrections and bounded claims. |
| `scripts/build_m2.py`, `verify_m2.py` and existing runbook | Extend the reproducible build/test recipe, not another dependency framework. |
| Reachability `dd56f3f053ed90239de5377021a7d3b3fbf424ac`: `reachability/pln_adapter.py`, `ADAPTERS.md` | Existing guarded `DeductionRule`, `PLNAdapter.apply_rule`, ancestry and formula semantics. Attention adapters are described there as pending. |
| PLN `4405956947c4b53c7ff01bd565aa3b114bc970a1`: `lib_pln.metta` | Actual `Truth_Deduction` and its conditional-consistency checks. |

Keep Hive `34b0fb32ab3806e5609fc89bb7535518a35e1aea`, DeTTa
`272888f264dd2dde18b574cabb53c266b0dac2ec`, PeTTa
`ae66fa8e41dcd5539d614706bd4e5cfb34f9608d`, and the verified SWI 10.1.14 build
unless a concrete incompatibility requires an explicitly documented rebaseline.
Do not loosen the Reachability 10.0.1 lock or overwrite its historical evidence.

Meeting context: Kevin/Kabir 01:04:49–01:07:39 supports version-independent
contracts; AGI Benchmarks 00:11:14–00:12:40 establishes single-owner updates and
00:22:11–00:23:49 places STI and bounded inference after provenance/revision.
Neither meeting selected a numerical attention policy.

## 3. Responsibilities

| Module | Owns / does | Must not do |
|---|---|---|
| AtomStorage | Immutable, scoped private payloads and references. | Interpret rules, decide truth or own attention. |
| EpisodicMemory | Observation/action/result history and its delivery state. | Turn a reasoning result into a new independent observation. |
| BeliefRevision | Admitted observed and derived support, alternatives, immutable snapshots and decisions. | Invent evidence roots, schedule tasks or alter STI. |
| PLNKernel | Pure grounded-rule validation and numerical proposal generation. | Commit beliefs, choose an agenda, publish data or assert source independence. |
| Attention | STI, logical clock, stimulus deduplication, selection and policy-bound state. | Interpret claims, assign truth, read episode contents or require PLN/Hive. |
| InferenceControl | Bounded task selection, exact work intents, attempt budgets, progress and feedback delivery. | Implement PLN arithmetic, write foreign state or become a general agent scheduler. |
| Hive adapter | Native request translation and appropriately scoped presentation. | Become any of the owners above. |

Logical modules need not be separate processes. Foreign calls use declared ports;
concrete selection stays in composition. DA remains application-neutral. Private
claims, lineage, worksets, attention and reasoning traces stay on the private side.

## 4. Definition of ready: resolve these contract gaps first

Update the existing specification and ADRs, not a parallel design hierarchy.

1. **Attention context and selection snapshot.** Current `select` is scope-only.
   Specify isolation by scope and reasoning context, the eligible target set,
   policy parameters, deterministic ordering, logical step and state watermark.
   A response must identify the snapshot it ranked; no unstated globally atomic
   snapshot across attention and beliefs is promised.
2. **Executable work input.** `InferenceControl.step` currently carries only a
   mutation and budget. Bind it to a bounded immutable workset, context, exact rule
   profile, selected providers and semantic input. Do not hide the real task in
   process-global configuration or replace the operation with `execute(anything)`.
3. **Exact premises.** `PLNKernel.applyRule` needs a grounded rule instance and
   ordered support bindings, not just an algorithm name and whatever latest beliefs
   happen to be returned. Preserve an immutable vector of claim/context/revision/
   support IDs. Fusion has per-belief revisions, not one global knowledge revision.
4. **Derived admission.** M2 accepts occurrence evidence or a support already in
   the target ledger; it cannot yet admit a new cross-claim deduction. Add a narrow
   named admission operation to the same BeliefRevision owner. Do not forge an
   EpisodeEvent with a new source origin to get a deduction into the ledger.
5. **Support variants.** M2 validation permits observation leaves and two-premise
   same-claim `Truth_Revision`. Deduction needs five ordered cross-claim premises,
   ancestry, explicit rule assumptions and a different coverage interpretation.
   Use tagged, bounded variants with variant-specific validators, not relaxed
   arbitrary-length premises or arbitrary formula strings.
6. **Budgets and receipts.** Define attempted versus completed work, rejected tasks,
   native invocations, deduplicated admissions, feedback, remaining budget, pending
   state and terminal reasons. A timeout is not exhaustion of available knowledge.

Make version/profile choices explicit. Preserve existing M1 and M2 profiles and
replay behavior. Do not silently widen the `/revision/` runtime allowlist. New
profiles may use fresh private state; continue to test old state under its old
profile. A descriptor mismatch must not be bypassed to open an old journal.
There is no authorization to migrate populated journals in this task.

## 5. C3 — independently runnable STI attention

### 5.1 Reference policy, not an unsubstantiated ECAN port

First inspect any explicitly available attention implementation in the authorized
workspace. Reuse it only if its behavior and dependencies fit this bounded task.
Do not spend the increment surveying competing attention theories. The pinned
Reachability source is a PLN reuse candidate, not an already integrated ECAN.

Unless a suitable existing provider is identified and documented, implement this
proposed minimal `sti-additive-linear-decay/1` reference policy. It is an actual
persistent implementation of its own declared contract, not evidence of a full
classic ECAN implementation. Record the choice and parameters in an ADR.

Use exact nonnegative integer resource units, encoded as decimal strings at the
boundary. These are attention units, not probabilities. Freeze the maximum per
node S_max, total active budget B, decay d, maximum targets and maximum advances
in the policy identity; tests use small explicit parameters.

- A newly referenced target has zero STI. Ingress can request an explicit stipend;
  allocation is never an implicit side effect of reading or storing an atom.
- A stimulus of a units proposes delta = min(a, S_max - S_i). If adding delta
  exceeds B, reject the whole mutation without changing state. Otherwise apply
  delta and return the requested/applied amounts and saturation information.
- Advancing k logical steps applies S_i' = max(0, S_i - k*d) to every tracked
  target and advances the context clock atomically. Decay frees available budget.
  This is not a conservation-law claim or redistribution algorithm.
- Selection ranks eligible positive-STI targets by descending STI, then a canonical
  opaque-reference tie-break. Reads/select do not decay, reward or touch state.
- No negative stimuli, diffusion, Hebbian links, LTI, learned policy or automatic
  renormalization. Unsupported operations fail explicitly.

Bound all state and input collections. Explain behavior when capacity is full;
never silently evict a rewarded target or lose an acknowledged command.
Reference validation is syntactic/scope-aware: Attention need not load payloads.
Opaque test references work without AtomStorage, PLN, Hive or a graph service.

### 5.2 Logical order, authority and replay

Attention owns its journal, state revision and logical clock. Persist stimulus
application and replay response atomically. Bind semantic input to current caller,
scope/context, target, cause, generation, policy parameters and intended logical
step. A concurrent step advance conflicts with a stimulus intended for the old
step; replay of a successful command returns its original result after current
authorization rather than applying it at the new time.

Deduplicate a causal stimulus independently of its transport key. The same
feedback cause delivered under another request ID must not create another credit.
Changing the target/amount/body under an already bound causal identity conflicts.
Do not treat an unverified caller's `generation=0` as permission to reset feedback
limits. External generated ingress and controller feedback have distinct, explicit
authority and causal records. This is a trusted-local policy, not Sybil resistance.

### 5.3 Independent provider replacement

Implement or reuse a second independently implemented provider of the **same**
reference policy and guarantee profile. An atomic-file fixture is sufficient if
it actually meets the bounded restart semantics it advertises. It must not inherit
from the first owner, share its private tables/helpers or delegate to its owner
implementation. Shared DTOs/validators are fine; independently check transitions.

Run the unchanged consumer against both on fresh stores with identical stimuli,
logical steps and tasks. Require the same declared results, including tie-breaks,
replay and rejection behavior. Use a hostile proxy exposing only declared methods.
This proves substitution, not live migration or equivalence between unlike ECAN
algorithms. Alternative policies require their own profiles and later quality tests.

## 6. One pure native PLN deduction kernel

Reuse the pinned `PLNAdapter.apply_rule` and `DeductionRule(P,Q,R)`, preserving its
precondition checks, ancestry guard, numeric domain and proposal construction.
The ordered premises are P, Q, R, P=>Q, Q=>R; the conclusion is P=>R. This is a
single grounded schema, not a variable matcher or a two-premise rule that guesses
the missing marginals.

Make the mapping from private grounded claim records to proposition/implication
roles explicit and validated. The M2 revision adapter maps whole claims to opaque
proposition identities; that mapping alone cannot express this deduction pattern.
Never silently equate two claim references because their text looks similar.
The task manifest identifies the exact permitted role bindings and output claim.
A pre-created output claim atom has no truth merely because it exists.

Add a separately declared deduction runtime/profile using the verified native
SWI 10.1.14 build. Keep the revision-only profile's meaning intact. Reuse source
verification and invocation mechanics without copying the mathematics. Preserve
both the exact Python probability precheck and the upstream runtime consistency
check, including refusal when they disagree. Permit only the selected formula
and validated numeric literals; do not interpolate claim text into executable code.
Do not invoke `PLN.Derive`, `PLN.Query` or an upstream search loop.

Carry the real assumptions: upstream heuristic deduction and its Q>0.9999 branch.
Do not describe them as proven probabilistic entailment or calibrated uncertainty.
Overlapping premise lineage is not, by itself, a prohibition on deduction; preserve
its union so subsequent **revision** cannot count that source twice.

Use independent native oracles. A mathematical reference case is:

| Input | Strength | Confidence |
|---|---:|---:|
| P, Q and R, each | 1/2 | 4/5 |
| P=>Q and Q=>R, each | 4/5 | 7/10 |
| Expected P=>R | 17/25 = 0.68 | 196/625 = 0.3136 |

The expected pair is derived from the pinned formula, not a measured result in
this handoff. Execute the native formula and compare with a documented tolerance
for legal outputs only. Include infeasible conditionals, zero antecedents, the
near-one branch, wrong order/context/model, cycles, missing supports, malformed or
multiple output, timeout and source drift. The upstream `(stv 1 0)` failed-condition
fallback must never be admitted as a successful valid deduction.

## 7. Admit derivations without manufacturing observations

Prefer a new narrow `submitDerivation` operation on BeliefRevision that accepts
the exact grounded task/premise vector and invokes an injected PLNKernel itself.
The controller chooses work; this admission boundary reads authoritative premise
snapshots, calls the pure kernel outside its commit transaction and validates the
proposal before committing. It must not accept caller-supplied truth as trusted
just because the request names a valid formula or provider.

This placement makes the calculation-to-admission trust boundary explicit without
cryptographic proofs, foreign writes or a separate universal verifier service.
The kernel remains independently callable/testable as a pure proposal provider.
The controller never owns the mathematical result or the belief ledger.

Persist exact semantic attempt input before evaluation. Validate scope, context,
claim structures, immutable premise/support identities, source roots, selected
model/runtime and output role. If the upstream adapter requires one integer
knowledge_revision, document it as a local evaluation identifier and preserve the
actual premise revision vector separately; do not invent a global Fusion revision.

At commit, recheck current authority, output-belief CAS and the exact declared
snapshot policy. The initial policy may explicitly be 'derive from these immutable
historical snapshots'; then a later unrelated premise update does not rewrite the
request. Results must remain labelled as-of that vector, not as the latest global
belief. Any policy requiring current premises needs its own tested checks.

The committed derived support records:

- its deterministic logical identity, target claim/context and numeric profile;
- exact ordered premise claim/revision/support references and kernel identity;
- unioned source occurrence/evidence IDs and lineage roots;
- the grounded ancestor conclusions and named deduction assumptions;
- its origin kind `deduction`, distinct from observation or same-claim revision.

No new source root, independent observation or empirical evidence count is created.
Deduplication must survive a new controller step or transport key with the same
logical derivation. Keep derived alternatives inspectable. Unknown provenance or
an invalid proposal must not initialize a numeric aggregate.

For a previously unknown target, an admitted derivation can initialize explicitly
inferential support. When the target already has support, retain the derivation
as an alternative unless a separately authorized, exact-support independence
assumption justifies revision. No automatic independence merely because inference
ran successfully. Existing observed inputs continue through the M2 evidence path.

Keep variant-specific lineage rules: revision combines two same-claim supports;
deduction cites its five ordered, potentially different-claim premises. Do not
require foreign premise supports to masquerade as leaves in the target's observation
ledger. Coverage must state what it covers rather than reusing the M2 field with
an incompatible silent interpretation.

**Ancestry must survive later revision too.** The M2 conversion in
`GuardedRevision._support` has no cross-claim ancestry to preserve yet. Once derived
supports exist, propagate ancestry through deduction, admission, revision and
subsequent kernel input. Test derive -> revise -> derive cycles. Keeping roots while
dropping ancestor conclusions would weaken the existing upstream cycle guard.

## 8. C4 — bounded attention-guided work

Use a small, explicit immutable workset of grounded tasks, not search. Each task
is an ordinary private referencable record containing the allowlisted rule, exact
role bindings and context. It can also serve as Attention's opaque target; this
avoids making Attention understand a PLN rule. Declare task granularity in the
profile so it is not silently presented as atom-level attention equivalence.

A new step:

1. Authenticates and durably binds its identity, workset, policy/runtime selections,
   budget and deadline. Reusing its key with other semantics conflicts.
2. Reads one bounded attention selection from the declared eligible universe and
   records the selection snapshot/order. Rejected or unresolved tasks consume
   examined-candidate budget; no unbounded scan to find one executable task.
3. Reads/binds the selected immutable premise vector and reserves a native attempt
   before asking the owning admission operation to run the selected kernel.
4. Records the returned admission/refusal and exact support identity. A calculation,
   a persisted proposal and an admitted belief remain distinct observations.
5. Persists eligible feedback intent and delivers it through Attention's port with
   a stable causal identity; records its acknowledgment separately.
6. Continues only while the originally admitted work/deadline/generation limits
   allow it, then records an explicit terminal or resumable outcome.

Feedback can be a fixed, named test reward for one newly admitted derivation; it
is a workflow-success signal, not an increase in truth or evidence. Duplicate
admission produces no second reward. Use the logical derivation/admission identity,
not a fresh step ID, as its causal basis. Selection within a step can stay frozen;
a subsequent step can observe feedback. No immediate recursive feedback processing
is required to prove a closed loop.

Support a tiny two-stage fixture only if useful: an output admitted by one step
can be an explicit premise of a later task. The later step freezes its exact
vector. No automatic expansion of all possible grounded rules is requested.

### Budgets that survive restart

Define `max_rule_applications` as a hard bound on native evaluation **attempts**,
including retries after crashes, or add a separately explicit attempt limit.
Track successful unique derivations separately. Persist reservation before dispatch.
A crash after reservation but before execution may conservatively spend a slot;
never promise both unlimited replay and a strict physical-attempt cap.

Repeated calls with the same step identity do not reset candidate counts, attempted
calls, feedback generations or the deadline. An exhausted step may finish without
a conclusion. Recovery must report remaining work rather than manufacture success.

Bound kernel timeouts by the remaining step deadline, including provider checks
where performed in that invocation. Persist the deadline basis so a process restart
does not grant a fresh timeout. State the trusted same-host clock assumptions and
observed cancellation limits; no hard real-time scheduling or reboot guarantee.
Stop on unavailable dependencies without converting them into empty beliefs.

The global feedback-generation limit must follow admitted causal records across
step IDs; it is not merely a counter reset for each call. It is distinct from
logical deduction depth and from the source-evidence lineage.

## 9. Recovery, privacy and adversarial conformance

Reuse existing durable journal/outbox patterns, not a distributed transaction
coordinator. Run real process-kill tests at these boundaries:

- after attention stimulus commit before response: no second STI application;
- after native-attempt reservation: restart retains the spent/reserved budget;
- after kernel return before belief commit: repeat computation only within remaining
  attempts and admit at most one logical derivation;
- after belief commit before controller progress: recover the same decision/support;
- after attention feedback commit before controller acknowledgment: no second reward.

Also exercise output CAS conflict, concurrent logical clock advance, same-key
changed semantics, revocation before cached replay/after calculation, incompatible
profiles, malformed provider responses and empty/capacity-limited queues.
Verify complete request/response binding and that implementations expose only the
ports declared to their consumers. Do not rely only on runtime-checkable Protocol
shape tests.

Keep C3 tests runnable without PLN, Hive, DA or C1/C2. Keep M2 recording usable when
attention/inference is absent. Test the new private trace for canary content,
private hashes, provenance, task and attention identifiers escaping through shared
bindings or normal public Hive receipts. Only deliberate generated counts/status
may be exposed by this demonstration. Local administrator secrecy and production
identity/security remain outside the tested threat model.

## 10. Actual Hive demonstration and small comparison

Add one narrowly named generated inference action through the existing authenticated
native Programs dispatch. Preserve `fusion-inspect` and `fusion-episode`. Seed a
bounded private workset and explicit numerical observations; no live LLM or real
user history is needed.

Demonstrate two eligible grounded tasks. With a one-native-attempt budget, an
explicit STI change selects the other task in a fresh controlled run. The selected
task invokes actual native deduction, produces a lineage-preserving admission and
a duplicate-safe attention feedback receipt. Replay/restart recovers the same
logical outcome. Swapping the attention provider changes only composition.

Hold task inputs, evidence, policy parameters, budgets and logical schedule fixed
for the provider comparison. Report selection order, examined candidates, native
attempts, valid/refused proposals, unique admissions, deduplicated feedback,
recovery outcome and observed elapsed cost. State fixture size. Do not infer
cognitive-quality improvements or production throughput from this experiment.

## 11. Deliverables and gates

Update the existing docs, contracts, source locks and runbook. Deliver the minimal
C3 owner, independent same-profile provider, pure deduction adapter, explicit
C2-derived-admission extension, bounded controller, native Hive action, and focused
conformance/recovery tests. Supply one verification entrypoint and a machine-readable
manifest, plus `docs/module-interfaces/m3-evidence.md`.

| Gate | Required evidence |
|---|---|
| BASELINE | Applicable M1/M2 tests rerun; failures and unavailable inputs explicit. |
| CONTRACTS | Exercised C3/C4 contracts, tagged support semantics, versions and authority agree. |
| C3 | Persistent STI policy, bounds, logical clock, deterministic selection and causal replay. |
| C3_INDEPENDENT | No PLN/Hive/DA requirement; hostile declared-port dependency test. |
| ATTENTION_SWAP | Unchanged consumer on independent same-profile providers and fresh stores. |
| KERNEL_NATIVE | Actual pinned deduction formula with independent goldens, guards and runtime-profile evidence. |
| DERIVED_ADMISSION | Owner-only admission, exact premise vector, preserved roots/ancestry, duplicate/cycle rejection and no invented independence. |
| C4_BOUNDED | Selection affects work; durable attempt/deadline/generation limits survive restart. |
| RECOVERY | Real kill/replay preserves logical admission and feedback without restoring spent budgets. |
| PRIVACY | Private data and identifying derivatives stay off shared routes and public native receipts. |
| HIVE_M3 | Actual authenticated runtime action executes the bounded private loop and restart path. |
| REPRO | Fresh-directory declared-input recipe; warm-cache assumptions and access requirements explicit. |
| SCOPE | C3/C4 only, one grounded rule, no research-policy expansion or live migration. |
| CHAIN | NOT_RUN: a separate same-artifact integration decision, not an implicit pass. |

Tests follow obligations, not a numerical quota. Keep fixture/native classifications
inside mixed suites and retain failed development runs separately from the final
run. Report exact final source identity and any later evidence-only commits.

C3-only completion is useful but is not a complete M3 pass. If native deduction,
private admission or Hive is unavailable, complete independent work, report the
specific partial gates and stop rather than adding a substitute framework.

After M3, stop for review. Further attention algorithms, richer reasoning, and the
real ASI:chain integration gate require a separate decision; do not continue into
M4 automatically.

## Public source locations

These are review sources, not authorization to publish private dependencies.

```text
https://github.com/machieke/fusion-module-interfaces/tree/f0cee24
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/f0cee24/fusion/ports.py
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/f0cee24/fusion/beliefs.py
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/f0cee24/fusion/memory_contracts.py
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/f0cee24/fusion/adapters/pln_revision.py
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/f0cee24/docs/module-interfaces/m2-evidence.md
https://raw.githubusercontent.com/machieke/reachability-atomspace-prototype/dd56f3f053ed90239de5377021a7d3b3fbf424ac/reachability/pln_adapter.py
https://raw.githubusercontent.com/machieke/reachability-atomspace-prototype/dd56f3f053ed90239de5377021a7d3b3fbf424ac/ADAPTERS.md
https://raw.githubusercontent.com/trueagi-io/PLN/4405956947c4b53c7ff01bd565aa3b114bc970a1/lib_pln.metta
```
