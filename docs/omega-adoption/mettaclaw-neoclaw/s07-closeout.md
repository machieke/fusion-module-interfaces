# S07 closeout and functional coverage review

**READY_FOR_REVIEW. ADDITIONAL_LIVE_GENERATIONS=0.** The published bounded S07
integration is reconciled with its versioned evidence. This closeout changes only
review documentation and evidence; it adds no operation, profile, authority or
runtime behavior. The subsequent [retrieval-grounded workload](s07-next-workload.md)
is specified, unimplemented and unauthorized for live execution.

## Source and publication identity

Review starts at `4981788b4d8069a2b2264e65197f9886b74f1f5f`, branch `master`, the
completed S07 publication. Its parent is S06
`3fc1af31f2d64583fe4c873b6b656dad2d6b1275`. The starting worktree had only the
user-supplied untracked `codex_neoclaw_s07_closeout_and_coverage_review.md`.
No commit or push is authorized or performed in this closeout.

**Publication addendum to the historical S07 report:** its “uncommitted” wording
and `source-state.json` describe the prepublication working tree. They are retained
verbatim. Commit `4981788…` publishes those bytes; it is not the commit on which
the historical tests ran. All 270 recorded delivery hashes match the publication.
Its exact 272-file delta consists of those files plus `source-state.json` and
`final-audit.json`. The [source review](../../../evidence/s07-closeout/source-review.json)
enumerates every file/hash and resolves every versioned manifest entry.

