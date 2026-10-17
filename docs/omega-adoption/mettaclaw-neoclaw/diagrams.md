# Runtime, module overlay and proposed placement

Solid arrows in the current diagrams are source-defined calls/data flows, not proof that a live provider was exercised. Dashed edges in the overlay/target identify proposed adoption. All target diagrams are **unimplemented design** and depend on new profiles where marked DRAFT. [Source ledger](mapping-ledger.json), [state owners](state-ownership.md) and [seam contracts](seam-contracts.md) define the details.

## A. Current runtime

```mermaid
flowchart TB
  Human["IRC / Mattermost ingress"] --> Buffer["Transport daemon + volatile consuming buffer"]
  Buffer --> Loop["mettaclaw: wake/cycle loop in RAM"]
  Prompt["prompt.txt + getSkills prose"] --> Context["getContext"]
  History["Flat history.metta"] --> Context
  Promotion["SQLite promotion value + wall time"] --> Context
  Chroma["Chroma: documents + vectors + time + links + STV"] --> Context
  Context --> Loop
  Context --> Export["promoted_memories.metta derived rewrite"]
  Loop --> Model["Hosted LLM clients / operator keys"]
  Model --> Parse["balance_parentheses + sread"]
  Parse --> Eval["eval: commands / arbitrary metta"]
  Eval --> Memory["remember/query/update/support/promote facades"]
  Memory <--> Chroma
  Memory <--> Promotion
  Memory --> Emb["Local E5 or OpenAI embeddings"]
  Eval --> NAL["Truth functions / NAL / temporal rules"]
  Eval <--> Space["Mutable executable persistent space"]
  Space <--> Disk["persistent.metta import / non-atomic export"]
  Eval --> Effects["shell / file tools / DDGS web search"]
  Eval --> Send["send: best-effort IRC / Mattermost"]
  Loop --> History
  Video["YouTube + sampler thread / ffmpeg"] --> Image["JPEG + motion overlay"]
  Image --> Vision["Fixed Anthropic image call"]
  Loop --> Vision
  Vision --> Parse
```

## B. Fifteen-family semantic overlay

Orange shared sources deliberately have multiple edges. Gray families have no current counterpart. Blue out-of-inventory boxes do not increase the denominator. Edges mean responsibility resemblance, **zero demonstrated Fusion conformance**.

```mermaid
flowchart LR
  Mem["memory.metta command composition"]:::mixed
  Chr["Chroma shared collection"]:::mixed
  Hist["history text + around_time"]
  Promo["promotion SQLite + decay"]
  Rules["Truth_* / NAL rules"]
  Channels["IRC / Mattermost buffers"]
  Tools["shell, files, metta, websearch"]
  A["AtomStorage"]
  R["Relations"]
  S["Search projection"]
  C1["EpisodicMemory"]
  C2["BeliefRevision"]
  K["PLNKernel"]
  C3["Attention"]
  Msg["Messaging"]
  Exec["DelegatedExecution"]
  Mem --> A & R & S & C1 & C2 & C3
  Chr --> A & R & S & C2
  Hist --> C1
  Promo --> C3
  Rules --> K & C2
  Channels --> Msg
  Tools --> Exec
  subgraph Absent["Six families without current counterpart"]
    DA["DA storage"]:::absent
    C4["InferenceControl"]:::absent
    Reg["Registry"]:::absent
    Res["CompatibilityResolver"]:::absent
    Auth["Authorization"]:::absent
    Chain["ConsensusFinality"]:::absent
  end
  subgraph Outside["Outside bounded inventory"]
    LLM["ModelInference"]:::outside
    Emb["Embedding"]:::outside
    Vis["Perception"]:::outside
    Cat["Tool catalogue / sandbox policy"]:::outside
    Agent["Agent loop / prompt / task context"]:::outside
  end
  Mem -. consumes .-> Emb
  Agent -. future consumers .-> Reg & Res & Auth
  classDef mixed fill:#ffdfae,stroke:#914900,color:#222
  classDef absent fill:#eee,stroke:#888,color:#333
  classDef outside fill:#dcefff,stroke:#3476a3,color:#222
```

## C. Target thin-client placement

```mermaid
flowchart TB
  subgraph Local["Local trusted Omega client"]
    Policy["User/private policy + caller/route mapping"]
    Selection["Provider selection + operator credentials"]
    Agent["Existing command vocabulary + agent loop"]
    Facade["Proposed OmegaModuleFacade"]
    Receipt["Caller request/correlation + validated receipt state"]
    Policy --> Facade
    Selection --> Facade
    Agent --> Facade
    Facade <--> Receipt
  end
  subgraph Private["Existing private-local-only placement"]
    Atom["AtomStorage / opaque DA"]
    Search["Search projection: exact now, vector DRAFT"]
    Relations["Relations: typed roles"]
    Belief["C1 provenance / C2 belief owners"]
    Rank["STI now, promotion profile DRAFT"]
  end
  Facade -->|"private reads and owner commands"| Atom & Search & Relations & Belief & Rank
  subgraph Candidate["Authorized remote worker - DRAFT profiles only"]
    Auth["Authenticated boundary + current policy"]
    Exec["Named execution owner: jobs / results / outbox"]
    Kernel["Pure pinned NAL Truth_Deduction"]
    Payload["Result payload owner"]
    Mail["Scoped completion mailbox"]
    Auth --> Exec
    Exec --> Kernel
    Exec --> Payload
    Exec --> Mail
  end
  Facade -. "generated shareable STVs only, no secret payload" .-> Auth
  Mail -. "validated completion / ack after caller persistence" .-> Facade
  subgraph Missing["Separate capabilities, no force-fit"]
    Model["ModelInference / Embedding / Perception contracts"]
    Catalogue["ToolDescriptor + execution policy"]
  end
  Selection -. "operator-controlled API secrets" .-> Model
  Facade -. "explicit disclosure policy" .-> Model
  Catalogue -. "typed local allowlist" .-> Facade
```

