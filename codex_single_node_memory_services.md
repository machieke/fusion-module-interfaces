# Codex handoff — single-node k3s: native memory workflow across module services

## 1. Objective, baseline and authority

Continue `machieke/fusion-module-interfaces` from
`369483360b51baf968ad41b19d6776ac66fe085f`, or record the exact descendant
and relevant intervening changes. Read applicable `AGENTS.md`, the deployed
single-node report/runbook, S03–S03.2 contracts, and the current implementation.
Preserve unrelated work and historical evidence.

**Proposed next increment:** deploy the already implemented native
`remember → query` workflow on the same single-node k3s substrate, with
Embedding, vector Search and authoritative AtomStorage in separate workloads.
Reuse the existing Helm chart and module implementations. Do not develop a new
memory algorithm, framework or module family.

The required outcome is an actual native Omega command creating a previously
absent synthetic memory and finding it in a later turn of the same session,
through pod-to-pod authenticated HTTPS. No operator configuration edit or
operator-side insertion of that target may occur between the commands.

**Keep single-node deployment.** Multi-node placement, node-loss failover,
production hardening, private-memory export and migration are not this task.
**ADDITIONAL_LIVE_GENERATIONS=0.** Do not start/contact a text-generation backend,
reserve a generation, or reuse any exhausted campaign. Real pinned E5 encoding
is allowed and required; authored model responses and channel inputs remain
explicit fixtures.

Do not alter or delete the retained `omega-demo` release/PVCs. Inspect the
explicitly selected task-owned kubeconfig and available resources, then use a
new qualification namespace/release with fresh synthetic state. Do not switch
contexts implicitly or change host-wide cluster/network configuration.

## 2. Evidence baseline and review limits

The reviewed publication records runtime/image implementation
`d39d0aa87dd793196afe10daa4288aa6d6a5015c`; the later publication includes report,
digest selection and certificate-helper changes. Reconcile those relationships
locally, without relabelling historical tests or rebuilding the whole audit.

The prior result reports 84 selected contract/chart/regression methods, 22
historical native methods and 11 real cluster scenarios, plus separate default
installation and uninstall-retention checks. Scenarios are not additional test
methods. One outage scenario deliberately exhausts its caller's 64 calls and
ends without acknowledged completion: it passes its safety assertion, not a
successful workflow assertion.

The review underlying this brief inspected selected pinned public source and
checked-in reports. It did not run the cluster, execute tests, inspect the image
archive, or reconcile every hash. Verify findings in the actual workspace.

Do not claim that earlier live-model or ASI:chain results ran in Kubernetes.
The published single-node composition exercises S01, not every adopted command.

## 3. Source-ledger findings to verify

| Source | Concrete dependency or reuse point |
|---|---|
| `deploy/helm/omega-fusion/{values.yaml,values.schema.json,templates/components.yaml}` | Four fixed roles, one shared image, per-role ConfigMaps and existing Secrets, single-writer StatefulSets/PVCs, checksum rollout and probes. |
| `integration/single_node/{configure,server}.py` | S01-specific configuration and native session; independently hosted owners, lifetime PVC lock and bounded dependency readiness. |
| `fusion/neoclaw_services.py` | Service-DNS routing and narrow private create/completion ports; current public storage exposure is S01 `get`, not full memory/feed support. |
| `fusion/neoclaw_transport.py` | Explicit service-network support alongside historical loopback-only behavior. |
| `fusion/vector_composition.py:ReadService` | Currently constructs FeedAtomOwner/DeTTa and ChromaVector beneath one root; it is not already a separate Search service. |
| `fusion/append_composition.py:AppendService` | Also constructs storage and Search locally; authorization, bound append records and enrollment checks must survive the split. |
| `fusion/{vector_transport,append_transport,embedding_transport}.py` | Existing typed request/reply validation and operation-specific bounds; legacy network bindings are loopback-oriented. |
| `fusion/{atom_feed,lookup_composition,vector_enrollment}.py` | Authoritative acceptance feed, declared storage sessions, stable enrollment and mutation observation. |
| `fusion/adapters/chroma_vector.py` | Rebuildable generations, named maintenance, source coverage and publication observations. |
| `fusion/{embedding_service,neoclaw_embedding,neoclaw_memory,neoclaw_append}.py` | Encoding reservations, captured vectors, retained reads, append progress and native result handoff. |
| `integration/neoclaw/{memory_bootstrap,embedding_caller_build,memory_embedding}.py` | Source-checked native helpers, E5-free caller and metadata-only local compatibility state. |
| `docs/omega-adoption/mettaclaw-neoclaw/s03_2-contract-decisions.md` | Immutable append roles, publication versus readiness, stable UUID/time, retained views, numerical defaults and profile compatibility. |

