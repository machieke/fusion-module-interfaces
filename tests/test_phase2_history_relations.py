"""Preview owner qualification with explicit FileFeedFixture storage.

These are real durable C1/Relations owner transitions over a CONTRACT FIXTURE,
not DeTTa, native-loop, HTTPS or process-kill integration evidence. Interrupted
hooks below simulate loss of control at a named commit boundary and reopen the
actual persisted owner. No private stores or generative runtimes are accessed.
"""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import tempfile
import threading
import unittest

from fusion.adapters.fixture_feed import FileFeedFixture
from fusion.contracts import ContractError, canonical, digest, require
from fusion import lookup_contracts as lookup, memory_contracts as memory
from fusion.policy import Policy
from fusion.ports import Mutation
from fusion.preview_history import SessionHistoryOwner, PROFILE as HISTORY_PROFILE, CONTENT_TYPE as HISTORY_CONTENT, KINDS
from fusion.preview_relations import RetractableRelations, PROFILE as RELATION_PROFILE


SCOPE = 'synthetic-preview-owner-tests'
TIME = '2026-11-02T12:00:00Z'


class CurrentTestAuthority:
    """Declared authorization fixture using the existing live Policy checks."""
    def __init__(self, path, interface, profile):
        self.policy = Policy(path)
        self.interface, self.profile = interface, profile

    def authorize(self, scope, operation):
        principal = self.policy.authenticate('synthetic-owner-token')
        self.policy.check(principal, scope, self.interface+'.'+operation)
        return principal

    def selection(self):
        return digest(canonical([self.interface, self.profile]))

    def origin(self, scope, source):
        # History must suppress roots even if a source could otherwise mint one.
        self.authorize(scope, 'appendEvent')
        return 'synthetic-independent-source'


class OwnerFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='phase2-owner-fixture-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.policy_path = self.root/'policy.json'
        self.operations = {
            'atom.storage': ['create', 'get', 'getMany', 'availability', 'head', 'readCommits'],
            'episodic.memory': ['recordEpisode', 'appendEvent', 'readEpisode', 'readEvidence', 'pendingEvidence'],
            'relations': ['assertRelation', 'getRelation', 'retract', 'outgoing', 'incoming', 'history'],
        }
        self.config = {'principals': {'owner': {'credential': 'synthetic-owner-token', 'scopes': {
            SCOPE: [name+'.'+op for name, ops in self.operations.items() for op in ops]}}}}
        self.save_policy()
        self.atom_access = CurrentTestAuthority(self.policy_path, 'atom.storage', lookup.FEED)
        self.history_access = CurrentTestAuthority(self.policy_path, 'episodic.memory', HISTORY_PROFILE)
        self.relation_access = CurrentTestAuthority(self.policy_path, 'relations', RELATION_PROFILE)
        self.atoms = FileFeedFixture(self.root/'fixture-atoms.json', self.atom_access)

    def save_policy(self):
        # Atomic replacement keeps concurrent current-authorization reads valid.
        candidate = self.policy_path.with_suffix('.new')
        candidate.write_bytes(canonical(self.config))
        candidate.replace(self.policy_path)

    def revoke(self, *methods):
        permissions = self.config['principals']['owner']['scopes'][SCOPE]
        for method in methods:
            if method in permissions: permissions.remove(method)
        self.save_policy()

    def error(self, code, callback, *args, **kwargs):
        with self.assertRaises(ContractError) as caught: callback(*args, **kwargs)
        self.assertEqual(caught.exception.code, code)

    def payload(self, identity, text='generated synthetic payload'):
        written = self.atoms.create(Mutation(SCOPE, identity), 'text/plain', text.encode())
        self.assertEqual(written['receipt']['provider'], 'contract-fixture-files/1')
        return written['ref']

    def history(self, hook=lambda _: None):
        return SessionHistoryOwner(self.root/'history.sqlite', self.atoms, self.history_access, hook=hook)

    def relations(self, hook=lambda _: None):
        return RetractableRelations(self.root/'relations.sqlite', self.atoms, self.relation_access, lookup.SCHEMAS, hook)


