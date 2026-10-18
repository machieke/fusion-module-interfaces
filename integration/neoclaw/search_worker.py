"""One supervised SDK invocation of the original helper. Operator inputs only."""
import importlib.util
import ctypes
import json
import os
from pathlib import Path
import sys
import signal
import time

from fusion.contracts import canonical
from fusion import neoclaw_search_contracts as s


def execute(config, runtime, arguments):
    from ddgs.ddgs import DDGS
    from ddgs.engines import ENGINES
    from ddgs.http_client import HttpClient
    from ddgs.exceptions import TimeoutException
    trace, failure = [], []
    audit = Path(config['audit'])

    def event(value):
        with audit.open('a') as stream:
            stream.write(json.dumps(dict(pid=os.getpid(), **value))+'\n')

    prior = sum(json.loads(x)['event'] == 'sdk-start' for x in audit.read_text().splitlines()) if audit.exists() else 0
    event(dict(event='sdk-start', boundary=config['boundary']))
    original_request = HttpClient.request

    def guarded(client, method, url, *args, **kwargs):
        if method != 'POST' or url != 'https://html.duckduckgo.com/html/' or trace:
            failure.append('upstream-denied'); raise RuntimeError('EGRESS_DENIED')
        trace.append(True)
        kwargs['follow_redirects'] = False
        event(dict(event='http-entry', method=method, destination=url))
        response = original_request(client, method, url, *args, **kwargs)
        event(dict(event='http-status', status=response.status_code))
        if response.status_code != 200:
            failure.append('upstream-rate-limited' if response.status_code == 429 else
                           'upstream-denied' if response.status_code in (401, 403) else 'upstream-unavailable')
            raise RuntimeError('UPSTREAM_STATUS')
        return response

    HttpClient.request = guarded
    DDGS.threads = 1

    class PinnedDDGS(DDGS):
        def __init__(self): super().__init__(timeout=8, verify=True, proxy=None)

        def _get_engines(self, category, backend='auto'):
            # Reject the SDK's automatic fallback path, including a missing engine.
            if category != 'text' or backend != 'duckduckgo' or 'duckduckgo' not in ENGINES['text']:
                failure.append('upstream-denied'); raise RuntimeError('BACKEND_DENIED')
            engines = super()._get_engines(category, backend)
            if len(engines) != 1 or engines[0].name != 'duckduckgo': raise RuntimeError('BACKEND_DENIED')
            return engines

        def text(self, query, max_results=10):
            if config['boundary'] == 'recorded-response':
                recording = json.loads(Path(config['recording']).read_text())
                entry = recording['observations'][min(prior, len(recording['observations'])-1)]
                if entry.get('sleep'): time.sleep(entry['sleep'])
                if 'error' in entry:
                    failure.append(entry['error']); raise RuntimeError('RECORDED_FAILURE')
                return entry['rows']
            return super().text(query, region='us-en', safesearch='moderate', max_results=max_results,
                                page=1, backend='duckduckgo')

    spec = importlib.util.spec_from_file_location('original_websearch', runtime['helper'])
    helper = importlib.util.module_from_spec(spec); spec.loader.exec_module(helper)
    helper.DDGS = PinnedDDGS  # Original search_ body is unchanged and source checked.
    try:
        rows = helper.search_(arguments['query'], arguments['max_results'])
        rows = s.items(rows, arguments['max_results'])
        observation = dict(identity=s.IDENTITY, items=rows, observed_ms=int(time.time()*1000),
            completeness='top-k-not-exhaustive', truncated=False, outcome='results' if rows else 'empty',
            sdk_invocations=1, http_entries=len(trace), boundary=config['boundary'])
        event(dict(event='sdk-return', outcome=observation['outcome']))
        return dict(ok=observation)
    except Exception as exc:
        reason = failure[0] if failure else ('upstream-timeout' if isinstance(exc, TimeoutException) else
            'upstream-empty-unconfirmed' if str(exc) == 'No results found.' else
            'invalid-output' if exc.__class__.__name__ in ('ContractError', 'UnicodeEncodeError', 'TypeError', 'AttributeError')
            else 'upstream-unavailable')
        event(dict(event='sdk-error', reason=reason))
        return dict(error=reason)


def main():
    message = json.loads(sys.stdin.buffer.read(16385))
    # Linux supported recipe: a killed execution worker must not leave this SDK
    # invocation running. Check the race where the parent died before prctl.
    if ctypes.CDLL(None).prctl(1, signal.SIGKILL) != 0: raise RuntimeError('PDEATHSIG')
    if os.getppid() != message['parent']: os._exit(2)
    signal.alarm(10)
    value = execute(message['config'], message['runtime'], s.arguments(message['arguments']))
    # Bound even malformed fixture/provider results before returning to the owner.
    raw = canonical(value)
    if len(raw) > s.MAX_BYTES: raw = canonical(dict(error='invalid-output'))
    sys.stdout.buffer.write(raw)


if __name__ == '__main__': main()
