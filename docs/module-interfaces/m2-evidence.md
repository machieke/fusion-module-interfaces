# M2 evidence: private episodic memory and guarded native belief revision

M2 is complete for the supported local C1/C2 scope. All required gates passed;
there are no remaining blocked prerequisites. Chain is NOT_RUN. The
[presentation](../presentation/README.md) now covers M2 with an ELI16 executive
summary; its rebuild does not rerun these integration gates. The
[machine manifest](evidence/m2/manifest.json)
and [complete final verification](evidence/m2/final/verification.json) retain exact
commands, file hashes, classifications and results.

## Exact source state

The requested ancestor is `4ee5cbe8b84689a5d2432530083738b263142f90`.
Work started at clean descendant `6452fa725be5a688f9d5ad8f77955579df2f95ab`;
its intervening changes were presentation/documentation only. The supplied brief
was fetched from <https://ctxt.io/3/n3bumFNzG.md> and saved verbatim as
[`codex_fusion_m2_episodic_memory_and_pln_revision.md`](../../codex_fusion_m2_episodic_memory_and_pln_revision.md),
SHA-256 `e40f4293c60926c6b8c1c090a83f432fe3d39794e90793bfff5ef69472373d1b`.
The [initial manifest](evidence/m2/initial-source-state.json) records the exact
starting checkout and descendant file list.

M2 implementation commits are `bbad55c32ffbe7e7cf56ce29425fbc7b9f7d001f`
and `11eccc1150c93df000f3e0d7a3acd7667b65b1c6`. The latter closes acknowledgment
body binding and mutable-input/response-validation gaps found during review.
Test/reproduction refinements are `aa0566a4c63f4c36ce6b570b9ea933308c0ec6bf`
and `d9e75773c34987d5791a9207190fcbf0a8c1fd7b`. The final comprehensive run uses a
clean detached checkout of **`d9e75773c34987d5791a9207190fcbf0a8c1fd7b`**.
Evidence/report commits following it do not change the tested implementation.

| Source | Exact revision / use |
|---|---|
| Hive schematics | `4af00db4e395375484dd48d0b9068a59afcf01f8`; identifies the intended runtime |
| Actual Hive | `34b0fb32ab3806e5609fc89bb7535518a35e1aea`; native ASGI app, authenticated Programs dispatch, Supervisor and PeTTa |
| DeTTa | `272888f264dd2dde18b574cabb53c266b0dac2ec`; clean real local DA/FileStorage libraries |
| Reachability | `dd56f3f053ed90239de5377021a7d3b3fbf424ac`; unchanged `PLNAdapter.revise`, truth/support types and guards |
| PLN | `4405956947c4b53c7ff01bd565aa3b114bc970a1`; actual `Truth_Revision` |
| PeTTa | `ae66fa8e41dcd5539d614706bd4e5cfb34f9608d`; native formula evaluation |
| SWI / Python / Janus | SWI 10.1.14, Python 3.12.12, Janus 1.5.3; source/package pins retained in `integration/hive/sources.json` and hash locks |

PLN `lib_pln.metta` SHA-256 is
`cdfb3f18bd7b336440fc7b4409209afddf0e64c41f17dee7eefc8f02718de433`.
The fresh SWI binary SHA-256 is
`f1e29950cb5ccfe3904833db5c08409bc2a1c7c999f1e1933719a7c3e03ab20f`.
SWI source is `69775434c8226897626b226aefcc8266499f1e2e`; its pinned submodule
selection is retained in the build record. Historical Reachability SWI 10.0.1
checks and locks remain unchanged.
`fusion-petta-swi-10.1.14-revision/1` is an explicit narrow rebaseline; the two
versions are not silently treated as equivalent. Provider paths, runtime selection,
file hashes, source cleanliness and commands are retained in the machine evidence.

## Decisions and changed files

| Files | Decision / responsibility |
|---|---|
| `fusion/ports.py`, `memory_types.py`, `memory_contracts.py` | Local C1/C2 v2 contracts; stable episode identity versus head, explicit numerical observations, separate admission/numerical outcomes, exact context/polarity/coverage, closed bounded response validation |
| `fusion/private.py` | Separate `private-local-only` placement and live scope/method/descriptor checks; real DeTTa composition; explicit fixture injection only |
| `fusion/episodes.py` | C1 exclusively owns ordered occurrences, replay and append+delivery intents; immutable event bytes use AtomStorage |
| `fusion/beliefs.py` | C2 exclusively owns admitted evidence/supports, immutable snapshots and exact semantic attempts; authorization and CAS rechecked after calculation |
| `fusion/evidence_relay.py` | Specific bounded durable delivery cursor; unchanged retry after transient failure, new identity after genuine CAS conflict, separate acknowledgment |
| `fusion/adapters/pln_revision.py`, `integration/pln/sources.json` | Source-checked reuse of upstream guards; revision-only native runner, no substitute production arithmetic |
| `integration/m2_scenario.py`, `integration/hive/episode_program/` | Generated private scenario through a sibling real Hive plugin; native actor authority, no shared ingress or private history in public receipts |
| `tests/m2_support.py`, `tests/test_m2.py` | Explicit independent file-provider/guard fixtures and hostile declared-port checks |
| `integration/pln/test_revision.py`, `test_recovery.py`, `integration/hive/test_m2_integration.py` | Native goldens/refusals, true SIGKILL recovery/CAS/privacy and authenticated native caller tests |
| `scripts/build_m2.py`, `verify_m2.py`, `m2_demo.py` | Fresh pinned provider recipe, separate gate recorder and deterministic generated demo |
| Architecture, contracts, ADRs 008/009, discovery glossary, runbook and README | Current ownership, exact profiles, bounded operations, model selection, threat model and reproduction instructions |