class PreviewHistory(OwnerFixture):
    def setUp(self):
        super().setUp()
        self.owner = self.history()
        self.episode = self.owner.recordEpisode(Mutation(SCOPE, 'session-episode'), 'native-agent-A')['ref']

    def append(self, number, kind='input-receipt', *, expected=None, owner=None, payload=None, causation=None):
        owner = owner or self.owner
        return owner.appendHistory(Mutation(SCOPE, 'event-'+str(number)), self.episode,
            number-1 if expected is None else expected, 'occurrence-'+str(number), kind,
            payload or self.payload('payload-'+str(number)), causation or [], TIME)

    def test_distinct_kinds_causation_no_independence_or_delivery(self):
        receipts = []
        for number, kind in enumerate(sorted(KINDS), 1):
            previous = [receipts[-1]['evidence']['event_ref']] if receipts else []
            receipts.append(self.append(number, kind, causation=previous))
        snapshot = self.owner.historySnapshot(self.episode)
        page = self.owner.readHistory(snapshot, 1, 16)
        self.assertEqual([entry['kind'] for entry in page['events']], sorted(KINDS))
        self.assertFalse(page['evidence_weight_created'])
        self.assertEqual(page['ordering'], 'owner-commit-sequence')
        for index, entry in enumerate(page['events']):
            event = entry['event']
            self.assertEqual(event['lineage_roots'], [])
            self.assertEqual(event['event']['provenance'], [])
            self.assertIsNone(event['event']['numerical'])
            self.assertEqual(event['event']['causation'], [] if index == 0 else [receipts[index-1]['evidence']['event_ref']])
            self.assertIsNone(receipts[index]['delivery_id'])
        self.assertEqual(self.owner.pendingEvidence(self.episode, 16), ())

    def test_equal_text_distinct_occurrences_duplicate_replay_and_conflict(self):
        shared = self.payload('same-payload', 'identical observed text')
        first = self.append(1, payload=shared)
        self.assertEqual(self.append(1, payload=shared), first)
        second = self.append(2, payload=shared)
        self.assertNotEqual(first['evidence']['occurrence_id'], second['evidence']['occurrence_id'])
        self.assertEqual(self.owner.historySnapshot(self.episode)['through'], 2)
        self.error('CONFLICT', self.append, 1, 'model-proposal', payload=shared)
        self.error('CONFLICT', self.append, 3, expected=0)
        self.assertEqual(self.owner.historySnapshot(self.episode)['through'], 2)

    def test_fixed_snapshot_pagination_and_restart(self):
        for number in range(1, 6): self.append(number)
        snapshot = self.owner.historySnapshot(self.episode)
        first = self.owner.readHistory(snapshot, 1, 2)
        self.append(6)
        reopened = self.history()
        second = reopened.readHistory(snapshot, first['next_sequence'], 2)
        last = reopened.readHistory(snapshot, second['next_sequence'], 2)
        entries = first['events']+second['events']+last['events']
        self.assertEqual([entry['event']['evidence']['sequence'] for entry in entries], [1, 2, 3, 4, 5])
        self.assertTrue(last['complete'])
        self.assertIsNone(last['next_sequence'])
        self.assertEqual(last['snapshot'], snapshot)
        self.assertEqual(reopened.historySnapshot(self.episode)['through'], 6)
        self.assertEqual(reopened.readHistory(snapshot, 6, 1)['events'], [])
        self.error('INVALID_ARGUMENT', reopened.readHistory, snapshot, 0, 1)
        self.error('INVALID_ARGUMENT', reopened.readHistory, snapshot, 1, 17)

    def test_current_authority_snapshot_binding_and_wrong_owner(self):
        self.append(1)
        snapshot = self.owner.historySnapshot(self.episode)
        self.error('UNSUPPORTED_PROFILE', self.owner.readHistory, dict(snapshot, selection='stale'), 1, 1)
        self.error('NOT_AVAILABLE', self.owner.readHistory, dict(snapshot, through=2), 1, 1)
        original = json.loads(json.dumps(self.config))
        self.config['principals']['other'] = self.config['principals'].pop('owner')
        self.save_policy()
        self.error('UNAUTHORIZED', self.owner.readHistory, snapshot, 1, 1)
        self.config = original
        self.save_policy()
        self.revoke('episodic.memory.readEpisode')
        self.error('UNAUTHORIZED', self.owner.readHistory, snapshot, 1, 1)
        self.error('UNAUTHORIZED', self.owner.historySnapshot, self.episode)
        self.revoke('episodic.memory.appendEvent')
        self.error('UNAUTHORIZED', self.append, 1)

    def test_concurrent_append_cas_has_one_commit_and_replayable_loser(self):
        payloads = [self.payload('concurrent-'+str(i)) for i in range(2)]
        barrier = threading.Barrier(2)
        def append(index):
            owner = self.history()
            barrier.wait(timeout=5)
            try:
                return owner.appendHistory(Mutation(SCOPE, 'concurrent-'+str(index)), self.episode,
                    0, 'concurrent-occurrence-'+str(index), 'tool-result', payloads[index], [], TIME)
            except ContractError as exc: return exc.code
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(append, range(2)))
        self.assertEqual(sum(isinstance(result, dict) for result in results), 1)
        self.assertEqual(results.count('CONFLICT'), 1)
        self.assertEqual(self.owner.historySnapshot(self.episode)['through'], 1)
        loser = results.index('CONFLICT')
        receipt = self.owner.appendHistory(Mutation(SCOPE, 'concurrent-'+str(loser)), self.episode,
            1, 'concurrent-occurrence-'+str(loser), 'tool-result', payloads[loser], [], TIME)
        self.assertEqual(receipt['head'], 2)
        self.assertEqual(self.owner.appendHistory(Mutation(SCOPE, 'concurrent-'+str(loser)), self.episode,
            1, 'concurrent-occurrence-'+str(loser), 'tool-result', payloads[loser], [], TIME), receipt)

    def test_history_interruption_after_payload_or_owner_commit(self):
        for number, stage in enumerate(('after_payload_persist', 'after_episode_commit'), 1):
            with self.subTest(stage=stage):
                payload = self.payload('interrupt-payload-'+str(number))
                def interrupt(observed):
                    if observed == stage: raise RuntimeError('simulated interruption: '+stage)
                with self.assertRaises(RuntimeError): self.append(number, owner=self.history(interrupt), payload=payload)
                recovered = self.history()
                receipt = self.append(number, owner=recovered, payload=payload)
                self.assertEqual(receipt['head'], number)
                self.assertEqual(self.append(number, owner=recovered, payload=payload), receipt)
                self.assertEqual(recovered.historySnapshot(self.episode)['through'], number)

    def test_history_rejects_unknown_kind_and_unwrapped_events(self):
        payload = self.payload('raw-payload')
        self.error('UNSUPPORTED_OPERATION', self.owner.appendHistory, Mutation(SCOPE, 'unknown'), self.episode,
            0, 'unknown', 'fabricated-kind', payload, [], TIME)
        raw = dict(occurrence_id='raw', kind='observation', source='some-origin', observed_time=TIME,
            payload=payload, causation=[], provenance=[], numerical=None)
        self.error('UNSUPPORTED_PROFILE', self.owner.appendEvent, Mutation(SCOPE, 'raw'), self.episode, 0, raw)
        self.assertEqual(self.owner.historySnapshot(self.episode)['through'], 0)

    def test_history_refuses_cross_scope_nested_payload_even_when_both_readable(self):
        foreign = 'synthetic-other-scope'
        self.config['principals']['owner']['scopes'][foreign] = list(self.config['principals']['owner']['scopes'][SCOPE])
        self.save_policy()
        payload = self.atoms.create(Mutation(foreign, 'payload'), 'text/plain', b'other-scope data')['ref']
        self.error('UNAUTHORIZED', self.owner.appendHistory, Mutation(SCOPE, 'foreign'), self.episode,
            0, 'foreign', 'tool-result', payload, [], TIME)
        wrapper = self.atoms.create(Mutation(SCOPE, 'foreign-wrapper'), HISTORY_CONTENT,
            canonical(dict(profile=HISTORY_PROFILE, kind='tool-result', payload=payload)))['ref']
        event = dict(occurrence_id='foreign-direct', kind='result', source='native-session-history', observed_time=TIME,
            payload=wrapper, causation=[], provenance=[], numerical=None)
        self.error('UNAUTHORIZED', self.owner.appendEvent, Mutation(SCOPE, 'foreign-direct'), self.episode, 0, event)
        self.assertEqual(self.owner.historySnapshot(self.episode)['through'], 0)

    def test_history_numerical_assessment_cannot_be_smuggled_through_base_append(self):
        payload = self.payload('wrapped-body')
        wrapper = self.atoms.create(Mutation(SCOPE, 'wrapper'), HISTORY_CONTENT,
            canonical(dict(profile=HISTORY_PROFILE, kind='model-proposal', payload=payload)))['ref']
        event = dict(occurrence_id='numerical', kind='action', source='native-session-history', observed_time=TIME,
            payload=wrapper, causation=[], provenance=[], numerical=dict(claim=payload, context='synthetic-context',
                relationship='reports', truth=None, ingestion_profile=memory.INGESTION))
        self.error('UNSUPPORTED_PROFILE', self.owner.appendEvent, Mutation(SCOPE, 'numerical'), self.episode, 0, event)
        self.assertEqual(self.owner.historySnapshot(self.episode)['through'], 0)


