# Single-node Omega/Fusion deployment evidence

`SINGLE_NODE_SERVICE_INTEGRATION=PASS`

Four independently managed StatefulSets communicate over authenticated HTTPS through ClusterIP Services and Kubernetes DNS on one real k3s node. The actual native Omega loop delegates the existing `neoclaw-nal-truth-deduction/1` operation, retrieves its DeTTa-backed result, consumes and acknowledges its completion, and supplies that result to the next native context. The immutable image has been tested with fresh synthetic owner PVCs.

The [installation and operations runbook](../../deploy/single-node/README.md) contains the ownership diagram, prerequisites, exact build/import/install/upgrade/cleanup commands, Secret contract, resources, probes, retention policy and opt-in fault-test invocation. The chart is [deploy/helm/omega-fusion](../../deploy/helm/omega-fusion/Chart.yaml); the supplied [single-node values](../../deploy/single-node/values.yaml) pin the tested OCI digest.

## Sources and delivered artifact

| Input | Exact identity |
|---|---|
| Task starting checkout | `dba62caf72f9577349cc868edd29fd8b949172d7` |
| Previously pending six-file retrieval publication, preserved separately | `cc6abef8b5524e517b346ed091621f4e4d73d2f4` |
| Deployment implementation and image source commit | `d39d0aa87dd793196afe10daa4288aa6d6a5015c` |
| MeTTaClaw neoclaw | `2af37c3fec18613de54ca42fde2382a9087d4524` |
| PeTTa | `fea83178af3722666d2948d074591d10a3134f56` |
| SWI source, version 10.0.1 | `e58621a91ab7dd530e1e8185ed518f63d851c414` |
| Python native runtime | CPython 3.12.12; exact binary/library hashes in source manifest |
| secured-contract-spaces / DeTTa | `272888f264dd2dde18b574cabb53c266b0dac2ec`, clean isolated build source |
| DeTTa adapter binary SHA-256 | `cb7ed1a27e10e2869ca7357c6c249861623b9849c49fcbf7ef300aa19831f756` |
| k3s | `v1.34.1+k3s1`, image digest `sha256:5e0707cfd1239b358ef73f3254bc3eadc027dd30cd5ec6ca41e29e47652a1b8c` |
| Tested image | `fusion-single-node:single-node-v1`, Linux amd64, 252,272,268 image bytes |
| OCI manifest digest | `sha256:e248411f55865b65525eabf788c322756719fbcaac3b42903d3da004d015029c` |
| Docker image configuration digest | `sha256:083ccfa787d6f7a947d7b563507cae9d51697734515c68fa4eba5fb63ed9ce4d` |
| Local image archive | `artifacts/single-node/image-final.tar` |
| Archive SHA-256 | `48a4ec5a4a2fde8ca863ac969449134a207f67bd4707c55593e1eee387589942` |

The four workloads share one versioned image and select their role through their own ConfigMap. They have separate processes, network addresses, credentials, Services and mutable volumes. No image was uploaded to a public registry. The archive and source/build recipe are available locally; the committed record binds their identities.

[sources.json](../../evidence/single-node/sources.json) records every packaged Fusion source hash, upstream pins, binary/library hashes, chart/test hashes, the Debian base and runtime recipe. The DeTTa offline/locked rebuild reused its existing cache and produced the identical binary hash. The dirty developer sibling checkout was not used. This establishes recorded source/build provenance, not a clean-machine or bit-reproducible compiler build claim.

After the implementation commit, delivery-only changes pin the final digest, document its offline alias and fix demo-certificate CN length while retaining the full DNS SAN. The long-name replacement tests exercise that helper fix. None changes the image's runtime source, numerical profile, caller logic or owner protocol.

## Decisions and changed boundaries

