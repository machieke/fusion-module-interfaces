# Codex handoff — S02: adopt external web search through the existing Omega module interfaces

## 1. Objective and stop boundary

Continue `machieke/fusion-module-interfaces` from published commit
`58a5855ea55091c8f15e86d8293e519494bf728d`, or record the exact descendant and
relevant changes. Read applicable `AGENTS.md`, the MeTTaClaw mapping packet,
S01/S01.1 contracts, implementation, source manifests and evidence before editing.
Preserve unrelated working trees, private upstream state and historical reports.

**Objective:** adopt the existing MeTTaClaw `search <query>` command as a second,
named operation behind selectable local and authenticated same-host HTTPS
providers. Reuse S01.1's actual native-loop dispatch, durable command-occurrence
identity and recoverable next-context handoff. Exercise the real external-search
implementation, not just a replacement fixture returning search-shaped data.

This is S02, not S01.2 and not a new Fusion family. External web search is a
**DelegatedExecution operation**, not Fusion's Search projection over its owned
knowledge corpus. Use the mapping packet's proposed `external-web-search/1` and
`web_search` terminology, reconciling those names with the actual checkout.

**Stop after S02.** No internal semantic-memory adoption, embeddings, Chroma
migration, web-page fetching/crawling, automatic link following, arbitrary remote
Python/MeTTa/shell evaluation, broader NAL, new cognition, general scheduler,
public service, genuine multi-host deployment, chain work or populated-journal
migration. Do not repair the whole live Omega stack to complete this operation.

The model/channel/unused-memory fixtures can remain explicit. A **live external
web-search call** through the real loop and HTTPS provider is required for full
S02 completion. Full default Omega startup and live hosted-model/channel gates
remain separate. A provider/network prerequisite failure permits useful partial
work, not a fixture-backed claim of live adoption.

## 2. Review basis and source ledger

The reviewer inspected the published S01.1 commit patch, source, tests and checked-in
evidence, and the pinned upstream search/skill/channel source. The reviewer did
not execute the native suites, start Omega, or independently verify every recorded
hash against the committed tree. Recheck findings against your actual checkout.

The S01.1 report records 296 passing test methods: 32 historical S01, 9 new
application fixtures, 11 new controlled native-loop methods, and 244 other
regressions (156 core, 46 native-provider, 42 historical Hive). Parameterized kill
cases and repeated runs are not additional distinct test methods.

Its source-state manifest records tested working-tree bytes based on
`64d2d1583376f37811d37cb7f2557145690b3b00`, and says it was uncommitted when recorded.
The subsequent public commit is `58a5855...`. Verify that relationship against
recorded hashes, and add a short provenance note. Do not rewrite historical test
execution as a clean-commit run or require another milestone for this metadata.

| Source | Purpose |
|---|---|
| `docs/omega-adoption/mettaclaw-neoclaw/{README,remote-placement,seam-contracts,command-map}.md` | Mapping basis; S02 is already the second-ranked candidate; distinguish old mapping narrative from adoption addenda. |
| `docs/omega-adoption/mettaclaw-neoclaw/s01_1.md`, `evidence/s01_1/{verification,source-state}.json` | Exact tested inputs, controlled composition and scoped guarantees. |
| `fusion/neoclaw_application.py` | Session, accepted native batch, ordered command positions, result projection and bounded recovery. Currently recognizes only S01 and stores `premises`. |
| `fusion/{neoclaw_client,neoclaw_contracts,neoclaw_transport,neoclaw}.py` | Existing validated calls, owner commits, result capture, outbox, current authority and budgets; several shapes are S01-specific. |
| `integration/neoclaw/{native_loop,startup_overlay,loop_bridge,neoclaw_bridge}.py` | Checked native entrypoint, dispatch hooks and typed failure handling. |
| `integration/neoclaw/{controlled_run,operator,host}.py` | Existing supported operator lifecycle, isolated HTTPS and provider-only work/flush. |
| `integration/neoclaw/test_loop.py`, `tests/test_neoclaw_application.py`, existing S01 tests | Native next-context oracle, invocation identity, authority and recovery regressions. |
| MeTTaClaw `src/channels.metta` | Actual native `search` command calls `websearch.search`. |
| MeTTaClaw `channels/websearch.py` | Original `search_` calls `DDGS.text`; `search` renders title/snippet text and catches exceptions. |
| MeTTaClaw `src/{loop,skills}.metta`, `src/helper.py` | Real parser, skill advertisement and result-to-context behavior. |

