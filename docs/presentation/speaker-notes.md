# Omega × ASI — speaker notes

Implementation baseline: `1b17d74f2808703894ea55c9539adf264bc87976`.
Evidence snapshot: `985d2f34ea8df8c5d93582e4ed6fe5cbe1843074`.
Suggested delivery: 45–50 minutes for slides 1–36, with appendices for discussion.
Current claims use the recorded 16 October 2026 M3.1 evidence; historical M3 comparison measurements are labelled. The M1 chain observation is historical and separately labelled.

## 01 — Remember the evidence. Bound the work. Account for every effect.

Start with the ELI16 executive summary, then all fifteen module responsibilities and the exercised dependency maps. M1 established replaceable ports and independent commits; M1.2 connected real Hive; M2 added private memory and guarded revision; M3 adds independent short-term attention and bounded inference over an explicit workset. M3.1 closes delivery seams with separate owner-authoritative progress and no new cognition. Suggested delivery: 45–50 minutes through slide 36; eight appendices support discussion. Evidence is clean tested implementation 1b17d74f2808703894ea55c9539adf264bc87976 recorded by 985d2f34ea8df8c5d93582e4ed6fe5cbe1843074. This deck update does not rerun integration gates or add runtime behavior.

Source: `M3.1 evidence 985d2f3 · tested 1b17d74`.

## 02 — ELI16: remember, weigh evidence, do the calculation

ELI16 assumes a technically curious sixteen-year-old. The analogy explains responsibilities, not an additional experiment. C1 records occurrences and provenance. C2 distinguishes admission from numerical aggregation and retains disagreement. The pure providers reuse guarded Truth_Revision and one grounded Truth_Deduction rule. Their outputs remain model-specific heuristics, not proof of external truth or source independence. Derived conclusions inherit evidence roots and ancestry and add no observation or evidence count. Generated observations and operator assumptions remain fixtures, even when they travel through real runtimes.

Source: `M2 preserved · M3 derived admission`.

## 03 — ELI16: a priority list and a limited attempt budget

Short-term importance, or STI, is a simple deterministic priority score. It is separate from PLN truth values. C4 handles a fixed explicit workset; it does not invent new tasks or search the knowledge base. The measured two-task experiment changes initial attention to select the other task while keeping the one-attempt budget fixed. Attempts are durable physical evaluation opportunities. A crash after reservation spends the slot even if no result commits. Successful replay recovers recorded admission and feedback without extra native calls. These are local process-restart observations, not hard real-time or production-quality claims.

Source: `C3 attention · C4 bounded inference`.

## 04 — ELI16: finishing the job and settling its receipts

Closure means accounting for recorded effects, not guaranteeing global completion. Nine fixture methods, five real-provider methods, sixteen direct SIGKILL cases and seven native Hive cases (four with kills) support the new behavior. The 33-event episode uses real DeTTa/native PLN with generated observations. A report can be durably processed without a numerical truth value. Feedback resolution never newly applies eligible feedback: it returns an existing receipt, creates a no-credit retirement if stale or expired, or stays pending. C4 exposes progress separately from immutable execution counters. New profiles require fresh journals; old M3 pending stores are not migrated or repaired.

Source: `M3.1 delivery closure · owner receipts`.

## 05 — Fifteen modules; four responsibility groups

All fifteen responsibility groups remain visible. C1/C2 implement private memory and beliefs; M3 adds independent STI and bounded C4 plus a pure kernel for one grounded rule. Relations and Search remain specifications. Attention implements a bounded reference policy, not ECAN, LTI or the coupled metta-attention algorithm. RevisionMath is separate from PLNKernel.applyRule. Hive consumes these modules; a module need not be a separate process or repository. Blue means implemented local contracts, not production readiness. Authorization uses real Hive authentication followed by local test policy. Finality retains historical M1 evidence only; CHAIN is NOT_RUN through M3.1. Maintainer assignments remain unassigned.

Source: `architecture.md`.

## 06 — Data responsibilities: bytes → references → history

