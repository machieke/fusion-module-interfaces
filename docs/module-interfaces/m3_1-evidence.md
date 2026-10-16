# M3.1 — evidence delivery and feedback closure

Completed **M3.1 only**. All 12 supported acceptance gates passed; CHAIN is **NOT_RUN**. No supported runtime prerequisite was blocked. Results are sealed in the [machine manifest](evidence/m3_1/manifest.json) and [final verifier report](evidence/m3_1/final/verification.json).

## Source state

- Requested ancestor: `c4498ce3047f1283d3a4a3ae3d09b713e7dcf312`.
- Starting checkout: `3b34e00df75055d54a57ba7e38eb8b2d9e82ed7e`, master, with only the supplied M3.1 brief untracked. The intervening commit changed presentation/documentation only. Runtime/tests/build scripts matched the prior tested implementation `1af39794649d0ca95cd729c64868202368da1ec4`.
- Implementation: `0075fd42e562560187f1bebd1acb6c4daf246eec`.
- Final tested source: `1b17d74f2808703894ea55c9539adf264bc87976`. Commit `9f042108c0cdeced9efb4505fbc7cf7b7c78711b` strengthens the concurrent application/retirement test; `1b17d74` restores historical directly declared protocol signatures and rejects malformed closure inputs with typed errors. Verification uses `/tmp/fusion-m31-final-corrected`, a clean detached checkout.
- Brief SHA-256: `b84b80d41425a25998199501a39c94ce659eb5400ddbbae8bce306ea9c7af854`.
- Later report/archive commits contain evidence only. The implementation and tests are unchanged after the tested source above. No populated user stores or unrelated worktrees were modified.

Exact initial state is in [initial-source-state.json](evidence/m3_1/initial-source-state.json); [source-audit.json](evidence/m3_1/source-audit.json) records the changed-file list and 21 unchanged DA/native-math/source-lock/build files. The final machine manifest records source-file hashes, commands, log hashes, dependency status and build identity.

| Input | Exact source |
|---|---|
| Hive schematics/source-selection evidence | `4af00db4e395375484dd48d0b9068a59afcf01f8` |
| Native OmegaHive | `34b0fb32ab3806e5609fc89bb7535518a35e1aea` |
| DeTTa / secured-contract-spaces | `272888f264dd2dde18b574cabb53c266b0dac2ec` |
| Reachability guarded PLN adapter | `dd56f3f053ed90239de5377021a7d3b3fbf424ac` |
| PLN | `4405956947c4b53c7ff01bd565aa3b114bc970a1` |
| PeTTa | `ae66fa8e41dcd5539d614706bd4e5cfb34f9608d` |
| SWI source, supported version 10.1.14 | `69775434c8226897626b226aefcc8266499f1e2e` |

The unchanged `scripts/build_m3.py` recipe built fresh provider checkouts, SWI, native Python 3.12.12 environment and DeTTa target in `artifacts/m3_1/providers`. Download caches were warm. Fixture verification uses locked Python 3.11.14. Native dispatch remains the actual Hive ASGI/TestClient Programs mechanism, authenticated operator context, plugin discovery and default supervisor with native PeTTa. No runtime source or formula was substituted. Historical SWI 10.0.1 and empty-global-cache builds were not run.

## Verified findings before edits

The clean starting checkout passed the complete M3 verifier, including M1/M2 regressions. Focused real DeTTa/native PLN reproductions then confirmed the review findings:

| Before | Observation |
|---|---|
| M3 decision supplied to old C1 acknowledgment | `NOT_AVAILABLE`: v3 snapshot rejected by closed v2 validator |
| Old relay pointed at M3 C2 | `NOT_AVAILABLE`: old selected validators/profile |
| One episode with 16 pending events | Append 17 returned `OVERLOADED` |
| Clock advanced before feedback, either provider | Original feedback remained pending with the same `CONFLICT` after reopen |
| Original deadline elapsed | Execution became complete/deadline; terminal replay retained pending feedback and STI 9 |

[Baseline gap results](evidence/m3_1/baseline/gaps.json), reproduction source and logs are retained separately from corrected tests. The first probe used an M2-only claim predicate; its invalid-input traceback is labelled as a harness error, then corrected to M3 proposition claims. The expected old-profile gaps are not regression failures.

## Decisions and changed files

C1 receives a narrow, model-independent completion through a separately bound trusted local context. The relay, not C1, validates the full selected C2 decision and its exact request identity. Completing delivery means durable processing, including retained alternatives and reports; it does not assert truth. Ordinary C1/Hive callers cannot attest by constructing a matching DTO.

The actual M3 generated workflow now uses that relay as its sole evidence admission path under the new profile. Event, C2 decision, relay decision, C1 acknowledgment and relay acknowledgment remain separate commits. Lost acknowledgment replies are recovered from the relay's own committed intents, even when C1 no longer lists them as pending.

Attention owns deadline-bound application and no-credit retirement. Existing application returns the original receipt after expiry or decay. Otherwise expiry or obsolete clock/parent can atomically create a bounded causal tombstone. A delayed same-cause delivery cannot award after retirement. Neither provider retimes the intent, changes its generation, evicts records or alters belief state.

