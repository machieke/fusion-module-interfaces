# Omega × ASI — speaker notes

Implementation baseline: `d9e75773c34987d5791a9207190fcbf0a8c1fd7b`.
Evidence snapshot: `f0cee248294a1fce42913782390e6c084025c67e`.
Suggested delivery: 35–40 minutes for slides 1–30, with appendices for discussion.
Current claims use the recorded 16 October 2026 M2 evidence. The M1 chain observation is historical and separately labelled.

## 01 — Memory that remembers. Beliefs that can change. Boundaries that hold.

Open with the ELI16 executive summary, then the helicopter view and all fifteen module responsibilities before implementation details. M1.1 proved independent storage substitution and separate owner commits. M1.2 connected the real native Hive caller. M2 adds only C1 EpisodicMemory and C2 BeliefRevision, including actual guarded native PLN revision and one real Hive episode scenario. This is a bounded engineering integration, not a general reasoning agent or production system. Suggested delivery: 35–40 minutes through slide 30; eight appendices support questions. Current evidence is the final clean d9e7577 run, recorded in unchanged-code descendant f0cee24. Rebuilding this presentation does not rerun integrations.

Source: `M2 evidence f0cee24 · tested d9e7577`.

## 02 — ELI16: a notebook, an evidence ledger, a calculator

ELI16 means explain the idea to a technically curious sixteen-year-old without assuming distributed-systems or PLN vocabulary. The notebook is C1: what happened, in what order and with what provenance. The evidence ledger is C2: what was admitted, what contributes to the current aggregate and what remains an alternative. The calculator is the narrow RevisionMath dependency; it does not decide what to think about. The runtime is real, while the observations and independence declarations in the demonstration are generated fixtures. We killed actual processes and recovered from local files. That supports a local restart claim, not power-loss or distributed failover. Benefits are auditable history, duplicate-safe contributions and explicit provider choices.

Source: `m2-evidence.md · architecture.md`.

## 03 — ELI16: a copied report is not a new source

This sensor example is an explanatory analogy, not an additional experiment. The actual generated scenario uses the same distinctions: a report without a truth value, an explicit assessment, a copy with the original roots, and a contrary assessment. Admission preserves observations even when numerical aggregation is refused. Known common origins or overlapping evidence block additional weight despite an independence declaration. The operator's assertion of independence is an assumption, not proof; undisclosed copying is not detected. A separate generated independent pair exercises actual native revision.

Source: `C1 provenance · C2 support coverage`.

## 04 — Fifteen modules; four responsibility groups

The fifteen responsibility groups remain the same. C1 and C2 are now implemented private local modules; Relations, Search, the general PLN kernel, ECAN and inference control remain specifications. RevisionMath is a narrow dependency inside the C2 integration, not a claim to have implemented the general PLN kernel. Hive is a consumer. Provider, process and repository boundaries are independent. Blue means implemented local contracts, not production readiness. Authorization uses real native Hive authentication followed by a development Fusion policy. Finality has historical M1 evidence only; no M2 chain action occurred. Maintainer assignments remain unassigned.

Source: `architecture.md`.

## 05 — Data responsibilities: bytes → references → history

AtomStorage owns immutable scoped references and replay metadata, while DA only persists opaque payloads and generic coordinates. Relations and Search remain typed specifications. C1's local v2 operations are recordEpisode, appendEvent, readEpisode, readEvidence, pendingEvidence and trusted acknowledgeEvidence. findEpisodes is not advertised. C1 preserves committed episode-local order and admitted provenance; observed time is metadata. It can run without C2 or PLN and against an independently implemented AtomStorage fixture. Its event bytes are immutable atoms, while its episode head and delivery intents belong to C1.

Source: `architecture.md`.

## 06 — Cognitive responsibilities: history ≠ truth ≠ attention

C2 exclusively owns admitted observations/supports, immutable belief snapshots and exact semantic attempts. Its narrow RevisionMath port reuses the unchanged Reachability PLNAdapter.revise guards and the actual Truth_Revision formula. The general PLNKernel.applyRule contract remains unimplemented. Attention owns its own balances and logical time, with no hidden PLN or LLM dependency. Inference control would orchestrate bounded retrieval, selection and rules; it cannot own or mutate truth or attention behind their owners. No ECAN, inference-control or chain work is included in M2.