Preserve the existing MeTTaClaw/PeTTa/SWI, DeTTa, Chroma and E5 pins and numerical
profiles unless an actual packaging incompatibility is demonstrated. Do not
change a model, tokenizer, normalization, metric or SDK merely for convenience.
A container-path relocation needs verified source/asset identities, not disabled
hash checks.

## 4. Workloads and ownership

Extend the same chart with explicitly enabled memory-service configuration.
Retain the original four-workload S01 values as a working regression profile.

| Workload | Owns | Must not absorb |
|---|---|---|
| `omega-agent` | Native loop, accepted occurrences, captured vectors/results, append progress, active/retained read views and permitted local metadata | Remote owners' databases, a fallback vector index, E5 inference |
| `fusion-storage` | Immutable payload/vector/enrollment/binding records, acceptance feed and mutation receipts over real DeTTa | Search generations, embedding, native presentation |
| `fusion-search` | Chroma projection, bounded maintenance/publication state, named generations and source checkpoints | Authoritative corpus, DeTTa files, caller metadata or encoder evaluation |
| `fusion-embedding` | Pinned E5 evaluation and its durable attempt journal | Search, content storage, cognitive state or a new general model API |
| Existing execution/messaging workloads | Their previously implemented owners | Obligatory involvement in every synchronous memory read |

Do not route Search or encoding through a new execution job/mailbox solely to
make every deployed pod participate. Keep the S01 path runnable and test it
separately; inactivity of an unrelated owner is not a defect.

Each mutable owner gets its own PVC, process and service identity. Search may
read the corpus only through authenticated AtomStorage/AtomCommitSource ports.
It must never mount the storage PVC, instantiate local DettaStorage, or inspect
foreign SQL. The agent may retain its legitimate metadata-only Chroma helper;
that does not authorize a local candidate index or fallback document copy.

Use fresh memory-profile state. Do not open the existing S01 AtomOwner journal
as FeedAtomOwner, silently relabel descriptors, or migrate the retained demo.
Preserve the distinction between logical owners, deployment roles and profiles.

## 5. Minimal service separation changes

Reuse the S01 service-DNS/TLS mechanism through a new explicitly selected memory
placement composition. Extend only the necessary typed bindings and composition
injection. Keep old loopback and local profiles and journal guards unchanged.

The memory caller needs separately selected endpoints for encoding, storage and
Search; storage reads must not be proxied through Search merely to retain a
single-endpoint convenience. Candidate hydration is an independent storage call.

Expose the existing bounded storage operations required by append/read/indexing:
immutable approved creates, exact reads/batch reads, acceptance-head/feed reads
and observation of prior mutation receipts. Preserve per-operation validation,
byte limits and source visibility. Do not expose arbitrary content/code/paths.
The small S01 wire-size limits must not be blindly reused for vectors; use the
selected memory profile's limits without loosening all historical endpoints.

Move Search construction to its workload and inject declared authenticated source
and payload ports. Keep enrollment-validation and maintenance authorization
through those ports. Search may possess a narrowly scoped service credential for
its source, but a caller's `principal` string must not confer authority. Document
service identity versus initiating application identity and enforce their binding.
A broad shared administrator token is not a solution.

Preserve the current append protocol: bound intent → immutable records → accepted
source position → named Search publication → local metadata readiness → application
view selection. The owners still commit independently. Observe committed effects
before retrying; never treat a failed observation as proof of non-acceptance.

The new binding must validate certificate identity, selected descriptor/profile,
principal, request digest, response shape, scope and immutable references. Network
failure cannot trigger local encoding, local Chroma retrieval, another model or
an empty successful memory answer.

## 6. Helm, images and operational configuration

Keep one chart and a small, schema-validated memory values overlay. Add only the
component enablement, per-role image override and dependency configuration that
this composition needs. Do not extract a generic chart framework or require a
service mesh, public ingress, registry service or multi-node cluster.

