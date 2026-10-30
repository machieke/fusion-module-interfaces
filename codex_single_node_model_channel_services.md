# Codex handoff — single-node k3s: ModelInference and channel services

## 1. Objective and authority boundary

Continue the **completed single-node memory-service implementation**, not merely
its starting commit `369483360b51baf968ad41b19d6776ac66fe085f`. Reconcile the actual
checkout with `evidence/single-node-memory/{sources,changes,final-source-manifest}.json`
and the image/source reconciliation before editing. Record an available publication
commit, or the exact working-tree baseline when the changes are not yet committed.
Read applicable AGENTS.md, the current chart/runbooks, the S06/S07 and retrieval
workflow contracts, and the existing campaign machinery. Preserve unrelated work.

**Proposed next increment:** deploy the existing ModelInference owner and durable
IRC bridge in independently managed workloads on the same single-node k3s cluster.
Connect them to the already separated memory, storage and Messaging services.
Qualify a complete retrieval-to-reply workflow using explicitly recorded/authored
model responses, with real native Omega, E5, Chroma, DeTTa, ngIRCd and pod-to-pod
module HTTPS. This is a deployment/composition increment, not another module family.

The required preparation workflow is:

    separate native remember setup -> ready synthetic memory view
    real IRC question -> durable channel input -> ModelInference fixture
    -> native query -> actual memory result -> bound next model prompt
    -> ModelInference fixture -> admitted native send -> real peer observation

**ADDITIONAL_LIVE_GENERATIONS=0.** Do not start/contact a real text-generation
runtime, load its model, perform generation-bearing probes, reserve a real slot,
or reuse any historical live campaign. Real E5 encoding is permitted and required.
Offline inspection, hashing, image construction and declared dependency preparation
are permitted; build steps must not launch a generative runtime as a smoke test.

Missing live authorization does **not** block implementation or recorded-response
qualification. It blocks real-runtime activity and generation. Deliver executable
preparation, not another static report saying authorization is absent.

Keep single-node deployment. No multi-node, HA, production identity infrastructure,
private-memory export, migration, new cognition, general tool authority, full-default
Omega, ASI:chain work or public IRC connection. Do not adopt another command merely
to complete a test. Preserve the retained `omega-demo`; use a new explicitly selected
task-owned namespace and release with fresh synthetic state.

## 2. Evidence baseline and its limits

This handoff follows a review of accessible source and recorded reports, including
moving `master` paths. The reviewer did **not** run the cluster, inspect its current
state, run the suites, inspect the image archive, or reconcile every recorded hash.
Verify source findings locally. A published document describing a working tree is
not proof that the parent commit contains that implementation.

The memory-service packet records:

- 21 distinct final cluster scenarios in 24 executions: 21 passing executions and
  three unsuccessful executions retained with corrections/rechecks.
- 31 passing selected contract/chart methods; 46 of 47 selected owner regressions
  passing, with one reproducible baseline error.
- 42 historical native methods with two initial ten-second observer expirations;
  unchanged isolated rechecks passed. Source epochs differ and remain documented.
- Pod replacements, real memory writes/reads, authenticated source access, captured
  vectors/results and retained read views. Expired/exhausted cases pass safety
  assertions, not successful-workflow assertions.
- Independent prior S01 regression evidence. No generation, live IRC, ModelInference
  deployment or chain execution in that increment.

The baseline error is
`tests.test_m5_boundaries.Boundaries.test_lookup_has_no_cognitive_runtime_dependency_or_mutation`:
`isinstance(provider, AtomStorage)` refuses the fixture/protocol combination under
Python 3.12. The packet reproduces it at the unchanged parent. Do not mark it PASS,
suppress it or remove the ownership check to manufacture a green baseline. Record
its exact impact on this increment. A small separately documented fixture/protocol
compatibility correction is allowed when necessary and justified by source/tests;
preserve the hostile-port check and historical failure. A new required gate cannot
inherit a waiver merely because a superficially related failure is old.

The memory qualification also exposed genuine thirty-second deadline exhaustion
under concurrent load. Sequence resource-heavy tests; distinguish readiness,
observer timeouts and accepted-operation deadlines. Do not extend an accepted
deadline or treat an isolated recheck as erasing the original failure.

