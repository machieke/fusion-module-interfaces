# Completed retrieval-grounded campaign: publication review

Campaign **`retrieval-grounded-20261026-02`** completed both declared real-model
memory query/reply workflows. Exactly four slots were reserved and spent, four
backend calls completed, and four responses were durably captured. Both native
sessions admitted the query and reply, consumed the actual captured retrieval in
the next prompt, and delivered the correct reply to the independent IRC peer.
No remaining slot or renewed authority is implied by this publication.

This review uses only existing versioned evidence. It starts from evidence
publication **`dba62caf72f9577349cc868edd29fd8b949172d7`** and does not start or
contact runtimes, inspect private journals, reserve calls, execute the campaign,
or generate text. Raw reports, historical test identities and labels remain
byte-for-byte unchanged. The [publication audit](../../../evidence/retrieval-live/publication-review/review.json)
records the static checks and exact changed-file scope.

## Review trail

| Binding or observation | Evidence |
|---|---|
| Separate user approval | [Approval statement and fixed window](../../../evidence/retrieval-live/retrieval-grounded-20261026-02/approval.json); SHA-256 `b8b5e1b295efd7e6b89ab7bfdbe1f785081cdee0696cbbe3833b6b12f0c08103` |
| Frozen plan | [Manifest](../../../evidence/retrieval-live/retrieval-grounded-20261026-02/manifest.json) and [external SHA-256](../../../evidence/retrieval-live/retrieval-grounded-20261026-02/manifest.sha256): `0b75644c3b0e198fc606bb3b781087a2048a40f21b67b36bd7a5a1000465adb1` |
| Exact executed implementation | [`66366cb4ed262ab8a87b96540d5c17fc8f0977ea`](https://github.com/machieke/fusion-module-interfaces/tree/66366cb4ed262ab8a87b96540d5c17fc8f0977ea); the manifest binds 189 execution source hashes |
| Recorded pre-runtime verification | [Preflight](../../../evidence/retrieval-live/retrieval-grounded-20261026-02/execution/preflight.json): 189 sources, 212 configuration/corpus/TLS inputs and 15 runtime assets, including the full model and projector hashes |
| Actual command and runtime lifecycle | [Operator execution](../../../evidence/retrieval-live/retrieval-grounded-20261026-02/execution/operator-execution.json): one unchanged runner invocation, exit 0, no generation warm-up |
| Reservations and backend claims | [Final ledger](../../../evidence/retrieval-live/retrieval-grounded-20261026-02/execution/ledger.json), individual claims below |
| Owner captures, parsed admissions, prompts and peer traffic | [Unmodified raw session reports](../../../evidence/retrieval-live/retrieval-grounded-20261026-02/execution-report.json) |
| Actual backend HTTP observations | [Runtime request log](../../../evidence/retrieval-live/retrieval-grounded-20261026-02/runtime-requests.log): four successful `/api/chat` POSTs and eight non-generating version/tags GETs |
| Per-slot reconciliation and reported usage | [Reconciliation](../../../evidence/retrieval-live/retrieval-grounded-20261026-02/execution/reconciliation.json) |
| Recorded cleanup | [Cleanup observations](../../../evidence/retrieval-live/retrieval-grounded-20261026-02/execution/cleanup.json): all tracked task processes absent, no remaining campaign processes or listeners on its six frozen ports |
| Published packet integrity | [Checksums](../../../evidence/retrieval-live/retrieval-grounded-20261026-02/checksums.json), unchanged from the existing publication |

The nonrenewed approval window was **2026-10-26 13:07:54.665–14:07:54.665 UTC**.
The isolated runtime operated from **13:10:27.236 to 13:16:07.218 UTC** and was
stopped. Cleanup is a recorded campaign observation, not a new runtime probe.

## Four spent slots

| Slot and durable claim | Occurrence ID | Reservations | Backend entries | Captures | Admission | Reported input/output tokens |
|---|---|---:|---:|---:|---|---:|
| [local-query](../../../evidence/retrieval-live/retrieval-grounded-20261026-02/execution/claims/231c314b-5c67-5d1f-8e5e-674ae43105b4.json) | `231c314b-5c67-5d1f-8e5e-674ae43105b4` | 1 | 1 | 1 | query authorized | 257 / 8 |
| [local-reply](../../../evidence/retrieval-live/retrieval-grounded-20261026-02/execution/claims/4b3ed1d5-0765-5d8b-a339-e973536c164d.json) | `4b3ed1d5-0765-5d8b-a339-e973536c164d` | 1 | 1 | 1 | send authorized | 637 / 8 |
| [network-query](../../../evidence/retrieval-live/retrieval-grounded-20261026-02/execution/claims/b0f11fa9-6f9f-5d4d-9200-d31835ae01fb.json) | `b0f11fa9-6f9f-5d4d-9200-d31835ae01fb` | 1 | 1 | 1 | query authorized | 257 / 8 |
| [network-reply](../../../evidence/retrieval-live/retrieval-grounded-20261026-02/execution/claims/9d01b433-e9a8-51b6-b4fb-42f3b803473d.json) | `9d01b433-e9a8-51b6-b4fb-42f3b803473d` | 1 | 1 | 1 | send authorized | 637 / 8 |

All four captures preceded their original 300-second deadlines. Owner and caller
accepted intents and captured response bytes agree. Each model-call occurrence
spent four application RPC attempts out of eight; these are distinct from its
single generation reservation and backend invocation. There were no replacement
sessions, hidden generations, repairs, fallback, regeneration or automatic resend.
The raw request log corroborates four successful chat requests in slot order; it
does not expose provider request IDs, which remain unknown.

## Session outcomes and scope

| Session | Model placement | Response capture | Command admission | Retrieval | Actual query in next prompt | Factual correctness | Independent peer |
|---|---|---|---|---|---|---|---|
| `e4a391e8-14a2-4aa9-b4c6-0d5640d2e233` | Local | 2/2 | query + send | PASS | PASS | PASS | Exact reply observed once |
| `655f80ce-7d5e-453f-94fc-bdb1fb26f15f` | Authenticated same-host HTTPS | 2/2 | query + send | PASS | PASS | PASS | Exact reply observed once |

Both actual parsed/admitted send bodies were **`Synthetic answer: amber cabinet.`**
Output permission and factual correctness were evaluated separately. Each bridge
recorded one reserved send with `socket-write-returned`; peer observation independently
confirmed delivery. Both native loops exited 0 with `BOUNDED_STOP`.

The first measured prompt lacked the target fact and setup history. Its four
equally eligible reply strings did not identify the correct one. The actual native
query retrieved authoritative generated payloads, and its captured projection
appeared in the second model prompt under the existing disclosure receipts. Both
queries retained view `d7de349e0243de6d8443a8c0edd79beaf83b7f3ba219c9667a1eb247cfc355f2`.
Model placement changed; the mailbox stayed HTTPS, and encoding, retrieval and
cognitive state stayed local.

Native `remember` created the frozen synthetic corpus during the earlier setup
with explicit model/channel/clock fixtures. The measured live campaign exercised
model-directed **query and send**, with real E5, Chroma, DeTTa, IRC and HTTPS. It
does not demonstrate a real model choosing `remember`, live evidence revision or
promotion, private-memory export, full default Omega, multi-host placement, or a
combined model/memory/chain workflow. No kill or captured-result recovery was
induced during these two live sessions; preparation recovery results stay separate.

## Historical labels, usage and library limits

The raw `evaluation.model_usefulness=NOT_RUN` field is **preserved**. In the exact
executed implementation, the shared [preparation evaluator](https://github.com/machieke/fusion-module-interfaces/blob/66366cb4ed262ab8a87b96540d5c17fc8f0977ea/integration/neoclaw/retrieval_preparation.py#L220)
always returns that literal, including when called by the live runner. It is not
a runtime generation counter. `REAL_MODEL` session boundaries, durable response
captures and four real HTTP requests independently establish this campaign's
execution. The separately computed permission, retrieval, correctness and peer
fields establish the two bounded task passes. Neither the legacy label nor these
two successes establishes general model usefulness. No raw field is rewritten.

Reported usage totals **1,788 input tokens and 32 output tokens**. Reasoning-token
usage and provider request IDs are null for every capture and remain **unknown**,
not zero. Sequential shared-runtime cache state also prevents interpreting the
four observed durations as a controlled placement benchmark.

All 15 explicitly frozen runtime assets passed the recorded checks, including
full model/projector blobs. The [loaded-runtime observation](../../../evidence/retrieval-live/retrieval-grounded-20261026-02/execution/loaded-runtime-observation.json)
also records `libgfortran.so.5`, `libmlx.so`, `libmlxc.so` and `libopenblas.so.0`.
These four transitive host libraries were outside `runtime_required_files` and
had no comparison hash in the referenced historical inventory. Their
[supplementary hashes and qualifications](../../../evidence/retrieval-live/retrieval-grounded-20261026-02/execution/supplementary-runtime-libraries.json)
remain observations, not retroactive frozen pins. Their `match_frozen=false`
does not identify drift against a declared hash; no such binding existed.

## Coverage without merging evidence classes

| Evidence class | Recorded result | What this publication changes |
|---|---|---|
| [Historical preparation](retrieval-runner-preparation-report.md), [qualification accounting](../../../evidence/retrieval-runner/preparation-summary.json) | 72 distinct test methods; eight qualified native method executions / 16 scenarios; 23 recorded-response reservations, 22 fixture captures and eight peer-observed workflows. Zero live generations during preparation. | Adds a current pointer; preserves all original labels, counts and failure identities. |
| This completed real-model memory workflow | Two declared sessions; four reservations/calls/captures; two correct peer-observed query/reply workflows. | Adds workflow evidence to the existing native boundaries and X01/X02 profiles; adds no module, adoption or command. |
| [Separate M4 chain integration](../../module-interfaces/m4-evidence.md), [manifest](../../../evidence/m4/manifest.json), [same-artifact trace](../../../evidence/m4/final/same-artifact.json), [readback](../../../evidence/m4/final/readback.json) | Previously passed 10 gates on `55ed5402391ab6ed14f8ab20e1eea4c85d8be955`, including real isolated F1R3node effect/finality, recovery and readback. | No chain run, new chain claim or combined workflow; historical evidence is unchanged. |

The denominator remains **15 bounded families**, with **105 historical mapping
rows, eight bounded adoption entries, nine native user commands and zero newly
promoted whole families**. X01 ModelInference and X02 Embedding remain existing
extensions. The historical S07 twelve attempts/ten captures and its failures are
not relabelled or merged into this four-slot campaign. Historical `NOT_RUN` fields
in the closeout and preparation sections of [coverage.json](coverage.json) retain
their time scope; `current_workflow_evidence` supplies the later result.

## Publication scope and review entry point

This page is the review entry point. The exact six-file change list is
[changed-files.txt](../../../evidence/retrieval-live/publication-review/changed-files.txt):

| File | Change |
|---|---|
| `README.md` | Link current workflow evidence and distinguish separate chain history. |
| `docs/omega-adoption/mettaclaw-neoclaw/README.md` | Replace stale current wording with the three evidence classes; retain historical narrative. |
| `docs/omega-adoption/mettaclaw-neoclaw/coverage.json` | Add current workflow evidence; preserve every existing section and count. |
| `docs/omega-adoption/mettaclaw-neoclaw/retrieval-live-publication.md` | This review trail, limitations, outcomes and scope. |
| `evidence/retrieval-live/publication-review/changed-files.txt` | Exact publication-only allowlist. |
| `evidence/retrieval-live/publication-review/review.json` | Static integrity, accounting, privacy-scope, link and unchanged-count checks. |

Only approved synthetic result data and existing sanitized, versioned diagnostic
evidence are referenced. No credential, key, private journal, machine-local secret,
TLS configuration content or new runtime dump is copied. Manifest references to
local paths remain historical references; this review does not open them. Static
secret-pattern checks supplement that explicit file scope; they are not a claim
that pattern matching can prove the absence of every possible secret.

Runtime code, contracts, profiles, prompts and permissions are unchanged. No
commit or push is performed in this preparation; the previously published packet
at `dba62caf` remains intact. The current request supplies no new instruction to
commit or push this additional review.

```text
PUBLICATION_REVIEW=READY
CAMPAIGN_STATE=COMPLETED_ALL_FOUR_SLOTS_SPENT
LIVE_MEMORY_WORKFLOW=PASS_2_OF_2
ADDITIONAL_LIVE_GENERATIONS=0
REMAINING_GENERATION_AUTHORITY=0
CHAIN_RERUN=NOT_RUN
```
