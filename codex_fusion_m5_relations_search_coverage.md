# Codex handoff — M5: Relations and Search projection coverage

## 1. Objective and stop boundary

Continue the existing `machieke/fusion-module-interfaces` repository from M4 evidence HEAD
`05b1c52cfa6ced6e263700753e82ad6038a3b0dd` (tested implementation:
`55ed5402391ab6ed14f8ab20e1eea4c85d8be955`), or record the exact descendant and relevant
changes. Read applicable `AGENTS.md`, the original brief, current contracts, ADRs,
inventory and evidence before editing. Preserve unrelated work and dependency pins.

**Objective:** implement the two remaining specification-only module families,
**Relations** and **Search projection**, and demonstrate their integration through
real AtomStorage/DeTTa and an actual authenticated native Hive caller. Increase
functional and integration coverage, not merely test counts or line coverage.

The decisive new capability is:

> A caller supplies a bounded information request, not the answer references.
> Search discovers matching committed records. Relations exposes their explicitly
> asserted structure. The caller retrieves the connected payloads through AtomStorage.
> Restart, projection lag and index rebuilding preserve the declared semantics.

**Complete M5 only, then stop.** No new PLN rules, inference search, ECAN policies,
LTI, summarization, LLM parsing, embeddings, ontology induction, external search
service, graph database, background scheduler, public API deployment, new chain
operation, or populated-journal migration. Do not replace existing owners or modify
the application-neutral DeTTa core. New narrow feed/maintenance capabilities remain
parts of their existing owners, not additional module families.

This is a proposed engineering increment. It does not establish that the entire
Omega product requirement set is complete or that the meetings selected these exact
query, relation, or persistence profiles.

## 2. Review basis and findings to verify

The reviewer read the following public files at the M4 evidence SHA. The repository
suites and private Hive dependency were **not independently rerun** during this
brief's preparation. Verify these findings against the actual checkout; if a later
commit already implements a capability, reuse and test it instead of duplicating it.

| Source | Relevant baseline finding |
|---|---|
| `docs/module-interfaces/architecture.md` | Relations and Search projection are explicitly specification-only. Relations owns structure; Search is a rebuildable, non-authoritative projection. |
| `fusion/ports.py` | Relations declares `assertRelation`, `getRelation`, `outgoing`, `incoming`. Search declares `query`. Traversal returns bare tuples; query results have a watermark/version/completeness flag, but no continuation or source-incarnation binding. |
| `fusion/ports.py`, `fusion/atoms.py` | AtomStorage supports create/get/getMany/availability. It does not expose committed-record enumeration or a replayable feed from which a generic index can be rebuilt. |
| `fusion/private.py` | Existing private composition enforces local placement and live scope authority. Do not make recording/retrieval require a PLN runtime. |
| `fusion/registry.py`, `responses.py`, `policy.py` | Reuse declared selection, response validation and trusted-context authority. Do not select a profile merely by provider name. |
| `integration/hive/`, `docs/module-interfaces/runbook.md` | Reuse the verified native Programs dispatch, operator-owned grants, private receipts, restart harness and source/build recipe. |
| `tests/test_m11.py` and existing private/recovery tests | Reuse independent storage fixtures, hostile port-only proxies and actual process-kill patterns. |
| `scripts/verify_m4.py` | Its historical scope gate compares protected files against a pre-M4 ancestor. An intentional M5 change to ports/atom metadata would fail that milestone-specific check; it is not automatically a behavioral regression. |

Run a baseline before changing implementation. Record exact source/worktree state,
commands, actual results and unavailable prerequisites. Historical M4 passes are
not passes for a new checkout.

The source direction is functional, replaceable interfaces, separate data/index
responsibilities, and integration tests on a working system. The detailed choices
below operationalize that direction; they are not verbatim meeting decisions.

## 3. Ownership and minimum architecture

| Boundary | Responsibility | Forbidden shortcut |
|---|---|---|
| AtomStorage | Authoritative immutable envelopes and scoped commit metadata. | Interpreting relation types, query expressions, truth or attention. |
| Relations | Accepted structural relation records, semantic replay, traversal and its own commit boundary. | Writing beliefs/STI or treating a stored implication as established truth. |
| Search projection | Derived lookup structures, processing checkpoint and query results for a declared corpus. | Becoming the only copy of indexed information or reading foreign owner tables. |
| Projection maintenance | Bounded feed consumption and rebuild through declared source/storage ports. May live in the Search package. | A general event bus, autonomous scheduler or unrestricted scan of runtime files. |
| Hive/lookup consumer | Translate the request, query, traverse and retrieve via declared interfaces. | Direct SQL, provider-specific branches, or receiving an expected-answer map. |

