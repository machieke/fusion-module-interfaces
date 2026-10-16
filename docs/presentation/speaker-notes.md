# Omega × ASI — speaker notes

Implementation baseline: `bb22ef5e28b089b80132b40bcf5a1bbfc38b065b`.
Evidence snapshot: `4ee5cbe8b84689a5d2432530083738b263142f90`.
Suggested delivery: 30–35 minutes for slides 1–26, with appendices for discussion.
Current claims use the recorded 16 October 2026 M1.2 evidence. The M1 chain observation is historical and separately labelled.

## 01 — One responsibility. One state owner. Many possible backends.

Start with the helicopter view, all fifteen module responsibilities and function dependencies before the implementation details. M1.1 separated owner commits and proved an independent AtomStorage replacement. M1.2 now connects a pinned real Hive runtime through its native Programs action route, with real DeTTa and a fixture counterparty. The cognitive modules remain specifications. These are engineering contracts, not a final community AtomSpace or numerical model. Suggested delivery: 30–35 minutes through slide 26; seven appendices support discussion. Current evidence is the recorded 16 October 2026 M1.2 run, implementation bb22ef5, evidence snapshot 4ee5cbe.

Source: `M1.2 evidence snapshot 4ee5cbe`.

## 02 — The architecture separates three commitments

The thesis remains behavior, authority and evidence. A matching method name is insufficient: profiles define semantics and guarantees. Only the state owner may write its state. Receipts describe specific facts rather than one universal success. The real Hive operator action generates a non-sensitive sample, stores it through AtomStorage, sends its reference to a labelled fixture counterparty, submits inspect_atom, recovers completion, records its accepted outcome and acknowledges delivery. Chain submission is not part of this M1.2 path.

Source: `architecture.md`.

## 03 — Fifteen modules; four responsibility groups

All fifteen modules remain visible: five cognition modules, five shared application ports, three control/policy functions and two provider-facing responsibilities. Hive is a consumer of these modules, not a newly invented sixteenth module. Dashed violet boxes remain specifications. Blue is the implemented local contract harness. DeTTa is real local DA/FileStorage; an independent file provider is a contract fixture. Finality has a historical real isolated-chain observation from M1, but the M1.2 chain gate was not run. Native Hive authentication is real; the downstream Fusion credential/scope policy remains a development fixture. No cognitive module is implemented by this increment.

Source: `architecture.md`.

## 04 — Data responsibilities: bytes → references → history

DA persists opaque payloads and erasure shares. AtomStorage owns the application reference metadata, immutable revision and semantic replay keys. Relations describe explicit ordered roles; a link is not automatically a belief. Search is a rebuildable projection that exposes its watermark, not the authoritative store. Episodic memory adds occurrence identities and episode-local ordering, so equal payload bytes may describe different observations. Its full private history remains client-side. This design deliberately does not require a parser, ontology, embedding model or LLM just to store data. Additional relation operations are outgoing/incoming; episode reads are readEpisode/findEpisodes. Those future contracts remain unimplemented through M1.2.

Source: `architecture.md`.

## 05 — Cognitive responsibilities: history ≠ truth ≠ attention

Belief revision is the only owner of the truth/evidence aggregate. Its numerical profile has not been selected as a universal model. The PLN kernel is pure over ordered immutable premise snapshots and returns a proposal; it cannot update beliefs or choose its own agenda. ECAN owns attention and logical time, including allocation, decay and tie-breaking under a declared policy. readAttention is also part of its contract. Inference control orchestrates retrieval, belief snapshots, rules and feedback within candidate, rule, generation and time budgets. Control stores its own step receipts/checkpoint, not the other owners' state. Reviewers and maintainers for these new contracts remain unassigned.

Source: `architecture.md`.

## 06 — Control responsibilities: move work without moving authority

Messaging owns accepted inbox entries, acknowledgements and replay. Execution owns jobs and the completion outbox, and accepts only inspect_atom. Its result atoms belong to AtomStorage, a separate owner. Registry and resolver select a configured descriptor, not permission. Finality is a separate adapter with a historical real M1 observation; it is not invoked by the real Hive M1.2 workflow. Native Hive authenticates the operator and supplies trusted actor context. Fusion then enforces current scope, method and route policy through a labelled local test-policy implementation. Caller-supplied identity does not confer authority.

