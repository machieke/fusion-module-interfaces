# Sustained single-node operator entry point

Use the selected release candidate's distribution manifest, exact image archive,
Helm chart and wheelhouse together. The final report records the actual artifact
path and SHA-256. Install only in a fresh `omega-ref-*` namespace. Preserve
`omega-demo`, `omega-ref-live01` and the old frozen campaign. No live text
generation or real generative-runtime readiness check is part of these commands.

Prerequisites: the existing supported single-node k3s cluster, its explicit
kubeconfig/context, Helm, kubectl, OpenSSL and CPython 3.12. Supplied images contain
the pinned native dependencies and E5 for the embedding role; the Omega caller
contains no E5 model/inference libraries. Restricted native/model assets retain
their existing acquisition requirements. This distribution is not an empty-cache
source rebuild, public registry publication or vulnerability certification.

From the extracted artifact directory, with the repository absent from
`PYTHONPATH`:

```sh
python3.12 -m venv /tmp/omega-operator
/tmp/omega-operator/bin/pip install --no-index --find-links wheelhouse \
  'fusion-preview-operator[preview-install,artifact-verification,chain-key-setup]==0.3.0'
/tmp/omega-operator/bin/fusion-verify-artifacts distribution.json
/tmp/omega-operator/bin/fusion-import-images --container omega-fusion-k3s \
  --manifest images.json --archive images.tar
/tmp/omega-operator/bin/fusion-sustained-values --images images.json \
  --scope synthetic-operator-example --mode combined --output fresh-values.yaml
/tmp/omega-operator/bin/fusion-sustained --kubeconfig /absolute/kubeconfig \
  --context default --namespace omega-ref-example install \
  --chart omega-fusion-0.6.3.tgz --values fresh-values.yaml \
  --directory /absolute/new-private-secret-directory
```

Use the chart filename listed in `distribution.json`. Its version is not a promise
that arbitrary images are compatible. A standard existing-host k3s import also
accepts `--k3s-binary /usr/local/bin/k3s` instead of `--container`; its command
rendering is tested, while a second host environment is not claimed executed.

All following commands use the same installed `fusion-sustained` with explicit
`--kubeconfig`, `--context`, `--namespace` and optional `--agent omega-agent-b`.
Credentials stay inside their selected pods. No operator SQL or journal edits
are needed.

```sh
fusion-sustained ... inventory
fusion-sustained ... allocate --template shared --identity first-allocation
fusion-sustained ... submit --session RETURNED_SESSION --identity remember-1 \
  --text 'remember The synthetic silver prism is stored in crate orchid'
fusion-sustained ... observe --session RETURNED_SESSION --content
fusion-sustained ... submit --session RETURNED_SESSION --identity query-1 \
  --text 'query synthetic silver prism storage'
fusion-sustained ... current --session RETURNED_SESSION
fusion-sustained ... capacity
fusion-sustained ... cancel --session RETURNED_SESSION --identity cancel-1 --target query-1
fusion-sustained ... reconcile --session RETURNED_SESSION
fusion-sustained ... close --session RETURNED_SESSION --identity close-1
fusion-sustained ... archive --session RETURNED_SESSION --identity archive-1
```

Reuse an identity only to observe the same intention. A new intentional command
gets a new identity. Observe before deciding whether more work is permitted.
`reconcile` never runs a missing tool. Undispatched expiry can release queue
headroom; a started uncertain effect fences dependent input. Closing preserves
retained quotas and pending completion reserves. Archive does not reclaim bytes.

`current` labels fresh owner heads separately from the application's retained
view. Its reads are bounded and not an atomic snapshot across services. Attention
shows committed value/effect time, not a new score evaluated at the current
clock. Captured historical results are never silently refreshed.

`allocate --template private` selects the generated private scope for that agent.
Exact private-to-shared projection is an operator action only:
`project --request-file exact-approved-projection.json`. Its closed request
schema is documented in `integration/single_node/sustained_projection.py` in the
source artifact. The request binds the returned private payload reference,
exact approved content, session, recipient scope, identity and approval record.
Do not put credentials in that file or treat a model proposal as approval.

The installed `fusion-preview-workbench` requires an explicit task namespace and
new private `--access-file`. It listens on loopback. The local access token is
separate from pod credentials. Never expose this service publicly. Current owner
reads, retained results, capacity and uncertain outcomes have separate panels;
buttons invoke the same authorized contracts as the CLI.

## Qualification and restore