Source: `architecture.md`.

## 07 — Control responsibilities: move work, preserve authority

Messaging acceptance differs from delivery and acknowledgement. Execution accepts only inspect_atom and owns jobs plus its completion outbox; result atoms commit independently. The registry advertises descriptors, and the resolver matches consumer requirements. Neither grants permission. Finality records independent chain observations from historical M1; it is not a C1/C2 dependency. Native authentication supplies trusted actor context, while local Fusion policy determines current access. The M2 relay is a narrow delivery cursor between two owners, not a sixteenth general service, event bus or inference controller.

Source: `architecture.md`.

## 08 — Function dependencies: the exercised M2 path

Composition alone selects concrete providers and binds authenticated private authority. The generated scenario appends to C1, drains the relay and can submit an explicit pair assumption to C2. The relay invokes C1 pendingEvidence/acknowledgeEvidence and C2 readBelief/submitEvidence, storing exact attempts in its own journal. C2 resolves C1 EvidenceRefs through readEvidence and validates immutable records/claims through AtomStorage. C1 and C2 never read each other's SQL. C2 alone calls RevisionMath. C1's dependencies exclude C2, Hive, PLN, mailbox and execution. Registry/authority checks surround each invocation and the final C2 commit; omitted side arrows keep the function diagram readable. All illustrated arrows are exercised local calls, not promises of remote placement.

Source: `ports.py · private.py · evidence_relay.py`.

## 09 — Function dependencies: the preserved M1.2 path

Follow the real native dispatch into the thin plugin, which holds a caller-owned receipt and uses Subprocess/Peer through descriptor-bound validation. Direct storage, messaging and execution calls all cross the same authenticated boundary. Trusted composition supplies concrete owners; the plugin never constructs them or accesses their tables. Messaging.send validates the referenced bytes through caller-authorized AtomStorage.get; Execution.submit reads the input before accepting a new job. The worker calls declared AtomStorage get/create, then execution commits terminal state/outbox. CompletionDelivery.accept belongs to the mailbox owner and commits separately. Chain remains a separate, uninvoked adapter. This is a logical call map; it does not force one process per module.

Source: `program.py · ports.py · execution.py`.

## 10 — The DA boundary remains application-neutral

This unchanged DA boundary is exercised against a freshly fetched clean secured-contract-spaces revision 272888f264dd2dde18b574cabb53c266b0dac2ec. No Hive-specific schema is added to DeTTa. Application references and replay semantics belong above opaque DA. Conformance removes the cached payload and two erasure shares and verifies reconstruction; three missing shares and corruption fail explicitly. This is actual local library execution, not a validator/custody network or an indefinite-retention claim. The independent atomic-file provider is an AtomStorage contract fixture, not a second DA network. The clean-source rebaseline excludes historical dirty storage-format and custody-pruning additions and reruns applicable tests.

Source: `adapters/detta/src/main.rs · test_contract.py`.

## 11 — Replace the provider; keep the consumer’s contract

The four recorded M1.2 substitution workflows use protocol fixture callers, two AtomStorage implementations and two bindings. The independent file fixture neither inherits AtomOwner nor uses its atom table. The final M2 regression reruns the preserved matrix. M2 separately proves C1 against the independent file provider with cognition absent and hostile declared-port wrappers. Do not label the file fixture as another real DA provider. Wire remains 1.0.0 and immutable-bytes/1 remains unchanged. C1/C2 use local interface 2.0.0, implementation 0.2.0 and explicit private profiles. Descriptor hashes bind selection consistency, not provider honesty. These are fresh-store tests, not live namespace replacement or migration.

Source: `m11-swap-demo.json · memory_contracts.py`.

## 12 — Private history stays in a separate local composition