Source: `architecture.md`.

## 07 — Function dependencies: the proposed cognitive path

This is a declared runtime dependency view, not a claim that the cognitive loop was executed. Arrows point from a caller to the port it invokes. Inference control calls Search.query, attention.select and submitStimulus, belief.readBelief and submitEvidence, and PLN.applyRule. Episode history produces EvidenceRef values for the orchestrator; episode writes do not invoke hidden truth setters. Relations can persist ordinary atom records and episodic memory stores referenced payloads. AtomStorage then calls the opaque DA storage port: this is the solid implemented path. Search reads immutable records/events and belief revision consumes evidence/atom snapshots; those data dependencies are named below the diagram to avoid a misleading tangle of arrows. Interface imports remain acyclic; runtime feedback is expressed through explicit commands and values.

Source: `ports.py + contracts.md`.

## 08 — Function dependencies: the real native path

Follow the real native dispatch into the thin plugin, which holds a caller-owned receipt and uses Subprocess/Peer through descriptor-bound validation. Direct storage, messaging and execution calls all cross the same authenticated boundary. Trusted composition supplies concrete owners; the plugin never constructs them or accesses their tables. Messaging.send validates the referenced bytes through caller-authorized AtomStorage.get; Execution.submit reads the input before accepting a new job. The worker calls declared AtomStorage get/create, then execution commits terminal state/outbox. CompletionDelivery.accept belongs to the mailbox owner and commits separately. Chain remains a separate, uninvoked adapter. This is a logical call map; it does not force one process per module.

Source: `program.py · ports.py · execution.py`.

## 09 — Separate owners now have separate durable commits

This replaces the old M1 shared-journal drawing. M1.1 split atom metadata, messages and execution into separately committed owner stores and declared the dependencies actually exercised by the worker. Execution's own terminal state and outbox are atomic with each other, not with atom persistence or mailbox acceptance. Wire replay metadata is colocated with execution, while cross-owner operations have owner-local replay. M1.2 adds only a minimal caller boundary receipt, not episodes or a new journal framework. It serializes one caller journal and permits one unfinished intent per dedicated route. All observations concern persistent local files and process restart.

Source: `architecture.md · atoms.py · messaging.py · program.py`.

## 10 — AtomStorage replacement is independently exercised

The committed M1.2 matrix contains 4 workflows: DeTTa and fixture-files under both in-process and private subprocess bindings. These peers remain fixtures; this matrix is not relabelled as the new native Hive test. Execution depends on declared AtomStorage and CompletionDelivery ports and does not inspect concrete atom owners. The file fixture owns atomic payload/record files and is independently implemented. This proves substitutability in the documented fresh-store profile. It is not another DA network, live namespace switching, a journal migration or distributed placement. M1.2 preserves these boundaries without changing fusion/.

Source: `evidence/m1_2/m11-swap-demo.json · test_m11.py`.

## 11 — Compatibility binds semantics and selected replies

The resolver uses fixed consumer requirements, exact profiles, supported operations, privacy and claimed guarantees. Binding invocation and success replies carry the selected descriptor token; response validation checks shape, scope, references, integrity, receipts and known correlation. The native adapter loads operator-selected descriptors and uses that same boundary. Native-path tests reject an incompatible profile and a changed descriptor. Wire remains 1.0.0; the /2 messaging and execution profiles describe neutral process-restart receipts and recoverable status. They do not imply live 1.x rolling interoperability. No proof verifier is installed, so required verification fails closed.

Source: `registry.py · bindings.py · responses.py`.

## 12 — Native identity and stable intent stay separate

The diagram shows native action fields, not a complete copy-paste HTTP request; the actual body also includes the swarm and an empty items list. Hive authenticates the operator, checks swarm visibility, rejects identity fields in params, and delivers trusted actor/command context. An exact principal/swarm configuration selects credential, scope, reply route and a fixture counterparty. The plugin accepts only an integer seed and no arbitrary input bytes. Stable keys cover input creation, sharing, job submission and acknowledgement. On retry, status/get/poll/ack continue to enforce the current Fusion policy. Test credentials and private configuration are never embedded in the deck.

