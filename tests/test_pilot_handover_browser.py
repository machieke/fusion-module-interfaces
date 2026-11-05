"""Offline packaging/provisioning fixtures; no cluster or handover is claimed."""
import copy,json,shutil,tempfile,unittest
from pathlib import Path
import yaml
from fusion.contracts import ContractError
from examples.pilot_handover_browser import prepare
from examples.pilot_handover_values import generate
from tests.test_phase2_operator_values import image_manifest_fixture

ROOT=Path(__file__).resolve().parents[1]
SOURCE='omega-ref-pilot-recipe-source'
TARGET='omega-ref-pilot-recipe-target'


def fixture(root):
    value=generate(image_manifest_fixture(),'synthetic-handover-browser',SOURCE)
    pilot=value['preview']['pilot'];pilot['writer_fence'].update(deployment=TARGET,generation=2)
    pilot['handover']=dict(profile=pilot['writer_fence']['profile'],generation=2,checkpoint_sha256='a'*64)
    values=root/'values.yaml';values.write_text(yaml.safe_dump(value));secrets=root/'secrets';secrets.mkdir()
    for role in ('omega-agent','omega-agent-b','fusion-search'):
        (secrets/(role+'.secret.json')).write_text(json.dumps(dict(apiVersion='v1',kind='Secret',
            metadata=dict(namespace=TARGET,name=role+'-tls-auth'),data={'ca.crt':'YXV0aG9yZWQtZml4dHVyZS1ub3QtYS1jZXJ0','existing-token':'ZXhhY3QtZml4dHVyZS10b2tlbg=='})))
    return values,secrets,value


class Recipe(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.values,self.secrets,self.original=fixture(self.root);self.output=self.root/'browser'
    def test_preserves_input_values_all_old_keys_and_private_output(self):
        original_bytes=self.values.read_bytes();secret_bytes={p.name:p.read_bytes() for p in self.secrets.iterdir()}
        report=prepare(self.values,self.secrets,SOURCE,TARGET,self.output)
        actual=yaml.safe_load((self.output/'gateway-values.yaml').read_bytes());gateway=actual.pop('pilotWorkbench')
        selected=actual['preview']['pilot'].pop('browser');self.assertEqual(actual,self.original)
        self.assertEqual(selected['users']['handover-operator']['scopes'],['synthetic-handover-browser'])
        self.assertEqual(gateway['configuration']['handover']['deployments'],[SOURCE,TARGET])
        self.assertEqual(gateway['existingAuthoritySecret'],'pilot-current-writer');self.assertEqual(report['cluster_calls'],0)
        self.assertEqual(self.values.read_bytes(),original_bytes)
        for name,raw in secret_bytes.items():
            self.assertEqual((self.secrets/name).read_bytes(),raw)
            old=json.loads(raw)['data'];new=json.loads((self.output/name).read_bytes())['data']
            self.assertEqual({k:new[k] for k in old},old)
            self.assertTrue(all(k.startswith('browser-') for k in new.keys()-old.keys()))
        self.assertEqual(self.output.stat().st_mode&0o777,0o700)
        for path in self.output.iterdir():self.assertEqual(path.stat().st_mode&0o777,0o600)
        with self.assertRaises(ContractError):prepare(self.values,self.secrets,SOURCE,TARGET,self.output)
    def test_wrong_epoch_or_namespace_refuses_without_output(self):
        value=copy.deepcopy(self.original);value['preview']['pilot']['writer_fence']['generation']=1
        self.values.write_text(yaml.safe_dump(value))
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):prepare(self.values,self.secrets,SOURCE,TARGET,self.output)
        self.assertFalse(self.output.exists());self.values.write_text(yaml.safe_dump(self.original))
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):prepare(self.values,self.secrets,SOURCE,'omega-ref-pilot-other',self.output)
        self.assertFalse(self.output.exists())
    def test_foreign_secret_and_existing_browser_key_refuse_without_partial_output(self):
        path=self.secrets/'fusion-search.secret.json';old=path.read_bytes();value=json.loads(old)
        value['metadata']['namespace']=SOURCE;path.write_text(json.dumps(value))
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):prepare(self.values,self.secrets,SOURCE,TARGET,self.output)
        self.assertFalse(self.output.exists());path.write_bytes(old)
        path=self.secrets/'omega-agent.secret.json';value=json.loads(path.read_bytes());value['data']['browser-handover-operator-token']='already-selected'
        path.write_text(json.dumps(value))
        with self.assertRaisesRegex(ContractError,'CONFLICT'):prepare(self.values,self.secrets,SOURCE,TARGET,self.output)
        self.assertFalse(self.output.exists())
    @unittest.skipUnless(shutil.which('helm'),'Helm required for exact rollout render')
    def test_chart_rollout_is_explicit_and_has_no_foreign_owner_mount(self):
        from integration.single_node.placement import render
        from integration.single_node.owner_seal import selected
        prepare(self.values,self.secrets,SOURCE,TARGET,self.output)
        changed=yaml.safe_load((self.output/'gateway-values.yaml').read_bytes())
        chart=ROOT/'deploy/helm/omega-fusion'
        before={(x['kind'],x['metadata']['name']):x for x in render(chart,TARGET,self.original)}
        after={(x['kind'],x['metadata']['name']):x for x in render(chart,TARGET,changed)}
        owners=[k for k in before if k[0]=='StatefulSet'];self.assertEqual(len(owners),12)
        for key in owners:self.assertNotEqual(before[key]['spec']['template']['metadata']['annotations'],after[key]['spec']['template']['metadata']['annotations'])
        for key in before:
            if key[0]=='ConfigMap' and 'component.json' in before[key].get('data',{}):
                old=json.loads(before[key]['data']['component.json']);new=json.loads(after[key]['data']['component.json'])
                self.assertEqual(selected(old),selected(new));new['preview']['pilot'].pop('browser');self.assertEqual(old,new)
        pod=after['Deployment','omega-workbench']['spec']['template']['spec'];self.assertFalse(pod['automountServiceAccountToken'])
        self.assertFalse(any('hostPath' in x or 'persistentVolumeClaim' in x for x in pod['volumes']))
        authority=next(x for x in pod['volumes'] if x['name']=='writer-authority')
        self.assertEqual(authority['secret']['items'],[dict(key='current.json',path='current.json')])


class InstalledRecipe(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from tests.test_pilot_operator_package import Installed
        Installed.setUpClass.__func__(cls)
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    def test_distributed_script_runs_with_installed_python_isolation(self):
        from tests.test_pilot_operator_package import Installed
        script=self.root/'distributed-handover-browser.py';shutil.copyfile(ROOT/'examples/pilot_handover_browser.py',script)
        values,secrets,_=fixture(self.root);output=self.root/'browser'
        result=Installed.invoke(self,str(script),'--values',str(values),'--secrets',str(secrets),
            '--source-namespace',SOURCE,'--replacement',TARGET,'--output',str(output))
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads((output/'provision-report.json').read_bytes())['cluster_calls'],0)
        self.assertNotIn('fixture-token',result.stdout)


if __name__=='__main__':unittest.main()
