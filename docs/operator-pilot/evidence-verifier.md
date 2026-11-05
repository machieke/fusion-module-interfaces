# Offline pilot evidence verifier

Run `python -m integration.single_node.pilot_evidence verify evidence.json` from
the extracted operator artifact. `--output verification.json` writes its report.
The input must be canonical JSON (`fusion.contracts.canonical`) with the SHA-256
in the adjacent `evidence.sha256`. Referenced paths are relative to this file;
absolute paths, escapes, duplicate identities and unbound files are refused.
The verifier reads files, parses reports and hashes bytes. It does not instantiate
Omega, execute a subprocess, observe a chain node or contact a model/runtime.

The input profile is `operator-pilot-evidence/1`, with these required fields and the optional `test_sources` mapping:

- `release_status`: `PASS` or `PARTIAL`.
- `candidate`: `{source, source_manifest_sha256, images}`. `source` maps actual
  source paths to SHA-256. `images` maps distribution image kinds to
  `sha256:<manifest>`. These must match the verified distribution's actual image
  and tested-source records. An independent Go source/image binding remains
  separate inside that distribution. Optional `candidate.image_roles` maps an
  actual service name to `{kind,plan}`, where `plan` is a registered canonical
  `omega-single-node-placement/1` artifact. The verifier matches the plan's
  source and image export to this candidate, then the role's exact values/graph
  image to the distribution kind. This permits original primary service-role
  image maps without rewriting them. Missing roles, stale plans and wrong
  digests fail. An explicitly frozen inactive `f1r3node` image may be bound from
  its selected component values; this does not claim activation or readiness.
  Independent Go bindings additionally require the verified reference image,
  separate source manifest and reference-artifact digest. They cannot inherit
  the Python source identity or pass an unverifiable partial distribution.
- `distribution`: the registered artifact ID for the existing distribution
  manifest, or `null` for an explicit partial evidence review. The existing
  `reference_artifacts.verify` validates the actual image archives, source
  packages, wheel contents, chart and values. `PASS` requires this check.
- `artifacts`: nonempty rows `{id,path,sha256,bytes,visibility}`. Visibility is
  `approved-public` or `unavailable-private`. A private record must name an
  absent file, `sha256:null` and `bytes:null`, and never supplies a passing gate.
  No identifying private digest or content-size metadata is published. Credentials, keys, journals and
  private bytes must not be published merely to satisfy this verifier.
- Optional `test_sources`: a map from logical `tests/test_*.py` source paths to
  registered approved-public source artifact IDs. The verifier checks the actual
  source bytes and class definitions. Only each named file's exact package name
  and discovery name may share a canonical case identity. For example,
  `tests.test_x.C.test_a` and `test_x.C.test_a` become
  `tests/test_x.py::C.test_a` only with that source binding. Unbound identities
  stay distinct; ambiguous aliases or missing classes are refused. Raw log IDs,
  source hashes and all invocation counts remain visible in the verification.
- `runs`: nonempty rows in the format below.
- `scenario_plan`: the artifact ID of the frozen independent assertion plan.
- `gates`: keyed records including all acceptance stories `A` through `H`.
- `packages`: exactly `V01` through `V40`.
- `counts`: independently recomputed integers listed below.
- `historical`: rows `{artifact,index,pointer}`. The historical artifact's exact
  SHA must equal the value at that JSON pointer in a separately included old
  index. Self-links, cycles and changed identities are rejected. This is hash
  continuity against the supplied prior index, not a signature or trust oracle.
- `authorization`: exactly `{additional_live_generations:0,live_reservations:0,
  live_captures:0,generative_runtime_contact:false}`.
- `limitations`: nonempty explicit strings describing remaining coverage limits.

Each run has exactly these fields:

```json
{
  "id":"unique-run-id",
  "kind":"native-session",
  "phase":"candidate",
  "status":"PASS",
  "classification":"REAL_NATIVE_RECORDED_MODEL",
  "primary":"primary-report-artifact-id",
  "native":"native-runner-report-artifact-id",
  "internal":[],
  "chain":null,
  "source_manifest_sha256":"<actual candidate source manifest hash>",
  "images":{"caller":"sha256:<actual image manifest>"},
  "image_binding":{"artifact":"primary-report-artifact-id","pointer":"/selected_images"},
  "components":{
    "storage":{"kind":"REAL","evidence":[{"artifact":"primary-report-artifact-id","pointer":"/actual_storage_receipt"}]},
    "model":{"kind":"FIXTURE","evidence":[{"artifact":"primary-report-artifact-id","pointer":"/model"}]}
  },
  "depends_on":[],
  "reason":""
}
```

`kind` is `unittest-verbose`, `go-test-json`, `native-session`, `primary-json` or
`chain-trace`. `phase` is `candidate` or `historical`; historical runs remain
visible but cannot supply a candidate passing gate. Status is `PASS`, `FAIL`,
`PARTIAL`, `BLOCKED`, `NOT_RUN` or `UNAVAILABLE_PRIVATE`. An unexecuted run has
null `primary`/`native`, empty images/components/internal, null image binding and
an explicit reason. It cannot masquerade as a failed test or passing gate.

Classification is `FIXTURE`, `STATIC`, `REAL_PROVIDER`,
`REAL_NATIVE_RECORDED_MODEL` or `REAL_CHAIN`. The latter three require actual
primary-report image bindings and nonempty real-component observations. A real
claim pointing only to fixture/unrun labels is refused. Components select
`REAL`, `FIXTURE`, `UNRUN` or `UNAVAILABLE`; evidence references must point into
that run's actual primary/native report. The verifier does not infer that a
recorded model is real generation, or that every provider in a mixed test is real.
Image bindings accept a kind-to-digest map or existing exported image rows with
`kind`/`role` and `manifest_digest`/`manifest`/`image`.
The existing restore observer's literal terminal `FAILED` is recognized as
the verifier's `FAIL`; its raw spelling and report bytes remain unchanged.
No unfinished or unknown status is inferred to pass.

A native run must carry the exact native report digest in its primary report's
`native_report_sha256`. Its native report must have the existing
`RECORDED_MODEL_REAL_NATIVE_TOOLS` classification and nonempty `inputs`, each
with original role/session/occurrence, command, acceptance and actual observed
payload/result. Admission/observation identities and original deadlines must
match. Complete inputs require captured native projections and occurrence IDs.
Repeated observations across runs count an occurrence once and cannot change
an existing capture or accepted deadline. Duplicate entries within one input
list are rejected. Retained unsuccessful inputs are kept distinct from captures.

`internal` can contain `{artifact,pointer}` references to actual session
observations with `principal`, `session` and `inputs`. Only `delegated-task` and
`delegated-result` inputs are counted there, by preserved identity. The output
lists which runs supplied these observations. The observed internal count is
not an inference about unexported session pages.

For unit tests, retain `python -m unittest -v ...` output as primary bytes.
The historical `authored_test_methods` field counts distinct executed,
source-qualified test **case identities**. An inherited method exercised by a
different test class is another case, but it is not another authored function.
Keep this field and historical results unchanged. The supplementary
`source-resolved-authored-test-definitions/1` audit resolves each Python case to
its actual defining class and function using the exact test-time source index,
imports and class inheritance. It records unresolved definitions explicitly and
counts named definitions separately from case identities, invocations and runs.
The independent Go audit binds named test functions to its own compiled source
archive. Later focused runs retain their own source versions; repeated methods
and changed versions of an existing named function do not become newly authored
methods. Source maps and literal primary logs make the audit reproducible from
the evidence packet without importing or executing tests.

