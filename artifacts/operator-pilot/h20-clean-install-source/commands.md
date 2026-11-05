# H20 clean-install successor — disabled

H19's actual clean installation failed before any cluster/native activity: its source checker unconditionally rejected `fusion.preview_application`, although the exact SDK25 operator manifest includes that helper. The original packet19, source, raw report and failed launcher remain unchanged. H20 corrects only `CHECK_SOURCES`; it does not change installation, verifiers, runtime/SDK, model boundaries or native H19 source.

The new check keeps `torch`, `transformers` and `chromadb` unavailable in every environment. Client/provider environments must still lack the owner helper. For the operator, only the exact installed `fusion.preview_application` source listed in the operator manifest may be available: origin, resolved location, byte count and SHA-256 must match. `PathFinder` inspects availability without importing the package; an import blocker plus before/after module checks prevent execution of the `fusion` namespace. The wheel-generated package initializer is checked for its installed origin, not falsely demanded as a source-manifest row.

[guards-02.log](guards-02.log) records 19 passing methods. Those checks executed only source-validation snippets in disconnected, read-only sandboxes over retained installed packages and explicitly synthetic distribution fixtures. They did not run this complete installation or the native workload. [review.json](review.json) preserves the actual H19 failure and the first successor candidate's two isolated-check failures. There are 38 invocations of 19 distinct methods across the two successor check runs.

The shipped plan is disabled. Root must bind the actual reviewed packet20 digest, publication commit and fresh private outputs separately. Preserve all plan fields except `distribution`, `distribution_sha256`, `output` and `enabled`; the existing `script_sha256` is already the selected H20 source. No passing test or enabled flag grants release. Do not overwrite or reuse H19's failed output.

Selected constants:

- Clean source: `6911b2ccc03042c4d0543b25b0881d01a80cf271f5f0608219b2a79b527371e3`.
- Disabled plan: `9dcd3e230900a14cb68ef4e52a320acf8bffc0edfdd4c8144f77526eb5ed20d8`.
- SDK25 manifest: `f902477c74ed25c5753d5903fa3c9071c6a6820172c3cc6cc8bb8ef2fd27ee90`.
- Runtime14 source: `437927520d53825dc9c642df6cc074d6ccccb3ccaec4bd937402e319baacd6fc`.
- Fresh clean output: `/data/fusion-operator-pilot-release/qualification-private/final-H20-clean01`.

After root's separate preparation/release and actual packet binding, invoke the selected supervisor from that packet once:

```bash
h20_python=/data/fusion-operator-pilot-release/operator25/bin/python
h20_packet=/data/fusion-operator-pilot-release/distribution20
h20_private=/data/fusion-operator-pilot-release/evidence-assembly
"$h20_python" -B -I \
  "$h20_packet/artifacts/operator-pilot/h20-supervision-source/h20-detached-command.py" clean \
  "$h20_packet/artifacts/operator-pilot/h20-clean-install-source/h20-offline.py" \
  "$h20_private/h20-clean-plan.ENABLED.PRIVATE.json" \
  /data/fusion-operator-pilot-release/qualification-private/H20-clean-launch01
```

Do not invoke the original failed H19 clean script or substitute a mutable checkout path. A detached acknowledgment is not installation PASS. Require the supervisor's reaped-child barrier and zero entry exit code, then independently validate the clean primary, original launcher and exact installed verifier. Retain unsuccessful outcomes. No automatic retry or output overwrite is provided.

The installation bound remains1800 seconds; its original outer wait remains1830, and supervision remains bounded by1980 including termination/reaping. The output environments are reused through the existing `/python` and `/work` mounts, not recreated as host venvs. Native work still uses the byte-exact H19 native bundle and original4200-second bound, and requires the separate root release and new clean PASS. Root owns those successor bindings; this bundle does not enable or launch them.
