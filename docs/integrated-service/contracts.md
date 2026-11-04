# Integrated selections and ownership

This release extends the existing owners. It does not add module families or
change the historical fifteen-family denominator or X01/X02 accounting.
Numerical kernels, accepted input domains and historical profiles retain their
existing identities. New behavior requires the explicit selections below.

| Selection | Responsible owner | Bound behavior |
|---|---|---|
| `session-bound-native-worker/1` | Native session/application owner | Reuses one actual interpreter within one session and incarnation. Finite input, idle, lifetime and incarnation limits. A failed resident worker does not silently become a cold retry. |
| `verified-native-preparation/1` | Source-checked native launcher | Reuses verified immutable overlays on a read-only mount. Runtime configuration and authority remain separately checked. |
| `bounded-authenticated-https-reuse/1` | Each service client | Bounded connections, requests and lifetimes, with current credentials and exact response validation. A lost mutation reply is not retried by the pool. |
| `immutable-administrative-captures/1` | Application history plus existing AtomStorage/EpisodicMemory owners | Captures immutable dependencies once and hydrates exact retained history. This changes representation, not occurrence count or evidence weight. |
| `omega-single-node-placement/1` | Trusted composition/operator | Compiles only supported service edges, profiles and owner volumes. It does not move accepted work or populate a replacement owner's journal. |
| `trusted-provider-lifecycle/1` | Existing Registry/session owner | Separates advertised capabilities, operator admission, bounded readiness observations, current authority and conformance evidence. Disable affects new selection; old bindings remain exact. |
| `bounded-native-nal-envelope/1` | Caller, DelegatedExecution and existing NAL provider | A data-only envelope for the one named original two-STV operation. No executable text, callback, import, path or additional reasoning rule. |
| `bounded-inspect-envelope/1` | Caller and existing inspection executor | One named inspection with validated immutable input, selected provider, correlation and original bounds. |
| `bounded-native-inspection-continuation/1` | Application owner | Eight fixed nodes, one in flight, at most 32 relay calls and one logical execution. Captured prerequisites determine progress; no interpreter heap or general workflow engine. |
| `bounded-approved-chain-continuation/1` | Application plus existing ConsensusFinality owner | Five fixed nodes, one submit reservation and at most 16 observations. Exact captured artifact approval is separate from native workflow acceptance. |
| `execution-commit-cursor/1` | Execution owner; application owns its consumption cursor | Three ordered owner commits, bounded pages and explicit gaps. Hints never replace authoritative result hydration or authorize execution. |
| `owner-sealed-payload-archive/1` | Existing AtomStorage/feed owner | Copy, verify and atomically publish bounded sealed segments. Refs and feed sequences stay unchanged; authorization still runs at the owner. No hot-copy deletion, quota refund or physical erasure. |
| `bounded-derived-search-repair/1` | Search owner | A named repair of an exact selected generation from authenticated authoritative feeds. Three attempts, a fixed 120-second window, bounded source/index records and no source repair. |
| `bounded-owner-headroom/1` | Each existing owner, observed by the operator | Read-only owner-local accounting. Missing counts remain unknown; a preflight is neither a reservation nor a cross-owner admission promise. |
| `bounded-owner-integrity/1` | Bounded backup/diagnostic inspector | Classifies corrupt or missing authoritative data separately from reconstructible projections. It cannot replay an effect to recreate history. |

Registry requirements are a conjunction, not a preference list. A permutation
of identical requirement predicates is compatible with an already admitted
record. The original stored bytes, actions and selection digests remain intact;
changed predicates, implementation pins or profiles still conflict.

AtomStorage's optional archive capabilities are negotiated explicitly. Old
clients keep their original selection and operations. Required features cannot
silently downgrade to an older provider. Version ranges are interpreted by the
existing resolver; exact profiles and selected descriptors are frozen at
admission. Wire compatibility is qualified separately from resolver tests.

Archive reads use the existing authenticated storage ports; neither Omega nor
Search mounts storage files. Search continues to consume AtomStorage and
AtomCommitSource. Coherent read selections are vectors of owner observations,
not a global transaction. Older captures retain their selected views; a new
input can select a newer compatible view. A repair of an older generation may
not replace a newer published head.

Inspection, task completion, caller capture, acknowledgment and notifications
remain independent commits. Cancellation can prevent an unstarted stage; it
cannot undo a stored atom, emitted message or signed deploy. A started unknown
effect stays fenced. Retained captures may be observed after their execution
deadline only under current authority, without renewing the deadline or
reserving another effect.

Restore uses the existing quiesced owner export and a fresh observation-only
namespace. New credentials authorize observation, not old execution. Archive,
capture, profile and dependency checks precede disclosure. The isolated chain
node's private state is excluded from application restore; saved application
intent, reservation and finality receipts remain observable with execution
disabled. This is not a populated-state migration or a writable disaster
recovery procedure.

## Native state retained between inputs

| State | Lifetime and reconstruction |
|---|---|
| Native `&prevmsg`, `&lastresults` | One session/interpreter. Committed application turns reconstruct results after restart; equal text is not occurrence identity. |
| `loop_bridge._app` | One frozen session, scope, catalogue and model binding. An incarnation cannot move to another session. |
| Current command/position and proposal | One accepted turn/occurrence. Caller/model journals preserve selected bytes and spent reservations. |
| Imported helper configuration | Frozen session runtime/composition. No provider payload or legacy retrieval fallback is cached as authority. |
| `lib_chromadb.COLLECTION` enrichment facade | Selected at native memory/context entry from the captured view. Vector retrieval and authoritative payload hydration remain distinct ports. |
| History, belief and priority views | Application-owned per-input selections. A new input may select newer heads; old views are not rewritten. |
| Working context and workspace revisions | Existing application/workspace owners. A process variable is never a receipt. |
| Credentials and permission | Current port policy at admission and disclosure, including replay and pooled connections. Readiness does not confer authority. |
| Prepared overlays | Derived immutable source/runtime/template inputs, revalidated on reuse. Their existence does not prove tool completion. |

The qualification checks both reuse and separation: five mixed native inputs
in one observed incarnation, then revocation without restarting it, and three
interleaved private/shared sessions whose actual next prompts contain only their
own notes. These are bounded observations, not proof against a malicious host.
