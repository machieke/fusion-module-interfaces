# Conditional Codex handoff — retrieval-grounded live evaluation

## 1. Status, authority and objective

Continue `machieke/fusion-module-interfaces` from
`01d0b023e6990670eae65e14ed5910e64e72f929`, or record an explicitly selected
subsequent commit and its relevant diff. Read applicable `AGENTS.md`, the
retrieval-preparation report and decisions, the existing workload specification,
and `evidence/retrieval-preparation/live-plan.disabled.json`.

**This document is a proposed execution protocol, not a grant of live-generation
authority.** Current effective additional live-generation allowance is **ZERO**.
The previous S07 allowance is exhausted. The user's preparation-completion report
does not authorize model startup, generation, new spending, or a new campaign.

Only after a new explicit user authorization is bound to the frozen campaign may
the live portion run. Authorization must cover the two named placement sessions,
exact approved synthetic disclosure, selected runtime/model, limits, stop rules,
and any minimal runner changes. Merely receiving this document, passing a test,
setting `enabled=true`, or copying an old approval cannot supply that authority.
If authorization is missing, leave the campaign disabled and report
`AWAITING_LIVE_AUTHORIZATION`; do not run a generation-bearing readiness probe.

**Objective after authorization:** evaluate the already prepared, tightly guided
native `query -> send` workflow with actual generated model responses. Establish
whether the model follows the admitted query instruction, uses the returned
synthetic fact in its next input, and proposes a correct permitted reply actually
observed by the independent IRC peer, under local and same-host HTTPS
ModelInference placement.

This is not another module implementation, a new adoption family, unrestricted
autonomous tool selection, a statistical reliability benchmark, or a redesign of
memory, attention, inference or the agent loop. Stop after the finite campaign,
including unsuccessful outcomes. Do not extend it until it passes.

## 2. Review basis and preserved evidence

The reviewer inspected the pinned preparation publication, selected disclosure,
model-owner, native-startup, rehearsal and test source, plus the gate manifest and
disabled plan. The reviewer did not execute the suites, verify every publication
hash, start a runtime, or establish present generative-runtime availability.

The preparation records ten passing gates and 99 distinct methods: 27 new and
72 reexecuted methods. Its 22 combined workflow scenarios are contained in nine
integration methods; another integration method compares original/local/HTTPS
remember-query behavior. Every preparation model response is an authored fixture.
The native loop, E5, Chroma, DeTTa, IRC and HTTPS are real where reported.

The preparation started from `367c9b583eb85d6cf99ca93827c9f40b9c681bc6`, which
published the 17-file closeout after S07. Four final runs are recorded against the
same 214-file executable/test source set. Preserve those working-tree identities;
do not retrospectively describe them as executions of the later publication.

Inspect the relevant manifest-to-publication relationship once before proceeding.
A focused diff/hash check is sufficient where inputs match; do not repeat the
entire historical audit, claim a fresh whole-repository regression, or relabel
recorded fixture outputs as live results. Preserve all earlier failures and
unresolved S07 payload, context-export and usage facts.

## 3. Reuse the current contracts and sources

| Source | Purpose |
|---|---|
| `docs/omega-adoption/mettaclaw-neoclaw/retrieval-preparation.md` | Completed preparation, actual placement, test accounting and limits |
| `retrieval-preparation-decisions.md` in the same directory | `/10`, exact disclosure, stage admission, retained-view and privacy semantics |
| `s07-next-workload.md` in the same directory | Existing workload definition; do not create another scenario taxonomy |
| `evidence/retrieval-preparation/{verification,final-source,inputs,inputs-final-check}.json` | Qualification and source identities |
| `evidence/retrieval-preparation/live-plan.disabled.json` | Existing unauthorized campaign proposal and source/model candidates |
| `fusion/neoclaw_retrieval_disclosure.py` | Complete result/consent/view binding and sender-side current-policy preflight |
| `fusion/{model_service,model_transport,neoclaw_model}.py` | Independent model acceptance/reservation/capture, transport and application handoff |
| `integration/neoclaw/model_startup.py` | Source-checked native retrieval prompt, parser path and one-command grammar |
| `integration/neoclaw/retrieval_preparation.py` | Real native setup and fixture-only measured composition; reuse selectively |
| `integration/neoclaw/test_retrieval_preparation.py` | Recorded-response authority, recovery and evaluator cases |
| `integration/neoclaw/{preparation_guard,retrieval_fixture}.py` | Keep the zero-generation qualification path closed and explicitly fixture-backed |
| Existing S07 live backend, source lock and launch recipes | Locate through the repository's source ledger; reuse, do not invent a model server |

