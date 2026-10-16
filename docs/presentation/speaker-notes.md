# Omega × ASI — speaker notes

Implementation baseline: `3f75db993d354d18dff2a3e36498eabe4a33afb3`.
Suggested delivery: 25–30 minutes for slides 1–24, with appendices for discussion.
All claims refer to the recorded 16 October 2026 local M0/M1 run.

## 01 — One responsibility. One state owner. Many possible backends.

This talk explains how independently implemented modules can cooperate without taking ownership of each other's state. Start with the helicopter view, then module responsibilities and function dependencies. Only after those boundaries are clear do we examine the running M1 slice. M0 and the bounded local M1 integration are complete. M2 and the cognitive stack are explicitly outside the completed work. These contracts are proposed engineering choices, not a finalized community AtomSpace specification. Suggested delivery: 25–30 minutes for slides 1–24; remaining slides are discussion material.

Source: `brief + implementation commit 3f75db9`.

## 02 — The architecture separates three commitments

The three commitments are the architecture's thesis. Behavior means operation semantics and guarantees, not merely a matching method name. Ownership means only an owner's methods may mutate its state, even when modules share a database. Evidence means a stored payload, an accepted job, an acknowledged message and a finalized chain deploy remain different facts. The M1 path below is a conformance experiment using two protocol peers, actual DeTTa libraries, a separate worker and an optional real local chain runtime.

Source: `architecture.md`.

## 03 — Fifteen modules; four responsibility groups

This is the placement map, not a process topology. All fifteen modules from the brief appear here. The five cognitive modules plus Relations and Search are specifications only. Blue modules are implemented by the local harness; Authorization is explicitly a test policy. Teal shows actual provider integration: local DeTTa DA/storage libraries and a real isolated single-validator F1R3node. Consensus/finality includes the bounded commitment adapter. Private episodic history belongs on the client in future work. A module may be co-located with another module without surrendering its state boundary. The actual Hive runtime was unavailable, so no box here implies a running Hive agent.

Source: `architecture.md`.

## 04 — Data responsibilities: bytes → references → history

DA persists opaque payloads and erasure shares. AtomStorage owns the application reference metadata, immutable revision and semantic replay keys. Relations describe explicit ordered roles; a link is not automatically a belief. Search is a rebuildable projection that exposes its watermark, not the authoritative store. Episodic memory adds occurrence identities and episode-local ordering, so equal payload bytes may describe different observations. Its full private history remains client-side. This design deliberately does not require a parser, ontology, embedding model or LLM just to store data. Additional relation operations are outgoing/incoming; episode reads are readEpisode/findEpisodes. Those contracts are specified but have no M1 runtime.

Source: `architecture.md`.

## 05 — Cognitive responsibilities: history ≠ truth ≠ attention

Belief revision is the only owner of the truth/evidence aggregate. Its numerical profile has not been selected as a universal model. The PLN kernel is pure over ordered immutable premise snapshots and returns a proposal; it cannot update beliefs or choose its own agenda. ECAN owns attention and logical time, including allocation, decay and tie-breaking under a declared policy. readAttention is also part of its contract. Inference control orchestrates retrieval, belief snapshots, rules and feedback within candidate, rule, generation and time budgets. Control stores its own step receipts/checkpoint, not the other owners' state. Reviewers and maintainers for these new contracts remain unassigned.

Source: `architecture.md`.

## 06 — Control responsibilities: move work without moving authority

Messaging owns accepted inbox entries and acknowledgements. Execution owns jobs and its outbox, and only accepts inspect_atom in M1. Registry is a static provider catalogue, not capability authority or chain registration; the resolver is a pure selection function over those descriptors. Finality is a separate bounded adapter with a registered approved commitment, durable signed intent and direct node observations. It does not establish belief confidence, execution success or indefinite availability. Authorization reads current server-owned policy from authenticated transport context; the implemented policy is a fixture for the trusted local harness. No caller-supplied sender field grants authority.

Source: `architecture.md`.

## 07 — Function dependencies: the proposed cognitive path

