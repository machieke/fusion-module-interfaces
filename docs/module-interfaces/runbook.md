# Reproduce the bounded gates

From this repository, with Python 3.11 available through uv and the inspected
DeTTa checkout as a sibling:

```bash
uv run --python 3.11 python scripts/verify.py
```

This fingerprints dependencies, builds the external adapter with offline Cargo,
runs the same conformance suite under in-process and subprocess bindings, and
executes the two-peer demo with a separate worker and real DA files. Failures
remain failures; missing DeTTa is not silently replaced by a memory store. Set
`DETTA_REPO` for a different checkout, inspect its resulting fingerprints, and
revalidate before treating it as the same provider.

`artifacts/tests.log`, `verification.json`, `demo.json` and `discovery.json`
contain raw local evidence. Each demo uses a fresh mode-0700 directory. Its
`config.json` selects paths, capacities, credentials, scopes and reply routes;
credentials are generated fixtures and are not included in the checked-in report.
`fusion/composition.py` selects the storage implementation. `Peer` depends only on
the binding contract; changing `Harness(binding=...)` swaps invocation transport.

The SQLite file is service-owned. Worker and reconciliation commands are trusted
operator entry points, not public module operations:

```bash
uv run --python 3.11 python -m fusion.host work /absolute/path/to/config.json
uv run --python 3.11 python -m fusion.host flush /absolute/path/to/config.json
```

`--pause-at` requires the explicitly enabled test configuration. Tests wait for a
marker, then send actual SIGKILL. Those checkpoints distinguish acceptance before
response, DA result write before metadata/outbox commit, and completion commit
before mailbox dispatch. Process death does not exercise power loss or filesystem
corruption beyond the separate destructive fixture tests.

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
