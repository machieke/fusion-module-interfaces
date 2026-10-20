# Codex handoff — retrieval-grounded Omega workload: implementation and generation-disabled qualification

## 1. Objective and authority boundary

Continue `machieke/fusion-module-interfaces` from S07 publication
`4981788b4d8069a2b2264e65197f9886b74f1f5f`, retaining the completed, currently
uncommitted S07 closeout or its explicitly identified later publication.
Read applicable AGENTS.md, the closeout packet, and
`docs/omega-adoption/mettaclaw-neoclaw/s07-next-workload.md` before editing.

**Proposed next assignment:** implement the existing retrieval-grounded workload
and qualify its integration using explicitly recorded or authored model-response
fixtures. Reuse the adopted memory, embedding, messaging and model interfaces.
This is not another inventory pass, a new module family, or a replacement for the
existing workload definition. It is not the historical S08 Embedding candidate.

The intended future workflow is:

    real IRC question -> model-proposed native query -> actual memory retrieval
                      -> captured query result in next model input
                      -> model-proposed native send -> peer observation

**Additional live text-generation authorization for THIS task: ZERO.**
The twelve S07 reservations are exhausted. Do not restart Ollama, load a
generative model, contact a real text-generation endpoint, run generation-bearing
readiness/warm-up calls, or reuse/reset an old campaign or its journals. A model
fixture response is not an additional real generation or a real-model PASS.

This proposed implementation assignment differs from the completed review-only
closeout: it permits bounded native MeTTaClaw/PeTTa/SWI execution, actual isolated
IRC, local authenticated HTTPS tests, and existing real E5/Chroma/DeTTa providers
on fresh synthetic data. E5 encoding is permitted here as an existing retrieval
dependency, separately recorded from forbidden generative-model evaluation.
No public channel, external web search, hosted model or private data is needed.

Do not infer that this document itself grants current access, publication rights,
or a future live-generation allowance. It is a proposed task for the user to
assign. Even when assigned, its generative-model allowance remains zero.

**Stop at `READY_FOR_LIVE_AUTHORIZATION`** only when all preparation gates pass.
Report real-model usefulness and live workflow gates as NOT_RUN. Do not execute
the proposed four-call campaign. Missing prerequisite: report the exact partial
result rather than replacing a real retrieval/channel dependency with a fixture.

## 2. Source and evidence baseline

The reviewer read the public S07 commit, current closeout/report/manifest and
proposed workload, plus selected pinned model transport, disclosure, application
and startup source. The reviewer did not rerun the suites or independently
recompute the full hash audit. Moving-path closeout content is not proof that
its files belong to the S07 publication commit.

The closeout records:

- 270 delivery hashes matched to publication; 1,509 versioned manifest entries
  resolved, without rewriting historical working-tree runs as clean-commit runs.
- Twelve spent generation reservations, ten captures, eight authorized captured
  batches, two rejected captured batches, three complete workflows and two real
  post-capture recoveries. No remaining generation authorization.
- 149 distinct historical test methods. The separate 20-method recorded-response
  recheck overlaps those methods; it does not raise the distinct count to 169.
- Six review gates, not six new runtime integration or usefulness gates.
- A 17-file uncommitted closeout delta. Preserve it and its exact source identities.

Before implementation, reconcile the actual checkout with
`evidence/s07-closeout/review-state.json`. Record starting HEAD, worktree status,
closeout delivery hashes and any subsequent changes. Preserve historical evidence
and unrelated files. Do not reset the working tree, stage everything, create a
release or push without separate user/workspace authorization. Keep this new
implementation delta distinguishable from the closeout delta.

Do not repeat the entire historical audit merely to change its label. Run the
relevant safe checks and an impact-selected regression set against newly tested
bytes. Record genuine failures, rechecks, skipped/unrun dependencies and fixture
classes independently.

## 3. Existing specification and implementation points

Treat `s07-next-workload.md` as the source of the workload, preserving its
terminology, two-input sequencing, exact command scope and separate readiness,
authorization and correctness criteria. Changes below operationalize the pending
application/disclosure decisions; record them as proposed engineering choices,
not past meeting decisions or historical S07 behavior.

