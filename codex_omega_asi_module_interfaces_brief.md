# Codex brief: Omega Hive ↔ ASI:chain module-interface architecture

**Prepared:** 16 October 2026  
**Requested by:** Kevin Machiels  
**Status:** Proposed implementation handoff grounded in the two 15 October meeting transcripts. This is Kevin’s starting architecture for review, not an agreed final Hyperon/AtomSpace specification.  
**Immediate scope:** Architecture, versioned contracts, conformance tests, and one bounded storage/communication/execution prototype. Do not build the entire cognitive stack in the first run.

## 1. Mission and first-run boundary

Define the smallest useful, single-responsibility module interfaces through which Omega Hive can use shared storage, agent communication, and delegated execution, without depending on a particular Omega version or deployment backend. Prototype implementations against the existing application-neutral data-availability (DA) layer and/or ASI:chain, according to what actually works in the inspected repositories.

Extend the design—not the first implementation milestone—with a clear progression from minimal AtomSpace to episodic memory, bounded PLN revision, ECAN short-term attention, and attention-guided PLN inference. Keep long-term promotion and more elaborate orchestration later.

**Complete milestones M0 and M1 in this run, then stop.** Deliver design artifacts and working evidence, not just interface stubs. Attempt a real integration using the available DA/chain code. A local conformance harness is useful but must not be reported as Omega, DA, or chain integration when those integrations have not actually run. When an external dependency is unavailable, complete the independent work, preserve an executable adapter contract, and report the exact blocked integration gate.

Do not expand into a new agent framework, a new blockchain, a new DA implementation, a replacement AtomSpace, or a wholesale Omega rewrite.

## 2. Evidence, decisions, and unresolved choices

### Source keys

- **S1:** `Kevin _ Kabir - 2026_10_15 10_00 CEST - Notes by Gemini.rtf`, transcript headed “Kevin / Kabir”.
- **S2:** `AGI Benchmarks - 2026_10_15 12_34 EDT - Notes by Gemini.rtf`, transcript headed “AGI Benchmarks”.

References below use meeting elapsed timestamps, not wall-clock times. Both transcripts are automatically generated and contain terminology errors.

### Source-derived direction

| Direction | Source and status |
|---|---|
| Define interfaces by function; begin with practical service contracts rather than waiting for full formal verification. | S1 00:09:06–00:13:36; 00:34:16–00:38:58. Kevin/Kabir direction. |
| Interfaces should support interchangeable implementations, versioning, and independent evolution of Omega variants. | S1 00:35:43–00:38:58; 01:04:49–01:07:39. Kevin/Kabir direction. |
| Demonstrate modules implementing these interfaces on chain, using a working alternative substrate where necessary. | S1 00:16:54–00:18:47; 00:57:38; 01:06:09–01:07:39. Kevin/Kabir integration direction. |
| Cover inter-agent communication, shared memory, delegated execution, delegated consensus, and delegated storage. | S2 00:04:11–00:05:40. Kevin’s proposed interface scope. |
| Start with referencable storage; then episodic provenance and revision; then attention and inference; defer more complex LTI/promotion control. | S2 00:09:07–00:11:14; 00:20:56–00:23:49. Kevin’s staged proposal, positively received but not a finalized collective specification. |
| Explicitly assign state ownership: other modules request attention changes rather than directly editing ECAN state. | S2 00:11:14–00:12:40. Clarified in discussion. |
| Establish terminology, acceptance criteria, integration tests, and module-specialist responsibility. | S2 00:12:40–00:17:02; 01:08:13; 01:11:12–01:13:00. Discussed engineering needs. |

**Do not turn disputed discussion into a decision.** The meetings did not select a final AtomSpace representation, atomization strategy, PLN numerical model, ECAN algorithm, universal ontology, or exact Omega repository/release. John’s Hive was discussed as an initial target, but Kabir explicitly emphasized version-independent contracts. The relationship and naming of subsequent Omega variants were not settled across participants. S1 01:03:33–01:07:39; S2 00:25:20–00:30:36 and 01:04:03–01:13:00.

The requested integration demonstration was discussed for **20 November 2026**. Treat that as meeting context, not a reason to silently remove correctness requirements or invent a fixed full-product scope. S1 00:12:10 and 00:46:30–00:48:05; S2 01:02:40.

