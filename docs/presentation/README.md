# Omega × ASI — private discovery, cognition and verified commitments

[Present the PDF](omega-asi-module-interfaces.pdf) ·
[Edit the PowerPoint](omega-asi-module-interfaces.pptx) ·
[Speaker notes](speaker-notes.md)

64 slides, 16:9. Slides 1–54 form a 60–65 minute talk; slides 55–64 are
technical discussion appendices. Five early **ELI16 executive-summary slides**
explain the notebook, evidence ledger, calculator, priority list, work budget,
delivery receipts, approved commitment and searchable library catalogue.
The helicopter view covers all 15 module families, responsibilities, state
ownership and function dependencies before implementation detail. Separate maps
show private cognition, original inspect dispatch, approved chain commitment
and the new **query → relation traversal → payload retrieval** workflow.

All diagrams are vector graphics. PowerPoint text, shapes and connectors are
editable, with speaker notes on every slide. The PDF embeds its fonts.
For faithful PowerPoint editing, install the bundled [DejaVu fonts](fonts/),
distributed with their [license](fonts/LICENSE.txt).

| Slides | Story |
|---|---|
| 1–6 | Thesis and five ELI16 summaries, including the new catalogue analogy |
| 7–10 | All 15 module families, responsibilities, owners and bounded implementation status |
| 11–14 | Function dependencies: cognition, inspect, commitment and private lookup |
| 15–18 | Application-neutral DA, independent replacement, placement and contracts |
| 19–24 | C1 history/delivery, C2 admission, inherited support and guarded native mathematics |
| 25–33 | Independent STI, durable budgets, feedback closure, recovery and actual native inference |
| 34–38 | Preserved M4 same-artifact chain proof, exact approval, finality, recovery and isolation |
| 39–44 | M5 Relations, authoritative feed, exact Search, freshness, native lookup and recovery |
| 45–47 | Separate coverage denominators, provider classifications and executed tests |
| 48–51 | Preserved M4 gates and all 12 required M5 gates |
| 52–54 | Exact sources, limitations and takeaway |
| 55–64 | Code, pins, profiles, old stores, original sequence, historical chain, reproduction and retry identities |

Current claims use the recorded **16 October 2026 M5 final run**, tested at clean
`bfb0ec8856c932dc2bcbc05b8949c957da8d72cd` and recorded in the evidence-only
descendant `3dc6c1146601a0d0aa8785e61884970ec84a57c6`. This presentation update
starts from that evidence checkout. The build manifest hashes 82 evidence/report
inputs. QA audits the M2/M3/M3.1/M4/M5 archives, 132 current runtime/test/build
hashes and earlier observations against their historical revisions. The update
changes presentation and documentation only; it does not rerun integrations or
expand their guarantees.

M5 implements all four Relations operations (`assertRelation`, `getRelation`,
`outgoing`, `incoming`) and one explicit exact-attribute Search profile. An
AtomStorage-owned contiguous accepted commit feed supplies replayable indexing.
Search uses declared `head`, `readCommits` and `get` ports; no foreign owner
SQL or answer list supplies its index. Bounded `catchUp` and `beginRebuild`
maintenance own separate commands. Query exposes indexed prefix, page completion,
requested freshness and observed source head separately. Search and Relations
have independent snapshots and owner commits.

Actual authenticated native Hive `fusion-lookup` discovers **5 matching roots,
15 relations and 8 payloads**, across three Search pages. Setup exits before the
consumer starts; its request contains query attributes and a freshness barrier,
with no answer references. A later matching record produces an explicit lag
failure, then **6 roots and 9 payloads** after catch-up. Rebuild, restart and
same-profile independent Search substitution preserve discovery and canonical
payload bytes. The alternate atomic-file Search provider evaluates predicates
and persists state independently; it is explicitly a fixture. An opaque native
request label keeps private query text out of Hive parameter logs. Ordinary
receipts expose counts/status; detailed results and identifiers remain private.

All **12 required M5 gates pass**. Coverage has three distinct denominators:

- **15/15 bounded reference module families**, up from 13; this is not full Omega completeness.
- **9/9 new operations**, or **13/13 operations** including inherited AtomStorage dependencies in the M5 slice.
- **18/18 behavioral groups**: 12 brief scenarios and six crash-boundary groups. Line/branch coverage is **NOT_MEASURED**.

