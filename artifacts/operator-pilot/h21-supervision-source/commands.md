# H21 detached qualification supervision

This successor changes only the H20 supervisor's native source pin and native packet-relative path. The H20 clean source, Linux subreaper/pidfd mechanism, start-tick checks, finite bounds, duplicate-launch refusal and child termination barrier remain byte-identical. The H19/H20 supervision sources and failed runs are preserved. [review.json](review.json) records this static selection check; no H21 clean or native run is claimed here.

Wrapper SHA-256: `67c3a9bd960be1f9aab17ac3c2dbac4b36cc9dd050b8bec4140f0103a0b266d9`. Native SHA-256: `352658b175b455ec866343ee6abd7456e80c171e7af1767e1c98ab1e71bc76bf`.

Use the unchanged [H20 clean recipe](../h20-clean-install-source/commands.md) with a separately enabled detached plan bound to the actual final packet21 digest and fresh `final-H21-clean01` output. Do not modify its public disabled-plan bytes. Root supplies those missing final bindings and a separate heavy-slot release. These commands do not authorize their own execution:

```bash
h21_python=/data/fusion-operator-pilot-release/operator25/bin/python
h21_packet=/data/fusion-operator-pilot-release/distribution21
h21_private=/data/fusion-operator-pilot-release/evidence-assembly
"$h21_python" -B -I \
  "$h21_packet/artifacts/operator-pilot/h21-supervision-source/h21-detached-command.py" clean \
  "$h21_packet/artifacts/operator-pilot/h20-clean-install-source/h20-offline.py" \
  "$h21_private/h21-clean-plan.ENABLED.PRIVATE.json" \
  /data/fusion-operator-pilot-release/qualification-private/H21-clean-launch01
```

After exact clean PASS and a separate root release covering adopter21 and adopter21-go, invoke native once:

```bash
"$h21_python" -B -I \
  "$h21_packet/artifacts/operator-pilot/h21-supervision-source/h21-detached-command.py" native \
  "$h21_packet/artifacts/operator-pilot/h21-rehearsal-source/h19-native.py" \
  "$h21_private/h21-bound01/plan.PRIVATE.json" \
  /data/fusion-operator-pilot-release/qualification-private/H21-native-launch01
```

A detached acknowledgment is not completion. Observe the recorded terminal status, exact source/plan, child-reap barrier and independent namespace cleanup. Missing acknowledgment is uncertain and forbids automatic relaunch. The clean/native original bounds stay 1800/4200 seconds; process envelopes remain1980/4360. The native window includes its300-second cleanup reserve and the new30-second maximum disconnected tool preflight. No live generation or runtime implementation change is introduced.