### Status of the remainder of this brief

The concrete boundaries, method names, schemas, milestone gates, and tests below are **proposed v0 engineering choices** that operationalize the discussions. Reconcile names and reusable contracts with repository evidence before implementing them. Do not present them as verbatim meeting decisions.

Two retained constraints from Kevin’s earlier project work also apply, separately from S1/S2: preserve private, full episodic details client-side; and prefer live, server-side capability enforcement using the authenticated caller and registered requirements, rather than routinely making callers supply capability bundles. Share only deliberately authorized projections/artifacts. Do not put private episodic payloads on chain, including encrypted copies.

## 3. Inspect and reuse before designing replacements

Inspect the active workspace, its `AGENTS.md`, remotes, dependency manifests, existing interfaces, tests, and documentation. Record exact paths and commit identifiers for every implementation used. Do not assume remembered repository behavior is current.

Known candidate repositories from prior project context, **not verified by this brief**:

| Candidate | What to inspect |
|---|---|
| Current Omega/Hive workspace; any supplied next-generation Omega workspace | Channel, memory, search, tool/transformation, model/reasoner, and registry interfaces; actual integration entry points. The transcripts do not identify a definitive repository or branch. |
| `machieke/secured-contract-spaces` | Existing application-neutral DA, guarded state, service dispatch, authorization, receipts, and event facilities. |
| `F1R3FLY-io/f1r3node-rust` | Actual deployment, execution, event, state-query, and finality APIs available at the inspected commit. |
| `machieke/reachability-atomspace-prototype` | Reusable AtomSpace, episodic/lifecycle, retrieval, PLN, and attention-facing interfaces. Preserve existing authoritative-store/projection boundaries. |

Locate Kevin’s earlier Omega interface/type registry if it is available; wrap or evolve it rather than inventing a parallel registry. S1 00:10:11–00:15:01.

Produce a compact discovery matrix: `component → source path@commit → existing contract → authoritative state → reusable implementation → missing seam → evidence/test`. Mark inaccessible repositories explicitly. Do not silently clone unrelated alternatives or choose a provider merely because its name appeared in the transcript.

**Keep the DA layer application-neutral.** Omega IDs, PLN rules, truth-value fields, ECAN values, and cognitive policies belong above the generic DA API. Place application adapters outside the DA core.

## 4. Architecture rules

A module is the smallest useful unit with one clear responsibility and one owner for each category of mutable state. It is not necessarily a process, container, repository, or network service. Modules may be co-located; cross-boundary calls still use the declared contract. Avoid distributing every function merely to make the design look modular.

Separate four concepts:

1. **Interface:** operations, types, effects, errors, and behavioral guarantees.
2. **Implementation:** a provider that satisfies a particular interface/profile version.
3. **Transport:** in-process calls, messages, or an inspected chain/client protocol.
4. **Placement:** local client, authorized shared service/DA, or ASI:chain.

“Service contract” here does not mean “blockchain smart contract.” A smart contract can be one implementation. The interface must not force every module or every read/write onto chain.

Logical ownership does not require a globally single server: replicas may implement an owner’s contract, provided its concurrency and consistency guarantees hold.

Core domain modules must not import backend SDKs or concrete provider implementations. Constructors/composition supply declared ports. Keep interface-definition dependencies acyclic; runtime messages may form feedback loops through explicit events and commands.

A replaceable implementation must preserve behavior, not merely method signatures. Keep a shared interface identifier only when the promised semantics really match. Differing numerical models, query dialects, or guarantees require a named profile, explicit conversion, or a different contract version—not hidden coercion.

## 5. Logical module catalogue and state ownership

Names below are descriptive placeholders pending the repository/glossary pass. Several ports may live in one package while retaining separate ownership and dependency boundaries.

### 5.1 Cognitive/data modules

