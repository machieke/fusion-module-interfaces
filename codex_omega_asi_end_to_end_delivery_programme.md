# Codex delivery programme — end-to-end Omega / DeTTa / ASI:chain reference distribution

**Primary repository:** `machieke/fusion-module-interfaces`  
**Starting reference:** `fd54e61289ecf8e729f28d501d974aa662517f90`, or the actual verified descendant containing completed later work  
**Deployment:** one existing, explicitly selected k3s node; Helm-managed services and independently owned persistent state  
**Delivery mode:** one outcome-based programme; fourteen internal work packages; one integrated handoff  
**Live text-generation allowance during engineering:** **ZERO**  
**Status of this document:** proposed expanded implementation assignment; becomes the task scope when the user assigns it to Codex

## 0. Deliver the reference distribution, not another next-step proposal

Build an installable, recoverable, inspectable **single-node Omega service reference distribution** using the existing module implementations. It must demonstrate native memory, evidence, priority, messaging, recorded-model interaction, deterministic delegated execution, and an isolated chain-backed commitment through the appropriate interfaces.

Include the runtime artifacts, charts, scoped authorization, operator commands, deployment/recovery qualification, backup/restore drills, diagnostics, CI, performance baselines, and a complete disabled campaign for the later live-model evaluation.

This document REPLACES `codex_omega_single_node_completion_batch.md` as the primary assignment. It includes that document's work packages A–G and adds substantial engineering scope. Do not require the operator to merge the two backlogs or send another brief for a package already included here. Earlier specifications remain sources for behavioral contracts and historical evidence, not repeated stop/review checkpoints.

### Deliberate scope expansions

Unlike the previous batch, this programme includes:

- Separately deployable C1, C2, Attention and Relations capabilities under **new, explicitly synthetic same-node service profiles**, while retaining the historical local-only private profiles.
- One real isolated single-validator F1R3node deployment and the existing fixed, approved-result commitment path in k3s. No generative model is needed for that path.
- Recoverable demonstration-state backup and restore, safe compatible upgrades, certificate/credential rotation, observability, bounded load characterization and CI.
- A final reference-distribution bundle and executable operator walkthrough, rather than a collection of intermediate research reports.

These are new engineering tasks in this proposal. They are not assertions that earlier meetings approved these concrete deployment choices or that existing code already supports them.

### Working agreement

1. Inspect the actual checkout once, identify which requirements already work, and continue from those bytes. Never discard a later implementation to return to a historical parent.
2. Implement, test, correct and integrate all ready packages. An internal gate is a test assertion, not a request for another user approval.
3. Choose reversible engineering details yourself: filenames, narrow adapters, test organization, compatible internal refactors, image layers, resource sizing within the selected host, and implementation order.
4. Reuse owners, profiles, source locks, native adapters, charts, test tools and campaign machinery. Do not create a replacement agent, generic orchestration platform, new service mesh, new evidence framework or new campaign database.
5. Do not stop because one runtime asset, chain API or optional execution permission is missing. Record the exact blocker and continue independent work. Do not call unfinished implementation an external blocker.
6. Fix defects exposed by this assignment. Preserve the invariant the failing test protects; do not weaken the test to obtain a green result.
7. Maintain one concise progress ledger: package, state, source identity, tests, artifacts, blocker and next concrete action. Avoid a new narrative document for every substep.
8. Parallelize independent read-only inspection or builds only where resources permit. Serialize edits to common contracts and heavy same-node qualification runs. Parallel work must not contend over journals, namespaces or the final freeze.
9. If a session boundary prevents completion, checkpoint the existing programme with exact commands, paths, unfinished tests and resource ownership. Resume this same assignment; do not propose a new task. Do not claim asynchronous work will continue.
10. Finish only after all authorized feasible work is implemented and evaluated, or every remaining path has a concrete external prerequisite. A failing but repairable test is work to perform, not a reason for immediate closeout.

## 1. Scope and authority — large engineering scope, explicit consequential boundaries

### 1.1 Included when this assignment is given

- Inspect authorized repositories and assets; implement changes in this repository and permitted narrow upstream overlays.
- Build and import versioned images, inspect their contents offline, and obtain pinned dependencies through existing authorized access.
- Install, upgrade, scale and remove **task-owned** workloads in fresh namespaces on the selected existing single-node k3s cluster.
- Run actual native MeTTaClaw/PeTTa/SWI, deterministic NAL/PLN, E5, Chroma, DeTTa, module services, isolated ngIRCd, independent test peers and authenticated internal HTTPS.
- Run explicitly selected recorded-response ModelInference backends, including fault injection. These are not live-model evidence.
- Deploy and run a disposable local F1R3node with generated unfunded test keys and fresh genesis, with verified network isolation. Submit only the already supported fixed commitment operation for approved synthetic artifacts.
- Exercise fault/recovery, synthetic backup/restore, bounded resource/load tests, scoped network policy and credential rotation within task-owned resources.
- Prepare immutable distribution artifacts, offline-verified real-generative-runtime packaging, and disabled future live-run plans.

This grants no permission to mutate retained user deployments. A namespace, PVC or process must be proven task-owned before destructive tests.

### 1.2 Not authorized by this assignment alone

- Starting, loading, contacting or evaluating a **real text-generation runtime**, including an image smoke test, warm-up, readiness generation or an allegedly harmless API probe.
- Reserving or spending any live-generation slot. Historical allowances remain exhausted.
- Public-chain transactions, funded wallets, public IRC, organizational channels, new paid hosted services or exposure of a public endpoint.
- Using existing private memories, prompts, beliefs, source events or identifying hashes in networked tests. Synthetic same-node service profiles do not authorize private-data export.
- Modifying `omega-demo`, unrelated namespaces/PVCs, host-wide firewall/network settings, cluster topology or unrelated dependency working trees.
- Multi-node execution, cluster HA, distributed-storage replication, a production multi-tenant claim, existing-state migration, new mathematical policies, arbitrary tool execution, on-chain model inference or a new consensus algorithm.
- Publishing secrets, restricted source, credentials, private keys, kubeconfig or unredacted journals.