AtomStorage owns immutable scoped references and replay metadata, while DA only persists opaque payloads and generic coordinates. Relations and Search remain typed specifications. C1 exposes recordEpisode, appendEvent, readEpisode, readEvidence and pendingEvidence. The new local v3 completion port is bound to a trusted relay context separately from the ordinary EpisodeJournal. C1 validates completion identity and selected consumer, not PLN snapshots. Original v2 remains selectable. findEpisodes is not advertised. C1 preserves committed episode-local order and admitted provenance; observed time is metadata. It can run without C2 or PLN and against an independently implemented AtomStorage fixture. Its event bytes are immutable atoms, while its episode head and delivery intents belong to C1.

Source: `architecture.md`.

## 07 — Cognitive responsibilities: four separate roles

C3 implements the bounded sti-additive-linear-decay/1 reference policy, not ECAN or the inspected metta-attention implementation. C4 owns selection and physical attempt reservations; it depends on AtomStorage, Attention, DerivedBeliefRevision and PrivateAuthority. It does not call PLNKernel directly. C2 depends on AtomStorage, C1 readEvidence, RevisionMath, PLNKernel and PrivateAuthority. The pure kernel owns no belief, agenda or attention state. M2 revision-only local v2 remains selectable; derived private C2 is a fresh local v3 profile.

Source: `architecture.md`.

## 08 — Control responsibilities: move work, preserve authority

Messaging acceptance differs from delivery and acknowledgement. Execution accepts only inspect_atom and owns jobs plus its completion outbox; result atoms commit independently. The registry advertises descriptors, and the resolver matches consumer requirements. Neither grants permission. Finality records independent chain observations from historical M1; it is not a C1/C2 dependency. Native authentication supplies trusted actor context, while local Fusion policy determines current access. The preserved M2 relay is a narrow delivery cursor between C1 and C2. M3 C4 separately owns its bounded step journal; neither grants authority.

Source: `architecture.md`.

## 09 — Function dependencies: the exercised M3.1 path

This graph shows exercised calls. Hive's scenario appends private C1 events and uses the selected relay as its only new-profile evidence-admission path. Relay calls C1 pending/ack and C2 submitEvidence; it validates the complete selected C2 decision before attesting completion to C1. C4 reads private task/workset atoms and C2 snapshots, selects through C3, reserves work and submits or recovers C2 derivations. C4 reconciliation calls only Attention.resolveFeedback on recorded intents: no task selection, C2 admission or PLN call. C2 reads evidence through C1 and calls the unchanged pure math providers. C3 requires authority and reference syntax only. Bottom cards summarize storage/authority dependencies; each owner has an independent local commit. Original M2/M3 profiles remain selectable.

Source: `cognition.py · ports.py · evidence_relay.py`.

## 10 — Function dependencies: the preserved M1.2 path

Follow the real native dispatch into the thin plugin, which holds a caller-owned receipt and uses Subprocess/Peer through descriptor-bound validation. Direct storage, messaging and execution calls all cross the same authenticated boundary. Trusted composition supplies concrete owners; the plugin never constructs them or accesses their tables. Messaging.send validates the referenced bytes through caller-authorized AtomStorage.get; Execution.submit reads the input before accepting a new job. The worker calls declared AtomStorage get/create, then execution commits terminal state/outbox. CompletionDelivery.accept belongs to the mailbox owner and commits separately. Chain remains a separate, uninvoked adapter. This is a logical call map; it does not force one process per module.

Source: `program.py · ports.py · execution.py`.

## 11 — The DA boundary remains application-neutral

This unchanged DA boundary is exercised against a freshly fetched clean secured-contract-spaces revision 272888f264dd2dde18b574cabb53c266b0dac2ec. No Hive-specific schema is added to DeTTa. Application references and replay semantics belong above opaque DA. Conformance removes the cached payload and two erasure shares and verifies reconstruction; three missing shares and corruption fail explicitly. This is actual local library execution, not a validator/custody network or an indefinite-retention claim. The independent atomic-file provider is an AtomStorage contract fixture, not a second DA network. The clean-source rebaseline excludes historical dirty storage-format and custody-pruning additions and reruns applicable tests.

Source: `adapters/detta/src/main.rs · test_contract.py`.

## 12 — Two independent substitutions, one design principle

