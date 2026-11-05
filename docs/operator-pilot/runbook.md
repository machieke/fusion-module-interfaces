# Omega operator pilot

This is the current operator entry point for the completed V01–V40 pilot,
`READY_WITH_EXPLICIT_LIMITS`. Consult the [release record](../../evidence/operator-pilot/release-summary.json),
[acceptance ledger](../../evidence/integrated-service/pilot/acceptance.json) and
[qualification report](programme-report.md) for executed results and retained
failures. Earlier Q01–Q30 evidence remains historical. The fifteen module
families and X01/X02 denominator are unchanged.

Use a trusted operator, one explicitly selected existing k3s node and fresh
synthetic scopes. The model selection is recorded command proposals. No command
in this runbook authorizes a generative runtime, live generation, public chain,
public ingress, funded account or protected-state migration.

## Verify and install the declared artifacts

The qualified packet is `/data/fusion-operator-pilot-release/distribution21`,
with distribution manifest SHA-256
`5907fe306495bd404db90a8743c644fcfac6698cb4de08270c4ca43c0f3f8f60`.
The complete detached evidence directory is
`/data/fusion-operator-pilot-release/evidence-assembly/final21-detached12`,
with evidence manifest SHA-256
`3ed52933e22ef0b2f536e38257167ea9ebe67354ea1bdbaa2b14e6a55f8d52ff`.
These are the actual local handoff artifacts. Copy the complete authorized
bundle when relocating it; the Git review metadata alone omits the large and
restricted artifact files and is not a standalone verifier input. Packet21's
documentation is its frozen preparation snapshot; this runbook and the
detached report record subsequent terminal results without modifying that packet.

The packet contains immutable role image archives, their required base archive,
one Helm chart, exact source, operator/client wheels, an independent Go provider
artifact and dependency/license observations. Source identity and the exported
image digest are verified separately from live pod readiness. Helm, kubectl,
OpenSSL and Python 3.12 are operator prerequisites; the browser needs none of
them. Docker is needed only by the documented container-hosted k3s import path.

The public source/evidence selection is explicit. Historical
`operator-pilot-public-inputs/1` manifests accept up to 512 extra paths;
`operator-pilot-public-inputs/2` accepts up to 2,048. Both reject duplicate,
escaping and symlink paths. This is an offline publication bound, separate from
owner capacity or runtime authority. Neither format permits directory-wide
publication or replaces review of each file's disclosure suitability.

```sh
python3.12 -m venv /private/pilot-operator
/private/pilot-operator/bin/python -m pip install --no-index \
  --find-links /packet/wheelhouse \
  'fusion-preview-operator[preview-install,chain-key-setup]==0.4.0'
/private/pilot-operator/bin/fusion-pilot verify-artifacts /packet/distribution.json
mkdir /private/pilot-source
tar -xzf /packet/source.tar.gz -C /private/pilot-source
```

The verifier checks canonical manifests, external digests, all registered files,
OCI layers/configurations, image-declared source, exact wheel contents, explicit
profile selection and the Go binary/kit relationship. It executes no image.
Do not infer a missing archive from a developer's Docker cache. Restricted
native/model assets stay in the locally authorized artifact distribution;
publishing repository source does not grant redistribution rights to them.

Import the verified archives using the shipped
`deploy/single-node/import_workflow_images.py`. Select either the existing local
`--k3s-binary` or the explicitly identified task container with `--container`.
Supply `--manifest /packet/images.json --archive /packet/images.tar
--base-archive /packet/images.base.tar`. Do not install another cluster or use
an implicit current context.

```sh
fusion-pilot values --images /packet/images.json \
  --scope synthetic-pilot-example --namespace omega-ref-pilot-example \
  --output /private/pilot-values.yaml
fusion-pilot placement freeze \
  --chart /private/pilot-source/deploy/helm/omega-fusion \
  --images /packet/images.json --values /private/pilot-values.yaml \
  --namespace omega-ref-pilot-example --output /private/pilot-plan.json
fusion-pilot services --kubeconfig /private/kubeconfig --context SELECTED \
  --namespace omega-ref-pilot-example preflight
fusion-pilot services --kubeconfig /private/kubeconfig --context SELECTED \
  --namespace omega-ref-pilot-example install \
  --chart /private/pilot-source/deploy/helm/omega-fusion \
  --values /private/pilot-values.yaml --directory /private/fresh-secret-material
fusion-pilot placement verify-installed --plan /private/pilot-plan.json \
  --kubeconfig /private/kubeconfig --context SELECTED \
  --namespace omega-ref-pilot-example
```

Verify the complete detached evidence without starting services:

```sh
fusion-pilot verify-evidence verify /release/evidence.json \
  --output /private/pilot-evidence-verification.json
```

