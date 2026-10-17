# Codex handoff — map MeTTaClaw `neoclaw` to the Fusion module interfaces

## 1. Objective and stop boundary

Inspect the actual Omega candidate at:

- `https://github.com/patham9/mettaclaw`, branch `neoclaw`

and map its internal tools, skills, state stores, provider calls, background loops,
and externally visible operations to the 15-family bounded reference inventory in
`machieke/fusion-module-interfaces`.

The purpose is to identify stable module-interface seams through which selected
Omega functionality can later move from local placement to remote placement without
rewriting the Omega agent loop or binding consumers to a specific backend.

This task is an **inventory, semantic mapping, and remote-placement design**. It is
not an implementation milestone.

**Stop after the mapping/review packet.** Do not:

- modify MeTTaClaw runtime behavior;
- replace ChromaDB, PeTTa, MeTTa, NAL, channels, or LLM providers;
- implement a remote service;
- add new module families merely to make the denominator look complete;
- migrate memory, journals, embeddings, truth values, or persistent atoms;
- publish private memory or credentials;
- claim that a name or similar method signature establishes contract conformance.

## 2. Required source state

Work from authorized fresh checkouts. Before analysis, record:

1. exact MeTTaClaw `neoclaw` commit and worktree state;
2. exact `fusion-module-interfaces` commit and evidence state;
3. exact PeTTa revision used or declared by MeTTaClaw;
4. exact `petta_lib_chromadb` revision imported by MeTTaClaw;
5. other relevant imported libraries or runtime dependencies;
6. whether each dependency is pinned, moving, generated, or locally modified.

Use the current Fusion M5 reference as the semantic baseline where applicable. Its
tested implementation is recorded as
`bfb0ec8856c932dc2bcbc05b8949c957da8d72cd`, but verify the actual checkout and any
later evidence-only/documentation commits. Do not silently treat moving `master` as
the tested revision.

Read applicable `AGENTS.md` files. Preserve unrelated changes and source-access
restrictions.

## 3. Mapping principles

### 3.1 Map responsibilities and state ownership, not filenames

A source file can contain several module responsibilities. A single operation can be
a consumer of several modules. Do not assign one file to one module simply to make a
clean table.

For every component distinguish:

- **provider** — owns state or behavior promised by a module interface;
- **consumer** — invokes a module interface but does not own its state;
- **compatibility facade/adapter** — preserves an Omega-facing command while
  translating to one or more declared module ports;
- **orchestrator/cross-cutting runtime** — coordinates modules and should not be
  mislabelled as one of them;
- **out-of-inventory capability** — a real Omega function not adequately represented
  by the bounded 15-family inventory.

### 3.2 Preserve the four-way distinction

For every proposed mapping distinguish:

1. interface;
2. implementation;
3. transport;
4. placement.

For example, ChromaDB is an implementation detail. `query` is an Omega command. A
semantic Search interface is the behavioral boundary. Local Python calls versus a
remote request are transports/placements. Do not conflate them.

### 3.3 Do not force-fit missing capabilities

The 15-family denominator is a bounded reference inventory, not complete Omega
product coverage. When MeTTaClaw has a capability with no semantically adequate
family, record the gap explicitly.

Likely examples to verify include:

- LLM/model inference;
- embedding generation;
- perception/vision and motion sampling;
- the agent control loop;
- a user-facing tool/skill catalogue and effect schema;
- sandbox/process execution policy.

A bounded named `DelegatedExecution` profile may be appropriate for some of these,
but do not use `execute(anything)` to hide missing contracts. Recommend a new port
only when the behavior cannot be represented honestly by an existing interface.

### 3.4 Existing behavior is not automatically conformant

Classify each mapping as one of:

- `DIRECT_FIT` — behavior and ownership already align closely;
- `ADAPTER_FIT` — a narrow adapter can preserve behavior without changing the owner;
- `SPLIT_REQUIRED` — the current function combines multiple module responsibilities;
- `PROFILE_REQUIRED` — the family fits, but the current Fusion profile does not;
- `INTERFACE_GAP` — no adequate family/interface exists;
- `NOT_A_MODULE` — configuration, composition, orchestration, or presentation;
- `UNASSESSED` — insufficient source or runtime evidence.

Do not call a component implemented against Fusion merely because it resembles a
port.

## 4. The 15-family reference inventory

Map against these bounded families and their current selected profiles where
relevant:

1. DA storage
2. AtomStorage / minimal AtomSpace
3. Relations
4. Search projection
5. EpisodicMemory
6. BeliefRevision
7. PLNKernel
8. Attention
9. InferenceControl
10. Messaging
11. DelegatedExecution
12. Registry
13. CompatibilityResolver
14. ConsensusFinality
15. Authorization

Use the current Fusion architecture, contracts, ports, descriptors, capability
ledger, and executed evidence as the authority for what those profiles currently
promise. Do not infer broader semantics from family names.

## 5. Required MeTTaClaw inventory

Perform a symbol-level inventory, not only a directory summary. At minimum inspect
and trace:

- `lib_mettaclaw.metta` imports and composition;
- `src/loop.metta`;
- `src/memory.metta`;
- `src/skills.metta` and `src/skills.pl`;
- `src/channels.metta`;
- `src/utils.metta`;
- `src/helper.py`;
- `channels/irc.py`;
- `channels/mattermost.py`;
- `channels/websearch.py`;
- `lib_nal.metta`;
- `lib_nal7.metta`;
- `lib_llm_ext.py`;
- `memory/prompt.txt` and generated/persistent memory files where present;
- the imported `petta_lib_chromadb` implementation;
- PeTTa/MeTTa spaces and imported library calls used by the runtime.

Inventory all callable Omega commands, including at least:

- `remember`, `forget`, `update`, `query`, `episodes`;
- `link`, `unlink`, `support`, `contradict`;
- `promote`, `demote`, `pin`;
- `send`, `receive`, `search`;
- `shell`, `read-file`, `write-file`, `append-file`;
- `metta`;
- LLM completion, embedding, and visual-input helpers;
- persistent-space import/export/bounding;
- NAL revision, deduction, temporal inference, and other callable rules.

Also inventory:

- mutable state and its authoritative owner;
- external effects;
- secrets and credentials;
- background threads/processes;
- queues/buffers;
- retries, timeouts, deduplication and replay behavior;
- identifiers and serialization formats;
- file/database paths;
- runtime configuration and provider selection;
- implicit assumptions about local shared memory or filesystem access.

## 6. Preliminary hypotheses to verify

These are review hypotheses, not conclusions to copy blindly.

### 6.1 Agent loop and composition

`src/loop.metta::mettaclaw`, `getContext`, provider selection and command execution
appear to form the **local Omega runtime/orchestrator**. They consume memory,
channels, model providers and tools. They should normally remain a thin local client
initially and must not be labelled as the C4 InferenceControl provider merely because
they choose actions.

Assess separately whether any bounded portion maps to InferenceControl. The current
Fusion C4 profile selects explicit grounded tasks under durable budgets; an LLM
agent loop is not equivalent by name or purpose.

### 6.2 Memory path is a mixed responsibility

`src/memory.metta` and `petta_lib_chromadb` appear to combine several concerns:

- content persistence and identifiers;
- embedding generation and vector indexing;
- memory retrieval/ranking;
- episode links;
- strength/confidence fields and revision;
- promotion scores and decay;
- mutable update/delete behavior.

Map these separately. Do not call the whole file “Memory module” and stop.

Likely candidate mapping to verify:

- `createMemory` / `remember` → AtomStorage consumer plus Search enrollment;
- Chroma persistent documents → mixed AtomStorage + Search implementation;
- `query` → Search + AtomStorage retrieval, with Relations, BeliefRevision and
  Attention-derived enrichment/ranking;
- `link` / `unlink` and linked episode metadata → Relations;
- `support` / `contradict` / `tvUpdate` → BeliefRevision, with episode provenance;
- `promote` / `demote` / promotion SQLite map → attention/importance policy;
- `episodes`, history append/read → EpisodicMemory;
- `forget` / `update` → semantic mismatch with immutable AtomStorage that needs an
  explicit revision/tombstone/supersession design rather than hidden mutation.

The current Fusion Search profile is exact structured attributes. MeTTaClaw's
`query` is embedding similarity plus promotion ranking. Therefore it is not a direct
fit to `exact-attributes/1`; it likely requires a separately named semantic/vector
Search profile or a decomposition where the existing exact profile serves only a
subset.

The current Fusion Attention profile is integer STI with linear decay. MeTTaClaw's
promotion score uses a different decaying ranking policy and is closer to long-term
importance/promotion. Record it as a distinct policy/profile, not as conformance to
the STI profile.

### 6.3 Reasoning and revision

`lib_nal.metta`, `lib_nal7.metta`, `Truth_Revision`, `|-` and `|-t` likely map to:

- RevisionMath / BeliefRevision dependencies;
- PLNKernel rule profiles;
- possible inference-control consumers where multi-step application is introduced.

Separate pure truth functions/rule application from rule selection, premise lookup,
state admission and agent-level orchestration.

`src/skills.metta::metta` is an arbitrary evaluation gateway. It must not be mapped
wholesale to PLNKernel. Split named, validated reasoning operations from general code
execution. General MeTTa evaluation, if remotely placed, belongs behind a bounded
DelegatedExecution profile plus Authorization and resource limits.

### 6.4 Messaging

`src/channels.metta`, IRC and Mattermost likely form Messaging providers/adapters.
Assess their actual semantics against the Fusion Messaging contract:

- message identity;
- durable acceptance;
- polling/delivery;
- acknowledgments;
- correlation/reply routes;
- deduplication;
- backpressure;
- restart recovery;
- recipient and scope isolation.

A last-message in-memory buffer or best-effort send is not automatically a
`durable-mailbox/2` provider. It may be a legacy transport adapter in front of a
module-owned mailbox.

`channels/websearch.py` is **external web search**, not the Search projection over
Omega's internal knowledge. Map it as an allowlisted tool/delegated operation unless
a separate WebSearch interface is justified.

### 6.5 Skills and external effects

`getSkills`, the command list in `helper.py`, shell/file tools and tool-call parsing
appear to combine:

- user-facing skill catalogue;
- command parser;
- local effect implementation;
- model prompt documentation.

The Fusion Registry describes module providers and compatibility, not necessarily a
complete user-facing skill catalogue. Determine whether a separate ToolRegistry or
ToolDescriptor contract is needed. Do not claim that a prompt string is a versioned
provider registry.

Map shell and file operations to bounded DelegatedExecution profiles only with:

- explicit schemas;
- working-directory and path policy;
- read/write effect classification;
- time/resource limits;
- output bounds;
- idempotency/retry semantics;
- sandbox and current caller authorization.

Remote shell or arbitrary filesystem access must default to `NOT_REMOTE_SAFE` until
those semantics exist.

### 6.6 LLM, embeddings and perception

`lib_llm_ext.py` appears to contain:

- multiple LLM completion providers;
- local/OpenAI embedding paths;
- YouTube media resolution;
- video sampling and optical flow;
- image-enhanced model calls.

Map each capability separately. Determine whether it can be represented as a
bounded DelegatedExecution operation or whether a dedicated ModelInference,
Embedding, or Perception interface is needed.

Provider API keys, model choice and endpoints are operator configuration/secrets,
not caller-supplied operation parameters.

### 6.7 Registry, resolver, authorization and finality

Verify whether MeTTaClaw has real counterparts for:

- versioned provider descriptors;
- compatibility resolution;
- authenticated principal/scope/method/route enforcement;
- chain commitment/finality.

Hardcoded `if provider == ...`, prompt-listed skills and runtime `configure` calls
are not by themselves Registry or CompatibilityResolver implementations.

If no counterpart exists, classify Omega as a **consumer to be adapted** to the
Fusion provider rather than inventing a local implementation. ConsensusFinality is
expected to be such a case unless source proves otherwise.

## 7. Required mapping ledger

Create one machine-readable ledger and one readable report. Each row must represent
one semantic capability or state owner, not an arbitrary source line.

Recommended schema:

```json
{
  "component_id": "mettaclaw.memory.query",
  "source": {
    "repository": "patham9/mettaclaw",
    "commit": "<sha>",
    "paths": ["src/memory.metta"],
    "symbols": ["query", "embed", "get-promotion"]
  },
  "omega_role": "provider|consumer|facade|orchestrator|external_effect",
  "current_behavior": "...",
  "owned_state": ["..."],
  "dependencies": ["..."],
  "external_effects": ["..."],
  "data_classification": "private|shareable|secret-bearing|executable|mixed",
  "module_mappings": [
    {
      "family": "Search projection",
      "role": "consumer/provider/facade",
      "status": "DIRECT_FIT|ADAPTER_FIT|SPLIT_REQUIRED|PROFILE_REQUIRED|INTERFACE_GAP|NOT_A_MODULE|UNASSESSED",
      "current_profile": null,
      "candidate_profile": "semantic-embedding-memory/<version>",
      "reason": "..."
    }
  ],
  "placement": {
    "current": "local|remote-api|mixed",
    "recommended": "must-local|local-default|remote-safe-after-adapter|remote-preferred|not-remote-safe",
    "remote_unit": "...",
    "constraints": ["..."]
  },
  "contract_gaps": ["..."],
  "evidence": ["source reference or executed test"],
  "confidence": "high|medium|low"
}
```

