# Omega × ASI — module-interface presentation

[Present the PDF](omega-asi-module-interfaces.pdf) ·
[Edit the PowerPoint](omega-asi-module-interfaces.pptx) ·
[Speaker notes](speaker-notes.md)

29 slides, 16:9. Slides 1–24 form a 25–30 minute talk; slides 25–29 are
discussion appendices. All diagrams are vector graphics. The PowerPoint uses
editable text, shapes and connectors, with notes embedded on every slide.
The PDF embeds its fonts. For faithful PowerPoint editing, install the bundled
[DejaVu fonts](fonts/), distributed with their [license](fonts/LICENSE.txt).

The opening gives the helicopter view, all 15 module responsibilities, and
function dependencies **before** the detailed contracts and implementation:

| Slides | Story |
|---|---|
| 1–3 | Architecture thesis and complete module map |
| 4–6 | Responsibilities, owned state and implementation status of every module |
| 7–8 | Function dependencies for cognition, data and runtime control |
| 9–12 | Ownership, independent architecture choices, compatibility and invocation semantics |
| 13–17 | Real M1 sequence, independent receipts, crash recovery, generic DA and authorization |
| 18–21 | Real providers versus fixtures, chain trace, executed tests and measured baseline |
| 22–24 | Design tradeoffs, open gates and explicit stop before M2 |
| 25–29 | Code navigation, future contract obligations, errors, provenance and reproduction |

Evidence is the recorded **16 October 2026** run at implementation baseline
`3f75db993d354d18dff2a3e36498eabe4a33afb3`. Metrics and the chain digest are read
directly from the committed evidence JSON. No new integration, cognitive
implementation, benchmark run or production guarantee is implied by the deck.
The full [M0/M1 report](../module-interfaces/evidence.md) and
[runbook](../module-interfaces/runbook.md) retain the detailed scope and limits.

The presentation review corrected one prose mismatch in the report: the final
chain JSON contains `pending → included → finalized`, including an intermediate
block observation with deploy effects still `Pending`. The recorded evidence was
not changed. Existing upstream modifications were not committed by this task.

## Rebuild

From the repository root:

```bash
uv run --python 3.11 --with-requirements docs/presentation/requirements.txt \
  python docs/presentation/build.py
```

The presentation dependencies are isolated from the application's runtime and
test dependency groups. [build.py](build.py) is the complete editable source:
content, diagrams, charts, notes and layout. It generates the PDF, PowerPoint,
[individual SVG slides](slides-svg/), speaker notes and
[build manifest](build-manifest.json). Font files are bundled so the build does
not depend on Linux system font paths.

The builder checks text bounds and text overlap, reopens the PowerPoint, renders
all PDF pages, and writes slide images/contact sheets under ignored
`artifacts/presentation-qa/`. The PDF and PowerPoint share the same measured
layout. See [QA record](qa.json) for the delivered files' independent renderer
check and visual review. Rebuilds do not rerun or overwrite M1 integration
evidence.
