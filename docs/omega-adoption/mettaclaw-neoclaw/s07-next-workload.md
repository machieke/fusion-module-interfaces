# Proposed evaluation: retrieve a synthetic fact, then reply over IRC

**Generation-disabled preparation is qualified; live execution is not authorized.**
The original specification below is retained. The preparation implementation and
its qualification are tracked in [the preparation decisions](retrieval-preparation-decisions.md)
and [the preparation report](retrieval-preparation.md).
Effective additional live-generation allowance: **ZERO**. This is a workload
proposal, not the historical S08 Embedding candidate. Existing X02 query and
append encoding are sufficient; no new embedding module is proposed.

The conditional live-evaluation brief has now been reviewed against preparation
publication `01d0b023e6990670eae65e14ed5910e64e72f929`. Current status is
**AWAITING_LIVE_AUTHORIZATION**; see the [static authorization review](../../../evidence/retrieval-live/authorization-review.json)
and the live-evaluation status below. The disabled proposal remains unchanged.

The question is whether the real model can select the adopted native `query`,
use its actual returned memory in the next model input, and propose a correct,
approved reply that the independent IRC peer observes. S07 demonstrated this
sequence with a numerical tool and empty promoted context. It did not demonstrate
retrieval-grounded generation over populated memory.

## One bounded workload

An operator creates a **fresh synthetic corpus** through actual native
`remember <approved text>` in a separate setup session using the existing S03.2
adopted append path. No raw Chroma insertion or test answer-reference list is an
authoritative source. Include one target fact and at least two distractors with
distinct generated project names and locations. For example, the shape is
“Synthetic project NAME keeps its calibration card in LOCATION.” Generate and
freeze the actual values only when the future workload is authorized. Keep the
target location out of the evaluation prompt, peer question, skill descriptions
and any promoted memory shown before retrieval.

Complete and record all four separate setup observations: immutable storage
acceptance, named Search publication, local metadata/view readiness and native
`REMEMBER-SUCCESS`. Freeze the ready enrollment head and record the exact
payloads, E5 revision, query text, distractors and expected fact in a **local
evaluator file inaccessible to the model/provider**. Do not put this answer in
model-visible configuration. Model and retrieval providers remain separate owners.

In a new measured session, the real isolated IRC peer asks where that project's
calibration card is stored. The first real completion must choose the exact
approved native query. After its real native result is committed, the peer sends
a second approved instruction to answer using the preceding tool result. This
uses the existing two-input loop pattern; it introduces no scheduler. The second
completion must choose a bounded native `send`. The response is consumed as
generated: no alias, rewriting, repaired command or fallback.

The measured session must not contain the setup `remember` result or command in
history. Setup and measured sessions use explicit ready-view composition; no
operator configuration edits are allowed between query and reply. This workload
does not claim model-directed memory creation, support, contradiction or promotion.

## Exact contract and authority decisions

| Boundary | Reused contract and admitted arguments | Required owner/authority |
|---|---|---|
| Setup only: `remember <text>` | `neoclaw-append-only-memory/1`; one exact approved nonempty UTF-8 string, within the existing 2,048-byte intersection and encoded payload bounds; no multiline command or quoting tricks | Existing application occurrence, exact `inputs` mapping, append/disclosure authorization; no authority to write in the measured model session |
| Query encoding | `embedding@1.0.0`, `neoclaw-e5-query-text/1`; native `string-safe` once, unprefixed pinned E5, normalized 1,024 float32 vector | Separate encoder; exact helper input, model, occurrence, deadline and encode/disclose authority |
| Append encoding | `neoclaw-e5-memory-text/1`, same E5 model and preprocessing | Setup encoder only; its placement selected independently of retrieval |
| Native `query <query>` | `semantic-embedding-memory/1`; one fixed approved UTF-8 query of 1–2,048 bytes, exact `queries` membership, native recall=2/similarity=4/inflation=4 unchanged | Search owns the immutable generation; AtomStorage owns/hydrates verified authoritative bytes; application retains selected view/vector/result |
| Local enrichment | S04 owner-bound belief display plus S05 `wall-clock-promotion/1` score/context reads | Local C1/C2/Attention and compatibility labels; no evidence, promotion or Search mutation in the measured session |
| Text completion | Existing `model.inference@1.0.0`, `neoclaw-ollama-qwen38-text/2` runtime and numerical settings | Independent completion owner; prompt bound before reservation, captured before whole-batch admission; exact current authority |
| Native `send <body>` | S06 `isolated-irc-mailbox/1`, existing AtomStorage/Messaging and exact-body approval | Local output policy, one reserved socket attempt, no automatic resend; peer observation separate from acceptance/socket return |

