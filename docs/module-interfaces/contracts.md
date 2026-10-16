# Contracts, transport and conformance

All proposed contracts use interface version **1.0.0**, separate from provider
descriptor implementation version **0.1.1** (the unchanged deterministic
`inspect_atom` payload algorithm remains version **0.1.0**). The `1` stabilizes this experiment's semantics,
not a community standard. `fusion/ports.py` provides readable typed signatures;
`fusion/contracts.py` provides the executable M1 wire validator;
`contracts/wire.schema.json` describes requests; `contracts/responses.schema.json`
describes every operation/profile response. `fusion/responses.py` enforces
response shapes and request/descriptor-dependent invariants on both bindings.

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
| `episodic.memory` / `episode-local-sequence/1` (C1) | recordEpisode/appendEvent/readEpisode/findEpisodes. Private client-side history; append requires expected_sequence and atom refs, increments sequence atomically or CONFLICT. Event occurrence ID is distinct from payload hash; identical payloads may be distinct observations. No timestamp-based global order. Emits immutable evidence-available event after commit; replay doesn't duplicate it. Tests EP-order, EP-duplicate, EP-contrary, EP-privacy, EP-source-not-truth. |
| `belief.revision` / numerical profile pending (C2) | submitEvidence/readBelief. CAS expected_revision; owner alone updates truth/evidence aggregates. Exact model reference, evidence relationships, roots, assumptions, contradictory alternatives and provenance in each snapshot. Duplicate evidence adds no weight; overlap/derived cycles cannot invent independence. Strength/confidence/evidence-count are decimal strings interpreted by a profile, not universal arithmetic. Emits belief-revised after commit. Tests BR-duplicate, BR-overlap, BR-cycle, BR-contradiction, BR-golden, BR-unknown. |
| `pln.kernel` / rule model pending (C4) | profiles/applyRule. Pure ordered immutable premise snapshots → proposed derivation; no mutation/idempotency ledger needed. Reject unsupported model/rule/preconditions explicitly. Retain source evidence and assumptions. No agenda, revision or attention writes. Tests PLN-order, PLN-golden, PLN-purity, PLN-lineage. |
| `attention` / STI-only policy pending (C3) | submitStimulus/readAttention/select/advance. ECAN owns allocation and logical time; deduplicate stimulus key. Policy must specify stipend, finite legal values, conservation/nonconservation, saturation, decay, budget and tie-break. advance CAS expected_step, monotonic bounded steps. Atomic step plus attention-changed events; no foreign setters. Tests ECAN-no-PLN, ECAN-owner, ECAN-duplicate, ECAN-budget, ECAN-decay, ECAN-tie. |
| `inference.control` / `bounded-step/1` (C4) | step obeys candidate, rule-application, feedback-generation and deadline budgets. Reads explicit snapshots, requests revision and stimuli through their owners. Reports actual work and stop cause; durable checkpoint and replay policy required before crash-safe advertisement. No cross-owner atomic transaction implied. Tests IC-bounds, IC-feedback, IC-replay, IC-provider-swap. |
| `consensus.finality` / `asi-deploy-effects/1` | submit eligible approved commitment; observe actual deploy inclusion/effect-finality. Preserve provider evidence and tx/block IDs; distinguish not-observed/pending/included/finalized/rejected, including merge rejection. Submission idempotency must bind deploy signature/intent; no new transaction after ambiguous timeout. Finality alone does not certify off-chain bytes. CHAIN-inclusion, CHAIN-effects, CHAIN-no-synthetic. |

C2's candidate numerical model comes from reachability's existing guarded PLN
adapter; confidence is not universally clamped and truth value 1 remains a model
question. C3 does not silently wrap a multi-currency implementation as STI-only.
Specialist review remains unassigned. All cognitive test names above are future
specifications, **not executed tests**.

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
