"""Handoff observer and interruption fixtures; no cluster/native/model claim.

SQLite snapshots are real. Captured native rows and prompts are authored. The
last tests use real NativeTasks/Messaging owners with FileFeedFixture atoms and
explicit in-process transport, retaining the prior task test classifications.
"""
import copy
import inspect
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
import uuid

from examples import preview_handoff_recovery as q
from fusion.contracts import ContractError, canonical, digest
from fusion.lookup_contracts import make_head
from fusion.preview_lifecycle import PROFILE as LIFECYCLE
from fusion.preview_tasks import PROFILE
from fusion import vector_contracts as vector, preview_vector_contracts as active
from tests import test_phase2_tasks as old


SCOPE = 'synthetic-handoff-recovery-fixture'


class HandoffRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.a, self.b, self.task_id, self.query_id = [str(uuid.uuid4()) for _ in range(4)]
        self.view = dict(generation=str(uuid.uuid4()), head=make_head(str(uuid.uuid4()), SCOPE, 3),
            corpus='synthetic-fixture-corpus', embedding=vector.FIXTURE, index=vector.INDEX,
            profile=active.PROFILE, lifecycle=make_head(str(uuid.uuid4()), SCOPE, 2, LIFECYCLE), active_digest='a'*64)
        self.view['logical'] = digest(canonical({k: v for k, v in self.view.items() if k != 'generation'}))
        self.ref = dict(scope_ref=SCOPE, id='task-fixture', revision=1, digest='b'*64)
        self.result_ref = dict(scope_ref=SCOPE, id='result-fixture', revision=1, digest='c'*64)
        self.payload = dict(scope_ref=SCOPE, id='payload-fixture', revision=1, digest='d'*64)
        self.task = dict(profile=PROFILE, kind='task', scope=SCOPE, id=self.task_id,
            sender='A', recipient='B', session=self.a, deadline=100000, parent='parent-fixture',
            limits=dict(queries=1, relay_calls=24, recursive_delegation=False), query='synthetic query fixture', minimum=self.view)
        self.result = dict(profile=PROFILE, kind='result', scope=SCOPE, id=self.task_id,
            sender='B', recipient='A', session=self.b, deadline=self.task['deadline'], parent=self.task['parent'],
            limits=self.task['limits'], task=self.ref, view=self.view,
            projection='Actual captured fixture bytes Ω', payloads=[self.payload], status='captured-native-query')
        self.before = dict(session=self.b, task_id=self.task_id,
            outboxes=[dict(id='result/'+self.task_id, record=self.result, ref=self.result_ref, receipt=None, wake=None, calls=1)],
            inputs=[dict(turn=2, identity='mailbox/task-fixture', acknowledged=0,
                source=dict(occurrence='b-source', deadline=self.task['deadline'],
                    task_origin=dict(record=self.task, ref=self.ref)), projection_sha256='e'*64)],
            occurrences=[dict(id=self.query_id, turn=2, position=1, deadline=90000, done=1,
                result=self.result['projection'], attempts=1, premises=dict(profile=active.PROFILE,
                    operation='query_with_ids_and_dists', arguments={'query': self.task['query']}))],
            reads=[dict(id=self.query_id, queries=1, calls=3, request_sha256='a'*64, candidates_sha256='b'*64,
                payloads_sha256='c'*64, enrichment=123.5, hit_refs=[self.payload])],
            views=[dict(occurrence=self.query_id, view_id='view-fixture', value_sha256='f'*64, snapshot=self.view)],
            models=[dict(slot=2, id='model-fixture', calls=1, result_sha256='a'*64, admission_sha256='b'*64,
                intent_sha256='c'*64)])
        self.after = copy.deepcopy(self.before)
        self.after['outboxes'][0].update(calls=4, receipt={'boundary': 'AUTHORED_ACCEPTANCE_FIXTURE'},
                                         wake={'status': 'accepted'})
        self.after['inputs'][0]['acknowledged'] = 1
        self.origin = dict(profile=PROFILE, record=self.result, ref=self.result_ref, delivery='result-delivery-fixture')
        self.recipient = dict(inputs=[dict(turn=8, identity='mailbox/result-fixture', acknowledged=1,
            projection_sha256='a'*64, source=dict(occurrence='a-source', deadline=self.task['deadline'], task_origin=self.origin))],
            models=[dict(source_id='a-source', deadline_ms=self.task['deadline'], result_sha256='b'*64,
                admission_sha256='c'*64, feedback=dict(native='captured prior fixture', delegated_report=self.origin,
                    interpretation='agent-report-not-independent-corroboration'))])

    def denied(self, fn, *args, code='CONFLICT'):
        with self.assertRaises(ContractError) as caught:
            fn(*args)
        self.assertEqual(caught.exception.code, code)

    def check(self):
        return q.recovered(self.before, self.after, self.recipient, self.task, self.ref)

    def test_exact_captured_result_view_and_actual_next_prompt_pass(self):
        result = self.check()
        self.assertEqual(result['new_search_queries'], 0)
        self.assertTrue(result['actual_recipient_prompt_binding'])
        self.assertFalse(result['independent_corroboration'])

    def test_changed_query_projection_or_atom_is_rejected(self):
        for field, value in [('ref', {**self.result_ref, 'id': 'replacement'}),
                             ('record', {**self.result, 'projection': 'preferred answer'})]:
            saved = copy.deepcopy(self.after)
            self.after['outboxes'][0][field] = value
            self.denied(self.check)
            self.after = saved

    def test_changed_retained_view_or_query_deadline_is_rejected(self):
        self.after['views'][0]['value_sha256'] = '0'*64
        self.denied(self.check)
        self.after['views'] = copy.deepcopy(self.before['views'])
        self.after['occurrences'][0]['deadline'] += 1
        self.denied(self.check)

    def test_requery_refunded_or_exhausted_budgets_are_rejected(self):
        for group, key, value in [('reads', 'queries', 2), ('reads', 'calls', 2), ('reads', 'calls', 65),
                                 ('models', 'calls', 9), ('occurrences', 'attempts', 3), ('outboxes', 'calls', 0)]:
            saved = copy.deepcopy(self.after)
            self.after[group][0][key] = value
            self.denied(self.check)
            self.after = saved

    def test_missing_capture_publication_or_ack_never_passes(self):
        self.before['reads'][0]['payloads_sha256'] = None
        self.denied(self.check)
        self.before['reads'][0]['payloads_sha256'] = 'c'*64
        self.after['outboxes'][0]['receipt'] = None
        self.denied(self.check)
        self.after['outboxes'][0]['receipt'] = {'boundary': 'FIXTURE'}
        self.recipient['inputs'][0]['acknowledged'] = 0
        self.denied(self.check)

    def test_expected_answer_cannot_substitute_actual_prompt_origin(self):
        self.recipient['models'][0]['feedback'] = dict(native='preferred answer')
        with self.assertRaises((ContractError, KeyError)):
            self.check()

    def test_result_prompt_deadline_source_and_corroboration_binding_are_checked(self):
        for key, value in [('deadline_ms', self.task['deadline']+1), ('source_id', 'new-occurrence')]:
            saved = copy.deepcopy(self.recipient)
            self.recipient['models'][0][key] = value
            self.denied(self.check)
            self.recipient = saved
        self.recipient['models'][0]['feedback']['interpretation'] = 'independent evidence'
        self.denied(self.check)

    def test_empty_result_not_counted_as_memory_handoff(self):
        self.before['outboxes'][0]['record']['payloads'] = []
        self.before['reads'][0]['hit_refs'] = []
        self.denied(q.captured, self.before, self.task, self.ref)

    @staticmethod
    def encoded_feedback(value):
        # Fixture of the pinned native protocol, including tokens that already
        # occur literally in data. No expected task answer is supplied.
        return canonical(value).decode().replace(':-:-:-:', '\\u003a-\\u003a-\\u003a-\\u003a').replace('"', '_quote_').replace('\n', '_newline_').replace("'", '_apostrophe_')

    def write_snapshot(self, feedback_wire=None):
        directory = self.root/'sessions'/self.a
        directory.mkdir(parents=True)
        path = directory/'caller.sqlite'
        source = self.recipient['inputs'][0]['source']
        feedback = self.recipient['models'][0]['feedback']
        selected_wire = self.encoded_feedback(feedback) if feedback_wire is None else feedback_wire
        prompt = 'PROMPT_AND_SKILLS_JSON: {} LAST_SKILL_USE_RESULTS: '+selected_wire+' HISTORY: [] :-:-:-: ["HUMAN-MSG:", "task-context"]'
        intent = dict(native_prompt=prompt, source_id='a-source', deadline_ms=self.task['deadline'])
        with sqlite3.connect(path) as db:
            db.executescript('''CREATE TABLE preview_native_inputs(turn,identity,source,acknowledged);
                CREATE TABLE app_turns(id,projection);
                CREATE TABLE app_occurrences(turn,position,id,premises,deadline,result,done);
                CREATE TABLE app_model_calls(slot,id,intent,context_view,calls,result,normalized,parse_text,proposal,admission);
                CREATE TABLE private_credentials(secret);
                INSERT INTO private_credentials VALUES('do-not-publish-fixture-secret');''')
            db.execute('INSERT INTO preview_native_inputs VALUES(8,?,?,1)', ('mailbox/result-fixture', canonical(source).decode()))
            db.execute('INSERT INTO app_turns VALUES(7,?)', (feedback['native'],))
            db.execute('INSERT INTO app_turns VALUES(8,?)', ('Captured context fixture',))
            db.execute('INSERT INTO app_model_calls VALUES(8,?,?,?,1,?,?,?,?,?)',
                ('model-fixture', canonical(intent).decode(), 'retained-context-fixture',
                 'response-fixture', 'normalized-fixture', 'task-context', 'proposal-fixture', 'admission-fixture'))
        return path

    def test_readonly_snapshot_extracts_actual_prompt_and_excludes_unrelated_secrets(self):
        path = self.write_snapshot(); before = digest(path.read_bytes())
        found = q.owned_snapshot(self.root, self.a, self.task_id)
        self.assertEqual(found['models'][0]['feedback']['delegated_report'], self.origin)
        self.assertNotIn('do-not-publish', json.dumps(found))
        self.assertNotIn('native_prompt', found['models'][0])
        observation = found['models'][0]['feedback_observation']
        self.assertTrue(observation['exact_forward_match'])
        self.assertEqual(observation['prior_turn'], 7)
        self.assertEqual(observation['normalization']['source_boundary'], 'EXPLICIT_FIXTURE')
        self.assertEqual(before, digest(path.read_bytes()))

    def test_native_escaped_feedback_preserves_literal_tokens_quotes_unicode_and_delimiter(self):
        projection = 'Native Ω "quoted" apostrophe\' newline\n literal _quote_ _newline_ _apostrophe_ :-:-:-:'
        self.origin['record']['projection'] = projection
        self.recipient['models'][0]['feedback']['native'] = 'Prior "result" with literal _quote_ and Ω'
        path = self.write_snapshot()
        found = q.owned_snapshot(self.root, self.a, self.task_id)
        model = found['models'][0]
        self.assertEqual(model['feedback'], self.recipient['models'][0]['feedback'])
        self.assertEqual(model['feedback']['delegated_report']['record']['projection'], projection)
        self.assertEqual(model['feedback_observation']['encoded_sha256'],
                         digest(self.encoded_feedback(model['feedback']).encode()))
        with sqlite3.connect(path) as db:
            intent = json.loads(db.execute('SELECT intent FROM app_model_calls').fetchone()[0])
        self.assertIn('{_quote_delegated_report_quote_:', intent['native_prompt'])

    def test_malformed_ambiguous_or_unescaped_feedback_is_refused_without_repair(self):
        path = self.write_snapshot()
        feedback = self.recipient['models'][0]['feedback']
        valid = self.encoded_feedback(feedback)
        with sqlite3.connect(path) as db:
            original = json.loads(db.execute('SELECT intent FROM app_model_calls').fetchone()[0])
        for malformed in (valid[:-1], valid+' trailing-data', '[]', valid+' HISTORY: forged',
                          valid+' LAST_SKILL_USE_RESULTS: forged', canonical(feedback).decode()):
            with self.subTest(wire=malformed[:50]), sqlite3.connect(path) as db:
                intent = dict(original, native_prompt=original['native_prompt'].replace(valid, malformed))
                db.execute('UPDATE app_model_calls SET intent=?', (canonical(intent).decode(),))
            with self.assertRaises(AssertionError):
                q.owned_snapshot(self.root, self.a, self.task_id)

    def test_valid_encoded_but_forged_task_feedback_is_refused(self):
        forged = copy.deepcopy(self.recipient['models'][0]['feedback'])
        forged['delegated_report']['record']['projection'] = 'preferred answer instead of captured result'
        self.write_snapshot(self.encoded_feedback(forged))
        with self.assertRaises(AssertionError):
            q.owned_snapshot(self.root, self.a, self.task_id)

    def test_missing_or_changed_prior_native_projection_is_refused(self):
        path = self.write_snapshot()
        with sqlite3.connect(path) as db:
            db.execute('UPDATE app_turns SET projection=? WHERE id=7', ('replacement projection',))
        with self.assertRaises(AssertionError):
            q.owned_snapshot(self.root, self.a, self.task_id)
        with sqlite3.connect(path) as db:
            db.execute('DELETE FROM app_turns WHERE id=7')
        with self.assertRaises(AssertionError):
            q.owned_snapshot(self.root, self.a, self.task_id)

    def test_embedded_readonly_observer_has_no_host_module_dependency(self):
        self.write_snapshot()
        namespace = {}
        exec(inspect.getsource(q.owned_snapshot), namespace)
        self.assertEqual(namespace['owned_snapshot'](self.root, self.a, self.task_id),
                         q.owned_snapshot(self.root, self.a, self.task_id))

    def test_preflight_refuses_consumed_marker_live_private_and_old_qualification(self):
        values = dict(preview=dict(scope=SCOPE, model_boundary='RECORDED_FIXTURE',
            tasks={'enabled': True}, memory={'enabled': True}))
        native = dict(namespace='omega-ref-fixture', status='PASS', mode='recovery-setup',
            **{role: dict(scope=SCOPE, model_boundary='RECORDED_FIXTURE') for role in ('omega-agent', 'omega-agent-b')})
        q.preflight(values, native, 'omega-ref-fixture', None)
        self.denied(q.preflight, values, native, 'omega-ref-fixture', {'old': 'pause'})
        for replacement in ({'futureLive': {'enabled': True}}, {'preview': {**values['preview'], 'scope': 'private'}},
                            {'preview': {**values['preview'], 'model_boundary': 'LIVE'}}):
            self.denied(q.preflight, {**values, **replacement}, native, 'omega-ref-fixture', None, code='UNAUTHORIZED')
        self.denied(q.preflight, values, {**native, 'mode': 'combined'}, 'omega-ref-fixture', None, code='UNAUTHORIZED')

    def session_selection_fixture(self):
        # Match h18's real failure shape: canonical JSON maps reorder B's UUID
        # keys, while the configured task ingress uses the original list order.
        b_first = 'b1ca9649-c0a1-44c1-b2ae-05e796473adc'
        b_second = 'a84387db-37b1-439a-910a-71e93d57e2c9'
        a_second = str(uuid.uuid4())
        agents = {'omega-agent': dict(principal='A', sessions=[self.a, a_second]),
                  'omega-agent-b': dict(principal='B', sessions=[b_first, b_second])}
        values = dict(preview=dict(scope=SCOPE, model_boundary='RECORDED_FIXTURE', agents=agents))
        tools = {name: dict(descriptor={'profile': profile}) for name, profile in (
            ('delegate', PROFILE), ('task-context', 'working-task-context/1'), ('query', active.PROFILE))}
        inventories = {}
        for role, agent in agents.items():
            inventories[role] = dict(principal=agent['principal'], scope=SCOPE, model_boundary='RECORDED_FIXTURE',
                sessions={sid: dict(catalogue='catalogue-fixture', policy='policy-fixture',
                    model_boundary='RECORDED_FIXTURE', limits={'timeout_ms': 120000}) for sid in sorted(agent['sessions'])},
                catalogues={sid: dict(profile=q.CATALOGUE_PROFILE, tools=copy.deepcopy(tools))
                            for sid in sorted(agent['sessions'])})
        return values, inventories, a_second

    def test_task_recipient_uses_configured_ingress_session_with_reversed_inventory_order(self):
        values, inventories, selected_a = self.session_selection_fixture()
        selected = q.session_bindings(values, inventories, selected_a)
        expected_b = values['preview']['agents']['omega-agent-b']['sessions'][0]
        self.assertNotEqual(next(iter(inventories['omega-agent-b']['sessions'])), expected_b)
        self.assertEqual(selected['recipient']['session'], expected_b)
        self.assertEqual(selected['sender']['session'], selected_a)
        self.assertEqual(selected['recipient']['selection'], 'configured-task-ingress-first-session')
        self.assertEqual(selected['recipient']['session_binding'], inventories['omega-agent-b']['sessions'][expected_b])
        # An inventory round-trip must never select a replacement B session.
        reordered = json.loads(json.dumps(inventories, sort_keys=True))
        self.assertEqual(selected, q.session_bindings(values, reordered, selected_a))

    def test_session_selection_refuses_missing_membership_wrong_owner_or_profile(self):
        values, inventories, selected_a = self.session_selection_fixture()
        sid_b = values['preview']['agents']['omega-agent-b']['sessions'][0]
        absent = copy.deepcopy(inventories)
        del absent['omega-agent-b']['sessions'][sid_b]
        self.denied(q.session_bindings, values, absent, selected_a)
        self.denied(q.session_bindings, values, inventories, str(uuid.uuid4()))
        wrong = copy.deepcopy(inventories); wrong['omega-agent-b']['principal'] = 'A'
        self.denied(q.session_bindings, values, wrong, selected_a, code='UNAUTHORIZED')
        for section, key, value in [('sessions', 'model_boundary', 'LIVE'), ('catalogues', 'profile', 'other/1')]:
            wrong = copy.deepcopy(inventories); wrong['omega-agent-b'][section][sid_b][key] = value
            self.denied(q.session_bindings, values, wrong, selected_a, code='UNSUPPORTED_PROFILE')
        wrong = copy.deepcopy(inventories)
        wrong['omega-agent-b']['catalogues'][sid_b]['tools']['query']['descriptor']['profile'] = 'semantic-embedding-memory/1'
        self.denied(q.session_bindings, values, wrong, selected_a, code='UNSUPPORTED_PROFILE')

    def test_real_outbox_barrier_recovers_same_atom_and_spent_budget_with_fixture_ports(self):
        fixture = old.TaskHandoffTests('runTest'); fixture.setUp(); self.addCleanup(fixture.doCleanups)
        task = fixture.task(); ref, _ = fixture.send(task)
        body = fixture.result(task, ref)
        app, native = fixture.native_outbox_fixture(fixture.interrupt(q.STAGE))
        native.port = fixture.clients['B']
        with self.assertRaisesRegex(RuntimeError, 'explicit interruption fixture'):
            native.publish(body)
        before = dict(app.db.execute('SELECT * FROM preview_task_outbox').fetchone())
        self.assertIsNotNone(before['ref']); self.assertIsNone(before['receipt']); self.assertEqual(before['calls'], 1)
        self.assertEqual(len(fixture.mailbox_rows()), 1)
        # Exercise the original deadline: stop the optional wake after the real
        # Messaging acceptance without granting another task execution window.
        def hook(stage):
            if stage == 'after_task_publication_capture':
                fixture.now = task['deadline']+1
        app.hook = hook
        with patch('fusion.preview_native_tasks.write_body', side_effect=AssertionError('must reuse saved AtomRef')):
            receipt = native.publish(body)
        after = dict(app.db.execute('SELECT * FROM preview_task_outbox').fetchone())
        self.assertEqual(before['record'], after['record']); self.assertEqual(before['ref'], after['ref'])
        self.assertEqual(after['calls'], 3); self.assertEqual(len(fixture.mailbox_rows()), 2)
        self.assertEqual(receipt['recipient_observation']['code'], 'DEADLINE_EXCEEDED')
        self.assertEqual(receipt['deadline'], task['deadline'])

    def test_revoked_authority_blocks_barrier_recovery_before_publication(self):
        fixture = old.TaskHandoffTests('runTest'); fixture.setUp(); self.addCleanup(fixture.doCleanups)
        task = fixture.task(); ref, _ = fixture.send(task)
        body = fixture.result(task, ref)
        app, native = fixture.native_outbox_fixture(fixture.interrupt(q.STAGE)); native.port = fixture.clients['B']
        with self.assertRaises(RuntimeError): native.publish(body)
        before = dict(app.db.execute('SELECT * FROM preview_task_outbox').fetchone())
        fixture.policy['principals']['B']['scopes'][old.SCOPE].remove('tasks.authorize'); fixture.save_policy()
        app.hook = lambda stage: None
        self.denied(native.publish, body, code='UNAUTHORIZED')
        self.assertEqual(before, dict(app.db.execute('SELECT * FROM preview_task_outbox').fetchone()))
        self.assertEqual(len(fixture.mailbox_rows()), 1)


if __name__ == '__main__':
    unittest.main()
