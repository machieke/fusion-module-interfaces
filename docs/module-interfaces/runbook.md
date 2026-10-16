# Reproduce the bounded gates (M1.1)

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

The current DeTTa and F1R3 working trees contain modifications not distributed
here. Their HEAD hashes alone cannot reproduce these runs. Obtain the exact
authorized working source/patches or choose and validate a new immutable revision.
The clean-checkout reproduction gate remains **BLOCKED** until that is resolved;
a hash manifest supplies identity, not missing source. No sibling changes were
reset, staged or committed by this task.

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
