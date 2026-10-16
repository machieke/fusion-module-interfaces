# Omega × ASI — independent attention and bounded native inference

[Present the PDF](omega-asi-module-interfaces.pdf) ·
[Edit the PowerPoint](omega-asi-module-interfaces.pptx) ·
[Speaker notes](speaker-notes.md)

40 slides, 16:9. Slides 1–32 form a 40–45 minute talk; slides 33–40 are
discussion appendices. Two early **ELI16 executive-summary slides** explain
memory, evidence and the calculator, then introduce a priority list and a limited
attempt budget. The complete map of 15 modules, their responsibilities, state
ownership and function dependencies precedes implementation details.

All diagrams are vector graphics. The PowerPoint contains editable text, shapes
and connectors, with speaker notes on every slide. The PDF embeds its fonts.
For faithful PowerPoint editing, install the bundled [DejaVu fonts](fonts/),
distributed with their [license](fonts/LICENSE.txt).

| Slides | Story |
|---|---|
| 1–3 | Thesis and ELI16 summary: remember evidence, choose priorities, preserve budgets |
| 4–7 | All 15 modules, responsibilities, state ownership and implementation status |
| 8–9 | Exercised M3 private dependencies and preserved M1.2 shared application path |
| 10–13 | Application-neutral DA, independent replacement, private placement and executable contracts |
| 14–18 | Preserved C1/C2 behavior, inherited evidence, actual native deduction and revision goldens |
| 19–23 | Independent STI, controlled provider swap, durable budgets, five crash boundaries and authorization |
| 24–27 | Actual native Hive action, selection effect, evidence classifications and executed tests |
| 28–32 | Every M3 gate, exact source/build evidence, limits and explicit stop at M3 |
| 33–40 | Code, full source pins, profiles, C1 acknowledgment seam, M1.2 sequence, historical chain, commands and retry identities |

Current claims use the recorded **16 October 2026 M3 final run**, tested from
clean detached `1af39794649d0ca95cd729c64868202368da1ec4` and documented by the
unchanged-code descendant `c4498ce3047f1283d3a4a3ae3d09b713e7dcf312`. This
presentation update starts from that clean evidence checkout. Gates, comparison
measurements and native source pins come from committed JSON. The build manifest
hashes 14 evidence inputs; the QA script also audits the archived M2/M3 evidence
and tested implementation hashes. This update changes documentation and
presentation artifacts only; it does not rerun integrations or expand guarantees.

C3 implements **`sti-additive-linear-decay/1`**, a bounded independent reference
policy. C4 coordinates an immutable workset with durable candidate, attempt,
generation and deadline limits. C2 alone admits derived support, using the pure
PLN kernel's unchanged guarded five-premise native deduction. Derived conclusions
inherit evidence roots and ancestry; they do not become fresh observations.
Relations/Search, ECAN, LTI, general search and live state migration remain outside
the implemented scope. M1/M2 profiles, independent commits and native paths remain
supported.

The four controlled cases compare SQLite attention with an independently
implemented atomic-file **fixture**. All record one native formula call, one
unique admission and one feedback credit; reopening owners adds no native call.
Changing initial preference selects the other task. Step timings are individual
local observations, not a production throughput or cognitive-quality ranking.
Real Hive, native PLN/PeTTa and local DeTTa remain distinct from generated inputs,
operator assumptions, guard-only RecordingRuntime tests and injected faults.

All **13 required M3 gates passed**; no supported M3 prerequisite remains blocked.
The deck covers **15 actual SIGKILL boundary cases** (10 direct + 5 native Hive),
including conservative budget exhaustion without a conclusion. Concurrent clock
changes can leave feedback pending. M3 v3 belief snapshots do not fit the M2 v2 C1
acknowledgment DTO: generated C1 intents remain available and pending, while direct
M3 admission/replay is durable and original M2 acknowledgment tests still pass.
The 51 original and 16 M2 fixture isolation runs overlap the 118-case matrix;
repeated subsets are not counted as additional unique tests.

CHAIN is **NOT_RUN**. Slide 38 retains the historical M1 isolated-chain observation
`pending → included → finalized`, without attributing it to a Hive result.
Exact historical chain-source reproduction remains **BLOCKED** by unavailable
dirty source inputs. Empty-global-cache builds, historical SWI 10.0.1, power-loss,
distributed failover, the full Hive suite and production-quality studies remain
**NOT_RUN**. None is substituted with a fixture pass.

Read the [M3 report](../module-interfaces/m3-evidence.md),
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
  --outdir artifacts/presentation-qa/office-m3 \
  docs/presentation/omega-asi-module-interfaces.pptx
uv run --python 3.11 --with-requirements docs/presentation/requirements.txt \
  python docs/presentation/check.py \
  artifacts/presentation-qa/office-m3/omega-asi-module-interfaces.pdf
```

The [QA record](qa.json) records independent LibreOffice rendering, slide text,
notes, fonts, evidence audit, visual review and ProofShot browser verification.
Microsoft PowerPoint itself is unavailable. Local visual proof artifacts are
ignored; generated presentation files and the QA record are committed. Rebuilding
or checking the presentation does not rerun or overwrite integration evidence.