open_private resolves private descriptors and constructs separate local owners over actual DeTTa. It rejects overlap with configured shared roots. C1, C2, atoms and relay have distinct owner journals; the local composition grants one authenticated principal per private scope. Native Hive supplies actor and command context, and operator configuration maps actor/swarm to the private credential and scope. Canary tests inspect real shared stores/messages, intercepted outbound bindings, diagnostics, native responses and Hive traces. This is routing and placement isolation under a trusted host/operator, not encryption, administrator secrecy or remote privacy. Native authentication is real; the downstream Fusion policy remains the labelled local test policy.

Source: `private.py · episode_program/program.py`.

## 13 — Contract gaps are resolved before adding behavior

C1 profile is episode-local-sequence/2; C2 is pln-revision-private/1. Local interface version is 2.0.0, implementation 0.2.0. No new remote cognitive wire schema or M1 mutation route was added. EpisodeRef is stable while head tracks committed sequence; observed time is metadata. Evidence distinguishes report and explicit numerical assessment. Grounded claims use exact predicate, ordered string arguments and positive polarity plus exact context. A contrary low-strength assessment of the same claim differs from a negated claim. Admission admitted/duplicate is independent of initialized/revised/no-change/retained-alternative/model-inapplicable. Every attempt binds semantic input and selection. The separate belief.revision.assume permission authorizes pair assumptions; it is not an invented public method.

Source: `memory_types.py · memory_contracts.py · ADR 008/009`.

## 14 — C1: one occurrence, one position in the story

The four illustrated event roles match the generated story. Each immutable event is referenced by an AtomRef; the episode head begins at zero and advances by one for accepted occurrences. A duplicate occurrence with the same semantic content returns its original receipt before a stale expected-head check, even under a new request key. Changed content or provenance for that occurrence conflicts. Distinct occurrences can have identical bytes. Payload persistence can precede episode commit and leave an orphan after death; replay recovers the same atom without inventing an acknowledged event. C1 exposes bounded reads, pending evidence and trusted acknowledgements, with no cognition dependency. No dynamic episode search or garbage collector is implemented.

Source: `episodes.py · tests/test_m2.py`.

## 15 — C2: admitting evidence and changing belief are separate

The first eligible explicit assessment initializes the aggregate. Later evidence is retained without automatic aggregation unless an exact pair assumption and guards permit revision. Unknown origins cannot initialize a justified numerical aggregate. A report without numerical assessment is model-inapplicable. The ledger retains observations, support records, immutable snapshots and exact decisions. A later authorized independence declaration may combine already admitted supports, without creating another observation. Exact successful replay returns the original historical decision even after later revisions; a new-key duplicate returns current state without adding weight. Retained-alternative is a pair outcome, so an already covered ancestor need not produce a new alternative list entry or revision. Coverage fields state the actual result.

Source: `beliefs.py · memory_types.py`.

## 16 — Lineage blocks double counting, even after aggregation

This is a support-lineage diagram, not a general inference graph. Registered source origins are operator assumptions. Copies inherit the union of admitted provenance roots. The unchanged upstream guards require an exact independence declaration binding both supports, with matching model, claim, context and disjoint relevant lineage. Known shared origin or evidence overlap takes precedence over that declaration. Aggregation unions lineage; reintroducing an ancestor cannot increase weight. In the generated demo ancestor_outcome is retained-alternative, while the aggregate and contribution coverage remain unchanged. The model does not detect undisclosed copying or establish the truth of source registration.

Source: `PLNAdapter.revise · beliefs.py`.

## 17 — Native revision reuses the guarded implementation

Reachability is pinned at dd56f3f053ed90239de5377021a7d3b3fbf424ac; PLN at 4405956947c4b53c7ff01bd565aa3b114bc970a1; PeTTa at ae66fa8e41dcd5539d614706bd4e5cfb34f9608d. C2 loads the unchanged PLNAdapter.revise and its truth/support guards, injecting only a revision-specific native runner. The runtime profile is fusion-petta-swi-10.1.14-revision/1, with model trueagi-pln-stv-finite-k1/v1. The upstream historical 10.0.1 checks/locks were not weakened. Source and binary drift, missing binaries, invalid outputs and timeouts are refused. This is not a general PLN rule kernel or an AdmissionService/AtomSpace projection. C2 rechecks live authority and expected revision after computation before committing.

