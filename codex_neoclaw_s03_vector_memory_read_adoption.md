# Codex handoff — S03: adopt the vector-retrieval boundary inside native memory query

## 1. Objective and stopping point

Continue `machieke/fusion-module-interfaces` from
`34295802e16cd3f0ab1998d2876462dff3a7978a`, or record the exact descendant and
relevant changes. Read applicable AGENTS.md, the original architecture brief,
M5 contracts, the MeTTaClaw mapping packet, and S01/S01.1/S02 implementations and
evidence. Preserve unrelated work and historical evidence.

**Objective:** make the existing native MeTTaClaw `query` command obtain its vector
candidates and authoritative payloads through selectable local or authenticated
same-host HTTPS module providers. Keep the surrounding native query composition
and local enrichment behavior. Use only a new, explicitly shareable generated
corpus. Demonstrate actual native-loop dispatch and next-context consumption.

This is a bounded implementation of the first part of the mapped S03 core-memory
read composition. It does NOT complete all of S03's originally proposed memory
semantics, remote private memory, or the whole `query` family. Report the precise
adopted internal operation: `lib_chromadb.query_with_ids_and_dists`, reconstructed
through Search projection plus AtomStorage. Do not count hydration and transport
as additional independently adopted native commands.

**Stop after this read-boundary slice.** No user-memory migration; no production
private-memory service; no `remember`, `update`, `forget`, `link`, `unlink`,
`support`, `contradict`, `promote` or `demote` adoption; no new belief mathematics,
attention policy, graph traversal, history redesign, general SDK/framework,
background scheduler, multi-host deployment or chain work. Do not add another
external tool to avoid confronting the memory contracts.

The work below is a proposed engineering increment, not a claim that the meeting
participants selected its concrete profiles, model or deployment policy.

## 2. Review basis and baseline

The reviewer inspected the pinned public S02 source, its report, selected tests,
manifest and live trace, the mapping documents, and the pinned native memory and
Chroma-helper sources. The reviewer did NOT independently execute the suites,
verify the local dependency installations, or start Omega.

S02 records 318 test methods/cases: 22 new and 296 regression cases, with no skips.
Its two live external-search integration sessions are additional gates, not two
more test methods. Original/native rendering comparisons use recorded external
responses. The Brave 429 preflight and the subsequently selected DuckDuckGo
backend are recorded separately; no admitted request changed backend. Preserve
that distinction and the stable captured-observation semantics.

S02 demonstrates two adopted operations in controlled native-loop sessions. It
does not demonstrate a generic arbitrary-operation service, fully live Omega,
or multi-host deployment. Existing new-composition profiles require fresh journals.
Do not relabel stored records or remove identity guards to reuse them for S03.

### Source ledger to inspect

| Source | Relevance |
|---|---|
| `docs/omega-adoption/mettaclaw-neoclaw/{remote-placement,seam-contracts,interface-gaps}.md` | S03 is ranked next but has unresolved vector, identity, metadata, source-feed and privacy requirements. These are historical mapping statements, not implementations. |
| `docs/omega-adoption/mettaclaw-neoclaw/{source-state,mapping-ledger,coverage}.json` | Source pins and operation-level accounting. |
| `docs/omega-adoption/mettaclaw-neoclaw/s02.md`, `evidence/s02/` | Source identities, mixed-session limits, live/fixture split and recovery baseline. |
| `fusion/neoclaw_application.py`, `neoclaw_client.py`, `neoclaw_operations.py` | Current durable occurrence/result handoff; closed two-operation job binding. |
| `fusion/neoclaw_transport.py`, `integration/neoclaw/{native_loop,startup_overlay,loop_bridge,controlled_run}.py` | Validated TLS transport, native startup/dispatch and explicit substitutions. |
| `fusion/{ports,atom_feed,atoms,search,lookup,lookup_contracts,lookup_composition}.py` | M5 source-head/feed, authoritative storage, exact Search, maintenance and consumer ownership. |
| `integration/test_m5_real.py`, M5 tests, native Hive lookup tests | Existing feed/rebuild/freshness and dependency-boundary evidence to preserve. |
| MeTTaClaw `src/memory.metta`, `src/helper.py`, `lib_llm_ext.py`, `src/loop.metta` | Actual vector query, local promotion, metadata reads, rendering and native context. |
| `patham9/petta_lib_chromadb:lib_chromadb.py` | Existing collection setup and query `[uuid,time,document,distance]` result. |

