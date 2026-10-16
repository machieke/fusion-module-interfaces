# Omega ↔ ASI module interfaces: M0 / M1 / M1.1

A backend-neutral contract package and bounded storage, mailbox and delegated
execution conformance slice. Peers are **protocol fixtures**, not Omega agents.
The storage integration calls the real DeTTa DA and FileStorage libraries from
the inspected `secured-contract-spaces` checkout. It does not run consensus.

```bash
uv run --python 3.11 python scripts/verify_m11.py
```

This builds the Rust adapter offline, runs the contract and integration suites,
and records four provider/transport demonstrations in `artifacts/m1_1/`.
`--fixture-only` runs independent file-provider checks without passing the real DA gate. Set `DETTA_REPO` to override the sibling
checkout. No source files in that checkout are modified. Runtime Python uses its
standard library; the test suite also uses pinned JSON Schema validation. Cargo
needs the dependencies already present in its cache.

Read [architecture](docs/module-interfaces/architecture.md),
[contracts](docs/module-interfaces/contracts.md),
[decisions](docs/module-interfaces/decisions.md), and
[M1.1 evidence](docs/module-interfaces/m1_1-evidence.md).
The [original M1 evidence](docs/module-interfaces/evidence.md) is historical.
OMEGA is blocked by absent intended runtime source; M1.1 does not rerun the
optional real chain gate. M2 is not implemented.

The [conference presentation](docs/presentation/README.md) provides the system
original M0/M1 overview, module responsibilities, dependency diagrams and
historical integration evidence as an editable PowerPoint and a PDF, with speaker notes.

The presentation predates M1.1’s separate owner stores and neutral `/2` receipts;
use the current architecture/contracts and M1.1 report for those changes.
