# M5 Relations and exact Search evidence

M5 is complete at tested implementation
`bfb0ec8856c932dc2bcbc05b8949c957da8d72cd`: **all 12 required gates pass**.
This includes real DeTTa, authenticated native Hive and the existing real isolated
M4 chain regression. No required gate remains blocked, failed or unrun; no final
observation timeout occurred. The resolved intermediate failures are recorded below.
Work stops at M5.

## Exact source and scope

Requested ancestor: `05b1c52cfa6ced6e263700753e82ad6038a3b0dd`.
Starting checkout: `4093301ea6b34bb8de487a4e4d9aae8a9ee6e61d`, whose only
intervening commit updated the M4 presentation/documentation. The sole initially
untracked input was the supplied M5 brief. No applicable AGENTS.md was found.

Before editing, the review findings were reproduced: Relations and Search were
specified without providers, traversal returned bare tuples, and AtomStorage had
no replayable enumeration. The baseline aggregate passed 138 tests. A clean
baseline worktree then passed all ten existing M4 gates, including actual isolated
chain behavior and M1–M3.1 regression. This is a new baseline run, not a copied
historical pass. See [baseline results](../../evidence/m5/baseline/summary.json).

Implementation commit `0cb61d586318034b76f0bb8db853698fcb6de587` adds M5.
Commit `9b0ed3520837e06f7c07824f3e79c60e1aff24a2` fixes verifier environment
composition and adds response-size and rebuild-head rollback guards. Commit
`bfb0ec8856c932dc2bcbc05b8949c957da8d72cd` removes shared query predicate
evaluation from the independent Search fixture and tightens gate classifications.
Final tests run from a fresh detached worktree at that third commit. Later changes are
restricted to evidence and documentation; they do not replace the tested code.

All historical runtime files, dependency locks, source pins, guarded mathematics,
M1–M4 tests and the M4 verifier remain byte-identical. `fusion/ports.py` only appends
new explicit protocols. No cognitive, scheduler, migration or chain operation was
added. The presentation remains the previously delivered M4 presentation.

| Runtime source | Exact revision | M5 role |
|---|---|---|
| Hive | `34b0fb32ab3806e5609fc89bb7535518a35e1aea` | Authenticated native Programs dispatch through the unmodified ASGI application and Supervisor |
| DeTTa / secured-contract-spaces | `272888f264dd2dde18b574cabb53c266b0dac2ec` | Real local opaque bytes, reconstruction and availability |
| PeTTa | `ae66fa8e41dcd5539d614706bd4e5cfb34f9608d` | Native Hive runtime; legacy guarded PLN regression |
| SWI-Prolog | `69775434c8226897626b226aefcc8266499f1e2e` | Version 10.1.14, native runtime |
| Reachability | `dd56f3f053ed90239de5377021a7d3b3fbf424ac` | Unchanged legacy guarded revision/deduction regression only |
| PLN | `4405956947c4b53c7ff01bd565aa3b114bc970a1` | Unchanged legacy mathematics only |
| F1R3node | `9ec1096e10774926ea8e72f0823482f0bf9213e1` | Existing M4 behavioral regression only |

The native entrypoint remains `hive.core.app.create_app`, exercised by
`integration/hive/native_caller.py` with real login and Programs dispatch.
`integration/hive/lookup_program/program.py` supplies the new `fusion-lookup`
Programs 0.1 action. The same pinned sources were obtained into fresh provider
source directories. SWI, virtual environment and DeTTa adapter were freshly built;
download caches were warm. The unchanged M4 Python requirements lock was then
installed for the chain rerun (seven added packages, no removed/replaced packages).
This followed an intermediate collection failure and preceded the final chain
suite. Existing Hive/PLN package versions stayed unchanged. The provider build records
Fusion `4093301`, when that unchanged build recipe ran; its recipe and Rust adapter
bytes are identical at the tested M5 commit. Lookup Python and plugin code are
loaded from the final detached checkout, not from that build marker. The exact pinned M4
node build is reused, with new
route-free network isolation and generated chain state. Empty-cache reproduction,
public networks and power-loss testing were not run.

## Ownership and executable decisions

