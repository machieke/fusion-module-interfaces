# Omega ↔ ASI module interfaces: through M4

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

M3.1 adds model-independent C1 completion, repeated evidence draining and bounded,
owner-authoritative feedback reconciliation. Native Hive reports original execution
and later closure progress separately. New explicit profiles require fresh journals;
existing M3 pending stores are not migrated or repaired. All 12 supported gates pass,
with M1–M3 regressions preserved. See [M3.1 evidence](docs/module-interfaces/m3_1-evidence.md).

M4 connects an authenticated native generated inspect result, retrieved through
real DeTTa, to an approved commitment on a real isolated F1R3node. Exact inclusion
post-state readback and matching deploy-effect finality survive caller/adapter
kills and same-genesis node restart. All 10 required gates pass, including the full
M1–M3.1 regression. Private cognitive owners remain separate. See the
[M4 report](docs/module-interfaces/m4-evidence.md),
[gate manifest](evidence/m4/manifest.json) and
[fresh-checkout build/run recipe](docs/module-interfaces/runbook.md#m4-required-isolated-chain-reproduction).

For the complete M3.1 source/build/test path (Linux prerequisites and access are
listed in the runbook):

```bash
uv run --python 3.11 --locked python scripts/build_m3.py artifacts/m3_1/providers
uv run --python 3.11 --locked python scripts/verify_m3_1.py artifacts/m3_1/providers/environment.json
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
separate and is not rerun in M1.2, M2, M3 or M3.1. M3 implements only the specified
reference STI policy and bounded grounded inference. No LTI, general search,
research attention policy, live state migration or further inference expansion is included.

The [conference presentation](docs/presentation/README.md) covers the architecture
through M4, opening with four ELI16 executive-summary slides before all 15 module
responsibilities and function dependencies. It includes private C1/C2 ownership,
inherited evidence, guarded native deduction, independently replaceable STI,
durable inference budgets, evidence delivery, feedback closure and the actual
native Hive → DeTTa → approved result → isolated F1R3node workflow. The deck adds
exact approval, durable signed-intent replay, post-state finality, crash recovery
and independent readback, with an editable PowerPoint, PDF and speaker notes. New-profile and
existing-state compatibility limits remain explicit.
Real providers, fixtures, historical chain evidence, blocked inputs and unrun
gates remain separately labelled.