Native source remains MeTTaClaw `2af37c3fec18613de54ca42fde2382a9087d4524`,
PeTTa `fea83178af3722666d2948d074591d10a3134f56`, SWI 10.0.1
`e58621a91ab7dd530e1e8185ed518f63d851c414`, and DeTTa
`272888f264dd2dde18b574cabb53c266b0dac2ec`. The selected local Ollama source is
`0d0720e51fb2fd9aa58781c3d720c06d720c2e7b` plus the two recorded MLX CPU patches;
binary SHA-256 `db8d6a16322494d762bf5394d5e5318d48f42e93f9dd44888d48d3a12099d43c`.
`qwen3.8:27b` manifest is
`9a8921f5b297f01451509b60e4a7e754674fe40d4a64dd9f89fc4a56c4fc5ee1`.
The existing [source ledger](../../../integration/neoclaw/model-sources.json),
[S07 source table](s07.md#exact-source-state) and historical manifests retain all
helper, E5, Chroma, IRC, runner and independent Fusion PLN pins. No upstream fetch,
model download, build or runtime restart was needed for this review.

## Source-to-test relationship

These are historical source relationships, not a claim that all 149 methods ran
on the publication or with unchanged transitive dependencies.

| Manifest under `evidence/s07/` | Resolved entries | Publication differences | Executed evidence tied to that version |
|---|---:|---|---|
| `test-source.json` | 251 | 16 files | Final 138-method unit run; six loaded native methods plus one loader error; corrected promotion method; live-01 via identical `pre-live/test-source.json` |
| `cpu-test-source.json` | 251 | 9 files | 23 contract methods, one native recorded-model kill method, 140-method unit run, one real-channel/recorded-model regression |
| `cpu-live-source.json` | 251 | 9 files | Load-only allowance changed 120→600 seconds; readiness phases, no new captured generation attributed to this version |
| `isolated-test-source.json` | 252 | 4 files | 23 contract methods, one native recorded-model kill method; live-04 uncaptured validation failure |
| `cache-counter-test-source.json` | 252 | 2 files | 24 contract/oracle/TLS methods; live-05 two captures, unsupported reply retained |
| `remaining-live-source.json` | 252 | 1 file | Live-06 eight calls; three complete workflows and two actual caller recoveries |

All **1,509 entries** resolve to current bytes, preserved snapshots or exact Git
objects. The machine-readable source review lists the path/hash/version relation
for each entry and every successive difference. Inspection found these material
changes across the historical phases:

| Files / phase | Classification and effect | Relevant later evidence / limit |
|---|---|---|
| `model_contracts`, `model_service`, `model_transport`, `neoclaw_model`, `neoclaw_channel`, adapter | **1: runtime/profile behavior.** Explicit `/2` five-minute input/model profile, exact selection, original `/1` limits retained | CPU contract/native checks and subsequent live captures; no old occurrence retimed |
| `channel_composition`, `controlled_run`, `operator`, `model_composition`, `model_run` | **1/2: runtime and executable reproduction configuration.** Longer bounded test-actor lifetimes; second input after real first-command completion; prior spent calls counted | CPU channel regression, isolated native check and live records; actor lifetime is not a deadline reset |
| Adapter, `model_transport`, `channel_startup`, `model_composition` | **1/2: endpoint binding/isolation.** Selected loopback port, manifest path validation, owner seal, caller raw-port denial and filesystem masks | Isolated tests and actual same-host HTTPS cases; no arbitrary model-selected endpoint |
| Adapter `convert`, `tests/test_model.py` | **1: response validation.** Admit only the source-declared optional bounded cache counter without changing closed receipt usage | Latest 24-method recorded/TLS run and ten real captures; earlier rejected raw payload remains unavailable |
| `model_run.py` after cache-counter tests | **2, with category-3 evidence exports:** explicit continuation of predeclared cases, retained failure/capture exports | Exact recipe then exercised by live-06. Not a documentation-only change and not covered by the earlier unit-run identity |
| Test files | **1: test behavior.** CPU, selected-port and cache-counter assertions added | Separate versioned run identities; no retroactive test credit |

Only `integration/neoclaw/model-sources.json` differs between the final live
manifest and publication: `8573cecd…` → `097bd6e8…`. Its exact field diff is in
`source-review.json`. The changed selected profile, input deadline and isolated
runtime description are **category 2 reproduction metadata**. Call counts,
authority history, observation flags, outcome, prior-manifest links and historical
profile labels are **category 3 reporting**. The binary, model digest, source hashes,
model options and numerical/runtime profiles did not change after the final run.

This classification follows executable consumption, not the JSON extension:

- `model-sources.json` is a source ledger, with no executable reader in the
  inspected Fusion, integration or test sources. Its `runtime.api` still describes
  the historical default 11434 endpoint. Its root-service `/proc` limitation is
  historical. Neither field overrides the later task-owned run at port 48173.
- `model_composition.runtime_lock` writes a **different** `ollama-runtime.json`.
  `configure` checks its hash; `ModelService` seals its path/hash;
  `OllamaCompletion.__init__` consumes its binary/version/model/native source and
  optional port/asset-root fields. Client binding freezes the declared port.
  `complete` subsequently checks readiness and the selected profile. None of those
  calls was made in this closeout.
- The retained per-run locks agree with the final ledger's binary/version/model
  identities. Their pinned native source bytes also match. The task-owned process
  observation records the same running binary hash. Seven of eight mapped runtime
  files match the prior runner inventory; `libmtmd.so.0.5.0` was additionally
  observed/pinned. This is observation reconciliation, not an independent rebuild
  or a new assertion about a currently running process. The adapter does not
  automatically enforce the whole mapped-library inventory; those hashes are
  separate reproduction evidence, not execution attestation.
- `/1` remains 30 seconds; `/2` remains 300 seconds for newly accepted inputs.
  Tool/context deadlines remain 30 seconds. Original failed intent bytes,
  deadlines, options, reservation counts and all failure records are unchanged.

## Campaign accounting at separate units

The [independently derived accounting](../../../evidence/s07-closeout/accounting.json)
joins each provider row to its application occurrence and intent, checks captured
receipt bytes and bound deadlines, then checks native projection, egress and peer
records. It contains all twelve exact IDs. The historical summary agrees.

| Attempts | Retained source | Model / mailbox placement | Captures and command outcome | Complete workflow / recovery |
|---|---|---|---|---|
| 1 | `live-01` | local / local | Original `/1` timeout; one reservation, no capture/admission, unknown final usage | No / no |
| 2 | `live-04/1` | local / local | Backend HTTP 200 followed by adapter validation failure; spent/uncaptured | No / no |
| 3–4 | `live-05/1` | local / local | Two captures; native deduction then rejected `Send Message to User …` | No reply / no |
| 5–6 | `live-06/1` | HTTPS / local | Deduction and approved send, both captured/admitted | Yes / first captured call recovered after SIGKILL |
| 7–8 | `live-06/2` | HTTPS / HTTPS | Deduction and approved send, both captured/admitted | Yes / no |
| 9–10 | `live-06/3` | local / HTTPS | Deduction and approved send, both captured/admitted | Yes / no |
| 11–12 | `live-06/4` | HTTPS / HTTPS | Deduction then rejected `send_message_to_user …`, both captured | No reply / first captured call recovered after SIGKILL |

All HTTPS placements are authenticated **same-host isolated** placements.
`live-06/2` versus `live-06/3` is the successful model-placement comparison with
the same HTTPS mailbox placement. Local/local was exercised, but its retained
campaign has no complete positive reply. A recovered first call does not turn a
later rejected new call into a completed workflow.

Counts: **12** spent generation reservations, **10** captured responses,
**2** uncaptured attempts, **8** authorized batches, **2** rejected captured
batches, **5** actual native deductions, **3** approved peer-observed replies,
**3** complete two-call workflows, **2** real native post-capture SIGKILL
recoveries and **0** regenerations of those recovered calls. There are seven
generation-bearing sessions (five reached two calls), four exercised placement
combinations and six named campaign phases; live-02/live-03 consumed zero
generation reservations. These units must not be added together.

The two recoveries preserve the public before/after ID, exact intent (including
prompt/deadline) and captured result bytes. The executed recipe also asserted
`context_view` equality. Public row exports omit that field, so its equality can
be traced to the runtime assertion and recovery record, not independently
recomputed from the reduced row exports. The failed live-04 API payload was not
retained; the cache-counter explanation remains a source-supported **inference**.

Load-only readiness observations and the interrupted readiness wait are separate
from generations. The failed fixed-port launch is also retained separately.
No failed occurrence was refunded or replaced. Unsupported commands remain
unsupported: correct refusal passes authorization conformance and fails the
intended reply task.

## Tests, timings and limits of the measurements

The [test map](../../../evidence/s07-closeout/test-map.json) independently parses
the ten final-series logs: **358 passing method executions**, representing
**149 distinct methods** (30 S07, 119 selected historical regressions). One
loader-name error remains recorded alongside six loaded passing methods; its
corrected target later passed. The last broad run contains 140 methods; the
latest adapter/oracle/TLS run contains 24. Earlier baseline/development runs are
additional historical records, not silently included in this ten-run count.

Provider-side kill testing uses a recorded backend with four stages inside one
test method. Six distinct model preflight/native-loop methods use recorded or
absent model responses with real native components where labelled. The two real
application SIGKILL trials above are separate live scenarios. No aggregate
“test count” combines methods, subtests, kill stages or workflows.

Closeout executed the offline source/accounting audit and **one new isolated
recorded-response run of 20 existing methods**, with 55 subcase observations,
including four recorded-provider kill stages. It rechecks the final adapter,
owner/profile guards and pinned native text oracle. These methods overlap the
historical 149; they add no new distinct-method claim. Test entrypoints were read
first. The run used Python 3.12.12 in `bwrap --unshare-net`, read-only repository
mount, temporary writable `/tmp`, and an audit guard that blocks connections,
binds and executable launches. The guard was probed before the tests. No forbidden
attempt occurred during the tests; no service/native stack was launched. See
[exact sources and results](../../../evidence/s07-closeout/offline-checks.json)
and [log](../../../evidence/s07-closeout/offline-checks.log).

| Ten captured backend responses | Minimum seconds | Median seconds | Maximum seconds |
|---|---:|---:|---:|
| Total backend duration | 69.582603 | 74.843056 | 85.694854 |
| Prompt evaluation | 52.428736 | 57.942815 | 61.577121 |
| Output generation | 8.976584 | 18.197613 | 29.962745 |
| Per-request reported load | 0.001264 | 0.001876 | 0.002920 |

These come from nested `durations_ns` fields. Total duration includes prompt
evaluation and is **not output-decoding time**. Component medians need not sum
to the total median. Per-request load does not represent cold readiness; readiness
was separate. Application/tool/IRC time was not independently measured end to
end, and is not represented by backend totals. Captured usage is 3,220 input and
216 output tokens; final usage for two uncaptured attempts remains unknown.
No monetary estimate, complete token total, exactly-once billing, production
throughput or fixed-condition reliability benchmark is supported. These are small
versioned synthetic CPU trials.

## Current native-boundary / module / profile / placement matrix

“Real model” below means actual generative model selection/consumption of that
boundary in the retained S07 workflow. Real **E5** execution alone does not imply
a generative-model workflow. All prior evidence remains tied to its own source
manifest; this review did not rerun those integrations.

| Native boundary | Module / selected profile | Authoritative owner | Local evidence | HTTPS evidence | Native-loop evidence | Real-model evidence | Remaining fixture / restriction | Source / run |
|---|---|---|---|---|---|---|---|---|
| `metta` with exact `Truth_Deduction` | PLNKernel + DelegatedExecution; `neoclaw-nal-truth-deduction/1`; AtomStorage/Messaging delivery | Pure native NAL; independent execution/result/outbox, payload and mailbox owners; app occurrence/ack | Original and adapted real native/DeTTa | S01/S01.1 authenticated same-host | Actual parser, skill and next-context handoff | **Yes:** five native deductions and actual feedback in subsequent prompts; S07 numerical execution placement local | Two grounded STVs only; broader NAL/MeTTa not adopted | [S01](s01.md), [S01.1](s01_1.md), S07 live-05/1 and live-06/1–4 |
| Native `search` | DelegatedExecution; `external-web-search/1` | Execution owner retains first observation; independent payload/completion owners | Real helper/SDK and live external search | Two local/network live-provider sessions | S01+S02 in one controlled session | **Unrun** with real generative model | Recorded SDK negatives separate; web text untrusted; no exactly-once upstream | [S02 verification](../../../evidence/s02/verification.json) |
| `query` → `query_with_ids_and_dists` → hydration | Search `semantic-embedding-memory/1` + AtomStorage | Search generation/checkpoint; authoritative enrollment feed and immutable payload owner; app retained view/result | Real E5/Chroma/DeTTa, original/adapted parity | Real authenticated same-host retrieval | Actual query/selection/unique/presentation and next context | **Unrun** | Model/channel fixtures; no whole-memory adoption, stable tie-order or ANN recall guarantee | [S03](s03.md), [same-query](../../../evidence/s03_1/same-query-final.json) |
| Query-time `embed` / `useLocalEmbedding` | X02 `embedding@1.0.0`; `neoclaw-e5-query-text/1` | Encoder owns evaluations; app captures bound vector before Search | Original pinned E5 inference | Independent encoder/retrieval placement; E5-free caller | Actual native query and next context | **Unrun** as model-directed memory query | Other embedding modes not covered; no hosted fallback | [S03.1 verification](../../../evidence/s03_1/verification.json) |
| Native append-only `remember`, later new `query` | X02 `neoclaw-e5-memory-text/1` + AtomStorage/feed + Search; `neoclaw-append-only-memory/1` | App stable UUID/time/occurrence; independent storage accepts, Search publication and local metadata readiness | Real native/E5/Chroma/DeTTa parity and read-your-writes | Real same-host full and mixed placement; E5-free caller | Success and query result in subsequent native context | **Unrun** | Scripted model/channel; fresh state only; no update/delete/migration | [S03.2 verification](../../../evidence/s03_2/verification.json), [same-memory](../../../evidence/s03_2/same-memory-final.json) |
| Native `support` / `contradict` → `tvUpdate` | C1 `neoclaw-local-source-assessment/1`; C2 `neoclaw-nal-revision-private/1`; capped NAL profile | Separate local source/assessment/provenance and belief owners, trusted relay | Real original `Truth_Revision`, DeTTa and committed query readback | Private C1/C2 remote placement unsupported | Actual commands/source capture and next-context consumption | **Unrun** | Model/channel fixtures; labelled compatibility prior, no invented evidence roots | [S04 verification](../../../evidence/s04/verification.json), [trace](../../../evidence/s04/same-session-trace.json) |
| Native query belief / linked-label presentation | C2 retained belief view; local compatibility labels, not adopted general Relations | C2 authoritative revision and app immutable query view; labels local | Actual revision/query tests | Cognitive owners remain local even with remote retrieval | Actual `getSTV`/query display | **Unrun** | General relation/link/unlink ownership still outside adoption | S04 `final/native-loop.json`, `final/view-repair.json` |
| Native `promote` / `demote` and query score reads | Attention `wall-clock-promotion/1` | Separate local Attention score/time/receipt owner | Real SQLite and native arithmetic; independent atomic-file **fixture** substitution | Private Attention remote placement unsupported | Actual commands/query ordering | **Unrun** | Wall-clock policy, not STI or ECAN; no evidence-weight/index change | [S05 verification](../../../evidence/s05/verification.json) |
| `getContext` → promoted-memory selection/hydration | Attention `wall-clock-promotion/1` + AtomStorage + retained belief display | Local Attention; payload owner; app retained context view | Nonempty real selection/hydration in S05 | Payload interface support is not remote Attention adoption | Actual native `getContext` | **Empty set only** in S07, not populated memory disclosure | S05 model/channel fixtures; S07 positive promoted set `()` | [S05](s05.md), S07 bound prompts |
| Native `receive` / input source handoff | Messaging `durable-mailbox/2` + AtomStorage `immutable-bytes/1`; `isolated-irc-mailbox/1` | Bridge occurrence, payload, mailbox, app acceptance/ack, local C1 source are separate | Real isolated IRC and socket peer | Real same-host mailbox/payload HTTPS | Actual native receive and model input | **Yes:** S07 exact synthetic source occurrences | Peer is scripted but real socket; pre-capture loss window; no text-equality IDs | [S06 verification](../../../evidence/s06/verification.json), S07 channel-inputs/intent rows |
| Native `send` | Same S06 Messaging/AtomStorage route | App intent, mailbox acceptance, bridge reservation/outcome separately committed | Real isolated IRC send | Real HTTPS mailbox cases | Actual native send | **Yes:** three peer-observed approved bodies | Exact-body consent; socket return ≠ receipt; unknown send never automatically resent | S07 live-06/1–3 result/egress records |
| Native pre-command text completion | X01 `model.inference@1.0.0`; `/1` historical, `neoclaw-ollama-qwen38-text/2` selected | App prompt/occurrence/admission; independent model acceptance/reservation/capture | Real local Ollama CPU | Authenticated same-host HTTPS owner; caller lacks selected model assets/raw API | Actual loop/context/parser and capture recovery | **Yes:** ten captures, bounded outcomes above | Synthetic scaffold, unused history/web; two unsupported replies; no default Omega | [S07 verification](../../../evidence/s07/verification.json), closeout accounting |
| Provider selection and current authorization across adopted boundaries | Registry, CompatibilityResolver, Authorization supporting contracts | Static operator descriptors/policies; owners recheck principal/scope/route/profile | Real checked selection/policy code; generated authority fixtures | TLS and generated scoped credentials | Used by adopted consumers | Exercised within S07; no independent new user command | No distributed discovery, production SCS or hostile-host attestation claim | `registry.py`, `policy.py`, S01–S07 contracts/negative gates |

The historical denominator remains **15 families**, the mapping **105 semantic
rows / 327 definition occurrences**, and the operation ledger **eight entries /
nine native user commands**. X01 ModelInference and the two X02 query/memory
Embedding profiles stay explicit extensions. These are different inventories;
there is no combined functionality percentage. The old semantic-responsibility
9/15 assessment and zero-conformance mapping snapshot are historical, not current
native-adoption counts.

DA is an implementation dependency below adopted storage, not a new direct native
DA command. General Relations and InferenceControl have no adopted native seam;
the application loop is not C4. ConsensusFinality/chain has no S07 run. Historical
Fusion M1–M5 Hive/chain evidence is not MeTTaClaw evidence. Registry/resolver/auth
support does not promote an entire family. Broader models, media/perception, tool
catalogue and arbitrary execution remain outside this adopted scope.

The historical [placement scorecard](remote-placement.md) is a mapping-era design
assessment, not current measured coverage. Its **S08 Embedding** candidate has
already received bounded X02 coverage in S03.1/S03.2. Finishing S07 does not
authorize or require implementing another Embedding module.

## Closeout gates and limitations

| Gate | Result | Evidence / qualification |
|---|---|---|
| SOURCE_CLOSURE | PASS | 270 publication hashes, all 1,509 versioned entries, exact 272-file publication delta; final lock field and consumer trace; current runtime unchanged |
| CAMPAIGN_ACCOUNTING | PASS | All twelve owner/application identities reconciled; 10 captures, 8 admissions, 2 rejections, 3 workflows, 2 recoveries; no calls left |
| EVIDENCE_UNITS | PASS | 149 historical distinct methods across ten final-series runs; separate 20-method offline run, subcases, recorded faults and real workflow units |
| COVERAGE_CURRENT | PASS | Matrix above; unchanged historical rows/denominator/adoptions and explicit X01/X02; combined live-memory workflow unrun |
| NEXT_WORKLOAD_READY | PASS for specification | [One bounded definition](s07-next-workload.md); command/disclosure/output decisions pending; not implementation-ready or live-authorized |
| NO_NEW_GENERATION | PASS | Static checks and isolated recorded responses only; no model readiness, restart, generation request or campaign/journal reuse |

Unresolved facts remain explicit: exact live-04 rejected field; independent
context-view reconstruction from reduced public exports; original S06 baseline
observation failure cause; complete usage for uncaptured attempts; independent
Ollama rebuild; cold/clean-cache reproducibility; general model quality, production
throughput and end-to-end channel timing. No new live test could be spent to close
them here. Unsupported command refusals are observed, not unresolved bugs to fix
by aliasing. Full default Omega, populated-memory real-model interaction,
multi-host, private export, migration and chain work remain unrun/out of scope.

## Commit-ready changes and reproduction

The [review source manifest](../../../evidence/s07-closeout/review-state.json)
records the exact changed-file list and hashes separately from historical evidence.
Publication authorization remains pending; no blanket staging was performed.

- User-provided closeout brief: preserved as the scope input.
- `s07-closeout.md` and `s07-next-workload.md`: review entry, current matrix,
  source/attempt reconciliation, limitations and one proposed workload.
- Mapping `README.md`, `coverage.json`, `mapping-ledger.json` and
  `remote-placement.md`: additive closeout links and historical-roadmap clarification;
  original rows, entries and scores unchanged.
- Module-interface `runbook.md`: closeout-only static/offline recipe and source-ledger
  versus executable-lock clarification.
- `evidence/s07-closeout/`: reproducible offline audit, source relationships,
  attempt accounting, test map, isolated test runner/log/results and final review
  hashes/checks. Historical `evidence/s07/` remains byte-for-byte unchanged.

Executed commands are recorded in `review-state.json`. The safe audit entrypoint
is `artifacts/s03/venv/bin/python evidence/s07-closeout/audit.py`; it imports only
stdlib and permits only read-only Git child commands. The isolated recorded test
recipe is in the runbook addendum. Do not run `model_run`, `model_corpus`, the
runtime launcher or native integration suites as part of this closeout.

**ADDITIONAL_LIVE_GENERATIONS=0 — READY_FOR_REVIEW.**
