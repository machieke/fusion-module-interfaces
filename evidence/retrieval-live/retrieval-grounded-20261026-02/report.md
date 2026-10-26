# Frozen campaign execution: retrieval-grounded-20261026-02

Both declared sessions passed. The unchanged runner was invoked once and exhausted exactly the four authorized slots. All temporary processes stopped.

- Implementation: `66366cb4ed262ab8a87b96540d5c17fc8f0977ea`.
- Manifest SHA-256: `0b75644c3b0e198fc606bb3b781087a2048a40f21b67b36bd7a5a1000465adb1`.
- Separate approval: [approval.json](approval.json), SHA-256 `b8b5e1b295efd7e6b89ab7bfdbe1f785081cdee0696cbbe3833b6b12f0c08103`.
- Nonrenewed approval window: 2026-10-26T13:07:54.665+00:00 through 2026-10-26T14:07:54.665+00:00.
- Isolated runtime active: 2026-10-26T13:10:27.236+00:00 through 2026-10-26T13:16:07.218+00:00.

| Session | Captures | Admitted commands | Retrieval | Actual query in next prompt | Correctness | Independent peer |
|---|---:|---:|---|---|---|---|
| Local | 2/2 | query + send | PASS | PASS | PASS | observed once |
| Same-host authenticated HTTPS | 2/2 | query + send | PASS | PASS | PASS | observed once |

Both actual parsed/admitted send bodies were `Synthetic answer: amber cabinet.` The independent peer received that exact body from omega on the frozen IRC route. Output permission, factual correctness, socket-write outcome and peer receipt were assessed separately. Each bridge reserved one send and recorded `socket-write-returned`; each application accepted one output and acknowledged both inputs.

The first prompt did not contain the target fact, setup history or captured retrieval result. The four equally eligible reply strings remained in the frozen policy. Native query captured authoritative payloads from the retained generated corpus; that exact captured projection appeared in each second prompt. Both queries retained view `d7de349e0243de6d8443a8c0edd79beaf83b7f3ba219c9667a1eb247cfc355f2`. Real native dispatch, E5, Chroma, DeTTa, isolated IRC and authenticated HTTPS were exercised. Historical setup fixtures remain setup evidence; the four measured responses were real model generations.

| Slot | Backend response time (s) | Reported input tokens | Reported output tokens |
|---|---:|---:|---:|
| local-query | 52.186 | 257 | 8 |
| local-reply | 59.443 | 637 | 8 |
| network-query | 26.531 | 257 | 8 |
| network-reply | 59.477 | 637 | 8 |

Totals: four durable reservations, four backend entries, four successful `/api/chat` requests, four owner captures and four command admissions; 1788 reported input tokens and 32 reported output tokens. Reasoning tokens and provider request IDs remain unknown. Each application spent four of its eight RPC attempts; those RPCs are not additional model generations. All responses were captured before their unchanged 300-second deadlines, and owner/application intents and response bytes agree.

Validation passed before runtime startup: 189 source files, 212 configuration/corpus/TLS bindings, all 15 runtime assets including full model/projector hashes, pinned runtime source/build recipe, isolated asset aliases and free frozen ports. The actual serving binary and all eight selected llama-server runtime files matched their pins. Post-run frozen-input drift is empty. Policy expiry was initialized only through the already-frozen activation rule. No source, manifest, prompt, deadline, command-policy or model change was made.

The runtime used the existing S07 isolated recipe at loopback port 48173 with cloud disabled and private home masked. Eight non-generating GET requests checked version/tags inside the existing backend. There was no warm-up, hidden generation, retry, replacement, response repair, fixture fallback or resend. The frozen CLI and exact invocation are retained in [operator-execution.json](execution/operator-execution.json).

All campaign process IDs are absent, all six frozen listener ports are closed, and no campaign process remains. Unrelated services were untouched. Original owner journals, responses, claims, peer traffic and raw logs remain in the ignored canonical campaign artifact directory; this packet copies diagnostic evidence without credentials or private TLS keys. Historical evidence is unchanged.

Limitations retained without changing the frozen implementation:

- Same-host authenticated HTTPS; no multi-host or full-default Omega claim.
- Two successful sequential synthetic workflows are not a general model-usefulness benchmark; runtime cache differs between sessions.
- Frozen evaluator hardcodes model_usefulness=NOT_RUN; raw reports preserve it. Live execution is independently evidenced by REAL_MODEL reports, durable captures and four successful runtime POSTs.
- Four MLX/OpenBLAS/Fortran libraries loaded by the Ollama host are outside runtime_required_files; observed hashes are retained, not retroactively added to the freeze. All fifteen explicitly frozen runtime files matched.
- No process-kill or captured-result recovery was induced in this live campaign. Preparation recovery evidence remains historical and unchanged.
- Provider request IDs and reasoning-token usage were unavailable and remain null.
- Initial system-Python offline approval helper failed on Python compatibility before recording approval or contacting runtime; the pinned integration Python recorded the single approval.

No additional tests or runtime sessions were run after completion. No commit or push was performed under this execution-only authorization.

```text
CAMPAIGN_STATE=COMPLETED_ALL_FOUR_SLOTS_SPENT
LIVE_MEMORY_WORKFLOW=PASS_2_OF_2
LIVE_GENERATIONS=4
REMAINING_GENERATION_AUTHORITY=0
TEMPORARY_PROCESSES=STOPPED
```
