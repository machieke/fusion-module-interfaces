# Omega × ASI — speaker notes

Implementation baseline: `1af39794649d0ca95cd729c64868202368da1ec4`.
Evidence snapshot: `c4498ce3047f1283d3a4a3ae3d09b713e7dcf312`.
Suggested delivery: 40–45 minutes for slides 1–32, with appendices for discussion.
Current claims use the recorded 16 October 2026 M3 evidence. The M1 chain observation is historical and separately labelled.

## 01 — Remember the evidence. Choose where to focus. Bound the work.

Start with the ELI16 executive summary, then all fifteen module responsibilities and the exercised dependency maps. M1 established replaceable ports and independent commits; M1.2 connected real Hive; M2 added private memory and guarded revision; M3 adds independent short-term attention and bounded inference over an explicit workset. Suggested delivery: 40–45 minutes through slide 32; eight appendices support discussion. Evidence is the clean tested implementation 1af39794649d0ca95cd729c64868202368da1ec4 recorded by c4498ce3047f1283d3a4a3ae3d09b713e7dcf312. This deck update does not rerun integration gates or add runtime behavior.

Source: `M3 evidence c4498ce · tested 1af3979`.

## 02 — ELI16: remember, weigh evidence, do the calculation

ELI16 assumes a technically curious sixteen-year-old. The analogy explains responsibilities, not an additional experiment. C1 records occurrences and provenance. C2 distinguishes admission from numerical aggregation and retains disagreement. The pure providers reuse guarded Truth_Revision and one grounded Truth_Deduction rule. Their outputs remain model-specific heuristics, not proof of external truth or source independence. Derived conclusions inherit evidence roots and ancestry and add no observation or evidence count. Generated observations and operator assumptions remain fixtures, even when they travel through real runtimes.

Source: `M2 preserved · M3 derived admission`.

## 03 — ELI16: a priority list and a limited attempt budget

Short-term importance, or STI, is a simple deterministic priority score. It is separate from PLN truth values. C4 handles a fixed explicit workset; it does not invent new tasks or search the knowledge base. The measured two-task experiment changes initial attention to select the other task while keeping the one-attempt budget fixed. Attempts are durable physical evaluation opportunities. A crash after reservation spends the slot even if no result commits. Successful replay recovers recorded admission and feedback without extra native calls. These are local process-restart observations, not hard real-time or production-quality claims.

Source: `C3 attention · C4 bounded inference`.

## 04 — Fifteen modules; four responsibility groups

All fifteen responsibility groups remain visible. C1/C2 implement private memory and beliefs; M3 adds independent STI and bounded C4 plus a pure kernel for one grounded rule. Relations and Search remain specifications. Attention implements a bounded reference policy, not ECAN, LTI or the coupled metta-attention algorithm. RevisionMath is separate from PLNKernel.applyRule. Hive consumes these modules; a module need not be a separate process or repository. Blue means implemented local contracts, not production readiness. Authorization uses real Hive authentication followed by local test policy. Finality retains historical M1 evidence only; CHAIN is NOT_RUN in M3. Maintainer assignments remain unassigned.

Source: `architecture.md`.

## 05 — Data responsibilities: bytes → references → history

AtomStorage owns immutable scoped references and replay metadata, while DA only persists opaque payloads and generic coordinates. Relations and Search remain typed specifications. C1's local v2 operations are recordEpisode, appendEvent, readEpisode, readEvidence, pendingEvidence and trusted acknowledgeEvidence. findEpisodes is not advertised. C1 preserves committed episode-local order and admitted provenance; observed time is metadata. It can run without C2 or PLN and against an independently implemented AtomStorage fixture. Its event bytes are immutable atoms, while its episode head and delivery intents belong to C1.

Source: `architecture.md`.

## 06 — Cognitive responsibilities: four separate roles

C3 implements the bounded sti-additive-linear-decay/1 reference policy, not ECAN or the inspected metta-attention implementation. C4 owns selection and physical attempt reservations; it depends on AtomStorage, Attention, DerivedBeliefRevision and PrivateAuthority. It does not call PLNKernel directly. C2 depends on AtomStorage, C1 readEvidence, RevisionMath, PLNKernel and PrivateAuthority. The pure kernel owns no belief, agenda or attention state. M2 revision-only local v2 remains selectable; derived private C2 is a fresh local v3 profile.

