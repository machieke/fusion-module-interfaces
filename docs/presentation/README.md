# Omega × ASI — bounded inference and delivery closure

[Present the PDF](omega-asi-module-interfaces.pdf) ·
[Edit the PowerPoint](omega-asi-module-interfaces.pptx) ·
[Speaker notes](speaker-notes.md)

44 slides, 16:9. Slides 1–36 form a 45–50 minute talk; slides 37–44 are
discussion appendices. Three early **ELI16 executive-summary slides** explain
the notebook, evidence ledger, calculator, priority list and attempt budget,
then distinguish finishing work from settling its receipts. The complete map
of 15 modules, their responsibilities, state ownership and function dependencies
precedes implementation details.

All diagrams are vector graphics. The PowerPoint contains editable text, shapes
and connectors, with speaker notes on every slide. The PDF embeds its fonts.
For faithful PowerPoint editing, install the bundled [DejaVu fonts](fonts/),
distributed with their [license](fonts/LICENSE.txt).

| Slides | Story |
|---|---|
| 1–4 | Thesis and ELI16 summary: evidence, budgets and delivery receipts |
| 5–8 | All 15 modules, responsibilities, state ownership and implementation status |
| 9–10 | Exercised M3.1 private dependencies, including the relay, and preserved M1.2 path |
| 11–14 | Application-neutral DA, replacement, private placement and executable contracts |
| 15–20 | C1 history and five delivery commits; C2, inherited support and native math |
| 21–26 | Independent STI, historical comparison, durable budgets, feedback outcomes, recovery and authorization |
| 27–30 | Actual native Hive action and closure progress; selection effect and evidence classifications |
| 31–36 | Executed tests, every M3.1 gate, exact sources, limits and stop at M3.1 |
| 37–44 | Code, full source pins, profiles, old-store limits, M1.2 sequence, historical chain, commands and retry identities |

Current claims use the recorded **16 October 2026 M3.1 final run**, tested from
clean detached `1b17d74f2808703894ea55c9539adf264bc87976` and documented by the
evidence-only descendant `985d2f34ea8df8c5d93582e4ed6fe5cbe1843074`. This
presentation update starts from that clean evidence checkout. Gates, observed
outcomes and source pins come from committed JSON. The build manifest hashes
20 evidence inputs. QA also audits the M2, M3 and M3.1 archives, current tested
implementation hashes and historical M3 source hashes at their own revision.
This update changes presentation artifacts only; it does not rerun integrations
or expand their guarantees.

M3.1 makes C1 completion independent of PLN snapshots: the trusted relay validates
the selected C2 decision, then attests durable processing to C1. The actual
new-profile workflow uses that relay. **33 distinct observations** in one
persistent episode drain in batches **16, 16, 1**, reaching zero pending after
each drain. Reports and unregistered-origin observations also close processing
without a numerical truth value; contrary observations remain retained.
The 16-pending and 256-lifetime-event bounds remain unchanged.

Attention owns the outcome of each deadline-bound feedback intent: **applied**
with the original receipt, **retired without credit** when expired or obsolete,
or **pending**. Both the SQLite provider and independent atomic-file **fixture**
exercise the same closure semantics. C4 keeps separate, versioned closure
progress; original execution counters, reservations and deadline stay fixed.
Reconciliation performs **zero new native formula calls** and does not apply
fresh eligible feedback. Actual Hive dispatch exposes execution and closure
separately, including explicit zero-conclusion execution.

All **12 supported M3.1 gates passed**, with no blocked supported runtime
prerequisite. New coverage comprises nine fixture methods, five real-provider
methods, three direct recovery methods covering **16 SIGKILL cases**, and seven
native Hive cases, **four with kills**. Two non-numerical real-provider probes
are separate. Complete M1–M3 regression also passed. The 127-case aggregate
includes the nine new fixtures; repeated subsets are not additional unique tests.

The earlier four M3 controlled-comparison cases remain labelled historical
measurements: one native formula call, one unique admission and one feedback
credit per case, with no extra call after reopen. Timings are individual local
observations, not performance rankings. Real Hive, native PLN/PeTTa and local
DeTTa remain distinct from generated inputs, operator grants, guard-only tests,
injected faults and the independent attention fixture.

New explicit C1/C3/C4 profiles require **fresh journals**. M3.1 does not migrate
or repair pre-existing M3 pending work. Disposable populated old-store copies
reject new selection without modification and still replay under old profiles.
Eligible or unavailable feedback and finite exhausted capacities can remain
pending. The native math, application-neutral DA boundary, private placement,
live authorization and independent owner commits remain preserved. No new
cognition, scheduler, ECAN, LTI, general search, migration or chain work is added.

CHAIN is **NOT_RUN**. Slide 42 retains the historical M1 isolated-chain observation
`pending → included → finalized`, without attributing it to a Hive result.
Exact historical chain-source reproduction remains **BLOCKED** by unavailable
dirty source inputs. Empty-global-cache builds, historical SWI 10.0.1, power loss,
distributed failover, the full Hive suite and production-quality studies remain
**NOT_RUN**. None is substituted with a fixture pass.

Read the [M3.1 report](../module-interfaces/m3_1-evidence.md),
[M3 report](../module-interfaces/m3-evidence.md),
[M2 report](../module-interfaces/m2-evidence.md),
[M1.2 report](../module-interfaces/m1_2-evidence.md),
[M1.1 report](../module-interfaces/m1_1-evidence.md),
[historical M0/M1 report](../module-interfaces/evidence.md) and
[runbook](../module-interfaces/runbook.md) for the underlying evidence.

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
  --outdir artifacts/presentation-qa/office-m3_1 \
  docs/presentation/omega-asi-module-interfaces.pptx
uv run --python 3.11 --with-requirements docs/presentation/requirements.txt \
  python docs/presentation/check.py \
  artifacts/presentation-qa/office-m3_1/omega-asi-module-interfaces.pdf
```

The [QA record](qa.json) records independent LibreOffice rendering, slide text,
notes, fonts, evidence audit, visual review and ProofShot browser verification.
Microsoft PowerPoint itself is unavailable. Local visual proof artifacts are
ignored; generated presentation files and the QA record are committed. Rebuilding
or checking the presentation does not rerun or overwrite integration evidence.
