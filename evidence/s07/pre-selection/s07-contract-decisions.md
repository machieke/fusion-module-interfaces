# S07 contract decisions and unresolved selection

**Status: partial contract preparation; no selected or registered S07 runtime.**
The starting checkout is `3fc1af31f2d64583fe4c873b6b656dad2d6b1275`.
The [S07 brief](../../../codex_neoclaw_s07_model_completion_adoption.md)
requires resolution of one authorized backend and finite test budget before
expanding implementation. Neither is yet supplied. The existing local Ollama
installation is a discovered candidate, not authorization or a verified selected
runtime. No generation, download, SDK installation or hosted account probe ran.

## Executed native contract findings

The original source is MeTTaClaw
`2af37c3fec18613de54ca42fde2382a9087d4524`, `lib_llm_ext.py` SHA-256
`9c819f2d15aa36277548d0d9e7a146c07399cb17e6e7edee694284421b097f5d`.
The original loop's nominal `LLM=gpt-5.4`, `maxOutputToken=6000` and
`reasoningMode=medium` do not select the actual model/options in its Anthropic,
OpenRouter or ASI branches. Those branches call wrappers with hardcoded models:

| Native callable | Model literal in pinned source | Configured native endpoint |
|---|---|---|
| `useClaude` | `claude-opus-4-6` | `https://api.anthropic.com/v1/` |
| `useOpenRouter` | `z-ai/glm-5.2` | `https://openrouter.ai/api/v1` |
| `useMiniMax` | `minimax/minimax-m2.7` | `https://inference.asicloud.cudos.org/v1` |

These are historical source literals, **not current availability claims**. No
endpoint compatibility or current provider support for these options is asserted.
All three wrappers call `_chat` with `max_tokens=6000` and
`extra_body={enable_thinking: true, thinking_budget: 6000}`. No temperature, seed,
native tool definitions, explicit streaming flag or SDK retry override is supplied.
SDK defaults therefore remain an unresolved part of any original live recipe.

The checked `_chat` first removes `<tool_call>`, replaces `<arg_value>` and
`</tool_call>` with spaces, removes `</arg_value>`, and splits at the first
`:-:-:-:`. It emits system then user messages, retaining further separators.
Whitespace-only user input becomes `EMPTY / NO NEW USER INPUT.`. `_clean` replaces
`_quote_` and `_apostrophe_`. The original helper reads only choice zero's content;
it neither validates truncation/refusal nor retains usage. It retries null content
up to five helper calls with one-second sleeps. Actual SDK retries are separate
and were not executed by the oracle.

The new pure `NativeChatText` helper extracts those exact building statements and
keyword expressions from hash-checked source. Its successful request and rendering
match the independent oracle, which executes the original whole helper against
recorded responses. The extraction executes no SDK client, sleep, media or embedding
initialization. It neither selects a backend nor authorizes, generates, captures,
parses or executes a completion. It rejects null rendering rather than retrying.
That is a deliberate prerequisite for the future one-reservation contract, not a
claim that durable invocation has been implemented.

## Proposed owner and operation contract

The extension remains **X01 ModelInference**, outside the fifteen-family inventory.
Its proposed interface is `complete` plus `observe`. The selected profile,
descriptor, model options, context/token accounting, runtime pin and application
composition version remain unresolved; none is advertised by the live catalogue.
No `/9` application or HTTPS route is registered in this delivery.

The following are implementation requirements, not exercised provider guarantees:

| Boundary | Required owned state and contract |
|---|---|
| Native application | One model-call occurrence per durable S06 processing assignment, allocated before commands; exact raw/transformed prompt, selected context and original input deadline; captured provider receipt and native proposal; whole-batch decision. |
| ModelInference | Exact accepted input, selected model/options, current principal/scope and descriptor; one durable backend reservation; retained response/outcome. No application, C1/C2 or Attention database access. |
| Backend adapter | One source-checked SDK/runtime mapping with all automatic retries disabled; bounded response validation, raw text and necessary accounting only. |
| Local cognition | Existing source, belief and priority owners unchanged. Generated responses cause no implicit observation, revision, promotion or index rebuild. |
| Channel | Existing separate payload/mailbox/application commits and one reserved socket send. Model completion never implies external delivery. |

`complete` must carry a closed request with interface/profile/selection, trusted
principal, scope, session, model-call occurrence, native input occurrence/slot,
exact ordered text input, original absolute deadline and selected fixed limits.
The caller retains local view/context identifiers; private identifiers must not be
included in a remote request merely to bind it. An approved synthetic context
binding may be transmitted only under explicit consent. Model/endpoint/credentials,
options and permitted tools come from operator composition, not generated text.
Changed input under an identity conflicts. Prompt text alone is never identity.

`observe` must identify the retained accepted call under current authority. It can
release a captured result after expiry but cannot reserve generation or create
missing commands. Result validation must bind occurrence/request/selection, exact
raw provider text and separately versioned native rendering, selected and observed
model, optional request ID, known-or-unknown usage, finish reason and explicit
outcome. Null/empty/refused/truncated/multiple-choice/tool/media responses must not
be repaired into successful commands. Hidden reasoning must not be stored.

Before either a remote authorizer or generator sees input, the caller must approve
the complete raw and transformed prompt against trusted synthetic components and
the actual recipients. A `synthetic=true` field or private-text hash is not consent.
The next prompt must retain the actual tool result, not a test-supplied answer.

## Required lifecycle and pending tests

The application must commit the exact prompt before `complete`; the provider must
commit its one reservation before any backend request escapes. Provider response
capture precedes its reply, and application result capture precedes the unchanged
native parser and command admission. Interrupted pre-capture reservations remain
spent/unknown. Captured results replay exact bytes with no regeneration, model
switch, new identity, deadline reset or refund. Late capture may remain diagnostic
but cannot create a missing late command. Session count/token/byte/time bounds must
survive restart. These mechanisms remain **NOT_IMPLEMENTED** here.

Whole-batch validation must admit only the exact selected existing S01 expression
and S06 approved-body send subset, before any `eval` effect. The visible skill
subset must be an explicit new prompt/profile decision. Existing arbitrary MeTTa,
shell, memory mutation and configuration commands are not implicitly authorized.
The parser/repair path, nested expressions, mixed batches, Unicode, refusal,
revocation, credential substitution and captured-result rejection require tests.

Both local and same-host HTTPS ModelInference placements must use one selected
backend and the same caller. Model computation location must be stated separately.
The new selected socket guard must enumerate the model endpoint without loosening
S06 direct-IRC restrictions. Provider keys/assets must be absent from the HTTPS
caller. Real post-capture native recovery and real IRC → model → S01 → next model
input → approved send → peer observation are mandatory remaining gates.

No implementation is inferred from this design. The [S07 report](s07.md) and
[gate record](../../../evidence/s07/verification.json) distinguish the executed
source/fixture work from these blocked and unrun requirements.
