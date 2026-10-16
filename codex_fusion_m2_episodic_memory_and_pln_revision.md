# Codex handoff — Fusion M2: private episodic provenance and bounded PLN revision

## 1. Objective, baseline and stop boundary

Continue `machieke/fusion-module-interfaces` from

`4ee5cbe8b84689a5d2432530083738b263142f90`, or record the exact descendant and

its relevant changes before starting. Read applicable `AGENTS.md`, the original

architecture brief, and the current contracts, decisions, discovery and evidence.

Preserve unrelated work and the existing scientific terminology.

\*\*Objective:\*\* implement the previously specified C1 EpisodicMemory and C2

BeliefRevision boundaries. Demonstrate a private episode with explicit evidence

lineage, duplicate-safe numerical revision, retained contrary evidence, and

recovery through one real native Hive action. Reuse the existing guarded PLN

revision implementation; do not build another reasoning engine.

\*\*Stop after M2 (C1 + C2).\*\* No ECAN/STI allocation, inference search/control,

PLN deduction workflow, LTI, promotion, summarization, LLM parser, generic query

engine, new agent framework, new transport, production deployment, live migration,

or chain work in this task. Do not add these to overcome an unavailable dependency.

M1.2 is the local integration baseline, not a reason to add another M1.x plumbing

milestone. Keep its generated `inspect` operation and existing contracts working.

The ASI:chain integration remains a separate product/demo gate; its absence does

not block private episodes or local revision and must not be relabelled a pass.

This handoff proposes one bounded engineering implementation. It does not assert

that the meetings selected a final collective AtomSpace specification, universal

ontology, numerical interpretation or product release.

## 2. Review basis and source ledger

The reviewer inspected public source and recorded evidence at the Fusion commit

above, plus the pinned reuse candidate below. The reviewer did \*\*not\*\* rerun the

suites or independently inspect the Hive runtime checkout. Recheck every finding

against the actual workspace. Source review is not an execution or security audit.

M1.2's recorded fresh runs are 90 conformance tests (including the separately

exercised 51 fixture-only tests), clean DeTTa 62 DA + 38 storage tests, 34 native

Hive baseline tests and 13 real-caller tests. The final verifier ran at

`bb22ef5e28b089b80132b40bcf5a1bbfc38b065b`; the reported final commit adds the

report/evidence without changing the tested implementation. The DeTTa 38-test

source is an intentional clean rebaseline, not reproduction of the older dirty

40-test source. Do not sum the fixture subset into the 90 again.

| Source | Inspect / preserve |

|---|---|

| `codex\_omega\_asi\_module\_interfaces\_brief.md` | Original C1/C2 scope, private client-side episodes, no private payloads on chain, model-specific revision. |

| `docs/module-interfaces/{architecture,contracts,decisions,discovery}.md` | Existing names, ownership and currently specification-only cognitive ports. |

| `docs/module-interfaces/m1\_2-evidence.md`, `evidence/m1\_2/verification.json` | Exact tested sources, native dispatch, recovery and reproduction limits. |

| `fusion/ports.py` | `EpisodeEvent`, `Episode`, `EvidenceRef`, `EvidenceSubmission`, `Truth`, `BeliefSnapshot`, `EpisodicMemory`, `BeliefRevision`. |

| `fusion/{contracts,responses,registry,policy,composition,service}.py` | Existing validation, exact-profile selection, current authorization and composition. |

| `fusion/{atoms,execution,messaging}.py` | Independent owner commits and replay; reuse patterns, not foreign tables. |

| `integration/hive/program/program.py` | Existing native caller receipt; it is not episodic memory. |

| `integration/hive/{native\_caller,test\_integration}.py` | Real authenticated Programs path, subprocess recovery and labelled counterparty. |

| `integration/hive/sources.json`, `scripts/{build\_hive,verify\_m12}.py` | Pinned native environment; extend rather than replace. |

| `machieke/reachability-atomspace-prototype` @ `dd56f3f053ed90239de5377021a7d3b3fbf424ac` | `reachability/pln\_adapter.py`, `ADAPTERS.md`, `adapters.lock.json`, `tests/test\_pln\_contracts.py`, and actual native revision integration tests. |

