"""Bounded owner races on fresh local files; no deployed/runtime claim.

Lifecycle uses real independent SQLite transactions for two authorized caller
fixtures. Immutable storage is explicitly FileFeedFixture with unit-vector
enrollments, not DeTTa, Chroma or E5. Workspace uses real local files, descriptor
relative opens, atomic rename and SQLite; adversarial filesystem changes are
injected at controlled boundaries rather than relying on scheduling luck.
No native agent, HTTPS, cluster, private data or generative runtime is used.
"""
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest
from unittest.mock import patch

from fusion.adapters.fixture_feed import FileFeedFixture
from fusion.contracts import ContractError, require
from fusion.ports import Mutation
from fusion.preview_lifecycle import MemoryLifecycle
from fusion.preview_workspace import Workspace
from fusion import vector_contracts as vector
from fusion.vector_enrollment import enroll


SCOPE = 'synthetic-owner-race-fixture'
CORPUS = 'owner-race-fixture'


class PrincipalFixture:
    def __init__(self, principal): self.principal = principal

    def authorize(self, scope, operation):
        require(scope == SCOPE, 'UNAUTHORIZED')
        return self.principal


class LifecycleCASRaces(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='phase2-lifecycle-races-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.atoms = FileFeedFixture(self.root/'fixture-atoms.json', PrincipalFixture('storage-fixture'))
        self.database = self.root/'lifecycle.sqlite'
        self.owner = self.open('A')

    def open(self, principal, hook=lambda _: None):
        return MemoryLifecycle(self.database, self.atoms, PrincipalFixture(principal),
            SCOPE, CORPUS, hook, embedding=vector.FIXTURE)

    def enrollment(self, identity):
        import uuid
        return enroll(self.atoms, SCOPE, CORPUS, vector.FIXTURE, identity,
            dict(scope=SCOPE, corpus=CORPUS, uuid=str(uuid.uuid4()),
                 time='2026-11-02 12:00:00', content='Synthetic '+identity), [1.0]+[0.0]*1023)

    def race(self, operations):
        original_ref = self.enrollment('original')
        original = self.owner.change(Mutation(SCOPE, 'introduce'), 'introduce', enrollment=original_ref)
        barrier = threading.Barrier(2, timeout=3)

        def accepted(stage):
            if stage == 'after_lifecycle_intent': barrier.wait()

        actors = [self.open(who, accepted) for who in ('A','B')]
        enrollments = [self.enrollment('successor-'+str(index)) if operation=='supersede' else None
                       for index, operation in enumerate(operations)]
        source_before = self.atoms.head(SCOPE)
        bytes_before = self.atoms.path.read_bytes()

        def compete(index):
            try:
                return 'PASS', actors[index].change(Mutation(SCOPE, 'race-'+str(index)), operations[index],
                    logical_id=original['logical_id'], expected_revision=1, enrollment=enrollments[index])
            except ContractError as error:
                return 'REFUSED', error.code

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(compete, index) for index in range(2)]
            outcomes = [future.result(timeout=6) for future in futures]
        self.assertEqual(sorted(value[0] for value in outcomes), ['PASS','REFUSED'])
        winner = next(index for index, value in enumerate(outcomes) if value[0]=='PASS')
        loser = 1-winner
        self.assertEqual(outcomes[loser], ('REFUSED','CONFLICT'))
        result = outcomes[winner][1]
        self.assertEqual(result['revision'], 2)
        self.assertEqual(result['operation'], operations[winner])
        self.assertEqual(result['logical_id'], original['logical_id'])
        self.assertFalse(result['empirical_weight_transferred'])
        self.assertFalse(result['priority_transferred'])
        head = self.owner.head()
        self.assertEqual(head['sequence'], 2)
        events = self.owner.readEvents(0, head, 8)['events']
        self.assertEqual(events, [original, result])
        self.assertEqual(self.owner.activeSet(original['at'])['active'][0]['uuid'], original['memory']['uuid'])
        selected = self.owner.activeSet(head)['active']
        self.assertEqual([entry['uuid'] for entry in selected],
            [] if operations[winner]=='withdraw' else [result['memory']['uuid']])
        self.assertEqual(self.atoms.head(SCOPE), source_before)
        self.assertEqual(self.atoms.path.read_bytes(), bytes_before)
        with sqlite3.connect(self.database) as db:
            pending = db.execute('SELECT intent,result FROM lifecycle_intents').fetchall()
        self.assertEqual(len(pending), 3)
        self.assertEqual(sum(receipt is None for _, receipt in pending), 1)

        # Reopening cannot turn the stale contender into another head, and the
        # accepted winner replays its original result without a new event.
        for index in (winner, loser):
            reopened = self.open(('A','B')[index])
            args = dict(logical_id=original['logical_id'], expected_revision=1, enrollment=enrollments[index])
            if index == winner:
                self.assertEqual(reopened.change(Mutation(SCOPE, 'race-'+str(index)), operations[index], **args), result)
            else:
                with self.assertRaises(ContractError) as caught:
                    reopened.change(Mutation(SCOPE, 'race-'+str(index)), operations[index], **args)
                self.assertEqual(caught.exception.code, 'CONFLICT')
        self.assertEqual(self.owner.head(), head)
        self.assertEqual(self.owner.readEvents(0, head, 8)['events'], events)
        self.assertEqual(self.atoms.path.read_bytes(), bytes_before)

    def test_two_callers_superseding_same_head_have_one_commit_and_durable_conflict(self):
        self.race(('supersede','supersede'))

    def test_two_callers_update_withdraw_race_preserves_one_head_and_old_view(self):
        self.race(('supersede','withdraw'))


