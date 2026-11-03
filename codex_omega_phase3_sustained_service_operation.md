# Codex implementation programme — Phase 3: sustained single-node Omega service operation

**Repository:** `machieke/fusion-module-interfaces`  
**Starting publication:** `660803cb955802175765ad16391b7453926b5f47`, or its verified descendant  
**Delivery:** one twelve-package implementation programme; one integrated release candidate  
**Topology:** existing explicitly selected single-node k3s cluster, Helm-managed services  
**Data:** fresh synthetic scopes; no import of user histories or existing private data  
**Additional live text-generation authority:** **ZERO**  
**Status:** proposed next assignment. It becomes implementation scope when assigned; the preceding completion report does not itself authorize execution.

## 0. Outcome and working agreement

Phase 2 delivered the native developer preview. Reuse it rather than reimplement its twenty tools, SDK, two-agent composition, owners, chain adapter, workbench or distribution.

This programme addresses the next usability boundary: the preview must support repeated operation without exhausting a tiny demonstration pool, leaving an expired input permanently at the head of a queue, depending on session-specific chart edits, or presenting fixture-only model selection as a general model interface.

**Outcome:** a bounded but sustained service deployment in which operators can create policy-constrained sessions, handle expired or partially completed work, run consecutive native tasks with visible resource headroom, maintain agent-private synthetic histories, and inspect current owner state. Model backend selection must be structurally independent of recorded-response fixtures, with the real-backend execution path qualified offline and still disabled without separate authority.

This is not another feature-catalogue expansion. No new reasoning mathematics, general scheduler, public marketplace, extra channel, multi-node cluster or new chain operation is requested. Add only the capabilities and contract extensions needed below.

Execute R01–R12 as one backlog. Internal checkpoints do not require another user brief. Make ordinary reversible implementation decisions. Correct in-scope defects, preserve the protected invariant, and continue independent packages when a genuine dependency is missing. Missing live approval never blocks engineering or recorded-response qualification.

Keep one progress ledger with exact sources/images, package state, test evidence, protected/task-owned resources, blockers and the next executable action. If a session ends, leave a precise continuation checkpoint for this same programme. Do not call unfinished included work a future recommendation. Do not imply asynchronous work will continue after stopping.

Deliver one primary report and one operator entry point; retain detailed evidence in machine-readable records. Do not re-run an unrelated historical hash audit or regenerate every presentation merely to produce activity.

## 1. Review basis: distinguish observations from the new design

The author inspected selected public source and reports at the starting publication. No cluster execution, independent image rebuild, complete 357-file audit or native test rerun was performed in preparing this document. Codex must verify the actual checkout and reproduce relevant boundary observations before changing them.

The published Phase 2 evidence is a baseline, not a new test run. Its current capability matrix records a union of twenty exercised descriptor names; the combined session itself covers sixteen. Recorded model proposals select commands, while native execution and service effects are real where identified. Do not inflate native-input, scenario, method, SDK or workflow counts.

### Concrete boundaries to inspect

| Reference | Source-derived boundary; verify before editing |
|---|---|
| R-A: `fusion/preview_session_service.py` | Session IDs must occur in `session_templates`; session selection is explicitly `RECORDED_FIXTURE`. |
| R-B: `fusion/preview_sessions.py` | The oldest non-complete input is selected, then its deadline is checked. There is no general expired-input terminalization path in that selection. |
| R-C: `docs/phase2/programme-report.md` | The installed preview has finite templates and an aggregate 512-record feed/storage bound, including administrative and vector records. |
| R-D: `fusion/preview_model.py` and `preview_recorded_model.py` | The application imports the recorded client/configuration directly. Existing live machinery elsewhere is not automatically a selectable Phase 2 backend. |
| R-E: `docs/phase2/private-scopes.md` | Private AtomStorage denial is tested, but native history/cognition is shared synthetic data; semantic episode ownership does not hide shared underlying bytes. |
| R-F: `docs/phase2/latency-diagnosis.md` | Earlier source inspection identifies repeated validation and hydration candidates; it does not establish the final dominant cost. |
| R-G: `docs/phase2/programme-report.md` | Final native per-method timing is unobserved; retained workbench results are not current owner heads. |
| R-H: repository root `README.md` | Its current overview still foregrounds historical M5/deployment status. Preserve old evidence, but provide an accurate current starting point. |

These observations motivate proposed changes below. They do not retrospectively turn the scoped Phase 2 qualification into a failed run or imply that earlier meetings selected this particular lifecycle design.

### Preserve baseline identities

