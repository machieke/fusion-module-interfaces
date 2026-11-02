"""Lifecycle owner semantics; file AtomStorage and unit vectors are fixtures."""
import json
from contextlib import closing
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
import uuid

from fusion.contracts import ContractError
from fusion.ports import Mutation
from fusion.adapters.fixture_feed import FileFeedFixture
from fusion import vector_contracts as v
from fusion.vector_enrollment import enroll
from fusion.preview_lifecycle import MemoryLifecycle


class Access:
    revoked = False
    def authorize(self, scope, operation):
        if scope != 'synthetic-lifecycle' or self.revoked: raise ContractError('UNAUTHORIZED')
        return 'A'


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.access = Access()
        self.atoms = FileFeedFixture(self.root/'atoms.json', self.access)
        self.owner = self.open()

    def open(self, hook=lambda _: None):
        return MemoryLifecycle(self.root/'lifecycle.db', self.atoms, self.access,
                               'synthetic-lifecycle', 'new-corpus', hook, embedding=v.FIXTURE)

    def command(self, key): return Mutation('synthetic-lifecycle', key)

    def enrolled(self, text, axis=0):
        identity = str(uuid.uuid4())
        vector = [0.0]*1024; vector[axis] = 1.0
        return enroll(self.atoms, 'synthetic-lifecycle', 'new-corpus', v.FIXTURE, identity,
            dict(scope='synthetic-lifecycle', corpus='new-corpus', uuid=identity, time='2026-11-02 00:00:00', content=text), vector)

    def test_supersession_withdrawal_retained_views_and_cas(self):
        ref = self.enrolled('original')
        one = self.owner.change(self.command('one'), 'introduce', enrollment=ref)
        self.assertEqual(self.owner.change(self.command('one'), 'introduce', enrollment=ref), one)
        two = self.owner.change(self.command('two'), 'supersede', logical_id=one['logical_id'],
                                expected_revision=1, enrollment=self.enrolled('successor'))
        self.assertEqual(two['predecessor'], one['memory'])
        self.assertFalse(two['empirical_weight_transferred'])
        self.assertFalse(two['priority_transferred'])
        self.assertEqual(two['projection'], 'NOT_OBSERVED')
        self.assertEqual(self.owner.activeSet(one['at'])['active'][0]['uuid'], one['memory']['uuid'])
        with self.assertRaisesRegex(ContractError, 'CONFLICT'):
            self.owner.change(self.command('race'), 'supersede', logical_id=one['logical_id'], expected_revision=1, enrollment=self.enrolled('loser'))
        gone = self.owner.change(self.command('gone'), 'withdraw', logical_id=one['logical_id'], expected_revision=2)
        self.assertEqual(self.owner.activeSet(gone['at'])['active'], [])
        with self.assertRaisesRegex(ContractError, 'UNAUTHORIZED'):
            self.owner.disclose(one['logical_id'], one['memory'], one['at'])
        self.assertTrue(self.owner.disclose(one['logical_id'], one['memory'], one['at'], historical=True)['authorized'])
        self.assertEqual(json.loads(self.atoms.get(one['memory']['payload']).bytes)['content'], 'original')
        self.assertEqual(self.owner.readEvents(0, gone['at'], 2)['next'], 2)
        self.assertTrue(self.owner.readEvents(2, gone['at'], 2)['complete'])

    def test_commit_interruption_replay_and_current_authorization(self):
        def stop(stage):
            if stage == 'after_lifecycle_commit': raise RuntimeError('simulated interruption')
        ref = self.enrolled('committed')
        with self.assertRaises(RuntimeError): self.open(stop).change(self.command('one'), 'introduce', enrollment=ref)
        result = self.open().change(self.command('one'), 'introduce', enrollment=ref)
        self.assertEqual(result['revision'], 1)
        self.access.revoked = True
        with self.assertRaisesRegex(ContractError, 'UNAUTHORIZED'):
            self.owner.change(self.command('one'), 'introduce', enrollment=ref)

    def test_exact_deadline_refuses_new_intent_and_lifecycle_effect(self):
        deadline = 2000; ref = self.enrolled('expires before acceptance')
        before = self.owner.head()
        with patch('fusion.preview_lifecycle.time.time_ns', return_value=deadline*1000000):
            with self.assertRaisesRegex(ContractError, 'DEADLINE_EXCEEDED'):
                self.owner.change(self.command('expired'), 'introduce', enrollment=ref, deadline_ms=deadline)
        self.assertEqual(self.owner.head(), before)
        with closing(self.owner.connect()) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM lifecycle_intents').fetchone()[0], 0)

    def test_bound_intent_cannot_commit_at_expiry_or_renew_its_original_deadline(self):
        deadline = 2000; now = [deadline-1]; ref = self.enrolled('intent bound before expiry')
        def advance(stage):
            if stage == 'after_lifecycle_intent': now[0] = deadline
        owner = self.open(advance)
        with patch('fusion.preview_lifecycle.time.time_ns', side_effect=lambda: now[0]*1000000):
            with self.assertRaisesRegex(ContractError, 'DEADLINE_EXCEEDED'):
                owner.change(self.command('bound'), 'introduce', enrollment=ref, deadline_ms=deadline)
            with self.assertRaisesRegex(ContractError, 'DEADLINE_EXCEEDED'):
                self.open().change(self.command('bound'), 'introduce', enrollment=ref, deadline_ms=deadline)
            with self.assertRaisesRegex(ContractError, 'CONFLICT'):
                self.open().change(self.command('bound'), 'introduce', enrollment=ref, deadline_ms=deadline+1000)
        self.assertEqual(self.owner.head()['sequence'], 0)
        with closing(self.owner.connect()) as db:
            rows = db.execute('SELECT intent,result FROM lifecycle_intents').fetchall()
        self.assertEqual(len(rows), 1); self.assertIsNone(rows[0][1])
        self.assertEqual(json.loads(rows[0][0])['deadline_ms'], deadline)

    def test_captured_receipt_observes_at_expiry_but_new_supersession_withdrawal_refuse(self):
        deadline = 2000; ref = self.enrolled('original visible memory')
        with patch('fusion.preview_lifecycle.time.time_ns', return_value=(deadline-1)*1000000):
            accepted = self.owner.change(self.command('accepted'), 'introduce', enrollment=ref, deadline_ms=deadline)
        replacement = self.enrolled('unused successor'); before = self.owner.head()
        with patch('fusion.preview_lifecycle.time.time_ns', return_value=deadline*1000000):
            self.assertEqual(self.open().change(self.command('accepted'), 'introduce', enrollment=ref,
                deadline_ms=deadline), accepted)
            for operation, enrollment in (('supersede', replacement), ('withdraw', None)):
                with self.subTest(operation=operation), self.assertRaisesRegex(ContractError, 'DEADLINE_EXCEEDED'):
                    self.owner.change(self.command(operation), operation, logical_id=accepted['logical_id'],
                        expected_revision=1, enrollment=enrollment, deadline_ms=deadline)
            self.assertEqual(self.owner.head(), before)
            self.access.revoked = True
            with self.assertRaisesRegex(ContractError, 'UNAUTHORIZED'):
                self.owner.change(self.command('accepted'), 'introduce', enrollment=ref, deadline_ms=deadline)
        self.access.revoked = False
        self.assertEqual(self.owner.activeSet(before)['active'][0]['uuid'], accepted['memory']['uuid'])

    def test_real_chroma_indexes_selected_membership_before_topk(self):
        # This gate requires real pinned Chroma. Unit vectors and file storage
        # remain explicitly substituted; it is not an E5/DeTTa native gate.
        from fusion.adapters.active_chroma import ActiveChroma
        from fusion import preview_vector_contracts as active
        scope = 'synthetic-lifecycle'
        one = self.owner.change(self.command('one'), 'introduce', enrollment=self.enrolled('nearest', 0))
        two = self.owner.change(self.command('two'), 'introduce', enrollment=self.enrolled('second', 1))
        through = self.atoms.head(scope)
        def projection(head):
            return ActiveChroma(self.root/'search', self.atoms, self.atoms, self.access, scope,
                                'new-corpus', v.FIXTURE, self.owner, head)
        first = projection(two['at'])
        first_view = first.build_named(scope, through, 'first', int(time.time()*1000)+30000)
        gone = self.owner.change(self.command('gone'), 'withdraw', logical_id=one['logical_id'], expected_revision=1)
        second = projection(gone['at'])
        current = second.build_named(scope, through, 'second', int(time.time()*1000)+30000)
        request = active.VectorQuery(str(uuid.uuid4()), scope, current, [1.0]+[0.0]*1023, 1, int(time.time()*1000)+30000)
        hits = second.query(request)['hits']
        self.assertEqual([hit['uuid'] for hit in hits], [two['memory']['uuid']])
        # Re-publishing an older same-source-head lifecycle epoch is retained but
        # cannot replace the selected active visibility epoch.
        first._publish(scope, first._verified(first_view['generation'], through), None)
        self.assertEqual(second.current(), current)
        with self.assertRaisesRegex(ContractError, 'UNAUTHORIZED'):
            first.query(active.VectorQuery(str(uuid.uuid4()), scope, first_view, [1.0]+[0.0]*1023, 1, int(time.time()*1000)+30000))
        rebuilt = second.build_named(scope, through, 'rebuild', int(time.time()*1000)+30000)
        self.assertEqual(rebuilt['logical'], current['logical'])
        with self.assertRaises(ContractError): v.snapshot(current, scope)


if __name__ == '__main__': unittest.main()
