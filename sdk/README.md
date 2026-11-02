# Fusion contracts/client kit

The kit packages shared types and validators without E5, Chroma, DeTTa, native
reasoning binaries or Omega application code. It requires Python 3.12 or newer
and the standard library. The example is a separate package; installing the kit
alone installs no provider implementation.

The builder also emits a separate, bounded [operator wheel](OPERATOR.md).
Installing the client kit does not install operator tooling or PyYAML. The
operator package reuses existing workbench/operator code without packaging
native owners or adding a new orchestration layer.

`build.py` copies a positive list of repository contract sources **byte for byte**
into a deterministic wheel. Each wheel includes `source-manifest.json` with the
original source path, full SHA-256 and byte length. There is no independently
edited SDK copy of a validator. Rebuild the kit when a shared validator changes.

```sh
artifacts/reference-distribution/operator-venv/bin/python sdk/build.py --output sdk/dist/expanded-02
python3.12 -m venv /tmp/fusion-client
/tmp/fusion-client/bin/python -m pip install --no-index --no-deps sdk/dist/expanded-02/fusion_module_client-0.2.0-py3-none-any.whl
```

Extracting/installing these artifacts outside the checkout is supported. Tests
install both wheels in a new venv, run with `-I`, remove `PYTHONPATH`, and verify
that the concrete DeTTa/primary owner/full application modules are unavailable.

## Selected contract

`fusion.preview_client.AtomFeedClient` implements the six bounded AtomStorage
and AtomCommitSource methods under `immutable-commit-feed/1`: `create`, `get`,
`getMany`, `availability`, `head`, `readCommits`. Existing `Mutation`,
`AtomEnvelope`, opaque references, descriptor selection and operation-specific
validators are reused. The client accepts interface versions from `1.0.0` to
before `1.2.0` when every required operation/profile/guarantee is present. This
range reflects existing interface descriptors; it does not claim that an
arbitrary server is compatible. The example executes `1.1.0`. Native historical
service interoperability is a separate qualification gate.

The wire envelope matches the existing cognitive service's typed envelope;
`typed-atom-feed-https/1` is a new explicitly synthetic transport composition,
not a changed storage profile. Every response binds the request digest, ID,
descriptor selection and expected authenticated principal. Payload bytes are
verified against the immutable reference digest. TLS verifies the CA and peer
hostname. Explicitly select any other supported composition when constructing a
client; it is never inferred or used as a fallback.

```python
from fusion.preview_client import AtomFeedClient, Endpoint
from fusion.ports import Mutation

# Endpoint, credential, descriptor, principal, scope and absolute deadline come
# from trusted application composition; never from model-controlled tool args.
atoms = AtomFeedClient(endpoint, credential, principal, scope, descriptor,
                       deadline_ms=accepted_deadline_ms)
written = atoms.create(Mutation(scope, durable_occurrence),
                       "application/synthetic", b"approved synthetic payload")
payload = atoms.get(written["ref"])
```

The caller persists the mutation identity before submission. `get` observes
saved bytes without resubmitting a write. If a create reply is lost and no ref
was captured, acceptance remains unknown; this contract lacks the optional
mutation-observation method. Replay only the **same** mutation/content within
the caller's existing deadline/budget, or report unknown. Do not allocate a new
identity, infer rollback, or claim exactly-once transport calls.

The client has no retry loop, budget authority, fallback or cancellation method.
`retry_classification` offers explicit advice, not permission. Its absolute
deadline bounds transport observation; the historical synchronous source port
does not claim a provider-owned durable work budget or remote cancellation.
Applications must retain their existing acceptance/deadline/accounting owners.
`NOT_AVAILABLE` never becomes an empty feed or successful absence. Profile,
version, authority and malformed-response refusals retain typed error codes.

## Independent provider and conformance

See [the provider example](../examples/phase2_provider/README.md). Its exact
existing `FileFeedFixture` implementation is packaged independently. It shares
types and validators, and neither subclasses nor imports `FeedAtomOwner`,
DeTTa, a foreign database or the Omega application.

```sh
artifacts/reference-distribution/operator-venv/bin/python -m unittest tests.test_phase2_sdk tests.test_phase2_sdk_contracts tests.test_phase2_sdk_compatibility -v
```

The shared invariant runner exercises replay, conflict, hydration, batches,
availability, source pagination/snapshots, scope and digest refusal through only
the declared ports. HTTPS tests add revocation, wrong credentials/certificates,
descriptor mismatch, response binding, lost replies and actual provider
SIGKILL/restart. All provider data is a new generated synthetic scope.