Produce at least these views from the ledger:

1. source component → module family;
2. Omega command → module operation(s);
3. module family → current Omega providers/consumers;
4. state owner → store → writers → readers;
5. local/remote placement recommendation;
6. interface/profile gaps;
7. migration/compatibility blockers;
8. test/evidence coverage.

## 8. Required diagrams

Create native Mermaid diagrams in the report:

### A. Current MeTTaClaw runtime

Show:

- channel ingress;
- agent loop and prompt/context assembly;
- model calls;
- tool parsing/execution;
- history and persistent spaces;
- Chroma memory/search/metadata;
- NAL/MeTTa reasoning;
- channel egress;
- external effects.

### B. Fifteen-family overlay

Overlay the actual symbols/stores onto the module families. Show mixed components
with multiple edges rather than pretending they belong to one box.

### C. Target thin-client placement

Show the local Omega loop consuming declared ports with candidate local and remote
providers. Mark private/local-only flows, secret boundaries and shareable flows.

### D. Two sequence traces

At minimum:

1. current and target `query` flow;
2. current and target named tool/reasoning execution flow.

Each target trace must distinguish acceptance, persistence, execution, result,
acknowledgment and retry where applicable.

## 9. Remote-placement assessment

Score every candidate remote cut using explicit criteria, for example 0–3 each:

- interface fit;
- state-owner clarity;
- deterministic/replayable semantics;
- privacy suitability;
- payload size/bandwidth;
- latency sensitivity;
- local dependency coupling;
- external-effect risk;
- expected compute/offload benefit;
- existing Fusion provider maturity;
- migration difficulty;
- testability.

Do not collapse the score into an unexplained recommendation. Retain the component
scores and rationale.

Classify recommended placement:

- **must remain local initially**;
- **local by default, optionally remote**;
- **remote-safe after a named adapter/profile**;
- **good first remote prototype**;
- **not remote-safe under current semantics**.

The local thin client should normally retain:

- user/private policy decisions;
- credential and provider selection;
- current caller identity and authority mapping;
- the agent loop's task/correlation state;
- private data unless an explicit policy authorizes delegation.

Do not assume that “remote” means “on chain.” Remote providers may be an authorized
service, DA provider, worker, or chain adapter. Select placement from required
properties.

## 10. Required mismatch analysis

Explicitly analyze these likely semantic mismatches:

1. mutable `forget/update` versus immutable AtomStorage;
2. vector similarity query versus exact-attributes Search profile;
3. promotion/LTM ranking versus integer STI Attention profile;
4. direct Chroma STV mutation versus evidence-ledger BeliefRevision;
5. timestamp links versus typed Relations with stable refs;
6. flat history text versus sequenced EpisodicMemory records;
7. arbitrary `metta`/shell execution versus allowlisted DelegatedExecution;
8. best-effort channel buffers versus durable Messaging;
9. prompt skill list versus Registry/Resolver;
10. provider/environment variables versus trusted Authorization/composition;
11. broad NAL rule set versus the bounded current PLNKernel profile;
12. current record IDs/timestamps versus scoped stable interface references;
13. current local file/database assumptions versus remote failure/retry behavior.

For each mismatch choose one of:

- preserve via compatibility facade;
- introduce a new named profile;
- split one Omega command across multiple module operations;
- keep local;
- defer pending product decision;
- add a genuinely missing interface.

Do not prescribe data migration in this task.

## 11. Candidate compatibility facade

Design—but do not implement—a local `OmegaModuleFacade` layer that preserves the
existing MeTTaClaw command vocabulary while consuming declared ports.

Specify the proposed facade operations and their composition, for example:

- `remember(text)`;
- `query(text)`;
- `link(memory, episode)`;
- `support(memory, episode)`;
- `promote(memory)`;
- `send(message)`;
- `invoke_tool(name, arguments)`;
- `apply_reasoning(profile, premises)`.

For each facade operation state:

- which module ports it calls;
- which owner commits what;
- what remains local;
- what may be remote;
- idempotency/correlation requirements;
- error mapping back to existing Omega behavior;
- privacy and authorization requirements;
- whether existing semantics can be preserved exactly.

The facade is a compatibility design, not a new universal module and not an
`execute(anything)` route.

## 12. Select—but do not implement—the first remote slice

