"""Kubeconfig-free browser-API qualification against a separately started gateway.

No provider credentials, cluster client, model socket or source checkout are
required. Native tools execute only through the existing session owner. The
selected model boundary must be RECORDED_FIXTURE; this runner cannot activate a
live model. Reconnect mode observes the exact retained inputs and never submits.
Reports contain approved synthetic captures and must be retained privately until
an operator selects a sanitized publication.
"""
import argparse
import hashlib
import http.cookiejar
import json
import os
from pathlib import Path
import time
import urllib.error
import urllib.parse
import urllib.request

def check(condition, message='QUALIFICATION_REFUSED'):
    if not condition:
        raise ValueError(message)

class BrowserClient:

    def __init__(self, base, user, bootstrap):
        parsed = urllib.parse.urlsplit(base)
        check(parsed.scheme == 'http' and parsed.hostname in ('127.0.0.1', 'localhost') and parsed.port and (parsed.path in ('', '/')))
        self.base = base.rstrip('/')
        self.user = user
        self.bootstrap = bootstrap
        self.csrf = None
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def request(self, path, body=None):
        check(path.startswith('/api/') and len(path) < 2048)
        raw = None if body is None else json.dumps(body, separators=(',', ':')).encode()
        headers = {} if body is None else {'Origin': self.base, 'Content-Type': 'application/json'}
        if body is not None and self.csrf:
            headers['X-Omega-CSRF'] = self.csrf
        request = urllib.request.Request(self.base + path, data=raw, headers=headers)
        try:
            with self.opener.open(request, timeout=35) as response:
                value = json.loads(response.read(131073))
                check(response.status == 200)
        except urllib.error.HTTPError as error:
            value = json.loads(error.read(4097))
            raise RuntimeError(value.get('error', 'NOT_AVAILABLE')) from None
        return value

    def login(self):
        auth = self.request('/api/login', {'user': self.user, 'credential': self.bootstrap})
        self.csrf = auth['csrf']
        return auth

    def observe(self, role, session):
        return self.request('/api/session?' + urllib.parse.urlencode({'role': role, 'session': session, 'after': 0}))

    def logout(self):
        return self.request('/api/logout', {})

def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