Read `AGENTS.md`, `docs/phase2/{programme-report,runbook,native-capability-matrix,storage-layout,private-scopes,sdk-compatibility}.md`, `evidence/phase2/final/`, current source locks, role-image builders and the current SDK/operator entrypoints.

Record actual HEAD/worktree, relevant image/source relationships, cluster context, host capacity and installed profiles. The reported dev19 runtime map is `369daf1ab470fb8fe8265fe16a3a5765670c643e7011e3d5369636a803e7e49d`; verify it where needed, not by assuming every later file belongs to that image map.

Keep original numerical/native/runtime dependencies unless an actual packaging incompatibility is demonstrated. No model, E5 preprocessing, distance metric, NAL/PLN policy or wall-clock Attention change is justified merely by this operational work.

## 2. Authority, protected resources and failure model

When assigned, this programme permits repository implementation, task-only images, fresh task-owned namespaces/PVCs, actual native tools, pinned E5/Chroma/DeTTa, recorded-model services, isolated IRC, bounded filesystem tools and the existing isolated-chain test with generated unfunded keys.

It does **not** authorize:

- Starting, loading or contacting a real generative runtime, generation-bearing readiness/warm-up, live reservations or new text generation.
- Using or altering the old frozen campaign, its images, credentials, PVCs, allowance or approval files.
- Existing private user data, public endpoints/channels, paid provider activity, public/funded chain transactions or publishing restricted artifacts.
- Multi-node/HA, host-wide cgroup/firewall modification, automatic user-data migration, physical erasure claims or arbitrary shell/MeTTa execution.
- Removing authorization, validation, provenance or journal guards to make performance or capacity tests pass.

Protect `omega-demo`, the actual retained original campaign namespace, and campaign `omega-reference-k3s-20261030-03` with manifest hash `669dc641863968947fdea63b504f0902a1f93425032177d42294bd2312c51f47`. Discover actual resource identities from retained manifests. Compare before/after; do not assume historical health or current presence.

Real E5 encoding and deterministic native mathematics remain permitted and distinct from generative-model calls. The CPU-quota exception remains until separately established; application limits are not kernel enforcement. Do not repair host infrastructure under this assignment.

Use a trusted single host with intact files and one authoritative writer per store. New tests may expose gaps in that model; they do not establish protection from a malicious host, multi-tenant production isolation or disk/node-loss failover.

Use existing user/workspace Git authority for task-only commits and publication. No force-push, automatic public release or blind staging of unrelated files.

## 3. Programme graph

| ID | Package | Main result |
|---|---|---|
| R01 | Bounded dynamic sessions | New sessions from approved policy templates without editing per-session Helm values |
| R02 | Expiry, terminalization and reconciliation | No permanent queue obstruction from safely expired work; uncertain effects remain fenced and observable |
| R03 | Sustained capacity and accounting | A measured fresh-state capacity profile beyond the old aggregate demonstration limit |
| R04 | Native telemetry and measured optimization | Actual per-stage timing/call evidence, followed by invariant-preserving improvements |
| R05 | Concurrent native agents and task progress | Two real native callers exercising shared writes and deadline-aware handoffs |
| R06 | End-to-end synthetic private history/cognition | Private native source/history paths do not leak through raw storage/feed or context |
| R07 | Model backend independence | Explicit recorded versus existing real-backend bindings; live path cannot execute without authority |
| R08 | Evaluation-ready workflows | Independent task oracles, counterfactual corpora and non-answer-bearing proposals |
| R09 | Current-state operator workbench | Current owner observations distinguished from historical captures and pending effects |
| R10 | Recovery, compatibility and fenced restore | New lifecycle/capacity/privacy state survives supported restart and restore without reissuing effects |
| R11 | Developer distribution and independent setup | Artifact-driven operator workflow, precise environment support and safe CI lanes |
| R12 | Sustained integrated qualification | One coherent final-image release candidate with explicit remaining limits |

R01/R02/R03/R04 are the primary operational path. R06 and R07 can proceed independently after the existing responsibility map is verified. R08/R09/R11 should reuse outputs as they become available. R10/R12 qualify the resulting combined system.

No package needs live text generation. Do not make a new frozen campaign the principal deliverable.

## 4. R01 — policy-constrained dynamic sessions

Retain the existing native session service, inbox, supervisor and one-child-per-agent discipline. Do not introduce a cluster scheduler or a replacement native loop.

Replace the need to predeclare every exact future session ID with a new explicit **session-allocation profile**. Operators choose from bounded approved templates; the service creates the session identity and immutable binding under current authority.

