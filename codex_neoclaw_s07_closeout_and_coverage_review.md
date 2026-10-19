# Codex handoff — S07 closeout and functional-coverage review

## 1. Objective and hard stopping boundary

Continue the completed, uncommitted S07 working tree in
`machieke/fusion-module-interfaces`. The reported parent is
`3fc1af31f2d64583fe4c873b6b656dad2d6b1275`; that commit alone does NOT contain
S07. Read applicable AGENTS.md, the S07 brief, the current adoption ledger,
contract decisions, report and source manifests. Preserve unrelated changes.

**This is an evidence/review task, not S08 or another runtime milestone.**
Reconcile the exact completed source, prepare an inspectable reference, update
the operation-to-module coverage assessment, and specify one subsequent useful
memory workload. Do not implement that workload.

**Additional authorized model generations: ZERO.** The prior twelve-attempt
allowance is exhausted. Do not launch the real generative runtime, send a
generation request, restart the old campaign, buy credits, invoke a hosted model,
or create a new campaign/session/journal to bypass that boundary. Existing
captured responses may be inspected or replayed in explicitly offline tests.
Any future live experiment requires separate authorization.

No model/prompt tuning, command aliasing, output repair, automatic retries,
new tools, network deployment, migration, cognition, chain work or model build
is authorized. Runtime and historical profiles should remain unchanged.

## 2. Review basis and required inputs

The reviewer read publicly accessible S07 source and reports, including
`model_service.py`, `neoclaw_model.py` and the selected backend adapter, but did
not execute native suites, verify every hash or establish an immutable S07
publication commit. Moving public URLs are not a substitute for source identity.

Inspect at least:

- `docs/omega-adoption/mettaclaw-neoclaw/s07.md`
- `docs/omega-adoption/mettaclaw-neoclaw/s07-contract-decisions.md`
- `evidence/s07/{verification,source-state,live-summary}.json`
- `evidence/s07/{remaining-live-source,cpu-generation-authorization}.json`
- The source snapshots and individual results referenced by those manifests
- `integration/neoclaw/model-sources.json`
- `fusion/{model_contracts,model_service,model_transport,neoclaw_model}.py`
- `fusion/neoclaw_model_disclosure.py`
- `fusion/adapters/{ollama_completion,neoclaw_model_text}.py`
- `integration/neoclaw/{model_run,test_model_loop,model_composition}.py`
- The current mapping, coverage, remote-placement, interfaces and runbook
- The supplied `codex_neoclaw_s07_model_completion_adoption.md`

Do not substitute prior native Hive integration for MeTTaClaw integration, or
historical chain evidence for a current S07 chain run.

## 3. Reconcile the final source without relabelling historical runs

Record HEAD, branch, worktree and the exact S07 changed-file set. Compare the
current runtime files with the appropriate versioned test/live manifests.
For each difference classify:

1. Runtime behavior, request/response schema, authority or profile change.
2. Reproduction input or runtime-lock/configuration change.
3. Report/evidence-only addition.

The verification manifest lists `integration/neoclaw/model-sources.json` as
changed after the final runs. Inspect the actual difference. Because runtime
locks can be consumed by executable source validation, do not assume every
JSON change is documentation-only. Explain how the final bytes relate to the
recorded running executable, model and mapped-library observations.

Build a compact source-to-test map. A method passed on an earlier source version
is historical evidence for that version until the relevant final-source
relationship is established. Do not pretend that all 149 methods ran together
on one clean commit.

Use static checks and appropriately isolated recorded-response tests for any
necessary final verification. Inspect test entrypoints before running them;
some operator recipes start real services or generate text. Ensure offline
checks cannot reach the model endpoint. Do not rerun the full native stack merely
to obtain a cosmetic new total.

If a meaningful final-source difference cannot be validated without another
real generation, record the precise unverified relationship. Do not spend an
unauthorized call or replace live evidence with a fixture pass.

Preserve the two historical model profiles, original failed occurrence, selected
five-minute fresh-occurrence behavior, model options, tool deadlines and exhausted
generation counts. Do not reset identities or rewrite past timestamps.