Real E5 encoding and deterministic native reasoning are permitted and must be counted separately from prohibited text generation. A default-deny setting is not evidence that no generation occurred: prove denial and collect counters.

### 1.3 Publication and external approval

Follow current repository/user permissions for local commits and push. Make task-only commits where permitted; do not stage unrelated work, force-push or release/upload artifacts to new external destinations without authority. Lack of push permission does not block implementation, local verification or preparation of an exact publish command.

The future live procedure is included in Section 9. It requires a **new approval bound to the final campaign**. No further technical design brief is needed after that approval. Engineering does not wait for it.

## 2. Definition of the delivered system

### 2.1 Component responsibilities, not one pod per type

Use the existing Helm chart with explicit profiles/enablement. The following are logical deployment roles; retain existing names where possible.

| Role | Owned behavior/state | Forbidden shortcut |
|---|---|---|
| Omega agent | Native control loop, accepted inputs/commands, prompt/result captures, application read-view selection | Access to provider databases, local fallback implementations hidden in the caller |
| Storage / DeTTa | Immutable scoped payloads, vectors/enrollments, acceptance feed and mutation observations | Search policy, evidence mathematics, attention decisions |
| Vector/exact Search | Derived indexes, generation maintenance/publication and scoped queries | Authoritative duplicate corpus or direct storage-file mounts |
| Embedding | Pinned E5 evaluation and applicable attempt accounting | Searching or reading unrelated memory/history |
| Messaging | Mailbox acceptance, ordering, acknowledgment and deduplication | Claiming socket receipt is durable acceptance or guaranteed external delivery |
| Execution | Named deterministic operation admission, reservations, results/outbox | Arbitrary code/tool surface or writing foreign owner state |
| ModelInference | Model-call admission, spent reservations, captured responses and observation | Tool authorization, memory ownership, automatic fallback/regeneration |
| Channel bridge | Durable input capture, relay progress and bounded external-send observations | Treating nickname/text equality as source identity or automatic ambiguous resend |
| EpisodicMemory | Occurrences, provenance, episode ordering and delivery intent | Authoritative truth aggregates or fabricated source roots |
| BeliefRevision | Priors, admitted contributions, alternatives and decisions | Attention updates or substituting a different numerical policy |
| Attention | Selected existing priority policy, revisions, timestamps and receipts | Evidence/truth updates or reinterpreting promotion as reference STI |
| Relations | Existing structural relation assertions and bounded traversal | Assigning truth/priority or silently adopting unsupported native mutation commands |
| Chain commitment adapter | Approved artifact binding, signer authority, durable signed intent and chain observations | Arbitrary deploy code, private-data publication or using chain availability as storage acceptance |
| Isolated F1R3node | Existing fixed commitment effect and its observable finality | Claiming off-chain computation is validator-executed or verified |

Keep pure numerical kernels and bounded controllers colocated with their legitimate consumers when an independent process adds no useful boundary. Registry/resolver/authentication may remain shared libraries and configuration where that is the current architecture. Do not create fifteen or seventeen mandatory pods to satisfy a catalogue.

Each independent mutable owner has its own PVC, identity and single-writer enforcement. Multiple containers may share a pod where explicitly justified, but different owner journals remain distinct. Never use shared mutable files to avoid a missing protocol.

### 2.2 Supported profiles

At minimum retain independently runnable configurations for:

1. Existing deterministic four-service S01 demonstration.
2. Memory-only native remember/query across storage, Search and Embedding.
3. Recorded retrieval-to-reply across deployed model owner, bridge and real IRC.
4. Synthetic cognitive-owner workflow over separately selected service ports.
5. Optional isolated-chain commitment of one actual deployed deterministic result.
6. Live-capable model deployment that is **guarded and inactive without approval**.

A small operator profile selector is sufficient. Do not create a framework for combinatorial permutations. Test the supported combinations, reject unsupported ones explicitly, and retain all historical profiles under their original semantics.

### 2.3 Functional completion versus evidence classes

The core distribution must have executable code and actual in-cluster evidence for required non-generative paths. Runtime image inspection, recorded model responses, real deterministic computation, real chain execution and future real generation are different classes.

Do not describe the entire native tool catalogue as adopted. Keep the bounded fifteen-family inventory, X01/X02 extensions, native-command counts, deployment coverage and integrated workflow evidence separate.

## 3. One discovery pass and one dependency-driven work graph

The supplied last completion states that `fd54e612...` contains recorded retrieval-to-reply deployment, a selected suite of 84 passes plus one skip, an OPEN M5 fixture/protocol regression, and an incomplete future real-runtime/campaign preparation. These are **reported historical results**, not new passes. Newer descendants may already fix or implement parts of this programme.

Inspect applicable AGENTS.md and map the current equivalents of:

- `deploy/helm/omega-fusion/`, per-profile values, image builders/importers.
- `integration/single_node/`, especially `future_live.py`, deployment runners and scoped cleanup.
- `deploy/single-node/future-live/` and the existing campaign controls.
- `fusion/model_service.py`, `retrieval_services.py`, memory/vector/embedding services and transports.
- `fusion/{episodes,beliefs,evidence_relay,promotion,relations}.py` or their current equivalents, and exact S04/S05/M5 native adapters.
- `fusion/adapters/f1r3_m4.py`, original chain source/build/runtime/readback fixtures and signer implementation.
- Known failure `tests.test_m5_boundaries.Boundaries.test_lookup_has_no_cognitive_runtime_dependency_or_mutation` and the skipped historical isolation launcher.
- Current deployment, adoption and per-run source/image/test evidence.

Record actual HEAD/worktree, selected cluster/context, dependency and model availability, available disk/CPU/RAM, protected-resource identities and permitted publication actions. Reconcile relevant changed files and image provenance once. Do not repeat the 1,509-entry historical audit merely because this is a new assignment.

### Work packages — all are part of this assignment