- ConfigMaps: non-secret endpoints, scopes, profile/model identities, bounded
  native script/approved synthetic input policy, limits and log settings.
- Secrets: per-service TLS keys and credentials; reference separately created
  Secrets, never commit actual values or persist them in journals.
- PVCs: each owner's mutable state. Model weights are separate read-only assets,
  delivered in verified image layers or a documented provider-owned preparation
  volume; never mounted from the developer's home or placed in a ConfigMap.

Do not put E5 libraries/weights in the caller image merely because the previous
four roles shared one image. A base image may be reused where appropriate, but
prove `torch`, `transformers` and `sentence_transformers` unavailable to the
network caller and model assets inaccessible. Report residual caller SDKs honestly.

Use suitable explicit CPU/memory/storage requests and limits for actual E5 and
Chroma. The existing small deterministic demo values are not evidence of their
resource requirements. Check node capacity before admission; missing capacity is
a prerequisite, not permission to return fixture vectors or increase deadlines.
No runtime package installation or implicit model downloading during a query.

Retain single writers, owner locks/seals, read-only roots, minimal privileges,
ServiceAccount token restrictions and PVC retention. Do not reset volumes on
Helm upgrade/rollback. Use stable component names and Kubernetes DNS. Verify
config-driven rollouts; secret rotation follows an explicit restart procedure.

Startup/readiness may load and validate provider assets before accepting work;
health checks must not encode text, create occurrences, write corpus records or
consume budgets. Separate provider warm readiness and observer timeouts from the
native operation's original deadline. Readiness is not business completion.

Use ClusterIP-only service endpoints. No Kubernetes API or private keys inside
the native application. If existing NetworkPolicies are used, test the needed
DNS/service flows. Do not claim network isolation or tenant security merely from
separate namespaces and TLS; production policy hardening remains a separate gate.

## 7. Required native workflow

In a fresh generated session with real providers:

1. Establish a ready corpus containing only declared distractors. Show the new
   target memory is absent. A test may inspect state; it cannot supply answer
   references to the caller.
2. Let an explicit model-response fixture propose the native `remember` command.
   Real native parsing, time sampling, embedding and append must execute.
3. Preserve one memory UUID and creation time for the accepted occurrence. Encode
   remotely, capture the vector, and persist its approved immutable records.
4. Build/observe a named Search generation from the real committed feed. Prepare
   the legitimate local metadata view and select it atomically in the application.
5. Return native success only when the selected read-your-writes contract holds.
   Stored-but-unindexed or not-yet-visible work stays explicitly partial.
6. A later fixture command invokes native `query` with text, not answer IDs.
   Use remote E5, Search refs and AtomStorage hydration. Preserve the original
   local ranking/enrichment/uniqueness/presentation and next-context consumption.
7. Demonstrate same-occurrence replay versus a new intentional identical-text
   append; retain an earlier query view/result across the later successful write.

Fixtures select commands; they do not implement encoding, return candidates,
construct payloads or substitute the native result. No real generative backend,
live external channel, public web or production user data is needed.

The main integration must run the caller, encoder, Search and storage in separate
pods with no host-side service secretly satisfying their work. Test Jobs and the
operator can install assets, create approvals and collect observations, but cannot
perform the target append/query as a shortcut.

## 8. Recovery and compatibility evidence

Exercise actual pod termination and stable PVC reopening, with observed UIDs and
commit boundaries, not only a local exception. Required cases include:

- Lost append/storage receipt: recover the original records and one logical UUID.
- Encoder/caller interruption after vector capture: no additional encoder evaluation.
- Enrollment accepted before publication: no false ready/empty result; recover
  the same bounded maintenance identity when still permitted.
- Search pod interruption before/after publication: expose only verified coverage;
  reuse an already published generation instead of allocating unlimited ones.
- Caller interruption after publication/result capture: preserve view, identity,
  time, response and next-context handoff without configuration editing.
- Temporary storage or Search outage: partial/unavailable outcomes stay explicit;
  exhausted budgets remain exhausted after service restoration.
- Delete/rebuild only a disposable derived Search index through authoritative
  ports: recover the declared source snapshot or explicitly refuse an unavailable
  old generation. Do not edit the surviving demo's state.
