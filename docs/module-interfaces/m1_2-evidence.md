# M1.2 — native Hive caller and reproducible source handoff

Recorded 2026-10-16. This increment stops at M1.2. It adds one bounded generated
sample operation through the verified native Programs route, without changing
the shared contracts or any Fusion module owner. Final gate results are below.

## Exact source state

Work began at exactly `ecfef54f0f0ab5b9bdce186af2e83184d10cc246`, with no tracked
changes and only the supplied M1.2 brief untracked. The source-discovery record is
[initial-source-state.json](evidence/m1_2/initial-source-state.json); the starting
dependency states/toolchains are in [baseline/source-manifest.json](evidence/m1_2/baseline/source-manifest.json).
No sibling worktree was reset, edited, staged or published.

| Input | Exact identity / selection |
|---|---|
| User-supplied schematics | `4af00db4e395375484dd48d0b9068a59afcf01f8`, clean; README/component index point to the intended runtime and `34b0fb3`. |
| Real Hive | `git@github.com:PhysixSNET/omegahive.git`, clean `34b0fb32ab3806e5609fc89bb7535518a35e1aea`. Observed remote HEAD `d0cee09e5c9943df14f9e08a2a40364f633e4d9f` was not selected. |
| Real DeTTa rebaseline | `ssh://git@github.com/machieke/secured-contract-spaces`, clean `272888f264dd2dde18b574cabb53c266b0dac2ec`, freshly fetched. This excludes the historical sibling's local changes. |
| PeTTa | `trueagi-io/PeTTa`, clean `ae66fa8e41dcd5539d614706bd4e5cfb34f9608d`. |
| SWI-Prolog | `SWI-Prolog/swipl-devel`, `69775434c8226897626b226aefcc8266499f1e2e` (10.1.14), selected submodules pinned by that tree. |
| Fusion adapter/tests | `85e62ae2c3e3c8bf9d91f6119b1545920c357398`. |
| Native venv environment correction | `1a627b0a214d0120886a06fc9e6af415088d20f1`; fresh native build used this revision. |
| Executed final verification source | `bb22ef5e28b089b80132b40bcf5a1bbfc38b065b`; only verifier import ordering changed after the native build. The build script, locks, adapter and tests are identical to the freshly built revision. |

The source bundle identified in the machine manifest contains Fusion only. It
does not contain Hive source, credentials, private histories or dirty sibling
changes. Authorized collaborators obtain upstream bytes by the pinned remote
fetches; successful fresh fetches establish obtainability for this run, not
permanent public access. The schematics pin selects this engineering experiment,
not a final community product release.

## Native seam and design decisions

The native startup is `hive/__main__.py:main` (`python -m hive`). The test caller
uses the same exclusive data-directory lock, startup recovery and `create_app`,
with the real default Supervisor and PeTTa, in a separate OS process. ASGI
TestClient supplies the test transport; there is no new server or HTTP protocol.
The caller signs in through native authentication, creates a swarm, and invokes
`POST /api/programs/fusion-inspect/act`. The plugin is discovered through the
existing `HIVE_PLUGIN_DIRS` loader. The path is native
`ProgramActions.person_act → Programs.act → program.act(ctx, action, items, params)`.
The [entrypoint map](discovery.md) and [ADR 007](decisions.md) give the source basis.

Hive derives the actor and command digest and rejects supplied identity fields.
The operator maps that actor/swarm to a private credential, scope and routes.
The adapter selects exact existing profiles from full descriptors, then uses only
the existing validated private stdio binding. It does not instantiate a storage
owner, read foreign SQL tables, call private Fusion helpers or branch on providers.
Wire 1.0.0, descriptor implementation 0.1.1, `immutable-bytes/1`,
`durable-mailbox/2`, `inspect-atom/2`, and output algorithm 0.1.0 are unchanged.

The only action is `inspect`, with an integer seed and stable native intent key.
It generates explicitly shareable bytes, stores them, sends their reference to a
**fixture counterparty**, delegates `inspect_atom`, and reconciles the result.
The caller records original intent before effects and pending context after
admission. It uses status `/2` to recover the known job/correlation after restart,
checks result bytes and completion identity, commits one logical accepted outcome,
then acknowledges delivery with a stable key. Cached outcomes still require live
module authorization. Unknown deliveries are not dropped or treated as causality.