Retain these existing pins unless a documented, narrow incompatibility requires a
new dependency profile:

- MeTTaClaw: `2af37c3fec18613de54ca42fde2382a9087d4524`.
- S01 PeTTa: `fea83178af3722666d2948d074591d10a3134f56`.
- S01 SWI source: `e58621a91ab7dd530e1e8185ed518f63d851c414` / 10.0.1.
- S01 embedded Python: recorded CPython 3.12.12 build.
- DeTTa: `272888f264dd2dde18b574cabb53c266b0dac2ec`.

The inspected upstream imports `ddgs` without a package pin. Inspect its actual
installed/obtainable SDK, primary documentation and dependencies; select and lock
one compatible version and its effective backend configuration. Do not describe
that new selection as reproduction of an unknown historical deployed SDK. Leave
Fusion's separate guarded PLN runtime and profiles unchanged.

## 3. Current semantics to preserve or change explicitly

At the pinned upstream source:

```text
native search(query)
    -> Python websearch.search(query, max_results=10)
    -> websearch.search_(query)               # outer max_results is not forwarded
    -> DDGS.text(query, max_results=10)
    -> {title, url, snippet} rows
    -> title/snippet string                   # public wrapper drops URLs
```

The outer wrapper returns an empty string on exceptions. That is not an acceptable
internal success/error distinction for a remote operation. Successful zero results,
upstream failure, rate limiting, invalid output and uncertain/lost completion must
be represented separately. This is an explicit adapter/profile correction, not
unqualified byte-for-byte preservation of all historical behavior.

Prefer reusing the pinned original `search_` helper for the real SDK call, with
source-checked dependency injection or a narrow execution wrapper where necessary
for timeouts and controlled fixtures. Do not implement a second scraping engine.
Retain URLs in the structured persisted result even when a compatibility rendering
only shows titles/snippets. Returned links are data, not permission to fetch them.

## 4. Contract and composition: reuse the lifecycle without pretending S01 is generic

Perform one focused contract pass before implementation. Keep the existing module
owners and exact S01 profile. Add only a closed S02 operation, its argument/result
validators, provider adapter and the minimum shared lifecycle changes needed.

Use a small explicit, trusted operation binding where it avoids duplicating the
whole caller/application/execution state machine. For example, the accepted
application occurrence can bind a tagged operation/profile/argument record instead
of treating every operation as two numerical premises. Exact names follow the
repository. Do not add arbitrary `execute(anything)`, reflection-based imports,
caller-selected validators or an unrestricted plug-in loader.

If journal semantics or stored bindings change, select a new explicit composition
profile with fresh journals. Preserve S01/S01.1 readers, validators, replay and
controlled-loop behavior under their old profiles. Do not silently reinterpret
populated S01 application rows as S02. The same provider, route and authority
bindings must survive restart.

The intended call path is:

```text
Real native loop accepts parsed search command occurrence
  -> application persists session/turn/position, operation and exact arguments
  -> caller persists selected provider, deadline, budgets and request identity
  -> DelegatedExecution durably accepts the named job
  -> provider-only worker reserves an external-call attempt
  -> pinned websearch helper / real DDGS SDK obtains an observation
  -> execution owner durably captures and selects that observation
  -> AtomStorage / real DeTTa persists its validated result bytes
  -> execution owner commits terminal state and completion outbox
  -> Messaging independently accepts completion
  -> caller validates/persists result, acknowledges delivery
  -> application records result; actual native loop builds next context
```

The search adapter owns SDK invocation/normalization, not job admission or another
job journal. Execution owns attempts and selected observations. Storage owns
payloads. Messaging owns deliveries. The caller owns application receipts. No
foreign owner SQL, shared cross-owner transaction or shared mutable filesystem
between caller and network provider is implied.