Inspected source pins:

- MeTTaClaw: `2af37c3fec18613de54ca42fde2382a9087d4524`.
- Chroma helper: `218484875d5d1bfb217a9a03d3983dc1ed9d406c` (inspection pin;
  historical deployed SDK version remains unknown).
- S01 PeTTa: `fea83178af3722666d2948d074591d10a3134f56` and verified SWI 10.0.1.
- DeTTa: `272888f264dd2dde18b574cabb53c266b0dac2ec`.

Do not change the independent Fusion PLN/SWI baseline merely to run this slice.

## 3. Confirm the native behavior before choosing a contract

Run the original memory query on a disposable generated corpus before changing
its retrieval boundary. Pin an obtainable compatible Chroma SDK, its index
configuration, Python/native dependencies, helper code and relevant serialization.
A newly selected SDK is a tested baseline, not reconstruction of the unspecified
historical Omega deployment.

The inspected `query` is more specific than “vector search followed by reranking”:

1. `embed(text)` supplies a query vector.
2. `query_with_ids_and_dists` requests
   `promotionInflationFactor * maxRecallItems` candidates.
3. It reads a wall-clock time and local promotion values. Positive-promotion
   candidates are sorted using the native tuple containing negative promotion,
   distance, UUID and the remaining fields, then limited to `maxRecallItems`.
4. It concatenates those promoted results with the vector-result order, applies
   native `unique-atom` to the rendered records, and limits the combined result to
   `maxRecallItems + maxSimilarityRecall`.
5. Each presented item includes timestamp-labelled `id`, linked-episode labels,
   STV and content. It does not read full episode histories during this command.

Verify these statements on the pin. Preserve the native functions for promotion,
merging, uniqueness and presentation instead of rewriting them in Python. In
particular do not replace this with a weighted similarity-plus-STI score, a global
promotion search, deduplication by UUID, or a new episode-recall algorithm.

The timestamp is display metadata, NOT unique identity. Distinct UUIDs may share
a timestamp; identical rendered records may collapse under the native uniqueness
rule. Write tests for both, and record any explicitly profiled domain restriction.

### Embedding baseline

The original code supports a Local path using `intfloat/e5-large-v2` and normalized
`SentenceTransformer.encode`; it defaults to the hosted OpenAI path. Select the
Local path explicitly for this generated demonstration. Pin exact model/tokenizer
revision, weight hashes, dimensions, normalization, dtype, SDK and input processing.
Do not silently add query/passage prefixes, change the model, or imply preservation
of the default hosted mode. Reuse the relevant native implementation through a
source-checked adapter/loader; unrelated eager LLM/media clients need not run.

Use hand-specified vectors for deterministic mathematical/ordering tests, clearly
labelled as vector/embedding fixtures. Full S03 success additionally requires a
text query using an actual pinned local embedding model and real Chroma. Fixtures
alone cannot pass that gate. If model assets or a compatible SDK are unavailable,
record the exact blocker and deliver the runnable independent contract work.

There is no request to deploy Embedding remotely or to build a general Embedding
service. A minimal typed embedding-profile dependency is enough for this boundary.

## 4. Adopt only the vector-query and payload-read boundary

Target flow:

```text
Real native query(text)
  -> existing local embedding path
  -> compatibility adapter for query_with_ids_and_dists(vector, k)
       -> Search.query(vector, embedding profile, corpus/generation, k, source head)
       <- scoped refs + ordered distances + source/generation observations
       -> AtomStorage.getMany(refs), bounded batches
       <- authoritative immutable records
       -> validate identities/integrity and reconstruct [uuid,time,content,distance]
  -> unchanged local promotion / linked-label / STV reads
  -> unchanged native selection, merge, uniqueness and result construction
  -> durable local result handoff
  -> actual next native-loop context
```