The storage matrix has two implementations times two bindings. C1 is independently exercised without cognition using hostile declared-port wrappers. M3 attention replacement uses a separately implemented atomic-file provider; only DTO validation is shared with the SQLite implementation. Four controlled native cases hold exact task/evidence identities, policy, budgets and deadline fixed while selecting the provider in composition. Separate initial-preference cases show the selection effect. Both replacements persist actual state, but the file implementations remain classified fixtures rather than real DeTTa or a production attention service. This demonstrates same-profile replacement on fresh stores, not live migration.

Source: `m11-swap-demo.json · m3/final/comparison.json`.

## 13 — Private state has explicit owners and placement

The native plugin receives authenticated actor context and derives authority from operator configuration. Request parameters cannot select credentials, arbitrary scopes or private premise identities. Public parameters are generated seed, preference a/b and an absolute deadline. Privacy tests intercept shared bindings, populate shared stores and inspect native receipts/logs/state for canaries and private hashes. This is tested local placement under a trusted operator/host, not secrecy from administrators. Each journal has one owner and commits independently; there is no cross-owner SQL transaction.

Source: `cognition.py · inference_program/program.py`.

## 14 — Executable contracts make the inference step finite

The contracts use closed bounded DTOs and detach nested request inputs before authorization or foreign calls. A task binds P,Q,R,P⇒Q,Q⇒R to exact private references. Premise vectors record each belief's historical revision and support ID; the upstream knowledge revision of zero is only a local evaluation ID, not a global ledger. Derived support tags distinguish observation, two-local-premise revision and five-foreign-premise deduction. C2 local v3 is explicit and does not widen M2 v2. WorkBudget contains an absolute Unix-ms deadline, max_candidates, max_rule_applications and max_feedback_generation. Historical reads and recovered owner responses are validated against the exact request.

Source: `attention_contracts.py · cognition_contracts.py`.

## 15 — C1: one occurrence, one position in the story

The four illustrated event roles match the generated story. Each immutable event is referenced by an AtomRef; the episode head begins at zero and advances by one for accepted occurrences. A duplicate occurrence with the same semantic content returns its original receipt before a stale expected-head check, even under a new request key. Changed content or provenance for that occurrence conflicts. Distinct occurrences can have identical bytes. Payload persistence can precede episode commit and leave an orphan after death; replay recovers the same atom without inventing an acknowledged event. C1 exposes bounded reads, pending evidence and trusted acknowledgements, with no cognition dependency. No dynamic episode search or garbage collector is implemented.

Source: `episodes.py · tests/test_m2.py`.

## 16 — C1 delivery closes without understanding PLN

Five commits belong to three owners; there is no cross-owner transaction. The selected adapter validates exactly one C2 profile and full response, including v3 support fields after a real deduction. C1 accepts trusted-evidence-completion/1 through a separately bound context unavailable to ordinary episode/Hive clients. A completion identifies scope, delivery, exact evidence/claim/context, selected consumer, request and decision digests. It asserts committed processing, not truth. Relay recovers its own committed intents when the C1 acknowledgment response was lost and the delivery no longer appears pending. The real-provider run drains 33 generated observations in batches 16/16/1. Capacity testing refuses append 17, then uses public drain before appending. Reports and unregistered-origin observations close as model-inapplicable with null numerical truth; contrary observations remain retained. Four evidence boundaries times two providers give eight direct kills, plus two native caller evidence kills.

Source: `delivery_contracts.py · evidence_relay.py · m3_1 evidence`.

## 17 — C2: admitting evidence and changing belief are separate

This slide describes preserved observation admission. M3 adds a separate derivation command with inherited evidence, described next. The first eligible explicit assessment initializes the aggregate. Later evidence is retained without automatic aggregation unless an exact pair assumption and guards permit revision. Unknown origins cannot initialize a justified numerical aggregate. A report without numerical assessment is model-inapplicable. The ledger retains observations, support records, immutable snapshots and exact decisions. A later authorized independence declaration may combine already admitted supports, without creating another observation. Exact successful replay returns the original historical decision even after later revisions; a new-key duplicate returns current state without adding weight. Retained-alternative is a pair outcome, so an already covered ancestor need not produce a new alternative list entry or revision. Coverage fields state the actual result.

