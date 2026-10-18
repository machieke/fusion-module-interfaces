# Codex handoff — S04: native episodic evidence and belief-revision adoption

## 1. Objective and stopping point

Continue the completed S03.2 implementation in `machieke/fusion-module-interfaces`.
The reported starting commit is `ba48d78b3f76fb134ed9b46de2df1063f6bb16a6` (S03.1);
that commit alone is NOT the completed S03.2 tree. Resolve the actual descendant
or reconcile the working tree with `evidence/s03_2/source-state.json`, its test
manifest and final audit before editing. Read applicable AGENTS.md, the original
brief, adoption mapping, current contracts and historical evidence. Preserve
unrelated changes and restricted dependency sources.

**Proposed increment:** adopt the actual native `support` and `contradict` path
through separately owned EpisodicMemory and BeliefRevision, with a pure adapter
executing the pinned MeTTaClaw `Truth_Revision`. A subsequent native `query` must
present the committed assessment under an explicitly selected local read view.

This is the mapped **S04 episode-provenance/belief-revision** slice, not S03.3,
S05 promotion, or another general memory framework. It introduces a first
local-only cognitive-state adoption. It does not claim remote evidence-state
placement, calibrated beliefs, a complete ontology, or whole-family adoption.

**Stop at this bounded S04.** New synthetic records and fresh journals only.
No existing-history import, user-memory migration, general link/unlink, update,
forget, promotion, new inference/search rules, model-derived ontology, remote
private evidence, live channels/models, multi-host, chain, scheduler or generic
agent framework. Do not turn pure revision into a new remotely callable arbitrary
MeTTa service. Existing adopted HTTPS memory operations remain supported under
their existing disclosure rules; they are not a route for private S04 state.

The hard criterion is an actual native sequence:

    remember -> recorded source event -> support/contradict -> query

with inspectable evidence, one logical contribution per underlying source
assessment, explicit assumptions, coherent readback and recoverable delivery.
Original arithmetic is preserved on the declared admissible domain. Safer
identity/admission behavior is a documented change, not claimed universal legacy
parity.

## 2. Review basis, baseline and source discipline

The reviewer read public moving-path S03.2 reports/manifests and selected source
and tests, plus pinned MeTTaClaw source. The reviewer did NOT execute the native
suites, establish a new immutable S03.2 publication commit or independently
verify every manifest hash. Recheck findings locally against actual bytes.

S03.2 reports 158 distinct methods with passing evidence: 22 new and 136 selected
regressions. One historical source-freeze failure was followed by a 13-method
passing recheck, overlapping twelve earlier passes. The 158 is the passing union,
not one uninterrupted all-green full-repository run. Nine caller-kill and five
provider-kill phases are parameterized evidence, not fourteen additional methods.
Preserve the earlier failures and their documented corrections.

Run the applicable S03.2 baseline and an explicit impact-selected regression set.
S04 touches previously separate cognitive owners: include applicable M2, M3 and
M3.1 episode, belief, native-math, trusted-acknowledgment and closure regressions,
not just the recent 158-method adoption set. Record newly executed versus
historical/unrun evidence. Do not repeat unchanged live web/chain calls simply
to enlarge the test count.

Preserve these sources unless an actual incompatibility is documented:

- MeTTaClaw: `2af37c3fec18613de54ca42fde2382a9087d4524`.
- Its native runtime: PeTTa `fea83178af3722666d2948d074591d10a3134f56`, SWI 10.0.1
  with the recorded binary/source hash and source-checked loader.
- Chroma helper: `218484875d5d1bfb217a9a03d3983dc1ed9d406c`.
- DeTTa: `272888f264dd2dde18b574cabb53c266b0dac2ec`.
- E5: `intfloat/e5-large-v2@f169b11e22de13617baa190a028a32f3493550b6`, existing
  unprefixed normalized CPU float32 path and current SDK/model locks.
- The separate Fusion PLN/Reachability/SWI 10.1.14 profiles and their historical
  formula/source identities. Do not switch those providers to MeTTaClaw NAL.

## 3. Source and responsibility map

