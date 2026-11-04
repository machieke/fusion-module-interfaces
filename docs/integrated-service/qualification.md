# Executed qualification recipes

Run from the extracted, verified distribution source. Select absolute paths and
a task-owned namespace. Each deployed qualifier stops its namespace in `finally`;
restart the **same** values with the installed operator between checks. Never
reinstall Secrets, reset retained state or renew an accepted occurrence to obtain
a pass. Heavy native/E5/chain lanes run serially. Models remain recorded fixtures.

The final runtime is build18. Historical packets18/18c/18d/18e and helper revisions
are retained separately from the final packet. The report identifies which
helper was executed; newer documentation does not relabel an older run.

## Installed native and independent provider

The historical native manifest contains a fixed Python path. This recipe hides
the developer checkout with a read-only extracted packet at that virtual path,
then separately mounts the exact pinned native assets and DeTTa executable.
It keeps the runtime file and numerical pins unchanged. It requires Linux
`bwrap`, OpenSSL, the pinned native asset tree and the installed operator Python.
The output must be a fresh private directory outside the hidden checkout.

```sh
python -m examples.integrated_native_package \
  --source /absolute/extracted-source \
  --native /absolute/pinned-native-02 \
  --detta /absolute/pinned/fusion-detta-adapter \
  --python /absolute/installed-operator/bin/python \
  --directory /tmp/new-private-native-qualification
```

The existing generation-denial launcher runs before the seven fixed methods.
Original/local/HTTPS NAL, resident reuse, current revocation, saved-result kill
recovery, compact history, read-only preparation and an independently built
atomic-file provider are exercised. The independent provider remains a contract
fixture; the original NAL and selected DeTTa lanes are real. A child JSON report
cannot override a failed unittest exit. Do not publish private test directories.

For independent encoder/retrieval placement, use the existing pinned S03/S03.1
asset recipes and full test environment; no generative runtime is used:

```sh
artifacts/s03/venv/bin/python -m integration.neoclaw.preparation_guard \
  --guard-evidence /absolute/new-denial.json -- \
  artifacts/s03/venv/bin/python -m integration.neoclaw.embedding_run \
  --evidence /absolute/new-private-placement-report.json
```

This executes the original native oracle, the historical S03 baseline and all
four local/HTTPS encoder/retrieval combinations. The helper records explicit
model/channel/context/clock fixtures. Real E5 inference is permitted; text
generation is not. The HTTPS caller cannot access E5 assets/inference libraries.

The actual old/new wire check needs the baseline Git object as well as the
published old wheel and real DeTTa binary. Unlike the installed provider lane,
this recipe deliberately reads Git to export the original server:

```sh
artifacts/s03/venv/bin/python -m integration.neoclaw.preparation_guard \
  --guard-evidence /absolute/new-wire-denial.json -- \
  artifacts/s03/venv/bin/python -m unittest -v tests.test_integrated_archive_wire
```

## Deployed native and recovery

Use the common flags `--kubeconfig KUBE --context CONTEXT --namespace TASK_NS`.
Do not pass answer references to native retrieval or delegated consumers.

| Module entrypoint | Additional arguments | Bounded work |
|---|---|---|
| `examples.integrated_baseline` | `--directory NEW --label LABEL` | 14 operator inputs; 16 native inputs including task/result |
| `examples.integrated_sustained` | See its CLI help for the selected initial/resume recipe | 80-input fresh retained workload; failed resume records stay separate |
| `examples.integrated_concurrent_rebuild` | `--directory NEW --values ORIGINAL --chart CHART --native-report PRIOR` | Four inputs: new ready native view, enrollment during reserved old repair, two real queries |
| `examples.integrated_retained_recovery lifecycle` | Same values/chart/native-report/directory flags | Six inputs: safe expiry/cancel, started uncertainty, independent progress |
| `examples.integrated_go` | `--directory NEW --binary /absolute/go/omega-client` | Two real native inputs plus independently issued storage/authority calls |
| `examples.integrated_continuation_recovery` | `--directory NEW --values ORIGINAL --chart CHART --case accepted-caller-kill` or `--case lost-acceptance-reply` | Four inputs per separate fresh scenario; exact saved graph across caller/executor replacement |
| `examples.integrated_chain_continuation` | `--output NEW --values ORIGINAL --chart CHART --observer /absolute/examples/preview_chain_observer.py` | Four native inputs, one approved isolated-chain submit reservation, independent readback |

