# Codex handoff — S03.2: append-only native remember → query adoption

## 1. Objective and stop boundary

Continue the completed S03.1 implementation in `machieke/fusion-module-interfaces`.
Its reported parent is `2bddbc3467f98ed258741a21a329230a0cd21dd9`; that parent alone
is the S03 baseline, NOT the full S03.1 implementation. Reconcile the actual working
tree or published descendant with `evidence/s03_1/source-state.json` before editing.
Preserve unrelated changes, applicable AGENTS.md instructions and historical evidence.

**Proposed next increment:** allow the real native `remember` command to append a
new, explicitly approved synthetic memory through the existing module boundaries,
and allow a later native `query` in the SAME application session to discover it.
No operator re-enrollment, expected-answer injection, configuration editing or
application restart may be required between successful remember and subsequent query.

This extends S03's bounded memory adoption with one append-only command. It does
not rename the mapping's S04 (episodic provenance and belief revision), adopt the
whole memory service, or expand the historical 15-family reference denominator.
It is a proposed engineering task, not a previously agreed product requirement.

**Stop at S03.2.** Use only a new generated corpus and fresh application journals.
No existing user-memory import or migration; update, forget, unlink, general link,
support, contradict, promote or demote adoption; new evidence mathematics; full
Omega/live-model deployment; multi-host networking; chain work; general ingestion
framework; event bus; scheduler; or production-private-memory service.

The success criterion is a usable write-to-read lifecycle, not more read-only
fixtures: memory that was absent from the corpus is created by actual native
command dispatch, durably enrolled, indexed, and later retrieved through Search
and AtomStorage without a legacy candidate-search or payload fallback.

## 2. Review basis and source identity

This handoff follows a review of selected public S03.1 source, its report, decisions,
measurement file, tests and source/gate manifests, plus the pinned native memory
and Chroma-helper source. The reviewer did not run the native suites, reconcile
all working-tree hashes, or verify an immutable publication commit for S03.1.
Public `master` paths were retrieved; Codex must bind conclusions to actual bytes.

S03.1 records 114 distinct test methods: 18 new (5 contract fixtures and 13 integration
methods) and 96 S01–S03 regressions. The earlier 340-test S03 result remains a
historical broader run; the 114 is neither 114 additional tests nor a rerun of all
340. Repeated comparisons and parameterized kill phases are separate evidence.
The manifest also distinguishes the 18-test source from a subsequent two-line
operator-path correction and its rechecks. Preserve those identities.

Before changes, record the selected commit/worktree, match test and final source
manifests, and explain any differences. If only the S03 parent is present, report
the missing S03.1 inputs rather than recreating it from a description. Do not reset,
blindly stage, or publish unrelated work to manufacture a clean baseline.

Retain these dependencies unless an actual incompatibility is evidenced:

- MeTTaClaw `2af37c3fec18613de54ca42fde2382a9087d4524`.
- Chroma helper `218484875d5d1bfb217a9a03d3983dc1ed9d406c`.
- PeTTa `fea83178af3722666d2948d074591d10a3134f56`; verified SWI 10.0.1.
- DeTTa `272888f264dd2dde18b574cabb53c266b0dac2ec`.
- E5 `intfloat/e5-large-v2@f169b11e22de13617baa190a028a32f3493550b6`, with the
  existing model/tokenizer hashes, normalized CPU float32 path and SDK locks.
- Existing separate Fusion PLN/SWI profiles. Do not rebaseline them for this task.

## 3. Inspect these implementation boundaries