| Module/port | Sole responsibility and minimal operations | Dependencies and exclusions |
|---|---|---|
| **DA storage** | Persist and retrieve opaque, scoped payloads: `put`, `get`, `availability`. Return an accurately described storage receipt. | No cognitive dependency. No inference, atom semantics, attention, or application-specific chain workflow. Backend-internal durability/consensus is allowed. Reuse existing DA. |
| **Minimal AtomSpace / AtomStorage** | Give stored units stable, scoped references and retrievable typed envelopes: `create`, `get`, `getMany`. | Depends on a storage port. Stores data without understanding it. No parser, truth revision, ECAN, semantic search, or mandatory ontology. |
| **Relations** | Represent explicit structural relationships/hyperedges: `assertRelation`, `getRelation`, `outgoing`, `incoming` where supported. | References atoms. Structural links are not beliefs and carry no authoritative truth/attention fields. Persisted link records can themselves be ordinary atoms. |
| **Search/index projection** | Find references by a declared query profile: `query`; expose the projection watermark/version. | Reads stored records/events. An index is not automatically the authoritative store. Symbolic and embedding search have distinct capabilities unless semantics genuinely match. |
| **Episodic memory** | Record ordered observations, actions, results, and provenance: `recordEpisode`, `appendEvent`, `readEpisode`, `findEpisodes`. | Uses atoms/relations and optional search. Does not directly update truth or attention. Emits evidence records for other owners. |
| **Belief revision** | Maintain authoritative belief/evidence state and apply a specified revision policy: `submitEvidence`, `readBelief`. | A narrow PLN-revision implementation may implement this port. No inference search or attention allocation. Evidence lineage and model version belong in its output. |
| **PLN inference kernel** | Apply an identified rule to explicit premise snapshots: `applyRule`; enumerate supported rule profiles. | Reads typed premises, returns a proposed conclusion and derivation. Does not choose its own agenda, mutate episodes, or write ECAN values. |
| **ECAN / attention** | Own attention allocation and decay: `submitStimulus`, `readAttention`, `select`, `advance`. Start with STI only. | Operates on opaque target references and declared feedback. No hard dependency on PLN, an LLM, or one AtomSpace implementation. |
| **Inference control** | Select and schedule bounded reasoning work: `step` with explicit work limits. | Composes retrieval, belief snapshots, ECAN, and PLN ports. Does not reimplement their mathematics or own their state. Later promotion/recall control is separate. |

This split is a proposal to make the staged implementation possible, not a claim that the community has agreed to a new definition of AtomSpace. In particular, preserve Kevin’s storage-first boundary while allowing typed relationship records above it. S2 00:09:07–00:11:14; 00:20:56–00:25:20; 01:13:00.

**Write-authority rule:** episodic memory owns episode history; belief revision owns truth/evidence aggregates; ECAN owns attention; the execution service owns job status. PLN or ingestion may *request* attention changes through ECAN. They may not edit its storage directly. A common database is not permission to bypass an owner.

### 5.2 Integration/control ports

| Port | Minimal responsibility | First-run treatment |
|---|---|---|
| **Agent messaging/channel** | Scoped message exchange, delivery acknowledgement, and explicit correlation/reply routes. | Implement a small transport adapter; do not invent a new messaging network. |
| **Delegated execution** | Submit a named operation, expose job status/result, and deliver correlated completion: `submit`, `status`, `result`. | Implement one allowlisted deterministic fixture operation across a real process/message boundary. |
| **Registry** | Describe and resolve interface implementations, versions, profiles, and advertised capabilities. | Prefer an existing registry; static/local registration is acceptable for the harness. It is not chain registration. |
| **Compatibility resolver** | Decide whether offered versions/profiles meet caller requirements. | One shared, small resolver; not a bespoke negotiation protocol embedded independently in every module. |
| **Consensus/finality** | Submit an eligible commitment/decision and report chain inclusion/finality with evidence. | Specify the boundary; implement only the smallest supported chain adapter. Do not implement a new consensus algorithm. |
| **Authorization enforcement** | Enforce the current caller’s access to scopes, methods, and owner-controlled state. | Reuse the existing enforcement seam; an explicit local test policy is acceptable only inside the harness. |

Delegated consensus is distinct from execution success, message delivery, and an agent’s confidence in a belief. Never conflate these outcomes.

Keep existing Omega memory, search, model/reasoner, and tool/transformation APIs as compatibility facades/adapters where useful. Do not replace a rich existing API with one universal `execute(anything)` escape hatch. Motivation can remain a clearly labelled fixed fixture; no working motivation system is required. S2 00:00:10–00:02:28.

## 6. Minimal contract package