| ID | Package | Exit evidence | Principal dependencies |
|---|---|---|---|
| A | Baseline defects and invariant-preserving cleanup | Supported tests repaired or precise genuine exception; impact map | Discovery |
| B | Reproducible role images and assets | Immutable artifacts, packaged hashes, caller/provider separation | Discovery; A as needed |
| C | Complete Helm profile matrix and lifecycle | Executable installs, upgrades, guards and retained state | A/B |
| D | Cross-service identity, disclosure and scoped security | Positive and negative service traffic/authority tests | Existing services; C |
| E | Deploy existing cognitive and relation owners | Actual native/source-owned workflows and service isolation | C/D; existing S04/S05/M5 |
| F | Deploy isolated chain-backed commitment | Same-artifact real effect/finality and restart/readback | B/C/D; available pinned node |
| G | Integrated functional acceptance suite | Final-image native workflows, no answer injection, clear modes | C/D/E; F adds chain workflow |
| H | Fault, restart and compatible-upgrade qualification | Lost-reply/restart/rotation/rollback invariants | G |
| I | Backup and restore without replaying effects | Scoped quiesced restore drill, safe accounting fence | Owner inventory; C/D/H |
| J | Observability and diagnostics | Actionable non-mutating status, metrics and sanitized traces | Existing state readers; parallel |
| K | Bounded resource and performance characterization | Baseline measurements and honest capacity envelope | Stable G; J |
| L | CI and distribution verification | Fast/native/cluster lanes with hard zero-generation controls | A/B/G/H |
| M | Unified operator tooling and reference handoff | Reproducible CLI/runbook/archive and coverage map | Progresses alongside all packages |
| N | Final campaign freeze and delivery | Exact approval-ready disabled plan and source/image map | Stable tested artifacts and setup |

Run independent packages despite blockers. For example, missing model blobs block complete B/N but not recorded workflows, cognitive deployment, CI or chain integration. Missing F1R3 source blocks F, not all memory work. Missing live approval blocks only Section 9.

## 4. Package specifications

### A. Baseline defects and invariant-preserving cleanup

1. Reproduce the OPEN M5 boundary test under the supported interpreter. Establish whether the error is in a Protocol definition, fixture exposure, runtime-check behavior or a real provider mismatch.
2. Fix narrowly and retain the hostile-port purpose: the consumer may call only declared methods and may not depend on foreign SQL/private attributes/cognitive runtimes. Add a negative incompatible-provider case. Do not remove `isinstance` or equivalent validation without providing an equally explicit supported check.
3. Execute the historical isolation test through its proper launcher with real generative access denied. An unavailable launcher is an exact missing prerequisite, not a pass.
4. Inspect shared-file paths, direct-owner constructions and endpoint assumptions only in the changed/deployed paths. Remove demonstrated violations through existing typed ports; do not sweep unrelated code into a refactor.
5. Consolidate genuinely duplicated configuration/validation helpers when needed for the supported profiles. Avoid a new universal `execute(anything)` API or a permissive validator union.
6. Maintain a small change-to-consumer-to-test impact map. Carry genuine unchanged baseline exceptions openly; never waive a new required failure by association.

**Exit:** corrected supported baseline with preserved invariants, or a precise OPEN exception and its bounded impact. All other packages continue.

### B. Reproducible role images and verified assets

Build separate role images when dependencies differ; do not force a unique image for every role. Keep the Omega caller free of E5 inference and generative-model assets. Pure math runtime reuse is permissible under source-checked numerical profiles.

For E5, Chroma, DeTTa, native reasoning and the generative backend, preserve the actual pinned source/model/runtime selections. Verify artifact content, not just build inputs. Capture image configuration/manifest identities, archive hashes, installed lock information and an inventory of relevant third-party components/licences. Use available SBOM tooling if present; an honest dependency manifest is preferable to installing an unrelated platform.

For the **generative-runtime image**, inspect the packaged executable, dynamic-loader requirements, required libraries, model manifest and every referenced weight/projector blob with full hashes. Static inspection must not run the executable, load the model or issue a backend request. Verify relocated lock paths without disabling checks. Record `OFFLINE_VERIFIED` separately from `RUNTIME_NOT_CHECKED`.

Model assets may be in immutable layers or a verified read-only provider asset volume. No developer-home mounts, request-time downloads, or unverified unpinned assets. Cached expensive verification is keyed by the complete immutable artifact identity, not a mutable tag.

Package the existing chain runtime similarly, but its disposable real execution is permitted in F. A source fingerprint does not supply undistributed changes: obtain authorized exact inputs or explicitly rebaseline on an obtainable immutable revision and rerun applicable checks. Do not silently alter consensus/resource controls.

Provide build/import/verify commands, architecture and CPU assumptions, artifact sizes and resource prerequisites. Do not publish restricted assets or image layers to a public registry without permission. A local distribution is sufficient.

**Exit:** actual verified artifacts or precise missing inputs; no generative-runtime activation. Continue feasible packages when one artifact is blocked.

### C. Complete Helm profiles, persistence and guarded activation

Extend the existing chart, schema and values. Each component receives non-secret configuration through ConfigMaps, scoped credential/TLS references through Secrets, and its own mutable state on PVCs. Use Kubernetes service DNS, authenticated HTTPS for module APIs, explicit supported endpoint profiles, resources, minimal service accounts and deliberate rollout checksums.

Retain single-writer owner locks, seals and journal-profile binding. Choose workload types based on state/lifecycle needs; do not claim replica count or PVC mode alone proves exclusive ownership. No HPA or multiwriter behavior for single-writer journals.

Profile installs must not rely on preexisting files in the developer workspace. Validate dependencies and incomplete configurations before starting business work. Keep health probes non-mutating: no embedding, generation, message consumption, job submission or chain deployment. Provider asset loading/readiness must be distinguished from accepted-operation deadlines.

For live-capable ModelInference, colocate the runtime with its owner where suitable and bind backend HTTP to pod-local localhost. Expose only the authenticated module API. Guard **both provider activation and real runtime process startup**, before exec/model loading/contact. An enabled Helm value, successful fixture test, copied approval filename or manifest digest does not grant permission.

Test guard paths using harmless sentinels and recorded providers. The default remains recorded/disabled. Do not start a real runtime with a test approval to prove denial.

Provide retained-state upgrade and cleanup behavior. Fresh synthetic profiles are acceptable; no migration of historical private or populated user journals. Compatible rollouts preserve accepted configuration; incompatible ones fail with a reason rather than silently rebind state.

