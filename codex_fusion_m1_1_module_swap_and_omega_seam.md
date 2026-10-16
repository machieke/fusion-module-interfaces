# Codex handoff — Fusion module interfaces: M1.1

## Objective and stop boundary

Work in the existing `machieke/fusion-module-interfaces` repository. Continue the
existing M0/M1 implementation; do not regenerate the original design or build a
new framework.

**Objective:** turn the published M1 module contracts into exercised composition
seams, demonstrate replacement of one module independently of its consumers, and
connect one real Omega/Hive entry point when the intended runtime source is
available.

**Stop after M1.1.** Do not implement M2 episodic memory/belief revision, ECAN,
PLN inference control, new consensus, a distributed scheduler, or a general
agent marketplace in this task. Do not start empty cognitive services.

This is a proposed engineering follow-up, not an assertion that the meeting
participants approved a final AtomSpace specification or selected an Omega
release. Keep the original brief, terminology and unresolved scientific choices.

## Review basis and evidence limits

This handoff follows a web source review of `master` on 2026-10-16. The reviewer
read implementation, contracts, tests, discovery and checked-in execution
reports. The full repository integration suite was **not independently rerun**.
The branch's exact commit must be recorded from your checkout before work starts.

The existing execution report records:

- 27 local contract/adapter tests passing under the M1 verification command.
- 62 DA and 40 storage tests passing in the inspected DeTTa checkout.
- Real DeTTa DA/FileStorage library calls and persisted 4+2 erasure-coded shares.
- Protocol-fixture peers, a separate deterministic `inspect_atom` worker, and a
  separate real isolated single-validator F1R3node commitment/finality run.

Those are historical repository-reported outcomes, not automatic passes for a
new checkout. There is no evidenced production Hive integration, distributed DA
custody guarantee, multi-validator safety test, or production authorization.

### Source ledger to inspect before editing

| Path / symbols | Relevance |
|---|---|
| `codex_omega_asi_module_interfaces_brief.md` | Original scope, source ledger and constraints. |
| `docs/module-interfaces/architecture.md` | Responsibilities, dependencies, ownership, C0–C4 roadmap. |
| `docs/module-interfaces/contracts.md` | Behavioral guarantees and explicitly deferred capabilities. |
| `docs/module-interfaces/decisions.md` | Identity, authorization, cross-store recovery and placement decisions. |
| `docs/module-interfaces/discovery.md` | Inspected Omega candidates, missing actual Hive checkout, reuse decisions. |
| `docs/module-interfaces/evidence.md` and `evidence/sources.json` | Historical tests and dirty dependency fingerprints. |
| `fusion/ports.py` | Published method-level contracts. |
| `fusion/contracts.py` | Wire validation, shared types, internal opaque storage port. |
| `fusion/service.py`: `Service`, `AtomOwner`, `ExecutionOwner`, `MessageOwner` | Actual composition, inter-owner calls and transaction boundaries. |
| `fusion/composition.py`, `bindings.py`, `client.py`, `registry.py` | Provider construction, transport bindings, client requests and resolution. |
| `fusion/adapters/f1r3.py` | Pinned approval and durable signed-intent submission. |
| `tests/test_contract.py`, `tests/test_adapters.py`, `tests/support.py` | Existing conformance and failure-injection coverage. |
| `scripts/verify.py`, `scripts/schema.py`, `docs/module-interfaces/runbook.md` | Verification, wire schema and reproduction. |

## Findings to verify, not assumptions to copy blindly

### F1 — Declared ports and exercised dependencies differ

In the reviewed source, `Service.__init__` constructs concrete owners directly.
`ExecutionOwner.submit` calls `atoms.row`, and `work_one` uses the implementation's
`get` and `create` conventions. `ports.AtomStorage` instead declares methods using
`Mutation` and `AtomEnvelope`; it does not expose `row`. The published
`AtomStorage` protocol also lacks the existing wire `availability` operation.

The current DA `Storage` injection is a genuine backend seam. Switching
`InProcess` to `Subprocess` is a genuine transport test. Neither by itself proves
that an independently implemented **AtomStorage module** can replace the current
one while execution and its consumer remain unchanged.

This is not a demand for one process, file or database per module. Shared local
resources are permissible; undeclared implementation dependencies are the issue.

### F2 — Some shared receipts encode the implementation

`JobAcceptance.acceptance`, `MessageAcceptance.acceptance` and
`MessageAck.persistence` currently expose the literal `sqlite-full`. That is
honest evidence for this harness, but is not a neutral requirement that an
otherwise conformant replacement must implement using SQLite.

Resolve whether these are explicitly local-profile types or shared behavioral
contracts. Preserve actual guarantees; changing a label must not upgrade them.