Source: `pln_revision.py · integration/pln/sources.json`.

## 18 — Independent goldens check the actual native result

These are independent expected-value oracles for actual Truth_Revision through native PeTTa/SWI, not replacement production arithmetic. The valid-result absolute tolerance is 1e-12. Decimal-string inputs must pass both decimal and float64 domain checks; a value that rounds confidence to one is refused, not clamped. Nonfinite values, wrong model/context/claim, zero total weight and malformed native output fail explicitly. evidence_count remains null. The golden tests include equal, unequal and swapped input order. Malformed/empty/multiple output tests are labelled injected fixtures inside the broader native-provider suite. These computations do not validate the external truth or statistical independence of observations.

Source: `integration/pln/test_revision.py · final/demo.json`.

## 19 — Four crash gaps across independent commits

These are actual OS-process SIGKILL tests with intact persistent local files. Atom persistence, C1 append+intent, C2 snapshot+decision and C1 acknowledgement are independent commits. The relay owns a separate exact request/cursor record, never foreign SQL. C2 saves its full semantic attempt before calculation, then rechecks authority and expected revision before final commit. Formula work may repeat after a crash, but logical evidence weight is duplicate-safe. Tests also exercise a two-process CAS race, retrying the unchanged key/occurrence/head through transient contention until a genuine final conflict. None of this proves power-loss durability, distributed failover or exactly-once physical evaluation.

Source: `test_recovery.py · test_m2_integration.py`.

## 20 — Authority, replay and compatibility stay live

Private authority validates complete descriptor selection and current principal, scope and method on every operation, including cached replay. The separate belief.revision.assume permission governs explicit pair assumptions. C2 also checks authority and expected revision after native calculation. Full acknowledgement-body fingerprints prevent substituting a different decision behind the same acknowledgement identity. Inputs are detached from caller mutation. Same-key semantic changes conflict, including expected revision and runtime selection. Genuine CAS conflicts require a new attempt identity; retryable NOT_AVAILABLE preserves the exact attempt. The relay is bounded to three CAS retries per drain and at most 32 attempts per delivery. It is not a general retry scheduler or inference controller.

Source: `private.py · beliefs.py · evidence_relay.py`.

## 21 — One actual Hive episode reaches private C1 and C2

The verified schematics pin actual Hive 34b0fb32ab3806e5609fc89bb7535518a35e1aea. Native startup is python -m hive; the integration driver uses the actual create_app, default Supervisor, PeTTa and native authenticated Programs dispatch in real processes. ASGI TestClient is only the transport. The sibling fusion-episode plugin derives authority from trusted actor context and operator principal/swarm mapping; it does not expose arbitrary observations over the shared wire. The original fusion-inspect plugin and thirteen tests remain unchanged. The seven M2 cases cover completion, exact replay/restart, all four SIGKILL boundaries, live revocation and private result isolation. Generated observations and assumptions remain fixtures even when the caller and providers are real.

Source: `episode_program/program.py · test_m2_integration.py`.

## 22 — The recorded story keeps copies and disagreement

This slide reads the committed CLI demo record, whose own classification is: generated fixture, real DeTTa and native PLN; this CLI is not the Hive gate. It is not relabelled as a native Hive trace. The real Hive test suite independently exercises the same integration/m2_scenario.py through native authentication and Programs dispatch. The story contains 4 events and 2 retained alternatives. A separate pair of 2 generated independent observations produces strength 0.5, confidence 0.6666666666666666, evidence_count null. Exact restart result equality is True. The ancestor outcome is retained-alternative; no extra observation or numerical contribution is created. No real-world source reliability is inferred from generated assessments.

Source: `m2/final/demo.json · test_m2_integration.py`.

## 23 — M1.2 remains a working, separate integration

