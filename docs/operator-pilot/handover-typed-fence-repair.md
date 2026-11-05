# Handover identity fence correction

The executed handover11 cut retired the original deployment, activated the replacement under generation 2, and preserved shared/private captures and the original spent unknown model reservation. Its first new native input failed before ModelInference acceptance: the historical-effect guard treated a retained memory UUID in an Attention request's `targets` list as an old executable identity. That input expired without a capture or resubmission. Both namespaces were stopped before the programme's conservative stop bound. [Sanitized execution evidence](../../evidence/operator-pilot/development/handover11.json) remains a partial result, not a completed handover gate.

The opt-in activation guard now validates the existing typed wire contracts before distinguishing data from executable identity. It changes neither those contracts nor numerical profiles. Current owner authentication, disclosure checks, descriptor selection, deadlines and durable budgets still run inside the original owners.

| Existing port | Data excluded from historical effect matching | Identity still fenced |
| --- | --- | --- |
| Attention wall-clock bind/adjust/scores/rank/observe | Validated memory target UUIDs | Outer request ID and original binding request ID |
| Query/memory Embedding | Validated text | Encoding occurrence |
| Append-only AtomStorage | Validated content and helper input | Session, occurrence and request ID |
| ModelInference | Selected prompt and its validated native transformation | Call, session and source IDs |
| Workspace write/append | Validated path and text | Raw mutation identity and its principal/scope-derived journal key |
| Session submit | Input text | Session and input occurrence |
| Native worker completion | Captured projection text | Session, input and tool occurrences |

Workspace's derived-key check also rejects an imported pending mutation whose receipt has not yet committed its raw identity. It uses the actual configured native principals, not a wire-supplied principal. Historical model, send, task and chain effects retain the conservative fence. New bounded recorded-model calls remain current-authorized for the permitted native inputs; handover restores no live-generation, external-send, task-publication or chain authority. Unknown routes retain the prior scan. Malformed shapes and profile/selection mismatch do not gain data exemptions. Retained AtomStorage references and source heads keep their original semantics.

The focused qualification executed 36 method invocations: 15 activation tests, 15 handover driver tests and 6 continuation tests. It included real SQLite/Workspace files under explicit fixture authority and clocks, malformed contracts, old IDs inside completion occurrences, valid JSON text containing old IDs, and a pending old Workspace effect with no receipt. These are contract/owner tests, not deployed native evidence. The full pilot lane separately executed 307 method invocations against unchanged source during the run.

Frozen repair identities:

- `integration/single_node/pilot_activation.py`: `57642f9f471111078deb47ed4cb5fd0089035fa57259776e93c5779cf62e3ddd`
- `tests/test_pilot_activation.py`: `16a5c23e9f05154568abd77e5278c7a3c40c1bdd295547948b47e228b5589235`
- Focused log: `artifacts/operator-pilot/activation-typed-data-repair-04.log`
- Source copies: `artifacts/operator-pilot/activation-typed-data-source/manifest.json`

Earlier failed runs and intermediate test failures remain preserved. The old handover input and deadlines are not renewed. A separately frozen, fresh synthetic full handover must qualify the repaired artifact before a positive native handover or post-cutover browser result is claimed. Additional live generations remain zero.
