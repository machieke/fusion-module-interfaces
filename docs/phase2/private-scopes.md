# P05 synthetic private-scope boundary

The preview retains one shared synthetic corpus and adds one distinct synthetic
AtomStorage scope per agent. These scopes isolate approved test records; they do
not authorize moving existing private user data or claim that the shared native
history has become confidential.

`preview.scope` remains the shared scope. Newly generated values also set
`preview.agents[role].private_scope` to the shared scope followed by
`-private-a` or `-private-b`. Both private selections must be supplied together,
must have valid synthetic scope names, and must differ from each other and the
shared scope. Older explicit configurations without either field remain
shared-only. They are not relabelled as private-scope qualifications.

| Boundary | Shared scope | A's private synthetic scope | B's private synthetic scope |
|---|---|---|---|
| A's authenticated AtomStorage operations | Permitted by current grants | Permitted by current grants | Denied |
| B's authenticated AtomStorage operations | Permitted by current grants | Denied | Permitted by current grants |
| Delegated C1/Relations/cognitive storage credentials | Only their declared operations | Denied | Denied |
| Shared Search/indexer, task and commitment composition | Existing shared selection | No new grant | No new grant |

The existing storage process and PVC remain the sole writer. Its feed and DeTTa
payload addressing already bind scope; no new database owner or shared mutable
mount is introduced. The opt-in `allowed_scopes` configuration is a closed set of
at most three scopes and is supported only on the AtomStorage cognitive port.
Membership in that list is not authority: both the authenticated transport actor
and its represented principal need the current operation grant. Other cognitive
interfaces retain their existing single-scope configuration.

The outer request scope must match each nested AtomRef, Mutation, head or feed
scope. Even an agent authorized for two scopes cannot mix their references in one
request. Each agent receives its own `/run/fusion/private-atoms.json` containing
the existing typed client configuration, scoped principal and HTTPS selection.
It contains no foreign owner path. The model does not select credentials,
endpoints or the private scope. Existing profile/numerical behavior and the
normal native shared-memory workflow remain unchanged.

## Shared history is explicitly shareable

`EpisodeOwner._episode` requires the episode's owner to equal the authenticated
principal. Accordingly, B cannot use C1 `historySnapshot`, `readHistory` or
`readEvidence` to read A's episode, even when both have permissions in the common
scope. The native facade also resolves handles from its own accepted history.

However, the current native history, event wrappers and source payloads are
stored in the **shared** AtomStorage scope. A scope-authorized B can enumerate
that feed and hydrate those bytes directly. C1 episode ownership does not override
the selected AtomStorage disclosure policy. Positive workflow history is approved
synthetic shared data; it must never be labelled private solely because C1 rejects
another principal's semantic episode read.

The new private scopes are bounded storage/authorization qualification selections.
They do not silently move C1/C2, Attention, memory enrichment, the native session
history or structural labels. Making any of those private would require an
explicit further composition and disclosure decision; a shared structural link
must not confer access to a private event.

## Isolated tests and deployed evidence

[`test_phase2_private_scopes.py`](../../tests/test_phase2_private_scopes.py) uses
the actual `cognitive_services.Ports`, `Policy`, `AtomSession` and SQLite
`FeedAtomOwner`, with an explicit in-memory DeTTa byte/receipt-shape fixture.
Generated configuration and role-separated credential material are real; TLS
certificate bytes and image metadata are fixtures. A separate test uses the real
C1 history owner over `FileFeedFixture` to distinguish episode ownership from
shared payload access. No TLS handshake, DeTTa process, native Omega turn, pod
replacement or cluster integration is claimed by these tests.

The tests cover positive owner reads/writes, replay without duplicate acceptance,
separate scoped feed coverage, every cross-agent AtomStorage operation, mixed
outer/nested scopes, delegated-actor restrictions, current revocation, unknown
identity, shared-membership removal, malformed allowlists and old single-scope
compatibility. A reconstructed port over the retained test journal is not a
process-kill qualification.

The initial 15-method run found three malformed-allowlist subcase failures and
one list-valued configuration error. Those development failures are retained in
the tool transcript. The configuration now validates scope types before using a
set, and the storage allowlist requires the same closed synthetic-name syntax.
The added C1/shared-payload distinction test brings the recheck to **16 methods,
all passing in 1.237 seconds**. Counts are methods, not native workflows.

The separate final dev19 [deployed qualification](../../evidence/phase2/final/private-scopes-rotation.json)
passed **28 cases** in `omega-ref-phase2-h19b`, using actual authenticated HTTPS,
DeTTa and current image identities. It checked private create/read/feed, all six
cross-scope denials, wrong credentials, storage outage and unchanged source head,
A credential revocation with B unaffected, replacement credentials and a same-CA
TLS leaf rotation. Native sessions were idle; application/model accounting was
unchanged. The [two-client source check](../../evidence/phase2/final/shared-source.json)
separately exercised concurrent approved opaque writes through one authoritative
owner and retained feed coverage. Neither direct port check adds a native private
memory command or changes the shared-history disclosure boundary above.

The runtime source map is
`369daf1ab470fb8fe8265fe16a3a5765670c643e7011e3d5369636a803e7e49d`.
Original fixture tests and dev14 shared-only results retain their historical
identities; they are not the source of the deployed pass.

Invocation:

```sh
artifacts/reference-distribution/operator-venv/bin/python -m unittest tests.test_phase2_private_scopes -v
```

`ADDITIONAL_LIVE_GENERATIONS=0`. The isolated tests above did not contact native/cluster runtimes; the separately
linked deployed qualification did. Neither contacted a real generative runtime.