## 5. Bounded input, output and evidence meaning

Start from the mapping packet's proposed bounds: UTF-8 query at most 2048 bytes,
`max_results` 1–10, total result at most 32768 bytes. The native command initially
fixes `max_results=10`; model text does not select runtime/provider/endpoint,
credentials, retry policy, deadline, scope or permissions. Reject blank/malformed
inputs and unknown fields before admission. Define Unicode/control-character
behavior and record exact accepted query bytes; do not silently rewrite meaning.

The structured result should identify the selected operation/provider/SDK profile,
request/job, validated items (`title`, `url`, `snippet`), observation/capture time,
and explicit truncation/completeness status. Separate SDK implementation identity
from upstream service/backend identity where knowable. Never invent an upstream
version that the service does not report. Define bounded per-field sizes, stable
ordering and encoding; truncate only with explicit metadata, or reject according
to the chosen profile. Do not label top-k results as an exhaustive web corpus.

A stored observation says what this provider returned for this request at that
time. It is not verified knowledge, calibrated truth, a belief update or proof of
web-content accuracy. No C1 event, C2 admission or attention reward is implicit.

Treat titles, snippets and URLs as untrusted content. Construct MeTTa strings and
result projections with safe native values/escaping, never interpolation into
executable source. Do not `sread`/`eval` search results, auto-dispatch embedded
commands, or treat returned instructions as authority. Test quotes, parentheses,
newlines, terminal/control characters, Unicode, fake tool instructions and oversized
fields through the actual native path. This tests data-boundary integrity, not
complete resistance to prompt injection by a live model.

For ordinary bounded successful rows, preserve the existing visible formatting
where safe. Document necessary escaping/error changes under the S02 profile. Test
that rendering with fixed recorded rows using the original wrapper and the new
facade. Do not assert that separately executed live searches must be byte-equal.

## 6. Nondeterministic replay and external effects

This is the principal difference from S01. Repeating a web request may return a
different observation and consumes upstream resources. A request key is not an
upstream idempotency guarantee.

Persist the attempt reservation before invoking the external provider. Bind its
ordinal and request semantics; use the original absolute deadline and durable
per-job attempt limit. Distinguish caller RPC attempts, adapter/SDK invocations,
and actual HTTP requests. Inspect SDK internal retries, backend fallback and
fan-out. Disable or bound them where supported, and disclose the actual bound;
one SDK call is not necessarily one network request.

Use an enforceable remaining-time bound, including SDK startup and result
collection. A supervised subprocess is acceptable when the SDK cannot enforce
the full bound; stop only owned descendants and record cancellation limits.
Do not promise to recall a request already transmitted upstream.

**The first valid observation durably selected by the owner is immutable for the
accepted occurrence.** Persist capture/selection before subsequent publication
steps. On a crash after capture or payload persistence, recover those exact bytes,
time, identity and rendering instead of issuing another search or regenerating
metadata. AtomStorage idempotency keys must not be reused with different candidate
contents. Serialize attempts or provide an equivalent bounded owner-local selection
rule so late/duplicate responses cannot replace the chosen observation.

A crash after external response but before durable capture can lose that
observation. A later attempt may differ and must consume the remaining budget.
A lost reservation can exhaust the budget without results. Choose and document a
conservative default, such as one permitted SDK invocation; any explicitly allowed
retry must stay within the original bound. No automatic local fallback or service
substitution after admission, no new occurrence invented on timeout, and no claim
of exactly-once upstream requests/billing or repeatable live web contents.

Replayed accepted occurrences return their captured observation, even when the web
has changed. An intentional new search with the same query in a later turn/position
gets a distinct occurrence and can observe newer data. No implicit global query
cache or semantic deduplication is introduced.

Record temporary upstream unavailability/rate limiting separately from successful
empty results. Respect service restrictions and backoff; do not rotate proxies,
change providers silently, bypass access controls or loop indefinitely to force a
live PASS. A blocked live gate does not block independent contract tests.

## 7. Privacy, authority and placement

