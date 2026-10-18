# Codex handoff — S01.1: use the adopted operation from the real MeTTaClaw loop

## 1. Objective and stopping condition

Continue `machieke/fusion-module-interfaces` from
`64d2d1583376f37811d37cb7f2557145690b3b00`, or record the exact descendant and
relevant changes. Read applicable `AGENTS.md`, the MeTTaClaw mapping packet,
`docs/omega-adoption/mettaclaw-neoclaw/s01.md`, and S01 contracts/evidence first.
Preserve unrelated working trees and private upstream data.

**Objective:** connect the already implemented
`neoclaw-nal-truth-deduction/1` operation to the actual native MeTTaClaw
agent-turn path, with application-owned invocation identities and recoverable
result handoff into the next turn. Demonstrate several intentional calls and a
replay without manually rewriting request configuration between calls.

This is application adoption of the same operation, not a second numerical
capability, a new Fusion family, or a new reasoning engine. S01 remains a completed
bounded command-level milestone; full-loop behavior was explicitly outside it.

**Stop after S01.1.** Do not implement S02 web search, memory migration, semantic
search, additional NAL rules, arbitrary remote evaluation, new cognition, a generic
agent scheduler, public/multi-host deployment, production identity, chain work,
or upgrades to unrelated numerical runtimes. No automatic local fallback.

A controlled native-loop test with explicitly substituted external dependencies
is acceptable. It must be labelled as such, not as the default full Omega stack
or an autonomous-agent benchmark. Full live-provider startup is a separate gate.

## 2. Source and evidence basis

The reviewer inspected public S01 implementation, tests, reports and the commit
patch, plus the pinned upstream loop. The reviewer did not execute the suites,
rebuild native dependencies, or perform a security audit. Verify findings locally.

The S01 report records 32 tests: 13 fixture-focused and 19 native/network integration
methods. Existing regressions are 156 core + 46 native-provider + 42 native-Hive
cases, totaling 244. Those Hive regressions target the previously integrated Hive;
they do not establish that the separate MeTTaClaw agent loop was started.

The report was recorded against an additive working tree based on
`c305a66fe1eda17a47134ec56d4fefdf55354147`; `evidence/s01/source-state.json` hashes
the tested files. The subsequent public commit is `64d2d158...`. Verify the mapping
from recorded hashes to the checkout. Preserve the original report as historical
evidence rather than rewriting its pre-commit state as a clean-commit test run.

Retain the existing S01 source selection unless an explicitly documented
application incompatibility requires a narrowly scoped addition:

| Component | S01 pin |
|---|---|
| MeTTaClaw `neoclaw` | `2af37c3fec18613de54ca42fde2382a9087d4524` |
| S01 PeTTa | `fea83178af3722666d2948d074591d10a3134f56` |
| S01 SWI-Prolog | `e58621a91ab7dd530e1e8185ed518f63d851c414` / 10.0.1 |
| S01 Python | 3.12.12, as verified in the runtime manifest |
| Real DeTTa source | `272888f264dd2dde18b574cabb53c266b0dac2ec` |

Existing Fusion guarded PLN uses a different pinned runtime/profile. Leave it
unchanged. A shared mathematical name does not make the two profiles equivalent.

### Files to inspect

| Source | Why it matters |
|---|---|
| `integration/neoclaw/native_command.py` | Real parser/skill execution, but a generated one-command outer driver; temporary checked replacement of one `metta` definition. |
| `integration/neoclaw/neoclaw_bridge.py` | Named-operation recognition and current configuration-based caller creation. |
| `fusion/neoclaw_client.py` | Durable request/receipt/RPC budget; request identity and deadline currently come from configuration. |
| `fusion/neoclaw_contracts.py` | Exact lexical domain, profile, selection, identities and limits. |
| `fusion/neoclaw_transport.py` | Composition-only local or verified loopback HTTPS selection; no fallback. |
| `fusion/neoclaw.py`, `integration/neoclaw/host.py` | Existing independent owners and operator-only work/flush entrypoints. |
| `integration/neoclaw/test_{s01,network,recovery}.py` | Three paths, numerical boundaries, actual TCP/TLS and recovery evidence. |
| `tests/neoclaw_support.py` | Test harness supplies a new request identity/configuration and drives work; do not mistake it for the agent lifecycle. |
| Upstream `run.metta`, `lib_mettaclaw.metta` | Actual imports/startup, including unpinned dynamic imports to control in the new recipe. |
| Upstream `src/loop.metta` | Model response -> parser -> command evaluation -> results/history -> next context; currently volatile loop state. |
| Upstream `src/{skills,utils,memory,channels}.metta`, `src/helper.py` | Actual command handler and external/local-state boundaries. |