| `trueagi-io/PLN` @ `4405956947c4b53c7ff01bd565aa3b114bc970a1` | `lib\_pln.metta`: `Truth\_c2w`, `Truth\_w2c`, `Truth\_Revision`. |

The existing Fusion source pins identify Hive

`34b0fb32ab3806e5609fc89bb7535518a35e1aea`, clean DeTTa

`272888f264dd2dde18b574cabb53c266b0dac2ec`, and PeTTa

`ae66fa8e41dcd5539d614706bd4e5cfb34f9608d`. Use the declared obtainable inputs,

not remembered sibling paths. Preserve source-access restrictions; do not copy

private upstream source or credentials into the public repository.

Meeting basis: Kevin/Kabir 01:04:49–01:07:39 supports version-independent module

interfaces. AGI Benchmarks 00:11:14–00:12:40 distinguishes requesting another

module's work from owning its state; 00:20:56–00:23:49 proposes storage, episodic

provenance/revision, then attention and inference control. The concrete design

below is an engineering proposal, not a verbatim meeting decision.

## 3. Architecture: two state owners and a pure dependency

| Boundary | Owns | Must not own or perform |

|---|---|---|

| Private AtomStorage composition | Immutable local payloads and scoped reference metadata. | Episode sequencing, truth arithmetic, inference agendas, shared publication. |

| EpisodicMemory | Episode identity, ordered append-only event history, occurrence identity, provenance and durable evidence-delivery intent. | Belief aggregates, truth-value assignment, attention values or automatic publication. |

| BeliefRevision | Admitted support/alternative ledger, exact belief revisions, numerical aggregate basis and revision decisions. | Editing episodes, attention, selecting reasoning tasks or accepting arbitrary executable rules. |

| Guarded PLN revision adapter | No mutable domain state; explicit supports to a proposed revision and explanation. | Authoritative belief commits, creating evidence, asserting independence or running search. |

| Native Hive adapter / bounded relay | Translation, durable delivery progress where necessary, and presentation of results. | Reimplementing the owners or their mathematics; direct SQL access to their tables. |

A module is a responsibility boundary, not a mandatory separate process or

service. These modules may all run in the user's private local runtime. Consumers

receive declared, authenticated ports; composition selects implementations.

The Reachability admission service/journal and native AtomSpace projection are

not replacements for Fusion's owners. Reuse the narrow revision adapter and its

guards; do not import the full planning, certification or projection architecture.

Do not make an OpenCog C++ build, a graph database or an attention module a

prerequisite of C1/C2 when the selected revision path does not require them.

## 4. Definition of ready: resolve the executable contract gaps

Do one focused source/contract pass before implementation. Update the existing

contract catalogue and ADRs, not a parallel framework. At minimum resolve:

1. \*\*Episode identity versus head.\*\* An immutable AtomRef at revision 1 cannot

silently double as a mutable stream version. Define the stable episode identity,

its owner-controlled head/sequence, and the immutable event references.

2. \*\*Numerical input.\*\* `EvidenceSubmission` currently identifies evidence,

expected revision, profile and an optional independence reference, but has no

explicit numerical support payload. Specify a typed immutable evidence record

or explicit field from which the selected model obtains its inputs. A source

payload is not automatically a truth value. Do not guess numbers from text.

3. \*\*Results and coverage.\*\* A successful evidence admission need not produce a

numerical revision. Represent duplicate/no-change, retained alternatives,

model-inapplicable and actual revised outcomes explicitly. Identify which

supports an aggregate covers, rather than implying it covers every ledger entry.

4. \*\*Context and meaning.\*\* Bind target claim, scope/context, source occurrence,

polarity/relationship, profile, lineage and exact premise revisions. Define

which structured claims are supported; semantic canonicalization is not needed.

5. \*\*Private placement.\*\* The current M1 wire contract requires

`sharing=non-sensitive-fixture`. It is not an existing general private-memory

profile. Specify the new private local composition and any necessary profile

changes explicitly; do not route private episodes through that shared profile.

Keep the existing interface names where their semantics still fit. Cognitive

interfaces were specifications, but the repository describes them as versioned:

record any changes to their types/profiles and compatibility. Do not silently

reinterpret existing M1 1.0.0 or `/1` and `/2` receipts, weaken the descriptor

validator, or replace typed operations with `execute(anything)`.

