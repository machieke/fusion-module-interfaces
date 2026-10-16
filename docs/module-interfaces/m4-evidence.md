# M4 — native generated result to isolated real chain

**M4 PASS: all 10 required gates**, including real CHAIN, on tested implementation
`55ed5402391ab6ed14f8ab20e1eea4c85d8be955`. The complete M1–M3.1 regression
passes on that same clean checkout. Its commit and runtime-file hashes are unchanged
at verification end. Final missing prerequisites, executed failures and observation
timeouts are each empty; earlier failed attempts remain separately recorded.

The [machine-readable manifest](../../evidence/m4/manifest.json),
[same-artifact trace](../../evidence/m4/final/same-artifact.json) and
[independent readback](../../evidence/m4/final/readback.json) accompany the final
evidence-only commit. Private runtime artifacts are excluded.

## Source and scope

Requested ancestor: `985d2f34ea8df8c5d93582e4ed6fe5cbe1843074`.
Started at `8491c4900a5ccab872073e62b1024e3b731aeaf9`, its single
presentation/documentation-only descendant. The supplied brief was the only
initial untracked file. The original M1–M3.1 runtime and tests were unchanged.

F1R3node uses an obtainable **clean new baseline** at
`9ec1096e10774926ea8e72f0823482f0bf9213e1`, from the named fork. The historical
workspace's uncommitted consensus/resource-limit changes were not used or changed.
Implementation commit `1219bb5e3c505490dd018baa079534eca9333b54` adds the M4
slice; `55ed5402391ab6ed14f8ab20e1eea4c85d8be955` then freezes nested approval
and binding inputs against caller mutation. A real build/start/effect/finality/
same-genesis restart probe preceded native implementation. Native Hive, DeTTa, PeTTa, SWI, Reachability and PLN pins are
unchanged. No upstream source or consensus behavior was patched.

## Decisions and changed areas

- `fusion/adapters/f1r3_m4.py`: fresh single-operation owner under explicit
  `f1r3-generated-post-state/2`; exact approval/context binding; durable logical
  plan and signed request; current authority; strict effect/finality observations.
- `fusion/adapters/f1r3_signing.py`: the inspected protobuf/BLAKE2b/secp256k1
  low-S signing procedure, with optional dependencies isolated to the chain recipe.
- `integration/hive/program/completed.py`: read-only accessor owned by the original
  caller; current native/service authority and exact accepted/acknowledged bytes.
  The existing plugin is byte-for-byte unchanged.
- `integration/hive/commitment/`: narrow native sibling, operator-only allowlist,
  typed local ConsensusFinality session and independent caller progress.
- `integration/chain/`, `tests/test_m4_chain.py`: pinned inputs, real node lifecycle,
  fixture validation tests and actual authenticated caller recovery/readback tests.
- `scripts/build_chain.py`, `build_m4.py`, `verify_m4.py`, `readback_m4.py`: fresh
  declared-input build, isolated real run, separate classifications and read-only
  verification. The old build invocation remains available.
- Contracts, ADR-013, architecture, discovery and runbook document compatibility,
  ownership, source/API semantics and the reproduction command.

## Independent states and guarantees

The original inspect result is retrieved and checked before approval. It is
explicitly shareable generated data under the existing shared-fixture policy.
Normal action parameters cannot provide an arbitrary payload/ref/hash, approval,
code, RPC endpoint, signer or network. Approval binds the exact scope/ref/digest,
operation, native owner, profile/descriptor, target genesis/network/shard, signer,
protobuf identity and phlo limits. Current authority is rechecked even for cached
responses. Revocation prevents new sends; it cannot retract bytes already sent.

The owners commit independently. A logical plan freezes timestamp and limits
before signing; a complete signed deployment is durable before submission.
Replays reuse exact signed bytes. Native progress does not rewrite chain, DA,
execution or messaging state. Off-chain completion survives chain outage.

Finality requires actual non-consuming value readback at the matching inclusion
block's **post-state**, successful target execution and matching deploy-effect
finality. A finalized block or submitted term alone cannot satisfy the gate.
Pending, typed rejection/expiry, unavailable/incompatible evidence and finalized
matching effect remain distinct. Raw incompatible observations are retained.

## Executed development attempts

These are retained separately from the final run; none is a missing runtime
prerequisite or a positive chain timeout.

1. Prerequisite probe launcher exit 127: an ephemeral `uv --with` Python path had
   expired. Corrected by creating a persistent pinned environment; no node had
   started in the failed launch.
2. Native development 01: test bug assumed `EpisodeRef.digest`. Corrected to use
   the actual episode identifier and identifying derivative in the privacy scan.
3. Native development 02: Hive rejected an empty `kinds` declaration. Corrected
   against native `Programs` validation.
4. Native development 03: Hive rejected `started` without a pending/unknown
   receipt. Corrected to its verified result-envelope contract. Six cases failed
   this same assertion; the real node itself started and accepted signed deploys.
5. Development 04/05: 10 fixture tests and six real native tests passed; 05 adds
   post-finality response-loss replay and first-observation kill coverage. These
   development runs are superseded by the final clean-source run.
