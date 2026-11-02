"""Loopback HTTP security over an explicit operator/backend fixture.

The real Workbench handler/listener and operator request validator are exercised.
No kubectl, Helm, native process, model, owner journal or remote service runs.
Temporary configuration contains synthetic fixture credentials only.
"""
import http.client
from http.server import ThreadingHTTPServer
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import uuid

from fusion.contracts import ContractError, canonical, digest
from fusion.preview_sessions import PROFILE
from integration.single_node import preview_operator, preview_workbench as w


class OperatorFixture:
    namespace = 'omega-ref-workbench-fixture'
    def __init__(self):
        self.sid = str(uuid.uuid4()); self.calls = []; self.workload_calls = 0; self.failure = None
        self.inventory = dict(principal='A', scope='synthetic-workbench', sessions={self.sid: {}},
            assignments=['synthetic-notes'], catalogues={self.sid: {'profile': 'FIXTURE_CATALOGUE'}},
            worker=None, model_boundary='RECORDED_FIXTURE', additional_live_generations=0)

    def workloads(self):
        self.workload_calls += 1
        return [dict(metadata={'name': role}, status={'readyReplicas': 1},
            spec={'template': {'spec': {'containers': [{'image': 'fixture.invalid/never-run:1'}]}}})
            for role in ('omega-agent', 'fusion-storage')]

    def k(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        if self.failure: raise self.failure
        operation = args[6]
        if operation == 'inventory': return json.dumps(self.inventory)
        if operation == 'observe':
            return json.dumps(dict(session=self.sid, state='active', inputs=[], next_after=None, complete=True))
        return json.dumps(dict(boundary='OPERATOR_RESULT_FIXTURE', operation=operation))


class QuietServer(ThreadingHTTPServer):
    def handle_error(self, request, client_address):
        # Do not print a synthetic secret-marker traceback into test logs.
        self.errors.append(type(sys.exc_info()[1]).__name__)


class WorkbenchHTTPTests(unittest.TestCase):
    def setUp(self):
        self.operator = OperatorFixture()
        self.workbench = w.Workbench(self.operator)
        self.workbench.state()
        self.server = QuietServer(('127.0.0.1', 0), w.handler(self.workbench, 0))
        self.server.errors = []
        self.port = self.server.server_address[1]
        self.server.RequestHandlerClass = w.handler(self.workbench, self.port)
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={'poll_interval': .01}, daemon=True)
        self.thread.start()
        self.addCleanup(self.close)

    def close(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join(2)

    def request(self, method='GET', path='/', value=None, *, raw=None, headers=None):
        body = raw if raw is not None else canonical(value) if value is not None else b''
        if headers is None:
            headers = [('Host', '127.0.0.1:'+str(self.port)), ('Authorization', 'Bearer '+self.workbench.token)]
            if method == 'POST': headers += [('Origin', 'http://127.0.0.1:'+str(self.port)),
                ('Content-Type', 'application/json'), ('Content-Length', str(len(body)))]
        connection = http.client.HTTPConnection('127.0.0.1', self.port, timeout=2)
        try:
            connection.putrequest(method, path, skip_host=True, skip_accept_encoding=True)
            for name, value in headers: connection.putheader(name, value)
            connection.endheaders(body)
            try:
                reply = connection.getresponse()
                return reply.status, dict(reply.getheaders()), reply.read()
            except http.client.RemoteDisconnected: return 0, {}, b''
        finally: connection.close()

    def action(self, **changes):
        return dict(role='omega-agent', session=self.operator.sid, operation='submit', identity='stable-input',
                    text='Synthetic note', assignment='synthetic-notes', **changes)

    def assert_error(self, result, code=None):
        status, headers, raw = result
        self.assertEqual(status, 400)
        value = json.loads(raw)
        self.assertEqual(set(value), {'error'})
        if code: self.assertEqual(value['error'], code)
        self.assertEqual(headers['Cache-Control'], 'no-store')
        self.assertNotIn(b'SECRET_FIXTURE_MARKER', raw)
        self.assertNotIn(self.workbench.token.encode(), raw)
        self.assertNotIn(self.workbench.token, str(headers))
        return value

    def test_public_shell_has_no_session_data_or_credentials_and_does_not_call_operator(self):
        before = (len(self.operator.calls), self.operator.workload_calls)
        status, headers, body = self.request(headers=[('Host', '127.0.0.1:'+str(self.port))])
        self.assertEqual(status, 200)
        self.assertIn(b'Developer workbench', body)
        self.assertIn(b'type="password"', body)
        for secret in (self.workbench.token, self.operator.sid, self.operator.namespace,
                       self.operator.inventory['scope'], 'SECRET_FIXTURE_MARKER'):
            self.assertNotIn(secret.encode(), body)
            self.assertNotIn(secret, str(headers))
        self.assertEqual((len(self.operator.calls), self.operator.workload_calls), before)

    def test_generated_access_tokens_are_distinct_and_not_provider_credentials(self):
        other = w.Workbench(self.operator)
        self.assertGreaterEqual(len(self.workbench.token), 32)
        self.assertNotEqual(self.workbench.token, other.token)
        self.assertNotEqual(self.workbench.token, 'SECRET_FIXTURE_MARKER')

    def test_missing_wrong_and_duplicate_authorization_refuse_before_operator(self):
        cases = [
            ('missing', []),
            ('wrong', [('Authorization', 'Bearer wrong-workbench-access')]),
            ('provider-credential', [('Authorization', 'Bearer SECRET_FIXTURE_MARKER')]),
            ('wrong-scheme', [('Authorization', 'Basic '+self.workbench.token)]),
            ('duplicate-valid', [('Authorization', 'Bearer '+self.workbench.token)]*2),
            ('mixed-case-duplicate', [('Authorization', 'Bearer '+self.workbench.token),
                                     ('authorization', 'Bearer wrong-workbench-access')]),
        ]
        endpoints = [('GET', '/api/state'),
                     ('GET', '/api/session?role=omega-agent&session='+self.operator.sid+'&after=0'),
                     ('POST', '/api/action')]
        before = (len(self.operator.calls), self.operator.workload_calls)
        for method, path in endpoints:
            body = canonical(self.action()) if method == 'POST' else b''
            base = [('Host', '127.0.0.1:'+str(self.port))]
            if method == 'POST':
                base += [('Origin', 'http://127.0.0.1:'+str(self.port)),
                         ('Content-Type', 'application/json'), ('Content-Length', str(len(body)))]
            for name, authorization in cases:
                with self.subTest(method=method, endpoint=path.split('?')[0], authorization=name):
                    self.assert_error(self.request(method, path, raw=body, headers=base+authorization),
                                      'UNAUTHORIZED')
                    self.assertEqual((len(self.operator.calls), self.operator.workload_calls), before)
        self.assertEqual(self.server.errors, [])

    def test_query_parameter_or_cookie_cannot_replace_authorization(self):
        before = (len(self.operator.calls), self.operator.workload_calls)
        headers = [('Host', '127.0.0.1:'+str(self.port)), ('Cookie', 'access='+self.workbench.token)]
        self.assert_error(self.request(path='/api/state?access='+self.workbench.token, headers=headers),
                          'UNAUTHORIZED')
        self.assertEqual((len(self.operator.calls), self.operator.workload_calls), before)

    def test_page_security_headers_and_inventory_do_not_execute_actions(self):
        before = len(self.operator.calls)
        status, headers, body = self.request()
        self.assertEqual(status, 200)
        self.assertIn(b'Developer workbench', body)
        self.assertEqual(headers['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(headers['Referrer-Policy'], 'no-referrer')
        self.assertIn("frame-ancestors 'none'", headers['Content-Security-Policy'])
        self.assertEqual(len(self.operator.calls), before)
        status, _, body = self.request(path='/api/state')
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)['additional_live_generations'], 0)
        self.assertNotIn(self.workbench.token.encode(), body)
        self.assertNotIn(b'SECRET_FIXTURE_MARKER', body)
        self.assertTrue(all(call[0][6] == 'inventory' for call in self.operator.calls))

    def test_same_origin_submission_preserves_identity_text_and_fixed_entrypoint(self):
        body = self.action()
        body['text'] = 'Synthetic $(not-executed) ; <script>data</script>'
        status, _, raw = self.request('POST', '/api/action', body)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(raw)['boundary'], 'OPERATOR_RESULT_FIXTURE')
        self.assertNotIn(self.workbench.token.encode(), raw)
        self.assertNotIn(b'SECRET_FIXTURE_MARKER', raw)
        args, options = self.operator.calls[-1]
        self.assertEqual(args[:6], ('exec', 'omega-agent-0', '--', w.PYTHON, '-m', 'integration.single_node.preview_operator'))
        self.assertEqual(args[args.index('--identity')+1], 'stable-input')
        self.assertEqual(args[args.index('--text')+1], body['text'])
        self.assertEqual(options, {'timeout': 40})
        self.request('POST', '/api/action', body)
        self.assertEqual(self.operator.calls[-1], (args, options))

    def test_foreign_host_origin_and_missing_origin_refuse_before_backend(self):
        raw = canonical(self.action())
        good = [('Host', '127.0.0.1:'+str(self.port)), ('Origin', 'http://127.0.0.1:'+str(self.port)),
                ('Content-Type', 'application/json'), ('Content-Length', str(len(raw))),
                ('Authorization', 'Bearer '+self.workbench.token)]
        before = len(self.operator.calls)
        for headers in ([('Host', 'evil.invalid'), *good[1:]], [good[0], ('Origin', 'https://evil.invalid'), *good[2:]],
                        [good[0], *good[2:]]):
            with self.subTest(headers=headers): self.assert_error(self.request('POST', '/api/action', raw=raw, headers=headers))
        self.assertEqual(len(self.operator.calls), before)

    def test_duplicate_security_headers_and_transfer_encoding_refuse(self):
        raw = canonical(self.action())
        base = [('Host', '127.0.0.1:'+str(self.port)), ('Origin', 'http://127.0.0.1:'+str(self.port)),
                ('Content-Type', 'application/json'), ('Content-Length', str(len(raw))),
                ('Authorization', 'Bearer '+self.workbench.token)]
        before = len(self.operator.calls)
        for extra in [('Host', 'evil.invalid'), ('Origin', 'https://evil.invalid'), ('Content-Type', 'text/plain'),
                      ('Content-Length', str(len(raw))), ('Transfer-Encoding', 'chunked')]:
            with self.subTest(extra=extra): self.assert_error(self.request('POST', '/api/action', raw=raw, headers=[*base, extra]))
        self.assertEqual(len(self.operator.calls), before)

    def test_root_type_unhashable_selectors_and_duplicate_json_keys_are_sanitized(self):
        for value in ([], None, 7, dict(self.action(), role=[]), dict(self.action(), session={})): 
            with self.subTest(value=value): self.assert_error(self.request('POST', '/api/action', raw=canonical(value)))
        self.assert_error(self.request('POST', '/api/action', raw=b'{"role":"omega-agent","role":"forged"}'))
        self.assertEqual(self.server.errors, [])

    def test_closed_action_fields_authority_and_bounds_prevent_backend_dispatch(self):
        before = len(self.operator.calls)
        cases = [dict(self.action(), role='fusion-storage'), dict(self.action(), session=str(uuid.uuid4())),
            dict(self.action(), assignment='shell'), dict(self.action(), identity='x'*129),
            dict(self.action(), text='x'*4097), dict(self.action(), extra='credential'),
            dict(self.action(), operation='shell')]
        for body in cases:
            with self.subTest(keys=body.keys()): self.assert_error(self.request('POST', '/api/action', body))
        raw = b'x'*16385
        self.assert_error(self.request('POST', '/api/action', raw=raw))
        self.assertEqual(len(self.operator.calls), before)

    def test_observation_query_is_closed_bounded_and_readonly(self):
        base = '/api/session?role=omega-agent&session='+self.operator.sid
        status, _, raw = self.request(path=base+'&after=0')
        self.assertEqual(status, 200)
        self.assertNotIn(self.workbench.token.encode(), raw)
        self.assertNotIn(b'SECRET_FIXTURE_MARKER', raw)
        self.assertEqual(self.operator.calls[-1][0][6], 'observe')
        before = len(self.operator.calls)
        for suffix in ('&after=-1', '&after=33', '&after=1&after=2', '&after=0&credential=forged'):
            with self.subTest(suffix=suffix): self.assert_error(self.request(path=base+suffix))
        self.assertEqual(len(self.operator.calls), before)

    def test_backend_failures_are_sanitized_json_including_timeout_and_missing_binary(self):
        failures = [RuntimeError('SECRET_FIXTURE_MARKER'),
            subprocess.TimeoutExpired(['fixture', 'SECRET_FIXTURE_MARKER'], 40),
            subprocess.CalledProcessError(1, ['fixture'], stderr='SECRET_FIXTURE_MARKER'),
            OSError('SECRET_FIXTURE_MARKER')]
        for failure in failures:
            with self.subTest(error=type(failure).__name__):
                self.operator.failure = failure
                self.assert_error(self.request('POST', '/api/action', self.action()), 'NOT_AVAILABLE')
        self.assertEqual(self.server.errors, [])

    def test_partial_post_does_not_hold_global_operator_lock(self):
        sock = socket.create_connection(('127.0.0.1', self.port), timeout=2)
        try:
            request = ('POST /api/action HTTP/1.1\r\nHost: 127.0.0.1:'+str(self.port)+
                '\r\nOrigin: http://127.0.0.1:'+str(self.port)+
                '\r\nAuthorization: Bearer '+self.workbench.token+
                '\r\nContent-Type: application/json\r\nContent-Length: 20\r\n\r\n{').encode()
            sock.sendall(request)
            time.sleep(.03)
            status, _, _ = self.request(path='/favicon.ico')
            self.assertEqual(status, 200)
            sock.shutdown(socket.SHUT_WR)
            self.assertIn(b'400', sock.recv(4096))
        finally: sock.close()

    def test_truncated_declared_body_cannot_dispatch_even_if_received_json_is_valid(self):
        body = canonical(self.action())
        before = len(self.operator.calls)
        sock = socket.create_connection(('127.0.0.1', self.port), timeout=2)
        try:
            headers = ('POST /api/action HTTP/1.1\r\nHost: 127.0.0.1:'+str(self.port)+
                '\r\nOrigin: http://127.0.0.1:'+str(self.port)+
                '\r\nAuthorization: Bearer '+self.workbench.token+
                '\r\nContent-Type: application/json\r\nContent-Length: '+str(len(body)+10)+'\r\n\r\n').encode()
            sock.sendall(headers+body); sock.shutdown(socket.SHUT_WR)
            response = http.client.HTTPResponse(sock); response.begin()
            self.assert_error((response.status, dict(response.getheaders()), response.read()))
        finally: sock.close()
        self.assertEqual(len(self.operator.calls), before)

    def test_abandoned_partial_body_has_a_bounded_read_timeout(self):
        sock = socket.create_connection(('127.0.0.1', self.port), timeout=6)
        try:
            headers = ('POST /api/action HTTP/1.1\r\nHost: 127.0.0.1:'+str(self.port)+
                '\r\nOrigin: http://127.0.0.1:'+str(self.port)+
                '\r\nAuthorization: Bearer '+self.workbench.token+
                '\r\nContent-Type: application/json\r\nContent-Length: 20\r\n\r\n{').encode()
            start = time.monotonic(); sock.sendall(headers)
            response = http.client.HTTPResponse(sock); response.begin()
            self.assert_error((response.status, dict(response.getheaders()), response.read()), 'NOT_AVAILABLE')
            self.assertLess(time.monotonic()-start, 5.5)
        finally: sock.close()

    def test_unknown_path_is_not_a_tool_endpoint(self):
        self.assertEqual(self.request(path='/execute?command=id')[0], 404)
        self.assert_error(self.request('POST', '/execute', self.action()), 'UNSUPPORTED_OPERATION')


class OperatorResponseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='phase2-operator-fixture-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.sid = str(uuid.uuid4())
        self.owner = self.root/'owner.json'; self.component = self.root/'component.json'
        self.owner.write_bytes(canonical(dict(principals={'operator': {'credential': 'SECRET_FIXTURE_MARKER'}},
            native_sessions=dict(principal='B', session_templates={self.sid: {}}))))
        self.component.write_bytes(canonical(dict(role='omega-agent-b', https_port=8443,
            peers={'omega-agent-b': 'omega-agent-b.synthetic.svc.cluster.local'})))

    def invoke(self, mutate=lambda value: value):
        def reply(cfg, route, wire):
            self.assertEqual(route, '/preview/session')
            self.assertEqual(cfg['credential'], 'SECRET_FIXTURE_MARKER')
            return mutate(dict(id=wire['id'], profile=PROFILE, request_digest=digest(canonical(wire)),
                actor='operator', principal='B', value={'boundary': 'RECORDED_REPLY_FIXTURE'}))
        with patch.object(preview_operator, 'invoke', side_effect=reply):
            return preview_operator.request('observe', self.sid, {'content': False, 'after': 0},
                                            owner=str(self.owner), component=str(self.component))

    def test_correct_reply_returns_only_value_without_credentials(self):
        self.assertEqual(self.invoke(), {'boundary': 'RECORDED_REPLY_FIXTURE'})

    def test_response_correlation_actor_and_principal_are_checked(self):
        for field, replacement in [('id', str(uuid.uuid4())), ('request_digest', '0'*64),
                                  ('actor', 'worker'), ('principal', 'A')]:
            with self.subTest(field=field), self.assertRaises(ContractError):
                self.invoke(lambda value: dict(value, **{field: replacement}))

    def test_wrong_missing_profile_and_extra_response_fields_are_rejected(self):
        def missing(value): del value['profile']; return value
        for mutate in (lambda value: dict(value, profile='unselected-session-profile/1'), missing,
                       lambda value: dict(value, authorized=True)):
            with self.subTest(mutate=mutate), self.assertRaises(ContractError): self.invoke(mutate)

    def test_protected_namespace_refused_before_operator_or_cluster_construction(self):
        for namespace in ('omega-demo', 'omega-ref-live01'):
            with (self.subTest(namespace=namespace), patch.object(w, 'Operator') as operator,
                  patch.object(sys, 'argv', ['workbench', '--kubeconfig', '/not-read', '--context', 'fixture',
                      '--namespace', namespace, '--access-file', str(self.root/'not-created-access')])):
                with self.assertRaises(ContractError): w.main()
                operator.assert_not_called()

    def test_main_writes_new_private_access_file_without_printing_token(self):
        access = self.root/'private-access'
        output = io.StringIO()
        args = ['workbench', '--kubeconfig', '/fixture-not-read', '--context', 'fixture',
                '--namespace', 'omega-ref-workbench-fixture', '--port', '8768', '--access-file', str(access)]
        with (patch.object(sys, 'argv', args), patch.object(w, 'Operator') as operator,
              patch.object(w, 'ThreadingHTTPServer') as server, redirect_stdout(output)):
            w.main()
        token = access.read_text().removesuffix('\n')
        self.assertGreaterEqual(len(token), 32)
        self.assertEqual(access.read_text(), token+'\n')
        self.assertEqual(access.stat().st_mode & 0o777, 0o600)
        self.assertNotIn(token, output.getvalue())
        self.assertNotIn('SECRET_FIXTURE_MARKER', output.getvalue())
        operator.return_value.owned.assert_called_once_with()
        self.assertEqual(server.call_args.args[0], ('127.0.0.1', 8768))
        server.return_value.serve_forever.assert_called_once_with()
        server.return_value.server_close.assert_called_once_with()

    def test_main_refuses_existing_access_file_without_overwrite_or_listener(self):
        access = self.root/'existing-access'
        access.write_text('retained synthetic access\n')
        args = ['workbench', '--kubeconfig', '/fixture-not-read', '--context', 'fixture',
                '--namespace', 'omega-ref-workbench-fixture', '--access-file', str(access)]
        with (patch.object(sys, 'argv', args), patch.object(w, 'Operator'),
              patch.object(w, 'ThreadingHTTPServer') as server):
            with self.assertRaises(FileExistsError): w.main()
        self.assertEqual(access.read_text(), 'retained synthetic access\n')
        server.assert_not_called()


if __name__ == '__main__': unittest.main()