Source: `architecture.md`.

## 07 — Control responsibilities: move work, preserve authority

Messaging acceptance differs from delivery and acknowledgement. Execution accepts only inspect_atom and owns jobs plus its completion outbox; result atoms commit independently. The registry advertises descriptors, and the resolver matches consumer requirements. Neither grants permission. Finality records independent chain observations from historical M1; it is not a C1/C2 dependency. Native authentication supplies trusted actor context, while local Fusion policy determines current access. The preserved M2 relay is a narrow delivery cursor between C1 and C2. M3 C4 separately owns its bounded step journal; neither grants authority.

Source: `architecture.md`.

## 08 — Function dependencies: the exercised M3 path

This is the exercised port graph, not a proposed future cognitive loop. C4 reads immutable task/workset atoms and C2 snapshots, asks Attention to select, reserves work, then submits or recovers a C2 derivation. C2 reads evidence from C1, invokes pure PLNKernel or RevisionMath and alone commits admitted support. The Hive scenario also records a private episode and seeds exact inputs; those setup edges are omitted for readability. C3 depends only on PrivateAuthority and opaque-reference syntax, not AtomStorage, C1/C2, PLN or Hive. Every owner checks live authority and descriptors; omitted authority arrows apply to all calls. The M2 relay remains supported under its original profile; M3 v3 responses do not masquerade as M2 C1 acknowledgments.

Source: `cognition.py · ports.py · architecture.md`.

## 09 — Function dependencies: the preserved M1.2 path

Follow the real native dispatch into the thin plugin, which holds a caller-owned receipt and uses Subprocess/Peer through descriptor-bound validation. Direct storage, messaging and execution calls all cross the same authenticated boundary. Trusted composition supplies concrete owners; the plugin never constructs them or accesses their tables. Messaging.send validates the referenced bytes through caller-authorized AtomStorage.get; Execution.submit reads the input before accepting a new job. The worker calls declared AtomStorage get/create, then execution commits terminal state/outbox. CompletionDelivery.accept belongs to the mailbox owner and commits separately. Chain remains a separate, uninvoked adapter. This is a logical call map; it does not force one process per module.

Source: `program.py · ports.py · execution.py`.

## 10 — The DA boundary remains application-neutral

This unchanged DA boundary is exercised against a freshly fetched clean secured-contract-spaces revision 272888f264dd2dde18b574cabb53c266b0dac2ec. No Hive-specific schema is added to DeTTa. Application references and replay semantics belong above opaque DA. Conformance removes the cached payload and two erasure shares and verifies reconstruction; three missing shares and corruption fail explicitly. This is actual local library execution, not a validator/custody network or an indefinite-retention claim. The independent atomic-file provider is an AtomStorage contract fixture, not a second DA network. The clean-source rebaseline excludes historical dirty storage-format and custody-pruning additions and reruns applicable tests.

Source: `adapters/detta/src/main.rs · test_contract.py`.

## 11 — Two independent substitutions, one design principle

The storage matrix has two implementations times two bindings. C1 is independently exercised without cognition using hostile declared-port wrappers. M3 attention replacement uses a separately implemented atomic-file provider; only DTO validation is shared with the SQLite implementation. Four controlled native cases hold exact task/evidence identities, policy, budgets and deadline fixed while selecting the provider in composition. Separate initial-preference cases show the selection effect. Both replacements persist actual state, but the file implementations remain classified fixtures rather than real DeTTa or a production attention service. This demonstrates same-profile replacement on fresh stores, not live migration.

Source: `m11-swap-demo.json · m3/final/comparison.json`.

## 12 — Private state has explicit owners and placement

The native plugin receives authenticated actor context and derives authority from operator configuration. Request parameters cannot select credentials, arbitrary scopes or private premise identities. Public parameters are generated seed, preference a/b and an absolute deadline. Privacy tests intercept shared bindings, populate shared stores and inspect native receipts/logs/state for canaries and private hashes. This is tested local placement under a trusted operator/host, not secrecy from administrators. Each journal has one owner and commits independently; there is no cross-owner SQL transaction.

