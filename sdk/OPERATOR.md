# Artifact-only operator installation

`fusion-preview-operator` packages the existing host-side operator, workbench,
artifact verifier, fresh-values selector, scoped Secret helper and image-import
recipes byte for byte. All installed source identities are in the wheel's
`source-manifest.json`. The small CLI selector checks optional cryptographic
imports before delegating to the original Secret recipe; it does not duplicate
TLS, signing-key, Helm or owner behavior.

The client wheel remains independent. Installing `fusion-module-client`
installs no operator, provider, journal owner, PyYAML, cryptographic library,
model asset or native runtime. The operator core adds only standard-library
host tools and pure contract/configuration helpers. The selected pod still owns
its existing `integration.single_node.preview_operator` application code.

## Prepare the declared artifacts

The final distribution must supply its chart archive, verified `images.json`,
`images.tar`, the client/operator wheels and required dependency wheels. Build
into a new output directory; do not overwrite historical qualification inputs:

```sh
python3.12 sdk/build.py --output /absolute/output/preview-wheels
python3.12 sdk/inventory.py /absolute/output/preview-wheels/*.whl \
  --output /absolute/output/preview-wheels/dependency-inventory.json
```

The exact optional wheels used in development qualification are recorded in
[`operator-wheel-inputs.json`](operator-wheel-inputs.json). This is a CPython
3.12 Linux x86_64 wheel set; another platform needs its own artifact pins.
The source dependency recipe is the existing pinned operator requirements.
PyYAML enables fresh preview values/Secret selection and artifact verification.
The `chain-key-setup` extra additionally installs pinned cryptography,
pycryptodome, cffi and pycparser. It provisions synthetic key material only;
it does not package or start a chain node.

The example commands below use an **extracted, already verified distribution**
whose non-secret files are listed in its manifest. These shell variables are
operator choices, not original developer paths:

```sh
TASK_DIST=/absolute/extracted/distribution
TASK_VENV=/absolute/operator-venv
TASK_KUBECONFIG=/operator-owned/kubeconfig
TASK_CONTEXT=explicitly-selected-context
TASK_NAMESPACE=omega-ref-new-preview
TASK_K3S_CONTAINER=explicitly-selected-task-container
TASK_WORK=/operator-owned/new-preview

python3.12 -m venv "$TASK_VENV"
"$TASK_VENV/bin/python" -m pip install --no-index \
  --find-links "$TASK_DIST/wheelhouse" \
  fusion-module-client==0.2.0 \
  'fusion-preview-operator[preview-install,artifact-verification]==0.2.0'
"$TASK_VENV/bin/fusion-preview-workbench" --help
"$TASK_VENV/bin/fusion-preview-values" --help
```

The extra dependency wheel must already be in the declared wheelhouse; no
network fallback is implied. `fusion-preview-values` uses its original main,
which imports PyYAML even for `--help`. Core-only workbench/import/help commands
do not need that optional dependency.

## Fresh recorded preview installation

Prerequisites are explicit `kubectl`, Helm, OpenSSL and the supported Docker-
hosted single-node k3s adapter on the operator's `PATH`. The import command uses
only the supplied container name and verifies archive/tag/manifest/configuration
identities. It does not discover a default Docker container or active context.
Other CRI/runtime import modes are not qualified by this package.

```sh
"$TASK_VENV/bin/fusion-import-images" \
  --container "$TASK_K3S_CONTAINER" \
  --manifest "$TASK_DIST/images.json" --archive "$TASK_DIST/images.tar"
mkdir -m 700 "$TASK_WORK"
"$TASK_VENV/bin/fusion-preview-values" \
  --images "$TASK_DIST/images.json" --scope synthetic-new-preview \
  --mode combined --output "$TASK_WORK/preview-values.yaml"

"$TASK_VENV/bin/python" -I -c \
  'import sys; from integration.single_node.reference_ops import Operator; Operator(*sys.argv[1:]).create()' \
  "$TASK_KUBECONFIG" "$TASK_CONTEXT" "$TASK_NAMESPACE"
"$TASK_VENV/bin/fusion-create-secrets" \
  --preview-values "$TASK_WORK/preview-values.yaml" \
  --kubeconfig "$TASK_KUBECONFIG" --context "$TASK_CONTEXT" \
  --namespace "$TASK_NAMESPACE" --directory "$TASK_WORK/private-secrets"

# Bind fresh chain public identity BEFORE the first Helm install, if selected.
# Non-chain selections leave the values unchanged and read no chain file.
"$TASK_VENV/bin/python" -I - "$TASK_WORK/preview-values.yaml" \
  "$TASK_WORK/private-secrets/chain-public.json" <<'PY'
import json
from pathlib import Path
import sys
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
    assert all(isinstance(public[name], str) and public[name] for name in public)
    chain.update(public_key=public['public_key'], wallet_address=public['wallet_address'])
    path.write_text(yaml.safe_dump(values, sort_keys=False))
PY

helm upgrade --install omega "$TASK_DIST/omega-fusion-chart.tgz" \
  --kubeconfig "$TASK_KUBECONFIG" --kube-context "$TASK_CONTEXT" \
  --namespace "$TASK_NAMESPACE" -f "$TASK_WORK/preview-values.yaml"
"$TASK_VENV/bin/fusion-preview-workbench" \
  --kubeconfig "$TASK_KUBECONFIG" --context "$TASK_CONTEXT" \
  --namespace "$TASK_NAMESPACE" --port 8768 \
  --access-file "$TASK_WORK/workbench-access.json"
```