| Inspect | Why |
|---|---|
| `docs/omega-adoption/mettaclaw-neoclaw/{remote-placement,seam-contracts,interface-gaps}.md` | Historical S04, G04/G05/G06/G11/G12: local-first evidence, identity, numerical and provenance gaps. Do not rewrite historical mapping judgments as implementation claims. |
| Native `src/memory.metta:tvUpdate/support/contradict/getSTV/query` | Existing composite mutation, timestamp fan-out, numerical inputs and consumer presentation. |
| Native `lib_nal.metta:Truth_c2w/Truth_w2c/Truth_Revision` | Exact arithmetic and confidence cap, distinct from Fusion's existing PLN model. |
| Native `src/loop.metta`, channel/clock integration | Actual accepted input, command dispatch, history and next-context points; select a narrow new-source capture hook. |
| `fusion/{episodes,beliefs,memory_contracts,memory_types,private}.py` | Existing owners, model-specific validators, unknown state, origins, support variants and local authority. |
| `fusion/{evidence_relay,delivery_contracts}.py` and closure composition | Trusted model-independent acknowledgment, selected response validation and durable delivery recovery. |
| `fusion/adapters/{pln_revision,neoclaw_nal}.py` | Reuse guards/loader mechanics where compatible; preserve source/profile and numerical differences. |
| `fusion/{neoclaw_application,neoclaw_append,neoclaw_memory}.py` | Occurrence identities, active and retained views, budgets, captures and native handoff. |
| `fusion/adapters/neoclaw_metadata.py`, native memory startup/bootstrap | Existing metadata-only projections; these must not become belief authority. |
| `integration/neoclaw/test_append.py`, cognitive native/recovery tests | Baseline ownership, time sampling, UUIDs, view retention and actual process-kill patterns. |

Findings to verify, not assumptions to copy:

1. Native `tvUpdate` links an episode label, finds all UUIDs matching a timestamp,
   reads STVs, invokes `Truth_Revision(old, (sign, 0.5))`, then writes metadata.
   A repeated link label does not prevent another numerical update.
2. The original helper's initial `(1.0, 0.5)` is a read default. It is not an
   empirical observation and lacks historical evidence roots.
3. Native `Truth_Revision` caps output confidence at 0.99. Its source and output
   policy are not identical to `trueagi-pln-stv-finite-k1/v1`.
4. Existing C1 numeric validation, C2 support validation and parts of the relay
   recognize specific model/profile identifiers. Injecting another arithmetic
   function alone does not establish a conformant new model profile.
5. C2 currently initializes its first admissible support as an aggregate. It does
   not by that fact provide the separately typed legacy prior described below.
6. S03.2 metadata views contain default STVs and labels; its query retains a frozen
   view. Mutating a Chroma metadata row would bypass the intended authoritative owner.

## 4. Separate native compatibility from evidence correctness

Preserve the real parser and native `support`/`contradict` wrappers. Introduce the
smallest checked adapter at their shared `tvUpdate` boundary; the legacy body
must not also run its direct `set_stv` or general `link` mutation. Keep native
query selection, promotion calculation, uniqueness and rendering unchanged except
for obtaining the explicitly bound new STV/label presentation through its seam.

Use an explicit new application/profile selection and fresh journals. Preserve
historical `/1` through `/5` behavior under their stored identities. Confirm the
current catalogue before choosing another version. No unrestricted union of old
and new response shapes; no try-every-validator fallback or global MODEL patching.

The supported compatibility domain initially consists of newly created, exactly
identified memories and source events in the controlled session. Keep the native
timestamp argument syntax where unambiguous. Resolve each label through a trusted
local binding to one immutable memory identity or source event before effects.
Missing or ambiguous targets fail explicitly. Do not choose the first match,
fan out a mutation across all matching memories, or treat a timestamp as authority.
This restriction is an intentional safer profile, not historical behavior parity.

An exact grounded claim can identify the assessment of this particular immutable
memory item in a named context. Do not parse arbitrary memory text into propositions,
merge semantically similar items, infer that a paragraph is one objective fact,
or introduce variable matching. Freeze the target mapping per occurrence.

## 5. C1: record actual source occurrences, not invented provenance

