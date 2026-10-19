# Codex handoff — S07: bounded native model-completion adoption

## 1. Objective and stop boundary

Continue `machieke/fusion-module-interfaces` from
`3fc1af31f2d64583fe4c873b6b656dad2d6b1275`, or record the exact descendant and
relevant differences. Read applicable AGENTS.md, the original interface brief,
the MeTTaClaw mapping, S01–S06 contracts and current evidence. Preserve unrelated
work, source-access restrictions, historical profiles and historical results.

**Proposed increment:** adopt one existing text-completion boundary of the actual
native Omega loop through a typed ModelInference interface. Replace the scripted
model only in a new selected composition. Demonstrate a real generative model
receiving a durably bound native prompt, returning a durably captured response,
and proposing an authorized existing command whose actual result reaches the next
model input. Retain real S06 IRC input and bounded outbound delivery.

This is the mapped S07 / X01 capability, not another PLNKernel rule or a new
reference family. Model completion is already an external call in the upstream
application; the value here is its contract, authority, capture, recoverability
and selectable provider placement—not a claim of newly inventing remote LLMs.

**Stop at bounded S07.** One text-only, non-streaming completion profile and one
real model backend. No vision, media capture, model training, new cognitive math,
general provider marketplace, arbitrary execution, second channel, public IRC,
private-memory export, populated-state migration, multi-host or chain work. Do
not build a generic model-serving framework or replace the native agent loop.
Full default Omega startup and production autonomy are not acceptance criteria.

The positive workflow uses fresh, explicitly disclosure-approved synthetic data.
It must not silently reuse private S04/S05 prompt material in a network model call.

## 2. Review basis and source reconciliation

The reviewer inspected selected public implementation, native source and recorded
S06 evidence at the commit above. No native suites, server, model or dependency
build was independently executed, and not every manifest hash was reconciled.
Confirm all findings against the actual checkout before changing code.

S06 reports 25 new methods and 151 selected historical methods, a 176-method
passing union across runs/rechecks. Its model remains scripted. Historical source
manifests identify working-tree test inputs on `c9c6e798…`; the publication commit
must not replace those historical identities. Compare the selected checkout with
`evidence/s06/{source-state,test-source,final-audit}.json` and its per-run records.
Explain differences and run an impact-selected baseline, not a cosmetic full rerun.

Keep these verified project dependencies unless a concrete incompatibility is
recorded: MeTTaClaw `2af37c3fec18613de54ca42fde2382a9087d4524`; PeTTa
`fea83178af3722666d2948d074591d10a3134f56`; the selected SWI 10.0.1 build; DeTTa
`272888f264dd2dde18b574cabb53c266b0dac2ec`; existing Chroma/E5 locks; and ngIRCd
`6ae13bf89e934d167f6ead8bb9ee39f57a0935c0`. Preserve the independent Fusion PLN/SWI
profiles. New completion-provider inputs receive their own source/runtime ledger.

### Source ledger: findings to verify, not instructions to copy blindly

| Source at the selected pin | Inspection target |
|---|---|
| `docs/omega-adoption/mettaclaw-neoclaw/{remote-placement,seam-contracts,interface-gaps}.md` | Historical S07 and X01; ModelInference is distinct from logical rule application. Preserve historical mapping classifications. |
| `docs/omega-adoption/mettaclaw-neoclaw/{s06,s06-contract-decisions}.md`; `evidence/s06/` | Current capture/acknowledgment, send uncertainty, privacy and replay limits. |
| Native `src/loop.metta` | Actual getContext, receive, provider branch, prompt separator, parsing, command execution and next-context order. |
| Native `lib_llm_ext.py` | `_chat`, `_clean`, selected text wrapper, effective arguments, eager clients and retry layers. |
| `integration/neoclaw/{native_loop,startup_overlay}.py` | Checked source overlay and model-fixture import; preserve old compositions. |
| `integration/neoclaw/controlled/lib_llm_ext.py` | Scripted response selection; must be unavailable on the new real-model path, retained for historical tests. |
| `fusion/neoclaw_application.py`; `integration/neoclaw/loop_bridge.py` | Existing command acceptance occurs after model output; add pre-generation identity without duplicating the application lifecycle. |
| `fusion/{neoclaw_channel,irc_bridge}.py` | Durable input slot, current authority, one-attempt egress and explicit uncertainty. |
| `integration/neoclaw/channel_startup.py` | Selected socket audit hook currently permits only the mailbox endpoint; an added model endpoint needs a new exact composition, not removal of the guard. |
| `fusion/neoclaw_priority.py`, `neoclaw_evidence.py` | Retained local context/evidence; prevent additional disclosure or unintended mutation. |
| Existing Embedding/execution client and provider patterns | Reuse source validation, selected descriptors, reservations and capture patterns where compatible; do not copy entire state machines. |