Use an impact-selected baseline/final suite, not an automatic full historical audit.
Preserve test-method, scenario, execution and recheck counts separately. Source and
image hashes must describe the bytes actually executed; explain later changes.

## 3. Inspect and reuse these seams

| Source | Concrete issue or reuse point to verify |
|---|---|
| `docs/deployment/single-node-memory.md`, its evidence directory | Current six-role chart, uncommitted/source relationship, runtime pins, known failures and cleanup |
| `deploy/helm/omega-fusion/`, `integration/single_node/` | Per-role images/configuration, Services, StatefulSets, PVC locks/seals, lifecycle and service-DNS profile |
| `fusion/memory_services.py` | Independent storage, Search and encoder routes; scoped read-only source delegation |
| `fusion/model_transport.py` | Existing `/s07-model` route; current network constructor does not select the new service-DNS composition |
| `fusion/model_service.py` | Separate durable acceptance, reservation, response capture and readback; single-writer model owner |
| `fusion/neoclaw_model.py` | Application-owned prompt, model occurrence, capture, parsing and whole-batch admission |
| `fusion/neoclaw_retrieval_disclosure.py` | Same-host policy-file preflight and receipt_root reads; these cannot be cross-pod contracts |
| `fusion/channel_transport.py`, `channel_service.py` | S06 currently routes storage/mailbox through one endpoint and constructs a combined local composition |
| `fusion/irc_bridge.py`, `adapters/irc_socket.py` | Durable ingress/egress and one-attempt socket outcome; existing loopback-only deployment assumptions |
| `integration/neoclaw/retrieval_{preparation,runner,backend,campaign,freeze}.py` | Existing qualified workload, real-versus-recorded backend selection, evaluation and exhausted campaign controls |
| `integration/neoclaw/channel_composition.py` | Existing real ngIRCd/server/peer recipe and host-side process orchestration to replace in this deployment |
| S06/S07, retrieval preparation, runner and live execution evidence | Historical behavior and limits; do not relabel the successful outside-k3s campaign as current deployment evidence |

Reuse existing numerical/model/runtime pins. A verified container-path relocation
is acceptable; silently changing the model, response conversion, parser, E5,
Chroma, DeTTa or native runtime is not. Check dependency platform compatibility
before promising an executable generative-runtime image. If it is unavailable,
record that future-live packaging gap without substituting another model.

## 4. Workload boundaries

Extend the existing chart and values/schema. Do not create another deployment
framework or one pod per interface simply to inflate the inventory.

| Workload | Required responsibility |
|---|---|
| `omega-agent` | Actual native loop, accepted inputs/commands, captured query/prompt/result state and result-to-context handoff |
| `fusion-storage` | Authoritative memory records and explicitly scoped channel payloads through declared ports |
| `fusion-search` | Existing Chroma projection/publication, consuming storage/feed HTTPS ports |
| `fusion-embedding` | Existing pinned E5 encoding and durable evaluation accounting |
| `fusion-messaging` | Existing mailbox acceptance, poll, acknowledgment and deduplication state |
| `fusion-model` (new role) | ModelInference API and its own durable journal; selected recorded backend during qualification |
| `fusion-channel-bridge` (new role) | Actual IRC connection, durable capture/relay and bounded outbound socket attempts |
| Isolated test IRC server | Real pinned ngIRCd, reachable only through the intended test network placement |
| Independent peer Job/workload | Sends questions and observes actual received frames; never supplies model answers or query payloads |

Preserve the existing execution workload and S01 values as a separate supported
path. It need not run for every synchronous query or generation request.

Each stateful owner keeps its own PVC, configuration, credentials, seal and writer
lock. Do not mount another owner's PVC, developer workspace, model assets or mutable
receipt directory. Separate profiles may use separately sealed stores within their
own storage workload; do not force old AtomOwner/FeedAtomOwner journals to share a
schema or migrate them to accommodate channel payloads.

