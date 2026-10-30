# Single-node model/channel evidence

Review the [deployment report](../../docs/deployment/single-node-model-channel.md),
[gate results](report.json), [test ledger](tests.json), [same-workflow trace](same-workflow-trace.json),
[source reconciliation](sources.json), [images](images.json) and [changes](changes.json).

This packet records real native Omega/E5/Chroma/DeTTa/Messaging/ngIRCd and pod HTTPS
with **recorded model responses**. All live generation counters are zero. Future
live configuration is disabled and incompletely frozen. The known M5 baseline error
remains open; a separately selected historical launcher test was skipped.

`runs/` preserves synthetic read-only per-owner projections, logs and non-secret
configurations, including unsuccessful executions. No raw databases, kubeconfig,
credentials or private keys are published. Raw reports retain their original hashes.
`packages/` pins each development image's runtime source files; `historical/` retains
the q06 driver and original final image observation. Historical source gaps are
explicit in `sources.json`, not reconstructed as executed identities.

There are 18 distinct workflow scenarios in 25 executions: 20 assertion passes,
including 12 correct complete recorded workflows and eight negative safety results;
five unsuccessful executions remain recorded. Four independent final-image S01/memory
regression executions pass. The final selected unittest run contains 85 methods,
84 passing and one skipped. None of these denominators should be added together.

`cleanup.json` and `cleanup/` establish that retained `omega-demo` identities and
specifications are unchanged, with four Ready pods and no remaining task namespaces
or PV claims. Images and pinned source/assets remain cached locally. The image
archive is local-only; its SHA-256 and rebuild/import recipes are published.

`SHA256SUMS` indexes this packet. `final-source-manifest.json` hashes the final source
and documentation outside the packet. `publication-audit.json` records source/value
reconciliation and an exact-value scan against the generated private test credentials.
The checked source is the commit containing this packet; the explicit baseline is
`1af14c48d33a2976d954fa715bb5c2e1bdcf9483`.
