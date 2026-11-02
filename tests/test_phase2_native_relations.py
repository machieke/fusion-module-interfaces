"""Native relation-adapter tests over real C1/Relations owner transitions.

AtomStorage is explicitly FileFeedFixture. Application, selected-memory view,
lifecycle authorization and direct port transports are declared fixtures. No
native runtime, E5, Chroma, HTTPS, cluster or process-kill claim is made. Named
hook exceptions and owner reopening exercise durable interruption boundaries.
"""
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
from fusion.contracts import ContractError, canonical, digest, require
from fusion.ports import Mutation
from fusion.preview_handles import make, parse
from fusion.preview_history import SessionHistoryOwner
from fusion.preview_native_history import NativeHistory
from fusion.preview_native_relations import NativeRelations, SCHEMAS
from fusion.preview_ports import descriptor
from fusion.preview_relations import RetractableRelations, PROFILE
from fusion.registry import selection_token


SCOPE = 'synthetic-native-relation-tests'
NOW = 1793620800000


class AuthorityFixture:
    def __init__(self, interface):
        self.interface, self.denied = interface, set()

    def authorize(self, scope, operation):
        require(scope == SCOPE and operation not in self.denied, 'UNAUTHORIZED')
        return 'A'

    def selection(self): return selection_token(descriptor(self.interface))
    def origin(self, scope, source): return None


class DirectOwnerPort:
    """Exact method calls; explicitly not network transport evidence."""
    def __init__(self, owner, access):
        self.owner, self.access, self.calls = owner, access, []
        self.transform = lambda operation, value: value

    def call(self, operation, *args, deadline=None):
        self.calls.append((operation, copy.deepcopy(args), deadline))
        if operation == 'authorize':
            self.access.authorize(SCOPE, args[0])
            value = {'authorized': True}
        elif operation in ('outgoing', 'incoming'):
            value = self.owner.traverse(operation, *args)
        elif operation == 'assertRelation':
            command, schema, roles, directed = args
            value = self.owner.assertRelation(command, schema, tuple(tuple(x) for x in roles), directed)
        else: value = getattr(self.owner, operation)(*args)
        return self.transform(operation, copy.deepcopy(value))


class LifecycleFixture:
    def __init__(self, member): self.member, self.allowed, self.calls = member, True, []
    def call(self, operation, *args):
        self.calls.append((operation, copy.deepcopy(args)))
        require(self.allowed, 'UNAUTHORIZED')
        head = dict(profile='immutable-memory-lifecycle/1', scope_ref=SCOPE,
                    source='11111111-1111-4111-8111-111111111111', sequence=1)
        if operation == 'head': return head
        require(operation == 'disclose' and args == (self.member['logical_id'], dict(uuid=self.member['uuid'],
            payload=self.member['envelope']['target']['payload'], enrollment=self.member['envelope']['target']['enrollment']), head, False), 'UNAUTHORIZED')
        return {'authorized': True}


class SelectedMemoryFixture:
    def __init__(self, atoms, member):
        self.storage, self.member = atoms, member
        self.clients = {'memory.lifecycle': LifecycleFixture(member)}

    def resolve(self, handle):
        parse(handle, 'memory')
        require(handle == self.member['envelope']['handle'], 'NOT_FOUND')
        return copy.deepcopy(self.member)

    def atoms(self, deadline=None): return self.storage


class NativeRelationAdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='phase2-native-relations-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.atom_access = AuthorityFixture('atom.storage')
        self.history_access = AuthorityFixture('episodic.memory')
        self.relation_access = AuthorityFixture('relations')
        self.atoms = FileFeedFixture(self.root/'fixture-atoms.json', self.atom_access)
        self.history_owner = SessionHistoryOwner(self.root/'history.sqlite', self.atoms, self.history_access)
        self.relation_owner = RetractableRelations(self.root/'relations.sqlite', self.atoms, self.relation_access, SCHEMAS)
        self.history_port = DirectOwnerPort(self.history_owner, self.history_access)
        self.relation_port = DirectOwnerPort(self.relation_owner, self.relation_access)
        db = sqlite3.connect(self.root/'application-fixture.sqlite')
        db.row_factory = sqlite3.Row
        self.addCleanup(db.close)
        cfg = self.root/'history-atoms-fixture.json'
        cfg.write_bytes(canonical({'boundary': 'FILE_FEED_FIXTURE', 'credential': 'synthetic-unused'}))
        self.app = SimpleNamespace(db=db, preview_config={'scope': SCOPE},
            binding={'principal': 'A', 'history_atoms': {'boundary': 'FILE_FEED_FIXTURE'}},
            config={'history_atoms_config': str(cfg)}, session=str(uuid.uuid4()), hook=lambda stage: None)
        payload = self.atoms.create(Mutation(SCOPE, 'memory-payload'), 'text/plain', b'Synthetic memory')['ref']
        enrollment = self.atoms.create(Mutation(SCOPE, 'memory-enrollment'), 'application/synthetic-enrollment', b'Synthetic enrollment')['ref']
        member = dict(envelope=make('memory', SCOPE, 'A', dict(payload=payload, enrollment=enrollment)),
            logical_id=str(uuid.uuid4()), revision=1, time='2026-11-02 12:00:00', uuid=str(uuid.uuid4()), structure=None)
        self.memory = SelectedMemoryFixture(self.atoms, member)
        self.history = NativeHistory(self.app, self.history_port)
        self.history.atoms = lambda deadline=None: self.atoms
        self.app.preview = SimpleNamespace(memory=self.memory, history=self.history)
        self.native = NativeRelations(self.app, self.relation_port)
        clock = patch('fusion.preview_native_relations.time.time_ns', return_value=NOW*1000000)
        clock.start(); self.addCleanup(clock.stop)
        self.history.record('input-one', 'input-receipt', dict(observed_ms=NOW, text='Synthetic input'),deadline=NOW+120000)
        self.history_view = self.history.read()
        self.event_handle = self.history_view['events'][0]['event_handle']

    def error(self, code, callback, *args, **kwargs):
        with self.assertRaises(ContractError) as caught: callback(*args, **kwargs)
        self.assertEqual(caught.exception.code, code)

    def row(self, identity, result=None, deadline=NOW+20000):
        return dict(id=identity, result=result, deadline=deadline)

    def admit_link(self, identity='link-1', history=None):
        with self.app.db:
            self.native.admit(identity, 'link', dict(memory=self.memory.member['envelope']['handle'],
                                                    history=history or self.event_handle))
        return self.row(identity)

    def link(self, identity='link-1', history=None):
        row = self.admit_link(identity, history)
        result = self.native.replay(row, 'link')
        return row, result, json.loads(result)

    def unlink(self, linked, identity='unlink-1'):
        with self.app.db: self.native.admit(identity, 'unlink', dict(relation=linked['relation']['handle']))
        row = self.row(identity)
        result = self.native.replay(row, 'unlink')
        return row, result, json.loads(result)

    def test_link_event_and_episode_use_actual_owned_handles_without_evidence_weight(self):
        row, _, result = self.link()
        self.assertEqual(result['status'], 'LINKED')
        self.assertFalse(result['evidence_changed'])
        self.assertEqual(result['history']['handle'], self.event_handle)
        self.assertEqual(result['memory'], self.memory.member['envelope'])
        relation = self.relation_owner.getRelation(result['relation']['target'])
        self.assertEqual(relation['body']['structure']['relation_type'], 'memory-event/1')
        _, _, episode = self.link('link-episode', self.history.handle())
        self.assertEqual(self.relation_owner.getRelation(episode['relation']['target'])['body']['structure']['relation_type'], 'memory-episode/1')
        page = self.history_owner.readHistory(self.history_owner.historySnapshot(self.history.episode()), 1, 16)
        self.assertEqual(len(page['events']), 1)
        self.assertEqual(page['events'][0]['event']['lineage_roots'], [])
        self.assertEqual(self.history_owner.pendingEvidence(self.history.episode(), 16), ())

    def test_owner_replay_new_occurrence_and_saved_result_do_not_duplicate_assertions(self):
        row, result, first = self.link()
        head = self.atoms.head(SCOPE)
        self.assertEqual(self.native.replay(row, 'link'), result)
        self.assertEqual(self.atoms.head(SCOPE), head)
        saved = dict(row, result=result, deadline=NOW-1)
        mutations_before = sum(op == 'assertRelation' for op, _, _ in self.relation_port.calls)
        self.assertEqual(self.native.replay(saved, 'link'), result)
        self.assertEqual(sum(op == 'assertRelation' for op, _, _ in self.relation_port.calls), mutations_before)
        _, _, second = self.link('link-new-occurrence')
        self.assertNotEqual(first['relation']['handle'], second['relation']['handle'])
        self.assertEqual(len(self.relation_owner.outgoing(self.memory.member['envelope']['target']['payload'], 8)['refs']), 2)

    def test_query_presentation_uses_traversal_and_unlink_preserves_payload_and_history(self):
        _, _, linked = self.link()
        payload = self.memory.member['envelope']['target']['payload']
        presented = self.native.presentation(payload)
        self.assertEqual(presented['links'][0]['relation'], linked['relation'])
        self.assertEqual(presented['links'][0]['history']['handle'], self.event_handle)
        row, raw, unlinked = self.unlink(linked)
        self.assertEqual(unlinked['status'], 'STRUCTURALLY_RETRACTED')
        self.assertFalse(unlinked['receipt']['payload_erased'])
        self.assertFalse(unlinked['receipt']['evidence_changed'])
        self.assertEqual(self.native.presentation(payload)['links'], [])
        self.assertEqual(self.native.replay(row, 'unlink'), raw)
        self.assertEqual(self.native.replay(dict(row, result=raw, deadline=NOW-1), 'unlink'), raw)
        self.assertEqual(self.atoms.get(payload).bytes, b'Synthetic memory')
        self.assertEqual(self.history_owner.historySnapshot(self.history.episode())['through'], 1)

    def test_foreign_or_wrong_kind_handles_fail_before_relation_mutation(self):
        foreign_episode = make('episode', SCOPE, 'A', dict(scope_ref=SCOPE, id='not-this-session'))['handle']
        foreign_memory = make('memory', SCOPE, 'A', dict(payload=dict(self.memory.member['envelope']['target']['payload'], id='foreign'),
            enrollment=self.memory.member['envelope']['target']['enrollment']))['handle']
        original = self.atoms.head(SCOPE)
        for memory, history, code in ((foreign_memory, self.event_handle, 'NOT_FOUND'),
            (self.memory.member['envelope']['handle'], foreign_episode, 'NOT_FOUND'),
            (self.memory.member['envelope']['handle'], self.memory.member['envelope']['handle'], 'INVALID_ARGUMENT')):
            with self.subTest(code=code), self.app.db:
                self.error(code, self.native.admit, 'bad-link', 'link', dict(memory=memory, history=history))
        self.assertEqual(self.atoms.head(SCOPE), original)
        self.assertEqual(self.app.db.execute('SELECT count(*) FROM preview_link_acceptances').fetchone()[0], 0)

    def test_saved_link_still_checks_current_c1_lifecycle_and_relation_authority(self):
        row, result, _ = self.link()
        saved = dict(row, result=result)
        self.history_access.denied.add('readEpisode')
        self.error('UNAUTHORIZED', self.native.replay, saved, 'link')
        self.history_access.denied.clear()
        self.memory.clients['memory.lifecycle'].allowed = False
        self.error('UNAUTHORIZED', self.native.replay, saved, 'link')
        self.memory.clients['memory.lifecycle'].allowed = True
        self.relation_access.denied.add('assertRelation')
        self.error('UNAUTHORIZED', self.native.replay, saved, 'link')

    def test_independent_owner_commit_loss_replays_one_assertion(self):
        row = self.admit_link()
        def lost(stage):
            if stage == 'after_relation_commit': raise RuntimeError('simulated lost owner response')
        self.relation_owner.hook = lost
        with self.assertRaisesRegex(RuntimeError, 'simulated lost'): self.native.replay(row, 'link')
        self.relation_owner = RetractableRelations(self.root/'relations.sqlite', self.atoms, self.relation_access, SCHEMAS)
        self.relation_port.owner = self.relation_owner
        recovered = NativeRelations(self.app, self.relation_port)
        linked = json.loads(recovered.replay(row, 'link'))
        self.assertEqual(linked['status'], 'LINKED')
        self.assertEqual(len(self.relation_owner.outgoing(self.memory.member['envelope']['target']['payload'], 8)['refs']), 1)
        self.assertEqual(self.app.db.execute('SELECT calls FROM preview_link_calls WHERE id=?', (row['id'],)).fetchone()[0], 2)

    def test_reservation_interruption_spends_budget_before_dispatch_and_survives_reopen(self):
        row = self.admit_link()
        def lost(stage):
            if stage == 'after_relation_rpc_reservation': raise RuntimeError('simulated reservation interruption')
        self.app.hook = lost
        with self.assertRaisesRegex(RuntimeError, 'simulated reservation'): self.native.replay(row, 'link')
        self.assertEqual(sum(op == 'assertRelation' for op, _, _ in self.relation_port.calls), 0)
        self.app.hook = lambda stage: None
        reopened = NativeRelations(self.app, self.relation_port)
        self.assertEqual(json.loads(reopened.replay(row, 'link'))['status'], 'LINKED')
        self.assertEqual(self.app.db.execute('SELECT calls FROM preview_link_calls WHERE id=?', (row['id'],)).fetchone()[0], 2)

    def test_budget_ceiling_and_original_deadline_do_not_dispatch_extra_work(self):
        row = self.row('budget')
        for _ in range(16): self.native.call(row, 'authorize', 'assertRelation')
        calls = len(self.relation_port.calls)
        reopened = NativeRelations(self.app, self.relation_port)
        self.error('OVERLOADED', reopened.call, row, 'authorize', 'assertRelation')
        self.assertEqual(len(self.relation_port.calls), calls)
        self.error('DEADLINE_EXCEEDED', reopened.call, self.row('expired', deadline=NOW-1), 'authorize', 'assertRelation')
        self.assertEqual(len(self.relation_port.calls), calls)
        self.assertEqual(self.app.db.execute('SELECT calls FROM preview_link_calls WHERE id=?', ('budget',)).fetchone()[0], 16)

    def test_malformed_assertion_state_does_not_enter_handle_cache(self):
        row = self.admit_link()
        def change(operation, value):
            if operation == 'assertRelation': value['state'] = 'retracted'
            return value
        self.relation_port.transform = change
        self.error('NOT_AVAILABLE', self.native.replay, row, 'link')
        self.assertEqual(self.app.db.execute('SELECT count(*) FROM preview_link_handles').fetchone()[0], 0)

    def test_malformed_assertion_head_missing_fields_and_extra_authority_are_refused(self):
        _, _, linked = self.link()
        original = self.relation_owner.getRelation(linked['relation']['target'])
        cases = []
        bad = copy.deepcopy(original); bad['asserted_at']['scope_ref'] = 'private-foreign'; cases.append(bad)
        bad = copy.deepcopy(original); bad['asserted_at']['sequence'] = True; cases.append(bad)
        bad = copy.deepcopy(original); del bad['ref']; cases.append(bad)
        bad = copy.deepcopy(original); bad['authorized'] = True; cases.append(bad)
        for index, value in enumerate(cases):
            with self.subTest(case=index): self.error('NOT_AVAILABLE', self.native.checked, value)

    def test_malformed_retraction_effect_is_not_reported_as_success(self):
        _, _, linked = self.link()
        def change(operation, value):
            if operation == 'retract':
                value['effect'] = 'erased-evidence'
                value['at'] = dict(value['at'], scope_ref='private-foreign')
            return value
        self.relation_port.transform = change
        with self.app.db: self.native.admit('bad-retract', 'unlink', {'relation': linked['relation']['handle']})
        self.error('NOT_AVAILABLE', self.native.replay, self.row('bad-retract'), 'unlink')

    def test_valid_but_wrong_endpoint_assertion_is_not_accepted_for_bound_input(self):
        row, _, linked = self.link('first-link')
        old = self.relation_owner.getRelation(linked['relation']['target'])
        row = self.admit_link('wrong-correlation', self.history.handle())
        self.relation_port.transform = lambda operation, value: old if operation == 'assertRelation' else value
        self.error('NOT_AVAILABLE', self.native.replay, row, 'link')

    def test_same_endpoints_do_not_make_a_different_assertion_occurrence_valid(self):
        _, _, linked = self.link('first-link')
        old = self.relation_owner.getRelation(linked['relation']['target'])
        row = self.admit_link('second-distinct-link')
        self.relation_port.transform = lambda operation, value: old if operation == 'assertRelation' else value
        self.error('NOT_AVAILABLE', self.native.replay, row, 'link')

    def test_query_presentation_checks_current_history_authority(self):
        self.link()
        self.history_access.denied.add('readEpisode')
        self.error('UNAUTHORIZED', self.native.presentation, self.memory.member['envelope']['target']['payload'])


if __name__ == '__main__': unittest.main()
