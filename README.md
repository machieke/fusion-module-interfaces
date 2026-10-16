# Omega ↔ ASI module interfaces: M0 / M1

A backend-neutral contract package and bounded storage, mailbox and delegated
execution conformance slice. Peers are **protocol fixtures**, not Omega agents.
The storage integration calls the real DeTTa DA and FileStorage libraries from
the inspected `secured-contract-spaces` checkout. It does not run consensus.

```bash
uv run --python 3.11 python scripts/verify.py
```

This builds the Rust adapter offline, runs the contract and integration suites,
and records a demo in `artifacts/`. Set `DETTA_REPO` to override the sibling
checkout. No source files in that checkout are modified. Runtime Python uses its
standard library; the test suite also uses pinned JSON Schema validation. Cargo
needs the dependencies already present in its cache.

Read [architecture](docs/module-interfaces/architecture.md),
[contracts](docs/module-interfaces/contracts.md),
[decisions](docs/module-interfaces/decisions.md), and
[evidence](docs/module-interfaces/evidence.md). M2 is not implemented.
