# Bounded Go provider starter kit

This reference implements only `inspect_atom` under `inspect-atom/2`. It computes
SHA-256 and byte length for an immutable, authenticated AtomStorage input and
persists its exact JSON result through that same declared port. It does not
implement NAL, execute MeTTa, read a provider database, or call a model.

The extracted `go/` tree needs Go 1.18 or later and its standard library. The
published build pins the actual toolchain hash and records all files and binaries.
The maintained contract is embedded as `go/inspectprovider/contract.json`.
No Python process participates in the provider's transitions or conformance.

```sh
cd go
GOPROXY=off GOSUMDB=off CGO_ENABLED=0 go test ./... -count=1
GOPROXY=off GOSUMDB=off CGO_ENABLED=0 go build -trimpath -o ../omega-inspect-provider ./cmd/omega-inspect-provider
GOPROXY=off GOSUMDB=off CGO_ENABLED=0 go build -trimpath -o ../omega-client ./cmd/omega-client
cd ..
./omega-inspect-provider --config /config/provider.json
```

Supply existing Secret files separately. `config.example.json`,
`policy.example.json` and `storage.example.json` contain references only; the
storage descriptor is the selected real AtomStorage descriptor, not the Go
execution descriptor. Bind the caller's execution descriptor to the embedded
contract and enable `bounded-inspect-envelope/1`. Configure its endpoint by
composition; the native `inspect-atom` command is unchanged. NAL stays with its
original provider. The example synthetic scope must match every selected port.

`POST /preview/inspection` accepts the existing bounded submit/status/result
wrapper and commit-cursor reads. Recognized errors use HTTP 200 and the existing
typed error object, matching the native transport. `GET /descriptor` requires a
current bearer credential. `GET /healthz`, `/health/startup`, `/health/ready` and
`/health/live` make no work, budget reservation, upstream call or model call.

The explicit scope/profile/input/envelope are validated before acceptance.
Caller input-read authority, worker get/create authority, storage-owner grants,
and completion-mailbox grants are separate. Policy and credential files are
reread on each call/phase. Existing jobs retain their original identity, deadline
and exact response when credentials or deployments change. No credential values
are copied into the state file. TLS/endpoint/descriptor changes fence existing
state instead of silently rebinding it.

Use one process, one replica and one dedicated retained state volume. POSIX
`flock` on `/state/owner.lock` fences a second writer. The immutable owner seal
binds composition, role and synthetic scope. A restore-fence file refuses writable
startup; restore observation uses the existing operator/backup path. Acceptance, result/outbox, completion receipt and
Messaging acknowledgment remain independent commits. Files are fsynced before
rename and the parent directory is fsynced. SIGTERM gives HTTP shutdown ten
seconds. Never delete state to free capacity; this reference has a finite lifetime
bound of 128 jobs, four unclosed jobs, 128 KiB journal bytes and 32 spent worker
attempts per job. The first reached bound wins. No compaction, archival or
populated-state migration is advertised for this reference. A failed journal
commit fences that process until restart. Backward clocks are refused.

Transport loss may repeat a bounded, idempotent storage/completion request with
its existing identity. Attempts are committed before each worker phase and stay
spent after process death. The result is never recomputed after its capture.
The 32-attempt ceiling may exhaust during an outage; recovery then stays pending.
Mailbox acceptance is not recipient observation or acknowledgment. This
reference does not make exactly-once network-delivery claims.

The Go suite uses explicit fixture storage/completion ports. Actual journal
transitions, HTTPS, byte computation and process kills are real in those tests.
The extracted kit build is a separate portability result. Native Omega plus
real DeTTa/Messaging and Kubernetes placement are reported in the programme's
separate deployed evidence; passing this suite does not imply those gates.
The reference is single-node Linux/amd64, generated synthetic data only,
no public exposure or live-generation authority. The independently implemented
Go codec's existing integer/UUID constraints are part of this finite profile.

Provider onboarding must register the exact selected descriptor/artifact and
current scopes. Draining stops new admissions in trusted lifecycle composition;
it does not revoke authorized reads of retained results. Withdrawal does not
retime accepted work, erase its journal, change its descriptor, or refund attempts.


## Owner capacity and finish space (kits 03–04)

`GET /capacity` is a read-only `go-inspect-capacity/1` observation. A separately
provisioned principal needs exactly `execution.capacity` in the provider's
configured synthetic scope. Ordinary caller submit/status/result permissions do
not grant aggregate observation. The response contains no job IDs, principals,
payloads, deadlines, journal hash or source identity. Current credentials and
policy are checked on every read, including immediately before return. Health
checks remain unauthenticated and never expose this accounting.

The view reports lifetime and pending job counts, current serialized journal
bytes, logical completion reservation, available admission bytes, spent worker
phases, remaining phases of pending jobs and aggregate closure counts. A phase
reservation is not refunded when work closes. Completion reservations are
conservative logical journal-space admission checks; they do not reserve physical
filesystem space. Filesystem/PVC free bytes, process RSS, CPU time and the unknown
next request's size are explicitly null. Observation performs no owner save,
clock read, dependency call, dispatch, reservation or deadline renewal.

Kit 03 preflights the full worst-case retained state before inserting a new job.
It retains the existing 128-job, four-pending, 32-phase and 128-KiB limits. Each
future result plus its durability receipt is limited to **4096 JSON-marshaled
bytes**, independently of the 4096-byte input-atom limit. Result/outbox duplication,
maximum counter widths, escaped request fields and completion events are included
in the projection. This is stricter resource admission; it is not a universal
claim that every receipt accepted by the wider storage transport fits this
provider. Oversized upstream receipts return NOT_AVAILABLE, leave the attempt
spent and acceptance intact, and do not poison the journal. Already captured
results are never regenerated. At saturation exact duplicate acceptance and
current authorized result/status/capacity reads remain available; admitted pending
work has room to finish within these limits. Physical disk failures still fence
the owner. Existing journals are not rewritten, migrated or granted retroactive
space reservations; an uncovered legacy projection is explicitly reported and
new work is refused. Only fresh generated state is qualified by kit 03.

The closed standalone client uses the existing binary; it never invokes execution:

```sh
./omega-client --action inspect-capacity \
  --config /operator/capacity-client.json --deadline-ms ORIGINAL_ABSOLUTE_MS
```

The selected file has the shape of `capacity-client.example.json`. Only the
literal HTTPS `/capacity` route is allowed. The client validates the exact
profile, provider, scope, units, limits, headroom equations and explicit unknowns,
rejects redirects, and never retries or extends its original observer deadline.
Keep operator credential values outside the source/archive and caller/model
configuration. The policy example adds only an operator-scoped read grant; it
does not broaden native execution authority.

Kit 04 additionally binds observations to the durable owner revision and last
commit timestamp. Current observation time and reclaimable bytes remain unknown;
observations do not read or advance the owner clock. Control-write reservation is
explicitly zero because these read operations commit no journal data. This does
not imply physical disk headroom or reserve authority for another write action.
Kit 03's prior source/archive and tests remain separately preserved.
