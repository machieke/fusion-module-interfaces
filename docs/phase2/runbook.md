# Single-node developer-preview runbook

This runbook describes the current supported entrypoints. A command shown here
is a **recipe, not execution evidence**. Bind a run to its actual distribution
digest, values, image IDs and reports. The current image qualification is dev19;
the primary programme report distinguishes its executions from earlier
development candidates. The selected manifest must supply every named artifact.

Use one task-owned single-node k3s environment and fresh synthetic state. Keep
`omega-demo`, `omega-ref-live01`, all retained campaign namespaces and the frozen
campaign artifacts untouched. Do not reuse their Secrets, PVCs, session IDs or
approval files. These procedures neither activate nor contact a real text
generation runtime: **ADDITIONAL_LIVE_GENERATIONS=0**. Recorded model proposals
still pass through actual native parsing, authorization and module owners.

The [artifact installation specification](../../sdk/OPERATOR.md),
[distribution format](../../sdk/DISTRIBUTION.md),
[scenario matrix](scenario-matrix.md) and
[private-scope boundary](private-scopes.md) provide the detailed contracts.

## Select and verify artifacts

Prerequisites: CPython 3.12, `kubectl`, Helm, OpenSSL, the explicitly selected
Docker-hosted single-node k3s adapter, its kubeconfig/context and local-path
storage. Use the provided CPython 3.12 Linux x86_64 dependency wheels. Images
already contain their pinned native dependencies, E5 assets, Chroma and DeTTa;
there is no runtime download or hosted-model fallback. Parent-image caches are
needed only for the separately documented rebuild, not for importing the
provided image archive. Do not infer CPU-quota enforcement from configured
limits; retain the distribution's observed resource exception.

Set these values to operator-owned paths and a new namespace. The reviewed
manifest digest must come from the publication, not from recalculating an
untrusted download and treating that value as approval.

```sh
TASK_DIST=/absolute/extracted/distribution
TASK_MANIFEST_SHA256=replace_with_reviewed_distribution_digest
TASK_VENV=/absolute/new-operator-venv
TASK_KUBECONFIG=/operator-owned/kubeconfig
TASK_CONTEXT=explicit-task-context
TASK_K3S_CONTAINER=explicit-task-k3s-container
TASK_NAMESPACE=omega-ref-new-preview
TASK_SCOPE=synthetic-new-preview
TASK_WORK=/operator-owned/new-preview
TASK_MODE=combined

printf '%s  %s\n' "$TASK_MANIFEST_SHA256" "$TASK_DIST/distribution.json" | sha256sum --check
python3.12 -m venv "$TASK_VENV"
"$TASK_VENV/bin/python" -m pip install --no-index \
  --find-links "$TASK_DIST/wheelhouse" \
  fusion-module-client==0.2.0 \
  'fusion-preview-operator[preview-install,artifact-verification]==0.2.0'
mkdir -m 700 "$TASK_WORK"
"$TASK_VENV/bin/fusion-verify-artifacts" "$TASK_DIST/distribution.json" \
  --output "$TASK_WORK/offline-verification.json"
TASK_CHART="$TASK_DIST/$("$TASK_VENV/bin/python" -I -c \
  'import json,sys; print(json.load(open(sys.argv[1]))["chart"])' \
  "$TASK_DIST/distribution.json")"
```

An offline verification pass establishes artifact integrity and binding. It
does not establish cluster availability, successful installation or workflow
completion. Stop on a missing wheel, source mismatch or unsupported platform;
do not install an unpinned substitute from the network.

## Fresh installation and mode selection

The standard generator creates two independently owned native agents, A and B,
with two preselected session templates each. The single-agent example below
selects A alone. Select the topology and mode before the first install.

| `--mode` | Native capabilities selected |
| --- | --- |
| `minimal` | Working context, session history, bounded workspace files and the named deterministic NAL operation; recorded ModelInference. |
| `memory` | Minimal plus real remember/query, lifecycle update/forget, Relations link/unlink and two-agent retrieval handoff; E5 and vector Search services. |
| `combined` | Memory plus separately owned C1/C2 evidence/revision, wall-clock Attention and bounded artifact inspection. Required by combined and chain qualification. |

Generate values once; the command refuses an existing output file. Do not use
disabled example values or regenerate a populated installation's identities.

