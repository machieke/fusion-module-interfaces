"""Operator observer tests with explicitly authored protocol responses.

No native loop, module provider, runtime, cluster or model is contacted. The
fixture supplies pre-authored captures, never executes commands or implements
NAL/context effects. A deployed run must independently establish those claims.
"""
import copy
import json
from pathlib import Path
import tempfile
import time
import unittest

from examples import preview_single_agent_qualification as q
from examples.preview_single_agent_values import generate
from fusion.contracts import ContractError, canonical, digest
from tests.test_phase2_operator_values import image_manifest_fixture


class ProtocolFixture:
    namespace = 'omega-ref-protocol-fixture'

    def __init__(self, values, destination):
        self.p = values['preview']
        self.destination = destination
        self.calls, self.receipts = [], []
        self.wrong_projection = False
        self.changed_deadline = False
        self.lost_submission_reply = False
        self.populated = False
        self.page_size = 1
        self.states = [(1, {'task': 'Synthetic solo task note'}),
                       (1, {'task': 'Synthetic solo task note'}),
                       (2, {'task': 'Synthetic solo task note', 'detail': 'Synthetic solo detail note'}),
                       (3, {'detail': 'Synthetic solo detail note'}),
                       (3, {'detail': 'Synthetic solo detail note'})]
        self.projections = ['(RESULTS: ((COMMAND_RETURN: ((metta fixture) (stv 0.5599999999999999 0.4032)))))']
        for revision, items in self.states:
            value = dict(profile='working-task-context/1', revision=revision, items=items,
                digest=digest(canonical(items)), interpretation='unverified-task-notes')
            self.projections.append('(RESULTS: ((COMMAND_RETURN: ((fixture) '+canonical(value).decode().replace('"','_quote_')+'))))')

    def owned(self):
        return {'metadata': {'uid':'fixture-namespace'}}

    def preflight(self):
        return {'classification':'EXPLICIT_PROTOCOL_FIXTURE', 'generative_runtime':'NOT_CONTACTED'}

    def workloads(self):
        return [dict(metadata=dict(name='omega-agent', uid='fixture-workload'),
            spec=dict(replicas=1, template=dict(spec=dict(containers=[{'image':'example@sha256:'+'a'*64}]))))]

    def binding(self):
        return dict(catalogue='fixture-catalogue', policy=self.p['policy_revision'],
            model_boundary='RECORDED_FIXTURE', limits=self.p['limits'])

    def k(self, *args, timeout=35):
        assert args[:6] == ('exec', 'omega-agent-0', '--', q.PYTHON, '-m', 'integration.single_node.preview_operator')
        assert 0 < timeout <= 35
        operation = args[6]
        opts = list(args[7:])
        self.calls.append((operation, opts))
        sid = self.p['agents']['omega-agent']['sessions'][0]
        if operation == 'inventory':
            value = dict(principal='A', scope=self.p['scope'], model_boundary='RECORDED_FIXTURE',
                additional_live_generations=0,
                sessions={s:self.binding() for s in self.p['agents']['omega-agent']['sessions']},
                catalogues={sid:dict(tools={name:{} for name in self.p['agents']['omega-agent']['tools']})})
        elif operation == 'create':
            value = dict(state='active', inputs=[], capacity=dict(accepted=int(self.populated)), binding=self.binding())
        elif operation == 'submit':
            identity = opts[opts.index('--identity')+1]
            # Observer must save identity before crossing an uncertain boundary.
            journal = json.loads((self.destination/'report.json').read_text())
            assert journal['inputs'][-1]['identity'] == identity
            assert 'accepted' not in journal['inputs'][-1]
            text = opts[opts.index('--text')+1]
            assert text == q.COMMANDS[len(self.receipts)]
            now = time.time_ns()//1_000_000
            value = dict(session=sid, id=identity, sequence=len(self.receipts)+1,
                assignment='synthetic-task', accepted=now, deadline=now+120000, state='accepted')
            self.receipts.append(copy.deepcopy(value))
            if self.lost_submission_reply:
                raise RuntimeError('Explicit authored lost-reply boundary')
        elif operation == 'observe':
            after = int(opts[opts.index('--after')+1])
            rows = []
            for index, receipt in enumerate(self.receipts):
                row = copy.deepcopy(receipt)
                row.update(state='complete', result=dict(turn=index, occurrences=['fixture-occurrence-'+str(index)],
                    projection=self.projections[index]))
                if self.changed_deadline:
                    row['deadline'] += 1
                if self.wrong_projection and index == 1:
                    row['result']['projection'] = row['result']['projection'].replace('Synthetic solo task note','Incorrect authored result')
                if row['sequence'] > after:
                    rows.append(row)
            selected = rows[:self.page_size]
            complete = len(selected) == len(rows)
            value = dict(session=sid, live_generations=0, inputs=selected, complete=complete,
                next_after=None if complete else selected[-1]['sequence'])
        else:
            raise AssertionError(operation)
        return json.dumps(value)