C4 reconciles only its recorded feedback intents through the Attention port, with 1–16 resolutions/call and at most 128 reconciliation commands/step. Closure observations have a separate version; the original result, terminal reason, reservations, remaining budget and deadline stay unchanged. Reconciliation does not call PLN, C2 admission or task selection. An eligible intent stays pending; an unavailable or malformed owner response stays pending with a typed reason. Same-key replay returns its original observation, while readProgress/fresh keys can observe newer closure.

New explicit profiles are C1 `episode-delivery-completion/1`, Attention `sti-additive-linear-decay-closure/1` and C4 `bounded-grounded-closure/1`, enabled by `fusion-delivery-closure/1`. The STI policy arithmetic and C2/native rule profiles are unchanged. Fresh journals are required. Old populated M3 stores remain usable under the historical profile and reject the new selection without modification.

| Files | Responsibility |
|---|---|
| `fusion/delivery_contracts.py`, `episodes.py`, `private.py`, `ports.py` | Closed completion DTO, trusted attestation context, declared journal/acknowledgment ports and explicit C1 profile |
| `fusion/evidence_relay.py`, `cognition.py`, `integration/m3_scenario.py` | Explicit selected C2 adapter, durable relay recovery and actual generated workflow wiring |
| `fusion/attention_contracts.py`, `attention.py`, `adapters/fixture_attention.py` | Deadline-bound feedback and independent serialized application/retirement transitions |
| `fusion/inference.py`, `cognition_contracts.py` | Bounded reconciliation, live selection/authority checks, separate versioned closure state |
| `fusion/beliefs.py` | Type annotation narrowed to the consumed EpisodeJournal port only; numerical implementation unchanged |
| `integration/hive/inference_program/{program.py,plugin.json}` | Authenticated prepared-request lookup, native reconciliation action and privacy-safe progress |
| `tests/m3_1_support.py`, `test_m3_1_{attention,delivery,compat}.py` | Explicit fixtures, same-profile provider comparison, trust/capacity/race/compatibility tests |
| `integration/pln/{test_m3_1.py,test_m3_1_recovery.py,m3_1_worker.py}` | Real provider/native formula checks and 16 parameterized SIGKILL cases |
| `integration/hive/test_m3_1_integration.py` | Seven real native caller cases, four involving process kills |
| `scripts/verify_m3_1.py`, supplied brief, architecture/contracts/ADR-012/runbook | Reproducible gate runner and declared design |

The verified Hive guard rejects arbitrary parameter names ending in `_key`; the public reconciliation reference is `original_command`. Its credential guard is unchanged. Programs 0.1 `done/committed` means the action returned; explicit detail separately reports execution termination, admissions, evidence backlog and feedback closure. No private episode/task/support identifiers, roots, snapshots, credentials or paths enter that projection.

## Executed verification

Commands and exact results are recorded in the sealed machine manifest. Primary commands:

```sh
# Clean original descendant, before edits:
cd /tmp/fusion-m31-baseline-3b34e00
uv run --python 3.11 --locked python scripts/verify_m3.py /home/purplezky/work/takopi/fusion-module-interfaces/artifacts/m3/providers/environment.json --output /home/purplezky/work/takopi/fusion-module-interfaces/artifacts/m3_1/baseline
# Unchanged recipe, fresh provider destination:
cd /home/purplezky/work/takopi/fusion-module-interfaces
uv run --python 3.11 --locked python scripts/build_m3.py artifacts/m3_1/providers
# Clean final tested checkout, fresh verification destination:
cd /tmp/fusion-m31-final-corrected
uv run --python 3.11 --locked python scripts/verify_m3_1.py /home/purplezky/work/takopi/fusion-module-interfaces/artifacts/m3_1/providers/environment.json --output /home/purplezky/work/takopi/fusion-module-interfaces/artifacts/m3_1/final-corrected
```

Development results are retained, including the corrected duplicate-grant revocation fixture and native parameter-name failure. An initial verification of `0075fd4` was interrupted deliberately after strengthening the race test; it is not a completed verification pass. The `9f04210` run then found one historical M2 protocol-introspection failure among 127 aggregate Python tests: inherited methods were missing from the protocol’s direct declarations. The implementation restored those historical declarations without weakening that test. A 37-test targeted correction run passed. Final results must come from `1b17d74`.

The new coverage comprises nine fixture methods, five real-provider methods, three direct process-kill methods covering **16 distinct kill cases**, and seven native Hive cases, **four with kills**. The two providers run the same consumer and closure scenarios. Repeated subsets in the historical regression runners are not additional unique tests.

## Gates