Source: `ProgramActions.person_act · integration/hive/program/program.py`.

## 13 — The intended Hive source now has a verified entrypoint

The old runtime-unavailable statement is historical. The user supplied clean omegahive-schematics 4af00db4e395375484dd48d0b9068a59afcf01f8; its component map names 34b0fb3. Authorized SSH retrieved PhysixSNET/omegahive at 34b0fb32ab3806e5609fc89bb7535518a35e1aea. The different observed remote HEAD was not silently selected. Native startup is python -m hive. The test driver uses its lock, startup recovery and create_app in a separate OS process, with real PeTTa and the default Supervisor. It signs in and traverses the actual Programs route. Native baseline tests have their declared fake process driver; the new real-caller tests do not. No LLM or mind is started. This pin selects an engineering experiment, not a final community product release.

Source: `sources.json · discovery.md · native-baseline.xml`.

## 14 — One native operation crosses the existing interfaces

All effects originate in the real native operation, not a renamed protocol demo. The caller first commits its original intent. AtomStorage persists generated bytes in actual DeTTa, then Messaging accepts a reference for the explicitly labelled fixture counterparty. DelegatedExecution accepts only inspect_atom under the original key and correlation. The caller records the accepted job. A separate real worker reads/persists through AtomStorage, then commits execution terminal state/outbox. Messaging accepts the completion in a separate transaction. The final arrow summarizes the reconciliation expanded on the next slides: status /2 restores known correlation, poll and get verify the completion, caller acceptance commits, and a stable-key acknowledgement follows. This is not one distributed transaction.

Source: `program.py · execution.py · messaging.py`.

## 15 — Six receipts describe six different facts

These facts are independent. A result atom can persist while the job is still queued after worker death. A succeeded job may have an unsent outbox when a reply route is full. A caller may have recorded its accepted outcome while acknowledgement is still pending. The plugin commits its outcome before acknowledgement to deduplicate that gap, and rechecks live authorization before returning it on replay. A failed worker completion is verified, recorded and acknowledged as an error, never transformed into empty memory or successful inspection. There is no exactly-once display or physical-execution guarantee. The original acceptance receipt in the trace remains queued/not-observed because it describes admission, not the later outcome.

Source: `contracts.md · m1_2-evidence.md`.

## 16 — A restarted Hive caller recovers without its old RAM

These are actual OS-process kills, not exceptions standing in for restart. The test caller is a native Hive app process with real authentication and dispatch. Trusted configuration enables a SIGSTOP checkpoint; the test waits for its marker and sends SIGKILL. Admission-loss occurs after durable Fusion acceptance but before saving the job in the caller record. Submission-loss occurs after that local record commits. Acceptance-loss occurs after outcome commit and before ack. A new app process signs in against the same native data directory and reconciles the original request. Tests assert stable job identity, two total atoms (input and one result), one outbox, one completion, one caller outcome and no delivery after ack. The receipt is a minimal boundary record, not an episodic-memory implementation.

Source: `test_integration.py · hive-integration.xml`.

## 17 — Worker failure and backpressure preserve pending work

The native worker-recovery test kills the existing worker after AtomStorage has committed the result and before execution terminal state/outbox commit. The test observes two atoms, one queued job and no outbox, then restarts and verifies one result. In the full-route test, a labelled fixture fills the dedicated reply route. Flush reports zero sent and one pending. The native operation refuses the unrelated delivery and does not record an accepted outcome. After fixture cleanup, flush and native completion succeed. A separate test revokes worker create authority after admission and observes an explicit UNAUTHORIZED failed completion without a result atom. Temporary input unavailability is exercised in the preserved M1.1 matrix; the new native representative provider-failure case is route backpressure. No cross-owner atomicity is claimed.

Source: `execution.py · test_m11.py · test_integration.py`.

## 18 — The DA boundary remains application-neutral

