# Codex handoff — Fusion M1.2: reproducible handoff and one real Hive caller

## 1. Objective and stop boundary

Continue `machieke/fusion-module-interfaces` from the reported M1.1 commit
`ecfef54f0f0ab5b9bdce186af2e83184d10cc246` (or an explicitly recorded descendant).
Read applicable `AGENTS.md` files, the original brief, and current architecture,
contracts, ADRs, discovery and M1.1 evidence before editing. Preserve unrelated
changes and all existing scientific terminology.

**Objective:** make the existing contract slice usable from one verified,
intended Omega Hive runtime entrypoint, and establish an obtainable, repeatable
source/build recipe for the gates actually exercised. Do not redesign the module
architecture to accomplish this.

**Stop at M1.2.** No M2 episodic-memory or belief-revision implementation, ECAN,
PLN inference control, new agent framework, distributed scheduler, new consensus,
production security system, general remote-execution engine, journal migration,
live stateful provider switching, or performance-optimization programme.

A module remains a responsibility and ownership boundary, not a requirement for
one process, container, database or repository per module. Concrete runtime
integration may target a pinned Omega version without making the shared
contracts dependent on that version.

This is a proposed engineering increment. It does not select the community's
final AtomSpace representation, numerical model, or Omega product release.

## 2. Review basis and baseline status

A source review retrieved the exact M1.1 commit patch and commit-specific files
on 2026-10-16. The reviewer inspected the changed ports, composition, owners,
bindings, response validation, tests and checked-in reports. The reviewer did
**not** independently execute the repository suite. Validate all conclusions
against the actual checkout before changing code.

M1.1 reports the following results; these are historical evidence, not passes for
this task:

- Baseline: 27 tests; final local suite: 90 tests.
- Fixture-only isolation: 51 tests with DeTTa deliberately unavailable. These are
  a subset of the final suite, not 51 additional distinct tests.
- Upstream DeTTa: 62 DA and 40 storage tests.
- Four provider/transport workflows and four final worker-authorization rechecks.
- PORTS, SWAP, RECOVERY and WIRE passed within their documented local profiles.
- OMEGA was BLOCKED. The optional real CHAIN gate was NOT RUN.
- Clean-checkout reproduction was BLOCKED by undistributed dependency changes.

The source now gives execution `AtomStorage` and trusted `CompletionDelivery`
dependencies. Atom persistence, execution terminal state/outbox, and mailbox
acceptance have separate commits and durable replay. Preserve this design.

Important limits:

1. The module replacement experiment starts with fresh stores; it does not move
   existing references or accepted jobs between providers.
2. The observed durability is same-host process restart with persistent files
   intact, not power-loss survival, distributed failover or indefinite DA custody.
3. The file provider is an independent contract fixture, not another DA network.
4. Wire version is still 1.0.0. `durable-mailbox/2` and `inspect-atom/2` are exact
   behavioral profiles, not a claim of live 1.x rolling-upgrade interoperability.
5. Descriptor hashes establish binding consistency, not remote identity,
   authentic execution, or proof of provider guarantees.
6. The deterministic `inspect_atom` output algorithm remains version 0.1.0.

## 3. Source ledger

Use the existing files rather than introducing a parallel specification:

| Source | Why inspect it |
|---|---|
| `docs/module-interfaces/m1_1-evidence.md` and `evidence/m1_1/` | Historical source identities, runs, limits, manifests and gate results. |
| `docs/module-interfaces/discovery.md` | Exact blocked Hive seam and rejected substitute projects. |
| `docs/module-interfaces/contracts.md` and `decisions.md` | Named profiles, replay semantics, privacy and explicit ownership. |
| `fusion/ports.py`, `contracts.py`, `registry.py` | Declared operations, schemas, independent consumer requirements and selection. |
| `fusion/atoms.py`, `execution.py`, `messaging.py`, `service.py` | Exercised owner boundaries and separate commits. |
| `fusion/composition.py`, `bindings.py`, `responses.py`, `policy.py` | Operator selection, caller-bound authority and validated replies. |
| `tests/test_contract.py`, `test_m11.py`, `test_responses.py` | Shared conformance, failure injection and negative response tests. |
| `scripts/preflight.py`, `discovery.py`, `verify_m11.py` and the runbook | Current source discovery, commands and gate classification. |
| `fusion/adapters/f1r3.py`, optional chain scripts | Existing isolated commitment path; do not replace its signer or approval rules. |

