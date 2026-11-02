# Current-image isolated IRC regression recipe

Current status: **all six dev19 regression assertion sets PASS**. The
[versioned summary](../../evidence/phase2/final/irc-regressions.json) and
[dispatcher report](../../evidence/phase2/final/irc/qualification.json) record the
completed execution. One case completes the retrieval-to-reply workflow; five
cases preserve unsuccessful or uncertain task outcomes as required. Passing a
negative assertion does not turn that task into a successful workflow.
`ADDITIONAL_LIVE_GENERATIONS=0`.

This document's preparation instructions and `PREPARED_UNRUN` packet below are
preserved historical inputs. They are not current execution status or permission
to repeat the completed cases. The original execution paths and namespaces now
contain retained evidence; their refusal-to-overwrite guard must stay in place.
The final documentation reconciliation used static report/hash reads only.

## Executed dev19 results

The summary SHA-256 is
`e7cc869e630acd4ebfa912ac22a6d84f742dc6d7a2a37911cb73b2532f72d7e2`;
the dispatcher report SHA-256 is
`906be3f93c2d984f4183a3b1141a4b447e8cd0b33a0927b305b8b2832e9379d8`.
Both bind the selected dev19 runtime source manifest below. The artifact-only
qualification tree separately contains 353 files with source-map digest
`8139c8f84f77633ffc3c62d1b0a3bda3327c721b091b137b37b9fc22560c1fbc`;
it includes operator/test files beyond the 330 runtime-export files.

| Executed case | Assertions | Workflow | Factual correctness | Peer observation | Recorded caller captures |
|---|---|---|---|---|---|
| [Correct](../../evidence/phase2/final/irc/recorded.json) | PASS | true | true | true | 2 |
| [Uncertain send](../../evidence/phase2/final/irc/uncertain-send.json) | PASS | false | true | false | 2 |
| [Wrong permitted answer](../../evidence/phase2/final/irc/wrong-answer.json) | PASS | false | false | true | 2 |
| [Absent fact](../../evidence/phase2/final/irc/absent-fact.json) | PASS | false | false | true | 2 |
| [Unready Search](../../evidence/phase2/final/irc/unready-search.json) | PASS | false | not observed on negative path | not observed on negative path | not observed on negative path |
| [Missing payload](../../evidence/phase2/final/irc/missing-payload.json) | PASS | false | not observed on negative path | not observed on negative path | not observed on negative path |

The first four cases each retain two authorized command admissions, actual
retrieval and exact query-result binding in the next prompt. The uncertain send
retains its unknown socket outcome and no observed reply, with no automatic
resend. Wrong/absent answers were permitted and actually delivered; the separate
factual evaluator failed both. The final two cases refuse captured query
completion and emit no reply; fields absent from those negative-path reports
remain `NOT_OBSERVED_FOR_NEGATIVE_PATH`, not fabricated zeroes or successes.

All cases used actual native Omega, E5, Chroma, DeTTa, Messaging, isolated
ngIRCd/socket peer and authenticated pod HTTPS. Model responses, empty promoted
and history context, and metadata clocks are explicit fixtures. This is the
preserved single-agent IRC composition, not the combined two-agent cognitive
workflow or a live-generation pass. The summary binds each sanitized raw report
by SHA-256; raw reports and preparation labels are unchanged.

## Historical preparation recipe

Use the existing `integration.single_node.reference_qualification` dispatcher with
the six prepared scenarios `recorded`, `uncertain-send`, `wrong-answer`,
`absent-fact`, `unready-search` and `missing-payload`. They invoke the existing
`integration.single_node.test_workflow_cluster` cases listed below.
Each case creates its own namespace, Secrets,
PVCs and native application journals. This is a regression of the preserved
single-agent IRC composition, not a claim that the new two-agent preview has
been driven through IRC or that its cognitive context is exercised here.

The selected dev19 image publication is
`artifacts/phase2/build-dev19/images.json`, with public source-manifest SHA-256
`369daf1ab470fb8fe8265fe16a3a5765670c643e7011e3d5369636a803e7e49d`.
All **330 exported source files** matched both the current checkout and
`/tmp/omega-phase2-source-dev19-candidate09` during this static review. All four image
package manifests contain that same source map. The image publication's own
SHA-256 is `7f8a1058fe852cedbf08a4c4cbc24bec9913cc62d90707ecf71a82d5078c2d91`.
The extracted source is from candidate09 distribution manifest
`fde2f831621d74a5f6d40da8c615a8bc9c06787355eede8550727b408d38a5bd`.
Its chart is **0.5.1**. The chart, values and Secret generator are operator files
outside that image source manifest; the prepared input record binds all five
chart file hashes, and the harness separately snapshots chart, values and source
hashes before execution.

