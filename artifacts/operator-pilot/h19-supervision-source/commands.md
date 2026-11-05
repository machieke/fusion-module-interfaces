# Ready artifact-derived H supervision commands

These are the recommended v2 launch commands. The older `h19-detached-launch-procedure.md` is retained historical compiled-only evidence; its original executable body is not the selected launcher. The v2 wrapper and inner H entrypoints below all come from the same reviewed final packet. No code bytes changed for publication.

Actual H remains **NOT_RUN**. Before either command, verify the final packet digest and implementation commit, the selected Python/SDK, and the wrapper source SHA-256 `34400330527071f74473d90a877f2fb6c835281a6e212babb3714a6b0f165e19`. Use the existing separately reviewed enabled clean plan. Native H additionally requires the completed clean PASS and the existing binder's separate root heavy-slot release. A hash, enabled flag or passing process test is not that release. Do not invent a final packet digest or activate a disabled plan.

The paths below are the selected qualification layout. Plan/release contents and launch records remain private; no credential or private owner record is included in this bundle. Each launch-record directory must be fresh and absent.

```bash
h19_python=/data/fusion-operator-pilot-release/operator25/bin/python
h19_packet=/data/fusion-operator-pilot-release/distribution19
h19_private=/data/fusion-operator-pilot-release/evidence-assembly
"$h19_python" -B -I \
  "$h19_packet/artifacts/operator-pilot/h19-supervision-source/h19-detached-command-v2.py" clean \
  "$h19_packet/artifacts/operator-pilot/h19-clean-install-source/h19-offline.py" \
  "$h19_private/h19-clean-plan.ENABLED.PRIVATE.json" \
  /data/fusion-operator-pilot-release/qualification-private/H19-clean-launch01
```

This returns a detached acknowledgment, not clean-install success. Observe its exact terminal record and require a passed complete-tree process barrier and exit code zero, then independently validate the unchanged clean primary report and launcher. A missing acknowledgment is an uncertain launch, never permission to repeat it.

After that completed clean PASS, bind the native plan using the separately approved existing binder and root release. That binding must retain the final packet digest, implementation, exact clean report, node selection, source/assets and unchanged limits. Only then launch native H once:

```bash
"$h19_python" -B -I \
  "$h19_packet/artifacts/operator-pilot/h19-supervision-source/h19-detached-command-v2.py" native \
  "$h19_packet/artifacts/operator-pilot/h19-rehearsal-source/h19-native.py" \
  "$h19_private/h19-bound01/plan.PRIVATE.json" \
  /data/fusion-operator-pilot-release/qualification-private/H19-native-launch01
```

Native's original bound remains 4200 seconds, with 300 reserved for its cleanup; accepted input deadlines and budgets remain unchanged. Its separate maximum process envelope is 4360 seconds. Clean installation retains the 1800-second inner bound, 1830-second original outer wait and at most 1980 seconds supervised process envelope. These are separate launches, not a blocking combined shell lifetime or renewed workflow authority.

The wrapper records its own actual source digest, PID/start ticks, fixed process windows and terminal barrier. It launches exactly one original entrypoint, does not perform owner effects or external cleanup, and has no automatic retry. No shell EXIT trap may stop owners while a surviving producer is unproven. Any separate safety cleanup requires the saved complete-tree barrier first and must preserve original failures and uncertain effects. The selected host x86_64/libc and kernel pidfd checks fail closed, without PID-only fallback.

Publication adds no execution claim: process tests used explicitly labeled fixtures and clocks. Actual H terminal evidence must be a detached reviewed supplement referencing the already frozen final packet digest, not inserted into that same hashed packet. Neither a detached acknowledgment nor a process exit is an owner receipt or native workflow PASS.