The qualified result is `VERIFIED_PARTIAL`: artifact and available evidence
checks pass, while private primary receipt proof remains unavailable. This is
separate from the locally observed A–H operational results. The verifier adds
no native identities from sanitized aggregate counts.

Installation creates fresh credentials and a separate current-writer authority
Secret. An upgrade reuses that authority and exact accepted template identities;
it must not rerun fresh Secret generation. The supplied example profile has
native workers disabled; the trusted `values` generator creates the explicit
fresh working composition. Configuration, permission and TLS changes are
reviewable inputs, never model-controlled arguments.

Every journal owner is a one-replica StatefulSet with its own retained PVC.
No consumer mounts another owner's journal. The optional browser gateway is a
stateless one-replica Deployment using Recreate; it has no PVC or Kubernetes
service account token. A gateway replacement requires login again; native
occurrences, captures and subscription progress remain with the application.

For an artifact update, install into a fresh operator virtual environment and
verify that packet first. Development wheels can share version `0.4.0` while
their source hashes differ; an existing environment satisfying that version
is not proof that it contains the selected wheel. Keep the old environment
and its manifest for retained observations.

For a qualified configuration-only change in the same synthetic installation,
freeze the reviewed values and apply the existing chart directly. Preserve
accepted profile/template identities, Secret references and writer authority;
do not run fresh secret generation. This is not an existing-state format upgrade.

```sh
fusion-pilot placement freeze \
  --chart /private/pilot-source/deploy/helm/omega-fusion \
  --images /packet/images.json --values /private/reviewed-existing-values.yaml \
  --namespace omega-ref-pilot-example --output /private/reconfiguration-plan.json
helm --kubeconfig /private/kubeconfig --kube-context SELECTED \
  upgrade omega /private/pilot-source/deploy/helm/omega-fusion \
  --namespace omega-ref-pilot-example -f /private/reviewed-existing-values.yaml \
  --wait --timeout 5m
fusion-pilot placement verify-installed --plan /private/reconfiguration-plan.json \
  --kubeconfig /private/kubeconfig --context SELECTED \
  --namespace omega-ref-pilot-example
```

A failed rollout remains an observation. It does not authorize a new occurrence,
deadline extension, reservation refund or replay of an uncertain effect.

## Use the private browser

Follow [browser-and-capacity.md](browser-and-capacity.md) to bind exact existing
scoped browser credentials to the optional `pilotWorkbench` configuration.
The operator applies the reviewed ConfigMap/Secret references and opens a
loopback-only port-forward to `service/omega-workbench`, port 8878. The browser
receives a scoped bootstrap credential, then a bounded authenticated session;
it never receives Kubernetes or provider credentials. Do not expose an Ingress,
NodePort or public unauthenticated listener. Host, Origin, CSRF, scope and current
owner authority are checked independently of transport reachability.

The bootstrap credential can create another bounded login until the operator
rotates or revokes it; it is not a single-use token. Gateway authentication is
ephemeral, with at most four concurrent logins per user and 64 in total. A
policy change immediately denies old sessions, but revoked entries occupy their
bounded slots until expiry or gateway replacement. A successful authorized
logout releases its own entry. A gateway restart
invalidates all logins while retaining application-owned work and cursors; it
does not establish durable-owner capacity recovery.

Allocation selects an admitted trusted template. Provider add/probe/enable is
an explicit operator action through the existing Registry. A readiness probe is
not provider conformance or permission. New provider selection uses the retained
template mechanism in [go-provider.md](go-provider.md); it does not rewrite an
old session or transfer a result between owners.

A browser reconnect observes its saved occurrence and cursor. It does not
submit an identical command as a retry. Current views, retained views,
withdrawn memories, sealed history, contrary belief and attention scores are
labelled separately. Unverified workspace notes do not become evidence.

## Operate bounded work windows

Inspect owner-specific capacity before allocating. Units differ: bytes,
retained objects, attempts, sessions and reservations are not one percentage.
Unknown dimensions remain unknown. Application estimates cannot promise an
atomic reservation across all owners. Admission refusal preserves partial
acceptance, old results and spent reservations.

Use `fusion-pilot services ... capacity`, `providers --provider-action headroom`
and the browser's current observations. After work, close only complete
sessions, inspect unknown effects, preview/seal exact Registry epochs and
preview/apply only eligible derived cleanup. Sealing retains audit facts and
bindings; cleanup does not refund retention or erase authoritative state.

The four-window qualifier is `fusion-pilot qualify-endurance`. It freezes 160
meaningful operator inputs, with separately counted registered-recipe inputs
and internal task/completion inputs. It has a finite wall-time bound, no reset,
no deadline renewal and no replacement of a failed occurrence. Historical
captures are compared after each maintenance window. Private windows do not
gain workspace, delegation or NAL authority from the shared template.
The frozen workload selects inspection in the first shared window and named
NAL deduction after delegation in the later shared window. A growing query
result can exceed inspection's existing three-observation domain; the qualifier
does not truncate results, widen that profile or fall back after refusal.

