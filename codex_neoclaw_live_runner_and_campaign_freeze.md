# Codex instructions — implement the retrieval live runner and freeze its campaign

## 1. Assignment and stopping point

Work in `machieke/fusion-module-interfaces` from
`9816873d5bb605c9c03be5f65baef7410c8cce0f`, or record the actual descendant and
relevant changes. Read applicable `AGENTS.md` and the existing retrieval workload,
preparation decisions, disabled plan and authorization review.

**Implement the missing runner, qualify it with explicit model-response fixtures,
and deliver a concrete campaign manifest ready for user approval.** This is an
implementation task, not another static authorization review.

When assigned by the user, this brief permits that implementation, fresh synthetic
memory setup and bounded generation-disabled integration tests. It does **not**
permit real text generation, generative-runtime startup/contact, or activation of
the resulting campaign.

**Absence of live authorization is expected and is not a blocker to building and
testing the runner.** This instruction replaces the earlier sequencing that put
runner implementation behind approval of a not-yet-frozen campaign. All live-call
restrictions remain in force.

Stop with a tested runner and an approval-ready manifest. Do not add another
module, invent another architecture, execute the proposed campaign, or spend time
repeating the completed historical audit.

### Permission boundaries for this assignment

| Permitted | Not permitted |
|---|---|
| Edit the narrowly required runner, adapters, tests and documentation | Start, load, probe or contact a real text-generation runtime |
| Explicit recorded/authored completion fixtures | Any real generative inference, including warm-up or readiness generation |
| Actual native MeTTaClaw, E5 encoding, Chroma and DeTTa on fresh generated data | Hosted-model calls, model changes or reuse of the exhausted S07 allowance |
| Isolated local IRC and certificate-checked same-host HTTPS | Public channels, public endpoints, multi-host or chain work |
| Offline inspection and hashing of accessible runtime/model files | Assuming runtime availability from historical evidence |
| Planned session/slot identities and a disabled campaign manifest | Real generation reservations, captures or self-issued user approval |

Keep `ADDITIONAL_LIVE_GENERATIONS=0` throughout. E5 encoding and fixture responses
must be counted separately from real generative calls.

## 2. Baseline and review basis

The supplied status and pinned authorization review report that the preceding
commit changed documentation/review evidence only. They record successful
reconciliation of 102 delivery hashes and 214 source files with preparation
publication `01d0b023e6990670eae65e14ed5910e64e72f929`.

The preparation already exercised the combined memory/channel workflow using
fixture model responses. The pending items are an executable live runner, concrete
campaign bindings and later user authorization. This brief follows a source review;
its author did not run the repository suites or independently reproduce that audit.

Check the starting worktree and relevant manifest relationship once. Preserve
unrelated edits, historical failures, original test identities and unresolved usage
or diagnostic facts. Do not reinterpret earlier working-tree tests as tests of a
later clean commit. Select regressions by the actual change impact.

### Reuse these sources

| Path | Purpose |
|---|---|
| `docs/omega-adoption/mettaclaw-neoclaw/s07-next-workload.md` | Existing retrieval task, command scope, evaluation and disclosure rules |
| `retrieval-preparation.md` and `retrieval-preparation-decisions.md` in that directory | Qualified composition and existing limits |
| `evidence/retrieval-live/authorization-review.json` | Current missing-runner state and focused source findings |
| `evidence/retrieval-preparation/live-plan.disabled.json` | Historical proposal; retain it unchanged |
| `integration/neoclaw/retrieval_preparation.py` and its tests | Real setup and fixture-only workflow; extract reuse without making this entrypoint live |
| `integration/neoclaw/preparation_guard.py` | Generation-denial facilities and verification |
| `fusion/model_service.py`, `model_transport.py`, `neoclaw_model.py` | Model acceptance/reservation/capture and native application handoff |
| `fusion/neoclaw_retrieval_disclosure.py` | Captured query, retained view, recipient and consent checks |
| `fusion/adapters/ollama_completion.py` | Existing source-checked real backend; inspect without contacting it |
| `integration/neoclaw/model_run.py` | Historical numerical runner; not the new campaign or its budget authority |

