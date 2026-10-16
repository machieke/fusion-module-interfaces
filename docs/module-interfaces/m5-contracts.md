# M5 executable profile decisions

Baseline 4093301ea6b34bb8de487a4e4d9aae8a9ee6e61d is a presentation-only
descendant of 05b1c52. Before implementation, 138 aggregate tests passed; a clean
separate baseline worktree also passed all ten M4 gates, including real isolated
chain and M1–M3.1 behavior. At that baseline, Relations and Search were
specifications and AtomStorage had no committed enumeration.

M5 introduces private local profiles, with fresh stores only. Historical Relations
and Query declarations remain specifications; their tuple/watermark semantics are
not reinterpreted. The new local Relations/Search interfaces are version 2.0.0.
AtomStorage 1.1.0 selects immutable-commit-feed/1, adding head/readCommits without
changing the four original signatures. No DeTTa changes or journal backfill.

Relations owns accepted structure. schema-ordered-relations/2 uses operator-defined
versioned schemas: requires/1 (dependent -> prerequisite), transfer/1 (sender ->
object and recipient), association/1 (symmetric incidence). Roles remain ordered;
repeated endpoints/self-links are allowed and a traversal includes a relation once.
Unknown schemas, duplicate/wrong role labels, wrong direction/arity and foreign
scope or invalid references fail. Exact schema/direction/ordered refs determine one
structural identity per scope, independent of transport keys. Scope ownership reassignment is not a supported
state migration; replay authorization and mutation identity remain principal bound. Replayed
keys bind exact semantic intent. Up to 128 accepted relations and 512 replay keys;
no deletion or eviction. Relation bytes commit in AtomStorage before Relations
acceptance; only accepted records participate in traversal. Cursors bind principal,
scope, source incarnation, query/direction/ref, limit and immutable accepted head.
Traversal returns relation references, not neighboring atom references.

Atom feed entries contain only immutable reference, content type, size and sequence.
Atom acceptance and its entry commit together in the atom owner. Head identifies
source UUID + scope + sequence + profile. At most 512 atoms per fresh store, payload
limit 4096 bytes, read pages at most eight. readCommits is snapshot bound and must
return a contiguous prefix; foreign incarnations and impossible heads fail. Legacy
stores cannot be opened as feed stores; no synthetic historical order is permitted.

Search exact-attributes/1 extracts only canonical UTF-8 JSON knowledge records of
application/fusion-knowledge-v1 with required kind and optional topic/label. Values
are strings (1–128 code points, <=512 UTF-8 bytes); unknown fields, duplicate JSON
keys/noncanonical bytes or malformed enrolled records fail closed. Matching is exact
case/Unicode, no normalization. Missing field never matches. Query is a closed
conjunction of 1–3 distinct allowlisted fields with eq only; <=1024 bytes. Other
content types are ignored deterministically, including relations and private
cognitive atoms. Search does not claim that a stored relation payload was accepted.

Source prefix W and Relations accepted head R are independent. Queries describe
complete indexing at W, page completeness, minimum freshness and equality to a
labelled head observed by maintenance separately. They do not fetch a current head
or ingest as a read side effect. Allowed stale reads use a minimum from the same
incarnation at or below W. Insufficient freshness returns NOT_AVAILABLE, not an
empty answer. Results order by source commit sequence. Pages freeze W and reject
changed query/principal/scope/source/generation/limit. No globally atomic snapshot.

catchUp consumes <=8 new records/32768 payload bytes plus at most one checkpoint
metadata anchor. Every envelope is retrieved to verify content type, size and
digest before an out-of-corpus type is ignored; unavailable ignored bytes also
block that batch. Index entries and contiguous checkpoint commit in one Search
transaction. At most 256 enrolled records. Malformed/unavailable enrolled bytes stop
progress with a private sequence/reason diagnostic. Read-only query does not repair.
beginRebuild captures a source head, clears only derived state, assigns a fresh
generation and blocks queries until that prefix is complete. Batches resume after
restart. Rebuild keys are bounded and replayable; old-generation cursors fail.
The source has no pruning API. Missing/corrupt replay ranges or required bytes stop
maintenance without advancing its checkpoint; a partial rebuild remains unavailable.
No automatic backfill, repair or fabricated prefix is permitted.
Atomic-file Search fixture implements its own state transitions, using only shared
DTO validation/extraction; it does not call or inherit the SQLite owner.

Lookup uses declared ports only, with maximum eight search pages, 32 discovered
matches, 128 traversed relations and 64 retrieved records; one hop and visited sets.
It validates each returned relation, reverse incidence and connected payload bytes.
A private caller journal retains exact query, snapshots and full authorized results.
Native public params name a private operator-registered bounded information request
(query + source barrier only, never answers). Hive receives no query text or private
identifiers. The new caller reads no writer oracle or expected-result manifest.
This request indirection preserves query privacy under the existing native command
logging behavior; it is not a token-to-answer map. Counts/status and a public command
receipt are the only ordinary native output. New queries after lag/rebuild use new
commands; original commands retain their recorded snapshot or fail explicitly if a
pending cursor generation is invalidated. No numerical or chain effects occur.