Rank at least three candidate slices and recommend one for the next implementation
milestone.

Include at least:

- a low-risk external tool operation such as web search through bounded
  DelegatedExecution;
- a core memory/read slice;
- a named NAL/PLN reasoning operation.

The recommendation should maximize architectural value, not only ease.

For the recommended slice provide a prospective acceptance test that proves:

- actual MeTTaClaw command invocation;
- unchanged caller behavior at the compatibility facade;
- explicit selected provider/profile;
- local versus remote placement switch by composition only;
- current authority and private-data policy;
- stable request identity and bounded retry;
- no duplicate logical effect;
- result validation;
- provider unavailability and restart handling;
- local fallback only when explicitly allowed by policy;
- no hidden direct access to the old provider's files/database.

Do not start that implementation under this handoff.

## 13. Validation and evidence

Run only the checks needed to validate the map:

- parse/import or baseline startup where safely available;
- source symbol extraction;
- call/reference search;
- existing tests, if any;
- small non-mutating probes in disposable state when required.

Do not use real user history, production channel credentials, private chats, or
paid external calls merely to prove the map. Synthetic configuration and fixtures
must remain labelled.

Every mapping claim must cite source symbols and, where available, executed evidence.
Unknown runtime behavior remains `UNASSESSED`.

## 14. Deliverables

Add a single review area, preferably under
`docs/omega-adoption/mettaclaw-neoclaw/` in `fusion-module-interfaces`, containing:

1. `README.md` — executive mapping and conclusions;
2. `mapping-ledger.json` — complete machine-readable ledger;
3. `command-map.md` — every Omega command and its module composition;
4. `state-ownership.md` — current stores, writers/readers and hidden coupling;
5. `remote-placement.md` — scored placement analysis and ranked candidates;
6. `interface-gaps.md` — profile gaps and out-of-inventory capabilities;
7. `diagrams.md` — current, overlay, target and sequence diagrams;
8. `source-state.json` — exact commits/dependencies/worktree status;
9. `evidence.md` — commands run, outputs, limitations and unassessed areas;
10. `next-slice.md` — one recommended bounded implementation brief outline.

Optionally generate a CSV view from the JSON ledger, but the JSON is authoritative.
Do not create another presentation in this task unless explicitly requested.

## 15. Acceptance gates

| Gate | PASS condition |
|---|---|
| SOURCE_PIN | Exact MeTTaClaw, Fusion, PeTTa, Chroma adapter and relevant dependency identities recorded; dirty/unpinned inputs explicit. |
| COMPLETE_INVENTORY | All exported commands, imported providers, state stores, background activities and external effects are represented or explicitly excluded with reason. |
| SYMBOL_TRACE | Every mapping row cites concrete files/symbols and actual call/dependency paths. |
| MODULE_MAPPING | Components are classified as provider, consumer, facade, orchestrator or gap; no forced one-file/one-module assignment. |
| COMMAND_COMPOSITION | Each user-visible Omega command maps to the ordered module operations and commit/effect boundaries it requires. |
| STATE_OWNERSHIP | Authoritative state, writers, readers and mixed-owner violations are explicit. |
| PROFILE_DISCIPLINE | Existing Fusion profiles are distinguished from proposed profiles; similarity by name is not called conformance. |
| REMOTE_PLACEMENT | Each candidate has scored placement, privacy, latency, failure and migration analysis. |
| GAP_DISCIPLINE | LLM, embedding, perception, tool catalogue/sandbox and other uncovered capabilities are explicit rather than hidden in DelegatedExecution. |
| TARGET_ARCHITECTURE | Thin-client target and two end-to-end target sequences are coherent and preserve owner boundaries. |
| NEXT_SLICE | At least three candidate slices are compared and one bounded next milestone is recommended with prospective acceptance tests. |
| NO_RUNTIME_CHANGE | No runtime behavior, data, profiles, journals or external deployments changed. |
| REVIEW_PACKET | All deliverables agree and are ready for human review. |

## 16. Required final report

End with:

- exact source/worktree identities;
- inventory counts by classification;
- module-family coverage from the **Omega mapping**, not the bounded reference
  denominator alone;
- list of mixed-responsibility components;
- list of genuine interface/profile gaps;
- placement recommendations;
- the recommended first remote slice and why;
- unassessed or blocked areas;
- files created;
- commands/checks executed;
- all gate outcomes.

Do not state that Omega is modularized or remote-capable merely because a map was
written. Report `READY_FOR_MAPPING_REVIEW` when the packet is complete, then stop.
