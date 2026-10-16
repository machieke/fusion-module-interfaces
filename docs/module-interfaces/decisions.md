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

SQLite FULL/WAL is the authority for accepted jobs, message acknowledgements,
idempotency and the execution outbox. DeTTa FileStorage is the payload authority.
DeTTa builds and verifies real 4+2 Reed–Solomon shares. Reads reconstruct from
persisted shares; the adapter never substitutes SQLite payload bytes.

There is no atomic commit across SQLite and FileStorage. Deterministic DA writes
are replayable, so a crash after DA write and before journal commit may leave an
unreferenced DA artifact. Retry uses the same DA coordinate and bytes. Accepted
jobs survive caller/worker death; result metadata, job completion and outbox
intent commit together. Inbox delivery and outbox completion also commit together.
Poll is at least once until explicit acknowledgement; job effects are one logical
result, not exactly-once physical computation. The only operation is deterministic
`inspect_atom`. No arbitrary external side effects can be registered.

The single SQLite writer serializes worker transitions, including bounded DA I/O.
The generic DA adapter also holds a nonblocking per-root OS file lock, inherited
by its child process, so a killed parent cannot release ownership while a DA
write is still running. Direct concurrent access returns OVERLOADED.
Busy writers return OVERLOADED. This is intentionally a small single-host harness,
not a lease-based distributed scheduler. Pending jobs/outbox and inboxes have
explicit limits; an unavailable consumer retains completion in the outbox.
Rows are retained for replay; retention/GC and multi-host recovery are deferred.
Tests cover process death, not disk failure, power loss or Byzantine operators.

## ADR 004 — Placement/privacy: accepted

Keep the DA core unchanged and application-neutral. A Rust adapter outside that
repository maps opaque byte records to an opaque DA application profile. It
imports `detta-da` and `detta-storage`, not cognitive modules. Backend-neutral
Python contracts do not import it. Composition chooses a storage port and a
binding. In-process and subprocess service bindings share the same consumer.

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

The current workspace had only the brief. Use stdlib Python types/JSON/unittest,
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