Source: `beliefs.py · memory_types.py`.

## 18 — A derived conclusion inherits its evidence trail

The five foreign premises are not five independent observations of the output claim. local-admitted-supports/1 treats the deduction as one local support unit with its inherited evidence/root union. Logical derivation identity is independent of request/step IDs, deadlines and output CAS. A duplicate cannot gain another admission or causal feedback credit. A separately authorized independence assumption can request the unchanged guarded native revision of eligible supports. Derive → revise retains grounded ancestry; a cyclic subsequent deduction is refused. Claims remain heuristic and lineage-aware, not calibrated uncertainty or proven entailment.

Source: `derived_beliefs.py · pln_deduction.py`.

## 19 — One grounded rule reuses the actual native PLN

The unchanged Reachability dd56f3f implementation invokes PLN 4405956 Truth_Deduction on PeTTa ae66fa8 and SWI source 6977543, version 10.1.14. The exact runtime profile is fusion-petta-swi-10.1.14-deduction/1. No PLN.Derive, PLN.Query or task search is used. The Q>0.9999 branch and its assumptions remain upstream semantics and are tested. Kernel source checks and native subprocesses use the remaining absolute deadline. This pure component owns no belief, agenda or attention state. Source drift, malformed output and timeout are explicit refusals, with fault injections labelled in the native suite.

Source: `deduction-sources.json · integration/pln/test_deduction.py`.

## 20 — Native goldens check deduction and preserved revision

The M3 golden has five ordered premises and uses the actual native Truth_Deduction. Expected values are independent test oracles, not production mathematics. M2 revision goldens still pass in the M3 regression, including reversed unequal pairs. Native suites include actual computation plus explicitly injected malformed responses, timeouts, source-drift clones and authorization/CAS interleavings. Fifteen upstream guard-only tests use RecordingRuntime and are not counted as native numerical evaluation. Evidence_count remains null, and a derived conclusion never turns into a fresh independent observation.

Source: `test_deduction.py · preserved test_revision.py`.

## 21 — C3: a small, independent attention policy

The reference policy is frozen in its identity. Bounds are 16 targets, 16 advance steps per call, eight contexts, 512 causes per context, 1024 commands per owner and feedback generation three. Capacities refuse without silent eviction of acknowledged commands. Stimulus saturation is min(amount, Smax-current); total context budget is enforced atomically. Successful replay is checked before logical clock CAS under live authorization. Causal deduplication is independent of request identity; changing a causal body conflicts. Fresh feedback follows the target's current causal parent and next generation. metta-attention 3e1c8147 was inspected but not integrated because it couples STI/LTI/VLTI, wages and shared funds. C3 has no hidden dependency on AtomStorage, C1, C2, PLN or Hive.

Source: `attention.py · fixture_attention.py`.

## 22 — Attention replacement preserves the measured outcome

All four fresh cases use two tasks, five premises per task, ten generated observations, two episodes and twelve claim atoms. Held fixed: exact task/evidence refs, policy parameters, one-attempt/two-candidate budgets, absolute deadline and logical schedule. Separate preference cases exchange initial scores 20/10 and 10/20. Only composition chooses SQLite or the independently implemented file fixture; no consumer code changes. Every result records examined=2, reserved=1, completed=1, refused=0, unique admission=1 and feedback_applied=1, ending at rule-budget. The second candidate is counted before discovering the exhausted rule budget. Preparation takes about 11.5–11.8 seconds and is separate from the reported step time. Store sizes are 1,040,671 and 1,020,409 bytes respectively. These are one-run local measurements, not throughput or cognitive-quality evidence.

Source: `m3/final/comparison.json`.

## 23 — C4: reserve work durably before invoking the rule

C4 counts a candidate before resolving it, including unresolved or refused candidates. It commits reservation before dispatch and queries a prior C2 decision first during recovery. C2 persists semantic intent before evaluation, evaluates outside its commit transaction, then rechecks authority and output CAS. A killed pending attempt needs a new reserved slot/key; a committed decision is read back without evaluation. Logical derivation identity is distinct from transport request, controller step, attempt key, deadline and output CAS. Feedback is a fixed one-unit workflow signal tied to logical derivation identity, never a truth update. Absolute Unix-ms deadline survives restart; scheduling/file I/O remain cooperative, not hard real-time.

