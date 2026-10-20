# Retrieval-grounded native workload preparation

**READY_FOR_LIVE_AUTHORIZATION** — all ten preparation gates pass. The gate/result ledger is
[`evidence/retrieval-preparation/verification.json`](../../../evidence/retrieval-preparation/verification.json).
All model responses in this preparation are authored fixtures. **Additional live
text generations: 0. LIVE_MEMORY_WORKFLOW=NOT_RUN.** No real text-generation
runtime is started, contacted, warmed or loaded by this task.

## Source and scope

Work started on `master` at `367c9b583eb85d6cf99ca93827c9f40b9c681bc6`, the
published closeout directly after S07 `4981788b4d8069a2b2264e65197f9886b74f1f5f`.
The 16 non-self closeout hashes and exact 17-file publication delta were checked
before editing. Only the supplied preparation brief was initially untracked.
[`baseline.json`](../../../evidence/retrieval-preparation/baseline.json) records
that reconciliation. Historical evidence is retained, including the old 12/10
attempt/capture accounting and unresolved API, usage, context-export and channel
failure facts. This preparation does not repair or reinterpret those facts.

Exact runtime inputs, installed binary hashes and source-checkout status are in
[`inputs.json`](../../../evidence/retrieval-preparation/inputs.json). Six repository
identities/statuses and fourteen installed runtime/lock/binary hashes were
[checked again unchanged](../../../evidence/retrieval-preparation/inputs-final-check.json).
The [delivery manifest](../../../evidence/retrieval-preparation/final-source.json)
records the changed files and final bytes; all four final runs match its 214-file
frozen executable/test source set. These are qualified working-tree runs on the
starting commit, not retroactively labelled clean-commit executions. Existing
source-checked installations were reused; no independent cold rebuild was run.

| Input | Revision |
|---|---|
| MeTTaClaw neoclaw | `2af37c3fec18613de54ca42fde2382a9087d4524` |
| PeTTa | `fea83178af3722666d2948d074591d10a3134f56` |
| SWI-Prolog | `e58621a91ab7dd530e1e8185ed518f63d851c414` |
| DeTTa / secured-contract-spaces | `272888f264dd2dde18b574cabb53c266b0dac2ec` |
| Chroma helper | `218484875d5d1bfb217a9a03d3983dc1ed9d406c` |
| E5-large-v2 | `f169b11e22de13617baa190a028a32f3493550b6` |
| ngIRCd 28 | `6ae13bf89e934d167f6ead8bb9ee39f57a0935c0` |

Chroma remains 1.5.5. The native source checkout has an untracked Python bytecode
cache; selected source bytes match the pins. Runtime source files, model weights,
preprocessing, normalization and numerical profiles were not edited.

## Implemented boundary

The new application selection is `controlled-native-loop/10`, with disclosure
`synthetic-retrieval-query-send/1`. It composes the existing interfaces: native
remember setup, Embedding, Search, AtomStorage, local belief/priority enrichment,
ModelInference and durable Messaging. No module, native command or numerical
profile is newly adopted. Historical `/9` and both S07 model profiles stay intact.
The [decision record](retrieval-preparation-decisions.md) explains the contract,
privacy, authority and recovery choices.

The real setup invokes three native remembers against an empty enrollment source.
Their separate storage, publication, readiness and native-success observations
are retained. A fresh measured journal selects the ready immutable view. Its
first input contains neither the stored location nor setup commands/results,
flat history or promoted memories. Setup write authority is revoked before the
measured session starts.

The first authored completion proposes the exact native query. Real E5, Search
and verified AtomStorage hydration supply the candidates; native local enrichment
and rendering remain in use. A trusted receipt binds the committed projection,
full retained view, occurrence and explicit component consent before disclosure.
Current model permission is checked at the sender through the same read-only
operator Policy and independently at the owner. The second prompt contains the
actual saved projection; the second authored completion proposes a send. The
finite output policy approves every harmless candidate location equally. The
evaluator independently scores factual correctness and actual peer observation.

The combined workflow fixes retrieval/encoding and private C1/C2/Attention locally,
and fixes the mailbox to authenticated same-host HTTPS. Only model placement
changes. Separate original/local/HTTPS native append/query checks use the same
new generated facts, real E5/Chroma/DeTTa and an E5-free HTTPS caller. They do not
claim remote private cognition, multi-host operation or default full Omega.

## Evidence distinctions and limits

- **Real:** source-checked native dispatch/parser/remember/query/getContext;
  pinned E5; Chroma; DeTTa; isolated ngIRCd; independent socket peer;
  authenticated, certificate-checked same-host HTTPS; OS process kills.
- **Fixtures:** authored model command responses; controlled empty flat history;
  creation/enrichment clocks; explicit fault injections. Owner contract unit tests
  additionally use their labelled in-memory/file fixtures. The selected historical
  Search metric test uses deterministic vectors; S02 reuses recorded external-search
  responses; S07 regressions use recorded responses or stop before model submission.
  Authored completion values are not measurements of generative-model competence.