| Source | Finding or reuse target to verify |
|---|---|
| Native `src/memory.metta` | `remember` calls `createMemory`; creation samples time, embeds, calls the Chroma helper, then links the creation label. `query` retains its native composition. |
| Pinned helper `lib_chromadb.py` | `remember` allocates a UUID and writes content/vector/time; linked labels are metadata; missing STV fields default to `(1.0, 0.5)`. |
| `fusion/vector_enrollment.py` | Existing port-only enrollment persists payload, vector, then validated enrollment under stable mutation keys. It currently runs operator-side. |
| `fusion/atom_feed.py`, AtomStorage sessions | Authoritative acceptance sequence, immutable records, replay and live authority. |
| `fusion/adapters/chroma_vector.py` | Builds and verifies an unpublished generation before publication; current `build` allocates a new generation each call, including retries. |
| `fusion/neoclaw_memory.py` | The whole selected snapshot and metadata seal currently belong to the frozen application binding. Queries cannot simply switch generations mid-session. |
| `integration/neoclaw/memory_bootstrap.py` | Sealed metadata-only local Chroma; legacy remember, link, STV mutation and candidate/payload helpers are forbidden. Do not remove that guard globally. |
| `fusion/neoclaw_application.py` | Native accepted occurrences, command admission, budgets, captures and context handoff. |
| `fusion/neoclaw_embedding.py`, `embedding_*` | Query-only input/consent profile, captured vectors, encoder attempt accounting and independently selected placement. |
| `fusion/vector_composition.py`, `vector_transport.py` | Read-oriented wire admission and principal binding. A descriptor listing create/build is not permission for arbitrary network writes. |
| `integration/neoclaw/{native_loop,loop_bridge,memory_startup}.py` | Checked native integration; preserve actual parsing, evaluation and next-context processing. |
| S03/S03.1 reports, decisions, tests and manifests | Prior parity, failures, isolation, native semantics and explicit unrun work. |

Verify the selected metadata SDK compatibility already used by the native oracle.
Do not make a new vector database or a replacement query algorithm for this task.

## 4. Preserve native behavior; explicitly strengthen recovery

First run an original native `remember` followed by `query` on a disposable generated
corpus. Establish actual parser/input behavior, returned token, creation-time label,
UUID identity, stored content, embedding input, initial linked label and STV default.

Keep native `embed`/`string-safe`, normalized encoding, query ranking, promotion,
linked-label/STV rendering, native uniqueness and result construction. Raw memory
content and the post-`string-safe` encoder input are not necessarily the same bytes.
Apply each transformation once, and bind both representations explicitly.

The observed native defaults are compatibility metadata, not validated beliefs.
Do not manufacture a C1 observation, empirical evidence count, independence claim
or C2 support from a fresh record's default STV or its linked timestamp. A creation
label is not a unique episode identity or proof of provenance. Promotion defaults
and the existing zero-promotion behavior must be verified, not guessed.

The original helper allocates a new UUID on every physical call. The adopted path
must allocate a stable memory UUID ONCE per accepted native command occurrence and
persist it before effects. This is an explicit stronger replay guarantee, not a
claim that the legacy helper was idempotent. Different accepted occurrences with
identical text create distinct memory identities. Equal timestamps do not merge them.

Preserve the native time-sampling point before embedding. Persist the selected time
and memory identity before the first remote effect; do not regenerate them on retry.
For original/adapted comparisons, use declared UUID/time fixtures or an explicit
identity correspondence. Never require separately allocated random UUIDs to match
by coincidence, and never weaken production identity checks to simplify a test.

Expose `REMEMBER-SUCCESS` only after the bounded adopted workflow's required durable
append and same-session read visibility are confirmed. If storage committed but
publication or local metadata readiness did not, expose a distinct stored-but-not-
ready/pending/failure outcome with a recoverable occurrence. Do not return the
legacy success token unconditionally after a swallowed exception.

## 5. Ownership and the write path

Use a narrow native compatibility adapter and the existing application lifecycle.
Do not add another owner for truth, attention or authoritative memory payloads.

| Boundary | Owns in this increment |
|---|---|
| Native application | Accepted write occurrence, UUID/time, selected providers, captured encoding, bounded workflow progress, and its active read-view selection. |
| Embedding | Encoding under the selected, explicitly authorized memory-text profile; no corpus writes or search. |
| AtomStorage / AtomCommitSource | Immutable payload/vector/enrollment records, stable mutation identity, and committed source sequence. |
| Search maintenance | Rebuildable vector generations and truthful publication/source coverage. |
| Local compatibility metadata | Only the generated legacy creation-label/default-STV/promotion representation and immutable view selection; no new belief or attention mathematics. |
| Search / AtomStorage reads | Existing ranked references and verified payload hydration under the query's bound view. |

Preferred sequence:

```text
Actual native remember(text)
  -> accept occurrence; persist identity, time, input, selections and deadline
  -> authorize and capture the original E5 encoding through its selected port
  -> persist immutable payload, vector and validated enrollment through AtomStorage
  -> obtain evidence of the enrollment's committed source position
  -> prepare and verify a Search generation covering that position
  -> prepare the matching local metadata view using the committed append identity
  -> durably select that coherent read view in the application
  -> record and deliver the native successful result
Later actual native query(text)
  -> bind the selected read view for this occurrence
  -> existing Embedding -> Search -> AtomStorage -> native enrichment -> next context
```

Payload, vector, enrollment, search publication, metadata readiness, application
selection and result handoff are separate commits. Do not claim atomicity across
owners. A crash may leave unreferenced immutable records or an unused generation;
it must not produce an acknowledged invalid enrollment or an incoherent read view.

Reuse `vector_enrollment.enroll` through authenticated declared ports where it fits.
Extend only the missing narrow write/maintenance operations needed by the selected
profile. Do not read foreign SQLite tables, expose filesystem paths, accept arbitrary
code, or make Search create its own authoritative memory records.

Before persisting anything, validate the intersection of native text, embedding,
AtomStorage envelope, corpus and metadata limits. Byte limits after transformation
and serialization matter. Do not silently truncate content or raise all limits.

## 6. New consent/profile requirements

S03.1's `neoclaw-e5-query-text/1` specifically admits query-time helper inputs. Reusing
the same E5 arithmetic does NOT silently grant authorization to encode memory text.
Add a narrow declared memory-text purpose/profile, or another explicit compatible
versioned policy, and test it. Preserve the historical query profile unchanged.
The numerical model/representation must remain compatible with the existing corpus.
Do not add passage prefixes or choose another model just because this is ingestion.

Define write permission separately from read, disclosure and maintenance permission.
Only operator-approved synthetic append inputs and exact transformed helper strings
may enter the remote path. Approval records are not pre-enrolled data or expected
answers. Provider URLs, model identities, target scopes, keys and corpus selection
are not model-controlled command arguments.

A new read/write application profile with fresh journals is appropriate. Preserve
`controlled-native-loop/1` through `/4` and their old journal bindings. Do not turn
historical read-only records into writable sessions or relax identity guards.
Do not automatically call the new profile `/5` without checking the actual catalogue.

Credential rotation preserving the accepted principal may work under existing rules.
Substitution of a different authorized principal must not create, resume, publish or
disclose the original occurrence. Validate authority before new effects and before
returning replayed receipts/results. Revocation cannot undo bytes already committed.

## 7. Publication, local metadata and read-your-writes

This is the principal semantic extension. S03/S03.1 freeze an entire corpus snapshot
and metadata seal at application startup. Do NOT solve new visibility by rewriting
that configuration file or by silently changing an old query's stored request.

Use explicit application-owned read-view selection. A view binds corpus, source
identity/head, published Search generation, embedding profile and the local metadata
seal needed by native enrichment. It is a selection of already committed owner
states, not a new distributed knowledge revision or shared transaction.

Prepare the new Search and metadata states, validate their compatibility, then
atomically publish the application's pointer to that view. Readers must never see
a new candidate without its required local metadata. Only metadata for newly
created generated records is appended; pre-existing linked labels, STVs and promotion
values stay unchanged. Maintain the metadata-only guard: no caller-side copy of
remote payload text, embedding vectors or the candidate index.

A small generation-specific local metadata snapshot is acceptable. Its authority,
reconstruction source and replay identity must be explicit. Use the legacy helper's
supported interface or a narrow owner-controlled compatibility adapter, not foreign
SQL. Copying committed UUID/time/default metadata is not adopting general Relations,
BeliefRevision or Attention. Do not silently enable their mutating commands.

The same session's next newly admitted query must bind a ready view whose source
coverage includes the successful append. A lagging index must report not-ready,
not an empty or older successful answer. Read-your-writes means the appended record
is in the searchable corpus; it does NOT force every top-k query to return it.
Use a small, well-separated positive example where the native oracle retrieves it.

Existing queries retain their old view, captured vectors, enrichment time and
captured results. A new occurrence may select the new view; a replay cannot. Retain
old generations for the bounded experiment, and fail explicitly if an old generation
becomes unavailable. No retention/garbage-collection or live migration programme.

