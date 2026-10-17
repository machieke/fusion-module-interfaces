# Recommended next brief — bounded native NAL truth deduction

**Proposal only. Do not implement under the mapping handoff.** Select S01, DRAFT `neoclaw-nal-truth-deduction/1`, exposed through a named `nal_truth_deduction` execution profile and a separate pure kernel provider. This is a different profile/input shape from Fusion's guarded five-premise PLN. It does not replace that implementation or alter C2 beliefs.

The architectural test is whether the actual MeTTaClaw command can switch local/remote placement by composition while preserving admitted numerical behavior, current authority, owner commits and recoverable result identity. Two STVs are small; network overhead will likely outweigh compute savings. The selected function has an exact source/native oracle and avoids unresolved memory ownership. S02 web search lacks a stable numerical oracle; S03 memory reads need several missing profiles and a source feed.

Pin the implementation milestone's source revisions again. This map inspected MeTTaClaw `2af37c3fec18613de54ca42fde2382a9087d4524`, PeTTa `fea83178af3722666d2948d074591d10a3134f56`, SWI-Prolog 10.0.1 for isolated NAL probes, and Fusion `33388d20cb10c5f9878a463a6d0debba7949e35a`. These inspection pins are **not** proof that full Omega startup is reproducible. First resolve Janus, PeTTa/provider import requirements and a bounded startup recipe without introducing credential-dependent live calls into tests. Keep Fusion's existing PeTTa/PLN/SWI selections unchanged.

Scope:

- Recognize only `metta (Truth_Deduction (stv f1 c1) (stv f2 c2))` through the actual command/parser/evaluator-facing facade. Do not remote arbitrary `metta` text. Preserve local behavior for other expressions under existing policy.
- Admit exactly two finite, grounded STVs within the declared domain and byte bounds. Compile a fixed invocation of the pinned existing function; never implement a new numerical formula in the adapter.
- Introduce an explicit named operation/profile/input DTO. Do not route it through current `inspect_atom` or fabricate five belief snapshots. Keep pure numerical provider, execution journal, result payload owner, messaging and local caller receipt owner separate.
- Use generated, explicitly shareable inputs initially. No private episode, belief, vector, provenance, prompt, identifier or identifying hash leaves the client. Private-local-only profiles remain local and fail incompatible remote selection.
- Bound execution, retries, payloads, queue capacity and original absolute deadlines. Save selection and request identity before dispatch; no transparent fallback, unlimited retry, renewed budget or deadline.
- No migration, full NAL engine service, general shell/eval endpoint, new cognition, inference control, chain operation or unrelated infrastructure.

Prospective acceptance tests — **all unrun in this mapping task**:

| Gate | Required future experiment and observable result |
|---|---|
| Actual caller | Invoke the exact command through native MeTTaClaw parsing and the facade, not a direct Python helper. Compare legacy local and adapted local output on admitted STVs, including the `repr` formatting expected by the caller. Full runtime/import setup must be real and pinned. |
| Mathematical identity | Use the original `Truth_Deduction` symbol. Compare normal, zero/one boundary and decimal-rounding cases against pinned native execution. Reject NaN/infinity/out-of-range/malformed/extra arguments before execution. No changed arithmetic order. No truncation of broad `\|-nal` results because that dispatch is out of scope. |
| Explicit selection | Descriptor binds source/runtime/profile, operation, limits, privacy and guarantees. Wrong version/profile/dimensions of input, stale selection, undeclared operation and unsupported guarantees fail. Existing PLN profile must refuse this new input. |
| Placement switch | Same native caller command and same facade/profile operate with an in-process provider and an authenticated remote worker selected only by composition. Demonstrate separate processes/transport and block direct filesystem access to the old implementation's stores. Report fixture versus actual remote evidence separately. |
| Current authority | Test unauthenticated, wrong principal/scope/route, revoked-before-submit and revoked-before-read/ack. Client-supplied identity cannot confer access. Shareable-only remote provider rejects private placement; no keys in payload/log. |
| Stable intent | Persist request ID, canonical digest, profile/selection, correlation, reply route, deadline and bounded retry state before send. Same ID/same intent returns same logical job/result; same ID/changed intent conflicts. A second intentional request gets a distinct ID. |
| Independent commits | Kill caller after request persistence and after submission before acceptance receipt. Kill worker after acceptance, after numerical computation, after result payload commit, and after terminal/outbox commit. Recover by provider status/replay, not foreign DB access. Durable job acceptance and result bytes remain distinct commits. |
| Duplicate completion | Kill caller after durable completion receipt before ack; redeliver and drain repeatedly. Exactly one logical caller result, same result digest and same job identity; duplicate physical computation is allowed for this pure function and must not be misreported as exactly-once execution. |
| Bounds / outages | Provider unavailable, capacity exhausted, deadline expired and retry budget exhausted are typed states. Restart must not reset budgets/deadlines. Replaying a previously completed job may read its existing result; it cannot launch new work after deadline. |
| Result validation | Reject wrong request/profile/runtime/selection, malformed truth, oversized payload, wrong digest/ref/scope, forged completion and unrelated delivery. A failed validation never becomes a successful command result. |
| Policy fallback | Default deny fallback. If an operator explicitly enables same-profile local fallback, record the decision, retain request identity and ensure one terminal caller result despite a late remote completion. No fallback to existing five-premise PLN or arbitrary local eval. |
| Regression / isolation | Re-run appropriate M1–M5 contract and native regressions after the future change. Verify no changes to C1/C2/Attention/C4 owners, no inference or evidence admission, no chain use, no reads of private Chroma/history/promotion stores. |

Expected future evidence: exact source/build manifests, local/native and remote traces for the same admitted request, process-kill boundaries, current-authorization failures, result/receipt validation failures, duplicate replay proof and bounded outage behavior. Timing measurements may describe transport cost; do not invent a performance win. The mapping task stops before this work.
