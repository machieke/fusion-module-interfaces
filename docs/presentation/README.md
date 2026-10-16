# Omega × ASI — private memory and guarded belief revision

[Present the PDF](omega-asi-module-interfaces.pdf) ·
[Edit the PowerPoint](omega-asi-module-interfaces.pptx) ·
[Speaker notes](speaker-notes.md)

38 slides, 16:9. Slides 1–30 form a 35–40 minute talk; slides 31–38 are
discussion appendices. Two early **ELI16 executive-summary slides** explain the
notebook, evidence ledger and calculator, then show why copied reports do not
count as independent evidence. The complete module map, responsibilities and
function dependencies precede the detailed implementation.

All diagrams are vector graphics. The PowerPoint contains editable text, shapes
and connectors, with speaker notes on every slide. The PDF embeds its fonts.
For faithful PowerPoint editing, install the bundled [DejaVu fonts](fonts/),
distributed with their [license](fonts/LICENSE.txt).

| Slides | Story |
|---|---|
| 1–3 | Thesis and ELI16 executive summary: memory, disagreement and justified updates |
| 4–7 | All 15 modules, responsibilities, state ownership and implementation status |
| 8–9 | Exercised M2 private dependencies and preserved M1.2 shared application path |
| 10–13 | Application-neutral DA, independent substitution, private placement and contract decisions |
| 14–18 | Duplicate-safe episodes, admission versus revision, lineage guards, pinned native PLN and goldens |
| 19–23 | Four crash boundaries, live authorization, real Hive episode, recorded story and M1.2 preservation |
| 24–27 | Provider/fixture classification, executed suites and every M2 gate |
| 28–30 | Reproduction evidence, bounded guarantees and explicit stop at M2 |
| 31–38 | Code, exact sources, profiles/bounds, future contracts, M1.2 sequence, historical chain, commands and retries |

Current claims use the recorded **16 October 2026 M2 final run**, tested at clean
`d9e75773c34987d5791a9207190fcbf0a8c1fd7b` and documented by the unchanged-code
descendant `f0cee248294a1fce42913782390e6c084025c67e`. The presentation starts from
that clean evidence checkout. Counts, gates, demo decisions and source pins are
read from committed JSON. The build manifest hashes nine evidence inputs; QA
also checks the 54 archived M2 evidence files and 70 tested implementation hashes.

C1 EpisodicMemory and C2 BeliefRevision are now implemented private local modules.
The deck distinguishes the narrow guarded RevisionMath provider from the future
general PLN kernel. Relations/Search, ECAN and inference control remain specified
future work. The original M1.2 native path and independent owner commits remain
visible alongside the new private integration.

Real Hive/PeTTa, real local DeTTa and actual native PLN revision are distinguished
from generated observations/assumptions, the independent file provider,
RecordingRuntime guard fixtures, injected failures and the local test policy.
The CLI demo record is separately labelled; it is not presented as a Hive trace.
The 51 original fixtures and 16 M2 fixtures are subsets of the 106-case matrix,
so their separate isolation runs are not added to a unique-test total.

All 11 required M2 gates passed; no M2 prerequisite remains blocked. CHAIN is
**NOT_RUN**. Slide 36 retains the historical M1 isolated-chain observation,
`pending → included → finalized`, without attributing it to a new Hive result.
Exact historical chain-source reproduction remains **BLOCKED** by unavailable
dirty source inputs. Empty-cache builds, historical SWI 10.0.1, power-loss and
distributed failover, and the full Hive suite remain **NOT_RUN**.

Read the [M2 report](../module-interfaces/m2-evidence.md),
[M1.2 report](../module-interfaces/m1_2-evidence.md),
[M1.1 report](../module-interfaces/m1_1-evidence.md),
[historical M0/M1 report](../module-interfaces/evidence.md) and
[runbook](../module-interfaces/runbook.md) for the detailed evidence.
This presentation update changes documentation and presentation artifacts only.
It does not rerun integrations or expand the observed guarantees.

## Rebuild

From the repository root:

```bash
uv run --python 3.11 --with-requirements docs/presentation/requirements.txt \
  python docs/presentation/build.py
```

Presentation dependencies are isolated from the application's runtime and test
dependency groups. [build.py](build.py) is the complete editable source: content,
diagrams, notes and layout. It generates the PDF, PowerPoint,
[individual SVG slides](slides-svg/), notes and [build manifest](build-manifest.json).
Bundled fonts avoid dependence on Linux system font paths.

The builder checks bounds and text overlap, reopens the PowerPoint, renders every
PDF page and creates contact sheets under ignored `artifacts/presentation-qa/`.
PDF and PowerPoint share measured layout. The [QA record](qa.json) records the
independent LibreOffice render, text/notes checks, evidence audit, visual review
and ProofShot browser verification. Microsoft PowerPoint itself is unavailable.
Rebuilds do not rerun or overwrite integration evidence.
