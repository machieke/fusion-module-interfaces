# S07 selected local model contract decisions

Status: implemented and exercised with recorded model responses and real native pre-generation startup. **The first authorized real generation attempt timed out before capture at its original 30-second input deadline.** This is not S07 completion. The earlier blocked source-preparation packet is retained in `evidence/s07/pre-selection/`.

## Selection and intentional differences

The operator selected **local Ollama `qwen3.8:27b`**. X01 uses `model.inference/1.0.0`, numerical/model profile `neoclaw-ollama-qwen38-text/1`, and fresh application composition `controlled-native-loop/9`. It does not reuse a hosted model profile or change Fusion PLN/NAL, Embedding, Search, C1/C2 or Attention profiles.

The pinned native `_chat` statements still determine marker removal, first `:-:-:-:` split, empty-user handling and system/user order. `_clean` still determines quote-placeholder rendering. Recorded native wrapper oracles verify those functions without eager hosted clients. The selected adapter intentionally changes the backend/model and disables thinking, streaming, truncation and speculative drafting. It keeps the native 6,000 output-token ceiling, fixes context at 32,768 and preserves the model's recorded sampling defaults. No tools, images, arbitrary URLs or provider options are model arguments.

A 12,288-byte native-prompt bound leaves substantial room below the selected context window, including the two-role Qwen scaffold and 6,000 generated tokens. The pinned tokenizer is byte-BPE; the actual approved scaffold is much smaller. Returned prompt/output counts are validated. One real CPU attempt reported 295 prompt tokens and 26.42 seconds of prompt processing; no complete response or final usage was captured. The Ollama API [documents nonstreaming chat, options and usage fields](https://docs.ollama.com/api/chat); the locally verified source is authoritative for this custom binary.

The selected prompt shows exactly the original `send` and `metta` skill descriptions. Its explicitly new synthetic task instructions request native command lines. The original `getContext`, `balance_parentheses`, `sread`, `HandleError`, skill execution and `RESULTS/COMMAND_RETURN` handoff remain native. An initial recorded fixture used a wrapped batch incorrectly; the real parser rejected it. The corrected instructions follow native line syntax. No generated response was resampled.

## Ownership and commits

The existing application database owns input slot, model UUID (session plus slot), selected native prompt including TIME, source occurrence, local context view, provider receipt, native normalized text and parsed proposal. It owns no generation arithmetic. Equal prompts in different admitted slots have different identities. Restart uses the first committed prompt and original channel deadline.

The completion owner has its own sealed SQLite WAL/FULL journal. It commits exact intent acceptance, one reservation, and validated response capture independently. It never reads cognitive or application journals. `complete`, `observe` and narrow current `authorize` are the only operations. Exact descriptor, principal, scope, session, model digest, limits and intent bind replies. The HTTPS route is `/s07-model`, using the existing certificate-verified transport/host mechanisms and generated bearer credentials.

Application capture precedes parsing and command admission. Raw observed text is retained separately from native cleaned text, normalized parser input, parser representation and authorized AST. Parse failure and whole-batch rejection remain attached to the captured response. Only the operator-selected exact S01 expression and approved S06 send body can execute. A mixed unsupported batch performs no first command. Completion is never automatically C1 evidence or a priority adjustment.

## Bounds and recovery

One reservation permits at most one adapter generation request. No helper, SDK or caller automatically regenerates. The pinned Ollama runner performs one generation POST; readiness/status polling and model-loading recovery are separate from generation. A failure or kill after reservation and before capture is unknown/spent, even if no request escaped. An observed adapter error is recorded separately from an interruption with no observed error. No refunds, new hidden identities or deadline changes are permitted.

The application allows at most eight completion RPC reservations per occurrence, including authorization checks. The profile allows at most four input slots per session and twelve accepted calls per sealed owner; the supported demonstration narrows each fresh session to **two** calls. The owner seals the session list, finite count and expiration. The initial three-case live plan had six calls within the twelve-call authorization, 6,000 output tokens reserved per call, and the unchanged 30-second accepted-input deadline. Its one bounded empty-chat model load occurs before input admission. One load-only request and one generation request ran. The first generation timed out, so the campaign stopped with eleven authorized calls unused.

Captured results can be observed after expiry, with current authority. Late captures are labelled and cannot create missing commands. Previously accepted command recovery retains its own original deadlines. S06 durable acceptance, socket-write result, recipient observation, unknown-send state and no-automatic-resend policy are unchanged. Unknown token usage stays null; no billing or cancellation guarantee is claimed.

## Disclosure and placement

Operator configuration approves the complete public scaffold, fresh synthetic channel inputs, exact selected memory presentations and a narrow numeric S01 feedback grammar. The caller additionally checks feedback against its actual owner-validated previous projection and retained Attention context. Any disallowed history, memory, input or transformation marker is rejected before model authorization or submission. The current positive recipe has an empty promoted set obtained through real Attention/context machinery; it does not claim positive disclosure of populated private memory.

The HTTPS caller masks the selected GGUF/manifest and provider key/state, refuses direct Ollama access, and lacks the historical scripted model import. The model provider masks the native caller workdir, corpus/provider root, mailbox and bridge roots. Local C1/C2/Attention remain local. These are verified filesystem masks plus trusted Python socket guards, not a hostile-host network sandbox. Both model and mailbox placements are same-host; no public service or multi-host claim.

## Compatibility and exclusions

Historical `/1`–`/8` compositions and profile meanings remain intact. `/9` requires fresh journals; no populated-state migration or adoption of old model state is supported. X01 adds no user command and does not enlarge the fifteen-family denominator or eight existing operation-adoption entries. No new cognition, vision, arbitrary execution, second channel, live default Omega or chain work is included.
