# Codex handoff — S06: one real channel through durable Messaging

## 1. Objective and stop boundary

Continue `machieke/fusion-module-interfaces` from S05 publication
`c9c6e7985c8214feeedc78686f475efb3ad40625`, or record the exact descendant and
relevant changes. Read applicable AGENTS.md, the original brief, the MeTTaClaw
mapping, S01–S05 contracts, source manifests and affected tests. Preserve unrelated
work and restricted dependency sources.

**Proposed next increment:** implement the mapped S06 durable-mailbox/channel
boundary for ONE existing channel: IRC. A real isolated IRC server and a separate
test peer must deliver generated input to the actual native Omega loop through
AtomStorage and Messaging. A native `send` must create a durable, bounded outbound
intent and reach the peer in the positive demonstration. Make mailbox/payload
placement selectable between local and authenticated same-host HTTPS without
changing native application logic.

This selects a first bounded IRC profile, not a universal channel implementation
or a decision already made in the meetings. IRC is selected because it is an
existing native path and can be exercised on a disposable server without touching
an organizational account. Do not implement Mattermost as well in this increment.

**Stop at S06.** Fresh synthetic journals, one server, one configured channel, one
Omega consumer, sequential processing and one bounded outbound wire message per
accepted send. No public IRC/Mattermost connection, production workspace messages,
remote private cognition, migration, multi-host deployment, hosted-model adoption,
new reasoning, general history synchronization, universal event bus, scheduler,
IRC server implementation, or chain work. Do not remove existing private-local
restrictions to make the new messaging placement pass.

The hard result is real channel input -> durable module handoff -> native input
consumption -> native operation/result -> durable outbound intent -> observed test
peer receipt, with honest uncertainty at the nontransactional IRC boundary.

## 2. Review basis and baseline

The reviewer inspected selected public S05 implementation, tests, report, manifest,
legacy channel source and native loop at the pins below. The reviewer did NOT run
the native suites, reconcile every source hash, start an IRC server or test this
new design. Validate the findings locally before implementation.

S05 records 27 new methods and 159 selected regression methods: 186 distinct
methods in its passing union. The report distinguishes development corrections,
parameterized kill scenarios and final targeted native-runtime rechecks. It is
not one full-repository run and not 186 new methods. Final publication must not
retroactively replace the recorded working-tree identity of any historical run.

Reconcile the published files against `evidence/s05/test-source.json`,
`source-state.json`, `source-reconciliation.json` and relevant per-run manifests.
Record documentation-only differences separately. Run an impact-selected baseline,
including Messaging, acknowledgment/replay, S05 native context and affected S01–S04
application/transport paths. Do not stage/reset unrelated sibling work.

Retain existing MeTTaClaw, PeTTa/SWI, DeTTa, E5 and Chroma pins. The existing separate
Fusion PLN runtime is unrelated to channel adoption and must not be rebaselined.
A new IRC server dependency needs its own obtainable source/image identity,
configuration, build/start command and local isolation evidence.

## 3. Findings to verify and sources to inspect

All Fusion paths here refer to the S05 publication above. Native MeTTaClaw is
`2af37c3fec18613de54ca42fde2382a9087d4524` unless explicitly rebaselined later.

| Source | Relevant boundary/finding |
|---|---|
| `docs/omega-adoption/mettaclaw-neoclaw/remote-placement.md`, `seam-contracts.md` | S06 separates durable mailbox semantics from channel transport, identity and external delivery. These mapping statements are historical proposals. |
| Native `src/channels.metta` | `receive` obtains and clears a latest-text buffer; `send` discards transport results and returns `SEND-SUCCESS`. |
| Native `channels/irc.py` | Volatile concatenated buffer; no retained external message ID; per-`recv` CRLF splitting; send errors/disconnection are not propagated as a durable outcome. |
| Native `channels/mattermost.py` | Different identity/recovery opportunities: post IDs exist but the current seen set is volatile. Inspect only to keep this unimplemented counterpart distinct. |
| Native `src/loop.metta` | `getContext` runs before `receive`; new input is detected by changed text versus `&prevmsg`, not by an occurrence ID. Identical genuine messages may therefore be treated as old. |
| `integration/neoclaw/native_loop.py`, `startup_overlay.py`, `controlled/irc.py` | Current controlled launcher substitutes the channel. Existing parser, result construction, accepted turns and context machinery should be reused. |
| `fusion/neoclaw_application.py`, `integration/neoclaw/loop_bridge.py` | Accepted model responses and command-position identities already persist, but inbound channel occurrence admission is a different boundary. Native `send` is not an adopted operation here. |
| `fusion/neoclaw_evidence.py` | Current S04 source hook obtains exact scripted inputs from configuration keyed by slot. A real input must not be reconstructed from that fixture schedule. |
| `fusion/neoclaw_priority.py` | Retained global context has an identity before a tool command exists. Preserve it when integrating input waiting/replay. |
| `fusion/messaging.py`, `ports.py`, `contracts.py`, `responses.py`, `policy.py` | Existing ref-based mailbox acceptance, polling, acknowledgment and current principal/route checks. Trusted CompletionDelivery is not a general channel ingress port. |
| `fusion/neoclaw_transport.py`, current service/host scripts | Certificate-verified loopback HTTPS, descriptor binding and no fallback already exist; reuse mechanisms without pretending the S01 operation allowlist already admits channel traffic. |

