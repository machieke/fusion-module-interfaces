# Codex handoff — S05: native promotion and attention adoption

## 1. Objective and stopping point

Continue `machieke/fusion-module-interfaces` from
`0d66b4b8f404450367a711de905f4a251f4b0255`, the published S04 tree,
or record the exact descendant and relevant differences. Read applicable
`AGENTS.md`, the original interface brief, the MeTTaClaw mapping, the S04
handoff, current contracts/ADRs and evidence. Preserve unrelated work.

**Proposed increment:** adopt native `promote` and `demote`, their score reads
inside `query`, and the bounded promoted-memory selection used by the actual
`getContext` path. Put authoritative promotion state behind a separately
selected Attention implementation, initially local. Preserve the native
wall-clock policy under a named profile rather than substituting reference STI.

The functional demonstration is:

    remember -> query -> promote -> query / next global context
             -> demote -> query / next global context

Promotion changes selection priority, not belief strength or evidence weight.
The same session must also preserve S04 assessment/readback. A priority change
must not rebuild the memory's vector index or numerically revise its belief.

**Stop at bounded S05.** Fresh synthetic records and journals only. No migration,
remote private attention/evidence, public endpoint, new cognitive mathematics,
full ECAN, fluid/SPH policies, inference control, learned salience, general
link/unlink, update/forget, full history, live models/channels, multi-host,
chain integration, background scheduler or framework extraction.

The mapping labels S05 local-first. This task proves a replaceable interface and
state ownership; it does not by itself claim a new network-placement result.
Do not add a sixteenth reference family. S05 belongs to Attention; the historical
15-family inventory is neither the entire Omega taxonomy nor product coverage.

## 2. Review and source discipline

The reviewer inspected selected public files and recorded evidence at the S04
publication, plus pinned native sources. The reviewer did not run the suites,
build the dependencies, or reconcile every published byte with the test manifest.
Verify findings locally before implementation. This is not a security audit.

S04 records a passing union of 228 distinct test methods: 21 new, 158 selected
adoption regressions, and 49 cognitive regressions. Corrected failures and
rechecks remain recorded. It is not one uninterrupted all-green run. Its
source manifest identifies the tested working tree on
`ecf5f48dec699a333853396e12141dc3a23720ac`; preserve that historical identity.
The later S04 publication must not be retrospectively substituted into the run.

Before editing, reconcile `evidence/s04/{source-state,test-source,final-audit}.json`
with the selected checkout and record any differences. Read the regression
impact map. Run an applicable baseline and retain real/fixture/unrun distinctions.
Do not reset dependency worktrees or rewrite old failure reports.

Keep the existing pins unless a concrete incompatibility is demonstrated:

- MeTTaClaw: `2af37c3fec18613de54ca42fde2382a9087d4524`.
- PeTTa: `fea83178af3722666d2948d074591d10a3134f56`; verified SWI 10.0.1
  and its existing executable/source hashes.
- Chroma helper: `218484875d5d1bfb217a9a03d3983dc1ed9d406c`.
- DeTTa: `272888f264dd2dde18b574cabb53c266b0dac2ec`.
- E5: `intfloat/e5-large-v2@f169b11e22de13617baa190a028a32f3493550b6`,
  the existing unprefixed normalized CPU float32 profile and asset/runtime locks.
- The independent Fusion PLN and SWI 10.1.14 profiles, and the S04 capped NAL
  revision profile. Neither becomes an attention implementation.

## 3. Source ledger and findings to verify

