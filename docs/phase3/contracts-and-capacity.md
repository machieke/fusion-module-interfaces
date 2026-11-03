# Phase 3 contracts and finite capacity

This is a fresh-state operational composition over the existing owners. It does
not migrate Phase 2 journals or revise the historical numerical profiles.
`omega-native-sessions/3` selects `bounded-native-session-allocation/1` and
`causal-session-fence/1`; `immutable-commit-feed/2` selects the new finite opaque
source capacity. The old exact-template session and 512-record source profiles
remain selectable and unchanged. A populated incompatible seal refuses startup.

A stable allocation request returns the same session, frozen template, lifetime
and provider binding. Current credentials and grants are rechecked. Closing or
archiving consumes retained capacity; it neither deletes history nor refunds
work. Template fingerprints exclude replaceable credentials, but bind selected
endpoints, CA, scopes, descriptors, policy and model semantics. An accepted
occurrence cannot silently move to a different template after a rollout.

An undispatched expired input commits `expired-before-start / NO_DISPATCH`.
A dispatched input commits uncertainty (`needs-reconciliation` or
`cancel-requested / UNKNOWN_AFTER_DISPATCH`). Later dependent input is fenced.
Read-only owner observation and another permitted session remain available.
Reconciliation observes saved application projections and commits only the
original completion; it never launches native work or completes missing effects.
Original command identities, result bytes, deadlines and spent budgets remain.

## Configured default envelope

| Owner or resource | Finite bound | Accounting/retention |
|---|---|---|
| Each application | 2 active, 8 retained sessions; 8 pending inputs; 8 MiB logical inbox budget | Retained sessions do not reclaim credits; pending completion reserves 66,560 bytes |
| Each session | 24 input acceptances, 4 pending, 120,000 ms original input window, 1 day lifetime | Current scope/policy plus original occurrence limits apply; generated values can choose stricter approved bounds |
| Allocation protocol | At most 4 templates, 16 retained, 32 global pending, 512 control actions | No hidden garbage collection or unbounded scheduler |
| Each selected immutable source scope | 2,048 reserved records, 32 MiB charged bytes | Every record charges actual payload plus 8,192 metadata bytes, including incomplete reservations |
| Immutable payload / feed page | Historical 4,096 bytes / bounded page contract | No larger individual atom or widened opaque DA meaning |
| Native active memory preparation | At most 16 active members | Final qualification uses at most 8; references and history survive withdrawal |
| Lifecycle | 256 events per selected lifecycle journal | Supersession/withdrawal retain immutable payloads; no evidence or priority transfer |
| C1 | 256 events per episode, page 16, pending 16, provenance 8 | Administrative history and empirical source roles stay distinct |
| C2 | Existing bounded native NAL revision profile, 3 numerical evaluations and 96 app attempts | No replacement mathematics, no fresh evidence from forwarding |
| Wall-clock Attention | 128 targets, 256 bindings/revisions, 8 contexts, 3 evaluations | Value/time/receipt remain atomic; priority does not change truth |
| Recorded ModelInference | Existing 128-owner-call bound, finite per-session input mapping | Recorded reservations/captures are real owner lifecycle; no live allowance |
| Working context / workspace | 8 notes / 4 KiB; 16 files / 16 KiB each / 128 commands | Existing owner receipts and append ambiguity survive restart |
| Task | 1 delegated query, 24 relay calls, no recursion | Recipient acceptance and mailbox acknowledgment are independent |
| Private projection | 16 accepted requests, 8 charged calls each, original 30-second effect window | Exact operator-approved content; observe committed publication after reply loss |
| Stage traces | 4 MiB per process sink, fixed method labels | Truncation/missing observations fail telemetry gates; nested totals are not additive |
| Fenced backup | 512 MiB per owner; up to 150,000 files for Phase 3 (old profiles retain 20,000) | Authority excluded, every included file hashed, all original writers stopped |

These are independent owner limits, not a cross-owner admission transaction or
unlimited service guarantee. A downstream refusal can leave accepted partial
work; that partial state and its charge remain visible. Logical charged bytes
are not physical disk usage or filesystem quota enforcement.

## Measured amplification and design basis

The actual unchanged Phase 2 dev19 baseline performed six native commands on a
fresh deployed shared source. Accepted records progressed 0 → 21 → 38 → 57 → 78
→ 95 → 112. Payload bytes reached 68,026 and serialized feed metadata 81,841.
The commands were remember, query, episodes, support, query and the second
agent's query. History wrappers, C1 events, captures, chunks and vectors account
for the difference between user memories and source records. The report is
[evidence/phase3/deployed-baseline.json](../../evidence/phase3/deployed-baseline.json).

The new source reserves before invoking DeTTa, then independently publishes the
feed. Recovery cannot release a reservation merely because publication is not
yet observed. Reference lookup uses a local index on immutable reference IDs;
content verification and current authorization still occur on each read. The
existing DeTTa opaque-coordinate partitions, numerical binaries and immutable
retention policy are preserved. A missing partition is an error.

The sustained workload freezes 72 maximum operator inputs, two agents, three
sequential shared sessions per agent, at most eight active user memories and
36 initial native inputs for the threshold crossing. The deployed run must
establish crossing and at least four more native operations without resetting
its logical source. Unit-test feed generation is explicitly insufficient.
