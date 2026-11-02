"""Early native preview seam gate; explicit old model/channel fixtures.

This is not the final ModelInference-owner or deployed preview qualification.
The real pinned native loop/parser evaluates tools and produces feedback.
"""
import json
import os
from pathlib import Path
import signal
import time
import unittest
import uuid

from fusion.contracts import canonical
from fusion.preview_application import APPLICATION
from .controlled_run import ControlledRun


class NativePreviewContext(unittest.TestCase):
    def fresh(self, responses):
        output = os.environ.get('PHASE2_EVIDENCE')
        root = Path(output).resolve()/'private-runs'/uuid.uuid4().hex if output else None
        run = ControlledRun('local', responses, root=root)
        self.addCleanup(run.close)
        authority = run.h.caller_root/'preview-authority.json'
        authority.write_bytes(canonical(dict(principal='A', scope='synthetic-preview-context',
            tools=['pin', 'unpin', 'task-context'], revision='preview-context-policy-1',
            expires_ms=int(time.time()*1000)+120000, revoked=False)))
        run.app.update(composition=APPLICATION, session_id=str(uuid.uuid4()), preparation_diagnostics=True,
            preview=dict(profile=APPLICATION, base='controlled-native-loop/1', authority_file=str(authority),
                         tools=['pin', 'unpin', 'task-context'], scope='synthetic-preview-context'))
        run.model['expected_feedback'] = {}
        run.save()
        return run

    def test_native_pin_context_unpin_and_retained_results(self):
        run = self.fresh(['pin task Synthetic note from actual pin', 'task-context', 'unpin task', 'task-context'])
        result = run.finish(run.start())
        self.assertEqual(result, (0, {'status': 'BOUNDED_STOP'}), (result, (run.h.root/'native.log').read_text()[-3500:]))
        rows = run.rows('app_occurrences')
        self.assertEqual(len(rows), 4)
        self.assertEqual([json.loads(r['result'])['revision'] for r in rows], [1, 1, 2, 2])
        self.assertEqual(json.loads(rows[-1]['result'])['items'], {})
        observed = run.observations()
        self.assertIn('Synthetic note from actual pin', observed[1]['context'].split('UNVERIFIED_TASK_CONTEXT_JSON: ')[1])
        self.assertNotIn('Synthetic note from actual pin', observed[3]['context'].split('UNVERIFIED_TASK_CONTEXT_JSON: ')[1])
        before = [r['id'] for r in rows]
        self.assertEqual(run.finish(run.start()), (0, {'status': 'BOUNDED_STOP'}))
        self.assertEqual(before, [r['id'] for r in run.rows('app_occurrences')])
        output = os.environ.get('PHASE2_EVIDENCE')
        if output:
            Path(output).mkdir(parents=True, exist_ok=True)
            (Path(output)/'native-context.json').write_bytes(canonical(dict(status='PASS',
                native=True, model='CONTROLLED_RESPONSE_FIXTURE_NOT_MODEL_OWNER', channel='FIXTURE',
                occurrences=rows, observations=observed, startup=json.loads((Path(run.app['workdir'])/'startup.json').read_text()),
                additional_live_generations=0)))

    def test_native_mixed_forbidden_batch_has_no_pin_effect(self):
        run = self.fresh(['pin task should not commit\nmetta (+ 1 2)'])
        result = run.finish(run.start())
        self.assertEqual(result, (2, {'status': 'PENDING_OR_FAILED', 'code': 'UNSUPPORTED_OPERATION'}))
        self.assertEqual(run.rows('app_occurrences'), [])

    def test_native_sigkill_after_note_commit_keeps_occurrence_and_deadline(self):
        run = self.fresh(['pin task Recover this actual note', 'task-context'])
        run.app['pause_at'] = 'after_context_commit'
        run.save()
        process = run.start()
        marker = Path(run.app['failpoint_marker'])
        run.h.wait_file(marker, process)
        paused = json.loads(marker.read_text())
        before = run.rows('app_occurrences')[0]
        self.assertIsNone(before['result'])
        os.kill(paused['pid'], signal.SIGKILL)
        self.assertIn(process.wait(timeout=5), (-9, 137))
        run.app.pop('pause_at'); run.save()
        self.assertEqual(run.finish(run.start()), (0, {'status': 'BOUNDED_STOP'}))
        after = run.rows('app_occurrences')[0]
        for key in ('id', 'premises', 'deadline', 'turn', 'position'):
            self.assertEqual(before[key], after[key])
        self.assertEqual(json.loads(after['result'])['revision'], 1)
        self.assertEqual(len(run.observations()), 2)


if __name__ == '__main__': unittest.main()