Source: `cognition.py · inference_program/program.py`.

## 13 — Executable contracts make the inference step finite

The contracts use closed bounded DTOs and detach nested request inputs before authorization or foreign calls. A task binds P,Q,R,P⇒Q,Q⇒R to exact private references. Premise vectors record each belief's historical revision and support ID; the upstream knowledge revision of zero is only a local evaluation ID, not a global ledger. Derived support tags distinguish observation, two-local-premise revision and five-foreign-premise deduction. C2 local v3 is explicit and does not widen M2 v2. WorkBudget contains an absolute Unix-ms deadline, max_candidates, max_rule_applications and max_feedback_generation. Historical reads and recovered owner responses are validated against the exact request.

Source: `attention_contracts.py · cognition_contracts.py`.

## 14 — C1: one occurrence, one position in the story

The four illustrated event roles match the generated story. Each immutable event is referenced by an AtomRef; the episode head begins at zero and advances by one for accepted occurrences. A duplicate occurrence with the same semantic content returns its original receipt before a stale expected-head check, even under a new request key. Changed content or provenance for that occurrence conflicts. Distinct occurrences can have identical bytes. Payload persistence can precede episode commit and leave an orphan after death; replay recovers the same atom without inventing an acknowledged event. C1 exposes bounded reads, pending evidence and trusted acknowledgements, with no cognition dependency. No dynamic episode search or garbage collector is implemented.

Source: `episodes.py · tests/test_m2.py`.

## 15 — C2: admitting evidence and changing belief are separate

This slide describes preserved observation admission. M3 adds a separate derivation command with inherited evidence, described next. The first eligible explicit assessment initializes the aggregate. Later evidence is retained without automatic aggregation unless an exact pair assumption and guards permit revision. Unknown origins cannot initialize a justified numerical aggregate. A report without numerical assessment is model-inapplicable. The ledger retains observations, support records, immutable snapshots and exact decisions. A later authorized independence declaration may combine already admitted supports, without creating another observation. Exact successful replay returns the original historical decision even after later revisions; a new-key duplicate returns current state without adding weight. Retained-alternative is a pair outcome, so an already covered ancestor need not produce a new alternative list entry or revision. Coverage fields state the actual result.

Source: `beliefs.py · memory_types.py`.

## 16 — A derived conclusion inherits its evidence trail

The five foreign premises are not five independent observations of the output claim. local-admitted-supports/1 treats the deduction as one local support unit with its inherited evidence/root union. Logical derivation identity is independent of request/step IDs, deadlines and output CAS. A duplicate cannot gain another admission or causal feedback credit. A separately authorized independence assumption can request the unchanged guarded native revision of eligible supports. Derive → revise retains grounded ancestry; a cyclic subsequent deduction is refused. Claims remain heuristic and lineage-aware, not calibrated uncertainty or proven entailment.

Source: `derived_beliefs.py · pln_deduction.py`.

## 17 — One grounded rule reuses the actual native PLN

The unchanged Reachability dd56f3f implementation invokes PLN 4405956 Truth_Deduction on PeTTa ae66fa8 and SWI source 6977543, version 10.1.14. The exact runtime profile is fusion-petta-swi-10.1.14-deduction/1. No PLN.Derive, PLN.Query or task search is used. The Q>0.9999 branch and its assumptions remain upstream semantics and are tested. Kernel source checks and native subprocesses use the remaining absolute deadline. This pure component owns no belief, agenda or attention state. Source drift, malformed output and timeout are explicit refusals, with fault injections labelled in the native suite.

Source: `deduction-sources.json · integration/pln/test_deduction.py`.

## 18 — Native goldens check deduction and preserved revision

