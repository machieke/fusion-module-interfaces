"""Fixture tests of fail-closed operator observations; no deployed result claim."""
import json,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
from fusion.contracts import ContractError
from examples.pilot_incidents import outages,retained,reply_reads

class IncidentSafety(unittest.TestCase):
    def test_reply_observer_cannot_extend_original_programme_bound(self):
        with tempfile.TemporaryDirectory() as directory:
            fault=Mock(values={'components':{'fusion-storage':{'config':{}}}},
                       values_path=Path(directory)/'values.yaml',chart='fixture-chart')
            fault.read.return_value=None
            op=Mock();op.k.return_value=json.dumps(dict(status='PASS',value={'head':'saved'}))
            op.command.side_effect=ContractError('NOT_AVAILABLE')
            report={};r=Mock(end=100.5)
            with patch('examples.pilot_incidents.time.monotonic',return_value=100), \
                 patch('examples.pilot_incidents.time.time_ns',return_value=100000000000):
                with self.assertRaisesRegex(ContractError,'NOT_AVAILABLE'):
                    reply_reads(op,r,fault,'session',{},report,lambda:None)
            selected=fault.values['components']['fusion-storage']['config']['test']['reply_fault']
            self.assertEqual(selected['observer_deadline_ms'],100500)
            self.assertEqual(op.k.call_count,1)
            r.call.assert_not_called()

    def test_expiry_during_rollout_never_claims_a_missing_marker(self):
        with tempfile.TemporaryDirectory() as directory:
            clock=[100];rollouts=[0];head=dict(status='PASS',value={'head':'saved'})
            marker=dict(state='claimed');original=dict(identity='same',observed=dict(id='same',deadline=100123,result='saved'))
            fault=Mock(values={'components':{'fusion-storage':{'config':{}}}},
                       values_path=Path(directory)/'values.yaml',chart='fixture-chart')
            fault.read.side_effect=lambda role,name: marker if rollouts[0]==1 and 'partial-body' in name else None
            def rollout(*args,**kwargs):
                rollouts[0]+=1
                if rollouts[0]==2:clock[0]=102
            op=Mock();op.command.side_effect=rollout
            op.k.side_effect=[json.dumps(x) for x in (head,dict(status='REFUSED',code='NOT_AVAILABLE'),head,head)]
            r=Mock(end=101);r.call.return_value=dict(inputs=[original['observed']]);report={}
            with patch('examples.pilot_incidents.time.monotonic',side_effect=lambda:clock[0]), \
                 patch('examples.pilot_incidents.time.time_ns',side_effect=lambda:clock[0]*1000000000):
                with self.assertRaisesRegex(ContractError,'NOT_AVAILABLE'):
                    reply_reads(op,r,fault,'session',original,report,lambda:None)
            self.assertEqual(report['reply_read_faults'][0]['status'],'PASS')
            self.assertNotEqual(report['reply_read_faults'][1]['status'],'PASS')
            self.assertNotIn('marker',report['reply_read_faults'][1])
            self.assertEqual(op.k.call_count,4)  # No request after the programme expires.
            fault.replace.assert_not_called()

    def test_observation_failure_restores_only_selected_owner(self):
        class Fixture:
            def __init__(self):self.stopped=False;self.calls=[]
            def k(self,*args,**kw):
                self.calls.append(args)
                if args[:2]==('scale','statefulset'):
                    self.stopped=args[-1]=='--replicas=0';return ''
                if args[0]=='exec':return json.dumps(dict(status='REFUSED',code='UNAUTHORIZED') if self.stopped else dict(status='PASS'))
                return ''
        op=Fixture();r=Mock(end=1e30);fault=Mock();fault.pod.return_value=dict(images=['fixture'],volumes=['owned'])
        report={}
        with self.assertRaisesRegex(ContractError,'CONFLICT'):
            outages(op,r,fault,'s',{},report,lambda:None)
        self.assertFalse(op.stopped)
        self.assertEqual([x for x in op.calls if x[0]=='scale'],[
            ('scale','statefulset','fusion-embedding','--replicas=0'),
            ('scale','statefulset','fusion-embedding','--replicas=1')])
        self.assertEqual(len(report['dependency_outages']),1)
        self.assertNotEqual(report['dependency_outages'][0]['status'],'PASS')
        r.call.assert_not_called()  # An authorization failure is not normal outage.

    def test_capture_comparison_rejects_changed_deadline_or_result(self):
        original=dict(identity='same',observed=dict(id='same',deadline=123,result='captured'))
        r=Mock();r.call.return_value=dict(inputs=[dict(original['observed'])])
        self.assertTrue(retained(r,'session',original)['captured_result_exact'])
        for change in [dict(deadline=124),dict(result='replacement')]:
            r.call.return_value=dict(inputs=[{**original['observed'],**change}])
            with self.assertRaisesRegex(ContractError,'CONFLICT'):retained(r,'session',original)

    def test_outage_requires_typed_unavailable_and_valid_recovered_port(self):
        class Fixture:
            def __init__(self):self.calls=0
            def k(self,*args,**kw):
                if args[0]=='exec':
                    self.calls+=1
                    return json.dumps(dict(status='REFUSED',code='NOT_AVAILABLE') if self.calls%3==2 else dict(status='PASS'))
                return ''
        r=Mock(end=1e30);original=dict(identity='same',observed=dict(id='same',deadline=123,result='captured'))
        def observed(role,op,sid=None,*args):
            if op=='observe':return dict(inputs=[original['observed']])
            return dict(status='unavailable' if 'incident-down' in args[-1] else 'ready')
        r.call.side_effect=observed;fault=Mock();fault.pod.return_value=dict(images=['same'],volumes=['same'])
        op=Fixture();report={};rows=outages(op,r,fault,'s',original,report,lambda:None)
        self.assertEqual(len(rows),4);self.assertEqual(op.calls,12)
        self.assertTrue(all(row['status']=='PASS' and row['client_invocations']==3 for row in rows))
        self.assertTrue(all(row['new_work_admission']=='NOT_ATTEMPTED' for row in rows))
