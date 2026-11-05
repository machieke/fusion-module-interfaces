# Retention, derived maintenance and planned synthetic handover

This track extends the existing application, Search and backup owners. It adds
no scheduler, authoritative knowledge graph or general garbage collector. All
commands below target fresh synthetic state. The original deployment, private
backup packets and failed observations remain retained. The protected
`omega-demo` and frozen model campaign are outside this procedure.

## Contracts and limits

| Surface | Authority and retained state | Bounded change |
| --- | --- | --- |
| `quiesced-owner-dependency-inventory/1` | Existing owner export under its maintenance lock; exact file/table head, immutable refs, retained Search snapshots, conservative unknown-table retention | Head-bound pages of at most 128 entries; 65,536 rows and 32 MiB manifest limit |
| `expired-unpublished-search-reclamation/1` | Existing Search owner; current authenticated source ports, publication head and original generation receipt | Only expired, unpublished `index/` bytes; all published generations remain pinned; 16 generations, 256 files, 64 MiB and 32 receipts |
| `closed-session-derived-reclamation/1` | Existing application owner; closed/archived session, no supervisor work, caller lock, current per-scope operator permission | Verified history materializations, exact duplicate startup diagnostics, reconstructible stale prepared overlays; 128 files, 16 MiB, 32 receipts |
| `synthetic-incremental-owner-backup/1` | Existing quiesced full exports, with credentials and active execution authority excluded | 64 KiB content chunks, at most eight linked packets and 32 owners; exact manifest/base identities; bounded flatten |
| `registry-exact-wire-to-interned-copy/1` | Quiesced `/1` Registry export copied into a fresh, fenced output; original export untouched | Exact decoded inventories and original receipt-wire verification under `/2` bounds; no activation or completion of unknown probes |
| `planned-synthetic-writer-handover/1` | Current external writer authority outside every restored PVC; installed Operator observes Kubernetes and current owner exports | One drained original and one replacement, monotonically increasing generation; historical effects read-only; new shared synthetic memory/history/workspace sessions only |

Cleanup does not erase authoritative DeTTa payloads, history roots, accepted
views, invocation identities, prior captures, last results or spent attempts.
Deleting an index does not refund its generation reservation. Application
cleanup reserves its receipt and completion bytes in the application owner's
finite accounting **before** its independent cache/file commit. Missing source
bytes, changed heads/pins, symlinks, current revocation and unsupported shapes
cause refusal. A changed prepared overlay is retained unless every byte can be
reconstructed from the current retained immutable entry.

`unlinked_allocated_bytes` measures unlinked file blocks. It is not proof of
physical disk recovery while another process retains file handles; SQLite
freelist space and exact replay receipts can also retain storage. Reports keep
physical recovery unknown where it was not independently measured.

Dependency extraction runs inside the stopped owner, not inside a foreign
application consumer. Cross-owner closure uses declared, authenticated
AtomStorage `get` and Search `ready` ports. Private dependency fragments are
verified by a currently authorized caller for that scope and merged against the
original inventory head. Native history roots and chunks are hydrated through
their actual immutable format. An exported inventory alone says
`cross_owner_closure=UNVERIFIED`; it never licenses reclamation or activation.

## Installed operator commands

Use the declared Python 3.12 operator environment with the distribution's
dependencies and modules on its import path. Do not use the system Python 3.8.
The concrete development operator executable was
`/tmp/omega-integrated-operator-dev18/bin/python`; this machine path is an
observation, not a portable installation dependency. The standalone Secret
installer is launched using `sys.executable` from the operator driver.

The existing CLI forwards closed requests to the authenticated owner. Request
files contain no token or arbitrary path. For application cleanup, first submit
`{"operation":"inventory","session":"SESSION","body":{}}`; then pass its
exact `selection` to `plan`, review that plan, and use one stable `identity`
with the returned `plan` for `apply` and `observe`.

```bash
python -m integration.single_node.sustained_cli \
  --kubeconfig KUBE --context default --namespace TASK_SOURCE \
  --agent omega-agent derived-maintenance --request-file /absolute/request.json
```

Search uses the existing maintenance route and CLI action `search-maintenance`.
Select `profile: expired-unpublished-search-reclamation/1`, the explicit
synthetic `scope`, and `operation: planCleanup` with
`args: [LIFECYCLE_HEAD, [GENERATION_ID]]`. `applyCleanup` and `observeCleanup`
take `[LIFECYCLE_HEAD, EXACT_PLAN, STABLE_IDENTITY]`. IDs originate from actual
owner receipts; the owner rechecks eligibility independently.

