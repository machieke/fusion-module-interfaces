# Immutable historical endpoint inputs

The two wheels in `0.1.0/` are the exact installable artifacts executed in
[`../qualification.json`](../qualification.json), copied from the original
ignored build directory. They contain only the explicit public source lists
and distribution metadata recorded in that report: no configuration, private
state, TLS material, credentials or native assets.

| Artifact | SHA-256 |
| --- | --- |
| fusion_module_client-0.1.0-py3-none-any.whl | `3db7d4c879634c92c0cdf5bef22fe9fab6f47c4bc0f0e8033e961be580b57938` |
| fusion_file_feed_example-0.1.0-py3-none-any.whl | `53290c6f5dc98f7cd468c1974239897c5ba3e35e2986f44de75f27d2e061bb3c` |

These are frozen compatibility test inputs, not independently maintained SDK
source copies. Tests verify the report hashes **before installation**, then
execute the actual installed old client and old server outside the checkout.
Do not rebuild them from newer source or edit the historical report. The new
kit continues to copy current authoritative source byte for byte.

The archive demonstrates the supported package-level additive change while
keeping interface `1.1.0` and `immutable-commit-feed/1` unchanged. It does not
stand in for tests against every earlier Fusion/Hive runtime profile.

## Preserved Phase 2 package inputs

The `0.2.0/` wheels were copied byte for byte from the completed Phase 2
artifact wheelhouse, before building 0.3.0. The compatibility tests retain
the historical test names and execute 0.1.0, 0.2.0 and 0.3.0 as distinct
installed endpoints. They do not relabel a new build as the old provider.

- `fusion_file_feed_example-0.2.0-py3-none-any.whl`: `92361d6be2a18868c711c34ed621df629e905d105797664cc382256b373237a8`
- `fusion_module_client-0.2.0-py3-none-any.whl`: `b7ff0eb206dd554922b70e9e8d9087f717d851b16c7b59b5592a06906651ed50`