Keep `controlled-native-loop/10`, `synthetic-retrieval-query-send/1`,
`model.inference@1.0.0`, and `neoclaw-ollama-qwen38-text/2` unless a genuine
incompatibility requires a separately reviewed change. Preserve historical `/9`,
all memory/numerical profiles, state owners and current authorization.

The disabled plan has `executable_entrypoint=null`. Activation is therefore not
just a configuration toggle. A narrowly scoped live runner must connect the
qualified composition to the existing real S07 backend, with fail-closed
campaign admission. Do not add another application or owner state machine.

## 4. Minimal live-runner differences to address

These are preparation-to-live adaptation requirements, not defects invalidating
the fixture tests.

### Actual generated output, not expected fixture output

The rehearsal's convenience `workflow` waits for `BODIES[0]`. The test case helper
derives its expected body from the supplied fixture `commands`. That is appropriate
for those tests, but cannot be the live outcome source.

A live runner must:

- retain the real provider's raw response, native transformation and parsed batch;
- obtain the actual admitted `send` body from application-owned output/receipts;
- observe that exact output through the real peer and selected route/sender;
- give that observed body plus the actual captured retrieval to the evaluator;
- distinguish parser/admission rejection, no send, wrong permitted send, valid
  refusal, socket uncertainty and missing peer observation without fabricating an
  expected response;
- never write a fixture response into live model configuration or replace, alias,
  repair, rerank, truncate into validity or regenerate an unwanted proposal.

Do not copy an exporter whose `fixture_evaluations` field or constant `NOT_RUN`
status assumes preparation into a live success report. Preserve the preparation
exporter unchanged; select a small evidence adapter for actual live records.

### Observer timeouts are not command deadlines

Preparation helpers wait roughly 30–40 seconds for a completed query after the
first authored response. Those observers are not sufficient by definition for a
real generation governed by the existing 300-second bound.

Before admitting work, configure bounded observers to cover the selected model,
tool and handoff windows. Follow progress and the accepted deadlines; do not
extend an accepted deadline, change an owner budget, or classify an observer
expiry as a model rejection. Record startup/readiness, generation, query and
channel observation times separately. Do not make an unbounded wait to conceal a
failure. A timed-out observer does not authorize resubmission.

### Preserve the preparation guard

Do not remove the existing namespace/runtime denial or fixture checks to make the
preparation command generate real text. Keep that command zero-generation. The
separate live entrypoint must require the new bound authorization before any
real generative runtime start/load/contact permitted by that authorization.
Unit and recorded-response checks for the small runner delta must run with real
generation denied. A fixture-only pass remains fixture evidence.

## 5. Freeze the campaign before any generation

Use a new campaign directory and fresh measured journals, never the old S07 call
ledger or completed preparation journals. Preserve the disabled proposal as
historical evidence. The active authorization record, when supplied, belongs to a
new immutable plan identifying:

1. The preparation publication, exact runner diff/publication and tested file
   hashes; the existing runtime/model/profile and verified assets.
2. The fresh synthetic fact records, their native setup identities and committed
   enrollment/source view, exact query, two peer inputs and native prompt template.
3. The exact equally eligible harmless answer bodies and the independent evaluator
   rule, plus approved diagnostic fields. The answer file is not model-visible.
4. The two named sessions, provider selections, principal/scope/recipient bindings,
   local endpoint/TLS identities, and approved raw/transformed prompt components.
5. Four uniquely named possible generation slots, per-session limits, original
   deadlines, owner/application reservation budgets, and stop rules.
6. The actual user authorization, its scope and the exact plan it approves.

Resolve setup-versus-measured identities before freezing. Actual native remember
must populate the new synthetic corpus; do not pre-enroll the answer through an
operator database shortcut. Setup may use explicit command fixtures and real E5;
it is not measured model-directed memory creation. Obtaining new setup data or
starting bounded test infrastructure still requires the assigned task's authority.
No artifact or instruction in this document grants it on its own.

Runtime availability remains unknown until verified. The historical candidate is
only a candidate: read exact model/runtime identifiers from the selected source
locks, verify their obtainable bytes, and stop on drift or missing prerequisites.
Do not silently pull a new tag, use a hosted substitute or change quantization,
prompt settings, temperature, seeds, model options or hidden conversation state.
Any readiness call capable of generation would consume the finite allowance and
is not an additional free warm-up. Prefer verified non-generating checks.

A needed behavioral/model/source change after freeze stops activation and requires
an updated reviewed plan and authorization. Do not tune during a measured campaign.

## 6. Proposed authorized envelope — presently inactive

These limits are carried forward from the disabled proposal, not newly granted:

