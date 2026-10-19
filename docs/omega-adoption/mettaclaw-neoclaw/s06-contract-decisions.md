# S06 selected contracts and regression impact

S06 selects `isolated-irc-mailbox/1` and a fresh `controlled-native-loop/8` composition. This is a channel adapter profile over the existing `atom.storage@1.0.0 / immutable-bytes/1` and `agent.messaging@1.0.0 / durable-mailbox/2` ports. It neither changes their historical profiles nor adds a module family. The native application, local C1/C2, Attention and their numerical dependencies retain their existing owners.

The bridge owns connection epochs, frame occurrences, pending ingress relay and outbound socket reservations. AtomStorage owns immutable channel envelopes. Messaging owns ordered delivery and acknowledgment. The application owns the accepted input's assignment to a processing slot, source linkage, command occurrences and native result/context captures. None reads another owner's tables. Evidence helpers may inspect journals only after execution for the report.

Each complete permitted `PRIVMSG` has a bridge UUID, a persisted connection epoch and a sequence allocated with its exact body and relay intent. Equal text in separate frames creates separate occurrences. Partial frames and traffic before capture remain volatile. Every new connection records a discontinuity, without inventing missing messages or continuity. One exact configured channel and one Omega consumer are supported; nicks are attribution, never internal principals.

An application input is committed with its immutable envelope, mailbox delivery and processing slot before acknowledgment. Receive retries recover that assignment. The new native input predicate uses the assignment rather than text equality. One frame is presented per slot instead of the old concatenated buffer. Existing accepted commands resume before another input is assigned. Before model-response acceptance, generation may repeat; no exactly-once model guarantee is claimed.

The existing S04 source hook obtains its selected source specification from the accepted channel envelope in `/8`, rather than the historical scripted slot map. Its stable source key derives from that message occurrence. It records a transport observation locally, with no automatic belief submission, fabricated independence or evidence weight. S05 global context is prepared and captured before receive as before. Input wait limits are separate from, and never renew, context or command deadlines.

Native send accepts only one explicitly approved generated string on the fixed route. It preserves the original one-chunk bytes on the admitted domain; control characters, multiline/chunked bodies and content requiring legacy wrapping or normalization fail. Disclosure is checked locally before a remote call. `SEND-ACCEPTED` means AtomStorage/Messaging acceptance, not peer delivery. The bridge accepts and acknowledges the outbound envelope into its own journal, then reserves exactly one attempt before the socket write. A crash after reservation leaves `unknown` unless a transport outcome was recorded. It never automatically resends. The peer log remains separate evidence.

Closed envelopes and wire requests bind profile, selected descriptors, principal, scope, fixed routes, bridge, session/occurrence, correlation and exact bytes. Live policy governs new work and replay. Bridge and application have distinct credentials and route permissions. Only synthetic channel records enter the new shared scope; private cognitive state and identifying derivatives are refused by a narrow explicit output allowlist. This is not general declassification of model output.

Placement is chosen in composition. The same application calls the same ports locally or through the existing certificate-verified loopback HTTPS mechanisms. The bridge owns the IRC connection. The caller has no provider configuration in HTTPS mode, and filesystem isolation hides mailbox/bridge/server stores. Native startup forbids the legacy IRC buffer/socket helper. Network restrictions and their actual enforcement strength are recorded separately; this host's Linux 5.4 kernel does not provide Landlock network controls.

Bounds, failure statuses, actual isolation checks and executed evidence will be recorded in the S06 report. No accepted row is evicted to regain capacity. Pending work can remain blocked or expired; neither a timeout nor a socket write is a delivery acknowledgment. This increment adds no daemon scheduler, second channel, history recovery, populated-state migration, remote private cognition, live model or chain operation.

Before shared-source edits, 247 S05 tested hashes, 35 final changed-file hashes and 141 evidence hashes reconciled with `c9c6e7985c8214feeedc78686f475efb3ad40625`. Baseline/final impact covers M1/M1.1 Messaging/storage/receipts; shared application/native startup and S01/S02 transport; S04 source linkage; S05 context; and the affected S03–S03.2 HTTPS query/embedding/append paths. Historical tests and failure reports retain their identities.

## Executable limits and observations

| Boundary | Bound / meaning |
|---|---|
| IRC frame | 512 bytes including CRLF; strict UTF-8 only after a complete frame; retained incomplete frame at most 510 bytes |
| Body | 1–400 UTF-8 bytes; no control characters; outbound must already equal one original wrapping chunk |
| Bridge ingress | 4 pending relays, 128 captured occurrences per fresh journal, 16 connection epochs |
| Mailbox | 2 unacknowledged deliveries per route; acknowledgment frees capacity, never deletes the authoritative capture |
| Relay | Original capture deadline +120 seconds, 32 durably reserved calls per put/send phase; availability retries wait one second |
| Application input | One occurrence per processing slot; configured wait 100–10,000 ms and 1–128 persisted polls; no empty-success substitution |
| Source/model admission | Original accepted-input deadline, at most 30 seconds; earlier context deadline remains separate |
| Native commands | Existing at-most-five homogeneous commands per turn and original 30-second command deadline; every send has one wire message |
| Application outbound | 32 persisted calls per payload/mailbox phase; accepted replay performs current authorized read |
| Bridge acknowledgment | 32 persisted attempts, recoverable from its own retained delivery even after poll stops returning it |
| External send | Exactly one reserved attempt per accepted occurrence; no reset or automatic resend |

The egress observation states are `pending`, `unknown`, `socket-write-returned`,
`rejected-before-write`, `expired-before-reservation`, and
`expired-after-reservation`. The bridge-owned `observe(id)` read reauthorizes
through AtomStorage and returns the retained reservation/outcome/epoch with
`recipient: not-observed-by-provider`. It is an operator-local read, not a new
public execution operation or recipient acknowledgment. The separate peer log can
corroborate a first write while the provider's outcome correctly remains unknown.

The selected HTTPS envelope admits only AtomStorage `create/get` and Messaging
`send/poll/ack`. It binds the complete pair of selections as well as the existing
per-operation receipt. The new scope holds only canonical, validated channel
records, with stable `payload/<occurrence>` and `mail/<occurrence>` keys. Egress
uses the existing application command UUID; ingress uses UUIDv5(connection epoch,
sequence). Credentials are excluded from durable composition bindings so rotation
for the same principal is possible. Endpoint/CA, local provider path, roles,
allowlists, scopes and routes remain bound. Old unsealed service journals are
refused. Historical M1 DTOs and profiles are unchanged.

A source-checked module named `s06_channel` replaces only the selected native
receive call. PeTTa appends Python import paths, so sharing the old `irc` basename
could import the historical fixture first. Startup now requires that the old
module is absent. The native Python audit hook refuses direct IRC connections and
permits only the selected mailbox HTTPS port. Filesystem masks are exercised in
the native caller, provider and bridge. These are trusted-runtime guards, not an
OS network sandbox or protection against hostile code running as the host user.

Each channel release requires the complete selected role and both registered
routes. Existing route policy also requires each route owner to retain poll
authority. Revoking the application's ingress poll can therefore halt bridge
activity until explicit operator recovery; it does not erase accepted state.
Revocation tests distinguish this from revoking only caller payload-read authority.