**Exit:** all supported profiles install under exact values; disabled live mode cannot activate; old installs still work.

### D. Cross-service identity, disclosure and scoped security

Eliminate remaining shared mutable policy/receipt dependencies in the deployed paths. Static shared policy may be distributed deliberately; dynamic decisions must cross declared authenticated boundaries or remain with their owner.

Implement/retain distinct authorities:

- Caller approval of content, exact input/result and intended recipient.
- Provider permission to invoke the selected operation and disclose the result.
- Service identity for restricted reads performed on behalf of an initiating actor.
- Exact issuer/recipient/principal/scope/occurrence/profile/view/prompt binding on transported receipts.

A certificate authenticates a channel/endpoint under its selected trust policy; a digest checks identity/integrity; neither is blanket permission. A principal string cannot delegate another actor's rights. Metadata-only preflight must be available where provider permission needs checking before content disclosure. Recheck live authority at effect, capture observation and result-release points.

Add/reuse namespace-scoped NetworkPolicies and verify actual allowed/denied traffic on the existing CNI. Include DNS, readiness, bridge-to-IRC and intended dependency flows. Do not alter cluster-wide networking. Where enforcement is unavailable, record that gate BLOCKED instead of reporting policy YAML as isolation.

Exercise certificate expiry/mismatch, same-principal credential rotation, wrong-principal substitution, revocation, wrong Service/profile/recipient, unauthorized pod and malformed/swapped receipts. Rotation cannot reset journals or permit replay under a new identity. Keep keys out of ordinary logs, ConfigMaps and distribution archives.

Network isolation is a bounded tested control, not protection from a malicious host or production tenant-security certification. No new PKI platform or service mesh is needed.

**Exit:** service communication has tested authority and network boundaries with no foreign filesystem dependency.

### E. Deploy the existing cognitive and Relations owners

This package expands placement of already implemented responsibilities; it does not add new mathematical capabilities.

1. Inspect the current C1/C2, NAL revision, promotion and Relations ports/profiles. Preserve native numerical functions, historical PLN versus NAL distinctions, prior/evidence tagging, exact provenance and model-specific validators.
2. Expose independently selectable C1, C2 and Attention services using the existing transport/enforcement infrastructure. Add only the missing typed operations required by their existing native consumers: admission/read, exact receipt observation, trusted evidence completion, promotion adjustment/snapshot/ranking. Do not expose owner internals or generic SQL/evaluation.
3. Add the existing Relations reference provider to the chart with actual assertion/traversal conformance. This is reference-service deployment. It does not silently adopt MeTTaClaw `link`, `unlink`, `forget` or `update` where their semantics remain unresolved.
4. Keep old `private-local-only` profiles intact. The new pod-to-pod positive tests use a separately declared **synthetic same-node service composition** with specific approved records and recipients. Actual private C1/C2/Attention state remains untouched. Different pods are not equivalent to private local calls.
5. Preserve separately owned commits and C1–C2 delivery closure. Source recording must remain usable when the mathematical provider is unavailable. A retained alternative can close processing without implying numerical revision.
6. Exercise actual native `remember -> recorded source -> support/contradict -> query -> promote/demote -> query/getContext` through selected owners using recorded model/channel inputs where needed. A fixture may select commands, not supply numerical results, provenance or ranked memories.
7. Distinguish command occurrence from evidence contribution and from priority adjustment. A new command citing old evidence adds no weight; a new intentional promotion may add one bounded adjustment. Neither increases the other's state.
8. Preserve the same native time policy and stronger admitted backward-clock restrictions; old accepted views/captured results retain their snapshot and evaluation time.
9. Hydrate global context through storage in the selected order. Do not replace it with fixture text or a legacy full-content database. Keep derived presentation files rebuildable from owners.
10. Include a direct-port hostile provider and, where already available, the independent same-profile Attention implementation in the unchanged consumer tests. Do not develop competing attention policies.

Do not make the future real-model campaign disclose the cognitive test corpus. Use separate scopes, sessions and storage bindings. A small deterministic cognitive workflow can be qualified independently of the retrieval-grounded real-model campaign.

**Exit:** real deployed owner separation and native command/readback evidence on synthetic data; historical private profile and mathematical contracts unchanged. Interface gaps must receive a concrete adapter/profile implementation or a specific blocker, not a renamed fixture pass.

### F. Real isolated ASI:chain commitment in k3s

Deploy the existing chain commitment adapter and pinned F1R3node in a disposable, isolated single-validator configuration. Leave this profile disabled in the default install. When this expanded assignment is given, the task-owned deterministic chain qualification is included; no text-generation permission is needed.

Use generated unfunded test keys, a fresh genesis and dedicated PVCs. No public network, bootstrap peers, funded wallet, external signer or real user data. Verify actual bound interfaces and permitted/denied connectivity rather than trusting a network name. Internal validator ports are not public module APIs. Do not disable consensus/resource protections to make a demo pass.

Reuse the existing fixed commitment template, exact-result approval, durable signed-intent journal and node observation API. Identify one **actual approved synthetic result created by a native in-cluster workflow** supported by that adapter, preferably the existing `inspect_atom` path. Preserve its domain; do not broaden to arbitrary hashes/code just to accept a different result. A needed thin native invocation adapter is permitted, not a new execution engine.

Required path:

`native operation -> deployed execution/storage -> verified persisted result -> exact-artifact approval -> commitment owner -> real node -> block/post-state effect readback and matching finality -> independent observer`.

Bind approval to the result bytes/ref/digest, allowed fixed operation, chain instance, signer and limits. Prior test artifacts, evaluator constants or an unrelated transaction do not pass the same-artifact gate. Full private cognitive records and their hashes are excluded.

Retain the signed bytes before submission. Lost replies and process restart recover the identical signed intent; no silent resigning, new timestamp, replaced genesis or duplicate off-chain job. Inclusion, execution success, actual effect and deploy-effect finality remain distinct. Query the actual stored effect, not its source term or RPC echo.

Run real adapter/node pod restart on retained generated data, node outage, uncertain submission and key-free readback by another process/pod. A submission error is not a missing prerequisite; a finality timeout is not PASS. Keep the no-chain memory workflow operational while the node is unavailable.

