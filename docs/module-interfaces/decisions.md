# Proposed engineering decisions (v0)

These decisions operationalize the supplied brief. They are not community
agreement on AtomSpace, PLN, ECAN or an Omega release. S1/S2 refer to the brief's
transcript ledger; the transcripts themselves were not supplied.

## ADR 001 — Identity and bytes: accepted for this prototype

AtomStorage assigns opaque UUIDs scoped by `scope_ref`, immutable revision 1.
Equal bytes in distinct creates are distinct occurrences. An idempotency key is
bound to principal, scope, interface, operation and semantic input. Reusing it
with different input is CONFLICT. Mutation message IDs are delivery identities,
not content or occurrence identities. No deletion, cross-scope merging, semantic
canonicalization, implicit ontology or LLM matching is implemented.

Wire JSON uses UTF-8; byte strings use canonical base64. Our idempotency encoding
sorts JSON object keys, uses compact separators and rejects nonfinite numbers.
It does not normalize Unicode or reorder lists. DA's existing canonical payload
and manifest encoding remains authoritative for DA commitments. SHA-256 verifies
retrieved bytes; a hash is neither permission nor proof of truth. This provider
accepts only deliberately shared, non-sensitive fixtures. Private references
need not be public content hashes; the public AtomRef is not the DA manifest ID.

## ADR 002 — Authority: accepted for the harness; production gate open

Only module methods write their owned tables. Storage has no truth/attention
columns. Episodes, beliefs and attention have definitions but no writable
service in M1. Public dispatch never exposes worker, SQL, raw DA or owner setters.
Authentication is resolved by the service from an opaque bearer credential in
the transport context. There is no caller-supplied principal/capability bundle.
Each invocation reloads the registered local scope/route policy; revocation is
effective on the next call, including reads, retries and worker runs.

This local test policy is not SCS production enforcement. Direct file access by
the same OS user bypasses it. Configuration, SQLite and DA directories are trusted
service files. The subprocess binding uses private stdin/stdout pipes, not a
publicly deployed network service. Production needs trusted service isolation,
an authenticated transport and a real enforcement adapter before private use.

## ADR 003 — Durability and recovery: accepted, bounded failure model

Each owner commits independently: AtomStorage metadata/replay, mailbox and
acknowledgement replay, and execution jobs/outbox. Wire admission replay shares
execution's journal, never the atom or mailbox store. The real atom provider uses
SQLite FULL/WAL over DeTTa FileStorage; the independent test provider uses fsync,
atomic rename and an OS lock over JSON records/payload files. Both advertise only
same-host process restart. Real DeTTa retains its actual 4+2 share reconstruction;
the fixture is one local copy and makes no DA claim.

The failure model is process SIGKILL, lost acknowledgement and temporary provider
or route unavailability on a trusted host with persistent files intact. Power
loss, disk/controller failure, multi-host failover and Byzantine operators are
outside the observed guarantee. No cross-owner atomic commit is claimed.

There are three replay stages:

1. Atom create commits bytes and its owner-local mutation fingerprint/receipt
   before returning. A wire intent digest preserves conflict detection if the
   caller's admission journal has not committed. A crash between real DA bytes
   and atom metadata can leave unreferenced bytes; deterministic DA replay recovers.
2. Execution persists a result using the worker-scoped key `result/job_id`, then
   commits terminal job state and outbox intent together in its own journal.
   Death after the atom commit leaves a queued job; retry obtains the same result
   ref/receipt, without querying or sharing the atom store's transaction.
3. Execution calls CompletionDelivery.accept. Messaging commits its own deduplicated
   delivery first; execution then records sent. Death between those commits may
   cause another acceptance attempt, not another logical completion. Deduplication
   persists even if the recipient has already acknowledged the first delivery.

The former M1 single-journal metadata/inbox atomicity is intentionally replaced
by these explicit replay stages. Poll remains at least once until acknowledgement;
physical execution may repeat. Only deterministic inspect_atom is allowed.
Temporary input loss retains the queued job; full/unavailable/revoked routes retain
the outbox. Authorization is rechecked, including current worker permissions.
No external side-effect executor, distributed transaction coordinator or scheduler
is introduced. Owner-local deduplication records persist for the store lifetime;
retention/GC and migration are deferred.