The model-visible grammar is exactly **one line per call**: `query <the selected
query>` on the first call and `send <one approved body>` on the second. The native
parser stays in use. A successful parse still requires the entire batch to match
the operator's exact command allowlist. No `metta`, `search`, `remember`, shell,
support/contradict or promote/demote is authorized in the measured model session.

**Historical S07 `/9` cannot express this workflow by configuration alone.**
`model_transport.configuration` permits only `metta` and `send`;
`model_startup` advertises those skills with a deduction-specific prompt;
`neoclaw_model_disclosure.disclose` accepts only the narrow numerical
`COMMAND_RETURN` feedback grammar. The existing application can dispatch `query`
under other adopted compositions, but that does not authorize it through S07.
Those decisions were pending at closeout. The assigned preparation now selects
`controlled-native-loop/10` and `synthetic-retrieval-query-send/1`, with exact
component consent and a trusted retained-view receipt. The [decision record](retrieval-preparation-decisions.md)
describes this new implementation; historical `/9`, model profiles and parser
behavior remain unchanged.

Keep promoted context empty for the first workload so the target fact can reach
the model only through query. The query result is the required **nonempty**
synthetic context. Approve its complete native representation, including generated
IDs, creation labels and belief/prior display, before provider disclosure. Validate
it against the actual captured owner-bound projection; a digest or
`synthetic=true` flag is not consent. Do not import S04/S05 private canaries.

An explicit **egress decision is required**. Recommended: freeze a finite exact
set of harmless synthetic answer bodies covering all candidate locations, plus
an exact “insufficient retrieved information” refusal. The authority service may
hold this set; do not show the target-specific approved answer to the model or
embed it in the task prompt as S07 did. A general response-format instruction may
specify “Synthetic answer: LOCATION.” Include all candidate bodies, rather than
only the correct one, so approval cannot serve as an answer oracle. The evaluator
scores factual correctness separately from publication authorization. The preparation implements this finite policy under its explicit selection; it
does not authorize a live campaign or unrestricted generated-output publication.

## Definition of ready and evaluation

1. Separate approval covers the corpus, every prompt recipient, query-result
   representation, output-body set, implementation changes and finite live budget.
   Review the new application/disclosure selection before any generation.
2. Original native and adapted local/HTTPS query checks agree on this corpus on
   the admitted domain. Real E5, Chroma, DeTTa and AtomStorage hydration are used;
   original/adapted checks establish plumbing, not live model usefulness. Confirm
   the target is actually in the native result; otherwise stop with a retrieval
   failure before measuring model use. Do not repeatedly change the corpus/query.
3. Freeze a measured plan with the same HTTPS mailbox, local cognitive state and
   fixed retrieval/encoder placement in both model-placement cases. Use local
   ModelInference once and authenticated same-host HTTPS ModelInference once.
   Independent setup sessions may bind the same declared synthetic fixture, with
   fresh identities/journals. Preserve the E5-free HTTPS retrieval caller where
   applicable. No multi-host claim or private remote cognition.
4. Correct retrieval requires candidate refs/distances from Search, digest-verified
   payload reads, unchanged native enrichment, and the exact target fact in the
   captured native result. The next bound prompt must contain that actual result,
   not a separately assembled expected answer. Correct answering requires the
   model's proposed fact to match the retrieved content and an actual peer-observed
   approved body. A permitted but wrong answer fails usefulness.
5. A missing/ambiguous fact must not cause an invented location. The approved
   refusal is appropriate only when the retrieved content does not establish the
   fact. Missing or lagging Search views stop retrieval explicitly; they are not
   silently rebuilt or replaced. Existing query occurrences retain their view and
   captured bytes even if a later view becomes ready. Replaying a captured model
   response must not regenerate; current revocation can still prevent release.
6. Malformed/unsupported commands fail whole-batch admission. Their refusal is a
   contract success and a task-completion failure. Unknown send outcomes stay
   spent; absence of peer observation is a timeout/unknown delivery, not success.