| Item | Ceiling / selection |
|---|---|
| Placement sessions | 2, predeclared and sequential |
| Session A ModelInference | Local provider binding |
| Session B ModelInference | Authenticated same-host HTTPS binding |
| Mailbox in both | Authenticated same-host HTTPS |
| E5, retrieval, C1/C2 and Attention in both | Local under the already qualified profiles |
| Model generations | At most 2 per session and 4 total |
| Output tokens | At most 6,000 per call; 24,000 summed maximum allowance, not actual usage |
| Input/model deadline | Existing 300,000 ms |
| Tool/context deadline | Existing 30,000 ms |
| Model application RPC reservations | Existing 8 per occurrence |
| Owner evaluation reservation | Existing 1 per occurrence |
| External send | Existing one reserved socket attempt; no automatic resend |

Hold the synthetic content, query, prompt, model/options, memory view semantics
and non-model placements constant. Independent sessions have fresh identities and
journals, not shared accepted responses or inherited setup/model conversation.
Use the same frozen logical corpus, with explicit identity correspondence where
separate native setup is required. Do not change the target location along with
placement and then describe it as a controlled placement comparison.

Do not claim the combined campaign exercises remote private memory: it changes
ModelInference placement only. Earlier HTTPS Embedding/Search/AtomStorage passes
remain separate evidence. This campaign does not require another all-combinations
matrix, counterfactual live run, absence test or new SIGKILL generation.

## 7. Execute the two-stage workload without an answer shortcut

### Before the measured model input

Confirm separate setup storage acceptance, Search publication, metadata readiness
and native remember success. Start a fresh measured native session with no setup
commands/results/history, no inherited provider conversation and empty promoted
context. Empty context must come from the selected owner state, not target-specific
removal of an inconvenient record.

The complete first native prompt, question and help may describe the required
query and response format but must not contain the target location, correct answer
body, expected-answer file or selected-answer hint. All possible result components
must have recipient-specific approval; approval cannot serve as the answer oracle.
The provider process has no filesystem access to the corpus/index/evaluator,
application journals, preparation answer scripts or unapproved private records.
Document actual isolation; do not upgrade same-host checks to hostile-host claims.

### First real generation and retrieval

The independent peer sends the frozen first input. The actual model response must
pass the native parser and whole-batch stage policy: exactly the approved query.
Do not accept an unauthorized alternative just because it seems useful.

Execute actual native Embedding -> Search -> AtomStorage hydration -> local
presentation. Bind the selected view and capture the real query result. Confirm
that the expected target fact is actually present for this positive campaign;
otherwise stop that session as a retrieval failure before answer generation.
Do not change the query/corpus, widen top-k or rebuild the selected view to rescue it.

### Second real generation and reply

After successful committed retrieval, the peer sends the frozen follow-up asking
for a reply from the preceding result. It does not supply a location. The next
prompt must contain the exact captured native projection with the retained view
and valid disclosure receipt. Preserve the sender's current-policy preflight and
the owner's independent checks before disclosure/processing.

The real second response must parse as one permitted send. All harmless candidate
locations remain equally eligible for publication. Score the actual proposal and
peer-observed body, not a test's preferred body. A wrong but permitted answer is
allowed to be sent and is a task failure. An unjustified refusal is also a task
failure. Missing generation/capture, command refusal and uncertain delivery each
keep their own outcomes.

This is a guided two-call factual lookup, not autonomous planning, general memory
comprehension or proof that retrieval causally improved the model. Successful
answers from two sessions are useful examples, not a reliability estimate.

## 8. Reservation, recovery and stopping discipline

Create durable campaign and per-owner slot accounting before a request can escape.
Two separate model owners must not each silently inherit a four-call allowance;
each has its assigned maximum two slots, with aggregate maximum four. Reuse the
existing owner enforcement and a small operator-run ledger, not a new scheduler.

Reserve before physical evaluation. A crash can spend a reservation without a
captured response. Count attempted/reserved, observed backend calls, captures and
usage separately. No uncaptured failure earns a refund. Unknown usage remains
unknown, not zero. Provider transport retries must not become extra backend calls.

A durable captured response may be observed again through the same authorized
occurrence without generation. Recovery preserves prompts, source views, result
bytes, deadlines, command identities and spent budgets. Recovery is not permission
to create a new occurrence. No automatic send follows an ambiguous spent socket
attempt, and socket return is not peer receipt.

Stop the affected session at its first parser/admission rejection, error, timeout,
incorrect permitted answer or ambiguous effect. Preserve unspent subsequent slots.
The second session may still run once only if the explicit frozen authorization
includes it and the first result was an ordinary recorded task failure. Any
privacy violation, source/authorization mismatch, budget-control failure or
untrusted evidence condition stops the entire campaign before further disclosure.