```sh
"$TASK_VENV/bin/fusion-import-images" \
  --container "$TASK_K3S_CONTAINER" \
  --manifest "$TASK_DIST/images.json" --archive "$TASK_DIST/images.tar"
"$TASK_VENV/bin/fusion-preview-values" \
  --images "$TASK_DIST/images.json" --scope "$TASK_SCOPE" \
  --mode "$TASK_MODE" --output "$TASK_WORK/preview-values.yaml"
```

### Single-agent alternative

For one native A, replace the values-generation invocation above with this
public example from the **verified source archive**. Do not run both generators
against the same output file. Image import, namespace/Secret creation and Helm
installation otherwise use the same commands and chart.

```sh
TASK_SOURCE="$TASK_WORK/qualification-source"
mkdir -m 700 "$TASK_SOURCE"
"$TASK_VENV/bin/python" -I - "$TASK_DIST/source.tar.gz" "$TASK_SOURCE" <<'PY'
import sys, tarfile
with tarfile.open(sys.argv[1], 'r:gz') as archive:
    archive.extractall(sys.argv[2], filter='data')
PY
cd "$TASK_SOURCE"
test -f examples/preview_single_agent_values.py
env -u PYTHONPATH -u PYTHONHOME "$TASK_VENV/bin/python" \
  -m examples.preview_single_agent_values \
  --images "$TASK_DIST/images.json" --scope "$TASK_SCOPE" \
  --mode "$TASK_MODE" --output "$TASK_WORK/preview-values.yaml"
```

The helper supports `minimal`, `memory` and `combined`, defaulting to `minimal`
when `--mode` is omitted. It reuses the existing generated composition and
profiles, removes B and B's recorded response slots, and disables B's workload.
A retains its two fresh sessions, original limits, existing selected owners and
distinct synthetic private storage scope. Delegation and inspection derived
from two-agent task results are not selected; chain is not selected. Combined
single-agent memory/cognition uses the same numerical profiles.

Use the native session CLI/workbench below with `omega-agent`, and wait for
each actual command completion. The shipped combined/recovery/Attention/scope/
chain qualification runners target A and B explicitly; do not run them against
a single-agent installation or infer their results from its smoke test. This
example is a supported configuration seam, not evidence of native execution
by itself. It is included in the final public artifact allowlist. Earlier candidate
packets assembled before this example cannot substitute for that publication.

### Optional chain and private selection

For the isolated-chain variant, select `combined` and add `--chain` to that
**initial** values-generation command, and install the optional dependencies
before creating Secrets. This variant uses the standard two-agent generator:

```sh
"$TASK_VENV/bin/python" -m pip install --no-index \
  --find-links "$TASK_DIST/wheelhouse" \
  'fusion-preview-operator[preview-install,chain-key-setup]==0.2.0'
```

Generated private scopes are `$TASK_SCOPE-private-a` and, for the standard
two-agent selection, `$TASK_SCOPE-private-b`. These are distinct, approved synthetic AtomStorage
scopes; the native remember/query corpus, history and cognition remain in the
shared scope. Private storage selection does not move existing user memory or
make shared history confidential. For explicit two-agent names, set both
`preview.agents.omega-agent.private_scope` and
`preview.agents.omega-agent-b.private_scope` before Secret creation/first
startup. For the single-agent example, only A's field is selected. Use distinct
valid synthetic names and retain them thereafter. Older
values with neither field remain shared-only.

For independent Attention substitution, use another fresh combined namespace
and values file. Before its first startup, set
`preview.cognition.attention_provider` to `file-fixture`; the default is
`sqlite`. Keep native images, policy and numerical profile unchanged. This is
new-session provider selection, not migration or hot replacement of accepted
work.

```sh
"$TASK_VENV/bin/python" -I -c \
  'import sys; from integration.single_node.reference_ops import Operator; Operator(*sys.argv[1:]).create()' \
  "$TASK_KUBECONFIG" "$TASK_CONTEXT" "$TASK_NAMESPACE"
"$TASK_VENV/bin/fusion-create-secrets" \
  --preview-values "$TASK_WORK/preview-values.yaml" \
  --kubeconfig "$TASK_KUBECONFIG" --context "$TASK_CONTEXT" \
  --namespace "$TASK_NAMESPACE" --directory "$TASK_WORK/private-secrets"
```