The M2 verifier explicitly compares the preserved source files against requested M1.2 evidence ancestor 4ee5cbe8b84689a5d2432530083738b263142f90. It reruns the original thirteen real native Hive tests, the selected native baseline, upstream DeTTa and the full conformance suite. ports.py grows new local protocols, while the preserved original wire schemas and bindings remain unchanged. All six built provider source trees are clean after testing, and supplied sibling sources remain unchanged. No ECAN, inference control, general PLN kernel, live migration or chain action is added.

Source: `source-preservation.json · final/m1_2/verification.json`.

## 24 — Real providers and fixtures answer different questions

Do not flatten the system into one real/fixture label. The runtime/provider gates execute actual pinned source. The scenario data, source-origin registrations and independence declarations are generated assumptions. The independent file provider proves the AtomStorage contract but is not real DeTTa. Eight upstream guard tests use RecordingRuntime fixtures; malformed output tests inject fixtures into an otherwise native suite. The upstream Hive baseline uses its fixture process driver, while the actual integration tests use the real default Supervisor. ASGI TestClient is transport, not a fake native application. The historical chain observation remains separate, and the M2 chain gate is NOT_RUN.

Source: `m2/manifest.json · final/verification.json`.

## 25 — Executed suites cover distinct layers of the claim

The final comprehensive run is recorded from clean detached d9e75773c34987d5791a9207190fcbf0a8c1fd7b with PYTHONPATH forced to that checkout. The 106-case matrix includes the original 90 tests plus sixteen M2 fixtures; the fifty-one original fixtures and sixteen M2 fixtures are also run separately for isolation. Do not sum those repeated runs as unique tests. DeTTa has 62 DA and 38 storage tests. The 34 selected Hive baseline tests retain their upstream process-driver fixture; thirteen unchanged M1.2 tests and seven M2 tests exercise the real caller. Twelve native revision tests include real computations and deliberately injected malformed responses. Six recovery/privacy tests use actual local providers and SIGKILL. The CLI demo also passed with exact reopen results. Failed development runs remain in the evidence archive and are not counted as passing gates.

Source: `m2/final/verification.json · final/m1_2/verification.json`.

## 26 — M2 gates: contracts, memory and native revision

Gate statuses are read from the committed M2 manifest, not inferred from slide content. BASELINE includes source preservation and regression. CONTRACTS includes local v2 protocol fidelity and response validation. C1 combines sequence/CAS/replay with real DeTTa persistence. C1_INDEPENDENT is a fixture conformance gate, deliberately independent of the real math provider. C2_GUARDS includes eight unchanged upstream RecordingRuntime tests, local guards and native-suite refusal cases. C2_NATIVE includes actual native formula computations plus source/runtime compatibility checks. Fixture gate success is not relabelled as native numerical execution.

Source: `m2/manifest.json · m2-evidence.md`.

## 27 — M2 gates: privacy, recovery, Hive and reproducibility

PRIVACY proves canary isolation over the tested local routes under the trusted-host threat model. RECOVERY proves process restart, not power loss or distributed failover. HIVE_M2 uses actual native dispatch and the real private provider path. REPRO uses fresh native objects, venv and DeTTa Cargo target, while Git/Python/Cargo downloads may use warm caches. SCOPE limits the change to C1/C2 and preserves named original source files. CHAIN is explicitly NOT_RUN. No required M2 prerequisite remains blocked. A different historical question—exact reproduction of the dirty M1 F1R3 source state—remains blocked by unavailable source inputs and is documented separately in the appendix.

Source: `m2/manifest.json · source-preservation.json`.

## 28 — Reproducibility binds source, build and execution

The fresh build took 337.325 seconds, including 139.055 seconds for native SWI/Janus/Hive. Its native-build record names 6452fa7 because provider construction began before the M2 commits; the native recipe/locks and compiled DeTTa adapter source were unchanged, and the recipe hash matches the committed M2 build script. Final Fusion verification separately used clean detached d9e75773c34987d5791a9207190fcbf0a8c1fd7b. Exact source hashes, built binary digest, commands, logs and provider-cleanliness checks remain recorded. All six provider trees remained clean. No native target, venv or compiled object was copied from the original workspace. Globally empty-cache builds are NOT_RUN. The binary digest identifies the selected built runtime, not cross-host bit reproducibility. This deck updates presentation artifacts only and does not rerun native gates.