Source: `inference.py · deadlines.py`.

## 24 — C3 alone settles the feedback outcome

resolveFeedback never applies fresh eligible feedback. Existing application wins even after expiry or decay; it returns the original receipt without changing current STI. Otherwise stale/expired intent can create a no-credit tombstone atomically; eligible or unavailable/malformed responses remain pending, and revocation fails closed. Application and retirement share SQLite transaction or independent atomic-file locking. Concurrent eligible application versus clock advance/retirement and both serialized outcomes were exercised on both providers. First retirement consumes one existing cause and command slot; existing receipts/tombstones need no new slot. No capacity enlargement or eviction. C4 persists a bounded cursor and separate closure version. Same reconciliation key returns its original observation; fresh keys/readProgress can see newer closure. It never calls selection, C2 admission or PLN, refunds reservations, resets deadlines or retimes feedback. Finite exhausted capacity can leave work pending.

Source: `attention.py · fixture_attention.py · inference.py`.

## 25 — Five crash boundaries, independent owner commits

Three native recovery methods cover ten actual SIGKILL cases: stimulus commit for both attention providers; reservation and kernel-return loss under budgets one and two; belief/feedback recovery for both providers. The real Hive suite adds five actual caller kills across the same boundaries. A one-slot loss conservatively exhausts the budget; a two-slot case may recover one logical admission after another physical calculation. Thus there is no claim of exactly one physical calculation per logical derivation. Committed admission and feedback are duplicate-safe. This is intact-local-file, same-host process restart, not reboot, power loss or distributed failover.

Source: `test_m3_recovery.py · test_m3_integration.py`.

## 26 — Authorization, replay and profiles remain live

Input records are copied before foreign calls and authorization so a malicious boundary cannot mutate the retained command. Recovered C2 and attention responses are checked against exact owner/request identities and semantics. Current principal, scope, method and descriptor permissions apply on every invocation. The assumption permission for revision remains separate. Native proposal calculation runs outside the owner commit transaction; final authorization and expected output revision are rechecked afterward. Old-profile feedback can remain CONFLICT after a clock change. The new profile lets Attention resolve recorded stale feedback by no-credit retirement; eligible or unavailable feedback stays pending. The controller never rewrites the logical schedule. These are local trusted-authority guarantees, not a production identity system.

Source: `cognition.py · derived_beliefs.py · tests/test_m3.py`.

## 27 — One real Hive action reaches the entire private path

The real pinned Hive create_app, authenticated Programs dispatch, default Supervisor and native PeTTa run in the integration. The narrow sibling plugin uses native assessment role, action infer-generated, and trusted actor mapping. ASGI TestClient, identities, observations and operator assumptions are fixtures; the runtime, DeTTa and formula execution are actual providers. The plugin owns caller intent/receipt and invokes the private scenario; it owns no belief, STI or controller state. The preserved M3 suite has eight native cases and five kills. The new M3.1 suite adds seven native cases, four with actual kills, covering both providers, closure progress, evidence recovery and explicit zero-conclusion execution. The new-profile scenario drains C1 evidence through the relay. The diagram summarizes the call sequence; each owner commits independently. M1 fusion-inspect and M2 fusion-episode remain supported and rerun in regression.

Source: `inference_program/program.py · test_m3_integration.py`.

## 28 — Native Hive exposes execution and closure separately

The top row summarizes the tested stale-feedback case: original execution has one admission and zero acknowledged feedback; after controlled clock advance STI is nine, and reconciliation retires the stale effect without changing that execution. The bottom row covers separate applied-before-lost-reply and expired-before-execution tests, not one combined run. The actual authenticated native Programs 0.1 dispatcher selects the existing plugin. Prepared original-command mapping is private and persisted before step. Public parameter original_command respects the unchanged Hive credential guard. The response exposes execution status/reason, admissions, original counts/remaining, evidence pending/state, feedback closure counts and version. Private episode/task/support IDs, roots, snapshots, credentials and paths are excluded. Seven native cases include four process kills; both attention providers are exercised. Same public reconciliation identifier replays the same observation; use a new one for newer progress.

