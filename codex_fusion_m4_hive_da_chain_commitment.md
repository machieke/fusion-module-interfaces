# Codex handoff — Fusion M4: one real Hive → DA → ASI:chain commitment

## 1. Objective and stop boundary

Continue `machieke/fusion-module-interfaces` from evidence commit
`985d2f34ea8df8c5d93582e4ed6fe5cbe1843074`, whose tested implementation is
`1b17d74f2808703894ea55c9539adf264bc87976`, or record the exact descendant and
relevant intervening changes. Read applicable `AGENTS.md`, the original architecture
brief, M3.1 contracts/ADRs/evidence and the existing chain adapter before editing.
Preserve unrelated working trees and private dependency access restrictions.

**Objective:** demonstrate one authenticated native Hive operation producing an
explicitly shareable result through the existing storage/message/execution
interfaces, then committing that exact result's digest through the existing
ConsensusFinality interface to a real, isolated F1R3node. Observe the actual
on-chain effect and its deploy-effect finality, and recover the same logical
operation after caller/adapter interruption. Make the supported slice reproducible
from declared, obtainable sources.

The first chain-backed capability is **approved commitment persistence and
observation**, not on-chain PLN, ECAN, private memory, or arbitrary execution.
This is a proposed engineering increment. It does not assert that the meetings
selected a final product architecture, consensus deployment or mathematical model.

**Stop at M4.** No M3.2 cleanup programme, new cognition, extra inference rules,
LTI/promotion, general export service, marketplace/tokenomics, multi-validator
research, public-network deployment, new consensus, new validator-native plugins,
whole-program transpilation, live migration, or production security infrastructure.
Fix only defects directly preventing this slice or regressing existing contracts.
Do not manufacture progress by adding another generic interface framework.

Chain is a **required real gate in M4**, not the optional/unrun gate of earlier
milestones. A missing prerequisite permits useful partial delivery, but not a
complete M4 pass. A fixture cannot replace the real-chain outcome.

## 2. Review basis, baseline and meeting direction

The reviewer read commit-specific public implementation, tests and checked-in
M3.1 evidence. The reviewer did not independently execute the suites, inspect the
private Hive checkout, or verify/build an F1R3node in this environment. Recheck
findings against the actual checkout. Source review is not a security audit.

M3.1 records closure of C1 delivery through a trusted model-independent completion,
33 events drained in one episode in 16/16/1 batches, and owner-authoritative
Attention reconciliation on SQLite and an independent atomic-file fixture.
Its new closure profiles require fresh journals; historical populated M3 stores
remain under their historical profiles. No existing-state migration was performed.
Reconciliation does not replenish execution budgets or deliver fresh inference.

Treat the reported 12 supported PASS gates as historical evidence until rerun.
The report distinguishes 16 direct parameterized SIGKILL cases from the four
additional caller-kill cases within seven native Hive tests. Suite subsets overlap;
do not sum repeated subsets into a unique test total. Durability is bounded to
same-host process restart with intact files. Download caches were warm.

Meeting basis:
- Kevin/Kabir, 00:57:38: use implementations that meet the interfaces' required
  properties; do not force an unsuitable chain backend into every module.
- Kevin/Kabir, 01:04:49–01:07:39: version-independent module contracts and a
  prototype demonstrating a concrete chain implementation/integration.
- AGI Benchmarks, 00:11:14–00:12:40: modules request other owners' work instead of
  modifying their state.

The transcript's 20 November 2026 demonstration goal is context, not permission
to remove guarantees or claim that the full cognitive stack executes on chain.

## 3. Inspect and reuse this source ledger

| Existing source | Purpose / finding to verify |
|---|---|
| `docs/module-interfaces/m3_1-evidence.md`, `evidence/m3_1/final/verification.json` | Tested implementation identity, current local guarantees and regressions. |
| `docs/module-interfaces/{architecture,contracts,decisions,discovery,runbook}.md` | Existing boundaries, historical chain evidence and unresolved reproduction. |
| `fusion/ports.py` | Existing `ApprovedCommitment`, `ChainObservation`, `ConsensusFinality`, AtomStorage, Messaging and DelegatedExecution ports. |
| `fusion/adapters/f1r3.py` | Fixed registered approval; signed-intent journal; submit/observe HTTP mapping. |
| `scripts/{build_chain,chain_demo}.py` | Existing signer/protobuf and isolated-node launch; staging protoc; historical demo. |
| `tests/test_adapters.py:ChainObservationTests` | Existing uncertain-submission fixture and distinct inclusion/effect-finality cases. |
| `integration/hive/program/{program.py,plugin.json}` | Real authenticated `fusion-inspect` action, generated shareable input and caller receipts. |
| `integration/hive/{native_caller,test_integration}.py` | Native Programs dispatch and caller/worker recovery harness. |
| `fusion/{composition,bindings,client,registry,policy}.py` | Actual provider selection, validated boundaries and live authorization. |
| `integration/hive/sources.json`, `scripts/{build_hive,build_m3,verify_m3_1}.py` | Existing reproducible real Hive/DeTTa/cognitive baseline. |