| Selected image | Immutable manifest digest |
|---|---|
| `docker.io/library/fusion-single-node` | `sha256:8471ca9dbb119d11111861fd22a14e7a5c0115f47e9f6591b3b5c12fe38a7b35` |
| `docker.io/library/fusion-memory-caller` | `sha256:e3982b8cbb7283530df8563047b8a0b9c9316b1da49e7ba33f3074474876587b` |
| `docker.io/library/fusion-memory-embedding` | `sha256:d5ce4e6e3ca9218d12784d5fa0ab3cb7bbc37201193951f642ab2abdad94b6ec` |

These are sufficient: no generative or chain image belongs in this run. Do not
call `reference_build.profiles()` on this four-image dev19 publication; that
historical helper unconditionally expects a `generative` entry. The small offline
prepared values select only the existing three images, each tagged
`reference-phase2-dev19` and pinned by manifest digest.

## Historical prepared inputs and offline verification

The existing prepared packet is `artifacts/phase2/irc-dev19-01`. Its
`operator-inputs.json` remains `PREPARED_UNRUN`; preparation is not a scenario
pass. Static validation confirmed these exact bytes and all six planned names:

| Prepared file | SHA-256 |
|---|---|
| `profiles/workflow.yaml` | `2d6930c3c40a7e203c7101b9a0102abe1cc1927dbca7c6c3d9cfdc3aaf1b000c` |
| `operator-inputs.json` | `1059fb265c2ffa07568831f9d720fdc7020f863b3398acfe217b0932ece349c5` |

The prior `artifacts/phase2/irc-dev17-01` and `artifacts/phase2/irc-dev18-01`
packets are preserved byte-for-byte. Their `operator-inputs.json` files still
record **PREPARED_UNRUN**, respectively with SHA-256
`125a75a192938f1175a47913a7256573dd39f3ec60009c442e4c836426dae850` and
`e14790115b2e0034e99d688e38ddccc90100937e16e83ede2da3386966af2390`.
Neither has an execution directory at this review. They are historical
preparation, not executed dev17/dev18 results. Dev19 changes only the selected
images in the workflow values; the synthetic inputs and six case choices are
unchanged. The input record additionally binds the distribution and
chart, whose canonical five-file hash map has SHA-256
`932fb6c1e9d092452ec983c42a6c4b6a6c4ff26518d9db1534f16fd9f23afdbd`.

Use the artifact-extracted source and separately installed operator environment;
the execution command does not import the developer checkout. The distribution
and prepared-input paths below can point to byte-identical copied artifact
packets. All preflight image/source metadata comes from the distribution itself;
the original image-build directory is unnecessary. The already installed
`/tmp/omega-phase2-operator-dev18` environment is reused because its candidate03
wheel sources are unchanged; its directory name does not select dev18 pod images.
The extracted source includes the chart and Secret generator required by the
historical harness. Do not regenerate or edit the prepared values between cases.
The task-local
kubeconfig must select `default` as its current context: the dispatcher accepts
`--context default`, but the existing child harness passes only `--kubeconfig` to
kubectl/Helm. The assertion below prevents a different current context from being
used. It does not change the kubeconfig or contact a cluster.

