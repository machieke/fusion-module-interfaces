# S02 contract pass

Recorded before implementation, starting at
`58a5855ea55091c8f15e86d8293e519494bf728d`. Historical S01.1 evidence is preserved.

1. `web_search` / `external-web-search/1` is DelegatedExecution, not the internal
   exact-attribute Search projection. It owns no knowledge, episodes or beliefs.
   A closed two-operation binding shares the existing application, caller,
   execution, outbox and acknowledgment lifecycle. S01 mathematics and profiles
   remain unchanged.
2. `controlled-native-loop/2` and `neoclaw-tools/2` require fresh application and
   execution journals. Version 1 remains readable under its original composition.
   Version 2 stores tagged operation intents and binds both descriptor selections.
   Native `search` accepts one query and fixes max_results=10. S01 and S02 may run
   in separate turns; mixed adopted-operation batches are rejected before effects.
3. Queries are exact UTF-8, nonblank, at most 2048 bytes, without Unicode control,
   surrogate or format characters. A trusted exact query allowlist is checked at
   application admission and provider dispatch/release. No history is exported.
4. Select DDGS 9.16.0 with DuckDuckGo HTML, POST to exactly
   `https://html.duckduckgo.com/html/`, page 1, no proxy, no redirects, one selected
   backend and one SDK invocation per occurrence. This is a new SDK selection;
   the upstream repository did not pin its historical deployment. The initial
   Brave compatibility probe received 429 and was not retried. A separate,
   pre-admission DuckDuckGo compatibility probe succeeded. No admitted job may
   switch backends. No result links are fetched.
5. The original pinned `channels/websearch.py:search_` executes in an isolated SDK
   subprocess. Operator-owned dependency injection fixes SDK configuration; no
   arbitrary execution/endpoint interface is exposed. The SDK issues one engine
   request. Primp 2.0.1 has a bounded protocol-NACK retry policy (up to two extra
   transmissions); its Python API has no retry switch. SDK invocations and observed
   HTTP entry calls are counted separately; wire transmissions are not measured.
   A supervised process deadline bounds startup, query and collection. Killing a
   process cannot recall a transmitted query. The URL guard is at the SDK boundary,
   not an OS firewall or an exactly-once upstream guarantee.
6. Execution commits its attempt before I/O, then selects and commits the first
   validated observation before AtomStorage publication. The canonical captured
   bytes include identity, SDK/backend identity, original query, ordered items,
   observation/capture timestamps and rendering. Recovery after capture does not
   query or regenerate metadata. A pre-capture crash spends the sole attempt and
   can permanently lose a response. Independent owner commits remain independent.
7. Title/url/snippet byte bounds are 1024/2048/8192; excess is rejected, not silently
   truncated. Total result is at most 32768 bytes; at most requested top-k items,
   explicitly non-exhaustive. Unknown upstream version is null. Control characters
   in result text are escaped in the compatibility rendering; Unicode and ordinary
   formatting are retained. Native Python string values carry the result; no
   result is parsed/evaluated as MeTTa source. Links and instructions are untrusted
   data. This does not claim a live model is immune to prompt injection.
8. Empty successful SDK rows, rate limiting, denial, outage, timeout, malformed
   output and spent ambiguous attempts remain distinct. DDGS's ambiguous
   `No results found` exception is a failure, not evidence of successful emptiness.
   Ordinary recorded rows retain the upstream title/snippet rendering; URLs stay
   in structured results. Exceptions no longer masquerade as successful empty
   strings. Closure after capture may finish past the original deadline; new I/O
   may not. Neither reservations nor deadlines reset on replay.

Authoritative SDK references: [DDGS package](https://pypi.org/project/ddgs/9.16.0/),
[DDGS source](https://github.com/deedy5/ddgs),
[Primp retry source](https://github.com/deedy5/primp/blob/cf29cd94f339c1a69ec7f271f532f0f2411aa06e/crates/primp/src/retry.rs).
The reproducible lock and runtime manifest pin the actual inspected distribution.
