# Executed evidence and mapping gates

This is a source-mapping review, not an Omega integration milestone. Each evidence class below is intentionally separate. There is no measured remote performance result, live model/channel call, state migration or deployed service.

## Exact source acquisition and verification

Working directory: `/home/purplezky/work/takopi/fusion-module-interfaces`. Before semantic mapping, repository identities and status were checked with `git rev-parse HEAD`, `git status --porcelain`, `git remote get-url origin`, branch inspection and `git ls-remote`. Fresh inspection sources were obtained with:

```sh
git clone --depth 1 --branch neoclaw https://github.com/patham9/mettaclaw.git artifacts/omega-mapping-source/mettaclaw
git worktree add --detach artifacts/omega-mapping-source/fusion 33388d20cb10c5f9878a463a6d0debba7949e35a
git clone --depth 1 https://github.com/patham9/petta_lib_chromadb.git artifacts/omega-mapping-source/petta_lib_chromadb
git clone --depth 1 https://github.com/trueagi-io/PeTTa.git artifacts/omega-mapping-source/PeTTa
```

Those moving-source acquisition commands describe what was run, **not a reproducible revision recipe**. To reproduce inspection later, fetch and detach each exact SHA in [source-state.json](source-state.json) rather than accepting a newer head. Omega's bootstrap does not itself select `neoclaw`, and its unversioned git-import can reuse an arbitrary existing checkout. No declared deployed PeTTa/adapter SHA could be recovered from that source; fresh observed pins are labelled accordingly.

`rg`, line-numbered reads, Python AST parsing and MeTTa form/definition extraction covered all tracked application code, all Chroma-adapter code and the selected PeTTa import surface. Selected runtime builtins are cited at actual definitions. Scope exclusions are explicit in [symbol-index.json](symbol-index.json). No applicable AGENTS.md was found in workspace ancestors or inspected roots/repositories. The old local MeTTaClaw tree was only checked for source identity/status; its untracked private/runtime contents and `.env` were not read.

Fusion evidence was reconciled against the current checkout:

```sh
git log --format='%H %s' bfb0ec8..33388d2
git diff --name-only bfb0ec8856c932dc2bcbc05b8949c957da8d72cd 33388d20cb10c5f9878a463a6d0debba7949e35a -- fusion contracts integration adapters tests scripts
```

The second command returned no paths. SHA-256 revalidation matched **132/132** files named by `evidence/m5/final/verification.json`. The manifest records twelve M5 PASS gates at `bfb0ec8`; historical real DeTTa/native Hive and fixture results remain historical, not new Omega tests. [Fusion baseline](fusion-baseline.md) lists exact current contracts and limitations.

## Executed scoped probes

Reproduction (sources must be checked out at the manifest revisions first):

```sh
python3 docs/omega-adoption/mettaclaw-neoclaw/probes.py artifacts/omega-mapping-source docs/omega-adoption/mettaclaw-neoclaw/probe-results.json
uv run --python 3.11 --locked python -m unittest tests.test_contract.Compatibility -v
python3 docs/omega-adoption/mettaclaw-neoclaw/validate.py
```

`probes.py` uses temporary directories and synthetic values; no socket connection, hosted model or real Chroma collection is opened. It sets no provider credentials and does not start Omega. Native NAL uses direct SWI `-q -s <pinned PeTTa>/src/main.pl -- <temporary probe.metta> --silent`, importing only the pinned NAL source. Python 3.8.10 was used for the standalone mapping probes; the Fusion tests ran under the repository's locked Python 3.11 environment. SWI reports 10.0.1; this does not establish Fusion's 10.1.14 runtime compatibility.

| Check | Class | Observed result | Limit |
|---|---|---|---|
| Existing helper script tests | Real Python + real temporary SQLite, synthetic data | 12 parser assertions and promotion CRUD/default assertions passed; `promotion hashmap tests passed` | No crash/power-loss test or Chroma integration. |
| Parser bounds/allowlist | Real local function | Six commands retained; unknown command name retained | Demonstrates parser is not a security allowlist or durable command budget. Does not execute the unknown command. |
| IRC consuming buffer | Real local function, no network | `one \| two`, then empty on second get | No server delivery/auth/reconnect claim. |
| Chroma link/deleted truth | **Fixture backend, actual wrapper source** | Duplicate timestamp suppressed; existing default STV `[1,.5]`; deleted record returns `None` | Collection double replaces metadata. Does **not** validate actual SDK list acceptance, metadata merge/remove or durability. |
| Update order | Static source assertion | `forget_ids` precedes old `get_stv` | Full native update and its failure/partial-result presentation unrun. |
| Native NAL deduction/revision | **Real SWI/PeTTa native computation**, synthetic inputs | Deduction `(stv 0.5599999999999999 0.4032)`; contrary revision `(stv 0.5 0.6666666666666666)`; twice-positive revision `(stv 1.0 0.75)` | No full Omega command, Fusion PLN profile, evidence admission or remote provider claim. |
| Source parse | Static Python AST | All 6 application/adapter Python files parse | Does not import unpinned provider SDKs. |
| M5 source audit | Recorded evidence + fresh hash verification | 132 hashes match | Does not rerun historical integration gates. |
| Existing Fusion compatibility tests | Fixture/contract unit tests | 2 tests passed: same-major/profile/guarantee rejection and no backend/cognition imports across contract boundary | Not a full M1–M5 rerun. |
| Diagram syntax/render | Mermaid 11.12.0 in headless Chromium | Seven native Mermaid blocks parsed and produced SVG | Render validation, not presentation benchmarking or human visual review. SVGs/tool installation are ignored local build artifacts. |
| Review consistency | `validate.py` | Source pins/hashes, symbols, command inventory, ledger counts, score totals, links, source cleanliness and no changes outside the review packet/original brief checked | Allows review-only descendant commits while keeping inspection sources pinned. A consistency checker does not prove every semantic judgment; packet is for human review. |