Reconcile these paths against the checkout. Reuse existing interfaces and profiles,
including the selected retrieval application/disclosure and model profile. No new
parser, memory database, model server or general experiment framework is requested.

## 3. Implement one runner with explicit execution modes

Provide a small entrypoint with clearly separated preparation, recorded-response
qualification, read-only inspection and future authorized execution. Choose names
consistent with the repository and document the actual executable commands.

A future execution request must verify campaign identity, source/configuration
integrity and separate operator-supplied authorization **before** constructing or
contacting a real backend, invoking readiness, starting a generative process,
loading a model, or reserving a generation. Imports and default constructors must
not create an accidental contact path.

A missing, stale or mismatched approval must return an explicit refusal with zero
backend contact. An `enabled` flag, manifest hash, successful test or model-supplied
string is not user authorization. Use the existing trusted-local policy model;
no production identity platform or new signature infrastructure is requested.

Test positive authorization logic only with a clearly test-only authority and
recorded backend in isolated test campaigns. These approvals and captures must be
unusable by the production entrypoint or the frozen campaign. Never automatically
fall back to a fixture when a real provider fails.

Preserve the old preparation command as generation-disabled. Do not remove its
guard to make the new runner work.

### Reuse the workflow, not its fixture assumptions

The preparation harness knows the authored commands and preferred reply. The new
runner must instead obtain the actual parsed/admitted output through the application
boundary, observe that exact body from the correct peer route/sender, and score it.
It must not wait for `BODIES[0]`, read an expected answer to choose a reply, repair
commands, or fill missing results from an audit database.

Keep runner orchestration distinct from owners. ModelInference owns call outcomes;
Messaging owns deliveries; the application owns accepted inputs and command/results;
Search and AtomStorage own retrieval and content. No cross-owner SQL or replacement
state machine. Read-only evidence inspection must not supply runtime answers.

### Bounded observation

Set observer limits suitable for the frozen five-minute model bound and separate
tool/channel phases. Do not copy the fixture harness's short waits blindly.

Track runtime preparation, accepted generation, query execution, next-input binding,
outbound acceptance and peer observation separately. An observer expiring does not
extend a deadline, authorize resubmission or prove provider rejection. Its outcome
must remain distinguishable from an actual backend or task failure.

Send the second peer instruction only after the first query has really completed;
do not let that input expire while waiting in a channel during generation.

## 4. Exercise the real retrieval path with fixture completions

Build a fresh synthetic target and distractor corpus using the actual native
`remember` path. Retain evidence for storage acceptance, source enrollment, Search
publication, metadata readiness and native success. Reuse real E5, Chroma and DeTTa.
Do not prepopulate the target through direct index insertion or an expected-answer
list.

Use separate setup and measured sessions. The measured initial prompt must not
contain the target answer via setup history, remembered commands, promoted context,
evaluator files, policy errors or skill instructions. Keep its initial promoted
context empty under the existing profile. Model providers cannot read the corpus,
evaluator or caller journals.

Recorded responses may propose the approved `query` and an approved `send`. They
must not implement retrieval, supply its results or construct feedback. The second
model input must contain the exact actual native query capture with its retained
view and recipient consent. Validate the entire disclosure, including generated
labels and prior/STV presentation, through existing interfaces.

Keep all harmless candidate reply bodies equally eligible for sending. Store the
correctness mapping separately, inaccessible to providers and prompt construction.
A wrong but permitted answer must be sent in the corresponding negative test and
score incorrect. Authorization must not reveal the correct answer.

Exercise both recorded-model placements: local and authenticated same-host HTTPS.
Keep mailbox HTTPS and encoder, retrieval and cognition local in both, matching the
existing proposal. Do not imply that this comparison tests private remote cognition.

