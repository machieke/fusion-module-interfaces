"""Real configuration/SQLite/materialization, fixture TLS/health/native outputs."""
import copy,json,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
from fusion.contracts import canonical,digest,ContractError
from fusion.registry import descriptor_wire,selection_token
from fusion.reference_inspect_contracts import descriptor
from fusion.sustained_sessions import SustainedSessionStore
from fusion.provider_lifecycle import Registry
from integration.single_node.pilot_go_values import initial,replace
from integration.single_node.preview_secrets import material
from integration.single_node.sustained_configure import configure
from integration.single_node.sustained_runtime import materialize,template_files

class InspectionTemplate(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        images=dict(source_manifest_sha256='a'*64,source_export_verification='PASS',images=[dict(kind=k,repository='fixture/'+k,
            local_tag='fixture/'+k+':fixture',manifest_digest='sha256:'+str(i)*64) for i,k in enumerate(('base','caller','embedding'),1)])
        checked=dict(repository='fixture/inspect-go',manifest='sha256:'+'d'*64,configuration='sha256:'+'e'*64,
            source_manifest_sha256='f'*64,contract=selection_token(descriptor()),source_package='fixture/kit',manifest_sha256='e'*64)
        with patch('integration.single_node.pilot_go_values.verify',return_value=checked):
            self.values,_=initial(images,'fixture-only','synthetic-go-template-fixture','omega-ref-pilot-go-template-fixture')
        roles=tuple(self.values['components']);self.roles=roles
        # Generated test secrets are used only by real configuration functions;
        # TLS bytes and probe responses are explicitly fixtures.
        clients={r:('client-'+r)*5 for r in roles}
        for role,entries in material(self.values['preview'],roles,clients).items():
            directory=self.root/role/'secrets';directory.mkdir(parents=True)
            base={k:b'fixture-not-a-TLS-certificate' for k in ('ca.crt','tls.crt','tls.key')}
            base.update({'caller-token':clients[role].encode(),'worker-token':('worker-'+role).encode()*5})
            if role=='omega-agent':base.update({r+'-token':v.encode() for r,v in clients.items() if r!=role})
            if role=='fusion-execution':base.update({r+'-token':('worker-'+r).encode()*5 for r in ('fusion-storage','fusion-messaging')})
            for name,raw in {**base,**entries}.items():(directory/name).write_bytes(raw)
    def settings(self,value=None):
        return dict(role='omega-agent',service_composition=self.values['preview']['profile'],state=str(self.root/'state'),run=str(self.root/'run'),
            secret_directory=str(self.root/'omega-agent'/'secrets'),https_port=8443,capacity=8,revision='fixture',native_enabled=False,
            worker_enabled=False,enable_test_faults=False,test={},preview=copy.deepcopy((value or self.values)['preview']),
            peers={r:r+'.omega-ref-pilot-go-template-fixture.svc.cluster.local' for r in self.roles})
    def test_extra_template_keeps_existing_allocation_and_runtime_exact(self):
        _,before,state,run=configure(self.settings());selected=before['native_sessions']
        original=copy.deepcopy(selected);files={k:template_files(v['directory']) for k,v in selected['runtime_templates'].items()}
        store=SustainedSessionStore(selected['database'],lambda *_:None,selected['allocation']);self.addCleanup(store.close)
        registry=Registry(store,selected['provider_registry'],lambda *_:None)
        for key in selected['provider_registry']['templates']['shared']:
            registry.act('add-'+key,'add',key);registry.probe('probe-'+key,key,lambda _:True);registry.act('enable-'+key,'enable',key)
        old=store.allocate('A','old-native','shared',admission=registry.admit);sid=old['session'];old_selection=registry.selected(sid)
        accepted=store.submit('A',sid,'original-input','task-context','synthetic-task');store.next_input('A',sid)
        store.complete('A',sid,'original-input',dict(turn=1,projection='explicit native fixture',occurrences=['fixture-occurrence']))
        observed=store.observe('A',sid,True);app=materialize(run/'owner.json',state,run,sid);old_app=app.read_bytes()
        _,after,_,_=configure(self.settings(replace(self.values)));new=after['native_sessions']
        for name in ('shared','private'):
            self.assertEqual(new['allocation']['templates'][name],original['allocation']['templates'][name])
            self.assertEqual(new['runtime_templates'][name],original['runtime_templates'][name])
            self.assertEqual(template_files(new['runtime_templates'][name]['directory']),files[name])
        self.assertEqual(len(new['allocation']['templates']),3);self.assertLessEqual(len(new['provider_registry']['records']),32)
        for key,value in original['provider_registry']['records'].items():self.assertEqual(new['provider_registry']['records'][key],value)
        self.assertEqual(materialize(run/'owner.json',state,run,sid).read_bytes(),old_app)
        newstore=SustainedSessionStore(new['database'],lambda *_:None,new['allocation']);self.addCleanup(newstore.close)
        reg=Registry(newstore,new['provider_registry'],lambda *_:None)
        self.assertEqual(newstore.observe('A',sid,True),observed);self.assertEqual(reg.selected(sid),old_selection)
        for key in new['provider_registry']['templates']['go-shared']:
            reg.act('new-add-'+key,'add',key);reg.probe('new-probe-'+key,key,lambda _:True);reg.act('new-enable-'+key,'enable',key)
        second=newstore.allocate('A','new-native','go-shared',admission=reg.admit)
        self.assertNotEqual(second['allocation']['frozen']['runtime_digest'],old['allocation']['frozen']['runtime_digest'])
        newapp=materialize(run/'owner.json',state,run,second['session']);cfg=json.loads(newapp.read_bytes())
        inspector=json.loads(Path(cfg['inspect_config']).read_bytes())
        self.assertEqual(canonical(inspector['execution_descriptor']),canonical(descriptor_wire(descriptor())))
        self.assertIn('fusion-inspect-go',inspector['ports']['execution']['endpoint']['host'])
        self.assertEqual(cfg['preview']['tools'],json.loads(old_app)['preview']['tools'])
        self.assertEqual(inspector['ports']['execution']['credential'],files['shared']['inspection.json']['ports']['execution']['credential'])
        self.assertEqual({x.provider for x in __import__('fusion.preview_inspect',fromlist=['selections']).selections(inspector).values()}, {'go-immutable-inspect-reference','local-mailbox','atom-detta'})
        self.assertIn('go-shared-fusion-inspect-go',reg.selected(second['session']))
        reg.act('drain-original','drain','shared-fusion-execution');reg.act('retire-original','retire','shared-fusion-execution')
        with self.assertRaisesRegex(ContractError,'NOT_AVAILABLE'):newstore.submit('A',sid,'new-old-work','task-context','synthetic-task')
        self.assertEqual(newstore.observe('A',sid,True),observed);self.assertEqual(reg.selected(sid),old_selection)
        self.assertEqual(newstore.submit('A',second['session'],'new-work','task-context','synthetic-task')['state'],'accepted')
    def test_extra_template_never_accepts_arbitrary_service_profile_or_private_name(self):
        for field,value in [('name','private'),('service','untrusted-endpoint'),('profile','arbitrary-execution/1')]:
            settings=self.settings(replace(self.values));settings['preview']['inspection']['additional_template'][field]=value
            with self.subTest(field=field),self.assertRaises(ContractError):configure(settings)
    def test_missing_trusted_peer_or_weaker_descriptor_fails_before_new_allocation(self):
        settings=self.settings(replace(self.values));settings['peers'].pop('fusion-inspect-go')
        with self.assertRaisesRegex(ContractError,'NOT_AVAILABLE'):configure(settings)
        settings=self.settings(replace(self.values));settings['preview']['inspection']['additional_template']['descriptor']['max_payload_bytes']=4095
        with self.assertRaisesRegex(ContractError,'UNSUPPORTED_PROFILE'):configure(settings)

if __name__=='__main__':unittest.main()