| Source | Inspect / preserve |
|---|---|
| `docs/omega-adoption/mettaclaw-neoclaw/remote-placement.md` | Historical S05 scope and local-first policy; its scores are design judgments, not benchmark results. |
| `seam-contracts.md`, S05 section | Draft `wall-clock-promotion/1`; named adjustment/ranking and unresolved clock semantics. |
| `src/memory.metta` in pinned MeTTaClaw | `get-promotion`, `promote`, `demote`, `best-promoted-memory-ids`, `best-promoted-memories`, `query`. |
| Native `src/helper.py` | Promotion SQLite fields and commits; UUID conversion; command parsing. |
| Native `src/loop.metta:getContext` | Global promoted content is assembled before receiving/model-processing that iteration's input. |
| Pinned `lib_chromadb.py:query_by_ids` | Requested-ID-order hydration; original helper silently omits missing IDs. |
| `fusion/{attention,attention_contracts}.py`, independent Attention fixture | Existing integer/logical-time policy, current authority, journal binding and replay patterns. Do not silently widen these contracts. |
| `fusion/{neoclaw_application,neoclaw_memory,neoclaw_append,neoclaw_evidence}.py` | Durable occurrences, ordered execution, retained views, source/assessment ownership and context handoff. |
| `fusion/adapters/{neoclaw_metadata,neoclaw_belief_presentation}.py` | Derived presentation only; no new promotion or belief authority. |
| `integration/neoclaw/{memory_bootstrap,memory_startup,native_loop,startup_overlay,loop_bridge}.py` | Checked native hooks, sealed promotion reads, and currently empty global-promoted-context fixture. |
| S04 tests, report, manifests; M3/M3.1 attention tests | Native readback, provenance, clock/causal recovery and historical-profile regression evidence. |

Verified review observations to reproduce, not assumptions to copy blindly:

1. S04 query enrichment still reads a generated read-only promotion database.
2. The controlled memory startup supplies an empty `best-promoted-memories`;
   successful S04 query readback does not exercise that global context consumer.
3. The existing C3 policy admits integer positive stimuli and logical-step decay.
   MeTTaClaw uses bounded real-valued promotion and wall-clock decay instead.
4. Native mutation labels can resolve to multiple memories, or none; the original
   wrappers do not provide the stronger occurrence/replay/ambiguity rules below.
5. Native global rendering also writes a promoted-memories file. Treat that output
   as a local derived side effect, not authoritative attention or a public artifact.

## 4. Native oracle and explicit behavioral profile

Resolve the mapping's draft `wall-clock-promotion/1` against the current catalogue.
Keep one clear name/version, selected independently of implementation. Do not
advertise `sti-additive-linear-decay/1` for this behavior or remove old guards.

The source-derived policy to verify is:

    score(v, last_time, t) = v * (1 + (t - last_time) / 86400.0) ** (-0.7)
    promote at t: store min(10.0, score + 1.0), last_time = t
    demote at t:  store max(0.0, score - 1.0), last_time = t

Missing promotion state has the native zero default. Score reads are not writes.
Caps apply to the stored adjustment result; there is no global conserved budget
or automatic redistribution between targets. An explicit demotion is not a
negative STI stimulus retrofitted into the old contract.

Run the original native wrappers and arithmetic before adapting them. Preserve
native numerical evaluation order, conversion and rendering on the admitted
finite domain. Prefer a source-checked extraction/adapter of the original
numerical expression under the existing native runtime, with only validated
numeric bindings. Reusing a pure adapter is acceptable; handwritten replacement
production arithmetic with a broad tolerance is not a parity demonstration.
The owner and consumers must not accept executable text or an arbitrary function.

A pure test reference may independently compute expected values. Include equal
clock values, fractional times, one-day and longer decay, repeated same-time
adjustments, saturation at 10, floor at zero, and mixed promote/demote order.
Test invalid/nonfinite values and conversion overflow separately from valid
numerical tolerance. Do not repair malformed values by clamping them silently.

This handoff proposes stricter behavior outside the native compatibility domain:
missing or ambiguous mutation targets fail before effects; stale trusted clock
samples and unresolved state reads fail explicitly. Record those changes as
new-profile restrictions, not unchanged legacy behavior.

## 5. Minimal Attention contract and ownership

Extend the existing Attention family with only the operations required by the
native consumers. The following are semantic requirements, not mandatory new
method names if equivalent declared ports exist:

| Operation | Required behavior |
|---|---|
| `adjust` | Exactly one +1/-1 request for a bound target and command occurrence, with expected owner revision, trusted effect time, deadline and policy selection. Return a durable receipt. |
| Snapshot / score read | Read finite scores for a bounded set of eligible opaque targets at an exact owner revision and trusted evaluation time, preserving request-to-result correspondence. |
| Bounded global ranking | Rank the authorized tracked targets in the selected context, not merely the current vector candidates; return refs, scores, rank/coverage and snapshot/time identity. |
| Adjustment observation | Recover an already committed exact receipt without applying a new mutation or requiring a new clock sample. |