### F3 — Compatibility is narrower than the proposed architecture

The resolver can evaluate same-major descriptor versions, but current dispatch
accepts only 1.0.0 and `Peer` constructs 1.0.0 requests. This is explicitly
documented, not a concealed defect. Do not claim rolling-upgrade interoperability
from descriptor fixtures. The M1.1 swap may remain at 1.0.0; it must actually use
the selected provider and fail closed on incompatible providers.

### F4 — Exact reproduction depends on external working trees

The reported DeTTa and F1R3node runs used modified working trees. The manifest
records hashes and changed files, including an untracked F1R3node source file.
A fingerprint establishes identity of bytes already possessed, not a way to
obtain those bytes. Do not claim the documented clean HEAD commits reproduce
those runs without the modifications.

### F5 — The real Omega consumer remains an open gate

The discovery ledger inspected the `omegahive-start-here` onboarding repository;
the actual Hive runtime checkout was absent. Preserve that distinction. Do not
rename `Peer` or wrap it in an Omega-named class and count that as integration.

## Work package A — Reproducible baseline and contract map

1. Read `AGENTS.md` wherever present. Record this repository's commit, worktree
   state, interpreter/toolchains, dependency revisions and relevant source hashes.
   Preserve unrelated local modifications; never reset or overwrite sibling work.
2. Run the current local M1 gate where its actual dependencies are available.
   Record every failure, skip and blocked prerequisite. Keep the optional real
   chain gate separate; `scripts/verify.py` is not itself that chain gate.
3. Produce a compact M1 contract-to-implementation map: declared method, wire
   operation, owning implementation, actual caller, authorization context,
   persistence/effects, and conformance test. Identify interface drift explicitly.
4. Add a machine-readable dependency/preflight manifest and commands that explain
   what is missing. Prefer obtainable immutable commits for reproducible runs.
   When the required modifications are not available, report the exact gate as
   blocked. Do not commit another person's changes or publish private source to
   make a reproduction claim.
5. If pure contract checks are separated from external integration checks, label
   them accordingly. A passing pure or fixture suite never substitutes for a
   failed or unavailable real DeTTa/chain gate.

## Work package B — Exercise module boundaries

### B1. Make the M1 ports meaningful at runtime

Use the existing names and module catalogue. Add the smallest typed facades or
adapters needed to reconcile `ports.py` with the actual M1 surface, including
`availability` and the envelope/receipt shapes used by callers.

Move concrete implementation selection into composition. Execution must consume
an explicit AtomStorage port and must not call `.row`, query atom tables, access
another owner's `.db`, or depend on provider class identity. Use existing public
read/availability methods for reference validation where sufficient; introduce a
new operation only with documented semantics and a concrete need.

Apply the same rule to completion acceptance: identify an explicit, narrow,
module-owned delivery port for execution's outbox, rather than treating a private
implementation helper as a universal public interface. It may remain a trusted
internal port; do not expose the worker or arbitrary completion mutation to
untrusted callers.

Keep authentication/authorization at trusted boundaries. Injection of a port is
not authority for a client to choose a principal or write another owner's state.
Document the caller context used for requester operations and worker operations.

### B2. Prove one independent module replacement

Add a contract-conforming alternative AtomStorage test provider that does not
inherit from `AtomOwner`, share its atom table, or expose its private helpers.
Clearly classify it as a test provider unless it independently meets a stronger
real-provider gate.

Exercise the same execution consumer against:

- the real DeTTa-backed AtomStorage composition; and
- the independent contract test provider, advertising only its actual profile
  and guarantees.

The execution logic and client workflow must be unchanged. Only composition may
select the provider. If the test provider cannot meet an advertised durability
requirement, either implement that bounded guarantee or test rejection; do not
silently weaken the consumer's requirement.

This is a module-contract proof, not evidence of a second real DA network. Keep
the original in-process/subprocess binding cases too, labelled as transport tests.

Add structural/type checks and a hostile test double that fails if private
helpers or foreign SQL access are used. Shape checks alone are not behavioral
conformance: run the same relevant invariant tests through both providers.

### B3. Preserve recovery across the newly explicit boundary

Do not inadvertently rely on one SQLite transaction spanning a replacement
module's storage. Specify the failure model before moving effects.

Persist delegated results through AtomStorage with a stable owner-scoped
idempotency identity derived from the accepted job. A restart after successful
result persistence but before job/outbox commit must recover the same logical
result. Keep completion intent durable with terminal execution state, and retry
delivery through the messaging owner without duplicating the logical completion.

