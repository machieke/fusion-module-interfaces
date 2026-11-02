# Independent AtomStorage/feed provider example

This example hosts the existing `fusion.adapters.fixture_feed.FileFeedFixture`
behind authenticated HTTPS. The class is included byte-exact from the repository
in its own wheel. It uses atomic file replacement, fsync and a local file lock;
it owns only its own state directory. It is explicitly a **contract-test
provider**, without DeTTa, erasure coding, distributed storage or HA guarantees.

Build the [client and provider wheels](../../sdk/README.md), install both in a
separate Python 3.12 venv, and run from a directory outside the developer tree:

```sh
/tmp/fusion-client/bin/python -m pip install --no-index --no-deps /absolute/path/fusion_file_feed_example-0.2.0-py3-none-any.whl
/tmp/fusion-client/bin/python -I -m phase2_provider.server --config /absolute/private/provider.json --bind 127.0.0.1 --port 8443
```

Supply an existing trusted certificate/key with an appropriate SAN. The server
never creates a public certificate, disables verification or starts a plaintext
listener. The bearer credential and TLS private key belong in private files or
existing Secret mounts. No credentials or keys belong in an image, wheel,
source manifest or public evidence. One process owns the configured state root;
a second process fails to acquire its exclusive server lock. SIGTERM drains
HTTP handlers before releasing the process lock. Health reads execute no owner
operation and consume no work budget.

The private provider configuration has this shape; placeholders are not usable
credentials:

```json
{
  "composition": "typed-atom-feed-https/1",
  "privacy": "generated-shareable",
  "synthetic_scopes": ["generated-example"],
  "root": "/owned-state/example",
  "tls_certificate": "/existing-tls/tls.crt",
  "tls_key": "/existing-tls/tls.key",
  "principals": {
    "agent-a": {
      "credential": "<existing generated credential>",
      "scopes": {
        "generated-example": ["atom.storage.create", "atom.storage.get", "atom.storage.getMany", "atom.storage.availability", "atom.storage.head", "atom.storage.readCommits"]
      }
    }
  }
}
```

Policy is reloaded at authorization boundaries, including before returning a
saved result. Scope membership is explicit. An ID, client-supplied principal or
digest is not authority. Server-side configuration fixes the provider's state
directory; requests cannot supply paths, SQL, imports, function names or MeTTa.
The descriptor is available through `phase2_provider.server.descriptor()`;
`--ready-file` optionally writes only the bound port, public descriptor and
fixture classification to an operator-owned path.

`phase2_provider.caller.save_and_consume` demonstrates application code that
accepts an injected storage port. The body is identical with a direct local
provider or `AtomFeedClient`. It is an adapted caller example, **not evidence of
an actual native Omega consumer**.

The conformance CLI accepts a private client config containing `endpoint`
(`host`, `port`, `ca_file`), `credential`, `principal`, `scope`, the exact public
`descriptor`, and an original absolute `deadline_ms`:

```sh
/tmp/fusion-client/bin/python -I -m phase2_provider.conformance --client-config /absolute/private/client.json
```

It uses only a new synthetic corpus and public ports. It never reads provider
files. Repository tests invoke this same runner against a genuinely separate
installed HTTPS server, then kill/restart the server and recover persisted
results. The source kit and fixture provider have no generative-model
dependencies or live-runtime activity.


Package 0.2.0 uses the same `1.1.0` storage descriptor and closed request/response
schema. Its declared client dependency is `>=0.1.0,<0.3.0`. The SDK qualification
installs historical 0.1.0 and current 0.2.0 client/provider packages into separate
venvs and executes all four pairings. See the [SDK compatibility scope](../../sdk/README.md#historicalcurrent-compatibility-evidence).
No higher storage version or transparent cross-provider migration is implied.
