# Scoped browser and owner capacity

The optional `pilotWorkbench` chart selection deploys the existing workbench as
one stateless gateway. Native sessions, captures, subscription cursors and
maintenance receipts remain with their existing owners. Restarting the gateway
expires browser login sessions; it does not recreate, cancel or resubmit work.

The trusted installer calls `pilot_browser_provision.provision` with the actual
already provisioned owner credential map through its `credentials` parameter.
Missing credentials refuse provisioning. The returned bootstrap credentials and
owner tokens are private installation material and must not enter evidence or
distribution artifacts. Only `gateway_configuration` belongs in the ConfigMap;
it contains bootstrap hashes, permitted scopes, endpoint selections and Secret
file references. Each user's selected scope receives its own owner principal.
Each role may inspect the selected Registry providers in that scope. Developers
and operators may select already trusted providers through an allowed session
template; only operators may seal Registry audit history. These grants do not
permit adding, probing, disabling or replacing providers.

Set `pilotWorkbench.enabled=true`, supply that configuration, select the tested
caller image, reference the existing CA Secret and list only the required
`browser-…-token` Secret keys under each selected owner in `credentials`.
The gateway has no kubeconfig, service-account token, owner PVC, developer tree,
provider private key or model asset. Its egress permits DNS and selected owner
HTTPS ports. No broad operator token is forwarded. TCP probes only accept a
connection and cannot execute work or consume owner budgets.

The operator opens the private access path:

```sh
kubectl --kubeconfig "$PILOT_KUBECONFIG" --context "$PILOT_CONTEXT" \
  -n "$PILOT_NAMESPACE" port-forward service/omega-workbench 8878:8878 \
  --address 127.0.0.1
```

The user visits `http://127.0.0.1:8878` and signs in with the separately delivered
synthetic bootstrap credential. The browser environment needs no Kubernetes or
provider credential, checkout or Python installation. HTTP is confined to the
managed loopback path; gateway-to-owner traffic uses authenticated HTTPS. Host,
Origin, peer address, SameSite/HttpOnly cookies, CSRF and current user policy are
checked. This profile does not support public ingress or remote plaintext HTTP.

Operator CLI equivalents use the same bounded owner contracts:

```sh
python -m integration.single_node.pilot_browser_client \
  --configuration PRIVATE_BROWSER_JSON --user alice state
python examples/pilot_browser_qualification.py \
  --base http://127.0.0.1:8878 --user alice \
  --bootstrap-file PRIVATE_BOOTSTRAP --plan SYNTHETIC_PLAN \
  --output NEW_PRIVATE_REPORT
```

The qualification helper accepts recorded-model configuration only. Its
`--reconnect-report` mode observes exact prior identities without submitting
commands. A completed application input is not automatically counted as a
successful native effect. The browser's observer admits at most 150 cycles in
300 seconds; expiry stops observation and never renews task authority.

The knowledge explorer takes active logical memory choices from the selected
owner observation, follows at most four Relations per page and retains the
owner's cursor/snapshot. Normal traversal refuses a withdrawn target. History
navigation binds the selected session's episode and retained sequence, then
hydrates at most four immutable bodies through AtomStorage. Sealed-archive
readback uses the same declared storage port; the browser does not claim which
physical path served a successful read. Historical episode data is
administrative history, not an empirical observation or independent support.
Exports repeat current authorization and require the exact reviewed page.

An operator may explicitly select `configuration.handover` with the existing
`planned-synthetic-writer-handover/1` profile, fixed
`/writer-authority/current.json` and one or two named task-owned `deployments`.
Set `pilotWorkbench.existingAuthoritySecret` to its separately provisioned
external authority Secret. Only its `current.json` key is mounted read-only.
The display returns actual byte digest, state, generation, incarnation and
checkpoint/closure digests. An exact-digest recheck refuses stale state. This
is an authority observation, not proof that writers are stopped; plan, retire
and activate remain the existing installed handover operator's responsibility.
No browser-supplied fencing assertion, restore payload or Kubernetes body is
accepted. CLI `explore` and `handover` use the same read-only contracts.

The `pilot-owner-headroom/1` observer reads bounded, owner-local SQLite snapshots
and Search metadata only. It never constructs an encoder, Chroma client, native
runtime or foreign owner. Fixed private partitions use their own configuration;
caller journals are selected from this application's retained allocations,
without emitting session IDs or private scope names. Symlinks and foreign paths
refuse. Missing, corrupt or unsupported observations remain `UNKNOWN`.