The compatibility adapter composes declared ports. It is not a sixteenth module,
a new memory owner, an index server with all of Omega inside it, or a universal
execution endpoint. Domain contracts must not import the Chroma SDK. Provider
selection belongs to trusted composition; selecting local versus HTTPS must not
change the native query's business logic.

Search returns references and distances. It must not supply authoritative payload
text, change beliefs, rank promotion values, expand episodes or access the caller's
metadata database. AtomStorage supplies verified payloads; only the local facade
materializes the old row shape. Missing, mismatched or unavailable payloads produce
an explicit incomplete/error outcome, not silent candidate omission.

Local legacy metadata readers may remain on their current backend, including
Chroma metadata and promotion SQLite, in this slice. Retain their status as
unadopted local components. Their presence is not Fusion Relations, BeliefRevision,
EpisodicMemory or Attention adoption. Do not fabricate evidence roots from their
STVs. The test corpus must exercise nonzero promotion and nontrivial metadata,
not bypass enrichment with all-zero/empty values.

The target caller must not fall back to its legacy candidate search or retrieve
candidate payloads from a second local document copy. Enforce this with a hostile
boundary wrapper and filesystem/process isolation where possible. A local
metadata-only collection is permitted for UUID, episode-label and STV lookups.
The original reference run may retain its original full Chroma corpus; keep it
separate from the adapted caller and unavailable to the network provider.

## 5. Define a real vector Search profile without changing exact Search

Start from the mapping's DRAFT `semantic-embedding-memory/1`; reconcile the final
name with the existing catalogue rather than adding a synonym. It is a new named
vector profile, not an implementation of M5 `exact-attributes/1` and not S02
`external-web-search/1`. Existing exact Search must retain its meaning and tests.

Before implementation specify:

- Scope/corpus identity, embedding profile, vector dimensions/encoding/finite
  domain, metric, distance direction/meaning, and the actual Chroma index settings.
- Fixed bounded candidate count, payload limits and admitted native configuration.
  Accommodate or explicitly reject the real candidate request; do not silently
  truncate native k to the final display limit.
- Source identity/head, selected immutable read generation, extraction/enrollment
  profile, index implementation revision and metadata observed at query time.
- Request/response correlation, provider descriptor binding, current authority,
  deadline and bounded read-attempt accounting.
- Ordering and ties, repeated-query stability and what approximate retrieval does
  and does not promise. SDK defaults are not an undocumented universal metric.
- Explicit empty, source-not-ready, retired-generation, invalid-vector,
  incompatible-model and temporarily-unavailable outcomes using the existing
  error vocabulary or a documented extension.

Keep the first read profile top-k bounded. Pagination may be explicitly unsupported;
reject cursor fields and do not advertise continuation support. Returning top-k
is not exhaustive retrieval. Exact-attribute pagination/freshness semantics must
not be claimed for an approximate vector profile automatically.

Use original/adapted comparisons on the same generated identities, vectors,
insertion schedule, index settings, local metadata and clock fixture. For
well-separated cases require matching candidates, native output order and content,
with justified numerical tolerance for distances. Add tie/near-tie cases and
report the native guarantee honestly. Do not conceal ranking changes behind broad
float tolerance; a newly deterministic tie policy would be a documented behavior
change, not unchanged native conformance.

A small independently computed distance oracle can test metric interpretation. It
is test code, not a replacement for real Chroma, and does not establish ANN recall
or production performance. No embeddings/attention quality improvement is claimed.

## 6. Use an authoritative enrollment source and a rebuildable index

Use a NEW generated corpus with immutable payloads and explicit vector enrollment.
An enrollment identifies a scoped stable memory identity, legacy presentation UUID,
payload reference, vector or vector reference, exact embedding profile and the
immutable metadata necessary to reconstruct the legacy row. Encoding is proposed;
reuse a compatible existing envelope where available.