For future live deployment, the model runtime may be a container in the model pod,
with its backend HTTP API bound to pod-local localhost and only the authenticated
ModelInference API exposed as a Service. During THIS qualification, the real runtime
container is absent/disabled and not started. The recorded provider is explicit,
not a fallback after live initialization fails. Do not claim real-runtime readiness
from success of its recorded counterpart.

## 5. Separate channel storage from Messaging

The existing `ChannelService` has useful validation but constructs colocated owners.
Keep its role/scope/route/body/descriptor/idempotency checks while injecting the
appropriate declared remote dependencies. Do not deploy the combined host harness
as a new all-in-one service with extra copies of storage and Messaging.

Application and bridge clients route payload operations to storage and mailbox
operations to Messaging over independently selected authenticated HTTPS endpoints.
Messaging may validate a referenced channel payload through a narrowly authorized
storage read port. Bind the service principal and initiating actor explicitly;
a caller-supplied principal string or shared administrator credential is not authority.

Preserve these separate commits and observations:

    bridge socket event -> durable bridge capture -> immutable payload
    -> mailbox acceptance -> durable application input/processing assignment
    -> mailbox acknowledgment

Separate equal-text inputs remain separate events. Internal replay cannot mint a
new source event. A poll returning text is not sufficient to acknowledge delivery.
Bound queues and framing, test backpressure/drain and preserve source ordering.
Traffic before durable bridge capture or during disconnected IRC history remains
potentially lost; reconnect is a recorded discontinuity, not complete recovery of
all upstream messages.

Outbound intent, mailbox acceptance, bridge receipt, spent socket reservation,
socket-write outcome and independent peer receipt remain different observations.
No automatic resend after an ambiguous spent send. Kubernetes restart/reconnect,
Helm upgrade or re-created peer must not refund it. The peer must observe the actual
admitted body, sender and channel, not an evaluator constant. Test the healthy and
unknown-delivery paths separately.

Adapt IRC listener/address validation only under a named service-deployment selection.
Use ClusterIP/private test placement without public IRC, host networking, NodePort
or ingress. IRC is a native TCP hop unless explicitly configured otherwise; do not
label it HTTPS because the module APIs use HTTPS. Namespace separation alone is not
network isolation. Record any actually tested NetworkPolicy separately; do not claim
hostile-code isolation or production channel security.

## 6. Remove shared-file ModelInference disclosure

Two existing assumptions must change under an explicit new deployment/disclosure
selection: the caller reads `authority_policy` from the model owner's filesystem,
and `validate_receipt` reads the caller-issued JSON beneath `receipt_root`.
Do not reproduce this by mounting either directory into the other pod.

Keep the two authorities distinct:

1. The application decides what data it is permitted to disclose and verifies the
   exact actual query capture and retained view through its existing owner ports.
2. The model owner decides whether the authenticated caller may use the selected
   provider/profile and receive the corresponding captured result.

Use the smallest authenticated receipt/authorization exchange needed for the
existing trusted-application threat model. A metadata-only preflight must be possible
before raw prompt bytes are sent when provider permission is part of disclosure.
Recheck authority at effect and result-release boundaries; a preflight does not
promise that permission cannot be revoked between calls.

After local validation, transport a bounded disclosure receipt through a declared
trusted issuer context, either with the bound model request or through a narrow
owner-owned registration/read path. Record the selected design and its trust limits.
The receipt must bind caller, issuer, recipient, scope, session/model occurrence,
profile/descriptor, consent policy/version, exact raw/transformed prompt identity,
retained query occurrence/view/projection and original lifetime. It cannot authorize
another principal, prompt, view or generation. A hash or `approved=true` is not
permission; model-generated arguments cannot issue receipts.

The provider validates receipt binding and current issuer/caller authorization,
without accessing the corpus, evaluator, application journals or private metadata.
It trusts the specifically authorized application's verification of its capture;
do not describe that trust as a cryptographic proof that retrieval occurred.
Static non-secret policy distribution through ConfigMaps is permissible, but a
copied provider-policy file is not a substitute for the live provider's checks.