The report separates retained history, current pending work, spent attempts,
completion/closure reservations, logical bytes and allocated SQLite/WAL blocks.
Per-scope or per-occurrence limits are labelled accordingly. Unbounded lifetime
dimensions have a null limit; no quota or reclamation promise is inferred.
Archive publication leaves feed charges intact. Source observations from
different journals are not an atomic cross-owner admission promise.

Development evidence is in `evidence/operator-pilot/browser-development.json`,
`capacity-development.json`, `state-machines.json` and the retry audit. Those
isolated checks do not stand in for the programme's deployed native workflows,
browser qualification, maintenance/handover stories or final image manifests.
`browser-registry-reconciliation.json` preserves the dev04 provisioning defect
and its real session/Registry regression: the initial browser fixture omitted
Registry selection, and therefore missed the required scoped inspect/select
permissions. Deployed browser evidence must use the corrected image epoch.

An operator can observe and decide an existing native workflow checkpoint through
`POST /api/workflows` (`role`, `session`, `workflow`, `operation`, `body`). The only
selected operations are `observe` and `decide`; the latter accepts the returned
checkpoint identity, exact binding digest, stable action identity, and
`approve`/`refuse`. The gateway binds the identity to the authenticated user and
validates the returned scope, principal, checkpoint digest, original deadline and
decision actor. Current owner policy is rechecked. No admission, amendment,
checkpoint creation or workflow advancement is exposed by this browser seam.

The page saves its action identity before sending and restores its authenticated
user after a cookie-backed reload. Editing the login textbox cannot change that
identity. A late approval is retained as ineffective under the original deadline;
refusal and expiry stay separate. Even effective approval requires a separate
explicit existing-owner drive and fresh prerequisites before another native
input. `browser-workflow-development.json` separates real HTTP/SQLite commits,
authored native/time fixtures, visual checks and the later deployed qualification.

The corrected page clears local rendered state and disables controls even when
logout is denied or its HTTP result is unavailable. This is not a claim that a
server cookie was revoked: the notice distinguishes unconfirmed server logout.
The existing finite/current server policy still controls every disclosure.
Pending action, workflow-decision and subscription identities remain in
per-user tab storage across logout. No input, capture body, bootstrap credential
or provider secret is persisted there. Reauthentication may observe or explicitly
repeat the same action; it never triggers automatic resubmission. These metadata
keys survive only the current tab's session-storage lifetime.

The public packet includes `examples/pilot_browser_story.py`, which reuses the
installed standard-library browser client. It accepts an explicit private JSON
plan with profile `bounded-native-browser-story/1`, task namespace, identity
prefix and `corpus` entries for `alice`, `bob` and `shared`. Each entry names
`remember`, `query`, `expected` and its `synthetic-private` or
`synthetic-shareable` disclosure. The expected value is an evaluator input and
must occur in the remembered corpus but not in the query. Returned native
handles supply link, evidence, priority, delegation and withdrawal arguments.
The runner refuses an existing report path and preserves unknown submission
identities without retry. It never substitutes an expected answer for a result.
Its capture observer records transient `OVERLOADED`/`NOT_AVAILABLE` refusals and
repeats only reads, with at most 150 reads within a 150-second window and the
original deadline plus five seconds. One already in-flight client read may take
its existing 35-second transport bound. An expired occurrence gets one read for
its retained capture. Current authorization failures are not retried.

An explicit `--resume-from FAILED_PRIVATE_REPORT` writes a different report and
binds both the exact prior report bytes and prior source identity. It requires the
same plan, phase, session and acknowledged allocation/input receipts. Previously
accepted commands are observed and their captured results reused; neither their
allocation nor submission is repeated. The remaining fixed commands keep their
original sequence identities. Unknown allocation or submission responses remain
blocked for separate owner reconciliation. Up to four explicit continuations are
allowed; none renews an accepted deadline or refunds work.

```sh
operator/bin/python -I /packet/examples/pilot_browser_story.py \
  --root /private/browser-bootstrap --plan /private/story-plan.json \
  --phase private --output /private/private-story.json
operator/bin/python -I /packet/examples/pilot_browser_story.py \
  --root /private/browser-bootstrap --plan /private/story-plan.json \
  --phase shared --output /private/shared-story.json
```

A trusted installer must first establish the private loopback forwarding path
and explicitly qualify the Registry selections. The browser/user client receives
only its own bootstrap credential. The recorded qualification used an isolated
environment and installed client files on the same host; it did not establish a
separate OS user or a filesystem mount sandbox. Raw private reports and proof
videos stay private. Public summaries withhold private session, input, memory,
checkpoint and capture identifiers and hashes, even for synthetic scopes.