```bash
export IRC_KUBECONFIG=/absolute/path/to/task-owned-k3s-kubeconfig
export IRC_ROOT=/home/purplezky/work/takopi/fusion-module-interfaces/artifacts/phase2/irc-dev19-01
export IRC_DISTRIBUTION=/home/purplezky/work/takopi/fusion-module-interfaces/artifacts/phase2/distribution-candidate-09
export IRC_SOURCE=/tmp/omega-phase2-source-dev19-candidate09
export IRC_PY=/tmp/omega-phase2-operator-dev18/bin/python
cd "$IRC_SOURCE"

env -u PYTHONPATH "$IRC_PY" - <<'PY'
import hashlib, json, os
from pathlib import Path
import yaml

source = Path(os.environ['IRC_SOURCE']).resolve()
prepared = Path(os.environ['IRC_ROOT']).resolve()
distribution = Path(os.environ['IRC_DISTRIBUTION']).resolve()
assert Path.cwd() == source
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
canonical = lambda value: json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()
config = yaml.safe_load(Path(os.environ['IRC_KUBECONFIG']).read_text())
assert config['current-context'] == 'default'
manifest_path = distribution / 'images.json'
assert sha(manifest_path) == '7f8a1058fe852cedbf08a4c4cbc24bec9913cc62d90707ecf71a82d5078c2d91'
manifest = json.loads(manifest_path.read_text())
assert manifest['source_export_verification'] == 'PASS'
assert manifest['source_manifest_sha256'] == '369daf1ab470fb8fe8265fe16a3a5765670c643e7011e3d5369636a803e7e49d'
package = json.loads((distribution / 'image-sources/base.json').read_text())
assert len(package['source']) == 330
assert hashlib.sha256(canonical(package['source'])).hexdigest() == manifest['source_manifest_sha256']
assert all(sha(source / name) == expected for name, expected in package['source'].items())
assert (prepared / 'images.json').read_bytes() == manifest_path.read_bytes()
assert sha(prepared / 'operator-inputs.json') == '1059fb265c2ffa07568831f9d720fdc7020f863b3398acfe217b0932ece349c5'
plan = json.loads((prepared / 'operator-inputs.json').read_text())
assert plan['classification'] == 'PREPARED_UNRUN' and plan['additional_live_generations'] == 0
assert plan['source_manifest_sha256'] == manifest['source_manifest_sha256']
assert plan['image_manifest_sha256'] == sha(manifest_path)
assert sha(distribution / 'distribution.json') == plan['distribution_manifest_sha256'] == 'fde2f831621d74a5f6d40da8c615a8bc9c06787355eede8550727b408d38a5bd'
assert plan['scenarios'] == ['recorded', 'uncertain-send', 'wrong-answer', 'absent-fact', 'unready-search', 'missing-payload']
assert sha(prepared / 'profiles/workflow.yaml') == plan['values_sha256'] == '2d6930c3c40a7e203c7101b9a0102abe1cc1927dbca7c6c3d9cfdc3aaf1b000c'
images = {item['kind']: dict(repository=item['repository'],
    tag=item['local_tag'].rsplit(':', 1)[1], digest=item['manifest_digest'],
    pullPolicy='Never') for item in manifest['images']}
values = yaml.safe_load((prepared / 'profiles/workflow.yaml').read_text())
assert values['image'] == images['base']
for role in ('omega-agent', 'fusion-search'):
    assert values['components'][role]['image'] == images['caller']
assert values['components']['fusion-embedding']['image'] == images['embedding']
assert values['networkPolicy'] == {'enabled': True}
assert values['preview'] == {'enabled': False}
assert values['workflow']['mode'] == 'recorded'
assert values['workflow']['liveEnabled'] is False
assert values['workflow']['phase'] == 'setup'
assert values['components']['fusion-execution']['enabled'] is False
chart_root = source / 'deploy/helm/omega-fusion'
assert yaml.safe_load((chart_root / 'Chart.yaml').read_text())['version'] == plan['chart']['version'] == '0.5.1'
chart_files = {path.relative_to(source).as_posix(): sha(path)
               for path in sorted(chart_root.rglob('*')) if path.is_file()}
assert chart_files == plan['chart']['source'] and len(chart_files) == 5
assert hashlib.sha256(canonical(chart_files)).hexdigest() == plan['chart']['source_manifest_sha256'] == '932fb6c1e9d092452ec983c42a6c4b6a6c4ff26518d9db1534f16fd9f23afdbd'
assert not (prepared / 'execution').exists(), 'retain prior execution; do not overwrite or rerun it'
print('STATIC_INPUT_BINDINGS_VALIDATED; SCENARIOS_UNRUN; ADDITIONAL_LIVE_GENERATIONS=0')
PY
```

The base corpus, commands, allowlisted reply bodies, deadlines, fixed clocks and
historical profile selections remain unchanged. The existing `wrong-permitted`
and `absent-corpus` cases make their declared scenario changes before creating
their fresh namespace; they do not repair responses during execution. Fixed logical IDs are
used only in separately fresh namespaces and journals; no historical state or
credentials are reused. The harness enables its existing fault hooks itself.
With `preview.enabled=false`, this historical IRC composition retains its
historical DeTTa layout. The dev19 coordinate-partition layout is selected
only by fresh preview configurations; this regression does not qualify that
layout's separate native-memory integration.