Reproduce the legacy single-message rendering, two-message buffering and send
presentation on disposable inputs. Record intentional changes rather than calling
new safety/recovery behavior universally identical to the legacy channel.

## 4. Real channel prerequisite and isolation

Use an existing authorized local IRC server when suitable, or obtain a pinned
real implementation such as ngIRCd for a disposable test deployment. Do not write
a fake IRC daemon and count it as the real server gate. Record server version,
source or image digest, build/package inputs and generated configuration.

Bind test endpoints locally or inside a verified isolated network namespace. No
server federation, public listener, public network connection, default native
channel, organizational credentials or existing user data. Do not modify host-wide
firewall rules. Verify actual listeners and allowed connectivity; a configured
hostname alone is not isolation. Clean up only the generated processes/resources.

Run a real independent peer process through the server for ingress and outbound
observation. It must not write the bridge, mailbox or application journals, inject
input through a test-only callback, or provide expected answers to the consumer.
A scripted peer is a labelled test actor; the server and socket transport are real.

Both local and HTTPS mailbox modes must use the real channel and actual native
loop. HTTPS mode uses current certificate verification, caller/provider filesystem
isolation and distinct credentials. The native application must not open the
mailbox provider's files or own the bridge's IRC connection. No stdio-only pass.
The IRC leg may use explicitly declared isolated test TCP; do not imply that its
traffic is TLS-protected because the separate Fusion leg uses HTTPS.

Missing executable/source/permission or safe isolation is BLOCKED. An executed
incorrect delivery is FAIL. A real-server observation timeout is explicit and
cannot be converted to a positive channel pass. Complete useful independent work
when blocked, but do not claim complete S06 without the real channel gates.

## 5. Responsibilities and narrow contracts

| Boundary | Owns / does | Must not do |
|---|---|---|
| IRC bridge | Connection/session identity, bounded frame parsing, accepted transport occurrences, relay progress, outbound effect reservations and observations | Interpret beliefs, generate model responses, own Omega turns or impersonate an external sender as a Fusion principal |
| AtomStorage | Immutable scoped channel-envelope/payload records | Own delivery state or decide channel routes |
| Messaging | Durable ref-based acceptance, delivery order within the declared route, repeat polling and acknowledgment | Claim that a human/IRC recipient received the message, execute tools or parse IRC |
| Native application | Accepted input occurrence/batch, its assignment to native processing, model-command occurrences, durable result/context handoff | Poll foreign SQL or equate text equality with occurrence identity |
| Optional existing local C1 hook | Record the actual observed input and source linkage when that composition requires it | Automatically treat message text, sender name or a receipt as true/independent evidence |
| Existing C2/Attention | Their existing local state and policy | Become channel queues or export their private state |

A journal for transport progress is not another mailbox implementation. Reuse the
existing Messaging owner for application delivery and only the smallest bridge
state needed to cross a socket boundary. No new general-purpose job framework.

Specify a named channel profile and selected application composition before
editing DTOs. Confirm names/versions against the catalogue; do not silently widen
historical `/1`–`/7` applications, M1 mailbox profiles or S01 HTTPS validation.
Fresh journals are permitted; no existing-state migration or seal rewriting.