For every interface, specify: responsibility; operations and typed inputs/outputs; required and optional dependencies; state ownership; preconditions/postconditions; events and ordering; idempotency; authorization; error/retry semantics; concurrency behavior; version/profile compatibility; and conformance tests.

Use the repository’s existing type/schema tooling. Provide a language-neutral wire representation for remote boundaries and readable method definitions. Do not adopt a new framework solely to generate boilerplate. Make transport bindings explicit; an HTTP schema is not, by itself, an asynchronous protocol.

### Common value types

- `InterfaceRef`: stable identifier plus semantic version. Track provider implementation version separately.
- `ScopeRef`: authorization/isolation boundary; never equate a public identifier with permission.
- `AtomRef` / `PayloadRef`: opaque scoped identifiers, optionally with an integrity digest and immutable revision. Do not require public content hashes for private records.
- `EvidenceRef`: unique occurrence, source, episode/sequence, target claim, evidence relationship, and provenance. Identical bytes are not automatically the same observation.
- `RuleProfileRef` / `PolicyProfileRef`: versioned algorithms, numerical representations, and applicable preconditions.
- `Receipt`: explicit outcome/evidence for one operation, not a universal “success” flag.

Resolve atom identity and canonical serialization explicitly in an ADR. Prefer existing conventions. For the initial fixture, immutable atoms plus new revisions/relations are sufficient; defer deletion/garbage collection and cross-scope merging. Exact serialization normalization is not semantic canonicalization. Never merge claims merely because an LLM says they resemble each other.

Relation schemas must state edge direction, ordered versus unordered roles, arity, and reference-validity rules. Do not silently sort arguments when order carries meaning.

Provider descriptors must declare supported operations/profiles, payload limits, privacy/access scope, durability/consistency guarantees, execution determinism, and any measured service-level characteristics. Consumers state required guarantees and budgets; the resolver must reject unsuitable providers rather than select by name alone. Keep advertised capabilities distinct from verified evidence. Performance targets remain unvalidated until measured.

### Invocation/message envelope

At minimum carry `message_id`, `interface_ref`, `operation`, `scope_ref`, an idempotency key for mutating operations, and a typed body or payload reference. Async requests additionally carry correlation and an authorized reply route; propagate causation and timeout/deadline information where supported.

The authenticated principal comes from the trusted transport/enforcement context, not from an unverified `sender` field. Do not routinely require callers to construct authorization-capability bundles.

Use typed errors such as `UNSUPPORTED_VERSION`, `UNSUPPORTED_PROFILE`, `UNSUPPORTED_OPERATION`, `INVALID_ARGUMENT`, `UNAUTHORIZED`, `NOT_FOUND`, `CONFLICT`, `NOT_AVAILABLE`, `OVERLOADED`, `DEADLINE_EXCEEDED`, and `INTERNAL`. Distinguish temporary unavailability from an absent record; do not convert failures into empty recall results.

### Versioning and stronger guarantees

Use semantic versions with explicit same-major compatibility rules and contract tests. Select only versions/profiles the consumer supports. Additive optional fields may be forward-compatible; unknown required features, ownership semantics, or security requirements must fail closed. Do not interpret “accept more” from the meeting as permission to accept malformed or unauthorized requests. S1 00:35:43–00:40:19.

Reserve optional declarations for behavioral specifications, invariant suites, verification requirements, and proof/attestation references. Initial providers can truthfully advertise “none/not verified.” Do not implement OSLF, zero-knowledge proofs, or trusted-execution infrastructure now. A future verifier must validate required evidence; the mere presence of a proof field cannot establish trust. S1 00:10:11–00:12:10; 00:32:09–00:38:58.

## 7. Reliability, privacy, and placement semantics

### Acknowledgements and recovery

Keep independent observations for:

- payload persistence and its stated durability scope;
- message acceptance/delivery;
- execution completion and result persistence;
- chain submission, inclusion, and finality.

Do not collapse these into one linear success state: a result may be durable before a chain commitment exists. A request accepted into memory is not durably stored; a transaction hash is not finality; chain finality is not evidence of indefinite off-chain availability.

For a provider advertising crash-safe persistence, use an existing durable journal/outbox or equivalent so a crash between storage and dispatch can be reconciled. Across separate stores, do not claim atomicity without an implemented protocol. Use replay, deduplication, and explicit failure states. Reusing the same idempotency key with a different payload is a conflict.

