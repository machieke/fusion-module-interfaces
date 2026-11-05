# Registered native continuations

`guarded-native-continuation/1` is a bounded facet of the existing application inbox owner. It reserves and submits existing native inputs, records owner observations and waits for actual captured results. It does not add a model, tool executor, generic graph engine or scheduler.

The three recipes are `knowledge-handoff/1`, `evidence-aware-review/1` and `approved-artifact-delivery/1`. Their closed tool sequences and finite data references live in `fusion/workflow_recipes.py`. Parameters may reference an earlier actual capture; no expected retrieval answer is supplied to the consumer. The artifact recipe takes the actual consumed delegated result as workspace bytes. Chain signature/commitment remains a separate exact-result approval and the existing chain continuation.

Prerequisites use current authenticated owner ports: exact active memory revision, structural relation state, immutable snapshot availability, a finite predicate over an existing NAL belief value, exact captured input result, or application capacity/current authority. Read failures are `UNKNOWN`; revocation is `UNAUTHORIZED`. Neither implies a false premise or permission to continue. Cross-owner reads are explicitly non-atomic and the observation-to-admission race window remains visible.

Plan amendments are compare-and-swap changes to unstarted suffixes. Started work, unknown effects, accepted identities, deadlines, prior captures and spent reservations cannot be replaced or refunded. Operator checkpoints bind the actor, exact version/plan, provider selections, evidence observations, capture digests and original deadline. Approval grants no new authority; current guards and permissions are rechecked before effects. A late decision is retained but ineffective.

Native submission identity is deterministic per workflow node. Reservation commits before submission. If an interruption leaves reservation without known acceptance, reconciliation observes; it does not manufacture acceptance or silently resubmit. The original owner quota includes bounded workflow metadata and reserved completion space. Observation-only restores refuse mutation.

## Qualification entrypoints

`examples.pilot_workflows` exercises a knowledge handoff, actual B-result consumption, a result-captured prerequisite and an explicit checkpoint. Variants are unchanged, actual source withdrawal and irrelevant source change. `examples.pilot_recipe_qualification` exercises the other two recipes. Its evidence review freezes an actual post-support belief predicate before contrary assessment, requires the real changed owner value to hold the dependent step, then explicitly amends the remaining query. It does not substitute a numerical calculation or force an expected guard outcome.

`examples.pilot_window_workflow.between_windows(op, directory, boundary, programme_end)` runs three finite inter-window cases: unchanged, withdrawn, unchanged. The middle checkpoint includes actual caller pod replacement before approval. Each case has three recipe inputs; the withdrawn case adds one explicit native forget. Actual recipient and returned-task inputs are counted from their owner receipts separately. These inputs do not replace any of the sustained programme's 160 inputs, and no workflow deadline can extend the enclosing programme end.

The independent evaluator freezes expected prerequisite/progression outcomes before native work. It scores safety, factual correctness, actual tool results, provenance and external effects separately. Safe refusal does not become positive task completion; a wrong permitted answer fails. The fixture-model designation is explicit. Unit fixtures, real SQLite/SIGKILL checks and deployed-native reports remain separate evidence classes.

```sh
python -m examples.pilot_workflows --kubeconfig "$KUBECONFIG_FILE" \
  --context default --namespace TASK_NAMESPACE --directory FRESH_REPORT \
  --variant withdrawn
python -m examples.pilot_recipe_qualification --kubeconfig "$KUBECONFIG_FILE" \
  --context default --namespace TASK_NAMESPACE --directory FRESH_REPORT \
  --recipe evidence-aware-review/1
```

These helpers use normal authenticated workflow/session ports. They export exact owner receipts to `workflow-native.json`, retaining the direct-input report separately. No invocation shown here itself establishes an executed qualification pass; use the bound primary reports and image/source manifests.

The complete artifact-delivery qualification is `examples.pilot_recipe_chain`.
It retains the recipe session, reads the written file through an additional
actual native command, and hydrates the captured task result through the declared
AtomStorage port. Their bytes and receipt digest must match. The existing
`inspect-atom/2` operation inspects the immutable retrieval envelope, including
that captured task-result reference; it does not claim to inspect a mutable
workspace file directly. The next native input consumes the inspection feedback.

Only then does the existing chain continuation receive a separate exact-result
registration. The driver reuses the Q continuation's single submit reservation,
fixed chain window, deliberate response loss, caller/provider/node replacement,
signed-intent reconciliation and independently scheduled readback. It never
creates a second signature to repair an uncertain submit. All original native
captures and deadlines are compared after recovery.

```sh
python -m integration.single_node.pilot_values --images IMAGES_JSON \
  --scope synthetic-pilot-recipe03 --namespace omega-ref-pilot-recipe03 \
  --chain --output FRESH_VALUES
# Use the documented fresh namespace and Secret installer. It binds a fresh
# unfunded public key before the inert node seals its PVC. Node activation is
# disabled until the qualification verifies the actual isolation probes.
python -m examples.pilot_recipe_chain --kubeconfig "$KUBECONFIG_FILE" \
  --context default --namespace omega-ref-pilot-recipe03 --values FRESH_VALUES \
  --chart PINNED_CHART --output FRESH_REPORT \
  --observer examples/preview_chain_observer.py
```

The chain path has five operator-selected native inputs: one setup remember,
three registered recipe inputs, and one native workspace readback. Internally
accepted task/result inputs are counted separately from these five. This command
is an executable recipe, not evidence that the real-chain gate has passed.

