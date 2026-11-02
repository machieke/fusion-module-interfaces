"""Real inspect/job/mailbox owners with explicit payload/transport fixtures.

FileFeedFixture replaces AtomStorage; JSON encode/decode dispatch replaces
HTTPS. No native runtime, DeTTa, cluster, chain, or generation is exercised.
"""
import copy
import json
from pathlib import Path
import sqlite3
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import uuid

from fusion.adapters.fixture_feed import FileFeedFixture
from fusion.client import Peer
from fusion.contracts import ContractError, canonical, digest, require
from fusion.ports import Mutation
from fusion import preview_inspect as inspect
from fusion import registry
from integration.single_node import preview_inspect_configure as configure


SCOPE = 'synthetic-inspect-port-fixture'


class InspectPorts(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='phase2-inspect-fixture-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.ca = self.root / 'ca.crt'
        self.ca.write_text('explicit transport fixture; not a certificate')
        self.paths = {}
        self.settings = dict(preview=dict(scope=SCOPE, tasks=dict(enabled=True),
            memory=dict(enabled=True), agents={'omega-agent': {'principal': 'A'},
                                            'omega-agent-b': {'principal': 'B'}}))
        for role in ('fusion-execution', 'fusion-messaging'):
            state, run = self.root / role, self.root / (role + '-config')
            state.mkdir(); run.mkdir()
            configure.provider(dict(self.settings, role=role),
                dict(messages_database=str(state / 'mailbox.sqlite')), state, run,
                self.token, self.endpoint)
            self.paths[role] = run / 'inspect-owner.json'

        def authorize(scope, operation):
            require(scope == SCOPE and operation in ('create', 'get', 'head'), 'UNAUTHORIZED')
            return 'fixture-payload-owner'
        self.atoms = FileFeedFixture(self.root / 'fixture-atoms.json',
                                    SimpleNamespace(authorize=authorize))
        self.addCleanup(patch.stopall)
        patch.object(inspect, 'atoms_client', return_value=self.atoms).start()
        patch.object(inspect, 'descriptors', side_effect=lambda: registry.descriptors(atom_provider='fixture-files')).start()
        patch.object(inspect, 'invoke', side_effect=self.transport).start()
        current = self.root / 'caller'
        current.mkdir()
        self.client_path = configure.client(self.settings, current, 'A',
            lambda _: self.token('inspect-caller-A-token'), self.endpoint)
        self.client = inspect.Client(self.client_path)
        self.peer = Peer(self.client, SCOPE, 'inspect-A')
        self.data = b'Explicitly synthetic application result\n'
        self.input = self.atoms.create(Mutation(SCOPE, 'input'), 'text/plain', self.data)

    @staticmethod
    def token(name):
        return 'fixture-token-' + name

    def endpoint(self, role):
        return dict(host=role, port=8443, ca_file=str(self.ca))

    def owner(self, role='fusion-execution', hook=lambda _: None):
        return inspect.Ports(self.paths[role], role, hook)

    def transport(self, cfg, path, request, deadline=None):
        # This is a declared transport fixture, including an actual JSON boundary.
        value = self.owner(cfg['endpoint']['host']).invoke(
            path, cfg['credential'], json.loads(canonical(request)))
        return json.loads(canonical(value))

    def denied(self, code, function, *args, **kwargs):
        with self.assertRaises(ContractError) as caught:
            function(*args, **kwargs)
        self.assertEqual(caught.exception.code, code)

    def config(self, role):
        return json.loads(self.paths[role].read_text())

    def revoke(self, role, principal, method):
        cfg = self.config(role)
        cfg['principals'][principal]['scopes'][SCOPE].remove(method)
        self.paths[role].write_bytes(canonical(cfg))

    def rows(self, role, table, *, mailbox=False):
        cfg = self.config(role)
        path = cfg['messages_database'] if mailbox else cfg['database']
        if not Path(path).exists(): return []
        with sqlite3.connect(path) as db:
            db.row_factory = sqlite3.Row
            if not db.execute('SELECT 1 FROM sqlite_master WHERE name=?', (table,)).fetchone(): return []
            return [dict(row) for row in db.execute('SELECT * FROM ' + table)]

    def run_owner(self, method, hook=lambda _: None):
        service = self.owner(hook=hook).service()
        try: return getattr(service, method)()
        finally: service.close()

    def submit(self, key='inspect-1', **metadata):
        return self.peer.delegate(self.input['ref'], key, **metadata)

    def completed(self):
        job = self.submit()
        self.run_owner('work')
        return job

    def completion(self, **changes):
        result = self.atoms.create(Mutation(SCOPE, 'completion-result'), 'application/json', b'{}')
        body = dict(job_id='job-1', correlation_id='occurrence-1', causation_id='request-1', result=result, error=None)
        q = dict(profile=inspect.PROFILE, id=str(uuid.uuid4()), scope=SCOPE,
                 route='inspect-A', delivery_id='job-1', completion=body)
        q.update(changes)
        return q

    def test_configured_ports_keep_owner_files_and_explicit_grants_separate(self):
        execution, messaging = self.config('fusion-execution'), self.config('fusion-messaging')
        self.assertNotEqual(execution['database'], messaging['database'])
        self.assertNotIn('messages_database', execution)
        self.assertNotIn('atom_clients', messaging)
        atom = execution['atom_clients']['worker']
        self.assertEqual((atom['principal'], atom['scope']), ('inspect-worker', SCOPE))
        self.assertEqual(atom['endpoint']['host'], 'fusion-storage')
        self.assertEqual(execution['completion_port']['endpoint']['host'], 'fusion-messaging')
        self.assertEqual(messaging['principals']['worker']['scopes'][SCOPE], ['agent.messaging.accept'])
        self.assertEqual(set(execution['routes']), {'inspect-A', 'inspect-B'})
        for feature in ('memory', 'tasks'):
            settings = copy.deepcopy(self.settings)
            settings.update(role='fusion-execution')
            settings['preview'][feature]['enabled'] = False
            self.denied('UNSUPPORTED_PROFILE', configure.provider, settings, {}, self.root,
                        self.root, self.token, self.endpoint)

    def test_actual_inspection_persists_result_outbox_and_explicit_ack(self):
        job = self.submit()
        self.assertEqual(self.submit(), job)
        self.assertEqual(self.peer.status(job['job_id'])['execution'], 'queued')
        self.assertIsNone(self.peer.poll())
        self.run_owner('work')
        result = self.peer.result(job['job_id'])
        self.assertEqual(result['receipt']['provider'], 'contract-fixture-files/1')
        self.assertEqual(json.loads(self.atoms.get(result['ref']).bytes), dict(
            digest=digest(self.data), length=len(self.data), operation='inspect_atom', provider_version='0.1.0'))
        self.assertEqual(self.rows('fusion-execution', 'outbox')[0]['sent'], 0)
        self.assertEqual(self.run_owner('flush'), {'sent': 1, 'pending': 0})
        delivery = self.peer.poll()
        self.assertEqual(delivery['body']['result'], result)
        self.assertEqual(self.peer.poll(), delivery)
        self.assertEqual(self.rows('fusion-messaging', 'messages', mailbox=True)[0]['acknowledged'], 0)
        ack = self.peer.ack(delivery['delivery_id'], 'ack-inspect-1')
        self.assertEqual(self.peer.ack(delivery['delivery_id'], 'ack-inspect-1'), ack)
        self.assertIsNone(self.peer.poll())
        recovered = Peer(inspect.Client(self.client_path), SCOPE, 'inspect-A')
        self.assertEqual(recovered.result(job['job_id']), result)
        self.assertEqual(recovered.status(job['job_id'])['completion_delivery'], 'mailbox-accepted')
        self.assertEqual(len(self.rows('fusion-execution', 'jobs')), 1)

    def test_closed_request_descriptor_role_scope_and_operation(self):
        request = self.peer.request('execution', 'submit',
            {'ref': self.input['ref'], 'operation': 'inspect_atom'}, 'one', 'one')
        q = dict(profile=inspect.PROFILE, selection=registry.selection_token(self.client.selected['execution']), request=request)
        owner = self.owner()
        token = self.token('inspect-caller-A-token')
        self.denied('UNAUTHORIZED', owner.invoke, inspect.ROUTE, 'wrong-token', q)
        self.denied('UNSUPPORTED_PROFILE', owner.invoke, inspect.ROUTE, token, dict(q, selection='stale'))
        self.denied('UNSUPPORTED_OPERATION', owner.invoke, inspect.ROUTE, token, dict(q, extra=True))
        self.denied('UNAUTHORIZED', self.owner('fusion-messaging').invoke, inspect.ROUTE, token, q)
        bad = copy.deepcopy(q); bad['request']['body']['operation'] = 'evaluate-arbitrary-text'
        self.denied('UNSUPPORTED_OPERATION', owner.invoke, inspect.ROUTE, token, bad)
        bad = copy.deepcopy(q); bad['request']['scope_ref'] = 'synthetic-foreign'
        bad['request']['body']['ref']['scope_ref'] = 'synthetic-foreign'
        self.denied('UNAUTHORIZED', owner.invoke, inspect.ROUTE, token, bad)
        self.denied('UNSUPPORTED_OPERATION', self.peer.share, self.input['ref'], 'inspect-B', 'send')
        self.assertEqual(self.rows('fusion-execution', 'jobs'), [])

    def test_current_authority_blocks_duplicate_submit_and_saved_result(self):
        job = self.completed()
        self.revoke('fusion-execution', 'A', 'execution.submit')
        self.denied('UNAUTHORIZED', self.submit)
        self.assertEqual(self.peer.status(job['job_id'])['execution'], 'succeeded')
        self.revoke('fusion-execution', 'A', 'execution.result')
        self.denied('UNAUTHORIZED', self.peer.result, job['job_id'])
        request = self.peer.request('execution', 'status', {'job_id': job['job_id']})
        q = dict(profile=inspect.PROFILE, selection=registry.selection_token(self.client.selected['execution']), request=request)
        self.denied('NOT_FOUND', self.owner().invoke, inspect.ROUTE, self.token('inspect-caller-B-token'), q)

    def test_deadline_is_retained_and_expired_job_does_not_create_output(self):
        deadline = time.time_ns() // 1000000 + 60000
        job = self.submit(deadline_ms=deadline)
        self.assertEqual(json.loads(self.rows('fusion-execution', 'jobs')[0]['request'])['deadline_ms'], deadline)
        with patch('fusion.execution.time.time_ns', return_value=(deadline + 1) * 1000000):
            self.run_owner('work')
        status = self.peer.status(job['job_id'])
        self.assertEqual((status['execution'], status['error']), ('failed', 'DEADLINE_EXCEEDED'))
        self.assertEqual(self.atoms.head(SCOPE)['sequence'], 1)
        self.assertEqual(self.submit(deadline_ms=deadline), job)
        self.denied('CONFLICT', self.submit, deadline_ms=deadline + 1)

    def test_lost_acceptance_and_completion_reply_preserve_committed_jobs(self):
        deadline = time.time_ns() // 1000000 + 60000
        request = self.peer.request('execution', 'submit',
            {'ref': self.input['ref'], 'operation': 'inspect_atom'}, 'inspect-1', 'inspect-1',
            deadline_ms=deadline)
        q = dict(profile=inspect.PROFILE,
                 selection=registry.selection_token(self.client.selected['execution']), request=request)
        def interrupt_acceptance(stage):
            if stage == 'after_acceptance': raise RuntimeError('accepted before reply')
        with self.assertRaisesRegex(RuntimeError, 'accepted before reply'):
            self.owner(hook=interrupt_acceptance).invoke(inspect.ROUTE,
                self.token('inspect-caller-A-token'), q)
        saved = self.rows('fusion-execution', 'jobs')[0]
        job = self.submit(deadline_ms=deadline)
        self.assertEqual(job['job_id'], saved['id'])
        self.assertEqual(len(self.rows('fusion-execution', 'jobs')), 1)
        def interrupt_completion(stage):
            if stage == 'after_completion_commit': raise RuntimeError('completed before reply')
        with self.assertRaisesRegex(RuntimeError, 'completed before reply'):
            self.run_owner('work', interrupt_completion)
        self.assertEqual(self.peer.status(job['job_id'])['execution'], 'succeeded')
        self.assertEqual(len(self.rows('fusion-execution', 'outbox')), 1)
        self.assertEqual(self.rows('fusion-messaging', 'messages', mailbox=True), [])
        self.assertEqual(self.run_owner('work'), {'worked': False})
        self.assertEqual(self.atoms.head(SCOPE)['sequence'], 2)
        self.assertEqual(self.run_owner('flush'), {'sent': 1, 'pending': 0})
        self.assertEqual(json.loads(self.rows('fusion-execution', 'jobs')[0]['request'])['deadline_ms'], deadline)

    def test_result_commit_survives_execution_transaction_interruption(self):
        job = self.submit()
        def interrupt(stage):
            if stage == 'after_result_persist': raise RuntimeError('result boundary')
        with self.assertRaisesRegex(RuntimeError, 'result boundary'):
            self.run_owner('work', interrupt)
        self.assertEqual(self.peer.status(job['job_id'])['execution'], 'queued')
        self.assertEqual(self.atoms.head(SCOPE)['sequence'], 2)
        self.assertEqual(self.rows('fusion-execution', 'outbox'), [])
        self.run_owner('work')
        self.assertEqual(self.peer.status(job['job_id'])['execution'], 'succeeded')
        self.assertEqual(self.atoms.head(SCOPE)['sequence'], 2)
        self.assertEqual(len(self.rows('fusion-execution', 'outbox')), 1)

    def test_mailbox_acceptance_survives_outbox_transaction_interruption(self):
        job = self.completed()
        def interrupt(stage):
            if stage == 'after_delivery_accept': raise RuntimeError('mailbox boundary')
        with self.assertRaisesRegex(RuntimeError, 'mailbox boundary'):
            self.run_owner('flush', interrupt)
        self.assertEqual(self.rows('fusion-execution', 'outbox')[0]['sent'], 0)
        self.assertEqual(len(self.rows('fusion-messaging', 'messages', mailbox=True)), 1)
        self.assertEqual(self.peer.poll()['body']['job_id'], job['job_id'])
        self.run_owner('flush')
        self.assertEqual(self.rows('fusion-execution', 'outbox')[0]['sent'], 1)
        self.assertEqual(len(self.rows('fusion-messaging', 'messages', mailbox=True)), 1)

    def test_malformed_completion_receipt_does_not_mark_outbox_sent(self):
        self.completed()
        def corrupt(cfg, path, q, deadline=None):
            value = self.transport(cfg, path, q, deadline)
            if path == inspect.COMPLETION: value['value']['correlation_id'] = 'wrong-occurrence'
            return value
        with patch.object(inspect, 'invoke', side_effect=corrupt):
            self.assertEqual(self.run_owner('flush'), {'sent': 0, 'pending': 1})
        self.assertEqual(len(self.rows('fusion-messaging', 'messages', mailbox=True)), 1)
        self.assertEqual(self.run_owner('flush'), {'sent': 1, 'pending': 0})

    def test_completion_ingress_rejects_malformed_bodies_before_acceptance(self):
        base = self.completion()
        cases = [(str(value), dict(base, completion=value)) for value in (None, [], 'not-a-completion')]
        for field in ('job_id', 'correlation_id', 'causation_id', 'result', 'error'):
            bad = copy.deepcopy(base); del bad['completion'][field]; cases.append((field, bad))
        for name, changes in (
            ('wrong-job', {'job_id': 'another-job'}),
            ('foreign-ref', {'result': {**base['completion']['result'], 'ref': {**base['completion']['result']['ref'], 'scope_ref': 'synthetic-foreign'}}}),
            ('both-error-result', {'error': 'NOT_AVAILABLE'}),
            ('unknown-error', {'error': 'INVENTED', 'result': None}),
            ('extra-field', {'arbitrary_text': '(import! &self evil)'}),
        ):
            bad = copy.deepcopy(base); bad['completion'].update(changes); cases.append((name, bad))
        for name, q in cases:
            with self.subTest(name=name), self.assertRaises(ContractError):
                self.owner('fusion-messaging').invoke(inspect.COMPLETION, self.token('inspect-completion-token'), q)
            self.assertEqual(self.rows('fusion-messaging', 'messages', mailbox=True), [])

    def test_completion_ingress_rejects_invalid_envelope_fields(self):
        for field, value in (('id', []), ('id', ''), ('delivery_id', ''), ('route', 'inspect-unknown')):
            q = self.completion(**{field: value})
            with self.subTest(field=field, value=value), self.assertRaises(ContractError):
                self.owner('fusion-messaging').invoke(inspect.COMPLETION, self.token('inspect-completion-token'), q)
            self.assertEqual(self.rows('fusion-messaging', 'messages', mailbox=True), [])

    def test_completion_requires_worker_and_rechecks_revocation_after_acceptance(self):
        q = self.completion()
        self.denied('UNAUTHORIZED', self.owner('fusion-messaging').invoke, inspect.COMPLETION,
                    self.token('inspect-caller-A-token'), q)
        original = inspect.MessageOwner.accept
        def accept_then_revoke(owner, *args):
            result = original(owner, *args)
            self.revoke('fusion-messaging', 'worker', 'agent.messaging.accept')
            return result
        with patch.object(inspect.MessageOwner, 'accept', accept_then_revoke):
            self.denied('UNAUTHORIZED', self.owner('fusion-messaging').invoke, inspect.COMPLETION,
                        self.token('inspect-completion-token'), q)
        self.assertEqual(len(self.rows('fusion-messaging', 'messages', mailbox=True)), 1)

    def test_client_rejects_malformed_response_and_changed_placement(self):
        self.completed()
        for field, value in (('request_digest', '0' * 64), ('provider', 'wrong-provider'), ('ok', {})):
            def corrupt(cfg, path, q, deadline=None):
                result = self.transport(cfg, path, q, deadline)
                result[field] = value
                return result
            with self.subTest(field=field), patch.object(inspect, 'invoke', side_effect=corrupt):
                self.denied('NOT_AVAILABLE', self.peer.status, self.rows('fusion-execution', 'jobs')[0]['id'])
        cfg = json.loads(self.client_path.read_text())
        cfg['ports']['execution']['endpoint']['host'] = 'replacement-host'
        self.client_path.write_bytes(canonical(cfg))
        self.denied('CONFLICT', self.submit)


if __name__ == '__main__':
    unittest.main()