- **Unsupported:** private S04/S05 state with remotely placed memory under the
  existing profiles. These checks remain closed rather than being weakened.
- **Unrun:** live retrieval-grounded model usefulness/workflows, current real
  generative-runtime readiness, live external search, cold runtime rebuild,
  full-default Omega, multi-host placement and chain work.

Known windows remain: IRC input before durable bridge capture may be lost;
external sends have one reserved socket attempt and may remain unknown after
interruption. Socket return and recipient observation are distinct. No automatic
resend, deadline extension, reservation refund or populated-state migration is
introduced. Trusted-local consent/policy files are not a cross-host signature
scheme; a malicious host administrator is outside this test's guarantee.

A wrong but permitted reply and an unnecessary refusal must remain task failures,
even when admission, sending and peer observation all work. A valid inconclusive
retrieval is different from an unavailable index or failed hydration. The latter
stop before authorizing the answer stage.

## Reproduction and disabled live plan

Use the existing recipes in `scripts/build_s01.py`,
`integration/neoclaw/memory_build.py`, `integration/neoclaw/embedding_caller_build.py`,
`scripts/build_detta.py`, and the S06 ngIRCd recipe with the pinned inputs above. Preparation used the already
installed manifests listed in `inputs.json`, not a new clean-cache build.
Run only through the checked isolation wrapper:

```sh
RETRIEVAL_PREPARATION_EVIDENCE=artifacts/retrieval-preparation/reproduction \
artifacts/s03/venv/bin/python -m integration.neoclaw.preparation_guard -- \
artifacts/s03/venv/bin/python -m unittest -v \
integration.neoclaw.test_retrieval_preparation
```

The wrapper first proves host-network separation against its own sentinel and
masks generative binaries/assets and service managers. The fixture backend is
selected explicitly before evaluation. Its evaluator/corpus/journal denial probes
run inside the provider sandbox. It cannot fall back to a generative backend.

The [disabled live plan](../../../evidence/retrieval-preparation/live-plan.disabled.json)
proposes two sessions and four calls total, with 6,000 output tokens/call and the
existing 300-second input/model and 30-second tool/context bounds. It contains
no authorization and no executable live entrypoint. A new user authorization
must bind a frozen plan before any real generation.

## What changed and why

`fusion/neoclaw_retrieval_disclosure.py` implements the small selected validator,
component consent, sender preflight, retained-view receipt and stage admission.
The existing model service/transport/adoption and application/append composition
select it explicitly. Their acceptance, reservation, capture, application receipt
and output commits remain independently owned. No model, memory, evidence,
priority, messaging or numerical contract was replaced.

The native startup overlays select `/10` and its prompt/skill list against the
pinned source. `loop_bridge.py` gains explicit test-only fixture selection and
slot-specific fault injection. `promotion_composition.py` forwards setup inputs
through the existing append composition. `preparation_guard.py`,
`retrieval_fixture.py`, `retrieval_preparation.py` and
`test_retrieval_preparation.py` provide the isolated qualification entrypoint;
two new contract test files exercise disclosure and receipt edges. The source
manifest enumerates every changed file; the coverage update is additive and
preserves all historical counters.

The existing parser still rejects malformed commands; the implementation does
not repair a proposal. A missing selected generation or payload fails retrieval.
The valid target-absent corpus instead produces actual inconclusive native
feedback. Policy permits wrong candidate bodies, which are sent and observed but
score **task FAIL**. An allowed insufficient-information response also fails when
the target is present. An interrupted socket reservation remains unknown and is
not resent.

## Corrected preparation failures

Earlier attempts are retained with their own source manifests and logs. They are
not clean-commit results and do not become passes retroactively. The interrupted
second-run log retains its original trailing progress-line space; the staged
whitespace check passes with that exact raw-log exception:


- The first guard preflight tried to inspect an inaccessible root-owned model
  directory; it stopped before tests. The guard now masks the actual authorized
  user's runtime assets and proves host-network denial. No complete source freeze
  was taken for that initial preflight.
- Initial prompt qualification exposed the exact native template's trailing
  placeholder; the receipt validation was corrected to match native bytes.
- The first query exposed native apostrophe placeholder conversion. Binding now
  preserves that original one-time transform, rather than changing the renderer.
- A contract-test authoring syntax error prevented test discovery; its zero-test
  failure is recorded before the corrected runs.
- The first full run was deliberately interrupted after inspection found that
  revocation also needed checking before sending a prompt-bearing HTTPS request.
  The new sender preflight reads the owner's current Policy before transport.
- The second full run exposed a pending-query restart restriction and a test
  failpoint installed after the provider had started. Initial-history validation
  now permits only its own unfinished first query. The provider test starts with
  the intended fault hook active. The earlier run remains interrupted/failed.