The prior discovery identifies **PhysixSNET/omegahive** as the intended runtime
pointer. It does not supply a verified runtime commit, callable symbol, supported
request shape or launch command. `omegahive-start-here` is onboarding and
`hive-appliance` is a separate appliance/controller project. Neither is the
intended runtime. Their presence cannot pass the real-caller gate.

## 4. Definition of ready: resolve source inputs once

### A. Confirm the actual runtime

Check the explicitly supplied paths, known authorized workspace and handover
materials in one bounded discovery pass. Use existing authorized access to the
named runtime if available. Do not repeatedly scan unrelated projects, infer
private credentials, copy private histories, or substitute a similarly named
agent implementation.

Record:

- Runtime repository identity, exact commit and relevant local modifications.
- The source path and callable/registration point for the selected existing
  memory, tool or transformation entrypoint.
- Its current request/response contract, lifecycle, startup command and a native
  baseline check that runs before Fusion is attached.
- Required dependencies and configuration. Record credential names/references,
  not credential values.
- Evidence that this is the intended integration target. A product decision
  resolving ambiguous versions must be recorded, not invented by Codex.

If no verified intended source is available, mark `HIVE_SOURCE=BLOCKED`, produce
one concise missing-input record, and do not implement runtime-specific code.
Do not create an Omega-named wrapper around `Peer`, an empty adapter class or a
new mock runtime to make the gate appear complete.

The missing-input record should request the authorized runtime checkout/access,
exact intended revision, startup/dependency recipe, entrypoint guidance if known,
and permission/ownership for any required upstream integration patch. Avoid a
second broad request for information that the workspace already contains.

### B. Establish a fresh baseline

Run the current fixture-only suite. Run the full M1.1 and upstream DA/storage
suites when their real dependencies are available. Existing commands include:

```bash
uv run --python 3.11 python scripts/verify_m11.py --fixture-only
uv run --python 3.11 python scripts/verify_m11.py
# In the selected secured-contract-spaces checkout:
cargo test --offline --locked -p detta-da -p detta-storage --lib
```

Record exact commands, toolchains, source identities, failures, skips and missing
prerequisites. Do not require the optional chain build to run fixture or
Omega-to-DA tests. Do not treat a blocked real gate as a fixture pass.

The existing baseline DeTTa source is recorded at HEAD
`272888f264dd2dde18b574cabb53c266b0dac2ec` **plus local changes**. Historical F1R3
source is HEAD `9ec1096e10774926ea8e72f0823482f0bf9213e1` **plus local changes and
an untracked source file**. These HEADs alone do not reproduce the recorded runs.
Do not change, reset, stage or publish the sibling worktrees to manufacture a
clean baseline.

## 5. Reproducible source and build handoff

Separate three questions in the evidence:

1. Can another authorized developer obtain the exact relevant source bytes?
2. Can those bytes and locked dependencies build in the documented environment?
3. Did the resulting runtime actually pass its integration gate?

Reuse the current manifest/preflight facilities. Make prerequisite paths
configurable where necessary; do not add another registry or dependency manager.
Do not let the historical M1.1 hard-coded BLOCKED observations become the result
of a new run without checking the new prerequisites and recording new evidence.

Preferred routes are obtainable immutable commits or an explicitly authorized,
versioned patch/source bundle applied in a disposable checkout. Source access may
be restricted to authorized collaborators; reproducibility does not require
publishing private source. Never bundle credentials, private memories or unrelated
working-tree changes.

When exact historical modifications cannot be supplied, an authorized new clean
revision may be selected and **rebaselined**. Compare relevant source changes,
retain the old evidence, and rerun the full applicable suite. Do not represent a
new provider revision as reproduction of historical bytes or assume behavioral
compatibility solely from a passing build.

Document locked Python/Rust/runtime dependencies and native build prerequisites.
Distinguish a recipe requiring a pre-populated offline cache from a build that
has actually been tested from an empty cache. Never use unqualified “clean-room
reproducible” for a run that reused undistributed artifacts.

