# P14/P16 cross-feature evidence review

This is a bounded development review against
`c4fb744edbddd003d09db408bed44a59d2df3823` plus the current Phase 2 working tree,
on 2 November 2026. It adds tests and this document only. It does not mark P14,
P16, the current deployed qualification, or the whole preview complete.

The [primary brief](../../codex_omega_phase2_multi_agent_developer_preview.md)
requires both actual client/server interoperability and integrated failure
evidence. Its reviewed SHA-256 is
`3cb1833eefd590861b784aedf9586bb18bfe5f99eee57a66b7b5ace7fb645013`.
The ongoing [programme report](programme-report.md) and
[scenario matrix](scenario-matrix.md) remain the programme-level records.

## Newly executed checks

```sh
artifacts/reference-distribution/operator-venv/bin/python -m unittest \
  tests.test_phase2_cross_feature_edges -v
```

**Eight methods passed in 1.081 seconds**, with zero skips. The first development
run had one test-authoring error: the new Relations test omitted the required
`expected_asserted_at` argument. Correcting that test invocation produced the
passing run; no production defect or production edit resulted.

| Methods | Independently observed outcome | Evidence boundary |
| --- | --- | --- |
| Recipient credential rotation after mailbox capture | Old credential is refused before session acceptance or acknowledgment; the refused attempt still spends its reserved call. Updating only the caller credential resumes the same delivery, original deadline and frozen selection, with one accepted input and one mailbox occurrence. | Actual task client, Policy, Messaging, ingress and SessionStore; in-process transport and FileFeedFixture. No certificate or wire-rotation claim. |
| Current recipient membership on publication replay | Revoking the recipient's mailbox read permission blocks sender observation/replay of its accepted publication. Restoring that permission returns the original receipt without another mailbox row. | Actual task/Messaging ownership and current Policy; fixture transport. |
| Acknowledgment revocation after session commit | Session acceptance survives a denied mailbox acknowledgment. Recovery retains the one accepted input and original deadline, eventually acknowledges the existing delivery and does not refund spent calls. | Separate real SQLite commits; hook interruption fixture, not a process kill. |
| Current peer revocation after capture | Removing the genuine sender from the recipient's current peer selection rejects the captured task before native input acceptance and acknowledgment. Reinstatement resumes the original delivery. | Actual ingress record validation; genuine generated task record, not a forged mock response. |
| Retained lifecycle views and current disclosure | Supersession and an unrelated change leave an older snapshot unchanged. Withdrawal blocks active disclosure through both older revisions; separately authorized historical disclosure remains possible. Revoking historical permission blocks it. Original atom bytes remain intact; no erasure, belief-weight transfer or priority transfer is claimed. | Actual lifecycle owner and Policy; generated enrollment with fixture vectors and FileFeedFixture. No Search/Chroma pass. |
| Revocation during payload hydration | Authority revoked after the payload is read still prevents disclosure from returning. The lifecycle journal remains unchanged and the separate historical permission is checked independently. | Actual lifecycle checks around a deliberately injected revocation race. |
| Historical/retractable Relations journals | The existing assertion-only owner refuses a populated retractable journal; the retractable owner refuses a populated assertion-only journal. Both logical database contents and AtomStorage head remain unchanged; each original owner still reads its state. | Both actual owner implementations from this checkout. This is schema/profile rejection, not an older deployed binary rollout. |
| Populated session profile refusal | Old/future profile markers and an unsealed populated session journal are rejected before schema or row mutation; accepted input state and deadline remain intact. | Actual SessionStore constructor with deliberately altered fixture metadata. No historical binary is executed. |

These eight methods are not eight native workflows. They do not run a model,
native Omega, HTTPS listener, E5, Chroma, DeTTa, process kill or pod replacement.
The task fixture delegates to the real owners through an explicitly patched
in-process transport. It is not a resolver-only test, but it is also not wire
interoperability. The lifecycle enrollment vectors and AtomStorage provider are
labelled fixtures. Private-scope implementation and qualification remain with
the separate P05 work; these tests make no private-scope coverage claim.