M1 wire schemas, registry/resolver, DeTTa adapter, AtomStorage, execution,
mailbox, original Hive plugin/driver and its 13 tests are byte-identical to the
requested M1.2 baseline; the verifier checks those files explicitly. No upstream
source is patched. No application semantics were added to DA. C1/C2 have no
messaging, chain, search, ECAN or inference-controller dependency.

Origin registration and independence remain explicit operator assumptions.
Copied records inherit admitted provenance roots; new request keys, new event
IDs and aliases do not grant independence. Unknown origins cannot initialize a
justified numeric aggregate. A new observation can be admitted while the older
aggregate remains unchanged, with uncovered alternatives named explicitly.
Later authorized assumption registration can aggregate those existing supports
without inventing another observation.

## Executed gates

| Gate | Final result and evidence |
|---|---|
| BASELINE | **PASS**: original 90 conformance cases plus 16 new fixtures (106 total), separate original 51-fixture subset; clean DeTTa 62 + 38; native Hive baseline 34; unchanged M1.2 Hive integration 13 |
| CONTRACTS | **PASS**: 16 local fixture tests; advertised C1/C2 operations match protocols, closed inputs/outputs, profiles, permissions, bounds and complete request fingerprints |
| C1 | **PASS**: real DeTTa-backed history, immutable events, duplicate-safe sequence/CAS, retained reports and contrary observations, bounded reads and delivery intents |
| C1_INDEPENDENT | **PASS**: cognition absent; independent file AtomStorage and hostile declared-port wrappers; foreign SQL/attribute access rejected |
| C2_GUARDS | **PASS**: 8 unchanged upstream revision guard tests (RecordingRuntime fixtures), local hostile-input tests and native-suite guard/refusal cases |
| C2_NATIVE | **PASS**: 12 real-provider suite tests, including actual equal/unequal/swapped golden computations, authority/CAS checks and real timeout; malformed-output cases are explicitly injected fixtures |
| PRIVACY | **PASS**: generated canary absent from intercepted outbound bindings, populated shared stores/messages, normal diagnostics, native responses and Hive traces; cross-principal/scope and revocation checks |
| RECOVERY | **PASS**: 6 real-provider recovery/privacy tests, including four actual SIGKILL boundaries and a two-process CAS race with unchanged retry after contention |
| HIVE_M2 | **PASS**: 7 actual authenticated native Hive tests, zero failures/errors/skips; completion, replay, restart, all four crash boundaries, live revocation and private result isolation |
| REPRO | **PASS**: fresh pinned provider build and clean detached Fusion checkout; all supported gates executed; download caches warm |
| SCOPE | **PASS**: C1/C2 only; preserved original M1.2 behavior and upstream guarded source; no ECAN/inference/chain/migration implementation |
| CHAIN | **NOT_RUN**: out of M2 scope; no chain dependency or fallback |

The final command was `uv run --python 3.11 --locked python scripts/verify_m2.py`
with the recorded fresh provider environment and output directory, from clean
`artifacts/m2/repro-final` at `d9e7577`. It returned **0**. All test commands
returned 0; the native suites reported zero skipped tests. The 16 new fixtures
appear both in the 106-case discovery suite and their isolated fixture run;
those counts must not be summed as distinct tests. Eight upstream cases were
selected specifically for revision/domain/identity guards; no `apply_rule`,
PLN.Derive or PLN.Query test was invoked.

The deterministic [demo summary](evidence/m2/final/demo.json) also passed with
exact results after reopen. Fixtures include its generated observations and
operator independence assumptions. Providers executing storage, numerical
revision and native Hive dispatch are real; the test driver is only transport.
Exact commands and test names are in [final logs](evidence/m2/final/console.log)
and the linked verification record.