The packet also includes nine static operator recipes under
`examples/pilot_browser_recipes/` and the offline
`examples/pilot_browser_bind_recipes.py`. The binder only validates and writes
reviewed source files; it starts no process and makes no network or cluster call.
Its parameter file contains paths, not credentials. Use absolute paths consisting
of letters, digits, slash, dot, underscore or hyphen. The tested Kubernetes
context is `default`; the namespace must start with `omega-ref-pilot-`.

```json
{
  "PRIVATE_ROOT": "/private/browser-run",
  "KUBECONFIG": "/private/operator/kubeconfig",
  "NAMESPACE": "omega-ref-pilot-browser-example",
  "PACKET": "/packet",
  "PROOFSHOT": "/tools/node/bin/proofshot",
  "NODE_BIN": "/tools/node/bin",
  "BROWSER_EXECUTABLE": "/tools/chromium/chrome",
  "BROWSER_SOCKET_DIR": "/tmp/browser-example-sockets",
  "BROWSER_SESSION": "browser-example",
  "IDENTITY": "browser-example",
  "KUBECTL": "/tools/kubectl"
}
```

Bind before creating the fresh preparation directory. Keep the parameters and
bound source manifest private; neither belongs in a public evidence archive.

```sh
operator/bin/python -I /packet/examples/pilot_browser_bind_recipes.py \
  --templates /packet/examples/pilot_browser_recipes \
  --parameters /private/browser-parameters.json \
  --output /private/browser-run/preparation
```

The normal trusted installer then creates `base-values.yaml`,
`gateway-values.yaml` and `secrets/` in that preparation directory, using the
packet's chart, image manifest, `pilot_values`, `create_secrets.py` and
`pilot_browser_provision.provision`. Provision with the exact generated
credential map, never a second independently generated owner token. Put only the
four user bootstrap files and the packet's `pilot_browser_qualification.py`
(named `browser_client.py`) in `preparation/user-client/`. Create `user-home/` and
a `proofshot.config.json` selecting the private proof output directory. Verify
the installed placement before any native input. Record all bound recipe hashes
with the plan before execution. A namespace installation, Registry probe or
Secret patch remains a trusted operator action, not a browser capability.

The core sequence is the private story, current Registry readiness for shared A/B,
typed shared-browser allocation and `remember`, and then the shared story. Use
the story's exact allocation key `<identity>-shared-shared-allocation` and first
input key `<identity>-shared-shared-0`; the helper observes the same first capture.
The two private sessions may then be explicitly closed under their own scoped
users with unchanged captures. Do not run overlapping owner-intensive observation
tools while measuring native work; finite `OVERLOADED` responses are retained
observations, not permission denials or evidence of disclosure.

After the shared story, the read-only two-view probe is interactive:

```sh
python /private/browser-run/preparation/user-client/reconnect_probe.py \
  --user shared \
  --bootstrap-file /private/browser-run/preparation/user-client/shared.bootstrap \
  --story-report /private/browser-run/shared-story.json \
  --output /private/browser-run/reconnect.json
```

Its stdin accepts only `{"operation":"observe"}`, `expect-denied`,
`login-again`, `current` and `stop` (each with that same `operation` envelope).
It cannot allocate or submit work. To test current browser revocation, run
`rotate_browser_policy.py revoke`, then `policy_projection_barrier.py`, then
`expect-denied`. In the actual UI, refresh/export must refuse; sign out must
clear rendered state and disable work controls even after denial. Run
`rotate_browser_policy.py rotate` for a new explicit bootstrap revision. The old
bootstrap must refuse. A stateless gateway replacement clears its finite login
table; it must not change any owner capture. Reopen only the trusted loopback
forward after replacement. Invalid old sessions still count until their bounded
expiry or gateway replacement; do not assume revocation refunds login capacity.

For same-CA renewal, run `rotate_owner_credentials.py` once, replace only the
selected caller pod through the existing operator, observe the projected current
Secret, and run `verify_owner_rotation.py`. The recipe preserves all other
Secret keys, uses the configured HTTPS endpoint, refuses the former scoped token
and records the actual leaf. Compare exact prior captures through the browser;
never resubmit work to make this check pass.

Each checkpoint case uses existing native workflow admission and the ordinary
browser UI. Start signed out and preserve the original deadline:

```sh
operator/bin/python -I /private/browser-run/preparation/workflow_browser_case.py \
  --case approve --root /private/browser-run/workflow-approve --maximum-seconds 240
operator/bin/python -I /private/browser-run/preparation/workflow_browser_case.py \
  --case refuse --root /private/browser-run/workflow-refuse --maximum-seconds 240
operator/bin/python -I /private/browser-run/preparation/workflow_browser_case.py \
  --case expired --root /private/browser-run/workflow-expired --maximum-seconds 240
```