The M3 golden has five ordered premises and uses the actual native Truth_Deduction. Expected values are independent test oracles, not production mathematics. M2 revision goldens still pass in the M3 regression, including reversed unequal pairs. Native suites include actual computation plus explicitly injected malformed responses, timeouts, source-drift clones and authorization/CAS interleavings. Fifteen upstream guard-only tests use RecordingRuntime and are not counted as native numerical evaluation. Evidence_count remains null, and a derived conclusion never turns into a fresh independent observation.

Source: `test_deduction.py · preserved test_revision.py`.

## 19 — C3: a small, independent attention policy

The reference policy is frozen in its identity. Bounds are 16 targets, 16 advance steps per call, eight contexts, 512 causes per context, 1024 commands per owner and feedback generation three. Capacities refuse without silent eviction of acknowledged commands. Stimulus saturation is min(amount, Smax-current); total context budget is enforced atomically. Successful replay is checked before logical clock CAS under live authorization. Causal deduplication is independent of request identity; changing a causal body conflicts. Fresh feedback follows the target's current causal parent and next generation. metta-attention 3e1c8147 was inspected but not integrated because it couples STI/LTI/VLTI, wages and shared funds. C3 has no hidden dependency on AtomStorage, C1, C2, PLN or Hive.

Source: `attention.py · fixture_attention.py`.

## 20 — Attention replacement preserves the measured outcome

All four fresh cases use two tasks, five premises per task, ten generated observations, two episodes and twelve claim atoms. Held fixed: exact task/evidence refs, policy parameters, one-attempt/two-candidate budgets, absolute deadline and logical schedule. Separate preference cases exchange initial scores 20/10 and 10/20. Only composition chooses SQLite or the independently implemented file fixture; no consumer code changes. Every result records examined=2, reserved=1, completed=1, refused=0, unique admission=1 and feedback_applied=1, ending at rule-budget. The second candidate is counted before discovering the exhausted rule budget. Preparation takes about 11.5–11.8 seconds and is separate from the reported step time. Store sizes are 1,040,671 and 1,020,409 bytes respectively. These are one-run local measurements, not throughput or cognitive-quality evidence.

Source: `m3/final/comparison.json`.

## 21 — C4: reserve work durably before invoking the rule

C4 counts a candidate before resolving it, including unresolved or refused candidates. It commits reservation before dispatch and queries a prior C2 decision first during recovery. C2 persists semantic intent before evaluation, evaluates outside its commit transaction, then rechecks authority and output CAS. A killed pending attempt needs a new reserved slot/key; a committed decision is read back without evaluation. Logical derivation identity is distinct from transport request, controller step, attempt key, deadline and output CAS. Feedback is a fixed one-unit workflow signal tied to logical derivation identity, never a truth update. Absolute Unix-ms deadline survives restart; scheduling/file I/O remain cooperative, not hard real-time.

Source: `inference.py · deadlines.py`.

## 22 — Five crash boundaries, independent owner commits

Three native recovery methods cover ten actual SIGKILL cases: stimulus commit for both attention providers; reservation and kernel-return loss under budgets one and two; belief/feedback recovery for both providers. The real Hive suite adds five actual caller kills across the same boundaries. A one-slot loss conservatively exhausts the budget; a two-slot case may recover one logical admission after another physical calculation. Thus there is no claim of exactly one physical calculation per logical derivation. Committed admission and feedback are duplicate-safe. This is intact-local-file, same-host process restart, not reboot, power loss or distributed failover.

Source: `test_m3_recovery.py · test_m3_integration.py`.

## 23 — Authorization, replay and profiles remain live

Input records are copied before foreign calls and authorization so a malicious boundary cannot mutate the retained command. Recovered C2 and attention responses are checked against exact owner/request identities and semantics. Current principal, scope, method and descriptor permissions apply on every invocation. The assumption permission for revision remains separate. Native proposal calculation runs outside the owner commit transaction; final authorization and expected output revision are rechecked afterward. A concurrent attention clock change can leave pending feedback with CONFLICT. The controller records this state rather than silently rewriting the logical schedule. These are local trusted-authority guarantees, not a production identity system.

Source: `cognition.py · derived_beliefs.py · tests/test_m3.py`.

## 24 — One real Hive action reaches the entire private path

