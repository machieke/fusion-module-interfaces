# H20 clean selection with unchanged H19 native supervision

[h20-detached-command.py](h20-detached-command.py) differs from the qualified H19 v2 wrapper only in the clean source pin and clean packet-relative path. Its native source pin/path, process control, pidfd checks, deadlines and cleanup barrier are byte-identical. [review.json](review.json) distinguishes this static seam qualification from the earlier process fixtures.

Selected wrapper SHA-256: `c1819954bec4f1dc6c6cd7c1eca4a7a52ed93e283b785d11c8227e818b2ffdcd`.

Use [the H20 clean commands](../h20-clean-install-source/commands.md) after root binds the actual final packet and separate private clean plan. No execution is authorized by this document. After that clean PASS and the separately bound native root release, the native command remains an invocation of the original H19 recipe from the same packet:

```bash
h20_python=/data/fusion-operator-pilot-release/operator25/bin/python
h20_packet=/data/fusion-operator-pilot-release/distribution20
h20_private=/data/fusion-operator-pilot-release/evidence-assembly
"$h20_python" -B -I \
  "$h20_packet/artifacts/operator-pilot/h20-supervision-source/h20-detached-command.py" native \
  "$h20_packet/artifacts/operator-pilot/h19-rehearsal-source/h19-native.py" \
  "$h20_private/h20-bound01/plan.PRIVATE.json" \
  /data/fusion-operator-pilot-release/qualification-private/H20-native-launch01
```

Native code stays SHA-256 `30165c0fe79f7a5778ef2973d4d91cf8536ae6783f68e74191f693b62665bb28`. Root's successor binder must select the actual H20 clean source/plan while retaining that native source and all runtime, SDK, authority and scope constraints. Binding creates no occurrence or deadline. H19's failed clean run created no native session; no prior accepted native work is being renewed or replayed here.

Use fresh exclusive records. Clean/native original bounds remain1800/4200 seconds, with separate process envelopes1980/4360. The same no-automatic-retry, exact-PID identity checks and complete-tree termination barrier apply. A missing acknowledgment is uncertain; do not relaunch. Neither successful process termination nor successful cleanup is a successful workflow. Actual H20 clean/native launch is **NOT_RUN** in this qualification packet.
