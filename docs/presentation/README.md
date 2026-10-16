# Omega × ASI — module-interface presentation

[Present the PDF](omega-asi-module-interfaces.pdf) ·
[Edit the PowerPoint](omega-asi-module-interfaces.pptx) ·
[Speaker notes](speaker-notes.md)

33 slides, 16:9. Slides 1–26 form a 30–35 minute talk; slides 27–33 are
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
| 7–8 | Proposed cognitive dependencies and the exercised native call path |
| 9–12 | Separate owner commits, independent AtomStorage replacement, profiles and native identity |
| 13–17 | Verified Hive entrypoint, operation sequence, receipts and caller/worker crash recovery |
| 18–22 | Application-neutral DA, authorization refusals, component classification, tests and actual Hive trace |
| 23–26 | Reproducible source/build recipe, all ten gates, limits and explicit stop before M2 |
| 27–33 | Code map, future contracts, errors, exact sources, commands, historical chain evidence and limits |

Current evidence is the recorded **16 October 2026 M1.2 run**, tested at
`bb22ef5e28b089b80132b40bcf5a1bbfc38b065b` and documented by the unchanged-code
descendant `4ee5cbe8b84689a5d2432530083738b263142f90`. Test counts, gate statuses,
the native trace and source pins are read from committed evidence JSON. The four
substitution workflows were checked against their recorded receipts and counts.
Input hashes are recorded in the build manifest.

The deck distinguishes real Hive/PeTTa and real local DeTTa from protocol peers,
the counterparty, generated data, the independent file provider and development
policy fixtures. The 34 selected upstream native baseline tests retain their
fixture process driver; the 13 real-caller cases use the default Supervisor and
actual native dispatch. The 51 fixture tests are a subset of the 90-test matrix.

Nine required M1.2 gates passed. The optional same-result chain gate is **NOT_RUN**.
Slide 32 preserves the separate historical M1 chain observation, including
`pending → included → finalized`, without attributing it to the new Hive result.
Exact historical chain-source reproduction remains **BLOCKED** by unavailable
dirty source inputs; empty-cache builds and the full Hive suite are **NOT_RUN**.

The [M1.2 report](../module-interfaces/m1_2-evidence.md),
[M1.1 report](../module-interfaces/m1_1-evidence.md),
[historical M0/M1 report](../module-interfaces/evidence.md) and
[runbook](../module-interfaces/runbook.md) retain the detailed scope and limits.
This update changes presentation content and documentation only. It does not
rerun integration tests, change recorded evidence, implement M2, or imply new
performance or production guarantees.

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
check and visual review. Rebuilds do not rerun or overwrite integration
evidence.