The real pinned Hive create_app, authenticated Programs dispatch, default Supervisor and native PeTTa run in the integration. The narrow sibling plugin uses native assessment role, action infer-generated, and trusted actor mapping. ASGI TestClient, identities, observations and operator assumptions are fixtures; the runtime, DeTTa and formula execution are actual providers. The plugin owns caller intent/receipt and invokes the private scenario; it owns no belief, STI or controller state. Eight native tests cover completion, duplicate-safe admission/feedback, restart, independent attention replacement, five real caller kills, authority and privacy. The diagram summarizes the call sequence; each owner commits independently. M1 fusion-inspect and M2 fusion-episode remain supported and rerun in regression.

Source: `inference_program/program.py · test_m3_integration.py`.

## 25 — The same one-attempt budget makes attention visible

This chart depicts the explicitly configured STI scores in the controlled scenarios, not a learned score or performance estimate. The comparison exercises both preferences with both providers; the real Hive tests separately exercise actual native action and replacement. A step freezes the ranked selection. Subsequent feedback affects a later step, not the order already accepted. C4 examines two candidates but reserves and executes only one attempt, so terminal reason is rule-budget. All four comparison cases recover identical receipts after reopening owners and invoke the native formula zero additional times on successful replay. Cognitive usefulness of the chosen conclusion is not measured.

Source: `m3/final/comparison.json · native Hive scenario`.

## 26 — Real providers and fixtures remain visibly separate

Native kernel/admission includes actual formula executions plus labelled malformed-response, timeout, source-drift and authorization/CAS fault cases. The fifteen upstream guard tests use RecordingRuntime. Both attention providers persist state, but the independent file provider retains fixture classification. Real Hive uses fixture identities, generated inputs and TestClient transport; its default Supervisor and Programs runtime are actual. Optional historical chain observations remain separate and are not a new M3 chain pass. Historical SWI 10.0.1, the full Hive suite and hard real-time behavior are unrun. The fresh build uses warm download caches, not reused native objects.

Source: `m3/manifest.json · m3-evidence.md`.

## 27 — Executed tests cover contracts, native calls and crashes

The complete baseline includes original 51 fixtures; aggregate 118; upstream DeTTa 62+38; Hive baseline 34 and unchanged M1.2 integration 13; M2 fixtures 16, guard fixtures 8, native revision 12, recovery/privacy 6, native Hive 7 and demo. M3 adds isolated attention five, contracts seven, upstream guard fixtures fifteen, mixed native kernel/admission thirteen, direct recovery three methods/ten cases, native Hive eight and comparison four cases. Do not sum repeated subsets as unique tests. Command durations and exact source/file hashes are machine-recorded. Supplemental empty-selection and zero-native-budget checks are fixtures at the same clean SHA. No integration test was rerun merely to rebuild this presentation.

Source: `m3/final/verification.json`.

## 28 — M3 gates: contracts and independent cognition

Statuses are read from the committed M3 manifest and match the final verifier. A pass applies to the gate's stated evidence, not to every possible provider or deployment. REPRO explicitly uses warm download caches but fresh build outputs. CHAIN is NOT_RUN and no required M3 prerequisite is blocked. Exact historical chain-source reproduction remains blocked by unavailable dirty inputs, a separate historical question. SCOPE excludes LTI, general search, new attention research, live migration and chain. All source, log and implementation hashes are retained for audit.

Source: `m3/manifest.json`.

## 29 — M3 gates: bounded operation and real integration

Statuses are read from the committed M3 manifest and match the final verifier. A pass applies to the gate's stated evidence, not to every possible provider or deployment. REPRO explicitly uses warm download caches but fresh build outputs. CHAIN is NOT_RUN and no required M3 prerequisite is blocked. Exact historical chain-source reproduction remains blocked by unavailable dirty inputs, a separate historical question. SCOPE excludes LTI, general search, new attention research, live migration and chain. All source, log and implementation hashes are retained for audit.

Source: `m3/manifest.json`.

## 30 — Reproducibility connects source, build and observed result

