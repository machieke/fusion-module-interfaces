# SDK, operator packaging and compatibility boundaries

This document records the bounded P03/P14/P17 package contribution. It is not
the final Phase 2 source/image freeze or an additional native integration count.

## Executed SDK evidence

The immutable [original qualification](../../sdk/qualification.json) executed
12 methods against package 0.1.0. Its artifact identities are retained in
[`sdk/compatibility`](../../sdk/compatibility/README.md).

The separate [development qualification 02](../../sdk/qualification-02.json)
executed 17 methods: the original 12 plus two isolated pure-contract methods
and three installed-endpoint compatibility methods. Four endpoint pairings are
scenarios inside the matrix, not four additional test methods or native
workflows. Both endpoint processes execute actual authenticated HTTPS; their
storage implementation remains the explicitly independent atomic-file contract
fixture. No DeTTa, native Omega consumer, cluster or numerical-kernel pass is
inferred from these tests.

| Client package | Independent example package | Interface/profile | Executed scope |
| --- | --- | --- | --- |
| 0.1.0 archived | 0.1.0 archived | atom.storage 1.1.0 / immutable-commit-feed/1 | Six operations and invariant cases over HTTPS |
| 0.2.0 development | 0.1.0 archived | Same | Six operations and invariant cases over HTTPS |
| 0.1.0 archived | 0.2.0 development | Same | Six operations and invariant cases over HTTPS |
| 0.2.0 development | 0.2.0 development | Same | Six operations and invariant cases over HTTPS |

The additive package exports pure typed handles and tool contracts; it does not
fabricate a higher storage wire version. Original accepted mutation identity,
deadline, descriptor selection, source head and result survive a compatible
package restart over the same independent provider's owned state. This is not
state migration or failover to a different empty provider.

Compatibility preflight refusal and actual wire selection refusal are reported
separately. Required features, incompatible major/profile/privacy/guarantees
remain closed. A foreign numerical-profile label is a profile-refusal test,
not numerical interoperability evidence.

The installed operator subset and its explicit prerequisites are documented in
[`sdk/OPERATOR.md`](../../sdk/OPERATOR.md). That separate wheel leaves the client
kit owner/runtime-free. Its core installation and mocked transport tests do not
establish a deployed workbench pass; the programme retains that evidence
separately. The final candidate03 wheels were rebuilt after shared runtime sources stabilized.
[Qualification04](../../sdk/operator-final-candidate-qualification-04.json) passed
26 methods with no skips against that exact eight-wheel house. The operator was
installed offline into a fresh environment and used for final dev19 deployments.

The [distribution review](../../sdk/DISTRIBUTION_REVIEW.md) records the actual
eight-wheel dependency/license metadata, authored verifier-fixture evidence
and conditions for the final artifact-only installation gate.

## P01 initial inspection findings requiring final reconciliation

The initially inspected `fusion.preview_capabilities` generator was not a complete
current capability manifest. It advertised only context pin/unpin/inspection
and original remember/query. It needs to project the **same selected typed
catalogue** used by the actual native configuration, including implemented
history, relations, lifecycle, workspace, task/cognitive/inspection capabilities
and named NAL when selected. Internal capabilities need their own records;
excluded broad legacy commands must not be counted as adopted.

The initial evidence input accepted unchecked booleans and arbitrary report values.
It needs exact report identities/source hashes and consistency checks against
registered implementations and exercised profile/placement combinations.
Input/output schema, exact native entrypoint, disclosure contract, limits,
recovery and intentional changes should be explicit fields. Preserve the
historical mapping and fifteen-family denominator. P02/diagnostics should
consume this generated projection rather than a second hand-maintained list.

These are retained initial inspection findings. The primary agent is updating
the generator, its evidence binding and catalogue use. Reconcile them with the
final generator/tests before publication; do not present these historical gaps
as unresolved solely from this earlier inspection.

## P17 inspection findings requiring integrated qualification

1. Extend the existing CI lane definitions with Phase 2 schema/SDK/provider,
   native, recorded cluster and explicit isolated-chain scenarios. The existing
   hosted fast job is restricted and unprivileged, but currently names only
   historical reference tests. Hosted execution remains `NOT_OBSERVED`.
2. The narrow install closure is now packaged: exact image-import/Secret
   recipes, fresh-values selection, pure deployment/address helpers and the
   existing workbench. It avoids broad reference CLI campaign imports and uses
   explicit artifact/chart/values paths with the existing Helm CLI. Its light
   tests use real TLS/cryptographic libraries and explicit kubectl/Docker stubs;
   real artifact-only cluster installation still requires the integrated gate.
3. Run one fresh namespace installation from the declared final chart, exact
   images and packages without unlisted source copies. Configurable container
   import already exists; other runtime modes need explicit rendered-only or
   executed labels.
4. Include the final wheels in the distribution manifest. Reconcile source
   hashes across all tested images, wheel inputs and experiments; a passing
   union of development sources is not one immutable distribution pass.
5. Generate the complete artifact/dependency/license inventory. The added wheel
   inventory covers actual package bytes and declared dependencies, and retains
   unknown licenses. Existing image/native asset inventories must remain part
   of the final SBOM; vulnerability scans are independent timestamped results.
6. Retain platform, warm-cache/model/parent-image prerequisites and disk/RAM
   observations. No current package test establishes empty-cache or air-gap
   installation, remote deployment, production readiness or live generation.

`ADDITIONAL_LIVE_GENERATIONS=0`. Historical qualifications and unresolved facts
are preserved; final-source qualification has not been silently refreshed.


The primary agent extracted the shared pure composition constant and address
helper, so fresh values and isolated synthetic chain key setup no longer require
runtime owners/chain adapters in the operator package. The exact native/model
implementations remain in the role images. See the current
[portable install commands](../../sdk/OPERATOR.md) and optional wheel pins.

## Final reconciliation of the inspection findings

The initial findings above are historical. The current executable capability
registry contains all twenty registered descriptors, exact native entrypoints,
typed arguments, closed profile requirements and evidence hash validation.
Current positive attachments are published in the [capability manifest](../../evidence/phase2/capabilities.json),
with operation-specific workflow/provider/fixture distinctions. Tests reject
unbound evidence, unknown implementations and incompatible selections.

The existing CI workflow now has Phase 2 fast, native, recorded-cluster and
opt-in isolated-chain lanes. Hosted execution remains **NOT_OBSERVED**; local
checks are in the [checks receipt](../../evidence/phase2/final/checks.json).
Final artifact-only installations use the dev19 image set, chart0.5.1 and
unchanged candidate03 wheels from extracted declared source. Helpers and public
evidence can change independently of the frozen330-file runtime source map;
the final detached artifact record binds those differences explicitly.
The [programme report](programme-report.md) supplies actual integration and
inventory results, remaining resource limits and the final publication identity.
