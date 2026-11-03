# Phase 3 sustained single-node release candidate

**READY_FOR_SUSTAINED_DEVELOPER_REVIEW — R01–R12 complete within the declared
single-node envelope.** The [detached artifact record](../../evidence/phase3/artifacts.json)
identifies the actual local distribution; no registry release is claimed.

This programme continues `660803cb955802175765ad16391b7453926b5f47` and reuses
Phase 2. The primary sustained workflow completed 70 operator inputs on one
retained corpus, including dynamic sessions, overlapping agents, private
cognition and counterfactual readback. Additional qualification and final
artifact verification are recorded in the [gate matrix](../../evidence/phase3/release-gates.json).
The matrix separates required gate results, historical failures, unavailable
measurements and environments that were not run.

Start with the [operator runbook](runbook.md). [Contracts and capacity](contracts-and-capacity.md)
define the finite envelope; [privacy and models](privacy-and-models.md) explains
disclosure and disabled real-model selection. The [programme ledger](../../evidence/phase3/progress.json)
retains the source, failure and continuation trail. No additional live generation,
generative-runtime startup, contact, loading or live reservation occurred.

## What changed

| Package | Delivered responsibility |
|---|---|
| R01 | `omega-native-sessions/3`: policy-bound dynamic allocation, replay-stable handles, finite active/retained/pending/byte limits, immutable accepted configuration |
| R02 | Explicit undispatched expiry, cancellation, bounded saved-receipt reconciliation and causal fencing of uncertain started work |
| R03 | Explicit fresh `immutable-commit-feed/2`, record/byte reservations, immutable source continuity and indexed owner-local reference lookup |
| R04 | Bounded native-stage/transport instrumentation, actual latency/call observations and measured reference lookup comparison |
| R05 | Concurrent native callers, dynamically allocated incoming task sessions, authenticated binding callback and original-deadline result routing |
| R06 | Separate synthetic private scopes throughout memory/history/cognition, current disclosure authority and exact operator-approved shared excerpts |
| R07 | Recorded and existing real model bindings selected independently; missing live approval denied before acceptance/reservation/backend construction |
| R08 | Reusable frozen evaluation, alternate evidence/withdrawal corpus, absent fact and explicit premise reassessment; actual native results scored separately from permission |
| R09 | Installed CLI/workbench allocation and safe lifecycle actions; current owner observations separated from retained captures |
| R10 | Process/pod fault qualification, exact retained accounting, compatible rollout and fresh observation-only restore |
| R11 | Client/operator 0.3.0, explicit source/artifact distribution, safe CI and standard-host import command rendering |
| R12 | Integrated sustained workload, privacy and negative cases, isolated exact-artifact chain regression, cleanup and protected-resource comparison |

A native process completes one input quantum before another eligible session
runs. Failed children do not automatically retry. Untouched expired inputs can
release pending queue headroom; started uncertain effects fence dependent work.
Reconciliation only observes saved owner/application results. Closing and
archiving do not erase history, refund reservations or grant capacity credits.

The feed reserves finite records and bytes before backend acceptance, then
publishes independently. A downstream refusal remains a charged partial state;
there is no cross-owner capacity transaction. Search still uses authenticated
AtomStorage/feed ports. The DeTTa opaque-coordinate partitions, E5 preprocessing,
Chroma metric, original NAL/PLN functions and wall-clock Attention policy remain.
Previous numerical, source and exact-template profiles remain distinct.

## Executed native continuity

The [core report](../../evidence/phase3/sustained-dev09.json) records one retained
namespace, `omega-ref-phase3-sustained09`. Its 36-input initial phase allocated
three sequential sessions per agent without per-session deployment edits.
Shared source heads progressed 108, 212, 316, 420, 524 and 628. The old 512-record
threshold was crossed at operator input 30, followed by six more initial inputs
and the remaining 34 core inputs. The early captured result stayed exact.
Later shared-source observations reached 1,089; the subsequent ten-input
alternate workflow reached 1,280 on the same source. These are aggregate source
records, not user-memory counts. No source, application or accounting reset
produced this crossing.

The core used 11 operator allocations plus two incoming task allocations, and
74 recorded-model captures: 70 operator inputs plus four automatically accepted
task/result inputs. These are different units, not an additive benchmark score.
Both directions of native delegation completed, including recipient query,
authoritative result publication and sender context consumption. Two overlapping
native remembers were followed by four cross-agent fresh query readbacks.
The native inspection was acknowledged before its approved artifact entered the
separate chain regression.

Each agent completed six private native steps. The storage/feed authority audit
rejected 12 foreign-scope requests and verified 982 shared payloads without the
private canary. Captured model-intent inspection found each private canary only
in its own partition; shared captures contained neither. A proper literal
excerpt was published with independent public identity and read by the other
agent. Current disclosure revocation denied both current and retained reads;
restoring the original policy bytes did not edit journals.