Execution's SQLite writer serializes bounded attempts; each atom/mailbox owner
has its own writer. The DeTTa adapter retains its inherited child-process file
lock, so a killed parent cannot release ownership while a DA child is writing.
Lock contention maps to OVERLOADED. The independent file fixture also uses an
exclusive nonblocking file lock. The conformance matrix exercises actual process
kills before acknowledgement and at both independent commit gaps.

## ADR 004 — Placement/privacy: accepted

Keep the DA core unchanged and application-neutral. A Rust adapter outside that
repository maps opaque byte records to an opaque DA application profile. It
imports `detta-da` and `detta-storage`, not cognitive modules. Backend-neutral
Python contracts do not import it. Composition chooses AtomStorage (real DeTTa-backed or independent file fixture),
its opaque storage backend, and a binding. In-process and subprocess service bindings share the same consumer.

Private raw episodes remain client-side in later work; encrypted private episodes
are also excluded from chain. M1 shares only generated test bytes and their result.
No IPFS/Arweave/Filecoin upload or production data is used. The optional chain
gate uses a generated fixture identity and isolated single-validator genesis;
only the approved result digest enters Rholang. DeTTa local erasure coding is real
DA-library integration, not a distributed custody test. No fabricated certificate,
transaction ID or finality.

## ADR 005 — Compatibility and reuse: accepted

Interface 1.0.0 contracts have same-major, minimum-version compatibility; profiles
are exact, versioned names. Consumers bound supported versions and reject unknown
required features, unsupported profiles and weaker guarantees. Optional extension
metadata is ignored; required extensions fail closed. Advertisements and verified
evidence are separate. Proof requirements cannot be satisfied by a proof-shaped
string. No verification provider is installed.

At M0 the workspace had only the brief; M1.1 continues that implementation. Use stdlib Python types/JSON/unittest,
as in reachability, and serde JSON in the DeTTa adapter. A static descriptor list
is a harness registry, not chain registration. The searched sibling Omega/legacy
registries do not expose the required version/profile/guarantee contract; the
discovery ledger records the search and seams. No alternate agent framework or
parallel cognitive authority is introduced.

## Deferred mathematical decisions

C2 will evaluate reachability's pinned `trueagi-pln-stv-finite-k1/v1`, including
lineage, independence and golden tests. It is not selected as a universal truth
model. C3 must select and name an STI-only policy; metta-attention's direct `setAv`
and STI/LTI/VLTI bank require an ownership wrapper and cannot silently claim that
profile. No mathematical provider or cognitive process is implemented in M1.

## ADR 006 — M1.1 seams and compatibility: accepted for this experiment

The verified review found execution depended on AtomOwner.row and concrete
get/create conventions despite published typed ports. It now depends solely on
AtomStorage.get/create and a narrow trusted CompletionDelivery.accept. Availability
is added to the published AtomStorage protocol because it was already a wire
operation; no speculative new retrieval API is introduced. Facades bind caller
context in composition, never in untrusted payload fields.

Neutral acceptance semantics use new exact `/2` messaging/execution profiles.
The `/1` local encoder preserves old response shapes and SQLite evidence labels;
wire version stays 1.0.0. Provider descriptor version is 0.1.1; the deterministic
inspect payload algorithm stays 0.1.0 so this refactor does not change result bytes.
The selected full descriptor is bound to every current binding invocation and
success reply. Live 1.x rolling interoperability is still unproven.

Separate stores require a fresh M1.1 configuration. Opening an old combined
journal is explicitly rejected as UNSUPPORTED_PROFILE rather than silently
reinterpreting metadata or dropping state. Independent replacement is demonstrated
on fresh stores, not as live data migration or instant substitution of populated
namespaces. Existing M1 evidence and presentation remain historical snapshots.

