# Separate retained-browser maintenance qualification

The completed B11 run did not keep an authorized old-token pool connection open
through credential rotation. Its genuine subscription gap was also separate
from Registry sealing and archive lookup. Those historical limits remain in
`browser11.json`; this supplement does not relabel that execution.

The E11 handover replacement retains Registry `/1`. Its verified `/2` format
copy is disposable and is not the activated state. The supplement therefore
uses the task-owned, stopped `omega-ref-pilot-browser11`, already on Registry
`/2` with ten closed native sessions, existing captured results and a published
archive. The original schedule placed this after E/V20 and suspension. E11 then
failed its first fresh target input and both handover namespaces were stopped.
The separately authorized supplement ran after that verified quiescence while
the corrected handover candidate was prepared offline. It did not extend B11's
earlier execution window or claim completion of E11/V20/suspension.

The standalone artifact `examples/pilot_live_pool_subscription.py` runs using
installed operator Python in isolated mode. A private, source-bound prospective
plan fixes the existing session, archive reference, selected provider, actor,
13 image pins and limits before any cluster action. The script validates all
owners are stopped, resumes only that namespace, requires all ten sessions to
remain closed, and stops it again with twelve PVCs retained. There are no native
submissions, generations, new corpus, profile changes or journal access.

Within a new 600-second maintenance window it performs:

1. Stage one temporary selected same-principal credential in its existing
   Secret and observe both projections, bounded by 120 seconds. This does not
   imply the owner automatically reloads its generated policy.
2. Create one 300-second application-owner subscription to a completed session.
   Leave its cursor unchanged while performing one exact current Registry seal,
   observing the existing archive and payload through the declared storage port,
   and replacing the storage pod once with the same image and PVCs.
3. Read the same subscription and authoritative snapshot. Explicitly rebase an
   actual gap, or acknowledge its actual complete page. Do not manufacture a gap
   or renew an expiry. Keep the same session and retained results.
4. Open a production `https_pool` socket using the still-authorized old token.
   The trusted operator atomically changes exactly one credential field in that
   owner's generated policy, preserving principal, scopes, profiles and every
   unrelated value. This is labelled **manual owner-local policy application**.
   Bounded read requests retain the actual connection; an old-token refusal must
   increment that same pool entry and close it. A new connection cannot pass this
   assertion. A stale-token subscription read must also refuse.
5. Use the same principal's current credential to read the exact retained inputs
   and same subscription cursor/expiry, then close the subscription. Restore the
   exact original policy bytes and complete original Secret data on every exit;
   verify restored readback. Unexpected unrelated policy drift refuses an
   overwrite and remains an explicit restoration failure, not silent success.

Bounds are at most 35 read invocations and five explicit control invocations:
29 reads in the browser-side driver, four archive reads and two closed-session
list reads. Actual driver `HTTPSConnection.request` method calls are counted
separately from logical calls and server acceptance. No method instrumentation
changes the frozen transport implementation. The socket phase has one fixed
15-second deadline; no read extends native task deadlines. The 300-second
subscription is never renewed. Original inputs and captured results are compared
inside the authorized observer; no private content or identifying hashes appear
in public evidence. Successful archive hydration does not prove a cold path or
hot-record deletion.

Run only after the serialized heavy slot is handed over:

```sh
operator13/bin/python -I /packet/examples/pilot_live_pool_subscription.py \
  --kubeconfig /private/operator.kubeconfig --context default \
  --namespace omega-ref-pilot-browser11 \
  --plan /private/browser11-pool-subscription-plan.json \
  --output /private/browser11-pool-subscription-result
```

The plan and its separate SHA-256 sidecar remain private because they bind
retained private identifiers. The immutable script/test copies and raw check
logs accompany the prospective plan. Tests use local temporary policy files and
explicit protocol fixtures; they are not deployed evidence.

The deployed supplement **passed on runtime11** on 2026-11-05. It took 158.976
seconds including quiescence, within its separate 600-second window. It made
22 module read invocations and four control invocations: create subscription,
seal Registry history, rebase the actual gap, and close subscription. The
browser-side driver separately counted 16 read and four control
`HTTPSConnection.request` calls; physical sends for the other six reads were not
instrumented, and server acceptance counts are not inferred from these calls.

The still-authorized old credential opened the actual production pool socket
before the trusted policy change. That same socket then received `UNAUTHORIZED`
and was closed and evicted. A stale subscription read also refused. The same
principal's current credential read the exact 15 selected existing captures and
the same subscription, with its original expiry. Its cursor had remained
disconnected through the actual six-action Registry seal, existing archive
readback and storage Pod replacement; an observed gap was explicitly rebased
from the authoritative snapshot. No new native input, capture or generation
occurred.

The exact original policy bytes, full original Secret material, both Secret
projections and retained capture readback were verified after restoration.
All ten native sessions remained closed; cleanup left zero pods and twelve
owner PVCs, with ConfigMap data unchanged. The ten source-qualified helper tests
also passed. See [the sanitized executed report](../../evidence/operator-pilot/live-pool-subscription11.json)
for exact source, counts and limitations. Private plans, identifying hashes,
socket addresses and raw reports are withheld. Original E11, B11, their primary
failures and the separately scheduled suspension remain independent evidence.