The [alternate evaluation](../../evidence/phase3/alternate-dev10.json) exercised
same-source repetition, retained contrary assessment, and two-source revision
under an explicit synthetic independence assumption. It does not establish
empirical independence. Belief changes left Attention revision/value unchanged.
A native withdrawal excluded the memory from fresh query while retaining the
old query capture. Current disclosure was denied, explicitly historical access
remained authorized, and a foreign agent's session read was denied. History
pagination is exercised rather than assuming the first page contains all source
handles.

The [full-quota case](../../evidence/phase3/quota-dev09.json) is a separate fresh
fault scope, not a substitute for sustained continuity. Two native remembers
filled its deliberately selected 32-record quota. A third accepted native input
retained partial uncertainty. Authenticated owner admission returned `OVERLOADED`;
old payloads, results and accounting survived replacement. Its earlier driver
expectation failures remain recorded.

## Timing and operating envelope

The core's 70 operator observations had median 19.928 s, p95 28.691 s, minimum
14.922 s and maximum 32.671 s. This is one finite machine/workload sample, not a
throughput SLA. No before/after end-to-end speedup is claimed.

[Native stage evidence](../../evidence/phase3/native-timing-dev10.json) contains
actual executed spans from both agents, not reconstructed totals. Agent A's
44 captured native inputs show median first bridge contact 3.629 s, application
bootstrap 221 ms, history context 885 ms, model-prompt construction 1.729 s,
source capture 1.636 s and finish 1.346 s. Native query encoding, memory retrieval,
source publication, C1/C2 validation, promotion, batch reads and result handoff
also have measured spans and call counts. Nested durations must not be summed.
Four provider-local trace collections were absent (Attention, Embedding, storage
and then-inactive commitment); their client-side spans do not manufacture those
missing provider-internal measurements.

On 1,089 real stored metadata rows, 36 lookups per implementation returned
identical references/coordinates: scan median 2.820 ms versus index median
0.017 ms. This supports the owner-local reference index only. The native process
and history costs still dominate; validation, authorization and hydration were
not bypassed. Three paired local native observer trials (12 commands) did not
establish a meaningful end-to-end overhead or speedup claim.

[Process observations](../../evidence/phase3/process-resources-dev10.json) cover
13 running owner pods with bounded two-second `/proc` samples. RSS sums can
double-count shared pages; CPU deltas censor exited processes. These sequential
samples are neither simultaneous peak load nor kernel working-set measurements.
Metrics API and pod cgroup files were unavailable. CPU quota enforcement remains
**NOT_ESTABLISHED**. The cluster exposed eight allocatable CPUs; overlapping
several full qualification namespaces hit `Insufficient cpu`. Quiescing finished
task scopes freed resources without changing requests, host cgroups or deadlines.

## Operation, recovery and failure evidence

The [control drill](../../evidence/phase3/control-dev09.json) preserves allocation
reply loss across replacement, untouched expiry and cancellation, next-input
progress, a started uncertain mutation and its blocked dependent input, and
independent progress by the other agent. The installed browser actually
reconciled another expired undispatched input and allocated a session. The
[workbench observation](../../evidence/phase3/workbench-current-dev10/report.json)
read current source sequence 1,280 beside retained view sequence 18 and the
original native capture. Screenshots are illustrative; the state distinction was
asserted from rendered DOM data. No UI action performs a missing effect.

The [control restore](../../evidence/phase3/control-restore-dev09.json) retained
three sessions, seven inputs, original deadlines/accounting and uncertainty.
The clone API denied allocation and reconciliation with newly issued credentials.
It exposed observation only; neither original nor clone resumed effects.
The [pod recovery report](../../evidence/phase3/recovery-dev10.json) covers seven
real durable-boundary fault cases: private source capture, private C2 decision,
backend acceptance before feed publication, recorded model capture, workspace
append, task payload capture and approved private publication capture. The
workspace readback contains one append, recipient model/command accounting stays
unchanged after replacement, and the sender consumes the task result. Allocation,
terminal-status and feed-admission SIGKILL tests are separate real SQLite/process
tests with fixture clocks/backends, not additional deployed native workflows.
The [main-state restore](../../evidence/phase3/main-restore-dev12.json) retained
13 owners, 14 closed sessions and 84 accepted inputs (80 operator inputs and
four task/result inputs). All captures, bindings, deadlines, capacities and
states matched through declared APIs. Fresh clone credentials permitted current
shared/private observations and denied allocation/reconciliation. The
[readback](../../evidence/phase3/restore-readback-dev12.json) verified an early
shared payload, private payload, eight retained history events and foreign
private-read denial. No native worker or external effect was executed by the clone.
Its first export failed because a deferred SQLite close removed a WAL after the
archive list was frozen. Closing checkpoint/diagnostic handles before enumeration
corrected this. The next attempt restored all archives but its private current
observer selected a shared seed configuration and was denied. Dev12 resolves
ports within the selected private template without executable materialization.
The same already-restored journals passed the recheck; no reimport, source
rewrite, expired-input reset or counter edit manufactured completion.

