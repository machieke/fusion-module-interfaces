# Fresh preview DeTTa physical layout

The dev15 integrated run reached both native handoffs, evidence/revision,
priority, inspection, unlink and workspace readback. Its next `remember` failed
with `DEADLINE_EXCEEDED` during presentation readiness. The failure and original
input/tool deadlines remain retained. Storage/lifecycle acceptance did not become
native success. No deadline or record cap was increased.

The pinned DeTTa FileStorage implementation validates growing application,
profile, namespace and retention indexes on each put. Each small administrative
history event contributes three immutable atoms. This amplifies backend write
cost as a shared synthetic session grows. The source is
`secured-contract-spaces@272888f264dd2dde18b574cabb53c266b0dac2ec`,
`crates/detta-storage/src/lib.rs`, SHA-256
`a375679bd3b806d8af4033b5b432fc28e502f85ac475eb74fc8b0266faa9f940`.
The unchanged adapter binary SHA-256 is
`cb7ed1a27e10e2869ca7357c6c249861623b9849c49fcbf7ef300aa19831f756`.

Fresh preview storage now selects `detta-opaque-coordinate-partitions/1` as a
physical layout inside the same service/PVC. A partition derives only from the
scope hash and the already principal-scoped opaque coordinate. The unchanged
native binary commits/reconstructs its actual six DA shares with threshold four.
There is no payload cache, new logical module, semantic DA interpretation,
second writer or replacement mathematics. The application-neutral opaque DA
profile and module descriptors remain unchanged. Receipt evidence explicitly
names the layout while retaining the actual `detta-local-rs/1` provider identity.

All cognitive, append and hydration/feed entry paths choose the same factory.
A single outer lock covers all partitions; each native backend also retains its
existing lock. The authoritative feed, idempotency identity, sequence, 512-record
cap and authorization remain with the existing owner. Search receives its data
through authenticated ports. Partition directories are never shared with it.

A layout seal refuses populated unsealed roots. Each partition binds the
original content hash before calling the native writer, then captures its
manifest independently. After interruption, changed bytes under that coordinate
are refused; the same bytes recover the same native manifest. Closed internal
locators contain fixed lowercase hashes, never caller-selected paths. Reads
check scope, record/manifest seals and native reconstruction. Missing data is an
error, not an empty replacement partition.

The new preview storage owner's startup seal includes the physical layout.
An older server's three-field seal comparison therefore refuses this populated
PVC before owner configuration or worker startup. New code also refuses an old
populated preview storage seal; no migration or automatic rollback is supported.
Historical compositions continue selecting their original layout. Fenced backup
retains the new seals and checkpoints `.sqlite3` as well as `.sqlite`/`.db` WALs.

## Executed development observation

[Real DeTTa report](../../evidence/phase2/development/storage-layout-real-01.json)
and [source bindings](../../evidence/phase2/development/storage-layout-source-01.json)
record two fresh 48-record roots, generated opaque bytes, verified hydration,
availability and reopen readback. A real SIGKILL after native put and before the
adapter's locator-manifest capture recovered the same intent and refused a
changed one. This is an adapter/backend test, not native Omega or cluster evidence.

| Layout | First 8 puts mean | Last 8 puts mean | Median of 48 |
| --- | ---: | ---: | ---: |
| Historical shared root | 153.0 ms | 484.1 ms | 313.8 ms |
| Coordinate partitions | 105.2 ms | 114.1 ms | 111.7 ms |

Measurements include writes only; all records also had actual verified reads.
They are one warm-host bounded sample, not a production throughput/SLA claim.
The tradeoff is additional directories/files: 962 versus 488 in this sample.
The deployed integrated candidate and its source/image report must independently
establish native completion; this microbenchmark does not establish it.

Fixture tests separately cover malformed locators, wrong scope, missing/corrupt
state, symlink refusal, global locking, old/new layout refusal, interrupted seals,
configuration agreement and sealed backup. The first selected test invocation
used an environment missing Chroma and failed one dependency import; the corrected
pinned environment passed all 36 selected methods. That failure remains retained.

The final lock-inheritance revision was separately rerun: [real report 02](../../evidence/phase2/development/storage-layout-real-02.json) and [source 02](../../evidence/phase2/development/storage-layout-source-02.json). Its final eight means were 115.2 ms (partitions) and 487.1 ms (historical), again 48 records each. A separate real-process test with an explicitly sleeping backend fixture verifies that killing Python leaves the outer lock held by its running child. A partially written seal fails closed; automatic repair of that boundary is not claimed.

`ADDITIONAL_LIVE_GENERATIONS=0`.
