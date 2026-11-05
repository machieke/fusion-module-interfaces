# Disabled clean artifact installation prerequisite

These are the actual reviewed standalone bytes for the clean-install prerequisite of the separate H native rehearsal. This entrypoint installs only the final packet's client, provider and operator wheels into three new environments, checks installed source files and runs the existing artifact verifier. It performs no cluster calls, native allocations or model/runtime contact. Its disconnected network namespace contains no author checkout, kubeconfig, Docker socket, private user home or generative assets.

The shipped plan is disabled. After the final distribution is assembled and the operator approves this bounded preparation, copy `plan.DISABLED.json` into a private detached plan. Set `distribution` to the final packet directory and `distribution_sha256` to its reviewed external digest. Resolve `output` to a fresh unused private directory. Preserve the SDK25/runtime14 selection, exact script/tool hashes, `max_seconds: 1800`, Python prerequisite and zero-generation field. Set `enabled: true` only in this separately recorded execution copy; preserve the shipped disabled plan.

Run once from the final packet, using the pinned bootstrap interpreter. `-B` prevents bytecode cache writes beside packet sources; `-I` disables ambient Python path configuration:

```bash
h19_packet=/data/fusion-operator-pilot-release/distribution19
h19_clean_plan=/data/fusion-operator-pilot-release/evidence-assembly/h19-clean-plan.ENABLED.PRIVATE.json
h19_bootstrap_python=/data/fusion-operator-pilot-release/operator25/bin/python
"$h19_bootstrap_python" -B -I "$h19_packet/artifacts/operator-pilot/h19-clean-install-source/h19-offline.py" --plan "$h19_clean_plan" --execute
```

The local prerequisites are the plan's pinned Python prefix and `/usr/bin/bwrap`, plus ordinary read-only OS binaries/loader libraries. All Python dependencies come from the final packet wheelhouse with indexes disabled, retries zero and no network access. No broad `/etc` mount is used. The original plan's machine paths are qualification prerequisites, not credentials or a universal deployment-path promise.

The clean environments are created at `/work/client`, `/work/provider` and `/work/operator` inside the sandbox. Their interpreter paths intentionally rely on the corresponding `/python` and `/work` mounts; do not try to turn them into a host venv or silently recreate them elsewhere. The native H launcher reuses this exact installed tree with those mounts.

Retain `clean-install-report.json`, `launcher.json`, each command's stdout/stderr, the exact executed plan and all hashes privately. A terminal PASS proves this offline installation and its unchanged artifact verifier only. `new_native_allocations=0` and `cluster_operations=0` remain true. It does not prove the browser/native/provider rehearsal, which has its own enabled plan, heavy-slot release, 4200-second bound and operational evidence. A failed clean-install primary must remain distinct from any later attempt; output directories are exclusive.

The supplementary source directory is separate from the frozen 11-file native bundle. No native recipe, SDK or runtime bytes were changed to add this prerequisite.
