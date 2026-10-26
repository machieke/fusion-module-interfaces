# Retrieval runner preparation — 2026-10-26

**RUNNER_PREPARATION=READY; CAMPAIGN_FREEZE=COMPLETE.** No generative runtime was contacted, started or loaded. No real generation was reserved or performed. Real-model usefulness remains untested.

The approval-ready campaign is **`retrieval-grounded-20261026-02`**. Its canonical manifest SHA-256 is:

```text
0b75644c3b0e198fc606bb3b781087a2048a40f21b67b36bd7a5a1000465adb1
```

The machine-local manifest is `artifacts/retrieval-campaigns/retrieval-grounded-20261026-02/manifest.json`. The [published review copy](../../../evidence/retrieval-runner/campaign/manifest.json), [external digest](../../../evidence/retrieval-runner/campaign/manifest.sha256), [unissued approval request](../../../evidence/retrieval-runner/campaign/approval-request.UNISSUED.json), [empty ledger](../../../evidence/retrieval-runner/campaign/initial-ledger.json) and [setup evidence](../../../evidence/retrieval-runner/campaign/setup-summary.json) are versioned. The original owner journals, ready Chroma view, authoritative records, credentials and TLS keys remain in the retained machine-local artifact directory. No populated database was copied or migrated.

## Source identity

The starting checkout was exactly `9816873d5bb605c9c03be5f65baef7410c8cce0f`; initially only the supplied task brief was untracked. Twelve relevant implementation files were reconciled against the preceding preparation source set. The old 102/214-file review was preserved rather than repeated.

The [source record](../../../evidence/retrieval-runner/source-state.json), [baseline](../../../evidence/retrieval-runner/baseline.json), unit source manifest and each native report identify the actual unpublished working-tree bytes. Publication is not a retroactive clean-commit test identity. The final manifest binds **189 source files and 212 configuration/artifact inputs**, including the actual shared DeTTa, ngIRCd and SWI executables and selected runtime/helper manifests.

| Source | Observed identity |
|---|---|
| Native MeTTaClaw | `2af37c3fec18613de54ca42fde2382a9087d4524`; no tracked changes; untracked `src/__pycache__/` observed |
| PeTTa | `fea83178af3722666d2948d074591d10a3134f56`; clean |
| SWI source | `e58621a91ab7dd530e1e8185ed518f63d851c414`; clean; executable separately bound |
| Chroma helper | `218484875d5d1bfb217a9a03d3983dc1ed9d406c`; clean |
| E5 / Chroma | E5 `f169b11e22de13617baa190a028a32f3493550b6`; Chroma `1.5.5`; original native encoding and retained-view profiles |
| Generative candidate | Existing Ollama `0.40.0+mlx.cpu.1`, `qwen3.8:27b`, `neoclaw-ollama-qwen38-text/2`; unchanged model digest and options |

[Offline inspection](../../../evidence/retrieval-runner/runtime-offline.json) verified thirteen runtime/model metadata or executable/library hashes. The two large model/projector blobs were readable but not rehashed in this assignment. Their required hashes are frozen and must pass full offline verification before activation. Runtime availability is **NOT_CHECKED**. Historical endpoint/usage observations embedded in the old source lock remain historical; its twelve-call allowance is exhausted.

## Implementation and decisions

