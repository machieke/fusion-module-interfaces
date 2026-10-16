# Omega ↔ ASI module interfaces: through M3

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

M3 adds independently persistent STI attention, an independent same-profile
atomic-file fixture, a pure guarded native deduction kernel, explicit derived
support admission and a bounded inference controller. The new native Hive action
exercises restart, replay, causal feedback and durable attempt budgets. See
[M3 evidence](docs/module-interfaces/m3-evidence.md) and the executable contracts.

For the complete M3 source/build/test path (Linux prerequisites and access are
listed in the runbook):

```bash
uv run --python 3.11 --locked python scripts/build_m3.py artifacts/m3-providers
uv run --python 3.11 --locked python scripts/verify_m3.py artifacts/m3-providers/environment.json
```

For the original M1 conformance slice:

```bash
uv run --python 3.11 --locked python scripts/verify_m11.py
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
separate and is not rerun in M1.2, M2 or M3. M3 implements only the specified
reference STI policy and bounded grounded inference. No LTI, general search,
research attention policy, live state migration or further inference expansion is included.

The [conference presentation](docs/presentation/README.md) covers the architecture
through M3, opening with an ELI16 executive summary before all 15 module
responsibilities and function dependencies. It includes private C1/C2 ownership,
inherited evidence, guarded native deduction, independently replaceable STI,
durable inference budgets and actual Hive recovery, with an editable PowerPoint,
PDF and speaker notes. The C1 acknowledgment compatibility limit remains explicit.
Real providers, fixtures, historical chain evidence, blocked inputs and unrun
gates remain separately labelled.