class PreviewRelations(OwnerFixture):
    def setUp(self):
        super().setUp()
        self.owner = self.relations()
        self.a, self.b, self.c = [self.payload('node-'+letter, letter) for letter in 'abc']
        self.roles = (('dependent', self.a), ('prerequisite', self.b))

    def assertion(self, key='edge', *, owner=None, roles=None):
        return (owner or self.owner).assertRelation(Mutation(SCOPE, key), 'requires/1', roles or self.roles, True)

    def test_assert_retract_replay_and_relink_are_distinct_occurrences(self):
        first = self.assertion()
        self.assertEqual(self.assertion(), first)
        self.assertEqual(self.owner.outgoing(self.a, 8)['refs'], [first['ref']])
        original_payload = self.atoms.get(first['ref']).bytes
        command = Mutation(SCOPE, 'unlink')
        removed = self.owner.retract(command, first['ref'], first['asserted_at'])
        self.assertEqual(self.owner.retract(command, first['ref'], first['asserted_at']), removed)
        self.assertFalse(removed['evidence_changed'])
        self.assertFalse(removed['payload_erased'])
        self.assertEqual(self.atoms.get(first['ref']).bytes, original_payload)
        self.assertEqual(self.owner.outgoing(self.a, 8)['refs'], [])
        self.error('NOT_FOUND', self.owner.getRelation, first['ref'])
        self.assertEqual(self.owner.getRelation(first['ref'], historical=True)['state'], 'retracted')
        # Replaying the old assertion is not a new link; a new key is required.
        self.assertEqual(self.assertion(), first)
        self.assertEqual(self.owner.outgoing(self.a, 8)['refs'], [])
        second = self.assertion('relink')
        self.assertNotEqual(second['ref'], first['ref'])
        self.assertNotEqual(second['body']['assertion_id'], first['body']['assertion_id'])
        self.assertEqual(self.owner.outgoing(self.a, 8)['refs'], [second['ref']])

    def test_conflicts_and_ordered_roles(self):
        first = self.assertion()
        self.error('CONFLICT', self.assertion, roles=(('dependent', self.b), ('prerequisite', self.a)))
        self.error('INVALID_ARGUMENT', self.assertion, 'bad-order', roles=(('prerequisite', self.a), ('dependent', self.b)))
        self.assertEqual(self.owner.incoming(self.b, 8)['refs'], [first['ref']])
        self.assertEqual(self.owner.incoming(self.a, 8)['refs'], [])
        self.assertEqual(self.owner.outgoing(self.b, 8)['refs'], [])
        wrong = dict(first['asserted_at'], sequence=0)
        self.error('CONFLICT', self.owner.retract, Mutation(SCOPE, 'wrong-state'), first['ref'], wrong)
        self.owner.retract(Mutation(SCOPE, 'remove'), first['ref'], first['asserted_at'])
        self.error('CONFLICT', self.owner.retract, Mutation(SCOPE, 'another-remove'), first['ref'], first['asserted_at'])
        self.error('CONFLICT', self.owner.retract, Mutation(SCOPE, 'edge'), first['ref'], first['asserted_at'])

    def test_undirected_selflink_and_foreign_scope_are_explicit(self):
        edge = self.owner.assertRelation(Mutation(SCOPE, 'self'), 'association/1',
            (('first', self.a), ('second', self.a)), False)
        self.assertEqual(self.owner.outgoing(self.a, 8)['refs'], [edge['ref']])
        self.assertEqual(self.owner.incoming(self.a, 8)['refs'], [edge['ref']])
        self.error('UNAUTHORIZED', self.assertion, 'foreign', roles=(
            ('dependent', self.a), ('prerequisite', dict(self.b, scope_ref='synthetic-other-scope'))))
        self.error('UNSUPPORTED_PROFILE', self.owner.assertRelation, Mutation(SCOPE, 'schema'),
            'unknown-schema/1', self.roles, True)

    def test_historical_assertion_only_database_is_not_implicitly_migrated(self):
        from fusion.relations import RelationOwner
        old = self.root/'historical-relations.sqlite'
        historical = RelationOwner(old, self.atoms, self.relation_access, lookup.SCHEMAS)
        original = historical.assertRelation(Mutation(SCOPE, 'historical'), 'requires/1', self.roles, True)
        self.error('UNSUPPORTED_PROFILE', RetractableRelations, old, self.atoms, self.relation_access, lookup.SCHEMAS)
        self.assertEqual(historical.getRelation(original['ref']), original)

    def test_historical_page_continuity_across_retraction_and_new_assertion(self):
        edges = [self.assertion('page-'+str(i)) for i in range(4)]
        first = self.owner.outgoing(self.a, 2)
        self.owner.retract(Mutation(SCOPE, 'remove-third'), edges[2]['ref'], edges[2]['asserted_at'])
        added = self.assertion('late')
        reopened = self.relations()
        second = reopened.outgoing(self.a, 2, first['cursor'])
        self.assertEqual(first['refs']+second['refs'], [edge['ref'] for edge in edges])
        self.assertEqual(second['at'], first['at'])
        self.assertTrue(second['page_complete'])
        current = reopened.outgoing(self.a, 8)
        self.assertEqual(current['refs'], [edges[i]['ref'] for i in (0, 1, 3)]+[added['ref']])
        self.error('CONFLICT', reopened.incoming, self.b, 2, first['cursor'])
        self.error('CONFLICT', reopened.outgoing, self.a, 1, first['cursor'])
        self.error('INVALID_ARGUMENT', reopened.outgoing, self.a, 2, 'broken')

    def test_current_authority_applies_to_replays_and_historical_reads(self):
        first = self.assertion()
        snapshot = self.owner.outgoing(self.a, 1)['at']
        removed = self.owner.retract(Mutation(SCOPE, 'remove'), first['ref'], first['asserted_at'])
        self.revoke('relations.history')
        self.error('UNAUTHORIZED', self.owner.getRelation, first['ref'], historical=True)
        self.error('UNAUTHORIZED', self.owner.outgoing, self.a, 1, snapshot=snapshot)
        self.revoke('relations.retract')
        self.error('UNAUTHORIZED', self.owner.retract, Mutation(SCOPE, 'remove'), first['ref'], first['asserted_at'])
        self.assertEqual(removed['state'], 'retracted')
        self.revoke('relations.assertRelation', 'relations.outgoing')
        self.error('UNAUTHORIZED', self.assertion)
        self.error('UNAUTHORIZED', self.owner.outgoing, self.a, 1)

    def test_assertion_interruption_payload_and_commit_reuses_one_acceptance(self):
        for number, stage in enumerate(('after_relation_payload', 'after_relation_commit')):
            with self.subTest(stage=stage):
                def interrupt(observed):
                    if observed == stage: raise RuntimeError('simulated interruption: '+stage)
                with self.assertRaises(RuntimeError): self.assertion('interrupted-'+str(number), owner=self.relations(interrupt))
                recovered = self.relations()
                result = self.assertion('interrupted-'+str(number), owner=recovered)
                self.assertEqual(self.assertion('interrupted-'+str(number), owner=recovered), result)
                self.assertEqual(result['asserted_at']['sequence'], number+1)
                self.assertEqual(len(recovered.outgoing(self.a, 8)['refs']), number+1)

    def test_retraction_interruption_commit_preserves_exact_receipt(self):
        first = self.assertion()
        def interrupt(stage):
            if stage == 'after_retraction_commit': raise RuntimeError('simulated interruption')
        with self.assertRaises(RuntimeError):
            self.relations(interrupt).retract(Mutation(SCOPE, 'remove'), first['ref'], first['asserted_at'])
        reopened = self.relations()
        receipt = reopened.retract(Mutation(SCOPE, 'remove'), first['ref'], first['asserted_at'])
        self.assertEqual(receipt['at']['sequence'], 2)
        self.assertEqual(reopened.retract(Mutation(SCOPE, 'remove'), first['ref'], first['asserted_at']), receipt)
        self.assertEqual(reopened.outgoing(self.a, 8)['refs'], [])

    def test_traverse_retract_race_is_one_snapshot_and_old_view_retains_assertion(self):
        first = self.assertion()
        snapshot = self.owner.outgoing(self.a, 1)['at']
        barrier = threading.Barrier(2)
        def traverse():
            barrier.wait(timeout=5)
            return self.relations().outgoing(self.a, 1)
        def retract():
            barrier.wait(timeout=5)
            return self.relations().retract(Mutation(SCOPE, 'remove'), first['ref'], first['asserted_at'])
        with ThreadPoolExecutor(max_workers=2) as pool:
            observation = pool.submit(traverse)
            removal = pool.submit(retract)
            page, receipt = observation.result(timeout=10), removal.result(timeout=10)
        self.assertIn(page['refs'], ([], [first['ref']]))
        self.assertEqual(page['refs'], [first['ref']] if page['at']['sequence'] == 1 else [])
        self.assertEqual(receipt['state'], 'retracted')
        self.assertEqual(self.owner.outgoing(self.a, 1, snapshot=snapshot)['refs'], [first['ref']])


if __name__ == '__main__': unittest.main()
