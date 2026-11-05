# Pilot failure, time and retry semantics

This audit covers the selected single-node implementations at the source hashes in [retry-audit.json](../../evidence/integrated-service/pilot/retry-audit.json). It is a source review plus the specifically listed isolated tests. It does not turn library tests into native/pod qualification, and it does not authorize live generation. The integrated programme records deployed fault stories separately.

## An uncertain response is not absent acceptance

The Python synchronous clients, pooled HTTPS transport and Go client send once per explicit invocation. A failed exchange is returned to the caller. The pool closes failed sockets and does not reconnect and retransmit that request. A new explicit invocation can reconnect, but must retain the original mutation/occurrence identity, input, scope, provider selection, view and accepted deadline. Error `retryable` is advice, not a retry instruction.

There are explicit bounded retry loops in the historical NAL caller and IRC ingress relay. NAL increments its durable caller-call counter **before every RPC**, including polling, result reads and acknowledgments. The bridge separately spends payload-put, mailbox-send and mailbox-ack budgets before I/O, and delays an unavailable ingress relay attempt. These are real retry points; they are not described as “no retries.” Physical transport sends can be fewer than reserved calls after process death. Owner acceptance, provider/backend evaluation and recipient observation are separate counts.

Browser JavaScript issues one `fetch` for each requested route and does not retry mutations. A single button action can perform several explicitly coded reads before its one mutation. The browser engine's internal TCP/HTTP behavior was not packet-audited; source-level fetch counts are not a claim about packets. Server-side deterministic action identities and current owner checks still prevent duplicated logical effects. Go creates a fresh transport with keep-alive and HTTP/2 disabled, prohibits redirects, and performs one `Do` for each invocation; it does not set an HTTP idempotency header that would invite automatic POST replay.

The selected native E5 worker uses one supervised pipe exchange per reserved encoding attempt. It never downloads a model, launches a hosted fallback or secretly retries a failed encode. Chroma is a local `PersistentClient` with `embedding_function=None`; payload hydration and feed access use declared HTTPS AtomStorage ports. DeTTa and NAL adapters run their pinned local subprocess once per explicit backend call. Their subprocess timeout does not prove an interrupted effect was absent. The Ollama adapter was inspected statically only: it makes two non-generative readiness reads and at most one `/api/chat` POST per admitted call, without an SDK retry. **It was never instantiated or contacted in this audit.**

## Model responses and external sends

The model owner independently commits acceptance, backend reservation and response capture. A reservation with no capture remains unknown/spent, including failure before the backend was contacted. `observe` never generates. Replaying `complete` with a capture returns the original captured response under current authority; replaying a reserved unknown does not call the backend. A changed identity is new work and cannot reconstruct the prior capture.

IRC socket output reserves before writing and immediately marks the outcome unknown. It rechecks current payload authority and the original deadline before the write. A socket error may mean some bytes escaped. An unknown outcome is never automatically selected for resend. `socket-write-returned` is not recipient observation. Mailbox acceptance and acknowledgement remain different from both. Reconnecting IRC records a new connection epoch with an explicit upstream history gap; it does not recover messages never durably captured by the bridge.

## Time domains and the new fresh-owner profile

