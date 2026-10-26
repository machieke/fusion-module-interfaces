# Retrieval runner and frozen campaign

This implements the runner missing at `9816873d5bb605c9c03be5f65baef7410c8cce0f`. It does not authorize or run live generation. The historical `retrieval_preparation` entrypoint and disabled proposal remain generation-disabled. No module family or adopted operation is added.

## Entrypoints

Use the repository root and its pinned integration Python:

```sh
artifacts/s03/venv/bin/python -m integration.neoclaw.preparation_guard \
  --guard-evidence evidence/retrieval-runner/guard.json -- \
  artifacts/s03/venv/bin/python -m unittest -v \
  tests.test_retrieval_disclosure.RetrievalDisclosure.test_guard_blocks_execution_and_host_network_before_tests

artifacts/s03/venv/bin/python -m integration.neoclaw.preparation_guard -- \
  artifacts/s03/venv/bin/python -m integration.neoclaw.retrieval_runner qualify \
  --root artifacts/retrieval-runner/NEW-RECORDED-CAMPAIGN \
  --evidence artifacts/retrieval-runner/NEW-RECORDED-REPORT.json

FUSION_RUNNER_NATIVE=1 artifacts/s03/venv/bin/python \
  -m integration.neoclaw.preparation_guard -- \
  artifacts/s03/venv/bin/python -m unittest -v tests.test_retrieval_runner_native

artifacts/s03/venv/bin/python -m integration.neoclaw.preparation_guard -- \
  artifacts/s03/venv/bin/python -m integration.neoclaw.retrieval_runner prepare \
  --root artifacts/retrieval-campaigns/NEW-DISABLED-CAMPAIGN

artifacts/s03/venv/bin/python -m integration.neoclaw.retrieval_runner inspect \
  --manifest artifacts/retrieval-campaigns/NEW-DISABLED-CAMPAIGN/manifest.json
```

`qualify` explicitly selects authored responses and creates **test-only** authority in a fresh recorded campaign. Production `execute` rejects that campaign kind and authority. The denial guard creates a separate network namespace, masks known generative executables/assets/service launchers, and verifies an owned host sentinel is inaccessible. Tests never use a real model endpoint to prove denial.

`prepare` creates three memories through native `remember`, seals the ready view, removes write authority, and creates two fresh measured compositions. It retains the original owners and their authoritative records. It creates no measured model/application journal, no call reservation, and no occurrence deadline. Its setup model/channel responses and creation/promotion clocks are fixtures; native memory dispatch, E5, Chroma and DeTTa are real.

## Placement and ownership

The same native `/10` consumer is used for both planned sessions. Only ModelInference placement changes: local, then certificate-checked same-host HTTPS. Mailbox placement remains HTTPS; Embedding, Search, AtomStorage, C1/C2 and Attention remain local. Both sides use generated credentials. This is neither multi-host deployment nor live default Omega startup.

The application exposes committed diagnostic observations from its own journal. ModelInference and the IRC bridge expose their own read-only observations. The runner does not query foreign databases or feed diagnostic records back into native retrieval. Model acceptance, reservation, response capture, application capture, command admission, output acceptance, socket outcome and independent peer receipt remain separate observations.

The campaign ledger links four UUID5 model occurrences to two predeclared sessions. Write-once attempt claims prevent another backend evaluation after a restart or projection reset. Existing ModelInference journals remain authoritative for reservations and captures, including a reservation lost before the campaign backend was entered. No capture is stored in a replacement result owner. Operator execution is locked; claims are independently locked and fsynced.

The first instruction is sent once after native readiness. The second instruction is sent only after the actual query has committed and the independent evaluator finds the target fact in that capture. The native application constructs the next prompt and disclosure receipt. The manifest freezes that construction rule, not invented second-prompt bytes. The observer obtains the actual admitted `send` body, matches that body against the independent peer's exact sender and channel, then evaluates factual correctness. A wrong permitted reply can be delivered and still fail.

Observers are bounded separately from model/tool deadlines. They cannot renew deadlines, create an occurrence, refund a reservation or authorize retransmission. A bridge's `unknown` socket outcome stays unknown even when independent peer evidence is available. A reserved send is never retried automatically.

## Future authority and prerequisites

The final report identifies the actual canonical manifest, digest, two sessions and four slots. The published manifest is a byte-identical review copy of the retained machine-local original. The machine-local owner journals, index, credentials and private TLS keys stay under the ignored campaign artifact directory. Removing or rebuilding those records invalidates this campaign; a new setup needs a new freeze and approval.

`approval-request.UNISSUED.json` is a request template, not approval. Only after separate explicit user authorization may the trusted operator supply `approval.json`, binding:

- `authority`: `EXPLICIT_USER_APPROVAL`;
- the exact `campaign_id`, `manifest_sha256`, ordered four slot names and `max_generations: 4`;
- the actual `user_statement` granting those calls;
- `not_before_ms` and `expires_ms`, defining an authorized window no longer than one hour.

There is no production approval in this delivery. An enabled flag, a passing test, possession of a manifest hash or a test authority is insufficient. Missing or mismatched authority fails before constructing a real backend, reserving a call or contacting a runtime. Source/configuration/TLS drift also refuses execution. The model-owner expiry is bound once at approved activation; original per-occurrence deadlines are set only by native input acceptance.

The future command is:

```sh
artifacts/s03/venv/bin/python -m integration.neoclaw.retrieval_runner execute \
  --manifest /ABSOLUTE/CAMPAIGN/manifest.json \
  --approval /ABSOLUTE/CAMPAIGN/approval.json \
  --evidence /ABSOLUTE/CAMPAIGN/execution-report.json
```

This command connects to the existing pinned Ollama backend at the frozen loopback port, after approval and integrity checks. It does not launch or warm up a model. Current runtime availability is `NOT_CHECKED`. Before a later authorized activation the operator must arrange the pinned isolated runtime and verify all required local assets; no runtime startup or readiness contact is authorized by this document. No fixture fallback, model substitution, hidden retry, prompt repair, replacement session or deadline extension is provided.

The selected historical identity remains Ollama `0.40.0+mlx.cpu.1`, `qwen3.8:27b`, model digest `9a8921f5b297f01451509b60e4a7e754674fe40d4a64dd9f89fc4a56c4fc5ee1`, and `neoclaw-ollama-qwen38-text/2`. The exhausted historical twelve-call allowance remains exhausted. This campaign proposes four **new** slots and currently authorizes zero.

## Evidence interpretation

The final preparation report gives exact test-source hashes and distinguishes methods, repeated runs, two-placement scenarios, authored evaluations and real E5 calls. Setup and fixture journals are not the frozen campaign's measured journals. Failed exploratory runs remain recorded, including a fixture masking check and a bounded setup observer expiry. No test of this runner proves real-model usefulness. Historical S07 failures, usage uncertainty and diagnostic limitations remain unchanged.

This work does not modify the historical fifteen-family denominator, X01/X02 inventory or command authority. It adds no memory migration, inference, model, channel, scheduler or chain operation.
