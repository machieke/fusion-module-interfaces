# Phase 2 native-turn latency diagnosis

This is a source-inspection note, not a performance qualification or a claim of a
fixed defect. No runtime, cluster, native test, owner journal, or model runtime
was accessed for this investigation. No implementation was changed and no cache
was introduced. `ADDITIONAL_LIVE_GENERATIONS=0`.

Inspection time: `2026-11-02T17:19:09Z`. Checkout HEAD:
`c4fb744edbddd003d09db408bed44a59d2df3823`, with the programme's in-progress Phase 2
changes. The source inspected includes changes after the dev10 image; notably the
opt-in bridge timing instrumentation is intended for the subsequent image. These
working-tree hashes do not identify the dev10 image contents.

## Observations and their limits

The programme operator reported these measurements from the existing dev10
deployment. This diagnostic task did not independently repeat them:

| Observation | Reported value |
|---|---:|
| Successive native turn durations | 17, 24, 28, 30, 41, 47, 52, 52, 57 seconds |
| One AtomStorage get, with 223 scope atoms | 0.068 seconds |
| Application construction | 0.383 seconds |
| One full current `PreviewEvidence.validate_view`, including ten RPCs | 0.946 seconds |

These turns are not established here as identical workloads. Neither the sequence
of timings nor a single get establishes asymptotic behaviour or identifies the
dominant elapsed-time component. The code does, however, show significant repeated
validation that can grow with the number of belief observations and memories.

## Strongest source-level candidate: repeated belief validation

For a fresh promoted context under the cognitive preview composition, the normal
call path performs at least eight complete retained belief-view validations:

| Native/context step | Validation path | Traversals |
|---|---|---:|
| `context_captured` | `PriorityAdoption.view` | 1 |
| `context_ids` | `PreviewPriority.payload_view` → `view` | 1 |
| `loop_bridge.call('context_ids')` post-hook | `promotion_startup.select_context` → `view`, then `evidence.projection` | 2 |
| `context_payloads` | `view`, then `payload_view` → `view` | 2 |
| `context_capture` → `context_replay` | `view`, then `payload_view` → `view` | 2 |

See `fusion/neoclaw_priority.py` (`view`, `context_captured`, `context_ids`,
`context_payloads`, `context_capture`, `context_replay`),
`fusion/preview_native_cognition.py` (`PreviewPriority.payload_view`),
`integration/neoclaw/loop_bridge.py` (`call`) and
`integration/neoclaw/promotion_startup.py` (`select_context`).

Each `PreviewEvidence.validate_view` delegates to
`EvidenceAdoption.validate_view` in `fusion/neoclaw_evidence.py`. That traversal
reauthorizes, reads each bound belief revision, hydrates its compatibility-prior
creation atom, and reads every retained assessment and every provenance source
through C1 and AtomStorage. C1 `EpisodeOwner._record` itself hydrates the immutable
event atom. Thus one logical provenance check can involve several nested network
operations. The eight traversals at the reported single-view timing would account
for about 7.6 seconds, **if** their costs are comparable. This is an illustrative
calculation, not a measured attribution of the 57-second turn.

Additional traversals occur outside this table: a new input's shared-memory view
preparation calls `PreviewEvidence.refresh` and `evidence.materialize`, command
paths validate retained views, and completion/restart replay reauthorizes completed
commands. `PreviewPriority.payload_view` also rehydrates every active memory on
each call. Unlike the historical implementation, this override does not use the
historical cached payload-view branch. These observations justify measuring call
counts before choosing any optimization; they do not justify weakening current
authorization, immutable payload validation, or retained-view semantics.

## Other costs and ruled-out explanations

* `FeedAtomOwner.row` in `fusion/atom_feed.py` fetches all `feed_atoms` rows for a
  scope and JSON-decodes rows until it finds the requested reference. Each `get`
  repeats this lookup; `getMany` calls `get` individually. This is a concrete
  scope-size-dependent cost. At the reported 223 atoms, the measured whole get
  was only 68 ms, so this alone is not evidence for a tens-of-seconds delay.
  `DettaStorage._call` starts the pinned backend executable for each get/put and
  uses the storage owner's exclusive lock. Its Python wrapper does not establish
  how much data the executable loads; no backend-wide replay is asserted here.
