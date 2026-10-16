# M3 evidence: independent STI attention and bounded grounded inference

M3 is complete for the supported local scope. **All 13 required gates passed.**
There are no blocked prerequisites. **CHAIN is NOT_RUN.**

The [machine manifest](evidence/m3/manifest.json), [complete final verification](evidence/m3/final/verification.json),
[comparison](evidence/m3/final/comparison.json), executable [contracts](contracts.md),
[ownership diagrams](architecture.md) and [runbook](runbook.md) retain the evidence.
This increment stops at M3. The presentation still describes M2.

## Exact source state

Requested `f0cee24` resolves to **`f0cee248294a1fce42913782390e6c084025c67e`**.
The actual clean starting descendant was **`926882afb9ab9c7288bf663f96f9e1ca63dd8520`**.
Intervening commits were presentation/docs `1997c879c35d25badaf377a45ac082fa0081edcb`
and the M3 brief `926882a`; no application implementation changed. The
[initial source record](evidence/m3/initial-source-state.json) lists those paths.
The brief SHA-256 is `e32b99ec398f43c534bd74383c5a955ab1a0c8cfd9fb77debcb14e4c2ae9411e`.

Implementation: `d4185284b06dad2ec9f91c7bdaba591f4a68e805`.
Boundary review correction: **`1af39794649d0ca95cd729c64868202368da1ec4`**.
The latter detaches mutable nested requests before authorization/foreign calls,
validates recovered responses and updates the architecture. Final verification
runs from a separate **clean detached checkout of `1af39794649d0ca95cd729c64868202368da1ec4`**.
Later report/evidence commits change no implementation or test code.

| Source | Exact revision and role |
|---|---|
| Inspected metta-attention | `3e1c8147dc17299d17ab34720334fc19277cb6a9`, clean; STI/LTI/VLTI, wages and shared funds are coupled, so it is not used as this policy's provider |
| Hive schematics | `4af00db4e395375484dd48d0b9068a59afcf01f8`, identifies intended native source |
| Actual Hive | `34b0fb32ab3806e5609fc89bb7535518a35e1aea`, native ASGI app, authenticated Programs dispatch, Supervisor and PeTTa |
| DeTTa / secured-contract-spaces | `272888f264dd2dde18b574cabb53c266b0dac2ec`, real local DA/FileStorage |
| Reachability | `dd56f3f053ed90239de5377021a7d3b3fbf424ac`, unchanged `PLNAdapter.apply_rule`, `DeductionRule`, guards, support/ancestry construction and revision |
| PLN | `4405956947c4b53c7ff01bd565aa3b114bc970a1`, actual native `Truth_Deduction` and preserved `Truth_Revision` |
| PeTTa | `ae66fa8e41dcd5539d614706bd4e5cfb34f9608d`, native formula runtime |
| SWI source | `69775434c8226897626b226aefcc8266499f1e2e`, version 10.1.14 |
| Python / Janus | Native Python 3.12.12 and Janus 1.5.3; fixture runner Python 3.11.14 |

PLN library SHA-256: `cdfb3f18bd7b336440fc7b4409209afddf0e64c41f17dee7eefc8f02718de433`.
Fresh SWI binary SHA-256: `2a9b28b46f54f5eb0a8e1c79bb201c50b8acbbd5c180875ea8a5bca4e8617dfc`.
All exercised upstream checkouts were clean at their pins. No upstream mathematics,
source lock or Hive runtime implementation was patched. Historical SWI 10.0.1
compatibility remains unrun. The deduction profile is separately named
`fusion-petta-swi-10.1.14-deduction/1`; the revision-only allowlist is unchanged.

The fresh provider build took **354.696 seconds**, with warm download caches and
new native objects, Python/Janus environment and DeTTa target. The existing M2 build
recipe remains byte-identical; `build_m3.py` adds the separately selected deduction
configuration. [Build output](evidence/m3/fresh-build.log) and the final manifest
retain pins, recipe hashes, native bridge checks and access requirements. Local
configuration/environment files are deliberately not copied into published evidence.

## Decisions and changed files