Concrete current-chain limits to verify:
1. `chain_demo.py` takes a result from `artifacts/demo.json`, not from a native
   Hive action in the same integration run. Do not relabel that historical result.
2. Its operation writes a digest with a fixed Rholang send. The current happy-path
   gate compares deploy inclusion, non-error execution and finality; M4 must add
   direct observation of the expected state/effect, not just the submitted term.
3. `F1R3Commitments` durably records signing output before submission and reuses it
   on uncertain retry. Preserve this property; its existing timeout test is a
   transport fixture, not evidence of real-node recovery.
4. The approval owner is a trusted local composition, not a general authenticated
   Hive-facing signing service. Native access requires an explicit trusted caller
   binding, not a caller-supplied approval string or arbitrary transaction.
5. The build script selects a workspace through `F1R3_REPO`; historical evidence
   used `9ec1096e10774926ea8e72f0823482f0bf9213e1` plus modified files, including
   `casper/src/rust/rholang/deploy_resource_limits.rs`. The HEAD alone does not
   reproduce those bytes. Determine the actual available source now.
6. The old script classifies broad runtime exceptions as blocked. A new M4 verifier
   must distinguish absent inputs from executed failures and observation timeouts.
7. The runbook warns that the historical node's P2P port binds all interfaces even
   with a loopback advertised host. An isolated network label is not OS isolation.

Do not rebaseline Hive, DeTTa, PLN, PeTTa or SWI merely to add chain integration.
Use existing build artifacts only when their exact identity is verified; final
fresh-directory reproduction must rebuild the supported inputs as documented.

## 4. Resolve the real-chain prerequisites once

Perform one bounded discovery pass over authorized workspace paths and the named
F1R3 source/remotes. Record the intended repository, exact commit, local changes,
submodules, Rust/toolchain and lockfiles, protobuf inputs/compiler, build flags,
native libraries, binary hash, and runtime configuration.

Prefer an obtainable immutable source revision. If the historical modifications
are necessary, use an explicitly authorized versioned patch/source bundle in a
disposable checkout. Do not stage, publish, reset or discard another worktree's
changes. An approved clean revision may be selected as a **new baseline**, with a
source comparison and fresh behavior tests, not described as historical reproduction.
Do not change consensus/resource-limit behavior to make this integration pass.

Inspect the selected source's actual deploy, inclusion, execution-result,
deploy-effect-finality and block/state-query APIs. Record endpoint/request/response
shapes and their meaning. Existing route names are discovery candidates, not proof
that the new node provides equivalent semantics. Pin any changed observation
profile explicitly rather than guessing field names or weakening validators.

Build/start the real node before implementing a speculative native integration.
Use a disposable single-validator local genesis and test-only key. No funded
wallets, public chain, external peers or persistent user node data are in scope.
Use the existing isolation mechanism where available, or the smallest supported
sandbox/network restriction that demonstrably prevents external P2P/API exposure.
Inspect actual bound sockets and test isolation. Do not alter host-wide firewall
rules or claim loopback isolation solely from a CLI flag. If isolation cannot be
established safely, record that real-run prerequisite as BLOCKED.

A missing source, API, build dependency or permission must produce a precise
missing-input record. An executed test with incorrect behavior is FAIL, not
BLOCKED. Do not repeat broad workspace scans, invent a runtime, or launch a
consensus-debugging programme when the required source is unavailable.

## 5. Preserve the private/shared boundary

Use the **existing `fusion-inspect` generated, explicitly shareable workflow** for
the first chain slice. Its input is constructed from a bounded synthetic seed,
and its existing deterministic worker returns an inspect result through real
DeTTa. This path already has a declared shared-fixture policy.

Do not export a private M2/M3 episode, belief, task, provenance record, support ID,
attention state, private reference or private content hash. Generated test data
routed through a private profile does not automatically become approved public
input. Do not add a generic `publish(private_ref)` flag, redaction engine or
privacy-policy bypass. The cognitive demo remains a separate unchanged regression.