* C1 administrative history has substantial constant fan-out. `readHistory`
  performs three atom reads per returned event (event, wrapper, underlying
  payload), and `NativeHistory.read` subsequently hydrates the application body,
  including all chunks for a chunked body. `context` selects only the last four
  committed events. It is **not** a complete chronological replay on every turn.
  Oversized body omission occurs after hydration, so it saves prompt size rather
  than those reads. Appending history also validates wrappers/payloads through
  several owner reads and two append guards.
* `Application.restore` replays only occurrences from the last completed turn.
  `finish` verifies the current turn's completed commands. Neither method loops
  over every previous turn. The providers reached by those checks may still
  perform growing validation, as described above.
* `ChromaVector.ready` calls `_verified`, which opens the retained collection and
  reads all embeddings and metadata to verify its manifest. This is proportional
  to indexed memories, not C1 history length. A real rebuild starts the immutable
  feed from sequence zero with eight-record pages; `ActiveChroma` skips hydration
  for non-enrollment records but still enumerates those pages. Shared-memory
  preparation selects a lifecycle-bound source head, so an administrative history
  append alone does not mandate a new Search generation.
* Caller metadata `collection` opens the immutable metadata collection and checks
  all documents, embeddings, and metadata. `memory_bootstrap.initialize` checks
  its initial metadata collection, and the caller runtime validator hashes its
  pinned SDK files at native-process startup. `NativeSupervisor` launches a fresh
  native process per wake after the previous child stops. These are startup and
  collection-size costs; the inspected code does not show them enumerating all
  previous application views on every startup. They should be measured separately
  from Application construction, which does not encompass the whole native
  bootstrap.

## Safe measurement plan

The next image's opt-in `loop_bridge._timing` records method, process ID, finish
time, elapsed milliseconds, and sanitized error code. It records no arguments or
results, has a 1 MiB file bound, and ignores diagnostic-write failures. It does not
perform work, change identities, reset deadlines, or reserve calls.

Use its existing timings to separate `more` (input preparation), `restore`,
`preview_history`, `context_captured`, `context_ids` (including its metadata
post-hook), `context_payloads`, `context_capture`, command execution, and `finish`.
Compare complete process-launch-to-first-bridge time separately to capture native
bootstrap and SDK validation. Account for nested measurements rather than summing
them twice.

If further observation is necessary, instrument counts and monotonic durations
inside the owner boundaries: full `validate_view` traversals and their nested RPCs;
AtomStorage row lookup versus backend get; C1 returned-event and body-chunk counts;
Search `ready` versus `_project`; and metadata `collection` initialization. Record
aggregate counts/bytes only, with no payload text, credentials, or identifying
references. Existing source/image evidence must identify the instrumented build.
Do not resubmit work, renew deadlines, disable authorization checks, bypass owner
hydration, or regenerate captured results to obtain a timing.

The dominant bottleneck remains **unconfirmed pending the instrumented existing
workflow**. A cache or other optimization would need its own authorization,
availability, retained-view, and recovery argument; none is implemented by this
note.

## Inspected working-tree source hashes

| File | SHA-256 |
|---|---|
| `fusion/atom_feed.py` | `f3f3100e64231c23dd4fed0c42baf2727facc0849c7f0a2a1280bb15fe656617` |
| `fusion/adapters/detta.py` | `c7f9577ce22636d6f75745007dbb095a693c49f4ea5f5e34312a4ba9711148b0` |
| `fusion/adapters/chroma_vector.py` | `fbfc5546389fcaf34ceffaca74e6474f42e0c957943bbbfd2f116417858113fb` |
| `fusion/preview_native_cognition.py` | `fdeae637c7ad774a1676efc6107d4f217eaa8a3bca953d993b9fc2b5f093006b` |
| `fusion/neoclaw_priority.py` | `a2e6b9dc5024a5f56a96424a3c722b4542e10ce3d4fd981673d00e86b37ff3a6` |
| `fusion/neoclaw_evidence.py` | `747ef9c9160c194cc3cfd92654d23640cc015526a8d4faed368f317e008c8cb3` |
| `fusion/preview_native_memory.py` | `59f73c5195873bc917e41fff3321f350142c29f332bab766f7954eb37656c0bb` |
| `integration/neoclaw/promotion_startup.py` | `bd297860e4a12b206063fba215da729e0a8ef9610cf0307be7530f94c22cfa1f` |
| `integration/neoclaw/loop_bridge.py` | `421cb16797a1b484e9c5a73f087451e93b2189c175416ef41f586c3843a663e7` |

Executed checks: source reads, exact checkout identification, and the hash reads
above. No tests or benchmark executions were performed for this note.