Development failures are not removed: profile wiring, C1 serialization, task
network/turn-permit checks, control-driver expectations, source-audit observer
bounds, and private test-barrier sealing were corrected and rechecked. The dev10
runtime correction canonicalizes only qualification hook fields, retaining the
old unarmed configuration digest exactly. A later recovery-driver timeout came
from an earlier source hook still armed for a newly selected shared scope; the
input remained uncertain and was not retimed. A separate missing-file append
failed without a file effect; the later explicit workspace setup and append
case do not relabel that failed occurrence.

The first same-artifact chain startup failed before genesis because placeholder
public values had not been bound to the generated key. The corrected fresh
installer binds only public identity before the initial node mount. The failed
PVC is retained. A separately named fresh node claim uses the original generated
unfunded key, with no prior signed intent/deploy to transfer. Main source,
application, artifact and result histories remain untouched. The new claim is
explicit operator configuration, not automatic recovery from an uncertain
chain effect. Historical chain profiles and consensus code are unchanged. The corrected
[same-workflow chain run](../../evidence/phase3/same-workflow-chain-dev10.json)
passed exact-result approval, lost-submit-response recovery, caller/adapter/node
replacement and independent readback. Its inspect digest
`38b255c9cbcc736612d34394a7bbbcc7a296d4d5e9c65a18f568417cd320048d`
matched finalized deploy effect in block 7. There was one submit, no automatic
resubmission, and no private-source export. Finality attests to that retained
artifact, not the truth or freshness of later memories.

## Source and evidence boundaries

The core run used dev09 images and chart 0.6.2. The selected dev10 image map is
`89a41f8266770102ec611e39d24991452ccbceef771a00c100af54ae839226c5`;
its [single runtime-file delta](../../evidence/phase3/dev09-dev10-source-delta.json)
is the compatible qualification-hook normalization. The same retained deployment
was rolled forward for affected private-boundary recovery and further native,
privacy, current-state and negative-task checks. Dev11 subsequently changes only backup/diagnostic connection lifetime and
file-list sequencing; its source map is
`298881316fe74ce8d8a5b89b9228de9466a7dbda4e6c3394769c1f1cf584d205`.
The [two-file delta](../../evidence/phase3/dev10-dev11-source-delta.json) has affected
WAL/diagnostic regression tests. Dev12 changes only the fenced current observer,
with source map `c5b7a67545a5c332d40fd3f0a462f08954fd5593a31ce7f7a9dde0a23ff83675`.
Its [one-file delta](../../evidence/phase3/dev11-dev12-source-delta.json) passed
private-port regression tests and the complete same-state restore readback.
Chart 0.6.3 adds
the explicit isolated-node claim selection. The report does **not** claim the entire core was
rerun on the final image/chart. Exact artifact, chart, wheel and per-scenario
bindings are published separately from historical raw report identities.

The historical Phase 2 lane passed 539 methods after correcting its dependency
setup and explicit profile fixtures. The Phase 3 fast lane passed 100 methods;
the later operator/chain-chart subset passed 10. After the WAL correction, the
Phase 3 lane passed 103 methods and the affected backup/diagnostic subset
passed 24. After the private observer correction, the final lane passed
106 methods in 90.200 seconds. These include explicit fixtures and real
SQLite/process-kill tests; method counts are not live-workflow counts. Installed
client compatibility uses authenticated HTTPS file-provider fixtures and keeps
0.1/0.2/0.3 selection results distinct. Hosted CI is **NOT_OBSERVED**.

Only recorded proposals selected the commands. Native Omega/parser, actual
remember/query, E5, Chroma, DeTTa and the declared deployed owners performed
work. Offline adapter tests use recorded HTTP; a separate actual native consumer
proves generation denial. No autonomous planning or real-model usefulness is
established. The historical fifteen-family denominator and adopted-command
counts do not increase for operational or workflow evidence.

The deployment is a trusted single-node developer reference. Retained capacity
is finite, scoped C2 provenance keeps its existing application binding, current
observations are not distributed snapshots, rollback/migration and malicious-host
privacy are unsupported, and node loss/HA/multi-node/production readiness are
not qualified. Restricted assets, private synthetic archives, TLS/signing keys
and raw authenticated browser logs are excluded from publication. The original
campaign remains separate and unspent by this programme.

The dev11/chart 0.6.3 [artifact-kit installation](../../evidence/phase3/artifact-smoke-dev11.json)
used a fresh virtual environment and namespace, with the repository absent from
`PYTHONPATH`. Native agent A remembered a new synthetic fact; native agent B
queried and returned its actual authoritative payload. Real E5, Chroma and DeTTa
served these two inputs. The corrected installer bound the freshly generated
public chain identity before the inert node sealed its PVC; no chain operation
ran in this smoke test. It is separate from the retained-state qualification,
and a new local environment does not imply a different human operator.

The final dev12 [installation recheck](../../evidence/phase3/artifact-smoke-dev12.json)
used the same installed 0.3.0 operator under Python isolated mode from `/tmp`, a
fresh namespace and two additional native inputs. Remember and cross-agent
query passed against real deployed E5/Chroma/DeTTa. The node remained inert.
All task namespaces are stopped with their PVCs retained. The
[protected-resource comparison](../../evidence/phase3/protected-cleanup.json)
records the unchanged original namespaces and frozen campaign.