```bash
python -m integration.single_node.pilot_backup pack --help
python -m integration.single_node.pilot_backup flatten --help
python -m integration.single_node.pilot_dependency_operator extract \
  --full /private/full-cut --output /private/inventories.json
python -m integration.single_node.pilot_dependency_operator verify \
  --inventory /private/authorized-fragments.json \
  --ports /private/current-port-config.json --output /private/closure.json
python -m integration.single_node.pilot_upgrade \
  --source /private/full-cut/omega-agent.tar.gz --sha256 EXPORT_SHA256 --dry-run
python -m integration.single_node.pilot_upgrade \
  --source /private/full-cut/omega-agent.tar.gz --sha256 EXPORT_SHA256 \
  --destination /private/fresh-format-copy
```

The copy upgrader supports `/1` exports, including empty, representative,
private, archived and unresolved-session state. It refuses unsupported
profiles, changed bytes and an existing destination. A full `/1` Registry of
unknown probes can exceed `/2`'s finite active representation: it is refused as
`OVERLOADED`, leaving the output fenced and without a completed upgrade
manifest. The original remains exact. Unknown probes are not sealed or
re-probed to manufacture room.

## Concrete bounded acceptance driver

`examples/pilot_handover.py` uses actual native inputs and existing owner ports;
its recorded model proposes only those inputs as commands. It must start from
an empty, freshly installed source. It does not resume by resubmitting old
inputs, alter their deadlines or reconstruct a tool result from an expected
answer. Failed runs keep their reports, journals and original identities.
The development-only `--continue-after-inert-search-kill` switch accepts only
the recorded pre-kill Search fault stage, verifies the four earlier captures
and exact image/configuration/authority bindings, and uses the same expired
Search reservation. It preserves each unsuccessful operator observation and
the original one-hour run bound; it is not a general restart or retry facility.

The source selection is restricted before any native allocation: Registry
`trusted-provider-lifecycle/1`; private scopes, immutable administrative history,
archive and maintenance enabled; inspection/task/chain/channel/Go execution
disabled. Inspection envelope seal fields may remain as historical identity
fields, but `inspection.enabled` is false when task execution is disabled.
New-epoch shared-only admission keeps retained private selections readable and
avoids increasing the unchanged 32-record Registry bound.

```bash
fusion-pilot handover-values \
  --images /absolute/tested-distribution/images.json \
  --scope synthetic-handover-review --namespace omega-ref-pilot-handover-fresh \
  --output /private/source-values.yaml

fusion-pilot qualify-handover \
  --kubeconfig /absolute/task-kubeconfig --context default \
  --namespace omega-ref-pilot-handover-fresh \
  --replacement omega-ref-pilot-handover-fresh-next \
  --chart /absolute/tested-distribution/deploy/helm/omega-fusion \
  --values /private/source-values.yaml \
  --images /absolute/tested-distribution/images.json \
  --directory /private/fresh-handover-run \
  --authority-file /private/source-secrets/writer-authority-state.json \
  --task operator-pilot-fresh
```

These commands are included in the installed operator package. The qualification
driver invokes the same packaged Secret recipe with its selected isolated
Python; it does not require a developer checkout beside `site-packages`.
Freeze and verify the exact image/chart placement before native admission.
The required `--images` selects the exact verified image manifest. The driver
checks actual source pods before the first native input and checks replacement
pods after active readiness, before constructing the new native runner. Its
private primary report retains both installed source/image observations,
configuration and TLS checks; a mismatch stops new admission.
After the four new inputs complete, the driver replaces the activated caller
pod and verifies its installed placement again. Old shared/private captures,
new captures and the retained uncertain occurrence must remain exact across
that restart. This adds no native input or model reservation. Persisted
current-generation Registry records are accepted at restart only when their
complete selected records match and their identities are absent from the
historical fence; historical aliases and changed bindings still refuse.
The example namespace must be newly created and explicitly labelled for this
task; the stopped development namespaces are retained historical evidence.

After a successful cutover, the distributed operator recipe can prepare scoped
browser observation without changing the retained handover values or old Secret
material:

```bash
/absolute/installed-operator/bin/python -I \
  /absolute/tested-distribution/examples/pilot_handover_browser.py \
  --values /private/fresh-handover-run/replacement-active.yaml \
  --secrets /private/fresh-handover-run/replacement-secrets \
  --source-namespace omega-ref-pilot-handover-fresh \
  --replacement omega-ref-pilot-handover-fresh-next \
  --output /private/fresh-browser-provisioning
```

This is an offline recipe, not a deployment or fencing proof. Its outputs contain
new credentials and must remain private. It reuses the installed provisioning
module, adds only the selected shared-scope browser keys, preserves every old
Secret value, and refuses foreign namespaces, old epochs, existing browser keys
and output reuse. The gateway reads only the separately referenced current
authority key; it receives no owner journal or Kubernetes credential.

