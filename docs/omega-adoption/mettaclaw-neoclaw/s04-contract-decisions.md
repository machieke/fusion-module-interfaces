# S04 selected contracts and ownership

This increment selects `controlled-native-loop/6` on fresh journals. It continues the completed S03.2 publication `ecf5f48dec699a333853396e12141dc3a23720ac`. Profiles `/1`–`/5` retain their identities. The historical mapping packet remains a historical assessment, not an integration claim.

## Native compatibility and intentional changes

The original `support` and `contradict` wrappers still dispatch through `tvUpdate`. A source-checked startup overlay replaces that shared body with one typed local assessment call. The original body does not also execute `link` or `set_stv`. Arbitrary MeTTa and general memory operations remain outside this selected application.

`neoclaw-nal-stv-capped-099/1` / `neoclaw-petta-swi-10.0.1-revision/1` execute the pinned MeTTaClaw `Truth_Revision` under SWI 10.0.1. They are distinct from every Fusion PLN profile. Strength admits finite binary64 values in [0,1], confidence in [0,1); decimal and binary conversion must both be admissible. Total weight must be positive. The native order and 0.99 confidence cap are preserved, including loss of uncapped mass. Strength 1 is legal. Confidence 1, nonfinite numbers, injected expressions, zero-total-weight inputs and malformed/multiple replies fail closed. Production Python does not implement the formula.

The supported native ingestion policy is exactly sign → `(1.0,0.5)` or `(0.0,0.5)`, named `neoclaw-sign-half-confidence/1`. These are agent assessments, not calibrated observations or proof of entailment. Source/claim/context/policy determine a contribution; command turn/position determines an application occurrence. A new command about an already contributed source does not increase confidence. Contrary interpretations remain recorded. The original timestamp fan-out and duplicate updates are intentionally replaced with explicit ambiguity refusal and contribution deduplication.

## Declared local ports

| Owner/dependency | Selected contract | Additional responsibility |
|---|---|---|
| Application | `controlled-native-loop/6`, `neoclaw-episodic-assessment/1` | Input and command identities, trusted alias resolution, frozen source/target binding, original deadline, call reservations, result capture, read-view selection |
| AtomStorage | Existing private `immutable-bytes/1` | Immutable source/assessment/claim/creation bytes through real DeTTa; no truth policy |
| C1 | `neoclaw-local-source-assessment/1`, version 4.0.0 | Existing episode journal plus owner-issued occurrence identity, authorized occurrence observation, explicit source-lineage policy and deadline-bound new appends |
| C2 | `neoclaw-nal-revision-private/1`, version 4.0.0 | Existing belief journal, typed compatibility prior, contribution/alternative ledger, immutable revisions, durable evaluation budget, read-only exact decision observation |
| Native math | `LocalRevision` | Pure guarded `Truth_Revision`, original pinned source, bounded subprocess; no journal or authority |
| Trusted relay | Existing `trusted-evidence-completion/1`, explicitly selecting NAL consumer | Durable exact request/decision, response validation, separate C1 acknowledgment, lost-response reconciliation |
| Presentation | Local immutable read view | Exact C1/C2 snapshot bindings and verified labels/STV, no truth authority or vector indexing |

The local extension protocols and validators are in `fusion/nal_memory_contracts.py`. No remote service or arbitrary-function protocol is introduced. AtomStorage/DeTTa still sees opaque bytes. C1 validates an assessment envelope but never calls numerical code. C2 and the relay consume declared ports; hostile wrappers reject private-owner access.

## Prior, source and independence

A newly completed `remember` remains a compatibility display default until C2 prior registration commits. The prior is tagged `prior`, has `(1.0,0.5)`, identifies the verified fresh memory creation, and carries `neoclaw-fresh-memory-compatibility-prior/1`. It has **zero empirical roots, zero evidence IDs, zero empirical coverage, and no episode or observation**. The trusted application verifies the memory payload through the existing owner port before creating its local creation attestation. Registration needs separate `registerPrior` authority and is at most once per claim/creation. It cannot import an arbitrary old Chroma STV.