Reuse the exercised `Messaging.send/poll/ack` operations and scoped AtomRefs.
If status or receipt observation requires a narrow bridge-owned read operation,
define it explicitly. It is not permission for arbitrary raw IRC commands or a
new generic execution service. Keep a trusted completion port trusted.

Channel records must bind their immutable text representation, scope, fixed route,
bridge identity, connection epoch, occurrence ID and locally recorded order/time.
Store external sender/target metadata separately from the authenticated principal.
A timestamp or content hash is not occurrence identity. No secrets in records.

Define closed request/response schemas, exact selections, correlation, authority,
limits, order, replay/conflict semantics and status/error vocabulary. Validate
responses against their specific request/profile. Do not accept any field merely
because it is named `delivered`, `verified` or `sender`.

## 6. Ingress: durable capture, not durable IRC history

Use the native channel path through a narrow checked transport adapter. Fix only
framing and effect reporting necessary for this profile. Retain a bounded byte
buffer across socket reads, parse complete CRLF-delimited messages, handle split
UTF-8 sequences and coalesced frames, and reject oversize/malformed input explicitly.
Do not use lossy decoding as an undocumented normalization. Filter by the exact
configured target and supported message kind before exposure. Own echoes, protocol
notices and malformed traffic must not become new human input or reply loops.

IRC has no usable persistent message identity in the pinned native path. Create a
bridge-owned connection epoch before admitting frames and an ordered event identity
for each complete admitted message. Persist occurrence allocation, body and relay
intent atomically in the bridge's own journal before claiming capture. Replaying
that event uses the same identity; a different received frame with identical text
is a different occurrence. Never deduplicate by text alone.

Explicit sequence:

    complete permitted IRC frame
      -> bridge durable capture + pending relay
      -> AtomStorage immutable envelope under stable key
      -> Messaging accepts its ref under stable key/correlation
      -> bridge records mailbox acceptance
      -> application polls and validates/hydrates the delivery
      -> application durably accepts input and processing assignment
      -> Messaging acknowledgment
      -> native receive/model-input path consumes the retained input

These are separate owner commits. A crash may leave an unreferenced payload but
must not lose a message already accepted under the bridge's capture guarantee.
An ambiguous AtomStorage/Messaging response is replayed or observed through its
port, not treated as absence. Application acknowledgment means responsibility has
transferred to its durable input state, NOT that a model or every later tool has
finished. Do not acknowledge merely because `receive()` returned a string.

A crash/disconnect BEFORE durable capture can lose IRC traffic. Reconnection is
not replayable history. Record a gap/uncertain interval or connection discontinuity;
do not invent missing counts/messages or claim complete upstream recovery. Under
this first profile no cross-reconnect server-ID dedup or history catch-up is claimed.

Backpressure must bound frame buffers, pending bridge records and route queues.
Never overwrite the oldest accepted item, silently concatenate forever or ack/drop
on `OVERLOADED`. Stop admission/pause or disconnect explicitly at capacity, retain
accepted work and report the upstream gap risk. Demonstrate queue draining and
reuse across more than one queue-capacity cumulatively without raising limits.

## 7. Native input identity and processing

The loop's text-comparison rule needs an explicit new-profile adaptation. Preserve
single-message human rendering and escaping where admitted, but determine newness
from a durably accepted input identity. Do not append hidden IDs to visible message
text just to defeat `&prevmsg` comparison. Replayed input is not new; two actual
messages with equal text are both eligible new input.

Prefer one admitted message per receive/processing slot for this bounded profile.
If batching is necessary, freeze an ordered list of message IDs and its rendered
form before acknowledgment. Do not combine whatever happens to be in RAM at retry.
Document the change from the legacy delimiter-concatenation behavior.

Bind a pending input to the existing application iteration/turn lifecycle. Resume
accepted commands before consuming another queued input into the same slot. A crash
before model-response acceptance may repeat model generation; after acceptance,
recover those commands rather than regenerate replacements. Hosted-model billing
and exactly-once generation are not solved in S06. The model remains a declared
fixture for this experiment.

The actual native `receive`, input-selection, parser, `RESULTS/COMMAND_RETURN`,
next-context processing and S05 global-context path must run. A prefilled transcript
or direct `loop_bridge.accept` test cannot pass the native-input gate.