Approve only the actual generated result produced by this native run, after an
authorized AtomStorage retrieval verifies its bytes/ref/digest and the caller's
completed execution result. Approval must be established in trusted operator
composition under a narrow generated-artifact policy, not accepted from action
parameters. Bind approval to the exact scope, immutable result, allowed fixed
operation, target chain instance/profile and relevant limits. An approval cannot
be obtained by presenting a structurally valid DTO or content hash alone.

Use an operator-owned allowlist for what can leave the runtime. Normal native
requests must not supply code, arbitrary payloads/digests, RPC URLs, signer paths,
credentials, network targets or approval-record substitutions. Refusal is explicit.

## 6. Minimal same-artifact workflow and ownership

The real integration must link these steps within one recorded run:

```text
Authenticated native Hive Programs dispatch
  → generated shareable input through AtomStorage / real DeTTa
  → existing reference message to a labelled fixture counterparty
  → existing delegated inspect_atom worker
  → persisted result and correlated completion
  → real Hive caller verifies/accepts result and acknowledges delivery
  → trusted, exact-result approval
  → ConsensusFinality.submit through its selected authorized adapter
  → durable signed deploy intent
  → real F1R3node execution of the fixed commitment operation
  → exact effect readback + matching inclusion / deploy-effect finality
  → native caller observes the separately classified chain result
```

Use the native registration/dispatch mechanism, not a standalone helper imported
from the plugin. The fixture counterparty stays labelled; one real caller is not
two operating Omega agents. No paid/live LLM is necessary.

A narrow sibling Programs action for commitment/observation can reference the
original authenticated inspect command. A small composition-only extension of
the current action is also acceptable if its old contract remains unchanged.
Do not turn the Hive plugin into the commitment owner, access another owner's SQL,
or duplicate the existing inspect state machine. If resolving the completed
inspect outcome needs a port, extract the smallest caller-owned validated accessor
from the existing code. It must recheck native principal/swarm and current service
authority; it must not be an arbitrary file path supplied by the caller.

The Hive adapter owns only its mapping/progress. AtomStorage owns payloads,
execution owns jobs, Messaging owns deliveries, and the chain adapter owns its
submission/replay records. The chain implements only the fixed commitment state
transition and consensus observations. Do not assume a transaction spans these
owners or tie off-chain success to successful chain inclusion.

Keep `ConsensusFinality` backend-independent. A typed local authorized session is
sufficient for the chain boundary; do not add a new transport framework. Reuse
existing descriptors/selection checks where applicable. If new receipt or profile
fields are necessary, make the compatibility decision explicit and preserve old
behavior under the old profile. Fresh M4 journals are acceptable; no migration.

## 7. Signing, replay and observation contracts

### Signed-intent continuity

Reuse the inspected signer and pinned protobuf serialization, after verifying
compatibility with the selected node. Persist the complete signed deployment
before any submission. Bind its owner journal to the selected operation/profile,
chain instance, shard/network or equivalent identity, test signer identity,
approval and artifact. Use only chain identity fields actually supported and
verified by the selected implementation; do not assume an endpoint URL is identity.

A retry of the same authorized logical operation reuses the original signed bytes,
signature, timestamp, gas/phlo bounds and deploy identity. It must not silently
resign or extend validity after a timeout. Persist the logical operation before
signing effects can escape. Concurrent duplicate requests must not create multiple
logical submissions. No claim of globally exactly-once execution across unrelated
keys or separate operators is requested.

Wrong artifact/approval/actor/network/profile under a bound operation conflicts or
fails authorization before a new effect. Recheck current authority on new calls
and cached replies. Revocation prevents new submission; it cannot retract bytes
already sent to the chain. Unknown submission remains unknown until evidence
resolves it. Node outage must not lead to a new genesis, timestamp or deploy.

### Exact observed effect

Keep the fixed operation small: the existing approved digest write, or the minimal
compatible fixed template needed for unambiguous generated readback. Do not add a
registry, payment system, arbitrary execution endpoint or PLN port to validators.
A fixed public namespace may be profiled explicitly; generated operation IDs or
extra fields must themselves be deliberately shareable.

Read back the actual expected value through the selected node's state/event API,
bound to the relevant block/post-state or other explicitly documented finalized
execution evidence. Use a non-consuming query where supported. A current-head
read must not be called a block-bound historical read. Compare actual digest,
operation identity and namespace with the approved result. Merely finding the
digest in the submitted source term, an RPC echo or a local log is not effect
readback. A deploy included without error still requires the matching effect.

