# Codex handoff — S03.1: independently place query embedding behind a typed interface

## 1. Objective and scope

Continue `machieke/fusion-module-interfaces` from published S03 commit
`2bddbc3467f98ed258741a21a329230a0cd21dd9`, or record the exact descendant and
relevant changes. Read applicable `AGENTS.md`, the original architecture brief,
the MeTTaClaw adoption mapping, S01–S03 contracts/evidence, and current source locks.
Preserve unrelated changes and restricted upstream source.

**Proposed next increment:** move only the query-time Local embedding dependency
behind an explicit, independently selectable Embedding port. Keep the existing
native `query` and its adopted Search → AtomStorage path. Demonstrate that the
HTTPS query caller works without loading or accessing the E5 model or invoking
its inference libraries locally.

This is a proposed implementation handoff, not a claim that S03 authorized this
work or that the meeting selected a new product architecture. The mapping already
identifies Embedding as gap X02; use that existing terminology. The historical
15-family reference inventory is not an exhaustive Omega capability taxonomy.

**Stop at S03.1.** No memory-write adoption, existing-data migration, remote private
memory, metadata/promotion/STV adoption, new model, quantization, GPU profile,
embedding-quality research, whole-Omega startup programme, multi-host deployment,
chain work, generic model server, scheduler or framework extraction. Do not turn
Search into an embedding or memory-state owner.

The bounded claim to demonstrate is:

> The same controlled native Omega query can generate its query vector through a
> selected local or authenticated same-host HTTPS Embedding provider, then use
> the existing Search and AtomStorage contracts, without requiring E5 inference
> on the HTTPS caller. Local enrichment remains local.

It is not full thin-client Omega, all memory moved remotely, private-memory
publication, general embedding-provider interchangeability or a speedup.

## 2. Review and provenance limits

The user's S03 completion described an uncommitted implementation on
`34295802e16cd3f0ab1998d2876462dff3a7978a`. During review, the public repository
exposed commit `2bddbc3467f98ed258741a21a329230a0cd21dd9` containing S03. The
historical manifest still records an additive working tree and per-file hashes.
Do not rewrite that historical run as a clean-commit run.

This handoff follows a review of selected public source, tests, the S03 report,
contract decisions and manifests. The reviewer did not execute the integration
suites or independently reconcile every published file with its recorded hash.
Validate those relationships locally before changing code.

S03 reports 340 unique methods/cases: 22 new and 318 regressions. Additional
real-E5 three-path/recovery demonstrations and parameterized fault phases are
separate evidence, not extra unique methods. An initial regression environmental
failure and a model-startup observation timeout are retained with successful
rechecks. Historical passes are not new passes for S03.1.

Before implementation:

1. Record commit, branch, worktree status and relevant dependency identities.
2. Compare every `implementation_manifest` entry in
   `evidence/s03/source-state.json` with the selected S03 checkout. Explain every
   mismatch; separate later documentation/evidence changes from runtime changes.
3. Run the relevant S03 baseline from the declared inputs. Preserve failed,
   blocked, timed-out and unrun classifications rather than normalizing them to
   success. Do not reset sibling worktrees to obtain matching source.
4. Record any source-identity reconciliation in an additive note. Do not rerun
   the entire project solely to label an old manifest differently.

## 3. Source ledger and concrete seams

