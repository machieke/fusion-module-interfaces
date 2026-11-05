"""Observer/export fixture checks, not native workflow execution evidence."""
import json,tempfile,time,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
from fusion.contracts import ContractError,canonical,digest
from examples.pilot_workflows import await_delegation,native_capture,close_consumed_sessions
from integration.single_node.pilot_evidence import native_inputs

class WorkflowQualification(unittest.TestCase):
    def test_observer_expiry_does_not_submit_or_drain(self):
        r=Mock();r.call.return_value={'inputs':[]}
        with self.assertRaisesRegex(ContractError,'NOT_AVAILABLE'):
            await_delegation(r,'session',{'deadline':1},time.monotonic()-1)
        self.assertEqual(len(r.call.call_args_list),1)
        self.assertEqual(r.call.call_args.args,('omega-agent','observe','session','--content'))
    def test_multiple_same_deadline_results_are_ambiguous(self):
        r=Mock();r.call.return_value={'inputs':[dict(assignment='delegated-result',deadline=20,state='complete')]*2}
        with self.assertRaisesRegex(ContractError,'CONFLICT'):await_delegation(r,'session',{'deadline':20},time.monotonic()+1)
    def test_export_binds_only_actual_workflow_receipts_and_captures(self):
        result=dict(projection='fixture projection',occurrences=['fixture occurrence'],turn=1)
        receipt=dict(id='input',session='session',accepted=10,deadline=20,assignment='synthetic-task',sequence=1,state='complete')
        row=dict(receipt,payload=dict(assignment='synthetic-task',text='task-context'),result=result)
        step=dict(input_id='input',version=1,receipt=receipt,deadline_ms=20,result_sha256=digest(canonical(result)))
        current=dict(workflow='workflow',steps={'followup':step});observed=dict(session='session',inputs=[row])
        r=SimpleNamespace(report={'inputs':[]},op=SimpleNamespace(namespace='fixture-only'))
        with tempfile.TemporaryDirectory() as directory:
            checksum=native_capture(directory,r,current,observed);raw=(Path(directory)/'workflow-native.json').read_bytes()
            self.assertEqual(digest(raw),checksum);self.assertEqual(native_inputs(json.loads(raw))['captured_inputs'],1)
            self.assertEqual(r.report['inputs'],[])
            step['deadline_ms']=21
            with self.assertRaisesRegex(ContractError,'CONFLICT'):native_capture(directory,r,current,observed)
    def test_cleanup_refuses_pending_effects_before_closing(self):
        r=Mock();r.call.return_value={'inputs':[{'state':'dispatched'}]}
        with self.assertRaisesRegex(ContractError,'NOT_AVAILABLE'):close_consumed_sessions(r,'session','workflow')
        self.assertEqual(len(r.call.call_args_list),1)