## 3. Gaps to address, without reclassifying S01 as a failure

1. The S01 driver imports selected native files and evaluates a supplied command.
   It does not invoke the complete `mettaclaw` turn loop.
2. Its adapted skill is installed in a temporary copy created by the test/command
   driver. Ordinary upstream startup does not automatically install that adapter.
3. `Caller.prepare` takes `request_id`, deadline and budgets from trusted config.
   Reusing a key with new inputs correctly conflicts; repeating the same request
   correctly replays. A running agent needs to distinguish a retry from a new
   intentional occurrence without an operator editing config each time.
4. The native loop can evaluate multiple commands and constructs the next context
   from `&lastresults`; the result must reach that path, not only a capture JSON.
5. HTTPS serves public module calls; work/flush are separate trusted operations.
   A reproducible application run needs a bounded operator lifecycle for them,
   not hidden test-harness calls masquerading as agent behavior.

## 4. Required application integration

Provide a supported, source-checked startup hook/overlay for the pinned MeTTaClaw
application. Prefer an existing extension mechanism. Otherwise supply a minimal,
reviewable patch/overlay and loader with exact source/hash checks. An additive
Fusion launcher may apply it to a disposable checkout; never modify the user's
populated Omega directory or push to a third-party repository without permission.

The same adapter must be usable by the declared application launcher and the
integration tests. It must not exist only inside `native_command.run`.

Invoke the actual upstream `mettaclaw` loop and preserve its model-response parsing,
command dispatch, result construction and next-context path. Small explicit hooks
for composition, invocation context, result recovery and bounded termination are
allowed. Copying/reimplementing the loop in Python or calling the one-command
driver repeatedly does not pass the application-loop gate.

Use an explicitly named controlled test composition. It may replace model responses,
channel ingress and unused memory/media dependencies with labelled deterministic
fixtures at their actual external boundaries. Keep the real native runtime, actual
loop/parser/skill path, S01 numerical provider, DeTTa and HTTPS in the real-path gate.
Do not replace the remote operation with a fixture, prepopulate its return value,
or substitute a precomputed next-context string for the loop's own construction.

Record every substitution and its initialization behavior. The fixture model emits
the selected command and verifies the result in a later received context; it does
not compute or inject the answer. Control wake/turn limits and generated storage
paths explicitly. Keep the original default/live startup recipe separate.

Do not acquire paid-model credentials or start live IRC/Mattermost/media services
merely to prove this boundary. Missing inputs for those optional paths are not
permission to claim they ran. Conversely, if the actual native loop cannot be
loaded and exercised under the declared composition, report the required loop gate
as BLOCKED or FAIL rather than replacing it with a new harness loop.

## 5. Invocation identity belongs to the application caller

Separate stable operator configuration from a local, trusted per-invocation context.
Configuration chooses allowed provider/profile, principal, route, TLS trust and
limits. Model/tool text must not choose any of those, or supply an idempotency key,
credential, arbitrary endpoint, path or deadline extension.

Reuse the existing caller journal/state owner where practical. Add only the small
local records needed to bind an accepted turn/tool occurrence to its S01 intent and
accepted result. Do not create another episode owner or workflow framework.

A suitable identity model is a locally assigned session + accepted turn + command
occurrence identifier. These are design examples, not mandatory wire fields.
Persist the accepted command batch/order and selected occurrence before execution.
Do not derive identity solely from input bytes, wall-clock time, process ID, a
volatile loop counter, or the order in which a nondeterministic enumeration happens
to evaluate commands. Identical commands at distinct accepted positions are distinct
occurrences; restarting an already accepted position is the same occurrence.

