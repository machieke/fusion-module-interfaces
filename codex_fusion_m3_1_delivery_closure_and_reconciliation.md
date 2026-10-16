# Codex handoff — Fusion M3.1: close evidence delivery and reconcile feedback

## 1. Objective, source baseline and stop boundary

Continue `machieke/fusion-module-interfaces` from
`c4498ce3047f1283d3a4a3ae3d09b713e7dcf312`, or record the exact descendant and
relevant changes. Read applicable `AGENTS.md`, the original brief, the M3 brief,
contracts, decisions, current implementation and M3 evidence before editing.
Preserve unrelated worktrees and private upstream access restrictions.

**Objective:** close the two demonstrated delivery-lifecycle gaps without adding
cognitive capability: (1) C1 evidence delivery to the M3 belief owner must be
acknowledgeable without teaching C1 the belief model's internal snapshot schema;
(2) committed or permanently obsolete attention feedback must have an explicit,
bounded reconciliation path even after inference execution has stopped.

**Stop at M3.1.** No new inference rules, general search, LTI, promotion,
summarization, adaptive attention research, full ECAN economics, new scheduler,
new transport, chain work, live migration or production deployment. Do not
replace existing ownership, numerical implementations or the DA layer.

M3's reported tests demonstrate its bounded feature scope. This handoff addresses
progress and completion semantics outside those successful examples; it does not
reinterpret the historical report as a failed test run. A lost native reservation
spending its slot is intentional, not a defect to fix by refunding the budget.

The public source/evidence review did **not** independently execute the repository
suites, native dependencies or Hive checkout. The report identifies clean tested
implementation `1af39794649d0ca95cd729c64868202368da1ec4`; the pushed commit records
the evidence. Verify both identities and the intervening diff locally.

## 2. Findings to reproduce before changes

The paths below are relative to the pinned Fusion revision. These are review
findings; confirm them against the actual checkout rather than copying them as
assumptions.

| Finding | Source and expected baseline observation |
|---|---|
| C1 validates a whole belief decision | `fusion/episodes.py:acknowledgeEvidence` calls `memory_contracts.decision`, which recursively validates the old snapshot/support schema. |
| M3 introduces a different belief shape | `fusion/cognition_contracts.py` adds tagged support, ancestry and `coverage_kind`; M3's `DerivedBeliefOwner` uses these validators. |
| The old relay also assumes M2 | `fusion/evidence_relay.py` selects the M2 belief profile and uses its snapshot/decision validators. Fixing the final acknowledgment argument alone does not make the relay M3-compatible. |
| The generated M3 workflow leaves deliveries pending | `integration/m3_scenario.py` appends ten evidence-bearing observations and submits them to C2 directly, but does not acknowledge the corresponding C1 delivery intents. |
| Pending delivery has a finite capacity | `memory_contracts.MAX_PENDING` is 16; `EpisodeOwner.appendEvent` rejects a new evidence-bearing event when that episode already has 16 pending deliveries. This is separate from the 256-event lifetime bound. |
| Feedback retries keep the original logical time | `fusion/inference.py` constructs feedback from the saved selection; `AttentionOwner.submitStimulus` rejects a fresh stimulus whose expected step or causal parent is stale. |
| Terminal execution prevents later reconciliation | `InferenceOwner.step` immediately returns a completed step; its feedback path checks the original deadline before attempting delivery. It therefore has no post-terminal closure path. |
| The existing native conflict test freezes the gap | `integration/pln/test_deduction.py:test_concurrent_clock_advance_keeps_feedback_pending` expects the same pending CONFLICT after reopening. |
| Native public output does not expose closure independently | `integration/hive/inference_program/program.py` projects controller completion into done/committed and exposes counters, but not explicit evidence/feedback closure status. |

Also inspect `fusion/{ports,cognition,private,attention_contracts}.py`, the
independent `fusion/adapters/fixture_attention.py`, M2/M3 test harnesses, native
recovery tests and the existing build/verification scripts.

Run the applicable baseline and add focused reproductions of the acknowledgment
mismatch, full pending queue, stale-feedback retry and post-deadline recovery.
Keep expected baseline limitations distinct from unexpected test failures. Do not
change policy limits or suppress regression cases to manufacture a pass.

## 3. Preserve the architecture and trust model

| Owner/boundary | Responsibility in this increment |
|---|---|
| EpisodicMemory | Own the episode and whether a particular committed delivery has been acknowledged. It must not understand deduction/revision mathematics. |
| BeliefRevision | Own evidence admission, the exact durable decision and all belief state. It remains the authority for whether an evidence submission completed. |
| Trusted local evidence relay | Deliver/replay the selected C2 request, validate its response under that selected profile, and relay a correctly bound completion to C1. |
| Attention | Own application, deduplication and any explicit retirement of a stimulus. No controller may edit its tables or infer application from current STI. |
| InferenceControl | Own execution limits, progress and reconciliation of its recorded feedback intents, not truth or attention state. |
| Hive adapter | Translate native requests and present privacy-safe progress. It is not another owner or a cleanup service. |