def qualify(client, plan, progress=lambda _: None):
    check(set(plan) == {'identity', 'role', 'template', 'commands', 'denied_sessions'})
    check(isinstance(plan['identity'], str) and 0 < len(plan['identity']) <= 64)
    check(isinstance(plan['commands'], list) and 1 <= len(plan['commands']) <= 24)
    journal=dict(schema='pilot-browser-native-qualification/1',state='PREPARING',user=client.user,plan_sha256=fingerprint(plan),attempts=[],additional_live_generations=0)
    progress(journal)
    client.login()
    state = client.request('/api/state')
    role = plan['role']
    agent = state['agents'][role]
    check(agent['model_boundary'] == ['RECORDED_FIXTURE'] and state['additional_live_generations'] == 0)
    allocation = client.request('/api/action', dict(role=role, session='', operation='allocate', identity=plan['identity'] + '-allocation', template=plan['template']))
    session = allocation['session']
    journal.update(state='SESSION_ACCEPTED',session=session,role=role);progress(journal)
    selected = dict(role=role, session=session)
    captures = []
    for number, commands in enumerate(plan['commands']):
        check(isinstance(commands, list) and len(commands) == 1 and isinstance(commands[0], list) and commands[0])
        caps = client.request('/api/capabilities?' + urllib.parse.urlencode(selected))
        check(caps['model_boundary'] == 'RECORDED_FIXTURE' and caps['advisory'] and (not caps['acceptance_created']))
        admitted = client.request('/api/preflight', dict(selected, commands=commands))
        check(admitted['preflight']['admissible'], admitted['preflight'])
        text = ' '.join(commands[0])
        key = plan['identity'] + '-input-' + str(number)
        attempt=dict(caller_identity=key,state='SUBMISSION_OUTCOME_NOT_YET_OBSERVED');journal['attempts'].append(attempt);progress(journal)
        accepted = client.request('/api/action', dict(selected, operation='submit', identity=key, text=text, assignment=agent['assignments'][0], catalogue=caps['catalogue']))
        attempt.update(state='ACCEPTANCE_OBSERVED',receipt=accepted);progress(journal)
        deadline = accepted['deadline']
        input_id = accepted['id']
        started = time.monotonic()
        observed = None
        for _ in range(150):
            observed = client.observe(role, session)
            row = next((x for x in observed['inputs'] if x['id'] == input_id))
            check(row['deadline'] == deadline)
            if row['state'] in ('complete', 'expired-before-start', 'cancelled-before-start', 'rejected'):
                break
            if time.time_ns() // 1000000 >= deadline:
                break
            time.sleep(min(1, max(0, (deadline - time.time_ns() // 1000000) / 1000)))
        record = dict(identity=input_id, deadline=deadline, state=row['state'], result=row.get('result'), result_sha256=fingerprint(row.get('result')), observation_seconds=round(time.monotonic() - started, 3))
        captures.append(record);attempt.update(state='OUTCOME_OBSERVED',outcome=record);progress(journal)
        if row['state'] != 'complete':
            break
    before = client.observe(role, session)
    denied = []
    for other in plan['denied_sessions']:
        check(set(other) == {'role', 'session'})
        try:
            client.observe(other['role'], other['session'])
        except RuntimeError as error:
            denied.append(str(error) == 'UNAUTHORIZED')
        else:
            denied.append(False)
    client.logout()
    client.login()
    after = client.observe(role, session)
    check(before == after)
    report = dict(schema='pilot-browser-native-qualification/1', namespace=state['namespace'], user=client.user, role=role, session=session, plan_sha256=fingerprint(plan), captures=captures, retained_inputs_sha256=fingerprint(after['inputs']), read_reconnect_exact=True, foreign_sessions_refused=all(denied), foreign_session_checks=len(denied), additional_live_generations=0, native_inputs=len(captures), native_complete=sum((x['state'] == 'complete' for x in captures)), model='RECORDED_FIXTURE', native_effect_success='NOT_INFERRED_FROM_APPLICATION_COMPLETION', transport='BROWSER_HTTP_TO_SCOPED_GATEWAY_TO_OWNER_HTTPS', kubeconfig_required=False, provider_credentials_in_client=False, submissions_retried=0, source_implementation_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),submission_attempts=journal['attempts'])
    client.logout()
    return report

def reconnect(client, baseline):
    check(baseline['schema'] == 'pilot-browser-native-qualification/1' and baseline['user'] == client.user)
    client.login()
    value = client.observe(baseline['role'], baseline['session'])
    client.logout()
    check(fingerprint(value['inputs']) == baseline['retained_inputs_sha256'])
    return dict(schema='pilot-browser-reconnect-qualification/1', session=baseline['session'], retained_inputs_sha256=baseline['retained_inputs_sha256'], exact=True, submissions=0, additional_live_generations=0)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', required=True)
    parser.add_argument('--user', required=True)
    parser.add_argument('--bootstrap-file', required=True)
    parser.add_argument('--plan')
    parser.add_argument('--reconnect-report')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    check(bool(args.plan) != bool(args.reconnect_report))
    client = BrowserClient(args.base, args.user, Path(args.bootstrap_file).read_text().strip())
    target=Path(args.output)
    fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600);os.close(fd)
    def progress(value):
        temporary=target.with_suffix(target.suffix+'.pending')
        with temporary.open('w') as stream:
            os.chmod(temporary,0o600);json.dump(value,stream,sort_keys=True,indent=2);stream.write('\n');stream.flush();os.fsync(stream.fileno())
        temporary.replace(target)
    try:
        if args.plan:result=qualify(client,json.loads(Path(args.plan).read_bytes()),progress)
        else:result=reconnect(client,json.loads(Path(args.reconnect_report).read_bytes()))
    except Exception as error:
        raw=target.read_bytes();value=json.loads(raw) if raw else {}
        value.update(qualification_state='FAILED_RETAINED',failure_type=type(error).__name__,additional_live_generations=0)
        progress(value);raise
    progress(result)
    print(json.dumps({key: value for key, value in result.items() if key in ('schema', 'native_inputs', 'native_complete', 'exact', 'additional_live_generations')}))
if __name__ == '__main__':
    main()