class WorkspacePathRaces(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='phase2-workspace-races-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def authorize(self, principal, scope, operation):
        require(principal=='A' and scope==SCOPE, 'UNAUTHORIZED')

    def test_leaf_symlink_swap_at_pre_rename_check_refuses_without_outside_effect(self):
        directory = self.root/'workspace'
        owner = Workspace(directory, self.root/'workspace.sqlite', self.authorize, scope=SCOPE)
        self.addCleanup(owner.close)
        first = owner.mutate('A', SCOPE, 'first', 'write', 'note', 'original', 0)
        outside = self.root/'outside-synthetic'; outside.write_bytes(b'outside untouched')
        original_read = owner._read
        reads = []

        def swap_at_final_check(name):
            reads.append(name)
            if len(reads)==3:
                # Validation and intent/effect preparation already happened.
                # Replace only the directory entry; never the outside content.
                (directory/name).unlink()
                (directory/name).symlink_to(outside)
            return original_read(name)

        with patch.object(owner, '_read', side_effect=swap_at_final_check), \
                patch('fusion.preview_workspace.os.replace', wraps=os.replace) as rename:
            with self.assertRaises(ContractError) as caught:
                owner.mutate('A', SCOPE, 'append', 'append', 'note', ' extra', 1)
        self.assertEqual(caught.exception.code, 'UNAUTHORIZED')
        self.assertEqual(reads, ['note','note','note'])
        rename.assert_not_called()
        self.assertEqual(outside.read_bytes(), b'outside untouched')
        self.assertFalse(list(directory.glob('.stage-*')))
        file_row = owner.db.execute('SELECT revision,digest FROM workspace_files WHERE name=?', ('note',)).fetchone()
        self.assertEqual(tuple(file_row), (1,first['digest']))
        effects = owner.db.execute('SELECT intent,receipt FROM workspace_effects ORDER BY rowid').fetchall()
        self.assertEqual(len(effects), 2)
        self.assertIsNotNone(effects[0]['receipt'])
        self.assertIsNone(effects[1]['receipt'])
        self.assertEqual(json.loads(effects[1]['intent'])['revision'], 1)

    def test_replaced_workspace_path_cannot_redirect_open_directory_effect(self):
        directory = self.root/'workspace'
        held = self.root/'original-directory'
        outside = self.root/'outside-directory'; outside.mkdir()
        (outside/'note').write_bytes(b'outside untouched')

        def replace_root(stage):
            if stage=='after_workspace_intent':
                directory.rename(held)
                directory.symlink_to(outside, target_is_directory=True)

        owner = Workspace(directory, self.root/'workspace.sqlite', self.authorize, scope=SCOPE)
        self.addCleanup(owner.close)
        owner.mutate('A', SCOPE, 'first', 'write', 'note', 'original', 0)
        owner.hook = replace_root
        receipt = owner.mutate('A', SCOPE, 'append', 'append', 'note', ' extra', 1)
        self.assertEqual(receipt['revision'], 2)
        self.assertEqual((held/'note').read_bytes(), b'original extra\n')
        self.assertEqual((outside/'note').read_bytes(), b'outside untouched')
        self.assertEqual(owner.read('A', SCOPE, 'note')['text'], 'original extra\n')
        self.assertEqual(owner.mutate('A', SCOPE, 'append', 'append', 'note', ' extra', 1), receipt)
        self.assertEqual((held/'note').read_bytes(), b'original extra\n')


if __name__ == '__main__':
    unittest.main()