Preserve the existing narrow generated-data policy. No wildcard `COMMAND_RETURN`
acceptance, generic publication flag or private S04/S05 context. Fresh measured
sessions have empty setup history/promoted context. Keep the correct location out
of the first prompt; all approved answer candidates have equal egress eligibility.
Wrong-but-permitted replies must remain authorized and score incorrect.

Keep historical same-host profiles and validators working under their old bindings.
Do not make a permissive union or try multiple validators until one accepts.

## 7. Model owner, packaging and zero-generation qualification

Host the actual existing ModelInference owner with a deliberately selected recorded
backend. Its acceptance, backend reservation, capture and observation path must run;
a stub HTTP handler returning canned command text is insufficient. The backend may
return authored responses but must not execute memory query or construct its feedback.

Add the minimum service-DNS selection to the model transport using the current
certificate, descriptor, request/reply and principal validation patterns. The caller
has CA trust and scoped client credentials, not model assets, provider private keys,
backend API keys or provider policy/journal paths.

Give each new role ConfigMaps for non-secret configuration, referenced Secrets for
credentials/TLS, explicit image digests, resource requests/limits and appropriate
persistent storage. Keep one writer, retained journals and deliberate configuration
rollouts. Use no model downloads, package installs or asset substitutions at request
time. No chart hook, probe, install/upgrade test or container startup may consume a
real generation or activate a campaign. Helm values are not user authorization.

Package or render the supported future real-backend configuration and its offline
asset-verification recipe. Reuse the pinned implementation if actually obtainable
and compatible. Never launch the real runtime to test packaging in this task. Keep
real-runtime build/asset availability distinct from recorded-service readiness; an
unbuildable real backend is a precise future-live prerequisite, not a fake PASS.

Prove the zero-generation controls before tests. Use explicitly selected recorded
mode, deny live-backend construction/launch/contact, and retain instrumented counters
for recorded responses versus real generations. Missing real-runtime access must
not silently select fixtures. Tests must not inherit historical approval files or
campaign directories. All previous live slots remain spent.

## 8. Actual in-cluster workflow

Implement a minimal cluster-aware runner using the existing workload and owner
lifecycle, not the old host harness which launches providers beside the cluster.
Operator/test code may prepare assets, install charts, send peer questions and
observe owner diagnostics. It must not perform the target memory query, supply
candidate IDs, fabricate a capture or run a provider outside its assigned workload.

1. In a separate setup session, actual native remember creates the approved target
   and distractors through the deployed encoder/storage/Search services. Retain
   acceptance, source coverage, publication and metadata/read-view evidence.
2. Start a new read-only measured session using that ready view. Setup prompts,
   commands and answers are not inherited. Restrict measured commands to the existing
   stage-specific query then send grammar. The target answer is not in the first
   peer input, prompt, skills, policy errors or model-accessible files.
3. A real peer sends the question through the in-cluster IRC server. Bridge capture,
   payload persistence, Messaging and native input assignment must be real.
4. The deployed ModelInference owner captures a labelled fixture proposal for the
   admitted query. Actual native query uses deployed E5, Search and AtomStorage.
5. The second model request contains the exact captured query projection and view,
   approved for that recipient through the new cross-pod disclosure path.
6. A labelled fixture proposes send. Preserve whole-batch admission and finite body
   eligibility. Observe the actual admitted body at the peer; score correctness
   separately from delivery and authority.

Use correct and wrong-permitted responses, unsupported commands, target-absent
records, unavailable generations and malformed receipt cases. At least one altered
synthetic target must produce correspondingly changed actual retrieval feedback.
Recorded responses do not measure whether a generative model understood the data.

The new measured-session startup must select a nonempty ready view without migrating
old application journals or depending on a setup process's memory. The existing
memory deployment initializes an empty source for its own workflow; keep that old
entrypoint unchanged and add a narrow supported new-session/read-view selection.

The E5-free Omega caller remains a hard gate. Keep Search as a projection; do not
embed E5 or a second authoritative corpus in ModelInference, the bridge or the peer.
S04/S05 cognitive-service deployment is not required; do not add it silently to
make the retrieval composition boot.

## 9. Bounded recovery, timing and resource tests