This is a declared runtime dependency view, not a claim that the cognitive loop was executed. Arrows point from a caller to the port it invokes. Inference control calls Search.query, attention.select and submitStimulus, belief.readBelief and submitEvidence, and PLN.applyRule. Episode history produces EvidenceRef values for the orchestrator; episode writes do not invoke hidden truth setters. Relations can persist ordinary atom records and episodic memory stores referenced payloads. AtomStorage then calls the opaque DA storage port: this is the solid implemented path. Search reads immutable records/events and belief revision consumes evidence/atom snapshots; those data dependencies are named below the diagram to avoid a misleading tangle of arrows. Interface imports remain acyclic; runtime feedback is expressed through explicit commands and values.

Source: `ports.py + contracts.md`.

## 08 — Function dependencies: admission, work and delivery

Demo setup resolves suitable descriptors, then Peer invokes the configured binding. The dashed offers arrow supplies descriptor data to the resolver. Each service invocation validates the wire envelope and checks the current local policy before the explicit dispatch allowlist. This diagram focuses on delegated execution; direct store and messaging calls pass through the same authorization boundary. Worker execution calls the atom owner to read inputs and create a persisted result. Completion goes through a durable outbox into the message owner's inbox; poll/ack are recipient-owned operations. The chain adapter is a separate optional consumer of one approved result digest. It is not on the mandatory storage or execution path. Scope/method checks also apply to worker reads and completion delivery. The static resolver does not grant permissions.

Source: `client.py · service.py · registry.py`.

## 09 — State ownership survives co-location

M1 uses one SQLite journal to keep the example small. That journal stores several logically owned categories: atom metadata, messaging inbox state, execution jobs and outbox, plus replay records. Public dispatch only exposes declared operations, never raw SQL, worker controls or setters for another owner. Shared storage therefore does not erase responsibility boundaries. DA payloads and erasure shares live in actual DeTTa FileStorage outside SQLite. In future work, private episode history remains client-side, and truth or attention can change only through the relevant owner. This is logical ownership, not a claim of multi-tenant process isolation against the same OS user.

Source: `architecture.md · ADR 002–004`.

## 10 — Keep four architecture choices independent

A service contract is an interface, not necessarily a blockchain smart contract. One module can run in process, behind a message boundary or through an inspected chain API, provided the profile and required behavior are preserved. The current proof runs identical Peer consumer code under in-process and subprocess service bindings. Both still use real DA helper processes and separate workers. This demonstrates a transport substitution within the local composition; it does not demonstrate an alternate DA provider or a distributed deployment. Constructor/composition code imports concrete adapters. The typed domain ports do not depend on DeTTa, F1R3, PLN or ECAN implementations.

Source: `ADR 004–005 · bindings.py`.

## 11 — Compatibility is a semantic filter

The resolver filters interface identity and a consumer's explicit same-major interval, exact profile and required features, supported operations, advertised guarantees, payload limits and privacy. Any required measured latency must be present in descriptor measurements. Required verification always fails because no verifier is available. Advertisements and evidence remain distinct. The actual M1 dispatch only accepts wire 1.0.0. A separate descriptor fixture at 1.2.3 exercises additive resolution; it is not evidence of a deployed 1.2.3 service. Unsupported requirements produce typed errors instead of weaker fallback selection. Interface 1.0.0 stabilizes this prototype, not an agreed community standard.

Source: `registry.py · test_adapters.py`.

## 12 — Identity, replay and authority travel separately

This is an illustrative field view, not a copy-paste wire JSON request. The actual schema is contracts/wire.schema.json. Immutable AtomRef identifies a scoped record with revision and integrity digest; the digest does not grant permission or establish truth. A mutation key is scoped by principal, scope, interface and operation, and bound to semantic input. Changing the body, routing or deadline with the same key is a conflict. Message ID and causation are delivery metadata. Async send/submit include correlation and an authorized reply route. Trusted transport supplies the opaque credential, which current service policy maps to a principal. The body cannot nominate its own authority.

Source: `contracts.py · wire.schema.json`.