Historical S07 failures and unknowns remain in the closeout; none of these new
preparation corrections resolves missing historical API payloads, unavailable
usage, reduced public context exports or the old channel-failure cause.

## Executed preparation evidence

The final integration run passed all **10 methods** in 1,479.114 seconds. Nine
methods cover **22 combined workflow scenarios**; the remaining method compares
three native remember/query paths. These counts do not describe 22 live-model
workflows. The final contract/owner/transport run passed **73 methods** in 5.673
seconds, including **17 new disclosure/receipt methods**. Two selected historical
S01/S02 native-loop methods passed in 29.350 seconds. The final **14-method** native regression run passed in **541.558 seconds**.
Across these four final runs there are **99 distinct methods: 27 new and 72
existing methods reexecuted**. Earlier repeated executions are kept separate in the
[run ledger](../../../evidence/retrieval-preparation/run-ledger.json); the
[test map](../../../evidence/retrieval-preparation/test-map.json) names every
qualified method. The historical 149-method S07 count and overlapping 20-method
closeout recheck are unchanged.

[Scenario exports](../../../evidence/retrieval-preparation/scenarios.json) retain
complete generated context/read views, actual query vectors/candidates/payloads,
raw and transformed prompts, receipts, parsed proposals, admission, outbound
acceptance/socket outcomes and peer observations where produced. The
[export manifest](../../../evidence/retrieval-preparation/export.json) hashes the
unmodified exports. Evaluator files, credentials, TLS keys, owner databases and
unrelated stores are not published. Database audit fields are test observations;
the application obtains retrieval/recovery data through its existing owners.

Recovery kills were exercised after query occurrence binding, vector capture,
candidate capture, native result capture, next-prompt binding, application model
capture, second-turn outbound occurrence binding, provider response capture, and
socket reservation. The provider-capture case kills both the fixture owner and
caller. Successful two-stage cases have exactly two authored fixture evaluations;
recovery reuses captured artifacts without refunding reservations. Original
occurrence IDs, views, intents and deadlines remain equal across each restart.

The [measurement record](../../../evidence/retrieval-preparation/measurements.json)
contains these two healthy observations:

| Model fixture placement | Native setup process | Measured native process | Peak RSS | Fixture evaluations |
|---|---:|---:|---:|---:|
| Local | 23.516 s | 19.39 s | 1,635,692 KiB | 2 |
| Authenticated same-host HTTPS | 23.710 s | 20.09 s | 1,635,664 KiB | 2 |

Both first prompts contain 1,077 characters; their following prompts contain
2,035, including the actual captured projection. Each model occurrence uses four
of its eight available RPC reservations and one owner evaluation reservation.
These observations include process startup, exclude parts of test orchestration,
and are not throughput, ANN-quality or model-competence benchmarks. The small
three-record corpus returns the target and distractors under unchanged native
query selection. No reliability percentage is inferred.


## Preparation gates and stop state

| Gate | Result and observed boundary |
|---|---|
| BASELINE | PASS — published closeout reconciled; exact inputs, changed bytes and impact map retained |
| CONTRACT_SELECTION | PASS — explicit `/10` and closed query/send disclosure; historical `/9` preserved |
| ZERO_LIVE | PASS — deny mechanism tested; every completion explicitly fixture-backed |
| SETUP_RETRIEVAL | PASS — native remembers, real E5/Chroma/DeTTa, original/local/HTTPS parity and honest unavailable-data failures |
| CONTEXT_BINDING | PASS — actual captured projection and full retained view in the next prompt, with current authority and exact consent |
| NO_ANSWER_ORACLE | PASS — no initial answer leak; wrong permitted reply and unnecessary refusal score task FAIL |
| CHANNEL_PLACEMENT | PASS — real IRC/peer with fixed mailbox/retrieval/encoder placement and local/HTTPS model fixtures |
| RECOVERY | PASS — real process kills preserve captures, identities, deadlines and spent reservations; no uncertain-send retry |
| COMPATIBILITY | PASS — selected S01–S07 regressions; historical profiles, counters and evidence retained |
| LIVE_PLAN_DISABLED | PASS — future plan has zero effective allowance, no authorization and no executable entrypoint |

There are no remaining preparation blockers. Future live execution requires new
explicit authorization bound to a frozen plan; current generative-runtime
availability and model usefulness remain untested. Full repository regression,
cold rebuild, remote private cognition, default Omega and multi-host execution
are outside this qualification. The complete [gate ledger](../../../evidence/retrieval-preparation/verification.json)
keeps real providers, fixtures, corrected failures, unsupported combinations and
unrun work separate.

```text
PREPARATION_STATUS=READY_FOR_LIVE_AUTHORIZATION
ADDITIONAL_LIVE_GENERATIONS=0
LIVE_MEMORY_WORKFLOW=NOT_RUN
```