If using S04 source capture in the selected S05-based composition, replace only
its selected scripted-input dependency with an authorized real input envelope.
Keep historical fixture behavior in historical profiles. Use the durable message
identity to avoid recording its replay as another source. A record says the bridge
observed this sender/text; it does not prove an author identity, truth, entailment
or statistical independence. Do not auto-submit evidence or update beliefs.
No retrospective import of channel history is requested.

Keep input wait/polling separate from the original context-preparation and command
deadlines. Repeated empty polls must not refresh accepted work budgets or silently
create fresh identities for unfinished input/context. Bound waits, messages per run
and turns; report pending/no-input/unavailable distinctly. Preserve the existing
conservative deadline behavior, including exhaustion without useful work.

## 8. Egress: explicit acceptance and uncertain external effects

Adopt the native `send(text)` boundary through the existing application occurrence
machinery. Only a configured test route and explicitly approved generated output
are allowed. The model cannot choose recipients, servers, credentials, protocol
commands or arbitrary AtomRefs. Validate content and disclosure before storing it
in remotely placed payload services or calling a remote authorizer.

The first profile admits one bounded IRC message per send. Inspect original
newline escaping/wrapping. Preserve successful bytes on the admitted single-message
domain, and explicitly reject inputs requiring multiple chunks or exceeding UTF-8
wire limits. Do not silently truncate, partially send or normalize away content.
Test Unicode and command/control injection separately. No DCC, file transfer,
private messages to arbitrary users, channel changes or bulk sends.

Proposed sequence:

    actual native send occurrence
      -> exact route/body/profile/authorization/deadline bound durably
      -> AtomStorage payload + Messaging outbound acceptance
      -> bridge polls, validates and durably owns its egress intent
      -> bridge acknowledges mailbox transfer
      -> bridge reserves the original socket-send attempt
      -> one permitted IRC write
      -> persist the observed transport outcome
      -> authorized outcome read/replay; separate test peer observation

`Messaging.ack` here acknowledges transfer to the bridge's durable egress state,
not receipt by the external peer. Expose a profile-specific accepted/pending token
such as `SEND-ACCEPTED` once the relevant durable contract is satisfied. Do not
retain unconditional `SEND-SUCCESS` as a claim of recipient delivery. Document
intentional legacy presentation differences and preserve old profiles unchanged.
Changes to `&lastsend` must also follow the recorded accepted occurrence rather
than silently change state before refusal.

Use a conservative one-attempt external-effect policy for this increment. Reserve
before the socket write; replay never creates a second external send. A crash after
reservation but before/after the write can leave `unknown` with a spent reservation.
Do not refund, retime, silently resend, mark failure as definitely not sent, or use
a fresh operation ID to hide uncertainty. An intentional new `send` is distinct.
Disconnected work not yet reserved can remain pending within its original bound;
expiry forbids a new attempt. Observation of existing receipts remains possible
without authorizing another effect.

Keep durable acceptance, socket-write return, known rejection, unknown transport
outcome and test-peer receipt as independent observations. A socket write or absence
of an error is not a recipient acknowledgment. The peer's test log is verification
evidence, not a fabricated provider receipt or an unimplemented ACK protocol.
The profile does not promise eventual delivery across ambiguous sends or exactly-once
IRC delivery. Do not introduce IRCv3 extensions/history or a new recipient ACK
protocol merely to erase this bounded limitation.

## 9. Authority, privacy and placement

Authenticate bridge and Omega principals independently to the module service.
Use route-specific ingress, poll/ack, payload and egress permissions. Principal
identity comes from current trusted transport/context, not nicknames or fields in
incoming text. Bind session, route, scope and provider selection on every replay.
Credential rotation for the same principal is distinct from substitution by a
different otherwise-authorized principal.

On the isolated server, a displayed nick is transport attribution, not a verified
human identity. The bridge is authorized to record a permitted observation from
that test channel; it cannot grant that nick the bridge's or Omega's authority.
Do not let text saying 'admin' or changing a nick affect internal scope/permissions.
If stronger server-authenticated identity is actually used, pin and test it rather
than assuming it from the nickname or connection password.

Keep C1/C2, Attention, private context, user history and private vectors local.
Only the generated channel envelope and separately approved generated egress may
enter the selected channel-storage/mailbox scope. Returning input through a real
channel does not permit exporting private belief/context output. Test private
canaries and identifying derivatives in messages, payload stores, RPC bodies and
normal diagnostics. Do not claim generic safe declassification of arbitrary
model output: this experiment uses a narrow explicit output policy.