## 13 — One slice crosses real process and storage boundaries

The arrows summarize the logical sequence; reads and writes from the worker pass through the atom/storage adapter, even when omitted for clarity. Peer A creates a generated 62-byte fixture through AtomStorage into real DeTTa. It sends the reference through the durable mailbox. Peer B receives it and fetches exactly the same bytes. A submits inspect_atom; the separate worker reads the referenced bytes and returns their digest and length. The demo kills the worker twice at persisted boundaries, restarts, then recovers a correlated completion and result. Every acknowledgement refers to its stated durability scope. Both service bindings use the same Peer code and validation. The peers and operation are fixtures, not Omega agents or reasoning.

Source: `scripts/demo.py · evidence/demo.json`.

## 14 — A receipt proves one fact at one boundary

Avoid turning this grid into a linear distributed transaction. A result can be durable before a chain commitment exists; messaging can be delayed while result retrieval already works. Payload persistence is qualified by its local durability scope. Mailbox acceptance is different from recipient acknowledgement. Execution completion is different from whether its outbox was delivered. Chain submission yields a deploy ID, inclusion yields a block observation and effect finality comes from the specific inspected endpoint. A finalized digest does not prove a payload will remain available, nor does any of these receipts establish belief confidence. This separation is central to both interfaces and reporting.

Source: `contracts.md · evidence.md`.

## 15 — Crash recovery is a replay protocol

The three tested fault boundaries are acceptance committed before a response, DA result persisted before the completion transaction, and completion committed before dispatch. The demo itself performs the latter two worker kills; the contract suite also tests the acceptance-reply boundary. Deterministic storage coordinates and semantic deduplication let an attempt replay without a second logical result. A DA write before journal commit can leave an unreferenced artifact: there is no cross-store atomicity claim. Result metadata, job completion and outbox intent commit together in SQLite; inbox delivery and outbox completion also commit together. A full or revoked reply route keeps completion pending. These tests cover SIGKILL on the same host, not power loss, disk loss, Byzantine behavior or exactly-once physical computation.

Source: `ADR 003 · test_contract.py`.

## 16 — The DA boundary carries bytes, not cognition

The Rust helper links actual detta-da and detta-storage from the inspected working tree. It maps bytes into an opaque application profile and binds the scope through generic coordinate metadata. The generic DA schema remains application-neutral; Omega-specific reference metadata lives above it. Reads reconstruct and verify persisted Reed–Solomon shares rather than retrieving a cached copy from SQLite. Tests remove the cached full payload and two of six shares and still recover exact bytes. A third missing share and corrupted-share cases fail explicitly; the tests do not establish an exhaustive adversarial-correction guarantee. This is real local library integration, not a running distributed validator/custody network. No certificate or remote replication guarantee is fabricated.

Source: `adapters/detta/src/main.rs · test_adapters.py`.

## 17 — Authorization is checked where state is owned

The local policy fixture maps opaque credentials to principals and stores current scope, method and route requirements on the service side. It is reloaded for each checked invocation, including retries and worker operations. A sender field or scope name in a request is never sufficient. The tests exercise foreign scopes, foreign routes, live revocation, ownership-safe dispatch, conflicting retries and overload. A full inbox retains execution completion in the outbox until delivery can occur. The same OS user can directly access trusted service files, so this harness does not claim production multi-tenancy, encrypted private storage or an SCS enforcement integration. Before private data use, real enforcement and service isolation are separate gates.

Source: `service.py · ADR 002`.

## 18 — What ran, what was a fixture, what is unavailable

DeTTa means actual DA and FileStorage code executed against local persisted shares, not a mock and not a custody network. F1R3node means a real local node with a fresh isolated genesis and one validator, not public mainnet/testnet or multi-validator safety. Peers are independently instantiated protocol fixtures; inspect_atom is a deterministic fixture operation running in a real OS process. Authorization is an explicit local policy fixture. Fake chain responses exist only in unit tests and are distinct from the real chain evidence. The supplied omegahive-start-here repository is an onboarding index; the intended Hive runtime checkout is absent. DAS, MeTTaClaw, metta-attention and reachability were inspected, but their cognitive/channel providers were not integrated. No upstream source files were changed.