| Files | Responsibility and decision |
|---|---|
| `fusion/ports.py`, `attention_contracts.py`, `cognition_contracts.py` | Executable context, immutable workset/task, exact premise vector, tagged-support admission and durable budget contracts; closed bounded validation |
| `fusion/attention.py` | SQLite owner for integer STI, per-context clock/watermark, causal identity and command replay |
| `fusion/adapters/fixture_attention.py` | Independent atomic-file implementation of the same policy; no owner inheritance, private tables or shared transition functions |
| `fusion/adapters/pln_deduction.py`, `integration/pln/deduction-sources.json` | Pure source-verified upstream grounded deduction and M3 ancestry-preserving revision adapter; separate native allowlist, no replacement arithmetic |
| `fusion/beliefs.py`, `derived_beliefs.py` | M2 behavior retained through its default validators; fresh C2 v3 journal adds exact derivation attempts, authoritative historical reads, final authorization/CAS and logical admission deduplication |
| `fusion/inference.py`, `deadlines.py` | C4-owned step/selection/reservation/progress/feedback journal and absolute deadline checks; no foreign SQL or general task search |
| `fusion/cognition.py` | Explicit private local descriptors, versions, permissions, provider choice and hostile-port-compatible composition |
| `fusion/adapters/pln_revision.py` | Reused invocation/source-check mechanics accept an optional absolute deadline; existing revision semantics and default behavior are preserved |
| `integration/m3_scenario.py`, `integration/hive/inference_program/` | Narrow generated native action, actual trusted Hive actor, two tasks, one attempt and private episode/trace |
| `tests/test_m3*.py`, `tests/m3_support.py` | Standalone C3, refusing/guard fixtures, malformed boundaries and immutable-input tests |
| `integration/pln/test_deduction.py`, `test_m3_recovery.py`, `m3_worker.py`, `integration/hive/test_m3_integration.py` | Native goldens, admission/ancestry, real process kills, authorization/CAS, privacy and actual Hive recovery |
| `scripts/build_m3.py`, `verify_m3.py`, `m3_compare.py` | Fresh recipe, single verification entrypoint and controlled substitution experiment |
| README, architecture, contracts, ADR 010/011, runbook and this evidence | Explicit ownership, profiles, guarantee boundaries, classifications and reproducibility |

The policy is **`sti-additive-linear-decay/1`**, not ECAN. Exact integer units,
Smax/B/decay and capacity limits are frozen in its identity. Reads never allocate or
decay. Successful replay precedes logical-step CAS under current authorization.
Fresh feedback must follow the target's current causal parent; decay, new ingress
and new controller step IDs cannot erase its stored generation. Capacities refuse
without evicting acknowledged commands. The atomic-file provider is classified as
an independent fixture even though it persists real state and passes the same policy.

C2's new `pln-derived-private/1` profile is local version **3.0.0**, with fresh
journals. C3, kernel and C4 are local **2.0.0**. M2 stays at its old profiles.
Task and workset records are immutable private atoms. Five bindings name exact
claim/context/revision/support IDs in P,Q,R,P=>Q,Q=>R order. Upstream's integer
knowledge revision is a local evaluation ID of zero, not a fictional global ledger.
The actual per-belief vector is retained separately in every derived support.

The kernel owns no belief, agenda or attention state. It uses both the upstream
exact Python probability precheck and the native conditional check, then the
unchanged `Truth_Deduction`. The independent golden is **0.68 / 0.3136** within
`1e-12`; the measured native pair is approximately
`0.6800000000000002 / 0.31360000000000005`. This remains an upstream heuristic with
an explicit Q>0.9999 branch, not calibrated uncertainty or proven entailment.

Deduction inherits the actual evidence/root union and grounded ancestry. It adds
no observation, root, independence assertion or evidence count. Unknown output
beliefs can initialize with inferential support; existing truth retains it as an
alternative. A later separately authorized revision uses the same guarded upstream
revision and preserves ancestry. A derive → revise → derive cycle is refused.
Local coverage units have an explicit tag; five foreign premises are never
misrepresented as five observations about the output claim.

C4 reserves a physical evaluation opportunity before dispatch. Every lost pending
attempt spends that slot; retries need another slot and attempt key. It queries a
committed C2 decision first and never reevaluates a completed logical admission.
Counters distinguish reserved/completed/refused, unique/duplicate admission,
acknowledged feedback and suppressed duplicate feedback. Feedback is a fixed one-unit
workflow signal tied to the logical derivation identity, never a truth update.
Selection is frozen for the step and observed anew by a subsequent step.

## Executed gates