The actual controlled native `receive` result is captured before the model receives an eligible source label. C1 issues the occurrence identity, checks its request-key binding before append and committed receipt replay, orders the event, validates its immutable payload, and issues roots only for an explicitly registered source. Display timestamps are aliases; captured UTC observation time and C1 sequence are separate. A copied source inherits its verified ancestry. Unknown ancestry stays unknown. Creating a command, hash, differently worded record or new credential does not authorize an independent contribution.

An assessment references an existing authorized source event and a grounded claim about one immutable memory item in a named context. Each command is separately recorded in C1; C2 deduplicates the underlying root/claim/assessment/policy contribution. C2 keeps contrary observations and alternatives. Even distinct source occurrences require an explicit named assumption bound to the exact support pair, with separate `assume` authority. The generated positive composition opts into that assumption; the model cannot select it. Overlap defeats aggregation even when an assumption is supplied. Aggregates and ancestor supports cannot be resubmitted as fresh observations.

## Separate commits and bounds

Source acceptance, C1 assessment plus outbox, C2 admission/prior/decision, relay decision capture, C1 completion acknowledgment, presentation selection, native result capture, and next-context consumption remain separate observations. No transaction spans owners. C1 acknowledgment validates the trusted model-independent completion; it does not inspect a NAL snapshot.

Application source/assessment attempt budgets are durable and bounded at 96; each attempt has bounded owner reads and a relay batch capped at 16. This is an attempt reservation, not a claim to count every local port call. Each C2 delivery has at most three reserved numerical evaluations across restart and CAS attempts. The work identity is the C1 delivery identity, and C2 verifies its deadline against the immutable assessment event. Reservations are never refunded. A crash before commit can repeat pure evaluation within that budget; after commit `observeDecision` recovers exact bytes without calculating. A temporary unavailable evaluator leaves delivery pending. A stale revision does not silently mutate the accepted request; a new bounded CAS attempt has an explicit identity and exact assumptions.

Current authority is checked before effects, after native evaluation at C2 commit, and during disclosure/replay. Expiry cannot create missing events, run missing calculations or construct a missing presentation. Exact committed decisions can be observed and delivery closure recovered after expiry. This is not an exactly-once computation or atomic multi-owner snapshot promise.

C1 caps remain 16 pending deliveries, 16 records/page and 256 events/episode. C2 retains the existing 32-observation/64-support bounds, with the prior occupying one support slot. Queue tests use multiple claims in one episode, bounded batches and real acknowledgment; no cap increase or queue deletion.

## Immutable query views and privacy

A new query selects the currently ready application view at acceptance. An accepted assessment freezes its source and target then selects its base presentation view once when its ordered application execution begins, so a second assessment in the same turn carries forward the first completed view. Accepted queries retain their prior Search generation, source head, metadata seal and C1/C2 references. A belief-only update uses the same Search snapshot and payload/vector feed head. The application materializes local read-only metadata from exact owner snapshots; it does not run legacy `set_stv`, encode memory again, enroll another vector or build Search again. An explicit authorized repair can reconstruct a deleted derived presentation from the same owner revisions without refreshing an old query.

C1, C2, native revision, source/claim/assumption/prior records and presentation bindings are local-only. This first composition also selects local memory/Embedding placements; the optional combined HTTPS-memory/private-evidence composition is not implemented. Historical HTTPS memory profiles remain separate regression gates. Source canaries do not become memory/embedding provider arguments. Native logs/model contexts in the controlled session are local and use synthetic data; no live-model or malicious-host privacy guarantee is claimed.

There is no migration, source-history reconstruction, remote private evidence, general Relations/link adoption, promotion adoption, inference, scheduler, full Omega startup, multi-host deployment or chain operation.