Source: `inference_program/program.py · test_m3_1_integration.py`.

## 29 — The same one-attempt budget makes attention visible

This chart depicts the explicitly configured STI scores in the controlled scenarios, not a learned score or performance estimate. The comparison exercises both preferences with both providers; the real Hive tests separately exercise actual native action and replacement. A step freezes the ranked selection. Subsequent feedback affects a later step, not the order already accepted. C4 examines two candidates but reserves and executes only one attempt, so terminal reason is rule-budget. All four comparison cases recover identical receipts after reopening owners and invoke the native formula zero additional times on successful replay. Cognitive usefulness of the chosen conclusion is not measured.

Source: `m3/final/comparison.json · native Hive scenario`.

## 30 — Real providers and fixtures remain visibly separate

Native kernel/admission includes actual formula executions plus labelled malformed-response, timeout, source-drift and authorization/CAS fault cases. The fifteen upstream guard tests use RecordingRuntime. Both attention providers persist state, but the independent file provider retains fixture classification. Real Hive uses fixture identities, generated inputs and TestClient transport; its default Supervisor and Programs runtime are actual. Optional historical chain observations remain separate and are not a new M3 chain pass. Historical SWI 10.0.1, the full Hive suite and hard real-time behavior are unrun. The fresh build uses warm download caches, not reused native objects.

Source: `m3_1/manifest.json · m3_1-evidence.md`.

## 31 — Executed tests cover delivery, races and real crashes

The M1–M3 verifier ran completely from corrected source 1b17d74: original fixtures 51, DeTTa-enabled aggregate 127 (118 previous plus nine new), DeTTa 62+38, Hive baseline 34 and unchanged M1.2 integration 13. M2 fixtures/guards/native revision/recovery/Hive: 16/8/12/6/7 plus demo. M3 attention/contracts/guards/native admission/recovery/Hive: 5/7/15/13/3/8 plus four comparison cases. M3.1 explicit fixtures nine, real-provider methods five, direct recovery methods three (sixteen distinct SIGKILL cases) and native Hive seven (four with kills). Two separate non-numerical real-provider probes are retained. Repeated subsets and development reruns are not extra unique coverage. Earlier protocol introspection and harness failures were corrected before this final run. No runtime integrations were rerun for this presentation update.

Source: `m3_1/final/verification.json · non-numeric-processing.json`.

## 32 — M3.1 gates: delivery and authoritative outcomes

Statuses are read from the M3.1 machine manifest and match the corrected final verifier. Twelve supported gates pass; CHAIN is NOT_RUN. The complete prior M1–M3 regression passes separately. COMPAT_REPRO uses fresh provider directories and original pins with warm download caches. Populated old-profile copies reject the new profiles without modification and still replay through the old selection. This is not migration or repair of existing pending stores. Exact historical chain-source reproduction remains blocked by unavailable dirty inputs, a separate historical question. Passes cover only the tested local scope; power-loss, distributed and production claims remain unrun.

Source: `m3_1/manifest.json`.

## 33 — M3.1 gates: bounded recovery and native integration

Statuses are read from the M3.1 machine manifest and match the corrected final verifier. Twelve supported gates pass; CHAIN is NOT_RUN. The complete prior M1–M3 regression passes separately. COMPAT_REPRO uses fresh provider directories and original pins with warm download caches. Populated old-profile copies reject the new profiles without modification and still replay through the old selection. This is not migration or repair of existing pending stores. Exact historical chain-source reproduction remains blocked by unavailable dirty inputs, a separate historical question. Passes cover only the tested local scope; power-loss, distributed and production claims remain unrun.

Source: `m3_1/manifest.json`.

## 34 — Reproducibility connects source, build and observed result

Requested ancestor c4498ce3047f1283d3a4a3ae3d09b713e7dcf312; actual starting descendant 3b34e00df75055d54a57ba7e38eb8b2d9e82ed7e; tested source 1b17d74f2808703894ea55c9539adf264bc87976; evidence-only descendant 985d2f34ea8df8c5d93582e4ed6fe5cbe1843074. Build_m3.py wraps the byte-identical M2 recipe and adds the separately selected deduction configuration. All exercised upstream sources were clean at their pins. Historical M2 SWI binary identity differs from the fresh M3 build and is not silently equated. Exact hashes, versions, command arguments, durations and JUnit results are committed. Provider environment files can contain local configuration and are deliberately excluded from published evidence. This deck hashes its evidence inputs and audits the archive without modifying it.