Requested ancestor f0cee248294a1fce42913782390e6c084025c67e; actual starting descendant 926882afb9ab9c7288bf663f96f9e1ca63dd8520; tested source 1af39794649d0ca95cd729c64868202368da1ec4; evidence-only descendant c4498ce3047f1283d3a4a3ae3d09b713e7dcf312. Build_m3.py wraps the byte-identical M2 recipe and adds the separately selected deduction configuration. All exercised upstream sources were clean at their pins. Historical M2 SWI binary identity differs from the fresh M3 build and is not silently equated. Exact hashes, versions, command arguments, durations and JUnit results are committed. Provider environment files can contain local configuration and are deliberately excluded from published evidence. This deck hashes its evidence inputs and audits the archive without modifying it.

Source: `m3/build.json · manifest.json · final/verification.json`.

## 31 — The limitations are part of the contract

The M3 admission path is durable and duplicate-safe, but generated C1 delivery intents remain available and pending because M3 v3 snapshots cannot be passed as M2 v2 acknowledgment DTOs. The original M2 relay/ack tests still pass under the original profile; no fabricated acknowledgment or silent widening was introduced. An absolute deadline can finish a bounded step with pending work, and a concurrent attention clock change is not implicitly retimed. No exactly-one physical calculation, hard real-time, reboot, administrator secrecy, distributed failover, live migration, production throughput or cognitive-quality claim is made. Origin/independence assertions remain operator assumptions. Specialist maintainer ownership is unassigned.

Source: `m3-evidence.md · compatibility and recovery limits`.

## 32 — Keep the evidence. Separate the decisions. Make the budget real.

Return to the executive summary. C1 remembers occurrences; C2 owns admitted beliefs and inherited evidence; the pure PLN kernel calculates; C3 ranks; C4 reserves and reconciles bounded work. The practical result is one actual native Hive inference action and a controlled independent attention replacement, preserving the M1/M2 application-neutral DA and authorization boundaries. The result is bounded local integration, not general reasoning or production deployment. All thirteen required gates pass, no supported prerequisite is blocked, and chain remains NOT_RUN. The deck and this work stop at M3.

Source: `M3 tested 1af3979 · evidence c4498ce`.

## 33 — Implementation map: responsibilities stay local

Paths are relative to fusion/ unless marked hive/, which is under integration/. ports.py declares the protocols; attention_contracts.py and cognition_contracts.py enforce the executable bounded schemas. Shared DTO validators are permitted in the independent fixture, shared owner transitions are not. C2 default M2 behavior remains via its original validators and profile; the derived owner selects fresh v3 behavior. The native plugin uses integration/m3_scenario.py and holds only caller intent and public receipt. No owner reaches into another owner's private SQL. Tests and exact source hashes are indexed in the M3 machine manifest.

Source: `architecture.md · ports.py`.

## 34 — Exact sources identify the verified native stack

Evidence commit c4498ce3047f1283d3a4a3ae3d09b713e7dcf312. Full inspected metta-attention revision: 3e1c8147dc17299d17ab34720334fc19277cb6a9, clean. Its coupled STI/LTI/VLTI, wages and funds are not silently adopted. Runtime profile: fusion-petta-swi-10.1.14-deduction/1; rule profile: grounded-five-premise-deduction/1; truth model: trueagi-pln-stv-finite-k1/v1. PLN library SHA-256 cdfb3f18bd7b336440fc7b4409209afddf0e64c41f17dee7eefc8f02718de433. Fresh SWI binary SHA-256 2a9b28b46f54f5eb0a8e1c79bb201c50b8acbbd5c180875ea8a5bca4e8617dfc. Native Python 3.12.12, Janus 1.5.3; fixture runner Python 3.11.14. All exercised source checkouts were clean. No upstream formula or runtime implementation was patched. Historical SWI 10.0.1 remains unrun.

Source: `m3/final/verification.json · build.json`.

## 35 — Profiles and bounds make compatibility explicit