This unchanged DA boundary is exercised against a freshly fetched clean secured-contract-spaces revision 272888f264dd2dde18b574cabb53c266b0dac2ec. No Hive-specific schema is added to DeTTa. Application references and replay semantics belong above opaque DA. Conformance removes the cached payload and two erasure shares and verifies reconstruction; three missing shares and corruption fail explicitly. This is actual local library execution, not a validator/custody network or an indefinite-retention claim. The independent atomic-file provider is an AtomStorage contract fixture, not a second DA network. The clean-source rebaseline excludes historical dirty storage-format and custody-pruning additions and reruns applicable tests.

Source: `adapters/detta/src/main.rs · test_contract.py`.

## 19 — Native-path refusals preserve authorization and replay

Every row here is tested through the actual native route, except the trusted operator's setup/failure injection. The first row is rejected by Hive before plugin effects. The plugin uses the authenticated actor/swarm mapping and current module credentials; it cannot nominate a principal in the request body. Changed descriptor identity fails binding consistency at the server even if its advertised method set looks compatible. Cached success still requires live status/get/poll/ack authority. The worker rechecks its own and requester permissions after admission. Fusion's credential/scope policy is explicitly a local test policy, not production SCS or isolation against the same OS user.

Source: `program_actions.py · policy.py · test_integration.py`.

## 20 — Real runtime, real provider, fixtures and unrun scope

The native dispatch is not a wrapper named Omega around Peer. It is the verified Hive app and plugin mechanism with real PeTTa. TestClient is an ASGI test transport and the caller driver is a test harness, not a substituted runtime. The new caller tests use the real default Supervisor without starting minds; the 34 upstream baseline tests use their labelled fake process driver. DeTTa is real local library storage. Mailbox and execution are actual Fusion implementations, while the payload, counterparty and policy are fixtures. The deterministic inspect operation is plumbing, not a cognitive capability. No live LLM is used. The historical chain observation is neither erased nor represented as a new same-artifact Hive-to-chain run.

Source: `m1_2-evidence.md · manifest.json`.

## 21 — Fresh verification exercises distinct layers

Counts come from the committed M1.2 verification JSON, not a new test run for this deck. The 51 fixture tests are included in the full 90-test matrix. Clean upstream DeTTa passes 62 DA and 38 storage tests; the historical dirty checkout passed 40 storage tests because it included two local additions. The native baseline is 34 selected tests, not the full Hive suite. The new real-caller suite has 13 cases covering success/replay, three caller kill points, worker death, route backpressure, worker revocation and six negative conditions. All final run commands returned zero; native JUnit records no failures, errors or skips. Development failures and their corrections remain in the evidence directory. No new benchmark or integration run is implied by rebuilding the presentation.

Source: `evidence/m1_2/verification.json`.

## 22 — One trace ties native intent to acknowledged outcome

Full source values: actor user:operator; swarm s_2ccf3f15; input ref a1b8c6b7-5dce-58c2-8880-c8492bbc3b36, digest 2e1748d637a3c6173c6021f3597fa403a43293c21f5ac861ce7921a90d7276b9, 53 bytes. Job and completion delivery ID 37fb2f12-9a0b-5eb7-9927-31208c06c687. Correlation and caller receipt 0573fa6e03b2edbc73855e849eab46b8c93d223c96cc67d4d5b8828cf96e7306. Result ref aa57a16c-94e2-5d5d-9ee7-121ae3dbfc82, digest cd2f727689b41e243ee78207d058d00b8be64932abbfd86a02851dfcbac400bb. Both atom receipts identify detta-local-rs/1, local-files-process-restart, six shares and threshold four, with no chain or custody certificate. Native outcome is done after result verification and acknowledgement. The initial job receipt still says queued/not-observed because it describes acceptance. This artifact was not submitted to a chain in M1.2.

Source: `evidence/m1_2/hive-trace.json`.

## 23 — Reproduction separates source, build and execution