Document each new operation's actual caller, state owner, preconditions,

authorization, limits, reply shape, idempotency, conflicts and conformance test.

Extend existing validation at boundaries used by the implementation. New local

ports still require runtime validation and current caller authority; injection

alone is not authentication. Keep pure DTOs free of backend/runtime imports.

## 5. Privacy and local payload storage

Full observations, episodes, evidence lineage and belief state derived from private

inputs remain on the private client/runtime side. All test data must be generated

and non-sensitive, but test the private routing policy rather than calling shared

fixtures private data.

Reuse the neutral AtomStorage seam with a separately scoped \*\*physically local\*\*

provider and owner-controlled authorization. A local instance over the existing

opaque persistence implementation is permissible if its private profile and

actual behavior are verified. A folder named `private` or the independent file

fixture does not by itself establish the required guarantee. Do not alter the

application-neutral DeTTa core to add episode or truth fields.

No automatic `share`, shared mailbox publication, cloud upload or chain operation

may receive private payloads, provenance or private content hashes. Local AtomRefs

must not be treated as capabilities or resolvable public references. Keep local

path/configuration details out of runtime responses not entitled to see them.

Publication is out of scope. The existing M1.2 generated-share demo remains a

separate regression; it must not become the default ingress for C1. An optional

positive share test may use an independently constructed, explicitly authorized

synthetic artifact, never a raw episode selected by a permissive export flag.

Add a private-canary test: put a unique synthetic marker into local observations,

then inspect outbound bindings, shared storage/messages, recorded traces and

normal diagnostics. The marker and unauthorized identifying derivatives must not

cross that boundary. Also test cross-principal/scope reads and replay after

revocation. State the threat model: trusted host/operator and intact local files,

not protection from a malicious host administrator or encrypted storage guarantees.

## 6. C1 — minimal episodic memory

Implement `recordEpisode`, `appendEvent` and bounded `readEpisode` using the

existing `episode-local-sequence/1` direction, with its clarified version/profile.

`findEpisodes` may offer a small declared exact-filter profile or be explicitly

unsupported and absent from advertised capabilities. Do not start a search/index

service merely to fill every proposed signature.

Each event retains occurrence identity, event kind, source attribution, observed

time, recorded order, immutable payload reference and explicit causation/provenance.

Use the existing observation/action/result vocabulary. Observed time is metadata;

only the episode owner's committed sequence orders that episode. No global clock,

global sequence or total ordering across agents is implied.

Define and test:

- Empty-episode head and sequence convention; append succeeds at the stated

expected sequence or conflicts. Two racing appends cannot both win the same head.

- Stable mutation identities bound to authenticated principal, scope, episode,

operation and semantic body. After live authorization, successful duplicate

replay is recognized before a now-stale head causes a false conflict.

- The same occurrence with changed content/provenance conflicts. A new transport

key cannot disguise an existing occurrence as new evidence. Separate genuine

occurrences may share identical bytes; a payload hash is not their identity.

- Payload commit and episode commit are distinct. Persist payloads through their

port using stable keys; after a crash recover the same logical event. A durable

atom without a committed episode append is not an acknowledged episode event.

- Explicit page limits, returned head/watermark and truncation/continuation

semantics. Never let a partial read look like a complete history.

- Contrary observations remain in history. An authenticated record that a source

asserted P is not proof of P and does not automatically create support for P.

Persist the episode append and evidence-available intent together in the episode

owner's journal. A bounded local drain/relay can deliver those typed records to

C2 after commit. It owns delivery progress, not belief state. This is a specific

replay mechanism, not a general event bus, scheduler or inference controller.

Ordinary events need not carry numerical evidence or trigger C2 at all.

## 7. C2 — narrow belief owner and reused PLN revision

### 7.1 Selected experimental model

The preferred initial provider is the existing Reachability `PLNAdapter.revise`

at the pinned source above, using `trueagi-pln-stv-finite-k1/v1` and the actual

pinned `Truth\_Revision` formula. Treat this as the selected \*\*experimental

profile\*\*, not a community-wide numerical standard. Record the choice in an ADR.

If inspected source differs, reconcile it explicitly before relying on it.

Reuse or narrowly package that adapter with source provenance; avoid an untracked