At M1.1 the intended PhysixSNET/omegahive runtime remained unavailable. The onboarding
index and separately inspected hive-appliance do not identify an executable Hive
consumer. No Omega-named wrapper around Peer is introduced. The real Omega seam
is blocked until authorized runtime source, revision and startup entrypoint exist;
see discovery and the M1.1 evidence report. M2 remains a subsequent task.

## ADR 007 — pinned native Programs seam and caller recovery (M1.2)

The user supplied `omegahive-schematics` at `4af00db4e395375484dd48d0b9068a59afcf01f8`.
Its component map names Hive revision `34b0fb3`; authorized SSH retrieval resolves
that to `34b0fb32ab3806e5609fc89bb7535518a35e1aea`. Use this revision for the bounded
engineering gate. This is not selection of the community's final product release;
the remote HEAD observed during discovery is recorded separately.

Reuse the native Programs operator action and plugin loader. The native caller
must authenticate and traverse dispatch; importing `Peer` in a test is insufficient.
Keep model and mind execution out of this deterministic gate. TestClient supplies
only an ASGI test transport around the actual app, startup lock/recovery, default
Supervisor and PeTTa. It does not substitute runtime behavior or expose a server.

The optional native `person_activity` mechanism requires named-person sessions;
its running action record can remain `in_progress` after SIGKILL. The supported
local operator action path does not own a durable receipt for this external job.
Use that existing path and a minimal plugin-owned receipt, without an upstream
patch or writes to `program_actions`. Stable request identity is supplied by the
host's command. Every retry rechecks current module authority; historical success
never grants access. One pending intent per dedicated reply route bounds recovery.

Rebaseline DeTTa from the obtainable clean historical HEAD, not the undistributed
working changes. Those changes include binary-share persistence/migration and
custody pruning beyond this opaque fresh-store slice. The clean source has 38
storage tests versus the historical dirty source's 40. Rerun conformance and
upstream tests; retain historical evidence. No live namespace or journal migration
is implied by a clean-provider pass. F1R3 source/build remains a separate gate.

Native build pins follow the inspected Hive recipe: Python 3.12, SWI 10.1.14,
PeTTa `ae66fa8`, Janus 1.5.3. Pin Python patch version and package hashes for this
tested Linux environment. Correct the CMake cache-type assumption in Fusion's
build recipe, check both live bridges, and leave upstream source unmodified.
The build recipe intentionally excludes the unrelated chromadb/mind smoke setup.

## ADR 008 — private episodic provenance and explicit admission (M2)

Accepted engineering design before implementation; execution evidence is recorded
separately. The starting checkout is `6452fa725be5a688f9d5ad8f77955579df2f95ab`,
whose only changes after `4ee5cbe` update the presentation. M1.2 regression passes
on its pinned clean sources. The five reviewed gaps are real: episode identity
and head were conflated; numerical evidence was unspecified; admission and numeric
revision had one result; context/coverage needed exact binding; the shared M1 wire
was not a private-memory profile.

C1/C2 were unimplemented 1.0.0 specifications. Their clarified local contracts use
2.0.0, `episode-local-sequence/2` and `pln-revision-private/1`. No implicit conversion
from the earlier specifications or persisted M1 journals is offered. AtomStorage
keeps its immutable bytes methods and profile, selected with a separate
`private-local-only` descriptor and one-principal private scope. M1 wire 1.0.0 and
its non-sensitive sharing requirement are unchanged; no cognitive wire route is
added. The existing resolver selects exact private descriptors. Every local call
reauthenticates the credential and checks current scope/method and selection.

An episode has a stable non-AtomRef identity and owner-controlled head (empty=0).
Events have immutable AtomRefs and sequences starting at 1. Event occurrence IDs
are unique within the owner's scope. Append binds the whole semantic request;
successful replay precedes CAS. Changed occurrence content conflicts even with a
new mutation key. Bounded pages expose captured head, next sequence and completeness.
`findEpisodes` is not advertised. A numerical observation is explicit, typed model
input attached to an event; ordinary reports create no truth. Event append and
evidence-delivery intent commit together in the episode journal.