Use a narrow hook in the actual controlled native input path to durably record
new generated input before a later command can cite it. The scripted channel/model
remain labelled fixtures; the native loop, C1 owner and storage must be real.

Separate at least:

- the actual source occurrence: who/what was observed, its immutable payload,
  local episode sequence, captured observed time and declared source identity;
- the application command occurrence: a turn/position asking for an assessment;
- the assessment: a typed support/contradiction of the particular target, referring
  to that already recorded source and the selected numerical/ingestion policy.

C1 records what happened; it does not decide truth. A source event can have no
numerical assessment. A `support` instruction is an agent's assessment, not proof
that the source entails the claim. The selected sign/confidence comes from the
explicit compatibility ingestion policy, not an inferred calibrated probability.

Use actual EpisodeRef/EvidenceRef and owner-issued occurrence identities. Aliases
and display timestamps are presentation data. Do not convert an old history line,
creation timestamp, hash or arbitrary caller string into a new independent source.
Do not reconstruct missing legacy history or add an `episodes` text-window service.

Use the existing provenance mechanism to keep copied/derived assessments tied to
the original source roots. Roots are issued/verified at the trusted source/owner
boundary; a new command, new wording, hash or credential cannot mint fresh roots.
If needed, add a narrow source-lineage validation extension without a universal
source registry or production channel adapter. Unknown lineage is retained as
unknown; it is not automatically sufficient for numerical aggregation.

Only the bounded new inputs are captured. Do not import the entire conversation or
replace the legacy flat-file history subsystem. A source record must be available
and authorized before its display label is exposed as an eligible evidence handle.

## 6. C2: a named native NAL profile with explicit priors and guards

### 6.1 Native arithmetic is a pure dependency

Add a separately named NAL revision profile using the original pinned
`Truth_Revision`; reconcile its exact name with the catalogue. Reuse the source-
checked native invocation machinery. Evaluate only validated numerical literals
under this one function. No arbitrary expression, file path, import, rule name,
`|-`, `|-t`, inference controller or new hosted model is accepted.

The actual native formula computes confidence-derived weights, revises strength,
and applies its own upper confidence cap. Preserve evaluation order, decimal to
native float conversion, caller-visible representation and the source cap. A test
reference calculation is permitted; replacement Python production arithmetic is not.

Specify admitted finite domains, positive total weight, parsing and output checks.
Confidence 1 and zero-total-weight singularities require explicit refusal. Strength
1 is not itself invalid. Preserve the behavior of legal high-confidence inputs,
including the output cap; do not claim monotonic uncapped evidence weight.

Independent mathematical reference cases, to be checked against the actual native
function rather than substituted for it:

| Inputs | Expected values before native decimal presentation |
|---|---|
| `(1, 1/2)` revised with `(1, 1/2)` | `(1, 2/3)` |
| `(1, 1/2)` revised with `(0, 1/2)` | `(1/2, 2/3)` |
| `(3/4, 1/2)` revised with `(1/4, 3/4)` | `(3/8, 4/5)` |
| `(3/4, 0.99)` revised with `(1/4, 0.99)` | strength approximately `1/2`; confidence `0.99`, not the uncapped value |

Test order/serialization, the native cap, invalid/nonfinite inputs, source/model
mismatch, timeout and empty/multiple/malformed native replies. Guard fixtures are
not native evaluation passes. Never relabel the old PLN profile as NAL-compatible.

### 6.2 The default is a prior, not another observation

For the fresh adopted memory, preserving the first native update requires an
explicit interpretation of its initial `(1.0, 0.5)` default. Represent this as a
**labelled compatibility prior** bound to the verified memory-creation identity
and policy. It must not receive an empirical source root, episode event, independent
observation count or fabricated provenance. Register it at most once through the
belief owner's declared authority, using a narrowly validated prior operation or
profile-specific initialization path.

Keep prior mass and actual evidence coverage distinguishable. Applying that prior
in a numerical calculation is a declared model assumption, not a statistical claim
that it is an independently observed sample. A bare `remember` does not prove its
contents. Uninitialized or historical metadata must not be imported into C2 as
observed support. No actual evidence-count field should be inferred from the native
confidence or the number of transport requests.