Keep vectors and payloads in scoped AtomStorage records over real DeTTa. Search's
index is a projection, not the only copy of the corpus. Use M5 AtomCommitSource and
its acceptance sequence through declared ports to discover committed enrollment
records. Do not add another event bus or inspect another owner's SQLite tables.

Payload/vector persistence and enrollment are separate commits. Publish enrollment
only when its referenced immutable inputs exist and validate; use stable mutation
keys so a crash can leave an orphaned payload but not an acknowledged invalid
enrollment. The AtomStorage-owned feed must represent actual committed records.
A test generator's answer list is not the source feed. The caller receives no
expected candidate IDs or precomputed response lists.

Use a bounded, immutable read generation built through a declared maintenance path.
Record the source head actually included, not the latest observed head as though
it had been indexed. A new source head that is not yet covered must not return a
successful empty answer. A frozen generation may remain usable while a new one is
prepared; its identity and availability must be explicit.

Chroma and a maintenance journal are not one transaction. Either stage and verify
an unpublished generation before atomically publishing a pointer, or implement
bounded idempotent replay of index writes and checkpoints. Never advance a durable
checkpoint before the corresponding index state can be recovered. On uncertain
recovery rebuild the affected unpublished generation or report unavailable; do not
claim cross-store atomicity from the M5 SQLite-only implementation.

Delete only the derived index and rebuild from source and payload ports. Recheck
the selected query at the reconstructed source snapshot without reseeding expected
answers. Physical index generations may differ; state how logical snapshot
identity and in-flight reads behave. Do not silently substitute a new generation
for a request already bound to a now-unavailable one.

This slice does not index existing user Chroma databases or add mutation/retraction
semantics. No need for a live write stream from the whole Omega. Operator-side
preparation and maintenance of the explicitly generated corpus is sufficient.

## 7. Read lifecycle, local enrichment and native-loop recovery

Search is a read interface, not automatically a DelegatedExecution job. Reuse the
application's session/turn/position identity, policy checks and next-context handoff,
but do not manufacture a mailbox/outbox for every synchronous read merely because
S01/S02 use one. A small typed read-client binding and application-owned captured
result are sufficient. Do not copy the entire application state machine.

Persist the accepted query occurrence and selected corpus/profile before crossing
the provider boundary. Bind its vector and read-generation identity before the
vector query. Record query/model versions, original deadline and bounded attempts.
Replays retain identity and budgets; the same query in a later turn is a new
occurrence. No fallback to the original local Chroma search on network failure.

Preserve the original local promotion semantics. Its wall-clock value is read
AFTER vector retrieval in the native source. For parity tests use an explicit clock
fixture at that point. For recovery, persist the chosen enrichment time before
using it, and replay the accepted value for that occurrence. Do not quietly capture
a different time on restart or present a changed timing convention as exact native
behavior. Keep the actual promotion calculation, not a new STI policy.

Keep local enrichment metadata immutable for an admitted read in this initial
profile, using a sealed generated snapshot/manifest. Do not claim a globally atomic
snapshot across legacy metadata, search and payload owners. Concurrent `promote`,
`support`, mutation or deletion in the generated adoption session is unsupported
and must be rejected at command admission or excluded by verified composition,
not silently permitted while advertising frozen reads.

After full validation, capture the native result and its source/profile/read
observations in the local application owner. A crash before capture can require
bounded reads again; a crash after capture restores the same accepted result and
next-context handoff. Current authorization still gates replay and disclosure.
A revoked or unavailable provider must not become an empty memory answer. Once a
result is captured, the record itself does not grant permission to reveal it.

Do not replay an incomplete batch containing unadopted mutable commands. Keep S01
and S02 available in the same application installation and sequential session.
Mixed command types in one batch can remain explicitly unsupported; no concurrent
scheduler or mailbox routing project is required.

## 8. Privacy, deployment and untrusted memory contents

Existing private user memory, vectors, promotion, episodes, history and belief
state stay local and untouched. A vector is not automatically anonymous or approved
for disclosure. Do not send real user queries, embeddings or identifying hashes
through the existing generated-shareable profile.