Hard-bound each run by declared deployments, observer calls and local resource limits. This is not a load/consensus-research programme. If source/build/isolation requirements cannot be met, finish the interface/chart/tests and mark the real gate BLOCKED; do not count mock finality as chain integration.

**Exit:** actual isolated k3s chain effect/finality for the same deployed synthetic artifact, or a specific partial package. This is off-chain execution with an on-chain commitment, not chain verification of the computation.

### G. One integrated acceptance suite against the final selected images

Create a single executable qualification entrypoint with named independently selectable scenarios. Reuse existing harnesses. Tests must drive the actual workloads; host-side code may observe or operate the peer but may not secretly perform the target query, inference, commit or send.

Required scenario families:

- Deterministic native delegation using execution, storage and Messaging.
- Native append then recall through deployed E5, storage/feed and Search.
- Recorded-model IRC retrieval-to-reply, including exact actual query feedback in the next prompt.
- Cognitive-owner native sequence from E with independent truth/priority effects.
- Relations assertion/traversal plus authoritative payload retrieval through separate ports.
- Same-artifact chain path from F, separate from cognitive/private scopes.
- Wrong-authorized answer, prohibited command, target absent, unready Search, missing payload and unauthorized prompt disclosure.
- Two synthetic corpus variants changing the actual retrieved fact; fixed model outputs are not evidence of model understanding.

The measured retrieval session starts fresh from native setup's ready view. It must not inherit setup history or answer-bearing promoted context. All candidate reply bodies are equally eligible; the evaluator knows correctness but cannot supply the answer to the model/consumer.

Keep the real model substituted. A recorded-response provider must run the actual ModelInference owner lifecycle and be explicitly selected. Failed real-runtime availability cannot select a fixture automatically.

Run a coherent final-image subset after shared changes settle. If a runtime/image correction occurs, rerun affected scenarios and identify superseded evidence. Reuse verified unchanged heavy layers. Counts are outputs of coverage, not targets.

**Exit:** actual workflow evidence tied to final artifacts, with successful tasks, expected rejection/exhaustion assertions and unresolved failures distinguished.

### H. Fault, restart and upgrade qualification

Test actual pod replacement with recorded old/new UIDs and retained PVCs. Inject lost responses at typed boundaries without replacing the real provider being tested. Include:

- Accepted storage record before response; enrollment before publication; Search publication before app visibility.
- Captured embedding/vector before Search; candidates before hydration; captured query before model input.
- Source/evidence acceptance before C2; C2 commit before C1 acknowledgment; priority commit before application result.
- Model reservation before recorded response, provider capture before caller capture, and application capture before command admission.
- Bridge capture before mailbox acceptance, application input acceptance before acknowledgment, and socket reservation before observed outcome.
- Chain signed-intent commit before send, lost submission response, effect observation before caller progress, and node restart on its original data.

Committed results must recover without repeating their logical contribution. Uncertain physical computation may repeat only under the selected policy and remaining bounds. Recorded/live model reservations are never automatically refunded; ambiguous sends are not automatically repeated. A failed observation is not proof of absence.

Test compatible ConfigMap/Secret rollout and exact principal binding. Preserve original occurrence profiles/time/deadline/budget. A mismatched journal/image/profile must refuse startup or operation, not reinitialize. Demonstrate safe compatible upgrade and rollback only for validated state versions; reject incompatible rollback. Do not claim general schema migration.

Sequence expensive tests to avoid artificial contention. Keep cold-readiness time, observer timeout and accepted business deadline separate. An isolated recheck does not erase an earlier failure.

**Exit:** required new and affected recovery paths have evidence; safety passes are not mislabelled completed user tasks.

### I. Backup/restore with effect replay prevention

Provide executable backup and restore for **new synthetic demonstration state**, not user's existing data. Prefer an explicitly quiesced snapshot procedure for the first implementation: stop new admission, let bounded work settle or report it unresolved, record each owner's checkpoint, flush using supported owner/database facilities, then copy consistent state. Do not copy an active SQLite database while ignoring its WAL or claim a globally atomic snapshot across owners.

Manifest every owner's store/seal, retained reference dependencies, source head, relevant Search generations, application views, image/profile identity and the named consistency cut. Search is disposable; prove rebuilding from authoritative records after restore. A missing retained view must fail rather than silently follow latest state.

**Restoring a journal must not restore authority to repeat effects.** Test these rules explicitly:

1. Restore by default into a fresh fenced namespace in read-only/reconciliation mode. No channel egress, chain submission, live model launch or mutating calls until safe identity/accounting checks complete.
2. Never let both original and restored owners act as the same logical writer/actor. Verify fencing or keep the clone observation-only.
3. Exclude active live approvals, funding/signing authority, mutable campaign capabilities and TLS private material from a normally shareable backup. Retain exact spent/unknown accounting evidence; never initialize a new full allowance from chart values.
4. Old approval is invalid for restored namespace/session/manifest bindings. Future mutating execution requires an explicitly safe deployment identity and applicable new authorization, not renaming files to evade spent state.
5. External IRC messages or chain effects already sent cannot be rolled back by restoring local state. Uncertain operations remain uncertain; receipts/read-only chain observations can reconcile them without resend.
6. Credentials and current revocation are managed independently from historical data. Restoring old policy must not grant revoked authority.
7. Protect backup bytes with existing approved storage/encryption controls where available; never archive another project's secrets or upload externally by default.

Exercise backup -> isolated restore -> query/readback -> projection rebuild -> refusal of duplicate send/generation/commit. A safe restore which refuses writes can be an honest bounded result; it is not full automatic disaster recovery.

**Exit:** usable scoped procedure and an executed drill, with observed recovery time/loss window and limits. Node-loss HA, distributed replication and populated-state migration remain unproven.

### J. Observability and diagnostics that do not become another control plane

Expose/reuse bounded read-only status, structured logs and metrics. No new telemetry stack is mandatory. Optional dashboard/scrape configuration may be included but disabled by default unless existing tooling is available.

