# Candidate artifact analysis

The current candidate is runtime14, recorded in
`artifact-scan-candidate14.json`. All four immutable role images were scanned
with the same pinned Trivy 0.76.1 binary and 2026-11-04 database. Their findings
are 223 for base, 227 for caller, 234 for embedding and 224 for chain; these
overlap and resolve to 235 distinct package/version/path/advisory keys. The
respective critical counts are 2, 4, 5 and 2. The independent Go04 image remains
the exact separately scanned artifact. These results are not a security pass.

The earlier dev09 embedding scan exhausted the root filesystem while exporting
the image into `/tmp`; its failure is retained. Scanning the same immutable
image with a task-owned temporary directory on `/data` succeeded. No retained
images or unrelated state were deleted to make the scan pass. SDK20's eight
wheels were separately extracted and scanned: all eight packages were detected,
with zero database matches. SDK21 adds only the closed-session
Attention qualification helper repair; its own eight-wheel scan also detected
eight packages with zero matches (`scan-wheels21.json`). SDK22 adds only the
fault-helper configuration retirement correction; its separate scan again
detected eight packages with zero matches (`scan-wheels22.json`). SDK23 changes
only the endurance readiness timing helper; its own eight-wheel scan detected
eight packages and zero matches (`scan-wheels23.json`). That report keeps its
original SDK23 build and wheel identities. SDK24 makes the later endurance
window select the existing bounded NAL operation explicitly, and SDK25 adds
the opt-in independent-reader health composition. The current SDK25 wheel set
was separately extracted and scanned: all eight packages were detected with
zero database matches ([scan-wheels25.json](../../evidence/integrated-service/pilot/scan-wheels25.json)).
Its operator wheel is `93350732cbc3294f16e2f8c9d787836dd4503c1ddad5a4cb0448493cde6fc4e9`,
bound by build manifest `f902477c74ed25c5753d5903fa3c9071c6a6820172c3cc6cc8bb8ef2fd27ee90`.
The runtime14 images and their 235 distinct findings are unchanged. Chart16 was
also scanned with the same embedded checks and has twelve LOW findings under
the default values. Neither result establishes absence of vulnerabilities.
Current inventories and unresolved dispositions are
`installed-dependency-license14.json`, `dependency-dispositions14.json` and
`scan-wheels25.json`. Earlier scans retain their original artifact identities.
Runtime14 retains the corrected10 dependency layers.
Runtime11 added the task-only reply-fault seam; runtime12/13 changed only the
opt-in activation implementation. Runtime14 adds explicit synthetic Workspace root re-attestation and feed-profile
validation; SDK20 includes the same source and exact checkpoint selection helper. Historical image, SDK, scan and test
identities remain separate.

The dev09 compatibility review found an actual remediation defect. HTTPX2
2.12.0's wheel requires HTTPcore2 2.12.0 and IDNA at least 3.18, while the
earlier remediation selected 2.10.0 and 3.15. Successful native memory runs did
not establish dependency closure. Exact OCI metadata confirmed both violations
in each SDK environment, and the historical lock and failed audit remain
preserved. Dev10 changes only these two leaf packages, using pinned
[HTTPcore2 metadata](https://pypi.org/pypi/httpcore2/2.12.0/json) and
[IDNA metadata](https://pypi.org/pypi/idna/3.18/json). Builds now run offline
`pip check` before publishing their runtime inventory. The independent audit
checks 224 effective metadata records and 335 active default requirements:
zero missing or incompatible dependencies in the selected environments.
Optional extras and semantic API compatibility are separate claims.

The package-file comparison retains 6,413 caller and 26,870 embedding files
unchanged; each SDK has only 35 changed paths belonging to the two repaired
packages. E5 model specifications/assets and mathematical packages are
unchanged. Actual dev10 native qualification is required because E5's import
path includes HTTPX2 through Hugging Face Hub. The complete dev09 browser story
remains labelled with its original artifacts, rather than being relabelled a
dev10 execution. See the separate `dependency-closure09.json` failure and
`dependency-closure10.json` pass under `evidence/operator-pilot/development/`.

The paragraphs below retain the development comparison and its limitations.
Development findings are not relabelled as final workflow qualification.

The dev04 image set was actually scanned with Trivy 0.76.1 and its pinned
2026-11-04 vulnerability database. The independent Go image has its own source,
binary, OCI and scan identities. No container entrypoint, native tool or model
was started by scanning. No source, image, SBOM or prompt was uploaded to a
scanning service. Scanner and database bytes are recorded in
`evidence/integrated-service/pilot/scanner-{source,database}.json`.

`artifact-scan-development04.json` binds five actual image reports. Per-image
finding counts overlap because dependencies are shared; do not add them as
unique vulnerabilities. The dev04 caller reports 227 findings versus the
historical Q caller's 261 under this database. This is a scanner observation,
not a score of application safety. The dev04 embedding image still reports
five critical findings; no production-security pass is claimed.

The compatible changes are explicitly pinned in
`integration/neoclaw/pilot-leaf-remediation.json` and
`evidence/integrated-service/pilot/debian-remediation.json`. The original native
E5 functions/model, Chroma numerical behavior, DeTTa and NAL/PLN source profiles
are preserved. The actual development native remember/query/NAL smoke passed
on the remediated dependencies; final candidate workflow qualification remains
separately reported. No numerical dependency was silently upgraded to improve
a vulnerability count.

`dependency-dispositions04.json` retains every unique reported package/version
finding and its affected roles. In particular, newer top-level certifi and
urllib3 coexist with older copies vendored by pip. An offline read of the exact
image's `pip/_vendor/vendor.txt` confirmed these versions. The SBOM-derived
findings were therefore retained, not suppressed as stale metadata. No package
installation occurs in the service workflow, but that is not a proof the
vendored code is unexploitable.

The pinned Chroma and sentence-transformers findings remain explicit
compatibility exceptions. Runtime assets are locally hash-checked and query
inputs use bounded typed ports; those restrictions do not substitute for a
security review or qualify an untested numerical-library upgrade. OS findings
without a fix in the selected database stay unresolved. Any other fix not
applied has an explicit unresolved disposition rather than an implicit waiver.

The exact eight operator/client/provider wheels were extracted and scanned as
a root filesystem: all eight packages were detected, with no database matches.
The first filesystem-mode attempt detected no Python packages and is retained
as inadequate coverage. It is not a zero-vulnerability pass. The chart was
scanned with embedded checks bound to the scanner binary; no downloaded check
bundle was available. Findings include UID/GID 1000, the template's unspecified
namespace and local image registry names. Actual placement separately binds
fresh non-default namespaces, non-root identities and immutable local images
with `imagePullPolicy: Never`. Scanner findings are not rewritten using those
observations.

The offline OCI inventory reads final installed package metadata and licence
files across all layers and records missing declarations as `NOASSERTION`.
It preserves notices; it does not grant redistribution rights. Native MeTTa,
DeTTa, model blobs and application-specific semantics have no comprehensive
advisory coverage merely because OS/Python/Go packages were scanned. Reachability,
malicious-provider behavior and new undisclosed vulnerabilities remain outside
this scanner result. Hosted CI is `NOT_OBSERVED`; local executed lanes have
their own complete primary logs.