If the selected node cannot expose the necessary effect/finality evidence, report
the specific unsatisfied gate. Do not manufacture a proof from local knowledge of
what the transaction was intended to do. No new consensus implementation is needed.

Record independent observations for:
- DA persistence, result acceptance and mailbox acknowledgment;
- durable signed intent and RPC submission response;
- inclusion, execution error/cost and verified effect;
- deploy-effect finality, and the actual observation source/time/block.

They are not one universal linear success flag. A submission receipt is not an
execution result; a finalized block alone is not proof of the target deploy's
successful finalized effect; finality does not prove indefinite DA availability,
source truth, privacy or correct off-chain reasoning.

Use bounded, call-driven observation with explicit attempt/time limits. A polling
deadline can end observation while the deploy remains pending; another authorized
observation may read the same deploy without resubmitting/restarting the job.
Transient unavailability is neither rejection nor absence. Preserve raw typed
rejection/expiry causes, mismatches and contradictory observations. Never silently
upgrade malformed output to a successful finalized receipt.

Do not promote original node response parsing to trustless verification. This is
an isolated real-node integration with node-observed evidence, not independent
multi-validator validation or cryptographic execution attestation.

## 8. Required recovery, integrity and isolation cases

Use deterministic failpoints and real process termination where claimed. Separate
actual real-node cases from transport/state-response fixtures in reports.

1. **Same-artifact happy path:** native Hive + real DeTTa + real F1R3node. Retrieve
   the result, recompute its digest, verify the actual on-chain value and matching
   successful deploy-effect finality. Record all linking identities from this run.
2. **Caller dies after result acceptance, before chain request:** restart through
   native dispatch, recover the same result/job and approve only those bytes.
3. **Adapter dies after signed-intent commit, before submission:** reopen the same
   journal, sign no new transaction, submit the saved bytes.
4. **Response lost after real-node submission:** an injected response-loss wrapper
   may drop the actual node's reply, but must not replace the node with a fake.
   Reconcile or resend the identical signed deploy. Record both the real node and
   the injected fault; verify the same deploy identity and logical commitment.
5. **Effect/finality observed, caller dies before recording progress:** a new native
   observation recovers the chain outcome without new worker execution/signing.
6. **Node restart:** restart the same generated node data/genesis, not a fresh
   chain. Re-observe the same finalized effect, within its documented durability
   scope. A restart failure is reported rather than hidden by regeneration.
7. **Temporary chain outage:** off-chain result and completion remain committed;
   chain state is visibly pending/unavailable and can be observed later. Do not
   roll back belief/memory, repeat inspect work or drop the pending operation.
8. **Negative bindings:** wrong digest, scope, result reference, native owner,
   approval, chain instance, descriptor/profile, expired authority and changed
   semantics under a replay key fail explicitly. Test revocation before cached
   reply and before a new send. Include incompatible node responses and finalized
   claims with missing/wrong effect, deploy or block evidence.
9. **Privacy/isolation:** canaries and identifying derivatives from private
   cognitive state do not occur in approved payloads, deploy bytes, chain values,
   normal public Hive receipts or shared diagnostics. Keys/credentials and private
   runtime paths are absent from published evidence. Verify real socket isolation.

Existing conservative reasoning budgets and M3.1 closure must remain unchanged.
Chain polling has its own finite observation budget; it does not reuse or reset
inference deadlines. No automatic scheduler, effect compensation or live migration.

At least one recovery must traverse actual native Hive dispatch. Adapter-only
fixtures do not pass the real-caller gate. Preserve the labelled independent
providers in earlier conformance tests; M4 does not require building another chain.

## 9. Reproduction, demonstration and acceptance gates

Extend the existing build/verification tooling rather than starting a second
framework. A new M4 entrypoint should make source selection, node lifecycle,
artifact provenance and gate classification explicit. Start from fresh disposable
source/build/test directories for the final supported reproduction. Obtain exact
sources and locked dependencies; no unlisted copied binaries or private histories.
Warm download caches may be used if disclosed. Empty-global-cache and production
runs remain NOT_RUN and are not prerequisites for this bounded demonstration.

Run the applicable M1–M3.1 regression suite on the recorded final implementation,
plus new fixture, real-node and native-caller cases. Preserve historical evidence
rather than replacing its inputs or relabelling it current. Store failed attempts
and corrections separately from the final pass.

Deliver a sanitized same-artifact trace: native generated command/run identifier,
input/result references and digests, execution/completion identity, approved
commitment, selected chain instance/profile, signed-deploy identity, inclusion,
observed value, effect finality, and replay/recovery outcome. Include only
intentionally shareable identifiers. Do not include private principal mappings,
secret-bearing configs, keys, bearer tokens or raw private journals.