The plugin's minimal receipt is the only new authoritative state. The native
operator action has no durable external-job receipt; the optional named-person
activity journal has different session requirements and leaves an interrupted
running action `in_progress`. No upstream patch or foreign-table workaround was
introduced. One unfinished intent per dedicated route bounds the slice. This
receipt is not an episodic-memory module, event bus, scheduler or migration system.
Atom persistence, job/outbox commit, mailbox acceptance, caller acceptance and
recipient acknowledgement remain separate commits.

## Executed checks

The initial unmodified checkout was executed before edits:

| Command / source | Observed result |
|---|---|
| `uv run --python 3.11 python scripts/verify_m11.py --fixture-only` | 51 tests passed; two fixture demonstrations. |
| `uv run --python 3.11 python scripts/verify_m11.py` with historical dirty DeTTa | 90 tests passed; four provider/transport demonstrations. |
| `cargo test --offline --locked -p detta-da -p detta-storage --lib` in the untouched sibling | 62 DA + 40 storage passed. |
| Same full M1.1 command in a disposable baseline checkout with clean fetched DeTTa | 90 passed, four demonstrations; clean upstream later passed 62 + 38. |
| Pinned native Programs/API/actions/confirmation tests, before attaching Fusion | 34 passed, no skips; upstream fake process driver explicitly retained in this baseline. |

The fixture 51 are a subset of the full 90, not 51 additional distinct tests.
The dirty-to-clean DeTTa comparison identified storage format/migration and
custody-pruning additions outside the current opaque fresh-store API; two storage
tests belong to those local additions. Clean-source passes rebaseline the selected
profile; they do not reproduce historical dirty bytes. Historical reports remain
unchanged. Original baseline scripts' hard-coded OMEGA BLOCKED strings are retained
as historical output, not used as the current M1.2 gate.

The fresh recipe was invoked as:

```bash
git clone --branch master artifacts/m1_2/fusion-m12-source.bundle artifacts/m1_2/fresh
# In the fresh clone:
uv run --python 3.11 --locked python scripts/build_hive.py artifacts/native
uv run --python 3.11 --locked python scripts/verify_m12.py artifacts/native/environment.json
```

The verifier-only correction was obtained through the source bundle and a Git
fast-forward before executing the tests. No binary, venv, source working change,
or target directory was copied from the original checkout. The fresh native build
took 139.595 seconds. Its checks observed SWI 10.1.14, Prolog→Python = 42,
Python→Prolog = 2, and a generated PeTTa expression = 42. Python interpreter/uv and
Cargo download caches were warm. Native `uv pip sync --no-cache` downloaded its
locked dependencies and rebuilt Janus against the private prefix. A globally
empty-cache build is NOT_RUN, not implied by the fresh-directory pass.

The tested host is Linux x86_64/glibc 2.31, Python 3.11.14 for M1.1 and 3.12.12
for Hive, Rust/Cargo 1.88.0, CMake 3.16.3, Ninja 1.10.0, GCC 9.4.0, uv 0.10.7.
GMP 6.2.0, OpenSSL 1.1.1f, PCRE2 10.34 and zlib 1.2.11 were present. Optional
libarchive, libyaml and libedit native headers were absent; CMake's omissions did
not prevent these Programs gates. See [native-prerequisites.json](evidence/m1_2/native-prerequisites.json).
The [runbook](runbook.md) documents the supported recipe and cache assumptions.

Final fresh-directory results and exact commands are recorded in
[verification.json](evidence/m1_2/verification.json); raw logs, JUnit results, lock
hashes and source identities are retained alongside it. All executed final gates
passed, with zero test failures/errors/skips:

| Fresh run | Result |
|---|---|
| Fixture-only, DeTTa/Hive source paths deliberately absent | 51 passed; two fixture workflows. |
| Full M1.1 provider/transport matrix, clean real DeTTa | 90 passed; four workflows (two real DeTTa, two independent file fixtures). |
| Clean upstream DeTTa | 62 DA + 38 storage passed. |
| Native Hive baseline before plugin attachment | 34 passed; upstream process-driver fixture labelled. |
| Real Hive caller + real DeTTa + fixture counterparty | 13 passed; native authentication, dispatch and process recovery. |

