# Offline preview packet assembly

`sdk.distribution` assembles existing tested image exports and wheels. It does
not build or start images, install packages, create namespaces, contact Docker,
contact providers or publish an artifact. Its only subprocess is the existing
`helm package` command. Run it after the image and wheel source bindings have
been reconciled with the checkout:

```sh
artifacts/reference-distribution/operator-venv/bin/python -m sdk.distribution \
  --build artifacts/phase2/build-dev19 \
  --wheelhouse sdk/dist/operator-final-candidate-03 \
  --output artifacts/phase2/distribution-final-01
```

The paths above identify the final selected build inputs. Assembly and
deployment retain separate receipts; the detached publication record identifies
the actual final output and digest. Choose a fresh output directory; existing output is refused.
The Python environment needs the existing verifier's PyYAML dependency, and
Helm must be on `PATH`. No Docker daemon or cluster access is needed for assembly.

The helper validates the exported archive hash, exact role source maps, local
source bytes, three SDK build records, all five pinned optional wheels and the
wheel inventory before copying. Only base/caller/embedding and optional chain
images are admitted. An added or missing wheel, an unlisted chart file, symlinked
source, source drift or a mismatched inventory refuses assembly. A later failure
leaves a partial output for diagnosis; it does not claim completion or silently
overwrite that directory on retry.

The packet contains:

- The immutable OCI archive, its import manifest and exact per-image source
  package records. A same-filesystem hardlink avoids another large copy; both
  the source and destination archive must remain immutable. Cross-filesystem
  assembly makes a full copy instead.
- The Helm-packaged chart and three example values from the existing
  `preview_values.generate`: minimal, memory and combined. Both native agent
  consumers and workers are disabled. No live model or chain activation is
  present. These are examples, with generated finite policy expiry; use the
  installed generator to create fresh installation identities and values.
- Exactly eight selected wheels, their build record and actual member/dependency/
  license inventory. Original third-party license files remain in the wheels.
- Byte-exact image-declared Fusion/integration sources plus the public paths
  enumerated in `PUBLIC_FILES`, in `source.tar.gz`. The SDK, examples, operator
  instructions, reviewed evidence and host recipes are also available as loose
  public files. The image dependency inventory names the exact exported image
  archive. Detached publication/digest verification records remain outside
  their own hashed packet to avoid circular identities.
  The explicit examples include single-agent values and qualification, fenced restore,
  shared-source qualification and independent chain observation, with their
  selected fixture tests and direct test helpers. Their inclusion is source
  availability, not permission to run a qualification against an existing scope.
  The shipped hosted-CI recipes also retain their exact selected test sources
  and historical profile fixture files. Install each lane's declared test
  dependencies separately; the eight operator/provider wheels do not claim
  to contain the full CI dependency environment. Including those recipes is
  not an observed hosted-CI run.
- The pinned public ngIRCd executable and its `COPYING` file in the source
  archive when required by the existing image package recipe. No other
  `artifacts/` content is walked or copied.
- Source and host-tool identity inventories, the canonical distribution
  manifest, its external SHA-256 and the existing verifier's detached report.

The manifest uses `omega-single-node-preview-distribution/1` and records
`ASSEMBLY_INTEGRITY_ONLY_NOT_AN_EXECUTED_DEPLOYMENT`. `distribution.sha256`
identifies `distribution.json`; `assembly-verification.json` is a derived report,
not an additional authority input. The same manifest can be checked from an
installed operator environment:

```sh
fusion-verify-artifacts /absolute/extracted/distribution/distribution.json
```

Use [OPERATOR.md](OPERATOR.md) for the artifact-only installation commands.
The actual fresh-namespace integration result must remain separate from offline
verification. The packet neither contains nor grants credentials, approval,
owner journals, generative assets or text-generation authority.

The source-overlay rebuild still requires each cached parent image at its
recorded configuration digest. Parent archives are not exported by this helper.
No empty-cache, air-gap, multi-node or production-readiness claim is made.
Fusion licensing stays `NOASSERTION`; original notices are preserved rather
than replaced with an invented grant. Host executable identities and wheel
metadata do not constitute a complete OS/native SBOM. Vulnerability scanning
remains `NOT_RUN`, and hosted CI remains `NOT_OBSERVED` without separate evidence.

Light tests use tiny authored image/chart/wheel inputs and an explicit Helm
command stub. They are not a real image or deployment qualification:

```sh
artifacts/reference-distribution/operator-venv/bin/python -m unittest \
  sdk.test_distribution sdk.test_preview_distribution \
  tests.test_reference_schema.ArtifactIdentity -v
```

`ADDITIONAL_LIVE_GENERATIONS=0`.