Define tagged prior/observed/revised support shapes where required. The existing
observation validator's nonempty empirical-root requirements must not be satisfied
with a fake prior event. Change only the selected new profile; retain old validation
and source-lock semantics. Until prior registration is committed, any default
shown by a compatibility reader must be labelled as such internally, not reported
as an admitted numerical belief.

### 6.3 Duplicates, contrary assessments and independence

Command identity and evidence identity are different. Replaying the same command
recovers the same decision. A new command citing the same source/target/assessment
must not supply another independent contribution merely because its turn changed.

Bind a contribution to immutable source provenance, exact claim/context, assessment
and numerical policy. A contrary assessment can be retained separately but shares
the original roots when it interprets the same source. Changed semantics under an
existing accepted contribution key conflict. Copied sources retain their roots.

Distinct IDs, distinct timestamps, another agent or different wording are not proof
of independence. Use explicit authorized assumptions bound to the exact admitted
supports when aggregation requires them; record them as assumptions. The positive
synthetic demonstration may declare independent sources through trusted composition.
The model cannot grant this authority through command text.

Missing/overlapping/unknown provenance retains an observation or alternative without
unjustified confidence increase. Preserve all contrary records. Recycled aggregate
or ancestor support must not become new evidence. Admission completion, numerical
revision, no-change and retained-alternative outcomes remain different.

Do not silently impose the old adapter's model identity on new NAL support. Reuse
lineage and independence guards only where their semantics fit the declared profile;
inspect model-specific checks instead of rewriting identities to fool them.

## 7. Reuse owners and trusted delivery closure

| Boundary | Owns |
|---|---|
| Application | Accepted command, alias resolution, frozen source/claim binding, budgets, result capture and read-view selection |
| Private AtomStorage | Immutable local source, claim and evidence bytes; no mathematical policy |
| EpisodicMemory | Ordered source/assessment records, lineage and durable evidence-delivery intent |
| BeliefRevision | Prior registration, contribution ledger, alternatives, immutable revisions and decisions |
| Pure native revision adapter | Proposed numbers under the pinned NAL profile; no authoritative commits |
| Trusted local relay | Exact C2 request/replay, selected response validation and narrow C1 completion acknowledgment |
| Local presentation adapter | Read-only materialization from exact owner snapshots; no independent truth authority |

Do not copy C1/C2 into `neoclaw_application.py` or implement a second journal/relay
framework. Small injected profile validators are appropriate where required. C1
may validate the declared assessment envelope but must not execute revision math.
C1 recording must remain usable without the numerical provider. The relay must
select the new C2 contract explicitly, not use an old hard-coded profile or discard
new fields until a historical validator accepts the response.

Reuse the M3.1 trusted, model-independent completion. C1 must not parse NAL priors
or belief snapshots to acknowledge a delivery. A caller-supplied success boolean,
claimed consumer name or arbitrary decision hash is not sufficient authority.

    source record -> assessment event + C1 delivery intent
                  -> C2 prior/admission/native calculation/decision
                  -> relay records validated committed decision
                  -> C1 acknowledges that delivery
                  -> local read presentation is ready
                  -> application captures native outcome

Each owner commits separately. No foreign SQL, private helper access or transaction
spanning the episode, belief and application stores. Reuse hostile declared-port
fixtures to enforce these boundaries; fixtures must not substitute for real C1/C2
or native-math integration.

## 8. Native success and subsequent query visibility

For an actual revised outcome, release the legacy `REVISION-SUCCESS` only when the
required C2 decision, delivery closure and same-session presentation readiness are
established. Describe replayed, no-change and retained-alternative outcomes with
explicit structured status; do not claim a numerical change simply because C1
accepted an event. Preserve expected legacy tokens on the compatible positive path,
but document new presentations for intentionally safer refusals/alternatives.

A subsequent `query` must obtain its STV and linked-evidence labels from the owning
records through declared reads, or from an immutable local projection validated
against those exact records. Do not execute legacy `set_stv` and then treat the
mutable metadata cache as authoritative. Arbitrary label strings are not evidence.

