# Reproduce the bounded gates

## M1.2: pinned real Hive caller

Use the implementation revision and source bundle recorded in
[M1.2 evidence](m1_2-evidence.md), in a fresh checkout. The source pins are in
`integration/hive/sources.json`. Git SSH access must already authorize the
developer for `PhysixSNET/omegahive` and `machieke/secured-contract-spaces`;
the recipe uses batch mode and strict host-key checking. It never obtains or
bundles credentials. Public PeTTa and SWI sources use HTTPS.

Required Linux tools: uv, Git, C/C++ compiler, CMake, Ninja, pkg-config, Rust/Cargo
1.88.0 (the tested toolchain),
and native headers for GMP, OpenSSL, PCRE2 and zlib. The inspected upstream recipe
also recommends libarchive, libyaml and libedit headers; this host lacks those
optional packages. Record CMake's actual package selection. The supported slice
does not need the mind smoke environment, chromadb, an LLM, node RPC or chain.

```bash
# From the fresh Fusion checkout; artifacts/native must not exist or be empty.
uv run --python 3.11 --locked python scripts/build_hive.py artifacts/native > /tmp/fusion-hive-build.log 2>&1
uv run --python 3.11 --locked python scripts/verify_m12.py artifacts/native/environment.json
```

The build fetches immutable clean sources, creates a Python 3.12.12 venv and a
private SWI 10.1.14 prefix, checks the actual Python include/library paths in
CMake, and exercises both Janus bridges and a generated PeTTa expression.
It does not patch upstream. The original Hive script's `INTERNAL`-only CMake
cache guard rejects CMake 3.16's correct `PATH` value; the recipe checks values
independently of cache type. Hash-locked native requirements are installed with
`--no-cache --no-binary janus-swi`, so Janus is compiled against this prefix.
The build backend is pinned separately. Source submodule commits come from the
pinned SWI tree. The recipe does not claim coverage of other platforms.

Cargo is deliberately invoked offline with checked-in locks. Its crates.io
downloads must be populated already. On a host without them, an online
`cargo fetch --locked --manifest-path artifacts/detta-build/Cargo.toml` can populate
the adapter cache after `scripts/build_detta.py` has written that manifest and
reported the cache miss. Populate the selected upstream checkout's locked Cargo
dependencies too. That empty-cache preparation was not exercised in this run;
no private or unlisted compiled artifacts are required by the warm-cache recipe.

Verification first runs fixture-only checks with deliberately absent DeTTa/Hive
paths, then the four-way M1.1 matrix against clean real DeTTa, upstream DA/storage,
native Hive Programs baseline, and actual native caller recovery tests. Python
and Cargo download caches may be warm. All venvs, adapters, native objects and
test stores are built afresh; this is **not** a claim of a wholly empty-cache run.
`artifacts/native/build.json` and `artifacts/m1_2/{verification,preflight}.json`
record sources, commands, lock hashes, timings and test outcomes. Build/source
errors stop the recipe; a failed executed test remains FAIL. Chain is NOT_RUN.

The verified native startup is `python -m hive`. The test driver uses the same
exclusive data-directory lock, startup recovery and `create_app`, including
real PeTTa and the default Supervisor, with FastAPI TestClient as an in-process
ASGI transport. Each caller runs in a separate OS process, signs in through
`/api/auth/login`, and invokes `POST /api/programs/fusion-inspect/act`. No test
listener is exposed and no mind or LLM is started. Upstream baseline tests use
their declared fake process driver; the new integration does not.

`HIVE_PLUGIN_DIRS` selects `integration/hive/program`. `FUSION_HIVE_CONFIG` names
a mode-0600 operator configuration with `service_config`, `receipts`, full
`descriptors` from the existing describe operation, and `grants` mapping exact
native `principal`/`swarm` to `credential`, `scope`, `reply_route`, `counterparty`.
The fixture harness generates these inputs; credentials are never action params
or checked-in evidence. The grant does not override Fusion's live authorization.
The one action is `inspect`, `params={"seed":12}`, with a stable native
`idempotency_key`. Repeat the identical request to reconcile it. Only generated
non-sensitive bytes are accepted. Use a dedicated reply route with one unfinished
intent at a time. Provider selection changes require fresh stores/context; there
is no migration or automatic switch.

The plugin owns only its receipt database. `started` with a pending receipt means
the delegated job or its completion is pending; it is not a Hive goal. `done`
means the result and correlated delivery were verified, one logical outcome was
recorded, and acknowledgement succeeded. Terminal worker failures remain explicit
errors. Retrying after an ambiguous acknowledgement reuses its original key.
Only trusted test configuration enables caller SIGSTOP checkpoints. Worker
failpoints remain the existing operator-only Fusion commands.

## M1.1 conformance and historical sources