| Gate | Result | Evidence |
|---|---|---|
| BASELINE | **PASS** | Original 51-fixture subset; 118 aggregate cases (90 original + 16 M2 + 12 M3); DeTTa 62 + 38; Hive baseline 34 and original integration 13; M2 fixtures 16, guards 8, native revision 12, recovery/privacy 6, native Hive 7 and demo. |
| CONTRACTS | **PASS** | 7 M3 contract fixtures plus native adversarial cases; exact intent/response binding, profiles, historical vectors and tagged support. |
| C3 | **PASS** | 5 standalone tests with both providers; bounded persistent STI, clock, ties, saturation, causal replay, generation retention and defensive copies. |
| C3_INDEPENDENT | **PASS** | Native/DA paths deliberately absent; no PLN/Hive/C1/C2 runtime dependency; declared-port wrappers. |
| ATTENTION_SWAP | **PASS** | Four fresh controlled cases with identical task/evidence bindings; unchanged consumer and matching results on SQLite and atomic-file providers. |
| KERNEL_NATIVE | **PASS** | 13-case mixed native/adversarial suite, actual golden and near-one branch, exact/native guards, parse/timeout/source-drift checks; 15 separate upstream guard fixtures. |
| DERIVED_ADMISSION | **PASS** | Exact historical vectors, owner-only CAS/authorization, logical deduplication, retained alternative, inherited evidence/ancestry and cycle refusal; no derived observation. |
| C4_BOUNDED | **PASS** | One-attempt selection effect, persistent candidate/attempt/deadline limits, generation across five new worksets/steps, explicit unavailable/clock-conflict outcomes. |
| RECOVERY | **PASS** | 3 native recovery methods cover 10 SIGKILL cases; five more real native Hive caller boundary kills. |
| PRIVACY | **PASS** | Intercepted shared bindings, populated shared stores and native receipts/logs/state remain free of private canaries, task/support hashes and provenance. |
| HIVE_M3 | **PASS** | 8 actual authenticated native tests, zero failures/errors/skips: inference, replay/restart, provider swap, all five boundaries, authority and privacy. |
| REPRO | **PASS** | Fresh-directory source build, new native objects/venv/DeTTa target and complete clean-checkout verification; warm download caches explicit. |
| SCOPE | **PASS** | C3/C4 plus required C2 admission extension only. One grounded rule; original M1/M2 profiles retained; no live migration. |
| CHAIN | **NOT_RUN** | Excluded; no chain integration or deployment executed. |

| Final command group | Executed cases | Elapsed seconds |
|---|---|---|
| `m2-regression` | Nested M1/M2 suites listed above | 311.453 |
| `m3-attention-fixtures` | 5 | 0.581 |
| `m3-contract-fixtures` | 7 | 6.253 |
| `upstream-guard-fixtures` | 15 (RecordingRuntime fixtures) | 0.084 |
| `m3-native-kernel-admission` | 13 (native + explicitly injected faults) | 124.813 |
| `m3-real-process-kills` | 3 methods / 10 kill cases | 59.845 |
| `m3-native-hive` | 8; zero failures/errors/skips | 210.515 |
| `m3-comparison` | 4 controlled cases | 51.197 |

Repeated subsets are not additional unique tests. Inherited M2 manifests retain their phase-specific exclusion labels; the top-level M3 manifest is authoritative for this increment.


Final execution used:

```bash
uv run --python 3.11 --locked python scripts/verify_m3.py \
  /home/purplezky/work/takopi/fusion-module-interfaces/artifacts/m3/providers/environment.json \
  --output /home/purplezky/work/takopi/fusion-module-interfaces/artifacts/m3/final-1af3979
```

The working directory was `/tmp/fusion-m3-verify-1af3979`. The final source status
was clean and the verifier returned zero. Exact command arguments, durations,
file hashes and JUnit results are retained in the machine evidence. A supplemental
[fixture check](evidence/m3/supplemental-empty-selection.json) at the same clean SHA
exercised empty positive-STI ranking and a zero-native-attempt budget.

The native recovery suite performs **10 actual SIGKILL boundary cases**: stimulus
commit (both providers), reservation and kernel-return losses (budgets one and two),
and belief/feedback commit recovery (both providers). The Hive suite performs
another **five** actual caller boundary kills. One-slot loss is conservatively
exhausted without a conclusion; two-slot recovery admits one logical support.
Committed admission and feedback recover without another native formula call or
second credit. These are actual process kills, not exception-only substitutes.

## Controlled comparison