A template specifies agent principal, allowed scopes, selected catalogue/providers, model-boundary class, resource/call limits, concurrency, disclosure policy and lifetime rules. It cannot contain model-supplied endpoints, filesystem roots, arbitrary executable text or credentials. Capability intersection remains mandatory: installed, selected, available and authorized.

Session allocation must:

1. Have a stable allocation request identity. A lost reply returns the same allocated session.
2. Freeze actual accepted configuration before work is admitted.
3. Check active-session, retained-session, pending-input and storage quotas before promising capacity.
4. Separate per-session application data and native worker configuration without shared foreign-owner mounts.
5. Return a usable handle through the API/CLI/workbench, not require manual editing of internal files.
6. Recheck current authority for subsequent input, results, pause, close and administrative observations.

Closing a session does not erase its accepted records, revoke another principal, refund work, reclaim all bytes or remove effect uncertainty. A session may become eligible for a bounded archived state; retained-session capacity remains explicitly finite. Do not implement hidden garbage collection.

A new session may deliberately select another compatible provider. An accepted occurrence may not be rebound to the provider's current defaults or a fresh empty journal after a rollout.

**Acceptance:** create at least three sequential fresh sessions per agent in one installed deployment, without chart/source/configuration edits per session. Test allocation replay, wrong principal/template, exhausted active and retained quotas, concurrent allocation, supervisor restart and old template compatibility. Do not describe the resulting bounded allocator as unlimited sessions.

## 5. R02 — expiry and cancellation without lost or repeated effects

Resolve the current head-of-line behavior through explicit states and owner observations, not by deleting an expired row, renewing its deadline or blindly skipping it.

Design and version a minimal input state machine. Illustrative states are accepted, assigned, running, completed, expired-before-start, rejected, cancel-requested and needs-reconciliation. Exact names may reuse existing ones. Every terminal result records what is known about effects; `failed` is not proof that nothing committed.

Separate three decisions:

- Is execution still permitted under the original deadline and budget?
- Did an owner already accept or commit any part of the operation?
- May dependent or independent later work proceed safely?

Required behavior:

- A provably undispatched input that expires can be durably terminalized without running its command; subsequent independent work can advance.
- A command already completed can be reconciled into the original input after expiry by observing its saved receipt. Do not execute missing effects to fabricate completion.
- An uncertain started mutation remains pending/unknown or fenced. Preserve its task/result and external-effect identities. Explicit independent work may proceed only where the declared ordering policy permits; dependent mutations stay blocked.
- Cancellation prevents unstarted work or further permitted stages when enforceable. It cannot retract an IRC message, erase a committed atom or undo a chain deployment.
- Cancelling one queued input must not cancel another agent's task or weaken authority checks.
- Recorded/live model reservations, socket attempts and chain signed intents retain their exact spent/unknown semantics. The latter live fields remain unused in this assignment.

Reconciliation is bounded, call-driven and read-only unless a narrowly defined terminal-status commit is required in the relevant owner. It must not perform a native tool simply because reading its outcome is inconvenient. Do not use foreign SQL to discover effects.

The ordering profile must state how a later input depends on an earlier one. Default to refusing dependent mutation when causality is unresolved. Never create an implicit “continue anyway” policy for context-dependent commands. Expose the blocked reason and a safe observation path in the UI.

**Acceptance:** an expired undispatched head no longer permanently stops its session; a completed-before-crash operation reconciles once; an ambiguous external send stays spent with no resend; dependent work stays fenced while unrelated read-only observation works. Test concurrent expiry/completion, cancel-versus-dispatch, revocation, duplicate cancellation, application replacement and deadline equality/clock boundaries. No deadline renewal or identity replacement is allowed.

## 6. R03 — sustained capacity with truthful admission

The old 512-record bound is an aggregate backend/owner limit, not a count of user memories. Native history, wrappers, vectors, task reports and captures all consume space. Preserve the historical profile; do not globally raise a constant and declare scalability.

Before changing capacity, measure actual record and byte amplification for the supported commands, including source history and chunking. Produce a bounded capacity model for:

- active and retained sessions;
- user memories, revisions and withdrawals;
- administrative C1 history and evidence;
- model/command captures and task exchanges;
- retained Search/presentation generations;
- workspace and effect-replay journals.

Implement a new explicitly selected **fresh-state sustained profile** with finite record, byte, revision and work limits. Reuse the existing storage owner and application-neutral DeTTa interfaces. A bounded per-scope quota or owner-internal segment layout is acceptable when justified by measurements; neither may change opaque reference identity, source sequence or replay semantics silently.