## 3. Resolve one real provider before expanding implementation

Make one bounded inspection of the intended native text wrappers and authorized
operator configuration. Prefer an already authorized provider/model used by an
existing wrapper. Record its native callable, effective request, endpoint identity,
model identifier, SDK/version, supported options, observed response fields and
source of configuration. Consult its current primary API documentation as needed.
A model string in the historical source does not prove current availability.

No access keys were supplied by this handoff. Use existing explicitly authorized
credentials and a finite operator-approved test budget only; do not search other
accounts, print keys, purchase credits, create subscriptions or infer permission
from the mere presence of an environment variable. When paid usage authorization
is absent, leave that prerequisite BLOCKED. An already authorized, available real
local text-generation runtime may instead be selected under an explicit different
provider/model profile; do not download/train a replacement model programme merely
to avoid reporting missing inputs.

Use only one selected backend for required integration. An alternative chosen
before admission is a new recorded baseline, not a fallback during a request.
Never change model/provider after an uncertain generation. Distinguish:

- local ModelInference adapter calling the selected backend;
- authenticated same-host HTTPS ModelInference provider calling that same backend;
- actual location of the model computation, which may still be hosted externally.

A local adapter around a hosted API is not local model inference. An HTTPS facade
returning prerecorded text is not a real-model gate. E5 is not a substitute for a
generative completion model. Require actual generated text in the positive gate.

For hosted models, record returned model/version/fingerprint where available, but
do not claim weight-level pinning when the service exposes only a model identifier.
For local models, record obtainable model/runtime/tokenizer identities. Missing
prerequisites permit useful partial delivery, not complete S07 PASS.

## 4. Preserve the native request while declaring intentional changes

Establish a source-checked oracle for the selected native wrapper. Use recorded
SDK responses to compare deterministic request construction and response rendering;
use actual model calls separately to prove live integration. Do not require two
independent generations to produce the same text.

Inspect actual transformations, not only nominal loop settings. At the reviewed
pin `_chat` removes specific XML-like markers, splits at the first `:-:-:-:`,
supplies an empty-input fallback, and cleans quote placeholders in output. Wrappers
also fix effective model/options, initialize clients eagerly and have retry behavior.
Those details must be mapped explicitly; configuration names alone are insufficient.

Keep admitted prompt construction, role order, escaping and successful text
presentation. Source-check the narrow helpers; avoid initializing unrelated keys,
vision/embedding clients or media imports just to make one text request. Do not
silently redesign the agent prompt or claim parity after changing the effective
model, reasoning options, token limits, repair rules or context truncation.

Safer admission and retry restrictions below are intentional new-profile behavior.
Preserve original fixtures and historical live-wrapper code under old profiles.
Do not edit upstream worktrees in place. New profiles may require fresh journals;
confirm the actual catalogue before choosing the next composition version.

## 5. Typed ModelInference contract and distinct responsibilities

Use the existing X01 name. Add the smallest adequate port, such as `complete` plus
a narrowly scoped `observe` for retained outcomes. It is not an `execute(anything)`
operation and not a tool the model may invoke recursively to change its own policy.
Reuse applicable contract/transport infrastructure; no separate scheduler is needed.