- `NalService` now optionally receives the existing AtomStorage and CompletionDelivery ports. Separated execution refuses local storage/mailbox paths and foreign interface dispatch. Historical colocated composition is retained.
- `service-network` routes the caller's existing envelopes to three explicitly selected service DNS names. Historical loopback selection remains loopback-only. There is no localhost peer, shared owner filesystem or fallback in this composition.
- Two closed authenticated HTTPS endpoints carry immutable atom-create mutations and trusted completion acceptance. They bind descriptor selection and request digest, validate receipts, and preserve principal-scoped idempotency. Public callers cannot access the worker ports.
- Per-service ConfigMaps contain non-secret settings; separately created Secrets contain TLS/auth data. Credentials are materialized only in mode-0600 tmpfs files, not owner PVCs. ServiceAccount token automount is disabled; containers run non-root with read-only root filesystems and dropped capabilities.
- One StatefulSet ordinal and a lifetime PVC lock enforce each writer. Other ordinals and a different owner's PVC seal are rejected. RollingUpdate has no surge; RWO local-path claims are retained on scale-down/uninstall. No HA, distributed fencing or disk-failure durability is claimed.
- Probe paths observe process health only. The native child runs once; failure does not trigger an application retry loop. SIGTERM drains the service within the pod grace period. Explicit test-only barriers allow Kubernetes process-kill tests without releasing the interrupted commit during graceful shutdown.
- Transport JSON nesting is explicitly bounded. Python 3.12 exposed a pre-existing test assumption that the decoder would reject extreme nesting automatically; valid historical envelopes and profiles are unchanged.

The implementation adds no module family or adopted operation. The historical fifteen-family denominator, X01/X02 entries, guarded Fusion PLN profiles, M1–M5 evidence and previously completed real-model/chain workflows remain unchanged. This deployment exercises S01; it does not deploy every adopted Omega command.

## Executed gates

The [machine-readable gate report](../../evidence/single-node/gates.json) links every selected raw observation. Counts below describe each selected scenario, not a throughput benchmark. All successful work scenarios have one job, one numerical attempt, one immutable atom, one mailbox completion and one caller acknowledgment. Original call limits are 64 and numerical-attempt limits are 3.

| Gate | Result | Caller calls | Observed result |
|---|---|---:|---|
| Native delegation and next-context consumption | PASS | 14 | Real pinned result, persisted receipt and acknowledged completion; two native contexts |
| Startup/readiness/liveness and single-writer lock | PASS | 0 | Twelve verified-TLS health reads changed no owner state or budgets; second writer refused |
| Lost execution acceptance response | PASS | 14 | One job and attempt after retry |
| Lost AtomStorage create response | PASS | 16 | Durable immutable create replayed; one atom and attempt |
| Lost mailbox acceptance response | PASS | 14 | Completion replayed; one mailbox item and acknowledgment |
| Caller pod replacement after durable receipt | PASS | 19 | Original identity/deadline/request retained; receipt consumed and completion acknowledged |
| Provider pod replacement after captured numerical output | PASS | 7 | Before kill: job queued, output committed. After replacement: no second attempt, completed delivery |
| Storage service outage and restoration | PASS | 7 | No storage endpoints; committed output remains queued. Restored service completes storage/delivery without recomputation |
| Execution service outage and caller replacement | PASS safety gate | 64 | Non-listening Service target exhausts all calls. Restoration/replacement leaves the caller failed and unacknowledged at 64; no refund or fallback |
| Wrong credential | PASS rejection gate | 1 | `UNAUTHORIZED`; no job, attempt, atom or completion |
| ConfigMap-driven rolling restarts | PASS | 15 | All four pod UIDs replaced; original rows, receipts and budgets retained; graceful shutdown observations |
| Digest-pinned default demonstration | PASS | See raw report | Four healthy pods use the exact OCI digest with fault injection disabled |
| Helm uninstall PVC retention | PASS | — | All four claims remain Bound after uninstall |

The outage safety gate intentionally does **not** produce a successful numerical caller workflow: the provider completed one accepted job, but the caller had no remaining RPC budget to consume its result. The raw failed native status and unacknowledged completion are retained.

Executed automated checks:

- **84** unit/contract/chart/regression methods passed: service boundary tests, Helm rendering/schema checks, historical S01 contracts/application, response validation, M1.1 and S02 fixtures. [Log](../../evidence/single-node/regressions.log).
- **22** historical real native methods passed: original/local/HTTPS command paths, numeric boundaries, authenticated HTTPS validation and actual native-loop recovery. Real NAL/DeTTa/TLS; external model/channel fixtures and declared fault injections. [Log](../../evidence/single-node/native-regressions.log).
- **11** selected real cluster scenarios passed their stated gates, plus the default digest-pinned installation and uninstall-retention check. Nine selected scenarios came from the first final-image run; the two replacement scenarios were executed in fresh longer namespaces after fixing certificate setup. Methods, scenarios and successful workflows are distinct counts.

No full repository-wide M1–M5/chain campaign was rerun. Existing evidence is preserved; the affected historical local/HTTPS paths were exercised. No live text generation, E5 workload, external search, live IRC session or chain operation was performed by this deployment task.

## Failure history and limits of the observations

[run-index.json](../../evidence/single-node/run-index.json) preserves 41 development/final scenario reports with hashes, including failures and superseded assertions. Earlier raw PASS labels are not silently promoted into stronger guarantees.

The recorded problems were: a bad diagnostic import; Python 3.12 nesting behavior; duplicate CA constraints inherited from host OpenSSL configuration; incorrect containerd CLI/import timing; an incorrect test receipt-field name; health observation before scheduling; insufficient scale-down observation time; namespace-PID-1 self-SIGSTOP being ineffective; an outage reaching the original deadline at 27 calls rather than the test's expected 64; and the X.509 CN length limit for two final-run namespaces. Each has a documented correction or narrower interpretation. Final provider interruption evidence requires the explicit queued/output boundary; earlier replacement reports did not establish that boundary. No earlier report is relabelled or removed.

Real providers: native Omega/parser/skill, original NAL function, DeTTa, k3s/containerd, Kubernetes DNS, TCP/TLS and SQLite owner persistence. Fixtures: authored external model responses, unused channel ingress and unused memory facade from the existing controlled S01 composition. The authored model supplies a command and consumes the actual tool result; it does not calculate or inject that result.

Observed guarantees are process/pod-restart persistence and duplicate-safe independent owner commits, current owner-side authentication, retained request identity/deadline/budgets, validated payload/receipt binding, and actual native feedback consumption. There is no exactly-once network delivery claim; uncommitted native computation could be retried within its original attempt budget. Health success is distinct from business completion.

Unrun future gates: multi-node placement, node/storage failure, HA, backup/restore, populated-state migration, production PKI/rotation, network policy hardening, load/capacity qualification and production operations. Local-path claims are node-local; requested PVC size is not a hard disk quota. Secret rotation takes effect on explicit owner/consumer restart. The single-node chart fixes the default `cluster.local` DNS domain. These are documented limits, not hidden fallback paths.

## Review and retained deployment

Start review with [gates.json](../../evidence/single-node/gates.json), [sources.json](../../evidence/single-node/sources.json), [the raw digest installation](../../evidence/single-node/final/digest-install.json), and the [exact changed-file list](../../evidence/single-node/changed-files.txt). [SHA256SUMS](../../evidence/single-node/SHA256SUMS) binds the published evidence files. Credentials, CA/server private keys, kubeconfig, SQLite journals and private build artifacts are excluded.

Only the task-owned `omega-demo` namespace is retained for inspection, with four healthy pods and its completed bounded native session. The isolated `omega-fusion-k3s` Docker node remains running; its API is bound to host loopback port 16443. Test namespaces and their disposable state were removed after observations were saved. [Cleanup evidence](../../evidence/single-node/cleanup.json) records the final resource state. The runbook provides the explicit remaining teardown commands.

`MULTI_NODE=NOT_RUN`  
`PRODUCTION_READINESS=NOT_ESTABLISHED`  
`ADDITIONAL_LIVE_GENERATIONS=0`