class SingleAgentQualification(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='single-agent-qualifier-')
        self.addCleanup(temp.cleanup)
        self.destination = Path(temp.name)/'report'
        self.values = generate(image_manifest_fixture(), 'synthetic-single-qualifier')
        self.operator = ProtocolFixture(self.values, self.destination)
        self.runner = q.Qualification(self.operator, self.values, self.destination)

    def error(self, code, operation):
        with self.assertRaises(ContractError) as caught:
            operation()
        self.assertEqual(caught.exception.code, code)

    def test_six_actual_operator_requests_observed_across_pages_and_preserved(self):
        result = self.runner.run()
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(result['completed_inputs'], 6)
        self.assertEqual(result['additional_live_generations'], 0)
        self.assertEqual([entry['command'] for entry in result['inputs']], list(q.COMMANDS))
        self.assertEqual(len({entry['identity'] for entry in result['inputs']}), 6)
        for entry in result['inputs']:
            self.assertEqual(entry['accepted']['deadline'], entry['observed']['deadline'])
            self.assertEqual(entry['accepted']['accepted'], entry['observed']['accepted'])
        self.assertEqual(result['inputs'][-1]['verified']['items'], {'detail':'Synthetic solo detail note'})
        self.assertTrue(any(op == 'observe' and opts[-1] == '5' for op, opts in self.operator.calls))
        self.assertEqual([op for op,_ in self.operator.calls].count('submit'), 6)
        self.assertEqual(json.loads((self.destination/'report.json').read_text()), result)

    def test_wrong_context_capture_stops_before_another_command(self):
        self.operator.wrong_projection = True
        self.error('NOT_AVAILABLE', self.runner.run)
        self.assertEqual(len(self.operator.receipts), 2)
        self.assertEqual(self.runner.report['status'], 'FAILED')
        self.assertIn('Incorrect authored result', self.runner.report['inputs'][-1]['observed']['result']['projection'])

    def test_changed_original_deadline_refuses_even_completed_result(self):
        self.operator.changed_deadline = True
        self.error('CONFLICT', self.runner.run)
        self.assertEqual(len(self.operator.receipts), 1)

    def test_lost_submission_reply_preserves_identity_and_never_resubmits(self):
        self.operator.lost_submission_reply = True
        with self.assertRaises(RuntimeError):
            self.runner.run()
        report = json.loads((self.destination/'report.json').read_text())
        self.assertEqual(report['status'], 'FAILED')
        self.assertFalse(report['automatic_resubmission'])
        self.assertEqual(len(self.operator.receipts), 1)
        self.assertEqual(report['inputs'][0]['identity'], self.operator.receipts[0]['id'])
        self.assertNotIn('accepted', report['inputs'][0])

    def test_prepopulated_session_refused_before_submission(self):
        self.operator.populated = True
        self.error('CONFLICT', self.runner.run)
        self.assertEqual(self.operator.receipts, [])

    def test_generation_and_two_agent_selection_refused_before_operator_activity(self):
        self.values['preview']['model_boundary'] = 'REAL'
        self.error('UNAUTHORIZED', self.runner.run)
        self.assertEqual(self.operator.calls, [])
        self.values['preview']['model_boundary'] = 'RECORDED_FIXTURE'
        self.values['preview']['agents']['omega-agent-b'] = {}
        self.error('UNSUPPORTED_PROFILE', self.runner.run)
        self.assertEqual(self.operator.calls, [])

    def test_expired_observer_does_not_call_provider_or_extend_deadline(self):
        self.error('DEADLINE_EXCEEDED', lambda:self.runner.observe(time.monotonic()-1))
        self.assertEqual(self.operator.calls, [])

    def test_malformed_pagination_cursor_refused_without_infinite_polling(self):
        self.runner.setup()
        original = self.operator.k
        def malformed(*args, **kwargs):
            if args[6] == 'observe':
                return json.dumps(dict(session=self.runner.sid, live_generations=0,
                    inputs=[], complete=False, next_after=0))
            return original(*args, **kwargs)
        self.operator.k = malformed
        self.error('CONFLICT', lambda:self.runner.observe(time.monotonic()+10))
        self.assertEqual(self.operator.receipts, [])


if __name__ == '__main__':
    unittest.main()