- Configuration-driven restarts: accepted operations retain their old semantic
  selections and counters; incompatible changes fail instead of rebinding work.

Test wrong credentials, another authorized principal, scope/model/descriptor
mismatch, malformed vectors/references, missing payloads, revocation before
cached disclosure, changed content under an identity, and dependency absence.
Compare original native and earlier adapted behavior on controlled corpus/clock
inputs; do not demand random UUID coincidence or relax ranking with broad float
tolerances. Repeat the existing no-E5-caller and no-legacy-fallback checks in pods.

Use an explicit impact map for regression selection. Rerun original S01 pod
integration and changed storage/feed/append/vector/encoding/native paths. Keep
methods, repeated runs, cluster scenarios and individual kill cases separate.
No live chain/web/generative run is necessary to increase test totals.

## 9. Delivery, gates and stopping condition

Deliver images/artifact digests, verified asset recipe, extended chart/schema,
new values, Secret contract, installation/upgrade/inspection/cleanup commands,
one report and source/test/gate manifests. Report startup and resource
observations without inferring production throughput or speedup.

Preserve the retained `omega-demo` release. Test resources may be removed only
within the new task-owned namespace after evidence collection. Do not leave a
second heavy E5 deployment running by default; document any deliberately retained
resources and their explicit shutdown procedure. Do not stop unrelated processes.

| Gate | Required evidence |
|---|---|
| BASELINE | Exact publication/image relationships and selected S01/owner regressions |
| CHART_IMAGES | Six-role capability, explicit enablement and per-role ConfigMaps/Secrets/PVCs; original S01 values still work |
| OWNER_SPLIT | Search owns only its projection; storage/feed and embedding are independent declared dependencies |
| NATIVE_WRITE_READ | Actual same-session remember → query and next-context consumption through service DNS/HTTPS |
| REAL_PROVIDERS | Pinned native runtime, E5, Chroma, DeTTa and k3s are real; fixtures limited to declared external responses |
| CALLER_NO_E5 | No inference libraries/assets or candidate/payload fallback in Omega |
| VIEWS_FRESHNESS | Honest publication coverage and read-your-writes; earlier queries keep their views |
| POD_RECOVERY | Independently restarted pods preserve logical effects, captures, deadlines and spent budgets |
| AUTH_CONFIG | Current principal/scope/disclosure checks, credential refusal and tested configuration behavior |
| COMPAT_SCOPE | Old profiles/regressions preserved, no migration or new live generation; precise evidence accounting |

A missing dependency/capacity is BLOCKED; wrong executed behavior is FAIL; excluded
work is NOT_RUN. A passing rejection/exhaustion test is not a successful application
workflow. Publish unsuccessful outcomes and rechecks rather than retrying until an
unqualified pass appears.

This task adds **deployment evidence**, not a new memory implementation, module
family, adopted command, or live-model campaign. The historical fifteen-family
inventory and X01/X02 entries do not change.

Final report:

    SINGLE_NODE_MEMORY_SERVICE_INTEGRATION=<PASS or PARTIAL/FAIL>
    PREVIOUS_S01_SERVICE_INTEGRATION=<newly tested result>
    E5_EXECUTION=<actual provider evidence>
    MODEL_RESPONSES=FIXTURE
    ADDITIONAL_LIVE_GENERATIONS=0
    LIVE_MEMORY_MODEL_WORKFLOW_IN_K3S=NOT_RUN
    MULTI_NODE=NOT_RUN
    CHAIN_IN_K3S=NOT_RUN
    PRODUCTION_READINESS=NOT_ESTABLISHED

Then stop. A later task may package ModelInference and the real channel, and a
separate authorization may evaluate live text generation. Neither is included here.

## Review locations

All implementation observations above refer to this immutable tree:

```text
https://github.com/machieke/fusion-module-interfaces/tree/369483360b51baf968ad41b19d6776ac66fe085f
```

The original Kevin/Kabir transcript (00:13:36–00:18:47 and 01:04:49–01:07:39)
supports service-based storage, recall and execution independent of Omega version.
The AGI Benchmarks transcript (00:11:14–00:12:40) distinguishes requesting another
module's work from owning its state. The concrete deployment plan here is a new
engineering proposal, not a claimed meeting decision.