Warnings or captured subprocess output may separate one test header from its
standalone outcome. The verifier pairs that one pending header with the exact
outcome, with bounded diagnostic lines/bytes; orphan, duplicate, interleaved or
missing outcomes and mismatched totals refuse. Raw diagnostics and method
identities remain unchanged. For
Go retain `go test -json ./... -count=1`. The verifier parses actual test outcomes,
not a hand-entered method count. Authored method unions count top-level executed
identities (including failures), excluding skipped helpers. Method invocations,
skips, runs and Go subscenarios are reported separately. A failing primary log
cannot become `PASS` through its wrapper. Use `STATIC` or `FIXTURE` for these
logs; passing fixture-port Go tests do not establish deployed provider coverage.
Candidate `go-test-json` runs may retain the independent Go kit's actual source
manifest only when it exactly matches the separately verified `inspect-go`
distribution artifact and its `independent-go` source kind. Missing/unverified
artifacts and other source hashes refuse. All other candidate runs require the
main source identity. `independent_test_sources` reports this binding separately;
the Go source is never relabelled as the Python image source.

A `chain-trace` primary is exactly the already approved exported
`{reg,saved_intent,final_observation}` trace. Its `chain` is
`{artifact:<actual generated payload file ID>,inspection_result:<actual result
bytes file ID>,readback:<optional independent readback report ID or null>}`.
Optional `chain.execution_report` names the unchanged actual execution report.
Its `registration`, `saved_intent` and `final_observation` must exactly equal the
three fields in the approved trace. Its terminal status must agree with the run;
a later failure cannot be hidden by an otherwise valid finalized trace. This
exactly linked report may supply the run's actual image map, component receipts
and scenario assertions. The immutable trace itself gains no metadata fields.
If the execution report declares a source manifest, it must match the run; image
bindings still require the candidate's exact exported placement/artifact source.
The independently scheduled readback report remains a separate field.

The verifier checks the native artifact codec, artifact hash, exact inspect
result bytes, approved commitment digest, signed-intent/deploy identity and
reported effect linkage. An exported failed readback remains `PARTIAL`. No
current finality/readback claim is added by this offline check. Other kinds use
`chain:null`.

The frozen scenario plan is `{profile:"operator-pilot-scenarios/1",scenarios:[...]}`.
Each scenario is `{id,run,assertions:[...]}`. Each assertion is exactly
`{artifact,pointer,operator,expected}`, with operator `equals` (type-sensitive) or
`contains` (nonempty string). Assertions must read the run's actual primary or
native report and include a substantive value beyond a `status`/`passed` label.
They cannot read their own expected-answer plan. Wrong but permitted output
therefore fails the relevant assertion. A failed positive scenario can remain in
a `PARTIAL` packet; correct-refusal safety and task completion should use
separate explicit assertions/gates.

Each gate is `{status,runs,scenarios,reason}`. A passing gate needs nonempty,
unique references to passing candidate runs and passing frozen assertions from
those runs. Each package is `{status,gates,reason}`. A passing package needs
nonempty passing gates. `PASS` release requires every gate/package passing,
verified distribution and no unsuccessful candidate run or unavailable private
prerequisite. Historical unsuccessful runs stay reported without being erased.

The exact `counts` fields are `authored_test_methods`, `test_method_invocations`,
`test_runs`, `test_subscenarios`, `test_skipped_invocations`, `workflow_scenarios`,
`native_operator_inputs`, `native_accepted_inputs`,
`observed_internal_native_inputs`, `native_captures`, and
`additional_live_generations`. All are nonnegative integers (booleans are not
integers here), and each must equal the recomputed candidate-only value.

The result is `VERIFIED_PASS` or `VERIFIED_PARTIAL`, with concise exceptions,
unsuccessful runs, withheld evidence and the exact count/method union. It cannot
prove malicious-host execution authenticity, unavailable evidence, the timing
of a supplied freeze, present chain finality or model competence. Missing files,
malformed counters, false status claims or changed source/image bindings cause
verification failure. No historical report is rewritten.