| Source | Why inspect it |
|---|---|
| `docs/omega-adoption/mettaclaw-neoclaw/interface-gaps.md` | G02 and X02 already separate Embedding from Search; gap labels are historical mapping judgments. |
| `docs/omega-adoption/mettaclaw-neoclaw/s03.md`, `s03-contract-decisions.md` | Current frozen corpus/read composition, native limits, privacy and runtime claims. |
| `evidence/s03/{source-state,verification}.json` | Tested hashes, package/model pins, overlapping test accounting and unrun gates. |
| `integration/neoclaw/memory_embedding.py` | Source-checked extraction of native `initLocalEmbedding` and `useLocalEmbedding`; pinned offline model location, CPU float32 and 1024 dimensions. |
| `integration/neoclaw/memory_bootstrap.py` | Initializes actual Local E5 in the caller and separately opens metadata-only Chroma and read-only promotions. |
| `integration/neoclaw/memory_build.py` | One combined SDK/model/helper recipe; runtime validation reads recorded installed package files. A remote binding cannot simply leave this model-runtime prerequisite on the caller. |
| `integration/neoclaw/memory_startup.py`, `native_loop.py`, `loop_bridge.py` | Source-checked native dispatch, real query construction and next-context consumption. |
| `fusion/neoclaw_application.py`, `neoclaw_memory.py` | Accepted turn/position identity, frozen binding, read reservations, candidate/payload/result capture and disclosure checks. |
| `fusion/vector_contracts.py`, `vector_composition.py`, `vector_transport.py` | Exact vector-model compatibility, immutable generation, authenticated read routes and independent storage hydration. |
| `fusion/adapters/chroma_vector.py`, `vector_enrollment.py` | Existing authoritative enrollment and projection; these must not silently start generating embeddings. |
| `integration/neoclaw/test_memory.py`, `test_memory_edges.py`, `memory_run.py`, `memory_recovery_run.py` | Existing parity, isolation, source/rebuild and recovery checks. |
| Pinned MeTTaClaw `src/memory.metta`, `lib_llm_ext.py` | `embed` calls `string-safe` and the Local helper; preserve input processing, numerical behavior and result composition. |

Selected S03 model: `intfloat/e5-large-v2` at
`f169b11e22de13617baa190a028a32f3493550b6`; exact weights/tokenizer hashes are in
`integration/neoclaw/memory-model.json`. Preserve the tested CPU float32 normalized
1024-dimensional path, native preprocessing, tokenizer/truncation semantics and
absence of added query/passage prefixes. Pin the exact selected package/runtime
configuration, not just the model name. Do not alter the separate Fusion PLN/SWI
runtime or the original S01 numerical profile.

## 4. Architecture and contract

| Boundary | Responsibility |
|---|---|
| Native Omega / compatibility adapter | Preserve the existing `embed` call and query composition; supply explicit inputs to its selected dependency. |
| Embedding | Validate one bounded text input and return a vector under an exact model/encoding profile. No corpus access, retrieval, ranking, beliefs, attention or publication. |
| Search | Rank the provided compatible vector over the selected immutable corpus generation; return references and distances. |
| AtomStorage | Supply immutable authoritative bytes through its existing interface. |
| Application owner | Bind the occurrence and provider selection, reserve attempts, capture the selected vector/result and recover next-context handoff. |
| Legacy local enrichment | Retain sealed linked-label/STV/promotion behavior; do not classify it as newly adopted cognitive functionality. |

Add the smallest backend-independent `Embedding.encode` port and one bounded
model-specific behavioral profile, reusing an already suitable declared port if
the inspected checkout contains it. Choose and record exact interface/version
names once. There is no universal `execute(text)` endpoint and no caller-selected
Python/MeTTa code, model file, repository, URL, device or credential.

Treat the mapping's X02 as an explicit adoption extension outside the historical
15-family denominator. Keep the original reference count and add a separate
extension/operation entry. Do not claim that model-loading, hydration and HTTPS
are three newly adopted native commands. Reconcile the precise adopted symbol
(e.g. the query-time `lib_llm_ext.useLocalEmbedding` boundary) against the ledger;
no adoption claim for all callers of that helper or all `embed` modes.

The typed request must bind at least the authenticated principal from trusted
context, scope, occurrence/call identity, exact model and preprocessing profile,
exact input representation or its bound fingerprint, selected descriptor,
deadline and size limit. The response binds that same invocation and contains
model/encoding identity, vector, dimension/dtype/normalization declarations and
an integrity digest over the declared canonical vector encoding.

A descriptor or digest checks binding/integrity, not truthful remote computation.
Provider code/assets are source-checked in the trusted local demonstration;
this is not cryptographic model-execution attestation.

Use one input string per call. Batch APIs, streamed tokenization, model discovery
and cross-request shared caches are out of scope. Inspect and specify empty input,
UTF-8/Unicode, quotes/control characters, byte limits and the model's actual token
limit/truncation behavior. Do not silently add normalization, prefixes, trimming,
truncation or escaping beyond the native path. Distinguish raw command text from
the exact string received by the native embedding helper; apply transformations
once and test that distinction.