The positive HTTPS test uses an explicitly approved synthetic corpus and approved
synthetic queries/embeddings under a named compatible shareable profile. Local
private-only tests may exercise refusal, but do not pass a private-remote gate.
Do not weaken historical `private-local-only` descriptors to make a network
binding pass. Provider selection is operator-controlled, not model input.

Reuse certificate-verified, authenticated loopback HTTPS and same-host filesystem
isolation; document any necessary typed read-route/profile extension. A stdio
process does not pass HTTPS. No public endpoint or multi-host guarantee is required.
The caller cannot open provider storage/index files; the provider cannot open the
caller's private metadata, history, keys or journals. A service endpoint name is
not proof of provider identity or query authorization.

Authorize candidate visibility before ranking/limiting for the selected scope;
unauthorized records must not affect returned counts, ranks or scope-visible
watermarks. Scope-isolated indexes are an acceptable bounded implementation.
Apply current checks to query, reference hydration, capture replay and context
release. Test malformed references, wrong scopes/profiles/model identities,
revocation, bad certificates and provider outage. Do not put credentials in
requests, persisted result payloads or published evidence.

Returned memory text is data. Preserve native escaping and never pass retrieved
content to `sread`, `eval`, a shell or another tool. Test embedded fake commands,
quotes, control characters and Unicode through the actual loop. Do not claim this
proves a live model is immune to prompt injection.

## 9. Required comparison and recovery scenarios

The main comparison has three paths on the same newly prepared corpus:

1. Original native query with the pinned Chroma helper and original local enrichment.
2. Adapted native query with local Search and AtomStorage providers.
3. The same adapted native query with authenticated HTTPS Search/AtomStorage.

Use the actual `mettaclaw` loop, query dispatch, native composition and next-context
consumption. Do not replace `query`, its vector call or enrichment with a fixture
that already knows the answer. Scripted model/channel and genuinely unused-memory
boundaries remain permitted and labelled. The previous broad unused-memory fixture
must no longer bypass any read required by the query under test.

Test a generated corpus with distractors, at least one useful promoted result
that changes presentation order, multiple linked labels, varied STVs, zero
promotion, duplicate timestamps, duplicate presentations, ties and another scope.
Use a declared native k/configuration that fits the implementation's bounds; do
not raise unrelated limits simply to fit a demonstration.

Required failure/recovery assertions:

- Enrollment accepted before index catch-up: not-ready versus actual empty corpus.
- Lost reply before local capture: retry stays on the original admitted read
  semantics and does not silently read latest state.
- Index-build process killed around data write/checkpoint/publication: no published
  generation claims records absent from its durable or reconstructible index.
- Caller killed after candidate capture and before hydration, then after payload
  validation and before native projection: stable occurrence and coherent result.
- Caller killed after result capture but before next-context consumption: same
  accepted result, current authority, no reset deadline or budget.
- Index removal/rebuild with authoritative records intact: same logical retrieval
  for the declared source snapshot, or explicit unavailable old-generation status.
- Wrong scope/model/dimension/metric/generation, nonfinite vectors, malformed
  result, missing payload, revoked authority and HTTPS outage: fail explicitly,
  never empty-by-default or local fallback.
- Before/after evidence that query and rebuilding did not mutate local truth,
  episode links, promotion state or Fusion cognitive state. Application receipts
  and expected native history/projection writes are separate, documented effects.

Use real process kills where claimed. Record method counts versus parameterized
scenarios; optional diagnostic coverage must not replace behavioral evidence.

## 10. Gates, deliverables and honest completion

