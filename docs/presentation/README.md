# Omega × ASI — private cognition and verified chain commitments

[Present the PDF](omega-asi-module-interfaces.pdf) ·
[Edit the PowerPoint](omega-asi-module-interfaces.pptx) ·
[Speaker notes](speaker-notes.md)

52 slides, 16:9. Slides 1–43 form a 50–55 minute talk; slides 44–52 are
technical discussion appendices. Four early **ELI16 executive-summary slides**
explain the notebook, evidence ledger, calculator, priority list, work budget,
delivery receipts and approved chain commitment. The helicopter view covers all
15 modules, responsibilities, state ownership and function dependencies before
implementation detail. Separate diagrams show private cognition, the preserved
native inspect workflow and the new approved-result commitment path.

All diagrams are vector graphics. The PowerPoint contains editable text, shapes
and connectors, with speaker notes on every slide. The PDF embeds its fonts.
For faithful PowerPoint editing, install the bundled [DejaVu fonts](fonts/),
distributed with their [license](fonts/LICENSE.txt).

| Slides | Story |
|---|---|
| 1–5 | Thesis and ELI16 summary: evidence, budgets, delivery and verified commitments |
| 6–9 | All 15 modules, responsibilities, state ownership and implementation status |
| 10–12 | Private cognition, preserved M1.2 dependencies and new M4 chain dependency map |
| 13–16 | Application-neutral DA, independent replacement, private placement and contracts |
| 17–22 | C1 history and delivery; C2, inherited support and unchanged native mathematics |
| 23–28 | Independent STI, historical comparison, durable budgets, feedback closure and recovery |
| 29–31 | Actual native Hive inference and closure progress; demonstrated selection effect |
| 32–36 | Same-artifact Hive/DA/chain trace, exact approval, post-state finality, four kills and isolation |
| 37–43 | Evidence classifications, executed tests, all ten M4 gates, exact sources, limits and takeaway |
| 44–52 | Code, full pins, cognitive profiles, old stores, original sequence, historical chain, reproduction, retry identities and M4 profile |

Current claims use the recorded **16 October 2026 M4 final run**, tested from
clean detached `55ed5402391ab6ed14f8ab20e1eea4c85d8be955` and recorded in the
evidence-only descendant `05b1c52cfa6ced6e263700753e82ad6038a3b0dd`. This
presentation update starts from that clean evidence checkout. The build manifest
hashes 47 evidence/report inputs. QA audits all four M2/M3/M3.1/M4 archives,
current tested runtime hashes, earlier observations against their historical
revisions, and the same-artifact readback. This update changes presentation and
its documentation only; it does not rerun integrations or expand their guarantees.

M4 connects one actual authenticated native `fusion-inspect` result through
real DeTTa and the existing execution/messaging interfaces to a narrow native
`fusion-commitment` sibling. Operator approval binds the exact accepted result,
actor, chain/genesis/profile, signer and fixed operation. The adapter commits the
logical plan before signing and the full signed request before sending. Retries
reuse the exact signed bytes, timestamp and deployment identity. Current authority
is checked on replay as well as new work. Existing backend-independent ports,
original inspect dispatch and private cognitive owners stay unchanged.

The real isolated F1R3node stores the fixed tuple of namespace, generated operation
ID and approved result digest. Success requires the **actual inclusion-block
post-state value plus matching successful deploy-effect finality**. A separate
read-only process verifies the same digest, deploy, block and post-state after a
same-genesis node restart, without opening a caller journal or signing key.
Only the explicitly shareable generated workflow is eligible; private episodes,
beliefs, provenance and their identifying hashes stay off-chain.

All **10 required M4 gates passed**, including **REAL_CHAIN_EFFECT**. There are
11 focused commitment fixtures and six actual native chain cases, including four
caller/adapter SIGKILL boundaries. Real node outage/restart and independent readback
also pass. The complete M1–M3.1 regression passed; its 138-case aggregate already
includes those 11 fixtures, and repeated subsets must not be summed into a unique
total. Both attention providers, strict causal/time semantics, durable budgets,
private placement and old-profile compatibility remain covered.

The same-artifact trace records a 53-byte generated input, a 143-byte accepted
result and a 673-byte signed request. First finalized-effect observation was
4.066 seconds, including proposal and authorized observation overhead, with
675 phlo execution cost. These are individual local observations with concurrent
regressions, **not performance, throughput or economic claims**.