Lineage comes from already admitted event provenance or operator-registered source
origins, never a caller's root list. Origin registration is an explicit ingestion
assumption, not proof of source accuracy or statistical independence. Aliases and
copied/reworded reports retain the same registered origin; unknown origins cannot
produce a justified numerical aggregate. C1 records history even without any
mathematical provider. C2 verifies evidence through the C1 read port and immutable
AtomStorage records, retains exact support records, and alone commits decisions.

The minimal claim fragment is an exact grounded predicate, ordered string
arguments and explicit polarity, stored immutably in the private scope. Context
and exact claim reference must match. A contrary assessment of the same claim is
an alternative, not a conversion of a negated claim. Strength/confidence are
explicit decimal strings; `evidence_count` remains unset. Aggregate coverage names
the exact leaf supports; unaggregated alternatives remain inspectable. Unknown
beliefs have no truth value. Assumption submission is distinct from occurrence
admission and binds exactly two immutable admitted supports, including an exact
derived support when used. It cannot override overlap or create fresh roots.

Atoms, episode append, belief commit and delivery acknowledgement remain independent.
A small bounded relay persists the exact attempted submission and selection before
calling C2. A CAS conflict requires a new persisted attempt/key; a timeout retains
the old attempt and pending evidence. C2 records request identity before calculation,
performs a final base-revision and live-authority check before commit, and returns
one stable decision on replay. Formula work may repeat; logical weight must not.
There is no event bus, search controller, cross-owner SQL or migration service.

Private placement is a separate local DeTTa/AtomStorage composition with local
owner journals and no messaging, execution or publication port. Generated canaries
test routing and diagnostics, not secrecy from the trusted host administrator.
There is no encrypted-storage, remote-privacy or power-loss guarantee. Existing
M1.2 generated sharing remains a separate regression.

## ADR 009 — guarded PLN reuse and explicit SWI rebaseline (M2)

Select experimental `trueagi-pln-stv-finite-k1/v1`, without claiming a universal
numerical model. Reuse `PLNAdapter.revise` unchanged from Reachability
`dd56f3f053ed90239de5377021a7d3b3fbf424ac`, obtained at an immutable source pin.
Do not import its admission/journal/projection services or invoke deduction/search.
Reuse the upstream `Truth_Revision` from PLN
`4405956947c4b53c7ff01bd565aa3b114bc970a1`, SHA-256
`cdfb3f18bd7b336440fc7b4409209afddf0e64c41f17dee7eefc8f02718de433`.

Reachability's runtime enforces SWI 10.0.1. Keep that guard and lock unchanged.
Inject a revision-only runtime with the explicit implementation profile
`fusion-petta-swi-10.1.14-revision/1`, using Hive's verified PeTTa/SWI source/build.
This is a rebaseline, not historical 10.0.1 reproduction. Before C2 implementation,
a direct native probe returned `(0.5, 0.6666666666666666)` and `(0.375, 0.8)` for
the brief's two reference pairs. Required golden, refusal, drift and timeout
checks must still pass before this profile is reported as a completed native gate.

Decimal input must be finite, in-domain before and after binary64 conversion;
strength 1 is allowed, confidence 1 is rejected. Numbers round-trip with `repr`;
no clamping, inferred values or Python substitute for revision is allowed.
Native golden comparisons use absolute tolerance 1e-12 only for valid outputs;
domain and exact support/independence checks have no tolerance. Malformed, empty,
multiple, nonfinite or rounded-to-certainty outputs fail closed. Native source,
runtime version and selected model identities are checked, and no source download
occurs in a runtime request. Missing or failed math leaves C1 available and C2
delivery pending. Source obtainability and fresh-build checks are separate gates.

## ADR 010 — bounded context-local STI and independent replacement (M3)