If independent placement loses a local transactional guarantee, implement the
smallest replay/outbox protocol needed or reject that placement/profile. Never
advertise cross-module atomicity merely because the local composition shares a
database. No generic distributed transaction coordinator or lease scheduler is
requested.

Regression cases must retain duplicate/conflicting mutation behavior, caller and
worker restart, unavailable storage, unavailable/full reply routes, scope
isolation, revocation and the existing three process-kill boundaries.

### B4. Neutral receipts and complete response contracts

Separate contractual observations from backend evidence. A caller should learn
which bounded persistence/acceptance guarantee holds; the provider evidence can
say SQLite FULL/WAL or name another implementation. Storage, execution,
completion delivery and chain effect finality remain separate observations.

Make an explicit compatibility decision before changing public types. An
internal adapter, a new named profile or an intentional breaking version may be
appropriate. Do not silently reinterpret existing 1.0.0 responses or force an
unnecessary wholesale version bump.

Define and validate per-operation success and error responses, not only request
shapes. Test missing/malformed responses, unknown states/errors, mismatched
scope/reference/correlation where applicable, and responses that assert a
stronger guarantee than the selected provider is allowed to offer. Such tests
validate protocol conformance, not cryptographic proof of remote truth.

Bind the consumer's selected descriptor to the invoked provider/profile. It is
acceptable to remain on live wire version 1.0.0. Descriptor-only 1.x compatibility
must remain labelled as such unless live compatible-version providers are tested.

## Work package C — One real Omega/Hive seam, availability-gated

First check the known handover materials and authorized workspace for the actual
runtime. Record the repository, commit, source entry point and runtime command.
Do not choose an unrelated legacy implementation as the intended Hive target.

When the intended source is available, add a thin integration adapter that
preserves its existing interface and calls the Fusion contracts. Use synthetic,
non-sensitive test input through an actual Omega memory/tool/transformation entry
point. Keep the demonstration bounded:

1. The real Omega entry point stores an explicitly shareable generated payload.
2. A reference is exchanged or consumed through the declared messaging interface.
3. The existing bounded `inspect_atom` operation is delegated.
4. The result returns to the real caller through the declared status/completion
   semantics; retry/restart preserves correlation and one logical outcome.

Reuse the existing fixture peer as the counterparty when useful, but label each
side accurately. One actual Omega component plus a fixture is not two Omega
agents and not an operating production Hive.

The existing approved commitment adapter may optionally anchor the generated
result through the isolated chain gate. That remains a commitment demonstration,
not on-chain execution of Omega or PLN. Do not replace the signer, broaden deploy
permissions or attach to a public network for this task.

When the intended runtime is unavailable, deliver a precise integration seam
note and a `BLOCKED` gate identifying the missing repository/revision/access.
Complete A/B and stop. Do not spend the task recreating Omega, scraping closed
source, or installing a new agent framework to manufacture an integration pass.

## Acceptance gates

| Gate | Required evidence |
|---|---|
| BASELINE | Exact tested source identity, commands and outcomes; dirty or missing dependencies explicitly accounted for. |
| PORTS | M1 contract map agrees with exercised calls; no execution dependency on AtomOwner helpers, foreign SQL or concrete provider identity. |
| SWAP | Same execution consumer works with real DeTTa-backed AtomStorage and one independent conformant test provider; incompatible guarantees are rejected. |
| RECOVERY | Existing regression tests remain green where runnable; result-persist-before-completion and outbox recovery work without assumed cross-owner atomicity. |
| WIRE | Request and response conformance are exercised; backend evidence is distinguished from guarantees; version/profile changes are explicit. |
| OMEGA | Actual named runtime entry point used and evidenced, or clearly BLOCKED. A fixture never passes this gate. |
| CHAIN | Separate optional real isolated run with deploy/effect observations, or NOT RUN/BLOCKED. Unit fixtures never pass this gate. |
| SCOPE | No M2/C1/C2 implementation, ECAN, inference controller, agent framework rewrite or new production-security claims. |

## Required deliverables

Update the existing architecture/contracts/ADRs rather than creating parallel
specifications. Deliver the small implementation changes, focused conformance
and failure tests, the independent swap fixture, the source/preflight manifest,
and the real Omega adapter or precise blocked-seam note.

Add an M1.1 evidence report recording commands, source fingerprints, classifications,
test counts, failure cases, outstanding limits and changed files. Preserve the
old report as historical evidence; do not overwrite old measurements as though
they came from the new run.

End with a gate-by-gate result and one recommended next increment. After M1.1,
the cognitive continuation remains M2: private episodic provenance and an
explicitly profiled belief-revision adapter, followed later by attention and
bounded inference. M2 is a subsequent task, not implied permission to continue.