From this repository, with Python 3.11 available through uv and the inspected
DeTTa checkout as a sibling:

```bash
uv run --python 3.11 python scripts/preflight.py
uv run --python 3.11 python scripts/verify_m11.py
```

This fingerprints dependencies, builds the external adapter with offline Cargo,
runs the same conformance suite with real DeTTa and independent file AtomStorage
providers under in-process and subprocess bindings, and executes all four
combinations of the unchanged two-peer workflow with a separate worker. Failures
remain failures; missing DeTTa is not silently replaced by a memory store. Set
`DETTA_REPO` for a different checkout, inspect its resulting fingerprints, and
revalidate before treating it as the same provider.

`artifacts/m1_1/{preflight.json,build-detta.log,tests.log,verification.json,swap-demo.json}`
contain fresh local evidence; the checked-in M1.1 snapshot is separate from M1. Each demo uses a fresh mode-0700 directory. Its
`config.json` selects paths, capacities, credentials, scopes and reply routes;
credentials are generated fixtures and are not included in the checked-in report.
`fusion/composition.py` selects the storage implementation. `Peer` depends only on
the binding contract; changing `Harness(binding=...)` swaps invocation transport.

Atom metadata, mailbox and execution/admission have separate owner stores.
Set `atom_provider` to `detta` (default) or `fixture-files` in trusted configuration;
`atoms_database`, `messages_database`, `database`, `da_root` and fixture-only
`atom_records` select paths. Execution and Peer remain unchanged. No credentials
or caller-selected provider name go into an operation body. Old M1 combined
journals are rejected: create fresh M1.1 stores; no migration is implemented. Worker and reconciliation commands are trusted
operator entry points, not public module operations:

```bash
uv run --python 3.11 python -m fusion.host work /absolute/path/to/config.json
uv run --python 3.11 python -m fusion.host flush /absolute/path/to/config.json
```

`--pause-at` requires the explicitly enabled test configuration. Tests wait for a
marker, then send actual SIGKILL. Those checkpoints distinguish acceptance before
response, atom commit before admission commit, result atom commit before
job/outbox commit, terminal completion commit before dispatch, and mailbox
acceptance before the outbox records delivery. Process death does not exercise power loss or filesystem
corruption beyond the separate destructive fixture tests.

For contract and independent fixture checks without external DeTTa:

```bash
uv run --python 3.11 python scripts/verify_m11.py --fixture-only
```

This executes only the named fixture/pure classes and two fixture demos. Its
`fixture-tests.log`, `fixture-verification.json`, `fixture-preflight.json` and
`fixture-demo.json` do **not** pass real DeTTa, Omega or chain gates. The recorded
isolation run set `DETTA_REPO=/tmp/fusion-m11-deliberately-absent-detta` to prove
that the fixture command remains runnable when real source is missing.

Preflight exits 2 when required real DeTTa source or Cargo is absent; an offline
locked build failure also prevents the real gate from passing. Its manifest
records interpreter/toolchains, current and initial repository state, all inspected
dependency revisions/diffs/source hashes, and pinned build locks. `DETTA_REPO`
and `F1R3_REPO` overrides affect the source ledger as well as build selection.
Tool presence is a prerequisite observation, not an integration pass.

The historical DeTTa and F1R3 working trees contain modifications not distributed
here. Their HEAD hashes alone cannot reproduce these runs. Obtain the exact
authorized working source/patches or choose and validate a new immutable revision.
M1.2 rebaselines clean DeTTa at the same HEAD through the recipe above; it does
not reproduce the historical modified bytes. F1R3 reproduction remains unresolved.
A hash manifest supplies identity, not missing source. No sibling changes were
reset, staged or committed by either task.

`uv run --python 3.11 python scripts/schema.py` regenerates both portable schemas.
The suite verifies checked-in schemas and per-operation shape/semantic validation.
`scripts/verify.py` remains the original local-gate entrypoint; on current source
it discovers the expanded suite, builds real DeTTa and runs two real demos. It
still never runs the optional real chain gate. Historical baseline logs used the
27-test checkout at the recorded initial commit.

To repeat the upstream generic DA regression gate:

```bash
cd ../secured-contract-spaces
cargo test --offline --locked -p detta-da -p detta-storage --lib
```

## Optional real local chain gate

Use the inspected Rust source, installed pinned nightly, native dependencies and
Cargo cache. The host's protoc 3.6.1 fails on current Proto3 optional fields, so
stage a compatible compiler without changing upstream sources:

```bash
uv run --python 3.11 --with 'grpcio-tools==1.84.0' python scripts/build_chain.py
uv run --python 3.11 --with 'cryptography==50.0.2' --with 'pycryptodome==4.0.0' --with 'grpcio-tools==1.84.0' python scripts/chain_demo.py
```