| Owner or boundary | Responsibility |
|---|---|
| Native application | Prompt assembly, accepted channel/context assignment, model-call identity, command authorization and next-context handoff. |
| ModelInference provider | Selected model invocation, enforceable attempt bounds, captured completion and bound outcome receipts. No tool execution or direct cognitive-state access. |
| Model/backend adapter | Exact selected SDK/runtime mapping, observed usage/finish/error information and narrow text conversion. |
| Local/private persistence | Captured prompt and completion bytes under their declared scope; no automatic shared mailbox, DA publication or new C1 observation. |
| Messaging/IRC bridge | Existing durable channel handoff and conservative external send; no authority granted by generated text. |
| C1/C2/Attention/Search | Their current state ownership remains unchanged. A model response is not automatically evidence, belief or priority. |

The request must bind trusted principal, scope, exact provider/descriptor/profile,
model parameters, model-call identity, native processing slot and context binding,
ordered text input, original deadline, byte/token limits and finite attempt policy.
Select endpoints, credentials, model, limits and permitted tools in trusted
composition, never in model/user-controlled arguments. No arbitrary URLs, files,
code, imports, media or delegated credential bundles.

Use one non-streamed text result and no provider-native tools/functions in this
increment. Include request binding, exact returned text, selected/observed model,
provider request ID when supplied, observed usage, finish reason and errors. Missing
usage is unknown, not zero; a returned provider name is not execution attestation.
Bound request/response bytes and all collections. Validate context-window and
output-token assumptions against the selected provider; reject oversized input
before effects rather than silently dropping memories or other native sections.

Retain the provider's original observed text separately from native compatibility
cleaning and parsing. Bind transformed text to its transformation version. Refusal,
empty/null text, truncation, multiple choices, unexpected tools/media, malformed
usage and unsupported finish states need explicit outcomes. A captured completion
need not be an admissible command. Never parse an incomplete truncated prefix as
successful instructions or repair an error into a fabricated command.

Do not persist hidden reasoning or unnecessary provider internals. Where the API
returns separate reasoning metadata, capture only what the selected contract
actually needs (for example accounting), not an extra memory stream or public log.

## 6. Identity and capture BEFORE tool-command acceptance

Model generation precedes the commands it will propose. Do not assign it a future
tool position or identify it by prompt text alone. Reuse the application's durable
input slot and context-preparation machinery to establish a model-call occurrence.
Two genuine input events with equal text remain distinct. Recovery of one model
call keeps its identity even before any command has been accepted.

Bind and durably capture the exact selected prompt before provider dispatch. Include
the already selected getContext segment, incoming message occurrence and relevant
view identifiers locally, plus effective model/options and original deadline.
The native TIME field and other changing context must not silently regenerate a
different prompt when that occurrence resumes. This is an exact input snapshot,
not a globally atomic snapshot of all owners. Do not acknowledge another channel
input or advance context just to evade a failed generation.

Preferred bounded lifecycle:

    real IRC input -> existing durable application assignment
        -> selected native prompt and model-call intent committed locally
        -> authorized provider accepts exact call; reserves generation opportunity
        -> actual backend response captured and bound durably
        -> application captures that exact provider result
        -> native cleaning/parser produces candidate commands
        -> whole batch is authorized and accepted with stable command identities
        -> existing command execution and result capture
        -> subsequent model input contains the actual tool result

Independent owners commit separately. No shared-file access to another owner's
journal and no cross-owner transaction. A provider may use a small durable call
ledger to enforce reservations and retain results; it must not copy the agent
loop, create another belief owner or expose general task execution. Reuse existing
persistence and observation patterns where appropriate.

After provider capture, caller retry retrieves the same completion without new
generation. After application capture, replay must not contact the model merely to
recreate text. Current disclosure/command authority still applies. A rejection by
the parser or tool policy is recorded against that captured result; do not discard
it and regenerate invisibly until the model happens to obey.

## 7. Attempts, deadlines and uncertain cost

Declare one backend invocation reservation per model-call occurrence for the first
profile. Disable helper/SDK/provider-routing automatic retries or prove how every
layer is counted and bounded. A caller HTTPS retry must not start another backend
invocation. Different profile guarantees require a separately tested decision;
never describe a client-send count as proof of upstream execution count.