`--variant unknown` temporarily stops the real storage owner before reading the
unchanged memory prerequisite. `--variant unauthorized` revokes only A's current
storage credential at the provider, restarts that provider, and performs the
same owner read with the caller's original credential. Both must hold the exact
unstarted suffix with two spent reservations and unchanged captures. The helper
restores the original service/credential even if the observer fails; it never
exports credential bytes. Restoration alone does not advance the workflow:
explicit checkpoint approval and fresh guard observations remain required under
the original deadline. These deliberate task-namespace controls are not a
simulation of a provider response.

The provider fault must rotate both `caller-token` and `caller-A-token` in one
Secret update: these are the S01 and memory aliases of the same storage
principal, and startup requires them to agree. Their original values must also
be restored together. The historical operator13 helper changed only one alias;
its recipe13 attempt failed provider startup before observing the prerequisite.
That failed report is retained. A separately source-pinned recovery changed both
aliases, observed an actual `UNAUTHORIZED` guard, restored the provider, and
completed the same workflow before its original deadline. The later helper fix
has separate fixture tests; it is not relabelled as the executed historical
operator13 helper.

`--variant unchanged --archive-prerequisite` adds a combined archive case. After
actual native memory/delegation capture, the helper seals that exact payload
through the existing bounded owner archive port under a workflow-specific
maintenance identity. Its returned reference and content type define an
additional `snapshot-available` guard. The native continuation reads it through
AtomStorage after archive activation. Existing sealed-archive semantics prefer
the activated segment and refuse a missing/corrupt segment without hot-copy
fallback. No native answer, source head, prior capture or input budget changes.

`qualify(..., checkpoint_decision=callback)` lets the installed browser driver
interact with an actual paused native recipe. The callback return value is
ignored. The helper independently observes the owner’s committed decision and
exact checkpoint. Approval permits only the original guarded suffix; refusal
or a late ineffective decision records safety success and an uncompleted
positive task, retaining the two earlier native captures and spent inputs.

`examples.pilot_workflow_restore` observes a previously completed shared recipe
through an authority-free clone. It reuses the normal quiesced backup/import,
verifies every imported owner’s actual read-only restore marker before omitting
writer-authority selection, and keeps the original source values unchanged.
Current scoped observation authority is separately issued. Saved plans,
captures, checkpoint decisions, original deadlines and reservations are
compared; advancing or creating a checkpoint is denied. This does not refresh
prerequisites or turn historical approval into present execution authority.

```sh
python -m examples.pilot_workflows --kubeconfig "$KUBECONFIG_FILE" \
  --context default --namespace omega-ref-pilot-recipe03 \
  --directory FRESH_ARCHIVE_WORKFLOW_REPORT --variant unchanged --archive-prerequisite
python -m examples.pilot_workflow_restore --kubeconfig "$KUBECONFIG_FILE" \
  --context default --original omega-ref-pilot-recipe03 \
  --clone omega-ref-pilot-recipe03-observation --values FROZEN_SOURCE_VALUES \
  --chart PINNED_CHART --directory FRESH_PRIVATE_RESTORE_DIRECTORY \
  --native-report FRESH_ARCHIVE_WORKFLOW_REPORT/report.json --images IMAGES_JSON
```

The restore command retains private owner archives and fresh Secret files only
in its mode-0700 operator directory. Publish approved sanitized reports, never
those archives or credentials. Actual archive, native recipe, browser and
restored-clone executions must each have their own primary evidence; these
commands and unit fixtures alone do not satisfy those gates.

The artifact recipe defaults to `--representation full-projection`. It writes
the exact captured task-result projection and refuses a projection outside the
existing 4096-byte command bound. No content is shortened. For a bounded
reference document, select `--representation reference-document` explicitly on
`qualify-recipe-chain` (or `examples.pilot_network_edges chain`). After native
B completes and A consumes its result, this option hydrates the correlated
source through AtomStorage, validates the existing inspection-artifact domain,
and amends only the unstarted suffix. A new version-bound checkpoint approves
the reference write; the inspection has its own existing checkpoint. Original
workflow deadlines, reservations and completed steps remain unchanged.

The document contains task/result references plus the full captured projection's
byte length and digest. It is neither an answer nor a replacement observation.
Native `read-file` must return its exact bytes. The independent observer binds
the known command echo to the actual return, so JSON in the write argument
cannot be mistaken for a receipt. The inspected and chain-approved object is
still the existing `synthetic-agent-retrieval-artifact/1` envelope: at most
three complete hydrated observations and 4096 total bytes, referencing the
full retained result. The whole task projection is **not** inspected or placed
on chain. More than three observations, oversized content, and an oversized
complete envelope are explicit refusals; no hidden selection or truncation
makes them admissible.

The original recipe13 full-projection attempt remains failed. Its actual task
record contained 5698 projection bytes and eight payload references; the
separate native B capture was 9259 bytes. An explicitly approved same-workflow
reference amendment captured the write, but inspection remained dispatched at
the original deadline with three workflow reservations spent. Its runtime
failure code was not captured; the eight-reference source is independently
outside the existing inspection domain. No native readback or chain operation
was performed for that failed attempt. Any corrected fresh qualification has
a separate source, namespace, plan and result; it cannot overwrite this history.
