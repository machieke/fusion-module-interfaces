"""Task handoff over real Messaging/SessionStore owners, with explicit fixtures.

AtomStorage is FileFeedFixture; view metadata and in-process transport are
fixtures. No Search, native runtime, HTTPS, cluster, or process-kill claim is
made. Hook exceptions and journal reopening exercise independent commits.
"""
import copy
import json
from pathlib import Path
import sqlite3
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import uuid

from fusion.adapters.fixture_feed import FileFeedFixture
from fusion.contracts import ContractError, canonical, digest, require
from fusion.lookup_contracts import make_head
from fusion.ports import Mutation
from fusion.preview_native_history import write_body
from fusion.preview_native_tasks import NativeTasks
from fusion.preview_sessions import SessionStore
from fusion.preview_tasks import Client, Ports, PROFILE, correlated, descriptor, record
from fusion.preview_lifecycle import PROFILE as LIFECYCLE
from fusion import preview_vector_contracts as active, vector_contracts as vector
from fusion.registry import descriptor_wire
from integration.single_node.preview_task_ingress import Ingress


SCOPE = 'synthetic-phase2-task-tests'
NOW = 1793620800000


class AtomAuthorityFixture:
    def authorize(self, scope, operation):
        require(scope == SCOPE, 'UNAUTHORIZED')
        return 'synthetic-fixture-writer'


class TaskHandoffTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='phase2-task-tests-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.now = NOW
        for target, clock in (('time.time_ns', lambda: self.now * 1000000),
                              ('time.time', lambda: self.now / 1000)):
            item = patch(target, side_effect=clock)
            item.start(); self.addCleanup(item.stop)
        self.atoms = FileFeedFixture(self.root/'fixture-atoms.json', AtomAuthorityFixture())
        self.sessions = {who: str(uuid.uuid4()) for who in ('A', 'B')}
        self.path = self.root/'messaging-policy.json'
        operations = ['tasks.'+op for op in ('authorize', 'send', 'published', 'poll', 'ack')]
        operations += ['agent.messaging.'+op for op in ('send', 'poll', 'ack')]
        self.policy = dict(profile=PROFILE, scope=SCOPE, capacity=8,
            messages_database=str(self.root/'messages.sqlite'),
            principals={who: dict(credential='synthetic-'+who, scopes={SCOPE: operations[:]}) for who in ('A', 'B')},
            routes={f'task-{who}': dict(scope=SCOPE, owner=who) for who in ('A', 'B')},
            inboxes={who: 'task-'+who for who in ('A', 'B')},
            sessions={who: [self.sessions[who]] for who in ('A', 'B')})
        self.save_policy()
        self.ports = Ports(self.path, atoms_for=lambda principal: self.atoms)
        self.calls, self.transform = [], lambda operation, reply: reply

        def transport(cfg, route, request, deadline=None):
            self.calls.append(copy.deepcopy(request))
            reply = self.ports.invoke(cfg['credential'], request)
            return self.transform(request['operation'], reply)

        selected = patch('fusion.preview_transport.invoke', side_effect=transport)
        selected.start(); self.addCleanup(selected.stop)
        selected = patch('integration.single_node.preview_task_ingress.atoms_client', return_value=self.atoms)
        selected.start(); self.addCleanup(selected.stop)
        ca = self.root/'fixture-ca.pem'; ca.write_text('EXPLICIT IN-PROCESS TRANSPORT FIXTURE')
        self.clients = {}
        for who in ('A', 'B'):
            path = self.root/f'client-{who}.json'
            path.write_bytes(canonical(dict(profile=PROFILE, fallback=False, descriptor=descriptor_wire(descriptor()),
                principal=who, scope=SCOPE, credential='synthetic-'+who,
                endpoint=dict(url='https://unused.invalid', ca_file=str(ca)))))
            self.clients[who] = Client(path)
        self.binding = dict(catalogue='explicit-fixture-catalogue', policy='explicit-fixture-policy',
            model_boundary='RECORDED_FIXTURE', limits=dict(inputs=8, pending=4, timeout_ms=30000))
        self.configs = {}
        self.wakes = []
        for who in ('A', 'B'):
            cfg = dict(principals={'worker': dict(credential='synthetic-worker', scopes={SCOPE: ['tasks.ingress']})},
                task_ingress=dict(database=str(self.root/f'ingress-{who}.sqlite'), scope=SCOPE, principal=who,
                    session=self.sessions[who], peers=[other for other in ('A', 'B') if other != who],
                    client=str(self.clients[who].path), atoms={'boundary': 'FILE_FEED_FIXTURE'}),
                native_sessions=dict(database=str(self.root/f'sessions-{who}.sqlite'),
                    session_templates={self.sessions[who]: self.binding}))
            path = self.root/f'ingress-{who}.json'; path.write_bytes(canonical(cfg)); self.configs[who] = path
        self.minimum = dict(generation=str(uuid.uuid4()),
            head=make_head(str(uuid.uuid4()), SCOPE, 3), corpus='generated-task-corpus',
            embedding=vector.FIXTURE, index=vector.INDEX, profile=active.PROFILE,
            lifecycle=make_head(str(uuid.uuid4()), SCOPE, 2, LIFECYCLE), active_digest='a'*64)
        self.rehash(self.minimum)
        active.snapshot(self.minimum, SCOPE)

    @staticmethod
    def rehash(view):
        view['logical'] = digest(canonical({k: value for k, value in view.items() if k not in ('generation', 'logical')}))
        return view

    def save_policy(self): self.path.write_bytes(canonical(self.policy))

    def error(self, callback, *args, code=None, **kwargs):
        with self.assertRaises(ContractError) as caught: callback(*args, **kwargs)
        if code is not None: self.assertEqual(caught.exception.code, code)

    def task(self, **updates):
        return dict(dict(profile=PROFILE, kind='task', scope=SCOPE, id=str(uuid.uuid4()), sender='A', recipient='B',
            session=self.sessions['A'], deadline=NOW+20000, parent='accepted-parent-occurrence',
            limits=dict(queries=1, relay_calls=24, recursive_delegation=False),
            query='synthetic archive marker', minimum=copy.deepcopy(self.minimum)), **updates)

    def result(self, request, ref, **updates):
        return dict(dict(profile=PROFILE, kind='result', scope=SCOPE, id=request['id'], sender='B', recipient='A',
            session=self.sessions['B'], deadline=request['deadline'], parent=request['parent'], limits=copy.deepcopy(request['limits']),
            task=ref, view=copy.deepcopy(self.minimum), projection='Captured native query fixture projection',
            payloads=[], status='captured-native-query'), **updates)

    def persist(self, body):
        return write_body(self.atoms, SCOPE, 'record/'+str(uuid.uuid4()), canonical(dict(body=body)))['ref']

    def send(self, body, ref=None, who=None):
        ref = ref or self.persist(body)
        receipt = self.clients[who or body['sender']].call('send', body['kind']+'/'+body['id'], ref,
            body['recipient'], body['deadline'], body['id'])
        return ref, receipt

    def published(self, body, ref, who=None):
        return self.clients[who or body['sender']].call('published', body['kind']+'/'+body['id'], ref,
            body['recipient'], body['deadline'], body['id'])

    def mailbox_rows(self):
        with sqlite3.connect(self.policy['messages_database']) as db:
            return db.execute('SELECT * FROM messages ORDER BY seq').fetchall()

    def native_outbox_fixture(self, hook=lambda _: None):
        """Real outbox methods; explicit application/atom composition fixture."""
        db = sqlite3.connect(self.root/'application-outbox-fixture.sqlite')
        db.row_factory = sqlite3.Row; self.addCleanup(db.close)
        app = SimpleNamespace(db=db, config={'task_config': str(self.clients['A'].path)},
            binding={'tasks': self.clients['A'].frozen}, preview_config={'scope': SCOPE}, hook=hook,
            preview=SimpleNamespace(authorize=lambda operation: require(operation == 'tasks', 'UNAUTHORIZED'),
                memory=SimpleNamespace(atoms=lambda deadline=None: self.atoms)))
        return app, NativeTasks(app)

    def task_complete_fixture(self):
        """Committed-row fixture, using Application.intent's real query naming."""
        from fusion.neoclaw_application import Application
        app, native = self.native_outbox_fixture()
        app.session = self.sessions['B']
        app.config['memory_read_config'] = 'explicit-configuration-fixture'
        app.binding['memory'] = {'fixture': 'selected-memory-profile'}
        app.preview.intent = lambda command: None
        app.channel_enabled = app.priority_enabled = app.evidence_enabled = app.two_operations = False
        app.memory_enabled = True
        app.memory = SimpleNamespace(c=active, authorize=Mock())
        view = dict(snapshot=copy.deepcopy(self.minimum))
        app.write = SimpleNamespace(view_for=Mock(return_value=view))
        task = self.task(); task_ref = self.persist(task)
        with patch('fusion.neoclaw_memory.configuration', return_value=(
                {'queries': [task['query']]}, {}, app.binding['memory'])):
            intent = Application.intent(app, ['query', task['query']])
        occurrence = str(uuid.uuid4())
        projection = '[["generated-memory", "captured Ω projection fixture"]]'
        payloads = []
        hits = []
        for number in range(2):
            memory_id = str(uuid.uuid4())
            body = dict(scope=SCOPE, corpus=self.minimum['corpus'], uuid=memory_id,
                time='2026-11-02 12:00:00', content='Synthetic memory '+str(number))
            ref = self.atoms.create(Mutation(SCOPE, 'query-payload-'+str(number)), vector.PAYLOAD, canonical(body))['ref']
            hits.append(dict(ref=ref, uuid=memory_id, distance=float(number)))
            payloads.append([memory_id, body['time'], body['content'], float(number)])
        candidates = dict(request_id=occurrence, request_digest='d'*64, snapshot=copy.deepcopy(self.minimum),
            hits=hits, top_k=2, exhaustive=False)
        app.db.executescript('''
            CREATE TABLE app_occurrences(turn INTEGER NOT NULL,position INTEGER NOT NULL,id TEXT UNIQUE NOT NULL,
                premises TEXT,deadline INTEGER NOT NULL,result TEXT,done INTEGER NOT NULL DEFAULT 0,PRIMARY KEY(turn,position));
            CREATE TABLE app_memory_reads(id TEXT PRIMARY KEY,request TEXT NOT NULL,calls INTEGER NOT NULL DEFAULT 0,
                queries INTEGER NOT NULL DEFAULT 0,candidates TEXT,payloads TEXT,enrichment REAL);
        ''')
        with app.db:
            app.db.execute('INSERT INTO app_occurrences VALUES(?,?,?,?,?,?,?)',
                (7, 1, occurrence, canonical(intent).decode(), task['deadline'], projection, 1))
            app.db.execute('INSERT INTO app_memory_reads(id,request,candidates,payloads) VALUES(?,?,?,?)',
                (occurrence, canonical({'boundary': 'FIXTURE_REQUEST'}).decode(),
                 canonical(candidates).decode(), canonical(payloads).decode()))
        native.publish = Mock()
        return SimpleNamespace(app=app, native=native, task=task, task_ref=task_ref, occurrence=occurrence,
            projection=projection, candidates=candidates, view=view, intent=intent,
            input_row=dict(turn=7, source=canonical(dict(task_origin=dict(record=task, ref=task_ref))).decode()))

    def task_report_fixture(self):
        """Explicit consumed-input/outbox fixtures; real report/input methods."""
        app, native = self.native_outbox_fixture(); app.binding['principal'] = 'A'
        task = self.task(); task_ref = self.persist(task)
        payload = self.atoms.create(Mutation(SCOPE, 'report-payload'), 'text/plain', b'Synthetic reported data')['ref']
        body = self.result(task, task_ref, payloads=[payload]); result_ref = self.persist(body)
        origin = dict(record=body, ref=result_ref)
        source = dict(occurrence=str(uuid.uuid4()), task_origin=origin)
        current = dict(snapshot=copy.deepcopy(self.minimum),
            handles={'fixture-handle': dict(envelope=dict(target=dict(payload=payload)))})
        app.preview.input = SimpleNamespace(source=Mock(return_value=source))
        app.preview.memory = SimpleNamespace(atoms=lambda deadline=None: self.atoms,
            input=Mock(return_value=current), call=Mock(return_value={'authorized': True}))
        app.db.executescript('''CREATE TABLE preview_native_inputs(turn INTEGER PRIMARY KEY,source TEXT,acknowledged INTEGER);
            CREATE TABLE app_turns(id INTEGER PRIMARY KEY,projection TEXT);''')
        with app.db:
            app.db.execute('INSERT INTO preview_native_inputs VALUES(?,?,1)', (3, canonical(source).decode()))
            app.db.execute('INSERT INTO app_turns VALUES(3,?)', ('committed native context fixture',))
            app.db.execute('INSERT INTO preview_task_outbox(id,record,ref) VALUES(?,?,?)',
                ('task/'+task['id'], canonical(task).decode(), canonical(task_ref).decode()))
        return SimpleNamespace(app=app, native=native, task=task, task_ref=task_ref, payload=payload,
            body=body, origin=origin, source=source, view=current)

    def ingress(self, who='B', hook=lambda _: None):
        return Ingress(self.configs[who], lambda sid: self.wakes.append(sid), hook)

    def row(self, who='B'):
        with sqlite3.connect(self.root/f'ingress-{who}.sqlite') as db:
            db.row_factory = sqlite3.Row
            return dict(db.execute('SELECT * FROM task_ingress').fetchone())

    def spent(self, who='B'):
        with sqlite3.connect(self.root/f'ingress-{who}.sqlite') as db:
            return db.execute('SELECT calls FROM ingress_limits').fetchone()[0]

    def store(self, who='B'):
        def authorize(principal, scope, operation): require(principal == who and scope == SCOPE, 'UNAUTHORIZED')
        return SessionStore(self.root/f'sessions-{who}.sqlite', authorize)

    @staticmethod
    def interrupt(at):
        def hook(stage):
            if stage == at: raise RuntimeError('explicit interruption fixture: '+at)
        return hook

    def test_exact_envelope_rejects_malformed_id_scope_query_and_unselected_fields(self):
        for key, value in [('profile', 'other/1'), ('scope', 'private-memory'), ('id', 'not-a-uuid'),
                           ('session', 123), ('deadline', True), ('kind', 'execute'), ('sender', 'C'),
                           ('query', 'do\nmore'), ('query', 'quote\"escape'), ('query', 'zero\u200bwidth'),
                           ('query', 'x'*513), ('extra', 'arbitrary-function')]:
            with self.subTest(key=key, value=value): self.error(record, self.task(**{key: value}), SCOPE)

    def test_limits_reject_boolean_integer_aliases(self):
        for key, value in [('queries', True), ('relay_calls', 24.0), ('recursive_delegation', 0)]:
            body = self.task(); body['limits'][key] = value
            with self.subTest(key=key): self.error(record, body, SCOPE)

    def test_wrong_actor_recipient_session_or_correlation_never_publishes(self):
        body = self.task(); ref = self.persist(body)
        self.error(self.send, body, ref, 'B', code='UNAUTHORIZED')
        for position, value in ((2, 'A'), (3, body['deadline']+1), (4, str(uuid.uuid4()))):
            args = ['task/'+body['id'], ref, 'B', body['deadline'], body['id']]; args[position] = value
            self.error(self.clients['A'].call, 'send', *args, code='UNAUTHORIZED')
        self.error(self.send, self.task(session=self.sessions['B']), code='UNAUTHORIZED')
        self.assertIsNone(self.clients['B'].call('poll'))

    def test_result_requires_actual_task_publication_and_accessible_payloads(self):
        task = self.task(); task_ref = self.persist(task); result = self.result(task, task_ref)
        ref = self.persist(result)
        self.error(self.send, result, ref, code='UNAUTHORIZED')
        self.send(task, task_ref)
        result['payloads'] = [dict(scope_ref=SCOPE, id='missing', revision=1, digest='b'*64)]
        self.error(self.send, result, code='NOT_FOUND')
        result['payloads'] = [self.atoms.create(Mutation(SCOPE, 'visible-payload'), 'text/plain', b'Synthetic result')['ref']]
        _, receipt = self.send(result)
        self.assertEqual(receipt['route'], 'task-A')

    def test_result_correlation_and_source_freshness_are_independent(self):
        task = self.task(); ref = self.persist(task)
        for key, value in [('id', str(uuid.uuid4())), ('parent', 'other-occurrence'), ('deadline', task['deadline']+1),
                           ('sender', 'A'), ('task', dict(ref, id='other'))]:
            with self.subTest(key=key): self.error(correlated, self.result(task, ref, **{key: value}), task, ref, code='UNAUTHORIZED')
        for field, key, value in [('head', 'sequence', 2), ('lifecycle', 'sequence', 1),
                                   ('head', 'source', str(uuid.uuid4())), ('lifecycle', 'source', str(uuid.uuid4()))]:
            result = self.result(task, ref); result['view'][field][key] = value; self.rehash(result['view'])
            record(result, SCOPE)
            with self.subTest(field=field, key=key): self.error(correlated, result, task, ref, code='NOT_AVAILABLE')
        result = self.result(task, ref); result['view']['head']['sequence'] += 1; self.rehash(result['view'])
        correlated(record(result, SCOPE), task, ref)
        result['view']['corpus'] = 'other-corpus'; self.rehash(result['view'])
        self.error(correlated, result, task, ref, code='NOT_AVAILABLE')

    def test_lost_send_reply_replays_one_mailbox_occurrence_under_current_authority(self):
        body = self.task(); ref = self.persist(body)
        self.ports.hook = self.interrupt('after_task_mailbox_accept')
        with self.assertRaises(RuntimeError): self.send(body, ref)
        self.ports = Ports(self.path, atoms_for=lambda principal: self.atoms)
        _, receipt = self.send(body, ref)
        delivery = self.clients['B'].call('poll')
        self.assertEqual(delivery['delivery_id'], receipt['delivery_id'])
        self.assertEqual(delivery['order'], 1)
        self.policy['principals']['A']['scopes'][SCOPE].remove('tasks.send'); self.save_policy()
        self.error(self.send, body, ref, code='UNAUTHORIZED')

    def test_expired_published_recovers_existing_acceptance_without_fingerprint_or_ack_change(self):
        body = self.task(); ref, accepted = self.send(body)
        self.clients['B'].call('ack', 'recipient-ack', accepted['delivery_id'])
        before = self.mailbox_rows()
        self.now = body['deadline']+1
        self.ports = Ports(self.path, atoms_for=lambda principal: self.atoms)
        self.assertEqual(self.published(body, ref), accepted)
        self.assertEqual(self.published(body, ref), accepted)
        self.assertEqual(self.mailbox_rows(), before)
        self.assertIsNone(self.clients['B'].call('poll'))
        self.error(self.send, body, ref, code='DEADLINE_EXCEEDED')

    def test_expired_absent_publication_never_calls_send_or_creates_message(self):
        body = self.task(); ref = self.persist(body)
        self.now = body['deadline']+1
        with patch('fusion.preview_tasks.MessagingSession.send', side_effect=AssertionError('observation may not send')) as send:
            self.assertIsNone(self.published(body, ref))
            self.assertIsNone(self.published(body, ref))
            send.assert_not_called()
        self.assertEqual(self.mailbox_rows(), [])
        self.assertIsNone(self.clients['B'].call('poll'))

    def test_expired_publication_conflict_cannot_replace_original_message(self):
        body = self.task(); ref, _ = self.send(body)
        before = self.mailbox_rows()
        changed = dict(body, query='different synthetic archive marker'); changed_ref = self.persist(changed)
        self.now = body['deadline']+1
        self.error(self.published, changed, changed_ref, code='CONFLICT')
        changed = dict(body, deadline=body['deadline']+5000)
        self.error(self.published, changed, ref, code='UNAUTHORIZED')
        self.assertEqual(self.mailbox_rows(), before)

    def test_expired_publication_requires_current_observation_and_send_authority(self):
        body = self.task(); ref, _ = self.send(body)
        before = self.mailbox_rows(); self.now = body['deadline']+1
        for permission in ('tasks.published', 'agent.messaging.send'):
            self.policy['principals']['A']['scopes'][SCOPE].remove(permission); self.save_policy()
            with self.subTest(permission=permission): self.error(self.published, body, ref, code='UNAUTHORIZED')
            self.policy['principals']['A']['scopes'][SCOPE].append(permission); self.save_policy()
        self.error(self.published, body, ref, 'B', code='UNAUTHORIZED')
        self.assertEqual(self.mailbox_rows(), before)

    def test_expired_result_publication_retains_original_task_binding_and_acceptance(self):
        task = self.task(); task_ref, _ = self.send(task)
        body = self.result(task, task_ref); ref, accepted = self.send(body)
        before = self.mailbox_rows(); self.now = task['deadline']+1
        self.assertEqual(self.published(body, ref), accepted)
        self.assertEqual(self.mailbox_rows(), before)

    def test_native_outbox_lost_acceptance_recovers_after_expiry_without_another_send(self):
        body = self.task(); app, outbox = self.native_outbox_fixture()
        self.ports.hook = self.interrupt('after_task_mailbox_accept')
        with self.assertRaises(RuntimeError): outbox.publish(body)
        row = app.db.execute('SELECT * FROM preview_task_outbox').fetchone()
        self.assertEqual(row['calls'], 3); self.assertIsNone(row['receipt']); self.assertIsNotNone(row['ref'])
        before = self.mailbox_rows(); self.now = body['deadline']+1
        self.ports = Ports(self.path, atoms_for=lambda principal: self.atoms)
        result = NativeTasks(app).publish(body)
        self.assertEqual(result['status'], 'TASK_PUBLISHED'); self.assertEqual(result['deadline'], body['deadline'])
        self.assertEqual(result['recipient_observation']['code'], 'DEADLINE_EXCEEDED')
        self.assertTrue(result['recipient_observation']['mailbox_acceptance_retained'])
        self.assertEqual(app.db.execute('SELECT calls FROM preview_task_outbox').fetchone()[0], 4)
        self.assertEqual(sum(request['operation'] == 'send' for request in self.calls), 1)
        self.assertEqual(self.mailbox_rows(), before)
        self.assertEqual(NativeTasks(app).publish(body), result)
        self.assertEqual(app.db.execute('SELECT calls FROM preview_task_outbox').fetchone()[0], 4)

    def test_native_outbox_expired_missing_publication_spends_observation_and_never_sends(self):
        body = self.task(); app, outbox = self.native_outbox_fixture(self.interrupt('after_task_payload_capture'))
        with self.assertRaises(RuntimeError): outbox.publish(body)
        self.now = body['deadline']+1; app.hook = lambda _: None
        self.error(NativeTasks(app).publish, body, code='DEADLINE_EXCEEDED')
        self.assertEqual(app.db.execute('SELECT calls FROM preview_task_outbox').fetchone()[0], 2)
        self.assertEqual(self.mailbox_rows(), [])
        self.assertFalse(any(request['operation'] == 'send' for request in self.calls))
        # Explicit exhausted-budget setup in this application's own fixture DB.
        with app.db: app.db.execute('UPDATE preview_task_outbox SET calls=24')
        before = len([request for request in self.calls if request['operation'] == 'published'])
        self.error(NativeTasks(app).publish, body, code='OVERLOADED')
        self.assertEqual(app.db.execute('SELECT calls FROM preview_task_outbox').fetchone()[0], 24)
        self.assertEqual(len([request for request in self.calls if request['operation'] == 'published']), before)

    def test_complete_uses_actual_application_query_intent_and_exact_committed_result_view_refs(self):
        fixture = self.task_complete_fixture()
        self.assertEqual(fixture.intent, dict(profile=active.PROFILE, operation='query_with_ids_and_dists',
            arguments=dict(query=fixture.task['query'])))
        self.assertIsNone(fixture.native.complete(fixture.input_row))
        fixture.native.publish.assert_called_once()
        result = fixture.native.publish.call_args.args[0]
        self.assertEqual(result, self.result(fixture.task, fixture.task_ref,
            view=fixture.view['snapshot'], projection=fixture.projection,
            payloads=[hit['ref'] for hit in fixture.candidates['hits']]))
        self.assertEqual(result['projection'].encode(), fixture.projection.encode())
        self.assertEqual(fixture.app.write.view_for.call_args.args[0]['id'], fixture.occurrence)
        self.assertEqual(fixture.app.memory.authorize.call_args.args[0]['id'], fixture.occurrence)
        record(result, SCOPE)

    def test_complete_refuses_incomplete_or_uncaptured_occurrence(self):
        fixture = self.task_complete_fixture()
        for changes in (dict(done=0), dict(result=None)):
            with fixture.app.db:
                fixture.app.db.execute('UPDATE app_occurrences SET done=?,result=?',
                    (changes.get('done', 1), changes.get('result', fixture.projection)))
            with self.subTest(changes=changes): self.error(fixture.native.complete, fixture.input_row, code='NOT_AVAILABLE')
        fixture.native.publish.assert_not_called()
        fixture.app.write.view_for.assert_not_called()

    def test_complete_refuses_missing_payload_capture_or_missing_read_row(self):
        fixture = self.task_complete_fixture()
        with fixture.app.db: fixture.app.db.execute('UPDATE app_memory_reads SET payloads=NULL')
        self.error(fixture.native.complete, fixture.input_row, code='NOT_AVAILABLE')
        with fixture.app.db: fixture.app.db.execute('DELETE FROM app_memory_reads')
        self.error(fixture.native.complete, fixture.input_row, code='NOT_AVAILABLE')
        fixture.native.publish.assert_not_called()

    def test_complete_refuses_wrong_operation_profile_and_query_text(self):
        fixture = self.task_complete_fixture()
        cases = [dict(fixture.intent, operation='query'), dict(fixture.intent, operation='arbitrary-evaluation'),
            dict(fixture.intent, profile=vector.PROFILE),
            dict(fixture.intent, arguments=dict(query='different synthetic query'))]
        for intent in cases:
            with fixture.app.db: fixture.app.db.execute('UPDATE app_occurrences SET premises=?', (canonical(intent).decode(),))
            with self.subTest(intent=intent): self.error(fixture.native.complete, fixture.input_row, code='UNAUTHORIZED')
        fixture.native.publish.assert_not_called(); fixture.app.write.view_for.assert_not_called()

    def test_complete_refuses_multiple_occurrences_or_revoked_memory_authority(self):
        fixture = self.task_complete_fixture()
        fixture.app.memory.authorize.side_effect = ContractError('UNAUTHORIZED')
        self.error(fixture.native.complete, fixture.input_row, code='UNAUTHORIZED')
        fixture.app.memory.authorize.side_effect = None
        with fixture.app.db:
            fixture.app.db.execute('INSERT INTO app_occurrences VALUES(?,?,?,?,?,?,?)',
                (7, 2, str(uuid.uuid4()), canonical(fixture.intent).decode(), fixture.task['deadline'], fixture.projection, 1))
        self.error(fixture.native.complete, fixture.input_row, code='NOT_AVAILABLE')
        fixture.native.publish.assert_not_called()

    def test_report_and_result_input_recheck_current_search_authority_and_visibility(self):
        fixture = self.task_report_fixture()
        self.assertEqual(fixture.native.report(fixture.task['id']), dict(origin=fixture.origin, task=fixture.task))
        fixture.native.input()
        expected = ('input-'+fixture.source['occurrence'], 'search', 'authorize', fixture.task['query'], fixture.view['snapshot'])
        self.assertEqual(fixture.app.preview.memory.call.call_count, 2)
        for call in fixture.app.preview.memory.call.call_args_list:
            self.assertEqual(call.args, expected); self.assertEqual(call.kwargs, {'bounded': False})
        fixture.app.preview.memory.call.side_effect = ContractError('UNAUTHORIZED')
        self.error(fixture.native.report, fixture.task['id'], code='UNAUTHORIZED')
        self.error(fixture.native.input, code='UNAUTHORIZED')
        fixture.app.preview.memory.call.side_effect = None
        fixture.view['handles'] = {}
        self.error(fixture.native.report, fixture.task['id'], code='UNAUTHORIZED')
        self.error(fixture.native.input, code='UNAUTHORIZED')

    def test_report_requires_exactly_one_acknowledged_completed_input(self):
        fixture = self.task_report_fixture()
        with fixture.app.db: fixture.app.db.execute('UPDATE preview_native_inputs SET acknowledged=0')
        self.error(fixture.native.report, fixture.task['id'], code='NOT_FOUND')
        with fixture.app.db:
            fixture.app.db.execute('UPDATE preview_native_inputs SET acknowledged=1')
            fixture.app.db.execute('UPDATE app_turns SET projection=NULL')
        self.error(fixture.native.report, fixture.task['id'], code='NOT_FOUND')
        with fixture.app.db:
            fixture.app.db.execute("UPDATE app_turns SET projection='committed fixture'")
            fixture.app.db.execute('INSERT INTO app_turns VALUES(4,?)', ('another committed fixture',))
            fixture.app.db.execute('INSERT INTO preview_native_inputs VALUES(?,?,1)', (4, canonical(fixture.source).decode()))
        self.error(fixture.native.report, fixture.task['id'], code='CONFLICT')

    def test_report_checks_current_task_permission_and_outbox_ownership(self):
        fixture = self.task_report_fixture()
        self.policy['principals']['A']['scopes'][SCOPE].remove('tasks.authorize'); self.save_policy()
        self.error(fixture.native.report, fixture.task['id'], code='UNAUTHORIZED')
        self.policy['principals']['A']['scopes'][SCOPE].append('tasks.authorize'); self.save_policy()
        fixture.app.binding['principal'] = 'B'
        self.error(fixture.native.report, fixture.task['id'], code='UNAUTHORIZED')
        fixture.app.binding['principal'] = 'A'
        with fixture.app.db: fixture.app.db.execute('DELETE FROM preview_task_outbox')
        self.error(fixture.native.report, fixture.task['id'], code='UNAUTHORIZED')

    def test_report_refuses_changed_captured_body_against_authoritative_atom(self):
        fixture = self.task_report_fixture(); changed = copy.deepcopy(fixture.source)
        changed['task_origin']['record']['projection'] = 'invented replacement fixture text'
        with fixture.app.db:
            fixture.app.db.execute('UPDATE preview_native_inputs SET source=?', (canonical(changed).decode(),))
        self.error(fixture.native.report, fixture.task['id'], code='CONFLICT')

    def test_completed_delegate_restores_under_report_context_without_recursive_publication(self):
        fixture = self.task_report_fixture(); fixture.native.publish = Mock()
        saved = canonical(dict(status='TASK_PUBLISHED', task=fixture.task['id'])).decode()
        row = dict(id=fixture.task['id'], result=saved, deadline=NOW-1)
        args = dict(recipient='B', query=fixture.task['query'])
        self.assertEqual(fixture.native.delegate(row, args), saved)
        fixture.native.publish.assert_not_called()
        self.error(fixture.native.delegate, dict(row, result=None), args, code='UNAUTHORIZED')
        fixture.native.publish.assert_not_called()
        self.policy['principals']['A']['scopes'][SCOPE].remove('tasks.authorize'); self.save_policy()
        self.error(fixture.native.delegate, row, args, code='UNAUTHORIZED')

    def test_client_validates_poll_delivery_identity_order_status_and_body_types(self):
        self.send(self.task())
        mutations = [('delivery_id', 'not-a-uuid'), ('order', True), ('order', 0), ('delivery', 'acknowledged'),
                     ('body', []), ('body', None), ('body', {'ref': {}})]
        for key, value in mutations:
            def malformed(operation, reply):
                if operation == 'poll': reply['value'][key] = value
                return reply
            self.transform = malformed
            with self.subTest(key=key, value=value): self.error(self.clients['B'].call, 'poll')

    def test_client_refuses_reply_selection_actor_and_request_binding_changes(self):
        for key, value in [('id', 'foreign-request'), ('request_digest', 'b'*64),
                           ('selection', 'c'*64), ('principal', 'A')]:
            def malformed(operation, reply): reply[key] = value; return reply
            self.transform = malformed
            with self.subTest(key=key): self.error(self.clients['B'].call, 'poll', code='NOT_AVAILABLE')

    def test_configuration_change_cannot_silently_rebind_selected_client(self):
        cfg = json.loads(self.clients['B'].path.read_text()); cfg['principal'] = 'A'
        self.clients['B'].path.write_bytes(canonical(cfg))
        before = len(self.calls)
        self.error(self.clients['B'].call, 'poll', code='CONFLICT')
        self.assertEqual(len(self.calls), before)

    def test_task_acceptance_inherits_deadline_origin_and_ack_follows_session_commit(self):
        task = self.task(); ref, receipt = self.send(task)
        self.assertEqual(self.ingress().drain(), 'accepted')
        store = self.store()
        try:
            item = store.next_input('B', self.sessions['B'])
            self.assertEqual(item['deadline'], task['deadline'])
            self.assertEqual(item['payload'], dict(text='query '+task['query'], assignment='delegated-task'))
            self.assertEqual(item['task_origin']['record'], task)
            self.assertEqual(item['task_origin']['ref'], ref)
            self.assertEqual(item['id'], 'mailbox/'+receipt['delivery_id'])
            self.assertEqual(len(store.observe('B', self.sessions['B'])['inputs']), 1)
        finally: store.close()
        self.assertEqual(self.row()['ack'], 1)
        self.assertIsNone(self.clients['B'].call('poll'))
        self.assertEqual(self.wakes, [self.sessions['B']])

    def test_capture_interruption_leaves_mailbox_unacknowledged_then_reopens(self):
        task = self.task(); self.send(task)
        with self.assertRaises(RuntimeError): self.ingress(hook=self.interrupt('after_task_ingress_capture')).drain()
        self.assertEqual(self.row()['status'], 'captured'); self.assertEqual(self.row()['ack'], 0)
        self.assertIsNotNone(self.clients['B'].call('poll'))
        spent = self.spent()
        self.assertEqual(self.ingress().drain(), 'accepted')
        self.assertGreater(self.spent(), spent)
        store = self.store()
        try: self.assertEqual(len(store.observe('B', self.sessions['B'])['inputs']), 1)
        finally: store.close()

    def test_session_commit_interruption_replays_without_duplicate_acceptance(self):
        task = self.task(); self.send(task)
        with self.assertRaises(RuntimeError): self.ingress(hook=self.interrupt('after_task_session_acceptance')).drain()
        self.assertEqual(self.row()['status'], 'captured'); self.assertIsNotNone(self.clients['B'].call('poll'))
        store = self.store()
        try: before = store.observe('B', self.sessions['B'])['inputs']
        finally: store.close()
        self.now += 1000
        self.assertEqual(self.ingress().drain(), 'accepted')
        store = self.store()
        try: self.assertEqual(store.observe('B', self.sessions['B'])['inputs'], before)
        finally: store.close()

    def test_expired_already_accepted_session_is_reconciled_without_deadline_renewal(self):
        task = self.task(); self.send(task)
        with self.assertRaises(RuntimeError): self.ingress(hook=self.interrupt('after_task_session_acceptance')).drain()
        self.now = task['deadline']+1
        self.assertEqual(self.ingress().drain(), 'accepted')
        self.assertEqual(self.row()['status'], 'accepted')
        store = self.store()
        try:
            inputs = store.observe('B', self.sessions['B'])['inputs']
            self.assertEqual(len(inputs), 1); self.assertEqual(inputs[0]['deadline'], task['deadline'])
            self.error(store.next_input, 'B', self.sessions['B'], code='DEADLINE_EXCEEDED')
        finally: store.close()

    def test_ack_commit_interruption_recovers_local_receipt_and_wake(self):
        self.send(self.task())
        with self.assertRaises(RuntimeError): self.ingress(hook=self.interrupt('after_task_ingress_ack')).drain()
        self.assertEqual(self.row()['status'], 'accepted'); self.assertEqual(self.row()['ack'], 0)
        self.assertEqual(self.wakes, []); self.assertIsNone(self.clients['B'].call('poll'))
        self.assertEqual(self.ingress().drain(), 'accepted')
        self.assertEqual(self.row()['ack'], 1); self.assertEqual(self.wakes, [self.sessions['B']])

    def test_expired_captured_task_is_terminally_refused_without_new_session(self):
        task = self.task(); self.send(task)
        with self.assertRaises(RuntimeError): self.ingress(hook=self.interrupt('after_task_ingress_capture')).drain()
        self.now = task['deadline']
        self.assertEqual(self.ingress().drain(), 'refused')
        self.assertEqual(self.row()['ack'], 1); self.assertEqual(self.wakes, [])
        store = self.store()
        try: self.assertEqual(store.db.execute('SELECT count(*) FROM preview_inputs').fetchone()[0], 0)
        finally: store.close()
        self.error(self.send, task, code='DEADLINE_EXCEEDED')

    def test_ingress_refuses_wrong_correlation_without_ack(self):
        self.send(self.task())
        original = self.transform
        def malformed(operation, reply):
            if operation == 'poll': reply['value']['body']['correlation_id'] = str(uuid.uuid4())
            return reply
        self.transform = malformed
        self.error(self.ingress().drain, code='UNAUTHORIZED')
        self.transform = original
        self.assertEqual(self.row()['ack'], 0); self.assertIsNotNone(self.clients['B'].call('poll'))

    def test_ingress_refuses_record_for_other_recipient_without_session_acceptance(self):
        self.send(self.task())
        wrong = self.task(sender='B', recipient='A', session=self.sessions['B'])
        ref = self.persist(wrong)
        def malformed(operation, reply):
            if operation == 'poll':
                reply['value']['body'].update(ref=ref, correlation_id=wrong['id'])
            return reply
        self.transform = malformed
        self.error(self.ingress().drain, code='UNAUTHORIZED')
        self.assertEqual(self.row()['ack'], 0)
        store = self.store()
        try: self.assertEqual(store.db.execute('SELECT count(*) FROM preview_inputs').fetchone()[0], 0)
        finally: store.close()

    def test_result_ingress_retains_actual_projection_and_originating_session(self):
        task = self.task(); task_ref, _ = self.send(task)
        payload = self.atoms.create(Mutation(SCOPE, 'result-payload'), 'text/plain', b'Synthetic payload')['ref']
        result = self.result(task, task_ref, payloads=[payload], projection='Actual captured projection fixture bytes')
        self.send(result)
        self.assertEqual(self.ingress('A').drain(), 'accepted')
        store = self.store('A')
        try:
            item = store.next_input('A', self.sessions['A'])
            self.assertEqual(item['payload'], dict(text='task-context', assignment='delegated-result'))
            self.assertEqual(item['task_origin']['record'], result)
            self.assertEqual(item['deadline'], task['deadline'])
        finally: store.close()

    def test_revoked_worker_cannot_resume_captured_delivery_or_ack(self):
        self.send(self.task())
        with self.assertRaises(RuntimeError): self.ingress(hook=self.interrupt('after_task_ingress_capture')).drain()
        cfg = json.loads(self.configs['B'].read_text()); cfg['principals']['worker']['scopes'][SCOPE] = []
        self.configs['B'].write_bytes(canonical(cfg))
        spent = self.spent()
        self.error(self.ingress().drain, code='UNAUTHORIZED')
        self.assertEqual(self.spent(), spent); self.assertEqual(self.row()['ack'], 0)

    def test_reservation_interruption_spends_budget_and_exhaustion_is_not_refunded(self):
        self.send(self.task())
        with self.assertRaises(RuntimeError): self.ingress(hook=self.interrupt('after_task_ingress_reservation')).drain()
        self.assertEqual(self.spent(), 1)
        with sqlite3.connect(self.root/'ingress-B.sqlite') as db: db.execute('UPDATE ingress_limits SET calls=256')
        before = len(self.calls)
        self.error(self.ingress().drain, code='OVERLOADED')
        self.assertEqual(self.spent(), 256); self.assertEqual(len(self.calls), before)


if __name__ == '__main__': unittest.main()