copy and an independently evolving rewrite. Do not call `PLNAdapter.apply\_rule`,

`PLN.Derive`, `PLN.Query` or other inference-search entrypoints in this increment.

The candidate's existing behaviors to preserve include finite strength in [0,1],

finite confidence in [0,1), guarded duplication/lineage handling, exact-support

independence declarations and non-mutating proposals. Recording-runtime tests are

guard tests, not evidence that a native formula ran.

Specify decimal-string parsing, float round trips, finite checks and numerical

tolerance in Fusion's profile. Strength 1 is allowed by this candidate; confidence

1 is not. Do not apply a blanket clamp below 1 to every field. Reject invalid or

rounded-to-certainty outputs instead of silently repairing them. Unknown/unset

knowledge must not become false or certain by default.

If `evidence\_count` is populated, define whether it denotes effective model

weight, an actual count or another quantity. For this candidate, confidence-derived

weight is not automatically the number of distinct event records. Leave the

optional field unset rather than invent an interpretation.

### 7.2 Runtime compatibility: a concrete prerequisite

The Reachability lock pins SWI-Prolog \*\*10.0.1\*\* and its formula runtime enforces

that pin. The new Hive build uses \*\*10.1.14\*\*. Both reference the same PeTTa commit;

that does not establish runtime equivalence.

Choose and document one bounded route:

- Reuse an obtainable, verified isolated 10.0.1 revision runtime behind the adapter,

with Hive remaining on its own tested runtime; or

- Rebaseline the narrow formula runtime on the existing 10.1.14 environment under

an explicit implementation/build profile, rerunning native golden and failure

tests before using it for C2.

Do not delete the old guard, mutate sibling locks, change Hive's global runtime or

claim historical reproduction on different bytes. Prefer an injected narrow

runtime wrapper over copying the revision mathematics. Do not require both routes.

If the necessary implementation cannot run, report `C2\_NATIVE=BLOCKED`; complete

the independent C1 work and preserve an explicit partial outcome, not a fake PLN pass.

### 7.3 Evidence admission and authoritative state

Implement `submitEvidence` and `readBelief` with owner-local durable replay and

compare-and-swap expected revision. Only BeliefRevision commits its aggregates.

Resolve the exact immutable evidence and numerical-support records through

ports, validate their origin/lineage and context, invoke the pure adapter where

applicable, then atomically commit the admission/decision, supported aggregate,

new revision, and any belief-revised intent in the belief owner's store.

The first admissible observation may initialize a profiled support snapshot, but

must retain how its numbers were obtained. A model/speaker prior is a labelled

prior, not independently validated evidence. A plain `reports` record does not

change the truth of its target. An explicit ingestion/fixture policy supplies

numeric supports; neither episodic memory nor the LLM invents them.

For the minimal supported claim fragment, use exact grounded identities and

context. Represent competing assessments of the \*\*same\*\* proposition explicitly.

Do not silently turn a support for not-P into a support for P by complementing a

number: the existing adapter rejects different conclusions. A distinct negated

claim remains distinct unless an explicit, tested conversion profile is later

introduced. Do not implement that conversion merely to broaden this demo.

A retained alternative is an admitted observation with a model outcome, not a

network error. Keep storage/admission status, numerical revision status and

execution errors separate. When no justified aggregate exists, report that state

without choosing the latest or most confident alternative behind the caller's back.

An older aggregate may remain available, but identify its exact covered evidence

and the unaggregated alternatives.

### 7.4 Independence, duplicates and contrary evidence

The exact same support adds no weight. New occurrence IDs, new keys, different

agents or different wording alone do not establish independent evidence.

Use the candidate's explicit independence declaration bound to the exact pair

of immutable support records. Preserve its recorded status as an assumption,

not proof of statistical independence. A declaration for different support bytes

or revisions is invalid. Overlapping occurrence/evidence IDs or lineage roots

retain alternatives even when independence is asserted.

Lineage must be derived from or checked against admitted immutable provenance;

a client must not mint fresh roots merely by submitting a new request. Derived

support retains its source roots. Reintroducing that support, its ancestor, or a

copied source must not increase weight. Unsupported/unknown provenance must not

be converted into independence.

Contrary evidence must remain inspectable after revision. Do not overwrite its