Prerequisites are the task-owned single-node k3s context, Helm/kubectl/OpenSSL,
the installed `/tmp/omega-phase2-operator-dev18` environment, artifact-extracted
source, `local-path` provisioning, and the three selected
image manifests already imported into that node. `pullPolicy: Never` makes an
absent image an explicit prerequisite failure. The recipe does not start or
contact a generative runtime to resolve any prerequisite.

## Historical invocation of the six scenarios

At preparation time these exact commands selected the following fresh
namespaces and all six scenarios were **UNRUN**. Execution is now recorded above;
do not rerun these completed namespaces or overwrite their evidence:

| Scenario | Existing case | Fresh namespace |
|---|---|---|
| `recorded` | `correct` | `omega-ref-p2irc19-01-0-correct` |
| `uncertain-send` | `uncertain-send` | `omega-ref-p2irc19-01-1-uncertain-send` |
| `wrong-answer` | `wrong-permitted` | `omega-ref-p2irc19-01-2-wrong-permitted` |
| `absent-fact` | `absent-corpus` | `omega-ref-p2irc19-01-3-absent-corpus` |
| `unready-search` | `unready-search` | `omega-ref-p2irc19-01-4-unready-search` |
| `missing-payload` | `missing-payload` | `omega-ref-p2irc19-01-5-missing-payload` |

The preflight name is observational and
does not create another namespace. Do not use an existing preview namespace,
`omega-demo`, or the frozen campaign namespace.

```bash
env -u PYTHONPATH "$IRC_PY" \
  -m integration.single_node.reference_qualification \
  --kubeconfig "$IRC_KUBECONFIG" --context default \
  --prefix omega-ref-p2irc19-01 \
  --output "$IRC_ROOT/execution" \
  --profiles "$IRC_ROOT/profiles" \
  recorded uncertain-send wrong-answer absent-fact unready-search missing-payload
```

The dispatcher runs a separate generation-denial check before the scenarios,
runs them sequentially even if one fails, and retains each failure. Do not
repeat an unsuccessful scenario under its old namespace, renew accepted
deadlines, or substitute another response to obtain a pass. Fix an ordinary
defect separately and retain the failed attempt before any newly qualified run.

Each runner requests deletion of only the namespace it created, after verifying
the namespace UID. Deletion is asynchronous, so a cleanup request alone is not
proof that pods have stopped. After the dispatcher returns, observe these exact
names until deletion; this does not submit work or retry a send:

```bash
for namespace in \
  omega-ref-p2irc19-01-0-correct \
  omega-ref-p2irc19-01-1-uncertain-send \
  omega-ref-p2irc19-01-2-wrong-permitted \
  omega-ref-p2irc19-01-3-absent-corpus \
  omega-ref-p2irc19-01-4-unready-search \
  omega-ref-p2irc19-01-5-missing-payload
do
  kubectl --kubeconfig "$IRC_KUBECONFIG" --context default \
    wait --for=delete "namespace/$namespace" --timeout=120s
done
```

If a name is already absent, record that observation. Retain deletion timeouts
as cleanup failures and inspect only the named task-owned namespace. No wildcard
namespace deletion or removal of retained preview PVCs belongs in this recipe.

## What executes and what each result means

`Workflow.run()` first lets native `remember` populate the two-record synthetic
corpus with real E5, Chroma and DeTTa. It then changes the declared workflow
phase from setup to measured through the existing ConfigMap rollout. This is
the historical setup/measured boundary, not an operator insertion of a query
answer. The independent `irc-peer` socket sends the question. The durable bridge
captures it through AtomStorage and Messaging, and actual native Omega consumes
it, calls ModelInference, parses `query`, retrieves the committed corpus, and
puts the captured result in the next model input when retrieval succeeds. A
second real IRC input then causes the permitted `send` proposal to pass through
the native parser and channel outbox. The two missing-dependency cases stop at
the refused query and never send that second input. Only the operator's peer
input and owner-local read-only observations
drive the harness; the operator does not perform the native tools.

Real components: native parser/loop/remember/query/send, E5 CPU, Chroma, DeTTa,
Messaging, ngIRCd and a separate socket peer, authenticated pod-to-pod module
HTTPS, DNS and dedicated PVCs. The isolated IRC hop itself is plaintext inside
the selected NetworkPolicy; it is not claimed as TLS or a public channel.

Explicit fixtures: the setup command stream, two recorded model responses in
`RecordedBackend`, empty promoted/history context, and declared metadata clocks.
Recorded responses only propose commands; the real ModelInference owner still
accepts, reserves, captures and discloses them. No live model usefulness or
two-agent cognition result follows from this regression.

