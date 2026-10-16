"""M2 contract fixtures. These do not count as real DeTTa, PLN, or Hive."""
from dataclasses import replace
import json
import sqlite3
import unittest
from unittest.mock import patch

from fusion import memory_contracts as c
from fusion.beliefs import BeliefOwner
from fusion.contracts import ContractError, canonical
from fusion.evidence_relay import EvidenceRelay
from fusion.ports import Mutation, EvidenceSubmission, EpisodicMemory, BeliefRevision
from fusion.private import open_private, OPERATIONS, descriptors
from tests.m2_support import MemoryHarness, PortOnly, SCOPE, truth


class Contracts(unittest.TestCase):
    def setUp(self): self.h = MemoryHarness()
    def tearDown(self): self.h.close()
    def error(self, code, function, *args, **kwargs):
        with self.assertRaises(ContractError) as caught: function(*args, **kwargs)
        self.assertEqual(caught.exception.code, code)

    def test_stable_identity_empty_and_bounded_pages(self):
        e = self.h.episode()
        self.assertEqual(self.h.episodes.readEpisode(e, 1, 4),
            {'ref': e, 'head': 0, 'events': [], 'next_sequence': None, 'complete': True})
        for n in range(3):
            self.h.append(e, self.h.event(occurrence='item-' + str(n), numeric=False), n)
        page = self.h.episodes.readEpisode(e, 1, 2)
        c.episode_page(page, e, 1, 2)
        self.assertFalse(page['complete']); self.assertEqual(page['next_sequence'], 3)
        self.assertEqual([r['evidence']['sequence'] for r in page['events']], [1, 2])
        self.assertNotIn('revision', e)
        self.error('INVALID_ARGUMENT', self.h.episodes.readEpisode, e, 1, 17)
        self.error('INVALID_ARGUMENT', self.h.episodes.readEpisode, e, 5, 1)

    def test_occurrence_replay_before_cas_and_changed_body_conflicts(self):
        e, event = self.h.episode(), self.h.event(numeric=False)
        original = self.h.append(e, event)
        self.assertEqual(self.h.append(e, event, 0), original)
        self.assertEqual(self.h.append(e, event, 0, 'new-request-key'), original)
        self.error('CONFLICT', self.h.append, e, {**event, 'kind': 'result'}, 1, 'changed-request-key')
        different = {**event, 'occurrence_id': 'distinct-occurrence'}
        self.h.append(e, different, 1)
        self.assertEqual(self.h.episodes.readEpisode(e, 1, 16)['head'], 2)
        self.error('CONFLICT', self.h.append, e, {**event, 'occurrence_id': 'third'}, 1)

    def test_live_authority_and_profile_before_replay(self):
        e, event = self.h.episode(), self.h.event(numeric=False)
        self.h.append(e, event)
        self.h.config['principals']['owner']['scopes'][SCOPE].remove('episodic.memory.appendEvent'); self.h.save()
        self.error('UNAUTHORIZED', self.h.append, e, event)
        self.h.config['principals']['owner']['scopes'][SCOPE].append('episodic.memory.appendEvent')
        self.h.config['private_descriptors'][1]['privacy'] = 'non-sensitive-fixture-only'; self.h.save()
        self.error('NOT_AVAILABLE', self.h.append, e, event)

    def test_c1_has_no_revision_dependency_and_no_foreign_sql(self):
        h = MemoryHarness(with_revision=False)
        try:
            e, event = h.episode(), h.event(numeric=False)
            real_connect = sqlite3.connect
            def connect(path, *args, **kwargs):
                self.assertEqual(str(path), str(h.root / 'private/episodes.sqlite'))
                return real_connect(path, *args, **kwargs)
            with patch('sqlite3.connect', connect), patch.dict('sys.modules', {'fusion.adapters.pln_revision': None}):
                h.append(e, event)
                h.reopen()
                self.assertEqual(h.episodes.readEpisode(e, 1, 16)['head'], 1)
            self.assertIsNone(h.beliefs)
        finally: h.close()

    def test_lineage_copy_new_speaker_and_new_key_do_not_create_origins(self):
        e = self.h.episode(); a = self.h.append(e, self.h.event())['evidence']
        b = self.h.append(e, self.h.event(occurrence='copy', source='sensor-b', provenance=[a]), 1)['evidence']
        d = self.h.append(e, self.h.event(occurrence='renamed', source='speaker-a'), 2)['evidence']
        self.assertEqual(self.h.episodes.readEvidence(a)['lineage_roots'], self.h.episodes.readEvidence(b)['lineage_roots'])
        self.assertEqual(self.h.episodes.readEvidence(a)['lineage_roots'], self.h.episodes.readEvidence(d)['lineage_roots'])
        forged = {**a, 'sequence': 2}
        self.error('CONFLICT', self.h.append, e, self.h.event(occurrence='forged', provenance=[forged]), 3)

    def test_report_alternative_and_duplicate_admission(self):
        claim, e = self.h.claim(), self.h.episode()
        report = self.h.append(e, self.h.event(claim, relationship='reports'))['evidence']
        first = self.h.submit(claim, report)
        self.assertEqual(first['numerical'], 'model-inapplicable'); self.assertIsNone(first['snapshot']['truth'])
        a = self.h.append(e, self.h.event(claim, occurrence='assessment'), 1)['evidence']
        initial = self.h.submit(claim, a, key='first')
        b = self.h.append(e, self.h.event(claim, occurrence='contrary', source='sensor-b', strength='0.25', relationship='contradicts'), 2)['evidence']
        contrary = self.h.submit(claim, b, key='second')
        self.assertEqual(contrary['numerical'], 'retained-alternative')
        self.assertEqual(contrary['snapshot']['truth'], initial['snapshot']['truth'])
        self.assertEqual(len(contrary['snapshot']['observations']), 3)
        duplicate = self.h.submit(claim, b, key='new-key')
        self.assertEqual(duplicate['admission'], 'duplicate')
        self.assertEqual(duplicate['snapshot'], contrary['snapshot'])
        self.assertEqual(self.h.submit(claim, report, expected=0), first)
        self.error('CONFLICT', self.h.submit, claim, report, expected=3)
        self.h.reopen()
        self.assertEqual(self.h.beliefs.readBelief(claim, 'generated', 2), initial['snapshot'])

    def test_numeric_domain_and_closed_inputs(self):
        for bad in ('NaN', 'Infinity', '-0.1', '1.1', '0.9999999999999999999999', '1'):
            self.error('INVALID_ARGUMENT', c.truth, truth(confidence=bad))
        c.truth(truth(strength='1', confidence='0'))
        e, event = self.h.episode(), self.h.event()
        self.error('INVALID_ARGUMENT', self.h.append, e, {**event, 'lineage_roots': ['forged']})
        self.error('INVALID_ARGUMENT', self.h.append, e, {**event, 'kind': []})
        self.error('UNSUPPORTED_PROFILE', c.truth, {**truth(), 'model': 'unknown'})

    def test_cross_claim_context_scope_and_unknown_origin(self):
        claim, e = self.h.claim(), self.h.episode()
        ref = self.h.append(e, self.h.event(claim, source='unregistered'))['evidence']
        result = self.h.submit(claim, ref)
        self.assertEqual(result['numerical'], 'model-inapplicable')
        self.assertIsNone(result['snapshot']['truth'])
        self.error('CONFLICT', self.h.submit, self.h.claim('negated', False), ref, key='wrong-claim')
        self.error('CONFLICT', self.h.submit, claim, ref, key='wrong-context', context='other')
        self.error('UNAUTHORIZED', self.h.episodes.readEpisode, {**e, 'scope_ref': 'other'}, 1, 1)

    def test_relay_through_only_declared_ports_and_unavailable_is_pending(self):
        claim, e = self.h.claim(), self.h.episode()
        ref = self.h.append(e, self.h.event(claim))['evidence']
        episodes = PortOnly(self.h.episodes, ('pendingEvidence', 'readEvidence', 'acknowledgeEvidence', 'readEpisode'))
        beliefs = PortOnly(self.h.beliefs, ('submitEvidence', 'readBelief'))
        relay = EvidenceRelay(self.h.root / 'private/relay.sqlite', episodes, beliefs)
        with patch.object(self.h.beliefs, 'submitEvidence', side_effect=ContractError('NOT_AVAILABLE')):
            failed = EvidenceRelay(self.h.root / 'private/relay.sqlite', episodes, self.h.beliefs)
            self.error('NOT_AVAILABLE', failed.drain, e)
        self.assertEqual(len(self.h.episodes.pendingEvidence(e, 16)), 1)
        decisions = relay.drain(e)
        self.assertEqual(decisions[0]['evidence'], ref)
        self.assertEqual(relay.drain(e), ())
        self.assertEqual(relay.decisions(e), decisions)
        self.h.config['principals']['owner']['credential'] = 'revoked'; self.h.save()
        self.error('UNAUTHORIZED', relay.decisions, e)

    def test_shared_placement_and_descriptor_drift_rejected(self):
        self.h.config['shared_roots'] = [str(self.h.root)]
        self.h.save(); self.error('UNSUPPORTED_PROFILE', self.h.reopen)

    def test_declared_operations_and_hostile_independent_c2_dependencies(self):
        self.assertTrue(isinstance(self.h.episodes, EpisodicMemory))
        self.assertTrue(isinstance(self.h.beliefs, BeliefRevision))
        for name, port in [('episodic.memory', EpisodicMemory), ('belief.revision', BeliefRevision)]:
            methods = {n for n in port.__dict__ if not n.startswith('_')}
            self.assertEqual(methods, set(OPERATIONS[name]))
            self.assertEqual(next(d for d in descriptors() if d.interface == name).operations, methods)
        self.h.beliefs = BeliefOwner(self.h.root / 'private/independent-beliefs.sqlite',
            PortOnly(self.h.atoms, OPERATIONS['atom.storage']), PortOnly(self.h.episodes, OPERATIONS['episodic.memory']),
            self.h.beliefs.access, self.h.math)
        claim, episode = self.h.claim(), self.h.episode()
        evidence = self.h.append(episode, self.h.event(claim))['evidence']
        result = self.h.submit(claim, evidence)
        self.assertEqual(result['numerical'], 'initialized')
        self.assertEqual(self.h.submit(claim, evidence, key='different-key')['snapshot'], result['snapshot'])

    def test_cross_principal_read_and_revoked_belief_replay(self):
        claim, episode = self.h.claim(), self.h.episode()
        ref = self.h.append(episode, self.h.event(claim))['evidence']
        self.h.submit(claim, ref)
        self.h.config['principals']['other'] = {'credential': 'other-credential', 'scopes': {
            SCOPE: self.h.config['principals']['owner']['scopes'][SCOPE]}}
        self.h.save()
        self.error('UNAUTHORIZED', open_private, self.h.path, 'other-credential', SCOPE, with_revision=False)
        self.h.config['principals']['owner']['scopes'][SCOPE].remove('belief.revision.submitEvidence'); self.h.save()
        self.error('UNAUTHORIZED', self.h.submit, claim, ref, expected=0)

    def test_bounded_delivery_capacity_does_not_drop_events(self):
        claim, episode = self.h.claim(), self.h.episode()
        for n in range(c.MAX_PENDING):
            self.h.append(episode, self.h.event(claim, occurrence='bounded-' + str(n), relationship='reports'), n)
        self.error('OVERLOADED', self.h.append, episode,
            self.h.event(claim, occurrence='bounded-overflow'), c.MAX_PENDING)
        self.assertEqual(self.h.episodes.readEpisode(episode, 1, 16)['head'], c.MAX_PENDING)
        self.assertEqual(len(self.h.episodes.pendingEvidence(episode, 16)), c.MAX_PENDING)

    def test_hostile_evidence_response_is_not_admitted(self):
        claim, episode = self.h.claim(), self.h.episode()
        ref = self.h.append(episode, self.h.event(claim))['evidence']
        record = self.h.episodes.readEvidence(ref)
        with patch.object(self.h.episodes, 'readEvidence', return_value={**record, 'lineage_roots': ['invented-root']}):
            self.error('NOT_AVAILABLE', self.h.submit, claim, ref)
        self.assertEqual(self.h.beliefs.readBelief(claim, 'generated', None)['revision'], 0)
        self.assertEqual(self.h.submit(claim, ref)['numerical'], 'initialized')


if __name__ == '__main__': unittest.main()