Reserve before the request can escape. An interruption after reservation but
before durable provider response capture may leave an unknown/spent result with
no command. Do not refund it, reset time, choose another model or retry under a
fresh hidden identity. Explicit user/operator-authorized future work may have a
new identity, but is not recovery of the previous generation.

Capture the response before replying to the caller. Treat lost replies after
capture differently from lost responses before capture. Bound startup/readiness,
request, response-capture and observation operations separately. Readiness time
before admission must not be used to extend an accepted deadline.

Use finite session limits on model-call occurrences, invocations, output tokens,
bytes and elapsed time. Do not enlarge the budget on restart or after a malformed
response. Account for returned reasoning/token usage where available. Unknown
billing after an ambiguous request remains unknown; no exactly-once billing or
cancellation guarantee. Record cost only from a documented selected pricing/usage
source, labelled as measured or estimated; do not invent a current price.

Observation after expiry may retrieve an earlier captured result. It does not
authorize new generation, late missing command creation or a new external send.
Define whether completed-but-late responses can be retained for diagnostics without
execution; test the selected behavior. New command deadlines may start only at
legitimate command admission, and recovery must never extend those already bound.
Preserve the S06 source/input deadline; a slow model must not receive repeated fresh
input slots or synthetic inputs to keep itself alive.

## 8. Prompt disclosure, output authority and isolation

The complete native prompt can contain history, tool results, promoted content,
labels and timestamps. Permission to receive an IRC message, send a vector or call
Embedding does not permit disclosure of that whole context. Hashing private
material does not automatically make it approved for transmission or publication.

Prepare a fresh S07 session with explicitly approved synthetic prompt components.
Do not reuse private S04/S05 canaries as positive prompt content or relabel existing
private journals as shareable. Before any model authorization call or SDK request,
check all actual prompt recipients and the exact raw/transformed representations.
Approved operator-owned fixtures and public scaffold may be composed locally; an
untrusted `synthetic=true` or matching digest is not sufficient consent. No general
redaction/declassification engine is requested. Encountering disallowed content
must stop before disclosure, rather than silently redact it and claim native parity.

If the model provider is HTTPS, it sees only the approved request, not the native
workdir, full corpus, mailbox credentials or C1/C2/Attention databases. The HTTPS
caller must lack the model provider's key and any local inference assets used by
that backend. For a hosted backend, only the provider process may contact the
approved hosted endpoint. Pin exact new routes in a selected composition; retain
S06's direct-IRC and other network restrictions. Do not remove the audit hook,
allow arbitrary sockets or label Python guards as an OS-level hostile-code sandbox.
Verify actual boundaries in the launched processes; no public service or host-wide
firewall changes. Local/private cognition remains local even when generated prompt
material is explicitly approved for a separate model profile.

The returned command proposal is UNTRUSTED. Keep native parser/format behavior on
its admitted domain, but validate the full parsed AST/batch before any `eval` or
other effect. In the positive session allow only a small existing set, such as the
exact S01 expression and bounded native `send` to the approved S06 route/body set.
Do not expose arbitrary `metta`, shell, paths, imports, configuration changes or
non-adopted commands because they remain visible in historical skill descriptions.
Prompt descriptions are not authority. Preserve batch limits and refuse mixed or
unsupported batches before partial execution where that is the selected policy.

Show the selected supported subset to the model through an explicitly documented
prompt/profile decision, reusing current skill definitions. This does not authorize
X05 ToolDescriptor implementation or silent rewriting of old prompts. Retain and
audit raw output plus the native normalized/parsed proposal; test that cleaning,
parenthesis repair, nested expressions and Unicode cannot bypass authorization.

S06 exact-body egress approval remains in force. A model may propose a fixed approved
synthetic reply; tests must observe it actually doing so, never replace its answer.
Unexpected or private output is refused, not automatically approved by the harness.
Do not weaken egress consent merely to make an unconstrained response transmissible.
No claim that these finite tests establish general prompt-injection immunity.

## 9. Required demonstrations and tests