A module is an ownership boundary, not necessarily a separate process or database.
Use persistent local implementations and existing composition. Backend imports stay
in adapters/composition; DTOs and consumers remain backend-independent. Prove that
Relations and Search can run with Hive, PLN, ECAN, C1/C2 and chain runtimes absent.
Do not construct the full cognitive composition merely to obtain storage or authority.

Use private local placement for this new lookup slice. Index entries, query text,
relation endpoints, references, cursors and manifests are private too. Existing
M4 publication remains a separate unchanged generated-data workflow.

## 4. Resolve the executable contracts first

Keep existing module and operation names where their semantics fit. Record explicit
version/profile decisions for the previously specified interfaces and new optional
capabilities. Do not silently reinterpret a tuple as a complete paginated result or
an integer as a universal cross-provider watermark.

### Relations

Specify and test:

- Exact immutable endpoint/reference validation; permitted scope/context; relation
  type/schema identity; ordered roles; directed versus undirected semantics.
- What `outgoing` and `incoming` return. Prefer **relation references**, followed by
  `getRelation` to inspect their endpoints. Do not mix neighbors and relation IDs.
- Deterministic ordering, page limits, a stable committed head and continuation.
  A truncated page must not appear to contain all relations. Bind cursors to the
  query, direction, endpoint, scope, source incarnation and snapshot.
- Idempotency and structural identity. Preferred initial rule: one relation for
  the exact type/schema, direction and ordered immutable roles within its scope.
  A new transport key does not duplicate that structure. Reusing a key with changed
  semantics conflicts. Independent reports about a relationship belong in episodes,
  not additional truth implied by repeated structural assertion.
- A new profile may use fresh stores; preserve historical contracts explicitly.

The old boolean `directed` does not define the direction of arbitrary hyperedges.
Use a small operator-configured, versioned role schema: for example, a directed
`requires` type with `dependent` and `prerequisite` roles, one three-role directed
example, and an undirected association. State which roles count as origins and
which as destinations. For an undirected relation, define symmetric incident
traversal explicitly while preserving stored role order. Do not infer direction
from role-label spelling or silently sort arguments.

Reject unknown schemas, wrong arity, duplicate roles where disallowed, invalid
revisions/digests, and cross-scope endpoints. Define repeated endpoints/self-links
explicitly. Relation-type configuration is not a general ontology or a new registry.

### Search

Implement one useful deterministic **exact-attribute conjunction** profile first,
for explicitly typed structured records. Example request semantics:

```json
{"all": [{"field": "kind", "eq": "task"},
         {"field": "topic", "eq": "retrieval-demo"}]}
```

Use the existing `Query.expression` only with a bounded, versioned parser, or an
explicitly revised typed DTO. Accept only allowlisted fields/operators and scalar
value types. Reject unknown syntax and excessive size/depth. No `eval`, arbitrary
SQL, regex execution, embeddings or external model calls. Define exact case,
Unicode and missing-field behavior; default to exact values, not guessed semantic
normalization. A profile name such as `exact-attributes/1` is a proposal to reconcile
with the existing catalogue, not a pre-existing contract.

A query result must identify its corpus/source, processed watermark, extraction
profile/version, projection generation, deterministic result order, completeness
and continuation when truncated. Separate these statements:

1. All matching records at processed source prefix W are represented.
2. All matches at W fit in the returned page.
3. W meets the caller's requested minimum freshness.
4. W equals an actually observed source head H, if that comparison is available.

They are not one global completeness claim. At W below the required minimum,
return an explicit not-ready/unavailable outcome; never a successful empty answer.
For allowed stale reads, describe completeness **at W**, not at an unknown current
head. Label any source-head observation by when/how it was obtained.

Search and Relations have independent snapshot/head identities. Record both when
a lookup traverses them; an atom-feed watermark is not a Relations, episode or
belief commit watermark. Do not advertise a globally atomic knowledge snapshot.

Capture a fixed W for pagination; later ingestion must not silently change that
page sequence. Reject a cursor used with another expression, principal/scope,
source, or rebuild generation. A legitimate zero-match result at a sufficient
watermark is distinct from lag, missing source, failed authorization or corruption.

## 5. Relations: persistent implementation and recovery