Source obtainability, buildability and a passing integration are separate questions. Authorized SSH fetches retrieved the exact Hive and DeTTa commits. Public pinned PeTTa/SWI sources and SWI submodule commits identify native inputs. The native build took 139.595 seconds on the recorded host; it observed Prolog-to-Python 42, Python-to-Prolog 2, and a generated PeTTa expression 42. It compiled a private SWI prefix and installed hash-locked dependencies, rebuilding Janus with --no-cache against that prefix. No prior venv, target or binary was copied. Python and Cargo download caches were warm; an entirely empty-cache build is unrun. The CMake cache-type guard and inherited virtual-environment issue were corrected and recorded. The verifier-only import-order correction was obtained by Git fast-forward before the final tests. None of these engineering choices changes upstream source or implies production deployment portability.

Source: `build_hive.py · native-build.json · verification.json`.

## 24 — Nine required gates passed; chain remains unrun

This board is generated from the M1.2 manifest. All nine required gates pass within the documented local profile. CHAIN is NOT_RUN, not failed and not a fixture substitute. Historical F1R3 reproduction remains blocked for its undistributed dirty source and untracked input; it would need authorized exact changes or a separately validated clean rebaseline. That optional source distribution issue does not block Hive-to-DeTTa. Empty-cache builds and the full Hive suite are intentionally unrun. Source availability alone does not pass the entrypoint or real-provider gate. Executed failed attempts remain recorded separately from the final successful run.

Source: `evidence/m1_2/manifest.json`.

## 25 — The real caller is proven; the cognitive increment is next

The stopping point moved from a missing Hive runtime to an evidenced native seam, without implementing M2. The next separately authorized increment can now be chosen from actual integration findings: private episodic provenance and explicitly profiled belief revision remain the cognitive roadmap, followed by attention and bounded inference. Existing upstream mathematics is not redefined here. Production transport/auth/isolation, distributed custody, independently verified proofs, performance characterization and live state migration remain outside this experiment. The minimal caller receipt is not a substitute for episodic memory. Do not describe the future entire Hive workflow or cognition as complete because one deterministic operation is integrated.

Source: `ADR 006–007 · m1_2-evidence.md`.

## 26 — Modularity now survives a real caller restart.

Close on the demonstrated change: a pinned real Hive runtime now invokes the same contracts and recovers across actual caller and worker process death. The consumer remains backend-independent, DA remains application-neutral, owner commits remain separate, and current authority still applies on replay. A fixture is labelled as a fixture; a historical chain observation does not become a new real-caller chain pass. The complete evidence, exact sources, build recipe and failure history are available in the repository. This presentation updates the explanation of completed M1.1/M1.2 work; it adds no runtime or cognitive implementation. Pause for discussion before the appendices.

Source: `M1.2 implementation bb22ef5 · evidence 4ee5cbe`.

## 27 — Implementation map: adapt at the native boundary

The actual adapter is integration/hive/program/program.py, registered by plugin.json. It owns only the caller receipt. native_caller.py is a test transport around the unmodified app, not a runtime replacement. The plugin invokes the same public validated binding as protocol consumers. Service is an authenticated facade; owner logic is now in atoms.py, messaging.py and execution.py, not all in service.py as the original deck suggested. composition.py alone selects concrete owner implementations. Execution depends on AtomStorage and trusted CompletionDelivery. The file fixture is independent of AtomOwner. The original Rust opaque adapter remains unchanged. Chain composition remains separate and unrun by this native flow.

Source: `integration/hive/ · fusion/`.

## 28 — Specified cognitive contracts carry test obligations

Episode expected_sequence and belief expected_revision make concurrent updates explicit. Replayed evidence must not add weight; derived cycles and overlapping roots cannot manufacture independent support. Reachability's guarded trueagi-pln-stv-finite-k1/v1 implementation is a candidate for review, not a selected universal model. metta-attention exposes STI/LTI/VLTI and direct setters, so it cannot be silently advertised as the proposed STI-only policy. Attention requires a declared budget, saturation, conservation or nonconservation, decay and tie-breaking behavior. Inference control must bound feedback generations and work, and define durable checkpoint semantics before advertising crash safety. These obligations belong to future milestones; new cognitive services remain absent.

Source: `ports.py · contracts.md`.

## 29 — Typed failures preserve the caller’s recovery choices