A module is not necessarily a separate process. Reuse local ports and journals;
no event bus or distributed transaction coordinator is requested. Current authority,
exact scope/context, descriptor binding and semantic replay apply to reads,
acknowledgments, reconciliation and cached results. Provider injection alone is
not authority. Retain the trusted-local-host failure model.

## 4. Work package A — model-independent evidence acknowledgment

### 4.1 Define the narrow completion contract

Introduce the smallest explicit completion/acknowledgment DTO or local profile
needed for the supported C1–C2 integration. Preserve the old operation/profile
where its semantics remain in use; do not make the old closed validator silently
accept arbitrary new snapshots.

The new acknowledgment must bind at least the delivery ID, exact EvidenceRef,
scope, selected consumer identity/profile and its durable decision identity. Bind
claim/context or a semantic request fingerprint wherever needed to prevent a
valid decision for another submission from clearing this delivery. It must state
that processing reached a durable final decision, not that the proposition is
true or that numerical revision necessarily occurred.

C1 validates delivery identity, authorization, allowed consumer binding and replay.
It must not parse `Truth_Deduction`, support arity, ancestry, coverage or the PLN
numerical model simply to clear its own delivery intent. Keep full decision and
snapshot validation at the C2-facing relay/adapter boundary.

Make issuance and trust explicit. Prefer the existing trusted local relay and
selected owner ports over signatures or new infrastructure. A caller-created
`committed=true`, an arbitrary decision ID, a matching content hash or an asserted
issuer name is insufficient. The relay must observe the exact committed C2
response through an authorized port/replay and validate its selection and request
binding before emitting the completion. Only the bound trusted acknowledgment
context can attest that observation to C1; do not expose arbitrary acknowledgment
authority through Hive parameters. This is local trust, not cryptographic proof.

An admitted retained alternative, report or model-inapplicable decision can close
delivery if the selected contract records it as durably processed. An unavailable
provider, timeout or pending attempt cannot. Keep transport/admission completion
separate from numerical outcomes.

### 4.2 Wire the actual M3 path

Adapt the existing relay with explicitly selected contracts, or add a narrow M3
adapter around it. Do not duplicate its state machine into the Hive plugin or add
parallel owners. A checked injected validator/profile adapter is acceptable;
trying validators until one happens to accept an unlabelled response is not.

Use the supported path for M3's generated observations. Prefer one durable
admission path rather than submitting directly and later inventing a second
request to acknowledge it. If existing direct admissions are reconciled, recover
their exact original semantics or a documented duplicate-admission receipt; never
count them as fresh evidence or silently add independence assumptions.

Retain separate commits:

```text
C1 event + delivery intent
  -> selected C2 admission/decision
  -> relay records the validated decision
  -> C1 acknowledges that exact delivery
  -> relay records acknowledgment
```

A lost response at any boundary replays the original identity. A changed claim,
context, occurrence, descriptor, decision, numerical input or assumption conflicts.
Recheck authority on cached replay. CAS retries require a new explicit attempt
without creating a new occurrence. No foreign SQL writes or direct queue clearing.

### 4.3 Required progress tests

Use one persistent episode across several batches, not one new episode per batch.
Process at least `2 * MAX_PENDING + 1` distinct evidence-bearing events, draining
between bounded batches. At the current pin that is 33 events. Keep unrelated
per-claim, atom and episode limits out of the way with suitable generated inputs;
do not raise the limits. Assert the committed event count, one logical contribution
per occurrence and zero eligible pending deliveries after each successful drain.

Also fill the pending queue deliberately, observe explicit backpressure, drain
through the public owner ports, and prove another append succeeds. Cover M3
receipts for a claim whose ledger already includes a deduction: dropping fields
until a v2 validator accepts it is not a valid compatibility implementation.

Test wrong delivery/evidence/consumer/decision, unknown profiles, malformed receipts,
uncommitted responses, duplicate acknowledgments, changed bodies, scope violations
and revocation. C1 remains runnable without PLN, Hive or C2 installed, using a
labelled trusted-consumer fixture for completion checks.

## 5. Work package B — bounded feedback reconciliation without more inference

### 5.1 Separate execution termination from delivery closure

Execution can stop at its deadline or budget while recorded deliveries remain
unsettled. Introduce an explicit call-driven reconciliation operation on the
existing controller, or an equivalent narrow extension, with its own bounded
I/O/reconciliation work limit. A read-only progress operation may accompany it
where necessary. Do not install a background service or scheduler.