| Owner / profile | State and behavior | Foreign dependencies |
|---|---|---|
| AtomStorage 1.1.0, `immutable-commit-feed/1` | Immutable envelope metadata and scoped contiguous acceptance sequence commit atomically; durable source incarnation | Opaque storage and live authority |
| Relations 2.0.0, `schema-ordered-relations/2` | Accepted structures, semantic command replay and incidence | AtomStorage ports and live authority |
| Search 2.0.0, `exact-attributes/1` | Derived records, complete processed prefix, generation, rebuild target and query cursors | Scoped commit source, AtomStorage.get and live authority |
| Lookup consumer / native adapter | Private query progress, fixed snapshots and authorized retained result | Declared Search, Relations and AtomStorage ports |

Relation bytes can survive a crash without an accepted assertion. Only the
Relations acceptance ledger drives traversal. Binary `requires/1`, three-role
`transfer/1` and symmetric `association/1` preserve ordered roles. Repeated
endpoints are permitted; each incidence returns a relation once. New transport
keys do not duplicate the same structure. Changed semantic replay conflicts.

Search indexes only `application/fusion-knowledge-v1` canonical UTF-8 JSON with
required `kind`, optional `topic`/`label`, and bounded string values. Queries are
exact conjunctions over those fields, without case folding or Unicode
normalization. Other content types are deterministically excluded. No foreign
owner database, writer answer list, PLN runtime or cognitive composition is needed.

Results distinguish complete prefix W, complete page, requested minimum, and a
head H observed by maintenance. Query does not ingest or obtain a fresh head.
Search and Relations have separate snapshot identities. Rebuild clears only the
derived index, captures a target, changes generation and refuses queries until
that target is complete. The atomic-file Search fixture owns separate persistence
and transitions; it neither inherits nor calls the SQLite provider.

Native commands identify an operator-registered private query plus source barrier.
The mapping has no answer references. A separate writer process creates the corpus
and exits. The native consumer discovers five roots, traverses 15 accepted
relations, verifies reverse incidence and retrieves eight payloads. Tests compare
full authorized private results to an oracle held only by the test process.
No-match, a later sixth match, lag, rebuild, restart and substitution are separate
assertions. Native receipts and checked-in traces contain only safe counts/status.