### Deterministic contract and compatibility evidence

Run the original source-checked request builder/renderer and new adapter with the
same recorded provider responses. Compare actual effective request parameters,
role order, raw/transformed strings, native presentation and command proposals.
These are fixtures, not live-generation results. Preserve successful behavior on
the named domain and separately test intentional retry/admission restrictions.

Reject mismatched request/profile/model/principal, changed input under one identity,
bad certificates, unauthorized endpoint/options, malformed/refused/empty/truncated
responses, oversized context, hidden retries and credential substitution. Test
cancellation/timeout observations only to the extent the selected backend exposes
them. No fallback to the old scripted model, original direct wrapper or another
backend. A provider outage must not become an empty successful turn.

### Real channel + real model + real existing tools

Use one real isolated ngIRCd and independent peer with fresh generated state.
Compare local and authenticated same-host HTTPS ModelInference placement using the
same native application logic and selected backend. Hold channel placement fixed
for that comparison; add one combined HTTPS-mailbox/HTTPS-model check without
requiring every Cartesian product of prior profiles.

1. A peer sends a generated request through the actual S06 input path.
2. The actual native prompt, including selected S05 context, reaches the real model.
3. The model itself proposes one permitted existing S01 calculation. No fixture,
   expected-answer file or hardcoded response supplies the proposal.
4. Native dispatch executes the real pinned function; its actual captured result
   appears in the NEXT request received by the model.
5. The model proposes an allowed synthetic native reply. Existing S06 handoff and
   bridge deliver it on the healthy path; the peer observes its exact body.
6. A response/model-call replay reuses accepted identities and bytes rather than
   generating another command or sending again.

Generated peer inputs, task instructions, approved reply choices, clocks and small
memory corpus remain fixtures. The model RESPONSE must not be one. No exact textual
agreement between separate live generations is required; each trace must bind its
actual result. Verify request/response facts, tool effects, next-context consumption
and peer observations, not a cognitive-quality score.

Bound the rehearsal's calls in advance and record every attempt, refusal and output.
Do not keep sampling, alter the model or repair responses until the test turns
green while discarding failures. Correctly refusing an invalid model proposal can
pass a safety case but cannot pass the positive live-workflow gate. If the chosen
backend cannot satisfy that bounded workflow, report the unsatisfied gate and stop.

### Recovery and no-new-effect checks

Use actual SIGKILL at durable boundaries, deterministic failpoints and separate
fault fixtures. At minimum exercise:

- accepted prompt before provider admission;
- backend reservation before request transmission;
- actual backend response lost before durable capture (explicit spent/unknown);
- provider capture before caller receives the reply;
- application capture before native command acceptance;
- command/result capture before the next model context;
- subsequent IRC-send uncertainty retaining S06's no-resend behavior.

After capture, assert zero new backend invocations for the original call, exact
raw/rendered response identity, unchanged original prompt/deadline/budgets and no
second command/source occurrence. Before capture, report unknown/spent without
claiming absent execution. For live fault tests, a response-dropping wrapper may
intercept a REAL response; identify that fault separately from the real backend.
Do not require many paid model calls solely to exercise deterministic storage
faults: use explicit fixtures for broad negatives and at least one real-model
post-capture caller recovery through native dispatch.

Test private content and identifying derivatives in candidate context, credential
substitution at replay/disclosure, revocation before generation and before command
admission, provider unavailability and finite journal/session capacity. Confirm that
response capture itself does not revise C2, promote a target or manufacture C1
sources. Only separately accepted adopted commands may cause their declared effects.

## 10. Regression, reporting and acceptance gates

Use an impact map covering S06 channel ownership, input identity, S01 command
recovery, current-authority release, S03 read/write/embedding, S04 evidence and S05
context consumers affected by shared code. Preserve historical source-freeze guards;
document the new scope instead of deleting checks. Selected regression unions,
parameterized kill scenarios and live rehearsals remain separate counts. Reused
verified builds/caches are not clean or empty-cache reproduction.

