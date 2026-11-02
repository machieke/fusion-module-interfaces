"""Original-deadline history delivery regressions, without native/network work.

Application and port transports are explicit fixtures; AtomStorage is the
FileFeedFixture and C1 is the real persistent SessionHistoryOwner. Interruption
uses a named hook exception, not a process kill. Network expiry exercises the
actual clients with TLS/socket construction mocked: no HTTPS service is started.
"""
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import uuid

from fusion.adapters.fixture_feed import FileFeedFixture
from fusion import cognitive_services
from fusion.contracts import ContractError, canonical
from fusion.ports import Mutation
from fusion.preview_history import SessionHistoryOwner
from fusion.preview_native_cognition import PreviewEvidence
from fusion.preview_native_history import NativeHistory
from fusion.preview_ports import Client, COMPOSITION, descriptor
from fusion.registry import descriptor_wire
from tests import test_phase2_native_relations as fixtures


SCOPE = fixtures.SCOPE
OBSERVED = fixtures.NOW
DEADLINE = OBSERVED + 120000


class InterruptedHistory(Exception):
    pass


class NativeHistoryDeadlineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='phase2-history-deadlines-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.atom_access = fixtures.AuthorityFixture('atom.storage')
        self.access = fixtures.AuthorityFixture('episodic.memory')
        self.atoms = FileFeedFixture(self.root/'fixture-atoms.json', self.atom_access)
        self.owner = SessionHistoryOwner(self.root/'history.sqlite', self.atoms, self.access)
        self.port = fixtures.DirectOwnerPort(self.owner, self.access)
        cfg = self.root/'atoms-fixture.json'
        cfg.write_bytes(canonical({'boundary': 'FILE_FEED_FIXTURE', 'credential': 'unused-synthetic'}))
        self.db = self.open_db()
        self.app = SimpleNamespace(db=self.db, preview_config={'scope': SCOPE},
            binding={'principal': 'A', 'history_atoms': {'boundary': 'FILE_FEED_FIXTURE'}},
            config={'history_atoms_config': str(cfg)}, session=str(uuid.uuid4()), hook=lambda _: None)
        self.history = NativeHistory(self.app, self.port)
        self.atom_deadlines = []

        def factory(config, *, deadline_ms):
            self.assertEqual(config['boundary'], 'FILE_FEED_FIXTURE')
            self.atom_deadlines.append(deadline_ms)
            return self.atoms

        self.factory = patch('fusion.preview_native_history.atom_client', side_effect=factory)
        self.factory.start()
        self.addCleanup(self.factory.stop)
        self.body = dict(observed_ms=OBSERVED, text='Generated synthetic input')

    def open_db(self):
        db = sqlite3.connect(self.root/'application-fixture.sqlite')
        db.row_factory = sqlite3.Row
        self.addCleanup(db.close)
        return db

    def error(self, code, callback, *args, **kwargs):
        with self.assertRaises(ContractError) as caught:
            callback(*args, **kwargs)
        self.assertEqual(caught.exception.code, code)

    def pending(self):
        return self.app.db.execute('SELECT * FROM preview_history_outbox').fetchone()

    def episode(self):
        return json.loads(self.app.db.execute('SELECT value FROM preview_history_episode').fetchone()[0])

    def interrupt_after_commit(self):
        def hook(stage):
            self.assertEqual(stage, 'after_history_provider_commit')
            raise InterruptedHistory()
        self.app.hook = hook
        with self.assertRaises(InterruptedHistory):
            self.history.record('input-one', 'input-receipt', self.body, deadline=DEADLINE)

    def test_original_deadline_and_logical_time_survive_commit_loss_and_reopen(self):
        self.interrupt_after_commit()
        original = self.pending()['intent']
        self.assertIsNone(self.pending()['receipt'])
        self.assertEqual(json.loads(original)['deadline'], DEADLINE)
        episode = self.episode()
        first = self.owner.historySnapshot(episode)
        self.assertEqual(first['through'], 1)
        atom_head = self.atoms.head(SCOPE)

        self.db.close()
        self.app.db = self.open_db()
        self.app.hook = lambda _: None
        reopened_owner = SessionHistoryOwner(self.root/'history.sqlite', self.atoms, self.access)
        reopened_port = fixtures.DirectOwnerPort(reopened_owner, self.access)
        reopened = NativeHistory(self.app, reopened_port)
        # A later wall clock must not replace the original accepted deadline.
        with patch('time.time_ns', return_value=(OBSERVED+90000)*1000000):
            reopened.drain(episode)
            reopened.record('input-one', 'input-receipt', self.body, deadline=DEADLINE)
        self.assertEqual(self.pending()['intent'], original)
        self.assertIsNotNone(self.pending()['receipt'])
        self.assertEqual(self.atom_deadlines, [DEADLINE, DEADLINE])
        appends = [call for port in (self.port, reopened_port) for call in port.calls if call[0] == 'appendHistory']
        self.assertEqual(len(appends), 2)
        self.assertEqual([call[2] for call in appends], [DEADLINE, DEADLINE])
        self.assertEqual(appends[0][1], appends[1][1])
        self.assertEqual(reopened_owner.historySnapshot(episode), first)
        self.assertEqual(self.atoms.head(SCOPE), atom_head)
        page = reopened_owner.readHistory(first, 1, 1)
        stamp = datetime.fromtimestamp(OBSERVED/1000, timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
        self.assertEqual(page['events'][0]['event']['event']['observed_time'], stamp)

    def test_changed_deadline_conflicts_for_pending_and_completed_occurrence(self):
        self.interrupt_after_commit()
        original = self.pending()['intent']
        atom_head = self.atoms.head(SCOPE)
        calls = len([call for call in self.port.calls if call[0] == 'appendHistory'])
        for delta in (-1, 1, 120000):
            self.error('CONFLICT', self.history.record, 'input-one', 'input-receipt', self.body,
                       deadline=DEADLINE+delta)
        self.assertEqual(self.pending()['intent'], original)
        self.assertEqual(len([call for call in self.port.calls if call[0] == 'appendHistory']), calls)
        self.assertEqual(self.atoms.head(SCOPE), atom_head)
        self.app.hook = lambda _: None
        self.history.drain(self.episode())
        receipt = self.pending()['receipt']
        self.error('CONFLICT', self.history.record, 'input-one', 'input-receipt', self.body,
                   deadline=DEADLINE+1)
        self.assertEqual(self.pending()['receipt'], receipt)

    def test_legacy_pending_intent_refused_before_atom_or_c1_mutation(self):
        episode = self.history.episode(DEADLINE)
        wire = canonical(dict(kind='input-receipt', body=self.body)).decode()
        with self.app.db:
            self.app.db.execute('INSERT INTO preview_history_outbox VALUES(1,?,?,NULL)', ('legacy-input', wire))
        before = tuple(self.pending())
        atom_head = self.atoms.head(SCOPE)
        for _ in range(2):
            self.error('UNSUPPORTED_PROFILE', self.history.drain, episode)
        self.assertEqual(tuple(self.pending()), before)
        self.assertEqual(self.atom_deadlines, [])
        self.assertEqual(self.owner.historySnapshot(episode)['through'], 0)
        self.assertEqual(self.atoms.head(SCOPE), atom_head)
        self.assertFalse(any(call[0] == 'appendHistory' for call in self.port.calls))

    def test_invalid_deadline_refused_before_outbox_or_owner_acceptance(self):
        for deadline in (None, True, str(DEADLINE), OBSERVED, OBSERVED-1):
            self.error('INVALID_ARGUMENT', self.history.record, 'input-one', 'input-receipt', self.body,
                       deadline=deadline)
        self.assertEqual(self.app.db.execute('SELECT count(*) FROM preview_history_outbox').fetchone()[0], 0)
        self.assertEqual(self.app.db.execute('SELECT count(*) FROM preview_history_episode').fetchone()[0], 0)
        self.assertEqual(self.port.calls, [])
        self.assertEqual(self.atom_deadlines, [])

    def test_expired_facet_network_deadline_refuses_before_request_and_outbox(self):
        ca = self.root/'ca.fixture'
        ca.write_text('TLS fixture: no TLS context or socket is constructed')
        config = dict(composition=COMPOSITION, placement='network', fallback=False,
            scope=SCOPE, principal='A', credential='synthetic-token',
            endpoint={'host': '127.0.0.1', 'port': 4443, 'ca_file': str(ca)},
            descriptors={'episodic.memory': descriptor_wire(descriptor('episodic.memory'))})
        path = self.root/'history-network-fixture.json'
        path.write_bytes(canonical(config))
        self.history.port = Client(path, 'episodic.memory')
        network = SimpleNamespace(endpoint=config['endpoint'], context=object())
        with patch('fusion.preview_transport.Network', return_value=network), \
             patch('fusion.preview_transport.http.client.HTTPSConnection') as connection, \
             patch('fusion.preview_transport.time.time_ns', return_value=DEADLINE*1000000):
            self.error('DEADLINE_EXCEEDED', self.history.record, 'input-one', 'input-receipt',
                       self.body, deadline=DEADLINE)
        connection.assert_not_called()
        self.assertEqual(self.app.db.execute('SELECT count(*) FROM preview_history_outbox').fetchone()[0], 0)
        self.assertEqual(self.app.db.execute('SELECT count(*) FROM preview_history_episode').fetchone()[0], 0)
        self.assertEqual(self.port.calls, [])
        self.assertEqual(self.atom_deadlines, [])

    def test_expired_atom_network_deadline_preserves_pending_intent_without_remote_effect(self):
        self.factory.stop()
        atom_config = dict(endpoint={'host': '127.0.0.1', 'port': 4443, 'ca_file': 'unused-fixture.pem'},
            credential='synthetic-token', principal='A', scope=SCOPE,
            descriptor=descriptor_wire(cognitive_services.descriptors()[0]), composition='typed-atom-feed-https/1')
        self.history.atom_path.write_bytes(canonical(atom_config))
        self.app.binding['history_atoms'] = self.history.atom_configuration()
        episode = self.history.episode(DEADLINE)
        atom_head = self.atoms.head(SCOPE)
        with patch('fusion.preview_client.ssl.create_default_context'), \
             patch('fusion.preview_client.http.client.HTTPSConnection') as connection, \
             patch('fusion.preview_client.time.time_ns', return_value=(DEADLINE+1)*1000000):
            self.error('DEADLINE_EXCEEDED', self.history.record, 'input-one', 'input-receipt',
                       self.body, deadline=DEADLINE)
            before = tuple(self.pending())
            self.error('DEADLINE_EXCEEDED', self.history.drain, episode)
        connection.assert_not_called()
        self.assertEqual(tuple(self.pending()), before)
        self.assertEqual(json.loads(self.pending()['intent'])['deadline'], DEADLINE)
        self.assertIsNone(self.pending()['receipt'])
        self.assertEqual(self.owner.historySnapshot(episode)['through'], 0)
        self.assertEqual(self.atoms.head(SCOPE), atom_head)
        self.assertFalse(any(call[0] == 'appendHistory' for call in self.port.calls))

    def test_native_input_model_and_command_records_use_authoritative_source_deadline(self):
        source = dict(occurrence='accepted-input', accepted=OBSERVED, deadline=DEADLINE,
                      payload={'text': 'Synthetic request'}, assignment='synthetic-task')
        self.app.preview = SimpleNamespace(input=SimpleNamespace(source=lambda: source))
        self.app.model = SimpleNamespace(row=lambda: dict(id='model-call', result='{"response":"synthetic"}'))
        self.app.db.executescript('''
            CREATE TABLE preview_native_inputs(turn INTEGER PRIMARY KEY, source TEXT);
            CREATE TABLE app_occurrences(id TEXT, turn INTEGER, position INTEGER, done INTEGER, result TEXT, premises TEXT);
        ''')
        with self.app.db:
            self.app.db.execute('INSERT INTO preview_native_inputs VALUES(7,?)', (canonical(source).decode(),))
            self.app.db.execute('INSERT INTO app_occurrences VALUES(?,7,0,1,?,?)',
                                ('command-one', 'captured-result', '{"operation":"query"}'))
        with patch.object(self.history, 'record') as record:
            self.history.input()
            self.history.model()
            self.history.commands(7)
            self.history.commands(7, results=True)
        self.assertEqual(record.call_count, 4)
        self.assertEqual([call.args[1] for call in record.call_args_list],
                         ['input-receipt', 'model-proposal', 'command-admitted', 'tool-result'])
        for call in record.call_args_list:
            self.assertEqual(call.kwargs, {'deadline': DEADLINE})
            self.assertEqual(call.args[2]['observed_ms'], OBSERVED)

    def test_evidence_source_history_uses_original_input_deadline(self):
        self.history.record('input-one', 'input-receipt', self.body, deadline=DEADLINE)
        evidence = json.loads(self.pending()['receipt'])['evidence']
        source = dict(occurrence='accepted-input', accepted=OBSERVED, deadline=DEADLINE)
        recorder = Mock()
        self.app.preview = SimpleNamespace(input=SimpleNamespace(source=lambda: source),
                                           history=SimpleNamespace(record=recorder))
        adapter = SimpleNamespace(app=self.app)
        self.assertEqual(PreviewEvidence.source_result(adapter, 'Synthetic observation', {}, {'evidence': evidence}),
                         'Synthetic observation')
        args, kwargs = recorder.call_args
        self.assertEqual(args[:2], ('accepted-input/source', 'external-observation'))
        self.assertEqual(args[2]['observed_ms'], OBSERVED)
        self.assertEqual(kwargs, {'deadline': DEADLINE})

    def test_external_effect_is_separate_causal_history_and_replay_keeps_one_event(self):
        source=dict(occurrence='accepted-input',accepted=OBSERVED,deadline=DEADLINE)
        self.history.record('delegation/result','tool-result',self.body,deadline=DEADLINE)
        ref=self.atoms.create(Mutation(SCOPE,'task-record'),'text/plain',b'Synthetic task')['ref']
        task=dict(id='delegation',kind='task',sender='A',recipient='B',deadline=DEADLINE-1000)
        receipt=dict(delivery_id='actual-owner-receipt-fixture',route='task-B')
        self.history.task_publication('task/delegation',task,ref,receipt,source)
        self.history.task_publication('task/delegation',task,ref,receipt,source)
        page=self.owner.readHistory(self.owner.historySnapshot(self.episode()),1,4)
        self.assertEqual([event['kind'] for event in page['events']],['tool-result','external-effect'])
        self.assertEqual(page['events'][1]['event']['event']['causation'],
                         [page['events'][0]['event']['evidence']['event_ref']])
        from fusion.preview_native_history import read_body
        body=read_body(self.atoms,page['events'][1]['payload'])['body']
        self.assertEqual(body['acceptance'],receipt)
        self.assertEqual(body['recipient_consumption'],'NOT_OBSERVED')
        self.assertFalse(body['independent_corroboration'])
        self.assertEqual(body['observed_ms'],OBSERVED)
        self.assertTrue(all(event['event']['event']['numerical'] is None for event in page['events']))
        intent=json.loads(self.db.execute('SELECT intent FROM preview_history_outbox WHERE identity=?',
            ('task/delegation/external-effect',)).fetchone()[0])
        self.assertEqual(intent['deadline'],DEADLINE-1000)
        self.error('CONFLICT',self.history.task_publication,'task/delegation',
            dict(task,deadline=DEADLINE+1),ref,receipt,source)

    def test_external_effect_delivery_reconciles_its_original_owner_commit(self):
        source=dict(occurrence='accepted-input',accepted=OBSERVED,deadline=DEADLINE)
        ref=self.atoms.create(Mutation(SCOPE,'task-record'),'text/plain',b'Synthetic task')['ref']
        task=dict(id='delegation',kind='task',sender='A',recipient='B',deadline=DEADLINE)
        receipt=dict(delivery_id='actual-owner-receipt-fixture',route='task-B')
        self.app.hook=lambda stage: (_ for _ in ()).throw(InterruptedHistory())
        with self.assertRaises(InterruptedHistory):
            self.history.task_publication('task/delegation',task,ref,receipt,source)
        before=self.owner.historySnapshot(self.episode())
        intent=self.pending()['intent']
        self.app.hook=lambda stage:None
        self.history.task_publication('task/delegation',task,ref,receipt,source)
        self.assertEqual(self.owner.historySnapshot(self.episode()),before)
        self.assertEqual(self.pending()['intent'],intent)
        self.assertIsNotNone(self.pending()['receipt'])

    def test_command_result_uses_captured_publication_not_recipient_hint_or_result_text(self):
        from fusion.preview_application import APPLICATION
        source=dict(occurrence='input-one',accepted=OBSERVED,deadline=DEADLINE)
        task=dict(id='command-one',kind='task',sender='A',recipient='B',deadline=DEADLINE)
        ref=self.atoms.create(Mutation(SCOPE,'task-record'),'text/plain',b'Synthetic task')['ref']
        receipt=dict(delivery_id='actual-owner-receipt-fixture',route='task-B')
        self.db.executescript('''
            CREATE TABLE preview_native_inputs(turn INTEGER PRIMARY KEY, source TEXT);
            CREATE TABLE app_occurrences(id TEXT, turn INTEGER, position INTEGER, done INTEGER, result TEXT, premises TEXT);
            CREATE TABLE preview_task_outbox(id TEXT,record TEXT,ref TEXT,receipt TEXT);
        ''')
        with self.db:
            self.db.execute('INSERT INTO preview_native_inputs VALUES(7,?)',(canonical(source).decode(),))
            self.db.execute('INSERT INTO app_occurrences VALUES(?,7,0,1,?,?)',('command-one',
                'Tool representation is not a mailbox receipt',canonical(dict(profile=APPLICATION,operation='delegate')).decode()))
            self.db.execute('INSERT INTO preview_task_outbox VALUES(?,?,?,?)',
                ('task/command-one',canonical(task).decode(),canonical(ref).decode(),canonical(receipt).decode()))
        self.history.commands(7,results=True)
        page=self.owner.readHistory(self.owner.historySnapshot(self.episode()),1,4)
        self.assertEqual([event['kind'] for event in page['events']],['tool-result','external-effect'])
        from fusion.preview_native_history import read_body
        self.assertEqual(read_body(self.atoms,page['events'][1]['payload'])['body']['acceptance'],receipt)
        self.history.commands(7,results=True)
        self.assertEqual(self.owner.historySnapshot(self.episode())['through'],2)


if __name__ == '__main__':
    unittest.main()
