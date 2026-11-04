"""Real application SQLite; explicit task, payload, execution and event fixtures.

The replayed workflow never calculates an answer. Real deployed execution is
qualified separately. No native/HTTPS/DeTTa/chain claim from this unit lane.
"""
import copy,json,unittest
from fusion.contracts import canonical,ContractError
from fusion import execution_envelope as e
from fusion.registry import select,descriptors
from fusion.preview_native_inspect import NativeInspection
from tests import test_phase2_native_inspect as base


class Continuations(base.NativeInspectionTests):
    def setUp(self):
        super().setUp()
        self.backend.frozen={'envelopes':e.PROFILE}
        self.backend.selected=select(descriptors(atom_provider='fixture-files'))
        self.app.binding['inspection']=self.backend.frozen
        original=self.backend.invoke
        def invoke(q,*,envelope=None):
            if q['operation']=='submit':e.check(envelope,q,'A',self.backend.selected['execution'])
            return original(q)
        self.backend.invoke=invoke
        self.events=[]
        def events(job,source=None,after=0,limit=3):
            kinds=['accepted'] if self.backend.status_value=='queued' else ['accepted','result-committed']
            value=dict(profile='execution-commit-cursor/1',scope=base.SCOPE,source='explicit-commit-source-fixture',
                job_id=job,head=len(kinds),after=after,next=len(kinds),gap=False,ordering='per-task-owner-commit',
                events=[dict(sequence=i+1,kind=kinds[i],job_id=job) for i in range(after,len(kinds))])
            self.events.append(copy.deepcopy(value));return value
        self.backend.events=events
        self.native=NativeInspection(self.app)
        with self.app.db:
            self.app.db.execute('BEGIN IMMEDIATE')
            self.native.continuation.admit(self.row['id'],self.task['id'],self.row['deadline'])

    def test_fixed_graph_capture_and_observation_does_not_execute(self):
        result=self.replay();state=self.native.continuation.observe(self.row)
        self.assertEqual(state['status'],'return-ready');self.assertEqual(len(state['steps']),7)
        self.assertEqual(state['cursor']['head'],2);self.assertEqual(state['chain_authority'],'NOT_GRANTED')
        self.assertLessEqual(state['relay_calls_spent'],32);before=copy.deepcopy(self.backend.requests)
        self.assertEqual(self.native.continuation.observe(self.row),state)
        self.assertEqual(before,self.backend.requests)
        self.assertEqual(json.loads(result)['job_id'],self.backend.job)

    def test_cursor_capture_interruption_consumes_same_commits_without_resubmit(self):
        self.interrupt('after_inspect_cursor_capture')
        with self.assertRaises(RuntimeError):self.replay()
        accepted=self.backend.accepted.copy();spent=self.native.state(self.row)['calls']
        self.reopen();self.replay()
        self.assertEqual(self.backend.accepted,accepted)
        self.assertEqual(sum(x['operation']=='submit' for x in self.backend.requests),1)
        self.assertEqual(self.events[-1]['after'],2)
        self.assertEqual(self.events[-1]['events'],[])
        self.assertGreater(self.native.state(self.row)['calls'],spent)

    def test_saved_result_recovery_reads_no_more_commit_notifications(self):
        self.interrupt('after_inspect_result_capture')
        with self.assertRaises(RuntimeError):self.replay()
        events=copy.deepcopy(self.events);result=self.native.state(self.row)['result']
        self.now=self.row['deadline']+1;self.reopen();self.replay()
        self.assertEqual(self.events,events);self.assertEqual(self.native.state(self.row)['result'],result)
        self.assertEqual(sum(x['operation']=='submit' for x in self.backend.requests),1)

    def test_cancel_before_dispatch_and_uncertain_after_request_remain_fenced(self):
        c=self.native.continuation
        value=c.control(self.row,'cancel','cancel-once')
        self.assertEqual(value['status'],'cancelled-before-submit')
        self.assertEqual(c.control(self.row,'cancel','cancel-once'),value)
        self.error('CONFLICT',c.control,self.row,'cancel','changed-id')
        self.error('NOT_AVAILABLE',self.replay)
        self.assertEqual(self.backend.requests,[])
        self.assertEqual(self.native.state(self.row)['calls'],0)

    def test_cancel_after_request_does_not_resubmit_or_ack(self):
        self.interrupt('after_inspect_request_capture')
        with self.assertRaises(RuntimeError):self.replay()
        self.reopen();value=self.native.continuation.control(self.row,'cancel','cancel-uncertain')
        self.assertEqual(value['status'],'needs-reconciliation')
        self.error('NOT_AVAILABLE',self.replay)
        self.assertEqual(self.backend.requests,[])
        self.assertFalse(self.backend.acked)

    def test_unsubscribe_retains_cursor_and_cannot_create_a_result(self):
        self.interrupt('after_inspect_cursor_capture')
        with self.assertRaises(RuntimeError):self.replay()
        self.reopen();c=self.native.continuation;before=c.observe(self.row)
        state=c.control(self.row,'unsubscribe','stop-observation')
        self.assertFalse(state['subscription']);self.assertEqual(state['cursor'],before['cursor'])
        self.error('NOT_AVAILABLE',self.replay)
        self.assertIsNone(self.native.state(self.row)['result'])

    def test_current_revocation_and_capture_corruption_are_not_repaired(self):
        self.replay();state=self.native.continuation.observe(self.row)
        self.authorize.side_effect=ContractError('UNAUTHORIZED')
        self.error('UNAUTHORIZED',self.native.continuation.observe,self.row)
        self.authorize.side_effect=None
        with self.app.db:self.app.db.execute("UPDATE preview_inspections SET result='{}' WHERE occurrence=?",(self.row['id'],))
        self.error('NOT_AVAILABLE',self.native.continuation.observe,self.row)
        self.assertEqual(state['chain_authority'],'NOT_GRANTED')


def load_tests(loader,tests,pattern):
    return unittest.TestSuite(Continuations(name) for name in Continuations.__dict__ if name.startswith('test_'))
