"""Authenticated real HTTPS gates; corruption injections are labelled fixtures."""
import copy
import http.client
import json
import os
from pathlib import Path
import signal
import sqlite3
import ssl
import subprocess
import time
import unittest

from fusion import neoclaw_contracts as c
from fusion.contracts import ContractError, canonical
from fusion.neoclaw_transport import Network
from fusion.ports import Mutation
from tests.neoclaw_support import Harness, GOLDEN, PREMISES, RUNTIME, DETTA
from integration.neoclaw.test_recovery import evidence


class NetworkS01(unittest.TestCase):
    def setUp(self):
        self.assertTrue(RUNTIME.is_file(), 'BLOCKED: pinned S01 runtime not built')
        self.assertTrue(DETTA.is_file(), 'BLOCKED: real DeTTa adapter unavailable')
        self.h = Harness(real=True);self.addCleanup(self.h.close)
        self.h.network();self.h.service().close()
        self.caller = self.h.caller();self.addCleanup(self.caller.close)
        self.request = self.caller.prepare(PREMISES)

    def raw(self, data, credential=None, authenticated=True):
        context = ssl.create_default_context(cafile=self.h.client['endpoint']['ca_file'])
        connection = http.client.HTTPSConnection('127.0.0.1', self.h.port, context=context, timeout=2)
        headers = {'Content-Type':'application/json'}
        if authenticated:headers['Authorization'] = 'Bearer '+(credential or self.h.client['credential'])
        try:
            connection.request('POST', '/s01', data, headers)
            response = connection.getresponse()
            return json.loads(response.read())
        finally:connection.close()

    def test_real_https_authority_closed_input_and_selection_matrix(self):
        self.assertEqual(self.raw(canonical(self.request), authenticated=False)['error']['code'], 'UNAUTHORIZED')
        for credential in ('not-a-credential', self.h.config['principals']['B']['credential'],
                           self.h.config['principals']['outsider']['credential']):
            self.assertEqual(self.raw(canonical(self.request), credential)['error']['code'], 'UNAUTHORIZED')
        variants = []
        def change(path, value, code):
            item = copy.deepcopy(self.request);owner = item
            for key in path[:-1]:owner = owner[key]
            owner[path[-1]] = value;variants.append((item, code))
        change(['scope_ref'], 'private-omega', 'UNAUTHORIZED')
        change(['reply_route'], 'reply-B', 'UNAUTHORIZED')
        change(['body','sharing'], 'private-local-only', 'UNAUTHORIZED')
        change(['body','operation'], 'eval', 'UNSUPPORTED_OPERATION')
        change(['operation'], 'work', 'UNSUPPORTED_OPERATION')
        change(['profile'], 'guarded-deduction/1', 'UNSUPPORTED_PROFILE')
        change(['selection'], 'f'*64, 'UNSUPPORTED_PROFILE')
        change(['interface_ref','version'], '99.0.0', 'UNSUPPORTED_VERSION')
        change(['body','premises'], [{'strength':'NaN','confidence':'1'}]*2, 'INVALID_ARGUMENT')
        change(['body','code'], '(import! &self arbitrary)', 'INVALID_ARGUMENT')
        change(['principal'], 'worker', 'INVALID_ARGUMENT')
        for request, code in variants:
            with self.subTest(code=code, body=request['body']):
                self.assertEqual(self.raw(canonical(request))['error']['code'], code)
        for raw in (b'{"a":1,"a":2}', b'{"a":NaN}', b'x'*4097, b'['*1500+b']'*1500):
            self.assertEqual(self.raw(raw)['error']['code'], 'INVALID_ARGUMENT')
        self.assertEqual(self.h.counts()['jobs'], 0)
        first = self.raw(canonical(self.request))['ok']
        repeated = dict(self.request, message_id='another-transport-attempt')
        self.assertEqual(self.raw(canonical(repeated))['ok'], first)
        conflict = copy.deepcopy(self.request);conflict['body']['premises'][0]['strength'] = '0.2'
        self.assertEqual(self.raw(canonical(conflict))['error']['code'], 'CONFLICT')
        self.h.config['principals']['A']['scopes'][c.SCOPE].remove('execution.submit');self.h.save()
        self.assertEqual(self.raw(canonical(self.request))['error']['code'], 'UNAUTHORIZED')
        evidence('network-authority', dict(placement='same-host isolated HTTPS', unauthorized_cases=8,
                 input_binding_cases=len(variants), malformed_json_or_size=4, replay='same logical acceptance',
                 changed_intent='CONFLICT', revoked_replay='UNAUTHORIZED', jobs=1))

    def test_certificate_verification_and_non_loopback_refusal(self):
        wrong = self.h.caller_root/'wrong.pem'
        subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(self.h.caller_root/'wrong.key'),
            '-out',str(wrong),'-days','1','-subj','/CN=wrong'], check=True, capture_output=True)
        endpoint = dict(self.h.client['endpoint'], ca_file=str(wrong))
        transport = Network(endpoint, self.h.client['credential'], self.caller.chosen)
        with self.assertRaises(ContractError) as failed:transport.invoke(self.request)
        self.assertEqual(failed.exception.code, 'NOT_AVAILABLE')
        for host in ('0.0.0.0','example.org','192.0.2.1','::1'):
            with self.assertRaises(ContractError) as failed:
                Network(dict(endpoint, host=host), self.h.client['credential'], self.caller.chosen)
            self.assertEqual(failed.exception.code, 'UNSUPPORTED_PROFILE')
        self.assertEqual(self.h.counts()['jobs'], 0)

    def test_native_invalid_named_command_never_falls_through(self):
        for expression in ('(Truth_Deduction (stv 2 1) (stv 1 1))',
                           '(Truth_Deduction (stv $f 1) (stv 1 1))',
                           '(Truth_Deduction (stv 0.8 0.9) (stv 0.7 0.8) extra)'):
            with self.subTest(expression=expression):
                actual = self.h.native('metta '+expression)
                self.assertIsNone(actual['values'], actual)
        self.assertEqual(self.h.counts()['jobs'], 0)
        self.assertEqual(self.h.counts()['caller_calls'], 0)

    def test_filesystem_namespace_masks_provider_and_old_omega(self):
        private = Path.home()/'work/takopi/mettaclaw'
        # Check path visibility, never read old Omega files or credential bytes.
        command = ['bwrap','--ro-bind','/','/','--proc','/proc','--dev','/dev',
            '--tmpfs',str(self.h.server_root),'--tmpfs',str(private),'--',
            '/usr/bin/test','!','-e',str(self.h.config_path)]
        self.assertEqual(subprocess.run(command, capture_output=True).returncode, 0)
        command[-2:] = ['-e', str(private/'.git')]
        self.assertEqual(subprocess.run(command, capture_output=True).returncode, 0)
        self.assertEqual(self.h.native()['values'], [GOLDEN])
        self.assertNotIn('provider_config', self.h.client)
        evidence('placement', dict(transport='HTTPS over TCP', bind='127.0.0.1',
            certificate_verification=True, bearer_authentication=True, caller_native_process=True,
            provider_files_masked=True, old_omega_checkout_masked=True,
            multi_host='UNRUN; unsupported by this loopback-only transport profile',
            public_service=False, fallback=False))

    def test_malformed_network_completion_cannot_ack_or_reset_budget(self):
        self.caller._call(self.request);self.h.drive()
        # Explicit malicious-receipt fixture injected into the generated mailbox.
        with sqlite3.connect(self.h.config['messages_database']) as db:
            original = db.execute('SELECT body FROM messages').fetchone()[0]
            bad = json.loads(original);bad['correlation_id'] = 'unrelated-command'
            db.execute('UPDATE messages SET body=?', (canonical(bad).decode(),))
        actual = self.h.native()
        self.assertNotEqual(actual['values'], [GOLDEN], actual)
        self.assertEqual(self.h.counts()['unacked'], 1)
        self.assertEqual(self.h.counts()['caller_completed'], 0)
        with sqlite3.connect(self.h.config['messages_database']) as db:
            db.execute('UPDATE messages SET body=?', (original,))
        # The invalid receipt exhausted the original bounded RPC reservation.
        # Repair is not permission to replenish that budget on process restart.
        self.assertNotEqual(self.h.native()['values'], [GOLDEN])
        self.assertEqual(self.h.counts()['caller_calls'], self.h.client['max_calls'])
        self.assertEqual(self.h.counts()['unacked'], 1)

    def test_valid_digest_malformed_payload_refused_before_completion_poll(self):
        self.caller._call(self.request)
        service = self.h.service()
        try:
            service.work()
            row = service.db.execute('SELECT id,result FROM jobs').fetchone()
            original = json.loads(row['result'])
            data = json.loads(service.atoms_for('worker').get(original['ref']).bytes)
            service.flush()
            malformed = [canonical(dict(data, profile='unrelated-profile/1')),
                         b'{"operation":"nal_truth_deduction",'+canonical(data)[1:],
                         b'['*1500+b']'*1500]
            for index, raw in enumerate(malformed):
                with self.subTest(index=index):
                    forged = service.atoms_for('worker').create(Mutation(c.SCOPE,'malformed-result-fixture-'+str(index)),
                        'application/neoclaw-nal-result',raw)
                    # Owner-state fault injection only. No production bypass endpoint.
                    with service.db:
                        service.db.execute('UPDATE jobs SET result=?', (canonical(forged).decode(),))
                    calls = self.h.counts()['caller_calls']
                    actual = self.h.native()
                    self.assertNotEqual(actual['values'], [GOLDEN], actual)
                    # Submit, status, result, get: fail before polling/acking.
                    self.assertEqual(self.h.counts()['caller_calls']-calls, 4)
        finally:service.close()
        self.assertEqual(self.h.counts()['caller_completed'], 0)
        self.assertEqual(self.h.counts()['unacked'], 1)

    def test_current_authority_on_result_and_read_over_https(self):
        accepted = self.caller._call(self.request);self.h.drive()
        for method, name, operation, body in (
            ('execution.result','execution','result',dict(job_id=accepted['job_id'])),
            ('agent.messaging.poll','agent.messaging','poll',dict(route='reply-A'))):
            with self.subTest(method=method):
                methods = self.h.config['principals']['A']['scopes'][c.SCOPE]
                methods.remove(method);self.h.save()
                request = self.caller._request(name, operation, body)
                self.assertEqual(self.raw(canonical(request))['error']['code'], 'UNAUTHORIZED')
                methods.append(method);self.h.save()
        request = self.caller._request('execution','status',dict(job_id=accepted['job_id']))
        self.assertEqual(self.raw(canonical(request), self.h.config['principals']['B']['credential'])['error']['code'],'NOT_FOUND')
        self.assertEqual(self.h.native()['values'], [GOLDEN])


if __name__ == '__main__':unittest.main()