Starting state is clean `926882afb9ab9c7288bf663f96f9e1ca63dd8520`, descendant of
`f0cee248294a1fce42913782390e6c084025c67e` with presentation/docs and the M3 brief
only. The applicable complete M2 baseline passed before editing. Inspected
metta-attention `3e1c8147dc17299d17ab34720334fc19277cb6a9` has coupled STI/LTI/VLTI,
wages, funds and in-memory MeTTa state; it is not this bounded persistent profile.
Use `sti-additive-linear-decay/1`, explicitly a reference policy, not ECAN.

C3 local interface 2.0.0 owns scope/context state, logical step, state revision,
causal stimuli and command replay. Policy identity freezes S_max, B, d, maximum
contexts/targets/advances/causes/commands and feedback generation. Units are exact
nonnegative integer decimal strings. Saturating credit rejects atomically if it
would exceed B. Decay removes units; reads and selection do not change state.
Selection returns the full bounded eligible value vector, deterministic ranking,
logical step and state watermark. There is no atomic snapshot across owners.

Ingress and feedback use separately bound trusted-local authority roles. Ingress
has generation zero. Feedback must name a previously admitted parent stimulus;
its generation is parent+1, checked by Attention, and cannot exceed the frozen
policy cap. A target retains its highest causal generation even after decay or
new ingress; a new step ID cannot reset it. Duplicate causal identity returns its
original receipt under current authority; a changed body conflicts. Controller
feedback is a fixed success signal, never truth or empirical evidence. Explicit
operator ingress is trusted, not Sybil-resistant.

The SQLite owner and atomic-file fixture independently implement transitions;
only DTOs/validators are shared. Capacity refusal never evicts acknowledged state.
Compare unchanged consumers through hostile declared-port wrappers on fresh
stores. Provider replacement is not migration. No DA/PLN/Hive requirement exists
for C3. Private placement and current authorization apply to every operation.

## ADR 011 — historical premise vectors, owner admission and durable attempts (M3)

Use a new local C2 3.0.0 profile `pln-derived-private/1` on fresh private journals.
The M2 `pln-revision-private/1`, replay, support schema and revision-only runtime
remain supported unchanged. C3/C4 specifications become executable local 2.0.0
contracts; M1 wire stays unchanged. No existing journal selection is bypassed.

Immutable task atoms bind context and exact P/Q/R/P=>Q/Q=>R/P=>R claim roles.
Immutable worksets bind at most 16 task refs to five ordered historical
claim/revision/support references. Propositions map to exact claim-reference
digests; implication claim arguments explicitly contain those digests. Equal text
never merges two references. Output claim existence creates no truth. Selection
is frozen per step; examined invalid/unresolved tasks consume candidate budget.

The same BeliefRevision owner gains submitDerivation/readDerivation. It reads
its authoritative immutable premise snapshots, invokes a pure injected PLNKernel,
validates the proposal, and rechecks output CAS and current authority at commit.
Snapshot policy is explicitly historical-as-of-vector; no global Fusion revision
is invented. The upstream integer evaluation revision is zero, a local evaluation
identifier, with the actual premise vector retained separately.

Observation, same-claim revision and five-premise deduction are closed tagged
support variants. Coverage means local admitted support units under this new
profile; a deduction is one unit with an explicit foreign premise vector.
Evidence/roots are unioned without creating observations. Grounded ancestors
survive admission, revision and later deduction. Existing target support keeps a
new derivation as an alternative unless separately authorized revision qualifies.
Logical derivation identity is independent of step/request keys.

The kernel reuses unchanged pinned PLNAdapter.apply_rule / DeductionRule and
Truth_Deduction, including exact Python and native consistency guards. A distinct
`fusion-petta-swi-10.1.14-deduction/1` runtime permits only that rule. The revision
allowlist is not widened. Heuristic and near-one assumptions remain explicit.

C4 owns a local step journal, selection checkpoint, native-attempt reservations,
results and feedback intents. Each reservation commits before dispatch. Each C2
derivation attempt key evaluates at most once; recovery first queries it. A lost
pending attempt spends its slot; another evaluation requires another durable
slot and another attempt key. Successful decision replay needs no new slot.
max_rule_applications counts physical evaluation opportunities, not successes.
Absolute Unix-ms deadline and all counters survive restart. Provider verification
and native subprocess timeouts consume the remaining deadline; trusted same-host
wall-clock and intact files are assumed, without hard real-time/reboot promises.