The Secret helper creates a new private directory and new credentials/TLS
material. Never publish that directory. For a chain-enabled selection, bind its
fresh **public** identity before the first Helm install, leaving activation off:

```sh
"$TASK_VENV/bin/python" -I - "$TASK_WORK/preview-values.yaml" \
  "$TASK_WORK/private-secrets/chain-public.json" <<'PY'
import json, sys
from pathlib import Path
import yaml
path = Path(sys.argv[1])
values = yaml.safe_load(path.read_text())
chain = values['preview'].get('chain', {})
if chain.get('enabled'):
    assert chain['nodeEnabled'] is False
    assert chain['isolationVerified'] is False
    assert chain['registration'] is None
    public = json.loads(Path(sys.argv[2]).read_text())
    assert set(public) == {'public_key', 'wallet_address'}
    chain.update(public)
    path.write_text(yaml.safe_dump(values, sort_keys=False))
PY

helm upgrade --install omega "$TASK_CHART" \
  --kubeconfig "$TASK_KUBECONFIG" --kube-context "$TASK_CONTEXT" \
  --namespace "$TASK_NAMESPACE" -f "$TASK_WORK/preview-values.yaml" \
  --wait --timeout 300s
kubectl --kubeconfig "$TASK_KUBECONFIG" --context "$TASK_CONTEXT" \
  -n "$TASK_NAMESPACE" get pods,pvc,services
```

Readiness checks execute no tool and consume no work budget. Services use
ClusterIP/DNS and authenticated HTTPS. Each journal owner has one StatefulSet
ordinal, one dedicated PVC, a process lock and a retained composition seal.
Do not scale owners above one replica, mount another owner's PVC, or mount a
developer checkout. Native callers do not contain the E5 inference stack.

## Operate a native session

The following CLI runs inside the selected agent pod; it reaches that agent's
authenticated session API. It does not invoke a provider tool on the host.
Start with the returned inventory and one selected session UUID.

```sh
TASK_AGENT=omega-agent
kubectl --kubeconfig "$TASK_KUBECONFIG" --context "$TASK_CONTEXT" \
  -n "$TASK_NAMESPACE" exec "$TASK_AGENT-0" -- \
  /opt/native/python/bin/python3.12 -m integration.single_node.preview_operator \
  inventory > "$TASK_WORK/inventory-a.json"
TASK_SESSION=$("$TASK_VENV/bin/python" -I -c \
  'import json,sys; print(next(iter(json.load(open(sys.argv[1]))["sessions"])))' \
  "$TASK_WORK/inventory-a.json")
kubectl --kubeconfig "$TASK_KUBECONFIG" --context "$TASK_CONTEXT" \
  -n "$TASK_NAMESPACE" exec "$TASK_AGENT-0" -- \
  /opt/native/python/bin/python3.12 -m integration.single_node.preview_operator \
  create --session "$TASK_SESSION"
```

Persist an occurrence identity before submission. Reuse its exact text and
assignment only when retrying that same occurrence. A new intentional input,
even with identical text, needs a new identity and a new identity-file path.

```sh
"$TASK_VENV/bin/python" -I - "$TASK_WORK/input-001.id" <<'PY'
import sys, uuid
with open(sys.argv[1], 'x') as file:
    file.write(str(uuid.uuid4()) + '\n')
PY
TASK_INPUT_ID=$(cat "$TASK_WORK/input-001.id")
kubectl --kubeconfig "$TASK_KUBECONFIG" --context "$TASK_CONTEXT" \
  -n "$TASK_NAMESPACE" exec "$TASK_AGENT-0" -- \
  /opt/native/python/bin/python3.12 -m integration.single_node.preview_operator \
  submit --session "$TASK_SESSION" --identity "$TASK_INPUT_ID" \
  --assignment synthetic-task --text 'pin task Verify the synthetic shipment location'
kubectl --kubeconfig "$TASK_KUBECONFIG" --context "$TASK_CONTEXT" \
  -n "$TASK_NAMESPACE" exec "$TASK_AGENT-0" -- \
  /opt/native/python/bin/python3.12 -m integration.single_node.preview_operator \
  observe --session "$TASK_SESSION" --content --after 0
```

Follow `next_after` for later observation pages. Observation and refresh do not
resubmit work. `accepted` is durable input acceptance; inspect the separate
completion/result before treating a command as successful. Preserve the
receipt if wakeup or observation fails. Do not repair a command or create a
replacement input to relabel a failed occurrence as recovered.