Reuse the original accepted deadlines and budgets under the selected profiles.
Cold provider readiness and fixture observer limits are separate from work already
accepted. Sequence heavy E5/Chroma tests on the node; report resource contention.
No automatic deadline extension, call refund or model-response repair. If a required
case cannot meet the selected domain, report it or make a separately documented
fresh-profile proposal; never change a previously accepted operation.

Run real pod replacements with observed old/new UIDs and retained PVCs at least at:

- Bridge capture before mailbox acceptance, then application input acceptance before ack.
- Model reservation before recorded backend response: preserve unknown/spent state.
- Model response captured before caller receipt: recover the exact response without
  another recorded evaluation; current authorization still applies.
- Actual query result captured before prompt handoff: preserve the view, vector,
  projection, input identity and remaining read budget.
- Native response/command accepted before send consumption.
- Bridge socket reservation with uncertain outcome: no duplicate transmission.
- ConfigMap-driven rollout of a selected owner without changing accepted semantics.

Also test wrong role/credential, another authorized principal, revoked disclosure,
scope/recipient/profile mismatch, modified or replayed receipt, bad certificates,
service outage and lost replies. A failed status read is not proof of absence.
Namespace/PVC recreation is not recovery. Do not reconstruct a spent allowance from
Helm values. Record negative safety assertions separately from positive workflows.

A bounded in-pod diagnostic endpoint or read-only owner export may help observers;
it cannot be an alternate business logic path. Do not access foreign SQL from the
application or add a new control-plane service solely to gather test evidence.

## 10. Finish with executable preparation, not another authorization dead end

Deliver a working recorded-mode installation, the future live-mode templates/runner
connection, and a disabled approval-ready deployment plan. The implementation phase
is not contingent on granting generations. Any later live execution is.

Reconcile the existing campaign machinery's filesystem assumptions without sharing
mutable campaign ledgers across pods. A future campaign reservation has one durable
owner; for the bounded single-provider deployment it can be colocated with that
provider's accounting if the existing contract permits it. The operator reads exported
observations. Define how provider reservations and the campaign projection reconcile;
do not add a distributed scheduler or silently weaken the existing budget guarantee.

The proposed future plan should identify image/source digests, profiles, service and
certificate identities, fresh session/slot IDs, corpus/view identity, input and egress
policies, diagnostic policy and original bounds. Define only the new k3s experiment;
do not reuse the completed `retrieval-grounded-20261026-02` campaign. A minimal proposed
live run can be one two-stage HTTPS session (query and reply, at most two generations);
this is a proposed ceiling, **not authorization**. Do not run local-vs-HTTPS again merely
for symmetry when the deployment question is the all-service k3s composition.

Plan slots remain unreserved, the approval field remains absent, and live allowance
stays zero. Start absolute deadlines only at future admission, not while waiting for
approval. Runtime availability remains unchecked. When exact future-live assets or
bindings cannot be frozen, return that plan as INCOMPLETE with precise prerequisites;
do not count it as a ready live environment or stop independent preparation work.

Keep the qualification runner and fixture journals separate from any future live
session. The latter must reject fixture mode and require fresh approval before real
runtime startup or evaluation. No fixture fallback, health-check generation, hidden
warm-up or inherited permission. Do not execute the proposal in this task.

## 11. Acceptance gates and reporting

| Gate | Required preparation evidence |
|---|---|
| BASELINE_SOURCE | Completed memory tree and image/source identities reconciled; known baseline error and impact explicit |
| CHART_IMAGES | ConfigMaps, referenced Secrets, independent workload state, service DNS/TLS, old values preserved |
| MODEL_OWNER | Real ModelInference owner with explicit recorded backend; persistent acceptance/reservation/capture |
| CROSS_POD_DISCLOSURE | No shared authority/receipt files; exact trusted issuer/recipient/input/view binding and live checks |
| CHANNEL_OWNER_SPLIT | Real bridge/IRC; payload storage and Messaging separated through declared ports |
| NATIVE_RETRIEVAL_REPLY | Actual in-cluster setup/query/context/send and independent peer observation |
| NO_ANSWER_ORACLE | No initial leakage; real feedback; wrong allowed answer fails independent evaluation |
| POD_RECOVERY | Captured work and uncertain effects retain their original identity, bounds and authority |
| ZERO_LIVE | Verified denial controls, explicit fixture selection, zero real-runtime startups/calls/reservations |
| COMPATIBILITY | Impact-selected memory/S01/channel/model/disclosure regressions; no silently waived new failure |
| OPERATIONS_CLEANUP | Reproducible commands, resource observations, protected retained demo, explicit cleanup |