6. Additional negative regression on `1219bb5`: mutating a retained nested
   approval dictionary did not raise the required refusal. The frozen dataclass
   alone was insufficient. `55ed540` captures canonical copies of approval and
   binding; the same regression and all 11 focused fixtures pass. Earlier suite
   passes do not establish this corrected guarantee.
7. One evidence-packaging command treated a sanitized source label as a path. It
   was corrected to the recorded authorized workspace; the upstream edits were
   confirmed unchanged. This was a metadata command failure, not a chain test.

No positive chain observation timed out. Missing prerequisites and final-run
failures are listed separately in the manifest; development and negative-fixture
failures do not become BLOCKED gates.


## Exact inputs and reproduction

| Input | Pin / identity |
|---|---|
| F1R3node | `9ec1096e10774926ea8e72f0823482f0bf9213e1` |
| Hive runtime | `34b0fb32ab3806e5609fc89bb7535518a35e1aea` |
| DeTTa / secured-contract-spaces | `272888f264dd2dde18b574cabb53c266b0dac2ec` |
| Reachability | `dd56f3f053ed90239de5377021a7d3b3fbf424ac` |
| PLN | `4405956947c4b53c7ff01bd565aa3b114bc970a1` |
| PeTTa | `ae66fa8e41dcd5539d614706bd4e5cfb34f9608d` |
| SWI-Prolog | `69775434c8226897626b226aefcc8266499f1e2e` (10.1.14) |
| Schematics, discovery only | `4af00db4e395375484dd48d0b9068a59afcf01f8` |
| Native / fixture Python | 3.12.12 / 3.11.14; Janus 1.5.3 |
| Rust / protobuf / native library | nightly-2026-02-09, rustc 1.95.0-nightly `6efa357bf`; grpcio-tools 1.84.0, libprotoc 35.1; OpenSSL 1.1.1f |

The fresh node binary SHA-256 is
`2021389d8e1a1db0470d55ba6744124e33f2bc44f5155e6cfa662798b4ffd085`.
[Build evidence](../../evidence/m4/build/chain.json) records lock/source hashes,
compiler identity, flags and 230.124 seconds for obtain/fetch/build. Provider build
inputs and resulting binary identities are recorded separately. The native provider
build began while Fusion still reported `8491c49`; its recipes, pins, guarded runtime
code, adapter source and locks are byte-identical at the tested commit, as checked
in [input equivalence](../../evidence/m4/preparation/provider-build-input-equivalence.json).
The native M4 plugins are loaded from `55ed540` during the actual tests.

The final verifier runs in a fresh detached Fusion checkout. Provider sources,
venv, SWI/DeTTa/node builds, M1 compatibility target, test directories and genesis
were fresh; no provider binary or target directory was copied. Downloads were
cached. Supplementary upstream Rust regression binaries may use their Cargo cache
across verification attempts. The first compatibility pass also used the historical
fixed target; the final corrected checkout rebuilds that target from empty.

Executed entrypoints:

```sh
uv run --python 3.11 --locked python scripts/build_m4.py <FRESH_BUILD>
uv run --python 3.11 --locked python scripts/verify_m4.py <FRESH_BUILD> --output <FRESH_EVIDENCE>
```