At minimum distinguish: service readiness; accepted and pending work; reservations spent; captures; publication head/lag; queue occupancy/backpressure; acknowledgment state; typed error counts; sampled operation latency; recovery/replay counts; chain inclusion/effect/finality; generation approval/allowance state. Unknown backend-call or usage data remains unknown.

Propagate existing correlation/occurrence IDs through permitted traces. Do not use per-prompt, memory-content or unbounded occurrence strings as metric labels. Keep private hashes, raw prompts, bodies, provenance, credentials and model keys out of standard logs. Debug exports require their exact synthetic-data policy and size bound.

Provide an operator symptom guide: pending versus unknown, stored versus ready, model disabled versus unhealthy, Search rebuilding versus empty, chain unavailable versus rejected. Health checks and observers must not submit work or mutate budgets.

**Exit:** an operator can locate the blocked owner from sanitized evidence without opening foreign SQL or restarting everything blindly.

### K. Resource and performance characterization on one node

Measure the final selected profiles on the actual host; invent no SLA or target improvement. Record cold startup/asset readiness separately from accepted command time; per-role RSS/CPU/storage; service RTT/bytes; embedding/evaluation time; storage/read/index-publication time; whole-workflow latency; recovery duration and queue behavior.

Use a small predeclared load plan with exact bounds in the progress ledger before execution. Start sequentially and use only modest concurrency supported by the current single-writer contracts. Do not enlarge protocol caps or renew deadlines to make a load run succeed. All model responses remain recorded; no live model throughput test is authorized.

Record environment, image identity, cache state, corpus size, sample count, errors/timeouts and actual percentiles only when sample count supports them. One run is one observation, not a reliability estimate. Overload must cause explicit refusal/backpressure or truthful pending state, not loss of acknowledged work.

Use measurements to set reasonable example resource requests/limits and installation preflight checks without modifying mathematical behavior. Retain a low-resource sequential demonstration profile where feasible. Leave data-heavy optional lanes disabled when they cannot coexist within node capacity; serialize them rather than claim simultaneous operation.

**Exit:** documented capacity envelope and reproducible measurement command, not a production performance guarantee.

### L. CI, reproducible distribution and supply-chain checks

Add/reuse these executable lanes:

- Fast contracts/static/schema/chart validation and generation-denial tests.
- Native numerical and recorded-model tests using declared dependency assets.
- Opt-in single-node cluster installation/workflow/recovery qualification on an explicitly trusted runner.
- Optional isolated-chain lane using generated keys and no public network.
- Offline runtime artifact verification, archive integrity and source-to-image-to-scenario checks.

No CI event automatically runs a real generative backend, consumes a campaign, publishes images/releases, or contacts public IRC/chain. Never expose a privileged kubeconfig, signing keys or retained volumes to untrusted pull-request code. Do not solve this by making an untrusted self-hosted job privileged.

Define required environment/capacity and fail/blocked/skipped semantics. Secrets/caches/artifact retention must be explicit; logs and archives are sanitized. A missing real dependency is not silently replaced with a fixture of the same gate name. Repeated methods/scenarios are not additional unique coverage.

Provide distribution manifest, chart archive, image/asset archive references and integrity checks. Reproduce one installation from those declared artifacts in a fresh namespace on the same node without copying unlisted working-tree files. Record warm-cache assumptions and any restricted assets the recipient must obtain separately.

**Exit:** checks are runnable from clean declared inputs and CI has a safe trust/permission boundary; no automatic deployment claim for untested environments.

### M. Operator tooling, compatibility and documentation

Extend existing scripts under one discoverable command surface rather than create a new framework. Required capabilities:

`preflight`, `build`, `verify-artifacts`, `import`, `install --profile`, `prepare-corpus`, `qualify`, `status`, `diagnose`, `observe`, `backup`, `restore --fenced`, `upgrade`, `freeze-campaign`, `run-live --approval`, `stop`, `cleanup --preview`.

Those names are illustrative; reuse current names and publish a mapping. Every mutating command requires explicit cluster/context, namespace/release, profile and owned-resource checks. Preparation is resumable without adding another corpus each retry. Cleanup never deletes campaign state or the protected demo implicitly.

Update the actual module/native-command/placement/evidence matrix. Show local library, pod HTTPS, pure fixture, recorded backend, real deterministic provider, chain and live-model status distinctly. A deployed Relations API is not native link/unlink adoption; a chain transaction is not on-chain reasoning; an offline model image is not live execution.

Provide a text/Mermaid architecture diagram from actual configured dependencies, marking module HTTPS, internal backend HTTP, native IRC TCP and chain-specific protocols. A diagram does not substitute for test evidence. Keep all owned-state and disclosure edges visible. Do not regenerate presentations unless needed for the final operator walkthrough.

Deliver one primary runbook, one concise programme report, and machine-readable supporting evidence. Include minimal install/demo/recovery commands, known limitations, exact sources and a review checklist for Kabir. Do not create another competing architecture hierarchy.

**Exit:** a developer can install and evaluate the supported reference without asking which of many historical scripts is current.

### N. Final freeze, approval-ready live plan and cleanup

After relevant code, images, chart and tests stabilize, freeze a new k3s campaign for one HTTPS query/reply session. Retain the proposed maximum of **two future text generations**. This is a ceiling in a disabled plan, not permission. Do not reuse the exhausted `retrieval-grounded-20261026-02` campaign or any historical slot.

Prepare fresh corpus/view state through native setup. Qualification fixture journals remain separate from future live journals. Freeze:

- Tested source and every participating image/chart/configuration identity.
- Full offline runtime/model asset verification and supported effective options.
- Actual retained namespace/PVC/service/TLS/caller/recipient/scope identities.
- Corpus/feed head, Search generation, embedding profile and complete selected metadata view.
- Session ID, two planned slot IDs, exact static questions/query/follow-up, prompt-construction/disclosure rules, equally eligible reply bodies and independent evaluator.
- Original deadline/budget rules, finite approval window requirements, stop conditions, diagnostics and cleanup.

Do not start absolute deadlines while waiting for approval. Bind actual clock samples once at future admission. The second prompt must include that session's actual captured query result; do not precompute it from the evaluator. Keep immutable manifest, external digest, future approval and mutable execution ledger distinct. Avoid circular hashes between an image and its own freeze.