Applying the resulting values changes all twelve owner configuration checksums.
Treat that as a separate graceful configuration rollout after the newly admitted
sessions are closed. Verify exact installed images and current authority again,
then compare old/private/new captures, accepted bindings and spent uncertain
accounting across the restart before using the browser. The browser selects the
retained new-generation shared session; its separate shared actor cannot read
private sessions. Its authority display is read-only and cannot retire or
activate writers. No additional native input is needed for these observations.

The external authority file is a separately provisioned trusted operator file,
not an imported owner journal. The chart mounts its current Secret read-only at
`/writer-authority`. The installed observer checks exact namespace UIDs,
task-ownership labels, one writer per logical role, current stopped-PVC
re-exports, original/replacement credential separation, exact deny-all policies
and an actual refused stale startup. Neither a caller boolean nor a copied
ConfigMap is evidence of fencing. Old effects are indexed and rejected before
mutating route dispatch. Session observations retain their original scope
checks; replacement allocation does not authorize another principal's history.

For the explicit pilot restore selection, Search observations use
`copy-backed-restored-search-observation/1`. Pinned Chroma changes lock rows and
derived index allocation bytes when opening a persisted index for reads. Before
the read service starts, the Search owner copies at most three of its own
configured memory roots (8,192 files / 64 MiB total) into private ephemeral
directories under its own `/run`. It verifies every source and copied byte,
rejects non-normal paths and symlinks, and requires the restore fence to deny
external effect authority. Current policy, source ports, retained snapshots and
generation identities remain unchanged. Chroma may update this disposable copy;
the imported checkpoint remains exact. No generation is built and no caller or
other owner receives these files. Normal activated service uses its own durable
state again. Oversized restored selections refuse this bounded observation path.

The driver prepares native shared/private captures and an actual archived
payload; produces a Search index through its port, interrupts its publication,
waits for its original expiry, cleans its derived bytes and rebuilds through
the authoritative feed. A recorded-model process is killed after durable
reservation and before its backend entry; that unknown slot stays spent.
It takes a base and two deltas, independently compares each exact full cut,
performs the disposable format copy, restores observation-only owners, checks
scoped closure, and performs the planned writer transition. The positive
replacement drill admits new shared native remember/query/history/workspace
inputs. Post-activation observations hydrate both the original archived shared
payload and retained private payload through current authenticated AtomStorage
ports; the other principal must still be refused. These reads do not submit
references as answers to a native query. Old captures, the unknown reservation,
stale credentials, historical completion refusal and the original's stopped
state are checked separately.
After session closure, the driver observes the native child's exit through the
existing cleanup inventory port for at most 30 seconds within the original
programme deadline. It records the positive candidate selection and plan before
one cleanup apply, then verifies the retained receipt and hydrates the exact
authoritative history references. Expiry, an empty selection, or a lost apply
response stops this stage; none authorizes another apply or a new native input.
Fault injection uses the pinned single-node container runtime's administrative
signal operation. Before SIGKILL it binds namespace ownership and UID, task
label, pod/controller UID, release/component labels, container ID and image
against current Kubernetes and containerd observations. The initial attempt to
signal namespace PID 1 from inside its own container was ineffective and is
retained as a failed test; it is not counted as process-kill evidence.

## Evidence and limitations

The isolated unit suite uses real SQLite, fsync, actual child-process SIGKILL,
the real Chroma library and existing contract owners. Feed/vector fixtures,
overlay-builder fixtures and synthetic cluster-observer callbacks are explicitly
labelled; they do not establish deployed handover. The executable deployment
driver is a separate gate. Its `report.json` is authoritative for which steps
actually ran; a stopped or failed driver is not a completed Story E.

The dev04 handover drill reached actual shared/private dependency closure,
derived cleanup/rebuild, three exact backup cuts, independent full-cut
comparison, disposable format upgrade, stale-startup refusal and source
retirement. Activation then refused because Chroma read initialization had
changed imported derived index bytes. The source and replacement remain
stopped; no replacement input was admitted. This is preserved as development
partial evidence in
[`handover03.json`](../../evidence/operator-pilot/development/handover03.json).
The subsequent disposable-observation repair is covered by real-Chroma tests;
the final image must still execute a fresh complete cutover qualification.

Only the trusted intact single host and planned quiescence model is supported.
Backup storage remains on the same host, not an offsite or independent fault
domain. Go owner activation, chain/IRC egress, automatic failover, restoration of
old live authority, general migration and rollback after new destination work
are excluded. Old unknown effects remain unknown and charged. All raw packets
and credentials are private artifacts; only sanitized summaries may enter the
publication. `ADDITIONAL_LIVE_GENERATIONS=0` throughout.