class WorkflowFaultCleanup(unittest.TestCase):
    def test_revocation_restores_original_credential_even_on_observer_failure(self):
        from examples.pilot_workflow_faults import storage_guard_fault
        original={'metadata':{'name':'fusion-storage-tls-auth'},'kind':'Secret','data':{
            'caller-token':'Zml4dHVyZQ==','caller-A-token':'Zml4dHVyZQ==','unrelated':'retained-fixture'}}
        writes=[];op=Mock(namespace='omega-ref-pilot-fixture')
        def k(*args,**kw):
            if args[:2]==('get','statefulset'):return json.dumps({'spec':{'replicas':1}})
            if args[:2]==('get','secret'):return json.dumps(original)
            if args[0]=='replace':writes.append(json.loads(kw['data']));return ''
            raise AssertionError(args)
        op.k.side_effect=k
        pod={'uid':'fixture-pod','images':['fixture-image'],'volumes':['fixture-volume']};report={}
        with patch('examples.pilot_workflow_faults.Recovery.pod',return_value=pod),patch('examples.pilot_workflow_faults.Recovery.replace',return_value={'fixture':'replacement'}):
            with self.assertRaisesRegex(RuntimeError,'observer failure'):
                with storage_guard_fault(op,'unauthorized',report):raise RuntimeError('observer failure')
        self.assertEqual(len(writes),2)
        self.assertNotEqual(writes[0]['data']['caller-A-token'],original['data']['caller-A-token'])
        self.assertEqual(writes[0]['data']['caller-A-token'],writes[0]['data']['caller-token'])
        self.assertEqual(writes[0]['data']['unrelated'],original['data']['unrelated'])
        self.assertEqual(writes[1]['data']['caller-A-token'],original['data']['caller-A-token'])
        self.assertEqual(writes[1]['data'],original['data'])
        self.assertNotIn(original['data']['caller-A-token'],json.dumps(report))
        self.assertTrue(report['original_provider_placement_restored'])
    def test_mismatched_aliases_refused_before_secret_or_pod_mutation(self):
        from examples.pilot_workflow_faults import storage_guard_fault
        op=Mock(namespace='omega-ref-pilot-fixture');op.k.side_effect=[json.dumps({'spec':{'replicas':1}}),
            json.dumps({'data':{'caller-token':'fixture-one','caller-A-token':'fixture-two'}})]
        with patch('examples.pilot_workflow_faults.Recovery.pod',return_value={}),patch('examples.pilot_workflow_faults.Recovery.replace') as replacement:
            with self.assertRaisesRegex(ContractError,'CONFLICT'):
                with storage_guard_fault(op,'unauthorized',{}):self.fail('invalid configuration yielded')
            replacement.assert_not_called()
        self.assertFalse(any(x.args[0]=='replace' for x in op.k.call_args_list))
    def test_missing_alias_refused_before_secret_or_pod_mutation(self):
        from examples.pilot_workflow_faults import storage_guard_fault
        op=Mock(namespace='omega-ref-pilot-fixture');op.k.side_effect=[json.dumps({'spec':{'replicas':1}}),
            json.dumps({'data':{'caller-A-token':'fixture-one'}})]
        with patch('examples.pilot_workflow_faults.Recovery.pod',return_value={}),patch('examples.pilot_workflow_faults.Recovery.replace') as replacement:
            with self.assertRaisesRegex(ContractError,'CONFLICT'):
                with storage_guard_fault(op,'unauthorized',{}):self.fail('missing alias yielded')
            replacement.assert_not_called()
        self.assertFalse(any(x.args[0]=='replace' for x in op.k.call_args_list))
    def test_first_replacement_failure_still_restores_both_aliases(self):
        from examples.pilot_workflow_faults import storage_guard_fault
        initial={'data':{'caller-token':'fixture-one','caller-A-token':'fixture-one'}};writes=[]
        op=Mock(namespace='omega-ref-pilot-fixture')
        def k(*args,**kwargs):
            if args[:2]==('get','statefulset'):return json.dumps({'spec':{'replicas':1}})
            if args[:2]==('get','secret'):return json.dumps(initial)
            if args[0]=='replace':writes.append(json.loads(kwargs['data']));return ''
            raise AssertionError(args)
        op.k.side_effect=k;pod={'images':['fixture'],'volumes':['fixture']};report={}
        with patch('examples.pilot_workflow_faults.Recovery.pod',return_value=pod),patch('examples.pilot_workflow_faults.Recovery.replace',side_effect=[RuntimeError('fixture startup failure'),{'fixture':'restored'}]):
            with self.assertRaisesRegex(RuntimeError,'fixture startup failure'):
                with storage_guard_fault(op,'unauthorized',report):self.fail('failed replacement yielded')
        self.assertEqual(len(writes),2);self.assertEqual(writes[-1]['data'],initial['data'])
        self.assertTrue(report['original_provider_placement_restored'])
    def test_unknown_owner_outage_restored_without_native_resubmission(self):
        from examples.pilot_workflow_faults import storage_guard_fault
        op=Mock(namespace='omega-ref-pilot-fixture');replicas=[1];calls=[]
        def k(*args,**kw):
            calls.append(args)
            if args[:2]==('get','statefulset'):return json.dumps({'spec':{'replicas':replicas[0]}})
            if args[0]=='scale':replicas[0]=int(args[-1].split('=')[1])
            return ''
        op.k.side_effect=k;pod={'uid':'fixture-pod','images':['fixture-image'],'volumes':['fixture-volume']};report={}
        with patch('examples.pilot_workflow_faults.Recovery.pod',return_value=pod):
            with storage_guard_fault(op,'unknown',report):self.assertEqual(replicas[0],0)
        self.assertEqual(replicas[0],1);self.assertFalse(report['accepted_inputs_changed'])
        self.assertEqual([x[-1] for x in calls if x[0]=='scale'],['--replicas=0','--replicas=1'])

class WorkflowCloneObservation(unittest.TestCase):
    def test_exact_retained_fields_and_no_effect_authority(self):
        from examples.pilot_workflow_restore import retained
        before=dict(status='complete',deadline_ms=2000,reservations_spent=2,observations_spent=3,
            steps={'first':dict(result_sha256='a'*64)},checkpoints=[{'identity':'historical'}],observation_only=False)
        after=dict(before,restore_fenced=True,execution_authorized=False,observation_only=True,
            guard_refresh_performed=False,retained_approval_is_current_authority=False)
        self.assertEqual(retained(before,after)['new_native_inputs'],0)
        for key,value in [('deadline_ms',2001),('reservations_spent',1),('guard_refresh_performed',True),('execution_authorized',True)]:
            with self.subTest(key=key),self.assertRaisesRegex(ContractError,'CONFLICT'):retained(before,dict(after,**{key:value}))

class ArchiveWorkflowObserver(unittest.TestCase):
    def test_guard_binds_actual_sealed_payload_and_content_type(self):
        from examples.pilot_workflow_archive import archive
        import uuid
        ref=dict(scope_ref='synthetic-fixture',id=str(uuid.uuid4()),revision=1,digest='a'*64)
        sealed=dict(state='sealed');reply=dict(hydrated_payload=ref,sealed=sealed,observation={'archive':sealed},
            source_head_unchanged=True,plan={'records':[{'ref':ref}]},content_type='application/json')
        op=Mock(namespace='omega-ref-pilot-fixture');op.k.return_value=json.dumps(reply)
        guard,report=archive(op,str(uuid.uuid4()),dict(memory={'target':{'payload':ref}},source={'fixture':'head'}))
        self.assertEqual(guard['target'],dict(ref=ref,content_type='application/json'))
        self.assertEqual(report['additional_native_inputs'],0)
        reply['sealed']['state']='reserved';op.k.return_value=json.dumps(reply)
        with self.assertRaisesRegex(ContractError,'CONFLICT'):
            archive(op,str(uuid.uuid4()),dict(memory={'target':{'payload':ref}},source={'fixture':'head'}))

if __name__=='__main__':unittest.main()