A COMPLETE freeze has no placeholders, missing retained volumes or unverified required model blobs. If an input is missing, keep the plan INCOMPLETE and report the exact input; other finished packages remain valid. Do not use this to stop independent work early.

Review all post-test changes. A relevant runtime change requires affected final-image rechecks; evidence-only publication does not retroactively change test identity. Produce the source-to-image-to-scenario map.

Remove disposable resources after collection. Preserve `omega-demo` after verifying its before/after identities. Retain only the expressly named campaign data/assets with heavy runtimes scaled down or guarded. Future real-runtime availability remains NOT_CHECKED. Never stop unrelated services.

**Exit:** one coherent distribution and disabled executable live plan, with precise status for every work package and no new generative-model activity.

## 5. Cross-cutting invariants

These survive every package, refactor, restart, backup and rollout:

- Modules own their own mutable state; consumers use declared ports. Sharing a pod or database server does not authorize foreign table access.
- No hidden local/provider fallback or silent model/profile substitution.
- Identity is occurrence/context/source-bound as applicable, never merely text equality. Evidence contribution identity is not command identity.
- Accepted deadline and budget survive process/pod replacement. Stored captures are recoverable; uncertain spent attempts are not refunded.
- Same idempotency key with changed semantics conflicts. Successful replay still checks current authority.
- Storage acceptance, projection publication, application readiness, model capture, command admission, socket outcome and chain finality remain distinct observations.
- Derived indexes/presentations are rebuildable. Authoritative stores and journals cannot be replaced by generated answers or permissive caches.
- Prompt/result identity and disclosure permission are both checked. Hash equality alone grants neither authority nor truth.
- No automatic resend after uncertain external effects. A restored old journal cannot repeat an already spent capability.
- Native NAL, PLN, promotion and embedding behavior remain under their exact selected profiles. State separation is not mathematical equivalence between profiles.
- Model fixtures propose commands only; actual native computations, retrieval and context construction remain real where claimed.
- A wrong but permitted answer can be sent and score incorrect. A safety rejection can pass its negative assertion while failing the positive task.
- Historical evidence remains immutable. New code/fixtures do not repair a missing historical payload or make unknown usage zero.

## 6. Evidence and acceptance matrix

Use one machine-readable matrix with `PASS`, `FAIL`, `BLOCKED`, `NOT_RUN` and narrowly explained baseline exceptions. Record each gate's exact source/image, command, provider class, scenario, assertions and observed outcome.

| Gate | Required demonstration |
|---|---|
| BASELINE | Relevant source relationships and known defects addressed without erased checks |
| ARTIFACTS | Role images/assets verified; generative image status explicitly offline only |
| CHART | Supported one-node profiles, ConfigMaps, Secrets, PVCs, probes, locks and service DNS |
| AUTHORITY | Scoped identity/disclosure, credential/TLS rotation and actual allowed/denied flows |
| MEMORY | Real native write-to-read, remote E5/Search/storage and retained views |
| COGNITION | Native evidence/prior/revision/priority paths through separately selected synthetic service owners |
| RELATIONS | Real typed relation provider and traversal integration; no overclaim of native mutation adoption |
| MODEL_CHANNEL | Actual in-cluster recorded-response retrieval-to-reply with independent peer/evaluator |
| CHAIN | Actual isolated same-artifact commitment, effect/finality, restart and independent readback |
| RECOVERY_UPGRADE | Pod/response/configuration faults preserve captures, state and spent accounting |
| RESTORE | Fenced synthetic restore and projection rebuild without reissuing effects or authority |
| OBSERVABILITY | Bounded actionable diagnostics and honest stage/accounting metrics |
| RESOURCE_BASELINE | Measured bounded resource/load envelope with failures and sample counts |
| CI_DISTRIBUTION | Safe executable lanes and fresh-namespace artifact-based reproduction |
| ZERO_LIVE | Tested denial, no real generative startup/contact/load/reservation/call/capture |
| FREEZE | Concrete disabled campaign with actual retained inputs and external digest |
| HANDOFF | Operator walkthrough, coverage mapping, sanitized artifact/evidence list and protected cleanup |

The chain or cognitive service gate cannot pass on fixture-only evidence. Missing actual assets or API behavior results in a partial programme with useful delivered code, not an invented finality/private-placement claim. All feasible independent packages still proceed.

A repaired baseline regression should close with executed evidence. If a genuine exception remains, classify the overall result `READY_WITH_EXPLICIT_EXCEPTION` only when it does not invalidate a required new gate; otherwise `PARTIAL` or `FAILED_REQUIRED_GATE`. Never collapse mixed results into "all tests pass".

Count methods, scenario names, executions, rechecks, completed tasks, expected safety failures and model attempts separately. Evidence is not better because the number is larger.

## 7. Resumption and completion discipline

Keep a progress file in the existing deployment evidence structure, not a second project tracker. It should contain:

- Exact working HEAD/delta and currently tested image set.
- Package states and concrete remaining code/tests.
- Protected and task-owned cluster resources; retained volume identifiers.
- Commands already executed, distinct failures and rechecks.
- External blockers, with the minimal needed input and unaffected packages to continue.
- Live-runtime denial/authorization counters and campaign state.
- Next executable action if the session must end.

Do not end with "next, implement the chain adapter/restore/CI" if that is in this programme and feasible. Continue. Conversely, do not invent access, mutate protected state, spend generations or broaden deployment topology to avoid reporting an authentic blocker.

When all ready work finishes, deliver one integrated report plus evidence. Do not require another user message to authorize routine fixes, chart wiring, regression execution or source documentation already included here.

## 8. Final report and distribution contents

Deliver working implementation, not only this plan:

1. Exact tested source/delta; task-only commits where permitted; image/asset/chart artifacts and hashes.
2. Complete supported profile values and environment/Secret contracts.
3. Operator interface and primary runbook with actual runnable commands.
4. Repaired regression evidence and remaining explicit exceptions.
5. Final-image native recorded workflows, cognitive service tests, deterministic execution and isolated chain evidence.
6. Recovery, restore, security, upgrade and resource observations with actual limits.
7. CI lanes, artifact verification and fresh-install rehearsal.
8. Frozen campaign ID/hash and unissued approval request, or exact incomplete fields and blockers.
9. Current architecture/coverage map distinguishing logical modules, native adoption, deployment and live outcomes.
10. Before/after protected-resource inventory, deleted qualification resources and intentionally retained campaign assets.

