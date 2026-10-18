# S03.2 append-only native memory decisions

Starting source: `ba48d78b3f76fb134ed9b46de2df1063f6bb16a6`, the published S03.1
implementation. Its 21 implementation, 29 non-evidence and 60 evidence hashes
match. The 21-file test manifest also matches the preserved frozen manifest.
Removing exactly the two documented `Path.resolve` statements reconstructs the
one earlier test-source hash. No historical run has been renamed or rerun under
its old evidence identity. See `evidence/s03_2/baseline-source.json`.

## Observed native semantics

The original controlled native loop has executed `query`, `remember`, then `query`
against a new generated corpus with the pinned native E5 and Chroma 1.5.5. The
original `createMemory` samples time before `embed`; the helper creates a random
UUID, stores the raw string/vector/time, and then appends the creation-time label.
There are no stored strength/confidence fields initially: native reads return
`(1.0, 0.5)`. There is no promotion row: value and last-time both default to zero.
The label and defaults are compatibility metadata, not episodes or belief evidence.
The supported SDK accepts the helper's list-valued linked-label metadata.

The adopted source overlay retains the original `remember`, `createMemory`,
`embed`, `string-safe`, and query/enrichment composition. Only the selected time,
append helper and creation-link boundary are routed to application-owned recovery.
Raw payload text and the actual post-`string-safe` helper string are bound separately.
Clock fixtures are explicit in parity runs. UUIDs correspond by occurrence, not by
accidental equality between independently executed original/adapted processes.

## Profiles and ownership

The catalogue has no pre-existing `/5` application profile. Fresh
`controlled-native-loop/5` adds only append-only `remember`; `/1` through `/4` keep
their existing bindings and refusal of unsupported mutations. A populated old
application cannot be reopened as `/5`. The extension does not rename mapping S04
or increase the historical fifteen-family denominator.

Memory text uses `neoclaw-e5-memory-text/1`, with separate
`embedding.memory.encode` and `embedding.memory.disclose` permissions and an exact
operator-approved raw/helper map. Historical `neoclaw-e5-query-text/1` is unchanged.
Both purposes retain the same pinned unprefixed normalized CPU float32 E5 path.
The SDK/model source and numerical profiles are not rebaselined.

The application owns accepted occurrence, UUID/time, vector capture, bounded call
reservations, write progress, and coherent read-view selection. Embedding owns its
physical evaluation reservations. AtomStorage owns opaque immutable records and
the acceptance feed. Search owns rebuildable generations and maintenance identity.
Local compatibility metadata owns only generated labels/default STVs and the
existing promotion representation. No new BeliefRevision, Evidence or Attention
responsibility is assigned to these records.

AtomStorage 1.2.0 adds optional `observe(Mutation)`: authoritative observation of an
already accepted principal-scoped mutation, its original receipt, and acceptance
position. It does not create or retry a mutation. Historical 1.1.0 descriptors are
unchanged. The new wire binding admits only the four append record roles and the
reads required to validate enrollment. It exposes neither arbitrary content types
nor generic remote AtomStorage writes.

An opaque append-binding record commits the digest of the accepted input, identity,
time, vector, selections, principal and original deadline before payload/vector/
enrollment. This additional immutable owner record prevents a partially completed
append from silently changing meaning. Existing `vector_enrollment.enroll` performs
the three remaining creates through declared ports. No provider shares a database
transaction with the application or another owner.

Search 3.1.0 adds named bounded maintenance and publication observation under the
existing vector profile. A logical key binds principal, source head, corpus, model,
index profile and original deadline to one generation. Interrupted unpublished
index contents are rebuilt in that generation; a verified checkpoint can be
published, and an already published generation can be observed without a new build.
New effects require the original deadline and unspent reservations. Generation
capacity includes unfinished named builds. Historical unkeyed `build` remains
available to the old read-only experiment.

The new read descriptor also adds `ready(snapshot)`. `/5` authorizes disclosure
against a retained, verified generation without invoking another vector query or
maintenance operation. Missing old generations fail explicitly, including captured
result replay. Historical 3.0 read descriptors and their semantics are preserved.
Initial 3.0-built snapshots remain compatible because the vector/index profiles
and source identity are unchanged; the new descriptor adds an observation operation.

## Visibility and recovery

Storage acceptance, Search publication, metadata readiness, application selection,
native result capture and next-context handoff are separate observations. No
cross-owner atomic transaction or exactly-once physical encoding is promised.
Lost replies remain uncertain until observed through an owner port. Reservations
remain spent; captured vectors are reused exactly.

The application stores immutable read views containing a published snapshot and
matching metadata seal. Query admission binds its view in the same application
transaction as occurrence creation. Later writes may advance the active pointer;
earlier queries and captured results retain their stored views. Operator configuration
is immutable between remember and query. A metadata view contains no payloads or
real vectors; its dummy one-dimensional Chroma vectors serve only the pinned SDK's
metadata representation. The legacy candidate/payload/mutation guards remain closed.

Append acknowledgment requires a coherent ready view and the creation-label
confirmation. A pending append blocks acceptance of an unrelated next turn. Failures
report independently observed stages; absent receipts are not proof of absent
effects. An original deadline can expire with accepted but unpublished records.
Observation of prior completion is permitted after expiry; it does not authorize
new encoding, storage, indexing or metadata preparation.

The supported corpus has one trusted application journal and sequential native
writer. The existing exclusive application lock rejects overlapping processes.
Provider policy binds the generated session and principal. This is not a multiwriter
consistency protocol, background scheduler, migration or general ingestion service.
The controlled loop's existing mixed-profile batch refusal remains: remember and
query are successive turns, while multiple remember positions have distinct IDs.

## Disclosure

All inputs and metadata are newly generated and explicitly approved. Embedding
receives transformed helper text; the append provider receives raw content and the
bound helper input; Search authorization already receives raw query text in S03.
AtomStorage receives payload/vector/enrollment/binding records. The caller retains
local compatibility metadata and result captures. No vector-only disclosure or
production-private-memory claim is made. Retrieved/written text remains data;
scripted model tests do not establish prompt-injection immunity.

Execution status and remaining gates belong to the S03.2 evidence report; these
decisions alone are not a claim that the new implementation has passed its tests.

## Historical scope guard

The S01 regression guard hashes all historical M5 implementation files, not only
numerical sources. S03.2 deliberately adds `FeedAtomOwner.observe`,
`AtomSession.observe` and the optional `AtomMutationObservation` protocol. The guard
now removes exactly those named AST spans, then checks every remaining byte against
the unchanged M5 manifest. Other files and all numerical pins are checked in full.
The first failed source-freeze assertion and the corrected test run are retained;
the historical manifest itself is not rewritten. New observation behavior has its
own contract and real-provider coverage.