If owner-internal segments are needed, their registry, epoch and continuation are owner-controlled. Consumers read declared feed/head operations, not directory names. One logical owner remains the writer. Missing historical segments are errors, not empty history. Old references and retained reads must continue to resolve under their declared retention policy.

Capacity admission must be honest. Estimate required resources before accepting a native operation where feasible; use a narrowly scoped reservation mechanism if a guarantee needs it. Do not claim a cross-owner capacity transaction. If another owner later refuses, retain the partial outcome and original work identity. No compensating deletion of evidence or resetting a receipt to retry as new work.

Do not silently prune history, evict a captured answer, forget spent reservations, increase every protocol cap, widen per-request byte bounds or suppress source events. If optional context is omitted under a declared budget, authoritative history remains available through bounded reads.

**Required sustained evidence:** on one retained fresh deployment and logical corpus, exceed the old 512 accepted-record threshold through legitimate native workflows, with early references/views and spent accounting still readable. Include the dynamically allocated sessions from R01. Run enough additional operations after the crossing to demonstrate continued function, not just the 513th acceptance followed by failure. Freeze the finite workload and expected resource ceiling before running it. Separately prove explicit refusal at the new configured limit with no loss of acknowledged data.

If the actual host cannot support this profile, report the measured boundary and incomplete sustained-capacity gate. Do not fabricate success using multiple reset namespaces or a direct synthetic feed generator instead of native work. Independent packages continue.

## 7. R04 — actual timing and measured, safe optimization

First make the existing opt-in native instrumentation observable in the final workload. A missing timing file must fail the timing-observation gate; do not infer per-method latency from end-to-end totals or reconstruct old measurements.

Collect bounded monotonic durations, nested-call relationships, counts and bytes for:

- native launch/bootstrap and first bridge contact;
- input preparation and previous-result restoration;
- history/context/promotion preparation;
- C1/C2 snapshot/provenance validation and hydration;
- Embedding, Search readiness/query and AtomStorage batch reads;
- append/publication/read-view selection;
- recorded model acceptance/reservation/capture;
- command execution and next-context handoff.

Do not log private text, credentials, raw model prompts or unbounded per-occurrence metric labels. Authorized synthetic traces may use existing correlation identities. Check observer overhead and bound both trace size and sampling. Missing spans remain missing; nested durations are not additive totals.

Reproduce the final baseline on declared small and growing workloads before selecting optimizations. Treat the historical latency diagnosis as hypotheses, not proof of the current bottleneck.

Permitted corrections include indexed owner-local lookups, genuine batch reads, avoiding duplicate hydration within a single already validated immutable snapshot, narrowing materialization to the requested window, or amortizing source-checked process readiness. Choose only changes supported by measured data.

Any validation reuse must distinguish immutable content integrity from current authorization. A stored hash does not permit bypassing revocation or current lifecycle withdrawal. Define cache keys, invalidation, scope/principal/recipient binding and recovery. Missing/corrupt retained payloads must not become cached successful answers outside a profile that explicitly permits captured-result use. No new global cache owner is required.

**Acceptance:** provide observed per-stage coverage and before/after comparisons on equal inputs, retained state, images and resource settings. Report regressions and cold/warm differences. Preserve numerical output, ranking, provenance, current authority, deadline and budget behavior. No arbitrary percentage speedup is a required result; a measured diagnosis with safe implemented corrections is preferable to unsupported optimization claims.

## 8. R05 — native concurrency and task lifecycle

The previous two-client opaque storage test is not proof of concurrent native remember/query. Add actual overlapping requests from two native agent workloads to the existing shared owners. Keep one writer per provider; two clients do not create distributed multiwriter consensus.

Test distinct and conflicting native memory operations, actual source coverage, out-of-order publication completions, shared query freshness, lifecycle update/withdraw races and per-agent response routing. Both clients must use their own application journals, credentials and captured contexts. Do not provide answer references through the test controller.

Extend the existing task/result exchange only as needed for R02: acceptance, start, terminal result, explicit refusal, safe expiry, cancellation request and retained observation. Preserve original task and command identity across duplicate delivery. A result received after a task deadline is recorded as a late observation, not automatically executed or treated as newly authorized work.

A task result is another agent's report with inherited provenance. It cannot create independent corroboration solely by crossing a mailbox. Forwarded refs require recipient access. Wrong-agent results, replay under another task and modified view bindings must fail before context release.

Use bounded fairness between the two configured agent sessions if one accepted stream starves another. This can be a small local scheduling policy for their existing inboxes; do not implement bidding, recursive delegation, work stealing or a general distributed scheduler.