Atoms, C1, C2, attention and controller commits are independent. Controller code
uses only declared ports, never foreign SQL or provider internals. A fixed causal
feedback identity comes from logical admission, not a step ID. A concurrent clock
advance may leave an explicit pending/conflicting feedback intent; no implicit
retiming or empty-belief fallback is allowed. No general scheduler/search,
migration, chain operation, LTI or research attention policy is implemented.

## ADR-012 — M3.1 delivery completion and owner-authoritative reconciliation

**Decision:** use an explicit fresh-state closure profile, a trusted local C2
completion relay, and no-credit Attention retirement. Preserve all historical
profiles and exact journal selection guards. Do not teach C1 PLN snapshot schemas.

The relay selects one closed validator adapter from the configured C2 profile.
Its durable sequence is C1 event, C2 final decision, relay decision, C1
acknowledgment, relay acknowledgment. It also recovers its committed rows when a
lost C1 acknowledgment response means those deliveries no longer appear in C1's
pending page. Authority is checked on replay; no owner writes another's journal.

Attention serializes applied receipts and bounded tombstones. Existing application
wins over deadline or staleness. If retirement wins, later delivery cannot award.
The file fixture implements its own transition logic; it shares DTO validation
only. Deadline is part of the exact feedback intent, preventing an expired effect
from being delivered with a replacement deadline. Eligible unresolved feedback
stays pending during reconciliation; reconciliation has no allocation power.

C4 keeps execution and closure observations in separate tables. It reserves each
bounded reconciliation call before I/O and commits each observation separately.
A process death can cause the same Attention resolution to be read again, but
cannot spend another inference slot or manufacture a receipt. Original execution
counts, terminal reason and deadlines are immutable. First retirement uses an
existing causal slot and command slot; existing outcomes remain readable when full.
No capacity is reclaimed and no journal migration is provided.

**Native compatibility finding:** the verified Hive request guard rejects arbitrary
parameter names ending in `_key`. The public reference is therefore
`original_command`; Hive's credential guard is unchanged. The Programs 0.1
`done/committed` envelope is retained for completed calls, while the explicitly
labelled detail distinguishes a terminated execution with zero conclusions or
pending feedback from settled delivery. Operator grants and private mappings
supply all authority; public parameters cannot attest completion.

**Consequences:** opt-in callers need fresh C1/C3/C4 journals; populated old M3
journals still replay under their original profile and cannot be reconciled through
this extension. Trusted-local-host and cooperative wall-clock assumptions remain.
No scheduler, cancellation framework, migration, new cognition or chain work.

## ADR-013 — M4 exact generated result and isolated chain observations

**Decision:** add one trusted, local `ConsensusFinality` composition under
`f1r3-generated-post-state/2`. Preserve the existing M1 port and legacy
`F1R3Commitments` implementation. New journals are required; no migration or
cognitive owner is involved. The original `fusion-inspect` plugin remains intact.
Its sibling caller-owned `completed.py` validates the accepted/acknowledged result
through current storage and execution ports, using only its own receipt SQL.

An operator allowlist binds one generated inspect command, native principal/swarm,
seed, expiry, shared scope, immutable result, descriptor, fixed operation, signer,
limits and chain identity. The chain identity is the verified source/profile plus
network, shard and genesis hash; an RPC URL is not identity. Caller parameters
cannot supply artifacts, approvals, code, credentials or network targets. Authority
is reloaded before cached replies and before sends. Revocation cannot retract a
previously transmitted deploy. No private cognitive reference is eligible.

Each owner commits separately: existing DA/execution/messaging, inspect acceptance
and acknowledgment, chain logical intent, signed deploy, submission receipt,
chain observation, and native progress. A logical intent freezes the timestamp
before signing. The complete protobuf-signed request is committed before HTTP.
Retries reuse the signed bytes; they never extend validity or reset inference
budgets. The native adapter owns only progress, and accepts neither arbitrary
transactions nor cross-owner SQL access.

