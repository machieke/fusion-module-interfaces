"""Native inspection adapter over explicit application/provider fixtures.

The real adapter, Peer request builder, artifact contracts and FileFeedFixture
are exercised. Execution/mailbox replies and consumed task reports are fixtures.
No native runtime, DeTTa, HTTPS, chain, cluster or process kill is claimed.
"""
import copy
import json
from pathlib import Path
import sqlite3
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import uuid

from fusion.adapters.fixture_feed import FileFeedFixture
from fusion.contracts import ContractError, canonical, digest, require, validate
from fusion.lookup_contracts import make_head
from fusion.ports import Mutation
from fusion.preview_native_inspect import NativeInspection
from fusion.preview_tasks import PROFILE as TASK_PROFILE
from fusion.preview_lifecycle import PROFILE as LIFECYCLE
from fusion import preview_artifact_contracts as artifact, preview_vector_contracts as active, vector_contracts as vector


SCOPE = 'synthetic-inspection-adapter-tests'
NOW = 1793620800000


class AtomAuthorityFixture:
    def authorize(self, scope, operation):
        require(scope == SCOPE, 'UNAUTHORIZED')
        return 'synthetic-inspection-fixture'


class InspectionRepliesFixture:
    """Protocol replies only: no real Execution/Messaging provider claim."""
    frozen = {'boundary': 'EXPLICIT_INSPECTION_REPLY_FIXTURE'}

    def __init__(self, atoms, clock):
        self.atoms, self.clock = atoms, clock
        self.requests, self.accepted = [], None
        self.acked = False
        self.fail_after_submit = self.fail_after_ack = False
        self.status_value = 'succeeded'
        self.failures = {}
        self.mutate_output = lambda value: value
        self.mutate_completion = lambda value: value

    def invoke(self, request):
        name, op = validate(request, check_deadline=False)
        self.requests.append(copy.deepcopy(request))
        failures = self.failures.get(op, [])
        if failures:
            raise ContractError(failures.pop(0))
        if op == 'submit':
            if self.accepted is None:
                require(self.clock() < request['deadline_ms'], 'DEADLINE_EXCEEDED')
                self.accepted = copy.deepcopy(request)
                self.job = str(uuid.uuid4())
                item = self.atoms.get(request['body']['ref'])
                output = self.mutate_output(dict(digest=digest(item.bytes), length=len(item.bytes),
                    operation='inspect_atom', provider_version='0.1.0'))
                self.output = self.atoms.create(Mutation(SCOPE, 'fixture-output/'+self.job), 'application/json', canonical(output))
                self.delivery = dict(delivery_id=self.job, scope_ref=SCOPE, route=request['reply_route'], order=1,
                    delivery='observed-unacknowledged', body=dict(job_id=self.job, result=self.output, error=None,
                    correlation_id=request['correlation_id'], causation_id=request['message_id']))
            else: require(self.accepted == request, 'CONFLICT')
            if self.fail_after_submit:
                self.fail_after_submit = False
                raise RuntimeError('explicit lost-submit-reply fixture')
            return dict(job_id=self.job, execution='queued', acceptance='process-restart',
                completion_delivery='not-observed', chain=None, evidence={'boundary': 'REPLY_FIXTURE'},
                scope_ref=SCOPE, correlation_id=request['correlation_id'], reply_route=request['reply_route'])
        if op == 'status': return dict(execution=self.status_value)
        if op == 'result': return self.output
        if op == 'poll': return {'delivery': None if self.acked else self.mutate_completion(copy.deepcopy(self.delivery))}
        if op == 'ack':
            self.acked = True
            if self.fail_after_ack:
                self.fail_after_ack = False
                raise RuntimeError('explicit lost-ack-reply fixture')
            return dict(delivery_id=request['body']['delivery_id'], delivery='acknowledged',
                persistence='process-restart', evidence={'boundary': 'REPLY_FIXTURE'},
                scope_ref=SCOPE, route=request['body']['route'])
        raise AssertionError((name, op))


class NativeInspectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='phase2-inspection-tests-')
        self.addCleanup(self.temp.cleanup); self.root = Path(self.temp.name); self.now = NOW
        clock = patch('time.time_ns', side_effect=lambda: self.now*1000000)
        clock.start(); self.addCleanup(clock.stop)
        self.atoms = FileFeedFixture(self.root/'fixture-atoms.json', AtomAuthorityFixture())
        self.backend = InspectionRepliesFixture(self.atoms, lambda: self.now)
        selected = patch('fusion.preview_native_inspect.Client', return_value=self.backend)
        selected.start(); self.addCleanup(selected.stop)
        db = sqlite3.connect(self.root/'application-fixture.sqlite'); db.row_factory = sqlite3.Row
        self.addCleanup(db.close)
        self.view = dict(generation=str(uuid.uuid4()), head=make_head(str(uuid.uuid4()), SCOPE, 3),
            corpus='synthetic-inspection-corpus', embedding=vector.FIXTURE, index=vector.INDEX,
            profile=active.PROFILE, lifecycle=make_head(str(uuid.uuid4()), SCOPE, 2, LIFECYCLE), active_digest='a'*64)
        self.view['logical'] = digest(canonical({k: v for k, v in self.view.items() if k != 'generation'}))
        self.payload = dict(scope=SCOPE, corpus=self.view['corpus'], uuid=str(uuid.uuid4()),
            time='2026-11-02 12:00:00', content='Synthetic artifact observation Ω')
        self.payload_ref = self.atoms.create(Mutation(SCOPE, 'fixture-memory'), vector.PAYLOAD, canonical(self.payload))['ref']
        self.task = dict(id=str(uuid.uuid4()), query='synthetic observation', sender='A')
        self.body = dict(profile=TASK_PROFILE, kind='result', scope=SCOPE, sender='B',
            payloads=[self.payload_ref], view=self.view)
        result_ref = self.atoms.create(Mutation(SCOPE, 'fixture-task-result'), 'application/explicit-test-report', b'Synthetic report')['ref']
        self.origin = dict(record=self.body, ref=result_ref)
        self.report = Mock(return_value=dict(origin=self.origin, task=self.task))
        self.authorize = Mock(side_effect=lambda operation: require(operation == 'inspection', 'UNAUTHORIZED'))
        self.app = SimpleNamespace(db=db, config={'inspect_config': 'EXPLICIT_CLIENT_FIXTURE'},
            binding={'inspection': self.backend.frozen, 'principal': 'A'}, hook=lambda stage: None,
            preview=SimpleNamespace(authorize=self.authorize, tasks=SimpleNamespace(report=self.report),
                memory=SimpleNamespace(atoms=lambda deadline=None: self.atoms)))
        self.row = dict(id=str(uuid.uuid4()), deadline=NOW+20000, result=None)
        self.args = dict(task=self.task['id'])
        self.native = NativeInspection(self.app)
        with db: self.native.admit(self.row['id'], self.task['id'])

    def error(self, code, operation, *args):
        with self.assertRaises(ContractError) as caught: operation(*args)
        self.assertEqual(caught.exception.code, code)

    def replay(self): return self.native.replay(self.row, self.args)

    def interrupt(self, stage):
        def hook(observed):
            if stage == observed: raise RuntimeError('explicit capture-interruption fixture')
        self.app.hook = hook

    def reopen(self):
        self.app.hook = lambda stage: None
        self.native = NativeInspection(self.app)

    def test_exact_hydrated_artifact_inspection_and_consumed_completion(self):
        result = json.loads(self.replay())
        stored = self.atoms.get(result['artifact']); decoded = artifact.record(json.loads(stored.bytes), SCOPE)
        self.assertEqual(decoded['observations'], [dict(payload_ref=self.payload_ref, content=self.payload['content'])])
        self.assertEqual(decoded['result_ref'], self.origin['ref']); self.assertEqual(decoded['view'], self.view)
        self.assertEqual(result['artifact_bytes'], len(stored.bytes))
        self.assertEqual(result['status'], 'INSPECTED_ARTIFACT'); self.assertTrue(result['caller_acknowledged'])
        self.assertEqual((result['chain'], result['approval']), ('NOT_SUBMITTED', 'NOT_GRANTED'))
        self.assertTrue(self.backend.acked)
        self.assertEqual([q['operation'] for q in self.backend.requests], ['submit', 'status', 'result', 'poll', 'ack'])
        self.assertEqual(self.backend.accepted['deadline_ms'], self.row['deadline'])
        self.assertEqual(self.backend.accepted['idempotency_key'], self.row['id'])

    def test_lost_submit_response_reuses_exact_request_after_deadline(self):
        self.backend.fail_after_submit = True
        with self.assertRaises(RuntimeError): self.replay()
        accepted = copy.deepcopy(self.backend.accepted)
        self.assertIsNone(self.native.state(self.row)['acceptance'])
        before = self.native.state(self.row)['calls']; self.now = self.row['deadline']+1; self.reopen()
        result = json.loads(self.replay())
        submits = [q for q in self.backend.requests if q['operation'] == 'submit']
        self.assertEqual(submits, [accepted, accepted]); self.assertEqual(result['job_id'], self.backend.job)
        self.assertGreater(self.native.state(self.row)['calls'], before)
        self.assertEqual(self.backend.accepted['deadline_ms'], self.row['deadline'])

    def test_captured_result_and_completion_recover_without_regeneration_or_repoll(self):
        self.interrupt('after_inspect_completion_capture')
        with self.assertRaises(RuntimeError): self.replay()
        self.assertIsNone(self.native.state(self.row)['ack']); self.assertFalse(self.backend.acked)
        self.now = self.row['deadline']+1; self.reopen(); self.replay()
        for operation in ('submit', 'result', 'poll'):
            self.assertEqual(sum(q['operation'] == operation for q in self.backend.requests), 1)
        self.assertTrue(self.backend.acked)

    def test_lost_ack_response_replays_ack_identity_without_new_execution(self):
        self.backend.fail_after_ack = True
        with self.assertRaises(RuntimeError): self.replay()
        self.assertTrue(self.backend.acked); self.assertIsNone(self.native.state(self.row)['ack'])
        self.reopen(); self.replay()
        acks = [q for q in self.backend.requests if q['operation'] == 'ack']
        self.assertEqual(len(acks), 2)
        self.assertEqual(acks[0]['idempotency_key'], acks[1]['idempotency_key'])
        self.assertEqual(acks[0]['body'], acks[1]['body'])
        self.assertEqual(sum(q['operation'] == 'submit' for q in self.backend.requests), 1)

    def test_saved_result_still_rechecks_current_task_disclosure(self):
        self.replay(); before = len(self.backend.requests)
        self.report.side_effect = ContractError('UNAUTHORIZED')
        self.error('UNAUTHORIZED', self.replay)
        self.assertEqual(len(self.backend.requests), before)

    def test_changed_task_selection_or_correlated_report_ref_is_refused(self):
        self.error('CONFLICT', self.native.replay, self.row, {'task': str(uuid.uuid4())})
        self.assertEqual(self.native.state(self.row)['calls'], 0)
        self.replay()
        self.origin['ref'] = dict(self.origin['ref'], id='different-result')
        self.error('CONFLICT', self.replay)

    def test_wrong_inspection_bytes_cannot_be_acknowledged(self):
        self.backend.mutate_output = lambda value: dict(value, length=value['length']+1)
        self.error('NOT_AVAILABLE', self.replay)
        self.assertFalse(self.backend.acked); self.assertIsNone(self.native.state(self.row)['completion'])

    def test_wrong_completion_correlation_is_not_captured_or_acknowledged(self):
        def malformed(delivery): delivery['body']['correlation_id'] = str(uuid.uuid4()); return delivery
        self.backend.mutate_completion = malformed
        self.error('NOT_AVAILABLE', self.replay)
        self.assertFalse(self.backend.acked); self.assertIsNone(self.native.state(self.row)['completion'])

    def test_observation_bound_refuses_before_payload_reads_and_effects(self):
        self.body['payloads'] = [self.payload_ref]*(artifact.MAX_OBSERVATIONS+1)
        before = self.atoms.head(SCOPE)
        self.error('OVERLOADED', self.replay)
        self.assertEqual(self.atoms.head(SCOPE), before); self.assertEqual(self.backend.requests, [])

    def test_queued_observation_is_bounded_without_refund_resubmission_or_deadline_renewal(self):
        self.backend.status_value = 'queued'
        with patch('fusion.preview_native_inspect.time.sleep') as sleep:
            self.error('NOT_AVAILABLE', self.replay)
        self.assertEqual(sleep.call_count, 8)
        self.assertEqual(sum(q['operation'] == 'status' for q in self.backend.requests), 8)
        self.assertEqual(sum(q['operation'] == 'submit' for q in self.backend.requests), 1)
        self.assertIsNone(self.native.state(self.row)['result'])
        spent = self.native.state(self.row)['calls']
        accepted_deadline = self.backend.accepted['deadline_ms']
        self.now = self.row['deadline']+1; self.reopen()
        self.error('DEADLINE_EXCEEDED', self.replay)
        self.assertGreater(self.native.state(self.row)['calls'], spent)
        self.assertEqual(self.backend.accepted['deadline_ms'], accepted_deadline)
        self.assertEqual(sum(q['operation'] == 'submit' for q in self.backend.requests), 1)
        self.assertFalse(self.backend.acked)

    def test_transient_status_and_poll_recover_with_spent_observations(self):
        self.backend.failures = {'status': ['OVERLOADED', 'NOT_AVAILABLE'],
                                 'poll': ['NOT_AVAILABLE', 'OVERLOADED']}
        deadline = self.row['deadline']
        pauses = []

        def pause(seconds):
            self.assertGreater(seconds, 0)
            self.assertLessEqual(seconds, min(2, (deadline-self.now)/1000))
            pauses.append(seconds)
            self.now += int(seconds*1000)

        with patch('fusion.preview_native_inspect.time.sleep', side_effect=pause):
            result = json.loads(self.replay())
        self.assertEqual(result['status'], 'INSPECTED_ARTIFACT')
        self.assertTrue(result['caller_acknowledged']); self.assertTrue(self.backend.acked)
        self.assertEqual(len(pauses), 4)
        self.assertEqual([q['operation'] for q in self.backend.requests],
                         ['submit', 'status', 'status', 'status', 'result', 'poll', 'poll', 'poll', 'ack'])
        # Ten normal reservations, plus the four failed reserved observations.
        self.assertEqual(self.native.state(self.row)['calls'], 14)
        self.assertEqual(self.backend.accepted['deadline_ms'], deadline)
        self.assertEqual(self.row['deadline'], deadline)
        self.assertEqual(self.backend.accepted['idempotency_key'], self.row['id'])
        self.assertLess(self.now, deadline)

    def test_permanent_status_overload_exhausts_existing_budget_without_resubmit(self):
        self.backend.failures['status'] = ['OVERLOADED']*32
        deadline = self.row['deadline']
        with patch('fusion.preview_native_inspect.time.sleep') as sleep:
            self.error('NOT_AVAILABLE', self.replay)
            accepted = self.native.state(self.row)['acceptance']
            self.assertEqual(self.native.state(self.row)['calls'], 13)
            self.assertEqual(sleep.call_count, 8)
            self.reopen(); self.error('NOT_AVAILABLE', self.replay)
            self.assertEqual(self.native.state(self.row)['calls'], 23)
            self.assertEqual(sleep.call_count, 16)
            self.reopen(); self.error('OVERLOADED', self.replay)
            self.assertEqual(self.native.state(self.row)['calls'], 32)
            self.assertEqual(sleep.call_count, 23)
            before = copy.deepcopy(self.backend.requests)
            self.reopen(); self.error('OVERLOADED', self.replay)
            self.assertEqual(self.backend.requests, before)
        self.assertEqual(self.native.state(self.row)['acceptance'], accepted)
        self.assertIsNone(self.native.state(self.row)['result'])
        self.assertEqual(sum(q['operation'] == 'submit' for q in self.backend.requests), 1)
        self.assertEqual(sum(q['operation'] == 'status' for q in self.backend.requests), 23)
        self.assertFalse(self.backend.acked)
        self.assertEqual(self.backend.accepted['deadline_ms'], deadline)
        self.assertEqual(self.row['deadline'], deadline)

    def test_permanent_poll_overload_retains_result_and_spent_budget(self):
        self.backend.failures['poll'] = ['OVERLOADED']*32
        deadline = self.row['deadline']
        with patch('fusion.preview_native_inspect.time.sleep') as sleep:
            self.error('NOT_AVAILABLE', self.replay)
            captured = self.native.state(self.row)['result']
            self.assertIsNotNone(captured)
            self.assertEqual(self.native.state(self.row)['calls'], 16)
            self.assertEqual(sleep.call_count, 8)
            self.reopen(); self.error('NOT_AVAILABLE', self.replay)
            self.assertEqual(self.native.state(self.row)['calls'], 27)
            self.assertEqual(sleep.call_count, 16)
            self.reopen(); self.error('OVERLOADED', self.replay)
            self.assertEqual(self.native.state(self.row)['calls'], 32)
            self.assertEqual(sleep.call_count, 18)
        self.assertEqual(self.native.state(self.row)['result'], captured)
        for operation in ('submit', 'status', 'result'):
            self.assertEqual(sum(q['operation'] == operation for q in self.backend.requests), 1)
        self.assertEqual(sum(q['operation'] == 'poll' for q in self.backend.requests), 18)
        self.assertIsNone(self.native.state(self.row)['completion'])
        self.assertIsNone(self.native.state(self.row)['ack']); self.assertFalse(self.backend.acked)
        self.assertEqual(self.backend.accepted['deadline_ms'], deadline)
        self.assertEqual(self.row['deadline'], deadline)

    def test_transient_failure_at_deadline_stops_before_pause_without_refund(self):
        self.backend.failures['status'] = ['OVERLOADED']
        original = self.backend.invoke

        def invoke(request):
            if request['operation'] == 'status':
                self.now = self.row['deadline']
            return original(request)

        with patch.object(self.backend, 'invoke', side_effect=invoke), \
                patch('fusion.preview_native_inspect.time.sleep') as sleep:
            self.error('DEADLINE_EXCEEDED', self.replay)
        sleep.assert_not_called()
        self.assertEqual(self.native.state(self.row)['calls'], 6)
        self.assertEqual([q['operation'] for q in self.backend.requests], ['submit', 'status'])
        self.assertIsNone(self.native.state(self.row)['result'])
        self.assertFalse(self.backend.acked)
        self.assertEqual(self.backend.accepted['deadline_ms'], NOW+20000)

    def unauthorized_observation(self, operation):
        self.backend.failures[operation] = ['UNAUTHORIZED']
        with patch('fusion.preview_native_inspect.time.sleep') as sleep:
            self.error('UNAUTHORIZED', self.replay)
        sleep.assert_not_called()
        self.assertEqual(sum(q['operation'] == operation for q in self.backend.requests), 1)
        self.assertEqual(self.backend.requests[-1]['operation'], operation)
        self.assertEqual(sum(q['operation'] == 'submit' for q in self.backend.requests), 1)
        self.assertIsNone(self.native.state(self.row)['completion'])
        self.assertIsNone(self.native.state(self.row)['ack']); self.assertFalse(self.backend.acked)
        self.assertEqual(self.native.state(self.row)['calls'], 6 if operation == 'status' else 9)

    def test_unauthorized_status_is_immediate_and_not_retried(self):
        self.unauthorized_observation('status')
        self.assertIsNone(self.native.state(self.row)['result'])

    def test_unauthorized_poll_is_immediate_and_keeps_captured_result(self):
        self.unauthorized_observation('poll')
        self.assertIsNotNone(self.native.state(self.row)['result'])

    def test_exact_deadline_refuses_new_artifact_effects(self):
        self.now = self.row['deadline']; before = self.atoms.head(SCOPE)
        self.error('DEADLINE_EXCEEDED', self.replay)
        self.assertEqual(self.atoms.head(SCOPE), before)
        self.assertIsNone(self.native.state(self.row)['artifact_ref'])

    def test_reservation_interruption_and_exhaustion_keep_spent_budget(self):
        self.interrupt('after_inspect_relay_reservation')
        with self.assertRaises(RuntimeError): self.replay()
        self.assertEqual(self.native.state(self.row)['calls'], 1)
        self.reopen()
        with self.app.db: self.app.db.execute('UPDATE preview_inspections SET calls=32')
        self.error('OVERLOADED', self.replay)
        self.assertEqual(self.native.state(self.row)['calls'], 32); self.assertEqual(self.backend.requests, [])


if __name__ == '__main__': unittest.main()
