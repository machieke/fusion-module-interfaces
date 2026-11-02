"""Focused P14/P16 owner/adapter checks; explicitly no deployed/wire claim.

The task client transport is the existing in-process fixture. It invokes actual
Messaging, Policy, ingress and SessionStore transitions over fresh journals.
Memory and Relations use FileFeedFixture, not DeTTa, vectors or a native loop.
No endpoint, TLS, process kill, pod, model, E5 or Chroma runs in this suite.
"""
from contextlib import closing
import copy
import json
from pathlib import Path
import sqlite3
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import uuid

from fusion.adapters.fixture_feed import FileFeedFixture
from fusion import lookup_contracts as lookup, vector_contracts as vector
from fusion.contracts import ContractError, canonical, require
from fusion.policy import Policy
from fusion.ports import Mutation
from fusion.preview_lifecycle import MemoryLifecycle
from fusion.preview_relations import RetractableRelations
from fusion.preview_sessions import SessionStore
from fusion.relations import RelationOwner
from fusion.vector_enrollment import enroll
from tests import test_phase2_tasks as tasks


class EdgeAssertions:
    def error(self, code, operation, *args, **kwargs):
        with self.assertRaises(ContractError) as caught:
            operation(*args, **kwargs)
        self.assertEqual(caught.exception.code, code)

    @staticmethod
    def logical_dump(path):
        with closing(sqlite3.connect(path)) as db:
            return '\n'.join(db.iterdump())


class TaskRecipientEdges(EdgeAssertions, unittest.TestCase):
    def setUp(self):
        # Composition fixture only, without inheriting/rerunning its test cases.
        self.f = tasks.TaskHandoffTests('runTest')
        self.addCleanup(self.f.doCleanups)
        self.f.setUp()

    def session_rows(self):
        store = self.f.store('B')
        try:
            return [tuple(row) for row in store.db.execute('SELECT * FROM preview_inputs ORDER BY sequence')]
        finally:
            store.close()

    def captured(self, stage='after_task_ingress_capture'):
        body = self.f.task()
        ref, receipt = self.f.send(body)
        with self.assertRaisesRegex(RuntimeError, 'explicit interruption fixture'):
            self.f.ingress(hook=self.f.interrupt(stage)).drain()
        return body, ref, receipt

    def test_recipient_credential_rotation_rechecks_captured_delivery_without_rebinding(self):
        body, _, receipt = self.captured()
        before = self.f.row()
        messages = self.f.mailbox_rows()
        spent = self.f.spent()
        frozen = copy.deepcopy(self.f.clients['B'].frozen)
        self.f.policy['principals']['B']['credential'] = 'synthetic-B-rotated'
        self.f.save_policy()
        self.error('UNAUTHORIZED', self.f.ingress().drain)
        self.assertEqual(self.f.row(), before)
        self.assertEqual(self.session_rows(), [])
        self.assertEqual(self.f.mailbox_rows(), messages)
        self.assertEqual(self.f.spent(), spent+1)
        self.assertEqual(self.f.wakes, [])

        path = self.f.clients['B'].path
        cfg = json.loads(path.read_text())
        cfg['credential'] = 'synthetic-B-rotated'
        path.write_bytes(canonical(cfg))
        self.assertEqual(self.f.clients['B'].current()[1], frozen)
        self.assertEqual(self.f.ingress().drain(), 'accepted')
        self.assertEqual(self.f.clients['B'].call('poll'), None)
        accepted = json.loads(self.f.row()['input'])
        self.assertEqual(accepted['id'], 'mailbox/'+receipt['delivery_id'])
        self.assertEqual(accepted['deadline'], body['deadline'])
        self.assertEqual(len(self.session_rows()), 1)
        self.assertEqual(len(self.f.mailbox_rows()), 1)
        self.assertEqual(self.f.row()['ack'], 1)
        self.assertGreater(self.f.spent(), spent+1)

    def test_current_recipient_membership_blocks_sender_publication_replay(self):
        body = self.f.task()
        ref, receipt = self.f.send(body)
        before = self.f.mailbox_rows()
        methods = self.f.policy['principals']['B']['scopes'][tasks.SCOPE]
        methods.remove('agent.messaging.poll')
        self.f.save_policy()
        self.error('UNAUTHORIZED', self.f.published, body, ref)
        self.error('UNAUTHORIZED', self.f.clients['B'].call, 'poll')
        self.assertEqual(self.f.mailbox_rows(), before)
        methods.append('agent.messaging.poll')
        self.f.save_policy()
        self.assertEqual(self.f.published(body, ref), receipt)
        self.assertEqual(self.f.clients['B'].call('poll')['delivery_id'], receipt['delivery_id'])
        self.assertEqual(self.f.mailbox_rows(), before)

    def test_ack_revocation_preserves_accepted_session_and_pending_mailbox(self):
        body, _, receipt = self.captured('after_task_session_acceptance')
        accepted = self.session_rows()
        self.assertEqual(len(accepted), 1)
        methods = self.f.policy['principals']['B']['scopes'][tasks.SCOPE]
        methods.remove('tasks.ack')
        self.f.save_policy()
        self.error('UNAUTHORIZED', self.f.ingress().drain)
        self.assertEqual(self.session_rows(), accepted)
        self.assertEqual(self.f.row()['ack'], 0)
        self.assertEqual(self.f.clients['B'].call('poll')['delivery_id'], receipt['delivery_id'])
        self.assertEqual(self.f.wakes, [])
        spent = self.f.spent()
        methods.append('tasks.ack')
        self.f.save_policy()
        self.assertEqual(self.f.ingress().drain(), 'accepted')
        self.assertEqual(self.session_rows(), accepted)
        self.assertEqual(json.loads(self.f.row()['input'])['deadline'], body['deadline'])
        self.assertEqual(self.f.row()['ack'], 1)
        self.assertGreater(self.f.spent(), spent)
        self.assertEqual(self.f.wakes, [self.f.sessions['B']])

    def test_current_peer_revocation_rejects_genuine_captured_task_without_ack(self):
        body, _, receipt = self.captured()
        path = self.f.configs['B']
        cfg = json.loads(path.read_text())
        cfg['task_ingress']['peers'] = []
        path.write_bytes(canonical(cfg))
        self.error('UNAUTHORIZED', self.f.ingress().drain)
        self.assertEqual(self.session_rows(), [])
        self.assertEqual(self.f.row()['ack'], 0)
        self.assertEqual(self.f.clients['B'].call('poll')['delivery_id'], receipt['delivery_id'])
        cfg['task_ingress']['peers'] = ['A']
        path.write_bytes(canonical(cfg))
        self.assertEqual(self.f.ingress().drain(), 'accepted')
        self.assertEqual(len(self.session_rows()), 1)
        self.assertEqual(json.loads(self.f.row()['input'])['deadline'], body['deadline'])


