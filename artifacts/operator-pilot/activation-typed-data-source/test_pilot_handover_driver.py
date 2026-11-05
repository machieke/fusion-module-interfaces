"""Operator fault-injection scope checks; runtime/pod observations are fixtures."""
import base64,copy,io,json,tempfile,unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import Mock,patch
from examples.pilot_maintenance_faults import application_cleanup,kill
from fusion.contracts import ContractError
from integration.single_node.reference_ops import LABEL,OWNER


class OperatorFixture:
    namespace='omega-ref-pilot-fixture'
    def __init__(self,mismatch=False):
        self.killed=False;self.mismatch=mismatch;self.commands=[]
        self.pod=dict(metadata=dict(namespace=self.namespace,uid='pod',labels={'app.kubernetes.io/instance':'omega','app.kubernetes.io/name':'fusion-search'},
            ownerReferences=[dict(controller=True,kind='StatefulSet',name='fusion-search',uid='workload')]),
            spec=dict(nodeName='omega-fusion-k3s'),status=dict(containerStatuses=[dict(
                containerID='containerd://'+'a'*64,image='test:pin',imageID='test@sha256:'+'b'*64,
                restartCount=0,ready=True)]))
    def owned(self):return dict(metadata=dict(uid='namespace',labels={'omega.pilot/task':'task'}))
    def k(self,*a,**kw):
        if a[1]=='statefulset':return json.dumps(dict(metadata=dict(uid='workload',labels=self.pod['metadata']['labels'])))
        value=copy.deepcopy(self.pod)
        if self.killed:value['status']['containerStatuses'][0].update(restartCount=1,lastState=dict(terminated=dict(exitCode=137)))
        return json.dumps(value)
    def command(self,args,**kw):
        self.commands.append(args)
        if args[-3:-1]==['containers','info']:
            return json.dumps(dict(Image='test:pin',Labels={'io.kubernetes.pod.namespace':'other' if self.mismatch else self.namespace,
                'io.kubernetes.pod.uid':'pod','io.kubernetes.pod.name':'fusion-search-0','io.kubernetes.container.name':'fusion-search'}))
        assert args[-5:-1]==['tasks','kill','--signal','SIGKILL'];self.killed=True;return ''


