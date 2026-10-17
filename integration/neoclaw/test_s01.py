"""Real pinned native parser/handler/kernel, real DeTTa, and real TLS/TCP.

Inputs, local authority and TLS certificates are generated test fixtures. No
private Omega stores, hosted model, production credential or public listener.
"""
import json
import os
from pathlib import Path
import signal
import sqlite3
import subprocess
import time
import unittest

from fusion import neoclaw_contracts as c
from fusion.contracts import ContractError, canonical
from tests.neoclaw_support import Harness, COMMAND, PREMISES, GOLDEN, RUNTIME, DETTA


class NativeS01(unittest.TestCase):
    def setUp(self):
        self.assertTrue(RUNTIME.is_file(), 'BLOCKED: pinned S01 runtime not built')
        self.assertTrue(DETTA.is_file(), 'BLOCKED: real DeTTa adapter unavailable')
        self.h = Harness(real=True)
        self.addCleanup(self.h.close)

    def test_three_native_command_paths_and_exact_representation(self):
        original = self.h.native(original=True)
        self.assertEqual(original['values'], [GOLDEN])
        local = self.h.native()
        self.assertEqual(local['values'], original['values'], local)
        # Composition only: same command and skill patch, fresh request identity.
        self.h.network('network-command')
        network = self.h.native()
        self.assertEqual(network['values'], original['values'], network)
        self.assertEqual(local['skill_sha256'], network['skill_sha256'])
        self.assertNotEqual(original['skill_sha256'], local['skill_sha256'])
        self.assertEqual(len(network['denied_paths']), 2)
        counts = self.h.counts()
        self.assertEqual(counts['jobs'], 2)
        self.assertEqual(counts['caller_completed'], 2)
        self.assertEqual(counts['unacked'], 0)
        output = os.environ.get('S01_EVIDENCE')
        if output:
            dest = Path(output); dest.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(self.h.config['database']) as db:
                trace = [dict(job_id=row[0], request=json.loads(row[1]), result=json.loads(row[2]))
                         for row in db.execute('SELECT id,request,result FROM jobs ORDER BY seq')]
            with sqlite3.connect(self.h.client['database']) as db:
                receipts = [json.loads(row[0]) for row in db.execute('SELECT receipt FROM caller_requests ORDER BY rowid')]
            self.assertEqual([x['job_id'] for x in trace], [x['job_id'] for x in receipts])
            (dest/'three-paths.json').write_text(json.dumps(dict(command=COMMAND, original=original, local=local,
                network=network, placement='same-host isolated loopback HTTPS, not multi-host', counts=counts,
                trace=trace, caller_receipts=receipts,
                providers=dict(kernel='real pinned original NAL', payload='real DeTTa',
                               caller='real MeTTaClaw parser + native metta handler', authority='generated local test policy'),
                fixtures=['generated STVs', 'test credentials', 'ephemeral trusted TLS CA']), indent=2)+'\n')

    def test_numeric_boundaries_match_original_in_both_placements(self):
        observed = []
        cases = [('0', '0', '1', '1'), ('1', '1', '1', '1'), ('1.0', '1.0', '1.0', '1.0'),
                 ('0.00000000000000001', '0.9', '0.7', '0.8'), ('0.33333333333333333', '0.99', '0.2', '0.25')]
        self.h.start_server()
        for i, values in enumerate(cases):
            command = 'metta (Truth_Deduction (stv %s %s) (stv %s %s))' % values
            original = self.h.native(command, original=True)
            self.assertEqual(len(original['values']), 1, original)
            for placement in ('local', 'network'):
                with self.subTest(values=values, placement=placement):
                    self.h.client = self.h.client_config(f'{placement}-{i}', placement);self.h.save_client()
                    actual = self.h.native(command)
                    self.assertEqual(actual['values'], original['values'], actual)
                    observed.append(dict(command=command, placement=placement, native=original['values'], actual=actual['values']))
        from integration.neoclaw.test_recovery import evidence
        evidence('numeric-boundaries', observed)

    def test_same_durable_intent_replays_after_composition_switch(self):
        original_config = dict(self.h.client)
        self.assertEqual(self.h.native()['values'], [GOLDEN])
        self.h.network(original_config['request_id'])
        self.h.client['deadline_ms'] = original_config['deadline_ms'];self.h.save_client()
        self.assertEqual(self.h.native()['values'], [GOLDEN])
        counts = self.h.counts()
        self.assertEqual(counts['jobs'], 1)
        self.assertEqual(counts['attempts'], 1)
        self.assertEqual(counts['caller_requests'], 1)
        self.assertEqual(counts['messages'], 1)
        self.assertEqual(counts['unacked'], 0)

    def test_broader_native_command_remains_local_and_no_fallback(self):
        self.h.network()
        broader = self.h.native('metta (+ 1 2)')
        self.assertEqual(broader['values'], ['3'], broader)
        self.assertEqual(self.h.counts().get('jobs', 0), 0)
        self.h.stop_server()
        self.h.client['max_calls'] = 2;self.h.save_client()
        refused = self.h.native()
        self.assertNotEqual(refused['values'], [GOLDEN], refused)
        self.assertEqual(self.h.counts()['caller_calls'], 2)
        self.assertEqual(self.h.counts()['caller_completed'], 0)


if __name__ == '__main__':
    unittest.main()
