# M1.1 evidence — exercised ports and independent AtomStorage replacement

Executed 2026-10-16 in `/home/purplezky/work/takopi/fusion-module-interfaces`.
M1.1 A/B are complete on the available local runtime. The real Omega seam is
**BLOCKED**; the optional real chain gate was **NOT RUN**. No M2, C1/C2, ECAN,
inference controller or new agent framework was implemented.

## Source state and review verification

The initial checkout was commit **6d879650f56046925f85f034d5fb9eda54cd16e1**.
Tracked files were clean; the only initial untracked file was the user-supplied
`codex_fusion_m1_1_module_swap_and_omega_seam.md`. The previous implementation
commit was `3f75db993d354d18dff2a3e36498eabe4a33afb3`. Applicable workspace and
upstream instructions were inspected; no instructions authorized rewriting sibling
source. No sibling source was reset, edited, staged or committed.

The baseline's exact dependencies and logs are preserved in
[evidence/m1_1/baseline](evidence/m1_1/baseline). The final local gate's
[full-preflight.json](evidence/m1_1/full-preflight.json) records all dependency
working-tree/source/diff hashes, implementation file hashes, build locks, paths,
remotes, toolchains and tested worktree state. The
[execution-manifest.json](evidence/m1_1/execution-manifest.json) binds those hashes
to the resulting adapter binary, verification and demo artifacts, and records
final file hashes separately from the full-suite input hashes. These identify
tested bytes; they do not distribute another person's source modifications.

| Inspected dependency | HEAD at baseline and final gate | State |
|---|---|---|
| omegahive-start-here | `0b15d2bed730950feedc6a525d340215c0a4da1a` | Clean onboarding; intended runtime absent |
| metta-attention | `3e1c8147dc17299d17ab34720334fc19277cb6a9` | Clean; no ECAN runtime used |
| das | `8afab5daa635af253ebf6776d1e3de0b54c355e7` | Clean; no DAS service used |
| mettaclaw | `d2da47207fecbcd9d08d3bf50b480b7f1b09bd43` | Existing untracked trees retained; no real consumer integration |
| reachability-atomspace-prototype | `dd56f3f053ed90239de5377021a7d3b3fbf424ac` | Clean; cognitive candidates remain deferred |
| secured-contract-spaces | `272888f264dd2dde18b574cabb53c266b0dac2ec` | Dirty source actually linked and tested |
| f1r3node-rust | `9ec1096e10774926ea8e72f0823482f0bf9213e1` | Dirty, including untracked deploy_resource_limits.rs; no new real chain run |

All nine dependency records (including the earlier legacy registry candidates)
match the initial baseline's commit, source hashes, diff hash and worktree status.
The additional hive-appliance inspection was clean at
`68cf39c3c44379479e19ae0ae3bf11b344f4fd33`; it is a different appliance/controller
project and was not selected as Hive runtime.

DeTTa's tracked-diff SHA-256 is
`8c1c5fb65bf35111e8d4b348ebcef1831065b71c30ae1bac84a951f2247b195f`.
Its linked dirty `crates/detta-storage/src/lib.rs` SHA-256 is
`a3e52dc911963f70035bf8f712f1b981911eb3b8987d4402de9dfcec86e949d1`.
F1R3's tracked-diff SHA-256 is
`44cdd424b690eb2fe218f611b73168b2b1b1c056b420174f1a9d15e09fe25ab6`;
its untracked `deploy_resource_limits.rs` SHA-256 is
`78834ef475c40925f3cc47091d97c52a281b7ee60fc5567fb4562a72b4fcb3ca`.
Those patches are not supplied here. Clean-HEAD reproduction is **BLOCKED** until
authorized exact modifications are available or a new immutable source is tested.