See [full contracts and bounds](m5-contracts.md),
[ADR-014](decisions.md#adr-014-m5-accepted-structure-and-a-replayable-exact-projection)
and [reproduction commands](runbook.md#m5-private-lookup-reproduction).

## Executed verification

The final M5-specific suites have passed on `bfb0ec8`:

| Suite | Executed units | Classification | Result |
|---|---:|---|---|
| `tests.test_m5`, `tests.test_m5_boundaries` | 18 unittest methods | Fixture inputs and independent substitutes; SQLite owners | PASS |
| `integration.test_m5_real` | 4 unittest methods; 9 deterministic SIGKILL cases within them | Real DeTTa; both Search providers | PASS |
| `integration/hive/test_m5_integration.py` | 7 pytest cases, including 4 native-caller SIGKILL cases | Authenticated actual Hive and real DeTTa | PASS |
| Supplemental populated-state probe | 4 attention/Search configurations | Real DeTTa lookup; pre-existing cognitive state uses explicit guard/refusing fixtures | PASS |
| Supplemental native payload comparison | 4 transitions: initial, catch-up, rebuild, substitution | Real native Hive and DeTTa; independent Search fixture only for substitution | PASS |
| M1–M4 behavioral regression | Existing unchanged suites; aggregate 156 unittest methods includes the 18 new methods | Real providers and separately labelled fixtures | PASS |

There are 13 specifically placed M5 SIGKILL cases across the storage/native suites;
ordinary shutdown/restart calls are not counted as additional crash scenarios.
Final results are recorded in the [gate manifest](../../evidence/m5/manifest.json).
Raw command-log hashes identify the ignored execution artifacts. Published copies
redact workspace paths and have separate hashes in `evidence/m5/checksums.json`.
The machine-readable [capability ledger](m5-capability-ledger.json) resolves each
operation against the final manifest. Independent selectors are `fixtures`,
`storage`, `hive`, and `legacy`; omitted gates stay NOT_RUN.

Development failures retained in the evidence record:

- A real-provider test incorrectly expected a provider name in an availability
  DTO. The declared DTO contains a content hash; the corrected binding assertion
  and all four real-provider methods passed.
- The first clean-checkout verifier attempt failed before real suites because
  it passed `PYTHONPATH` twice. Environment composition was corrected. This was a
  verifier execution failure, not an unavailable runtime or successful gate.
- The intermediate `9b0ed35` chain suite failed during collection because the
  fresh M3 environment lacked `cryptography`. No node or deploy was attempted.
  Installing the unchanged M4 Python lock resolved this prerequisite without
  replacing any existing package; the final chain suite uses that complete recipe.



| Required gate | Result |
|---|---|
| BASELINE_AND_SCOPE | PASS |
| RELATIONS_CONTRACT | PASS |
| RELATIONS_REAL | PASS |
| COMMITTED_SOURCE | PASS |
| SEARCH_CONTRACT | PASS |
| SEARCH_REAL_REBUILD | PASS |
| SUBSTITUTION | PASS |
| RECOVERY | PASS |
| AUTH_PRIVACY | PASS |
| HIVE_LOOKUP | PASS |
| REPRO_AND_LEDGER | PASS |
| LEGACY_REGRESSION | PASS |


The exact top-level command was the M5 verifier with the fresh provider environment,
existing pinned chain build and a new output directory, run from the detached
`bfb0ec8` checkout. [Reproduction metadata](../../evidence/m5/reproduction.json)
records that command, the build/install steps and supplemental probe commands.
The selected suites executed as follows; repeated legacy subsets are not added to
the new-test totals.

| Command/suite | Seconds | Observed result |
|---|---:|---|
| `uv run --python 3.11 --locked python -m unittest -v tests.test_m5 tests.test_m5_boundaries` | 27.434 | 18 methods passed |
| Native Python `-m unittest -v integration.test_m5_real` | 22.088 | 4 methods passed |
| Native Python `-m pytest integration/hive/test_m5_integration.py` | 111.519 | 7 cases passed |
| Unchanged `scripts/verify_m3_1.py` and its M1–M3 prerequisites | 1325.251 | All applicable behavioral suites passed |
| `python -m unittest -v tests.test_m4_chain` | 0.767 | 11 cases passed |
| Native Python under `unshare --user --map-root-user --net`, `-m pytest integration/chain/test_m4.py` | 99.299 | 6 real-chain cases passed |

All six node ports tested from the host refused connections while the node was
ready inside its route-free namespace. No public network was used. Final Fusion,
Hive, DeTTa, PeTTa, Reachability, PLN, SWI and F1R3node source checkouts are clean at
the recorded revisions: [source audit](../../evidence/m5/source-state.json).

The sanitized [lookup trace](../../evidence/m5/traces/lookup-trace-1.json) shows
5 roots / 15 relations / 8 payloads, strict lag refusal, discovery of a sixth root,
rebuild and substitution. A second independently generated corpus repeats it.
[Detailed payload comparison outcomes](../../evidence/m5/native-payload-comparison.json)
confirm exact reference sets and every canonical payload byte before/after catch-up,
rebuild and substitution, without publishing those private values.

## Coverage units

Module-family representation: baseline **13/15**; the two new bounded families
have real integration evidence, giving **15/15 represented families** in the
bounded reference inventory. The separate legacy-regression gate also passes.
This does not measure the completeness of Omega requirements.

Operation denominator: **nine new logical operations**, plus **four inherited
AtomStorage dependency operations**, for **13/13 implemented and integration-exercised operations in this slice**
(**9/9 new operations**). Pagination
extends outgoing/incoming/query; it does not introduce hidden additional methods.
Native dispatch is a consumer, not a sixteenth module family. No line/branch
coverage measurement was performed.

| New operation | Contract and principal integration evidence |
|---|---|
| Relations.assertRelation | Ordered schemas, structural identity, replay, endpoint validation; real payload/acceptance SIGKILL boundaries |
| Relations.getRelation | Accepted record and exact payload binding; orphan/malformed/unavailable rejection; native retrieval |
| Relations.outgoing | Fixed accepted head, multiple pages, direction/ref/principal binding; native discovery |
| Relations.incoming | Symmetric/directed incidence, exact reverse verification, live authority; native discovery |
| Search.query | Exact predicates, zero-match versus lag, page/snapshot/generation binding; real native query |
| AtomStorage.head | Scoped durable incarnation/sequence; source binding and lost-write-ack recovery |
| AtomStorage.readCommits | Bounded contiguous snapshot replay; gaps/duplicates/metadata/anchor rejection |
| Search.catchUp | Real opaque bytes through ports; index/checkpoint atomicity, failed-record/capacity backpressure |
| Search.beginRebuild | Captured target, stable replay receipt, partial unavailability, rollback rejection and restart |

Behavioral coverage uses the brief's **12 scenario groups plus six crash-boundary
groups**, all exercised successfully, not test totals. Each group maps to executable evidence in the final
manifest: relation semantics/identity, boundaries, traversal, exact queries,
freshness, projection integrity, rebuild, substitution, native dispatch,
privacy/authority, no cognitive effects; then atom acknowledgment, relation payload,
relation acceptance, pre-checkpoint, post-checkpoint and rebuild/native paging kills.


## Changed files

The exact implementation diff is listed in
[implementation-changes.json](../../evidence/m5/implementation-changes.json).
The principal changes are:

| Files | Responsibility |
|---|---|
| `fusion/ports.py`, `lookup_contracts.py` | Add explicit new protocols, typed queries, source heads, schema/cursor/response validation and limits |
| `fusion/atom_feed.py`, `relations.py`, `search.py` | Separate authoritative atom/feed, accepted Relations and derived Search owners |
| `fusion/adapters/fixture_feed.py`, `fixture_search.py` | Independent atomic-file contract substitutes; independent Search predicate evaluation |
| `fusion/lookup_composition.py`, `lookup.py` | Descriptor-selected private composition, live authority and bounded port-only lookup |
| `integration/hive/lookup_program/`, `test_m5_integration.py`, `integration/m5_driver.py`, `test_m5_real.py` | Actual native action, exited writer, real DeTTa and deterministic process-kill scenarios |
| `tests/m5_support.py`, `test_m5.py`, `test_m5_boundaries.py` | Generated private corpus, independent oracle, conformance and adversarial boundaries |
| `scripts/verify_m5.py` | Separately selectable new gates and unchanged legacy behavioral suites |
| Architecture/contracts/ADR/runbook/discovery, capability ledger and `evidence/m5/` | Profiles, reproduction, exact sources, safe traces and gate-by-gate evidence |

No human maintainer assignments were made. The documentation/evidence commit also
adds two supplemental verification scripts under `evidence/m5/`; both were executed
against the exact tested runtime. It makes no post-test runtime changes.

## Guarantees and limits

Observed guarantees are local process-restart guarantees with intact storage.
There are independent owner commits, current authorization on reads/replay/commit,
no accepted orphan relation, no skipped failed enrolled record, and deterministic
bounded discovery at explicit snapshots. Fixture corpora/policies, hostile proxies,
malformed responses and deterministic failpoints remain fixtures. Real SIGKILL,
real DeTTa and native Hive are separately identified. Search substitution uses a
fresh derived store under the same profile; existing caller receipts bind their
selected providers and are not migrated.

Limits: 512 atoms per fresh store, 4096 bytes per atom, 128 accepted relations,
256 indexed records, eight records per source/query/maintenance page, one to three
exact string predicates, one-hop lookup, at most eight query pages/32 roots,
128 relations and 64 retrieved records. Capacity refusals retain the prior complete
prefix; there is no eviction or automatic repair. A malformed enrolled record
blocks advancement until an operator addresses the source/profile outside this
increment; it is never silently skipped. Envelope availability/integrity is checked even
for excluded content types. A missing replay range or unavailable required bytes
also stops maintenance; a partial rebuild does not become queryable.

The implementation trusts the authoritative source's immutable contract; it does
not add cryptographic attestations against an arbitrarily compromised owner.
Checkpoint-boundary replays and metadata/content binding are checked. The
independent Search fixture also evaluates predicates itself; a test disables the
primary predicate helper while the fixture answers exact and zero-match queries. Historical
profiles remain explicit and unchanged; fresh-store feed/relation profiles do not
backfill old journals. Deleted derived state can be reconstructed, but there is no
live authoritative-state migration, cross-owner atomic snapshot or distributed
failover guarantee. Existing numeric rules and inference budgets are untouched.
One remaining functional gap is general semantic or transitive search: this
increment provides exact structured retrieval and one-hop relation use only.