Source: `discovery.md · evidence.md`.

## 19 — A real result digest reached a real local chain

Read the recorded chain JSON as the primary evidence. Its actual sequence is pending, included with effects Pending, then finalized. All three observations are present; the earlier report prose was corrected to match this trace. The block is height 3, execution errored=false, rejection count zero, cost 351 phlo. The approved commitment digest matches the persisted result ref in both demo bindings. Signing intent is stored before network submission, so an ambiguous timeout can reuse the same transaction signature. The local node was built from the inspected dirty working source and shut down with exit 0. Node startup took 25.735 seconds and the observed submission/propose/finality window took 4.013 seconds. These node responses are not independently verified consensus proofs or a public-network test.

Source: `evidence/chain-demo.json · f1r3.py`.

## 20 — Evidence concentrates on boundaries that can fail

The final local verification run passed 27 unittest tests with zero failures or skips. Applicable service conformance cases run under both in-process and subprocess bindings. Separately, the upstream detta-da library passed 62 tests and detta-storage passed 40, totalling 102. These are distinct counts and do not imply 27 tests for each binding or a full upstream regression for every repository. The chain build and real local chain demo also passed as separately recorded gates. Other checks included Rust formatting, Python compilation and git diff validation. Do not count unimplemented episode, belief, attention or inference test specifications as executed functionality. No full F1R3node, DAS, MeTTaClaw or cognitive regression suite is claimed.

Source: `evidence/tests.log · evidence/detta-tests.log`.

## 21 — A small baseline, with the failure path included

Values are read directly from the committed demo.json, not retyped as marketing claims. The in-process binding is about the service call only; both configurations launch real DA helpers and separate workers. End-to-end slices include failure injection and recovery: approximately 0.756 and 1.761 seconds. Each used 17 client calls with 6,550 request bytes and 5,731 response bytes. In-process counts are logical serialization sizes; subprocess counts are actual pipe bytes. Canonical DA fixture/result payloads were 1,027 and 1,284 bytes, but DA framing and worker-control traffic were not measured. Both runs ended with two atoms, one job, two acknowledged messages and no pending outbox. Zero observed acknowledged-data loss is bounded by this failure model and sample, not a general durability theorem or performance guarantee.

Source: `evidence/demo.json`.

## 22 — The design trades breadth for inspectable guarantees

These are proposed v0 engineering decisions that operationalize the brief, not claims of community consensus. Immutable scoped reference metadata and replay keys provide a small auditable starting point; deletion, retention and cross-scope merging are deferred. SQLite serialization and an outbox make process-death behavior testable at the cost of throughput and distributed scheduling. Exact profiles avoid pretending numerical semantics or query dialects are interchangeable. The DeTTa adapter remains external to the application-neutral DA core. A chain adapter registers a single approved non-sensitive result commitment; it is not an arbitrary deployment service. All unassigned specialists remain unassigned. No invented arithmetic, ontology or STI policy was silently chosen.

Source: `decisions.md`.

## 23 — M0 and M1 are complete. The next gate stays closed.

M0 and the bounded local M1 gate are complete. The next increment is M2, with private ordered episodes and duplicate-safe, lineage-aware belief revision, including contradictory evidence and numerical golden tests for a reviewed existing model. That work has not started. M3 attention/inference and M4 Hive workflow integration remain later milestones. Actual Hive integration is blocked by the missing intended runtime and unsettled version/registry target. Production authorization, multi-host DA custody, public or multi-validator chain operation, independently verified proofs and meaningful load characterization remain open. Their absence does not erase the local evidence; local evidence does not pass those gates. Ending here respects the original stopping condition.

Source: `brief · evidence.md`.

## 24 — Modularity is a promise about behavior and authority.

