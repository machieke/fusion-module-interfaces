# Independent chain reader readiness

The opt-in `--consumer-path-health` option on `fusion-pilot qualify-recipe-chain`
checks the existing Storage HTTPS health endpoint from the independently
scheduled reader pod before invoking the unchanged original reader once.
It is an operator observation, not a module profile or chain operation.

```sh
OBSERVER=$("$OPERATOR/bin/python" -I -c 'import examples.preview_chain_observer as m; print(m.__file__)')
"$OPERATOR/bin/fusion-pilot" qualify-recipe-chain \
  --kubeconfig "$KUBECONFIG" --context default --namespace "$NAMESPACE" \
  --values "$VALUES" --chart "$CHART" --output "$NEW_OUTPUT" \
  --observer "$OBSERVER" \
  --representation reference-document --consumer-path-health
```

This command runs the existing complete recipe and its separately approved
chain path; it is not permission to repeat an already accepted workflow.
Use the programme's frozen inputs, original limits and approval requirements.
The option is off by default, preserving historical reader composition.
`OPERATOR` is the installed operator environment from the selected distribution;
the original reader is shipped in that wheel, rather than as a loose example
at the distribution root.

The health gate validates the original reader's scope, endpoint and read
configuration, uses the existing CA and Service hostname, and sends only
`GET /health/ready`. It requires HTTP 200 with the exact Storage role and
`ready: true`. There are at most eight health attempts in thirty seconds,
each with a two-second socket bound, with every outcome retained. A malformed
health response stops immediately. Health requests carry no work, mutation
identity, authorization token, generation reservation or signing authority.

After readiness, the original reader performs its two AtomStorage reads and
one bounded node-effect observation. There is no artifact retry, response
repair, signing or submission. The composed observer has a separate bounded
180-second observation allowance; it does not change any accepted effect
deadline. Failure to become ready invokes the original reader zero times.
Original source hashes and health outcomes accompany the reader result.

G18's original [failed qualification](../../evidence/operator-pilot/recipe18.json)
is retained. A [separate current-authorized read](../../evidence/operator-pilot/recipe18-readback.json)
observed two connection refusals before the third health attempt succeeded;
then the unchanged reader verified the same stored artifact, result and
finalized chain effect. The Service port, named target port, container port
and ready EndpointSlice had matched before launching that reader. This
demonstrates delayed consumer-path readiness; it does not identify whether
CNI policy or service-proxy convergence caused the delay.

The first successful supplementary run used a task-local wrapper. A separate
[installed SDK25 qualification](../../evidence/operator-pilot/recipe18-readback-installed25.json)
then called the actual installed composition once. It passed in 17.923 seconds:
one health connection refusal, one successful health check, and one original
reader verifying the same artifact, result and finalized effect. Both owners
were stopped afterward, with all fourteen PVCs retained. The original failed
qualification and task-local supplement remain unchanged. None of these
observations grants new chain-effect authority or renews the expired original
signing deadline.
