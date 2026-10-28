# Single-node native memory service evidence

Review [the implementation report and runbook](../../docs/deployment/single-node-memory.md) first. This packet records the bounded `remember → query` deployment increment from `369483360b51baf968ad41b19d6776ac66fe085f`. It does not revise historical adoption counts, fifteen module families, X01/X02, prior live-model campaigns or separately demonstrated chain results.

**Result: `SINGLE_NODE_MEMORY_SERVICE_INTEGRATION=PASS`, within the declared bounds.** The final images run the actual native application, real pinned E5 CPU, real Chroma and real DeTTa in separate pods. Module calls use authenticated HTTPS through Kubernetes DNS. Model commands, channel input and comparison clocks are fixtures. No generative backend was contacted and `ADDITIONAL_LIVE_GENERATIONS=0`.

## Review trail

| Record | Purpose |
|---|---|
| [sources.json](sources.json), [final-source-manifest.json](final-source-manifest.json) | Starting HEAD, upstream pins, binary/model identities, verified packaging recipe and final file hashes |
| [changes.json](changes.json) | Exact implementation/configuration/test/documentation change list; no commit created in this task |
| [images.json](images.json), [packages/](packages/) | OCI manifests, Docker configuration IDs, SDK inventories and source manifests; image archive stays local |
| [image-source-reconciliation.json](image-source-reconciliation.json) | All served image/runtime files match; two unused image copies of operator tests differ explicitly |
| [gates.json](gates.json) | Required gates, limitations, blocked prerequisites and unrun work |
| [tests.json](tests.json) | Method counts, commands, impact map, source epochs and known failures |
| [runs.json](runs.json) | All 42 raw scenario reports: 36 development/final memory executions and six S01 regression executions |
| [final-a/baseline/report.json](final-a/baseline/report.json) | Final-image native workflow, four owner observations, actual pods/PVCs and next-context feedback |
| [workflow-original-native.json](workflow-original-native.json), [native-comparison-final.json](native-comparison-final.json) | Pinned original native oracle and exact feedback/vector/distance/order comparison; only random UUID correspondence |
| [native-final-three-paths.json](native-final-three-paths.json) | Existing original/adapted-local/HTTPS/mixed placement comparison rerun on final served source |
| [native-artifact-index.json](native-artifact-index.json) | Hashes of detailed local historical native traces; method logs are included under `logs/` |
| [measurements.json](measurements.json) | Observed startup and six E5 evaluations; no peak-memory or throughput claim |
| [cleanup.json](cleanup.json) | All fresh qualification namespaces removed; retained `omega-demo` UIDs/specifications/restarts unchanged |
| [publication-check.json](publication-check.json), [SHA256SUMS](SHA256SUMS) | Private-value scan and packet byte identities |

`final-a/`, `final-b/` and `closeout/` each retain their frozen chart, values and source manifest. Reports are copied byte-for-byte, including unsuccessful and interrupted statuses. No Secret objects, kubeconfig, private keys or raw database journals are published. Owner observations contain only this approved generated corpus and synthetic identities. Root logs include harmless paths/Secret names, not secret contents.

## Deployment and operation coverage

| Logical responsibility | Workload / actual bounded operations | Evidence boundary |
|---|---|---|
| Native application | `omega-agent`: remember/query parsing, durable occurrences, captured vectors/results, local metadata, retained views, next-context consumption | Real native loop; authored external model responses and empty channel/global-context fixtures |
| Embedding | `fusion-embedding`: existing query and memory-purpose encoding/disclosure, attempt journal | Real pinned E5; independent PVC; no text generation |
| AtomStorage / commit source | `fusion-storage`: immutable bound create, get/getMany, receipt observation, scoped head and paginated feed | Real DeTTa; authoritative records; application hydration goes directly here |
| Vector Search | `fusion-search`: named build/publication, ready checks, query refs/distances; authenticated source/enrollment validation | Real Chroma projection; no DeTTa instance or foreign-owner files |
| Execution / Messaging | Original separate workloads remain deployed; deterministic S01 delegation/completion tested separately | No artificial job/mailbox added to synchronous memory reads |

Storage acceptance, Search publication, metadata readiness, selected view and native success remain distinct. The baseline records twelve immutable source records, three distinct append UUIDs, three captured queries at positions 4/8/12, six encoder evaluations, four generations and seven model contexts. Neither the fixture nor the operator supplies candidate references or performs the target append.

## Evidence accounting and unsuccessful outcomes

- **Final memory cluster:** 21 distinct scenarios, 24 executions, 21 passing executions and three failures. Two failures exhausted the unchanged 30-second deadline before metadata readiness. The third was an operator probe selecting nonexistent turn zero. Fresh isolated rechecks passed; original reports remain FAIL.
- **Safety-only passes:** `budget-outage` retains all 96 spent observation calls; `expired-enrollment` remains expired across reopening; wrong credentials and current revocation refuse work/disclosure. These are not completed application workflows.
- **S01:** six passing scenario executions across packaging stages, representing repeated baseline/health scenarios. `original-smoke/original` uses the unchanged original published values and image with the extended chart.
- **Unit/contract/chart:** 31 selected methods pass. **Owner regressions:** 46 of 47 pass; the M5 `AtomStorage` runtime protocol/fixture error reproduces on the untouched starting commit under Python 3.12.
- **Historical native:** 42 unique methods initially yield 40 pass and two ten-second failpoint-observer timeouts. Both unchanged failed methods pass in isolated final rechecks; two other already-counted methods also pass there. The four rechecks add no unique methods. Initial source epochs and final frozen rechecks are distinguished in `tests.json`.
- **Development failures:** wrong bootstrap descriptor/missing packaged lockfile; missing image passwd entry; missing service-configuration credential alias; stale-PID observer; absent test config dict. All were corrected and their original evidence retained. `q06/search-before-publication` was interrupted during development; its raw RUNNING status is preserved with an audit explanation.
- **Invocation mistake:** `owner-regression-01.log` contains two nonexistent-module loader errors, not two behavioral tests.

The legacy provider readiness field `caller_canary_inaccessible=false` in pod reports means no separate `denied_canary` was configured for that provider (`embedding_worker.py` emits `bool(cfg.get('denied_canary'))`). It is not a successful canary test and is not used as isolation evidence. Actual caller probes, absent assets/libraries, separate PVC specifications and authenticated ports establish the tested deployment boundary. Historical local/HTTPS canary tests remain separately labelled.

No missing prerequisite remains for the delivered bounded integration. Recovery latency under load, the pre-existing Python 3.12 fixture error and the initial native observer failures remain explicit limits. This task does not establish production readiness, multi-node placement, migration, node-loss/HA recovery, live model/channel operation or chain in Kubernetes.

```text
SINGLE_NODE_MEMORY_SERVICE_INTEGRATION=PASS
PREVIOUS_S01_SERVICE_INTEGRATION=PASS
E5_EXECUTION=REAL_PINNED_CPU
MODEL_RESPONSES=FIXTURE
ADDITIONAL_LIVE_GENERATIONS=0
LIVE_MEMORY_MODEL_WORKFLOW_IN_K3S=NOT_RUN
MULTI_NODE=NOT_RUN
CHAIN_IN_K3S=NOT_RUN
PRODUCTION_READINESS=NOT_ESTABLISHED
```