Publication retries must not create unbounded generations. The inspected build
allocates a UUID each time and has a finite generation cap. Add an exact logical
maintenance identity or a declared way to recover an already published generation
for this source head/build profile. Do not enumerate private index files from the
caller or use a fresh generation to disguise an unresolved earlier publication.

A sequential single-writer corpus is sufficient. Serialize overlapping writers or
reject them explicitly; do not claim multiwriter consistency. Call-driven bounded
maintenance is sufficient; no background scheduler. Separate index-build reservations
and limits from encoder evaluations and native read budgets.

## 8. Recovery and effect accounting

Reuse the application occurrence/receipt machinery, adding only the append's typed
state. Use stable owner-scoped mutation keys for each immutable record. Same identity
with changed content/time/model/selection conflicts; identical text in a later turn
is a new operation. An accepted storage receipt is not a fully searchable-memory receipt.

Capture the validated memory vector before enrollment. After capture, recovery must
not encode again. Before capture, physical inference may repeat only under the
original recorded attempt/deadline policy. A lost reservation can remain spent.
Do not refund it, adopt the caller's latest model, or reset the accepted deadline.

Recover already committed data and completed publication before issuing another
mutation or build. Preserve honest partial outcomes when deadlines expire. Receipt
observation after expiry may reveal prior completion; it must not secretly grant
new encoding, storage or maintenance work. Any separately authorized maintenance
attempt has its own explicit bound and identity and does not become a new memory
occurrence. Uncertain remote acceptance must never automatically become 'absent'.

At least these process-kill scenarios must traverse real providers:

1. Accepted UUID/time, before encoding or remote append: same occurrence on restart.
2. Vector captured; payload/vector persistence interrupted before enrollment: no
   reevaluation, no second logical memory, and no invalid published enrollment.
3. Enrollment committed before generation publication: accepted record retained,
   query freshness does not fabricate availability.
4. Search generation published before application read-view/result commit: reuse
   the matching publication; no extra memory or unbounded generation allocation.
5. Native success captured before next-context consumption: recover the same result;
   the later query uses the ready view without operator changes.
6. An old query captured under an earlier view, followed by a successful append:
   replay of the old query stays on its captured view/result and current authority.

Temporary provider failure, malformed receipts, scope/model drift, revocation,
credential substitution, bad certificates, generation-cap exhaustion, changed
semantics, Unicode/control content and transformation overflow need explicit tests.
No local legacy write/search fallback and no successful-looking empty answer.

## 9. Native demonstration and privacy

Run three comparable paths: original native remember/query, adopted local modules,
and adopted authenticated same-host HTTPS modules. Use actual native parser,
command evaluation, memory/embedding/query semantics and next-context consumption.
Deterministic model-response and channel fixtures remain permitted and labelled.

In the main adoption session:

- Begin with a small generated corpus and show the new memory identity/content is
  absent from its authoritative records and initial query result.
- Submit the approved memory through the actual native `remember` command.
- Query in a later turn of the same session and retrieve the newly created content
  through Search references and AtomStorage hydration.
- Repeat the write's original occurrence to demonstrate deduplication; separately
  accept the same text again to demonstrate a distinct memory occurrence.
- Restart at the new durable boundaries, then exercise the same native read path.

The query receives text and a freshness requirement, not the answer reference.
The provider must not be preseeded with the new memory, and the test must not append
it via an operator helper outside the command under test. Capture/audit stores may
be inspected by tests; they may not supply answers to the native consumer.

The HTTPS caller must still lack E5 inference libraries and model access. Real E5,
Chroma, DeTTa and TLS are required for positive adoption gates. The operator may
prepare initial distractors and approve future inputs without storing those future
memories. Preserve independently selectable encoder and storage/search placement;
one mixed configuration is sufficient alongside the main local/HTTPS comparisons.

Only deliberately shareable synthetic memory text, queries and metadata may leave
the caller. Preserve private canaries and endpoint/diagnostic checks. S03 already
sends raw query text to Search authorization; S03.1 separately sends transformed
helper text to Embedding. Document all actual recipients accurately. Never claim
vector-only disclosure or private-remote support from these generated tests.

Keep retrieved and written text as data. Do not evaluate returned content as MeTTa,
shell or new commands. Scripted model tests do not establish prompt-injection immunity.
Full user history, existing metadata, private vectors and credentials remain untouched.

