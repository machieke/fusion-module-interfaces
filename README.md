# Omega ↔ ASI module interfaces: through M2

A backend-neutral contract package and bounded storage, mailbox and delegated
execution conformance slice. M1/M1.1 peers are **protocol fixtures**. M1.2 adds a
pinned native Hive Programs caller through the existing validated interfaces;
its counterparty remains a fixture. See the [M1.2 report](docs/module-interfaces/m1_2-evidence.md)
and [source/build recipe](docs/module-interfaces/runbook.md).
The storage integration calls the real DeTTa DA and FileStorage libraries from
the inspected `secured-contract-spaces` checkout. It does not run consensus. M2 adds private C1 episodic memory and C2 belief
revision, reusing the pinned guarded PLN implementation through actual native
PeTTa. See [M2 evidence](docs/module-interfaces/m2-evidence.md), including the
separate fixture, real DeTTa, real PLN, real Hive and unrun gates.

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
The M1.1 blocked runtime observation remains historical; M1.2 uses the revision
identified by the supplied `omegahive-schematics`. The optional chain gate is
separate and is not rerun in M1.2 or M2. No ECAN, inference control or live state
migration is implemented.

The [conference presentation](docs/presentation/README.md) covers the architecture
through M1.2: all 15 module responsibilities, function dependencies, separate
owner commits, independent AtomStorage replacement, and real Hive caller recovery.
It includes an editable PowerPoint, a PDF and speaker notes. Current real-provider
and fixture results are distinguished from the historical M1 chain appendix and
unrun gates. That presentation remains a historical M1.2 artifact; the current
M2 architecture and evidence are in the documents linked above.
