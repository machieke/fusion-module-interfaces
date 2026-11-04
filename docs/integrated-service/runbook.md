# Integrated single-node service operator runbook

Use the [gate ledger](../../evidence/integrated-service/gates.json) for current
qualification status and [contracts](contracts.md) for the exact selections.
The [qualification recipes](qualification.md) name the bounded executable lanes,
required assets and the distinction between installed and source-export checks.
The Q01–Q30 programme continues `bf8e87d7416cab6954a702d64d12cdfcf7b976d1`;
Phase 2/3 remain the baseline. The release is qualified with the explicit limits
in the primary report and detached artifact binding. No current
command authorizes text generation, a public deployment or a writable restore.

## Prerequisites and installation

Select the existing single-node k3s context explicitly. Installation needs the
local distribution, CPython 3.12, Helm, kubectl, OpenSSL and the existing image
import adapter. Build recipes additionally need the pinned native/E5/Chroma/DeTTa
assets and their declared toolchains. Restricted assets are not downloaded by
installation or published to a new registry. The Omega image contains neither
E5 inference libraries/assets nor a generative model.

`distribution.json` and its adjacent SHA-256 bind the chart, four role images,
OCI delta and required base archive, eight wheels, Go binary/source package,
public source and dependency inventories. Verify both archives; a cached node
image alone is not the offline distribution. Keep immutable hardlinked archives
immutable under every filename. Assembly verification alone is not a workflow
pass. Actual scenario/image bindings are recorded separately in the evidence.

From the distribution directory, unset any developer `PYTHONPATH`, install the
operator without network dependency resolution, and extract its public recipes:

```sh
unset PYTHONPATH
python3.12 -m venv /tmp/omega-review-operator
/tmp/omega-review-operator/bin/pip install --no-index --find-links wheelhouse \
  'fusion-preview-operator[preview-install,artifact-verification,chain-key-setup]==0.3.0'
/tmp/omega-review-operator/bin/fusion-verify-artifacts distribution.json
/tmp/omega-review-operator/bin/fusion-import-images \
  --container omega-fusion-k3s --manifest images.json --archive images.tar \
  --base-archive images.base.tar
mkdir source
tar -xzf source.tar.gz -C source
cd source
/tmp/omega-review-operator/bin/python -m integration.single_node.integrated_values \
  --images ../images.json --scope synthetic-review-01 --mode combined \
  --native-mode prepared --transport pooled --history compact --archive \
  --envelopes --nal-envelopes --search-repair --output ../fresh-values.yaml
/tmp/omega-review-operator/bin/fusion-sustained \
  --kubeconfig /absolute/selected-kubeconfig --context default \
  --namespace omega-ref-review-01 install \
  --chart ../omega-fusion-0.7.0-dev.1.tgz --values ../fresh-values.yaml \
  --directory /absolute/new-private-secret-directory
```

Use the filenames bound in the selected manifest. The source archive is an
operator recipe, never a pod mount. The installer creates the declared Secret
references once. ConfigMaps hold non-secret settings; each service owns its
PVC. ClusterIP/DNS and authenticated HTTPS connect the module ports. The
optional commitment adapter uses the pinned node's isolated native HTTP RPC;
that is a separate explicitly checked edge, not a second module transport.

One replica per journal owner is required, with the chart's controlled update
strategy and exclusive writer locks. Health checks do not consume work budgets.
PVCs retain journals, captures and archive segments after scale-down or workload
deletion. `upgrade` reuses existing Secrets and state. Choose quotas and optional
profiles before creating fresh journals; incompatible owner seals refuse startup.
Do not migrate historical state by editing the values file.

## Ordinary native work

Allocate a session from an approved template and retain the returned session ID:

```sh
fusion-sustained --kubeconfig KUBE --context default --namespace omega-ref-review-01 \
  allocate --template shared --identity review-session-1
fusion-sustained --kubeconfig KUBE --context default --namespace omega-ref-review-01 \
  submit --session SESSION --identity review-input-1 \
  --text 'remember The synthetic amber compass is stored in chest willow'
fusion-sustained --kubeconfig KUBE --context default --namespace omega-ref-review-01 \
  submit --session SESSION --identity review-input-2 \
  --text 'query synthetic amber compass storage'
fusion-sustained --kubeconfig KUBE --context default --namespace omega-ref-review-01 \
  observe --session SESSION --content
```

The selected recorded provider proposes the operator's command text. The actual
native loop, parser, batch admission, E5 encoding, Search, payload hydration and
cognitive tools execute. A response fixture never supplies a tool result.
Observe the first completion before submitting a dependent command. Ordinary
inputs require no ConfigMap edits. Equal text with a new intentional occurrence
uses a new identity; retrying an identity must keep its original payload.
Refresh/observe is never a submit retry.

Use `episodes current`, `task-context`, the existing native memory handles,
`delegate B <query>` and `inspect-atom <captured task handle>` as declared by
current capabilities. Delegation sends the query, not an answer reference.
Inspection consumes the actual returned task artifact. Broader MeTTa execution
and arbitrary paths, imports, endpoints or credentials remain unavailable.

Run the installed local workbench against the same APIs:

```sh
fusion-preview-workbench --kubeconfig KUBE --context default \
  --namespace omega-ref-review-01 --port 8765 \
  --access-file /absolute/new-private-workbench-access.json
```

Open its loopback URL and enter the separately generated local token. Keep the
access file and browser recordings private. The UI offers typed capabilities,
metadata-only preflight, captured results, current owner observations, lifecycle
controls and bounded maintenance. A visible control or successful preflight
grants no authority. Do not publish raw browser logs containing access material.

## Trusted selection and placement

The optional `--registry` setting requires separate operator admission of each
pinned provider in a template, followed by a bounded readiness observation and
enablement. These are supported CLI operations:

```sh
fusion-sustained --kubeconfig KUBE --context default --namespace omega-ref-review-01 \
  providers --provider shared-fusion-storage --provider-action add --identity storage-admission-1
fusion-sustained --kubeconfig KUBE --context default --namespace omega-ref-review-01 \
  providers --provider shared-fusion-storage --provider-action probe --identity storage-probe-1
fusion-sustained --kubeconfig KUBE --context default --namespace omega-ref-review-01 \
  providers --provider shared-fusion-storage --provider-action enable --identity storage-enable-1
```

Repeat for the selected template's providers. A probe is an explicit bounded
health observation, not an execution or a conformance certificate. Readiness
expires after at most five minutes. Replaying an unknown probe does not contact
the provider again or refresh its time. Do not probe needlessly before every
input. Provider records, bindings and actions consume finite retained capacity:
32 records, 256 actions and one MiB metadata, also charged to application bytes.
The sustained qualification reached the byte limit after its successful core
workload and follow-up security checks; new admission refused while old reads
remained available. No automatic pruning or migration is provided.

`inspect`, `selected`, `disable`, `drain` and `retire` expose distinct states.
Disable/drain block new selection/input assignment; accepted work and old
captures retain their original bindings. Current provider authorization remains
independent. Retirement requires retained observation access or an explicit
unavailability declaration. An admitted record's implementation/profile cannot
be overwritten. Add an explicitly approved replacement record for new sessions;
never fail over an uncertain mutation to an empty journal.

The extracted `integration.single_node.placement` entrypoint supports `freeze`,
`compile`, `diff`, `verify-installed`, `freeze-local` and `compile-local` as shown
by its help. A plan pins chart/config/image/profile/owner-volume edges; its
Mermaid diagram follows those edges. Freeze/compile do not install or execute.
Verification observes actual pod image IDs, source packages, service selection
and TLS bindings. Only supported compositions pass; all qualified placements
remain on one machine/node.

## Bounds, recovery and maintenance

The resident selection reuses an actual native interpreter within one session:
eight inputs per incarnation, 30 seconds idle, 15 minutes lifetime and 128
retained incarnations by default. There is one child per agent owner. Prepared
overlays reuse immutable verified source; mutable authority and response checks
still run. HTTPS reuse is bounded to 16 connections, 500 ms idle, 60 seconds
lifetime and 64 requests per connection. The pool never retries a lost mutation.

