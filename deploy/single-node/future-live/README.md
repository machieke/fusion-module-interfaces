# Disabled future experiment

`plan.json` proposes one new HTTPS query/reply session, maximum two generations. It is **INCOMPLETE**, has zero current allowance, contains no approval, and is not selected by the recorded chart. Both slots are unreserved. No absolute occurrence deadline has begun.

`runtime-pins.json` copies published public identities for the existing runtime/model, including the full model and projector digests. These are historical pins, not a new verification of files or a checked runtime. No runtime process, model loader or endpoint was contacted during preparation.

Offline inspection:

```bash
artifacts/s03/venv/bin/python -m integration.single_node.future_live deploy/single-node/future-live/plan.json
```

The future connection uses the existing `OllamaCompletion` and `ModelPorts`; it accepts neither fixtures nor an enabled flag as approval. Its separate two-slot envelope leaves the historical four-slot campaign machinery unchanged. Write-once claims use the same fsynced publication/locking primitives, colocated with ModelService on the provider PVC. `projection()` reports the union from the provider's own reservations and claims. A reservation without a claim remains spent, and a claim does not prove a backend call completed.

Before any future activation, freeze a fresh live corpus/view and owner PVCs, source/image hashes, selected DNS/TLS identities, complete consent and execution policies, relocated runtime lock and **all** runtime/model blob hashes. Supply a new explicit approval naming the manifest digest, two slots and bounded execution window. The existing historical approvals cannot be reused. The recorded qualification journals are never adopted as live campaign state.

The runtime should be colocated with the model owner in its future isolated pod; the native agent continues to use authenticated module HTTPS. Runtime files must be image-owned, not a host working-tree or another owner's mutable mount. Do not use a health probe that loads a model or generates text. Current runtime availability remains `NOT_CHECKED`, and no generative runtime image is asserted verified.

The unselected executable connections are:

```bash
python -m integration.single_node.future_live /config/live-plan.json \
  --approval /approval/user-approval.json --component /config/component.json --serve
python -m integration.single_node.future_live /config/live-plan.json \
  --approval /approval/user-approval.json --runtime
```

These are future container commands, **not instructions to activate this incomplete plan**. Both reject the delivered plan before sockets, backend construction, runtime launch or reservation. The service path reuses the ordinary single-node HTTP host and ModelPorts. The runtime path fixes the isolated historical `serve` recipe (loopback port 48173, cloud disabled, one loaded model/parallel request), with image-owned paths. The future provider and runtime image must both contain the frozen files they validate. The current Helm schema deliberately admits recorded mode only; an explicitly reviewed future activation overlay must bind the complete plan and existing Secret references.