Close on the central idea: functional decomposition alone is insufficient. A module boundary needs an owner, behavioral semantics and evidence for its guarantees. This work turns that idea into an inspectable contract package and one bounded running slice. The storage integration is real, the local chain integration is real, peers and test policy are fixtures, and the cognitive stack is specified only. The architecture can evolve without embedding cognition in DA or requiring every operation to run on chain. Pause here for discussion; the remaining slides provide method mappings, exact provenance, failure semantics and reproduction commands.

Source: `implementation 3f75db9 · evidence.md`.

## 25 — Implementation dependency map

Navigate implementation from Peer methods to binding.invoke, then to Service.invoke validation and policy. In-process invokes the service in the current Python process; subprocess invokes the host through private EOF-framed stdin and one JSON stdout response. Trusted composition chooses the concrete storage adapter. Atom, message and execution owner logic is in service.py. The operator-only work and flush entry points are separate from public dispatch. detta.py calls the Rust helper linked to the original DA/storage libraries. chain_demo.py separately registers an approved commitment with F1R3Commitments, injected signer, signed-intent journal and F1R3HTTP. The drawing abstracts call paths; it does not imply contracts import implementation files.

Source: `fusion/ · adapters/detta/`.

## 26 — Specified cognitive contracts carry test obligations

Episode expected_sequence and belief expected_revision make concurrent updates explicit. Replayed evidence must not add weight; derived cycles and overlapping roots cannot manufacture independent support. Reachability's guarded trueagi-pln-stv-finite-k1/v1 implementation is a candidate for review, not a selected universal model. metta-attention exposes STI/LTI/VLTI and direct setters, so it cannot be silently advertised as the proposed STI-only policy. Attention requires a declared budget, saturation, conservation or nonconservation, decay and tie-breaking behavior. Inference control must bound feedback generations and work, and define durable checkpoint semantics before advertising crash safety. These obligations belong to future milestones; new cognitive services remain absent.

Source: `ports.py · contracts.md`.

## 27 — Typed failures preserve the caller’s recovery choices

Permanent-for-unchanged-request failures also include INVALID_ARGUMENT and DEADLINE_EXCEEDED. INTERNAL is reserved and not automatically retryable. NOT_AVAILABLE covers missing persisted DA for a known ref and queued results; NOT_FOUND is absent metadata. Overload never silently drops acknowledged work. When transport fails after acceptance, the caller can retry the same semantic mutation or query the job owner. Already accepted mutations recover their original receipt even after the deadline expires, while new admissions and worker starts still honor the deadline. Empty poll means an authorized, known-empty inbox; failures do not become empty recall results. Live policy still applies to retries.

Source: `contracts.md · service.py`.

## 28 — Provenance includes working-tree state

The commit prefixes are navigation aids; the committed sources.json contains full identifiers, absolute roots, remotes, dirty-file lists and relevant working-source fingerprints. The real DeTTa and F1R3 builds used pre-existing modified source, so clean HEAD alone is insufficient to reproduce identical behavior. MeTTaClaw had untracked runtime/project artifacts. This task did not alter upstream sources or commit those upstream changes. Only the fusion-module-interfaces workspace is committed. The supplied Hive repository is an index; no actual Hive runtime checkout was available. Meeting transcripts were referenced in the brief but not independently supplied or inspected. The intended earlier Omega type/interface registry was not found; the static registry remains a bounded harness implementation.

Source: `discovery.md · evidence/sources.json`.

## 29 — Reproduce the gates; inspect the evidence

The main command is executable as shown. It builds the actual DA adapter offline, runs the tests and executes both bindings. The optional chain build requires staged grpcio-tools; chain_demo requires pinned cryptography, pycryptodome and grpcio-tools extras, documented exactly in runbook.md. Initial native CLI/protoc/stack bring-up failures and the resolved local configuration are recorded in evidence.md rather than omitted. The demonstration uses generated non-sensitive data and fresh local keys under ignored artifacts; do not copy private data into it. For the presentation itself, build.py and requirements.txt in this directory generate the editable PowerPoint, vector PDF/SVG and speaker notes from one layout. No M2 implementation is required or created by these reproduction commands.

Source: `runbook.md · evidence.md`.