**Acceptance:** both delegation directions, two genuinely overlapping native callers, expiry while queued, worker/caller replacement, late captured result and current shared-membership revocation are exercised. Independent tasks can progress where safe; ambiguous dependent work remains fenced rather than silently skipped.

## 9. R06 — end-to-end synthetic private history and cognition

This is an explicitly new **synthetic test composition**, not permission to use real private data or a production confidentiality claim.

Phase 2's private AtomStorage ports do not make its shared native history private. Implement a supported fresh session in which A's native memory, source/history events, evidence, belief state, notes, priority, indexes and derived presentation use A's selected synthetic private scopes throughout. B receives separate selections.

Use existing owner ports, typed scopes and trusted service delegation. Do not rely solely on C1 refusing another principal while storing the same event bytes in an enumerably shared AtomStorage scope. Audit the whole path: direct get/getMany, feed/head, Search/ranking, Relations, lifecycle, workbench, context, task attachments, logs and backups.

Private indexes must not reveal counts, ranks, candidate IDs or source watermarks to an unauthorized principal. A shared structural link must not become a capability to its private endpoint. Mixed-scope requests need explicit allowed semantics; otherwise fail closed before effects.

To share a useful result, provide one narrow operator-authorized projection of a generated private source into a distinct shared artifact. Keep raw source, private hashes/IDs and full provenance private. The shared artifact has its own deliberately disclosed identity; it is not another statistically independent observation. A model command cannot grant declassification. Reuse existing disclosure/approval machinery; no universal redaction engine or new cryptographic proof system.

The same deployment may support separate shared and private synthetic sessions. A single session that mixes both automatically is not required. Existing shared Phase 2 profiles remain unchanged.

**Acceptance:** real native remember/source/support/query/promotion/history in the new private synthetic session; B's attempted semantic, raw-storage/feed and index access denied; private canaries absent from B's context, shared feed, chain payload, ordinary diagnostics and unauthorized workbench views. An explicitly approved shared projection is accessible while its private source remains inaccessible. Test revocation and captured-context release as well as direct reads.

## 10. R07 — model backend independence without live execution

The current PreviewModel is explicitly recorded-provider based. Do not describe an endpoint change as enabling real generation. Separate backend selection, effective model identity, prompt conversion, disclosure and provider execution behind the existing ModelInference contract.

Implement a new opt-in application/session model binding with two explicit choices:

1. Recorded-response provider for engineering, labelled in all status/evidence.
2. Existing pinned real-backend adapter with the current approval/reservation/capture controls, inactive unless a separately authorized session/campaign satisfies them.

Reuse ModelAdoption, the native parser, typed tool catalogue, whole-batch admission, owner accounting and historical runtime validation. Do not fork another model service or maintain two incompatible application loops. Keep old recorded-only profiles unchanged and reject unsupported selection combinations explicitly.

Dynamic sessions must not automatically inherit model authority. Each real model-call occurrence would bind the complete selected prompt, policy, caller, recipient, state view, effective options, deadline and finite allowance before dispatch. Reconnection cannot regenerate a captured result or renew a reserved unknown call.

Test the actual real-adapter request/response translation with synthetic recorded SDK responses and a launch/contact-denying boundary. A sentinel can verify that the live path refuses missing/wrong/expired approval before any real process or network call. That is offline qualification, not native model execution. The selected fixture must never activate as fallback when the live adapter is unavailable.

Keep raw generated text, native transformation, parsed proposal, admission, tool execution and reply publication distinct. The model cannot pick credentials, restore budgets, alter allowlists, override R06 disclosure or approve chain publication.

**Acceptance:** the same native consumer can be constructed against either selected binding; recorded end-to-end tests pass; real execution is blocked by existing controls and its offline adapter/disclosure checks pass. Report `REAL_PREVIEW_MODEL_EXECUTION=NOT_RUN`. No model runtime startup, inference, hidden warm-up or historical campaign consumption is allowed.

## 11. R08 — evaluation readiness, not a fixture success score

Implement reusable workload definitions for the already existing tools. The evaluator and its expected state must be outside the agent/model-provider authority. Recorded proposals choose commands but cannot supply query payloads, mutate scores, read the evaluator or stand in for native effects.

Include a compact suite covering:

- retrieval of a new fact, plus a changed-fact and absent-fact variant;
- two-agent query/result handoff with wrong-agent and stale-view variants;
- contradiction from the same source versus explicitly assumed independent evidence;
- priority changes without belief changes, and belief changes without priority rewards;
- superseded/withdrawn memory with current versus historical authorization;
- safe expiry, capacity refusal and recovery of captured results;
- a synthetic source that invalidates a task premise, requiring an explicit stop/reassessment observation rather than silently continuing dependent work.