class DriverSafety(unittest.TestCase):
    def test_closure_observation_is_explicit_bounded_read_only_and_does_not_retry_authority_failure(self):
        from examples.pilot_handover import closure_observe
        owner=Mock();owner.k.side_effect=[RuntimeError('fusion.contracts.ContractError: NOT_AVAILABLE'),'{"selected":"exact-view"}']
        notes=[]
        with patch('examples.pilot_handover.time.monotonic',return_value=10),patch('examples.pilot_handover.time.sleep'):
            result=closure_observe(owner,'omega-agent','fixed-read-script',{'snapshot':'exact'},15,notes.append)
        self.assertEqual(result,{'selected':'exact-view'});self.assertEqual(len(notes),2)
        for call in owner.k.call_args_list:
            self.assertEqual(call.args,('exec','-i','omega-agent-0','--','/opt/native/python/bin/python3.12','-c','fixed-read-script'))
            self.assertEqual(call.kwargs['timeout'],5);self.assertEqual(json.loads(call.kwargs['data']),{'snapshot':'exact'})
        self.assertEqual([x['status'] for x in notes],['READ_TRANSPORT_NOT_AVAILABLE','CAPTURED'])
        self.assertTrue(all(x['mutations']==0 and x['finished_ms']>=x['started_ms'] for x in notes))
        owner.reset_mock();owner.k.side_effect=RuntimeError('UNAUTHORIZED')
        with patch('examples.pilot_handover.time.monotonic',return_value=10):
            with self.assertRaisesRegex(RuntimeError,'UNAUTHORIZED'):closure_observe(owner,'omega-agent','fixed',{},15,Mock())
        self.assertEqual(owner.k.call_count,1)

    def test_closure_observation_stops_at_attempt_and_time_bounds(self):
        from examples.pilot_handover import closure_observe
        owner=Mock();owner.k.side_effect=RuntimeError('fusion.contracts.ContractError: NOT_AVAILABLE')
        with patch('examples.pilot_handover.time.monotonic',return_value=10),patch('examples.pilot_handover.time.sleep'):
            with self.assertRaisesRegex(ContractError,'NOT_AVAILABLE'):closure_observe(owner,'omega-agent','fixed',{},50,Mock())
        self.assertEqual(owner.k.call_count,8)
        owner.reset_mock();now=[10.0]
        with patch('examples.pilot_handover.time.monotonic',side_effect=lambda:now[0]),\
                patch('examples.pilot_handover.time.sleep',side_effect=lambda seconds:now.__setitem__(0,now[0]+seconds)):
            with self.assertRaisesRegex(ContractError,'DEADLINE_EXCEEDED'):closure_observe(owner,'omega-agent','fixed',{},10.5,Mock())
        self.assertEqual(owner.k.call_count,2);self.assertEqual(now[0],10.5)

    def test_private_denial_probe_executes_and_requires_exact_authorization_refusal(self):
        from examples.pilot_handover import PRIVATE_DENIAL
        code=compile(PRIVATE_DENIAL,'private-denial-probe','exec')
        reference={'scope_ref':'synthetic-private','fixture':'reference'}
        with patch('pathlib.Path.read_bytes',return_value=b'{"scope":"shared","principal":"other"}'),\
                patch('fusion.preview_atoms.client') as client,patch('sys.stdin',io.StringIO(json.dumps(reference))),\
                patch('sys.stdout',new_callable=io.StringIO) as output:
            client.return_value.get.side_effect=ContractError('UNAUTHORIZED');exec(code,{})
            self.assertEqual(json.loads(output.getvalue()),dict(code='UNAUTHORIZED',returned_private_payload=False))
            client.assert_called_once_with(dict(scope='synthetic-private',principal='other'))
            client.return_value.get.assert_called_once_with(reference)
        for failure in (None,ContractError('NOT_AVAILABLE')):
            with patch('pathlib.Path.read_bytes',return_value=b'{"scope":"shared"}'),\
                    patch('fusion.preview_atoms.client') as client,patch('sys.stdin',io.StringIO(json.dumps(reference))):
                client.return_value.get.side_effect=failure
                with self.assertRaisesRegex(ContractError,'CONFLICT'):exec(code,{})

    def test_retained_runner_only_observes_original_inputs_and_preserves_window(self):
        from examples.pilot_handover import retained_runner
        from examples.integrated_sustained import IntegratedRunner
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'source-native').mkdir()
            observed=[dict(id=str(i),state='complete',deadline=1500+i) for i in range(3)]
            saved=dict(allocations=[dict(role='omega-agent',value=dict(session='s'))],
                inputs=[dict(identity=str(i),session='s',started_ms=1000,observed=value) for i,value in enumerate(observed)])
            (root/'source-native/report.json').write_text(json.dumps(saved))
            with patch.object(IntegratedRunner,'call',return_value=dict(inputs=observed)) as call,\
                    patch('examples.pilot_handover.time.time_ns',return_value=2000000000),\
                    patch('examples.pilot_handover.time.monotonic',return_value=10):
                r=retained_runner(Mock(),root,3)
            self.assertEqual(r.count,3);self.assertEqual(r.end,3609);self.assertEqual(r.report,saved)
            call.assert_called_once_with('omega-agent','observe','s','--content')
            with patch.object(IntegratedRunner,'call') as call:
                with self.assertRaisesRegex(ContractError,'CONFLICT'):retained_runner(Mock(),root,4)
                call.assert_not_called()
            with patch.object(IntegratedRunner,'call') as call,patch('examples.pilot_handover.time.time_ns',return_value=3601000000000):
                with self.assertRaisesRegex(ContractError,'DEADLINE_EXCEEDED'):retained_runner(Mock(),root,3)
                call.assert_not_called()

    def test_cleanup_waits_for_child_exit_then_applies_once_and_rehydrates_exact_source(self):
        calls=[];records=[];reference=dict(fixture='immutable-source-reference')
        captured=[dict(reference=reference,body_sha256='a'*64)]
        class Owner:
            def k(self,*args,**kw):
                request=json.loads(kw['data']);operation=request.get('operation','hydrate');calls.append(operation)
                self_test.assertLessEqual(kw['timeout'],10)
                if operation=='inventory':
                    if len(calls)==1:raise RuntimeError('native child still running: NOT_AVAILABLE')
                    return json.dumps(dict(selection=dict(overlays=[],materializations=['retained'],duplicate_startup=False)))
                if operation=='plan':return json.dumps(dict(plan=dict(candidates=[dict(kind='history-materialization',reference=reference)])))
                if operation=='apply':
                    self_test.assertEqual([r[0] for r in records],['application-derived-inventory','application-derived-plan'])
                    self.intent=request
                if operation in ('apply','observe'):
                    self_test.assertEqual(request['body'],self.intent['body'])
                    return json.dumps(dict(state='complete',fixture='committed-owner-receipt'))
                self_test.assertEqual(request,dict(session='exact-session',references=[reference]))
                return json.dumps(captured)
        self_test=self;end=20
        def record(stage,value):records.append((stage,value));return value
        with patch('examples.pilot_endurance.time.monotonic',return_value=10),patch('examples.pilot_endurance.time.sleep'):
            result=application_cleanup(Owner(),'exact-session',record,end)
        self.assertEqual(end,20);self.assertEqual(result,captured)
        self.assertEqual(calls,['inventory','inventory','plan','apply','observe','hydrate'])
        self.assertEqual(dict(records)['application-derived-cleanup-observations'],dict(inventory_observations=2,apply_calls=1,replay_exact=True))
        self.assertEqual(records[-1],('history-source-rehydration-after-cleanup',captured))

    def test_cleanup_wait_expiry_never_applies_or_hydrates(self):
        owner=Mock();owner.k.side_effect=RuntimeError('NOT_AVAILABLE');now=[10.0];end=10.75;record=Mock()
        def sleep(seconds):now[0]+=seconds
        with patch('examples.pilot_endurance.time.monotonic',side_effect=lambda:now[0]),patch('examples.pilot_endurance.time.sleep',side_effect=sleep):
            with self.assertRaisesRegex(ContractError,'DEADLINE_EXCEEDED'):application_cleanup(owner,'exact-session',record,end)
        self.assertEqual(end,10.75);self.assertEqual(now[0],end);self.assertEqual(owner.k.call_count,2)
        self.assertEqual([json.loads(c.kwargs['data'])['operation'] for c in owner.k.call_args_list],['inventory','inventory'])
        record.assert_not_called()

    def test_cleanup_requires_positive_candidate_and_never_claims_empty_cleanup(self):
        owner=Mock();owner.k.return_value=json.dumps(dict(selection=dict(overlays=[],materializations=[],duplicate_startup=False)))
        record=Mock()
        with patch('examples.pilot_endurance.time.monotonic',return_value=10):
            with self.assertRaisesRegex(ContractError,'NOT_AVAILABLE'):application_cleanup(owner,'exact-session',record,20)
        self.assertEqual(owner.k.call_count,1);self.assertEqual(record.call_count,1)
        self.assertEqual(record.call_args.args[0],'application-derived-inventory')

    def test_lost_cleanup_reply_is_not_retried(self):
        owner=Mock();owner.k.side_effect=[json.dumps(dict(selection=dict(overlays=[],materializations=[],duplicate_startup=True))),
            json.dumps(dict(plan=dict(candidates=[]))),RuntimeError('lost reply')]
        with patch('examples.pilot_endurance.time.monotonic',return_value=10):
            with self.assertRaisesRegex(RuntimeError,'lost reply'):application_cleanup(owner,'exact-session',Mock(),20)
        self.assertEqual([json.loads(c.kwargs['data'])['operation'] for c in owner.k.call_args_list],['inventory','plan','apply'])

    def test_exact_current_runtime_task_only(self):
        op=OperatorFixture();value=kill(op,'fusion-search')
        self.assertTrue(op.killed);self.assertEqual(value['exit_code'],137);self.assertEqual(value['namespace_uid'],'namespace')
        self.assertEqual(value['container_id'],'a'*64)
    def test_foreign_runtime_identity_refused_before_signal(self):
        op=OperatorFixture(True)
        with self.assertRaises(ContractError) as error:kill(op,'fusion-search')
        self.assertEqual(error.exception.code,'UNAUTHORIZED');self.assertFalse(op.killed)

    def test_image_manifest_is_required_before_operator_construction(self):
        from examples.pilot_handover import main
        args=['qualify-handover']
        for name in ('kubeconfig','context','namespace','replacement','chart','values','directory','authority-file','task'):
            args+=['--'+name,'fixture']
        with patch('sys.argv',args),patch('examples.pilot_handover.Operator') as operator,redirect_stderr(io.StringIO()) as error:
            with self.assertRaises(SystemExit) as stopped:main()
        self.assertEqual(stopped.exception.code,2);self.assertIn('--images',error.getvalue());operator.assert_not_called()

    def test_manifest_without_verified_export_refuses_before_cluster_contact(self):
        from examples.pilot_handover import qualify
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);values=root/'values.json';images=root/'images.json'
            values.write_text(json.dumps(dict(preview={})));images.write_text(json.dumps(dict(source_export_verification='NOT_RUN')))
            original=Mock(namespace='omega-ref-pilot-source');replacement=Mock(namespace='omega-ref-pilot-target')
            with patch('examples.pilot_handover.IntegratedRunner') as runner:
                with self.assertRaises(ContractError) as error:
                    qualify(original,replacement,root/'chart',values,images,root/'run',root/'authority','fixture')
            self.assertEqual(error.exception.code,'CONFLICT');self.assertEqual(original.method_calls,[])
            self.assertEqual(replacement.method_calls,[]);runner.assert_not_called()

    def test_actual_source_mismatch_refuses_before_native_admission_and_records_failure(self):
        from examples.pilot_handover import qualify
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);values=root/'values.json';images=root/'images.json';authority=root/'authority.json'
            original=Mock(namespace='omega-ref-pilot-source');replacement=Mock(namespace='omega-ref-pilot-target')
            current=dict(state='active',generation=1,deployment=original.namespace);authority.write_text(json.dumps(current))
            original.owned.return_value=dict(metadata=dict(labels={'omega.pilot/task':'fixture'}));original.workloads.return_value=[]
            original.k.return_value=json.dumps(dict(data={'current.json':base64.b64encode(authority.read_bytes()).decode()}))
            source=dict(preview=dict(profile='omega-single-node-sustained-preview/1',model_boundary='RECORDED_FIXTURE',
                agents={'omega-agent':dict(tools=['query'])},pilot=dict(writer_fence=dict(deployment=original.namespace,generation=1))))
            values.write_text(json.dumps(source));images.write_text(json.dumps(dict(source_manifest_sha256='a'*64)))
            plan=dict(fixture='exact-selected-plan')
            with patch('examples.pilot_handover.freeze',return_value=plan),patch('examples.pilot_handover.IntegratedRunner') as runner,\
                    patch('examples.pilot_handover.verify_installed',side_effect=ContractError('CONFLICT')) as verify:
                with self.assertRaises(ContractError):
                    qualify(original,replacement,root/'chart',values,images,root/'run',authority,'fixture')
                verify.assert_called_once_with(plan,original);runner.return_value.call.assert_not_called()
            report=json.loads((root/'run/report.json').read_bytes())
            self.assertEqual(report['status'],'FAIL');self.assertEqual(report['failure']['code'],'CONFLICT')
            self.assertEqual(report['artifact_binding']['source_manifest_sha256'],'a'*64)
            self.assertEqual(replacement.method_calls,[])

    def test_activated_restart_observes_exact_capture_and_spent_accounting_without_submission(self):
        from examples.pilot_handover import restart_activated_caller
        op=Mock(namespace='omega-ref-pilot-replacement')
        def pod(uid):return json.dumps(dict(metadata=dict(namespace=op.namespace,uid=uid,labels={'app.kubernetes.io/name':'omega-agent'})))
        op.k.side_effect=[pod('before'),'', '',pod('after')]
        captured=dict(inputs=[dict(id='exact',deadline=123,result='retained')]);runner=Mock(end=20)
        runner.call.return_value=captured
        with patch('examples.pilot_handover.verify_installed',return_value={'status':'PASS'}) as verify,\
                patch('examples.pilot_handover.diagnostic') as diagnostic,patch('examples.pilot_handover.time.monotonic',return_value=10):
            diagnostic.return_value.model_accounting.return_value={'spent':1,'capture':None}
            result=restart_activated_caller(op,runner,{'fixture':'exact-plan'},('retained',),'unknown')
        self.assertEqual(result['new_native_inputs'],0);self.assertTrue(result['captures_exact']);self.assertTrue(result['unknown_accounting_exact'])
        self.assertEqual(runner.call.call_count,2)
        for call in runner.call.call_args_list:self.assertEqual(call.args,('omega-agent','observe','retained','--content'))
        verify.assert_called_once_with({'fixture':'exact-plan'},op)
        self.assertEqual(runner.end,20)

    def test_restart_refuses_changed_capture_and_never_resubmits(self):
        from examples.pilot_handover import restart_activated_caller
        op=Mock(namespace='omega-ref-pilot-replacement')
        def pod(uid):return json.dumps(dict(metadata=dict(namespace=op.namespace,uid=uid,labels={'app.kubernetes.io/name':'omega-agent'})))
        op.k.side_effect=[pod('before'),'','',pod('after')];runner=Mock(end=20)
        runner.call.side_effect=[dict(inputs=[dict(id='same',deadline=123)]),dict(inputs=[dict(id='same',deadline=124)])]
        with patch('examples.pilot_handover.verify_installed',return_value={'status':'PASS'}),\
                patch('examples.pilot_handover.diagnostic'),patch('examples.pilot_handover.time.monotonic',return_value=10):
            with self.assertRaisesRegex(ContractError,'CONFLICT'):restart_activated_caller(op,runner,{},('retained',),'unknown')
        self.assertEqual(runner.call.call_count,2)
        for call in runner.call.call_args_list:self.assertEqual(call.args[1],'observe')


if __name__=='__main__':unittest.main()