class DurableOwnerEdges(EdgeAssertions, unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='phase2-cross-feature-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.scope = 'synthetic-cross-feature-edges'
        self.methods = ['lifecycle.'+name for name in ('read', 'history', 'project', 'introduce', 'supersede', 'withdraw')]
        self.methods += ['assertRelation', 'getRelation', 'retract', 'outgoing', 'incoming', 'history']
        self.path = self.root/'policy.json'
        self.save_policy()
        policy = Policy(self.path)

        def authorize(scope, operation):
            principal = policy.authenticate('synthetic-owner')
            policy.check(principal, scope, operation)
            return principal

        self.access = SimpleNamespace(authorize=authorize)
        self.atoms = FileFeedFixture(self.root/'fixture-atoms.json', SimpleNamespace(authorize=lambda scope, _: 'A'))
        self.owner = MemoryLifecycle(self.root/'lifecycle.sqlite', self.atoms, self.access,
                                     self.scope, 'new-generated-corpus', embedding=vector.FIXTURE)

    def save_policy(self):
        self.path.write_bytes(canonical(dict(principals={'A': dict(credential='synthetic-owner', scopes={self.scope: self.methods})})))

    def command(self, identity):
        return Mutation(self.scope, identity)

    def enrollment(self, text):
        identity = str(uuid.uuid4())
        return enroll(self.atoms, self.scope, 'new-generated-corpus', vector.FIXTURE, identity,
            dict(scope=self.scope, corpus='new-generated-corpus', uuid=identity,
                 time='2026-11-02 12:00:00', content=text), [1.]+[0.]*1023)

    def test_retained_snapshot_does_not_override_current_withdrawal_or_historical_authority(self):
        first = self.owner.change(self.command('first'), 'introduce', enrollment=self.enrollment('Synthetic original'))
        captured = self.owner.activeSet(first['at'])
        original = self.atoms.get(first['memory']['payload']).bytes
        second = self.owner.change(self.command('supersede'), 'supersede', logical_id=first['logical_id'],
                                   expected_revision=1, enrollment=self.enrollment('Synthetic successor'))
        self.owner.change(self.command('unrelated'), 'introduce', enrollment=self.enrollment('Unrelated synthetic memory'))
        self.assertEqual(self.owner.activeSet(first['at']), captured)
        self.assertTrue(self.owner.disclose(first['logical_id'], first['memory'], first['at'])['authorized'])
        gone = self.owner.change(self.command('withdraw'), 'withdraw', logical_id=first['logical_id'], expected_revision=2)
        for item in (first, second):
            self.error('UNAUTHORIZED', self.owner.disclose, item['logical_id'], item['memory'], item['at'])
            self.assertTrue(self.owner.disclose(item['logical_id'], item['memory'], item['at'], historical=True)['authorized'])
        self.methods.remove('lifecycle.history')
        self.save_policy()
        self.error('UNAUTHORIZED', self.owner.disclose, first['logical_id'], first['memory'], first['at'], historical=True)
        self.assertEqual(self.owner.activeSet(first['at']), captured)
        self.assertEqual(self.atoms.get(first['memory']['payload']).bytes, original)
        self.assertFalse(gone['payload_erased'])
        self.assertFalse(gone['empirical_weight_transferred'])
        self.assertFalse(gone['priority_transferred'])

    def test_current_authority_is_rechecked_after_payload_hydration(self):
        first = self.owner.change(self.command('first'), 'introduce', enrollment=self.enrollment('Synthetic race input'))
        before = self.logical_dump(self.owner.path)
        get = self.atoms.get

        def hydrate_then_revoke(ref):
            item = get(ref)
            self.methods.remove('lifecycle.read')
            self.save_policy()
            return item

        with patch.object(self.atoms, 'get', side_effect=hydrate_then_revoke) as reads:
            self.error('UNAUTHORIZED', self.owner.disclose, first['logical_id'], first['memory'], first['at'])
        self.assertEqual(reads.call_count, 1)
        self.assertEqual(self.logical_dump(self.owner.path), before)
        self.assertTrue(self.owner.disclose(first['logical_id'], first['memory'], first['at'], historical=True)['authorized'])

    def test_historical_and_retractable_relation_owners_refuse_each_others_populated_journals(self):
        left = self.atoms.create(self.command('left'), 'text/plain', b'Synthetic left')['ref']
        right = self.atoms.create(self.command('right'), 'text/plain', b'Synthetic right')['ref']
        roles = (('dependent', left), ('prerequisite', right))
        paths = [self.root/'historical-relations.sqlite', self.root/'retractable-relations.sqlite']
        historical = RelationOwner(paths[0], self.atoms, self.access, lookup.SCHEMAS)
        modern = RetractableRelations(paths[1], self.atoms, self.access, lookup.SCHEMAS)
        old = historical.assertRelation(self.command('old'), 'requires/1', roles, True)
        new = modern.assertRelation(self.command('new'), 'requires/1', roles, True)
        modern.retract(self.command('retract'), new['ref'], new['asserted_at'])
        before = [self.logical_dump(path) for path in paths]
        atom_head = self.atoms.head(self.scope)
        self.error('UNSUPPORTED_PROFILE', RetractableRelations, paths[0], self.atoms, self.access, lookup.SCHEMAS)
        self.error('UNSUPPORTED_PROFILE', RelationOwner, paths[1], self.atoms, self.access, lookup.SCHEMAS)
        self.assertEqual([self.logical_dump(path) for path in paths], before)
        self.assertEqual(self.atoms.head(self.scope), atom_head)
        self.assertEqual(historical.getRelation(old['ref']), old)
        self.assertEqual(modern.getRelation(new['ref'], historical=True)['state'], 'retracted')

    def test_populated_session_profile_refusals_precede_schema_or_row_mutation(self):
        path = self.root/'sessions.sqlite'
        store = SessionStore(path, lambda *_: None, lambda: 1000)
        session = str(uuid.uuid4())
        binding = dict(catalogue='fixed-fixture-catalogue', policy='fixed-fixture-policy',
                       model_boundary='RECORDED_FIXTURE', limits=dict(inputs=4, pending=2, timeout_ms=30000))
        store.create('A', session, self.scope, binding)
        accepted = store.submit('A', session, 'accepted', 'Synthetic unchanged input', 'synthetic-task')
        store.close()
        for marker in ('omega-native-sessions/1', 'omega-native-sessions/999', None):
            with closing(sqlite3.connect(path)) as db, db:
                if marker is None:
                    db.execute('DROP TABLE preview_session_profile')
                else:
                    db.execute('UPDATE preview_session_profile SET profile=?', (marker,))
            before = self.logical_dump(path)
            self.error('UNSUPPORTED_PROFILE', SessionStore, path, lambda *_: None)
            self.assertEqual(self.logical_dump(path), before)
            with closing(sqlite3.connect(path)) as db:
                deadline, state = db.execute('SELECT deadline,state FROM preview_inputs WHERE id=?', ('accepted',)).fetchone()
            self.assertEqual(deadline, accepted['deadline'])
            self.assertEqual(state, 'accepted')


if __name__ == '__main__':
    unittest.main()