The original cognitive story remains intact: C1 retains contrary observations,
C2 admits evidence and derived support, pure PLN reuses guarded native formulas,
C3 owns independent STI and causal feedback, and C4 owns durable work budgets.
M3.1 makes C1 processing completion independent of PLN snapshots and exposes
execution separately from later closure. The recorded 33-event drain and historical
four-case M3 comparison keep their own source labels. Reconciliation adds no new
formula calls, does not retime feedback, and never refunds a reservation or resets
a deadline. Eligible/unavailable feedback and finite capacity can still leave
closure pending.

Real Hive, native PLN/PeTTa, local DeTTa, SQLite owners and isolated F1R3node are
separate from generated inputs, operator grants, test keys/genesis, the fixture
reference-message counterparty, independent file attention and injected faults.
One native caller and one fixture counterparty are not two production agents.
One local validator establishes node-observed integration, not decentralized
safety, trustless attestation or correctness of off-chain reasoning.

The clean F1R3node source rebaseline is pinned at
`9ec1096e10774926ea8e72f0823482f0bf9213e1`. The old dirty workspace was untouched
and unused; exact historical M1 source reproduction remains **BLOCKED**. Slide 49
preserves that earlier chain observation without substituting it for M4 proof.
Nested legacy verifier `CHAIN=NOT_RUN` fields describe the older scope; the outer
M4 required real chain gate is **PASS**. Final M4 missing prerequisites, executed
failures and observation timeouts are separately recorded and all empty. Earlier
launcher/harness failures and the corrected mutable-approval regression remain
in the committed preparation evidence.

Explicit new profiles require **fresh journals**. No existing state is migrated.
Recovery covers same-host process termination with intact files. Builds used
fresh provider sources/objects and warm downloads; upstream Rust regression test
binaries may be cached between attempts. Public networks, multi-validator safety,
empty global caches, power loss, distributed failover, production security/economics,
historical SWI 10.0.1 and the full upstream Hive suite remain **NOT_RUN**.
No new cognition, scheduler, ECAN, LTI, general search or migration is added.

Read the [M4 report](../module-interfaces/m4-evidence.md),
[M4 manifest](../../evidence/m4/manifest.json),
[same-artifact trace](../../evidence/m4/final/same-artifact.json),
[independent readback](../../evidence/m4/final/readback.json),
[M3.1 report](../module-interfaces/m3_1-evidence.md),
[M3 report](../module-interfaces/m3-evidence.md),
[M2 report](../module-interfaces/m2-evidence.md),
[M1.2 report](../module-interfaces/m1_2-evidence.md),
[M1.1 report](../module-interfaces/m1_1-evidence.md),
[historical M0/M1 report](../module-interfaces/evidence.md) and
[runbook](../module-interfaces/runbook.md) for underlying evidence.

## Rebuild and verify

From the repository root:

```bash
uv run --python 3.11 --with-requirements docs/presentation/requirements.txt \
  python docs/presentation/build.py
```

Presentation dependencies are isolated from runtime/test dependency groups.
[build.py](build.py) is the editable source for content, diagrams, notes and layout.
It generates the PDF, PowerPoint, [SVG slides](slides-svg/), notes and
[build manifest](build-manifest.json). Bundled fonts avoid system-path dependencies.
The builder checks bounds/text overlap, reopens the PowerPoint and renders every
PDF page to contact sheets under ignored `artifacts/presentation-qa/`.

Export the PowerPoint independently with LibreOffice, then compare both renderers
and audit the source evidence:

```bash
libreoffice --headless --convert-to pdf \
  --outdir artifacts/presentation-qa/office-m4 \
  docs/presentation/omega-asi-module-interfaces.pptx
uv run --python 3.11 --with-requirements docs/presentation/requirements.txt \
  python docs/presentation/check.py \
  artifacts/presentation-qa/office-m4/omega-asi-module-interfaces.pdf
```

The [QA record](qa.json) records independent LibreOffice rendering, slide text,
notes, fonts, evidence audit, visual review and ProofShot browser verification.
Microsoft PowerPoint itself is unavailable. Local visual proof artifacts are
ignored; generated presentation files and the QA record are committed. Rebuilding
or checking the presentation does not rerun or overwrite integration evidence.