source event with the aggregate. Assumption admission should be distinct from

occurrence identity so later explicitly justified aggregation does not require

pretending an old observation is a newly observed one. This is not permission

for arbitrary root editing or general evidence retraction/migration.

### 7.5 Native numerical acceptance examples

Inspect the pinned formula and actual native integration fixtures. Add independent

expected-value checks, not just equality with the adapter's own output. For the

selected finite k=1 formula, these mathematical reference cases follow from

`w=c/(1-c)` and `c=w/(w+1)` for admissible independent inputs:

| Same grounded claim, explicit independence | Expected aggregate |

|---|---|

| `(s=3/4,c=1/2)` and `(s=1/4,c=1/2)` | `s=1/2`, `c=2/3` |

| `(s=3/4,c=1/2)` and `(s=1/4,c=3/4)` | `s=3/8`, `c=4/5` |

These are derived test oracles, not new empirical results or an alternative

production formula implementation. Run the actual upstream MeTTa formula through

the selected verified runtime and compare within a documented numerical tolerance.

Preserve exact domain/refusal checks; tolerance must not admit invalid inputs.

Also run same-support replay, swapped pair order, missing independence, overlapping

roots, a declaration bound to other inputs, zero total evidence weight, wrong

claim/context, nonfinite inputs, confidence=1, malformed/empty/multiple runtime

outputs, source/profile drift and timeout. Reuse the upstream guard tests but do

not count a `RecordingRuntime` returning a constant as a native golden test.

## 8. Cross-owner recovery and bounded integration

The supported flow is:

```

Native authenticated Hive action

-> private immutable input / evidence records

-> EpisodicMemory append + durable evidence intent

-> bounded delivery through BeliefRevision port

-> guarded pure PLN revision (when justified)

-> BeliefRevision admission / aggregate / decision commit

-> acknowledge evidence delivery

-> read the exact committed episode and belief snapshots

```

Atom persistence, episode append, belief commit and delivery acknowledgement are

separate observations. There is no cross-owner atomic transaction. Formula

execution is allowed to repeat after a crash; logical evidence weight must not.

At minimum inject process termination after payload persistence/before episode

append, after episode/evidence intent commit/before C2 delivery, after formula

return/before belief commit, and after belief commit/before relay acknowledgement.

After restart verify stable occurrence/support/decision identities and no lost

acknowledged event or doubled contribution. Replay the recorded semantic inputs

and model/runtime selection, not newly reconstructed guesses.

Current authority must be checked on reads, new admissions and cached replays.

Where a calculation runs outside the owner transaction, check its exact base

revision at commit. On a genuine CAS conflict, re-read and form an explicit new

attempt; never silently change expected\_revision under the same idempotency key.

The original occurrence stays the same and cannot be counted twice.

Keep pending evidence when C2 is unavailable; enforce explicit bounded capacity

or reject before promising durable acceptance. Do not acknowledge/drop delivery

because a formula timed out. Permanent model refusal may be recorded as a

completed decision without a truth update; distinguish that from temporary

unavailability. Test live revocation at a relevant replay boundary.

## 9. One real Hive episode, not another agent framework

Reuse the verified native Programs registration and authenticated dispatch at the

pinned Hive source. Add one narrowly named generated-data action or sibling plugin;

keep the original `fusion-inspect` behavior and regression suite unchanged.

Do not turn its 142-line caller-receipt implementation into the episode/belief owner.

Use generated structured input, with no LLM or private user histories. Through

actual runtime dispatch demonstrate:

1. A source report is stored as an episode event without automatically making its

reported proposition true.

2. An explicitly profiled observation supplies support for one grounded claim.

3. Request/occurrence replay does not duplicate the event or its contribution.

4. A new report copied from that origin remains visible, but does not become

independent support simply because it has a new event ID.

5. A contrary assessment of the same claim is retained. Without justified

independence it remains an alternative; a separate fixture with exact declared

independent supports exercises the numerical revision formula.

6. Replaying the derived aggregate with an ancestor cannot add evidence weight.

7. A restarted native caller recovers pending episode/revision work and reads the

same committed snapshot/decision through the module contracts.

The numeric fixture values are supplied by the declared test model, not inferred

from authentication or treated as calibrated truth about the world. This is a