Extend the application read view narrowly to bind the applicable C1/C2 snapshot
references and the presentation seal. A belief-only update can create a new metadata
view while retaining the same Search generation and payload/vector source head.
Do not regenerate an embedding or rebuild the vector index just to display a new
STV. Older accepted queries retain their prior selected view and captured result.
Current authority still gates disclosure; no global atomic knowledge snapshot is
implied. Promotion/decay, candidate order and native uniqueness remain unchanged.

Record the exact adopted symbols. Two native wrappers sharing one composite
revision boundary are not two new module families. Creation-link display and this
bounded evidence linkage do not complete general Relations or `episodes` adoption.

## 9. Bounded recovery and progress

Persist source/command identities, selected numerical and owner profiles, exact
inputs and the original deadline before new effects. Use the existing application
reservation machinery and narrow owner-level guards required by the new profile.
The old C2 DTO is not automatically a deadline-aware remote execution contract:
make any needed local admission extension explicit and keep old contracts unchanged.

Recheck current authority and expected belief revision at commit, including after
native evaluation. A genuine CAS conflict requires an explicit bounded new attempt;
it does not create a new source occurrence or silently change an existing request.
No automatic deadline renewal, refunded reservations or provider/model fallback.

A crash before belief commit may repeat the pure calculation within the original
budget. After decision commit, recover the same decision and contribution without
revising again. If observing committed completion needs a narrow owner read, add it
rather than querying foreign tables or using a mutating replay to create new work
after expiry. Observation after expiry may recover prior commits, not authorize
missing event creation, calculation or presentation construction.

Partial C1 or C2 completion remains visible and recoverable. A temporary unavailable
math provider is not a final empty/no-change decision. A permanent model refusal
may close delivery under its declared contract without a truth update.

Test actual process termination after source acceptance, assessment/C1 intent
commit, native formula return before C2 commit, C2 commit before relay receipt,
C1 acknowledgment before relay progress, and presentation/result capture before
next-context consumption. Verify stable identities and exact decision/result bytes,
unchanged deadlines/budgets and one logical contribution. Distinguish fixture clocks,
transport loss and malformed-result injection from real process kills.

Exercise C1 queue backpressure and drain/reuse through the new selected profile.
Process more than one queue-capacity cumulatively in bounded batches across a few
claims when necessary to respect per-claim limits. Do not raise caps, clear queues
or create a fresh episode for every batch to hide missing acknowledgment progress.

## 10. Privacy and placement

C1, C2, their source material and native revision run locally in the first S04
profile. This follows the mapping's local-first prerequisite; a local-only gate
must not be labelled remote adoption. Existing remote query/remember tests remain
a separate supported path and do not grant new episode/provenance disclosure.

Use newly generated data and actual local owner/storage implementations. Select
local-only profiles for cognitive records; never force them into the shared-fixture
append route. Keep private claims, source roots, event contents, prior/assumption
records, belief-derived identifying hashes and journals away from remote Embedding,
Search authorization, public receipts, external search and chain. Registering a
memory reference locally does not confer access to a different scope.

The first S04 positive integration may use a fully local fresh memory corpus. A
combined existing-HTTPS-memory/private-evidence run is optional and requires explicit
scope/recipient checks; do not make it necessary to invent private-remote profiles.
Repeat existing independent HTTPS memory regressions where affected.

Add canaries to source-event content and inspect new outbound paths and diagnostics.
Input text, evidence labels and retrieved text remain data, never executable code.
No live-model prompt-injection immunity, production source authentication or malicious
host protection is claimed. Trusted local host with intact files is the failure model.

## 11. Required demonstrations and evidence

1. Establish the original native `support/contradict -> query` behavior using the
   pinned helper and NAL runtime on generated unique-label inputs. Record the native
   default and confidence cap; include an observed duplicate-update counterexample.
2. Through the real controlled native loop, create a new memory, record a genuine
   generated source event, issue `support` or `contradict`, and consume the resulting
   STV/label in the next query/context. No preseeded C2 answer or standalone helper
   bypass may pass the native-adoption gate.
3. Compare original and adapted math/positive presentation on the admitted domain.
   Separately assert intentional differences: replay deduplication, repeated-source
   handling, ambiguity refusal, no invented independence and retained alternatives.