Implement all four declared logical operations, including actual traversal. Use
AtomStorage for immutable relation envelopes and a Relations-owned authoritative
record of which assertions committed. Traversal must depend on accepted relations,
not every atom with a relation-looking content type.

Use separate commits and stable replay:

```text
validate current authority and endpoint references
  -> persist canonical relation envelope through AtomStorage
  -> commit accepted relation, identity/replay record and local adjacency
  -> return the committed relation/receipt
```

A payload stored before the Relations commit is not an accepted assertion. After
interruption, retry the original semantic identity, reuse the persisted envelope,
and produce one accepted relation. Do not advertise cross-owner atomicity. Recheck
current authority before an externally computed result commits or is returned from
cached replay. Distinguish a missing endpoint from temporarily unavailable payloads.

Use bounded input, page, relation and history capacities with explicit backpressure.
Do not silently evict committed relations. Deletion/retraction is out of scope.

Exercise the same Relations consumer with real DeTTa-backed AtomStorage and the
independent storage fixture. A hostile dependency proxy must expose only declared
operations. This is storage substitution beneath Relations, not proof of a second
independent Relations implementation; report that distinction.

## 6. Search needs an authoritative replayable input

Do not build an index from a test's in-memory list or another owner's SQLite tables.
Inspect existing authorized source capabilities first. If no suitable committed
record feed exists, add the smallest **optional AtomStorage-owned read capability**
for the new fresh-store profile. Suggested logical operations are `head(scope)` and
`readCommits(scope, after, through, limit)`; reconcile exact names with the repository.

The feed must have:

- A durable source-incarnation identity, scope and monotonically ordered committed
  sequence. The same number in two unrelated stores is not the same watermark.
- Immutable reference and content-type metadata sufficient to resolve bytes through
  AtomStorage. Its metadata remains application-neutral.
- Atom acceptance and its feed entry in the **same atom-owner commit**. Stable-key
  retries return the same atom and do not append a second logical change.
- Snapshot-bound, bounded enumeration and continuation. Restart cannot lose an
  acknowledged entry or make sequence gaps appear consumed.
- Current trusted read authority. Indexer privilege does not authorize another
  query caller to discover the indexed references.

This is not a change to DeTTa, a global event bus, or a requirement that old stores
support enumeration. Fresh feed-enabled stores may be required. Old profiles and
journals must retain their old behavior; do not synthesize historical order or
silently backfill a populated user store. Validate the new source capability on
both real AtomStorage and an explicitly labelled independent source/storage fixture.

### Corpus and extraction boundary

For this increment, index explicitly typed **knowledge records** whose immutable
bytes contain bounded fields such as `kind`, `topic` and `label`. Store authoritative
fields in the atoms; query-time metadata supplied by a caller is not authoritative.

The corpus is the records eligible under the declared content-type/extraction
profile within one source/scope, not every file or every fact known to Hive.
Process the source prefix in order. Non-enrolled content types may have an explicit
ignored outcome; their treatment must be deterministic and tested.

Do not index raw episode histories, belief snapshots, attention state, or relation
payloads merely because they occur in the atom feed. In particular, a relation atom
may precede its separate Relations acceptance commit: indexing that atom would not
prove that the structural assertion committed. M5 Search discovers knowledge
records; accepted edges are obtained through Relations. Indexing multiple owners'
commit streams is a later profile, not permission to invent a shared global clock.

An unreadable or malformed enrolled record must not be skipped while advancing a
watermark advertised as complete. Default to fail-closed progress at that record,
with a precise error. No dead-letter-management framework is requested.

## 7. Persistent projection, lag and rebuild

Implement Search as a rebuildable persistent projection, preferably using existing
local database facilities. Add a narrow trusted maintenance API or operator entry
point for bounded catch-up and rebuild; read-only queries must not hide ingestion
side effects. Maintenance is call-driven, not a background service.

For each batch, resolve authoritative source records through declared ports, derive
the selected exact fields, then commit index changes and their **contiguous**
processed checkpoint in one Search-owned transaction. Replay is harmless. A crash
must not leave the checkpoint ahead of durable indexed records. Handle duplicate,
gapped, reordered and changed source records explicitly; source unavailability
cannot become an empty corpus.

Set finite budgets for bytes/records read, indexing work, query predicates, query
results and pages. Traversal also has a visited set and hop/result limits in the
consumer; do not add unbounded graph walking to Relations or Search.

### Rebuild acceptance