A fire-and-forget caller must not mean best-effort memory loss: durably accept work before acknowledging the promised persistence level. Under overload, either persist within a bounded queue or reject explicitly; never silently discard acknowledged work. Retries must not duplicate episode events, belief evidence, attention credits, or externally visible job results.

### Backend mapping

| Concern | Proposed default | ASI:chain seam |
|---|---|---|
| Private raw observations/full episodes | Client-side storage | No private payloads, including encrypted copies. |
| Deliberately shared atoms/artifacts | Authorized local/shared DA provider | Only approved non-sensitive references/commitments where justified. |
| Indexes | Rebuildable provider-specific projections | No mandatory on-chain indexing. |
| Reasoning and attention | Local/off-chain implementations first | Optional deterministic implementations after conformance/measurement. |
| Registry/identity/commitments | Existing local/service infrastructure as applicable | Small verified integration point, not a prerequisite for every operation. |
| External effects and model calls | Off-chain execution with explicit provenance/trust | Never treat a nondeterministic external result as validator-deterministic execution by wrapping it in a callback. |

A thin Omega client is a deployment goal, not permission to move private data off the client. Delegate only within the applicable privacy/access policy.

References must actually be resolvable by their intended consumer. If a chain component cannot obtain permitted data, anchor a commitment or use an explicit result-verification boundary instead of pretending the reference makes the payload available on chain.

Any DA finalization latency or runtime-performance claim in the meetings is an observation to validate, not an SLA. Likewise, do not encode the transcript’s conflicting “64 bytes/64 bits” descriptions of a storage engine as an architectural fact. S1 00:03:14–00:06:26; 00:22:02–00:25:29; 00:48:05.

### Delegated execution, not arbitrary live-process migration

Represent delegation as an allowlisted operation, versioned code/provider identity, explicit inputs, optional serializable application checkpoint, and correlated result. The first prototype proves request/result handoff, not capture and migration of arbitrary Python, MeTTa, or VM stacks. A callback alone does not establish such equivalence. S1 00:15:01–00:16:54.

## 8. Staged cognitive implementation

### C0 — Minimal AtomSpace

Ingest and retrieve structured fixtures and opaque observations by reference. No LLM or parser required. Demonstrate scoped sharing, exact retrieval, and survival of restart according to the selected provider’s declared guarantee.

Preserve the ability to capture something before its meaning is known. An optional later parser/atomizer can emit proposed canonical forms with source links; the store itself does not invent an ontology. This accommodates both the raw-capture and preprocessed bootstrap approaches discussed without selecting one as universal. S2 00:25:20–00:30:36.

### C1 — Episodic memory and evidence

Add episode-local sequence, source/time metadata, observation/action/result links, and explicit evidence lineage. Define local ordering; do not assume timestamps establish a global order across agents. Preserve contrary reports instead of overwriting history.

An authenticated record that “agent A asserted X” does not mean X is true. An assertion about a claim and the claim itself need distinct representation.

### C2 — Bounded PLN revision, without inference search

Use the narrow belief-revision port to update a claim from explicit evidence. Reuse an inspected PLN revision implementation with numerical golden tests; do not invent an averaging function and label it PLN.

Specify strength/confidence/evidence-count semantics, legal ranges, evidence overlap/independence assumptions, duplicate handling, and provenance propagation. Repeated delivery and recycled derived evidence must not count as fresh independent support. Contradictory evidence must remain inspectable.

The meeting’s objection to unqualified truth value “1” did not select a numerical representation or settle whether “1” refers to strength, confidence, or another quantity. Preserve that concern as an explicit numerical-policy decision; do not silently clamp every field below one. Unknown knowledge must not become certainty by default. Estimated model/speaker priors must be labelled and separated from validated revision state. S2 00:44:12–00:46:53; 01:01:34.

### C3 — Minimal ECAN, STI only

Implement a bounded attention policy that can receive stimuli, select candidates, and apply decay at explicit logical time/steps. New-atom stipend, decay, saturation, budget behavior, and tie-breaking are named policy parameters, not hidden constants.