`omega-fusion-chart.tgz` denotes the exact chart filename listed in the final
manifest; substitute that listed name if versioned. No developer tree or
repository `PYTHONPATH` is used by these installed commands. Values generation
creates fresh session/policy identities once, with recorded model proposals and
fixed image digests; it refuses to overwrite an existing selection file. The
normal authority expiry remains visible in that file. No occurrence deadline
or model reservation starts during generation of values.

The existing namespace operator enforces task-owned naming/labels. The original
Secret recipe creates a new mode-0700 private directory, mode-0600 key files and
explicit Kubernetes Secret references. It refuses an existing directory rather
than silently reminting identities. Never publish that directory. The workbench
keeps its existing loopback/origin checks and invokes the selected pod's native
session API; no second host-side application owner is installed.

The workbench creates the selected access file exclusively with mode `0600`
inside the private `TASK_WORK` directory. Do not pre-create that file: an
existing path is refused. Its contents are one opaque local access token, not
a JSON document despite this example filename. Read it privately and paste it
into the browser's **Local workbench token** field. This token protects the
local browser/API boundary and is separate from pod/provider credentials.
Keep it out of command arguments, screenshots, logs, distribution archives and
published evidence. A later workbench process needs a new private access-file
path; this procedure does not rotate provider credentials.

For an upgrade, retain current values, identities, PVCs and Secrets, verify the
new image/profile compatibility first, use `Operator.owned()` and
`Operator.workloads()` on the explicit target, then run the same Helm command
with an explicitly reviewed new values file. Do not rerun fresh Secret creation
or regenerate accepted session identities as an upgrade recipe.

## Isolated chain key setup and retained-state procedures

Install the explicit extra only when isolated synthetic key provisioning is
part of the selected task:

```sh
"$TASK_VENV/bin/python" -m pip install --no-index \
  --find-links "$TASK_DIST/wheelhouse" \
  'fusion-preview-operator[preview-install,chain-key-setup]==0.2.0'
```

`fusion-preview-values --chain` requires a declared chain image. Its emitted
`nodeEnabled=false` and `isolationVerified=false` remain disabled. The unchanged
Secret recipe can then create fresh synthetic signer/validator keys using the
pure shared address function. For this variant select `--chain` during the
initial values-generation step, then perform the public-identity copy shown
above **before the first Helm install**. Copy only `public_key` and
`wallet_address` from that fresh `private-secrets/chain-public.json` into
`preview.chain`. The generated placeholders must not reach the first owner
startup: identity is sealed even while the node remains disabled. This is a
fresh-install operation, not permission to rewrite an existing owner seal.
Keep `nodeEnabled=false`, `isolationVerified=false` and `registration=null`.
Missing cryptographic extras fail before any key
file or subprocess is created. Key provisioning is not chain execution,
registration, isolation verification, a funded transaction or finality evidence.
Follow the separately tested isolated-chain programme recipe before activation.

`integration.single_node.reference_ops.Operator` also retains the existing
quiesce/backup/fenced-restore implementation. Its host package contains no owner
journals. The current backup explicitly excludes node cryptographic state and
retains the stopped source PVC; it does not imply portable validator identity
restoration. Actual namespace/PVC restore qualification remains separate from
these package tests.

## Exact boundaries and evidence

The broad historical `integration.single_node.reference` CLI is deliberately
not packaged: the narrow installed recipes plus the existing Helm CLI provide
the recorded preview install path without importing campaign/runtime code.
Source-overlay image building, native-provider execution, campaign preparation,
activation, live generation and automatic migrations are not package behavior.

Light qualification installs from declared wheels into fresh venvs outside the
checkout, clears `PYTHONPATH`, and verifies exact source bytes. The install tests
use **real OpenSSL TLS and synthetic key generation**, **real dependency wheels**,
**real existing recipe code**, and explicit **kubectl/Docker command stubs**.
Their image descriptors/archive contents are fixtures. Thus they prove host
packaging/recipe dependency closure, not a real Kubernetes installation, image
import, native workflow, chain effect or browser session.

```sh
FUSION_SDK_OPERATOR_WHEELHOUSE=/absolute/pinned/dependency-wheels \
  python3.12 -m unittest sdk.test_operator_package sdk.test_operator_install -v
```

Without the explicit dependency wheelhouse the install methods are labelled
`UNRUN` by unittest skips. Historical development failures are retained in
`operator-install-development-failure-01.json` (test stub quoting) and `-02.json`
(optional-generator help invoked without its extra); later checks correct their
scope without changing historical evidence.

Wheel inventory records every artifact/file hash, declared dependency, Python
requirement, optional extra and available license metadata. Missing license
metadata remains `NOASSERTION`; it does not grant redistribution rights or invent
an SPDX license. Final image/OS/native inventories remain part of the outer
SBOM. `vulnerability_scan=NOT_RUN`, `hosted_ci=NOT_OBSERVED`, and
`ADDITIONAL_LIVE_GENERATIONS=0` remain explicit. No empty-cache, unrestricted
redistribution, air-gap, multi-node or production-readiness claim is made.