The selected clean F1R3 source is `9ec1096e10774926ea8e72f0823482f0bf9213e1`
from the named fork. This is a new clean baseline, not reproduction of the old
uncommitted resource-limit changes. The build/start/API probe preceded native
implementation. No upstream consensus code was modified. An unprivileged network
namespace with loopback only and no external route contains even wildcard-bound
P2P/gRPC sockets. Host connections are tested while the node is ready.

The fixed Rholang template creates one name and sends a tuple containing the
public namespace, deliberately shareable generated operation ID and approved
digest. `/api/prepare-deploy` supplies the deterministic read name. The non-consuming
`/api/data-at-name-by-block-hash` read is bound to the matching inclusion block.
Source inspection and live probes confirm this API always reads **post-state**;
its `usePreStateHash` argument is ignored upstream, so this profile permits only
`false`. It does not claim a pre-state or current-head proof.

A finalized receipt requires the exact tuple, matching deploy/inclusion/block,
non-error execution, cost and matching `Finalized` deploy-effect state. Raw
incompatible evidence remains distinct from success. These are node observations,
not trustless proofs or a multi-validator safety demonstration. Historical profiles
and M1–M3.1 cognition, logical clocks, closure and budgets remain unchanged.

## ADR-014: M5 accepted structure and a replayable exact projection

Relations owns its accepted structural ledger and incidence, separate from the
immutable relation bytes in AtomStorage. The new schema-ordered-relations/2
profile fixes role direction and ordering; structural identity deduplicates fresh
transport keys. A payload-only interrupted assertion cannot appear in traversal.

A fresh AtomStorage 1.1.0 profile adds scoped head/readCommits. Acceptance and feed
metadata share one atom-owner transaction. The application-neutral DeTTa boundary
still handles only opaque bytes. No existing atom journal is backfilled or opened
under this profile. Legacy declarations and implementations remain unchanged.

Search 2.0.0 owns a derived exact-attributes/1 projection over typed, canonical
knowledge records. Maintenance reads only the declared feed and AtomStorage
ports. Bounded catchUp commits rows and a contiguous prefix together; beginRebuild
captures a head and changes generation. Query is read-only and distinguishes
prefix completeness, page completeness, minimum freshness and observed head.
Independent atomic-file fixtures implement their own persistence and transitions.

The lookup consumer accepts only attributes and a source barrier, discovers
relation references through paginated traversal, checks reverse incidence and
retrieves payloads. Its own private journal records progress. Native Hive accepts
an opaque label for an operator-registered private query, keeping query text out
of its existing command log. This mapping contains no expected answers. Native
receipts contain counts/status only. Search and Relations snapshots are separate;
there is no globally atomic knowledge snapshot or cognitive effect.

All stores are bounded and private. No deletion, automatic repair, scheduler,
embeddings, numerical rule changes, migration or new chain workload is included.
See [executable profile decisions](m5-contracts.md) and the
[operation ledger](m5-capability-ledger.json); final results resolve through the
M5 gate manifest rather than historical M4 passes.

## ADR-015: S03.2 append acceptance and retained native read views

The controlled native `remember` compatibility path uses existing Embedding,
immutable AtomStorage/feed and Search owners. One accepted application occurrence
owns UUID/time, captured encoding and bounded progress. An opaque binding record
precedes payload/vector/enrollment and binds their accepted meaning; storage
acceptance remains distinct from index publication and native acknowledgment.

Named Search maintenance reuses one generation and durable attempt budget across
uncertain replies. Current read-provider readiness and matching local metadata are
required before the application selects a new view. Queries bind immutable views
when accepted; later publication cannot retarget earlier queries or captures.
Deadlines and reservations are not reset by recovery. No cross-owner atomicity,
new evidence semantics, mutable memory or journal migration is implied.