Do not assume every candidate ECAN implementation uses the same conservation law. Describe and test the selected policy, then require alternative providers to satisfy the applicable contract/profile. Test ECAN independently using opaque references with no PLN implementation installed.

### C4 — Bounded attention-guided PLN inference

Inference control obtains candidates from ECAN, reads explicit premise/belief snapshots, invokes one supported rule, and submits the proposed derivation to the owning belief/evidence module. Utility/attention feedback goes through ECAN commands. Set hard limits on rule applications, candidates, and feedback generations to prevent unbounded loops.

Only after this loop is demonstrated should the project tackle LTI, summarization, promotion, recall orchestration, more elaborate pressure-field policies, motivation, or evolutionary module selection. These are extension paths, not first-run requirements. S2 00:22:11–00:23:49.

## 9. Implementation milestones

### M0 — Architecture and executable contracts

Complete discovery and the terminology ledger. For every module, record responsibility, exclusions, state owner, dependencies, maintainer/specialist (`unassigned` where unknown), contract, profiles, and test obligations.

Deliver the dependency/ownership diagram, backend-placement ADR, interface definitions, common errors/receipts, minimal registry/resolver, and positive/negative conformance fixtures. Implement only infrastructure needed for M1. Specify cognitive ports C1–C4 but do not generate empty service processes for them.

**Exit:** a reviewer can identify who writes each state category, how providers are swapped, and which guarantees each backend does and does not offer. No hidden ASI:chain dependency in backend-neutral interfaces, and no Omega-specific semantics in the generic DA core. Backend-specific SDKs stay in adapters.

### M1 — One real storage/message/execution slice

Use two independently instantiated peers and at least one separate worker process. Prefer real Omega adapters where the repository is accessible. Otherwise label the peers as protocol fixtures, not Omega agents.

1. Resolve compatible providers and authorize a deliberately shared test scope.
2. Peer A stores a non-sensitive fixture through AtomStorage into a real available DA/chain-backed provider and receives the promised persistence receipt.
3. Peer B receives a reference through the messaging contract and retrieves identical bytes through its authorized adapter.
4. A delegates one allowlisted deterministic test operation. A suitable fixture is `inspect_atom`, which reads the referenced bytes and returns their digest and length. This is a transport/conformance test, not reasoning.
5. The worker persists its result, sends a correlated completion, and allows a restarted caller to recover status/result without duplicate effects.
6. Exercise duplicated requests, an unavailable consumer, a restart after durable acceptance, unauthorized scope access, and incompatible versions.
7. When a usable ASI:chain environment is available, submit one approved result/reference commitment and observe actual inclusion/finality separately. Record transaction/block evidence. When unavailable, report that chain integration was not demonstrated.

Compare in-process and separate-process bindings under the same contract. Provider selection changes configuration/composition, not business logic.

**Exit:** the bounded end-to-end slice runs with evidence, and its real versus simulated components are clearly named. A local-only harness passes a conformance gate, not the DA/chain integration gate. Do not build chain consensus or bypass isolation to make the demo green.

**Stop after M1.** Report the smallest next increment and any blocked gates.

### Subsequent runs, not automatically authorized by this brief

- **M2:** Add C1 and C2; demonstrate evidence lineage, duplicate-safe revision, and contradictory evidence.
- **M3:** Add C3 and C4; demonstrate a bounded inference loop and a contract-compatible attention-provider swap.
- **M4:** Connect the chosen Hive UI/workflow; improve a genuine ASI:chain integration point; evaluate harder workloads and richer policies only against explicit acceptance criteria.

## 10. Required conformance and regression checks

Implement M0/M1 tests now; provide named fixtures/specifications for cognitive checks that belong to later milestones. Do not report future test specifications as executed tests.