The bridge and network mailbox provider cannot inspect private application,
evidence, priority or model stores. In HTTPS mode the native caller cannot access
provider journals, and cannot bypass Messaging by connecting directly to the IRC
server or using the old text buffer. Test the process/filesystem/network boundary
where supported. No local channel fallback on RPC failure; no fabricated input.

Received text remains data in the human-message field. Never evaluate it as MeTTa,
shell, a provider URI or a new command. The model-response parser stays at its
existing separate boundary. Test quote/Unicode/control input and fake tool text.
This is not a demonstration of live-model prompt-injection immunity.

## 10. Required integration and recovery evidence

Compare the original single-message channel/rendering path with adapted behavior
on the admitted domain. Demonstrate intentional improvements separately: repeated
text occurrences, bounded queues, durability and honest send status are not legacy
byte-for-byte equivalence claims.

Run the same adapted native application with local and authenticated HTTPS
Messaging/AtomStorage, using fresh generated stores. For both:

1. A separate peer sends real traffic through the isolated server; Omega consumes
   the exact selected message in its actual model-input path.
2. The scripted model selects at least one already adopted operation and later a
   native `send`. Its input must contain the actual delivered message and operation
   result; it cannot obtain incoming text from a scripted source configuration.
3. A peer receives the approved outgoing body through the real server. Tie the
   trace to input ID, accepted turn/command occurrence, payload refs, mailbox
   deliveries, bridge intent and observed transport/peer outcome.
4. Run duplicate text in separate genuine messages and burst input; both equal-text
   messages are consumed as separate occurrences, while internal replay deduplicates.
5. Keep S05 global context and separate local cognition active where exercised; no
   evidence/priority change may arise from mailbox acknowledgment or retries alone.

Required fault cases, with real process termination where claimed:

| Boundary | Required recovery/result |
|---|---|
| After bridge capture, before payload/mailbox acceptance | Same captured occurrence reaches delivery once logically; no new event identity |
| After payload commit or mailbox acceptance, before relay progress | Stable reference/delivery; no duplicate pending message |
| After application input commit, before mailbox ack | Ack replays; input assignment and subsequent accepted commands remain stable |
| After ack, before model/command acceptance | Input is not lost; no new source occurrence; model-generation limitations explicit |
| After command result/context capture | Same logical result is consumed without reexecuting an adopted effect |
| After outbound mailbox acceptance or bridge egress commit | Recover exact intent; mailbox handoff does not imply external delivery |
| Before/after socket write with reservation already persisted | No automatic second send; actual or possible first effect reported honestly |
| Provider outage/full queue/revocation | Accepted state retained, no empty-success/local fallback; bounded recovery and current authority |
| IRC server or bridge reconnect | Internal accepted work recovers; upstream history continuity is explicitly unknown |

Also test split/coalesced frames, bounded incomplete frames, malformed payloads,
wrong route/scope/correlation, mismatched descriptor, conflicting replay bodies,
bad certificates, credential substitution, unauthorized acknowledgment/send,
changed nick, own echo, capacity reuse and expired effect budgets.

An upstream pre-capture message may be lost; test that it is not falsely included
in accepted-delivery guarantees. Report this case distinctly from acknowledged
message loss, which fails the gate. One healthy happy path plus honest ambiguous
recovery is sufficient; do not hide uncertainty to require every kill to yield a
recipient-visible output.

## 11. Regression, source evidence and adoption accounting

Reuse current build, lifecycle, policy and verification tooling. Only introduce a
small S06 entrypoint/configuration where needed. Record exact server/client source,
profile choices, commands, runtime hashes, isolation, startup/readiness/shutdown
and warm-cache assumptions. A fake server or fixture injection cannot pass real
IRC; a remote path cannot pass from an in-process test alone.

Run all affected historical Messaging/storage/acknowledgment tests plus an explicit
impact map for the shared application, native startup, S04 source hook and S05
context. Preserve affected HTTPS embedding/read/write and S01/S02 behavior. Keep
old source-freeze/scope guards; record intentional changes under the new milestone
rather than delete them. Unchanged live web/chain demonstrations need not be rerun
for counts, but remain historical or NOT_RUN in the new report.