Current private modules are **not remotely selectable** in this diagram. A later memory cut requires new explicit privacy/profile compatibility. No DA owner receives application semantics, no chain arrow exists.

## D1. Current query

```mermaid
sequenceDiagram
  participant O as Omega query(text)
  participant E as Embedding helper
  participant C as Chroma adapter
  participant P as Promotion SQLite
  O->>E: embed(text)
  E-->>O: vector (profile unpinned)
  O->>C: query_with_ids_and_dists(vector,100 default)
  C-->>O: UUID/time/document/distance candidates
  loop candidate enrichment
    O->>P: read value and last time
    P-->>O: mutable score inputs
    O->>O: wall-clock power decay
    O->>C: query_linked_episodes(UUID), get_stv(UUID)
    C-->>O: timestamp list + mutable STV
  end
  O->>O: promoted top10 + nearest, unique, take20
  O-->>O: displayed tuples omit UUID and distance
  Note over O,C: No accepted request journal, shared snapshot, freshness receipt or page cursor
```

## D2. Target query (new vector/promotion profiles required)

```mermaid
sequenceDiagram
  participant O as Local Omega facade
  participant E as Selected Embedding port
  participant S as Vector Search owner DRAFT
  participant P as Promotion owner DRAFT
  participant R as Relations owner
  participant A as AtomStorage owner
  participant B as BeliefRevision owner
  O->>O: authorize private scope, bind profiles and request
  Note over O,S: Read acceptance = validation, not durable mutation acceptance
  O->>E: embed under exact model profile
  E-->>O: validated vector/profile
  O->>S: query(vector,k,minimum source head,cursor)
  S-->>O: refs/distances/generation/freshness
  O->>P: rank eligible refs at declared clock
  P-->>O: scores/policy/revision
  O->>R: outgoing(memory ref,limit,snapshot)
  R-->>O: relation refs/page/snapshot
  O->>R: getRelation(refs individually)
  R-->>O: typed endpoints
  O->>A: getMany(payload refs)
  A-->>O: immutable validated payloads
  O->>B: readBelief(claim,context,revision)
  B-->>O: validated belief snapshot
  O->>O: validate refs/versions, format legacy view
  Note over O,B: No global snapshot claim, reads have no mailbox ack
  opt lost response
    O->>S: retry same bound query/generation within budget
    S-->>O: same page or explicit expired/unavailable
  end
  Note over S,A: Index checkpoint persists only through owner maintenance/feed, query does not rebuild
```

## E1. Current named reasoning through general evaluation

```mermaid
sequenceDiagram
  participant L as Model output / Omega loop
  participant P as Parser
  participant M as metta handler
  participant K as Native NAL function
  participant H as History text
  L->>P: metta (Truth_Deduction ...)
  P-->>L: repaired s-expression
  L->>M: eval command
  M->>M: sread arbitrary expression
  M->>K: eval under Prolog inference count limit
  K-->>M: stv result
  M-->>L: repr result
  L->>H: append message/response after execution
  Note over L,H: No durable acceptance/result identity/ack, replay recomputes
  Note over M,K: Other expressions can invoke arbitrary effects, this trace is the pure subset
```

## E2. Target bounded named reasoning with independent owners

```mermaid
sequenceDiagram
  participant O as Native Omega facade / caller journal
  participant X as Authorized execution owner
  participant K as Selected pure NAL kernel
  participant A as Result AtomStorage owner
  participant M as Completion Messaging owner
  O->>O: validate allowlisted AST, persist exact intent/key/deadline
  O->>X: submit named operation + selected profile
  X->>X: authenticate, persist acceptance before reply
  X-->>O: durable accepted job ID (not result)
  opt caller loses acceptance / restarts
    O->>X: replay same key/digest/selection/deadline
    X-->>O: same job or current authorization error
  end
  X->>K: execute pinned Truth_Deduction with two STVs
  K-->>X: validated numerical result
  X->>A: create result with stable subkey
  A-->>X: committed immutable result receipt
  X->>X: commit terminal state + completion outbox
  X->>M: send completion under stable delivery identity
  M-->>X: durable mailbox acceptance
  O->>M: poll scoped route
  M-->>O: repeatable completion delivery
  O->>A: get and validate result/selection/digest
  A-->>O: result bytes
  O->>O: persist validated caller completion
  O->>M: ack delivery after caller commit
  M-->>O: ack receipt
  opt crash after receipt before ack
    O->>M: poll and recognize already committed completion
    M-->>O: same delivery
    O->>M: repeat ack, no second logical result
  end
  Note over X,K: Pure computation may repeat, durable logical result must not
  Note over O,M: No C1/C2 admission, C4 inference selection, deadline reset or implicit fallback
```