The final fresh checkout is clean. The [source manifest](evidence/m1_2/source-manifest.json)
records code/lock hashes and paths. [Sibling preservation](evidence/m1_2/sibling-preservation.json)
confirms the original sources retain their exact initial commits, worktree status
and tracked-diff fingerprints.

## Recovery and refusal observations

The 13 native cases cover the happy path/replay, three caller SIGKILL checkpoints,
worker SIGKILL after atom persistence, full reply route, terminal worker revocation,
wrong scope, revoked caller, incompatible profile, changed descriptor, supplied
identity, and changed semantic input under the same key. Every case enters through
the actual authenticated native action route. Host-owned worker commands and
failure injection remain test/operator controls, not plugin capabilities.

The recovery assertions inspect durable counts and receipts: one job, one result
atom, one outbox entry and one completion delivery; one accepted caller outcome;
redelivery until acknowledgement and no delivery after acknowledgement. A lost
admission response keeps the same job identity when retried. Worker death before
terminal commit leaves a queued job while its result atom persists. Full-route
failure retains the outbox and never creates an accepted caller outcome. Worker
revocation yields an explicit failed completion with no result atom. Scope,
profile, descriptor and replay-conflict refusals never create another job.

Temporary input unavailability is covered by the unchanged M1.1 matrix; the new
native representative provider-failure case is full reply-route backpressure.
That distinction is intentional. No test of live provider replacement or state
migration is claimed. The concrete generated trace is [hive-trace.json](evidence/m1_2/hive-trace.json).
Its original job acceptance still says queued/not-observed: that receipt records
admission, not terminal state. The final native outcome records the verified result
and observed completion delivery ID separately.

| Trace field | Observed value |
|---|---|
| Native actor / swarm | `user:operator` / `s_2ccf3f15` |
| Scoped input reference | `shared-test:a1b8c6b7-5dce-58c2-8880-c8492bbc3b36`, revision 1 |
| Input digest / length | `2e1748d637a3c6173c6021f3597fa403a43293c21f5ac861ce7921a90d7276b9` / 53 bytes |
| Job / completion delivery | `37fb2f12-9a0b-5eb7-9927-31208c06c687` |
| Correlation / caller receipt | `0573fa6e03b2edbc73855e849eab46b8c93d223c96cc67d4d5b8828cf96e7306` |
| Result reference | `shared-test:aa57a16c-94e2-5d5d-9ee7-121ae3dbfc82`, revision 1 |
| Result digest | `cd2f727689b41e243ee78207d058d00b8be64932abbfd86a02851dfcbac400bb` |
| Persistence | Both receipts `detta-local-rs/1`, local files/process restart, six shares, threshold four; no chain/custody certificate. |

## Failures and corrections retained as evidence

- `gh` was unavailable; noninteractive HTTPS Git could not authenticate. Existing
  authorized SSH access succeeded. Source availability was resolved, not faked.
- The unmodified upstream setup script rejected CMake 3.16's correct `PATH` cache
  entry because it expected `INTERNAL`. The narrow recipe verifies include/library
  values independently of cache type, then executes both live bridges.
- One exploratory uv invocation used unsupported `--no-binary-package`; the
  supported `--no-binary` option was used thereafter.
- Development tests initially expected an unwrapped worker result, assumed a
  journal existed before profile admission, and expected a generic native error
  instead of `identity_in_request`. These were test-driver assertions, not weakened
  provider checks. The executed failures and targeted correction remain in
  `evidence/m1_2/development/`.
- The first fresh build passed but exposed an inherited Python 3.11 `VIRTUAL_ENV`.
  A second fresh build explicitly selected the native 3.12 venv and passed.
- The first verifier run stopped at a source-path gate before tests because
  discovery was imported before applying environment overrides. The corrected
  verifier loads paths first; [failed-preflight-order.json](evidence/m1_2/failed-preflight-order.json)
  preserves the failed attempt. This was an implementation error, not absent source.
- Native baseline emits a Starlette TestClient/httpx deprecation warning. The
  pinned environment remains tested; no unrequested runtime dependency upgrade
  or upstream source edit was made to suppress it.