The final run executes 18 new fixture methods, four real-provider methods and
seven native Hive cases, including **13 deliberate M5 SIGKILL cases** (nine direct,
four native). Supplemental probes cover four populated attention/Search
configurations and four complete native payload comparisons. The unchanged
M1–M3.1 regression passes with a 156-case aggregate (old 138 plus new 18); repeated
subsets must not be summed. Eleven unchanged M4 fixtures and six real isolated
M4 chain cases also pass as legacy regression. M5 adds no chain operation.

The original cognitive story remains intact: C1 retains contrary observations;
C2 admits evidence and derived support; pure PLN reuses guarded native formulas;
C3 owns independent STI and causal feedback; C4 owns durable budgets. M3.1 keeps
execution separate from delivery/feedback closure. Historical 33-event draining
and M3 comparison timings retain their own source labels. Reconciliation adds
no native formula calls, retiming, reservation refunds or deadline resets;
finite capacity and eligible/unavailable feedback can leave closure pending.

The preserved M4 workflow connects one approved generated native inspect result
to real isolated F1R3node inclusion post-state and matching deploy-effect finality.
Signed-intent replay, four native kill boundaries and independent readback remain
visible. The original M4 measurement is explicitly historical: 53-byte input,
143-byte result, 673-byte signed request, 4.066-second first finalized-effect
observation and 675 phlo. It is one local observation, not a throughput or economic
claim. Private episodes, beliefs, provenance and identifying hashes stay off-chain.
One local validator demonstrates node-observed integration, not decentralized
safety or correctness of off-chain reasoning.

Real Hive/PeTTa, native PLN, DeTTa, SQLite owners and isolated F1R3node stay separate
from generated corpora/oracles, policy/grants, keys/genesis, fixture counterparties,
independent atomic-file providers and injected faults. Final M5 missing prerequisites,
executed failures and observation timeouts are separately empty. Corrected development
failures and an intermediate **PARTIAL** run remain archived; neither supplies a
final pass. An intentional negative verifier probe retains **BLOCKED/NOT_RUN**
classification with no fixture fallback. Historical dirty M1 chain-source reproduction
is still **BLOCKED**; the verified clean M4 rebaseline remains separate.

New lookup profiles require **fresh stores**. Limits include 512 atoms, 4096 bytes
per atom, 128 accepted relations, 256 indexed records and pages/batches of at most
eight. One-hop lookup and exact case/Unicode attributes are bounded; unavailable
source bytes block indexing. There is no migration, eviction, automatic repair,
embedding search, new cognition, scheduler or new chain work. Recovery covers
same-host process termination with intact files. Provider source/objects were
fresh with warm downloads; the pinned M4 node binary was explicitly reused with
fresh isolated state. Power loss, distributed failover, public networks, empty
global caches, full upstream Hive tests and production security remain unrun.
Human maintainers remain unassigned.

Read the [M5 report](../module-interfaces/m5-evidence.md),
[M5 manifest](../../evidence/m5/manifest.json),
[capability ledger](../module-interfaces/m5-capability-ledger.json),
[contracts](../module-interfaces/m5-contracts.md),
[native trace](../../evidence/m5/traces/lookup-trace-1.json),
[payload comparisons](../../evidence/m5/native-payload-comparison.json),
[M4 report](../module-interfaces/m4-evidence.md),
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

Export PowerPoint independently with LibreOffice, then compare both renderers
and audit the source evidence:

```bash
libreoffice --headless --convert-to pdf \
  --outdir artifacts/presentation-qa/office-m5 \
  docs/presentation/omega-asi-module-interfaces.pptx
uv run --python 3.11 --with-requirements docs/presentation/requirements.txt \
  python docs/presentation/check.py \
  artifacts/presentation-qa/office-m5/omega-asi-module-interfaces.pdf
```

The [QA record](qa.json) records independent LibreOffice rendering, slide text,
notes, fonts, evidence audit, visual review and ProofShot browser verification.
Microsoft PowerPoint itself is unavailable. Local visual proof artifacts are
ignored; generated presentation files and the QA record are committed. Rebuilding
or checking this deck does not rerun or overwrite integration evidence.
