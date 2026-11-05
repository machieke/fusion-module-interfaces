# Bounded deployment reply faults

This hook is disabled by default and exists only for task-owned deployment
qualification. It runs after the selected authenticated owner operation returns;
it does not perform work, add retries or change owner contracts or profiles.
The [focused qualification](../../evidence/operator-pilot/reply-fault-tests.json)
separates real local TLS/process behavior from its fixture owner and from the
separately executed deployment gates.

Use a fresh fault identity and retain the original accepted observer deadline:

```yaml
testFaultsEnabled: true
components:
  fusion-storage:
    config:
      test:
        reply_fault:
          profile: deployment-reply-fault/1
          identity: storage-delayed-read
          path: /reference-cognition
          operation: head
          mode: delay
          delay_ms: 5000
          observer_deadline_ms: ORIGINAL_ABSOLUTE_DEADLINE_MS
```

`ORIGINAL_ABSOLUTE_DEADLINE_MS` must be replaced with the already selected integer
deadline. The typed `preview_atoms`/`AtomFeedClient` uses `/reference-cognition`.
The separate `memory_services.Client` uses `/memory-source` and its existing
`neoclaw-memory-source-ports/1` wire contract. Both `head` routes are allowed; do
not change a client's endpoint without preserving its actual contract.

For a partial body, select a distinct identity, `mode: partial-body` and
`delay_ms: 0`. The service writes a strict prefix of the real returned bytes,
preserves the original full Content-Length, and closes. It does not synthesize
an answer. Fixed delay choices are 250, 1000 or 5000 milliseconds. Both a fixed
monotonic limit and the original absolute observer deadline bound the delay;
applicable accepted request deadlines can only shorten it. Clock rollback and
marker fsync time cannot lengthen that bound.

The one-shot marker is `/state/reply-fault-<identity>.json` in that service's
own PVC. Its only fields are `selection`, `state: claimed` and `claimed_ms`.
It contains no request, result, credential, caller identity or payload digest.
An exclusive create and fsync consume the identity before any injected delay
or prefix. Replacement preserves that consumption even if no bytes escaped.
The marker is not a delivery receipt. A changed binding under the same identity
refuses; at most sixteen identities may be retained. Do not remove markers to
rearm a test or infer that an uncertain operation was absent.

While a delayed read is claimed, SIGTERM causes the server's existing stop event
to abort the reply without sending successful headers or body. A pod kill also
leaves the claim spent. A later explicit observation may check the unchanged
owner state. It must not replay an uncertain mutation under a new identity or
renew its original bounds. Owner locks and request-lane permits are released
before the delay. Health checks and denied/error responses never consume a
fault identity.

`reply_fault` cannot be combined with another test hook on the same component.
The historical `drop_response_operation` behavior is unchanged. Removing the
fault selection disables injection while retaining its marker. Cluster fault
drivers must keep actual caller invocations, known physical requests, owner
effects and recipient observations separate.