Source: `m3_1/build.json · manifest.json · final/verification.json`.

## 35 — The limitations are part of the contract

M3.1 solves the delivery/feedback seams only for explicitly selected new profiles and fresh journals. Disposable copies of populated old stores reject the selection with UNSUPPORTED_PROFILE and remain replayable under old profiles. Existing user stores are not migrated or repaired. Pending feedback need not converge: eligible effects are not newly applied by reconciliation, unavailable/malformed replies stay pending, and bounded tombstone/command capacity can exhaust. Unresolved derivation attempts use original step recovery, not reconciliation; lost reservations are not reclaimed. No exactly-one physical computation, hard real-time, power-loss, administrator secrecy, distributed failover, production throughput or cognitive-quality claim. Origin/independence remain operator assumptions. Specialist maintainer assignments remain open.

Source: `m3_1-evidence.md · compatibility and recovery limits`.

## 36 — Keep the evidence. Preserve the budget. Account for every effect.

Return to the ELI16 summary: record the report, preserve the calculation budget and settle each recorded effect with its owner. C1 accepts model-independent processing completion from the trusted relay. C2 owns beliefs and unchanged native math. C3 resolves applied, retired or pending feedback; C4 records later closure without changing historical execution. Native Hive exposes both facts. Both attention providers pass the same closure scenarios; process kills test independent commits. All twelve supported M3.1 gates pass, prior M1–M3 regressions pass, no supported prerequisite is blocked, and chain remains NOT_RUN. Existing pending stores need migration outside scope. This is delivery closure, not new cognition or production readiness.

Source: `M3.1 tested 1b17d74 · evidence 985d2f3`.

## 37 — Implementation map: responsibilities stay local

Paths are relative to fusion/ unless marked hive/, which is under integration/. ports.py declares the protocols; attention_contracts.py and cognition_contracts.py enforce the executable bounded schemas. Shared DTO validators are permitted in the independent fixture, shared owner transitions are not. C2 default M2 behavior remains via its original validators and profile; the derived owner selects fresh v3 behavior. The native plugin uses integration/m3_scenario.py and holds only caller intent and public receipt. No owner reaches into another owner's private SQL. Tests and exact source hashes are indexed in the M3.1 machine manifest. Historical protocol declarations are preserved; new closure protocols are explicit.

Source: `architecture.md · ports.py`.

## 38 — Exact sources identify the verified native stack

Evidence commit 985d2f34ea8df8c5d93582e4ed6fe5cbe1843074. Full inspected metta-attention revision: 3e1c8147dc17299d17ab34720334fc19277cb6a9, clean. Its coupled STI/LTI/VLTI, wages and funds are not silently adopted. Runtime profile: fusion-petta-swi-10.1.14-deduction/1; rule profile: grounded-five-premise-deduction/1; truth model: trueagi-pln-stv-finite-k1/v1. PLN library SHA-256 cdfb3f18bd7b336440fc7b4409209afddf0e64c41f17dee7eefc8f02718de433. Fresh SWI binary SHA-256 dcd379ed717cd4869b4ef0b4683bcb4023177b6d04f2356cddb85b1c5c666262. Native Python 3.12.12, Janus 1.5.3; fixture runner Python 3.11.14. All exercised source checkouts were clean. No upstream formula or runtime implementation was patched. Historical SWI 10.0.1 remains unrun.

Source: `m3_1/final/verification.json · build.json`.

## 39 — Profiles and bounds make compatibility explicit

The configuration selector is fusion-delivery-closure/1. C1's trusted completion DTO has profile trusted-evidence-completion/1. C3 arithmetic policy remains sti-additive-linear-decay/1 while its interface/profile explicitly adds submitFeedback and resolveFeedback. C4 adds readProgress and reconcile. Max 16 targets, 16 advance steps, eight contexts, 512 causes/context, 1024 commands/owner and feedback generation three are unchanged. First retirement consumes existing cause/command capacity; recovering an existing application or retirement does not allocate a new slot. Reconciliation has its own finite command budget and cannot reset original WorkBudget/deadline. M1 wire, M2 revision and M3 old cognition profiles remain supported. Algorithm profile, interface version, selected descriptor, runtime and current permissions all matter.

