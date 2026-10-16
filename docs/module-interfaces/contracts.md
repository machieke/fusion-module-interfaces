# Contracts, transport and conformance

The M1 wire and remaining specifications use interface version **1.0.0**, separate from provider
descriptor implementation version **0.1.1** (the unchanged deterministic
`inspect_atom` payload algorithm remains version **0.1.0**). The `1` stabilizes this experiment's semantics,
not a community standard. `fusion/ports.py` provides readable typed signatures;
`fusion/contracts.py` provides the executable M1 wire validator;
`contracts/wire.schema.json` describes requests; `contracts/responses.schema.json`
describes every operation/profile response. `fusion/responses.py` enforces
response shapes and request/descriptor-dependent invariants on both bindings.

M2 adds local C1/C2 contracts **2.0.0**, implementation **0.2.0**, with a separate
private placement. Their typed DTOs are in `fusion/memory_types.py`, signatures in
`fusion/ports.py`, and closed validators in `fusion/memory_contracts.py`. There is
no new remote schema or M1 wire route. See [private M2 contracts](#private-m2-contracts).

## Shared rules

Every remote invocation carries message ID, interface ID/version, profile,
scope, operation and typed body. Mutations require an idempotency key. Send and
submit require correlation and an authorized reply route. Causation and an
absolute Unix-millisecond deadline are optional. The local clocks are one host's
clock; no distributed clock accuracy is claimed. Unknown required fields or
features fail closed. Only an `extensions` object permits ignorable additions.

The selected private stdio transport wraps one invocation as
`{credential, request, selection}` (selection is a descriptor SHA-256),
framed by stdin EOF; stdout carries one newline-terminated JSON response. It is
request/response transport plus a durable asynchronous mailbox, not streaming RPC.
The principal is derived from the service's current credential mapping, never
the body. The process operator supplies the config. Selected success responses
are `{ok: ..., provider: selection}`; errors are `{error: {code, retryable}}`.
The host retains the legacy `{credential, request}` / `{ok: ...}` frame for
explicit raw local clients; the current bindings always pin selection. Errors contain no payloads or credentials.
The same validation and live policy apply to in-process invocation.

`UNSUPPORTED_VERSION/PROFILE/OPERATION`, `INVALID_ARGUMENT`, `UNAUTHORIZED`,
`NOT_FOUND`, `CONFLICT`, `DEADLINE_EXCEEDED` are permanent for the unchanged
request. `NOT_AVAILABLE` and `OVERLOADED` are retryable with the **same key and
semantic input**. `INTERNAL` is reserved and not automatically retryable.
Transport loss means unknown outcome: retry or query the owner; do not assume
failure. An absent atom is NOT_FOUND; lost shares for an acknowledged atom are
NOT_AVAILABLE. A queued result is also NOT_AVAILABLE. Empty poll means a known
empty authorized inbox, never a transport error.

The resolver accepts a provider only within the consumer's explicit same-major
version range, exact profile, required operations/features/guarantees, payload
limit, privacy policy and any measured latency requirement. Advertised guarantees
are not proof. A required verification profile currently always fails because
there is no verifier. Same-major resolution is tested with an additive 1.2.3
descriptor fixture; actual wire dispatch currently implements **1.0.0 only**.
No speculative 1.x wire version is silently accepted. Bindings resolve fixed
consumer requirements at construction and compare the actual provider's complete
descriptor token before an invocation can have effects. The response echoes that
token. Operator configuration drift fails closed; this is trusted local consistency,
not authentication or cryptographic verification of a remote provider's claims.

## M1 operations and postconditions

| Contract/profile | Inputs → outputs | Preconditions and effects |
|---|---|---|
| `da.storage` / `opaque-local-rs/1` (internal port) | `put(scope, coordinate, bytes) → payloadID, receipt`; `get(scope, id) → bytes`; `availability(scope, id) → present shares, threshold` | Trusted adapter, 1–65,536 bytes. Stable scope+coordinate+bytes replays same DA manifest. Scope digest is bound in the generic coordinate's subject hash; mismatching scope is rejected. Existing DA profile validates opaque envelope, encodes 4+2 shares. Get verifies/reconstructs persisted shares. No auth bypass is exposed remotely; no guaranteed lifetime/remote custody. |
| `atom.storage` / `immutable-bytes/1` | `create(content_type, base64 bytes, sharing) → ref, receipt`; `get(ref) → typed envelope`; `getMany(refs) → ordered envelopes`; `availability(ref) → observation` | Scope permission; `sharing=non-sensitive-fixture`; immutable revision=1 and scoped UUID/digest. At most 32 getMany refs; all-or-error in input order. No implicit deduplication of separate creates. |
| `agent.messaging` / `durable-mailbox/2` | `send(route, ref) → acceptance`; `poll(route) → delivery or null`; `ack(route, delivery_id) → acknowledgement` | Both routes registered for scope; reply belongs to sender; only owner polls/acks. Read/validate the atom through its port. Owner-local durable acceptance precedes response; poll repeats until ack. FIFO by committed inbox sequence, no global order or exactly-once delivery. |
| `execution` / `inspect-atom/2` | `submit(operation, ref) → jobID, queued receipt`; `status(jobID) → independent observations`; `result(jobID) → result ref, storage receipt` | Only inspect_atom. Read permission for caller and worker, caller-owned reply. Result visibility only to submitting caller through job API; shared result atom remains scope-readable. Result contains digest and byte length, operation and implementation version. |

Execution states are queued, succeeded or failed. The worker's transient running
state is deliberately not observable: one execution transaction owns the bounded
job transition. Result persistence commits independently through AtomStorage
first; terminal job state and completion outbox intent then commit together. Delivery is separately `not-observed`,
`mailbox-accepted` or explicitly acknowledged through messaging. Receipt fields
never imply chain submission/inclusion/finality. Outbox retry tolerates full or
revoked reply routes; jobs rejected before durable acceptance leave no job.

Concurrency: the execution/admission SQLite writer serializes public admission
and worker transitions; AtomStorage and Messaging own separate commits/replay. Every mutation key includes principal/scope/interface/operation;
different bodies/routing/deadlines conflict. Delivery message ID, causation and
optional extensions are excluded from semantic replay fingerprints. Deduplication
records persist for the lifetime of the journal. No cross-store atomicity is
claimed; see ADR 003. A terminal deadline failure is inspectable and correlated.
Deadlines apply to new admission and worker start, not cancellation midway through
a bounded deterministic attempt. An already accepted mutation can replay its
original receipt after its deadline, so acknowledgement loss cannot hide the job.

Authentication/authorization has no events beyond policy updates, checked live.
The static registry is operator-owned configuration, has no remote mutation and
emits no runtime events. The resolver is pure. Scope IDs confer no authority.

## Cognitive specifications and optional chain boundary

The following inherit common errors, scoped authorization, mutation-key conflict
rules, immutable outputs, explicit profiles and fail-closed required features.
No cognitive provider is registered in M1. Methods and their types are in
`ports.py`. The finality row is implemented separately by the bounded local
chain adapter, with an operator-pinned generated commitment and signed-intent
SQLite journal; it is not a mandatory dependency of the M1 peers.

| Interface / profile | Behavior, ordering, concurrency and test obligations |
|---|---|
| `relations` / `ordered-roles/1` | assertRelation/getRelation/outgoing/incoming. Ordered role list, arity 1–32, every ref same scope and resolvable at assertion. Directed edge role 0 is source; later roles are targets, duplicates retained. For undirected relations the roles are still ordered in this profile; a future unordered profile must specify its own identity. Atomic immutable relation creation; incoming may explicitly be unsupported. Tests REL-order, REL-dangling, REL-scope, REL-no-truth. |
| `search` / provider-specific symbolic or embedding profile | Query returns refs, projection version, source watermark and completeness. Query grammar is selected by exact profile; no silent conversion. Rebuildable index owns no canonical records. A minimum watermark not reached is NOT_AVAILABLE; bounded pagination/snapshot rules must be declared by provider. Tests SEARCH-watermark, SEARCH-dialect, SEARCH-failure-not-empty. |
| `episodic.memory` / `episode-local-sequence/2` (C1, local 2.0.0) | Implemented private episode owner; stable identity, immutable event refs, ordered CAS append and durable evidence intent. Exact methods and bounds below. Earlier `/1` specification is unsupported. |
| `belief.revision` / `pln-revision-private/1` (C2, local 2.0.0) | Implemented explicit evidence admission and guarded native revision. Exact support/context/lineage, independent assumption registration, historical snapshots and durable semantic attempts. See below. |
| `pln.kernel` / `grounded-five-premise-deduction/1` (local 2.0.0) | Pure `profile/applyRule`: exact grounded task and ordered historical premise bindings. Guarded native Truth_Deduction only; proposals, no owner writes. |
| `attention` / `sti-additive-linear-decay/1` (C3, local 2.0.0) | Persistent bounded integer STI, scoped context clock, deterministic eligible selection, causal and transport replay. Independently runnable SQLite owner and atomic-file fixture. |
| `inference.control` / `bounded-grounded-inference/1` (C4, local 2.0.0) | Immutable workset, recorded attention selection, durable native-attempt reservations, absolute deadline and independent feedback acknowledgment. |
| `belief.revision` / `pln-derived-private/1` (C2 extension, local 3.0.0) | Fresh tagged-support journal; `submitDerivation/readDerivation` supplement evidence admission and historical reads. M2 2.0.0 remains separate and unchanged. |
| `consensus.finality` / `asi-deploy-effects/1` | submit eligible approved commitment; observe actual deploy inclusion/effect-finality. Preserve provider evidence and tx/block IDs; distinguish not-observed/pending/included/finalized/rejected, including merge rejection. Submission idempotency must bind deploy signature/intent; no new transaction after ambiguous timeout. Finality alone does not certify off-chain bytes. CHAIN-inclusion, CHAIN-effects, CHAIN-no-synthetic. |

C2 uses the pinned guarded PLN revision model described below. C3 does not
silently wrap a multi-currency implementation as STI-only. Specialist review
remains unassigned. Relations and search remain future specifications. Executed
C1/C2 cases are in the M2 report; C3/C4 and the explicit C2 extension are in the M3 report.

## Conformance mapping

`tests/test_contract.py` runs the same cases with both bindings and a separate
worker process. It covers store-without-cognition, owned state, reference integrity,
scope/route isolation, live revocation, version/profile/features, key conflicts,
SIGKILL at three recovery boundaries, bounded overload, delayed completion and
caller restart. Additional adapter tests cover actual erasure recovery, corrupt
shares, simultaneous duplicate delivery and fail-closed chain observations.

The contract imports contain no backend/cognitive dependency. DeTTa's own DA and
storage library test results, the precise dependency source hashes, command logs
and demo measurements are recorded separately in the evidence report.

## M1.1 compatibility, receipts and response validation

Live version remains 1.0.0. New exact profiles `durable-mailbox/2` and
`inspect-atom/2` use `process-restart` for bounded durable acceptance/acknowledgement,
with backend detail in `evidence` (currently SQLite WAL/FULL for those owners).
They add explicit scope, correlation and route fields where applicable. `/1`
profiles retain the original field sets and `sqlite-full` literal through an
explicit local-profile encoder. They are advertised only by the local SQLite
mailbox/execution owners; a future replacement must not inherit that claim.
Changing the profile on the same mutation key conflicts, including after an
independent atom commit. No silent reinterpretation or rolling upgrade is claimed.
Old combined M1 journal files are rejected; use fresh M1.1 stores. Migration is
not implemented. The fixed inspect algorithm version preserves deterministic
result bytes and replay identities across this refactor.

AtomStorage retains `immutable-bytes/1` and the existing scoped immutable
AtomRef/receipt shape. `local-files-process-restart` is an actual bounded storage
observation, not finality. Its provider is either `detta-local-rs/1` (real libraries)
or `contract-fixture-files/1` (independent test provider). The latter uses a single
local copy: availability reports threshold 1, never erasure coding or network
custody. DA remains application-neutral. Acceptance, result persistence, mailbox
acceptance, recipient acknowledgement and chain effect finality remain separate.

Every operation admits a closed error envelope with known code and consistent
retryability. Success validators reject missing/extra fields, unknown states,
wrong scope/reference/order, mismatched byte digests, unsupported guarantees or
receipt provider, and a token different from the selected descriptor. JSON Schema
is structural; matching to the request and negotiated descriptor requires the
runtime validator. Malformed replies become NOT_AVAILABLE, never empty poll or
success. CompletionDelivery acknowledgements receive their own shape/context
check before an outbox row is marked sent.

A binding remembers accepted job correlation. A restarted caller can recover it
from `/2` status before validating a completion. Without previously known job
context, an unsolicited mailbox completion can be structurally checked but its
correlation cannot be compared to an unknown request. This is not proof of remote
truth, authenticity or causal validity. Scope/route authorization remains live
on cached mutation retries, including acknowledgements after route reassignment.

## Exercised M1 contract map

`Mutation` contains scope/key and an optional trusted adapter intent digest. The
digest carries the full semantic wire fingerprint across independent commits;
it is not a capability or caller identity. All wire operations below use version
1.0.0. A/B are protocol fixtures; no row is an Omega integration claim.

## M1.2 native consumer, unchanged module contracts

The pinned Hive Programs plugin is an additional real consumer of the same
validated stdio boundary. Its native `inspect` action translates only generated
sample input into existing `create`, `send`, `submit`, `status`, `result`, `get`,
`poll` and `ack` operations. It adds no wire operation, profile, descriptor field,
backend branch or mathematical implementation.

The caller persists its own intent/context and accepted outcome. Reconciliation
requires the same native key and semantic input, current authorization, the
original configured selection, and status `/2` for the known job. Its pending
receipt does not imply execution or mailbox acceptance; a native `done` result
requires verified completion and successful acknowledgement. One outcome identity
may be returned repeatedly on request replay. This is logical deduplication, not
exactly-once display, physical execution or arbitrary external side effects.

| Declared method → wire operation | Owning implementation | Actual caller/context | Persistence/effect | Executed conformance |
|---|---|---|---|---|
| AtomStorage.create(Mutation, type, bytes) → create | AtomOwner or FileAtomFixture via AuthorizedAtoms | Service: authenticated requester; ExecutionOwner.work_one: bound worker | Atom owner's durable scoped replay; stable `result/job_id` worker key | Shared ContractCases + RecoveryCases, both providers/bindings |
| AtomStorage.get(ref) → get | Same atom owner | Service/requester; MessagingSession/requester; ExecutionOwner/worker with requester read permission also checked | Verified typed AtomEnvelope with bytes; no foreign metadata query | Shared contract, unavailable-input, hostile-port and response tests |
| AtomStorage.getMany(tuple) → getMany | Same atom owner | Service/requester | Ordered all-or-error envelopes | Shared contract; response order/digest tests |
| AtomStorage.availability(ref) → availability | Same atom owner | Service/requester | Current observation only; read permission required | Shared contract; response hash/shape checks |
| Messaging.send(Mutation, ref, route, correlation, reply) → send | MessagingSession → MessageOwner | Authenticated sender; registered destination and sender-owned reply | Own inbox acceptance and idempotency commit | Shared contract/recovery; neutral and legacy response tests |
| Messaging.poll(scope, route) → poll | MessagingSession → MessageOwner | Current route owner | Oldest unacknowledged delivery; no acknowledgement effect | Shared contract; completion/reference/null response variants |
| Messaging.ack(Mutation, route, id) → ack | MessagingSession → MessageOwner | Current route owner, also checked before admission replay | Own ack and replay commit | Shared contract; route-reassignment replay regression |
| DelegatedExecution.submit(Mutation, operation, ref, correlation, reply, deadline) → submit | ExecutionSession → ExecutionOwner | Requester submit/read plus worker read, requester-owned reply | Service transaction commits job admission + replay response | Shared contract; worker revocation, acceptance SIGKILL |
| DelegatedExecution.status(scope, job) → status | ExecutionSession → ExecutionOwner | Submitting requester only | Read independent execution/persistence/delivery observations | Shared contract/recovery; queued/succeeded/failed response variants |
| DelegatedExecution.result(scope, job) → result | ExecutionSession → ExecutionOwner | Submitting requester only | Persisted AtomWrite, not bytes or a chain receipt | Shared contract/recovery; receipt guarantee validation |
| CompletionDelivery.accept(scope, route, delivery_id, completion) → **no public wire operation** | MessageOwner | Trusted execution outbox; current route policy | Own idempotent durable acceptance; no foreign transaction | Post-mailbox-acceptance SIGKILL; hostile port; malformed-ack tests |

PortStructure checks signatures/types, execution's allowed calls/own SQL, and a
hostile runtime proxy that rejects all undeclared attributes. These structural
checks complement behavioral tests; they are not substituted for them.

## Private M2 contracts

This is a trusted-host local composition, with `privacy=private-local-only`,
`local-only`, `scoped`, `idempotent` and `process-restart` descriptors. Each scope
belongs to one authenticated principal. Credentials, scope membership, method
permission and complete descriptor selection are reread on every operation,
including cached replay. `belief.revision.assume` is an additional policy
permission on assumption-bearing `submitEvidence`, not a fictitious third method.
C1 acknowledgment is a trusted relay permission: its receipt is not a portable
cryptographic certificate. Local refs are identifiers, not bearer capabilities.

| Owner / operation | Input and result / ordering |
|---|---|
| C1 `recordEpisode` | Mutation + source → empty Episode, stable `{scope_ref,id}`, head 0. Same key/source returns that original creation receipt. |
| C1 `appendEvent` | Mutation + EpisodeRef + expected head + closed EpisodeEvent → immutable EvidenceRef, new head, optional delivery ID. Sequence starts at 1. A committed occurrence is recognized before stale CAS. Changed body, episode or semantic key binding conflicts. |
| C1 `readEpisode` | EpisodeRef + start (1-based) + limit → captured head, ordered immutable records, next sequence and completeness. No timestamp sorting or search. |
| C1 `readEvidence` | Exact episode/occurrence/sequence/event AtomRef → checked immutable record and admitted lineage roots. |
| C1 `pendingEvidence` / `acknowledgeEvidence` | Bounded oldest unacknowledged intents / authenticated decision receipt matching the exact evidence. Append and intent share the C1 transaction; C2 and acknowledgment do not. |
| C2 `submitEvidence` | Mutation, exact immutable claim and context, **either** evidence ref **or** already admitted support ID, expected belief revision, selected profile/runtime and optional exact pair assumption → stable RevisionDecision. |
| C2 `readBelief` | Exact claim/context and optional historical revision → immutable snapshot. Latest absent belief is explicit revision 0 with no truth; missing requested nonzero revision is NOT_FOUND. |

The executable closed shapes are `memory_types.py` / `memory_contracts.py`.
An event has occurrence ID, observation/action/result kind, source, observed time,
payload AtomRef, causation refs, provenance evidence refs and optional numerical
observation. Observed time is lexical metadata, never a distributed ordering claim.
Numerical observation names an exact claim, context, relationship
(`supports`, `contradicts`, `reports`), ingestion profile and optional typed truth.
`reports` has no truth. Source text, signatures, authorization and confidence are
never automatically converted into each other.

Claims are immutable `application/fusion-claim` envelopes containing a predicate,
1–8 ordered grounded string arguments and a Boolean positive polarity. No parser,
variable binding, unification, quantified ontology or NLP interpretation is added.
A contrary assessment supplies a low strength for the **same** claim/context;
a negated claim is a distinct immutable target, without automatic complementation.

C2 records each distinct admitted occurrence and preserves numerical alternatives.
`admission` is `admitted` or `duplicate`; `numerical` is `initialized`, `revised`,
`no-change`, `retained-alternative` or `model-inapplicable`. A new request key is
not new evidence. Registering an independence assumption references existing
supports and creates no episode observation. An initialized aggregate covers the
first eligible assessment only. Further supports remain alternatives until an
exact declared pair passes the unchanged upstream guard. Every aggregate names
its leaf coverage, exact immutable premise IDs, unioned evidence IDs and roots,
formula ID and assumptions. Belief revision increments only when its ledger or
aggregate changes. Exact successful request replay returns its original snapshot,
even after later revisions. A new-key duplicate returns the current snapshot.
For an overlapping proposed pair, `retained-alternative` reports the guard
outcome. If the candidate is an already covered ancestor, the ledger and its
alternative list can remain unchanged; the explicit coverage fields govern.

The experimental model is `trueagi-pln-stv-finite-k1/v1`: decimal-string finite
strength in [0,1], confidence in [0,1), `evidence_count=null`. Validate both Decimal
and converted binary64 domains. Strength 1 is legal; confidence 1 and values
rounding to 1 are refused. Native outputs use binary64 `repr` round trips; there
is no clamping. Tests compare valid golden values with absolute tolerance 1e-12,
never use tolerance to relax domains or support identity. The native guard and
formula pins are in `integration/pln/sources.json`; the SWI 10.1.14 runtime profile
is an explicit rebaseline of the historical 10.0.1 runner, not a claim to reproduce it.

Origins are operator-registered ingestion assumptions. Provenance references
already admitted immutable C1 records; copied evidence inherits their unioned
roots. Unknown provenance/origins cannot be repaired by a fresh request key or
speaker label. The profile conservatively treats all observations of one registered
origin as overlapping. It cannot discover undisclosed copying or prove that an
operator's asserted source identity or statistical independence is true.

Bounds: atom bytes 65,536; event JSON 16,384; provenance/causation 8 each; episode
256 events; page and pending-delivery batch 16; belief 32 observations and at most
64 support records; snapshot JSON 262,144. Relay permits three CAS retries per
drain and at most 32 persisted attempts per delivery. Exceeding capacity is
OVERLOADED, never silent truncation or loss. Mutation/decision journals retain
history without garbage collection; these per-operation bounds are not a total
disk quota. `findEpisodes`, export, attention, inference and migration are absent.

A request attempt, its expected revision and its runtime selection are durably
recorded before calculation. A CAS conflict requires a new key; changing the
expected revision under an existing key conflicts. Transient provider failure
leaves the exact attempt and C1 intent pending. Authority and base revision are
checked again before C2 commit. Formula execution may repeat after SIGKILL; the
logical contribution does not. No transaction spans AtomStorage, C1, C2 or relay
acknowledgment. Malformed foreign replies fail as NOT_AVAILABLE and never become
an empty history or an accepted numeric result.


## M3 executable private contracts

The executable DTOs are in `fusion/ports.py`; closed validators live in
`attention_contracts.py` and `cognition_contracts.py`. These are local interfaces,
not additions to the M1 shared wire. `cognition.py` selects concrete providers;
consumers receive only declared ports. Hostile proxies exercise those limits.

| Consumer | Declared foreign dependencies | Owned durable state |
|---|---|---|
| C3 Attention | PrivateAuthority only | STI, clock, watermark, causal receipts and command replay |
| PLNKernel | Verified source/runtime adapter only | None; private temporary numerical program is deleted |
| C2 derived BeliefRevision | AtomStorage, EpisodicMemory, RevisionMath, PLNKernel, PrivateAuthority | Historical tagged supports, admission attempts and decisions |
| C4 InferenceControl | AtomStorage, DerivedBeliefRevision, Attention, PrivateAuthority | Immutable step intent, selection/order, counters, reservations, results and feedback intents |
| Native Hive action | Trusted composition and these ports | Hive's existing request lifecycle; generated action uses private owner records |

C3 `Stimulus` binds command, context, target, amount, causal identity, generation,
policy hash, expected logical step, kind and parent. `select` names a bounded,
unique eligible tuple and limit; it returns the exact eligible values, sorted
positive ranking, clock, revision and eligible digest. `readAttention` returns
value/clock/revision/policy/context. Neither read mutates state. `advance` returns
scope/context/policy/clock/revision and commits clock plus decay atomically.
All units are canonical nonnegative integer decimal strings, at most 16 digits.
Defaults: Smax=100, B=300, decay=1, targets=16, advances/call=16, contexts=8,
causes/context=512, commands/owner=1024, feedback generation=3. These parameters
are part of the policy hash and journal identity. Saturation precedes total-budget
validation; over-budget writes conflict without partial changes. Capacity refusal
is NOT_AVAILABLE; acknowledged entries are never evicted. Canonical *full reference*
JSON breaks ties. Exact successful replay is checked before clock CAS, under live
authorization. A causal replay under a new transport key consumes a command slot.

Ingress and feedback use distinct trusted authority bindings, additionally checked
against live principal permissions. Fresh feedback must name the target's current
causal parent and its next generation. Decay and later generation-zero ingress do
not reduce the stored maximum generation. This prevents resetting feedback by
changing step IDs; it is not a policy for untrusted identities or arbitrary reward
sources. Different policies require different selections and fresh stores.

`InferenceRequest` includes context, immutable workset AtomRef, all four selected
provider tokens and WorkBudget. A workset has profile/context and 1–16 unique task
entries. Each entry contains an immutable task ref and five exact ordered bindings:
claim ref, context, historical belief revision and support ID. Task roles are
P,Q,R,PQ,QR,PR. Proposition entities are hashes of exact immutable refs; implication
claims explicitly name those entity IDs. Equal-looking labels never merge claims.
Kernel input contains the verified task/claim records and authoritative support
records. A historical version is never replaced by latest state. Upstream's integer
knowledge_revision=0 is a local evaluation identity, not a global ledger revision.

C2 3.0.0 support is one of three closed tags: observation (one occurrence), revision
(two local supports), deduction (five ordered foreign bindings). Every tag retains
literal, bounded ancestors, actual evidence IDs and lineage roots. Observation has
no ancestors; revision and deduction preserve the upstream union of premises and
ancestors. Deduction coverage is one *local admitted support unit*, not five target
observations. Coverage's `local-admitted-supports/1` tag makes that distinction
explicit. Deduction never appends an observation, adds a root, supplies an evidence
count, or asserts source independence. Unknown target truth may initialize from
inferential support. Existing truth retains the deduction as an alternative; only
separate authorized `submitEvidence` with an explicit independence assumption can
request guarded revision of already admitted local supports.

`submitDerivation` accepts the task, exact vector, output revision CAS, selected
kernel identity and absolute deadline. The owner persists exact semantic intent
before reads/evaluation. Logical derivation identity hashes rule profile, task ref,
vector and kernel identity, excluding request/step ID, deadline and output CAS.
Duplicate logical admission returns existing support even under another key.
Evaluation occurs outside the belief transaction; commit rechecks authorization,
logical deduplication and output CAS. Per-attempt keys evaluate at most once:
`readDerivation` returns absent, pending, complete, refused or controlled error.
A killed pending evaluation can only be tried again with a new reserved attempt
and key. Successful replay returns its original decision. An error result is
explicit; it is never an empty belief.

C4 persists its absolute Unix-ms deadline and counters before foreign work. A
candidate is counted before resolution, including rejection. A `reserved` slot is
a conservative physical evaluation opportunity: reserve before dispatch, never
refund it, and query the prior C2 decision before allocating another. Native
formula invocations can be fewer than reservations because of crashes, guard
refusals or deduplication, never more. `completed` counts validated C2 completions;
`unique_admissions` and `duplicate_admissions` distinguish logical work.
`feedback_applied` counts acknowledged unique logical credits; `feedback_duplicate`
counts duplicate admissions whose feedback was suppressed. External kill-test and
comparison instrumentation measures actual native formula attempts independently.
All feedback uses a fixed one-unit workflow reward and the logical derivation ID;
it changes neither truth nor evidence. Selection stays frozen for the step.

C4 receipts retain selection, bounded results, feedback state, remaining candidate
and rule budgets, status and reason. Reasons include workset-exhausted,
candidate-budget, rule-budget, deadline, provider-unavailable and resumable
feedback-unavailable. A clock change can leave feedback pending with CONFLICT;
no retiming is implicit. Generation-limit entries explain suppressed reward.
A completed step may have no conclusion or pending unacknowledged work. It is a
completed bounded attempt, not an assertion that reasoning succeeded.

Kernel source checks, SWI version checks and formula subprocesses consume remaining
absolute deadline; native timeout is capped by it. Controller checks time before
new work and admission rechecks after computation. Same-host wall clock, bounded
local providers and intact owner files are assumed. File I/O and process scheduling
are cooperative, not hard real-time cancellation. No reboot, power-loss, distributed
failover, all-owner transaction or live migration guarantee is advertised.

M2 profiles/DTOs and `fusion-inspect`/`fusion-episode` stay supported. M3 opens new
`derived-beliefs.sqlite`, `attention.*` and `inference.sqlite` journals. M3 does not
feed its version-3 decisions into the version-2 C1 acknowledgment DTO: generated
observation delivery intents remain available in C1. Direct M3 admission and its
own durable decisions prove replay; no incompatible acknowledgment is fabricated.

C3 mutations/selections, C4 requests and kernel inputs defensively detach nested
caller dictionaries before authorization or foreign calls. C4 also detaches
provider replies and binds their decision ID, task/output claim, logical derivation,
profile and closed outcome fields before changing progress. Boundary tests mutate
caller-owned dictionaries during authorization and inject a mismatched admission
reply, then recover the original owner decision without another reservation.

## M3.1 opt-in delivery closure

Select `delivery_closure: fusion-delivery-closure/1` in trusted local configuration.
This selects C1 interface 3.0.0 (`episode-delivery-completion/1`), Attention 2.1.0
(`sti-additive-linear-decay-closure/1`) and InferenceControl 2.1.0
(`bounded-grounded-closure/1`). C2 remains `pln-derived-private/1`; the guarded
PLN rules, arithmetic and runtime pins remain unchanged. These are closed,
explicit selections. Old profiles retain their old operations and validators.
Fresh owner journals are required; this is not a repair path for M3 stores.

C1 adds `acknowledgeDelivery(Mutation, Completion)` in place of the historical
snapshot-bearing acknowledgment. `Completion` is a closed record containing
`profile`, `state=committed`, `scope_ref`, `delivery_id`, exact `evidence`, `claim`,
`context`, `consumer={principal,provider,profile,selection}`, `request_key`,
`request_digest`, `decision_id`, and `decision_digest`. Digests are SHA-256 over
canonical values. Delivery identity hashes the EvidenceRef; decision identity
hashes `[principal,scope,request_key]`. C1 checks its own event target, the live
allowed consumer and exact replay body. It never validates a support or snapshot.
The acknowledgment receipt binds the completion digest as well as delivery and
decision identities.

Only the separately bound trusted completion context may attest. An ordinary
C1 client, including Hive, cannot clear a queue by constructing this DTO. The
existing relay observes/replays the exact authorized selected C2 request,
validates its full v2 or v3 decision using one explicit profile adapter, then
attests completion. This is local composition trust, not a signature or proof
against a hostile host. A retained alternative or report is completed processing;
processing completion does not assert truth. Pending/malformed/unavailable C2
responses do not acknowledge. Each drain handles at most 16 deliveries, at most
three CAS attempts per delivery per call, and at most 32 semantic attempts per
delivery. Existing 16-pending and 256-event episode bounds are unchanged.

`FeedbackIntent = {stimulus: Stimulus, effect_deadline_ms: integer}` binds the
original absolute deadline as part of causal semantics. Under the closure profile,
`submitStimulus` accepts ingress; `submitFeedback` accepts this deadline-bound
intent with the existing exact step/parent/generation rules. No caller can evade
the effect deadline through the old feedback operation under this profile.
`resolveFeedback(intent)` is owner-authoritative and never allocates STI:

| Outcome | Meaning |
|---|---|
| applied | Exact original durable receipt, even after deadline or decay |
| retired | Atomic no-credit tombstone: expired, obsolete-step, or obsolete-parent |
| pending / eligible | No application observed; exact intent can still be submitted before expiry |
| typed error | Unknown/unavailable/unauthorized is not evidence of absence |

A resolution contains `profile=causal-feedback-resolution/1`, exact `intent_digest`,
`outcome`, `reason`, `receipt`, and `retirement`. Retirement contains the owner's
logical step and revision. First retirement consumes one existing causal slot and
one command slot; neither bound grows. Resolving existing application/retirement
needs no new slot. Submission and retirement use the same owner transaction or
file lock. A tombstone rejects delayed same-cause submissions under any transport
key. Retirement increments the owner's revision, without moving time, STI or
causal generation. Permanent capacity exhaustion remains an explicit limitation.

C4 adds `readProgress(original_request)` and
`reconcile(Mutation, original_request, limit)` with `limit` in 1..16. Reconciliation
binds the authenticated owner, exact stored request and original selections.
It calls only `Attention.resolveFeedback` for already-recorded pending intents.
It does not invoke C2, PLN, task selection or admission. Results preserve the exact
original execution result and add a versioned feedback observation and closure
counts. A fresh reconciliation key can observe newer progress; replay of the same
key returns its original observation after current authority checks. An unfinished
call resumes its reserved bounded indices. There are at most 128 reconciliation
commands per step, with no eviction or deadline reset. Read-only progress remains
available at that limit. New-profile feedback failure terminates execution with
`feedback-unavailable`; reconciliation remains separate. Historical-profile
resumable feedback behavior remains unchanged.

The native Programs 0.1 envelope still describes completion of the **action**.
The closure-profile detail separately exposes execution status/reason, result
admission count, original counters/remaining budget, evidence backlog, feedback
closure counts and observation version. `reconcile-generated` accepts only
`original_command` (the public original action idempotency identifier) and `limit`.
The adapter's private prepared-request mapping is written before dispatch; it does
not own episode, belief, attention or controller state. Private identifiers,
supports, source roots, local paths and credentials are excluded from projections.