Test the supported recipe from a fresh disposable directory without copying
unlisted artifacts from the original workspace. Scope reproducibility by gate:

- Fixture-only conformance.
- Real DeTTa integration.
- Real Hive integration.
- Optional chain integration.

Missing F1R3 source must not block an otherwise reproducible Hive-to-DeTTa slice.
If authorized DeTTa sources remain unobtainable, leave that reproduction gate
BLOCKED with a precise input list; complete the useful available work and stop.

## 6. One real runtime adapter, only after source verification

Select the smallest existing supported extension point. Prefer its registration
or plugin mechanism. Preserve the runtime's native API; implement translation at
the boundary. If an upstream patch is necessary, keep it narrow and separately
reviewable, and obey that repository's write/commit permissions.

The actual invocation must pass through runtime dispatch, tool invocation,
transformation evaluation or an equivalent verified native mechanism. Importing
a helper in a test script while bypassing that dispatch is adapter-level testing,
not a real-runtime integration pass.

Do not require a paid or live LLM just to prove deterministic interface plumbing
unless the actual runtime makes that unavoidable. Any substituted model/external
service must be labelled, while the actual runtime dispatch path remains real.
No synthetic model output is evidence of cognitive capability.

A generated, explicitly shareable input follows this bounded workflow:

1. A real runtime operation stores bytes through the selected AtomStorage
   interface. Retain the scoped reference and actual persistence receipt.
2. It sends or consumes that reference through Messaging. A fixture counterparty
   is acceptable and must remain labelled as a fixture.
3. It submits the existing `inspect_atom` operation through DelegatedExecution,
   with a stable idempotency key, correlation ID and caller-owned reply route.
4. The existing worker reads and persists through AtomStorage, then commits
   terminal state and outbox; Messaging durably accepts completion.
5. The real runtime receives/polls the correlated completion, retrieves and
   verifies the result through the existing interfaces, records its accepted
   outcome, and acknowledges delivery.
6. A restarted caller recovers pending context from durable local state or
   authoritative status, rather than assuming an empty in-memory correlation map
   proves causality. `/2` status can recover known job context; preserve the
   existing documented limits for unsolicited completions.

Prefer the existing in-process/private-stdio bindings on a trusted development
host. Do not silently expose the test credential policy as a production network
service. No new HTTP stack, websocket bus, distributed orchestrator or discovery
protocol is justified without a concrete incompatibility in the verified target.
If an unsupported deployment boundary is essential, record that boundary as
blocked instead of inventing production guarantees.

The adapter must not construct concrete storage owners, access foreign tables,
call private helpers, bypass descriptor-bound validation, or place provider-
specific branches inside Omega's business logic. Use the narrowest existing
validated boundary; do not bypass wire admission/replay merely because a typed
session can be imported directly.

Keep private histories and real personal data out of the shared slice. The
current sharing profile permits generated non-sensitive fixtures; do not quietly
promote it into a general private-memory integration.

## 7. Integration acceptance and recovery cases

Reuse the existing four-way provider/transport conformance matrix. Do not rerun
it under an Omega label and call that the new integration test. The new tests
must traverse the selected actual runtime entrypoint.

At minimum demonstrate a real-Hive/real-DeTTa happy path and representative
failure/recovery paths:

- Lost response after durable admission: retry with the original semantic input
  and key; do not generate a second job identity on a transport timeout.
- Worker termination after result persistence and before terminal/outbox commit:
  restart and recover one logical persisted result and completion.
- Caller termination after submission and before consuming completion: recover
  job context, correlate the result, and complete without relying on old RAM.
- Completion redelivery, including a caller crash after accepting the result but
  before acknowledgement: deduplicate the runtime-visible outcome. Reuse an
  existing caller-side durable receipt/acceptance mechanism where possible; add
  only a minimal boundary record if none exists, not a new episodic-memory module.
- Temporary storage failure or a full/unavailable reply route: retain the job or
  outbox according to the existing contract; do not convert failures to empty
  memory, dropped callbacks, or success.
- Wrong scope, revoked authority and an incompatible provider/profile: fail
  closed through the actual runtime path. Preserve stable request semantics.