provenance/revision demonstration, not evidence of autonomous reasoning quality.

Keep full data local. Do not force the episode through the M1 shared-test mailbox

to claim end-to-end reuse. Local typed owner ports are acceptable when validated,

authorization-bound and exercised. Retain the separate real-Hive/real-DeTTa M1.2

regression as evidence that the original shared integration still works.

At least one consumer/contract check must run with an independent hostile

storage/port fixture that rejects private helpers and foreign SQL. Label the

fixture as such. C1 must run without a PLN runtime, ECAN or Hive installed. A

missing mathematical provider must not prevent the module from recording history.

## 10. Acceptance gates and deliverables

| Gate | PASS evidence / honest alternative |

|---|---|

| BASELINE | Applicable M1.2 gates rerun against recorded sources; missing prerequisites distinct from executed failures. |

| CONTRACTS | New C1/C2 shapes, profiles, permissions, limits and implementation calls agree; current M1 wire behavior preserved. |

| C1 | Real persistent local episode implementation; ordered/CAS append, replay, occurrence identity, bounded reads, contrary reports and no automatic truth. |

| C1\_INDEPENDENT | C1 runs with cognition absent; hostile declared-port fixture exposes hidden implementation dependencies. |

| C2\_GUARDS | Exact support/context/model binding, unknown/alternative outcomes, duplicates, overlap and current authorization enforced. |

| C2\_NATIVE | Actual pinned upstream revision formula executes, with independent numeric oracles and validated runtime selection; otherwise BLOCKED, never fixture PASS. |

| PRIVACY | Private storage/profile and canary isolation verified; no private payload/lineage publication through shared paths or chain. |

| RECOVERY | Cross-owner process-kill/replay and CAS tests preserve each acknowledged occurrence and one logical contribution. |

| HIVE\_M2 | The new generated episode/revision flow traverses actual authenticated native dispatch, including a caller restart. |

| REPRO | Fresh-directory source/build/test recipe for the supported M2 gates; dependency identities and warm/empty-cache scope explicit. |

| SCOPE | No ECAN, inference search/control, promotion, new graph/query service, private publication, live migration or framework rewrite. |

| CHAIN | NOT\_RUN in M2; separate future same-artifact integration gate, not a hidden dependency or a current pass. |

Update the current architecture, contracts, ADRs, glossary and runbook. Deliver the

small implementation, typed/schema changes actually required, focused conformance

and native tests, one deterministic demo, and `m2-evidence.md` with a machine-readable

manifest. Record original dependency bytes and any explicit rebaseline; never

reset or publish unrelated sibling modifications.

Run new pure/local tests separately from real native tests. Keep current fixture,

DeTTa, Hive and PLN results distinguishable. Test counts follow coverage, not a

quota. Record actual failures and corrections; missing-source gates are not skips

that manufacture a green full milestone. Build only the native dependencies the

selected C2 path actually needs.

Maintain the bounded same-host process-restart claim. Do not infer power-loss

survival, distributed failover, remote privacy, exactly-once physical execution,

calibrated beliefs or AGI improvement from these tests. Fresh-source/warm-cache

reproduction is not an empty-cache or hermetic reproducibility claim.

End with exact commit/worktree state, changed files, decisions and their status,

commands/results, component classifications, model/runtime identities, observed

guarantees, limitations and gate outcomes. M2 is complete only when its required

local, native-revision and Hive gates pass. If a dependency blocks C2 or Hive,

report partial completion explicitly while delivering the independent C1 work.

\*\*Then stop.\*\* The subsequent cognitive step is C3/C4: independently profiled STI

attention and bounded inference control. That is a separate task. ASI:chain's

same-artifact commitment/execution demo is also a separate integration decision;

M2 does not prove that Hive or PLN runs on chain.

## Source locations for reviewers

Paths above are the primary source ledger. Public pinned entrypoints:

```text

https://github.com/machieke/fusion-module-interfaces/tree/4ee5cbe8b84689a5d2432530083738b263142f90

https://github.com/machieke/reachability-atomspace-prototype/tree/dd56f3f053ed90239de5377021a7d3b3fbf424ac

https://github.com/trueagi-io/PLN/blob/4405956947c4b53c7ff01bd565aa3b114bc970a1/lib\_pln.metta