| Path | Purpose / reviewed finding to verify |
|---|---|
| `docs/omega-adoption/mettaclaw-neoclaw/s07-closeout.md` | Current evidence matrix, source relationships and unresolved facts. |
| `s07-next-workload.md` | Synthetic retrieval-grounded reply, exact query, finite egress set, proposed but unauthorized live campaign. |
| `evidence/s07-closeout/{review-state,checks,offline-checks,test-map}.json` | Safe audit, new checks versus historical runs, exact closeout delta. |
| `fusion/model_transport.py:configuration` | Current configuration admits only `metta` and `send`; shared placement/response checking. |
| `integration/neoclaw/model_startup.py` | Deduction-specific prompt, skill list and source-checked native overlay. |
| `fusion/neoclaw_model_disclosure.py:disclose` | Closed numeric `COMMAND_RETURN` grammar and empty-history restrictions, not general query-result consent. |
| `fusion/neoclaw_model.py` | Prompt binding, retained context view, model result capture, parser and whole-batch admission. |
| `fusion/neoclaw_application.py` and existing memory/embedding clients | Native query dispatch, durable command occurrences, captured vectors/results and retained views. |
| `integration/neoclaw/model_composition.py` | Existing exact command/body policy and independently selected model/mailbox placement. |
| `integration/neoclaw/model_corpus.py` | Historical setup generator; it is not evidence of native remember-based setup for this workload. |
| Existing S03.2 append, S04/S05 presentation, S06 channel code | Reuse actual native append, owner-bound reads, context preparation and durable communication. |
| `fusion/model_service.py`, existing recorded-model test providers | Independent acceptance/reservation/capture; reuse fixture injection without enabling production fallback. |

Keep actual dependency/model/runtime pins. A generic wrapper refactor, new model,
embedding implementation, corpus database, scheduler or command language is not
required. Preserve historical application `/9`, numerical model profiles, source
locks, recorded prompt policies and their rejection behavior.

## 4. The bounded preparation workload

### Setup is real; model responses are fixtures in this task

Create a small new synthetic corpus in a separate setup session by actually
invoking the adopted native `remember` path. Include a target record and at least
two distractors with different project names and locations. Use the specified
calibration-card fact shape. This task may create preparation-test fixtures;
it does not select or spend a future live campaign.

Require separate evidence for storage/enrollment acceptance, named Search
publication, metadata/view readiness and native remember success. Use real E5,
Chroma and DeTTa. Do not insert records directly into Chroma or enroll the target
through a test shortcut and call that native setup.

Start a new measured/rehearsal application session from the ready immutable view.
It must not inherit the setup prompt, remember commands, replies, flat history,
model cache context, or answer-bearing global promoted context. Explicitly
inspect the accepted first prompt. The target location must be absent from it,
the peer question, skills and visible configuration. Keep global promoted
context empty for this first workload; nonempty query feedback is the new input.

The independent real IRC peer asks the project question. A clearly labelled
model-response fixture proposes the one approved native `query`. The actual
query runs through Embedding -> Search -> AtomStorage hydration -> unchanged
local enrichment/rendering. After successful capture, the peer supplies the
second instruction to answer using the preceding tool result. It contains no
answer. The next model input must contain the actual captured native result.
A second fixture proposes a native `send`, and the real peer records its receipt.

Model fixtures may provide commands but must not implement query, return its
payloads, search an evaluator file, perform embedding, or construct the feedback
inserted into the next context. Fixed fixture outputs are test inputs, not
measurements of generative-model competence. Preserve the distinction in every
report, trace and gate.

## 5. Closed composition, not blanket command expansion

Implement a distinct, explicitly selected application/disclosure configuration
for this workflow. Inspect the actual catalogue before assigning a profile name
or version. Reuse `model.inference`, the pinned completion options and existing
local/HTTPS transport; do not silently repurpose old journals or profiles.

The measured grammar is exactly one command per call:

- first stage: the single approved `query <query text>`;
- second stage: `send <body>` from the separately approved finite set.

Enforce stage, entire parsed batch, exact argument policy, scope, principal and
occurrence at command admission, not merely in the prompt. Reject two commands,
a stage-inappropriate send/query, mixed batches and any shell, arbitrary MeTTa,
external search, remember, assessment or promotion command before effects.
Do not add aliases or repair model output to obtain successful-looking commands.
Keep the native parser and rendering transformations.

