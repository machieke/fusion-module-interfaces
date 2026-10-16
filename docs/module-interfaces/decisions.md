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
