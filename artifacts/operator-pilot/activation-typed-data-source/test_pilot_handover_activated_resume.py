"""Artifact-binding fixtures; no cluster or native execution is claimed."""
import base64,copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
from fusion.contracts import canonical,digest,ContractError
from examples.pilot_handover_activated_resume import repaired_binding,qualify,REPAIRED,OLD,NEW


class ActivatedRepair(unittest.TestCase):
    def test_retired_probe_uses_bounded_phase_reads_and_always_removes_its_pod(self):
        from examples.pilot_maintenance_faults import packet_refusal
        original=Mock(namespace='retired');replacement=Mock()
        original.workloads.return_value=[dict(metadata=dict(name='omega-agent'),spec=dict(template=dict(spec=dict(containers=[dict(image='fixture-pinned')]))))]
        replacement.k.side_effect=[json.dumps(dict(spec=dict(clusterIP='10.0.0.1',ports=[dict(port=8443)]))),'REACHABLE']
        def pod(phase):return json.dumps(dict(metadata=dict(namespace='retired',uid='exact-probe',labels={'omega.pilot/task':'task'}),status=dict(phase=phase)))
        original.k.side_effect=[pod('Pending'),pod('Succeeded'),json.dumps(dict(blocked=True,error_type='TimeoutError',errno=None)),'']
        with patch('examples.pilot_maintenance_faults.time.monotonic',return_value=10),patch('examples.pilot_maintenance_faults.time.sleep'):
            result=packet_refusal(original,replacement,'task')
        self.assertEqual(result['phase_observations'],['Pending','Succeeded']);self.assertEqual(original.apply.call_count,1)
        self.assertEqual([c.args[0] for c in original.k.call_args_list],['get','get','logs','delete'])
        self.assertNotIn('volumes',original.apply.call_args.args[0]['spec'])

    def test_historical_probe_exports_from_owner_and_uses_declared_caller_network_path(self):
        from examples.pilot_maintenance_faults import historical_refusals
        original,replacement=Mock(),Mock();original.workloads.return_value=[dict(metadata=dict(name='fusion-model'),
            spec=dict(template=dict(spec=dict(volumes=[dict(name='secrets',secret=dict(secretName='source-model'))]))))]
        original.k.return_value=json.dumps(dict(data={'caller-A-token':base64.b64encode(b'fixture-stale').decode()}))
        accepted=dict(session='selected-session',principal='caller-A',scope='synthetic-fixture')
        expected=dict(old_observation='unknown',spent_reservations=1,stale_credential='UNAUTHORIZED',historical_completion='UNAUTHORIZED')
        replacement.k.side_effect=[json.dumps(accepted),json.dumps(expected)]
        self.assertEqual(historical_refusals(original,replacement,'selected-session'),expected)
        owner,caller=replacement.k.call_args_list
        self.assertEqual(owner.args[2],'fusion-model-0');self.assertEqual(caller.args[2],'omega-agent-0')
        compile(owner.args[-1],'owner-export','exec');compile(caller.args[-1],'caller-probe','exec')
        self.assertNotIn('invoke(',owner.args[-1]);self.assertIn('/run/fusion/templates/shared/model.json',caller.args[-1])
        self.assertEqual(json.loads(owner.kwargs['data']),dict(session='selected-session'))
        self.assertEqual(json.loads(caller.kwargs['data']),dict(session='selected-session',accepted=accepted,stale='fixture-stale'))

    def test_network_probe_continuation_refuses_any_prior_new_admission(self):
        root=self.root/'resume';root.mkdir();(root/'replacement-native').mkdir()
        report=dict(status='FAIL',failure=dict(type='RuntimeError',code=None),steps=[dict(step='unknown-restored-accounting')],
            original='source',replacement='target',conservative_observer_stop_ms=1000)
        (root/'report.json').write_bytes(canonical(report));(root/'replacement-native/report.json').write_bytes(canonical(dict(inputs=[],allocations=[{'fixture':'accepted'}])))
        source,target=Mock(namespace='source'),Mock(namespace='target')
        with self.assertRaisesRegex(ContractError,'CONFLICT'):qualify(source,target,None,None,None,None,None,root,None,None,1000,True)
        self.assertEqual(source.method_calls,[]);self.assertEqual(target.method_calls,[])
        self.assertEqual(json.loads((root/'report.json').read_bytes()),report)

    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.paths=[]
        for name,value in (('old',OLD),('new',NEW)):
            root=self.root/name;root.mkdir();source={REPAIRED:value,'fusion/numerical.py':'a'*64}
            images=[]
            for kind in ('base','caller','embedding','chain'):
                path=kind+'.json';(root/path).write_bytes(canonical(dict(source=source)))
                images.append(dict(kind=kind,source_package=path))
            path=root/'images.json';path.write_bytes(canonical(dict(images=images,source_export_verification='PASS',source_manifest_sha256=digest(canonical(source)))))
            self.paths.append(path)
        self.old=dict(image={'digest':'old'},components={'omega-agent':dict(image={'digest':'old'},config={'fixed':True})},
            preview=dict(sustained=dict(provider_registry=dict(profile='trusted-provider-lifecycle/1',pins={'storage':dict(image='old',source='old')})),pilot={'handover':{'generation':2}}))
        self.new=copy.deepcopy(self.old);self.new['image']['digest']='new';self.new['components']['omega-agent']['image']['digest']='new'
        self.new['preview']['sustained']['provider_registry']['pins']['storage']=dict(image='new',source='new')

    def test_only_exact_declared_repair_and_image_pins_are_accepted(self):
        value,_=repaired_binding(self.old,self.new,*self.paths)
        self.assertEqual(value['source_paths'],2);self.assertEqual(set(value['changed_source']),{REPAIRED})
        for path in (('profile',),('config',),('checkpoint',)):
            changed=copy.deepcopy(self.new)
            if path==('profile',):changed['preview']['sustained']['provider_registry']['profile']='other'
            elif path==('config',):changed['components']['omega-agent']['config']['fixed']=False
            else:changed['preview']['pilot']['handover']['generation']=3
            with self.assertRaisesRegex(ContractError,'CONFLICT'):repaired_binding(self.old,changed,*self.paths)

    def test_extra_source_change_and_unverified_export_are_rejected(self):
        path=self.paths[1];manifest=json.loads(path.read_bytes())
        for item in manifest['images']:
            p=path.parent/item['source_package'];v=json.loads(p.read_bytes());v['source']['fusion/numerical.py']='b'*64;p.write_bytes(canonical(v))
        manifest['source_manifest_sha256']=digest(canonical(v['source']));path.write_bytes(canonical(manifest))
        with self.assertRaisesRegex(ContractError,'CONFLICT'):repaired_binding(self.old,self.new,*self.paths)
        manifest['source_export_verification']='NOT_RUN';path.write_bytes(canonical(manifest))
        with self.assertRaisesRegex(ContractError,'CONFLICT'):repaired_binding(self.old,self.new,*self.paths)

    def test_expired_continuation_refuses_before_cluster_or_new_input(self):
        root=self.root/'run';root.mkdir();report=dict(status='FAIL',failure=dict(type='RuntimeError',code=None),
            steps=[dict(step='activation')],original='source',replacement='target',conservative_observer_stop_ms=1000)
        (root/'report.json').write_bytes(canonical(report));source,target=Mock(namespace='source'),Mock(namespace='target')
        with patch('examples.pilot_handover_activated_resume.time.time_ns',return_value=1000000000):
            with self.assertRaisesRegex(ContractError,'DEADLINE_EXCEEDED'):qualify(source,target,None,None,None,None,None,root,None,None,1000)
        self.assertEqual(source.method_calls,[]);self.assertEqual(target.method_calls,[]);self.assertEqual(json.loads((root/'report.json').read_bytes()),report)

if __name__=='__main__':unittest.main()