Never repair responses, alter prompts/allowlists, switch models, extend accepted
deadlines, run replacement sessions or repeat until green. End after both planned
sessions terminate or the four-reservation ceiling is reached, even with no
successful workflow. Retain nodes/owners only as needed for bounded read-only
observation, then stop all processes started for this campaign.

## 9. Required evidence and outcome reporting

Retain sufficient approved synthetic trace for independent review:

- frozen plan, source/model/runtime hashes, authorization and recipient scope;
- native setup, source head, published generation and complete selected views;
- actual IRC inputs, accepted prompts before/after native transformation and
  disclosure receipt bindings;
- all reservations, actual request/response metadata, captures, finish reasons,
  supplied usage or explicit unknowns;
- parsed proposals, admission and actual query vectors/candidates/payload checks;
- exact query projection in the second model input;
- actual outbound body, acceptance, socket result and independent peer observation;
- every failure/timeout, unspent slot and lifecycle teardown observation.

Do not publish credentials, TLS keys, raw private journals, evaluator access paths
or unapproved content. Export complete approved view bindings rather than silently
dropping them. Retain unknown diagnostics instead of reconstructing missing data.

Report each placement separately with at least:

| Dimension | Example outcomes |
|---|---|
| Runtime readiness | READY / BLOCKED / FAIL |
| Generation slot | UNATTEMPTED / RESERVED_UNCAPTURED / CAPTURED / CAPTURED_LATE |
| Command admission | AUTHORIZED / REJECTED / NOT_REACHED |
| Retrieval | VERIFIED_TARGET_PRESENT / FAILED / NOT_REACHED |
| Second-input binding | VERIFIED / FAILED / NOT_REACHED |
| Answer | CORRECT / INCORRECT / REFUSAL / NOT_REACHED |
| External delivery | PEER_OBSERVED / UNKNOWN / NOT_SENT |
| Task result | PASS / FAIL / NOT_RUN, with reason |

A completed campaign is not necessarily a passing campaign. Two-placement positive
success requires a genuine complete positive workflow in both sessions. One pass
is one demonstrated placement, not proof that both passed. Contract enforcement
can pass while a model's task fails. Do not collapse those assessments.

Preserve the preparation's 99-method evidence and historical S07 results. New
runner tests, repeated existing methods, live generation calls and live workflows
are different units. The fifteen-family inventory and X01/X02 adoption entries do
not increase because an existing composition gains a real-model demonstration.

Suggested final status fields:

    PREPARATION_STATUS=READY_FOR_LIVE_AUTHORIZATION  # historical, unchanged
    CAMPAIGN_STATE=<AWAITING_AUTHORIZATION|BLOCKED|STOPPED|COMPLETED>
    PLANNED_GENERATION_SLOTS=4
    AUTHORIZED_GENERATIONS=<0 unless newly granted; otherwise approved cap>
    RESERVED_GENERATIONS=<actual>
    CAPTURED_RESPONSES=<actual>
    LOCAL_TASK=<PASS|FAIL|NOT_RUN>
    HTTPS_TASK=<PASS|FAIL|NOT_RUN>
    LIVE_MEMORY_WORKFLOW=<NOT_RUN|ATTEMPTED|PARTIAL|PASS>

Use the repository's established equivalent states where they are more precise;
do not add a new reporting framework. Update the existing workload/evidence entry.
Finish with the exact tested source and any later publication distinction. Commit
or push only under the applicable explicit workspace/user permission.

**Then stop.** No new capability, migration, private remote memory, public network,
full-default Omega, multi-host, live attention/revision campaign or chain work.

## Review sources

All new preparation findings refer to the immutable publication:

```text
https://github.com/machieke/fusion-module-interfaces/tree/01d0b023e6990670eae65e14ed5910e64e72f929
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/01d0b023e6990670eae65e14ed5910e64e72f929/docs/omega-adoption/mettaclaw-neoclaw/retrieval-preparation.md
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/01d0b023e6990670eae65e14ed5910e64e72f929/evidence/retrieval-preparation/live-plan.disabled.json
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/01d0b023e6990670eae65e14ed5910e64e72f929/integration/neoclaw/retrieval_preparation.py
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/01d0b023e6990670eae65e14ed5910e64e72f929/integration/neoclaw/test_retrieval_preparation.py
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/01d0b023e6990670eae65e14ed5910e64e72f929/fusion/neoclaw_retrieval_disclosure.py
```

The October 15 meeting direction supports granular contracts and integrated
behavior. It does not itself authorize this campaign, choose this model, or grant
a new token/call budget.