The last workload may use recorded commands to test the application's condition-handling. It does not prove that a real model autonomously notices changed premises. Label plan selection and command proposals separately from deterministic contract results.

Separate output permission from factual correctness. Incorrect but harmless permitted replies must score incorrect after observation; unauthorized outputs must be rejected without being counted as successful tasks. Query/result binding, truth, actual peer receipt and chain finality are separate evaluation dimensions.

Freeze datasets, initial states, workload budgets and scoring rules before a measurement. For future real testing, keep a held-out synthetic variant inaccessible to prompt construction and the model provider; an operator may approve disclosure of data classes without supplying the answer. Do not execute a real campaign here.

**Acceptance:** the suite runs through real native tools and deployed owners with recorded proposals, tests actual alternate dataflow and negative cases, and exports a later live-evaluation definition with all allowances zero. Do not issue an aggregate cognitive-accuracy or reliability percentage from fixture choices.

## 12. R09 — current-state workbench and operational observations

Keep the existing workbench and CLI; do not add another frontend/control database. Expose current owner observations alongside retained task results with clear labels, revision/view identities and observation times.

Required distinctions include:

- accepted input versus active dispatch, expired-before-start and effects-needing-reconciliation;
- current memory head/withdrawal versus an old captured query;
- current episode/assessment/priority observations versus an input's historical view;
- remaining active/retained session capacity, record/byte capacity and pending-work headroom;
- recorded model mode, disabled live mode, approval expiry and unknown generation state;
- peer-observed send versus socket completion or ambiguous spent send;
- isolated-chain inclusion/effect/finality versus a local commitment request.

Owner reads are authenticated and bounded. The UI must not inspect provider files or grant authority by displaying a button. Detailed private synthetic views require their scope and disclosure permission. Escape content, preserve existing CSRF/origin controls, avoid unrestricted exports and never expose Secrets or raw workspace paths.

Add safe operator actions only through existing/new declared contracts: allocate session, pause, request cancellation, reconcile, inspect capacity and close/archive a session. Every action has a CLI equivalent and stable request identity. No clear-budget, force-success or unbounded retry button.

**Acceptance:** an operator can identify and resolve the safe expired-input case without SQL edits or namespace recreation, see an unresolved ambiguous effect accurately, allocate another permitted session, and inspect fresh versus retained views. Automated browser/CLI checks must use the actual installed package and service endpoints.

## 13. R10 — compatibility, restart and fenced restore

Introduce explicit profiles for new session/lifecycle/capacity semantics. Preserve the previous distribution and frozen campaign; no in-place migration of their populated journals is included. Fresh Phase 3 stores are appropriate.

Test actual client/server selection across supported old and new contracts. New optional fields are not an excuse to accept unknown required semantics. A rollout may not reopen accepted work under a different provider, scope, model, time policy or effect bound. Unsupported rollback is refused rather than attempted blindly.

Cover real process/pod termination at new durable boundaries:

- session allocation committed before response;
- input terminalization or task cancellation before caller observation;
- capacity reservation/admission and owner acceptance before reply;
- record/segment/feed publication before Search coverage;
- private source/assessment and permitted shared projection commits;
- task result captured before the recipient's context consumption;
- current-state observation after a compatible rollout.

Preserve earlier model, workspace, channel and chain interruption tests where changed code affects them. Captured work must not be recomputed merely to obtain a new successful receipt. Unknown effects stay unknown; cancellation is not compensation.

Extend fenced backup/restore to the new session allocator, terminal states, capacity records, retained segments, private scopes and task observations. Restore into a fresh observation-only namespace. Do not restore expired credentials or approvals as current authority. Prevent an old snapshot from minting capacity credits that authorize replay of already spent effects. Distinguish storage headroom from a permission to submit work.

**Acceptance:** query/history reconstruction and authorized captured-result readback after restore, private-scope denial, no duplicate workspace append, task publication, IRC send, chain deploy or model call. Original and clone must never act simultaneously as the same logical writer. This is not HA or general user-data migration.

## 14. R11 — usable distribution and safe independent qualification

Update the repository's primary entry page to the actual current release candidate. Link historical milestones as historical evidence rather than retain stale top-level claims as the current status. Keep original reports immutable.

Deliver one installable client/operator kit, provider example, chart and image manifest using the existing distribution format. The advertised starting commands should not require hidden author-working-directory files, unlisted wheels or modifications of generated policy files after every session.

The next operator should be able to install, allocate sessions, exercise native tools, inspect an expired input, run recorded qualification and perform fenced backup/restore from the distribution. Preserve restricted model/native assets and their separate acquisition requirements. No public registry/release upload is implied.