Preparation sessions and fixture-model journals must be separate from the eventual
campaign's two measured sessions. Never reuse rehearsal captures as live responses.
Retain the frozen corpus/ready view after cleanup; rebuilding it with new identities
later requires a new freeze, not an invisible substitution.

## 5. Freeze one concrete, disabled campaign

Create an immutable campaign manifest plus a separate mutable execution ledger and
separate future authorization record. Reuse existing schemas where possible. Keep
the historical disabled proposal intact rather than overwriting it as an approval.

The new manifest must bind:

- A campaign ID, baseline commit, tested runner/source identities and dependency
  locks. Record an unpublished worktree with exact file hashes when necessary.
- The selected runtime/model/profile and required binary/model identities from
  the existing locks. Distinguish offline verified bytes, declared required hashes
  and runtime availability that has not been checked. Do not launch a model to
  improve this status, or silently select a newer model.
- Actual new memory identities, payload/vector/enrollment references, source head,
  Search generation, complete retained metadata view and setup evidence.
- The exact query, two peer inputs, prompt scaffold, native transformations,
  allowed command stages, equally eligible reply bodies and independent evaluator.
- Both measured session IDs, scope/principal/recipient selections, provider
  descriptors, endpoint and public TLS identities, and operator-controlled secret
  references. Do not place credentials or private keys in the manifest or report.
- Explicit consent for the synthetic fields disclosed to each recipient and the
  diagnostics retained. Integrity hashes do not confer disclosure authority.
- The four possible generation slots, all bounds, stop rules, and artifact-retention
  requirements for later approved execution.

### Frozen choices versus future observations

Avoid creating another circular readiness requirement:

**Freeze now:** code, models, logical corpus, recipients, exact static inputs,
construction rules, duration ceilings, identities and evaluation policy.

**Bind at actual admission later:** permitted clock samples, absolute deadlines,
request IDs derived under the frozen identity policy, and the exact constructed
prompt/receipt. Persist these once before their effect.

The future second prompt must use that live session's actual query capture, not a
rehearsal result. Freeze its construction and disclosure rules now; do not pretend
its not-yet-produced bytes already exist. No post-freeze prompt tuning is allowed.

Do not start the five-minute occurrence deadlines while preparing the campaign.
A later authorization supplies an execution window; individual deadlines are set
once at the specified admission event. Replay never grants additional time.

Static model identity can be frozen while current runtime availability remains
`NOT_CHECKED`. Missing required local bytes must be recorded explicitly and must
prevent future activation until independently validated. Never turn that fact into
a fixture-backed claim of real readiness.

### Manifest hashing and preservation

Use an explicitly defined canonical encoding and an external SHA-256 digest; do
not include the manifest's own digest in the bytes being hashed. Keep immutable
source/configuration inputs separate from outputs, mutable counters and approval.
A later documentation-only commit may be linked additively without changing what
was tested. Changes to any execution-affecting input invalidate the relevant
freeze and any subsequently bound authorization.

Implement a read-only verification command that recomputes the bindings and reports
drift without starting providers. It must work after all temporary test processes
are stopped. An unchanged final campaign must survive that cleanup.

## 6. Preserve the proposed limits without activating them

| Item | Frozen proposed ceiling or selection |
|---|---|
| Measured sessions | Two, sequential: local ModelInference; authenticated same-host HTTPS ModelInference |
| Other placement | HTTPS mailbox; local encoder, retrieval and cognitive owners |
| Generation slots | Two per session; four total; no transfer between sessions |
| Output bound | 6,000 tokens per call; 24,000 summed maximum allowance, not usage |
| Input/model deadline | 300,000 ms from the selected admission event |
| Tool/context bounds | Existing 30,000 ms bounds |
| Model RPC allowance | Existing eight reservations per occurrence |
| Backend evaluation | At most one reserved invocation per model-call occurrence |
| Commands | First call: exact approved query. Second: one permitted send |
| Effective authorization now | Zero |