| Boundary | Time and behavior |
| --- | --- |
| Application allocation, dispatch, cancellation, Registry | Durable epoch-millisecond high-water in the application owner; backward samples refuse, deadline equality expires new work, original accepted identities remain retained. |
| Native promotion | Existing `wall-clock-promotion/1` uses original bound epoch seconds and per-context high-water. Reads of retained scores preserve their old revision/time. Native mathematics and historical equality semantics are unchanged. The native evaluator requires strictly positive remaining subprocess time. |
| Workflows | Original absolute deadline, finite observation/effect reservations, current authority and a persistent workflow clock. Operator approval records a decision; it does not renew execution or make a failed prerequisite true. |
| HTTPS pool and preview transport | Absolute caller bound where provided plus a monotonic per-exchange limit. Slow responses cannot restart the read window. Socket inactivity limits in older S01/channel/vector transports are not falsely claimed to be durable execution deadlines. |
| Browser auth | Finite monotonic session lifetime and current policy revision; reboot loses the cookie session, while application state remains owned durably. |
| Browser observation | At most150 admitted read cycles and a300000ms monotonic admission window. An in-flight bounded read may finish after the window; no additional cycle starts. Observer expiry does not cancel work or resend input. |
| Operator subscriptions | Durable epoch high-water, finite observation lease and action capacity. Renewing observation never changes an input deadline or spent allowance. An expired lease cannot be resurrected by replaying a renewal. |
| Historical ModelInference | Its existing selected profiles and two-table journal remain unchanged. They use epoch deadlines and do not acquire the new persistent high-water semantics implicitly. |
| Fresh pilot recorded ModelInference | Explicit `preview.pilot.owner_clock={"profile":"recorded-model-owner-time/1"}` installs clock metadata in each fresh model-owner partition, including private partitions. No live model profile is admitted by this option. |

The new recorded-owner clock profile checks persistent high-water before acceptance, reservation and backend entry. A process suspended after reservation until deadline equality keeps the reservation spent and enters no backend. Forward jumps can expire unstarted effects; backward samples cannot create new work. The profile stores bounded clock metadata inside the same existing model journal and refuses attaching to either a populated or empty historical journal. Removing it from a selected journal also refuses.

A response already returned by the provider is captured **before** clock-anomaly refusal, with its actual raw epoch sample. A backward or invalid capture sample is preserved in the owner journal and explicit owner inspection metadata; it is not rewritten to the high-water time. Its normal result-disclosure operation refuses `CONFLICT`, preventing command admission. Restart and a later valid clock do not regenerate or replace the capture. A forward late capture remains observable as late under current disclosure authority. These controls offer no distributed-clock or host-clock correctness guarantee.

## Bounded incident handling

The following modes are owner observations, not a global state machine. A refusal can be correct while the requested positive workflow remains incomplete.

| Dependency or mode | Permitted observation/control | Blocked or unsafe action | Recovery condition |
| --- | --- | --- | --- |
| Encoder unavailable | Read retained application captures and already stored AtomStorage data; scoped cancellation before dispatch | New remember/query needing an uncaptured vector; hidden local encoder fallback | Original pinned encoder ready, current authority and original occurrence deadline/budget still permit work |
| Search unavailable | Retained captured query readback, authoritative storage/history observations | Treating unavailability as an empty corpus; changing a retained query generation | Same selected generation is ready through authenticated Search, or a separately admitted new query selects a newly ready view |
| Storage unavailable or corrupt archive | Application receipt observation where independently retained | Rebuilding an authoritative payload from a fixture; using hot copies to bypass a selected corrupt archive | Original required immutable payload/archive closure verifies through owner ports |
| Messaging unavailable | Existing execution/result capture readback; observe an uncertain IRC send | Declaring completion delivered or acknowledging input from returned text alone | Same mailbox identity/route becomes available and exact saved receipt can be observed |
| Registry capacity-refusing | Authorized headroom/selection reads and reserved audit sealing controls | Refunding audit history, rebinding accepted sessions or dropping old action identities | Exact reviewed audit seal succeeds; retained capacity bounds and selected provider readiness still permit the next new acceptance |
| Chain unavailable | Completed off-chain native results and saved exact-artifact commitment intent | Assuming socket submission is finality, issuing a new signed intent to conceal uncertainty | Matching deploy-effect readback/finality on the same isolated selected chain; no new chain activity is authorized by this audit |
| Uncertain effects fenced | Owner receipt/source observation and bounded reconciliation | Calling a missing provider step, retrying unknown socket output or replacing IDs | Owner-authoritative result resolves the original identity; otherwise retain uncertainty |
| Draining or observation-only restore | Captured/history readback subject to current scope; exact finite maintenance if selected | New native effects, stale writer restart, accepting an old writer's authority from imported state | Explicit current external writer authority and qualified planned handover; a backup alone grants no execution authority |
| Model live-disabled | Recorded-only selected sessions and static future-plan inspection | Contacting/loading a real runtime or consuming a live slot | Separate campaign-bound user approval and all frozen prerequisite checks; not part of this programme |