## Executed source identity

The following production files were hashed before and after the test execution
and did not change during it. Other programme files may continue changing.

| File | SHA-256 |
| --- | --- |
| `fusion/preview_tasks.py` | `18c20255cbdf414d58db78c9763b0c65c24138e9ab0be76f473520ab1bf0f7e3` |
| `fusion/messaging.py` | `8afdac506f05308e7a8cc61e642353c9217525d4d5e703e45c2d583a518d7406` |
| `integration/single_node/preview_task_ingress.py` | `d8bb7efac28da42e54700a2ae4653791bddc34f3503b4df1f31eb4d377f7a004` |
| `fusion/preview_sessions.py` | `9941756bc49758f7b696eda1183c5bef4510a2a9efc21eef78bc118231048fef` |
| `fusion/preview_lifecycle.py` | `0f1b15a1d9b1c950ff4a280858de0f9b42787004157f9edbf5d0b066d97e6648` |
| `fusion/preview_relations.py` | `b32758c7b76788af3792a2a189f233fb0c649c2e610d050c734901892388f704` |
| `fusion/relations.py` | `1dccbc105c761c69064ff2dc152b2b2af10fbeff6314da9d31cd1d820865383d` |
| `fusion/policy.py` | `dcab3e306907c163caabf98bedf3be582a8b84b679e8971c4703a0cdf900b18f` |
| `tests/test_phase2_cross_feature_edges.py` | `8ae15b5ea193c5225e9ab822abd68ddc7d74ccd92bab39b331f987bb1bd5085d` |

## Existing evidence and what it establishes

The [SDK qualification 02](../../sdk/qualification-02.json), SHA-256
`0168927839baa627c1fcb16cdb8851bbc9444670786074248fc40e304c00ebeb`,
records seventeen methods, with four old/new installed-package endpoint
pairings as scenarios within them. Both processes execute authenticated HTTPS.
The provider is the independent atomic-file contract fixture. Packages 0.1.0
and 0.2.0 retain the existing `atom.storage` interface 1.1.0 and
`immutable-commit-feed/1`; additive package exports do not invent a new wire
version. Accepted identity, deadline and descriptor survive a provider process
kill and compatible package restart over the same owned state.

Its unsupported-major/profile/privacy/guarantee and required-feature checks
distinguish client preflight from actual wire descriptor-binding rejection.
Resolver checks alone do not prove interoperability. Its report explicitly
leaves native-consumer substitution and deployed rotation unrun. It is a
development source-bound qualification, not a qualification of later image
bytes. See the [SDK compatibility account](sdk-compatibility.md).

Existing task, lifecycle, Relations, workspace, model, history-deadline and
backup tests cover many owner-level refusals and interruption boundaries.
Their exceptions, direct ports, mocked source clients, actual local owners and
real provider tests must retain their respective labels. The current
[recovery runner](../../integration/single_node/preview_recovery_qualification.py)
contains deployed execution recipes, not passing evidence merely by existing.
Its reviewed SHA-256 is
`73b7a26fd8f2f464b1d366038715434cc35ea62b34ce6bf9729db477aff31e4d`.

At this review snapshot, published dev10–dev12 qualification reports retain
`FAILED`. The dev14 qualification report was still nonterminal; this review
does not infer completion from its intermediate scenarios. Later root-agent
execution must reconcile this snapshot with its exact reports and image pins.

The historical [single-node model/channel test record](../../evidence/single-node-model-channel/tests.json)
still contains `known_baseline.status=OPEN_ERROR` for
`tests.test_m5_boundaries.Boundaries.test_lookup_has_no_cognitive_runtime_dependency_or_mutation`:
the Python 3.12 protocol/fixture failure at `fusion/private.py:150`. This review
does not delete the ownership check, rewrite that old result, or silently count
it as passing. The later A–N [programme report](../reference-distribution/programme-report.md)
records its separate repair/regression evidence. Historical and current-source
results remain distinct; this eight-method suite did not rerun that baseline.

## Deployed gates still requiring programme execution

The following are open **in this review**, not declarations that future root
execution is blocked. Read final reports before retiring any item.

