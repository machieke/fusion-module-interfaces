import copy,json,os,subprocess,tempfile,unittest
from pathlib import Path
from integration.single_node.pilot_values import generate
from integration.single_node.owner_seal import selected
from integration.single_node.pilot_initial_authority import initial
from integration.single_node.preview_secrets import material
from fusion.contracts import ContractError


class Configuration(unittest.TestCase):
    def setUp(self):
        self.images=dict(source_export_verification='PASS',source_manifest_sha256='a'*64,images=[
            dict(kind=k,repository='synthetic/'+k,local_tag='synthetic/'+k+':test',manifest_digest='sha256:'+'b'*64) for k in ('base','caller','embedding')])
        self.value=generate(self.images,'synthetic-pilot-config','omega-ref-pilot-config')
    def test_fresh_registry_seal_and_external_authority_keep_exact_profiles(self):
        p=self.value['preview'];settings=dict(role='omega-agent',service_composition=p['profile'],preview=p)
        self.assertEqual(selected(settings)['provider_registry'],'trusted-provider-lifecycle/2')
        authority=initial('omega-ref-pilot-config',p)
        self.assertEqual(authority['generation'],1);self.assertEqual(authority['allowed_methods'],['writer.start','writer.request'])
        old=copy.deepcopy(settings);old['preview']['sustained']['provider_registry']['profile']='trusted-provider-lifecycle/1'
        self.assertNotEqual(selected(settings),selected(old))
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):initial('omega-demo',p)
    def test_private_browser_tokens_are_only_in_the_selected_owner(self):
        roles=tuple(self.value['components']);m=material(self.value['preview'],roles,{r:r*8 for r in roles})
        self.assertIn('browser-alice-token',m['omega-agent']);self.assertNotIn('browser-alice-token',m['omega-agent-b'])
        self.assertIn('browser-bob-token',m['omega-agent-b']);self.assertNotIn('browser-bob-token',m['omega-agent'])
        self.assertIn('browser-operator-search-token',m['fusion-search'])
        self.assertNotIn('browser-operator-search-token',m['omega-agent'])
    def test_rendered_chart_mounts_only_external_authority_and_owned_state(self):
        import yaml
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'values.yaml';path.write_text(yaml.safe_dump(self.value))
            raw=subprocess.check_output([os.environ.get('FUSION_TEST_HELM','helm'),'template','omega','deploy/helm/omega-fusion','-f',str(path),'--namespace','omega-ref-pilot-config'],text=True)
        docs=list(yaml.safe_load_all(raw));owners=[x for x in docs if x and x['kind']=='StatefulSet']
        self.assertGreater(len(owners),8)
        for x in owners:
            spec=x['spec']['template']['spec'];self.assertFalse(spec['automountServiceAccountToken'])
            mount=next(v for v in spec['volumes'] if v['name']=='writer-authority')
            self.assertEqual(mount['secret']['secretName'],'pilot-current-writer')
            self.assertFalse(any('hostPath' in v for v in spec['volumes']))
            self.assertEqual(x['spec']['replicas'],1)

    def test_attention_reservation_fault_renders_without_changing_opt_in(self):
        import yaml
        helm=os.environ.get('FUSION_TEST_HELM','helm')
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'values.yaml'
            values=copy.deepcopy(self.value)
            values['components']['fusion-attention'].setdefault('config',{})['test']={'pause_at':'after_priority_reservation'}
            values['testFaultsEnabled']=False
            command=[helm,'template','omega','deploy/helm/omega-fusion','-f',str(path),'--namespace','omega-ref-pilot-config']
            path.write_text(yaml.safe_dump(values))
            disabled=subprocess.run(command,capture_output=True,text=True,timeout=20,check=True)
            docs=list(yaml.safe_load_all(disabled.stdout))
            selected=next(x for x in docs if x and x['kind']=='ConfigMap' and x['metadata']['name']=='fusion-attention')
            settings=json.loads(selected['data']['component.json'])
            self.assertIs(settings['enable_test_faults'],False)
            values['testFaultsEnabled']=True;path.write_text(yaml.safe_dump(values))
            rendered=subprocess.run(command,capture_output=True,text=True,timeout=20,check=True)
            docs=list(yaml.safe_load_all(rendered.stdout))
            selected=next(x for x in docs if x and x['kind']=='ConfigMap' and x['metadata']['name']=='fusion-attention')
            settings=json.loads(selected['data']['component.json'])
            self.assertEqual(settings['test'],{'pause_at':'after_priority_reservation'})
            self.assertIs(settings['enable_test_faults'],True)
            values['components']['fusion-attention']['config']['test']['pause_at']='not_an_existing_hook'
            path.write_text(yaml.safe_dump(values))
            invalid=subprocess.run(command,capture_output=True,text=True,timeout=20)
            self.assertNotEqual(invalid.returncode,0)