Use only generated, explicitly approved public-information queries in this
increment. Authorization to run a tool is not blanket permission to export a whole
prompt or private history. Allowlist the demonstration queries or bind them to an
explicit local disclosure policy outside model text. No private Omega files,
secrets, contextual histories, content hashes or telemetry enter the query.

Operator composition controls SDK configuration, outbound destinations and any
credentials. Pin the approved search backend(s), constrain egress to those needed
for the inspected implementation, and do not accept proxy/URL/header overrides
from the command. Do not fetch result links or create a generic HTTP endpoint.
Record actual egress assumptions; do not claim an unimplemented network policy.

Reuse authenticated certificate-checked, same-host loopback HTTPS. Provider-side
outbound web access is a separate declared capability; it does not authorize a
publicly listening module service. Keep the current non-loopback refusal and
filesystem isolation. In network tests show that the caller neither imports the
search SDK for execution nor contacts the search backend as a fallback. Provider
journals and secrets are not mounted into caller state.

Recheck current principal/scope/operation/route/descriptor authority on submission,
worker dispatch, result access, cached replay and next-context handoff. Revocation
cannot undo a query already sent externally; it can prevent new calls or release
of a stored result. Use generated canaries and inspect serialized requests,
results, next contexts, diagnostics and published evidence for leaks.

## 8. Actual loop integration and test matrix

Use the existing checked `mettaclaw` launcher, parser and result/context path. Add
the narrow source-checked binding for native `search`, preserving S01 and the
unadopted local commands. Keep model, channels and unused memory substituted at
the same declared boundaries. The scripted model requests search and observes the
actual captured output in its next context; it must not inject the answer.

Demonstrate sequential S01 and S02 calls in the same application session, without
rewriting operator configuration or changing loop business logic for local versus
network placement. Keep one unfinished invocation per reply route. S02-only batch
recovery and separate S01/S02 turns are sufficient; mixed-operation batches may be
explicitly refused if their recovery is not supported. Never replay legacy shell,
file, send or other unadopted effects from a partial batch.

| Required case | Acceptance evidence |
|---|---|
| Original/adapted equivalence | Original native search facade, adapted local and HTTPS paths consume the same recorded SDK rows; defined rendering agrees. This is explicitly fixture evidence. |
| Real local integration | Actual native command/loop uses the pinned real search helper and SDK locally; result reaches next context. |
| Real remote integration | Actual loop -> authenticated isolated HTTPS -> real pinned helper/SDK -> live external search -> real DeTTa -> next context. No caller-side fallback. |
| Changing web observation | Stateful provider fixture returns A then B: replay after durable capture returns A with no new call; a new identical-query occurrence can observe B. |
| Pre-capture interruption | SIGKILL after reservation and after response/before capture; lost/ambiguous attempts stay spent, retries are bounded, no deterministic-output claim. |
| Post-capture recovery | SIGKILL after durable capture or payload persistence/before terminal commit; recover same observation without querying upstream again. |
| Caller/loop handoff | SIGKILL after caller receipt/ack and before native projection/next context; same result and identity, no command regeneration or duplicate fragments. |
| Failures versus empty | Empty successful SDK response is not timeout, rate limiting, malformed output, denial or provider outage. All remain observable with typed status. |
| Authority/isolation | Wrong CA, provider/profile, scope/route, current revocation and stored-result replay fail closed; no query/private-state leak. |
| Adversarial result text | Result strings stay data through parsing, rendering, next context and diagnostics; no injected native/tool execution. |
| Regression/reuse | S01 works unchanged within the new session and historical profiles; existing owner guarantees remain intact; no second application state machine. |

Failure-injection/replay cases should use controlled external-provider responses
rather than hammering a live service. Label that boundary, while keeping real
native-loop, HTTPS, DeTTa and process-kill components real where claimed.

Use a small declared live query set and bounded total live attempts. A successful
live run requires actual external results, not preloaded rows or an SDK import.
Do not require stable item ranks, exact content or cross-run timestamps. Capture
and compare the exact artifact within each run. Once a live result is durably
captured, at least one recovery should verify reuse of that artifact without
another live request. Classify missing packages/permission, runtime failure,
upstream denial and observation timeout accurately.