`worker-control --worker-action drain|recycle|resume|observe`, `pause`, `resume`,
`cancel`, `reconcile` and `close` use explicit identities where applicable.
An undispatched cancellation/expiry can terminalize safely. Started uncertainty
fences dependent work. Only an authoritative committed projection can reconcile
completion. Closing/recycling never refunds reservations, deadlines, occurrence
count or retained-session capacity. Independent eligible sessions may progress.

Read `current`, `capacity`, `capabilities` and continuation observations before
acting. Current views and old captures are separate. Metadata-only diagnostics
report unknown/truncated observations explicitly. Registry capacity is not the
same as retained-session, source-record, model, socket or chain capacity.
The sustained fresh profile selects 16 retained sessions; the historical default
remains eight. Owner startup seals prevent incompatible quota changes.

Archive is copy-and-verify within AtomStorage. Existing refs still use its
current authenticated read ports. It does not reclaim total retention, remove
hot payloads, erase history or create an independent backup. Search maintenance
uses its authenticated authoritative feeds; a missing index is an explicit
failure, never an empty successful answer. Preview a repair plan, then pass that
exact plan and an explicit identity/deadline using `search-maintenance
--request-file FILE`. Observe the same identity after a lost reply. The UI uses
the same protocol and preserves its original 120-second maintenance window.
Do not modify source records or resubmit an external effect to repair a view.

For quiesced backup and an observation-only restore drill, use the existing
installed operator and extracted recipe:

```sh
fusion-sustained --kubeconfig KUBE --context default --namespace omega-ref-review-01 \
  backup --directory /absolute/new-private-backup
python -m integration.single_node.sustained_restore_qualification \
  --kubeconfig KUBE --context default --original omega-ref-review-01 \
  --clone omega-ref-review-01-fenced --values ../fresh-values.yaml \
  --chart ../omega-fusion-0.7.0-dev.1.tgz --directory /absolute/new-private-restore-drill
```

The drill takes its own fresh quiesced backup and checks the restored owner
observations against the retained originals. It never enables a restored
executor. Private backup directories stay mode0700. Secrets, approvals and
node-local cryptographic state are excluded. The original node PVC remains
stopped; application commitment receipts can be restored without restoring a
chain node. Missing authoritative data or broken dependency/profile seals refuse
restore. A partial extraction is fenced before any payload is written.

## Qualification, artifacts and cleanup

Use `examples.integrated_baseline` for the frozen fourteen-input comparison,
`integrated_sustained` for the eighty-input retained workload, and the explicitly
named recovery/rotation/notification/chain examples in the artifact. Each records
its actual inputs and stops its owned namespace. Heavy native/E5/chain tests
must run serially on this node. The four final comparison plans vary only cold
per-input versus prepared resident execution; OS/model caches are not claimed
cold. Per-operation samples, censored failures, nested spans and trace truncation
remain separate. Recorded-model latency is not generative-model latency or an SLA.

The Go client is `go/omega-client`; its extracted build requires no Python agent
or developer checkout. The independent atomic-file provider remains a
**CONTRACT_FIXTURE**, qualified separately from real DeTTa. Real E5 placement
qualification likewise separates encoder placement from retrieval placement.
The old whole-DeTTa source guard failure remains open; no assertion was removed
to turn it into a pass. Vulnerability scanning and hosted CI are reported only
when actually observed. License entries without verified attribution remain
`NOASSERTION`.

Stop task workloads with `fusion-sustained ... stop`. Retain the review PVCs and
failed/uncertain receipts listed in the final evidence; delete none to manufacture
capacity. Cleanup never targets `omega-demo`, historical review installations or
the frozen campaign. No public registry release, multi-node qualification,
production isolation claim, live-model run or writable migration follows from
this distribution. `ADDITIONAL_LIVE_GENERATIONS=0`.