**Proposed budget, not effective authorization:** two predeclared placement
sessions, at most two generations each: **four calls**, at most **6,000 output
tokens/call** (24,000 reserved maximum), existing **300,000 ms** input/model
deadline and **30,000 ms** tool/context deadlines. Keep eight application model
RPC reservations/occurrence, one backend reservation and existing read/encoder
budgets. Do not extend accepted deadlines to make this workload pass. Fresh
profile changes, if necessary after offline readiness measurements, need separate
review before freezing the live plan.

Stop a session at its first failure, rejection, timeout or ambiguous effect and
retain every attempted and unspent slot. The second predeclared placement may run
once only if separately authorized in the frozen plan. No replacement attempts,
retry-until-green, within-run prompt tuning or response repair. Finish after the
four-call ceiling even when no complete workflow succeeds. Report retrieval,
admission, answer grounding and peer observation as separate outcomes; no general
reliability estimate follows from this small workload.

Historical closeout status: **NOT_IMPLEMENTED / NOT_RUN / LIVE_AUTHORIZATION_ZERO**.
The assigned preparation adds a distinct `/10` composition; its final preparation
gates are reported separately. **LIVE_MEMORY_WORKFLOW=NOT_RUN** remains unchanged.

## Live evaluation authorization status

The conditional brief does not grant generation authority. No new user
authorization has been bound to a frozen campaign. The existing proposal still
has `authorization=null`, zero effective allowance, an empty ledger and
`executable_entrypoint=null`. Its four-call ceiling describes two proposed
sessions, not four authorized calls. No active campaign or measured journal was
created during this review.

The focused static check matched 102 delivery hashes and the 214-file
executable/test source set to both the preparation publication and starting
checkout: 297 unique paths including the manifest itself. All four final
preparation run manifests retain their original working-tree source identity.
The historical 99-method qualification and earlier S07 results were not rerun or
relabelled. Runtime/model availability remains unchecked.

Source inspection confirmed the narrow future runner work: read the actual
parsed/admitted send body and observe that exact body from the selected peer
route/sender; use observers bounded by accepted deadlines; export actual live
records separately from fixture evaluation fields. Preparation's `workflow`
waits for `BODIES[0]`, its test helper selects a body from authored commands, and
its exporter labels fixture evaluations and `NOT_RUN`. Those remain correct for
preparation and remain unchanged. The real backend is the existing
`OllamaCompletion.complete`; the historical numerical S07 runner's 6/12-call
campaign and load path were inspected as source only.

A future frozen campaign must identify the tested runner bytes, fresh native
remember setup/view, exact synthetic disclosure and outputs, recipient/provider
and TLS bindings, four unique possible slots, and explicit user authorization.
The current proposal is not that frozen executable campaign. This review adds
no runner or runtime changes and performs no setup, fixture replay, readiness
probe, model load or generation. Its changes are this status entry, the supplied
brief and the static review record.

| Dimension | Proposed `model-local` | Proposed `model-https` |
|---|---|---|
| Runtime readiness | NOT_CHECKED | NOT_CHECKED |
| Generation slots | UNATTEMPTED | UNATTEMPTED |
| Captured responses | 0 | 0 |
| Command admission | NOT_REACHED | NOT_REACHED |
| Retrieval | NOT_REACHED | NOT_REACHED |
| Second-input binding | NOT_REACHED | NOT_REACHED |
| Correctness | NOT_REACHED | NOT_REACHED |
| External delivery | NOT_SENT | NOT_SENT |
| Task | NOT_RUN | NOT_RUN |

```text
PREPARATION_STATUS=READY_FOR_LIVE_AUTHORIZATION
CAMPAIGN_STATE=AWAITING_LIVE_AUTHORIZATION
PLANNED_GENERATION_SLOTS=4
AUTHORIZED_GENERATIONS=0
RESERVED_GENERATIONS=0
CAPTURED_RESPONSES=0
ADDITIONAL_LIVE_GENERATIONS=0
LIVE_MEMORY_WORKFLOW=NOT_RUN
```

### 2026-10-26 runner preparation

The missing runner is now implemented and qualified with generation denied. See the [preparation report](retrieval-runner-preparation-report.md) and [runnable commands](retrieval-live-runner.md). Campaign `retrieval-grounded-20261026-02` is frozen and awaits separate live authorization. No additional live generation occurred, and `LIVE_MEMORY_WORKFLOW=NOT_RUN`. Earlier preparation and authorization-review records remain historical evidence.