In memory/combined mode, submit `remember The synthetic amber token is stored
in crate cedar`, wait for its actual completion, then submit `query synthetic
amber token location` in the same session using a new persisted identity.
No operator inserts an answer reference or changes configuration between the
commands. Further tools use handles returned by actual completed commands;
scope/type handles are not credentials. For B, repeat inventory/session
selection with `TASK_AGENT=omega-agent-b`.

Session controls use the same CLI with `pause`, `resume` or `close`,
`--session "$TASK_SESSION"` and a new persisted `--identity`. They do not take
`--text` or `--assignment`. Pause/close preserve accepted effects, captures,
spent reservations and original deadlines. A closed session cannot be resumed;
an expired input is not renewed by pause/resume or pod replacement.
If storage reports `OVERLOADED`, inspect the existing receipt and worker state
before further submissions. A new input identity cannot recover an earlier
occurrence blocked by capacity. Session observation and pause/close remain the
supported control path; they do not clear owner records or spent budgets.

For the local UI, keep the workbench in the foreground and stop it with Ctrl-C:

```sh
"$TASK_VENV/bin/fusion-preview-workbench" \
  --kubeconfig "$TASK_KUBECONFIG" --context "$TASK_CONTEXT" \
  --namespace "$TASK_NAMESPACE" --port 8768 \
  --access-file "$TASK_WORK/workbench-access-001"
```

Open `http://127.0.0.1:8768` and privately paste the new access file's opaque
token into **Local workbench token**. The file is created exclusively with mode
0600; every new workbench process needs a new filename. Select agent/session,
open it, inspect its selected capabilities, submit one synthetic occurrence,
refresh its receipts, and use the displayed pagination and pause/resume/close
actions. The token is separate from pod credentials. Keep it out of URLs,
screenshots, arguments and published evidence. The workbench binds loopback;
this procedure does not expose a public service.

## Qualify the selected deployment

The narrow operator wheel packages installation and workbench code, not the
qualification modules. For artifact-only qualification, extract the verified
distribution's public source archive into a new operator-owned directory. This
is the exact distributed source, not a mount or import of the developer tree.
If this exact archive was already extracted for the single-agent helper, reuse
that directory rather than extracting it again. The following qualifiers still
require their separate two-agent selection.

```sh
TASK_SOURCE="$TASK_WORK/qualification-source"
mkdir -m 700 "$TASK_SOURCE"
"$TASK_VENV/bin/python" -I - "$TASK_DIST/source.tar.gz" "$TASK_SOURCE" <<'PY'
import sys, tarfile
with tarfile.open(sys.argv[1], 'r:gz') as archive:
    archive.extractall(sys.argv[2], filter='data')
PY
cd "$TASK_SOURCE"
```

Run each recipe only for its selected scope, on fresh qualification state with
enough original capacity. Do not run all modes successively against the same
bounded sessions and then raise caps when they fill. Qualifiers use recorded
responses, original deadlines and finite observers; every new execution needs
a new output directory. Preserve failures and nonterminal reports.

```sh
env -u PYTHONPATH -u PYTHONHOME "$TASK_VENV/bin/python" \
  -m integration.single_node.preview_qualification \
  --kubeconfig "$TASK_KUBECONFIG" --context "$TASK_CONTEXT" \
  --namespace "$TASK_NAMESPACE" --mode combined \
  --output "$TASK_WORK/combined-001"
```

`combined` requires combined values. It exercises both role directions, native
memory/history/Relations/cognition, artifact inspection, workspace and lifecycle.
It is not a minimal-mode smoke test. Keep the successful `report.json` for the
chain qualifier; an intermediate inspection does not substitute for the
required completed report.

Check the actual retained native contexts and owner receipts without submitting
more inputs:

```sh
"$TASK_VENV/bin/python" -m examples.preview_combined_observations \
  --kubeconfig "$TASK_KUBECONFIG" --context "$TASK_CONTEXT" \
  --namespace "$TASK_NAMESPACE" \
  --qualification "$TASK_WORK/combined-001/report.json" \
  --images "$TASK_DIST/images.json" \
  --source-package "$TASK_DIST/image-sources/caller.json" \
  --output "$TASK_WORK/combined-observations-001"
```