Numerical replies must meet S03's vector encoding and model compatibility rules.
Reject wrong dimensions, profiles, nonfinite values, malformed/multiple outputs,
invalid norms and request/principal mismatches before Search sees them. Do not
silently renormalize or substitute a model to make validation pass. Source identity
includes the preprocessing policy even where model weights are identical.

## 5. Local and HTTPS placements

Provide two conformant implementations/bindings of the same selected Embedding
profile: an adapted local call and a certificate-verified, authenticated same-host
HTTPS call to the actual pinned model implementation. Reuse transport, descriptor,
authorization and process-isolation facilities. Do not build another RPC framework.

The provider may share an operator-managed host/process with other services, but
its logical responsibility, code dependencies and selected descriptor stay
separate. Search must not call a private embedding helper, and the native caller
must not construct concrete provider owners. Placement changes only composition,
not native query logic or prompt contents.

Provider readiness may load and validate its resident model before admitted work.
State the readiness boundary separately from each accepted command's deadline.
Separate an observer's startup timeout from application work time; changing an
observer timeout must not reset an admitted deadline. Use bounded calls and
resource limits; a stuck model cannot block an unbounded number of requests.
Do not add a global scheduler to serve a sequential generated demonstration.

### Required caller-dependency removal

A successful network round trip alone is insufficient. The HTTPS caller must run
with the E5 model/tokenizer/cache directories inaccessible and with local E5
inference entrypoints forbidden. It must not initialize `SentenceTransformer`,
call native `useLocalEmbedding`, or load an alternate/default model locally.

Provide a caller-specific reproducible environment and source validation recipe
that does not require the provider's model-serving stack. Demonstrate the adopted
query with `torch`, `sentence_transformers` and `transformers` unavailable to the
caller, or identify and remove only incidental eager-import coupling required to
make this boundary work. Do not fake unavailable modules to reproduce numerical
outputs. A local metadata helper may retain real Chroma dependencies; that is not
permission to retain query-time E5 inference. List remaining caller dependencies
accurately rather than claiming a complete thin client.

The current combined `memory-runtime.json` verification scans a whole installed
SDK. Split caller-required versus provider-required validation where necessary;
do not disable source checks, allow missing hashes silently, or require the
caller to inspect provider filesystem paths to verify its descriptor. The provider
verifies its own actual files. Public model identifiers/hashes may be held by both.

Keep the native metadata functions and their sealed inputs unchanged. Do not
replace their semantics, migrate them or turn this into Relations/Belief adoption
merely to remove an incidental import.

## 6. Invocation capture, authority and bounded recovery

Reuse the existing application occurrence and read lifecycle. Before the encode
request crosses the boundary, durably bind the exact input, provider/profile and
original deadline, and reserve the applicable encode-call attempt. Do not make a
new occurrence just because the provider timed out.

Capture the first fully validated embedding result in application-owned state
before it is used in Search. Bind the captured vector bytes/digest to the exact
input/model and occurrence. Candidate requests must use that selected vector.
Once it is captured, restart or further retrieval must not call Embedding again.
After candidates or the final native result are captured, preserve S03's existing
recovery and current-disclosure rules.

A crash before capture may cause another physical model evaluation, but only
within the original declared deadline and remaining encode-attempt budget. Reuse
original identities. Do not promise exactly-once inference, automatic budget
refunds or bit-for-bit cross-hardware reproducibility. A byte-identical captured
replay is a stronger, separate claim from tolerance-based numerical comparisons
of two independently executed model calls.

Define encode-dispatch reservations separately from Search/hydration attempts.
Count provider evaluations separately from caller requests; disable or account
for transport retries. A bound on caller sends is not proof of a physical-kernel
invocation bound without corresponding provider enforcement. Reuse existing
reservation machinery where it fits, not a new job/queue architecture solely for
this synchronous dependency.

Frozen generation, corpus and local metadata selection do not change. The
embedding provider must be compatible with the stored corpus model profile. A
new provider model is not permission to query an old vector index. No automatic
index rebuild, generation rebind or journal migration occurs in this increment.

Specify invocation permission separately from captured-result disclosure. Apply
current, bound authority at new calls, relevant replays and release of private
application state, following existing fail-closed profiles. Preserve principal
binding independently of credentials: substituting another authorized principal's
token cannot release the original occurrence or change its input/profile.
Do not make a stored digest act as an authorization capability.