| Check | Required evidence |
|---|---|
| Store without cognition | Storage and retrieval work with no PLN, ECAN, LLM, or parser dependency. |
| Single-owner state | Foreign-module attempts to edit belief/attention/episode/job state are rejected or structurally impossible. |
| Reference integrity | Authorized retrieval returns expected bytes/revision; missing or unavailable content is an explicit error. |
| Scope isolation | A peer lacking access cannot read payloads or modify another scope; logs do not disclose private data. |
| Substitution | The same consumer and contract suite run against in-process and separate-process providers without consumer-code changes. |
| Compatibility | Supported same-major changes work; unsupported majors/profiles and required features fail explicitly. No silent guarantee downgrade. |
| Idempotency | Repeated mutation/job delivery yields one logical effect; same key with different content is rejected. |
| Crash/replay | Accepted durable work survives a tested failure/restart boundary; outbox reconciliation prevents silent loss. |
| Backpressure | Bounded overload results in durable acceptance or explicit rejection, not hidden drops. |
| Async handoff | Correlated results survive delayed/unavailable reply consumers and caller restart. |
| Honest chain state | Pending, included, and finalized observations are distinct; no synthetic transaction IDs or claimed finality. |
| Generic DA | DA builds/tests without Omega/PLN/ECAN imports or domain-schema requirements. |
| Episode/evidence isolation — M2 | Source claims are not mistaken for established facts; duplicate occurrences are not counted twice. |
| PLN semantics — M2/M3 | Golden tests identify exact rule/revision implementations and numerical profiles; no invented “PLN-like” substitutes. |
| ECAN independence — M3 | ECAN runs with opaque references and no PLN; only its API changes its attention state. |
| Bounded cognition — M3 | Work and feedback stop at declared budgets; alternate attention implementations meet the same applicable contract. |

Record environment, commits, fixture hashes, commands, outcomes, and remaining failures. Benchmarks should measure end-to-end latency, throughput, payload bytes across boundaries, queue depth, retries, recovery behavior, and acknowledged-data loss under the actual tested failure model. Establish a baseline before proposing thresholds. Never infer scalability or cognitive quality from a small conformance demo.

For later module-upgrade comparisons, hold inputs, evidence, budgets, and seeds/time schedules fixed. Separate contract correctness from quality/efficiency improvement. Use module-specific scorecards: revision correctness and provenance for belief revision; task-relevant selection and resource use for ECAN; rule correctness and bounded outcomes for inference.

## 11. Deliverables, governance, and reporting

Use the existing repository layout. A suitable small documentation directory is `docs/module-interfaces/`, containing:

- architecture and module/state-ownership catalogue;
- source/decision ledger and glossary/anti-glossary;
- contracts and compatibility/verification-profile notes;
- short ADRs for identity, authority, durability, privacy, and placement;
- conformance matrix, runnable demo instructions, and an evidence report.

Keep actual schemas/adapters/tests in the repository’s established locations. Include configuration selecting backends and one reproducible test/demo command. Do not create an independent replacement application just to demonstrate the design.

**Terminology discipline:** use AtomSpace, episodic memory, PLN, ECAN, STI, LTI, DA, Omega Hive, and ASI:chain consistently. Record transcript aliases and uncertain names; do not introduce synonyms that duplicate existing responsibilities. New concepts require a short justification and glossary update. S2 00:12:40–00:15:36.

**Definition of ready:** responsibility, owner, input/output contract, dependencies, selected provider/profile, acceptance cases, and stopping condition are explicit.

**Definition of done:** implementation passes the applicable contract and integrated regression tests; documentation and observed evidence match; failures, stubs, and unsupported guarantees are disclosed. Unit mocks alone are insufficient. S2 00:02:28 and 00:17:02.

Do not invent organizational ownership. Record technical specialists where supported by repository evidence; leave the rest unassigned. Route mathematical-policy questions for specialist review while proceeding with independent engineering work.

Finish the Codex report with: files changed; decisions and their status; commands and results; real/stubbed/unavailable providers; measured guarantees; compatibility and security limitations; and the next bounded milestone. Do not say “Omega Hive runs on ASI:chain” unless the report demonstrates what actually ran on chain and what remained elsewhere.

## 12. Explicit exclusions

No full formal-verification stack; no new ZK/TEE implementation; no whole-system transpilation; no new consensus algorithm; no tokenomics, billing, or marketplace; no production orchestration platform; no mandatory ontology or LLM-based parser; no simultaneous implementation of competing ECAN/PLN algorithms; no wholesale replacement of current Omega or AtomSpace; no claim that a callback is arbitrary continuation migration; no private episodic payloads on chain.

**Success criterion:** a small, inspectable interface architecture and a truthful working integration slice that let independently implemented modules evolve without taking responsibility for each other’s state or becoming tied to one backend.