A separate snapshot operation is unnecessary if existing reads can express and
validate the same guarantee. Do not introduce a general query language, global
identity registry, event bus or separate promotion microservice framework.

**Owner responsibilities:** Attention owns authoritative value/time pairs,
revision history needed by bounded retained reads, effect deduplication and
receipts. Application code owns command identity, target resolution, selected
views and result handoff. AtomStorage owns memory content. C1/C2 own provenance
and beliefs. Search owns its vector index. A local presentation cache owns none
of those facts.

An AtomRef/opaque memory target and a context are sufficient for Attention.
It must not open Chroma, parse the memory text, inspect C1/C2, infer importance
from STVs, or require E5/PLN/NAL. A pure native promotion-math dependency may use
PeTTa without loading the NAL rule library. Test the owner independently with
opaque generated targets and no cognitive store or embedding runtime installed.

Choose implementation at composition. Reuse persistence/authentication patterns
and narrow shared infrastructure, not the STI transition function with changed
constants. A sibling profile implementation is preferable to expanding a closed
integer validator until unrelated policies accidentally pass it.

DTOs must bind principal from trusted context, scope/context, selected descriptor,
policy, target, occurrence/effect identity, expected revision, clock identity,
deadline and bounded request. Responses must bind those same inputs, committed
revision and requested/applied outcome. A matching digest is not authority.

## 6. Clock, occurrence and replay semantics

**A command's identity and its text are different.** Each intentionally accepted
native promote/demote occurrence is a new adjustment, even for identical text.
Retrying one occurrence is not another adjustment. Unlike S04 evidence handling,
there is no rule that permanently deduplicates all promotion of one memory.

Persist the occurrence and resolved target before effects. Sample effect time
at the selected native adjustment point and durably bind it before calculating
or committing. Use trusted local clock/context, not model-supplied time or a
caller-selected stale timestamp. Preserve the original sample on retry.

Define and test backward-clock behavior. For this bounded profile, reject a new
sample earlier than the applicable retained owner high-water mark/last mutation;
do not let negative elapsed time increase a score or cause an invalid power.
Historical reads using already bound revisions/times remain legitimate historical
reads. Document the chosen high-water scope and tolerance explicitly. Do not
substitute monotonic elapsed time, clamp negative duration, or retime a committed
command while claiming exact wall-clock parity. A separate monotonic source may
bound timeouts, but is not the policy's epoch-time input.

Application deadlines, attention evaluation times and observed wall-clock
progress are distinct. Recovery does not extend deadlines. After expiry, an
authorized observation may recover a prior receipt; it may not apply an
unfinished adjustment, regenerate time or construct missing work under old limits.

The owner atomically commits value, last-time, revision and effect/response
identity. Do not expose separate network-like `set_value`, `set_lasttime`, and
`commit` as if they formed a safe mutation contract. A crash cannot leave one of
those authoritative fields committed without the others.

Successful replay is recognized after live authorization and before a now-stale
CAS value produces a false conflict. The same effect through another transport
key adds nothing; changed semantics under a bound identity conflict. At cap/floor,
a successful receipt must still bind the occurrence/time even when the displayed
score does not change.

Use the existing single-writer application constraint. At the owner, concurrent
requests with the same expected revision serialize: one commit or exact replay,
otherwise explicit conflict. A bounded new CAS attempt does not become a new
native occurrence; it cannot silently replace the original clock/intent. If the
frozen time is no longer admissible, report the conflict rather than spin.

## 7. Preserve both native consumers

### 7.1 Candidate-scoped query enrichment

Keep the native vector retrieval, promoted-prefix construction, tuple ordering,
merge with vector results, native uniqueness, limit and rendering. Replace only
its dependency on promotion state/score retrieval with a checked Attention port.
The native query must receive all requested candidate scores, including zeros,
not an unrelated global top list with different tie rules.

Bind an exact Attention snapshot and evaluation time at the native enrichment
point after vector retrieval. Persist the binding before using scores. A new
query can see a committed promotion; an existing query keeps its bound revision,
time, candidates and result. A replay must not decay at the restart time or use
new scores. Missing selected state is unavailable, not zero-by-default.