Bind each accepted S01 occurrence to its exact lexical premises, profile/selection,
request/correlation/reply route, original absolute deadline and original budgets.
The caller must obtain a new identity for a genuine new occurrence automatically,
not by repeatedly overwriting a global config file. Preserve the old S01 CLI/config
path for its existing tests where useful; do not change historical wire semantics.

Distinguish:

| Situation | Required behavior |
|---|---|
| Same accepted occurrence, lost reply/restart | Same durable request, job, budgets and result. |
| Same occurrence identity, changed arguments | Conflict before a new remote effect. |
| New occurrence, different arguments | New request and independently validated result. |
| New occurrence, identical arguments | New request; byte equality is not occurrence identity. |
| Repeated model response before local durable acceptance | Outside any exactly-once model-call claim; record the boundary honestly. |

Keep one unfinished invocation per reply route and sequential handling initially.
Do not add multiplexing to this increment. Pending/unrelated delivery must not be
acknowledged as the new command's result, and unresolved prior work must not be
hidden by advancing to a fresh request. Admit new work only within the existing
finite capacities; do not raise lifetime limits or clear journals to fake progress.

## 6. Result handoff and scoped recovery

Preserve the existing chain of independent commits:

```
Application accepts/binds command occurrence
  -> Caller persists S01 request
  -> Execution accepts/reserves/computes
  -> AtomStorage persists result
  -> Execution commits terminal state and outbox
  -> Messaging accepts completion
  -> Caller commits validated receipt and acknowledges delivery
  -> Application records the result for the accepted occurrence
  -> Native loop constructs subsequent context using that result
```

Do not merge owner databases or read provider SQL from the application. If an
application result accessor is needed, expose a narrow current-authority-checked
caller operation; do not expose arbitrary receipt paths or foreign tables.

On restart, recover the pending S01 occurrence before asking a model to regenerate
that already accepted command. Preserve lexical representation, current authorization,
selection and remaining budgets. A crash after caller completion but before loop
handoff must recover the same result, not create another job. Define a deterministic
projection of the accepted result into the loop's context so resuming does not
append duplicate result fragments or silently supply empty `&lastresults`.

Scope recovery to the accepted S01 occurrence and its result handoff. Do not claim
exactly-once hosted model requests, channel delivery, arbitrary tool effects or
legacy flat-file history appends. Never automatically replay unrelated shell/file
commands from a partially completed batch. The controlled recovery fixture can use
S01-only batches; include unrelated pure local commands in non-crashing regression
cases. Any wider batch recovery semantics must remain explicitly unsupported.

Preserve S01's durable RPC/native reservations and deadline behavior. Do not
replenish exhausted budgets, renew deadlines, retime identities or use silent local
fallback. Physical pure computation may repeat within the recorded attempt limit.
No new numerical computation starts after the original effect deadline. Previously
persisted output can still be read/closed under the existing contract and authority.

## 7. Operator lifecycle and placement

Provide one bounded operator-run recipe for the controlled demonstration: set up
disposable generated state and credentials, start the existing HTTPS server and
trusted work/flush driver, start the real native-loop composition, observe completion,
and stop only processes created by this invocation. Readiness and process identities
must be explicit; avoid arbitrary sleeps, process-wide kill commands and port guessing.

A small bounded local work/flush loop is acceptable. It is operational glue for the
existing owners, not a new general scheduler. Keep work/flush unavailable over the
public module API. The caller must not read the worker configuration or invoke
provider work directly. Its only contact with the provider is the declared boundary.

Use the same loop/adapter code with local and network placement; only composition
selects the binding. Keep the same-host loopback HTTPS limit. Do not remove loopback
checks or claim multi-host support under the existing profile. Retain verified TLS,
current authorization, no fallback and filesystem isolation in network tests.

This moves the selected operation's execution, not necessarily the caller's whole
native runtime or its installed files. No browser-only or runtime-free thin-client
claim follows from this task.

## 8. Required demonstrations and acceptance tests

Run an equivalent controlled multi-turn scenario under local and network composition,
with separate fresh generated state for the comparison. Compare original native
arithmetic as an oracle, not a replacement implementation. Include:

- A normal turn dispatching S01 and a later real-loop context containing its exact
  validated representation. The model boundary fixture must observe that context.