Bind reconciliation to the authenticated owner, exact stored step and original
provider selections. It must not select new tasks, invoke PLN, admit a new
inference, refund reservations, reset candidate/generation counters, extend the
original execution deadline or create fresh feedback causes. An expired execution
budget does not prohibit learning what already committed before expiry.

Keep the original execution result/terminal reason stable. Closure progress is a
separate versioned observation; a later acknowledgment is not a rewritten claim
about what happened during the original step. Bound every reconciliation call and
retain progress across its own lost responses.

### 5.2 Resolve applied versus obsolete feedback authoritatively

Preserve `submitStimulus`'s exact-step, exact-parent and causal deduplication rules.
Do not change `expected_step`, parent, generation or cause under the original key.
Do not retry under a fresh cause just to obtain a reward.

Implement the smallest declared Attention operation needed to obtain a receipt
for the original causal command, or atomically resolve/retire an inapplicable
intent. Both attention providers must implement the same selected semantics.

Required outcomes are:

- **Already applied:** return the original durable receipt and let the controller
  acknowledge it, including after the execution deadline or subsequent decay.
  Current STI is not evidence of whether this particular credit occurred.
- **Not applied and still eligible:** before the original effect deadline, any
  permitted delivery uses exactly the existing intent and budgets. This can remain
  the normal step path; reconciliation need not grant new allocation powers.
- **Permanently inapplicable:** for this increment prefer explicit no-credit
  retirement on an expired effect deadline or obsolete clock/causal parent.
  Record the reason without retiming, changing generations or altering truth.
- **Unavailable or indeterminate:** remain visibly pending with a typed reason.
  Provider unavailability must not become fabricated non-application or success.

Retirement is a proposed extension, not an existing M3 guarantee. The Attention
owner must serialize it with submission under its own transaction/lock. If the
original stimulus already applied, application wins and its receipt is returned.
If retirement wins, persist a bounded causal tombstone/equivalent terminal record
that prevents a delayed original submission, including a new transport key with
the same cause, from applying later. A controller-side `read absent; mark skipped`
sequence without this race protection is insufficient. Validate exact original
semantics and current authority before either outcome.

Keep policy retirement distinct from numerical failure. Retiring an unearned
workflow credit does not undo a valid belief admission. A remaining transient
capacity conflict can stay pending until a bounded later retry; do not evict
acknowledged state or enlarge capacities to claim unbounded progress.

These operations are local receipt/causality management, not new attention
mathematics or a general cancellation framework. No cross-owner atomicity is
claimed. The independent file fixture must implement its own transition logic;
sharing pure DTO validators is acceptable, delegating to SQLite is not.

### 5.3 Recovery obligations

Add deterministic controlled cases for at least:

1. Attention applied feedback; the controller died before acknowledgment; the
   original deadline expires before restart. Reconciliation must recover the
   applied receipt with no new credit or native call.
2. Clock advances after belief admission but before feedback application. Resolve
   the stale original intent to a visible no-credit terminal outcome rather than
   endlessly returning the same CONFLICT or retiming it.
3. Execution already reports complete with pending feedback. Reconciliation remains
   available, without reopening execution.
4. Application races with retirement. Exactly one owner-authoritative outcome is
   possible; delayed delivery cannot award after confirmed retirement.
5. Temporary Attention unavailability. Preserve pending status and later progress;
   do not classify a failed read as absence. Revoked authority still fails closed.
6. Crash after provider receipt/retirement commit but before controller progress.
   Replay recovers the same result under both attention implementations.

Use actual process kills at the new durable boundaries, with deterministic clock
control or controlled expiration rather than arbitrary sleeps. Keep injected clock,
response and provider fixtures labelled. Reconciliation must have zero new native
formula invocations and leave original execution budget consumption unchanged.

Do not broaden this task into reclaiming abandoned derivation rows or refunding
lost attempts. The existing conservative reservation behavior remains a required
regression, including one-slot exhaustion without a conclusion.

## 6. Work package C — real caller, compatibility and evidence

### Native Hive progress

Extend the actual authenticated generated-inference action and, where needed, one
narrow reconciliation/progress action through the same verified native mechanism.
Do not replace native dispatch with standalone helper calls for the integration gate.

Expose generated counters/status that distinguish execution termination, result
admission, evidence-delivery backlog and feedback closure. A finished execution
can legitimately have no conclusion or pending deliveries. Do not flatten these
into an unqualified successful result. Preserve normal Hive envelope compatibility
through an explicit version/profile decision; keep `fusion-inspect` and
`fusion-episode` working.