First wait for the qualifier and every child process to exit and be reaped.
Record any signal, exit status and incomplete observation. An EXIT trap must
not stop owners while a qualification child can still submit or observe work.
Use the [reviewed bounded supervisor](../../artifacts/operator-pilot/endurance17-supervision-source/review.md)
for this qualification; its outer observation bound never changes an accepted
input deadline. Then collect diagnostics before stopping the owned pods.
These existing modules only
read the selected owner's local state and process counters; they do not submit
work or consume an execution reservation. Keep a separate finite observer bound
and retain any missing or truncated observations. For example:

```sh
kubectl --kubeconfig /private/kubeconfig --context SELECTED \
  -n omega-ref-pilot-example exec omega-agent-0 -- \
  /opt/native/python/bin/python3.12 -m integration.single_node.sustained_diagnostics
kubectl --kubeconfig /private/kubeconfig --context SELECTED \
  -n omega-ref-pilot-example exec fusion-storage-0 -- \
  /opt/native/python/bin/python3.12 -m integration.single_node.measure
```

Repeat only for explicitly selected owners in this installation. Samples taken
sequentially are not one atomic cut. Native-stage durations may nest; summing
them does not produce end-to-end latency. Process samples include the observer,
and measured file sizes are distinct from logical retention charges. An observer
timeout never renews a native deadline or authorizes resubmission.

Registered recipes and decisions are described in
[registered-workflows.md](registered-workflows.md). A checkpoint binds an exact
plan version and current prerequisites. Only unstarted suffixes can be amended.
Approval neither extends deadlines nor resolves an uncertain earlier effect.

## Maintain, restore and investigate

[maintenance.md](maintenance.md) specifies dependency closure, base-plus-delta
backups, independent full-cut verification, derived reclamation, disposable
format-copy upgrade and planned writer handover. Old restore remains
observation-only. Writable handover is a distinct fresh-synthetic profile with
an external authority outside every restored PVC. The original stays stopped
and retained. The Go reference owner does not advertise this handover profile.

Plan/apply compares exact current heads. A changed source, missing base, corrupt
archive, new pin, revocation, unknown schema or unproven fence refuses. Keep the
failure and original export; do not delete old receipts or accept a new clock
value to make a plan current. There is no destructive rollback after new work
on a replacement. Observe and retain the state; do not start both writers.

[failure-semantics.md](failure-semantics.md) records transport retry and clock
behavior. Lost mutation replies require exact original identity reconciliation;
observation expiry does not authorize resubmission. An undispatched expired
input can terminalize; an already started uncertain input stays fenced.
Uncertain external sends are never automatically repeated. Chain commitment
requires separate exact-result approval and preserves the saved signed intent.
The [installed chain reader readiness option](chain-readiness.md) performs bounded
consumer-path health observations before one retained-artifact read. It neither
retries that read nor renews the original effect deadline or submits again.

Two separately bounded qualification helpers exercise narrower failure
boundaries without adding Omega inputs: [Attention suspension](attention-suspension-supplement.md)
targets one verified task container and preserves its spent reservation;
[pool and subscription continuity](live-pool-subscription-supplement.md) carries
an existing connection and subscription through explicit maintenance and a
scoped credential change. The latter applies owner-local policy as a trusted
operator action; it does not claim automatic Secret hot reload. Their own
maintenance windows never extend the accepted work they observe.

Use `fusion-pilot dependencies`, `backup`, `upgrade-copy`, `handover` and
`verify-evidence` with `--help` for their closed commands. Raw private fragments,
Secrets, TLS keys, journals, backups and source-identifying private hashes are
not publication material. Publish only approved sanitized evidence.

## Stop and retain

```sh
fusion-pilot services --kubeconfig /private/kubeconfig --context SELECTED \
  --namespace omega-ref-pilot-example stop
```

This stops gateway admission and all selected writers, preserving PVCs and
unknown outcomes. It is not erasure. Do not delete protected namespaces, old
campaigns, old images or any PVC merely because it is stopped. Compare the
protected before/after object inventories within their recorded scope;
Kubernetes metadata equality alone is not a byte-for-byte PVC claim.

Before considering uninstall of a task-owned release, make a read-only preview
and save the exact named PVC inventory in a private operator directory:

```sh
kubectl --kubeconfig /private/kubeconfig --context SELECTED \
  -n omega-ref-pilot-example get statefulsets,pvcs -o yaml \
  > /private/pilot-retention-before.yaml
helm --kubeconfig /private/kubeconfig --kube-context SELECTED \
  get manifest omega --namespace omega-ref-pilot-example \
  > /private/pilot-release-before.yaml
helm --kubeconfig /private/kubeconfig --kube-context SELECTED \
  uninstall omega --namespace omega-ref-pilot-example \
  --dry-run --keep-history --no-hooks
```

The Helm dry run identifies the selected release; it does not prove retention.
Review the exact installed StatefulSets for `whenDeleted: Retain` and
`whenScaled: Retain`, the saved PVC names/UIDs and the release resource list.
Refuse if any protected resource, unexpected direct PVC deletion or unproven
retention is present. These commands do not uninstall or delete state. Keep
Secrets, authority and Helm history with the retained state; reinstalling fresh
credentials against old PVCs is not a supported rollback. This programme stops
and retains its installations rather than uninstalling them.

The current assurance report must name unresolved scanner findings, unsupported
ecosystems, configured versus observed resource controls and hosted CI status.
Separate pods and TLS do not prove protection from a malicious host, multi-node
availability, kernel CPU quotas or production readiness.

## Reproduce the artifact-only adopter rehearsal

The packet includes the reviewed [current H rehearsal recipe](../../artifacts/operator-pilot/h21-rehearsal-source/commands.md)
and its disabled plan. It uses a clean installed SDK, a separate browser mount
namespace and an extracted Go kit. The browser and provider phases use two
fresh synthetic namespaces sequentially. Its bounded native walkthrough,
provider replacement, captured-result readback and maintenance are separate
from the preceding offline installation check.

The [current clean-install prerequisite](../../artifacts/operator-pilot/h20-clean-install-source/commands.md)
includes its exact standalone script and disabled plan. Execute that script
from the packet, retain its result, then bind the native rehearsal to those
installed environments. Neither step requires an unpublished author script.

Follow the recipe's detached binding and invocation instructions. The exact
packet, clean-install result and selected prerequisites must be bound before
execution. The qualification sources must run from the packet. The disabled
plan itself is neither an executed result nor authorization for live generation.
Keep all failure records and do not resubmit an expired or uncertain occurrence.

## Review the delivered pilot

1. Verify the exact distribution and detached evidence digests before installing.
   Keep the implementation commit, tested source manifests and later evidence
   commit distinct. Do not replace an immutable packet with a newer checkout.
2. Read the eight acceptance stories and their original failure records. Check
   the source/image/package combination actually used by each story; static
   equivalence does not mean a rerun occurred.
3. Inspect Registry growth, all owner capacity observations and the four-window
   native count. Keep direct inputs, internal inputs, test invocations and
   complete workflows separate.
4. Review the derived cleanup, backup and handover fences before any writable
   synthetic replacement. Confirm that unknown effects, original deadlines and
   spent reservations remain retained.
5. Review browser and provider authority, supported profiles, exact workflow
   approval and independent chain readback. Finality alone is not a successful
   independent artifact read.
6. Read the scanner exceptions and enforcement limits. Public verification can
   remain partial when private primary evidence is withheld; a sanitized
   summary does not provide access to those receipts or journals.
7. Confirm zero live generation, task-only cleanup, retained PVCs and the exact
   scope of the protected-resource comparison. A later live campaign requires
   separate explicit approval.

The final-packet H qualification also ships its
[current bounded detached launch commands](../../artifacts/operator-pilot/h21-supervision-source/commands.md).
The wrapper and inner clean/native entrypoints are all selected from the packet.
This task-local rehearsal supervisor preserves the original work bounds and
waits for child termination; it does not schedule application work or authorize
another attempt. Its historical compiled-only predecessor remains inspection
evidence and is not the recommended command.

H19’s first clean installation failed at a source assertion that incorrectly denied a manifest-pinned operator helper. Its report and packet remain immutable. The [H20 successor](../../artifacts/operator-pilot/h20-clean-install-source/review.json) corrects only this check, preserving caller/provider isolation and all native/runtime bytes. Use the [successor supervisor commands](../../artifacts/operator-pilot/h20-supervision-source/commands.md) for packet20; the native H19 recipe remains unchanged. Qualification-source checks passed 19 methods; complete installation and native execution are separate pending gates at packet freeze.

The H21 successor explicitly mounts the same pinned browser executable at a regular sandbox-local path. It adds a disconnected tool preflight before cluster operations and selects fresh adopter21 scopes. The [qualification review](../../artifacts/operator-pilot/h21-rehearsal-source/preparation-review.json) distinguishes the authored-page tool smoke from actual native acceptance. H19/H20 failures and completed captures remain immutable. Use the [H21 commands](../../artifacts/operator-pilot/h21-supervision-source/commands.md) with packet21 and a new private plan; no old invocation is retried.