Toolchain: Python **3.11.14**, uv **0.10.7**, Cargo **1.88.0**, rustc **1.88.0**.
The installed F1R3-pinned `nightly-2026-02-09` reports rustc 1.95.0-nightly; observing
that toolchain does not constitute running the chain gate. The runtime uses stdlib
Python; JSON Schema tests use the pinned development dependency. Builds were
`cargo build --offline --locked` against the actual external working source.

| Review finding | Verified against initial checkout | M1.1 disposition |
|---|---|---|
| F1 port drift | Service constructed owners; execution used AtomOwner.row and concrete get/create conventions; availability absent from protocol | Concrete selection moved to composition; typed facades exercised; public atom reads and CompletionDelivery.accept replace private calls |
| F2 backend-specific shared receipt | Shared acceptance/ack types contained sqlite-full | Neutral process-restart types in exact `/2` profiles; evidence separate; explicit `/1` local encoders preserve old shapes |
| F3 compatibility narrower than architecture | Live dispatch/client only 1.0.0; additive 1.2.3 descriptor fixture | Remains 1.0.0; selected descriptor bound to actual invocation/reply; no live rolling-upgrade claim |
| F4 dirty dependencies | Linked DeTTa and historical chain used modified/untracked source | Machine-readable preflight records identity/availability; clean reproduction remains blocked, no private patches published |
| F5 missing real Omega | Onboarding existed; intended omegahive/hive runtime absent | Rechecked, still BLOCKED; precise seam note, no relabelled fixture adapter |

## Design and changed files

The existing [architecture](architecture.md), [contracts and method map](contracts.md)
and [ADRs](decisions.md) are updated in place. The original evidence report and
presentation are preserved as historical M0/M1 snapshots.

| Changed files | Purpose |
|---|---|
| `fusion/ports.py`, `contracts.py` | Reconciled typed AtomStorage surface including availability; trusted completion port; neutral receipts and exact profile boundaries |
| `fusion/atoms.py`, `policy.py` | Real atom owner with its own metadata/replay transaction; caller/worker-bound facade; live authorization |
| `fusion/adapters/fixture_atoms.py` | Independent atomic-file test provider, no AtomOwner inheritance/SQL; bounded fsync/rename/replay; UUID IDs cannot become filesystem paths |
| `fusion/messaging.py`, `execution.py`, `service.py` | Separate owner stores; typed calls; stable result replay key; durable outbox/acceptance replay; explicit `/1` encoder; current route checks before cached acknowledgement replay |
| `fusion/composition.py`, `registry.py`, `bindings.py`, `host.py` | Sole operator-selected provider construction; fixed consumer requirements; descriptor-bound invocation; private delivery/worker boundary; independent-commit failpoints |
| `fusion/responses.py`, `contracts/{wire,responses}.schema.json`, `scripts/schema.py` | All operation/profile response shapes; semantic reference/scope/correlation/state/guarantee validation; malformed replies fail closed |
| `tests/{support,test_contract,test_m11,test_responses}.py` | Shared invariant matrix across two providers/two transports; hostile port/type/SQL checks; independent commit SIGKILLs; negative wire and migration/path checks |
| `scripts/{demo,discovery,preflight,swap_demo,verify_m11}.py` | Actual selected provider reporting; source/preflight metadata; real vs fixture gates; four unchanged workflows and fixture-only verification |
| `README.md`, `docs/module-interfaces/{architecture,contracts,decisions,discovery,runbook,m1_1-evidence}.md`, `evidence/m1_1/*` | Current contracts/ownership/reproduction, blocked Omega seam and preserved fresh evidence |
| `codex_fusion_m1_1_module_swap_and_omega_seam.md` | User-supplied task brief retained |

`fusion/client.py` and the opaque Rust DeTTa adapter are unchanged. Execution has
no provider-specific branch: it consumes `AtomStorage.get/create` and trusted
`CompletionDelivery.accept`. Caller and worker principals are bound in trusted
composition; injected ports do not let wire callers choose authority.