Before edits, M1.2 passed 90 conformance tests (including the separately run
51-fixture subset), DeTTa 62 + 38 library tests, 34 native baseline tests and the
original 13 real Hive integration tests. Those pre-edit logs remain in
[`evidence/m2/baseline/`](evidence/m2/baseline/verification.json).

The real native caller starts `hive.core.app.create_app` with the default
Supervisor, authenticates with Hive, and invokes
`POST /api/programs/fusion-episode/act`. No fake actor, plugin loader or PeTTa
provider is used. The original `fusion-inspect` route remains separate.

Native golden oracles are independent expected values: equal confidence inputs
`(.75,.5),(.25,.5)` produce `(.5,2/3)`; unequal confidence inputs
`(.75,.5),(.25,.75)` produce `(.375,.8)`, including reversed input order.
Tolerance is absolute 1e-12 for valid results only. No tolerance permits invalid
inputs, wrong support bindings or confidence rounded to one. `evidence_count`
remains null.

The native Hive scenario records a report without truth, an explicit assessment,
a copy retaining its origin and a contrary alternative. Duplicate appends do
not advance the episode. A separate generated pair invokes actual native
revision under an explicit independence assumption. Reintroducing an ancestor
adds no weight. Normal replay and actual caller SIGKILL/restart preserve exact
private snapshots and decision receipts; the plugin emits only generated counts
and the public command receipt ID.

## Observed limits and reproducibility scope

The supported guarantees are local process-restart durability, one logical
occurrence/contribution under the stated replay protocol, immutable event and
belief history, current authorization, declared-port isolation and explicit
provider/profile compatibility. Formula evaluation may repeat after a crash.
Atoms, C1 append, C2 commit and relay acknowledgment are separate commits.
A durable payload without a C1 commit is an orphan, not an acknowledged event.

Private-canary tests inspect real shared DeTTa/mailbox stores, intercepted outbound
bindings, captured diagnostics, native responses and Hive traces. This proves
isolation for the tested routes under a trusted host/operator with intact local
files. It does not establish encryption, secrecy from an administrator, remote
privacy, power-loss survival or distributed failover. Authorization is the existing
local test policy, not production identity management. Assumptions do not establish
source accuracy or statistical independence; undisclosed copying is not detected.

The profile is deliberately bounded: 256 events/episode, pages and pending batches
of 16, 32 observations/belief, at most 64 supports and three CAS retries per drain.
History is retained without garbage collection or a total disk quota. No semantic
claim conversion, dynamic query/search, retraction, export, attention, inference
control, chain action or live state migration is implemented.

Fresh provider build took 337.325 seconds, including a 139.055-second native
SWI/Janus/Hive build, with new venv, native objects and DeTTa Cargo target.
Authorized SSH obtained Hive/DeTTa; public HTTPS obtained Reachability/PLN.
The provider build began before the M2 commits, so its native-build record names
workspace HEAD `6452fa7`; the native recipe/locks and compiled DeTTa adapter source
are unchanged from that baseline. Its recipe hash matches the committed M2 build
script. Final Fusion code was tested separately at the exact clean `d9e7577` state.
The tests run from a fresh detached Fusion checkout and override PYTHONPATH to
that checkout. Download caches are warm; a globally empty-cache build is NOT_RUN.
Runtime selection includes the built binary digest, so this is a reproducible
source/build/test recipe, not a claim of bit-identical binaries across hosts.
See the [runbook](runbook.md#m2-private-c1c2-real-native-revision-and-hive-episode).

## Failures and corrections retained

- An early compile command accidentally selected the host's legacy Python; it
  was rerun with the pinned Python 3.11 environment and its generated bytecode
  removed. This was not a provider or native gate pass.
- The first privacy test patched a nonexistent binding method. It now intercepts
  the actual `invoke` methods and compares real populated shared stores/messages.
- Native Hive rejected an empty kind declaration, then a receipt missing its ID.
  Both were corrected against `hive/core/programs.py`; public receipts use the
  command key, not a private content hash.
- The forged-actor test initially expected a plugin refusal. Native Hive correctly
  rejected it earlier with HTTP 400 `identity_in_request`; the assertion now
  checks that exact native response and unchanged private state.
- Under fresh-run load, the CAS race loser first returned retryable NOT_AVAILABLE
  due to SQLite contention. The test now retries the unchanged occurrence/key/head
  and requires the final CAS conflict; a transient failure is not counted as proof.
- Review added full acknowledgment-body fingerprints, detached semantic inputs,
  and snapshot lineage/premise consistency checks, with focused regression tests.

The raw failed/partial runs are retained under `evidence/m2/development/` and
indexed in the machine manifest. No failed or interrupted run is promoted to a
passing gate. Historical SWI 10.0.1 reproduction, global empty-cache builds,
power-loss/distributed failover, chain, ECAN, inference control and live migration
remain NOT_RUN or outside this implemented scope. Work stops at M2.