- `retrieval_runner.py` supplies separate `prepare`, `qualify`, `inspect` and `execute` modes. The old preparation entrypoint remains generation-disabled.
- `retrieval_campaign.py` validates separate user approval, canonical external hashing, source/configuration drift and four fixed UUID5 slots. Test-only authority cannot activate a live campaign. The ledger records attempts; existing ModelInference owners retain reservation/result authority. Claims are locked, fsynced and monotonic across projection reset or concurrent reopen.
- `retrieval_backend.py` selects either the explicitly recorded backend or the existing real Ollama adapter after approval. There is no fallback or model substitution. `retrieval_freeze.py` composes fresh persistent setup and two measured sessions, without creating their journals or starting their occurrence deadlines.
- Application, ModelInference and Bridge gained read-only observations of their own committed state. The runner reads those boundaries instead of foreign-owner SQL. Observations never supply a runtime answer.
- The runner follows actual command admission and accepted output, matches the exact sender/channel/body at the independent IRC peer, then evaluates correctness. It never waits for a preferred answer constant. Candidate bodies are equally sendable; correctness is a separate check.
- Model deadlines remain 300,000 ms; tool/context limits remain 30,000 ms; model RPC budget remains eight; each owner permits two calls. The persistent **setup observer** is 120 seconds for three native writes and the concluding turn. This changed only the observer that previously expired at 45 seconds; it did not extend an accepted command or generation deadline.
- Current authority is checked on replay. Captured responses and query results retain their original identity/view/deadline. Unknown reservations stay spent. A bridge's unknown socket outcome remains distinct from peer observation and never triggers automatic resend.

Model placement changes through composition only. Both sessions keep mailbox HTTPS and encoder/retrieval/cognition local. The common native consumer, original parser and whole-batch authorization are unchanged. Recorded provider processes/fixture actors mask the current corpus, evaluator and caller state; the prompt receives the actual committed query capture only through existing consent/receipt validation. No new family, native operation, cognition, migration, multi-host placement or chain work was added.

## Executed qualification

**72 distinct test methods passed:** 65 focused unit/contract/control methods and seven native integration methods. Methods, repeated runs, scenarios and workflows are separate in the [machine-readable summary](../../../evidence/retrieval-runner/preparation-summary.json).

| Qualification | Executed result |
|---|---|
| Denial guard, before integration | PASS: owned host sentinel unreachable; generative launch/assets masked; no actual model endpoint probe |
| `unit-03.log` | 65 PASS: approval/drift refusal, monotonic claims, concurrent reopen, current authority, disclosure, original model/channel contracts and owner recovery |
| `native-03.log` | Seven PASS; 14 local/HTTPS session scenarios: actual bodies, command rejection, missing retrieval, revocation, observer expiry, caller/provider/bridge kills |
| `native-04.log` | One repeated method PASS; two more session scenarios qualify the final shared-executable binding addition |
| Final offline verification | PASS: no source/configuration/artifact drift after cleanup |
| Final production entrypoint without approval | Refused with `AWAITING_LIVE_AUTHORIZATION`, exit 2; counters/journals unchanged |

The only execution-source difference after the complete native suite was the added external byte bindings in `retrieval_freeze.py`; both placements were requalified after that change. The exact before/after hashes are recorded, and earlier reports were not relabelled as tests of the later tree.

The qualified native set comprises **eight method executions / sixteen session scenarios**, with **23 recorded-model reservations, 22 fixture captures, eight peer-observed two-turn workflows, six factually correct replies and two wrong-but-permitted replies correctly scored incorrect**. One reserved completion remained uncaptured after process loss. These are not live-model workflows.

Real E5 work in that qualification set: 24 captured native memory encodings, 11 captured query encodings and eight explicit corpus-preparation query encodings. Setup model responses and channel inputs were scripted; measured model responses were authored fixtures. The measured native loop/parser, remember/query, E5, Chroma, DeTTa, ngIRCd, separate socket peer and certificate-checked HTTPS were real. Creation/promotion clocks were explicit synthetic fixtures. Final campaign setup separately performed three native memory encodings and one corpus-preparation encoding; its native setup took about 22.5 seconds. These timings are not generative-model benchmarks.

Native recovery included two caller process kills (captured completion and captured query), one HTTPS provider kill after reservation, and two bridge kills after socket write. The existing unit tests also killed processes at four model-owner commit boundaries and at a campaign claim. Recovery retained original limits and captures; no additional backend evaluation or socket resend was used to repair an uncertain result.