Prepare an explicit commit-ready change list and validated source manifest.
Commit or push only if current workspace/user instructions separately authorize
those actions. Do not use blanket staging to include unrelated work, credentials,
model assets or private source. Record a later publication commit as a publication,
not as the commit on which historical working-tree tests ran.

## 4. Close the execution accounting at the correct units

Derive the following from individual records, not merely the report totals:

| Unit | Reported S07 outcome to reconcile |
|---|---|
| Authorized generation reservations | 12 spent; zero remaining |
| Durably captured model responses | 10 |
| Earlier uncaptured attempts | 2; retain timeout/validation distinctions |
| Authorized command batches | 8 |
| Rejected captured command batches | 2 |
| Actual native deductions | 5 |
| Approved peer-observed replies | 3 |
| Complete two-call workflows | 3 |
| Real native post-capture SIGKILL recoveries | 2; zero regeneration for the recovered call |
| Distinct methods with passing evidence | 149: 30 S07 plus 119 selected historical methods |

The counts overlap by design. A captured response, admitted batch, tool execution,
complete workflow and recovery trial are not interchangeable denominators.

Preserve the placement matrix:

- Local model / local mailbox: exercised; no complete positive reply in the
  retained campaign. Keep its unsupported-reply outcome visible.
- HTTPS model / local mailbox: complete workflow and capture recovery observed.
- HTTPS model / HTTPS mailbox: complete workflow observed; a separate recovery
  trial later rejected a new reply.
- Local model / HTTPS mailbox: complete workflow observed.

Use the two cases with the same HTTPS mailbox to explain the successful
local-versus-HTTPS model-placement comparison. Do not claim a successful
end-to-end outcome in all four combinations.

Separate the real application SIGKILLs from provider-side fault cases using a
recorded backend. A subsequent rejected new response does not invalidate an
earlier successful captured-result recovery; neither should that recovery
convert the later rejection into a successful workflow.

Do not call the unsupported commands compatibility aliases and accept them
retroactively. Do not repair raw model text or erase unsuccessful sessions.
The original rejected API payload was not retained: preserve any explanation
of its exact failing field as an inference, not independently reconstructed fact.

## 5. Report cost and quality without overclaiming

The live ledger records a range and median for total captured backend durations.
Inspect the nested duration fields and label total, prompt evaluation, output
generation, load and application/channel time separately. Do not label a total
including prompt evaluation as output-decoding time.

Captured usage excludes the two uncaptured attempts. Unknown usage stays unknown.
Do not invent a monetary price, exactly-once billing, complete token total or
production throughput result. These are small synthetic trials on a selected
local CPU environment with versioned changes, not a fixed-condition reliability
or model-quality benchmark.

Keep these two conclusions distinct:

- Contract/authorization conformance: unsupported proposals were refused.
- Task completion: those refused proposals did not deliver the intended reply.

The evidence supports a working bounded integration. It does not establish
reliable unrestricted command generation or general autonomous operation.

## 6. Refresh functional coverage, not the historical denominator

Produce one current matrix linking:

`native boundary → module/profile → authoritative owner → local evidence
→ HTTPS evidence → native-loop evidence → real-model evidence
→ remaining fixture/restriction → source/run`

Retain the historical fifteen-family reference inventory and 105-row mapping.
The existing ledger has eight operation-adoption entries covering nine native
user commands, with X01 ModelInference and X02 Embedding recorded as explicit
extensions. Do not add internal calls, profiles, transports and user commands
together as one functionality percentage.

Separate these questions:

1. Does a bounded provider implement the reference interface?
2. Does a native Omega consumer actually use it?
3. Can that consumer change placement through composition?
4. Has this exact composition run with a real model and channel?
5. Is it adequate for the intended workload?

Passing one question does not automatically pass the others. In particular,
S04/S05 local cognition, S03 memory adoption and S07 live generation have
independent evidence; do not join them into an unexecuted live-memory workflow.

The positive S07 promoted set was empty. Its real task used S01 and an approved
send, not model-directed remember/query/support/promote over populated memory.
Record that as a functional-representativeness gap, not an unreported S07 failure.