Allow native remember in the separate setup composition only. The measured
session has no memory-write authority. Query authorization is a read capability;
it does not permit modifying cognitive state or selecting arbitrary providers.

One policy discriminator with selected validators is preferable to a growing
permissive union or copied state machine. Reuse the existing application and
provider owners. Where old validators must remain closed, use a small explicit
new adapter/profile rather than removing their checks.

## 6. Disclosure: prove identity and permission separately

The current numeric feedback regex is not a query-result consent system.
Do not replace it with a wildcard, allow arbitrary `COMMAND_RETURN`, or accept
`synthetic=true`/a matching hash as permission.

Before releasing the next prompt, the trusted application boundary must:

1. Reauthorize the actual caller and selected model recipient.
2. Recover the exact committed query occurrence and retained memory view through
   declared owner/client reads, not foreign database inspection.
3. Verify that the native feedback equals the actual captured projection, including
   generated IDs, timestamps/labels, STV/prior presentation, record order and text.
4. Verify that all disclosed record components are covered by the operator's
   bounded synthetic-data policy for that recipient and this workflow.
5. Bind the approved feedback and view to the model occurrence before reservation.

Integrity is not consent; consent is not proof that the correct record was read.
Preserve both checks. The provider may validate a narrow recipient-bound disclosure
receipt issued by trusted composition, without access to private stores. A receipt
must not be mintable by model-supplied arguments. No new signature infrastructure
is required for this trusted-local test.

The query output may include distractors. Approve all potentially disclosed
synthetic result fields, not only the expected target text. Do not strip inconvenient
fields or narrow retrieval until an old validator accepts the result. Refuse the
whole unauthorized prompt rather than silently redact it while claiming parity.

Input containing section delimiters, quote markers or fake tool syntax must remain
data or be explicitly refused under a declared restriction. Preserve raw versus
native-transformed bytes and test that transformations occur exactly once.

Prevent first-prompt answer leakage through setup history, promoted context,
policy errors, command help and read-only files. Model providers must not read
the corpus/index, evaluator answer file or caller journals. The caller may use
its legitimate result capture; an audit store must not serve as a retrieval fallback.

## 7. Output authority is not the correctness oracle

Freeze a bounded, exact set of harmless synthetic answer bodies covering all
candidate locations, plus one insufficient-information response. Keep this set
in trusted output policy, not the model-visible prompt. A general format such as
`Synthetic answer: LOCATION.` is sufficient; do not supply the correct body to
the model as the requested completion.

All candidate bodies have equal publication eligibility. Do not admit only the
correct location or expose candidate-by-candidate authorization feedback that
reveals it. Keep the evaluator's target mapping inaccessible to model/providers.

Exercise these distinct results with recorded model responses:

| Proposal / state | Authority | Task outcome |
|---|---|---|
| Correct harmless candidate, real matching retrieval | May be admitted and sent | Positive recorded integration case; live usefulness still NOT_RUN |
| Wrong but equally permitted candidate | May be admitted and sent | Grounding/correctness FAIL, not an authorization failure |
| Permitted insufficient-information reply with decisive target present | May be admitted and sent | Task FAIL |
| Insufficient-information reply with valid but inconclusive retrieval | May be admitted and sent | Appropriate negative-case result |
| Unapproved body, unsupported command or private canary | Rejected before send | Negative contract test PASS; not a completed positive task |
| Missing/unready Search generation or failed payload hydration | No answer-stage authorization | Retrieval failure; do not masquerade as a valid empty answer |
| Unknown external send after reservation | No automatic resend | Unknown delivery; not peer success |

Bound the body-set size without weakening historical limits globally. A new explicit
workflow limit may be needed because the S07 numerical command list is small.
Do not let the number of expected answers dictate a general command-execution API.

## 8. Retained state, budgets and recovery

Keep the source coverage, Search generation, embedding identity, local metadata,
belief/priority view and sampled times fixed per accepted query/context.
The next prompt uses the actual saved feedback. A new context may have a new
identity; a resumed context must not silently adopt a newer view.

Preserve the existing five-minute selected input/model deadline, thirty-second
tool/context bounds, eight model RPC reservations and one backend reservation
where those are the admitted profiles. Corpus/model readiness is separate from
accepted work. Never extend an existing deadline, refund an uncertain reservation,
replace a failed occurrence or rebuild an unavailable selected generation silently.
If combined work cannot meet a bound, record it as a readiness failure and propose
an explicit fresh-profile decision instead of changing an old guarantee.