For example, name the planned slots `model-local/query`, `model-local/reply`,
`model-https/query`, and `model-https/reply`, mapping them to the actual owner
session/slot fields. Naming a slot is not reserving or consuming it.

Implement and fixture-test durable accounting across both placements. A caller
retry must use the original occurrence; reopening a service cannot restore a spent
slot. Reuse owner reservation records and only the narrow campaign linkage needed
to enforce the four-slot ceiling. Do not introduce a second authority for model
results or a generic scheduling service.

Keep prospective aggregate accounting monotonic and conservative across separate
owner commits. A crash may waste an allowance; it cannot create extra permission.
An uncaptured reserved backend attempt remains spent. A captured response is
observed again, not regenerated. Transport retries do not imply backend retries.

After future authorization, a rejection, runtime error, timeout, wrong permitted
answer or ambiguous external effect ends that session. No replacement sessions,
repairs, aliases, re-prompting, fallback or extra warm-up calls. The other predeclared
session may proceed only within that future approval and absent a campaign-wide
safety, integrity or authorization failure. Preserve unused slots as unused.

## 7. Required generation-disabled tests

Run the new runner's shared orchestration, not just the older preparation harness.
Use test-only manifests/ledgers for simulated reservations and captures. The final
campaign must remain untouched and unreserved.

| Case | Required observation |
|---|---|
| Missing/wrong/expired authorization | Rejected before backend construction, runtime contact or generation reservation |
| Manifest/source/model/recipient/TLS drift | Refusal before effects; no repair or provider substitution |
| Valid test-only approval | Recorded backend exercises the same orchestration without becoming usable live approval |
| Correct recorded reply | Actual query capture, prompt binding, admitted output and peer observation all linked |
| Wrong permitted reply | Received body is scored incorrect rather than waiting for a preferred-answer constant |
| Unsupported/multiple/stage-inappropriate commands | Whole batch rejected before effects; no repair or follow-up generation |
| Missing/stale retrieval or failed hydration | Typed failure, not a successful empty answer or invented second prompt |
| Revoked or substituted principal | No new effects or unauthorized disclosure of captured data |
| Observer expiry | Classified separately; no renewed deadline, new occurrence or automatic retry |
| Uncaptured reserved completion | Spent/unknown result survives restart; no further backend evaluation |
| Captured completion/query recovery | Same bytes, view, identities and original limits are retained |
| Ambiguous external send | No resend, no invented recipient confirmation |
| Counter tampering or concurrent reopen | No duplicate reservation or aggregate/per-session budget reset |
| Initial-context inspection | No target answer, setup-history leakage or evaluator access |

Include real process termination at relevant new orchestration boundaries, using
recorded completion providers and real supported retrieval/channel services. Label
clock/response faults separately from actual process kills. A fake model does not
pass real-model usefulness, even when everything around it is real.

Verify the generation-denial guard with owned sentinels and blocked launch/connect
attempts, never a request to an actual model endpoint. Preserve the separate
namespace/filesystem controls already used by preparation; do not weaken them for
convenience. Inspect regression entrypoints to prevent accidental live execution.

Select affected historical tests through an explicit impact map. Preserve prior
failures and source records; do not repeat the full 102/214-file audit simply to
produce another review artifact. Report unique methods, repeated subsets,
parameterized scenarios, fixture evaluations and real E5 calls separately.

## 8. Deliverables and acceptance gates

Deliver working code, not only a specification:

1. Runnable preparation/qualification and guarded future-execution entrypoints,
   with exact commands and nonzero error exits for unsupported activation.
2. New focused tests and generation-disabled local/HTTPS integration evidence.
3. One frozen campaign manifest, external digest, persistent setup/view artifacts,
   empty execution ledger and absent approval record.