Source: `m2/fresh-build.json · final/verification.json`.

## 29 — The guarantees stop at the tested boundary

The local profiles are deliberately bounded: 256 events per episode, pages/pending batches of sixteen, 32 observations per belief, at most 64 support records, and three CAS retries per drain. Owner history is retained without garbage collection or a total disk quota. Authority is a development local policy, not production identity management. Explicit model semantics and exact runtime selection are required. Native caller evidence is for the chosen Programs route and selected tests, not the full Hive suite, LLM operation or arbitrary application behavior. Future Relations/Search, ECAN, inference control and general PLN rules remain outside implemented scope. Chain and live migration are unrun. No new runtime guarantee is created by rebuilding this presentation.

Source: `m2-evidence.md · manifest.json`.

## 30 — Remember the event. Keep the disagreement. Justify the update.

Return to the executive summary: the notebook preserves occurrences, the evidence ledger preserves disagreement and lineage, and the pinned calculator runs only when the explicit pair qualifies. The practical result is a private local memory/revision slice exercised by a real Hive caller, with duplicate-safe evidence and recovery across independent commits. It is not yet an autonomous reasoning loop or production deployment. All required M2 gates passed; fixtures, real providers, historical blocked source reproduction and unrun extensions retain their labels. The work stops at M2.

Source: `M2 tested d9e7577 · evidence f0cee24`.

## 31 — Implementation map: each owner has a small surface

Paths without prefixes are under fusion/. The adapter is fusion/adapters/pln_revision.py; the plugin is integration/hive/episode_program/. Source/build scripts are scripts/build_m2.py, verify_m2.py and m2_demo.py. Fixture tests live in tests/test_m2.py and tests/m2_support.py. Native and recovery tests live in integration/pln/; real Hive tests in integration/hive/test_m2_integration.py. C1 tables own episodes/events/mutations/deliveries, C2 owns snapshots/attempts, and the relay owns only exact handoff progress. Immutable payload and event bytes remain in private AtomStorage over separate local DeTTa. No upstream source is patched.

Source: `m2-evidence.md · architecture.md`.

## 32 — Exact sources include the explicit runtime rebaseline

Requested ancestor: 4ee5cbe8b84689a5d2432530083738b263142f90. Starting checkout: 6452fa725be5a688f9d5ad8f77955579df2f95ab, presentation/docs-only descendant. Final clean tested Fusion: d9e75773c34987d5791a9207190fcbf0a8c1fd7b; evidence snapshot: f0cee248294a1fce42913782390e6c084025c67e. Schematics: 4af00db4e395375484dd48d0b9068a59afcf01f8; Hive: 34b0fb32ab3806e5609fc89bb7535518a35e1aea; DeTTa: 272888f264dd2dde18b574cabb53c266b0dac2ec; Reachability: dd56f3f053ed90239de5377021a7d3b3fbf424ac; PLN: 4405956947c4b53c7ff01bd565aa3b114bc970a1; PeTTa: ae66fa8e41dcd5539d614706bd4e5cfb34f9608d; SWI source: 69775434c8226897626b226aefcc8266499f1e2e. Formula SHA-256: cdfb3f18bd7b336440fc7b4409209afddf0e64c41f17dee7eefc8f02718de433. Built SWI SHA-256: f1e29950cb5ccfe3904833db5c08409bc2a1c7c999f1e1933719a7c3e03ab20f. Runtime profile: fusion-petta-swi-10.1.14-revision/1; model: trueagi-pln-stv-finite-k1/v1. Python 3.12.12, Janus 1.5.3; fixture orchestration Python 3.11.14. Native source trees remained clean after the recorded final run. The supplied brief's content hash and fetch URL remain in the manifest.

Source: `final/verification.json · integration/pln/sources.json`.

## 33 — Profiles and bounds are part of compatibility