Use actual process kills in generation-disabled integration at:

- accepted query before capture;
- captured vector/candidates/result before next-context delivery;
- full next prompt and its context view durably bound;
- recorded provider response captured before application receipt;
- application model capture before parsing/admission;
- approved outbound intent or socket reservation before outcome observation.

After capture, recover exact saved artifacts without new encoding/search/model
fixture evaluation when that stage's contract promises reuse. Before capture,
work may repeat only within its original declared budgets. Count fixture model
calls separately from real encoding and from zero live generative calls.
Current authorization, revocation and credential/principal binding apply to all
captures, retained observations, prompt release and command effects.

Retain S06's one-attempt ambiguous-send behavior. A functioning independent peer
must observe the healthy send, but a socket return is not recipient confirmation.
Pre-durable-capture IRC loss remains outside the guarantee.

## 9. Tests that cannot pass by supplying the answer

Required preparation evidence:

- Original and adapted query parity over the setup corpus, with real native query,
  E5, Chroma, DeTTa, owner-bound hydration and unchanged enrichment. Confirm the
  target appears in the chosen native result before scoring a response.
- Fresh measured history and empty promoted context; actual first prompt contains
  no target location. A hidden answer file cannot be opened by the model provider.
- The second prompt contains the real captured result and no expected-answer overlay.
- Two controlled corpus variants with a changed target location produce correspondingly
  changed native feedback. This tests dataflow; recorded responses do NOT establish
  that a generative model noticed the difference.
- A target-absent corpus can return a valid empty/inconclusive result; a stale or
  unavailable projection raises its actual error instead. Do not conflate them.
- Wrong-authorized answer versus unauthorized-output cases described above.
- Forged/swapped receipts, different occurrence/view/scope/model/recipient, altered
  timestamps/labels/STVs/content/order, malformed native results, timeouts, revocation,
  credential substitution, bad certificates and no-fallback behavior.
- Actual native IRC workflow with recorded model backend under local and authenticated
  same-host HTTPS ModelInference placement. Hold mailbox/retrieval/encoder placement
  fixed for that comparison. Run real HTTPS retrieval/encoding where the existing
  selected composition permits it, retaining E5-free caller isolation.

If S04/S05 private state cannot safely coexist with a proposed remote memory
placement, use the existing local private owners and an explicitly scoped synthetic
retrieval composition. Do not reinterpret historical private profiles to make the
comparison pass. Record any unsupported combination rather than inventing a guarantee.

Reuse source pins and declared test hosts. Instrument and deny access to actual
text-generation endpoints, service managers and model binaries. Prove the deny
mechanism itself works before the suite. The recorded provider must be selected
explicitly; inability to use a real provider must never trigger fixture fallback.
Inspect test entrypoints so regression discovery does not inadvertently launch a
real model or reuse an old live run.

## 10. Closeout limitations: preserve the past, improve future traces

Do not reconstruct the missing historical rejected API payload. Preserve its exact
cause as unresolved, with any cache-counter attribution labelled inference.
Keep unavailable usage unknown, not zero, and do not estimate a complete historical
bill from captured requests only. Reduced public context exports do not become
complete merely because a runtime assertion once passed.

For this new generated workload, capture bounded authorized evidence sufficient
for independent checks: source/version identity; source-head/generation and complete
selected view; query occurrence; verified refs/payload digests; native projection;
raw/transformed model prompt and approved recipient binding; response and parse;
admission; outbound acceptance/socket outcome; and independent peer observation.
Do not flatten these into one success field.

Keep full synthetic evaluator/private-side traces access-controlled. Publish only
explicitly shareable fields. Where a field cannot be exported, describe the check
that cannot be independently reproduced. An evidence exporter should preserve
context-view bindings rather than dropping them unmentioned.

Fixtures can exercise bounded rejected-response diagnostics, including unknown
fields, without fabricating the missing S07 payload or enabling raw private logging.
A future real campaign must define diagnostic retention/consent before execution.

## 11. Future live plan — prepared, not authorized

