# Independent Go inspection provider

This reference implementation performs only `inspect-atom/2`: it reads an authenticated immutable atom, computes its SHA-256 and byte length, writes the exact result through AtomStorage, and delivers completion through Messaging. It does not implement NAL arithmetic. The original NAL and workspace providers remain separately selected.

The extracted `sdk/go` project uses Go's standard library and the existing typed Go client. It does not import Python owner transitions or require the repository at build/runtime. The starter kit builder runs its build and tests in an isolated mount/network namespace. Unit ports are explicit fixtures; those tests are not deployed-provider evidence.

Kit 02 is pinned to Go 1.27.3. Its independent source manifest is `60fd865aaf5eaf9cfce2591d79d739ac7b68f6e7a7bf22063f9029873f2c2dd5`; provider binary SHA-256 is `8fc1cee13d0259dceb06054454832fdd9894cb8260a841218cd2fee631de9d73`. The provider selection is `41e88ad1ba0135f71666f8516629470a962a8444153111b1165fafe9be0625ed`. Kit 01's older compiler/source identity remains historical.

The scratch image contains the static provider binary and its build manifest. It runs as UID/GID 1000, with its own PVC, current credential-file references and authenticated HTTPS to storage/Messaging. `/health/startup`, `/health/ready` and `/health/live` never execute work or contact another provider. `/descriptor` requires authentication. The chart binds the actual storage feed profile explicitly; the pilot selects `immutable-commit-feed/2`.

The owner uses an exclusive `owner.lock`, immutable scope/role seal, fsync/rename journal commits, current policy checks, fixed accepted deadlines and spent phase budgets. Acceptance, result/outbox and completion observation are separate durable commits. It refuses writable startup under a restore fence. It does **not** implement the separate writer-handover profile, numerical rules, archival rotation, multi-host availability or HA. Its limits remain 128 lifetime jobs, four pending jobs, 32 reserved worker phases per job, 128 KiB journal and 4096-byte input atoms.

## Installed onboarding

`integration.single_node.pilot_go_values initial` prepares the original shared/private templates with an idle Go workload. `replace` adds the opt-in `retained-inspection-template/1` template named `go-shared`; the existing shared/private templates, runtime digests and accepted sessions remain exact. Only this new template changes the inspection descriptor and endpoint. Allocation chooses a trusted template name, never an executable path or provider URL.

Registry admission is explicit for each new template. Readiness is an observation, not authority or conformance. The old execution record can be drained/retired while its original capture remains observable. A separate new native session selects the independently admitted Go record. No journal or capture transfers between providers.

The two-stage executable qualification is:

```sh
python -m examples.pilot_go_provider --kubeconfig "$KUBECONFIG_FILE" \
  --context default --namespace omega-ref-pilot-go03 \
  --plan INITIAL_PLAN --artifact GO_PROVIDER_IMAGE_MANIFEST --directory BASELINE_REPORT
# Explicitly install the additional-template Helm values before the next command.
python -m examples.pilot_go_provider --kubeconfig "$KUBECONFIG_FILE" \
  --context default --namespace omega-ref-pilot-go03 \
  --plan REPLACEMENT_PLAN --artifact GO_PROVIDER_IMAGE_MANIFEST \
  --original BASELINE_REPORT --directory REPLACEMENT_REPORT
```

Both stages call the same `consume()` function and actual native remember, delegate, inspect and context commands. The replacement stage tests unadmitted refusal, current wrong-credential rejection, old-record drain, provider pod replacement, immutable event replay and actual inspection feedback in the next captured native prompt. Recorded models propose commands only. The operator reads public owner observations and the caller's own accepted prompt for audit; it never supplies provider results.

The distribution verifier treats this as a separate `inspect-go` artifact with independent source/image/kit pins. It verifies the exported OCI's exact static binary and build manifest, then compares that image digest to the deployed pod. It does not pretend the scratch image has Python or the main Python source manifest. Qualification reports, rather than these invocation examples, determine whether deployed gates ran and passed.


Kit 03 adds the separately authorized `/capacity` owner observation and a closed
`omega-client --action inspect-capacity` command. It also reserves conservative
logical finish space before new acceptance, retaining the original operation,
selection, identity and journal schema. The retained result plus receipt is now
bounded to 4096 JSON-marshaled bytes; this is a provider-local resource limit,
separate from the 4096-byte input atom. Oversized receipt attempts stay spent and
leave the accepted job pending without poisoning the owner. Kit 02's source,
artifacts and fixture-port conformance remain historical; no migration or
retroactive completion-space guarantee is asserted for its populated state.

The capacity credential has only explicit `execution.capacity` authority in the
configured synthetic scope. Native submit/status credentials do not grant it.
Aggregate counts and byte projections omit all job IDs and payloads. Physical
filesystem/PVC free space, process RSS, CPU time and next-request size remain
unknown. Journal projection is a logical admission reservation, not a physical
storage reservation. The exact new artifact identities and executed deployed
observations are recorded separately when produced.