| Gate | Required observation and current executable path |
| --- | --- |
| Remote independent same-policy replacement | Run `integration.single_node.preview_qualification --mode attention-replacement` with the same native caller image and policy against the primary and independent `file-fixture` Attention implementations in separate fresh namespaces/PVCs. Select `preview.cognition.attention_provider` before session admission. Record authenticated service-DNS HTTPS and unchanged truth while native promote/demote affect priority. The independent atomic-file implementation remains labelled as such; this is no migration or accepted-operation failover. |
| New-profile pod failures and response loss | After a successful native report, run `integration.single_node.preview_recovery_qualification`. Its five fault cases cover native input capture, workspace effect, relation response loss, recorded-model capture and lifecycle commit before publication, plus two native readbacks. Observe changed pod UIDs, unchanged PVC/image identities, same occurrence/deadline and monotonic spent attempts. Missing fault markers or timeout are failed/unobserved outcomes, not permission to resubmit. |
| Cross-agent context-handoff recovery and retained-view races | Interrupt after B captures its query and before A consumes the correlated result; preserve the actual immutable task/result references. An unrelated memory change must not rewrite that captured view. Withdrawal or unavailable retained data must fail current disclosure rather than select a new view. Existing owner/adapter tests do not establish this deployed combination. |
| Credential and certificate rotation | Exercise current old-credential refusal and new-credential acceptance against actual preview services. Rotate only the selected same-CA leaf where the current client binding permits it; show certificate identity changed, CA binding retained, accepted selection/occurrence unchanged and no fallback. Historical `test_security_cluster` is an S01 composition, not an automatic preview pass. The new tests establish only in-process credential semantics. |
| Compatible application restart and incompatible rollback | Reopen accepted preview state after a compatible caller rollout and observe its original capture/deadline/budget. Attempt the explicitly unsupported schema/profile configuration on a disposable copied owner journal; record refusal before worker/effect activation. New unit tests prove owner checks, not older-image admission or full chart rollback. Do not weaken a journal marker to make rollback succeed. |
| Actual fenced restore | Use `Operator.backup` after quiescing all selected writers, then `Operator.restore` into a separate task-owned namespace. Observe lifecycle/context/task/Relations/workspace state and retained captures with no resumed worker or external effect. Old authority is excluded. The `f1r3node` PVC stays stopped and retained in the original namespace; cryptographic node state is not mounted/exported, so no node restore/failover is claimed. |
| Final combined and bounded-load semantics | Finish actual two-direction task handoff, cognition, native lifecycle/workspace and same-workflow chain evidence on exact tested images. Run the declared bounded repeated-turn envelope with original deadlines and caps. Keep wrong-but-permitted answers, absent target, inaccessible payload, unready source, overload and timeout distinct. Historical IRC/chain uncertain-send results remain separately identified; no new IRC or chain recovery pass follows from these tests. |

The existing recovery entrypoint takes a **completed PASS** native report; it
must not be aimed at an in-progress or failed report. Its bounded command is:

```sh
python -m integration.single_node.preview_recovery_qualification \
  --kubeconfig "$PREVIEW_KUBECONFIG" --context "$PREVIEW_CONTEXT" \
  --namespace "$PREVIEW_NAMESPACE" --values "$PREVIEW_VALUES" \
  --chart "$PREVIEW_CHART" --native "$COMPLETED_NATIVE_REPORT" \
  --output "$NEW_RECOVERY_OUTPUT"
```

The caller of this command must supply the actual task-owned namespace and
frozen artifacts. The runner retains one-shot `pause.json` and
`response-dropped.json` markers. It must not clear them to replay a fault, renew
an expired input, or count a replacement input as recovery. A fresh preparation
can use `preview_qualification --mode recovery-setup`; its inputs are separately
counted from fault cases. `--mode attention-replacement` similarly creates fresh
sessions and must not switch a populated Attention provider in place.

No cluster command was executed for this review. No generative runtime was
started, loaded or contacted. **ADDITIONAL_LIVE_GENERATIONS=0**.
