# Bounded Attention suspension supplement

This operator qualification is separate from the frozen handover acceptance
driver. It admits no Omega inputs and makes no model calls. Its initial focused
tests use explicit Kubernetes/containerd observation fixtures; only an executed
deployed report can establish the suspension gate.

After successful handover and its browser observation, freeze a concrete plan
using the actual handover report, current post-browser values, image manifest
and chart. Run the helper with the installed operator Python from outside the
author checkout:

```sh
"$OPERATOR_PYTHON" -I examples/pilot_attention_suspension.py freeze \
  --handover "$HANDOVER_REPORT" --values "$CURRENT_VALUES" \
  --images "$IMAGE_MANIFEST" --chart "$CHART" --output "$PLAN"
"$OPERATOR_PYTHON" -I examples/pilot_attention_suspension.py run \
  --plan "$PLAN" --directory "$PRIVATE_REPORT_DIRECTORY" \
  --kubeconfig "$KUBECONFIG" --context default --namespace "$REPLACEMENT"
```

The selected memory reference comes from the completed replacement's native
remember result and is hydrated through authenticated AtomStorage. The helper
reads the closed caller-owned allocation through SQLite `mode=ro` and
`query_only`, requires a non-historical `g2-shared` selection, and verifies its
frozen template and CA-bound runtime digest against current configuration.
It uses those current template clients directly; it does not recreate session
files, reopen a native session or transfer native session authority. Provider
credentials still undergo the existing current per-request authorization.
SQLite may maintain SHM read locks or an empty WAL during this observation;
the qualification preserves authoritative rows and bytes rather than claiming
that these engine lock files never change.

The helper
creates a fresh synthetic Attention context and establishes a real adjustment
through the existing pinned native wall-clock policy. A second adjustment is
reserved under its original 15-second deadline and stopped at the existing
`after_priority_reservation` test barrier. Before pausing, the operator binds
the task-owned namespace, StatefulSet, Pod and container identities to current
Kubernetes and containerd observations. Only that single captured container is
paused for at least 20 seconds and beyond the accepted deadline.

Cleanup resumes only the original container ID; it never follows a replacement
Pod automatically. The original Helm configuration is restored, retiring the
blocked process. The exact accepted binding, one spent reservation, absent
result and baseline state must survive the restart. An explicit expired
re-invocation of that same binding must refuse without another reservation or
evaluation. Selected owner diagnostics are read-only and remain in the private
report. The helper retains failures, replacement and uncertain outcomes.

The entire supplement has a 300-second bound including 75 seconds reserved for
cleanup. It does not extend the original handover window, renew the adjustment
deadline, refund a reservation, delete the barrier or manufacture completion.
Configuration restarts and container suspension are reported separately from
native invocation counts. No node, k3s control-plane container, protected
namespace or host-wide cgroup setting is paused. Private references and journal
digests must be withheld from the public summary.