The currently executed environment is Docker-hosted single-node k3s. Support its exact path. Where adding a standard existing-k3s import mode is straightforward, implement it behind the same operator interface and test command/render behavior without pretending that a second environment was executed. Do not install a new host cluster or change topology merely to produce a portability claim.

Retain safe CI lanes, generation-denial tests and dependency/image integrity checks. Hosted execution is `NOT_OBSERVED` unless an actual authorized CI run is inspected. Never give untrusted pull requests kubeconfigs, persistent state, model access or chain signing keys. No implicit cloud spending, public endpoint or real-generation CI step.

**Acceptance:** fresh environment installation with the repository absent from `PYTHONPATH`, actual workflow through packaged clients, operator walkthrough, artifact verification and a concise review checklist. A genuinely different operator is reported only if observed, not because a second local directory was created.

## 15. R12 — final sustained qualification and delivery

Freeze a bounded final workload before execution. Keep single-node resource contention visible. Choose a finite agent/session/input/byte envelope derived from R03/R04 measurements; sequence heavy E5 and isolated-chain scenarios as needed. Do not promise concurrency unsupported by the owner contracts or change accepted deadlines during the run.

Run the following on the final selected images in one retained fresh deployment where the particular test requires continuity:

1. At least three dynamically created sessions per agent with no per-session Helm edits.
2. Actual native operations that cross and continue beyond the historical aggregate storage limit without resetting source history, native applications or result accounting.
3. Safe expiry of an undispatched head and progress of the next eligible input.
4. An uncertain started operation that remains fenced while safe independent observations and another session continue.
5. Overlapping native agent calls with actual shared-memory freshness and correct result routing.
6. Private synthetic native history/cognition and explicit authorized shared projection.
7. Recorded model placement with real native work; unavailable live selection refuses before generation.
8. Context, workbench, current-owner and retained-result observations from the same actual data.
9. Restart/restore scenarios, including exact old references/views and spent-effect accounting.
10. A same-workflow isolated-chain regression using only the supported approved synthetic artifact path; no new chain semantics or automatic disclosure.

Not every fault scenario must share one namespace: use disposable fault scopes where necessary. State exactly which continuity assertions use the same deployment and which use fresh qualification environments. Never pass a long-running-state gate by resetting it between stages.

Measure actual latency distribution and provider call counts only for declared samples; report missing spans and censored timeouts. Record configured versus observed resource enforcement. CPU quotas remain unestablished unless new evidence establishes them without unauthorized host changes.

Tie source, chart, images, packages and each final scenario together. Corrected runtime changes require affected rechecks. Do not claim one final-image run from an unlabelled union. Retain all unsuccessful attempts and explain corrections. Counts of methods, inputs, tasks, scenarios and repetitions are not additive.

### Required output

- Working code and explicit contracts for R01–R12, not another backlog recommendation.
- One current operator runbook, primary report and machine-readable gate matrix.
- Actual packaged artifacts, exact hashes and source-to-image-to-test relationships.
- Capacity policy, observed operating envelope and real native timing data.
- Native session/expiry/private-scope/workload evidence and remaining limits.
- Generation-denial evidence; offline real-backend binding evidence separately classified.
- Protected-resource before/after inventory and task-owned cleanup.

Stop heavy test processes after evidence collection. Retain only specifically documented state needed for review; do not modify the protected campaign. Publication follows existing user/workspace authority.

## 16. Acceptance states

| Gate | PASS evidence |
|---|---|
| SESSIONS | Policy-bound dynamic allocation and repeated native use without per-session deployment edits |
| TERMINALIZATION | Safe expiry/cancellation/reconciliation; no silent skip of unknown dependent effects |
| SUSTAINED_CAPACITY | Actual continued native use beyond the old bound with preserved early references and explicit new quota refusal |
| TIMING | Observed final native stages and measured attribution; no reconstructed missing data |
| CONCURRENCY | Two actual native clients, owner serialization, freshness and causal task results |
| PRIVATE_COMPOSITION | Raw and semantic access control across native history/cognition, not AtomStorage-only qualification |
| MODEL_BINDING | Explicit backend independence, captured-result semantics and generation denied without approval |
| EVALUATION | Independent factual/authority/delivery outcomes, alternate corpora and no answer injection |
| OPERATIONS | Current-versus-retained views and safe lifecycle actions in installed CLI/workbench |
| RECOVERY_RESTORE | New state recoverable without renewing authority or repeating uncertain effects |
| DISTRIBUTION | Artifact-only installation and compatibility checks on actually exercised environments |
| ZERO_LIVE | No real generative startup/contact/load/reservation/call/capture |