Kit 04 is the current capacity-conformance artifact. Its source manifest is
`738bdb6ad57aa939545400f3074283f68a9b5343d1d6665a3a5313fd4a44e53a`,
provider binary is `e29991d23c42a00c0f7d4609245ddfa333d8aa59081fdadd0ba0f3b0ef0b9dac`,
and image is `sha256:e2f7505e2ae6d6e3038f5049cfd2a181e3add14db98b388dd05ba8b7ded859cc`.
Kit 03 remains a separately tested preparation artifact. Kit 04 additionally
reports the durable owner revision and last-commit time. Read time and reclaimable
bytes are explicitly unknown. Control-write reserve is zero: capacity and retained
read operations write no journal data. These fields do not claim physical free
space or permission to accept an unbounded future request.

The exact `inspect-atom/2` descriptor and selection are unchanged. The narrower
4096-byte retained result/receipt admission is explicit; deployed qualification
must show the selected real storage receipts fit. Neither fixture-port tests nor
image scanning alone establish that real-provider compatibility gate.

## Capacity operator recipe

`examples/pilot_go_capacity.py` is distributed separately from the Go kit. It
verifies the selected image artifact, frozen placement plan and chart before
using an existing scoped namespace. Provisioning adds only
`inspect-capacity-token` to the fresh `fusion-inspect-go-tls-auth` Secret, with
optimistic resource-version protection. It refuses an existing Go StatefulSet,
Pod, PVC or capacity key. A failed/uncertain Secret update retains its prepared
private credential and does not rotate or retry it. Never publish that directory.

For a fresh namespace, create the existing service Secrets with the packaged
`fusion-create-secrets` command first. Then provision capacity before installing
the unchanged chart recipe. `services upgrade` uses `helm upgrade --install`, so
it accepts this explicitly pre-provisioned first installation without generating
another set of Secrets:

```sh
"$OPERATOR/bin/python" -I "$PACKET/examples/pilot_go_capacity.py" provision \
  --kubeconfig "$KUBECONFIG_FILE" --context default --namespace "$NS" \
  --plan "$PLAN" --artifact "$PACKET/go-provider/provider-image.json" \
  --chart "$PACKET/deploy/helm/omega-fusion" --directory "$PRIVATE_CAPACITY"
"$OPERATOR/bin/fusion-pilot" services --kubeconfig "$KUBECONFIG_FILE" \
  --context default --namespace "$NS" upgrade \
  --chart "$PACKET/deploy/helm/omega-fusion" --values "$VALUES"
"$OPERATOR/bin/python" -I "$PACKET/examples/pilot_go_capacity.py" observe \
  --kubeconfig "$KUBECONFIG_FILE" --context default --namespace "$NS" \
  --plan "$PLAN" --artifact "$PACKET/go-provider/provider-image.json" \
  --chart "$PACKET/deploy/helm/omega-fusion" --provisioned "$PRIVATE_CAPACITY" \
  --directory "$FRESH_OBSERVATION" --deadline-ms "$ORIGINAL_OBSERVER_DEADLINE_MS"
```

The observer allows at most one HTTP call and an original deadline within 120
seconds. It runs the verified static Go client outside all workload pods, with a
private `127.0.0.1` port-forward and an isolated hosts mapping for the exact TLS
name. It does not change host DNS or put operator credentials in a caller/model
container. The selected pod's configured and observed image IDs are recorded;
the forward is stopped even on failure. Client invocations and validated owner
observations are counted separately. This operator observation route is separate
from the native caller's real pod-to-pod HTTPS gate.

Only the Go chart block adds the operator grant, when the existing pilot capacity
selection is present. Native caller/worker grants stay exact. Rendered manifests
for the six selected Go-disabled compositions remain byte-identical to packet 11;
[the chart reconciliation](../../evidence/operator-pilot/go-capacity-chart.json)
records the actual hashes. [Go qualification preparation](../../evidence/operator-pilot/go04.json)
keeps real Go/fixture-port tests, earlier harness failures, static artifacts and
unrun deployed gates distinct.

For a paused or interrupted qualification, inspect the current Registry
readiness before retiring an original provider with retained access. An expired
readiness result is not renewed by replaying its identity. Make a separately
identified current probe through the normal operator port, and retain the prior
refusal. This observation does not renew an accepted session binding, input
deadline, reservation or execution window.

After a native session is closed and its caller pod restarts, its ephemeral
`/run/fusion/sessions/<session>/inspection.json` may no longer exist. Retained
session observations remain available through the application API. Provider
event readback must select the exact existing trusted `go-shared` template port
and current authority, after comparing the retained Registry selection. Do not
reconstruct the deleted session configuration or initialize another native
session to obtain a read. The installed native consumer uses its active
configuration before closing the session; this restriction applies to later
operator observations.

Keep the observer's deadline within both its original control window and the
capacity client's 120-second maximum. A local argument rejection has made no
provider call. Preserve that rejection, and distinguish any subsequent bounded
read from the failed observer invocation. If the original execution window has
expired, a separately declared finite owner-control window may inspect retained
results and drain new selection; it grants no native work and does not make the
original-window qualification complete.

[Go13 deployed evidence](../../evidence/operator-pilot/go13.json) records the
runtime11/Go04 composition: eight selected native inputs and four internal task
captures across the original and Go placements. It preserves five failed
operator/control invocations, the successful same-session native recovery, and
the separately bounded retained-state drain/readback. The original-window drain
remains `NOT_COMPLETED`; the later control result does not relabel it. All task
pods were stopped and the 13 owner PVCs retained. These results supplement the
historical preparation and Go12 evidence without changing their source labels.