Set `F1R3_REPO` to override `/home/purplezky/work/asi/f1r3node-rust`. The script
uses the existing node implementation, fresh generated keys/genesis, selected
free local ports, and the repository's 8 MiB thread stack setting. It shuts down
its own node in a finally block. It never attaches to a production chain.
The node's P2P implementation binds its protocol port to all interfaces even
when advertising 127.0.0.1; the API is loopback, network ID is isolated, and no
peers are configured. This is a development integration, not a hardened service.

The current debug CLI's deploy help panics and keygen tries to connect to a node.
The adapter therefore uses the inspected HTTP API. It derives the exact deploy
protobuf message from the inspected source and signs its Blake2b-256 digest with
secp256k1, matching the source implementation. `F1R3Commitments` pins the approved
non-sensitive result and persists a signed intent before network submission.
Retries reuse the same signature; fixture tests exercise an ambiguous timeout.

Only a generated result digest is submitted. The script records actual deploy ID,
block, cost, execution error, rejection count and canonical effect finality in
`artifacts/chain-demo.json`. A block-finalized flag alone cannot pass this gate.
Missing dependencies, failed genesis or absent finality produce a blocked report
and nonzero exit, never synthetic evidence. Signing/provider proof verification
and production policy integration remain separate gates.

The checked-in evidence snapshot is a report of the executed run, not a claim
that newly selected checkouts or environments have passed. M2/C1/C2 are not run
by these commands; future cognitive conformance fixtures remain specifications.

## Omega runtime gate

