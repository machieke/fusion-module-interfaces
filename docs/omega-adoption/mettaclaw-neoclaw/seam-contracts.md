# Candidate seam contracts — design, not implementation

Interface, implementation, transport and placement are separate choices. Current Omega calls are in-process PeTTa → Python/Prolog and external SDK calls. Current Fusion bindings are in-process or local JSON subprocess/stdio (`fusion/bindings.py`), **not a deployed generic remote API**. Current private module descriptors select local-only placement. The remote envelopes below are prospective, deliberately named operations; no server, contract change or adapter was added.

The exact current Fusion signatures come from [pinned ports.py](https://github.com/machieke/fusion-module-interfaces/blob/33388d20cb10c5f9878a463a6d0debba7949e35a/fusion/ports.py); current validation/dispatch is additionally constrained by `contracts/*.schema.json`, `fusion/service.py`, `private.py`, `lookup_composition.py` and the relevant validators. Python protocol declarations alone do not establish a supported wire operation. In particular M5 uses `PagedRelations`/`ExactSearch`; the earlier `Relations`/`Search` declarations in that file are not the exercised M5 contracts.

## Common prospective transport contract

For a selected **named** mutating/job operation, a new authenticated transport would carry:

```text
Submit = {request_id, scope_ref, selected_descriptor_digest, operation,
          profile, canonical_arguments, intent_digest, correlation_id,
          reply_route, absolute_deadline_ms}
Accepted = {request_id, intent_digest, selection, job_id, state: accepted}
Terminal = {request_id, intent_digest, selection, job_id,
            state: completed|failed|expired, result_ref?, result_digest?, error?}
```

These fields are a **proposal**, not the existing Fusion wire schema. Identity comes from authenticated transport credentials and live policy; a body `scope_ref` requests a scope and does not grant it. Bind digest to the exact canonical arguments, profile, selected provider, scope, correlation, route and original deadline. Reject extra fields/unknown profiles, malformed values, stale selection, unauthorized scope/route and conflicting replay. Raw credentials and model API keys never enter this envelope.

Before returning `Accepted`, the execution owner persists the exact intent and acceptance. It owns job/result/outbox state; the pure kernel owns no job journal. On replay, current authorization is checked and the original job/terminal result is returned. Computation may run again after a crash, but one logical result/terminal effect is accepted. The result payload owner commits bytes before execution commits its terminal/outbox reference; stable subkeys recover orphaned payload writes. The caller persists a validated completion before mailbox acknowledgment. Ack loss replays the same delivery. Do not reset deadline or retry counters on restart. Replayed terminal reads may be permitted after deadline, but new work may not start then.

Proposed typed errors: `INVALID_ARGUMENT`, `UNSUPPORTED_PROFILE`, `UNAUTHORIZED`, `CONFLICT`, `NOT_AVAILABLE`, `DEADLINE_EXCEEDED`, `CAPACITY`, `INVALID_RESULT`. These are candidate operation errors, **not a claim that every name already exists in Fusion's vocabulary**. Translate to a documented legacy presentation only after preserving status internally. Never interpret an empty string, `None`, socket write or timeout as a durable acceptance/result.

## S01 — bounded NAL truth deduction (recommended first)

- **Exact local call:** `metta("(Truth_Deduction (stv f1 c1) (stv f2 c2))")` → `sread` → `eval` under inference limit → `repr`; `lib_nal.metta:8–10` supplies the numerical function. Inputs are two STVs; output is one STV. No store is mutated by that function. General `metta` can do far more and is excluded.
- **Existing Fusion:** `PLNKernel.applyRule(task: JSON, premises: tuple[JSON,...], deadline_ms: int) -> JSON` under `grounded-five-premise-deduction/1`; `DelegatedExecution.submit(command: Mutation, operation: Literal['inspect_atom'], ref: AtomRef, correlation_id: str, reply_route: str, deadline_ms: int | None) -> JobAcceptance`, plus status/result. Neither admits this NAL call today.
- **Proposed remote cut:** DRAFT `neoclaw-nal-truth-deduction/1`, operation `nal_truth_deduction`, arguments `{premises:[{strength:decimal_string,confidence:decimal_string}, ... exactly 2]}`. No expression, import, file path, variable, URL or arbitrary function name is accepted. Finite values in [0,1], max input 4096 bytes/output 4096 bytes, fixed original float evaluation order; transport decimal strings must round-trip to the selected runtime's numbers. Pin PeTTa, SWI, NAL source and serialization together. Guards restrict admitted inputs without replacing mathematics.
- **Output:** exactly one validated STV plus request/profile/runtime identity; legacy rendering must match the pinned local path for admitted inputs. New named Execution profile owns acceptance/result/outbox; separate pure PLNKernel-family NAL adapter computes the result. New request/premise DTO is required rather than inventing five belief snapshots from two numbers. No C1 observation, C2 admission or C4 work selection occurs.
- **Placement/authority:** initial remote trial uses generated shareable STVs only. Existing private PLN profile remains local. A future explicitly private-authorized profile needs separate policy review; no secret or private claim hash is exported. Caller policy and selected provider remain local.
- **Recovery:** common durable job contract above; bounded pure recomputation allowed, duplicate logical result forbidden. No fallback unless composition policy explicitly permits an equivalent same-profile local provider and records the decision with the same request identity.
- **Mismatch:** NAL is not the existing guarded five-premise PLN. Also `|-nal` has deduction **and exemplification with the same inheritance-chain pattern** (lines 110 and 113); a future broad-rule adapter must preserve both outputs. This first slice avoids silently truncating `|-`/`|-nal` results by selecting the already named `Truth_Deduction` function.

## S02 — external web search

- **Local:** `search(str)` → `websearch.search(query,max_results=10)` → `search_(query)` → `DDGS.text(query,max_results=10)`. Outer max_results is ignored. Returns title/snippet text, drops URLs; exceptions return `""`.
- **Existing Fusion:** same Execution signature above, currently only `inspect_atom`; Search.query is an owned-knowledge projection, unsuitable here.
- **Proposed:** DRAFT `external-web-search/1`, operation `web_search`, arguments `{query:utf8<=2048 bytes,max_results:int 1..10}`; result `{items:[{title,url,snippet}],observed_at,provider_revision}` capped at 32768 bytes, with per-field limits/escaping and explicit truncation status. Initial facade fixes max_results=10 to match existing command vocabulary; bounded provider-call timeout fits the original absolute job deadline. Pin DDGS/dependencies.
- **Privacy/authority:** user-approved query only, no implicit prompt/history export. Operator controls outbound domains/credentials if needed. Treat result text as untrusted data, never executable commands.
- **Recovery:** persist first accepted result. Re-execution before result commit may contact upstream more than once; only one logical result is delivered, no claim of exactly-once upstream request or repeatable web contents. Deadline/error distinguished from no results. Current successful formatting can be reproduced; its silent-error behavior should not be retained internally.

## S03 — core memory read composition

- **Local:** `query(text)` → embed → `query_with_ids_and_dists(vector,k)` → `get-promotion` → link/STV lookup → display. The Python query returns `[uuid,time,document,distance]`; content is bundled with projection output today.
- **Existing Fusion:** `ExactSearch.query(AttributeQuery(scope_ref,expression,minimum,limit=2,cursor=None,profile='exact-attributes/1'))`; `AtomCommitSource.head(scope)` and `readCommits(scope,after,through,limit)`; `ProjectionMaintenance.catchUp(scope,limit)` / `beginRebuild(Mutation)`. `PagedRelations.outgoing/incoming(ref,limit,cursor=None,snapshot=None)`, `getRelation(ref)`; `AtomStorage.getMany(refs)`; `BeliefRevision.readBelief(claim,context,revision)`; `Attention.select(scope,context,eligible,limit)` currently STI, **not promotion**.
- **Proposed:** DRAFT vector `query(scope,embedding_profile,vector,k,minimum_source_head,cursor?)` → refs/distances/generation/observed head/page and freshness metadata; DRAFT promotion `rank(scope,eligible_refs,as_of_clock,limit)` → score/policy/time receipts. Immutable accepted-source events must identify payload + embedding/profile enrollment; Search may consume only ports, never Chroma's DB. No such legacy feed exists today. Initial target can only use a new disposable corpus, not pretend it rebuilt existing user memory.
- **Target relation/payload/belief reads:** stable memory ref → typed relation refs → actual payload and explicit belief context/revision. An episode-handle atom/schema is needed for C1 linkage; C1 EpisodeRef itself is not an AtomRef. Query result carries individual owner revisions; no global transactional snapshot is promised.
- **Privacy/authority:** all existing private data stays local; new authorized remote read profiles must bind caller/scope/query/cursor and selected generation. No read bypass via shared filesystem. Read retry may return newer data unless pinned generation is explicitly supported; expired snapshot returns typed unavailable rather than silently changing page.
- **Recovery:** read acceptance is validation, not a mutation commit; no delivery ack for a synchronous read. Search maintenance commits checkpoints separately. Caller may persist request/read versions for retry; no new inference or evidence is created. Cold rebuild/source freshness is a prerequisite, not present-day coverage.

## S04 — episode provenance and belief revision

- **Local:** `support/contradict` → `tvUpdate(time,episodeTime,polarity)` → link → get_stv → `Truth_Revision(old,(polarity,.5))` → set_stv. Only link strings deduplicate; numerical replay does not.
- **Existing Fusion:** `recordEpisode(Mutation,source)`; `appendEvent(Mutation,EpisodeRef,expected_sequence,event)`; `pendingEvidence(EpisodeRef,limit)`; `submitEvidence(EvidenceSubmission)`; `readBelief(claim,context,revision)`; `acknowledgeDelivery(Mutation,completed)`. Submission binds evidence **or** admitted support, expected revision, profile/runtime selection and independence. Completion acknowledgment requires trusted consumer authority; not a fabricated decision snapshot.
- **Proposed remote operation:** none admitted under current private-local-only profiles. A future NAL-compatible evidence profile needs explicit claim/episode IDs, event polarity, immutable evidence ref/root, expected revision and selected math runtime. C1 owns event/pending delivery; C2 owns admission/revision/retained alternatives; math is stateless.
- **Privacy/recovery:** private initially. Retry evidence by its owner-issued identity, retain contrary observations, reconcile through owner ports and trusted completion; no timestamp-based independence proof or re-import of an already derived conclusion. Old STVs cannot be migrated honestly without missing provenance. Requires G04/G06/G11 decisions before remote eligibility.

## S05 — promotion ranking and adjustment

The historical draft below is preserved. S05 now selects this exact profile for bounded local adoption; see [executable contract decisions](s05-contract-decisions.md) and [executed evidence](s05.md). It does not approve remote private placement.

- **Local:** `promote/demote(time)` resolve UUIDs, compute `value*(1+dt/86400)^(-.7)`, add/subtract one with caps, set time/value and commit SQLite. `get-promotion(current_time,uuid)` is read-time decay.
- **Existing Fusion:** `Attention.submitStimulus(Stimulus)`, `readAttention(target,context)`, `select(scope,context,eligible,limit)`, `advance(Mutation,context,expected_step,steps)`; closure adds `submitFeedback`/`resolveFeedback`. Integer STI, logical steps/causes and deadlines do not match the wall clock policy.
- **Proposed:** DRAFT `wall-clock-promotion/1`; `adjust(scope,target,cause_id,delta=+1|-1,expected_revision,clock_receipt)` and `rank(scope,eligible,as_of,limit)` with fixed caps/decay/ties/backward-clock behavior. These fields remain a design pending policy choice; no remote acceptance contract is approved.
- **Authority/recovery:** one promotion owner persists cause receipt/value/time atomically; caller cannot choose a clock to amplify rank. Private local default. Replays preserve original clock/identity, never retime as STI feedback. No promotion-state migration or new attention research.

## S06 — durable mailbox with legacy channel transport

- **Local:** `send(text)` discards transport outcomes; `receive()` clears text buffer. IRC socket has no durable ID; Mattermost post ID is discarded after a volatile seen set.
- **Existing Fusion:** `Messaging.send(Mutation,ref,route,correlation_id,reply_route) -> MessageAcceptance`; `poll(scope,route) -> MessageDelivery|None`; `ack(Mutation,route,delivery_id)`. Payload is an AtomRef, not raw text. Policy checks current principal/scope/method/route.
- **Proposed:** a named transport-adapter profile retains server ID when available, persists ingress before delivery, and maps accepted payload refs to configured channel routes. No arbitrary recipient/token in model arguments. Private payload storage and mailbox placement require compatible profiles; current local profiles stay local.
- **Recovery:** separate inbox, execution/application receipt and egress outbox commits. Poll repeats until ack after local application receipt. Mailbox dedup is possible; exactly-once IRC delivery is not promised across ambiguous sends. Bound queues/backpressure; persist transport errors. Mapping display names to authenticated principals is a prerequisite, not solved by the bot token.

## S07 — model completion

- **Local:** selected wrapper accepts prompt/model/output/reasoning args; text loop/provider fallback differs from fixed Anthropic vision path. Eager clients require environment keys.
- **Existing Fusion:** no adequate ModelInference interface; kernel and current Execution do not cover this behavior.
- **Proposed interface:** `complete(model_profile,input_parts,max_output_tokens,budget,deadline,request_id)` with pinned provider/model, modalities, result text/usage/finish reason and error identity. SDK request schema/version, retry policy and billing ambiguity must be declared. No generic execution escape hatch.
- **Placement/recovery:** policy and secrets local/operator-owned; explicit private prompt disclosure. Save first accepted result and spending receipts; repeated provider calls may incur cost after ambiguity, so do not promise exactly-once billing. Not a first slice.

## S08 — embeddings

- **Local:** `embed(str)` selects Local E5 or OpenAI model; local vectors normalized, hosted model/metric contract undeclared.
- **Existing Fusion:** no Embedding port; exact Search does not accept vectors.
- **Proposed interface:** `embed(embedding_profile,texts,request_id,deadline)` → vectors + exact model revision/dimensions/normalization/numeric encoding; bounded text/batch/output. Search descriptor must require this exact profile. No automatic cross-model vector mixing.
- **Placement/recovery:** text/vectors private unless authorized; weight cache owned by embedding provider, not Search. Provider result identity/cache and model reproducibility explicit. Reindex/migration of existing vectors is out of scope; no swapping deployed model under the same profile.

## S09 — media / perception

- **Local:** URL resolution → continuous sampler or ffmpeg → snapshot/reset/JPEG → base64 → model. Threads, files and resets have independent effects.
- **Existing Fusion:** no Perception contract; media decay is not Attention and an `episodes` folder is not EpisodicMemory.
- **Proposed interface:** only after product decisions, a bounded `capture(source_handle,capture_id,window,format,deadline)` → immutable media ref + time/source/provenance receipt; separate model inference. Source handle is operator-authorized, not arbitrary network/process text.
- **Placement/recovery:** private local initially. Explicit retention/consent and source identity needed; ambiguous reset/capture cannot be recovered by inventing prior frames. Continuous sampling is not admitted into current bounded Execution. No remote prototype recommended yet.

## S10 — arbitrary shell, MeTTa and filesystem mutation

- **Local:** `shell(str)`, `metta(str)`, `read-file(path)`, `write-file(path,str)`, `append-file(path,str)` under ambient process authority.
- **Existing Fusion:** `inspect_atom` only; no safe general-purpose remote equivalent.
- **Remote contract:** **none proposed**. `NOT_REMOTE_SAFE` until fixed operation schemas, sandbox/resource/path policy, effects and recovery are separately approved. Keep these local; do not wrap them in the common envelope and call the problem solved.
- **Authority/recovery:** local user policy must constrain host effects. Process kill can leave effects behind; replay is not idempotent. No automatic remote filesystem mount or remote access to a private worktree.

Registry/Resolver/Authorization are cross-cutting dependencies of every future admitted seam; they remain distinct families. DA remains below AtomStorage with opaque bytes, never embedding, episodes or truth metadata. ConsensusFinality has no observed Omega counterpart and is excluded from all proposed slices. Nothing here implies remote means chain.
