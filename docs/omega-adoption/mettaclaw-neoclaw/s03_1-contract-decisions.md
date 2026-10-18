# S03.1 query-time Embedding decisions

Baseline: `2bddbc3467f98ed258741a21a329230a0cd21dd9`. All 25 S03 implementation
hashes, 32 non-evidence hashes and 40 historical evidence hashes match. The additive
`evidence/s03_1/baseline-source.json` preserves the original working-tree run identity.
Historical passes and new executions have separate logs and counts.

The X02 extension is `Embedding` (`embedding`, version `1.0.0`), operation `encode`,
profile `neoclaw-e5-query-text/1`. It is outside the historical fifteen-family
denominator. It adopts only the query-time Local `lib_llm_ext.useLocalEmbedding`
dependency. Search, AtomStorage, local metadata and promotion keep their S03 contracts.

Source inspection corrects one premise in the handoff: S03's `MemoryRead.authorize`
already sends the raw query to `/s03-read` for its synthetic-query allowlist. S03 was
therefore not a strictly vector-only network protocol. This increment additionally
discloses the exact transformed helper input to the independently selected encoder
owner. Existing Search authorization remains unchanged; the new disclosure requires
its own explicit operator consent and method permissions.

Native `embed` still executes native `string-safe` exactly once. The compatibility
hook receives its resulting Python string, not raw command source. One strict UTF-8
string of 0–2048 bytes is admitted by the port. Empty text, quotes, Unicode, tabs,
newlines and NUL are data; lone surrogates and oversized input are rejected. Native
command parsing has its own narrower admission. The operator explicitly approves
both each raw synthetic command and its exact transformed helper input. Neither
adapter nor provider trims, escapes, normalizes, adds prefixes or tokenizes text.
Both the existing raw-query bound and the new helper-input bound apply: native
`string-safe` expansion can put a raw S03 query outside this new bounded profile.
Such input fails before encoding; it is never truncated to obtain admission.
The original pinned E5 function performs its unchanged normalized encoding with
the model's 512-token limit/truncation. CPU float32, model/tokenizer/package pins and
the existing S03 vector compatibility identity remain unchanged.

The request binds authenticated principal, scope, occurrence, exact helper input and
UTF-8 hash, selected descriptor, preprocessing identity, model, original deadline and
size cap. The reply binds that intent and principal, dimension 1024, float32, unit-L2,
little-endian encoding and SHA-256 of exactly 4096 vector bytes. Validation rejects
malformed/nonfinite/nonunit/wrong-model output before Search. It does not renormalize.
Digest/descriptor checking is integrity and binding, not proof of remote computation.

Fresh `controlled-native-loop/4` journals add `app_query_vectors` to the existing
application owner. Accepted occurrence identity is unchanged. Input binding commits
before encode-call reservation, which commits before dispatch. The first fully
validated vector commits before Search. Captured vector replay is byte-identical;
independent executions are compared separately. Existing candidate/payload/native
result/handoff commits remain independent. No job, queue, outbox or migration is added.

Three application encode reservations and 32 encoder-port calls per occurrence are
durable and never refunded. Search/hydration retain their separate S03 limits. The
provider independently records at most one physical model-dispatch reservation for
each attempt number 1–3 under an immutable intent, with 128 lifetime occurrences.
Duplicate delivery of one attempt is refused, not re-evaluated. A pre-capture crash
may lose work or cause another bounded evaluation. There is no exactly-once inference
or cross-occurrence result cache. Provider readiness is bounded separately; admitted
evaluation has a five-second process deadline capped by the original application
deadline. One supervised resident worker and the existing sequential HTTPS host
bound concurrency; no scheduler is introduced.

Current `embedding.encode` authority controls new evaluations. Separate
`embedding.disclose` authority controls response release and captured-state replay.
Exact transformed-text consent is checked independently of vector Search permission.
Credential rotation may preserve a principal; substituting another authorized
principal cannot release the accepted occurrence. Captured state is not a capability.
Expired work cannot start a new encode or retrieval; current authorized disclosure
of captured data may finish after expiry. Neither deadlines nor reservations reset.

Placement is selected independently for encoder and retrieval. The local binding
uses a supervised local resident native encoder; HTTPS uses the existing verified
loopback transport/host with a closed `/s03-encode` route. There are no automatic
retries or fallbacks. The slim caller recipe verifies only its own SDK/source files;
the provider verifies its own original source, installed packages and model assets.
Real Chroma remains a caller dependency for unchanged sealed local metadata.

Only generated approved text crosses HTTPS. Filesystem namespaces hide caller state
from the encoder and encoder assets/SDK from the network caller. This is same-host
isolation, not an egress firewall, private-model hosting or multi-host deployment.
Typed failures remain invalid, unauthorized, incompatible, unavailable, overloaded
or deadline failures; none become an empty-memory success.