- Sequential new S01 occurrences with different inputs, and a later intentional
  repeat of the original inputs. Assert distinct logical jobs for distinct
  occurrences without operator config edits. Replaying one occurrence adds no job.
- Two identical S01 commands at separate positions in one accepted batch; identities
  must distinguish positions. Keep sequential route handling and preserve result order.
- A broader pure local command such as `metta (+ 1 2)` still follows the original
  local path. Invalid arguments to the selected named command do not fall through.
- Network outage, wrong CA, revocation and malformed bound result remain typed
  failures/pending outcomes in the native path, never a fabricated numerical success.
- SIGKILL after occurrence binding but before submission; after remote acceptance;
  and after durable caller completion but before loop result handoff. Recover the
  accepted occurrence, same job/result and original budget through actual loop startup.
- Recovery of an accepted S01 turn must not ask the fixture model to regenerate it.
  The next genuinely new model call receives the recovered result. Record the
  boundary before accepted model-response persistence separately.
- Generated private canaries, operator paths, credentials and provider state do not
  enter outgoing S01 payloads, model-visible diagnostics or published evidence.
- Explicit capacity/budget exhaustion and a bounded stop. Do not clear state,
  refund reservations or invent a new request to convert failure to success.

Count tests from executed scenarios rather than targeting a quota. Preserve actual
failure traces and correction evidence separately. Only the new narrow application
boundary needs new failure coverage; reuse S01's deeper owner tests.

## 9. Gates, reproduction and delivery

| Gate | Required evidence |
|---|---|
| BASELINE | Exact hashes/commits; applicable 32 S01 and 244 recorded regressions rerun or individually classified. |
| STARTUP_HOOK | Source-checked application integration usable outside the one-command test driver; no silent moving dependency imports. |
| NATIVE_LOOP | Actual upstream loop/parser/skill/result-context path; each substituted dependency explicitly labelled. |
| INVOCATION_IDENTITY | Distinct occurrences, identical-input occurrences, exact replay and conflict behavior with persistent application identity. |
| RESULT_HANDOFF | Actual subsequent loop context consumes the validated result; no test-injected answer or duplicate result projection. |
| PLACEMENT | Same caller/loop code works locally and via real same-host verified HTTPS with real native worker and DeTTa. |
| RECOVERY_LIMITS | Actual native-loop restart preserves S01 identity, result, reservations and deadline; broader effects excluded. |
| AUTH_PRIVACY | Current authority, no fallback, closed remote input, no secret/private-state disclosure. |
| REPRO_SCOPE | Declared sources and cache assumptions; bounded operator lifecycle; no second operation or unrelated state migration. |

Track optional/unrun gates separately: DEFAULT_FULL_OMEGA_STARTUP,
LIVE_HOSTED_MODEL, LIVE_CHANNELS, GENUINE_MULTI_HOST, REAL_CHAIN,
POWER_LOSS and EMPTY_GLOBAL_CACHE. Do not promote a controlled loop PASS into
one of those. The historical native Hive tests remain a separate runtime track.

Keep existing owners/profiles and baseline source pins stable. If targeted S01
caller API changes are necessary, make them explicit, preserve the prior command
recipe, and verify old behavior. Fresh application-journal state is acceptable;
no migration of real user sessions is requested.

Deliver the minimal startup hook, caller-lifecycle extension, controlled native-loop
integration tests, operator instructions and an S01.1 evidence report/manifest.
Update `operation_adoptions` for the SAME numerical operation: command-level plus
controlled native-loop evidence. Do not count it as a second adopted operation or
promote the entire PLNKernel family or 15-family inventory.

Record exact tested commit or file hashes and the final committed relationship.
Report newly executed tests, reused historical evidence, fixture/real components,
resolved failures and unrun optional gates. Do not publish secrets or private data.

**Then stop.** The next numerical/tool capability and full memory adoption remain
separate choices. This task's success is an actual Omega turn consuming and recovering
an interface-backed operation, not a higher count of reference modules.

## Public review sources

Paths in the source ledger refer to these pinned trees:

```text
https://github.com/machieke/fusion-module-interfaces/tree/64d2d1583376f37811d37cb7f2557145690b3b00
https://github.com/patham9/mettaclaw/tree/2af37c3fec18613de54ca42fde2382a9087d4524
```