Keep future-real-runtime image/asset verification and current availability as separate
observations; they do not pass merely because the recorded backend runs.

Deliver one report, same-workflow trace, source/image manifests, chart/values, test
ledger, actual command lines, deployment/upgrade/cleanup instructions and disabled
live plan. Preserve historical limitations and raw failed attempts. Do not aggregate
methods, parametrized fault cases and scenarios into an inflated total. Do not claim
all tests pass while the known owner regression is unresolved.

After evidence collection remove only task-owned qualification resources. Preserve
`omega-demo` and independently verify its recorded before/after resource identities;
do not assume its historical health. Document retained image/model assets and any
state retained solely for a proposed campaign, without leaving unnecessary heavy
processes running. Do not publish Secrets, kubeconfig, private keys or raw journals.
Commit/push only under current user/workspace authorization.

Final status must distinguish at least:

    SINGLE_NODE_MODEL_CHANNEL_PREPARATION=<PASS/PARTIAL/FAIL>
    RECORDED_RETRIEVAL_WORKFLOW_IN_K3S=<PASS/FAIL/NOT_RUN>
    MODEL_RESPONSES=RECORDED_FIXTURE
    GENERATION_DENIAL_TESTED=<PASS/FAIL>
    AUTHORIZED_LIVE_GENERATIONS=0
    RESERVED_LIVE_GENERATIONS=0
    OBSERVED_GENERATIVE_BACKEND_CALLS=0
    CAPTURED_LIVE_RESPONSES=0
    ADDITIONAL_LIVE_GENERATIONS=0
    GENERATIVE_RUNTIME_IMAGE=<OFFLINE_VERIFIED/BLOCKED/NOT_VERIFIED>
    GENERATIVE_RUNTIME_AVAILABILITY=NOT_CHECKED
    K3S_LIVE_CAMPAIGN_FREEZE=<COMPLETE/INCOMPLETE>
    CAMPAIGN_STATE=DISABLED_PENDING_NEW_AUTHORIZATION
    LIVE_MEMORY_MODEL_WORKFLOW_IN_K3S=NOT_RUN
    MULTI_NODE=NOT_RUN
    CHAIN_IN_K3S=NOT_RUN
    PRODUCTION_READINESS=NOT_ESTABLISHED

Then stop. This adds deployment/composition evidence, not a new module family,
command count, live-generation result or whole-product completion percentage.

## 12. Review references

These public paths were inspected as source/evidence, not executed by the reviewer.
Resolve their exact bytes in the actual checkout; the reported parent alone lacks
the completed memory-service increment.

```text
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/master/docs/deployment/single-node-memory.md
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/master/evidence/single-node-memory/tests.json
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/master/evidence/single-node-memory/changes.json
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/master/fusion/memory_services.py
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/master/fusion/model_transport.py
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/master/fusion/model_service.py
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/master/fusion/neoclaw_retrieval_disclosure.py
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/master/fusion/channel_transport.py
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/master/fusion/channel_service.py
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/master/fusion/irc_bridge.py
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/master/integration/neoclaw/retrieval_runner.py
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/master/integration/neoclaw/retrieval_backend.py
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/master/integration/single_node/memory_host.py
```

The October 15 Kevin/Kabir discussion supports function-based service contracts,
storage/recall/execution handoff and version independence (00:13:36–00:18:47;
01:04:49–01:07:39). The AGI Benchmarks discussion distinguishes module requests from
state ownership (00:11:14–00:12:40) and asks for integration acceptance tests
(00:02:28; 00:17:02). This particular deployment and permission plan is a new
engineering proposal, not a claim that those meetings selected it.
