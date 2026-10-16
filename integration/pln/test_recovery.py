"""Real SIGKILL boundaries with real DeTTa + native PLN, and privacy canary."""
import contextlib
import hashlib
import io
import json
import multiprocessing
import os
from pathlib import Path
import secrets
import signal
import time
import unittest
from unittest.mock import patch

from fusion.contracts import ContractError, canonical, digest
from fusion.evidence_relay import EvidenceRelay
from fusion.ports import Mutation
from tests.m2_support import MemoryHarness, SCOPE, assumption, support_identity
from tests.support import Harness

FORK = multiprocessing.get_context('fork')


class Recovery(unittest.TestCase):
    def setUp(self): self.h = MemoryHarness(real=True)
    def tearDown(self): self.h.close()

    def kill(self, stage, operation):
        marker = self.h.root / 'pause-marker'
        def hook(observed):
            if observed == stage:
                marker.write_text(observed)
                os.kill(os.getpid(), signal.SIGSTOP)
        self.h.episodes.hook = self.h.beliefs.hook = hook
        process = FORK.Process(target=operation, args=(hook,)); process.start()
        try:
            deadline = time.monotonic() + 30
            while not marker.exists() and process.is_alive() and time.monotonic() < deadline: time.sleep(.01)
            self.assertTrue(marker.exists(), f'{stage} was not reached; exit={process.exitcode}')
            os.kill(process.pid, signal.SIGKILL); process.join(10)
            self.assertEqual(process.exitcode, -signal.SIGKILL)
        finally:
            if process.is_alive(): process.kill(); process.join()
            self.h.episodes.hook = self.h.beliefs.hook = lambda stage: None
        self.h.reopen()

    def test_kill_after_payload_before_episode_commit(self):
        claim, episode = self.h.claim(), self.h.episode()
        event = self.h.event(claim)
        self.kill('after_payload_persist', lambda hook: self.h.append(episode, event))
        self.assertEqual(self.h.episodes.readEpisode(episode, 1, 16)['head'], 0)
        self.assertEqual(self.h.episodes.pendingEvidence(episode, 16), ())
        receipt = self.h.append(episode, event)
        self.assertEqual(self.h.append(episode, event), receipt)
        self.assertEqual(self.h.episodes.readEpisode(episode, 1, 16)['head'], 1)

    def test_kill_after_episode_and_intent_before_belief(self):
        claim, episode = self.h.claim(), self.h.episode()
        event = self.h.event(claim)
        self.kill('after_episode_commit', lambda hook: self.h.append(episode, event))
        self.assertEqual(self.h.episodes.readEpisode(episode, 1, 16)['head'], 1)
        self.assertEqual(self.h.beliefs.readBelief(claim, 'generated', None)['revision'], 0)
        self.assertEqual(len(self.h.episodes.pendingEvidence(episode, 16)), 1)
        relay = EvidenceRelay(self.h.root / 'private/relay.sqlite', self.h.episodes, self.h.beliefs)
        self.assertEqual(relay.drain(episode)[0]['numerical'], 'initialized')
        self.assertEqual(relay.drain(episode), ())

    def test_kill_after_native_formula_before_belief_commit(self):
        claim, episode = self.h.claim(), self.h.episode()
        self.h.append(episode, self.h.event(claim))
        path = self.h.root / 'private/relay.sqlite'
        relay = EvidenceRelay(path, self.h.episodes, self.h.beliefs)
        a = relay.drain(episode)[0]
        b = self.h.append(episode, self.h.event(claim, occurrence='b', source='sensor-b', strength='0.25'), 1)
        declaration = {b['delivery_id']: assumption(a['support_id'], support_identity(self.h.episodes.readEvidence(b['evidence'])))}
        self.kill('after_formula', lambda hook: EvidenceRelay(path, self.h.episodes, self.h.beliefs, hook=hook).drain(episode, declaration))
        self.assertEqual(self.h.beliefs.readBelief(claim, 'generated', None)['revision'], 1)
        self.assertEqual(len(self.h.episodes.pendingEvidence(episode, 16)), 1)
        relay = EvidenceRelay(path, self.h.episodes, self.h.beliefs)
        result = relay.drain(episode, declaration)[0]
        self.assertEqual(result['numerical'], 'revised')
        self.assertAlmostEqual(float(result['snapshot']['truth']['confidence']), 2/3, delta=1e-12)
        self.assertEqual(len(result['snapshot']['observations']), 2)
        self.assertEqual(relay.drain(episode), ())

    def test_kill_after_belief_commit_before_ack(self):
        claim, episode = self.h.claim(), self.h.episode()
        receipt = self.h.append(episode, self.h.event(claim))
        path = self.h.root / 'private/relay.sqlite'
        self.kill('after_belief_commit', lambda hook: EvidenceRelay(path, self.h.episodes, self.h.beliefs, hook=hook).drain(episode))
        before = self.h.beliefs.readBelief(claim, 'generated', None)
        self.assertEqual(before['revision'], 1)
        self.assertEqual(len(self.h.episodes.pendingEvidence(episode, 16)), 1)
        relay = EvidenceRelay(path, self.h.episodes, self.h.beliefs)
        result = relay.drain(episode)[0]
        self.assertEqual(result['snapshot'], before)
        self.assertEqual(relay.decisions(episode), (result,))
        self.assertEqual(relay.drain(episode), ())

    def test_two_process_cas_race_has_one_winner(self):
        episode = self.h.episode()
        events = [self.h.event(occurrence=name, numeric=False) for name in ('race-a', 'race-b')]
        barrier, queue = FORK.Barrier(2), FORK.Queue()
        def append(event):
            barrier.wait(10)
            for attempt in range(5):
                try:
                    queue.put(self.h.append(episode, event)['head']); return
                except ContractError as error:
                    # Busy owner storage is retryable. Keep the SAME occurrence,
                    # key and expected head; the loser must eventually conflict.
                    if error.code in {'NOT_AVAILABLE', 'OVERLOADED'} and attempt < 4:
                        time.sleep(.05)
                    else:
                        queue.put(error.code); return
        processes = [FORK.Process(target=append, args=(event,)) for event in events]
        for p in processes: p.start()
        for p in processes: p.join(20)
        try:
            self.assertEqual(sorted([queue.get(timeout=2), queue.get(timeout=2)], key=str), [1, 'CONFLICT'])
            self.assertEqual(self.h.episodes.readEpisode(episode, 1, 16)['head'], 1)
        finally:
            for p in processes:
                if p.is_alive(): p.kill(); p.join()
            queue.close()

    def test_private_canary_never_enters_shared_binding_or_diagnostics(self):
        marker = ('private-canary-' + secrets.token_hex(24)).encode()
        payload = self.h.atoms.create(Mutation(SCOPE, 'canary'), 'text/plain', marker)['ref']
        claim, episode = self.h.claim(), self.h.episode()
        event = {**self.h.event(claim), 'payload': payload}
        shared = self.h.root / 'shared'
        public_harness = Harness(binding='inprocess', root=shared)
        control = public_harness.a.store(b'Public generated control record', 'control')
        public_harness.a.share(control['ref'], 'reply-B', 'control-message')
        before = {str(p.relative_to(shared)): p.read_bytes() for p in shared.rglob('*') if p.is_file()}
        output = io.StringIO()
        with patch('fusion.bindings.Subprocess.invoke', side_effect=AssertionError('Shared outbound call')) as outbound, \
             patch('fusion.bindings.InProcess.invoke', side_effect=AssertionError('Shared in-process call')) as local_outbound, \
             contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            receipt = self.h.append(episode, event)
            relay = EvidenceRelay(self.h.root / 'private/relay.sqlite', self.h.episodes, self.h.beliefs)
            relay.drain(episode)
        self.assertEqual(outbound.call_count, 0)
        self.assertEqual(local_outbound.call_count, 0)
        self.assertEqual({str(p.relative_to(shared)): p.read_bytes() for p in shared.rglob('*') if p.is_file()}, before)
        private_hashes = [payload['digest'].encode(), receipt['evidence']['event_ref']['digest'].encode()]
        public = output.getvalue().encode() + b''.join(before.values())
        for forbidden in [marker, *private_hashes, *[r.encode() for r in self.h.episodes.readEvidence(receipt['evidence'])['lineage_roots']]]:
            self.assertNotIn(forbidden, public)
        self.assertEqual(self.h.atoms.get(payload).bytes, marker)


if __name__ == '__main__': unittest.main()