AtomStorage commits a scoped result using `result/job_id` before execution commits
terminal state plus outbox. Messaging commits completion acceptance before the
outbox marks sent. Separate owner replay records close both gaps. Physical work
may repeat, but the tests observe one logical result and one logical completion.
No transaction spans all three owners. Atom create's semantic intent digest also
preserves key conflict detection before wire admission commits.

The new messaging/execution `/2` profiles use process-restart guarantees with
backend evidence separate. `/1` keeps its local SQLite literals and field sets.
Live wire version is 1.0.0; descriptor implementation is 0.1.1. The deterministic
inspect payload algorithm stays 0.1.0 to preserve output bytes. Old combined M1
journals are rejected without dropping their data; no migration is attempted.
The module replacement demonstration uses fresh stores, not a populated-namespace
migration or a live hot swap.

## Executed commands and results

| Command / classification | Result and evidence |
|---|---|
| Before edits: `uv run --python 3.11 python scripts/verify.py` | **27 passed**, zero failures/skips; two real DeTTa workflow demos. [Baseline log](evidence/m1_1/baseline/tests.log), [verification](evidence/m1_1/baseline/verification.json), [demo](evidence/m1_1/baseline/demo.json) |
| Final: `uv run --python 3.11 python scripts/verify_m11.py` | **90 passed** in 58.361 s, zero failures/errors/skips; locked offline adapter build; four swap demos. [Tests](evidence/m1_1/tests.log), [verification](evidence/m1_1/verification.json), [build](evidence/m1_1/build-detta.log) |
| `DETTA_REPO=/tmp/fusion-m11-deliberately-absent-detta uv run --python 3.11 python scripts/verify_m11.py --fixture-only` | **51 passed**, zero failures/errors/skips; two fixture demos with real source deliberately absent. [Tests](evidence/m1_1/fixture-tests.log), [verification](evidence/m1_1/fixture-verification.json), [missing-source manifest](evidence/m1_1/fixture-preflight.json) |
| In secured-contract-spaces: `cargo test --offline --locked -p detta-da -p detta-storage --lib` | **62 DA + 40 storage passed**, zero failures/ignored. [Fresh upstream log](evidence/m1_1/upstream-detta.log) |
| `uv run --python 3.11 python scripts/schema.py`; `git diff --check` | Schemas regenerated; exact generated-file/schema validity checks included in the suite; no whitespace errors |
| Optional `scripts/build_chain.py` / `scripts/chain_demo.py` | **NOT RUN** in M1.1. Two chain observation/signed-intent unit fixtures passed; they do not pass the real chain gate |

The 90-test total comprises 36 common contract cases, 32 additional recovery
cases, six structural/placement/path tests, seven response conformance tests,
two resolver/schema compatibility tests, five real DeTTa adapter tests and two
chain unit-fixture tests. The shared contract and recovery cases execute under
both AtomStorage providers and both transports. The fixture-only total is a
subset, not another 51 distinct tests.

Development runs also passed: the then-existing 45-test expanded suite, four
initial port tests, 32 initial new recovery/port tests, seven focused response
tests, an 88-test full intermediate run, and a 49-test fixture-only intermediate
run. Final runs include subsequent route/path/migration regression additions.
No test failures were suppressed or replaced with fixture evidence. Final whitespace
cleanup removed one trailing blank line from policy.py and the checked-in upstream
log; the manifest records both byte identities and the original raw log hash. The
four worker-revocation cases were then rechecked under both providers/bindings
(**4 passed**; [log](evidence/m1_1/policy-recheck.log)); no executable logic changed.

The [four-run swap report](evidence/m1_1/swap-demo.json) records real IDs, receipts,
selected providers, output bytes/digests, counts and timings:

| AtomStorage | Binding | Workflow seconds | Observed final state |
|---|---|---:|---|
| Real DeTTa DA/FileStorage | in-process | 0.889 | 2 atoms, 1 job, 1 outbox row, 2 messages; zero pending outbox |
| Real DeTTa DA/FileStorage | subprocess | 2.249 | Same logical counts; zero pending outbox |
| Independent atomic-file **fixture** | in-process | 0.407 | Same logical counts; zero pending outbox |
| Independent atomic-file **fixture** | subprocess | 1.785 | Same logical counts; zero pending outbox |

Every run stores/shares/fetches generated bytes, delegates inspect_atom, kills the
worker after result persistence and after terminal commit, restarts the caller,
retrieves the result, delivers correlated completion and acknowledges it. The
recovery suite additionally kills after mailbox acceptance before outbox marking
and after atom persistence before admission commit. Each demo has two fixture
peers and a real separate deterministic worker process. Only the DeTTa rows use
real DA libraries; none is an Omega or chain integration. These single-slice
measurements are not SLA, throughput capacity or distributed custody claims.

## Observed guarantees and limits

- Common behavior survived provider replacement: immutable scoped bytes,
  ordered getMany, duplicate replay/conflict, live caller/worker revocation,
  recipient isolation, bounded overload, unavailable input recovery, delayed
  and revoked reply routes, caller/worker restart and correlated completion.
- Result metadata survived the cross-owner crash window and replay returned the
  same public AtomWrite. Mailbox acceptance survived the next crash window;
  retry did not duplicate completion, even after recipient acknowledgement.
- Selected descriptor mismatch was rejected before mutation. Weaker guarantees
  were rejected. Missing/malformed replies, unknown errors/states, wrong scope,
  reference order/digest or known correlation, and exaggerated durability were
  rejected. These checks establish protocol consistency, not remote truth.
- Same-host process-restart is the bounded guarantee. Power loss, disk failure,
  distributed failover, remote provider proofs, production authorization, GC,
  journal migration and live 1.x upgrades are unproven. The file provider is a
  contract fixture with one local copy, not a second real DA network.
- Correlation can be compared only when the caller knows the job context; `/2`
  status lets a restarted caller recover it. An unsolicited completion with no
  known context receives structural/context validation, not causal proof.
- The F1R3 adapter/signing/approval behavior is unchanged and its unit fixtures
  pass. Historical real isolated finality evidence remains in the M1 report;
  this task did not produce another deploy or assert new chain finality.

## Gate-by-gate outcome and stop

| Gate | Result | Boundary |
|---|---|---|
| BASELINE | **PASS on recorded working bytes** | Initial 27-test gate rerun; full source/toolchain manifests. Clean-HEAD reproduction separately **BLOCKED** by undistributed dirty dependency changes |
| PORTS | **PASS** | Runtime typed facades, all-operation map, hostile port/type/SQL checks; no execution private AtomOwner access |
| SWAP | **PASS** | Real DeTTa plus independent file fixture, unchanged consumer/worker workflow, both bindings; insufficient guarantees rejected |
| RECOVERY | **PASS** | Original regressions plus independent atom/result/mailbox commit SIGKILLs and stable replay |
| WIRE | **PASS for live 1.0.0 and named profiles** | Complete structural/semantic response checks; explicit `/1` compatibility and `/2` neutral receipts; descriptor bound to invocation |
| OMEGA | **BLOCKED** | Missing authorized intended PhysixSNET/omegahive runtime/revision/entrypoint; [precise seam note](discovery.md#m11-omega-runtime-seam-blocked). Onboarding/appliance/Peer do not pass |
| CHAIN | **NOT RUN (optional)** | Unit fixtures only in this increment; historical real gate not reused as a fresh pass |
| SCOPE | **PASS** | No M2/C1/C2 implementation, ECAN, inference control, scheduler or production-security claim |

Recommended next increment: supply and pin the intended Hive runtime, then execute
the bounded real-caller seam against these contracts. M2 private episodic
provenance and explicitly profiled belief revision remain a separate subsequent
task. Work stops at M1.1.