| Attention provider | STI preference | Selection order | Examined | Native attempts | Valid/refused | Unique admission / feedback | Step seconds |
|---|---|---|---:|---:|---|---|---:|
| sqlite | b | b → a | 2 | 1 | 1/0 | 1/1 | 0.744361 |
| sqlite | a | a → b | 2 | 1 | 1/0 | 1/1 | 0.677157 |
| atomic-file-fixture | b | b → a | 2 | 1 | 1/0 | 1/1 | 0.726126 |
| atomic-file-fixture | a | a → b | 2 | 1 | 1/0 | 1/1 | 0.641150 |

All four cases end at the rule budget and recover the same receipt after reopening owners, with **zero additional native calls**. Initial duplicate admissions/feedback are zero; separate replay and crash tests prove suppressed duplicate admission and causal credit. Candidate count includes the second candidate encountered before stopping at the spent rule budget.


Each fresh case has two grounded tasks, five premises each, ten generated
observations, two episodes and twelve claim atoms. Exact task/evidence bindings,
policy parameters, budgets and logical schedule are held fixed across providers.
Only composition selects the attention provider. Separate preference cases switch
initial STI between 20/10 and 10/20. Timing is one local observation per case;
it demonstrates substitution and selection effect, not cognitive quality or
production throughput. Store size and preparation cost are in the machine result.

The actual Hive action independently seeds a **12-event** private episode:
ten explicit generated observations, one action and one result. Native dispatch
passes through the unchanged authenticated Programs runtime. The plugin receives
trusted actor identity and projects only generated counters/status; it does not
own beliefs, attention or the controller. Existing inspect and episode plugins,
M1 wire/DA boundaries, authorization and regressions remain supported.

## Guarantees, limitations and classifications

- **Observed:** persistent exact STI transitions; deterministic eligible ranking;
  same-profile independent replacement on fresh stores; live authorization on
  replay and final admission; CAS after calculation; exact historical premises;
  lineage/ancestry-preserving native deduction/revision; no fresh derived evidence;
  duplicate-safe logical admission and reward; attempt/deadline/generation budgets
  retained across tested crashes; no private trace in populated shared routes,
  intercepted outbound bindings, native public receipts or Hive logs/state.
- **Real providers:** SQLite reference-policy attention, DeTTa DA/FileStorage,
  unchanged guarded native PLN/PeTTa/SWI and actual Hive caller/runtime.
  **Fixtures:** generated observations/tasks/operator assumptions, the independent
  atomic-file attention provider, refusing-kernel/guard-only math fixtures and
  explicitly injected malformed responses, timeout, revocation and clock interleavings.
- **Compatibility limit:** M3 v3 belief snapshots are not M2 C1 acknowledgment DTOs.
  Generated C1 delivery intents remain available and pending; M3 does not fabricate
  an acknowledgment or silently widen the M2 interface. M2's original relay and
  acknowledgment tests continue to pass under their original profile.
- **Recovery limit:** independent commits are not a distributed transaction. A lost
  reservation can exhaust the only attempt without a result. A concurrent clock
  advance can leave feedback pending with CONFLICT; it is not implicitly retimed.
  A completed bounded step can retain unacknowledged work. Receipts expose that state.
- **Timing/storage assumptions:** same-host wall clock and intact local files,
  trusted operator/bound authority, bounded local providers. Kernel source checks
  and subprocesses use remaining deadline; file I/O and scheduling are cooperative.
  No hard real-time, reboot, power-loss, administrator secrecy, distributed failover,
  one physical calculation per logical derivation or live migration claim is made.
- **Model limits:** one grounded five-premise rule, no `PLN.Derive`/`PLN.Query`,
  automatic task expansion, independence discovery, LTI, general search, new attention
  research, richer inference control, M4 or chain work. Origin/independence assertions
  remain operator assumptions. Specialist/maintainer assignment remains unassigned.
- **Blocked prerequisites:** none for the supported local M3 gates. **NOT_RUN:**
  chain, historical SWI 10.0.1, empty-global-cache build, power-loss/distributed tests,
  production throughput/quality studies and all excluded extensions.

[Development logs](evidence/m3/development/index.json) remain separate from final
release evidence. Early failures included a canonical-reference tie-break test
oracle, an unsupported Hive presentation role, and a wrong expected error class
for a mismatched truth model. The initial direct native probe omitted a Janus
library path and is retained as failed readiness evidence even though its process
returned zero; the corrected native environment passed. The first clean verification
was intentionally interrupted after baseline/fixture passes to fix nested-request
mutability; it is explicitly labelled interrupted. None of those partial runs is
reported as the final gate pass.