## 10. Regression strategy, deliverables and gates

Run S03.1's applicable 114-method suite as a baseline and rerun affected S01–S03.1
behavior at completion. Add M5 feed/enrollment/search/storage tests for changed owner
boundaries, plus other contract and historical-profile tests selected by an explicit
impact map. Where common files change, explain how affected consumers are covered.

Do not automatically treat a selected regression subset as the full repository
suite, silently skip unavailable native prerequisites, or call a historical chain
pass a current run. Preserve existing historical scope guards; record intentional
new scope rather than deleting guards to force them green. Unchanged live web-search
or chain runs need not be repeated just to increase a test count; label them NOT_RUN.

| Gate | Required evidence |
|---|---|
| BASELINE_SOURCE | S03.1 tested/final bytes reconciled; selected regressions and impact map recorded. |
| NATIVE_ORACLE | Original remember/query, raw/helper bytes, time/identity and initial metadata behavior executed. |
| CONTRACT_AUTHORITY | Closed append/encoding/maintenance permissions and profiles; separate owners and principal binding. |
| APPEND_REPLAY | Stable occurrence/UUID/time; port-based payload/vector/enrollment; duplicate versus new occurrence tested. |
| READ_VISIBILITY | Same-session successful append is covered by later query; lag and partial publication explicit; old reads unchanged. |
| NATIVE_LOCAL_HTTPS | Actual loop, real E5/Chroma/DeTTa and TLS; no local E5 or legacy payload/candidate fallback on HTTPS caller. |
| PUBLICATION_RECOVERY | Real kills recover separate commits; repeated publication does not leak unbounded generations. |
| BUDGETS_PRIVACY | Deadlines/attempts remain spent; partial outcomes honest; live authority, canaries and untrusted text verified. |
| COMPAT_REPRO | Old read profiles and unaffected actions work; fresh-target declared-input reproduction with cache limits stated. |
| SCOPE_LEDGER | Exactly the append-only native remember path added; local enrichment and full-product limits not promoted. |

Deliver one S03.2 report, source/lock manifests, gate results, same-memory trace,
original/local/HTTPS comparison, and focused native/contract/failure tests. Update
the existing adoption ledger, contracts/ADRs and runbook rather than creating a
parallel architecture. Report exact final test hashes and later commits separately.
Count unique tests, repeated subsets and parameterized scenarios accurately.

Record observed append stages, publication lag, startup and caller cost without
inventing throughput or cognitive-quality improvements. Same-host process restart
with intact files remains the failure model. Full Omega, live hosted models/channels,
private remote memory, multi-host, chain, power loss and existing-state migration
remain separate unrun work.

A missing required dependency is BLOCKED; executed incorrect behavior is FAIL;
optional unexercised work is NOT_RUN. Useful partial delivery is appropriate when
blocked, but complete S03.2 requires the real native write-to-read gates.

**Then stop.** The bounded supported claim is:

> A controlled native Omega can append a new synthetic memory through independently
> placed module providers and retrieve it in a later turn of the same session,
> with durable identity, explicit publication, and recoverable result handoff.

This is not complete mutable memory, a production private-memory service, full
Relations/Belief/Attention adoption, or migration of existing knowledge.

## Review source locations

S03.1 implementation/evidence was reviewed from the following public paths. Resolve
an immutable commit or exact source manifest in the actual checkout; do not assume
that the historical S03 parent contains these additions.

```text
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/master/docs/omega-adoption/mettaclaw-neoclaw/s03_1.md
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/master/docs/omega-adoption/mettaclaw-neoclaw/s03_1-contract-decisions.md
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/master/evidence/s03_1/source-state.json
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/master/evidence/s03_1/verification.json
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/master/fusion/vector_enrollment.py
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/master/fusion/adapters/chroma_vector.py
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/master/fusion/neoclaw_memory.py
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/master/integration/neoclaw/memory_bootstrap.py
https://raw.githubusercontent.com/patham9/mettaclaw/2af37c3fec18613de54ca42fde2382a9087d4524/src/memory.metta
https://raw.githubusercontent.com/patham9/petta_lib_chromadb/218484875d5d1bfb217a9a03d3983dc1ed9d406c/lib_chromadb.py
```