This checks actual promoted/pinned context, retained pre/post unlink views,
unchanged truth and distinct mailbox-acceptance history. Mailbox acceptance
does not establish recipient consumption or independent evidence. It reads
each owner's own pod as an authorized operator; it is not a runtime dependency.

For the single-agent **minimal** selection, the short native demonstration is:

```sh
"$TASK_VENV/bin/python" -m examples.preview_single_agent_qualification \
  --kubeconfig "$TASK_KUBECONFIG" --context "$TASK_CONTEXT" \
  --namespace "$TASK_NAMESPACE" --values "$TASK_WORK/preview-values.yaml" \
  --output "$TASK_WORK/single-agent-001"
```

It submits six bounded inputs through the same session API: original named NAL,
pin/context, another pin, unpin and context. It does not perform those tools in
the operator process.

Use a separate fresh combined deployment for the recovery setup and its fault
run. The second command requires the first report to say `PASS`:

```sh
env -u PYTHONPATH -u PYTHONHOME "$TASK_VENV/bin/python" \
  -m integration.single_node.preview_qualification \
  --kubeconfig "$TASK_KUBECONFIG" --context "$TASK_CONTEXT" \
  --namespace "$TASK_NAMESPACE" --mode recovery-setup \
  --output "$TASK_WORK/recovery-setup-001"
env -u PYTHONPATH -u PYTHONHOME "$TASK_VENV/bin/python" \
  -m integration.single_node.preview_recovery_qualification \
  --kubeconfig "$TASK_KUBECONFIG" --context "$TASK_CONTEXT" \
  --namespace "$TASK_NAMESPACE" --values "$TASK_WORK/preview-values.yaml" \
  --chart "$TASK_CHART" --native "$TASK_WORK/recovery-setup-001/report.json" \
  --output "$TASK_WORK/recovery-001"
```

The runner arms bounded opt-in faults and replaces selected pods, retaining
one-shot markers, PVCs, identities, deadlines and spent attempts. Do not clear
markers or rerun a failed case under a new occurrence to call it recovery.

The handoff barrier needs a **different** fresh recovery-setup namespace; the
seven-case recovery run consumes B's one-use marker:

```sh
"$TASK_VENV/bin/python" -m examples.preview_handoff_recovery \
  --kubeconfig "$TASK_KUBECONFIG" --context "$TASK_CONTEXT" \
  --namespace "$TASK_NAMESPACE" --values "$TASK_WORK/preview-values.yaml" \
  --chart "$TASK_CHART" --native "$TASK_WORK/recovery-setup-001/report.json" \
  --output "$TASK_WORK/handoff-recovery-001"
```

It replaces B after its real query/report capture and observes A's actual
next-context consumption. It preserves the original task window and captured
bytes; it never clears markers or generates a replacement task.

For each fresh primary/independent Attention selection, run:

```sh
env -u PYTHONPATH -u PYTHONHOME "$TASK_VENV/bin/python" \
  -m integration.single_node.preview_qualification \
  --kubeconfig "$TASK_KUBECONFIG" --context "$TASK_CONTEXT" \
  --namespace "$TASK_NAMESPACE" --mode attention-replacement \
  --output "$TASK_WORK/attention-001"
```

Record both reports and exact caller/provider images. The independent file
Attention implementation remains labelled as that provider; it does not turn
other fixtures into real-provider passes.

The scope qualifier requires both generated private scopes and idle, created
sessions whose accepted inputs are all complete. Run after the native
qualification, before quiescing. It creates two synthetic storage records,
exercises cross-agent denial/outage, rotates A's storage credential and the
storage same-CA leaf, and verifies unchanged model/application accounting:

```sh
env -u PYTHONPATH -u PYTHONHOME "$TASK_VENV/bin/python" \
  -m integration.single_node.preview_scope_qualification \
  --kubeconfig "$TASK_KUBECONFIG" --context "$TASK_CONTEXT" \
  --namespace "$TASK_NAMESPACE" --private-material "$TASK_WORK/private-secrets" \
  --output "$TASK_WORK/scopes-001"
```

This needs the operator's original generated CA material and changes Secrets
only in the selected namespace. Its direct storage probes are a security
qualification, not private-memory adoption by native commands. A failed or
unfinished native session does not satisfy its idle precondition.

After all native workers are idle, the bounded two-client source check is:

```sh
"$TASK_VENV/bin/python" -m examples.preview_shared_source_qualification \
  --kubeconfig "$TASK_KUBECONFIG" --context "$TASK_CONTEXT" \
  --namespace "$TASK_NAMESPACE" --images "$TASK_DIST/images.json" \
  --output "$TASK_WORK/shared-source-001"
```

Its two opaque diagnostic records are outside the memory corpus. It verifies
one serialized source owner, retained feed coverage and independent caller
credentials. These probes do not insert the native workflow's answers.

For the initially chain-enabled combined deployment only:

```sh
test -f "$TASK_SOURCE/examples/preview_chain_observer.py"
env -u PYTHONPATH -u PYTHONHOME "$TASK_VENV/bin/python" \
  -m integration.single_node.preview_chain_qualification \
  --kubeconfig "$TASK_KUBECONFIG" --context "$TASK_CONTEXT" \
  --namespace "$TASK_NAMESPACE" --values "$TASK_WORK/preview-values.yaml" \
  --chart "$TASK_CHART" --qualification "$TASK_WORK/combined-001/report.json" \
  --observer "$TASK_SOURCE/examples/preview_chain_observer.py" \
  --output "$TASK_WORK/chain-001"
```

The qualifier first verifies isolation with the native node disabled, then
registers the exact inspected synthetic artifact under the programme's bounded
P13 authority. It retains signed intent, loses one submit response deliberately,
observes finality, replaces selected pods and performs independent readback.
It does not automatically resubmit an uncertain deploy. No public network,
funded transaction, private payload or unrelated commitment is authorized.
Stop if the observer is absent from the verified artifact; do not fetch a
replacement. Candidate 02 omitted this observer from its public archive; the
final packet must include its pinned bytes before this recipe is runnable.

## Upgrade, diagnostics and limits

For a compatible upgrade, retain values, session identities, PVCs and Secrets.
Verify the new artifacts/profile and run `Operator.owned()` and
`Operator.workloads()` against the explicit target before the reviewed Helm
upgrade. A configuration checksum causes the controlled restart. Do not rerun
fresh Secret creation, change a populated profile or select an empty alternate
provider for an accepted operation. Unsupported journal/profile rollback must
refuse startup; no migration is provided.

```sh
TASK_UPGRADE_VALUES=/operator-owned/reviewed-compatible-values.yaml
"$TASK_VENV/bin/python" -I - "$TASK_KUBECONFIG" "$TASK_CONTEXT" "$TASK_NAMESPACE" <<'PY'
import sys
from integration.single_node.reference_ops import Operator
owner = Operator(*sys.argv[1:])
owner.owned()
owner.workloads()
PY
helm upgrade omega "$TASK_CHART" \
  --kubeconfig "$TASK_KUBECONFIG" --kube-context "$TASK_CONTEXT" \
  --namespace "$TASK_NAMESPACE" -f "$TASK_UPGRADE_VALUES" \
  --wait --timeout 300s
```

Owner-local diagnostics are read-only and do not execute work:

```sh
kubectl --kubeconfig "$TASK_KUBECONFIG" --context "$TASK_CONTEXT" \
  -n "$TASK_NAMESPACE" exec omega-agent-0 -- \
  /opt/native/python/bin/python3.12 -m integration.single_node.diagnostics
```

Repeat for an explicitly selected owner pod; do not mount its journal elsewhere
while it writes. Diagnostics provide bounded counters, not factual task success
or proof that every dependency is healthy. Share only reviewed sanitized output.

Standard generated defaults are two agents; the single-agent helper selects one.
Both retain two sessions per agent, 24 inputs per
session, four pending inputs and one native child per agent. Input windows are
at most 120 seconds; ordinary tool dispatch keeps its 30-second bound, and
delegation uses its declared remaining input window. Configuration authority
expiry is generated once, normally 24 hours. The native qualifier additionally
caps operator submissions at 32 and observation at 30 minutes. None of those
limits renew accepted deadlines. History/feeds/workspace and other owners have
their own finite caps; an `OVERLOADED` result is not permission to enlarge them.

The AtomStorage/feed owner has an **aggregate limit of 512 source records**,
across the scopes served by that owner. This includes memory payloads, vectors
and enrollment records, administrative history/event records, task/result
payloads and any chunks used to store a larger record. It is not a limit of
512 user memories, nor an allowance of 512 records per agent or session. A
single native input can create several records. The 24-input session setting
is an admission ceiling; it does not guarantee that all four configured
sessions can each complete 24 inputs within the shared source capacity.