A second read-only verifier/process must be able to retrieve the permitted DA
result and inspect the chain evidence without the original caller's in-memory
state or signing key. Record its access prerequisites. This is independent
readback, not proof that the single node or synthetic source is trustworthy.

Report observed elapsed cost separately for storage/worker completion, signing
and submission, inclusion, finality and recovery; include actual bytes and chain
cost if returned. Do not infer throughput, AGI quality or production economics
from a one-run integration. Timing thresholds must not be invented to look good.

| Gate | Required evidence |
|---|---|
| BASELINE | Applicable M1–M3.1 regressions on exact final sources, with old profiles preserved. |
| CHAIN_SOURCE_BUILD | Obtainable pinned node source/build and safe isolated real startup; absent prerequisite is BLOCKED. |
| NATIVE_HIVE_DA | Actual authenticated native operation, real DeTTa, existing worker and same-run verified result; counterparty classified. |
| APPROVAL_BINDING | Exact generated-result approval, live caller authority, pinned provider/chain/signing context and negative binding tests. |
| REAL_CHAIN_EFFECT | Real fixed on-chain state transition, actual effect readback and matching inclusion/non-error deploy-effect finality. |
| RECOVERY | Real caller/adapter interruption, uncertain submission and same-node restart; stable signed intent and no duplicate logical off-chain work. |
| PRIVACY_ISOLATION | Private canaries excluded, secrets excluded from evidence and actual local network isolation verified. |
| REPRO_READBACK | Fresh-directory declared-input run and separate read-only verification of the same artifact/effect; cache scope explicit. |
| DEMO_HANDOFF | Native result/progress distinguishes local completion, chain submission, inclusion, effect and finality; runnable operator instructions and sanitized trace. |
| SCOPE | One chain-backed commitment capability; no new cognition, validator framework, public deployment or migration. |

A missing runtime/input is BLOCKED; an intentionally unexercised extra is NOT_RUN;
incorrect behavior in an executed required test is FAIL. A bounded finality timeout
must be explicit and cannot pass REAL_CHAIN_EFFECT. Expected rejection tests may
pass their negative assertion without passing the positive integration gate.
Do not collapse these states into the old script's broad exception handling.

**Overall M4 PASS requires all required gates, including REAL_CHAIN_EFFECT.**
When blocked, deliver the exact source/API/permission gap, verified local work and
next narrow remedy; stop. Do not fill the remaining task with LTI, another fixture
runtime, speculative interfaces or a node rewrite.

## 10. Final report and product claim

Update the current ADRs/contracts/runbook and add `m4-evidence.md`, a machine-readable
manifest, focused integration tests and one reproducible demonstration command.
Record tested implementation SHA, later evidence-only commits, source/lock/binary
identities, changed files, executed commands, failures/skips/unrun gates, generated
fixtures, actual providers and observed bounds. Do not publish restricted upstream
sources without authorization.

The demonstrated claim, only after the real gates pass, is:

> A native Omega Hive operation uses backend-independent module interfaces and
> real DeTTa for a generated shared result. A chain-backed commitment adapter
> records that result's approved digest on an isolated F1R3node, and the same
> effect can be retrieved and observed as finalized after bounded restart.

It is **not**: Omega/PLN runs entirely on ASI:chain; two real agents formed a
production Hive; private memory was published; the chain verified the off-chain
computation; or a single-validator demonstration established decentralized safety.

**Then stop for review.** Public-testnet deployment, a substantive on-chain
execution module, more cognition and legacy-state migration are separate decisions.

## Review sources

All Fusion source findings refer to the exact evidence tree below, not moving
master. Meeting references refer to the supplied 15 October 2026 transcripts.

```text
https://github.com/machieke/fusion-module-interfaces/tree/985d2f34ea8df8c5d93582e4ed6fe5cbe1843074
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/985d2f34ea8df8c5d93582e4ed6fe5cbe1843074/docs/module-interfaces/m3_1-evidence.md
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/985d2f34ea8df8c5d93582e4ed6fe5cbe1843074/docs/module-interfaces/runbook.md
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/985d2f34ea8df8c5d93582e4ed6fe5cbe1843074/fusion/adapters/f1r3.py
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/985d2f34ea8df8c5d93582e4ed6fe5cbe1843074/scripts/chain_demo.py
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/985d2f34ea8df8c5d93582e4ed6fe5cbe1843074/integration/hive/program/program.py
```
