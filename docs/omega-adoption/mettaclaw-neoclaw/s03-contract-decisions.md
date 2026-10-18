# S03 bounded memory-read contracts

The baseline is Fusion 34295802e16cd3f0ab1998d2876462dff3a7978a. The original
query was exercised before the Search adapter was introduced. Its first driver
failed because `lib_combinatorics` was omitted; adding the actual pinned native
library fixed the driver, without changing `query`. Chroma 1.5.5 is a newly tested
baseline, not a reconstruction of the historically unspecified Omega SDK.

`semantic-embedding-memory/1` adopts the mapping's draft name. It is a new Search
3.0.0 contract. Neither M5 `exact-attributes/1` nor S02 `external-web-search/1`
changes meaning. It accepts only an explicit scoped corpus, immutable physical
generation and source head, an exact embedding profile, normalized finite float32
1024-vector, squared-L2 metric and k=1..100. Lower distance is closer. The native
demo selects recall=2, similarity=4, inflation=4, hence k=8; no silent truncation.
Wire replies bind the server-authenticated principal to the immutable application read binding. Results are ordered scoped payload refs, UUIDs and distances, with request digest,
selected snapshot, top-k and exhaustive=false. No cursor or pagination is accepted.
Ties retain Chroma's order; no cross-build stable tie order or ANN recall is promised.

The real local embedding profile pins intfloat/e5-large-v2 at
f169b11e22de13617baa190a028a32f3493550b6, weights/tokenizer hashes in
`integration/neoclaw/memory-model.json`, CPU float32, native normalized encode,
512-token model limit, and no added prefixes. The source-checked loader changes
only model resolution to the pinned offline directory. `fixture-unit-vector-1024/1`
is separately labelled and never passes the real-embedding gate. Embedding stays
local; this is not an Embedding service. Chroma's observed default configuration is
L2, ef_construction=100, ef_search=100, max_neighbors=16, resize_factor=1.2,
sync_threshold=1000. SDK/wheels are separately locked: sentence-transformers 5.2.3, transformers 5.20.1, torch 2.10.0+cpu, NumPy 2.5.2, tokenizers 0.23.3 and safetensors 0.8.0. Fresh-target and initial package identities match.

AtomStorage keeps opaque records under existing M5 limits: 4096 bytes, 512 accepted
atoms, eight-item reads/feed pages. Float32 vectors occupy exactly 4096 bytes.
Immutable payloads carry corpus, scope, UUID, display time and <=3000-byte content.
The operator validates separately committed payload/vector refs before publishing
an enrollment. Stable keys make repeats safe; orphaned inputs are possible. The
feed remains the authoritative source, not a generator's answer list. Search
reads every committed envelope through ports and validates selected enrollment
inputs. Maximum 128 enrolled memories. Other scopes have separate indexes.

Maintenance stages a unique generation, verifies all stored vectors/ref metadata,
writes/fsyncs its manifest, then atomically publishes a pointer. No checkpoint is
advanced ahead of recoverable Chroma data. An interrupted unpublished generation
is abandoned; the bounded source prefix can be rebuilt. A lost index makes its
physical generation unavailable to candidate queries. An occurrence with already
captured candidates can hydrate those exact refs without querying another generation;
validated/captured output can finish under current authority. The selected snapshot
is fixed for the fresh application journal; rebinding requires a fresh journal. A rebuild has a
new physical generation but the same logical identity for the same source prefix,
corpus, model and index profile. A newer head cannot be claimed by an older
manifest. Frozen older generations remain explicitly selectable while present.
Publication retains at most 32 physical generations. Abandoned staging directories are retained for operator inspection; no background garbage collector is introduced. No cross-store atomicity, power-loss guarantee or mutation/retraction is claimed.

The application uses fresh `controlled-native-loop/3` journals, preserving /1 and
/2. Session/turn/position acceptance and next-context projection are reused. A
small `app_memory_reads` table owns vector/snapshot binding, candidates, verified
rows, enrichment time and spent calls. At most 64 port calls and three candidate
queries per occurrence; attempts reserve before I/O, never refund. Deadlines remain
the original <=30-second occurrence deadlines. Authorization/disclosure checks can
run after the deadline; new retrieval cannot. Later identical commands are new
occurrences. Captured results replay exactly after current authorization checks.
Reads create no DelegatedExecution job, outbox or mailbox.

Native promotion, sorting, linked-label/STV reads, rendered-record uniqueness and
presentation stay native. The chosen clock is persisted at the original point,
after retrieval; parity uses an explicit clock fixture there. Generated enrichment
metadata is sealed and read-only; the new composition admits only S01, S02 and
query, in homogeneous batches. Arbitrary MeTTa, shell and all memory mutations are
rejected. Unused history and global-promoted-context boundaries remain fixtures.
No global atomic snapshot across legacy and Fusion owners is advertised.

New descriptors explicitly select `generated-shareable-only`; private M5 profiles
are unchanged. Trusted composition chooses placement, corpus, model, credentials,
approved synthetic queries/vectors and generation. The existing certificate-checked
loopback HTTPS host adds a bounded `/s03-read` route for query, getMany and current
authorization. This is same-host placement only. Search cannot read local promotion,
links or STVs. A hostile local metadata wrapper rejects legacy candidate/payload
reads; hydration verifies every ref, scope, content type, digest and UUID. A missing
payload fails the whole read. Retrieved text remains data, never parsed/evaluated.

Errors use the existing vocabulary: invalid vector/cursor/schema → INVALID_ARGUMENT;
wrong model/metric/profile → UNSUPPORTED_PROFILE; wrong scope/revocation → UNAUTHORIZED;
wrong binding/source → CONFLICT; unbuilt, retired/lost generation, unavailable payload,
malformed result or outage → NOT_AVAILABLE; exhausted bounds → OVERLOADED;
expired new reads → DEADLINE_EXCEEDED. Only a valid, fully built empty corpus returns
successful empty hits. No network failure falls back to legacy local retrieval.