The historical dev17 workbench walkthrough reached this bound after the combined
workflow: `pin` and `task-context` completed, while a third `unpin` input failed
with storage `OVERLOADED` before model execution. That occurrence remains
incomplete, with its original accounting. The final dev19 minimal-profile
workbench completed pin/context/unpin/context and pause/resume/close; it does
not repair or reset the earlier exhausted deployment. Final combined-profile
workbench observations submit no further work.

On exhaustion, observe retained state, close or quiesce the affected session,
and preserve receipts, deadlines, journals and spent budgets. Further fresh
synthetic work requires a separately named task-owned namespace with fresh
state and newly generated authority. It does not reset, recover or migrate the
exhausted deployment. Do not delete records, reuse the failed identity in a
different store, or clear a journal to make a capacity failure appear recovered.
Scope/shared-source qualification uses fresh h19b state, separate from the
combined run; the minimal workbench uses solo19.

`update` creates immutable supersession. `forget` withdraws active visibility,
not stored bytes. Retained results/views remain captured, while current
disclosure authority can deny access. `unlink` retracts structure, not evidence.
Priority does not alter belief weight or rebuild vector indexes. Contrary
assessments remain retained; repeated source evidence is not fresh independent
support. File effects, task acceptance, result capture and acknowledgments have
separate commits. Lost replies do not establish that no effect happened.

## Quiesce, backup and fenced restore

Stop admission before maintenance. The installed `Operator` is the existing
scoped implementation; the broad historical `reference` CLI is intentionally
not packaged. This command stops all selected workloads and records the
observed cut in a private local file:

```sh
"$TASK_VENV/bin/python" -I - "$TASK_KUBECONFIG" "$TASK_CONTEXT" \
  "$TASK_NAMESPACE" "$TASK_WORK/quiesced.json" <<'PY'
import json, sys
from pathlib import Path
from integration.single_node.reference_ops import Operator
cut = Operator(*sys.argv[1:4]).quiesce()
Path(sys.argv[4]).write_text(json.dumps(cut, indent=2) + '\n')
PY
```

Backup also quiesces before opening any owner PVC; use a new destination:

```sh
TASK_BACKUP="$TASK_WORK/backup-001"
"$TASK_VENV/bin/python" -I - "$TASK_KUBECONFIG" "$TASK_CONTEXT" \
  "$TASK_NAMESPACE" "$TASK_BACKUP" <<'PY'
import sys
from integration.single_node.reference_ops import Operator
Operator(*sys.argv[1:4]).backup(sys.argv[4])
PY
```

The backup checkpoints each owner independently after writers stop. It is not
an atomic distributed transaction. It excludes credentials, TLS/signing keys,
policies and active approvals. It explicitly excludes the cryptographic
`f1r3node` PVC, which remains stopped and retained in the source namespace.
Keep backup directories private. The source namespace UID and stopped
StatefulSets must remain observable during restore.

Restore into a different new task-owned namespace, with no existing pods:

```sh
TASK_RESTORE_NAMESPACE=omega-ref-new-preview-restored
"$TASK_VENV/bin/python" -I - "$TASK_KUBECONFIG" "$TASK_CONTEXT" \
  "$TASK_RESTORE_NAMESPACE" "$TASK_BACKUP" <<'PY'
import json, sys
from integration.single_node.reference_ops import Operator
clone = Operator(*sys.argv[1:4])
clone.create()
print(json.dumps(clone.restore(sys.argv[4]), indent=2))
PY
```

This creates the included fresh PVCs and writes the persistent
`READ_ONLY_RECONCILIATION` fence. It does not install a Helm release or grant
effect authority. For a fenced preview host, retain the original shared/private
scopes, session selections and compatible images; disable every excluded owner
and all native/worker switches before the clone install:

```sh
"$TASK_VENV/bin/python" -I - "$TASK_WORK/preview-values.yaml" \
  "$TASK_BACKUP/manifest.json" "$TASK_WORK/restored-values.yaml" <<'PY'
import json, sys
from pathlib import Path
import yaml
values = yaml.safe_load(Path(sys.argv[1]).read_text())
backup = json.loads(Path(sys.argv[2]).read_text())
assert values['preview']['enabled'] is True
for role in backup['before']['workloads']:
    item = values['components'].setdefault(role, {})
    item['enabled'] = role in backup['owners']
    item.setdefault('config', {}).update(nativeEnabled=False, workerEnabled=False, test={})
values['testFaultsEnabled'] = False
if values['preview'].get('chain', {}).get('enabled'):
    values['preview']['chain'].update(enabled=False, nodeEnabled=False, isolationVerified=False, registration=None)
with open(sys.argv[3], 'x') as output:
    yaml.safe_dump(values, output, sort_keys=False)
PY
"$TASK_VENV/bin/fusion-create-secrets" \
  --preview-values "$TASK_WORK/restored-values.yaml" \
  --kubeconfig "$TASK_KUBECONFIG" --context "$TASK_CONTEXT" \
  --namespace "$TASK_RESTORE_NAMESPACE" \
  --directory "$TASK_WORK/restored-private-secrets"
helm upgrade --install omega "$TASK_CHART" \
  --kubeconfig "$TASK_KUBECONFIG" --kube-context "$TASK_CONTEXT" \
  --namespace "$TASK_RESTORE_NAMESPACE" -f "$TASK_WORK/restored-values.yaml" \
  --wait --timeout 300s
kubectl --kubeconfig "$TASK_KUBECONFIG" --context "$TASK_CONTEXT" \
  -n "$TASK_RESTORE_NAMESPACE" exec omega-agent-0 -- \
  /opt/native/python/bin/python3.12 -m integration.single_node.diagnostics
```

The clone disables chain activation and its excluded node, while retaining the
included commitment receipt PVC behind its fence. Fresh TLS credentials do not
restore signing authority. Require `restore_fenced=true` and compare bounded
owner counters with the backup.
The current **preview** fence permits health and operator diagnostics only;
module POSTs, session operations and workbench content retrieval are denied.
The historical workflow's `restore_probe` query/rebuild recipe is not a preview
readback API. No UI or API clears the fence. This runbook does not claim a
completed preview restore drill, automatic failover, active clone, node restore
or replay of model reservations, workspace appends, tasks, IRC sends or chain
deploys. Retain originals stopped until the actual drill is evaluated.

## Stop and retain state

Quiescing is the default reversible cleanup: stop the workbench and use the
scoped `Operator.quiesce()` command above. It retains the release, zero-replica
StatefulSets, PVCs, Secrets and failed/successful receipts for review. Do not
automatically reactivate a completed qualification or frozen campaign.

After any planned restore has been verified, a selected task release can be
uninstalled while retaining its PVC objects:

```sh
helm uninstall omega --kubeconfig "$TASK_KUBECONFIG" \
  --kube-context "$TASK_CONTEXT" --namespace "$TASK_NAMESPACE"
kubectl --kubeconfig "$TASK_KUBECONFIG" --context "$TASK_CONTEXT" \
  -n "$TASK_NAMESPACE" get pvc
```

Uninstall removes the original StatefulSets needed by the current restore
precondition; do not uninstall a source you still need to use for that drill.
Do not delete the namespace or PVCs as routine cleanup: local-path storage may
then remove the backing data. Never apply these commands to protected or
unrelated resources.

No command in this document was executed as part of drafting it. Final release
evidence must link actual reports, source/image identities, failures and cleanup
observations. Minimal, memory, combined, independent-provider, scope, recovery,
chain and fenced-restore results remain separate gates.

### Read-only stage observations

After quiescing every workload in the selected task namespace, this bounded
observer mounts only each stopped agent's own PVC read-only and deletes its
maintenance helpers. It reads at most two diagnostic files per agent; it does
not launch native work, replay tools, renew budgets or read worker logs.

```sh
"$TASK_VENV/bin/python" -m examples.preview_stage_observations \
  --kubeconfig "$TASK_KUBECONFIG" --context "$TASK_CONTEXT" \
  --namespace "$TASK_NAMESPACE" --output "$TASK_WORK/stage-observations.json"
```

Run from the extracted declared source. The final qualification's ownership
check passed, but method timing is `NOT_OBSERVED`: no best-effort timing files
were present. This is not zero latency. The exact historical cause is unknown.
Per-input round-trip and IRC setup/workflow measurements remain separate; nested
method durations, when present, must not be added as independent stage costs.
