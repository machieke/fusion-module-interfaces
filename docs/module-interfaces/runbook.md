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