Retain the existing proposal: two predeclared sessions, fixed HTTPS mailbox and
retrieval placement, local versus HTTPS ModelInference, at most two generations
per session. The proposed ceiling is four calls and 6,000 output tokens per call
under the selected existing profile. Those are ceilings, not expected usage or
new permission. The effective live allowance remains ZERO.

Prepare a disabled run-plan template identifying exact source/build/model IDs,
recipients, fixture policy, placement, command/output policy, bounds, attempted-call
ledger and stop conditions. No generic `approved=true` field supplied by model text
or copied historical authorization can activate it. A new user authorization must
be bound before any future live call. Do not issue that authorization here.

A later live campaign stops a session on its first rejection, error, timeout or
ambiguous effect. It may not tune prompts mid-campaign, repair responses, regenerate
until green, or silently add replacement sessions. No live generation in this task
is permitted to close a retrospective evidence gap.

## 12. Preparation gates and deliverables

| Gate | Required PASS evidence |
|---|---|
| BASELINE | S07 publication and completed closeout accounted for; exact new test source and impact map |
| CONTRACT_SELECTION | Explicit closed query/send application and disclosure selections; historical behavior preserved |
| ZERO_LIVE | No real text-model startup/access/generation; tested deny guard; fixture backend explicitly classified |
| SETUP_RETRIEVAL | Real native remember setup and query, actual E5/Chroma/DeTTa, honest freshness and verified hydration |
| CONTEXT_BINDING | Actual saved query projection reaches the next native prompt; retained view/current authority verified |
| NO_ANSWER_ORACLE | No first-prompt/setup leak; output eligibility separated from target correctness; wrong allowed reply scored wrong |
| CHANNEL_PLACEMENT | Actual IRC and native loop with local/HTTPS recorded-model provider, fixed other placements and isolated stores |
| RECOVERY | Real process kills of test runtimes preserve captured stages, identities, original deadlines and spent budgets |
| COMPATIBILITY | Selected S01–S07 and owner/transport regressions, exact impact map, no profile or private-placement weakening |
| LIVE_PLAN_DISABLED | Future campaign template complete but no active authorization; all real-model usefulness/combined workflow gates NOT_RUN |

Do not rename these preparation passes as the live workload PASS.
Final state is `READY_FOR_LIVE_AUTHORIZATION` only when applicable preparation
requirements pass, otherwise PARTIAL with precise blockers/failures.

Update the existing workload doc, decisions, test entrypoint, adoption coverage
and one compact preparation evidence directory/report. Do not create another
architecture hierarchy or regenerate all module presentations. Keep the historical
fifteen-family inventory and X01/X02 counts intact; composing existing interfaces
is not a newly implemented family or newly adopted user command.

Report exact source identity, changed files, new methods versus regression/repeated
methods, real provider and fixture classes, process-kill stages, resource/latency
observations, corrected failures, and unrun gates. No reliability percentage from
a recorded response or a two-session future demonstration.

End with:

    PREPARATION_STATUS=<READY_FOR_LIVE_AUTHORIZATION or PARTIAL>
    ADDITIONAL_LIVE_GENERATIONS=0
    LIVE_MEMORY_WORKFLOW=NOT_RUN

Then stop. No release/push without separate authorization; no migration, new
embedding or cognition, multi-host, public deployment, chain integration, generic
output-publication authority or whole-default-Omega claim.

## Review locations

Baseline executable findings are pinned to:

    https://github.com/machieke/fusion-module-interfaces/tree/4981788b4d8069a2b2264e65197f9886b74f1f5f

Closeout inputs were reviewed via the public moving paths below and describe an
uncommitted delta; reconcile their exact hashes against the local review manifest:

    docs/omega-adoption/mettaclaw-neoclaw/s07-closeout.md
    docs/omega-adoption/mettaclaw-neoclaw/s07-next-workload.md
    evidence/s07-closeout/review-state.json
    evidence/s07-closeout/offline-checks.json

The October 15 Kevin/Kabir transcript supports functional service boundaries and
local-to-remote handoff (00:13:36–00:18:47; 01:04:49–01:07:39). The AGI Benchmarks
transcript distinguishes integration evidence from mocks and calls for explicit
acceptance criteria (00:02:28; 00:05:40; 00:17:02). Those discussions do not select
this particular fixture, disclosure policy or live-generation budget.
