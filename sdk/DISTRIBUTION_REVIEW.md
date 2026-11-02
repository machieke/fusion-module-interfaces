# Development distribution review

This review records the bounded SDK/operator inspection on 2026-11-02. It does
not replace the final image/source freeze or the programme's deployed tests.
No package was rebuilt during this inspection; no runtime, cluster or generative
endpoint was contacted. Later package refreshes have their own qualification.

The reviewed eight-wheel set is
`sdk/dist/operator-install-development-01`. Its exact development inputs,
package hashes and source bindings remain in
[`operator-install-qualification-01.json`](operator-install-qualification-01.json)
and [`operator-wheel-inputs.json`](operator-wheel-inputs.json). That operator
wheel predates the preview distribution verifier and remains historical.

## Actual wheel dependencies and license metadata

These values were read from the wheels' `METADATA` and embedded license files,
without importing their modules. The wheel inventory hashes every member,
including license files. License expressions below are recorded metadata, not
a separate legal review or a grant of rights.

| Package | Version | Declared license | Required dependency on this CPython 3.12 selection |
| --- | --- | --- | --- |
| fusion-module-client | 0.2.0 | `NOASSERTION` | None |
| fusion-file-feed-example | 0.2.0 | `NOASSERTION` | fusion-module-client >=0.1.0,<0.3.0 |
| fusion-preview-operator | 0.2.0 | `NOASSERTION` | fusion-module-client ==0.2.0; selected extras below |
| PyYAML | 6.0.3 | MIT | None |
| cryptography | 50.0.2 | Apache-2.0 OR BSD-3-Clause | cffi >=2.0.0 |
| cffi | 2.1.1 | MIT-0 | pycparser |
| pycparser | 3.12 | BSD-3-Clause | None |
| pycryptodome | 4.0.0 | BSD-2-Clause AND Unlicense | None |

All five third-party wheels contain their declared license files; cryptography
contains both alternative license texts. The three Fusion wheels contain no
license metadata or license text. Their status remains `NOASSERTION`; this
review does not invent a project license or claim unrestricted redistribution.

The operator's `preview-install` and `artifact-verification` extras select
PyYAML 6.0.3. `chain-key-setup` selects cryptography 50.0.2, pycryptodome 4.0.0,
cffi 2.1.1 and pycparser 3.12. The latter is synthetic key provisioning only.
The selected CPython 3.12 environment does not activate cryptography's
pre-3.11 typing-extensions condition, SSH extra, or pycryptodome's test extra.
No dependency of the selected extras is missing from the eight-wheel set.

The binary wheel selection qualifies Linux x86_64 with CPython 3.12, including
cryptography's manylinux 2.28 floor. Other platforms need their own artifact
pins and qualification. The download command and configured-index origin are
recorded, but original package download URLs were not retained. This is not an
empty-cache, air-gap, native-library inventory or vulnerability-scan result.

## Preview verifier evidence

[`distribution-verifier-development-01.json`](distribution-verifier-development-01.json)
records 12 passing methods: 11 new fixture methods and the historical
`ArtifactIdentity` regression. The new tests construct small authored OCI
descriptors, source records, chart bytes, wheel ZIPs and profiles. They never
install a wheel, execute an image or submit work. Positive preview cases cover
the required three role kinds and the optional isolated-chain image. The
historical distribution schema remains accepted.

Refusal cases cover canonical manifest bytes and its external digest; duplicate,
absolute, escaping and stale file entries; unregistered secondary references;
profile and image selection; model/live authority; source identity; OCI
configuration linkage; changed wheel payloads; and inconsistent wheel inventory.
These are offline integrity checks. An integrity pass alone is not evidence of
a runnable chart, a complete dependency closure, live authority, or successful
native/provider behavior. Later verifier results retain separate source identities.

## Integrated publication conditions

The final publication needs one reconciled set of tested source identities,
role-image manifests/configurations, source-package records, chart, selected
values, SDK wheels and wheel inventory. Rebuild the operator/client/example
packages only after the shared source freeze, then perform the isolated
install/compatibility checks against those exact artifacts. An accumulation of
development passes does not establish an immutable final-distribution pass.

The preview bundle must list every secondary artifact used by the verifier and
install commands, including all selected optional wheels. The final artifact
producer must include the portable [operator instructions](OPERATOR.md),
supported examples and evidence using an explicit public-file selection. Never
include operator access tokens, fresh Secret directories, owner journals or
machine-local credentials. Existing image/OS/native inventories and their
licenses remain separate parts of the outer distribution inventory.

The fresh-namespace installation from extracted artifacts remains a programme
integration gate. The SDK's real TLS/crypto tests use explicit kubectl/Docker
stubs and do not establish that gate. Actual browser/workbench, Helm, image
import and native workflow results must reference the final artifacts. Hosted
CI remains `NOT_OBSERVED` until an actual hosted run is recorded;
`vulnerability_scan=NOT_RUN` remains separate from dependency enumeration.

`ADDITIONAL_LIVE_GENERATIONS=0`. No multi-node, production-readiness, live-model
or new adopted-command claim follows from this packaging work.