## Operator commands

The provisioned browser user needs only the loopback browser origin and a separate user bootstrap. The following equivalent CLI is for a trusted operator holding the provisioned gateway configuration; it does not use kubeconfig or a broad ambient provider credential:

```sh
python -m integration.single_node.pilot_browser_client --configuration PRIVATE_CONFIG --user alice state
python -m integration.single_node.pilot_browser_client --configuration PRIVATE_CONFIG --user alice observe < OBSERVE.json
python -m integration.single_node.pilot_browser_client --configuration PRIVATE_CONFIG --user alice current < CURRENT.json
python -m integration.single_node.pilot_browser_client --configuration PRIVATE_CONFIG --user alice subscription < SUBSCRIPTION.json
python -m integration.single_node.pilot_browser_client --configuration PRIVATE_CONFIG --user operator registry-maintenance < REVIEWED_REGISTRY_PLAN.json
```

`OBSERVE.json` is `{"role":"omega-agent","session":"ACCEPTED_SESSION","after":0}`. `CURRENT.json` adds `"operation":"current"` instead of `after`. Every session/ref, actor, scope and capability is checked again by the owner. Save the original accepted identity before diagnosing a lost response. Use `observe` first; do not press “new occurrence” to recover old work. A subscription gap requires the explicit full snapshot and exact rebase flow, not cursor advancement based on missing hints.

For a stable captured result after gateway replacement/credential rotation, the installed qualification helper accepts `--reconnect-report ORIGINAL_PRIVATE_REPORT`; that mode performs no submit. For maintenance, retain the exact preview digest and action identity. Stale plans refuse. Search repair/cleanup does not create missing authoritative data or free accepted budgets.

## Executed and remaining evidence

The audit JSON pins every reviewed file and the exact test invocations. The isolated pool tests use real TLS sockets with an explicit file payload fixture: lost reply, partial body, stale socket, rotated credential/CA, current revocation and bounded connection capacity. They do not establish k3s network-policy behavior. The Go tests use real local TLS and fixture responses. Model-clock tests use real SQLite and an actual SIGSTOP/SIGCONT child with authored proposals, never live generation. Browser ProofShot verifies a simulated expired observation window with zero read dispatches; it does not claim a five-minute deployed soak.

Deployed asymmetric network-policy loss, delayed replaced-pod replies, service-to-service partial outages, native promotion suspension, slow subscriptions across Registry seal/archive/provider replacement and cross-feature restored continuity remain separate programme evidence. The static audit cannot prove behavior inside an untested browser implementation, resolver, kernel or third-party SDK. The historical model time limitation remains explicit for unselected existing state.

The resident-worker selection has a stricter restart boundary than the earlier
single-process loop driver. A dispatched input without a committed final native
projection remains fenced after its process dies. A captured model proposal,
provider result, or task payload alone does not complete that application input.
`reconcile` may acknowledge an already committed final projection; it cannot run
missing tools, publish a missing task return, or register a replacement worker
for an uncertain assignment.

The original `faults10` qualification expected that earlier driver's automatic
continuation and failed at its unchanged deadline. Its retained source and
[failure observation](../../evidence/operator-pilot/faults10.json) remain intact.
The corrected operator qualifier tests final-projection recovery and uncertain
fencing separately. A safety pass for an unfinished dispatch is explicitly
`NOT_COMPLETED`; it does not count as a successful native workflow.