Permanent-for-unchanged-request failures also include INVALID_ARGUMENT and DEADLINE_EXCEEDED. INTERNAL is reserved and not automatically retryable. NOT_AVAILABLE covers missing persisted DA for a known ref and queued results; NOT_FOUND is absent metadata. Overload never silently drops acknowledged work. When transport fails after acceptance, the caller can retry the same semantic mutation or query the job owner. Already accepted mutations recover their original receipt even after the deadline expires, while new admissions and worker starts still honor the deadline. Empty poll means an authorized, known-empty inbox; failures do not become empty recall results. Live policy still applies to retries.

Source: `contracts.md · service.py`.

## 30 — Exact source identity includes the rebaseline

Full tested Fusion commit: bb22ef5e28b089b80132b40bcf5a1bbfc38b065b. Evidence snapshot: 4ee5cbe8b84689a5d2432530083738b263142f90. Hive 34b0fb32ab3806e5609fc89bb7535518a35e1aea; clean DeTTa 272888f264dd2dde18b574cabb53c266b0dac2ec; PeTTa ae66fa8e41dcd5539d614706bd4e5cfb34f9608d; SWI 69775434c8226897626b226aefcc8266499f1e2e; schematics 4af00db4e395375484dd48d0b9068a59afcf01f8. The native build used Fusion 1a627b0; only verifier import ordering changed before bb22ef5 verification. The final evidence descendant changes no implementation. Rust/Cargo 1.88.0, CMake 3.16.3, GCC 9.4.0 and uv 0.10.7 are recorded. Original supplied siblings remain unchanged. Historical F1R3 used a dirty tree at 9ec1096e1077 plus an untracked input; that historical source state is not distributed by the new recipe. The selected Hive revision is the one named by the supplied schematics, not a silent choice of remote HEAD.

Source: `m1_2/manifest.json · final-source-state.json`.

## 31 — Reproduce the selected gates from a fresh checkout

Run both two-line commands from a fresh Fusion checkout at the evidence revision or a reviewed descendant. artifacts/native must be absent or empty: the build refuses to overwrite existing work. SSH must already authorize access to the exact Hive and DeTTa repositories and host keys must be established. Public PeTTa and SWI sources are fetched at full commits. Cargo uses offline locked downloads; the native pip step uses hashes and --no-cache and builds Janus for the private SWI prefix. No dependency target directory, venv or binary is copied from the original workspace. The verifier deliberately hides real source paths for fixture-only testing, then runs the four-way matrix, upstream DeTTa, native baseline and actual caller tests. Chain is separate and not run. The runbook explains Linux prerequisites, missing optional native headers, the CMake guard correction and cache population limits. Building this deck does not rerun those integration tests.

Source: `runbook.md · build_hive.py · verify_m12.py`.

## 32 — Historical M1: one result reached an isolated chain

Preserve this historical result without promoting it into the new real-caller gate. The M1 chain JSON records pending, included with effect finality Pending, then finalized, at height 3 with no execution error, no rejection and cost 351 phlo. The committed digest belongs to the original protocol-peer result, not the generated native Hive result on slide 22. The M1 adapter used a registered approved digest, injected signer and durable signed intent against one isolated local node. That source had local changes and an untracked input. Exact historical reproduction remains blocked until those authorized bytes are supplied or a different clean revision is separately validated. No chain process or transaction was run during M1.2 or this presentation update. Finality does not establish indefinite off-chain availability.

Source: `evidence/chain-demo.json · M1 historical`.

## 33 — Keep the guarantees inside their observed boundary

No new performance benchmark is presented. The original M1 single-sample timing chart has been removed from the current evidence story; those measurements remain in historical JSON. The native build and suite durations are reproducibility observations, not runtime latency or throughput claims. One local worker and one pending caller intent per dedicated route bound the tested profile. Production authorization, multi-host DA custody, generic external effects, live rolling upgrades, named-person/mind action paths, full Hive regression and all cognitive work remain unrun or unsupported. The deck makes no claim that rebuilding slides extends any integration guarantee.

Source: `m1_2-evidence.md · manifest.json`.