Use a status block such as:

```text
PROGRAMME_STATUS=<READY_FOR_REVIEW | READY_WITH_EXPLICIT_EXCEPTION | PARTIAL | FAILED_REQUIRED_GATE>
COMPLETED_PACKAGES=<A..N actual>
BLOCKED_PACKAGES=<actual IDs and precise prerequisites>
TESTED_SOURCE=<actual commit/content manifest>
FINAL_ARTIFACT_MANIFEST=<actual path/digest>
BASELINE_REGRESSION=<PASS | OPEN_EXCEPTION | FAIL>
SINGLE_NODE_REFERENCE_DISTRIBUTION=<PASS | PARTIAL | FAIL>
RECORDED_RETRIEVAL_WORKFLOW_IN_K3S=<PASS | FAIL | NOT_RUN>
SYNTHETIC_COGNITIVE_SERVICES_IN_K3S=<PASS | BLOCKED | FAIL | NOT_RUN>
RELATIONS_SERVICE_IN_K3S=<PASS | BLOCKED | FAIL | NOT_RUN>
ISOLATED_CHAIN_COMMITMENT_IN_K3S=<PASS | BLOCKED | FAIL | NOT_RUN>
BACKUP_RESTORE_DRILL=<PASS_BOUNDED_FENCED | PARTIAL | FAIL | NOT_RUN>
CI_AND_ARTIFACT_REPRODUCTION=<actual result>
GENERATIVE_RUNTIME_IMAGE=<OFFLINE_VERIFIED | BLOCKED | NOT_VERIFIED>
GENERATIVE_RUNTIME_AVAILABILITY=NOT_CHECKED
K3S_LIVE_CAMPAIGN_FREEZE=<COMPLETE | INCOMPLETE>
CAMPAIGN_ID=<actual>
CAMPAIGN_MANIFEST_SHA256=<actual, only when complete>
CAMPAIGN_STATE=AWAITING_LIVE_AUTHORIZATION
AUTHORIZED_LIVE_GENERATIONS=0
RESERVED_LIVE_GENERATIONS=0
OBSERVED_GENERATIVE_BACKEND_CALLS=0
CAPTURED_LIVE_RESPONSES=0
ADDITIONAL_LIVE_GENERATIONS=0
LIVE_MEMORY_MODEL_WORKFLOW_IN_K3S=NOT_RUN
MULTI_NODE=NOT_RUN
PRODUCTION_READINESS=NOT_ESTABLISHED
```

If isolated chain testing is blocked, do not print `CHAIN_IN_K3S=PASS` from M4's historical host run. If real-model packaging is complete, do not print live runtime readiness. This programme is a bounded reference distribution, not a production certification.

## 9. Conditional live evaluation — procedure included, authorization not included

No further design task is required when the user later approves the completed campaign. Separate approval must identify the final ID/hash, exact finite slots, allowed runtime activity, time window and recipient/data policy.

Before such approval, this section is inert. Continue all engineering work; never start the real model merely because approval is the last remaining live prerequisite.

After valid approval:

1. Revalidate frozen source/images/assets, retained state, TLS/recipient and current approval before real runtime exec.
2. Start only the approved task-owned model/runtime. Readiness cannot consume unaccounted generations.
3. Execute only the declared query and reply slots with the existing owner/campaign accounting. Do not borrow slots from another session or historical campaign.
4. Stop on the frozen rejection/error/timeout/uncertain-effect rule. No response repair, prompt tuning, substitute model, replacement session, hidden retry or restored-budget trick.
5. Recover captured responses without regeneration. Unknown reservations remain spent; billing/usage remains unknown when not observed.
6. Verify actual retrieval, next-prompt binding, command admission, factual correctness and peer observation separately.
7. Stop task-owned temporary runtimes, preserve state/evidence, record actual counts and limitations.

Completing a campaign does not require a correct answer. Do not alter the final frozen implementation mid-campaign to obtain one. A changed implementation requires a distinct qualification and, when bindings change, new approval.

The earlier deterministic chain lane does not authorize automatic commitment of a live prompt, retrieved private content or generated reply. Any future combined live-result-to-chain demonstration needs an explicitly approved artifact/disclosure policy; it cannot be inferred from two independent passes.

## 10. Scope rationale and source basis

The previous seven-package batch already included baseline repair, offline runtime packaging, guarded activation, operator commands, integrated recorded qualification, campaign freeze and handoff. This programme incorporates those requirements and adds cognitive-service placement, Relations deployment, actual isolated chain integration, restore safety, observability, load characterization, CI and reference distribution.

The initial Kevin/Kabir discussion called for function-based version-independent contracts, practical local-to-remote handoff, reuse of working implementations and a concrete chain prototype. The benchmarks discussion separated state owners and emphasized integrated acceptance tests. Those sources motivate the outcome, but do not specify this particular Kubernetes topology, policy or future generation allowance.

Source inputs for this brief:

- `codex_omega_single_node_completion_batch.md` (the previous primary assignment; now superseded as the task backlog).
- `codex_k3s_generative_runtime_packaging_and_campaign_freeze.md` and relevant prior S04/S05/M5/M4 contracts as supporting specifications.
- User-reported publication `fd54e61289ecf8e729f28d501d974aa662517f90` and the later actual checkout to be verified by Codex.
- Kevin / Kabir, 15 October 2026: 00:13:36–00:18:47, 00:57:38, 01:04:49–01:07:39.
- AGI Benchmarks, 15 October 2026: 00:02:28, 00:11:14–00:12:40, 00:17:02.

This document was drafted from supplied specifications and conversation evidence; it is not a fresh repository, cluster or runtime audit. Codex must verify current files and actual capabilities before making implementation claims.

**Deliver the end-to-end single-node reference distribution and complete every authorized feasible package. Routine technical checkpoints stay inside this assignment. Live-generation authority, protected data and actual external prerequisites remain the only reasons for an external decision.**