## 9. Gates, reproduction and reporting

| Gate | PASS condition |
|---|---|
| BASELINE_SOURCE | Record actual starting commit, verify S01.1 hash relationship, run applicable 296-method baseline with exact classifications. |
| S02_CONTRACT | Closed arguments/results, exact operation/profile, explicit legacy differences, SDK pin and current authorization. |
| LIFECYCLE_REUSE | Real loop reuses durable occurrence/receipt machinery for both S01 and S02; no cloned framework, no hidden placement branch in business logic. |
| ORIGINAL_COMPAT | Native original and adapted rendering verified against identical controlled SDK rows, including error changes and escaping. |
| LOCAL_LIVE | Actual local native search helper/SDK reaches external service and result reaches the subsequent real-loop context. |
| HTTPS_LIVE | Same native caller uses real HTTPS, real external provider and real DeTTa under declared isolation; not fixture PASS. |
| OBSERVATION_RECOVERY | Captured result replay and real process kills preserve selected observation, identity, budget and deadline. |
| AUTH_UNTRUSTED_DATA | Live authority, no fallback, scoped disclosure, safe text boundaries and no secret leakage verified. |
| REPRO_SCOPE | Pinned SDK/build recipe, supported bounded operator lifecycle, appropriate old-profile regressions, cache and unrun gates explicit. |

Required real search gate failure means partial delivery, not complete S02. Report
`BLOCKED`, `FAIL`, `TIMEOUT`, `NOT_RUN` and expected-negative passes distinctly;
reuse existing repository vocabulary where compatible. Keep optional full Omega,
live hosted model, live IRC/Mattermost, genuine multi-host, chain, power-loss and
empty-global-cache gates unrun unless separately authorized and actually executed.

Deliver the small implementation, explicit profiles/ADRs, focused fixture and
native/live tests, one bounded operator recipe, `s02.md`, and a machine-readable
gate/source manifest. Reuse the S01 operator startup/readiness/shutdown mechanisms.
Do not terminate unrelated processes or read the user's populated Omega directory.

Update `operation_adoptions` for the exact new `search` capability only when its
required evidence passes. S01 remains one adoption with command and loop evidence;
S02 adds a second operation, not a new family. Keep the historical 105-row mapping
classifications and 15-family reference denominator intact. Do not divide the
adoption count by 15 or by 105 to claim product completion.

Report tests by newly executed methods, parameterized scenarios and historical
regression groups without double counting. Reproduction of code/build inputs does
not imply reproduction of live search results. Preserve development failures,
source-state history, warm-cache qualifications and the committed relationship.

**Then stop at S02.** Success is a second existing Omega command using the same
interfaces and native-loop lifecycle with correctly different external-effect
semantics, not an expanded service catalogue or a full product-readiness claim.

## Primary review sources

Source-relative paths above refer to these immutable public trees. The mapping
scorecard is a design assessment; the S01.1 evidence remains repository-reported.

```text
https://github.com/machieke/fusion-module-interfaces/commit/58a5855ea55091c8f15e86d8293e519494bf728d
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/58a5855ea55091c8f15e86d8293e519494bf728d/evidence/s01_1/verification.json
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/58a5855ea55091c8f15e86d8293e519494bf728d/evidence/s01_1/source-state.json
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/58a5855ea55091c8f15e86d8293e519494bf728d/fusion/neoclaw_application.py
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/58a5855ea55091c8f15e86d8293e519494bf728d/integration/neoclaw/test_loop.py
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/58a5855ea55091c8f15e86d8293e519494bf728d/docs/omega-adoption/mettaclaw-neoclaw/remote-placement.md
https://raw.githubusercontent.com/machieke/fusion-module-interfaces/58a5855ea55091c8f15e86d8293e519494bf728d/docs/omega-adoption/mettaclaw-neoclaw/seam-contracts.md
https://raw.githubusercontent.com/patham9/mettaclaw/2af37c3fec18613de54ca42fde2382a9087d4524/src/channels.metta
https://raw.githubusercontent.com/patham9/mettaclaw/2af37c3fec18613de54ca42fde2382a9087d4524/channels/websearch.py
```