Reconcile original roadmap labels with delivered scope. The historical S08
candidate denotes Embedding; query-time and append-memory encoding already have
bounded X02 adoption through S03.1/S03.2. Do not automatically build another
Embedding module because S07 has finished.

## 7. Specify one next workload, without executing or implementing it

Proposed next evaluation: **retrieval-grounded native interaction with a real
model and real channel using existing adopted memory interfaces**.

Write a bounded definition of ready, based on the current actual contracts:

- Use a fresh synthetic memory created through an adopted path. A useful answer
  should depend on retrieved content, not an expected answer secretly supplied in
  the model prompt or harness.
- Specify the exact selected memory/query and reply operations, existing profile
  compatibility, accepted argument grammar and current authority.
- Use nonempty, explicitly disclosure-approved synthetic context only where its
  inclusion is part of the experiment; do not relabel private S04/S05 data.
- Identify whether the existing S07 prompt/disclosure/command allowlists can
  express the workflow. Necessary extensions are proposed work, not authorized
  edits in this closeout.
- Keep original/adapted contract checks distinct from live model usefulness.
  A recorded command can validate plumbing but cannot establish live selection.
- Define what would count as correctly retrieved content, appropriate refusal,
  stale-view handling, command rejection and actual peer observation.
- Do not silently weaken S06's exact-body approval into unrestricted generated
  output publication. Explicitly specify any needed output-policy decision.
- State finite proposed calls/tokens/deadlines separately from effective
  authorization. Effective additional live-call authorization remains ZERO.
- Define a stopping rule that records every attempt. No retry-until-green,
  prompt tuning within the measured run, response rewriting or invented claims
  of model reliability.

This is preferable to immediately adding perception, arbitrary shell, another
numerical rule or a second model solely to increase the module count.
Do not implement a ToolDescriptor service, general parser redesign, planner,
memory migration or production model server in this task.

## 8. Minimal deliverables and gates

Reuse the existing documentation structure. Add one closeout entry point and
only necessary ledger/runbook amendments. Preserve historical reports verbatim
apart from clearly separate corrections/addenda.

| Gate | Required evidence |
|---|---|
| SOURCE_CLOSURE | Final source hashes, versioned test relationships and every post-test difference explained |
| CAMPAIGN_ACCOUNTING | All 12 attempts, 10 captures, command outcomes and recoveries reconciled with zero calls left |
| EVIDENCE_UNITS | Method/run/scenario/workflow counts and real/fixture distinctions remain separate |
| COVERAGE_CURRENT | Native-adoption and placement matrix with current limits; historical denominator preserved |
| NEXT_WORKLOAD_READY | One unexecuted, evidence-based memory workload definition with explicit pending decisions |
| NO_NEW_GENERATION | Zero live model invocations, no runtime restart and no spent-budget or profile alteration |

State unresolved facts instead of manufacturing a pass. If the S07 tree or
source snapshots are unavailable, report that exact prerequisite; do not
reimplement S07 from its narrative.

Finish with:
- actual source/worktree or separately authorized publication state;
- static/offline checks actually executed and their source identity;
- remaining reproducibility and adequacy limitations;
- `ADDITIONAL_LIVE_GENERATIONS=0`;
- `READY_FOR_REVIEW` when the supported closeout gates pass.

Then stop. A review packet is not approval for a new generation campaign or
full Omega deployment.

## Source locations used for the review

These moving URLs locate the records; the manifests, not the URLs, identify
the reported tested bytes.

```text
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/master/docs/omega-adoption/mettaclaw-neoclaw/s07.md
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/master/docs/omega-adoption/mettaclaw-neoclaw/s07-contract-decisions.md
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/master/evidence/s07/verification.json
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/master/evidence/s07/live-summary.json
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/master/evidence/s07/source-state.json
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/master/fusion/model_service.py
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/master/fusion/neoclaw_model.py
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/master/docs/omega-adoption/mettaclaw-neoclaw/coverage.json
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/master/docs/omega-adoption/mettaclaw-neoclaw/remote-placement.md
```