Return typed unavailable, overloaded, invalid, unauthorized, incompatible or
deadline outcomes. There is no fallback to local E5, OpenAI embeddings, another
model, a zero vector, cached answers from another occurrence, or legacy local
candidate retrieval. An encoding failure must not appear as an empty memory result.

## 7. Privacy and output handling

S03 sent a query vector to remote retrieval while generating it locally. This
extension sends the actual helper-input text to the chosen encoder. That is an
additional disclosure boundary; do not inherit permission automatically from an
existing vector-search setting.

Only explicitly approved generated query text may cross the new HTTPS boundary.
Record the operator policy for that exact transformation/input and model provider.
No real user questions, private memory text, conversation/history, metadata,
identifying private hashes, credentials or model-controlled endpoints. The encoder
needs the selected text, not the whole Omega context or corpus.

Use current same-host filesystem isolation and test canaries at the new endpoint,
logs, captures and diagnostics. Keep the caller's private stores inaccessible to
the encoder and its model files inaccessible to the caller. Do not claim that
filesystem isolation is an egress firewall or production private-model hosting.
No public endpoint or multi-host test is required.

Encoding text does not authorize interpreting it. Quotes, control characters and
fake MeTTa/tool instructions remain data. No code evaluation, file access or
network destinations derived from the text. Preserve existing untrusted-memory
rendering tests; scripted model tests do not prove prompt-injection immunity.

## 8. Required demonstration and tests

Use the existing generated corpus, declared native recall configuration, sealed
nontrivial enrichment and original query behavior. Keep operator-side corpus
encoding/enrollment on its already verified path; it is not a newly adopted memory
write or an answer map supplied to the query caller.

Compare:

1. Pinned original native query with original Local encoding.
2. Existing S03 retrieval composition with adapted local Embedding.
3. The same native query with HTTPS Embedding and HTTPS Search/AtomStorage, while
   the caller lacks E5 assets and inference libraries.

Independently select encoder versus Search/storage placement. At least one mixed
placement check must show these are separate dependencies, not one hidden remote
`query` server. S01/S02 may retain their separately verified runtime recipes;
the slim embedding caller need not lose their historical regression coverage.

All required positive integration paths use actual native MeTTaClaw/PeTTa/SWI,
real pinned E5, real Chroma and real DeTTa where claimed. Model-response/channel
fixtures remain explicit. A vector fixture or lookup table cannot pass the real
Embedding gate. Same-host TLS is not a multi-host deployment.

Compare model input bytes, vector representations/norms, selected candidate
identities/distances, final native output and next-context consumption. Preserve
S03's no-stable-tie/ANN-recall caveat. Use numerical tolerances justified from the
pinned runtime and encoding; do not permit altered rankings merely because vector
elements fall within a broad tolerance. Require exact replay of captured bytes.
Do not change model prefixes or improve model quality in a placement experiment.

Required process-kill/recovery cases include:

- after accepted encode intent/attempt reservation, before request delivery;
- after real provider evaluation with reply lost, before caller capture;
- after captured vector, before Search dispatch;
- after candidate/hydration capture and before native result capture;
- after final native capture, before next-context handoff.

The first two may consume attempts without useful progress or repeat physical
computation. The captured-vector and later cases must use zero additional encoder
evaluations. Retain original budgets/deadlines and exact occurrence identity.
Use real process termination where claimed and distinguish injected reply loss
from a fake model. Provider restart must reopen the selected model identity;
it does not justify switching model, resetting caller state or returning a fixture.

Also test model/profile/dimension/digest/principal mismatches; revoked invocation
and disclosure access; bad certificates; provider outage; bounds/empty/Unicode
input; malformed vector outputs; changed text under an old identity; identical
text at new positions; and malicious content remaining data. Preserve source
freshness, index-rebuild, sealed metadata, no-local-fallback and credential-
substitution tests from S03.

## 9. Measurements, compatibility and gates

Measure caller cold startup and peak RSS under the existing S03 and proposed
remote-encoder compositions on the same environment. Record provider readiness,
encode time, TLS transfer bytes, retrieval time and end-to-end query time
separately. List absent and remaining dependencies. These are small controlled
measurements, not production throughput or cost estimates. Report regressions as
well as improvements. Do not invent a speedup or require an arbitrary percentage.
The hard benefit gate is removal of the local inference dependency, not latency.