`fusion-sustained ... qualify --directory NEW_REPORT_DIRECTORY` freezes and runs
the bounded native threshold, concurrency, handoff, private and counterfactual workload. It requires fresh approved
capacity; it does not clear existing state or replace failed occurrences. The
complete release qualification additionally records privacy, task, fault,
workbench and isolated-chain cases linked in the primary report. Recorded model
proposals remain explicit fixtures; native tools/providers are actual where
reported. There is no aggregate cognitive-accuracy score.

`fusion-sustained ... backup --directory NEW_PRIVATE_BACKUP` first stops all
selected writers. Each archive mounts exactly one owner PVC under maintenance
RBAC, checkpoints SQLite and hashes every included file. Keep these archives
private, including synthetic private state. Keys, approvals and current
credentials are excluded. The chain node's key-bearing PVC is stopped and
retained, not cloned.

`fusion-sustained-restore --kubeconfig ... --context ... --original ... --clone ...
--values ... --chart ... --directory ...` performs the bounded observation-only
drill. The original remains stopped; clone Secrets are fresh. Restored allocator
headroom is explicitly not permission to replay spent effects. The clone exposes
only authenticated observation routes; allocation, submit, dispatch, reconcile,
model, encoder, channel sends and chain execution cannot activate through its API.
Both namespaces finish quiesced with PVCs retained. No HA/failover or migration
claim follows from this test.

Use `fusion-sustained ... stop` for normal cleanup. StatefulSets retain their
PVCs. Deleting a task namespace and its PVCs is a separate deliberate destructive
operator action; never delete retained/protected namespaces to make a run pass.

## Isolated chain and source-only qualification helpers

Selecting `--chain` in the fresh values generator does not authorize submission.
The fresh Secret recipe writes generated **public** chain identity into the
sustained values before the first Helm mount. Keep the private setup directory
restricted. The node remains inert until the existing exact-artifact qualifier
verifies network isolation and explicitly activates it. Never use placeholder
public values, an empty wallet address, or the old protected campaign's keys.

The final chain example imports the existing full source-side qualifier. Extract
`source.tar.gz` into a new directory and select that **artifact source directory**
for this optional helper; the small installed client/operator wheels intentionally
do not install consensus adapters or all runtime owners:

```sh
mkdir artifact-source
tar -xzf source.tar.gz -C artifact-source
PYTHONPATH="$PWD/artifact-source" /tmp/omega-operator/bin/python \
  artifact-source/examples/sustained_chain_qualification.py \
  --kubeconfig /absolute/kubeconfig --context default --namespace omega-ref-example \
  --values /absolute/fresh-values.yaml --chart "$PWD/omega-fusion-0.6.3.tgz" \
  --qualification /absolute/completed-native/report.json \
  --observer "$PWD/artifact-source/examples/preview_chain_observer.py" \
  --output /absolute/new-chain-report
```

This command permits only the already approved synthetic inspected artifact.
Do not run it without the assignment's isolated-chain authority. The first
observed Phase 3 attempt failed pre-genesis because of placeholder configuration;
its node PVC remains retained. The corrected qualification explicitly selected
`components.f1r3node.persistence.existingClaim: phase3-f1r3node-qualified-10`
for a fresh, separately named node claim. Chart 0.6.3 permits that field only for
the isolated node, retains the old claim template, and mounts exactly one selected
state volume. It is not automatic failover, journal migration or permission to
replace a node after an uncertain deploy. All non-node owners keep their original
PVCs. Both node claims are excluded from the fenced clone; the backup helper's
legacy excluded-owner label names the original claim, while the retained pod
manifest identifies the additional selected claim.

## Final review and retained evidence

Use the [review checklist](review-checklist.md) and the detached
[artifact record](../../evidence/phase3/artifacts.json) from the publication. The
primary report distinguishes core dev09, affected dev10, backup dev11 and private
restore dev12 sources. Do not relabel the core as a new final-image rerun.

The main restore retained 13 owners, 14 sessions and 84 inputs. Its archives stay
in the local mode-0700 private backup directory, excluded from the packet. Both
original and observation-only clone are stopped; PVCs remain for authorized
review. The explicit isolated node claim and failed pre-genesis claim are both
retained and excluded from these application archives.

For a previously imported fenced clone, the source artifact includes
`examples/sustained_restore_recheck.py` and `sustained_restore_readback.py`. They
compare declared ports and retained results without importing journals again.
Their `--help` lists explicit namespace, values, chart and report arguments.
Use the exact original values and disabled-worker restore selections. Neither
helper authorizes effect replay or resumes the old campaign.
