"""Real local DeTTa and pinned native PLN; explicit injected-failure cases.

No skips or fallback: source/runtime absence is a failed prerequisite.
"""
from dataclasses import replace
import json
import os
from pathlib import Path
import shutil
import subprocess
import threading
import unittest
from unittest.mock import patch

from fusion import memory_contracts as c
from fusion.adapters.pln_revision import GuardedRevision, RevisionRuntime, verify_source
from fusion.contracts import ContractError, canonical
from fusion.evidence_relay import EvidenceRelay
from tests.m2_support import MemoryHarness, assumption, support_identity


class NativeRevision(unittest.TestCase):
    def setUp(self): self.h = MemoryHarness(real=True)
    def tearDown(self): self.h.close()
    def error(self, code, function, *args, **kwargs):
        with self.assertRaises(ContractError) as caught: function(*args, **kwargs)
        self.assertEqual(caught.exception.code, code)

    def pair(self, confidence='0.5', reverse=False, zero=False, provenance=False):
        claim, episode = self.h.claim(), self.h.episode()
        values = [('a', 'sensor-a', '0.75', '0' if zero else '0.5'),
                  ('b', 'sensor-b', '0.25', '0' if zero else confidence)]
        if reverse: values.reverse()
        decisions = []
        for n, (occurrence, source, strength, conf) in enumerate(values):
            event = self.h.event(claim, occurrence=occurrence, source=source, strength=strength, confidence=conf,
                relationship='supports' if strength == '0.75' else 'contradicts',
                provenance=[decisions[0]['evidence']] if provenance and n else None)
            evidence = self.h.append(episode, event, n)['evidence']
            decisions.append(self.h.submit(claim, evidence, key=occurrence))
        return claim, episode, decisions

    def revise(self, claim, pair, key='assume', expected=None):
        return self.h.submit(claim, support_id=pair[1]['support_id'], key=key, expected=expected,
                             independence=assumption(pair[0]['support_id'], pair[1]['support_id']))

    def test_actual_equal_weight_golden_and_historical_snapshots(self):
        claim, episode, pair = self.pair()
        result = self.revise(claim, pair)
        self.assertEqual(result['numerical'], 'revised')
        self.assertEqual(result['admission'], 'duplicate')
        self.assertAlmostEqual(float(result['snapshot']['truth']['strength']), .5, delta=1e-12)
        self.assertAlmostEqual(float(result['snapshot']['truth']['confidence']), 2/3, delta=1e-12)
        self.assertIsNone(result['snapshot']['truth']['evidence_count'])
        self.assertEqual(len(result['snapshot']['observations']), 2)
        self.assertEqual(len(result['snapshot']['covered_supports']), 2)
        self.assertEqual(result['snapshot']['alternatives'], [])
        self.h.reopen()
        self.assertEqual(self.revise(claim, pair, expected=2), result)
        self.assertEqual(self.h.beliefs.readBelief(claim, 'generated', 1), pair[0]['snapshot'])
        self.assertEqual(self.h.episodes.readEpisode(episode, 1, 16)['head'], 2)

    def test_actual_unequal_weight_golden(self):
        claim, _, pair = self.pair('0.75')
        result = self.revise(claim, pair)
        self.assertAlmostEqual(float(result['snapshot']['truth']['strength']), .375, delta=1e-12)
        self.assertAlmostEqual(float(result['snapshot']['truth']['confidence']), .8, delta=1e-12)

    def test_actual_swapped_order_golden(self):
        claim, _, pair = self.pair('0.75', reverse=True)
        result = self.revise(claim, pair)
        self.assertAlmostEqual(float(result['snapshot']['truth']['strength']), .375, delta=1e-12)
        self.assertAlmostEqual(float(result['snapshot']['truth']['confidence']), .8, delta=1e-12)

    def test_missing_independence_retains_contrary_and_no_formula(self):
        math = self.h.beliefs.math
        with patch.object(math.native, 'evaluate', side_effect=AssertionError('Formula must not run')):
            claim, _, pair = self.pair()
        self.assertEqual(pair[1]['numerical'], 'retained-alternative')
        self.assertEqual(pair[1]['snapshot']['truth'], pair[0]['snapshot']['truth'])
        self.assertEqual(pair[1]['snapshot']['alternatives'], [pair[1]['support_id']])
        self.assertEqual(pair[1]['snapshot']['observations'][1]['relationship'], 'contradicts')

    def test_overlap_and_aggregate_ancestor_no_extra_weight(self):
        claim, _, pair = self.pair(provenance=True)
        with patch.object(self.h.beliefs.math.native, 'evaluate', side_effect=AssertionError('Overlap formula')):
            refused = self.revise(claim, pair)
        self.assertEqual(refused['numerical'], 'retained-alternative')
        self.assertEqual(refused['snapshot']['truth'], pair[0]['snapshot']['truth'])
        # Independent case in a separate private history, followed by its own ancestor.
        self.h.close(); self.h = MemoryHarness(real=True)
        claim, _, pair = self.pair()
        aggregate = self.revise(claim, pair)['snapshot']
        ancestor = self.h.submit(claim, support_id=pair[0]['support_id'], key='ancestor',
            independence=assumption(aggregate['aggregate'], pair[0]['support_id']))
        self.assertEqual(ancestor['snapshot'], aggregate)
        self.assertEqual(ancestor['numerical'], 'retained-alternative')

    def test_wrong_pair_rejected_and_assumption_permission_separate(self):
        claim, _, pair = self.pair()
        self.error('CONFLICT', self.h.submit, claim, support_id=pair[1]['support_id'], key='wrong-pair',
            independence=assumption(pair[1]['support_id'], 'unadmitted-support'))
        self.h.config['principals']['owner']['scopes']['private-memory'].remove('belief.revision.assume'); self.h.save()
        self.error('UNAUTHORIZED', self.revise, claim, pair)
        self.assertEqual(self.h.beliefs.readBelief(claim, 'generated', None)['revision'], 2)

    def test_zero_weight_pair_is_model_inapplicable_without_formula(self):
        claim, _, pair = self.pair(zero=True)
        with patch.object(self.h.beliefs.math.native, 'evaluate', side_effect=AssertionError('Zero formula')):
            result = self.revise(claim, pair)
        self.assertEqual(result['numerical'], 'model-inapplicable')
        self.assertEqual(result['snapshot'], pair[1]['snapshot'])

    def test_malformed_empty_multiple_and_nonfinite_output_fixtures(self):
        parse = self.h.beliefs.math.native.parse
        for output in ('', 'true', 'true\n(stv 0.5 0.5)\n(stv 0.5 0.5)', 'true\n(stv NaN 0.5)',
                       'true\n(stv 0.5 inf)', 'true\n(stv 0.5 1)', 'true\n(stv 0.5 0.99999999999999999)',
                       'true\ngarbage', 'false\n(stv 0.5 0.5)'):
            self.error('NOT_AVAILABLE', parse, output)

    def test_native_timeout_leaves_delivery_pending_and_exact_attempt_replays(self):
        claim, episode = self.h.claim(), self.h.episode()
        a = self.h.append(episode, self.h.event(claim))
        relay = EvidenceRelay(self.h.root / 'private/relay.sqlite', self.h.episodes, self.h.beliefs)
        first = relay.drain(episode)[0]
        b = self.h.append(episode, self.h.event(claim, occurrence='b', source='sensor-b', strength='0.25'), 1)
        candidate = support_identity(self.h.episodes.readEvidence(b['evidence']))
        declaration = {b['delivery_id']: assumption(first['support_id'], candidate)}
        self.h.beliefs.math.native.timeout = .000001
        self.error('NOT_AVAILABLE', relay.drain, episode, declaration)
        self.assertEqual(len(self.h.episodes.pendingEvidence(episode, 16)), 1)
        self.assertEqual(self.h.beliefs.readBelief(claim, 'generated', None)['revision'], 1)
        self.error('CONFLICT', relay.drain, episode)  # cannot change an in-flight semantic request
        self.h.beliefs.math.native.timeout = 10
        result = relay.drain(episode, declaration)[0]
        self.assertEqual(result['numerical'], 'revised')
        self.assertEqual(self.h.episodes.pendingEvidence(episode, 16), ())

    def test_runtime_pin_binary_and_formula_drift_fail_closed(self):
        math = self.h.beliefs.math
        config = dict(math.config, runtime_profile='other-runtime')
        self.error('UNSUPPORTED_PROFILE', RevisionRuntime(config, math.upstream).check)
        config = dict(math.config, swipl_sha256='0' * 64)
        self.error('UNSUPPORTED_PROFILE', RevisionRuntime(config, math.upstream).check)
        config = dict(math.config, swipl=str(self.h.root / 'unavailable-swipl'))
        self.error('NOT_AVAILABLE', RevisionRuntime(config, math.upstream).check)
        path = self.h.root / 'pln-drift'
        subprocess.run(['git', 'clone', '-q', '--no-hardlinks', math.config['pln'], str(path)], check=True)
        with (path / 'lib_pln.metta').open('a') as file: file.write('\n; injected drift\n')
        self.error('UNSUPPORTED_PROFILE', verify_source, 'pln', path)

    def test_authority_rechecked_after_native_formula_before_commit(self):
        claim, _, pair = self.pair()
        def hook(stage):
            if stage == 'after_formula':
                self.h.config['principals']['owner']['scopes']['private-memory'].remove('belief.revision.submitEvidence')
                self.h.save()
        self.h.beliefs.hook = hook
        self.error('UNAUTHORIZED', self.revise, claim, pair)
        self.assertEqual(self.h.beliefs.readBelief(claim, 'generated', None)['revision'], 2)
        self.h.config['principals']['owner']['scopes']['private-memory'].append('belief.revision.submitEvidence'); self.h.save()
        self.h.beliefs.hook = lambda stage: None
        self.assertEqual(self.revise(claim, pair)['numerical'], 'revised')

    def test_cas_conflict_requires_a_new_attempt_identity(self):
        claim, episode, pair = self.pair()
        reached, release = threading.Event(), threading.Event()
        def hook(stage):
            if stage == 'after_formula': reached.set(); self.assertTrue(release.wait(20))
        self.h.beliefs.hook = hook
        outcomes = []
        def delayed():
            try: outcomes.append(self.revise(claim, pair, expected=2))
            except ContractError as e: outcomes.append(e.code)
        thread = threading.Thread(target=delayed); thread.start()
        try:
            self.assertTrue(reached.wait(20))
            report = self.h.append(episode, self.h.event(claim, occurrence='report', relationship='reports'), 2)['evidence']
            other = self.h.submit(claim, report, key='racing-report')
            self.assertEqual(other['snapshot']['revision'], 3)
        finally: release.set(); thread.join(20)
        self.assertEqual(outcomes, ['CONFLICT'])
        self.error('CONFLICT', self.revise, claim, pair, expected=3)
        result = self.revise(claim, pair, key='new-cas-attempt', expected=3)
        self.assertEqual(result['snapshot']['revision'], 4)
        self.assertEqual(len(result['snapshot']['observations']), 3)


if __name__ == '__main__': unittest.main()