Preserve the application corpus/C1/C2 view independently. Promotion must not
re-enroll the memory, recompute its embedding, rebuild Search, create source
roots, update STVs or alter evidence coverage. Query-time embedding and ordinary
application/context journals are separate expected effects. Audit attribution
rather than demanding that no file anywhere changes during a full turn.

### 7.2 Actual global promoted-memory context

Remove the empty global-promoted fixture only in the new S05 composition. The
real `getContext` must invoke the adopted bounded global selection and consume
its hydrated result as `MOST_PROMOTED_MEMORIES`. Preserve the native ordering and
presentation through source-checked wrappers, not an expected-answer fixture.

This consumer runs before the model returns a command, so it cannot borrow an
uncreated command occurrence. Reuse/extend the application's durable context
preparation with a bounded context identity and captured revision/time, established
before that native context read. Capture the selected segment or exact underlying
receipts before model delivery. Recover that same segment when resuming the same
accepted context; a genuinely new iteration may sample a new view/time. This is
not exactly-once model delivery, full prompt journaling or a new scheduler.

Global eligibility is the authorized tracked memory set in the selected context,
subject to the chosen bounded corpus view. It is not the candidate set returned
by Search for a particular query. Define completeness/limits and retain old view
bindings. A high-priority item outside a selected query's candidates must still
be available to this independent global path.

Hydrate selected refs through AtomStorage in the returned order, and obtain
labels/STVs from the selected S04 owner-bound presentation. Reuse a narrow
reference-to-payload accessor; do not invoke Search with an artificial query,
read a second legacy payload database, or pass expected IDs to the consumer.
Unknown/stale refs, missing authorized content and malformed receipts fail
explicitly rather than silently disappearing from a successful result.

The native promoted-memories file is a derived private compatibility output.
Preserve its intended format for valid input, but put its path under trusted
application configuration and write/replace it safely from the captured result.
It must not be the read source or promotion authority. Recovery may reconstruct
this output from the same validated capture without reranking at current time.
Deleting it cannot erase or change attention. No export/upload route is added.

## 8. Native command adoption and coherent success

Retain native parser vocabulary and successful tokens where their stronger
preconditions hold. Resolve a timestamp alias to exactly one currently authorized
fresh memory before execution; reuse S04's trusted identity discipline. Do not
promote every collision, choose the first match, or report success for no match.
Record parser/underscore behavior from the original oracle before changing it.

An adjustment success means the owner receipt is committed and the application's
next new query/context can select the corresponding score state. Separate:

    accepted command -> committed adjustment -> application visibility
                     -> captured native result -> context consumption

Those are independent commits, not a cross-owner transaction. Keep pending,
committed-but-not-yet-visible and expired outcomes distinct. Reconciliation may
recover commits; it cannot award another increment to make the UI successful.
A score of zero or saturation is not a transport error.

The new fresh-journal composition should support sequential S03.2 writes,
S04 assessments, S05 priority changes and queries in one local controlled session.
Mixed operation types within a batch may remain unsupported explicitly. Two
same-profile priority commands in a batch must execute in order or be rejected
before either runs; do not accept an ambiguous partial batch.

Keep old `/1` through `/6` profiles and their startup/output behavior unchanged.
Choose the new version after inspecting the actual catalogue. Do not modify
existing private or read-only journals, replace seals in place, or automatically
migrate older promotion databases. Existing HTTPS memory regressions remain a
separate placement track; combining them with private S04/S05 state is not required.

## 9. Independence, privacy and failure handling

Demonstrate one independent, same-policy Attention test provider, preferably a
bounded atomic-file fixture alongside the primary persistent owner. It must not
inherit the first implementation's state transitions, access its tables or call
its private helpers. Shared DTO validation and the same pure numerical dependency
are permissible; independently check transition and replay invariants.

Run the same consumer/contract cases against both on fresh stores with identical
inputs and clocks. At least one complete native sequence must use the alternate
provider through composition only. This is provider substitution, not policy
competition, hot swapping or state migration.

Use hostile port-only wrappers; forbid legacy promotion-map read/write helpers in
the adopted path. The original oracle and explicitly historical profiles can still
use their real helper. Do not globally remove old code to conceal a fallback.

