# Omega × ASI — fifteen module talks

[Download all decks (ZIP)](module-decks.zip) · [Read all talks (bookmarked PDF)](all-modules.pdf) · [Architecture overview](../README.md)

Fifteen standalone conference presentations, **12 slides each / 180 slides total**. Each is designed for a 12–15 minute talk to a mixed engineering and research audience. Every talk starts with an ELI16 explanation, then places the module in the helicopter view and shows function dependencies before implementation details.

Each deck covers responsibility and why it matters; scope and state ownership; executable operations; a concrete worked example; four invariants; recovery and refusal; measurements and benchmark gaps; current real/fixture/blocked/unrun state; potential future directions with prerequisites and acceptance criteria; and exact source/reproduction references.

| Module | Present | Edit | Notes |
|---|---|---|---|
| DA storage | [PDF](01-da-storage/slides.pdf) | [PowerPoint](01-da-storage/slides.pptx) | [Notes](01-da-storage/speaker-notes.md) |
| AtomStorage · C0 | [PDF](02-atom-storage/slides.pdf) | [PowerPoint](02-atom-storage/slides.pptx) | [Notes](02-atom-storage/speaker-notes.md) |
| Relations | [PDF](03-relations/slides.pdf) | [PowerPoint](03-relations/slides.pptx) | [Notes](03-relations/speaker-notes.md) |
| Search projection | [PDF](04-search/slides.pdf) | [PowerPoint](04-search/slides.pptx) | [Notes](04-search/speaker-notes.md) |
| EpisodicMemory · C1 | [PDF](05-episodic-memory/slides.pdf) | [PowerPoint](05-episodic-memory/slides.pptx) | [Notes](05-episodic-memory/speaker-notes.md) |
| BeliefRevision · C2 | [PDF](06-belief-revision/slides.pdf) | [PowerPoint](06-belief-revision/slides.pptx) | [Notes](06-belief-revision/speaker-notes.md) |
| PLNKernel | [PDF](07-pln-kernel/slides.pdf) | [PowerPoint](07-pln-kernel/slides.pptx) | [Notes](07-pln-kernel/speaker-notes.md) |
| Attention · C3 | [PDF](08-attention/slides.pdf) | [PowerPoint](08-attention/slides.pptx) | [Notes](08-attention/speaker-notes.md) |
| InferenceControl · C4 | [PDF](09-inference-control/slides.pdf) | [PowerPoint](09-inference-control/slides.pptx) | [Notes](09-inference-control/speaker-notes.md) |
| Agent messaging | [PDF](10-messaging/slides.pdf) | [PowerPoint](10-messaging/slides.pptx) | [Notes](10-messaging/speaker-notes.md) |
| Delegated execution | [PDF](11-execution/slides.pdf) | [PowerPoint](11-execution/slides.pptx) | [Notes](11-execution/speaker-notes.md) |
| Module registry | [PDF](12-registry/slides.pdf) | [PowerPoint](12-registry/slides.pptx) | [Notes](12-registry/speaker-notes.md) |
| Compatibility resolver | [PDF](13-resolver/slides.pdf) | [PowerPoint](13-resolver/slides.pptx) | [Notes](13-resolver/speaker-notes.md) |
| ConsensusFinality | [PDF](14-consensus-finality/slides.pdf) | [PowerPoint](14-consensus-finality/slides.pptx) | [Notes](14-consensus-finality/speaker-notes.md) |
| Authorization | [PDF](15-authorization/slides.pdf) | [PowerPoint](15-authorization/slides.pptx) | [Notes](15-authorization/speaker-notes.md) |

## Evidence and benchmark policy

The source snapshot is `494df69a1ac401c3d3b2cf79dbfde07f74b5e277`; the exact final tested M5 implementation is `bfb0ec8856c932dc2bcbc05b8949c957da8d72cd`, with recorded evidence at `3dc6c1146601a0d0aa8785e61884970ec84a57c6`. Earlier M2/M3/M3.1/M4 observations retain their own milestone labels. All required M5 gates passed, including existing M1–M4 regressions. This presentation work does **not rerun runtime integrations or execute new performance benchmarks**.

Most modules have conformance and recovery evidence but no isolated latency/throughput benchmark. Their benchmark slide says so. Numerical goldens, counts, contract limits and historical whole-workflow timings are never presented as latency percentiles, quality scores or production SLOs. Every deck proposes a concrete controlled benchmark; those experiments are **NOT RUN**. Future directions are conditional design options, not a committed roadmap or implemented capability.

Real native Hive/PLN/DeTTa/F1R3node results remain separate from generated corpora, operator policy, protocol counterparties, independent atomic-file fixtures and fault injections. Static Registry and pure Resolver are local implementations; their metadata does not prove provider claims. Required verification cannot be satisfied without a verifier. Historical dirty M1 chain-source reproduction remains blocked independently of the verified clean M4 baseline.

The 15-family denominator is the bounded reference inventory, not complete Omega product coverage. Supporting seams such as RevisionMath, the evidence relay, native plugins and bindings are explained inside their owning talks rather than counted as extra module families. Human maintainers remain unassigned.

## Editing and reproduction

PowerPoint text, vector shapes and connectors are editable. PDF fonts are embedded. Install the existing [DejaVu fonts](../fonts/) when editing; see their [license](../fonts/LICENSE.txt). Each PowerPoint includes speaker notes and the companion Markdown notes contain source links. The ZIP contains the 15 PDF/PowerPoint/notes sets, a bookmarked combined PDF, fonts/license and editorial source files. Speaker-note citations link to the immutable repository snapshot. Rebuild from this repository: the source uses the shared overview renderer primitives and bundled fonts.

```bash
uv run --python 3.11 --with-requirements docs/presentation/requirements.txt \
  python docs/presentation/modules/build_modules.py
```

For a single deck, add `--module 04-search` (or another directory ID). A full build refreshes the combined PDF, series manifest and ZIP. `catalogue.py` is the editorial source; `build_modules.py` contains slide layouts; `render.py` exports editable vectors and measured text. The original overview deck and renderer are preserved.

Export each PowerPoint through an independent renderer into `<office-root>/<module-id>/slides.pdf`, then audit:

```bash
uv run --python 3.11 --with-requirements docs/presentation/requirements.txt \
  python docs/presentation/modules/check_modules.py <office-root>
```

[qa.json](qa.json) records all-page text/notes/fonts/bounds checks, source/evidence audits and visual verification. Independent LibreOffice and Chromium are verified; Microsoft PowerPoint itself is unavailable. Generated PDF/PPTX/SVG/notes and manifests are versioned; private visual QA artifacts remain under ignored `artifacts/presentation-modules-qa/`. No private runtime data is copied into the decks.

The [series manifest](series-manifest.json) hashes all cited implementation/report inputs. The [runbook](../../module-interfaces/runbook.md) contains runtime prerequisites and source recipes. Presentation checks are separate from those integration commands.