| Scenario in the preserved preparation plan | Required evidence and interpretation |
|---|---|
| `recorded` → `correct` | Two caller captures, two provider reservations/evaluations, admitted commands, one actual query, exact captured query projection in the next prompt, answer absent from initial prompt, independently evaluated factual correctness, and matching real peer body. `workflow_pass=true` is required. |
| `uncertain-send` | Kill/replacement at `after_socket_reservation`; retained egress reservation `reserved=1`, `outcome=unknown`, no peer reply, no automatic resend. Two recorded captures and query/next-prompt binding still exist. A successful safety case has `status=PASS`, **`workflow_pass=false`**, and `peer_observation=false`. |
| `wrong-answer` → `wrong-permitted` | The existing case selects the second equally permitted reply body. Two captures, retrieval, next-prompt binding and actual peer delivery must exist, while the independent committed-corpus evaluator reports `factual_correctness=false` and `workflow_pass=false`. Output permission does not establish correctness. |
| `absent-fact` → `absent-corpus` | Native `remember` prepares the existing case's unrelated synthetic corpus. The unchanged recorded answer may be admitted and delivered, but the evaluator derives `Insufficient retrieved information.` from the actual committed records and must report factual/workflow failure. This is a safe negative fixture result, not successful model abstention. |
| `unready-search` | Quarantine the Search-owned publication marker after setup. The measured caller must report `NOT_AVAILABLE`, retain one caller/model-owner call row, leave query occurrences incomplete without captured results, and emit no reply. A passing safety case reports `workflow_pass=false`. |
| `missing-payload` | Pause after candidate capture, quarantine the storage owner's synthetic payload root, then replace the caller. Verified hydration must report `NOT_AVAILABLE`; query occurrences remain incomplete and no reply is emitted. A passing safety case reports `workflow_pass=false`. |

`Workflow.invariants()` compares independent owner snapshots for unchanged
identities, accepted inputs, retained views, captured results and original
deadlines, monotonically spent counters and stable PVC identities. Read-only
operators inspect each owner's files only inside that owner's pod. They do not
mount another service's journals into the consumer.

Primary outputs are `execution/qualification.json`, six scenario logs and these
per-case reports:

- `execution/recorded/correct/report.json`
- `execution/uncertain-send/uncertain-send/report.json`
- `execution/wrong-answer/wrong-permitted/report.json`
- `execution/absent-fact/absent-corpus/report.json`
- `execution/unready-search/unready-search/report.json`
- `execution/missing-payload/missing-payload/report.json`

Reports contain pod image
IDs, observations, actions, command admissions, captures and peer traffic.
Each scenario also retains frozen chart/values and a source manifest. Keep
`private-secrets/` and its keys/credential-bearing Secret JSON outside any
publication; publish only reviewed sanitized reports, logs and hashes. The
public operator image manifest must accompany the actual observed image IDs.

## Bounded cost and limitations

The selected values produce **nine single-replica workloads**. The chart's total
requests are **2.75 CPU and 3968 MiB RAM**; limits total **10.5 CPU and 8704 MiB**;
PVC requests total **3328 MiB** per fresh scenario. E5 has the dominant declared
allocation: 2 CPU/3 GiB requested, 3 CPU/5 GiB limited. Existing cached images
are reused; the four-image dev19 export is 3,472,984,576 bytes, but this lane
uses only base/caller/embedding. Sequential namespace deletion can overlap
briefly with the next installation; do not schedule other heavy qualification
work concurrently on a constrained node.

Historical observations, **not dev19 predictions**: the earlier
`qualification-11/recorded/correct` report passed with 61.712 seconds cold setup
and 82.207 seconds through workflow completion; the earlier
`qualification-10/uncertain-send/uncertain-send` safety case passed at 72.905 and
97.650 seconds respectively. The successful historical resource sample recorded
an E5 cgroup peak of 1,461,067,776 bytes. A few minutes per scenario is a planning
allowance, not a deadline extension or SLA. Existing bounded observers and
30-second memory invocation deadlines must stay unchanged; a slower execution
is an observed failure or timeout, not permission to raise limits.

The successful case's resource observer also probes service health. NetworkPolicy
can deliberately deny health probes to non-dependency services; those individual
observations are not operation-throughput evidence. Preserve the existing host
CPU-quota-enforcement exception. Neither the declared resource limits nor a
passing workflow demonstrates production isolation, multi-node behavior, HA,
live generation, or guaranteed external delivery.