4. A concise preparation report, source/test manifests, actual changed-file list,
   and activation prerequisites. Preserve the old review and preparation evidence.
5. An approval request template containing the actual campaign ID and manifest
   digest. Mark it **unissued**; do not fabricate user approval or activate it.

| Gate | Required evidence |
|---|---|
| BASELINE | Correct starting implementation and narrowly scoped source reconciliation |
| RUNNER | Executable orchestration reuses existing contracts; no expected-output shortcut |
| ZERO_GENERATION | Denial mechanism tested; zero actual generative contacts/startups/evaluations |
| AUTHORIZATION | Separate approval binding, drift refusal and fail-closed pre-effect checks |
| ACTUAL_DATAFLOW | Native setup/query and exact result-to-next-prompt handoff remain real |
| EVALUATION | Authority, retrieval, prompt binding, factual correctness and peer receipt remain separate |
| RECOVERY_BUDGETS | Recorded-model kill tests preserve captures and conservative fixed-slot accounting |
| PLACEMENT | Same native consumer and runner logic exercised under both recorded-provider placements |
| FREEZE | Complete immutable plan, valid external hash and retained artifacts after cleanup |
| COMPATIBILITY | Impact-selected regressions; old entrypoints/profiles/evidence remain intact |

A source/runtime limitation is `BLOCKED` only for the affected gate. Missing live
approval is the intended final state, not a reason to skip the implementation.
Record executed incorrect behavior as `FAIL`, optional untested work as `NOT_RUN`,
and genuine partial completion as `PARTIAL`. Never mark live usefulness passed.

Stop only test processes created for this assignment; retain the artifacts needed
for the frozen campaign. Do not stop unrelated user services. Commit/push only
under separate current user/workspace authority, staging the reviewed task files
rather than unrelated work. A later commit is a publication reference, not a
retroactive test identity.

## 9. Required final report

Report exact commands, source hashes, fixtures versus real components, test counts,
corrected failures, integrity checks, campaign ID/digest and remaining prerequisites.
Give the next operator a concrete invocation recipe that still requires separately
supplied approval. Do not require another generic documentation pass before approval.

End with the actual values of:

```text
RUNNER_PREPARATION=READY | PARTIAL
CAMPAIGN_FREEZE=COMPLETE | INCOMPLETE
CAMPAIGN_ID=<actual identifier, or NOT_CREATED>
CAMPAIGN_MANIFEST_SHA256=<actual digest, or NOT_FROZEN>
CAMPAIGN_STATE=AWAITING_LIVE_AUTHORIZATION
PLANNED_GENERATION_SLOTS=4
AUTHORIZED_LIVE_GENERATIONS=0
RESERVED_LIVE_GENERATIONS=0
OBSERVED_GENERATIVE_BACKEND_CALLS=0
CAPTURED_LIVE_RESPONSES=0
ADDITIONAL_LIVE_GENERATIONS=0
LIVE_MEMORY_WORKFLOW=NOT_RUN
GENERATIVE_RUNTIME_AVAILABILITY=NOT_CHECKED
```

These live counters exclude clearly separated fixture-test counters. Missing
runtime bytes or untested availability must be disclosed, never disguised by the
`READY` preparation label.

The final decision requested from the user is approval of **this identified,
frozen campaign**, not permission to invent one afterward. No generation occurs
in this assignment. No new module-family or native-command adoption count results
from preparing this composition. Then stop.

## 10. Rationale and source scope

The original October 15 discussions called for version-independent functional
contracts, a practical local-to-remote prototype, explicit state owners and working
integration acceptance tests. They did not select this campaign, model or budget.
The detailed runner/freeze rules above are engineering instructions for the current
handoff, not retroactive meeting decisions.

Repository source findings are pinned to the baseline in section 1. The existing
workload and disabled proposal remain the semantic baseline; this brief changes
only the sequencing so implementation can finish before live authorization.