The verifier records the exact source at start/end and refuses final success if
it changes. It invokes `verify_m3_1.py` and all nested regressions, the focused
commitment fixtures, and actual native chain tests inside an isolated namespace.
See the [runbook](runbook.md#m4-required-isolated-chain-reproduction) for access
prerequisites, operator configuration and a separate readback invocation.

## Same-artifact evidence

The final native command is
`generated-m4-916416dc-1394-411e-ba8f-64420a8c4ffb`.
The generated input is 53 bytes; the accepted result is 143 bytes, with SHA-256
`cd2f727689b41e243ee78207d058d00b8be64932abbfd86a02851dfcbac400bb`.
There is one execution job, one completion outbox item, two mailbox records and
two shared atoms. The fixture counterparty receives the original reference.
The native caller retrieves the real DeTTa bytes, accepts the correlated completion
and acknowledges it before approval.

The on-chain value is the tuple `(fusion:m4:commitment/1, generated operation ID,
approved result digest)`. The trace deliberately publishes the generated Rholang
read name for independent verification; it contains no private cognitive identifier.
The target deploy is observed in block
`6922353b9d0d0b7307d3f472a92e40cbe5902e61da01150986d9daa9188a1b82`,
post-state `351c1234a0d0793edc7c19eb33f1f1a221d659a97f325261c6dac9afcc01f8f1`.
The original observation, same-genesis node restart and separate read-only process
match the exact deploy, block, post-state and result digest. Full generated refs,
execution/completion identity, approval, genesis, signed deployment and readback
are in the linked trace; no private actor mapping is included.

| Observed stage | Elapsed / size |
|---|---:|
| Storage, worker and native acceptance | 2.296 s |
| Local signing callback, including serialization/imports | 0.040513 s |
| Submission HTTP exchange | 0.041256 s |
| Full authorized signing/submission action | 2.522 s |
| First inclusion observation | 4.066 s |
| First finalized-effect observation | 4.066 s; one native observation call |
| Same-data/genesis node restart to readiness | 1.148 s |
| Signed JSON request | 673 bytes |
| Node-reported execution cost | 675 phlo |

Inclusion/finality timings include propose and authorized observation overhead;
they are first observations, not independent estimates of internal consensus time.
Regression work ran concurrently. No throughput or economic claim follows.

Four explicit native process-kill boundaries pass: after inspect acceptance,
after signed-intent commit, after real submission but before saving its response,
and after a verified observation but before caller progress. The response-loss
case waits for real finality before retrying. Signing-key access is removed for
signed-intent replay; the original signed bytes and timestamp remain identical.
Recovery calls take 8.070, 6.062, 3.593 and 1.535 seconds respectively, excluding
the injected pause and preceding caller startup. Whole-case times are in the
manifest. The first observation case never resets or edits owner state in the test.

A real node SIGKILL/outage leaves off-chain acceptance and acknowledgment committed;
an authorized observation reports unavailable, and later observation recovers the
same finalized effect after restart. The read-only verifier receives only permitted
DA get authority and read RPC; it opens neither a caller journal nor a signing key.
The ordinary native observe path also works while its signer file is unavailable.

## Tests and gates

All required gates pass in the final manifest. No required gate is blocked or
unrun. The final full regression took 1,414.133 seconds; the independent native
chain suite ran alongside it. Historical evidence was preserved.

| Gate | Result | Evidence |
|---|---|---|
| BASELINE | PASS | Exact-source M1–M3.1 regression, including both attention providers and old profiles |
| CHAIN_SOURCE_BUILD | PASS | Clean pinned build, route-free namespace, actual sockets and host refusal probes |
| NATIVE_HIVE_DA | PASS | Authenticated Programs dispatch, real DeTTa, same-run result, labelled fixture counterparty |
| APPROVAL_BINDING | PASS | Live authorization, immutable registered inputs, exact result/chain/profile and negative cases |
| REAL_CHAIN_EFFECT | PASS | Actual tuple read from inclusion post-state plus matching successful deploy-effect finality |
| RECOVERY | PASS | Four native caller/adapter kill boundaries, response loss, outage and same-genesis node restart |
| PRIVACY_ISOLATION | PASS | Private episode/payload/provenance canaries and derivatives absent; secrets/paths excluded; real socket isolation |
| REPRO_READBACK | PASS | Fresh declared builds/checkouts and a separate read-only process checking the same artifact |
| DEMO_HANDOFF | PASS | Native submission/observation receipts, explicit progress, runnable commands and sanitized trace |
| SCOPE | PASS | Original DA, cognition, guarded mathematics, ports, legacy chain adapter and inspect plugin unchanged |

There are 11 focused commitment fixture cases and six real native chain cases,
with no skipped native cases. The baseline includes the 138-case aggregate (which
already includes those 11 fixtures), the 51-case M1 subset, 62 + 38 upstream DeTTa
cases, 34 native Hive baseline cases and 13 original native inspect cases.
M2, M3 and M3.1 retain their explicit fixture, real-provider, native dispatch and
process-kill suites; M3.1 alone has 9 closure fixtures, 5 provider cases, 3 direct
recovery methods covering 16 kills, and 7 native cases covering 4 caller kills.
The six M4 native cases include four explicit fault-boundary cases. Fixture transport and
malformed-state responses are labelled and never substitute for a real chain.
The [regression summaries](../../evidence/m4/final/regression-summaries.json) retain
all executed commands, counts, results and timing. Repeated subsets overlap; do
not sum them into a unique test total. Legacy verifier `CHAIN=NOT_RUN` fields refer
to those older scripts; the required M4 chain proof is the outer manifest's
`REAL_CHAIN_EFFECT=PASS` and its same-artifact evidence.

## Limits and unrun work

One synthetic local workflow, one actual native caller and one fixture counterparty;
one real isolated validator. Node-observed evidence is not trustless execution
attestation or decentralized safety. DA and block/post-state availability depend on
retained local files. Restart evidence covers actual same-host process termination
with intact storage, not power loss, storage corruption or distributed failover.

The observation driver starts at most 120 calls and stops starting them after
180 seconds; in-flight requests retain the existing socket timeout and can finish
later. Per-operation chain observation retention is finite (256); there is no
scheduler, automatic eviction, compensation, validity extension or inference-budget
change. Fresh M4 journals only; old profiles remain available and no migration is
performed. The generated grants/key/genesis and response fixtures are test inputs.
Private canaries are stored under actual private owners but never approved/exported.

Warm download caches are allowed and disclosed. Empty-global-cache builds, public
networks, multi-validator validation, production deployment/security/economics,
further cognition and live migration are NOT_RUN and outside this increment.

The commits after the tested implementation contain documentation and sanitized
evidence only. No runtime, contract schema, source pin, adapter or test changes
follow the final verification. M4 is complete; work stops here for review.