## Gate-by-gate outcome and limits

| Gate | Result | Evidence / practical boundary |
|---|---|---|
| BASELINE | PASS | Fresh original 51/90 and dirty upstream 62+40; historical bytes explicitly identified. |
| HIVE_SOURCE | PASS | Intended source, full revision, native startup/plugin/dispatch inspected and fetched with authorized SSH. |
| FIXTURE_REPRO | PASS | Fresh bundle checkout; deliberately absent real provider/runtime source paths; 51 tests. |
| DETTA_REPRO | PASS | Fresh immutable clean source, locked new adapter build, 90 tests + 62/38 upstream; warm Cargo downloads. |
| HIVE_ENTRYPOINT | PASS | Actual native authentication and Programs dispatch in the unmodified runtime; ASGI test transport only. |
| HIVE_DETTA | PASS | Same native workflow uses real DeTTa receipts and existing messaging/execution; counterparty remains fixture. |
| HIVE_RECOVERY | PASS | Real caller/worker SIGKILL, admission replay, status correlation, acceptance-before-ack replay, backpressure and fail-closed cases. |
| HIVE_REPRO | PASS | Fresh fetched sources, private native build, locked dependencies and actual 34/13 runs. Authorized source access and warm Python/Cargo downloads required. |
| CHAIN | NOT_RUN | No same-artifact chain submission; historical source reproduction needs exact authorized F1R3 changes or a separate rebaseline. |
| SCOPE | PASS | M1.1 owners/contracts unchanged; no M2, ECAN, inference control, live migration or new framework. |

The [machine manifest](evidence/m1_2/manifest.json) separates current passes,
historical source-distribution blockers and unrun scope. No required local Hive
or DeTTa gate remains blocked in this environment.

The supported guarantee is bounded same-host process restart with persistent
files intact, one local worker and one pending caller intent per dedicated route.
It does not establish power-loss survival, distributed failover, exactly-once
physical execution, arbitrary side-effect recovery or indefinite DA custody.
Descriptor hashes bind request/response selection; they do not prove remote
identity or provider truth. Compatibility remains exact-profile selection, not
live rolling upgrades. DeTTa is real local DA/FileStorage, not a validator network.
Native dispatch is real Hive; the generated sample and counterparty are fixtures.
No LLM, ECAN, inference control, M2 module, live migration or new cognitive model
was implemented or used to manufacture completion.

The optional same-result chain workflow is NOT_RUN. Historical F1R3 dirty source
and its untracked source input are still outside the supplied immutable recipe;
reproducing that historical gate requires authorized exact bytes/patches or a
separate clean-source rebaseline. It is not a prerequisite of the passed local
storage/caller gates. Other deployments, full Hive suites, named-person/mind
actions and entirely empty download caches are unrun scope, not fixture passes.

## Changed files

| Files | Purpose |
|---|---|
| `integration/hive/program/{plugin.json,program.py}` | Verified native plugin and minimal caller-owned receipt/recovery. |
| `integration/hive/{native_caller.py,test_integration.py}` | Actual native startup/dispatch transport and process recovery/refusal tests. |
| `integration/hive/{sources.json,requirements.in,requirements.lock,build-constraints.txt}` | Obtainable immutable sources and locked native dependencies. |
| `scripts/{build_hive.py,verify_m12.py}` | Specific fresh build and gated execution recipe. |
| `scripts/{discovery.py,preflight.py,verify_m11.py,swap_demo.py}` | Configurable actual runtime paths and current observations; protocol fixtures no longer emit a hard-coded current runtime blocker. |
| `README.md`, `docs/module-interfaces/{architecture.md,contracts.md,decisions.md,discovery.md,runbook.md,m1_2-evidence.md}` | Scope, native seam, ownership diagram, design decisions and tested handoff. |
| `docs/module-interfaces/evidence/m1_2/` | Source/lock identities, initial/final runs, trace and retained failures. |
| `codex_fusion_m1_2_real_hive_integration.md` | User-supplied brief, preserved and committed. |

`fusion/`, the schemas, Rust adapter and all existing contract/recovery tests are
unchanged. The final documentation/evidence commit follows the executed source
revision without altering its implementation. Stop before M2.