Compare the four completed frozen baseline directories with:

```sh
python -m examples.integrated_compare COLD1 WARM1 COLD2 WARM2 --output NEW.json
```

The deployed Go client runs in a mount namespace containing only its static
binary and selected scoped TLS configuration. Operator setup is separate. When
an active-session quota is full, an operator may close a **fully completed**
session through its normal API before allocating new work; retention, prior
captures and spent accounting remain. Closing is not a retention refund.

The two `--resume-setup-report` qualifiers accept only their narrowly checked
failed setup states: a completed seed before any repair invocation, or three
terminal lifecycle inputs before the uncertain case. They verify those exact
old captures and continue only the unexecuted test steps. They cannot replay an
uncertain input or extend its original deadline. Original reports remain intact.

Chain execution uses only the existing pinned isolated node/operation, fresh
unfunded keys and explicitly shareable native result. The future generative
configuration remains disabled. Do not enable a public node or a live model.

Run the two continuation fault cases in separate fresh namespaces. The lost-reply
case arms the test fault before accepting its parent task. The earlier combined
five-input test passed caller-kill recovery but exhausted the parent task's
original deadline during the second case. That case remains pending/unsuccessful;
the four-input scenario is new work, not a renewed occurrence. No qualifier may
extend that parent deadline or reconstruct a captured model response.

## Restore, integrity and publication

`examples.integrated_retained_recovery restore` adds `--clone FRESH_FENCED_NS
--images IMAGES_JSON` to the common values/chart/native-report/directory flags.
`examples.integrated_chain_restore` uses `--original`, `--clone`, `--values`,
`--chart`, `--directory`, `--native-report`, `--images`, `--kubeconfig` and
`--context`. Node state/keys are excluded; only application receipts are restored.
Neither recipe enables a restored executor.

The restore drill first observes the original application APIs. If the preceding
chain qualifier already stopped its workloads, restart the original service
readers before the drill, leaving `f1r3node` at zero replicas. With the installed
operator Python and explicit task namespace:

```python
from integration.single_node.reference_ops import Operator
op = Operator('/absolute/selected-kubeconfig', 'default', 'TASK_CHAIN_NAMESPACE')
op.owned()
roles = [x['metadata']['name'] for x in op.workloads()
         if x['metadata']['name'] != 'f1r3node']
op.k('scale', *['statefulset/' + x for x in roles], '--replicas=1')
for role in roles:
    op.k('rollout', 'status', 'statefulset/' + role, '--timeout=120s', timeout=130)
```

This recipe is for the fully completed chain workflow, with no pending native
input. It does not invoke the chain continuation. The backup then stops these
writers, and the restore recipe stops original and clone on completion. A first
restore attempt against already stopped pods is retained as a harness failure.

`examples.integrated_integrity` works on disposable copies of actual backups.
It diagnoses bounded corruption without rewriting authority or source history.
Archive is not deletion, unlimited capacity or independent backup. A missing
authoritative record remains a failure. Use the existing Search maintenance API
only for derived repair, with an explicit identity and original bounded deadline.

Public evidence is an allowlist of source/image identities, counters, classified
outcomes and approved shareable chain trace. Raw backup archives, synthetic
private journals, prompts, canary hashes, credentials and browser recordings stay
local. Preserve unsuccessful attempts and unknown effects in the progress ledger.