Exact attention profile sti-additive-linear-decay/1: decay one, max targets sixteen, max advance sixteen, contexts eight, causes/context 512, commands/owner 1024 and feedback generation three. Kernel and C4 local interfaces are 2.0.0. Kernel runtime profile fusion-petta-swi-10.1.14-deduction/1 is separate from revision-only; M2 pln-revision-private/1 remains unchanged/default. The derived profile has three closed support forms and explicit local-admitted-supports/1 coverage. WorkBudget names candidates, physical rule opportunities, feedback generation and absolute Unix-ms deadline. Capacity exhaustion is explicit refusal, not eviction or automatic scope expansion. Interface version, algorithm profile, runtime identity, permissions and selected descriptor all matter.

Source: `contracts.md · cognition.py`.

## 36 — C1 acknowledgment compatibility remains an open seam

M3 does not solve this seam with a generic event bus, migration or a false success receipt. Generated C1 intents remain available and pending; direct M3 evidence/derivation admission and replay are nevertheless durable. The dashed bracket marks an incompatible response seam, not an executed call. The original M2 path retains its own supported DTO and acknowledgment behavior. A bounded step can also finish with unacknowledged work because an attempt was lost, a deadline elapsed or the attention clock advanced before feedback. Read the precise receipt counters and pending state instead of treating completion as global convergence.

Source: `m3-evidence.md · C1/C2 version boundary`.

## 37 — One native operation crosses the existing interfaces

All effects originate in the real native operation, not a renamed protocol demo. The caller first commits its original intent. AtomStorage persists generated bytes in actual DeTTa, then Messaging accepts a reference for the explicitly labelled fixture counterparty. DelegatedExecution accepts only inspect_atom under the original key and correlation. The caller records the accepted job. A separate real worker reads/persists through AtomStorage, then commits execution terminal state/outbox. Messaging accepts the completion in a separate transaction. The final arrow summarizes reconciliation: status /2 restores known correlation, poll and get verify the completion, caller acceptance commits, and a stable-key acknowledgement follows. This is not one distributed transaction.

Source: `program.py · execution.py · messaging.py`.

## 38 — Historical M1: one result reached an isolated chain

Preserve this historical result without promoting it into the new real-caller gate. The M1 chain JSON records pending, included with effect finality Pending, then finalized, at height 3 with no execution error, no rejection and cost 351 phlo. The committed digest belongs to the original protocol-peer result, not the generated native Hive result in M1.2. The M1 adapter used a registered approved digest, injected signer and durable signed intent against one isolated local node. That source had local changes and an untracked input. Exact historical reproduction remains blocked until those authorized bytes are supplied or a different clean revision is separately validated. No chain process or transaction was run during M1.2, M2, M3 or this presentation update. Finality does not establish indefinite off-chain availability.

Source: `evidence/chain-demo.json · M1 historical`.

## 39 — Reproduce the supported M3 gates

Linux build prerequisites and authorized SSH access to exact Hive/DeTTa sources are documented in the runbook; public HTTPS retrieves the pinned Reachability/PLN sources. New native objects, Python/Janus venv and DeTTa Cargo target are built in a fresh directory. Download caches may be warm. build_m3.py preserves the M2 build recipe and adds the explicit deduction profile. verify_m3.py runs M2 regression, isolated M3 fixtures, upstream guards, native deduction/admission, actual process kills, real native Hive and controlled substitution. The final record was executed from clean detached /tmp/fusion-m3-verify-1af3979. Do not publish broad local environment files. Deck generation is a separate documentation operation and does not rerun these gates.

Source: `runbook.md · build_m3.py · verify_m3.py`.

## 40 — Retry identities answer different questions

A derivation's logical ID excludes request/step identity, output CAS and deadline so a retry cannot manufacture new independent support. An attempt key freezes its exact semantic body and is evaluated at most once; a killed pending attempt consumes a physical reservation. Multiple physical calculations for one logical derivation remain possible under distinct reserved attempts. C2 commits its decision before C4 progress; C3 commits feedback before C4 acknowledgment. Recovery queries those owners rather than inferring success from a missing local reply. Feedback_applied counts acknowledged unique logical credits; feedback_duplicate records suppression on duplicate admission. Fixed feedback adds no truth evidence. The semantics distinguish bounded termination, successful admission and fully acknowledged work.

Source: `inference.py · derived_beliefs.py · attention.py`.
