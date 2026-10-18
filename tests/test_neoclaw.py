"""S01 contracts and owner recovery tests. Kernel/files fixtures labelled explicitly."""
from dataclasses import replace
import ast
import copy
import hashlib
import json
from pathlib import Path
import sqlite3
import time
import unittest

from fusion import neoclaw_contracts as c
from fusion.contracts import ContractError, canonical
from fusion.neoclaw_client import Caller
from fusion.neoclaw_transport import checked_reply, json_loads
from fusion.registry import descriptor_wire, selection_token
from tests.neoclaw_support import Harness, FixtureKernel, PREMISES, GOLDEN, ROOT


class S01Contracts(unittest.TestCase):
    def setUp(self):
        self.h = Harness()
        self.addCleanup(self.h.close)

    def error(self, code, fn, *args):
        with self.assertRaises(ContractError) as failure:fn(*args)
        self.assertEqual(failure.exception.code, code)

    def request(self):
        caller = self.h.caller()
        try:return caller.prepare(PREMISES)
        finally:caller.close()

    def invoke(self, request, principal='A'):
        service = self.h.service()
        try:return service.invoke(self.h.config['principals'][principal]['credential'], request)
        finally:service.close()

    def test_closed_two_stv_contract_rejects_code_and_invalid_values(self):
        for value in [[], PREMISES[:1], PREMISES*2, None, 'expression',
                      [dict(strength=True, confidence='0.9'), PREMISES[1]],
                      [dict(strength=.8, confidence='0.9'), PREMISES[1]],
                      [dict(PREMISES[0], path='/tmp/private'), PREMISES[1]]]:
            with self.subTest(value=value):self.error('INVALID_ARGUMENT', c.premises, value)
        for number in ['NaN', 'inf', '-0.1', '1.1', '2', '$x', '(import! &self /tmp/x)', '0.1) (shell x)', '0.000000000000000001']:
            with self.subTest(number=number):self.error('INVALID_ARGUMENT', c.premises, [dict(strength=number, confidence='1'), PREMISES[1]])
        for value in ['(Truth_Revision (stv 1 1) (stv 1 1))', '(Truth_Deduction (stv 1 1))',
                      '(Truth_Deduction (stv 1 1) (stv 1 1)) (import! &self x)']:
            self.error('INVALID_ARGUMENT', c.parse_expression, value)
        self.assertEqual(c.parse_expression(c.expression(PREMISES)), PREMISES)
        self.assertEqual(c.native_truth('(stv 7.0e-18 5.04e-18)'), dict(strength='7.0e-18', confidence='5.04e-18'))
        for value in ['(stv 2 0)', '(stv NaN 1)', '(stv 0.1 0.2) extra', '(stv -0.1 0.2)']:
            self.error('NOT_AVAILABLE', c.native_truth, value)

    def test_authority_method_scope_route_and_replay_revocation(self):
        request = self.request()
        self.error('UNAUTHORIZED', self.invoke, request, 'outsider')
        self.error('UNAUTHORIZED', self.invoke, request, 'B')  # A's reply route
        private = copy.deepcopy(request);private['scope_ref'] = 'private'
        self.error('UNAUTHORIZED', self.invoke, private)
        private = copy.deepcopy(request);private['body']['sharing'] = 'private'
        self.error('UNAUTHORIZED', self.invoke, private)
        accepted = self.invoke(request)
        self.assertEqual(self.invoke(request), accepted)
        self.h.config['principals']['A']['scopes'][c.SCOPE].remove('execution.submit');self.h.save()
        self.error('UNAUTHORIZED', self.invoke, request)
        service = self.h.service()
        try:self.error('UNAUTHORIZED', service.invoke, 'invalid', request)
        finally:service.close()

    def test_descriptor_version_profile_runtime_and_operation_binding(self):
        request = self.request()
        variants = [('selection', '0'*64, 'UNSUPPORTED_PROFILE'), ('profile', 'grounded-five-premise-deduction/1', 'UNSUPPORTED_PROFILE'),
                    ('operation', 'work', 'UNSUPPORTED_OPERATION')]
        for field, value, code in variants:
            altered = copy.deepcopy(request);altered[field] = value
            self.error(code, self.invoke, altered)
        altered = copy.deepcopy(request);altered['interface_ref']['version'] = '2.0.0'
        self.error('UNSUPPORTED_VERSION', self.invoke, altered)
        altered = copy.deepcopy(request);altered['body']['operation'] = 'metta'
        self.error('UNSUPPORTED_OPERATION', self.invoke, altered)
        altered = copy.deepcopy(request);altered['body']['expression'] = '(+ 1 2)'
        self.error('INVALID_ARGUMENT', self.invoke, altered)
        catalogue = c.catalogue('fixture-files')
        for field, value in [('profiles', frozenset({'grounded-five-premise-deduction/1'})), ('features', frozenset()), ('privacy', 'private-local-only')]:
            broken = [replace(d, **{field:value}) if d.interface == 'pln.kernel' else d for d in catalogue]
            with self.assertRaises(ContractError):c.selected(broken)
        self.assertEqual(self.h.counts().get('jobs', 0), 0)

    def test_replay_identity_conflict_and_deadline_not_renewed(self):
        request = self.request();accepted = self.invoke(request)
        replay = copy.deepcopy(request);replay['message_id'] = 'another-transport-id'
        self.assertEqual(self.invoke(replay), accepted)
        for edit in ['premises', 'deadline_ms', 'max_attempts', 'reply_route']:
            other = copy.deepcopy(request)
            if edit == 'premises':other['body']['premises'][0]['strength'] = '0.7'
            elif edit == 'max_attempts':other['body'][edit] = 2
            elif edit == 'reply_route':
                self.h.config['routes']['another-A'] = dict(scope=c.SCOPE, owner='A');self.h.save();other[edit] = 'another-A'
            else:other[edit] += 5000
            self.error('CONFLICT', self.invoke, other)
        self.assertEqual(self.h.counts()['jobs'], 1)

    def test_deadline_prevents_new_computation_but_not_completed_replay(self):
        from unittest.mock import patch
        self.h.client['deadline_ms'] = int(time.time()*1000)+30000;self.h.save_client()
        request, _ = self.h.submit();self.h.drive()
        caller = self.h.caller()
        try:
            with patch('fusion.neoclaw.time.time', return_value=self.h.client['deadline_ms']/1000+1):
                self.assertEqual(caller.run(PREMISES), GOLDEN)
        finally:caller.close()
        self.assertEqual(self.h.counts()['attempts'], 1)
        self.h.client = self.h.client_config('expired');self.h.save_client()
        self.h.submit()
        caller = self.h.caller()
        try:
            with patch('fusion.neoclaw.time.time', return_value=self.h.client['deadline_ms']/1000+1):
                self.h.drive()
                self.assertEqual(self.h.counts()['attempts'], 1)
                self.error('DEADLINE_EXCEEDED', caller.run, PREMISES)
        finally:caller.close()
        self.assertEqual(self.h.counts()['unacked'], 0)

    def test_native_attempt_budget_survives_owner_restart_and_bad_kernel(self):
        self.h.submit()
        class Malformed:
            def applyTruth(self, *args):return dict(representation='(stv NaN 0.5)', truth={})
        for _ in range(3):
            service = self.h.service();service.kernel = Malformed()
            try:service.work()
            finally:service.close()
        self.h.drive()
        self.assertEqual(self.h.counts()['attempts'], 3)
        caller = self.h.caller()
        try:self.error('NOT_AVAILABLE', caller.run, PREMISES)
        finally:caller.close()
        self.assertEqual(self.h.counts()['caller_completed'], 1)  # explicit failed receipt, no numerical success
        self.assertEqual(self.h.counts()['unacked'], 0)

    def test_caller_budget_is_durable_and_cannot_be_reset(self):
        self.h.client['max_calls'] = 2;self.h.save_client()
        class Unavailable:
            correlations = {}
            def invoke(self, request):raise ContractError('NOT_AVAILABLE')
        for _ in range(2):
            caller = self.h.caller(Unavailable())
            try:self.error('NOT_AVAILABLE', caller.run, PREMISES)
            finally:caller.close()
        self.assertEqual(self.h.counts()['caller_calls'], 2)
        self.h.client['max_calls'] = 64;self.h.save_client()
        caller = self.h.caller(Unavailable())
        try:self.error('CONFLICT', caller.run, PREMISES)
        finally:caller.close()

    def test_result_binding_and_representation_validation(self):
        request = self.request();chosen = c.selected(c.catalogue('fixture-files'))
        good = dict(profile=c.PROFILE, operation=c.OPERATION, runtime=c.RUNTIME,
            selection=selection_token(chosen['pln.kernel']), request_digest=c.fingerprint(request),
            premises=PREMISES, representation=GOLDEN, truth=c.native_truth(GOLDEN))
        self.assertEqual(c.result(good, request, chosen), good)
        for key, value in [('profile', 'other/1'), ('operation', 'inspect_atom'), ('runtime', 'other'),
                           ('selection', '0'*64), ('request_digest', '0'*64), ('premises', list(reversed(PREMISES))),
                           ('representation', '(stv 9.0 0.5)'), ('truth', dict(strength='0.1', confidence='0.2'))]:
            with self.subTest(key=key):self.error('NOT_AVAILABLE', c.result, {**good,key:value}, request, chosen)
        self.error('NOT_AVAILABLE', c.result, {**good,'extra':True}, request, chosen)

    def test_acceptance_completion_and_payload_receipts_reject_malformed_data(self):
        request, accepted = self.h.submit();chosen = c.selected(c.catalogue('fixture-files'))
        good = dict(ok=accepted, provider=selection_token(chosen['execution']))
        self.assertEqual(checked_reply(request, good, chosen, {}), accepted)
        for payload in [dict(good, provider='0'*64), dict(ok={**accepted,'scope_ref':'private'},provider=good['provider']),
                        dict(ok={**accepted,'acceptance':'volatile'},provider=good['provider'])]:
            self.error('NOT_AVAILABLE', checked_reply, request, payload, chosen, {})
        self.h.drive()
        caller = self.h.caller()
        try:
            poll = caller._request('agent.messaging','poll',dict(route='reply-A'))
            delivery = self.invoke(poll)
            for field, value in [('delivery_id','wrong'),('scope_ref','private')]:
                corrupted = copy.deepcopy(delivery);corrupted['delivery'][field] = value
                self.error('NOT_AVAILABLE', checked_reply, poll, dict(ok=corrupted,provider=selection_token(chosen['agent.messaging'])), chosen, {})
            complete = delivery['delivery']['body']['result']
            get = caller._request('atom.storage','get',dict(ref=complete['ref']))
            payload = self.invoke(get);payload['bytes'] = 'aW52YWxpZA=='
            self.error('NOT_AVAILABLE', checked_reply, get, dict(ok=payload,provider=selection_token(chosen['atom.storage'])), chosen, {})
        finally:caller.close()
        self.assertEqual(self.h.counts()['unacked'], 1)

    def test_current_authority_on_result_poll_ack_and_worker(self):
        request, job = self.h.submit();self.h.drive()
        caller = self.h.caller()
        try:
            read = caller._request('execution','result',dict(job_id=job['job_id']))
            self.error('NOT_FOUND', self.invoke, read, 'B')
            poll = caller._request('agent.messaging','poll',dict(route='reply-A'))
            self.error('UNAUTHORIZED', self.invoke, poll, 'B')
            ack = caller._request('agent.messaging','ack',dict(route='reply-A',delivery_id=job['job_id']));ack['idempotency_key']='ack'
            self.h.config['principals']['A']['scopes'][c.SCOPE].remove('agent.messaging.ack');self.h.save()
            self.error('UNAUTHORIZED', self.invoke, ack)
            self.h.config['principals']['A']['scopes'][c.SCOPE].remove('execution.result');self.h.save()
            self.error('UNAUTHORIZED', self.invoke, read)
        finally:caller.close()
        self.assertEqual(self.h.counts()['unacked'], 1)

    def test_capacity_recovery_and_independent_owner_databases(self):
        self.h.config['capacity'] = 1;self.h.save()
        first_request, _ = self.h.submit()
        self.h.client = self.h.client_config('next');self.h.save_client()
        request = self.request();self.error('OVERLOADED', self.invoke, request)
        self.h.drive()
        # Accepted mailbox completion frees execution outbox capacity; mailbox
        # remains occupied until caller commit + ack.
        self.invoke(request);self.h.drive()
        self.assertEqual(self.h.counts()['unacked'], 1)
        self.h.client = self.h.client_config('command-1');self.h.client['deadline_ms'] = first_request['deadline_ms'];self.h.save_client()
        caller = self.h.caller()
        try:self.assertEqual(caller.run(PREMISES), GOLDEN)
        finally:caller.close()
        self.h.drive()
        self.assertEqual(self.h.counts()['messages'], 2)
        with sqlite3.connect(self.h.config['database']) as db:
            tables = {x[0] for x in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            self.assertFalse(tables & {'atoms','messages','caller_requests'})

    def test_no_fallback_and_duplicate_json_keys_rejected(self):
        self.h.client['fallback'] = True;self.h.save_client()
        self.error('UNSUPPORTED_PROFILE', self.h.caller)
        self.error('INVALID_ARGUMENT', json_loads, '{"operation":"submit","operation":"work"}')
        self.error('INVALID_ARGUMENT', json_loads, '{"x":NaN}')
        self.error('INVALID_ARGUMENT', json_loads, '['*1500+']'*1500)

    def test_existing_numerical_sources_unchanged(self):
        for name, expected in c.PINS['fusion_pln_pins_unchanged'].items():
            self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(), expected, name)
        manifest = json.loads((ROOT/'evidence/m5/final/verification.json').read_text())
        # S03.2 permits only these optional acceptance-observation additions.
        # Remove their exact AST spans and retain the historical byte-for-byte
        # guard for every pre-existing M5 implementation, including DA/storage.
        additions = {
            'fusion/atom_feed.py': ('FeedAtomOwner', 'observe', 1),
            'fusion/lookup_composition.py': ('AtomSession', 'observe', 0),
            'fusion/ports.py': (None, 'AtomMutationObservation', 2),
        }
        for name, expected in manifest['source']['files'].items():
            source = (ROOT/name).read_bytes()
            if name in additions:
                owner, symbol, trailing_blanks = additions[name]
                tree = ast.parse(source)
                parent = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == owner) if owner else tree
                nodes = [n for n in parent.body if getattr(n, 'name', None) == symbol]
                self.assertEqual(len(nodes), 1, name)
                node = nodes[0]; lines = source.splitlines(keepends=True)
                self.assertTrue(all(not line.strip() for line in lines[node.end_lineno:node.end_lineno+trailing_blanks]))
                source = b''.join(lines[:node.lineno-1] + lines[node.end_lineno+trailing_blanks:])
            self.assertEqual(hashlib.sha256(source).hexdigest(), expected, name)


if __name__ == '__main__':unittest.main()
