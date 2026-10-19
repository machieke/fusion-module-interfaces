# Remote-placement scorecard

**Historical mapping scorecard; current-state addendum:** the rankings and
“not implemented” statements below describe the original mapping snapshot, not
the S07 publication. Consult the [current native-boundary evidence matrix](s07-closeout.md#current-native-boundary--module--profile--placement-matrix)
for delivered scope and placements. S08 was the Embedding candidate; bounded X02
query and append encoding already shipped in S03.1/S03.2. No new Embedding work is
triggered by closing S07. The proposed next work is a [retrieval-grounded evaluation](s07-next-workload.md),
with no implementation or live-generation authorization in this review. Scores
and original candidate identities remain unchanged.

Scores are reasoned design assessments, **not benchmarks**. Scale: 0 = missing/unfavorable, 1 = weak, 2 = workable after bounded adaptation, 3 = favorable; higher is always better, maximum 36. Privacy and missing-interface gates override totals. Scores refer to the stated candidate scope, not a hypothetical completed platform.

| Key | Criterion |
|---|---|
| F | Interface fit |
| O | State-owner clarity |
| R | Replayability |
| P | Privacy suitability |
| B | Bandwidth suitability |
| L | Latency tolerance |
| C | Low local coupling |
| E | Low external-effect risk |
| V | Offload benefit |
| M | Existing provider maturity for this operation |
| G | Low migration difficulty |
| T | Testability |

| Seam | Prototype rank | F | O | R | P | B | L | C | E | V | M | G | T | Total | Placement |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S01 Named NAL truth deduction | 1 | 1 | 3 | 3 | 3 | 3 | 2 | 2 | 3 | 0 | 1 | 3 | 3 | 27/36 | good first remote prototype |
| S02 Bounded external web search | 2 | 1 | 3 | 1 | 2 | 3 | 2 | 2 | 2 | 1 | 1 | 3 | 3 | 24/36 | remote-safe after a named adapter/profile |
| S03 Core memory read composition | 3 | 1 | 1 | 1 | 0 | 2 | 1 | 0 | 2 | 3 | 1 | 0 | 2 | 14/36 | local by default, optionally remote |
| S04 Episode provenance plus belief revision | Deferred | 1 | 1 | 1 | 0 | 3 | 2 | 1 | 2 | 1 | 1 | 0 | 2 | 15/36 | must remain local initially |
| S05 Promotion ranking/adjustment | Deferred | 1 | 2 | 1 | 0 | 3 | 1 | 1 | 2 | 0 | 0 | 0 | 2 | 13/36 | must remain local initially |
| S06 Durable mailbox plus channel adapters | Deferred | 1 | 2 | 1 | 0 | 3 | 2 | 1 | 1 | 1 | 2 | 1 | 2 | 17/36 | remote-safe after a named adapter/profile |
| S07 Model completion | Deferred | 0 | 2 | 0 | 0 | 1 | 2 | 1 | 1 | 2 | 0 | 2 | 1 | 12/36 | local by default, optionally remote |
| S08 Embedding generation | Deferred | 0 | 3 | 1 | 0 | 1 | 2 | 1 | 2 | 3 | 0 | 0 | 2 | 15/36 | local by default, optionally remote |
| S09 Perception and image capture | Deferred | 0 | 1 | 0 | 0 | 0 | 1 | 0 | 1 | 3 | 0 | 1 | 1 | 8/36 | must remain local initially |
| S10 Arbitrary shell/MeTTa/filesystem | Deferred | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 1 | 0 | 0 | 1 | 4/36 | not remote-safe under current semantics |

The ranked comparison is S01 → S02 → S03. S03 is a valuable **later** core-memory slice, not an eligible remote deployment today. Other candidates remain deferred behind their stated contract/privacy prerequisites even when a raw score exceeds S03. S01 wins for architectural clarity and a strong native numerical oracle, not for performance gain. Its tiny computation may cost more over a network; no latency or throughput benchmark was run.

## S01 — Named NAL truth deduction

Pure named function has a clean numerical boundary, tiny payload and exact local oracle; generated shareable STVs need no migration. A new kernel/input/execution profile is required. Compute saving is negligible; value is proving composition and numerical ownership without a foreign-state dependency. [Exact contracts and recovery](seam-contracts.md#s01--bounded-nal-truth-deduction-recommended-first).

## S02 — Bounded external web search

Low local state coupling and easy call-path seam, but DDGS output is nondeterministic, exceptions currently look empty and upstream requests cannot be exactly-once. Useful execution precedent; weaker test oracle and fewer core module boundaries than S01. [Exact contracts and recovery](seam-contracts.md#s02--external-web-search).

## S03 — Core memory read composition

High architectural/offload value, but current payload/vector/links/truth are one Chroma owner, timestamps are ambiguous and there is no accepted source feed. Vector and promotion profiles, identity and privacy decisions block an honest drop-in cut. No populated-state migration. [Exact contracts and recovery](seam-contracts.md#s03--core-memory-read-composition).

## S04 — Episode provenance plus belief revision

Owner split and C1/C2 recovery patterns exist in Fusion, but legacy STVs lack evidence roots and NAL math differs. Existing private profiles explicitly require local placement. Authority/provenance gaps precede any remote experiment. [Exact contracts and recovery](seam-contracts.md#s04--episode-provenance-and-belief-revision).

## S05 — Promotion ranking/adjustment

SQLite is a recognizable owner, but wall-clock power decay, timestamps and replay ambiguity differ from STI. Compute benefit is near zero; preserve separate policy and defer populated-state transfer. [Exact contracts and recovery](seam-contracts.md#s05--promotion-ranking-and-adjustment).

## S06 — Durable mailbox plus channel adapters

Durable Fusion mailbox is mature for its profile; channel delivery and identity mapping are not. Lost ingress and ambiguous IRC egress cannot be repaired by moving the buffer. Requires explicit transport semantics and private route policy. [Exact contracts and recovery](seam-contracts.md#s06--durable-mailbox-with-legacy-channel-transport).

## S07 — Model completion

Already calls remote APIs, but no model port or pinned SDK/runtime semantics. Prompt privacy, billing/retry ambiguity and credential scope dominate. Moving another wrapper offers less value than clarifying the missing contract. [Exact contracts and recovery](seam-contracts.md#s07--model-completion).

## S08 — Embedding generation

Separate model owner and potential compute benefit; model/dimension/normalization compatibility absent and existing vectors cannot silently switch. Text and vectors remain private. New corpus only avoids migration. [Exact contracts and recovery](seam-contracts.md#s08--embeddings).

## S09 — Perception and image capture

Video bandwidth, reset state, media consent/identity, retention, continuous threads and hosted image completion are entangled. No perception port or replayable capture receipt; future offload value is real but not ready. [Exact contracts and recovery](seam-contracts.md#s09--media--perception).

## S10 — Arbitrary shell/MeTTa/filesystem

No declared bounded effect, sandbox, path scope or recoverable identity. A generic execution envelope would hide rather than solve these constraints. Scores do not authorize a service. [Exact contracts and recovery](seam-contracts.md#s10--arbitrary-shell-metta-and-filesystem-mutation).

## Placement policy

Keep the Omega loop, prompt assembly, user/private policy, credential/provider selection, current caller mapping and task/correlation state local initially. API keys belong to operator-controlled provider configuration, not caller arguments. Private memory, vectors, beliefs, provenance, images and identifying hashes stay local by default. Current Fusion private descriptors cannot be made remotely compatible by changing transport alone.

Remote cuts may use an authorized worker or service. None requires chain state; ConsensusFinality is out of scope. Mutable forgetting/updating and executable persistent spaces are excluded from candidate migration: no remote contract can currently preserve their effects honestly.

The machine-readable [scorecard](remote-scorecard.json) preserves every criterion, total and rationale. [Next slice](next-slice.md) defines prospective tests; no ranked candidate has been implemented.