Qualification here is **same-host authenticated HTTPS with an independent
file-backed contract fixture**. It is neither DeTTa nor DA evidence. Actual
native consumer placement and cluster substitution are not established by these
tests. No text-generation runtime is started/contacted and no model runs.

## Pure handles and typed tools in 0.2.0

The additive `fusion_sdk` facade exports the original objects, not wrappers or
separate validators. The exact supported export list is `fusion_sdk.__all__`;
[public-api.json](public-api.json) records profiles, argument kinds and excluded
application conveniences. Import this facade from a client-only installation:

```python
from fusion_sdk import (
    AtomFeedClient, Endpoint, Mutation, Descriptor, Requirement,
    HandleEnvelope, MemoryTarget, ParsedHandle, make, envelope,
    Argument, ToolDescriptor, Catalogue, SessionAuthority,
)
```

| Surface | Supported behavior | Explicit boundary |
| --- | --- | --- |
| `MemoryTarget`, `TaskTarget`, `ResultTarget`, `Target`, `HandleEnvelope`, `ParsedHandle` | Pure typed targets for memory, episode, event, relation, task and result | No alias store or resolver; opaque owner references stay typed |
| `parse`, `target`, `derive`, `make`, `envelope` | Original `omega-preview-handles/1` syntax, identity and recipient correlation | No source-existence, authorization, active-state or owner-acceptance proof |
| `Argument`, `ToolDescriptor`, `Catalogue`, `SessionAuthority` | Exact command validation, closed typed arguments, provider requirements, whole-batch admission and current supplied authority | No dispatcher, implementation registry service, application lifecycle or persistent authority owner |
| `context_tools` | Pure descriptions for the existing context vocabulary | No context-state implementation is installed |
| `Descriptor`, `Requirement`, `resolve`, `selection_token` | Original static compatibility and exact descriptor binding | No automatic re-resolution or unknown-store failover |

Supported argument kinds are `text`, `label`, `path`, `handle`, `memory-handle`,
`relation-handle` and `history-handle`. The `deduction` argument validator and
`deduction_tools`, `memory_tools`, `workspace_tools`, `history_tools`,
`lifecycle_tools`, `relation_tools`, `cognitive_tools`, `task_tools` and
`inspection_tools` application builders require runtime pins or
owner/application composition and are **not exported by `fusion_sdk`**. Their
unchanged definitions remain in the byte-exact raw `fusion.preview_tools`
source, but are outside this distribution's supported API. Use typed
`ToolDescriptor` values supplied by trusted composition for such applications.

The handle validator's `memory_contracts` dependency is also packaged byte for
byte. It imports Python's standard-library `sqlite3` exception types but opens
no database and instantiates no owner. Isolated-install tests reject any SQLite
connection during import and confirm that owner/provider packages and heavy
inference dependencies are absent. The independent example remains a separate
wheel and has an explicit dependency on client packages `>=0.1.0,<0.3.0`.

## Historical/current compatibility evidence

The original [qualification](qualification.json) is unchanged. The two small
[0.1.0 wheel inputs](compatibility/README.md) are archived under their original
hashes so a clean checkout can execute both historical endpoints without
reconstructing old code from current validators. Current builds go to a new
output directory; the historical wheel identities are never overwritten.

The installed-endpoint matrix executes all six declared operations through
real authenticated same-host HTTPS for all four package combinations:

| Client package | Example package | Storage interface/profile |
| --- | --- | --- |
| 0.1.0 historical | 0.1.0 historical | 1.1.0 / immutable-commit-feed/1 |
| 0.2.0 current | 0.1.0 historical | 1.1.0 / immutable-commit-feed/1 |
| 0.1.0 historical | 0.2.0 current | 1.1.0 / immutable-commit-feed/1 |
| 0.2.0 current | 0.2.0 current | 1.1.0 / immutable-commit-feed/1 |

Package 0.2.0 adds pure contracts and the current source's finite-JSON response
validation; it does not invent a new storage interface version or loosen the
closed wire envelope. The compatible restart test accepts a mutation with the
old endpoint, SIGKILLs it, restarts the new package over **the same independent
provider's owned state**, and replays through both installed clients. It checks
unchanged mutation identity, reference, feed head, selection token and original
deadline. This is compatible binary restart, not provider migration or failover
to a fresh store.

Negative checks report client compatibility preflight separately from actual
wire-binding refusal. Unsupported major, required feature, profile, privacy and
guarantee selections cannot execute. The storage example cannot qualify
numerical-kernel interoperability; a deliberately foreign numerical-profile
label is only a profile-binding refusal. Native-consumer substitution, service
rotation and cluster behavior remain independent programme gates.