Keep S03 `controlled-native-loop/3` and existing Search/numerical profiles intact.
Use an explicit new composition/profile for the additional dependency and stored
vector stage where necessary. Fresh journals are permitted; do not silently
reinterpret the binding of old accepted occurrences. No populated-state migration.
Keep old baseline entrypoints working under their old profiles.

| Gate | Required evidence |
|---|---|
| BASELINE_SOURCE | Exact published/working-tree source reconciliation and applicable S03 regressions; no false clean-commit historical run. |
| EMBEDDING_CONTRACT | One closed typed port/profile; model/input/output, limits, authority and encoding match real calls. |
| NATIVE_PARITY | Original and adapted local native queries agree under the selected model/corpus/profile. |
| REAL_HTTPS | Real pinned encoder runs through authenticated TLS and feeds the real existing Search/storage path. |
| CALLER_NO_E5 | Caller cannot load model assets or local inference libraries; real end-to-end query still succeeds. |
| CAPTURE_RECOVERY | Captured vector/result replay does not reevaluate; unresolved attempts remain bounded and identities/deadlines unchanged. |
| AUTH_PRIVACY | New text-disclosure boundary, current authority, credential substitution, canary isolation and no fallback tested. |
| OWNER_COMPAT | Separate Embedding/Search/storage/enrichment ownership; mixed placement; old profiles and generation semantics preserved. |
| REPRO_MEASURE | Declared caller/provider recipes, explicit cache assumptions, dependency and timing/RSS observations. |
| SCOPE_LEDGER | Only the precise query-time embedding boundary adopted; X02 extension separate from 15-family inventory and whole-product coverage. |

Keep the suite's unique methods separate from repeated subsets, native model
rehearsals and parameterized kills. Preserve failed development attempts and
successful corrections. Fresh-target/warm-cache is not empty-cache reproduction.
Required real gates cannot be replaced by fixtures. Record unavailable prerequisites
as BLOCKED, executed incorrect behavior as FAIL and optional untested areas as
NOT_RUN. Deliver useful independent work if blocked without claiming completion.

## 10. Deliverables and stop

Extend the existing implementation, catalogue, adoption ledger, source recipes,
ADRs and tests. Deliver one S03.1 report, a gate manifest, same-query trace, caller-
dependency demonstration, measurements and exact tested source identities. Do not
create another stand-alone architecture/report hierarchy or publish private data.

Record all final files/hashes and any subsequent evidence-only commit. Full Omega,
live hosted models/channels, private remote memory, multi-host, power-loss,
legacy-state migration and chain remain independent gates, not implicit passes.

**Then stop at S03.1.** The next memory-state adoption decision remains separate.
Do not use this handoff to authorize `remember`, writes, metadata migration or
full knowledge-service replacement.

## Review sources

All Fusion implementation paths above were reviewed at:

```text
https://github.com/machieke/fusion-module-interfaces/tree/2bddbc3467f98ed258741a21a329230a0cd21dd9
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/2bddbc3467f98ed258741a21a329230a0cd21dd9/docs/omega-adoption/mettaclaw-neoclaw/s03.md
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/2bddbc3467f98ed258741a21a329230a0cd21dd9/docs/omega-adoption/mettaclaw-neoclaw/s03-contract-decisions.md
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/2bddbc3467f98ed258741a21a329230a0cd21dd9/docs/omega-adoption/mettaclaw-neoclaw/interface-gaps.md
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/2bddbc3467f98ed258741a21a329230a0cd21dd9/integration/neoclaw/memory_embedding.py
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/2bddbc3467f98ed258741a21a329230a0cd21dd9/integration/neoclaw/memory_bootstrap.py
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/2bddbc3467f98ed258741a21a329230a0cd21dd9/integration/neoclaw/memory_build.py
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/2bddbc3467f98ed258741a21a329230a0cd21dd9/fusion/neoclaw_memory.py
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/2bddbc3467f98ed258741a21a329230a0cd21dd9/evidence/s03/source-state.json
https://raw.githubusercontent.com/patham9/mettaclaw/2af37c3fec18613de54ca42fde2382a9087d4524/src/memory.metta
```