Raw scoped probe outcomes are in [probe-results.json](probe-results.json), diagram outcomes in [diagram-validation.json](diagram-validation.json), and packet checks in [validation-results.json](validation-results.json). Mermaid was installed only under ignored `artifacts/omega-mapping-build/mermaid` using `npm install --no-save --ignore-scripts --no-audit --no-fund mermaid@11.12.0`; an ephemeral Playwright script called `mermaid.parse` and `mermaid.render` on each block. No repository dependency lock or runtime was changed.

## Unrun, unassessed and prerequisite-blocked work

- **UNRUN:** complete MeTTaClaw startup and actual `metta` command/facade invocation; real Chroma SDK collection behavior; real IRC/Mattermost ingress/egress; hosted text/image models, embeddings and media; proposed remote adapters and every next-slice acceptance test; fresh full DeTTa/Hive/chain regressions. These were unnecessary for source mapping and some would require private credentials/data or live calls.
- **UNASSESSED source deployment:** author/deployed PeTTa and adapter revisions, Python SDK versions, embedding weight revisions, hosted model aliases/availability, optional MORK runtime use and generated private store contents. Exact observed inspection source revisions are known. Do not promote them into a deployed-runtime claim.
- **BLOCKED future memory cut:** no authoritative replayable legacy indexing feed; vector/model/promotion contracts absent; timestamp identity and immutable update/delete/retraction semantics unresolved; legacy STVs lack evidence roots; current private profiles prohibit remote placement. These are precise prerequisites, not reasons to substitute fixtures.
- **BLOCKED future model/perception/general execution cuts:** missing typed model/embedding/perception/tool-policy contracts, resource bounds and authority semantics. Runtime keys do not supply user authorization.
- **EXECUTED_FAILURE / TIMEOUT:** the first Mermaid render rejected semicolons in sequence-message text; those labels were corrected and all seven blocks were rerun. The first packet validator also rejected two source signature lines solely because of trailing whitespace; comparison now normalizes line-edge whitespace. Both were documentation/checker issues, not runtime/provider failures. No unresolved probe failures or observation timeouts remain. No network runtime gate was attempted and then called “passed.”

## Gate-by-gate result

All results below are **mapping/design PASS**, not implementation readiness. Machine-readable evidence is in [gates.json](gates.json).

| Gate | Result | Evidence / qualification |
|---|---|---|
| SOURCE_PIN | PASS | Fresh exact sources + dirty/unpinned/deployed unknown distinctions in source-state. |
| COMPLETE_INVENTORY | PASS | 105 semantic rows; 19 advertised commands plus runtime/imported surfaces; private/dynamic exclusions explicit. |
| SYMBOL_TRACE | PASS | 327 occurrences resolve to rows; pinned path/line citations and dependency traces. |
| MODULE_MAPPING | PASS | Nine observed family analogues, six absent; provider/consumer/facade/orchestrator/effect roles; no conformance inferred. |
| COMMAND_COMPOSITION | PASS | Ordered current/target operations, independent commits, error/compatibility decisions in command-map. |
| STATE_OWNERSHIP | PASS | Stores, identity, writers/readers, secrets, buffers, threads, file/DB coupling and recovery limits explicit. |
| PROFILE_DISCIPLINE | PASS | Current exact/vector, STI/promotion, PLN/NAL, immutable/mutable and local/remote distinctions; draft labels unimplemented. |
| REMOTE_PLACEMENT | PASS | Ten candidates × twelve criteria with rationale, privacy and failure prerequisites; first three ranked. |
| GAP_DISCIPLINE | PASS | Thirteen mismatches and seven additional gap groups; no universal execution escape hatch. |
| TARGET_ARCHITECTURE | PASS | Three native architecture diagrams and current/target query + reasoning sequences; owner and trust boundaries explicit. |
| NEXT_SLICE | PASS | Named pure NAL slice selected; actual native-caller, selection, authority, replay/crash/result/fallback tests specified, all prospective. |
| NO_RUNTIME_CHANGE | PASS | Only review-area additions; user's brief preserved; source checkouts clean and original local MeTTaClaw status unchanged. |
| REVIEW_PACKET | PASS | Required views present, source/count/link/diagram checks agree; human semantic review remains the next action. |

No service or remote prototype was implemented. No contracts, runtime behavior, journals or populated state were changed. No new presentation, migration, scheduler, cognition or chain work was undertaken. Stop boundary: **READY_FOR_MAPPING_REVIEW**.