A required gate with an authentic external prerequisite may remain BLOCKED while independent packages finish. An executed wrong behavior is FAIL. A deliberately unexercised environment is NOT_RUN. Do not call the complete programme READY when a required usability gate is replaced by a fixture or reset-store shortcut.

Suggested final status block:

```text
PHASE3_STATUS=<READY_FOR_SUSTAINED_DEVELOPER_REVIEW | PARTIAL | FAILED_REQUIRED_GATE>
COMPLETED_PACKAGES=<R01..R12 actual>
BLOCKED_PACKAGES=<exact external prerequisites>
TESTED_SOURCE=<actual commit/content manifest>
ARTIFACT_MANIFEST=<actual path/hash>
DYNAMIC_NATIVE_SESSIONS=<result>
EXPIRED_INPUT_PROGRESS=<result>
SUSTAINED_SHARED_STATE=<result and tested finite envelope>
NATIVE_STAGE_TIMING=<OBSERVED | PARTIAL | NOT_OBSERVED>
TWO_NATIVE_CALLER_CONCURRENCY=<result>
SYNTHETIC_PRIVATE_HISTORY_COGNITION=<result>
MODEL_BACKEND_SELECTION=<result>
RECORDED_PHASE3_WORKFLOWS=<result>
FENCED_PHASE3_RESTORE=<result>
CPU_QUOTA_ENFORCEMENT=<actual observation>
HOSTED_CI=<actual observed result or NOT_OBSERVED>
MODEL_PROPOSALS=RECORDED_FIXTURE
ADDITIONAL_LIVE_GENERATIONS=0
REAL_PREVIEW_MODEL_EXECUTION=NOT_RUN
OLD_REFERENCE_CAMPAIGN=UNCHANGED
MULTI_NODE=NOT_RUN
PRODUCTION_READINESS=NOT_ESTABLISHED
```

## 17. Optional later live evaluation — procedure, not current authority

Do not make a new campaign freeze a substitute for the required engineering. The original frozen campaign remains intact on its original images and permissions. This programme neither spends nor transfers its slots.

An operator may later choose an already qualified Phase 3 workload and authorize a **new** finite campaign bound to exact source/images, backend/model, synthetic recipients/data, command catalogue, slots, limits, diagnostics and execution window. The existing campaign controls must enforce it; do not invent a new approval system.

Without that authorization, do not start the real runtime even if all other work is complete. Once authorization actually exists, use the selected real adapter without fixture fallback, hidden warm-ups, response repair, prompt tuning, replacement sessions, deadline extensions or refunded reservations. Stop under the frozen failure rules and preserve unsuccessful outcomes. Result correctness, authority, actual use of retrieved evidence and observed delivery remain separate.

The absence of real-model evidence must remain visible. A larger recorded-response test set does not establish autonomous planning, task usefulness or model reliability.

## 18. Pinned review sources

All concrete code observations refer to `660803cb955802175765ad16391b7453926b5f47`. The new operations above are proposals, not assertions that this source already implements them.

```text
https://github.com/machieke/fusion-module-interfaces/tree/660803cb955802175765ad16391b7453926b5f47
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/660803cb955802175765ad16391b7453926b5f47/docs/phase2/programme-report.md
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/660803cb955802175765ad16391b7453926b5f47/docs/phase2/runbook.md
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/660803cb955802175765ad16391b7453926b5f47/docs/phase2/native-capability-matrix.md
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/660803cb955802175765ad16391b7453926b5f47/docs/phase2/private-scopes.md
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/660803cb955802175765ad16391b7453926b5f47/docs/phase2/storage-layout.md
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/660803cb955802175765ad16391b7453926b5f47/docs/phase2/latency-diagnosis.md
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/660803cb955802175765ad16391b7453926b5f47/fusion/preview_sessions.py
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/660803cb955802175765ad16391b7453926b5f47/fusion/preview_session_service.py
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/660803cb955802175765ad16391b7453926b5f47/fusion/preview_model.py
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/660803cb955802175765ad16391b7453926b5f47/fusion/preview_recorded_model.py
```

The October 15 Kevin/Kabir discussion motivates function-based services, local-to-remote handoff and implementation/version independence. The AGI Benchmarks discussion motivates explicit ownership, actual integration and task-level evaluation. Neither meeting chooses this exact session, capacity, privacy or model policy.

**Final instruction: deliver sustained usability of the implemented system. Do not respond with another list of proposed tools or return to campaign-approval paperwork while authorized engineering remains unfinished.**
