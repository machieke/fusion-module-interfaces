# S07 selected local model contract decisions

Status: bounded S07 demonstrated with real local/HTTPS generation and retained failures. Twelve attempts produced ten captures, three approved peer-observed replies and two native capture recoveries. Two unsupported reply commands were rejected. Historical blocked/timeout source packets remain preserved.

## Selection and intentional differences

The operator selected **local Ollama `qwen3.8:27b`**. X01 uses `model.inference/1.0.0`, historical completion profile `neoclaw-ollama-qwen38-text/1` and CPU profile `neoclaw-ollama-qwen38-text/2`, and fresh application composition `controlled-native-loop/9`. It does not reuse a hosted model profile or change Fusion PLN/NAL, Embedding, Search, C1/C2 or Attention profiles.

The pinned native `_chat` statements still determine marker removal, first `:-:-:-:` split, empty-user handling and system/user order. `_clean` still determines quote-placeholder rendering. Recorded native wrapper oracles verify those functions without eager hosted clients. The selected adapter intentionally changes the backend/model and disables thinking, streaming, truncation and speculative drafting. It keeps the native 6,000 output-token ceiling, fixes context at 32,768 and preserves the model's recorded sampling defaults. No tools, images, arbitrary URLs or provider options are model arguments.

A 12,288-byte native-prompt bound leaves substantial room below the selected context window, including the two-role Qwen scaffold and 6,000 generated tokens. The pinned tokenizer is byte-BPE; the actual approved scaffold is much smaller. Returned prompt/output counts are validated. One real CPU attempt reported 295 prompt tokens and 26.42 seconds of prompt processing; no complete response or final usage was captured. The Ollama API [documents nonstreaming chat, options and usage fields](https://docs.ollama.com/api/chat); the locally verified source is authoritative for this custom binary.

The selected prompt shows exactly the original `send` and `metta` skill descriptions. Its explicitly new synthetic task instructions request native command lines. The original `getContext`, `balance_parentheses`, `sread`, `HandleError`, skill execution and `RESULTS/COMMAND_RETURN` handoff remain native. An initial recorded fixture used a wrapped batch incorrectly; the real parser rejected it. The corrected instructions follow native line syntax. No generated response was resampled.

## Ownership and commits

The existing application database owns input slot, model UUID (session plus slot), selected native prompt including TIME, source occurrence, local context view, provider receipt, native normalized text and parsed proposal. It owns no generation arithmetic. Equal prompts in different admitted slots have different identities. Restart uses the first committed prompt and original channel deadline.

The completion owner has its own sealed SQLite WAL/FULL journal. It commits exact intent acceptance, one reservation, and validated response capture independently. It never reads cognitive or application journals. `complete`, `observe` and narrow current `authorize` are the only operations. Exact descriptor, principal, scope, session, model digest, limits and intent bind replies. The HTTPS route is `/s07-model`, using the existing certificate-verified transport/host mechanisms and generated bearer credentials.

Application capture precedes parsing and command admission. Raw observed text is retained separately from native cleaned text, normalized parser input, parser representation and authorized AST. Parse failure and whole-batch rejection remain attached to the captured response. Only the operator-selected exact S01 expression and approved S06 send body can execute. A mixed unsupported batch performs no first command. Completion is never automatically C1 evidence or a priority adjustment.

## Bounds and recovery

### Explicit CPU deadline selection

After the first real 30-second timeout, the user explicitly requested a feasible
deadline and all twelve authorized calls. Fresh CPU trials select
`neoclaw-ollama-qwen38-text/2`: a five-minute accepted-input/model deadline. Its
descriptor feature and bound limits differ from `/1`. The `/1` descriptor, limits
and 30-second behavior remain unchanged; a `/2` intent cannot enter a `/1` owner,
and a sealed application or owner cannot change profiles. Both use the supported
`controlled-native-loop/9` application, whose binding already freezes the exact
model profile and descriptor. No populated journal is upgraded.

Five minutes is a bounded allowance for this short command workflow, based on the
observed 26.42-second prompt evaluation; it does not promise that all 6,000 allowed
output tokens will finish. Model, preprocessing, sampling, context window, token
ceiling and one-generation reservation are unchanged. Tool operations and local
context preparation retain their 30-second deadlines. The selected model profile
determines the input deadline once when the application accepts the IRC occurrence;
replay never extends it. The failed `/1` occurrence stays spent with its original
deadline and unknown usage.

The first CPU plan allocated eleven remaining calls. After the additional adapter
validation failure and one captured unsupported reply, the explicit remaining
plans accounted for every spent call; the final total is twelve attempts. The independent socket peer sends the second input
after the first native command has completed, so a real new event is captured
without expiring in the unchanged S06 ingress queue. Disposable peer/bridge and
worker lifetimes are longer, bounded test-actor lifetimes; they do not reset any
accepted work deadline. Historical actor defaults remain unchanged.

The shared endpoint's only runner slot was observed busy before this campaign
admitted any new input. One load-only request timed out; a second readiness wait
was deliberately interrupted. Both consumed zero generation reservations. A
task-owned Ollama process was then selected before admission, using the identical
verified executable and existing model blobs, a fresh generated model manifest
directory, cloud features disabled, an empty ephemeral home and a loopback-only
listener. A fixed-port launch attempt found the port occupied and exited before
starting a server; the successful launch selected an available port. Existing
services were not stopped or reconfigured.

The `/2` runtime lock permits an operator-selected **loopback port only**, hashes
the selected manifest, and freezes this configuration in the provider seal. The
application binding freezes the declared backend port; changing it during replay
is a conflict. `/1` retains port 11434. The same-host HTTPS caller masks the
additional model directory and probes refusal of the actual selected raw backend
port. Generation arguments cannot select a host, port, asset path or model. The
standalone [executed launcher](../../../evidence/s07/isolated-ollama-launch.py) is
a bounded test recipe for this exact binary/model, not a serving framework.

One reservation permits at most one adapter generation request. No helper, SDK or caller automatically regenerates. The pinned Ollama runner performs one generation POST; readiness/status polling and model-loading recovery are separate from generation. A failure or kill after reservation and before capture is unknown/spent, even if no request escaped. An observed adapter error is recorded separately from an interruption with no observed error. No refunds, new hidden identities or deadline changes are permitted.

The application allows at most eight completion RPC reservations per occurrence, including authorization checks. The profile allows at most four input slots per session and twelve accepted calls per sealed owner; the supported demonstration narrows each fresh session to **two** calls. The owner seals the session list, finite count and expiration. The initial three-case live plan had six calls within the twelve-call authorization, 6,000 output tokens reserved per call, and the unchanged 30-second accepted-input deadline. Its one bounded empty-chat model load occurs before input admission. One load-only request and one generation request ran. The first generation timed out, so the campaign stopped with eleven authorized calls unused.

Captured results can be observed after expiry, with current authority. Late captures are labelled and cannot create missing commands. Previously accepted command recovery retains its own original deadlines. S06 durable acceptance, socket-write result, recipient observation, unknown-send state and no-automatic-resend policy are unchanged. Unknown token usage stays null; no billing or cancellation guarantee is claimed.

## Disclosure and placement

Operator configuration approves the complete public scaffold, fresh synthetic channel inputs, exact selected memory presentations and a narrow numeric S01 feedback grammar. The caller additionally checks feedback against its actual owner-validated previous projection and retained Attention context. Any disallowed history, memory, input or transformation marker is rejected before model authorization or submission. The current positive recipe has an empty promoted set obtained through real Attention/context machinery; it does not claim positive disclosure of populated private memory.

The HTTPS caller masks the selected GGUF/manifest and provider key/state, refuses direct Ollama access, and lacks the historical scripted model import. The model provider masks the native caller workdir, corpus/provider root, mailbox and bridge roots. Local C1/C2/Attention remain local. These are verified filesystem masks plus trusted Python socket guards, not a hostile-host network sandbox. Both model and mailbox placements are same-host; no public service or multi-host claim.

## Compatibility and exclusions

Historical `/1`–`/8` compositions and profile meanings remain intact. `/9` requires fresh journals; no populated-state migration or adoption of old model state is supported. X01 adds no user command and does not enlarge the fifteen-family denominator or eight existing operation-adoption entries. No new cognition, vision, arbitrary execution, second channel, live default Omega or chain work is included.

## Final executed accounting

The original thirty-second timeout and later adapter-validation failure each
remain spent/uncaptured. Ten subsequent responses were captured; two proposed
unsupported reply command names and were retained/refused. Eight batches were
authorized, yielding five actual native deductions and three approved IRC replies.
Three full local/HTTPS workflows passed. Two real native SIGKILLs retained capture
identity, prompt, deadline and bytes without regeneration; the second recovery's
later new reply was independently rejected. No prompt/model change or repair
followed a semantic rejection. The explicit user instruction to use all twelve
continued only predeclared independent sessions.

Pinned `api.Metrics` and runner source expose `prompt_eval_cached_count`; its
omission from the original adapter allowlist was corrected. The counter is typed
and bounded by total input tokens, while the existing closed receipt remains
unchanged. The earlier rejected raw response was not retained, so attribution of
that exact failure remains an inference. The task-owned runtime was stopped after
the final call. See `evidence/s07/live-summary.json` and `verification.json`.