On disposable generated stores, remove only the derived projection and rebuild it
through the declared feed plus AtomStorage. Do not copy the prior index, recover
from expected test answers, reseed the authoritative corpus, or modify beliefs/STI.

Capture the source head for the rebuild. Resume bounded rebuild batches after
restart. For this increment it is acceptable to make queries explicitly unavailable
while rebuilding; live blue/green replacement is not required. Never present a
partially rebuilt index as current and complete. After activation, return the same
logical results for the same source prefix. Old-generation cursors fail explicitly.
Document retention/capacity limits and behavior if the source can no longer replay
an earlier range.

### Independent Search provider

Add one independently implemented same-profile Search fixture, for example a bounded
atomic-file projection with exact-filter evaluation. It may share DTO validators,
but not inherit the primary provider, use its SQL/private helpers, or invoke it to
compute answers. It must honor the advertised persistence and watermark semantics.

Run the unchanged lookup consumer on the two Search providers against the same
immutable corpus and source prefix. Compare logical references, ordering,
completeness, pagination and required freshness. Provider identity and rebuild
generation may differ where explicitly permitted. Selecting the provider changes
only composition. This proves same-profile substitution, not embedding quality or
hot migration of populated state.

## 8. One real native Hive lookup workflow

Reuse the verified authenticated Programs mechanism. A narrowly named sibling action
such as `fusion-lookup` is acceptable; do not replace existing Hive services or add
a new agent framework. Use operator-owned scope/provider configuration and the
existing native principal/swarm checks. No caller-supplied credentials, backend
paths, query SQL, schema registrations or provider URLs.

Use a generated corpus with multiple matching records, same-topic wrong-kind and
same-kind wrong-topic distractors, unrelated relations and another private scope.
Include more matches than one chosen page limit and more source commits than one
catch-up batch. Do not increase existing limits merely to make the example pass.

The supported demonstration is:

```text
Writer/setup process, using declared ports:
  create structured task/prerequisite records through real AtomStorage/DeTTa
  -> assert typed requires/association relations
  -> record a source-head freshness barrier
  -> perform bounded projection catch-up
  -> exit

Fresh authenticated native Hive caller:
  query by kind/topic and the declared freshness requirement
  -> receive discovered record references, not supplied answer IDs
  -> outgoing/getRelation to discover linked prerequisites
  -> incoming to verify the corresponding reverse incidence
  -> get/getMany to retrieve and validate connected payload bytes
  -> retain an authorized private result and return a privacy-safe native receipt
```

The request may identify its corpus, query attributes and known freshness barrier.
It must not include answer atom IDs, expected neighbor IDs, a precomputed workset,
a query-token-to-answer dictionary or the seeding process's result manifest. The
harness may keep a separate oracle for assertions; the lookup consumer cannot read
it. Prove this by using a new process, changing generated IDs/insertion order, and
running positive and no-match queries. Check that required Relations/Search calls
actually occur, not just that helpers exist.

Then append a new matching authoritative record. Before catch-up, a strict query
requiring the new source head must report not-ready, not no-match. After catch-up,
it must discover the record. Restart the caller and providers, rebuild the index,
and repeat the same logical query with valid new-generation paging.

Keep full private payloads, relation graphs, query strings and identifying hashes
out of normal public receipts and checked-in traces. Tests must validate detailed
results through the authorized private boundary, not infer retrieval correctness
from a successful status/count alone. A generated private canary and its identifying
derivatives must not reach shared bindings, M4 approval/deploy bytes or public logs.

This proves structured retrieval and relation use, not semantic understanding,
autonomous planning, or cognition executing on chain. No new numerical support,
evidence weight, inference attempt or attention credit is created by a lookup.

## 9. Acceptance tests: behavior, not numerical quotas

Map each new advertised operation to positive, negative, authorization, response-
binding and relevant recovery evidence. Required scenarios include:

| Area | Required assertions |
|---|---|
| Relations semantics | Binary and three-role records preserve order and schema; directed/reversed and undirected traversal behave as declared; returned refs resolve to committed relations. |
| Relations identity | Same-key same-body replay is stable; changed-body conflicts; a fresh key cannot duplicate identical structural state under the selected semantics. |
| Boundaries | Wrong scope, altered digest/revision, missing/unavailable endpoints, invalid roles and unknown profiles fail explicitly; current revocation applies to cached replay. |
| Traversal completeness | Multiple pages at a fixed head have no duplicates/omissions; concurrent appends do not alter that snapshot; malformed/cross-query cursors fail. |
| Query semantics | Exact single/conjoined predicates, distractors, zero matches, missing fields, malformed expressions, excessive inputs and deterministic order. |
| Freshness | Behind requested watermark is not-ready; allowed stale results are labelled at their prefix; another source incarnation's watermark is refused. |
| Projection integrity | No skipped gaps, forged reference metadata, changed replay entries or checkpoint advancement past failed eligible records. |
| Rebuild | Delete derived index only; reconstruct identical results from authoritative sources; partial rebuild/cursor generation is explicit. |
| Substitution | Same consumer on real/fixture storage for Relations and independent same-profile Search providers; hostile proxies reject private helper access. |
| Native integration | Actual authenticated Hive lookup uses real DeTTa and both new providers; the consumer is not given answer refs. |
| Privacy/authority | Unauthorized search cannot disclose reference existence, counts, cursors or private content; revocation before reads/continuation/replay fails closed. |
| No cognitive effects | Lookup/rebuild leave episode contributions, belief snapshots, attention and inference budgets unchanged. |

Add actual process-kill cases at least at:

1. Atom/feed commit before the caller receives the write response.
2. Relation payload persistence before Relations acceptance commits.
3. Relations acceptance commit before the caller receives its response.
4. Index writes before the matching checkpoint transaction commits.
5. Index/checkpoint commit before catch-up acknowledgment.
6. An interrupted rebuild and a native caller interruption around a paged lookup.

Use deterministic failpoints, not timing sleeps. Reopen intact generated files and
verify durable identities, source prefixes and returned content through public
owner ports. Label response-loss, clock, malformed-source and storage-corruption
fixtures separately from real SIGKILL. Do not claim power-loss or distributed
failover from same-host process tests.

## 10. Preserve regression evidence without freezing future development

Run applicable M1–M4 behavioral regression suites against the final M5 source,
including the existing real chain suite when its supported isolated prerequisites
are available. No new chain workload or new dependency rebaseline is required.

Do not run the historical M4 protected-file comparison against intentional M5
changes and call that proof that M5 regressed. Equally, do not delete that guard,
hard-code it green or rewrite historical M4 evidence. Preserve the historical
verifier and use an explicit M5 regression entrypoint with its own reviewed source-
scope rules, reusing the existing behavioral tests and classifying results anew.

Keep the old wire/profile behavior, source identity guards, closure semantics,
private/shared routing, signed-deploy replay and conservative inference budgets.
New fresh-store feed/index profiles do not authorize migration or opening existing
journals under a different descriptor. Rebuild of a disposable derived index is
not migration of authoritative state.

A missing native/chain prerequisite must remain BLOCKED or NOT_RUN as appropriate,
not a fixture substitute. Independent Relations/Search gates can still pass, but
unrun regressions prohibit an unqualified claim that all existing integrations
were revalidated. Report new-feature completion and regression verification
separately if the latter is incomplete.

## 11. Measurable coverage and deliverables

Create a machine-readable capability ledger and a short human-readable matrix.
For each logical operation record: module, contract/profile, implementation,
consumer, positive/negative/recovery tests, real versus fixture dependencies,
command/run evidence, result and remaining unsupported semantics.

At minimum inventory the five original operations individually:
`Relations.assertRelation`, `Relations.getRelation`, `Relations.outgoing`,
`Relations.incoming`, and `Search.query`. Add every new advertised feed, paging and
maintenance operation; do not hide those additions outside the coverage denominator.

Report separately:

- **Module-family representation:** baseline inventory 13/15; potentially 15/15
  only after both new bounded families are implemented and evidenced. This is not
  100% of Omega requirements or production functionality.
- **Operation coverage:** counts of advertised operations with implementation and
  executed integration evidence, with explicit partial/missing/unassessed rows.
- **Behavioral coverage:** required scenarios passed/failed/blocked/not run, rather
  than treating one happy path as complete behavioral coverage.
- **Diagnostic code coverage:** line/branch figures only if actually measured with
  a documented tool and file scope. Optional; do not invent a percentage or pursue
  an arbitrary threshold at the expense of contract tests.

Do not double-count rerun subsets or count a transport switch as another module.
Do not rename fixtures as real backends. Update the existing inventory only from
executed evidence; preserve the difference between a bounded reference profile and
the larger service family. Maintainers remain unassigned unless explicitly agreed.

Required artifacts within the current repository:

1. Minimal implementation, DTO/profile/validation and composition changes.
2. Focused contract, integration, substitution, rebuild and recovery tests.
3. Existing architecture/ADRs/runbook updates, including the precise indexed corpus.
4. One M5 verification entrypoint with independently selectable fixture, real
   storage, native Hive and legacy-regression gates; one reproducible lookup command.
5. `m5-evidence.md`, a gate manifest, capability ledger and sanitized before/after
   lookup/lag/rebuild trace. Record exact tested SHA and later evidence-only changes.

Use fresh disposable source/test directories for final verification, with obtainable
locked dependencies. State any warm-cache/build-artifact reuse exactly. Never bundle
private upstream code, credentials, real memories or signing keys in evidence.

## 12. Gates and stopping condition

| Gate | PASS requires |
|---|---|
| BASELINE_AND_SCOPE | Exact baseline, verified gaps, explicit profiles and changes limited to this task. |
| RELATIONS_CONTRACT | All four logical operations implemented with schema/order/identity/paging validation. |
| RELATIONS_REAL | Real DeTTa-backed relation persistence/traversal/restart through declared ports. |
| COMMITTED_SOURCE | Authorized replayable enumeration bound to durable source incarnation and atom commits. |
| SEARCH_CONTRACT | Executable exact-query profile; positive/negative/freshness/paging response conformance. |
| SEARCH_REAL_REBUILD | Real-source indexing, visible lag, checkpoint recovery and rebuild without answer reseeding. |
| SUBSTITUTION | Hostile port checks and unchanged consumer across declared independent fixtures/providers. |
| RECOVERY | Actual process-kill evidence for independent owner commits, checkpointing and caller/rebuild progress. |
| AUTH_PRIVACY | Live authorization, no cross-scope metadata leaks, private canaries and no cognitive side effects. |
| HIVE_LOOKUP | Real authenticated native dispatch discovers and retrieves connected knowledge without supplied answer refs. |
| REPRO_AND_LEDGER | Reproducible supported run and accurate operation-level evidence/remaining-gap inventory. |
| LEGACY_REGRESSION | Applicable previous behavioral integrations rerun successfully; unavailable/unrun portions explicit. |

The real-chain rerun belongs to LEGACY_REGRESSION, not to new Search/Relations
functionality. A historical M4 pass stays historical. Complete independent work
when a prerequisite is missing, but report partial verification rather than claim
an all-gates pass.

**Stop after M5.** Do not automatically move to embeddings, a richer reasoner,
state migration, distributed deployment or another module. Finish with changes,
commands, source identities, provider classifications, gate results, exact coverage
counts, supported corpus/query limits and one remaining functional gap.

## Review sources

Pinned source review (not an independently executed run):

- https://raw.githubusercontent.com/machieke/fusion-module-interfaces/05b1c52cfa6ced6e263700753e82ad6038a3b0dd/docs/module-interfaces/architecture.md
- https://raw.githubusercontent.com/machieke/fusion-module-interfaces/05b1c52cfa6ced6e263700753e82ad6038a3b0dd/fusion/ports.py
- https://raw.githubusercontent.com/machieke/fusion-module-interfaces/05b1c52cfa6ced6e263700753e82ad6038a3b0dd/fusion/atoms.py
- https://raw.githubusercontent.com/machieke/fusion-module-interfaces/05b1c52cfa6ced6e263700753e82ad6038a3b0dd/fusion/private.py
- https://raw.githubusercontent.com/machieke/fusion-module-interfaces/05b1c52cfa6ced6e263700753e82ad6038a3b0dd/fusion/registry.py
- https://raw.githubusercontent.com/machieke/fusion-module-interfaces/05b1c52cfa6ced6e263700753e82ad6038a3b0dd/scripts/verify_m4.py
- https://raw.githubusercontent.com/machieke/fusion-module-interfaces/05b1c52cfa6ced6e263700753e82ad6038a3b0dd/docs/module-interfaces/runbook.md
- https://raw.githubusercontent.com/machieke/fusion-module-interfaces/05b1c52cfa6ced6e263700753e82ad6038a3b0dd/docs/module-interfaces/m4-evidence.md

Supplied meeting context:
- Kevin/Kabir, 00:09:06–00:16:54: function-based contracts, search/memory interfaces,
  service calls and delegated execution; 01:04:49–01:07:39: version-independent
  contracts and a working integration prototype.
- AGI Benchmarks, 00:02:28: integration beyond mocks; 00:09:07–00:12:40:
  referencable storage, distinct links and single-owner updates; 00:17:02:
  explicit acceptance criteria and regressions on a working system.