Source: `contracts.md · cognition.py`.

## 40 — New profiles close the seam; old stores stay explicit

Baseline reproduction against clean 3b34e00 confirms the old acknowledgment/relay NOT_AVAILABLE, 16 pending then append 17 OVERLOADED, and persistent stale-feedback CONFLICT after reopen. Those expected gaps are separate from the passing baseline regression. New-profile delivery drains, including after deduction and for model-inapplicable reports. Neither this extension nor the presentation migrates existing state. Compatibility tests populate old stores, operate on disposable copies, reject new selection without modifying bytes and replay with original descriptors. Fresh profiles preserve strict time and causal semantics. This distinction must survive any claim that the seam is now closed.

Source: `m3_1/baseline/gaps.json · test_m3_1_compat.py`.

## 41 — One native operation crosses the existing interfaces

All effects originate in the real native operation, not a renamed protocol demo. The caller first commits its original intent. AtomStorage persists generated bytes in actual DeTTa, then Messaging accepts a reference for the explicitly labelled fixture counterparty. DelegatedExecution accepts only inspect_atom under the original key and correlation. The caller records the accepted job. A separate real worker reads/persists through AtomStorage, then commits execution terminal state/outbox. Messaging accepts the completion in a separate transaction. The final arrow summarizes reconciliation: status /2 restores known correlation, poll and get verify the completion, caller acceptance commits, and a stable-key acknowledgement follows. This is not one distributed transaction.

Source: `program.py · execution.py · messaging.py`.

## 42 — Historical M1: one result reached an isolated chain

Preserve this historical result without promoting it into the new real-caller gate. The M1 chain JSON records pending, included with effect finality Pending, then finalized, at height 3 with no execution error, no rejection and cost 351 phlo. The committed digest belongs to the original protocol-peer result, not the generated native Hive result in M1.2. The M1 adapter used a registered approved digest, injected signer and durable signed intent against one isolated local node. That source had local changes and an untracked input. Exact historical reproduction remains blocked until those authorized bytes are supplied or a different clean revision is separately validated. No chain process or transaction was run during M1.2, M2, M3, M3.1 or this presentation update. Finality does not establish indefinite off-chain availability.

Source: `evidence/chain-demo.json · M1 historical`.

## 43 — Reproduce the supported M3.1 gates

Linux build prerequisites and authorized SSH access to exact Hive/DeTTa sources are documented in the runbook; public HTTPS retrieves the pinned Reachability/PLN sources. New native objects, Python/Janus venv and DeTTa Cargo target are built in a fresh directory. Download caches may be warm. build_m3.py preserves the M2 build recipe and adds the explicit deduction profile. verify_m3_1.py runs the complete M1–M3 verifier plus closure fixtures, real-provider methods, direct process kills and native Hive closure. The final record was executed from clean detached /tmp/fusion-m31-final-corrected. Use --output with a fresh evidence directory to avoid confusing prior runs. Fresh new-profile journals are required. Do not publish broad local environment files. Deck generation is a separate documentation operation and does not rerun these gates.

Source: `runbook.md · build_m3.py · verify_m3_1.py`.

## 44 — Retry identities answer different questions

A derivation's logical ID excludes request/step identity, output CAS and deadline so a retry cannot manufacture new independent support. An attempt key freezes its exact semantic body and is evaluated at most once; a killed pending attempt consumes a physical reservation. Multiple physical calculations for one logical derivation remain possible under distinct reserved attempts. C2 commits its decision before C4 progress; C3 commits feedback before C4 acknowledgment. Recovery queries those owners rather than inferring success from a missing local reply. Feedback_applied counts acknowledged unique logical credits; feedback_duplicate records suppression on duplicate admission. Fixed feedback adds no truth evidence. The semantics distinguish bounded termination, successful admission and fully acknowledged work.

Source: `inference.py · derived_beliefs.py · attention.py`.