Keep attention state, identifiers, selected ranks and cognitive labels local.
Neither existing encoder/search authorization nor a shareable payload grants
permission to disclose private priority metadata. Observe current authority on
new effects, snapshot/rank reads, mutation observations, cached replay, hydration
and context release. Substitution of another authorized principal must not
release or modify the original occurrence.

An unavailable owner is not an empty priority map. Do not fall back to sealed
legacy scores, integer STI, arbitrary cached context, or default priorities to
hide an error. Input and retrieved text remain data, never evaluation code.
Use canaries in local priority/context data and inspect all existing outbound
bindings, generated provider stores and normal diagnostics. Private local trace
files must remain correctly scoped. Trusted host/intact files is the threat model.

Bound targets, retained revisions, receipts, contexts, rank inputs/results and
per-call work. Exhaustion is explicit; no silent eviction of an acknowledged
receipt or retained query snapshot. Do not add garbage collection or increase
unrelated historical caps merely to fit tests. No unbounded numerical subprocess
per candidate without a declared total bound; a bounded batched score calculation
is acceptable if it preserves the numerical policy.

## 10. Required acceptance scenarios

Use original native execution, adapted primary provider and independent provider.
The positive application paths retain real MeTTaClaw/PeTTa/SWI, actual E5, Chroma,
DeTTa and S04 owners where exercised. Model responses, channel inputs and clocks
may be fixtures, explicitly labelled. Native numerical and context outputs must
not be supplied by those fixtures.

The generated corpus must contain multiple useful candidates, unequal similarity,
varied belief metadata, an unpromoted record, a separately scoped record, and a
promoted memory outside one query's vector candidate set. Fix generated IDs/times
or document correspondence for the original/adapted comparison.

Required evidence:

1. Original and adapted admissible priority values, adjustment order, query order,
   global rank order and native text agree at the same clock and initial state.
   Show a changed presentation order, not just a changed number in a database.
2. Actual promote/demote commands alter a later query and global context without
   operator configuration edits. Native getContext sees the new segment.
3. A query's own candidate set does not expand just because an out-of-candidate
   memory is highly promoted; the independent global context can include it.
4. Query-specific and global tie cases preserve their distinct native semantics.
   Cover positive filtering, saturation, floor, decay, missing state and empty sets.
5. Retries add nothing. New intentional occurrences may each adjust. Identical
   timestamp labels on different memories refuse before any mutation.
6. A new priority command cannot modify S04 truth/provenance. An S04 assessment
   cannot modify priority. Intersperse both and verify their next-context results.
7. An old query/context capture remains reproducible after later adjustments and
   elapsed time. A new context sees newer state under its own clock binding.
8. Delete only a derived promoted-context output, recover it through authorized
   captured records, and verify unchanged promotion and belief journals.
9. Exercise wrong scope/principal/profile, malformed numeric/snapshot replies,
   revoked authority before commit/disclosure, clock rollback, capacity limits,
   same-key changed intent, concurrent CAS, missing payload and provider outage.

Use actual SIGKILL tests at new durable boundaries, including accepted occurrence
and clock before adjustment; after pure evaluation before commit; after owner
commit before caller receipt; after visibility selection before native result
capture; after result capture before next-context consumption; and after a global
context selection/capture before its handoff. Reopen the same owner/app journals.
Assert stable effect identity, original time/deadline, original spent budgets,
owner revision and exact captured outcome. Record parameterized cases separately
from distinct methods.

Pure math may repeat before commit under the original bounds; committed adjustment
must never repeat. At least one expired recovery should retrieve an already
committed receipt while refusing a new effect or missing post-deadline work.
Do not create unlimited new context-preparation attempts on every restart.

## 11. Regression, gates and deliverables

Run an impact-selected baseline/final set covering S04's new owners and application,
S03.2 retained views, existing query/embedding/append HTTPS boundaries and the
historical M3/M3.1 Attention policies and feedback closure. Preserve original
source/profile guards; identify approved new paths rather than removing guards.
Unchanged live web or chain gates need not rerun just to increase a count. Do not
call a selected subset the entire repository suite.