| Gate | Required evidence |
|---|---|
| BASELINE_SOURCE | Exact starting/tested revisions, source locks and applicable M1–M5/S01/S02 behavioral regressions. |
| MEMORY_ORACLE | Original native query and Chroma helper execute on generated data with explicit metric, identity, ranking and presentation expectations. |
| EMBEDDING_REAL | Text queries use the pinned actual local embedding model; separate vector fixtures never pass this gate. |
| VECTOR_CONTRACT | Executable named profile, descriptor-bound inputs/outputs, limits, scope, generation and top-k semantics; exact Search unchanged. |
| SOURCE_REBUILD | Index consumes authoritative enrollment via declared feed/storage ports, exposes honest readiness and rebuilds after index loss. |
| OWNER_BOUNDARIES | Ref-only Search, independent payload hydration, local legacy enrichment and no foreign databases/answer-map dependency. |
| NATIVE_LOCAL | Real query composition and next-context consumption via adapted local providers match the admitted native baseline. |
| NATIVE_HTTPS | Same adapted caller on certificate-checked isolated HTTPS, real Chroma and real DeTTa; no local candidate/payload fallback. |
| READ_RECOVERY | Actual kill/restart preserves occurrence, read semantics, captured result and original bounds. |
| AUTH_PRIVACY | Scope/model/ref checks, current authority, explicit synthetic disclosure, canary isolation and untrusted-text boundary. |
| COMPAT_REPRO | Obtainable fresh-target recipe, cache scope, old profiles and S01/S02 behavior preserved; no populated-state migration. |
| SCOPE_LEDGER | Only the identified internal read boundary is adopted; remaining composite memory owners and full-product coverage not promoted. |

Full completion requires the real embedding, native query, Chroma, DeTTa and HTTPS
gates. Missing source/assets/permission is BLOCKED; incorrect executed behavior is
FAIL; an intentionally unexercised extra is NOT_RUN. Deliver useful independent
work on a blocked prerequisite without substituting fixture success for adoption.

Re-run applicable S02 behavioral tests. Keep live external search separate from
recorded-response regression: do not erase its historical pass or repeatedly hit a
rate-limited backend to make a S03 total green. A new live S02 rehearsal is needed
when changes affect its actual SDK/egress path; otherwise a clearly recorded
NOT_RUN live recheck does not invalidate unchanged fixture/regression evidence.
Full default Omega, hosted LLMs/channels, multi-host, chain, power loss and
empty-global-cache builds remain separate unrun gates unless independently tested.

Update the existing mapping/coverage and adoption documents, source locks,
contracts/ADRs, native overlay, tests and reproduction tooling. Add one S03 report,
machine-readable gate manifest and same-read trace. Record actual dependencies,
fixtures, development failures, final results and all missing/unrun gates.

State adoption narrowly: `query` traversed an adopted vector-retrieval and payload
read boundary. Promotion, linked-episode metadata, STV handling, embeddings as a
remote service, full memory writes and user-data migration remain unadopted.
If an operation count is incremented, define its unit consistently with the
existing operation ledger. Never turn this into a product-completion percentage.

The supported product claim after passing is:

> A controlled native Omega memory query can obtain vector candidates and verified
> payloads through local or authenticated same-host HTTPS module implementations,
> while its local enrichment and result consumption preserve the declared native
> behavior for a generated read-only corpus.

It is not full remote memory, general Chroma replacement, privacy-safe export of
existing memories, complete Omega startup, improved retrieval quality, or a speedup.

Then stop. The next decision concerns remaining local memory owners and real
workload requirements, not automatic rollout of all deferred candidates.

## Pinned review locations

```text
https://github.com/machieke/fusion-module-interfaces/commit/34295802e16cd3f0ab1998d2876462dff3a7978a
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/34295802/docs/omega-adoption/mettaclaw-neoclaw/s02.md
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/34295802/evidence/s02/verification.json
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/34295802/docs/omega-adoption/mettaclaw-neoclaw/seam-contracts.md
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/34295802/docs/omega-adoption/mettaclaw-neoclaw/interface-gaps.md
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/34295802/fusion/ports.py
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/34295802/fusion/search.py
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/34295802/fusion/atom_feed.py
https://raw.githubusercontent.com/patham9/mettaclaw/2af37c3fec18613de54ca42fde2382a9087d4524/src/memory.metta
https://raw.githubusercontent.com/patham9/mettaclaw/2af37c3fec18613de54ca42fde2382a9087d4524/lib_llm_ext.py
https://raw.githubusercontent.com/patham9/petta_lib_chromadb/218484875d5d1bfb217a9a03d3983dc1ed9d406c/lib_chromadb.py
```