See [the verified seam note](discovery.md#m11-omega-runtime-seam-blocked).
No intended `omegahive/hive` runtime, revision, entrypoint or startup command was
available. Do not replace the missing checkout with Peer, the onboarding repo or
hive-appliance. A future integration must first pin the authorized actual runtime,
then call the existing contracts from a verified memory/tool/transformation entry
point using generated shareable bytes and retain its original interface.

## M2: private C1/C2, real native revision and Hive episode

Use the tested implementation commit in [M2 evidence](m2-evidence.md).
The M1.2 Linux toolchain and authorized Git SSH access above remain required.
The M2 recipe also retrieves public Reachability and PLN at immutable pins;
`integration/pln/sources.json` records their identities and formula/source hashes.
It never edits a sibling checkout or the historical SWI 10.0.1 guard.

```bash
# Run from the selected Fusion checkout, with an empty provider destination.
uv run --python 3.11 --locked python scripts/build_m2.py artifacts/m2-providers > /tmp/fusion-m2-build.log 2>&1
uv run --python 3.11 --locked python scripts/verify_m2.py artifacts/m2-providers/environment.json
```

The first command runs the unchanged native Hive build recipe into a fresh
SWI/Janus/Python prefix and venv, verifies pinned Reachability/PLN, and compiles
the Rust DeTTa adapter into a fresh Cargo target. It writes explicit non-secret
runtime paths, binary hash, source pins, build record and cache scope. Git,
Python and Cargo download caches may be warm. No native objects, venv or Cargo
target are copied. A global empty-cache build is a separate NOT_RUN condition.
The M2 DeTTa build permits fetching locked crates; M1 regression still uses the
existing offline locked recipe and therefore needs its recorded Cargo cache.

The verifier reruns M1.2, then C1/C2 fixtures with real provider paths deliberately
absent, actual DeTTa/native PLN, cross-owner SIGKILL/privacy, real authenticated
Hive dispatch and a deterministic generated demo. Missing real prerequisites
produce BLOCKED records or executed failures; none become skips or fixture passes.
Logs and the machine manifest go to `artifacts/m2/final/` by default. Original
M1.2 artifacts remain under their existing path; the verifier embeds that result
and does not rewrite committed historical evidence.

For an already built, verified environment, these narrower commands help locate
a failed gate (real tests still require their explicit environment variables):

```bash
uv run --python 3.11 --locked python -m unittest -v tests.test_m2
# Use the environment's VIRTUAL_ENV/bin/python with M2_REVISION_ENV,
# M2_DETTA_BINARY, PETTA_PATH, HIVE_REPO and native library paths set:
python -m unittest -v integration.pln.test_revision integration.pln.test_recovery
python -m pytest -q integration/hive/test_m2_integration.py
python scripts/m2_demo.py artifacts/m2-providers/environment.json artifacts/m2/demo.json
```

Do not use this host's unqualified legacy `python` outside the selected environment.
Use `uv run --python 3.11 --locked python` for fixture scripts and the recorded
Python 3.12 venv for Hive. Generated demo observations and origin/independence
assumptions are fixtures; their DeTTa, PeTTa and Hive providers are real.
The CLI prints only generated test summaries. Private owner databases are not
export artifacts and must not be placed in shared or chain roots.

Private configuration supplies `private_root`, non-overlapping `shared_roots`,
`private_scopes`, `private_descriptors`, local `principals`/method permissions,
registered `origins`, `detta_binary` and `revision_environment`. See
`tests/m2_support.py` for a generated local policy example. Real production
identity and key management are not established by this test policy. To use
only C1, call `open_private(..., with_revision=False)`; no PLN or Hive dependency
is loaded. To retry a pending intent, reopen the same owners and relay and drain
the same episode with the same declaration. Do not change an attempt's expected
revision, selected provider or assumption under its existing key. A changed
profile/binary requires a new compatible deployment/history; live migration is
outside M2. Continue only after resolving an authorization/profile failure,
never downgrade to a fixture automatically.

## M3: independent STI and bounded grounded inference

Start with the exact implementation SHA in [M3 evidence](m3-evidence.md). The
requested ancestor is `f0cee248294a1fce42913782390e6c084025c67e`; execution began at
`926882afb9ab9c7288bf663f96f9e1ca63dd8520` (presentation and brief-only descendants).

```bash
uv run --python 3.11 --locked python scripts/build_m3.py artifacts/m3/providers
uv run --python 3.11 --locked python scripts/verify_m3.py \
  artifacts/m3/providers/environment.json --output artifacts/m3/final
```

The build destination must be empty. This extends the unchanged M2 source/build
recipe: exact Hive, DeTTa, Reachability, PLN, PeTTa and SWI sources, a new native
build/Janus environment and new DeTTa target. It adds a separate deduction runtime
configuration; it never widens the revision-only allowlist or rewrites Reachability's
historical 10.0.1 lock. Network/authorized Git source access and the compiler/tool
prerequisites of M1.2/M2 are required. Download caches may be warm. Provider paths
must remain unchanged after building. `environment.json` contains local environment
configuration and must not be published wholesale.

`verify_m3.py` initializes each gate to NOT_RUN, records source SHA/status/file
hashes, runs the unchanged M2 verifier (which runs M1.2), then standalone attention,
contract fixtures, pinned upstream guard fixtures, native deduction/admission,
actual SIGKILL recovery, actual Hive action and the controlled provider comparison.
Absent native inputs are BLOCKED prerequisites, never fixture passes. Failures stop
the verifier with retained logs. Detailed runtime and comparison data are saved in
`verification.json` and `comparison.json`. Fresh cloned checkouts need `artifacts/`
for the inherited M1 verifier; it creates its own regression artifacts.

For a focused fixture-only gate, no native environment is required:

```bash
uv run --python 3.11 --locked python -m unittest -v \
  tests.test_m3_attention tests.test_m3
```

For native subsets, use the built environment's `VIRTUAL_ENV/bin/python` and export
its declared `M2_REVISION_ENV`, `M2_DETTA_BINARY`, `M3_DEDUCTION_ENV`, `PETTA_PATH`,
`HIVE_REPO`, `LD_LIBRARY_PATH` and other native variables. Execute
`integration.pln.test_deduction`, `integration.pln.test_m3_recovery`, or pytest on
`integration/hive/test_m3_integration.py`. Do not accidentally run these with an
unconfigured system Python; missing Janus library paths are not a valid native pass.

Composition uses the original private C0/C1 descriptors plus `cognition_descriptors`
from `fusion.cognition.descriptors()`, `attention_policy` parameters, and explicit
`attention_provider` (`sqlite` or `atomic-file-fixture`). Fresh M3 owner filenames
keep old M2 journals under their original profiles. Changes to policy, provider,
runtime or descriptor identity reject incompatible populated stores. The swap test
always starts fresh stores; no state migration is provided.

The verified sibling plugin directory is `integration/hive/inference_program`.
The native action `fusion-inference / infer-generated` accepts only a generated
seed, preference `a`/`b`, and absolute `deadline_ms`. Operator-owned
`FUSION_M3_HIVE_CONFIG` maps authenticated Hive principal/swarm to private local
credentials and scope. The trusted Programs actor supplies identity; request bodies
cannot supply it. One action creates a private 12-event episode (10 generated
observations, action and result), two grounded tasks and a one-attempt step.
Only generated counts/status are returned publicly. Existing inspect/episode
plugins are unchanged. Test pause hooks are operator-only fixtures.

Recovery must use identical input and deadline. A spent reservation is not refunded.
A pending C2 attempt without a committed decision requires a new reserved slot/key;
with no remaining slot the step terminates without a conclusion. A committed C2
decision is recovered before allocating further work. Feedback has its own durable
intent and causal deduplication. A concurrent attention clock advance may leave
explicit pending CONFLICT feedback; the implementation never silently reschedules
it. Deadline expiry is terminal for that bounded request, even if feedback remains
unacknowledged. Check the receipt's counters/results/pending state; `complete` means
the bounded attempt ended, not that all possible conclusions were found.

Generated C1 observation delivery intents are intentionally retained: M3 does not
forge a version-2 acknowledgment out of its version-3 belief snapshot. No shared DA,
mailbox, chain or public Hive route carries the private trace. No LTI, general search,
attention research, live migration, inference expansion or M4 work is included.

## M3.1 delivery closure verification

Use fresh disposable directories. Do not point the new profile at populated M3
owner stores. `tests/m3_1_support.py` is an explicit generated-policy example;
operator configuration must select the new C1/C3/C4 descriptors, grant their new
operations and bind `evidence_consumer` to the exact selected C2 principal,
provider, profile and descriptor token. Ordinary episode clients receive no
completion-attestation context. Select either `sqlite` or `atomic-file-fixture`
before creating fresh journals; provider replacement is not state migration.

```sh
uv run --python 3.11 --locked python scripts/build_m3.py /absolute/fresh/providers
uv run --python 3.11 --locked python scripts/verify_m3_1.py /absolute/fresh/providers/environment.json --output /absolute/fresh/evidence
```

The build recipe and source pins are unchanged. Download caches may be warm;
provider checkouts, SWI build, native venv and DeTTa target are fresh. The verifier
runs M1–M3 regressions, explicit closure fixtures, real-provider tests, actual
SIGKILL recovery and authenticated native Hive dispatch separately. Missing native
inputs are BLOCKED, never replaced with fixture passes. Real tests must not skip.

For the native closure action, send the existing generated `infer-generated`
request with its original absolute `deadline_ms`. To observe closure later, use
`reconcile-generated` with `{original_command: <original public command>, limit: 1}`
and a distinct public idempotency identifier. Reuse a reconciliation identifier to
recover its exact response; use a new one for a newer observation. Inspect the
explicit detail fields, not only the Hive envelope. A deadline can end execution
without admitting any conclusion, and feedback closure can remain pending.

Limits remain finite: 16 pending deliveries/episode, 256 episode events, existing
Attention capacities and 128 reconciliation commands/step. Eligible feedback is
not newly delivered by reconciliation; expiry or staleness permits no-credit
retirement. An unavailable owner remains pending. Full causal/command journals
are not evicted. Old-format pending work requires the old profile; this task does
not migrate or repair it. See `m3_1-evidence.md` for exact tested source and gates.

## M4 required isolated-chain reproduction

Use a fresh Fusion checkout as well as fresh provider/output directories. This
also gives the historical M1 verifier an empty compatibility build target:

```sh
git worktree add --detach /absolute/fresh/fusion 55ed5402391ab6ed14f8ab20e1eea4c85d8be955
cd /absolute/fresh/fusion
```

Prerequisites: authorized Git access to the pinned Hive/DeTTa/PLN sources and the
named F1R3 fork, `uv`, Rust nightly `2026-02-09`, C/C++/SWI native build libraries,
OpenSSL development files, `ip`, `ss`, and permission for unprivileged user/network
namespaces. The existing native provider pins are unchanged. Optional signing and
protobuf Python dependencies are pinned in `integration/chain/requirements.lock`.
Download caches may be warm; source, build, venv, journals and genesis directories
must be fresh. No existing user node or private cognitive journal is an input.

```sh
uv run --python 3.11 --locked python scripts/build_m4.py /absolute/fresh/m4-build
uv run --python 3.11 --locked python scripts/verify_m4.py /absolute/fresh/m4-build --output /absolute/fresh/m4-evidence
```

The verifier starts the real native run in a route-free network namespace, checks
host inaccessibility while the node is ready, and stops its generated node on
completion. It also runs the full M1–M3.1 baseline on the exact committed checkout.
A missing input is BLOCKED; an executed assertion is FAIL; an elapsed bounded
chain observation is OBSERVATION_TIMEOUT. Development mode cannot pass BASELINE
or REPRO_READBACK and never yields overall M4 PASS. Historical evidence stays intact.

`same-artifact.json` contains only deliberately shareable generated identifiers,
result refs/digests, approval, chain instance/profile, signed deploy, observed value
and matching finality. `readback.json` is produced by another process using only
`atom.storage.get` authority and read RPC. Test keys and all raw runtime configs,
logs and journals remain in ignored private directories; do not publish them.
The verifier also preserves independent owner counts, native SIGKILL cases and
same-genesis node restart, including an outage between observations.

For a local operator session, register both `integration/hive/program` and
`integration/hive/commitment` with native `HIVE_PLUGIN_DIRS`. Follow the concrete
operator-only composition in `integration/chain/test_m4.py`; its `commitment`
allowlist is not an action parameter. Complete and acknowledge the original
`fusion-inspect` command first. Then dispatch `commit` with
`{original_command: <allowlisted generated command>}`. Re-dispatch `commit` after
an uncertain submission to recover the same signed intent. Dispatch `observe`
to read progress without re-running the worker or submitting another deploy.
Unavailability does not retract off-chain completion or change the genesis.
Replaying `commit` returns its original submission receipt; use `observe` for a
new chain observation. An unavailable observation does not erase earlier evidence
from the chain owner's journal.

A second process can run:

```sh
<NATIVE_PYTHON> scripts/readback_m4.py <PRIVATE_READ_ACCESS_JSON> <SAME_ARTIFACT_JSON>
```

Run it inside the same isolated namespace while the node and permitted DA files
are available. The access file supplies only a service configuration path,
a credential restricted to `atom.storage.get`, and the isolated RPC endpoint;
it contains no signer or original caller journal. Historical block/post-state
availability and local DA file retention are prerequisites, not indefinite-storage
promises. The completed test stops its node; the readback test is executed before
shutdown and after restarting the same generated data/genesis. Do not reconnect
this profile to a public network. No automatic scheduler, production deployment,
state migration or further cognition is included.

## M5 private lookup reproduction

M5 uses the unchanged locked M3 provider build (Hive, PeTTa, SWI, local DeTTa and
legacy PLN regression inputs). It does not need PLN for lookup. Linux prerequisites,
private Hive Git access and native build tools are the same as above. Use an empty
provider destination; Cargo/uv/download caches may be warm. The M4 real regression
reuses the already pinned node build in a new route-free network namespace and
fresh generated state. The existing M4 Python signer/protobuf lock must also be
installed for the legacy chain suite; the M3 provider build alone does not install
it. No lock or version is changed. It introduces no new chain operation.

```bash
uv run --python 3.11 --locked python scripts/build_m3.py artifacts/m5/providers
uv pip install --python artifacts/m5/providers/native/venv/bin/python \
  -r integration/chain/requirements.lock
uv run --python 3.11 --locked python scripts/verify_m5.py \
  --environment artifacts/m5/providers/environment.json \
  --chain-build artifacts/m4/reproduction-01/chain \
  --output artifacts/m5/final
```

If no pinned node build is available, the unchanged
`scripts/build_m4.py <empty-destination>` recipe builds all providers, installs
those chain Python requirements and builds the node; use its `providers/environment.json`
and `chain` paths with the M5 verifier.

Final verification requires a clean committed disposable Fusion checkout. The
runner checks that historical runtime files are unchanged and the ports change is
additive. It preserves `verify_m4.py` and directly runs the existing M4 behavioral
suites, including real-node isolation/readback. `--development` allows a dirty
checkout but cannot pass final scope/reproduction gates.

For one reproducible authenticated lookup demonstration, select the native gate:

```bash
uv run --python 3.11 --locked python scripts/verify_m5.py \
  --environment artifacts/m5/providers/environment.json \
  --gates hive --output artifacts/m5/lookup-demo
```

This creates fresh generated records via real DeTTa in a writer subprocess which
exits, then starts actual authenticated native Hive dispatch. Its private request
contains query attributes and a source barrier only. It discovers five matches,
15 accepted relations and eight payloads, then checks no-match, lag, a sixth match,
rebuild, restart and independent Search substitution. Generated IDs and insertion
order differ on repetition. Detailed answers are checked through the authorized
private consumer boundary. `traces/lookup-trace-*.json` contains only sanitized
counts and observed outcomes; private stores/configurations stay under ignored
artifacts. Do not publish those private test directories.

Select `--gates fixtures`, `--gates storage`, `--gates hive`, or `--gates legacy`
independently, or comma-join selections. Omitted gates stay NOT_RUN. Preflight
failures for native binaries, pinned sources or network isolation stay BLOCKED. A
missing dependency first exposed by test collection is recorded as an executed
prerequisite failure, with the effect tests unrun. A fixture never fills a real gate.
The capability ledger counts nine newly advertised operations (four Relations,
query, two source and two maintenance operations), plus four inherited AtomStorage
dependencies separately. Module representation does not mean complete Omega scope.

Only new journals support these profiles. To rebuild, call
`Search.beginRebuild(Mutation(scope, stable_key))`, then bounded `catchUp(scope,
limit)` until the captured target is processed. Queries are unavailable during a
partial rebuild. Old cursors and pending old-generation caller progress are not
migrated; use a new command after rebuilding. Replaying a completed caller command
returns its recorded historical result after current authorization checks.

## Controlled native append/read reproduction (S03.2)

Use the [S03.2 source/build/test recipe](../omega-adoption/mettaclaw-neoclaw/s03_2.md#reproduction-and-measurement-limits)
for a new approved synthetic corpus and fresh `/5` journals. It reuses the pinned
S01 native runtime, DeTTa adapter, S03 E5/Chroma provider SDK and S03.1 E5-free caller
recipe. The supported native entrypoint remains
`python -m integration.neoclaw.native_loop APPLICATION.json`; trusted composition
selects encoder and retrieval placement independently before the session starts.

Run the original oracle, then local, authenticated loopback HTTPS and mixed-placement
comparisons. A successful native `remember` must be followed by `query` in the same
session without an operator configuration change. Do not inject the answer reference
or enroll the future memory outside the native command. Keep recorded model/channel
responses and clocks labelled as fixtures; E5, Chroma, DeTTa and HTTPS are real gates.

On interruption, reopen the same application journal and original configuration.
Retain occurrence IDs, deadlines, reservations and captured vectors. Observe owner
acceptance/publication before retrying effects. Stored-but-not-ready failures remain
partial outcomes; do not return `REMEMBER-SUCCESS`, renew a deadline or replace a
query's retained view to hide them. Do not use populated older journals or private
Omega stores for this reproduction.

## Controlled local source/revision reproduction (S04)

Use the existing pinned S03.2 native/E5/Chroma/DeTTa builds and fresh journals. The
[S04 report](../omega-adoption/mettaclaw-neoclaw/s04.md) records executed source
hashes and test runs; the [contract decisions](../omega-adoption/mettaclaw-neoclaw/s04-contract-decisions.md)
explain intentional legacy differences. From the repository root:

```bash
export S01_DETTA="$PWD/artifacts/m5/reproduction-01/providers/detta/target/debug/fusion-detta-adapter"
export PYTHONPATH="$PWD" PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1
mkdir -p artifacts/s04
artifacts/s03/venv/bin/python -m integration.neoclaw.evidence_corpus --out artifacts/s04/corpus.json
artifacts/s03/venv/bin/python -m integration.neoclaw.evidence_oracle --corpus artifacts/s04/corpus.json --evidence artifacts/s04/original.json
artifacts/s03/venv/bin/python -m integration.neoclaw.evidence_run --corpus artifacts/s04/corpus.json --evidence artifacts/s04/native.json
```

`evidence_composition.configure` selects `/6`, a fresh local cognitive policy/root,
explicit synthetic source ingress and authorized assumptions before startup. The
supported launcher remains `python -m integration.neoclaw.native_loop APPLICATION.json`.
Source capture runs at native `receive`; the original wrappers/parser/query and next
model context remain in that actual loop. Scripted model/channel, unused history and
comparison clocks are fixtures. No hosted model or public service is required.

Resume the same configuration/journals after interruption. Do not change source
aliases, reinterpret prior profiles, renew deadlines or refund native reservations.
A committed C2 decision may be observed after expiry; missing calculations or
presentation construction remain unavailable. Delete/rebuild only a derived local
presentation through authorized owner reads, never an authoritative owner journal.

## S05 fresh local promotion recipe

Continue the S04 pinned builds; revalidate `integration/neoclaw/sources.json`, `memory-requirements.lock`, `memory-model.json` and the existing runtime manifests. S05 uses `artifacts/s01/native-02/runtime.json`, `artifacts/s03/memory-runtime.json`, the E5-free caller manifest at `artifacts/s03_1/caller/caller-runtime.json`, and the existing real DeTTa binary. The build commands remain those in the S01/S03/S03.1 runbooks; there is no new math/runtime pin. Warm builds and model caches are permitted and must be labelled.

From the repository root, with `PYTHONPATH=$PWD`, `PYTHONDONTWRITEBYTECODE=1`, `HF_HUB_OFFLINE=1` and `S01_DETTA` pointing to the built `fusion-detta-adapter`:

```bash
artifacts/s03/venv/bin/python -m integration.neoclaw.promotion_corpus --out artifacts/s05/corpus.json
artifacts/s03/venv/bin/python -m integration.neoclaw.promotion_oracle --corpus artifacts/s05/corpus.json --out artifacts/s05/original.json
artifacts/s03/venv/bin/python -m integration.neoclaw.promotion_run --corpus artifacts/s05/corpus.json --out artifacts/s05/primary.json --provider sqlite
artifacts/s03/venv/bin/python -m integration.neoclaw.promotion_run --corpus artifacts/s05/corpus.json --out artifacts/s05/alternate.json --provider file-fixture
```

Each command creates fresh synthetic state and stops only its own processes. The supported native launcher remains `python -m integration.neoclaw.native_loop APPLICATION.json`; the S05 composition helper selects `/7` and local Attention before startup. No operator edits are needed between commands. Original execution uses its real legacy helpers only as the oracle. Adapted startup forbids legacy promotion helpers and restores native global selection through the Attention/AtomStorage ports. Do not point this recipe at a user's existing memory or promotion journal.

Run `integration.neoclaw.test_promotion_owner`, `integration.neoclaw.test_promotion_loop` and `integration.neoclaw.test_promotion_edges.PromotionEdges` for the selected S05 gates. The explicit class selector avoids importing helper tests twice. Keep synthetic model/channel/clock boundaries and alternate fixture storage distinct from real native math, DeTTa, Chroma and E5. Historical HTTPS memory gates are separate; no remote private Attention/evidence placement is configured.

Also run `integration.neoclaw.test_promotion_recovery_edges.ContextRecovery` for owner outage and retained context budgets. Run `S05_REQUIRE_MINIMAL=1 uv run --python 3.11 --locked python -m unittest -v integration.neoclaw.test_promotion_guards` in the repository's E5-free core environment. Its reduced-source check copies only `src/memory.metta` and PeTTa's interpreter `src/`, reuses the exact pinned SWI libraries, and updates only the relocated runtime-manifest hash. It executes both Attention owners without NAL/PLN libraries and verifies policy/interpreter tamper refusal. Existing S01/S04 full-source validators remain unchanged. The [run specifications](../../evidence/s05/run-specs.json) list the executed commands, environment and source identities, including targeted final rechecks.

## S06 fresh isolated IRC recipe

Continue from `c9c6e7985c8214feeedc78686f475efb3ad40625`. Reuse the pinned S01
native runtime, real DeTTa, S03 SDK/E5/Chroma and S03.1 caller SDK described above.
The C1/C2/Attention owners remain local. All commands below use fresh temporary
journals and generated inputs; no private Omega tree or default live startup is
loaded. `bwrap`, OpenSSL (for generated HTTPS certificates), a C compiler, make,
and the existing Python environments are prerequisites.

Build the independently pinned real IRC server from its official generated
release distribution (autoconf is unnecessary):

```bash
curl --fail --location https://ngircd.barton.de/pub/ngircd/ngircd-28.tar.xz --output artifacts/s06/ngircd-28.tar.xz
sha256sum artifacts/s06/ngircd-28.tar.xz
# Required: b48ba320a931d445ae335c47f88a9406a20f5c71c623bee5f7755d0522d435ee
# Extract only after this digest matches, into a fresh artifacts/s06 directory.
tar -xf artifacts/s06/ngircd-28.tar.xz -C artifacts/s06
git clone --no-checkout https://github.com/ngircd/ngircd artifacts/s06/ngircd-src
git -C artifacts/s06/ngircd-src checkout --detach 6ae13bf89e934d167f6ead8bb9ee39f57a0935c0
```

From the repository root, select the absolute install prefix and build:

```bash
S06_PREFIX="$PWD/artifacts/s06/ngircd"
cd artifacts/s06/ngircd-28
./configure --prefix="$S06_PREFIX" --without-openssl --without-gnutls --without-pam --without-ident --without-tcp-wrappers --without-zlib --disable-ipv6
make -j2
make install
```

The exact source comparison, generated configure input and local binary hash are
in `evidence/s06/server-source.json` and `builds.json`. The recipe starts ngIRCd
with `-n -p`, no server links, `Listen=127.0.0.1`, an ephemeral port, DNS/Ident/PAM
disabled, eight connection slots and one configured channel. It inspects the
running server's socket descriptors and `/proc/net/tcp`, not just configuration.
The IRC leg is isolated TCP; only the separate module leg is TLS.

From the repository root, run the original native oracle and real bridge tests:

```bash
export S01_DETTA="$PWD/artifacts/m5/reproduction-01/providers/detta/target/debug/fusion-detta-adapter"
export PYTHONPATH="$PWD"
export PYTHONDONTWRITEBYTECODE=1
export S06_EVIDENCE="$PWD/artifacts/s06/reproduction"
uv run --python 3.11 --locked python -m integration.neoclaw.channel_oracle --out artifacts/s06/original-channel.json
uv run --python 3.11 --locked python -m unittest -v tests.test_channel integration.neoclaw.test_channel_recovery
HF_HUB_OFFLINE=1 artifacts/s03/venv/bin/python -m unittest -v integration.neoclaw.test_channel_loop
```

`ChannelRun` creates a real isolated server, independent socket peer and distinct
bridge/provider credentials. The tests select `local` and `network` using the
same application. The existing supported launcher remains
`python -m integration.neoclaw.native_loop APPLICATION.json`; the small bridge
entrypoint is `python -m integration.neoclaw.channel_actor bridge BRIDGE.json
--ready READY.json`. The composition helper supplies trusted configuration before
starting either actor. Model arguments cannot choose channel, server, credentials,
provider or arbitrary message references. No operator configuration changes are
made between messages.

Use only newly generated allowlisted inputs and replies. Missing runtime/source,
unsafe listeners or denied startup are blockers; incorrect native results fail;
a timed-out real recipient observation is a timeout, not success. Tests stop only
their generated process groups. Raw local cognitive audit artifacts stay under
ignored `artifacts/s06`; publish the reduced S06 channel traces and test outcomes.
Do not resume old journals under this profile or resend an `unknown` reservation.
