"""Real SIGKILL recovery through the actual native MeTTaClaw HTTPS caller.

Failpoint coordination and generated policies are test instrumentation. Owners,
TCP/TLS, MeTTa arithmetic and DeTTa persistence are real, separate processes.
"""
import json
import os
from pathlib import Path
import signal
import sqlite3
import time
import unittest

from tests.neoclaw_support import Harness, GOLDEN, RUNTIME, DETTA


def evidence(name, rows):
    output = os.environ.get('S01_EVIDENCE')
    if output:
        path = Path(output); path.mkdir(parents=True, exist_ok=True)
        (path/(name+'.json')).write_text(json.dumps(rows, indent=2)+'\n')


class RecoveryS01(unittest.TestCase):
    def setUp(self):
        self.assertTrue(RUNTIME.is_file(), 'BLOCKED: pinned S01 runtime not built')
        self.assertTrue(DETTA.is_file(), 'BLOCKED: real DeTTa adapter unavailable')
        self.h = None

    def fresh(self):
        if self.h:self.h.close()
        self.h = Harness(real=True)
        self.addCleanup(self.h.close)
        self.h.network()
        self.h.service().close()

    def wait(self, predicate, process=None, drive=False):
        until = time.monotonic()+10
        while time.monotonic() < until:
            if predicate():return
            if process is not None and process.poll() is not None:break
            if drive:self.h.drive()
            time.sleep(.02)
        self.fail('observation timeout awaiting explicit commit/failpoint')

    def native(self, stage=None):
        marker = Path(self.h.client['failpoint_marker']); marker.unlink(missing_ok=True)
        if stage:self.h.client['pause_at'] = stage
        else:self.h.client.pop('pause_at', None)
        self.h.save_client()
        process = self.h.start_native()
        def cleanup():
            if process.poll() is None:
                if marker.exists():
                    try:os.kill(json.loads(marker.read_text())['pid'], signal.SIGKILL)
                    except ProcessLookupError:pass
                process.kill();process.wait()
            process.stdout.close();process.stderr.close()
        self.addCleanup(cleanup)
        return process, marker

    def operator(self, mode):
        proc = self.h.worker(mode)
        stdout, stderr = proc.communicate(timeout=10)
        self.assertEqual(proc.returncode, 0, (stdout, stderr))
        return json.loads(stdout)['ok']

    def assert_closed(self, attempts=1):
        actual = self.h.counts()
        for key, value in dict(jobs=1, outbox=1, messages=1, unacked=0, caller_requests=1,
                               caller_completed=1, caller_acked=1, attempts=attempts).items():
            self.assertEqual(actual[key], value, actual)
        with sqlite3.connect(self.h.config['atoms_database']) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM atoms').fetchone()[0], 1)
        with sqlite3.connect(self.h.config['database']) as db:
            row = db.execute('SELECT id,request,result,state FROM jobs').fetchone()
            self.assertEqual(row[3], 'succeeded')
            self.assertEqual(json.loads(row[1])['deadline_ms'], self.h.client['deadline_ms'])
            self.assertEqual(db.execute('SELECT sent FROM outbox').fetchone()[0], 1)
        return dict(counts=actual, job_id=row[0], result=json.loads(row[2]), deadline_ms=self.h.client['deadline_ms'])

    def test_killed_native_caller_replays_every_independent_commit(self):
        rows = []
        for stage in ('after_request_persist', 'after_call_reservation', 'after_submit_reply',
                      'after_caller_receipt', 'after_mailbox_ack'):
            with self.subTest(stage=stage):
                self.fresh()
                process, marker = self.native(stage)
                self.wait(marker.exists, process, drive=True)
                before = self.h.counts()
                failpoint = json.loads(marker.read_text())
                os.kill(failpoint['pid'], signal.SIGKILL)
                killed = self.h.finish_native(process, drive=False)
                # bubblewrap reports the native child's signal as 128 + signal.
                self.assertEqual(killed['exit_code'], 128 + signal.SIGKILL, killed)
                if stage == 'after_request_persist':
                    self.assertEqual(before['caller_requests'], 1);self.assertEqual(before['jobs'], 0)
                if stage == 'after_call_reservation':self.assertEqual(before['caller_calls'], 1)
                if stage == 'after_caller_receipt':
                    self.assertEqual(before['caller_completed'], 1);self.assertEqual(before['unacked'], 1)
                if stage == 'after_mailbox_ack':
                    self.assertEqual(before['unacked'], 0);self.assertEqual(before['caller_acked'], 0)
                self.h.client.pop('pause_at');self.h.save_client()
                recovered = self.h.native()
                self.assertEqual(recovered['values'], [GOLDEN], recovered)
                first = self.assert_closed()
                # Repeated actual native invocations replay the same caller receipt,
                # provider job/result and independently idempotent mailbox ack.
                for _ in range(2):self.assertEqual(self.h.native()['values'], [GOLDEN])
                final = self.assert_closed()
                self.assertEqual(first['result'], final['result'])
                self.assertGreater(final['counts']['caller_calls'], before['caller_calls'])
                rows.append(dict(stage=stage, killed_native_signal=9, before=before, after=final))
        evidence('caller-kills', rows)

    def test_killed_native_worker_and_mailbox_delivery_recover(self):
        rows = []
        for stage in ('after_reservation', 'after_compute', 'after_output_commit',
                      'after_result_persist', 'after_completion_commit', 'after_delivery_accept'):
            with self.subTest(stage=stage):
                self.fresh()
                process, _ = self.native()
                self.wait(lambda:self.h.counts()['jobs'] == 1, process)
                mode = 'flush' if stage == 'after_delivery_accept' else 'work'
                if mode == 'flush':self.operator('work')
                killed = self.h.kill_worker(stage, mode)
                before = self.h.counts()
                if stage == 'after_result_persist':
                    self.assertEqual(before['outbox'], 0)
                    with sqlite3.connect(self.h.config['atoms_database']) as db:
                        self.assertEqual(db.execute('SELECT count(*) FROM atoms').fetchone()[0], 1)
                if stage == 'after_delivery_accept':
                    with sqlite3.connect(self.h.config['database']) as db:
                        self.assertEqual(db.execute('SELECT sent FROM outbox').fetchone()[0], 0)
                    self.assertEqual(before['messages'], 1)
                self.operator('work');self.operator('flush')
                completed = self.h.finish_native(process)
                self.assertEqual(completed['values'], [GOLDEN], completed)
                attempts = 2 if stage in ('after_reservation', 'after_compute') else 1
                after = self.assert_closed(attempts)
                self.assertEqual(self.operator('flush'), dict(sent=0, pending=0))
                rows.append(dict(stage=stage, killed_operator_signal=9, before=before, after=after))
        evidence('worker-kills', rows)

    def test_killed_https_acceptance_server_replays_lost_receipt(self):
        self.fresh()
        self.h.stop_server()
        self.h.config['pause_at'] = 'after_acceptance';self.h.start_server()
        process, _ = self.native()
        marker = Path(self.h.config['failpoint_marker'])
        self.wait(marker.exists, process)
        self.assertEqual(self.h.counts()['jobs'], 1)
        old = self.h.server
        self.h.stop_server(kill=True)
        self.assertEqual(old.returncode, -signal.SIGKILL)
        self.h.config.pop('pause_at');self.h.start_server()
        self.operator('work');self.operator('flush')
        recovered = self.h.finish_native(process)
        self.assertEqual(recovered['values'], [GOLDEN], recovered)
        evidence('acceptance-kill', self.assert_closed())

    def test_crash_reservations_exhaust_budget_without_reset_or_computation(self):
        self.fresh()
        process, _ = self.native()
        self.wait(lambda:self.h.counts()['jobs'] == 1, process)
        for attempt in range(1, 4):
            self.h.kill_worker('after_reservation')
            self.assertEqual(self.h.counts()['attempts'], attempt)
        failure = self.operator('work')
        self.assertEqual(failure['execution'], 'failed')
        self.operator('flush')
        actual = self.h.finish_native(process)
        self.assertNotEqual(actual['values'], [GOLDEN], actual)
        counts = self.h.counts()
        self.assertEqual(counts['attempts'], 3)
        self.assertEqual(counts['caller_completed'], 1)
        self.assertEqual(counts['caller_acked'], 1)
        with sqlite3.connect(self.h.config['database']) as db:
            self.assertEqual(db.execute('SELECT failure_reason,output FROM s01_work').fetchone(),
                             ('attempt-budget-exhausted', None))
            self.assertEqual(json.loads(db.execute('SELECT request FROM jobs').fetchone()[0])['deadline_ms'],
                             self.h.client['deadline_ms'])
        self.assertEqual(self.operator('work'), dict(worked=False))
        evidence('crash-budget', dict(counts=counts, native_attempts_reserved=3, native_computations=0,
                                     terminal='NOT_AVAILABLE', reason='attempt-budget-exhausted'))

    def test_deadline_after_output_commit_allows_closure_not_new_math(self):
        self.fresh()
        self.h.client['deadline_ms'] = int(time.time()*1000)+1800;self.h.save_client()
        # Actual native caller persists/submits, then is killed before waiting.
        process, marker = self.native('after_submit_reply')
        self.wait(marker.exists, process)
        os.kill(json.loads(marker.read_text())['pid'], signal.SIGKILL)
        self.h.finish_native(process, drive=False)
        self.h.kill_worker('after_output_commit')
        time.sleep(max(0, self.h.client['deadline_ms']/1000-time.time())+.02)
        self.operator('work');self.operator('flush')
        self.h.client.pop('pause_at');self.h.save_client()
        recovered = self.h.native()
        self.assertEqual(recovered['values'], [GOLDEN], recovered)
        evidence('deadline-closure', self.assert_closed())

    def test_revocation_after_native_receipt_blocks_ack_then_recovers(self):
        self.fresh()
        process, marker = self.native('after_caller_receipt')
        self.wait(marker.exists, process, drive=True)
        methods = self.h.config['principals']['A']['scopes'][self.h.client['scope']]
        methods.remove('agent.messaging.ack');self.h.save()
        os.kill(json.loads(marker.read_text())['pid'], signal.SIGCONT)
        refused = self.h.finish_native(process)
        self.assertNotEqual(refused['values'], [GOLDEN], refused)
        self.assertEqual(self.h.counts()['caller_completed'], 1)
        self.assertEqual(self.h.counts()['unacked'], 1)
        self.assertEqual(self.h.counts()['caller_acked'], 0)
        methods.append('agent.messaging.ack');self.h.save()
        self.h.client.pop('pause_at');self.h.save_client()
        self.assertEqual(self.h.native()['values'], [GOLDEN])
        evidence('revocation-recovery', self.assert_closed())

    def test_native_caller_kills_spend_rpc_budget_without_reset(self):
        self.fresh()
        self.h.client['max_calls'] = 2
        for expected in (1, 2):
            process, marker = self.native('after_call_reservation')
            self.wait(marker.exists, process)
            os.kill(json.loads(marker.read_text())['pid'], signal.SIGKILL)
            self.h.finish_native(process, drive=False)
            self.assertEqual(self.h.counts()['caller_calls'], expected)
            self.assertEqual(self.h.counts()['jobs'], 0)
        self.h.client.pop('pause_at');self.h.save_client()
        self.assertNotEqual(self.h.native()['values'], [GOLDEN])
        self.assertEqual(self.h.counts()['caller_calls'], 2)
        self.assertEqual(self.h.counts()['jobs'], 0)
        evidence('caller-crash-budget', self.h.counts())

    def test_expired_reservation_after_kill_never_recomputes(self):
        self.fresh()
        self.h.client['deadline_ms'] = int(time.time()*1000)+1400
        process, marker = self.native('after_submit_reply')
        self.wait(marker.exists, process)
        os.kill(json.loads(marker.read_text())['pid'], signal.SIGKILL)
        self.h.finish_native(process, drive=False)
        self.h.kill_worker('after_reservation')
        time.sleep(max(0, self.h.client['deadline_ms']/1000-time.time())+.02)
        self.assertEqual(self.operator('work')['execution'], 'failed')
        self.operator('flush')
        self.h.client.pop('pause_at');self.h.save_client()
        actual = self.h.native()
        self.assertNotEqual(actual['values'], [GOLDEN])
        with sqlite3.connect(self.h.config['database']) as db:
            self.assertEqual(db.execute('SELECT attempts,output FROM s01_work').fetchone(), (1, None))
            self.assertEqual(db.execute('SELECT error FROM jobs').fetchone()[0], 'DEADLINE_EXCEEDED')
        self.assertEqual(self.h.counts()['caller_acked'], 1)
        evidence('deadline-crash', self.h.counts())


if __name__ == '__main__':unittest.main()