Approval only records a decision; the existing driver separately advances the
already accepted workflow. Refusal and late approval must leave two spent
reservations and unchanged first captures. After approval, explicitly log out,
reconnect, reread that same workflow and repeat the exact saved decision in the
UI. No new decision identity or native step is needed for this replay.

`browser_cleanup_case.py FORWARD_SHELL_PID` uses the expired case's current
retained view, an explicitly selected Search fault point, one bounded build and
a verified task-owned process kill. Supply only the recorded shell PID whose
sole child is this namespace's loopback `kubectl port-forward`. It retains the
original attempt/deadline, rebuilds separately, demonstrates stale-plan refusal
and then exact-head cleanup through actual UI controls. After its child forward
ends, reopen the trusted forward explicitly; do not retry accepted native work.

For subscription recovery, use the UI to create a new bounded operator
subscription from cursor zero, read the actual gap, obtain the full owner
snapshot, explicitly rebase, then read again. An expired subscription is not
renewed. For archive readback, save the exact authorized history page as
`browser-history-before-archive.json`, then run `archive_browser_history.py`.
It publishes an existing returned immutable payload through the storage archive
port and requires the exact same page afterward; this does not prove a cold read
or physical removal of the hot copy. All recipes retain raw reports privately.

To observe a warm native worker during an already planned checkpoint case,
run the following separate read-only observer. It reads the native driver's
accepted session identity; it cannot allocate, submit, renew, resume or warm a
worker. The workflow keeps its original bound.

```sh
operator/bin/python -I /packet/examples/pilot_browser_warm_observation.py \
  --workflow-report /private/browser-run/workflow-approve/native/report.json \
  --bootstrap-file /private/browser-run/preparation/user-client/shared.bootstrap \
  --user shared --namespace omega-ref-pilot-browser09 --seconds 90 \
  --output /private/browser-run/planned-workflow-warm-observation.json
```

Record the same worker incarnation before and after current browser-policy
revocation. The two-view refusal check can observe an earlier completed session
in the same approved scope while this planned workflow is active; report those
different session identities explicitly in the private record. This establishes
current authorization at the deployed owner while its native worker remains
warm. It does not claim that a denied read interrupts already accepted work, or
that the two HTTP clients are the worker's own persistent socket connection.

The executed runtime09 browser record is
[`browser09.json`](../../evidence/operator-pilot/browser09.json). It separates
31 planned native inputs from four consumed delegated completions and four
second-agent task inputs: 39 captured inputs across ten closed synthetic
sessions. The typed browser `remember` is the same accepted occurrence as the
shared helper's first input. Current-policy revocation, same-CA credential
renewal, caller/gateway replacement, all three checkpoint outcomes, Search
process-kill recovery and stale/current cleanup plans, retained cursor rebase,
and history after archive publication were executed against that pinned image
epoch. Public evidence withholds private records and identifying hashes.

An independent dependency audit subsequently found a compatible leaf packaging
requirement defect in that epoch. The observed browser results are retained;
they were not relabelled as repaired-image results. Historical failed observer
requests remain in the record, separately from successful bounded observations.

The fresh repaired-image qualification is
[`browser10.json`](../../evidence/operator-pilot/browser10.json), bound to
runtime source `9f5c31cbedadece8c17715ddfb7e20e2e53f6087b1a92dd0ec2dd83bc2bb7123`,
distribution11 and installed operator11. It executed the same 31 direct native
inputs plus eight internal inputs, all 39 captures, three checkpoint cases and
the listed browser/security/maintenance stories. Ten sessions were closed, the
namespace was stopped and twelve owner PVCs retained. The typed UI remember is
one occurrence; its unchanged helper then performed one declared duplicate
HTTP submission with the exact key/body/deadline. The UI recovery itself only
observed the already accepted result.

Twelve failed observer invocations were retained separately: ten UI/HTTP or
assertion observers and two trusted diagnostic field-shape assumptions. None
was a native tool failure. They include early empty UI selections, transient
display parsing, a read during controlled gateway replacement, an incorrect
expectation that an authorization-denied socket remains open, and a strict
running-worker assertion when the same incarnation had become idle. The actual
refusal, capture and later readback evidence determines each gate; an observer
failure is not automatically counted as either denial or disclosure.

The production transport has a separate, bounded read-only socket check:

```sh
operator/bin/python -I /packet/examples/pilot_browser_pool_observation.py \
  --kubeconfig /private/operator.kubeconfig --context default \
  --namespace omega-ref-pilot-browser10 \
  --former-secret /private/browser-run/owner-credential-renewal/before-secret.json \
  --story-report /private/browser-run/shared-story.json \
  --output /private/browser-run/pool-socket-current-authority.json
```