AtomStorage remains immutable-bytes/1 with original interface 1.0; M2 selects a separate private-local-only descriptor. C1/C2 local interface 2.0.0 is not a silent change to the existing M1 wire 1.0.0. Ingestion is explicit-generated-assessment/1, keeping generated assessment policy outside the owners. Numerical input uses finite decimal strings validated again at the float64 boundary; strength is in [0,1], confidence in [0,1), and evidence_count is null. The bounds listed are semantic contract limits. History is retained without garbage collection or a total storage quota. Live migration and generic query/search are not implemented.

Source: `memory_contracts.py · contracts.md`.

## 34 — Future cognition remains a set of review obligations

This is a proposed future dependency map, not evidence of an executed cognitive loop. Inference control would use Search, Attention, C2 and a general pure PLN kernel through explicit ports. Attention owns its own budgets/balances and logical time, without a required PLN or LLM dependency. The general kernel returns proposals over immutable premises. Inference control owns only step receipts/checkpoints, not truth or attention state. Relations/Search, ECAN, general rules and inference control remain future contracts with model/policy and conformance obligations. M2's narrow RevisionMath provider is distinct from applyRule. No new work in these modules was undertaken.

Source: `ports.py · architecture.md`.

## 35 — One native operation crosses the existing interfaces

All effects originate in the real native operation, not a renamed protocol demo. The caller first commits its original intent. AtomStorage persists generated bytes in actual DeTTa, then Messaging accepts a reference for the explicitly labelled fixture counterparty. DelegatedExecution accepts only inspect_atom under the original key and correlation. The caller records the accepted job. A separate real worker reads/persists through AtomStorage, then commits execution terminal state/outbox. Messaging accepts the completion in a separate transaction. The final arrow summarizes the reconciliation expanded on the next slides: status /2 restores known correlation, poll and get verify the completion, caller acceptance commits, and a stable-key acknowledgement follows. This is not one distributed transaction.

Source: `program.py · execution.py · messaging.py`.

## 36 — Historical M1: one result reached an isolated chain

Preserve this historical result without promoting it into the new real-caller gate. The M1 chain JSON records pending, included with effect finality Pending, then finalized, at height 3 with no execution error, no rejection and cost 351 phlo. The committed digest belongs to the original protocol-peer result, not the generated native Hive result in M1.2. The M1 adapter used a registered approved digest, injected signer and durable signed intent against one isolated local node. That source had local changes and an untracked input. Exact historical reproduction remains blocked until those authorized bytes are supplied or a different clean revision is separately validated. No chain process or transaction was run during M1.2, M2 or this presentation update. Finality does not establish indefinite off-chain availability.

Source: `evidence/chain-demo.json · M1 historical`.

## 37 — Reproduce the supported M2 gates

Use a fresh destination; the build refuses to overwrite existing work. Authorized SSH access to the exact Hive and DeTTa sources is required. Public HTTPS retrieves the pinned Reachability/PLN inputs. The native build uses pinned PeTTa/SWI, hashed Python dependencies and new Janus objects; DeTTa is compiled into a fresh target. Git/Python/Cargo download caches may be warm. scripts/verify_m2.py runs the preserved M1.2 verifier and then isolated M2 fixtures, eight upstream revision guard tests, native revision, recovery/privacy, native Hive and a deterministic CLI demo. The exact final evidence run used a clean detached d9e7577 checkout and recorded commands/output paths. Failed development runs remain preserved. Building the presentation is a separate operation and never reruns or overwrites these integration records.

Source: `runbook.md · build_m2.py · verify_m2.py`.

## 38 — Retry decisions preserve meaning across owners

Exact successful C2 replay returns the original decision and historical snapshot even after later revisions. New-key duplicate evidence reads current state without adding weight. The relay saves exact requests and runtime selection in its own journal; a transient provider failure never acknowledges the intent. After a genuine CAS conflict it reconciles and allocates a new semantic attempt under bounded retry limits. C1 acknowledgement is a separate commit and validates the complete decision body. The receipt is trusted local evidence, not a remote proof. The physical formula may execute more than once; only the logical admission and contribution are duplicate-safe. Retained-alternative describes the pair decision, with actual coverage and unaggregated lists controlling interpretation.

Source: `episodes.py · beliefs.py · evidence_relay.py`.