Update the existing adoption ledger with precise receive/send/bridge boundaries.
Keep the 105-component historical mapping and 15-family denominator unchanged.
S05 records seven adoption entries and eight native user commands. Do not count
polling, acknowledgment, hydration, TLS and connection management as separate
new user commands or promote the entire Messaging family to complete.

## 12. Gates and deliverables

| Gate | PASS requires |
|---|---|
| BASELINE_SOURCE | Reconciled S05 bytes, pinned new server dependency and impact-selected baseline/regressions |
| REAL_CHANNEL | Actual isolated IRC server plus independent socket peer; no production-network access |
| CONTRACT_IDENTITY | Closed route/envelope/receipt profile; external attribution separate from internal authority; occurrence-based input |
| INGRESS_DURABILITY | Capture-to-mailbox-to-application/ack recovery, explicit pre-capture gap and bounded capacity reuse |
| NATIVE_CONSUMPTION | Real receive/new-input/model-input/command/next-context path; equal-text events do not disappear |
| EGRESS_SEMANTICS | Native send acceptance, real peer receipt on healthy path, bounded unknown-send behavior with no hidden resend |
| LOCAL_HTTPS | Same application against local and authenticated isolated HTTPS mailbox/payload placement; no file/socket bypass |
| RECOVERY_BUDGETS | Real kills preserve identities, original deadlines, source linkage and spent reservations across independent commits |
| AUTH_PRIVACY | Live permissions, route/principal/descriptor binding, private canaries and untrusted-text treatment |
| COMPAT_REPRO | Supported fresh-journal operator recipe, old profiles and affected consumers preserved, exact test/evidence classification |
| SCOPE_LEDGER | Only bounded IRC S06; no whole-Omega claim, private-state movement, second channel, migration or chain |

Deliver one S06 report, decisions/contracts updates, source and gate manifests,
same-message trace, native integration and focused fault tests, and reproducible
operator commands. Include remaining volatile/unconfirmed boundaries and exact
test units: distinct methods versus repeated runs and parameterized scenarios.
Preserve failed development runs and corrections rather than presenting a passing
union as a single uninterrupted run.

Full S06 requires the actual local and HTTPS native channel gates. Missing inputs
are BLOCKED, incorrect executed behavior FAIL, optional work NOT_RUN. All nodes
and generated transport processes must be stopped after the run. No real user
messages, keys, tokens or private cognitive journals belong in published evidence.

**Then stop.** A defensible successful claim is: the controlled native Omega
consumes real isolated-channel messages through durable module interfaces and
submits bounded replies through an independently owned channel bridge, with
recoverable internal handoff and explicitly limited external delivery guarantees.
It is not full live Omega, durable IRC history, remote private cognition,
exactly-once messaging, or a production communication deployment.

## Review references

Implementation claims above use the exact publication/native pins. The IRC choice,
new receipt semantics, admitted single-message domain and gates are proposals.
The original October 15 Kevin/Kabir discussion (00:13:36–00:16:54) motivates channel
interfaces and asynchronous handoff; AGI Benchmarks (00:04:11 and 00:11:14–00:12:40)
motivates inter-agent communication and separate state owners. Neither selected
IRC, a channel server, or this concrete receipt policy.

```text
https://github.com/machieke/fusion-module-interfaces/tree/c9c6e7985c8214feeedc78686f475efb3ad40625
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/c9c6e7985c8214feeedc78686f475efb3ad40625/docs/omega-adoption/mettaclaw-neoclaw/s05.md
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/c9c6e7985c8214feeedc78686f475efb3ad40625/docs/omega-adoption/mettaclaw-neoclaw/seam-contracts.md
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/c9c6e7985c8214feeedc78686f475efb3ad40625/fusion/messaging.py
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/c9c6e7985c8214feeedc78686f475efb3ad40625/integration/neoclaw/native_loop.py
https://raw.githubusercontent.com/patham9/mettaclaw/2af37c3fec18613de54ca42fde2382a9087d4524/src/channels.metta
https://raw.githubusercontent.com/patham9/mettaclaw/2af37c3fec18613de54ca42fde2382a9087d4524/channels/irc.py
https://raw.githubusercontent.com/patham9/mettaclaw/2af37c3fec18613de54ca42fde2382a9087d4524/src/loop.metta
https://www.rfc-editor.org/rfc/rfc2812.html#section-2.3
https://www.rfc-editor.org/rfc/rfc2812.html#section-3.3.1
https://github.com/ngircd/ngircd
```