Do not expose private episode IDs, task/support hashes, source roots, snapshots,
credentials or local paths to make progress observable. Repeat the existing
canary and outbound-binding checks for new diagnostics and receipts.

### Compatibility and retained state

Make operation/profile changes explicit before changing DTOs. Preserve old M1/M2
and M3 behavior under their historical profiles, including strict response
validation and journal selection checks. No silent permissive union of unrelated
snapshot schemas and no removal of stored identity guards.

Prefer a small additive, declared extension when its semantics permit it. New
profiles may require fresh state. State plainly whether the new implementation
can reconcile pre-existing M3-format pending work without migration. Test any
claimed compatibility on disposable copies of populated generated M3 journals.
A fresh-store success does not demonstrate repair of old pending records.

Do not edit or migrate the user's populated stores in this task. If older state
cannot be opened under the new profile, retain the old reader/replay behavior and
report that limitation separately instead of clearing or reidentifying its work.
No live migration framework is requested.

### Evidence and source discipline

Reuse `build_m3.py`, source locks and verifier patterns. Do not rebaseline PLN,
Hive, DeTTa or SWI merely to implement acknowledgment/reconciliation. Run applicable
M1–M3 regressions and new fixture, real-provider and native-caller cases separately.
Warm-cache reproduction is acceptable only with that qualification. CHAIN and
empty-global-cache builds remain NOT_RUN.

Record the exact tested commit and any later evidence-only commits. Retain failing
baseline reproductions and corrected results separately. Count unique tests and
parameterized kill cases accurately; rerunning a subset does not create additional
unique coverage. Do not turn unavailable dependencies into fixture passes.

## 7. Acceptance gates

| Gate | Required evidence |
|---|---|
| BASELINE | Exact sources; applicable M1–M3 regressions and focused pre-change gap reproductions. |
| ACK_CONTRACT | C1 validates bound delivery completion without parsing PLN support/snapshot internals; untrusted or mismatched completion is rejected. |
| C1_C2_PROGRESS | The real M3 observation path acknowledges actual C2 decisions; a repeated episode exceeds one pending-queue capacity cumulatively and drains correctly. |
| EVIDENCE_RECOVERY | Kills after belief commit and after C1 acknowledgment recover without lost events, duplicate contributions or foreign writes. |
| FEEDBACK_CLOSURE | Applied, retired and unresolved outcomes are explicit; post-terminal and post-deadline receipt reconciliation works. |
| CAUSAL_RACES | Submission/retirement race and delayed duplicate delivery cannot create a credit after terminal retirement or duplicate an applied one. |
| BUDGETS | No new native calls or replenished work/deadline/generation budgets during reconciliation; conservative lost-reservation behavior preserved. |
| PROVIDER_SWAP | Unchanged consumer and same closure tests on SQLite and independent atomic-file Attention providers. |
| AUTH_PRIVACY | Live authority, descriptor binding and private canary isolation on all new/replayed operations and native outputs. |
| HIVE_M3_1 | Actual native dispatch exercises delivery closure and caller restart, with accurate progress and unchanged earlier actions. |
| COMPAT_REPRO | Old-profile regressions, declared new profile/state compatibility, exact build inputs and fresh-directory verification of supported gates. |
| SCOPE | Delivery closure only; no new cognition, scheduler, migration or chain work. |
| CHAIN | NOT_RUN; not an implicit pass or dependency of this increment. |

## 8. Deliverables and final report

Update existing contracts, architecture, ADRs, runbook and implementation rather
than starting a second framework. Deliver the small profile/port extensions,
selected relay/composition changes, bounded reconciliation path, native progress
projection, conformance/failure tests, and `m3_1-evidence.md` plus a machine manifest.

Report the exact source state, design choices, changed files, commands, observed
outcomes and remaining limits. Include before/after evidence for queue draining
and terminal-step feedback recovery, with original budget and native-call counters.
List real providers, independent fixtures, injected faults and unavailable/unrun
gates. Do not claim power-loss survival, distributed delivery, production privacy,
full ECAN, cognitive-quality gains or chain execution.

**Then stop.** The next product integration decision should return to a deliberately
shareable artifact from an actual Hive workflow and a verified ASI:chain operation.
Keep full private episodes and identifying hashes off that path. This handoff does
not authorize that chain work or make local closure a prerequisite for unrelated
chain-source preparation.

## Review source location

All implementation paths in this brief refer to the pinned public tree below;
M3's evidence/manifest and final verification are under `docs/module-interfaces/`.
The original M3 handoff and both October 15 meeting transcripts remain the source
of scope and terminology, not approval of these new closure-policy choices.

```text
https://github.com/machieke/fusion-module-interfaces/tree/c4498ce3047f1283d3a4a3ae3d09b713e7dcf312
```