| Gate | PASS requires |
|---|---|
| BASELINE_SOURCE | Publication/test-hash relationship, pinned runtime and explicit regression impact map. |
| NATIVE_POLICY | Actual original oracle; native arithmetic/parity and explicit domain/safer behavior. |
| ATTENTION_CONTRACT | Separate selected policy, state owner, complete bound operations and current authority. |
| ADJUST_REPLAY | Durable occurrence/clock/CAS; atomic value/time/receipt; retry versus new occurrence. |
| QUERY_ADOPTION | Actual query uses owned scores and preserves native candidate/ranking/rendering semantics. |
| GLOBAL_CONTEXT | Non-fixture promoted-memory selection and verified hydration consumed by actual native getContext. |
| INDEPENDENT_PROVIDER | Same-profile independent provider and unchanged consumer, plus no foreign-store dependency. |
| VIEWS_RECOVERY | Real kills, retained revision/time/result, context capture and unchanged deadlines/budgets. |
| AUTH_PRIVACY | Local scope, current disclosure/effect authority, canaries, malformed responses and no fallback. |
| OWNER_COMPAT_REPRO | C1/C2 and Search unaffected by priority; old profiles and declared fresh-target recipe pass. |
| SCOPE_LEDGER | Exact adopted writes/reads/context seams, test accounting and placement limits; no whole-product claim. |

All required gates, including native global context and provider replacement,
must pass for full bounded S05 completion. Missing sources/runtime are BLOCKED;
wrong executed behavior is FAIL; deliberately untested extras are NOT_RUN.
Deliver useful partial work when blocked without a fixture-based native PASS.

Update existing architecture/contracts/ADRs, adoption ledger and runbook. Provide
one S05 report, machine-readable gates/source manifests, original/adapted trace,
priority/identity/view timeline, precise fixture labels and retained development
failures/corrections. Count new native commands, internal adopted boundaries,
unique methods and repeated scenarios separately. Do not infer a whole Attention
adoption percentage or higher cognitive quality from the positive test.

Record observed native call cost and context-preparation overhead where convenient,
but do not invent performance targets or claim remote compute savings. Disclose
warm/reused build artifacts and caches. No need for an empty-cache rebuild merely
to implement priority semantics. Record final tested bytes and any later
publication/evidence-only commit without relabelling old runs.

**Then stop at S05.** The supported claim is a controlled native Omega whose
priority mutations, query enrichment and global promoted context use a separately
owned, replaceable local Attention profile. Full ECAN, remote private attention,
live Omega, migration and broader cognition remain separate decisions.

## 12. Source references

The concrete design above is a proposed next task. The meetings support granular
interfaces and owner-only state changes, not this particular promotion policy.
Meeting references: Kevin/Kabir 00:13:36 and 00:16:54, 01:04:49–01:07:39;
AGI Benchmarks 00:07:19 and 00:11:14–00:12:40.

Pinned public sources used for the review:

```text
https://github.com/machieke/fusion-module-interfaces/tree/0d66b4b8f404450367a711de905f4a251f4b0255
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/0d66b4b8f404450367a711de905f4a251f4b0255/docs/omega-adoption/mettaclaw-neoclaw/s04.md
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/0d66b4b8f404450367a711de905f4a251f4b0255/evidence/s04/verification.json
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/0d66b4b8f404450367a711de905f4a251f4b0255/docs/omega-adoption/mettaclaw-neoclaw/seam-contracts.md
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/0d66b4b8f404450367a711de905f4a251f4b0255/fusion/attention_contracts.py
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/0d66b4b8f404450367a711de905f4a251f4b0255/integration/neoclaw/memory_startup.py
https://raw.githubusercontent.com/patham9/mettaclaw/2af37c3fec18613de54ca42fde2382a9087d4524/src/memory.metta
https://raw.githubusercontent.com/patham9/mettaclaw/2af37c3fec18613de54ca42fde2382a9087d4524/src/helper.py
https://raw.githubusercontent.com/patham9/mettaclaw/2af37c3fec18613de54ca42fde2382a9087d4524/src/loop.metta
https://raw.githubusercontent.com/patham9/petta_lib_chromadb/218484875d5d1bfb217a9a03d3983dc1ed9d406c/lib_chromadb.py
```
