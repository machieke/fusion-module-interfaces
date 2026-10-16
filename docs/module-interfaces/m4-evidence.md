# M4 — native generated result to isolated real chain

Final clean-checkout verification is pending. Development real-node passes are
not a final M4 completion claim. The final manifest will record every required
gate, exact tested implementation and subsequent evidence-only commit.

## Source and scope

Requested ancestor: `985d2f34ea8df8c5d93582e4ed6fe5cbe1843074`.
Started at `8491c4900a5ccab872073e62b1024e3b731aeaf9`, its single
presentation/documentation-only descendant. The supplied brief was the only
initial untracked file. The original M1–M3.1 runtime and tests were unchanged.

F1R3node uses an obtainable **clean new baseline** at
`9ec1096e10774926ea8e72f0823482f0bf9213e1`, from the named fork. The historical
workspace's uncommitted consensus/resource-limit changes were not used or changed.
A real build/start/effect/finality/same-genesis restart probe preceded native
implementation. Native Hive, DeTTa, PeTTa, SWI, Reachability and PLN pins are
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
5. Development 04: 10 fixture tests and six real native tests passed. Development
   05 adds stronger post-finality response-loss replay and first-observation kill
   coverage. Final source verification remains separately required.

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