| Gate | Required PASS evidence |
|---|---|
| BASELINE_SOURCE | Exact S06 reconciliation, selected baseline/regressions and pinned new model inputs |
| NATIVE_REQUEST | Original request/render oracle, actual effective model/options and declared profile changes |
| MODEL_CONTRACT | Typed completion/observation, bound authority, closed inputs/results and separate ownership |
| PROMPT_BINDING | Model-call identity exists before commands; exact retained context/input and original limits |
| REAL_MODEL | Actual generative backend executed; no scripted model on the positive path |
| LOCAL_HTTPS | Same native consumer with local and authenticated network ModelInference; truthful backend location |
| CAPTURE_RECOVERY | Real post-capture native recovery; no new generation, restored budgets or duplicate logical commands |
| BUDGET_UNCERTAINTY | Enforced reservations/session limits; retries and unknown execution/cost remain explicit |
| COMMAND_AUTHORITY | Parsed model proposals are authorized before effects; malformed/truncated/private outputs fail closed |
| CHANNEL_LOOP | Real IRC -> real model -> adopted tool -> actual result in next model input -> approved native send/peer observation |
| PRIVACY_ISOLATION | Exact prompt-disclosure consent, canaries, role/credential binding and tested caller/provider separation |
| COMPAT_REPRO_LEDGER | Historical profiles intact, reproducible selected recipe, precise X01 adoption and honest unrun work |

No fixture-only or raw API smoke result can pass the required real native loop.
Missing source/access/budget is BLOCKED; incorrect executed behavior is FAIL;
observation timeouts remain explicit; deliberately unexercised extras are NOT_RUN.
Deliver independent contract work on a blocked prerequisite without claiming S07
completion or inventing a successful model response.

Update existing contracts, source locks, ADRs, runbook and operation ledger. Deliver
one S07 report, gates, exact test/final source manifests, sanitized same-request trace
and operator startup/readiness/shutdown recipe. Record old-versus-new prompt and
admission semantics, individual model locations, limits, costs if known, and
measurements separating provider readiness, inference, tool work and channel delay.
Never publish keys, full private contexts, private hashes or raw cognitive journals.
A sanitized trace may include only approved synthetic identifiers and observations.

The historical 15-family inventory remains fixed. X01 is an explicit extension;
S07 is a pre-command internal completion adoption, not an additional user skill or
a claim that all model wrappers/vision modes are covered. Preserve the existing
eight entries/nine user-command baseline when adding the appropriate separate row.

**Then stop at S07.** The supported claim is a bounded selected Omega composition
with real channel input, real model completion through a module interface, existing
authorized tool execution and recoverable response consumption. It is not full
default/live Omega, unrestricted autonomous tool use, production private-memory
hosting, guaranteed external delivery, deterministic generation or on-chain AI.

## Review reference locations

Fusion paths above refer to `3fc1af31f2d64583fe4c873b6b656dad2d6b1275`.
Native paths refer to `patham9/mettaclaw@2af37c3fec18613de54ca42fde2382a9087d4524`.
The implementation choices in this handoff are proposals; the meeting supports
functional interfaces and single-owner state, not any particular model vendor.

- https://github.com/machieke/fusion-module-interfaces/tree/3fc1af31f2d64583fe4c873b6b656dad2d6b1275
- https://raw.githubusercontent.com/machieke/fusion-module-interfaces/3fc1af31f2d64583fe4c873b6b656dad2d6b1275/docs/omega-adoption/mettaclaw-neoclaw/seam-contracts.md
- https://raw.githubusercontent.com/machieke/fusion-module-interfaces/3fc1af31f2d64583fe4c873b6b656dad2d6b1275/fusion/neoclaw_application.py
- https://raw.githubusercontent.com/machieke/fusion-module-interfaces/3fc1af31f2d64583fe4c873b6b656dad2d6b1275/integration/neoclaw/native_loop.py
- https://raw.githubusercontent.com/patham9/mettaclaw/2af37c3fec18613de54ca42fde2382a9087d4524/src/loop.metta
- https://raw.githubusercontent.com/patham9/mettaclaw/2af37c3fec18613de54ca42fde2382a9087d4524/lib_llm_ext.py