4. Test identical command replay, a new command referencing the same evidence,
   distinct events with identical text, copied-source lineage, contrary interpretations
   of one source, wrong scope/claim/model, ambiguous labels, prior duplication,
   unknown provenance, revoked authority and credential substitution.
5. An old captured query remains on its old belief view. A new query sees the committed
   new view with no new embedding/enrollment/index build attributable to the assessment
   update itself. The query's own encoding/read work still follows its normal profile.
6. Run real owner/math recovery and queue-progress tests. Delete only the derived
   local presentation and rebuild it from owner records; do not change authoritative
   beliefs or silently refresh an already accepted query's view.
7. Demonstrate C1 without NAL and a pure native revision adapter without C1/C2. At
   least one hostile-port test rejects hidden owner internals. A second independent
   math implementation or new remote provider is not requested.

Source/model/channel fixtures, real native execution, direct-port checks, actual
loop cases and parameterized kill scenarios must remain separately classified.

## 12. Acceptance gates and deliverables

| Gate | PASS requires |
|---|---|
| BASELINE_SOURCE | Completed S03.2 bytes reconciled; applicable adoption and cognitive regressions executed; exact hashes and interpreter choices retained |
| NATIVE_ORACLE | Actual original native arithmetic/command behavior and explicit safer-profile differences recorded |
| CONTRACTS | New model/prior/assessment/identity shapes, selected validators and ownership map agree; historical profiles preserved |
| C1_PROVENANCE | Real new source/assessment capture, immutable identities/lineage, bounded reads/delivery and no invented history |
| C2_NATIVE | Actual pinned NAL revision, independent numeric oracles and correctly labelled nonempirical prior |
| EVIDENCE_GUARDS | Replay/source duplication, contrary/overlapping evidence, authorized assumptions, ambiguity and model/scope checks enforced |
| NATIVE_READBACK | Real support/contradict and later query consume the committed owner state; old views retained; no authoritative metadata bypass |
| DELIVERY_RECOVERY | Real kill/replay, trusted C1 acknowledgment, queue-capacity reuse, CAS and spent-budget behavior |
| AUTH_PRIVACY | Local-only cognitive placement, current authority, canaries and no evidence publication through existing HTTPS routes |
| COMPAT_REPRO | Fresh supported environment/session recipe, effect-based regression impact map, cache and unrun limits explicit |
| SCOPE_LEDGER | Precise S04 boundaries only; no family/product percentage promotion, remote cognitive claim, history migration or new cognition |

Deliver a single S04 report and machine-readable gate/source manifests; update
existing adoption ledger/contracts/ADRs/runbook. Include the source-to-assessment-
decision-to-query trace, coverage counts by unit, intentionally changed semantics,
failures and their corrections, partial outcomes, publication identity and remaining
limits. Retain historical reports and scope guards; document exact approved changes
instead of deleting those checks.

Do not claim full completion from C1-only or fixture-only success. Missing required
inputs are BLOCKED; incorrect executed behavior is FAIL; optional unexercised work is
NOT_RUN. Deliver useful partial work with that status rather than substituting math
or inventing prior provenance to make a gate pass.

**Then stop at S04.** Subsequent remote placement of evidence state, S05 promotion,
live model/channel startup and private-memory deployment require separate decisions.

## Review references

The paths in this brief were reviewed as public source, not proof of local execution.
Pin the actual checkout before relying on moving URLs.

```text
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/master/docs/omega-adoption/mettaclaw-neoclaw/s03_2.md
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/master/evidence/s03_2/source-state.json
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/master/evidence/s03_2/verification.json
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/master/docs/omega-adoption/mettaclaw-neoclaw/seam-contracts.md
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/master/docs/omega-adoption/mettaclaw-neoclaw/interface-gaps.md
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/master/fusion/beliefs.py
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/master/fusion/episodes.py
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/master/fusion/evidence_relay.py
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/master/fusion/memory_contracts.py
https://raw.githubusercontent.com/patham9/mettaclaw/2af37c3fec18613de54ca42fde2382a9087d4524/src/memory.metta
https://raw.githubusercontent.com/patham9/mettaclaw/2af37c3fec18613de54ca42fde2382a9087d4524/lib_nal.metta
```