These are optional versioned capabilities and fresh application profile `/5`.
Historical profiles retain their meanings. The exact contracts, partial states,
privacy boundaries and same-host evidence are in the
[S03.2 decisions](../omega-adoption/mettaclaw-neoclaw/s03_2-contract-decisions.md)
and [report](../omega-adoption/mettaclaw-neoclaw/s03_2.md).

## ADR-016: S04 source identity, compatibility priors and local belief views

The original native timestamp mutation conflates an assessment command, source
identity, linked-label update and numerical revision. The selected S04 profile
keeps the native wrappers and formula while resolving an unambiguous fresh memory
and previously captured source through trusted local application state. C1 owns
source/assessment records and lineage; C2 owns priors, contribution deduplication,
alternatives and immutable revisions. A repeat command is not independent evidence.

The fresh `(1.0,0.5)` default becomes a labelled compatibility prior with no empirical
roots or observation. Aggregation requires declared assumptions and current authority;
contrary and unknown-lineage assessments remain visible without unjustified weight.
The pure NAL adapter preserves the original cap and is a distinct numerical profile.

The existing relay and independent commits are reused. Durable native reservations
and original assessment deadlines survive restart; exact committed decisions have a
read-only recovery path. Local presentation binds owner snapshots without re-embedding
or rebuilding Search. Historical application profiles and populated state are not
reinterpreted. Cognitive state and provenance remain local. See the
[S04 contract decisions](../omega-adoption/mettaclaw-neoclaw/s04-contract-decisions.md).

## ADR-017: S05 independent wall-clock promotion and retained context

Keep native promotion under `wall-clock-promotion/1`, Attention 3.0.0, and select it only in fresh `controlled-native-loop/7` journals. Preserve original numerical expressions with the pinned native runtime. Existing STI, PLN and NAL profiles keep their numerical meanings and state owners.

Bind trusted epoch time and revision once, then atomically commit each intentional adjustment's value/time/receipt. An occurrence can replay; repeated command text can be a new occurrence. Newly bound backward samples and missing/ambiguous aliases fail. Existing read bindings remain historical. CAS conflicts are explicit; there is no retiming, refund, automatic retry or deadline extension.

Global context has an application iteration identity before a command exists. Its rank receipt, ordered AtomStorage hydration, S04 presentation and native rendered segment are captured separately. Replays reauthorize and reproduce that segment. The compatibility output file is an atomic derived write, never authority. Query keeps its native candidate ordering/merge and freezes a separate Attention snapshot at enrichment. Neither consumer rebuilds Search or changes beliefs.

Use the existing local owner/registry/policy and occurrence machinery. A second atomic-file provider implements the same transitions independently; sharing DTO checks and the pure native numerical dependency is allowed. This is bounded local adoption, not ECAN, cognitive research, scheduling, remote private placement or migration. Exact sources, limits and executed gates are in the S05 packet.

## ADR-018: S06 durable channel handoff and conservative external effects

Select `isolated-irc-mailbox/1` only in fresh `controlled-native-loop/8` journals.
Reuse immutable AtomStorage and durable Messaging; the bridge owns IRC epochs,
capture/relay progress and socket reservations, while the application owns input
assignment and native command/context handoff. External nicknames grant no Fusion
authority. Equal-text frames are distinct occurrences; replay retains identity.

Commit input ownership before mailbox acknowledgment. Keep S04 transport-source
observations local and independent of belief admission. Preserve S05 retained
context and original deadlines. Change native send presentation to `SEND-ACCEPTED`
once payload/mailbox acceptance is durable, with one approved body per occurrence.
Reserve the external attempt before writing. An interrupted reservation stays
spent and may remain unknown; recipient observation is separate evidence.

Use identical native application code with local or authenticated same-host HTTPS
channel storage/mailbox placement. Do not move cognitive owners or claim durable
IRC history, exactly-once external delivery, live-model safety or a hostile-host
sandbox. Bounds, intentional legacy differences and recovery are defined in the
[S06 contract decisions](../omega-adoption/mettaclaw-neoclaw/s06-contract-decisions.md).