Earlier failures remain available: `unit-01` exposed an incorrect new test assertion after deliberate manifest mutation; `qualification-01` exposed a masked-file PermissionError check; `qualification-02` hit the bounded setup observer; `native-02` exposed a test revocation that leaked into the following scenario. Their corrections and later passing results are separate. Campaign `…-01` was frozen but never activated, then superseded when shared executable bindings were added; its original digest and artifacts are retained under `superseded/` and its old source binding now refuses activation.

## Gate assessment

| Gate | Result and limit |
|---|---|
| BASELINE | PASS: exact requested checkout and focused reconciliation |
| RUNNER | PASS: runnable shared orchestration and actual admitted-output observation |
| ZERO_GENERATION | PASS: explicit denial guard; all real generation/contact/startup counters zero |
| AUTHORIZATION | PASS: separate authority required; negative guards and test-only positive path exercised |
| ACTUAL_DATAFLOW | PASS with recorded model: native storage/query and exact next-input binding |
| EVALUATION | PASS: wrong permitted output delivered and scored incorrect |
| RECOVERY_BUDGETS | PASS: owner commits, captured replay, spent unknown reservation, concurrent claim and no resend |
| PLACEMENT | PASS: same-host local/HTTPS recorded-model placement; fixed non-model placements |
| FREEZE | COMPLETE: immutable plan/digest, retained corpus/view, four unreserved slots, absent approval |
| COMPATIBILITY | PASS for impact-selected regressions; original profiles, math and acceptance/reservation code unchanged |

The impact-selected regressions cover ModelInference service/transport, retrieval disclosure/receipts and channel authorization/framing/budgets. Broader M1–M5 suites, default full Omega, live-model usefulness, multi-host and chain work were not run. The guarantees assume the existing trusted-local operator and persistent journals; this is not a host-rollback or production identity platform.

## Actual campaign and commands

The sessions are local `e4a391e8-14a2-4aa9-b4c6-0d5640d2e233` and HTTPS `655f80ce-7d5e-453f-94fc-bdb1fb26f15f`. Their two slots each are named in the manifest. No future second prompt has been fabricated. It must contain that session's actual captured query result. No absolute occurrence deadline exists yet.

[Entrypoint documentation](retrieval-live-runner.md) supplies all preparation/test commands and approval fields. The exact retained campaign inspection command is:

```sh
artifacts/s03/venv/bin/python -m integration.neoclaw.retrieval_runner inspect \
  --manifest artifacts/retrieval-campaigns/retrieval-grounded-20261026-02/manifest.json
```

Only after a new explicit user approval bound to the digest above and its execution window may the operator create the separate `approval.json` and use:

```sh
artifacts/s03/venv/bin/python -m integration.neoclaw.retrieval_runner execute \
  --manifest artifacts/retrieval-campaigns/retrieval-grounded-20261026-02/manifest.json \
  --approval artifacts/retrieval-campaigns/retrieval-grounded-20261026-02/approval.json \
  --evidence artifacts/retrieval-campaigns/retrieval-grounded-20261026-02/execution-report.json
```

The pinned isolated backend at loopback port 48173 must then be available. Its current availability was deliberately not checked. The runner does not launch, warm up or repair it. Missing approval blocks activation; it did not block implementation. Fixed ports, certificate validity, retained artifacts and the full required asset hashes remain activation prerequisites. There are no automatically substituted endpoints or replacement sessions.

The [changed-file list](../../../evidence/retrieval-runner/changed-files.txt) covers the runner/composition hooks, read-only owner observations, tests, task brief, documentation and evidence. Generated journals, credentials, keys and model assets are retained locally and excluded from Git.

```text
RUNNER_PREPARATION=READY
CAMPAIGN_FREEZE=COMPLETE
CAMPAIGN_ID=retrieval-grounded-20261026-02
CAMPAIGN_MANIFEST_SHA256=0b75644c3b0e198fc606bb3b781087a2048a40f21b67b36bd7a5a1000465adb1
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