Do not promise exactly-once physical execution or arbitrary external side effects.
The existing executor is deterministic and bounded; integration must not expand
its operation set. Preserve the distinction between persistence, job completion,
mailbox acceptance and recipient acknowledgement.

Use failure injection already present. Assert observed durable state and result
identity rather than timing-dependent sleeps. Test counts are consequences of
coverage, not a target to inflate.

## 8. Optional chain observation — separate gate

Only when the already supported isolated node prerequisites are available, reuse
the existing approval, signer and durable signed-intent implementation to anchor
the generated result digest from the **same real-runtime workflow**. Record the
link from runtime invocation to scoped input, job, persisted result digest,
commitment, deploy ID, inclusion and deploy-effect finality.

Do not submit an unrelated demo digest and call it end-to-end integration. Do not
replace signing, broaden deploy permissions, attach to a public network, or claim
that anchoring a digest executes Omega or PLN on chain. An isolated local
single-validator observation is not a multi-validator safety or availability test.

If not executed, record `CHAIN=NOT_RUN` or a specific prerequisite `BLOCKED`.
Historical M1 evidence remains historical. The chain gate is not a dependency of
the contract, DA or real-caller gates.

## 9. Deliverables and outcome rules

Update the existing docs and implementation, with a small new M1.2 evidence
report and machine-readable run manifest. Deliver:

- Verified runtime source/entrypoint map, or a precise missing-input record.
- Obtainable source/build recipe and fresh-directory verification for each gate
  actually supported; unresolved source distributions stay explicit.
- Thin real adapter and runtime-dispatch integration tests, only where ready.
- Existing conformance/recovery regressions plus real-caller recovery evidence.
- A trace tying caller, references, job, completion and optional chain observation
  together, with actual values and clear component classifications.
- Changed-file list, exact commands, source/lock hashes, failures/skips, observed
  guarantees and remaining limitations. Keep private inputs out of evidence.

| Gate | PASS condition / honest alternative |
|---|---|
| BASELINE | Fresh applicable M1.1 tests executed on exact recorded sources; missing real dependencies separately BLOCKED. |
| HIVE_SOURCE | Intended runtime/revision and actual entrypoint/startup verified; otherwise BLOCKED, with no speculative adapter. |
| FIXTURE_REPRO | Fresh-directory fixture run succeeds from declared inputs without DeTTa; never passes real DA or Hive. |
| DETTA_REPRO | Obtainable exact source/build inputs pass fresh real DeTTa suite; warm-cache assumptions explicit. |
| HIVE_ENTRYPOINT | Native runtime dispatch actually invokes the thin adapter; no renamed fixture or bypassed dispatch. |
| HIVE_DETTA | Same actual runtime workflow uses real DeTTa and existing execution/messaging interfaces; one real caller plus fixture remains labelled accordingly. |
| HIVE_RECOVERY | Actual caller restart/redelivery and representative worker/provider failures recover the documented logical outcome. |
| HIVE_REPRO | Another authorized fresh checkout can follow the declared recipe and run the real slice; otherwise source/build blockers explicit. |
| CHAIN | Separate actual same-artifact isolated commitment/effect observation, or NOT_RUN/BLOCKED. |
| SCOPE | No cognitive implementation, framework rewrite, live migration, invented runtime, or production-security claim. |

A successful fixture run, an accurate source manifest and a blocked runtime are
useful outputs, but together they do not constitute successful Hive integration.
Preflight availability is not a test pass. Missing prerequisites and genuine
executed failures must remain distinguishable; an intentionally unrun gate is not
a suppressed test failure.

Stop when the available scoped work is complete and report all gates. If the
runtime and dependency sources are both unavailable, deliver the concrete
handoff requirements and any useful fixture-reproduction result, then stop
rather than filling the task with additional generic infrastructure.

## 10. Next decision, not permission to continue

After an evidenced real-caller slice, choose the next increment from actual
integration findings. The cognitive roadmap remains private episodic provenance
and explicitly profiled belief revision, followed by STI and bounded inference.
It is a separate workstream: a missing Hive checkout does not conceptually make
those modules depend on a particular Omega version. Do not implement them under
this handoff or silently select a numerical model to keep busy.