This trusted operator recipe runs only five read requests in its passing
observation. A current-token binding read and former-token refusal use the same
actual TLS socket; the owner closes it on denial. The existing `https_pool`
then reuses one current-token socket twice and evicts that entry when selecting
the former credential, which is refused. It records connection identities only
in the private report. It submits no work and changes no policy. The first
executed observer's incorrect post-denial-open assertion remains a failed
record; the revised source is an explicit tools-only supplement to tested
distribution11. This does not claim a connection established with the old
credential before revocation, or that the browser gateway itself enabled the
pool. The native worker was running before browser-policy revocation and the
same incarnation idle afterward; continuous execution is not inferred.

The final runtime11 representative story is
[`browser11.json`](../../evidence/operator-pilot/browser11.json), bound to
runtime source `3ee4c1af77ffc75f1b9e48790d3c8494e9a72ad668b85417779896b8bc46cbc2`,
distribution13 and installed operator12. Its packet digest is
`1c4e21a93b9d4c06edfb0cef8601a7e5827af4e9ed0ee2ec94805edf8f8411fa`.
The tested browser/runtime helpers were unchanged while the run was accepted;
later incident-only operator packaging was not substituted into this evidence.
The same bounded recipes produced 31 direct native inputs, four delegated task
inputs and four consumed results, all 39 complete across ten sessions. The
native `remember` entered in the browser is shared input zero, not a further
input beyond those counts. One declared duplicate allocation HTTP call and one
declared duplicate submit call exercised the same accepted identities.

The approve and expired checkpoint drivers passed. The primary refuse driver
failed during the controlled gateway-forward outage before recording a
decision. After restoring that exact trusted forward, the actual UI made the
first refusal for the same accepted checkpoint before its original deadline.
Independent owner readback retained both spent reservations and the previous
steps; no new allocation, native input or workflow advance was used. The failed
primary report remains failed beside the bounded recovery result. Expiry was
observed at the original deadline, and its late approval was ineffective.

Thirteen classified qualification observer invocations failed: eleven client,
UI or diagnostic scripts and two duplicate port-forward binds. They are listed
individually in the evidence. These include an environment guard before
contact, an unavailable artifact-only import, reads during gateway replacement,
a mistaken gap expectation for a three-input session, and an incorrect count
classification by owner rather than accepted assignment. The real shared
session's earlier gap, snapshot and explicit rebase remain the subscription
proof. A separate shell exit 143 occurred after the shared helper had written
its complete passing report; its cause remains unknown. A mixed reauthentication
observation included an overloaded login and a later refusal of that view's
old cookie; both current views subsequently recovered the exact captures.
Neither overload nor an observer exception is treated as a provider pass.

Actual Search process-kill recovery, stale and current cleanup plans, both
retained views, private-scope refusals, owner/gateway replacement, same-CA leaf
renewal and the five-request socket/pool authority audit were executed against
this exact image epoch. The authorized history page remained exact after
sealed archive publication; no cold-read or physical-erasure claim follows.
The existing subscription's identity, cursor and expiry survived gateway
replacement. Worker observation showed the same incarnation running before
revocation and idle afterward, without a continuous-execution claim.

All ten sessions were closed and all 13 workloads stopped after 2316.109 seconds
of the original 3600-second qualification window. Twelve PVCs remain retained.
ProofShot reported a 2207-second bundle with zero console/server errors; logs
for the separately managed trusted forward remain distinct. Its residual
recorder required explicit cleanup after the bundle completed. Two earlier
owned recorders and two earlier crashpad processes were also stopped separately;
this does not retroactively claim those historical runs had no active processes.
The [cleared browser view](../../evidence/operator-pilot/browser11-denied-logout.png)
was visually inspected before publication. Other screenshots, video, raw
reports and identifying hashes stay private. Browser automation uses a clean
same-host environment without required or received Kubernetes/provider
credentials; a separate OS user or mount sandbox was not established.

For final count reconciliation, use the installed `preview_operator list` and
`observe --session <accepted-session> --content` ports for each native owner.
Count the actual `synthetic-task`, `delegated-task` and `delegated-result`
assignment fields across complete pages. A private user's direct input may be
owned by the second agent; owner role alone does not classify delegation.
Observe captures before closing remaining sessions with a stable close identity,
require exact input equality afterward, then call the existing scoped
`Operator.quiesce()` and retain the zero-pod/PVC inventory. These are observation
and terminalization steps; they never submit native commands or renew deadlines.