| Gate | Result | Executed evidence |
|---|---|---|
| BASELINE | PASS | Clean starting regression and gap reproductions; corrected final M1–M3 regression |
| ACK_CONTRACT | PASS | Standalone C1, trusted-context restriction, wrong/malformed completion and live replay authorization |
| C1_C2_PROGRESS | PASS | 33 real-provider observations in one episode, 16/16/1 drains; actual M3 path; deduction-ledger and non-numerical receipts |
| EVIDENCE_RECOVERY | PASS | Eight direct SIGKILL cases at four independent evidence boundaries; two native caller evidence kills |
| FEEDBACK_CLOSURE | PASS | Applied receipt after expiry/decay, stale/expired retirement, eligible/unavailable pending, immutable terminal execution |
| CAUSAL_RACES | PASS | Both serialized outcome orders and concurrent eligible application versus clock advance/retirement, on both providers |
| BUDGETS | PASS | Zero native formula calls during reconciliation, unchanged execution result/deadline/budget; historical conservative lost-reservation regression |
| PROVIDER_SWAP | PASS | Same consumer and closure semantics with SQLite and independent atomic-file fixture |
| AUTH_PRIVACY | PASS | Malformed replies, revoked grants, changed descriptors, cached replay checks and native canary/outbound isolation |
| HIVE_M3_1 | PASS | Seven authenticated native caller cases, four with SIGKILL; restart, closure projection and explicit zero-conclusion execution |
| COMPAT_REPRO | PASS | Fresh directories and original pinned build; disposable populated old stores reject new profiles and preserve old replay; caches warm |
| SCOPE | PASS | Delivery closure only; audited DA/math/build files unchanged; no scheduler, migration or new cognition |
| CHAIN | NOT_RUN | Outside this increment; no implicit pass |

Final execution counts (subsets overlap; do not sum these into a unique total):

| Suite | Passed |
|---|---:|
| M1 fixture subset / DeTTa-enabled Python aggregate | 51 / 127 |
| Upstream DeTTa library tests | 62 + 38 |
| Native Hive baseline / unchanged M1.2 integration | 34 / 13 |
| M2 fixture / upstream revision guards / native revision / recovery / native Hive | 16 / 8 / 12 / 6 / 7 |
| M3 attention / contract / upstream guard / native admission / recovery methods / native Hive | 5 / 7 / 15 / 13 / 3 / 8 |
| M3 provider comparison | Four comparison runs |
| M3.1 explicit fixtures / real-provider methods / direct recovery methods / native Hive cases | 9 / 5 / 3 / 7 |

The three new direct recovery methods cover 16 unique parameterized SIGKILL cases; the seven new Hive cases include four additional native caller kills. The two non-numerical probe cases are recorded separately. Final native pytest suites report zero failures, errors and skips. Historical M2 demo and M3 comparison artifacts are retained with their commands.

## Observed guarantees and limits

After correction, one persistent episode commits **33 distinct evidence-bearing events** in batches **16, 16, 1**, with one logical observation per occurrence and zero pending deliveries after each drain. Backpressure at 16 is explicit; draining through owner ports permits the next append. A real native deduction ledger accepts and acknowledges a later contrary observation without discarding its v3 support fields. The additional [real-provider processing probe](evidence/m3_1/non-numeric-processing.json) confirms that a report and an observation with an unregistered origin each close delivery as `model-inapplicable`, retaining one observation, no numerical truth and zero pending deliveries after reopen.

In the stale-feedback case, the original execution records one examined candidate, one reserved/completed rule attempt, one unique admission and zero applied feedback. Reconciliation retires the stale effect; STI remains 9 after the controlled clock advance. For feedback applied before a lost reply, post-deadline recovery returns the original one-unit receipt, including after decay has reduced current STI to zero. Original execution counters remain unchanged, and instrumented reconciliation makes **zero new native formula calls**. Actual SIGKILL tests cover independent evidence commits, application before acknowledgment, retirement before controller progress and progress before response.

Live revocation and descriptor changes reject new and cached operations. Malformed/pending responses never become fabricated acknowledgment or retirement. Concurrent eligible application versus clock advance/retirement yields one authoritative outcome; delayed same-cause delivery follows that outcome. The ordinary C1 fixture runs without C2, PLN, Janus or Hive loaded. Native canary checks cover responses, program metadata, native logs and Hive store files; no shared binding is created.

Real providers are local SQLite ownership, DeTTa bytes, guarded native PLN and native Hive dispatch. The independently implemented atomic-file Attention is explicitly a fixture. Generated observations, tasks, operator grants, trusted-consumer completion fixtures, guard-only/refusing math fixtures, injected malformed responses, unavailability and deterministic clock controls remain labelled as fixtures. Actual process termination is SIGKILL, not a simulated exception.

This extension cannot reconcile pre-existing M3-format pending work without migration. Disposable populated copies reject the new profile with `UNSUPPORTED_PROFILE` and still replay under the old profile; the user's populated stores are untouched. Capacity remains finite, and exhausted tombstone/command capacity can leave feedback pending. Reconciliation handles already-recorded feedback only. Unresolved derivation attempts still use the original step recovery path; reconciliation does not deliver eligible feedback, reclaim abandoned derivation rows or refund lost inference reservations. Authorization is trusted-local-host authority, not cryptographic remote attestation. Process-restart results do not establish power-loss durability, distributed failover or production privacy. No new cognition, LTI, general search, inference research, scheduler, live migration or chain work was implemented.
