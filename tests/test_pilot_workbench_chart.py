"""Helm artifact/security boundaries only; no cluster or native execution."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from fusion.contracts import ContractError
from integration.single_node.pilot_browser_provision import provision

ROOT=Path(__file__).resolve().parents[1]


class Provisioning(unittest.TestCase):
    def test_existing_owner_credentials_are_exact_not_regenerated(self):
        users={'alice':dict(role='developer',scopes=['synthetic-shared'],credential_key='browser-alice-token')}
        agents={'omega-agent':dict(principal='A',scopes=['synthetic-shared'])}
        tokens={'omega-agent':{'browser-alice-token':'existing-authorized-'+40*'x'}}
        prepared=provision('omega-ref-pilot-chart',users,agents,credentials=tokens)
        self.assertEqual(prepared['owner_credentials'],tokens)
        self.assertNotIn(tokens['omega-agent']['browser-alice-token'],json.dumps(prepared['gateway_configuration']))
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):provision('omega-ref-pilot-chart',users,agents,credentials={})


@unittest.skipUnless(shutil.which('helm'),'Helm is required for artifact rendering')
class Chart(unittest.TestCase):
    def overlay(self):
        from integration.single_node.pilot_values import generate
        # Explicit image metadata fixture, never claimed as a built OCI image.
        from tests.test_phase2_operator_values import image_manifest_fixture
        images=image_manifest_fixture()
        value=generate(images,'synthetic-workbench-chart','omega-ref-pilot-chart')
        users=value['preview']['pilot']['browser']['users']
        agents={role:dict(principal=x['principal'],scopes=['synthetic-workbench-chart',x['private_scope']]) for role,x in value['preview']['agents'].items()}
        prepared=provision('omega-ref-pilot-chart',users,agents,cleanup=True)
        value['pilotWorkbench']=dict(enabled=True,configuration=prepared['gateway_configuration'],existingTrustSecret='omega-agent-tls-auth',
            credentials={role:dict(existingSecret=role+'-tls-auth',keys=keys) for role,keys in prepared['required_secret_keys'].items()})
        return value
    def render(self,value):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'values.json';path.write_text(json.dumps(value))
            return subprocess.run(['helm','template','pilot',str(ROOT/'deploy/helm/omega-fusion'),'--namespace','omega-ref-pilot-chart','-f',str(path)],capture_output=True,text=True,timeout=30)
    def test_gateway_is_stateless_scoped_no_kube_credentials_and_probes_are_inert(self):
        import yaml
        values=self.overlay();result=self.render(values);self.assertEqual(result.returncode,0,result.stderr)
        docs=[x for x in yaml.safe_load_all(result.stdout) if x]
        pod=next(x for x in docs if x['kind']=='Deployment' and x['metadata']['name']=='omega-workbench')['spec']
        self.assertEqual(pod['strategy']['type'],'Recreate');self.assertEqual(pod['replicas'],1)
        spec=pod['template']['spec'];self.assertFalse(spec['automountServiceAccountToken'])
        self.assertFalse(any('hostPath' in x or 'persistentVolumeClaim' in x for x in spec['volumes']))
        container=spec['containers'][0];self.assertIn('--listen',container['args'])
        caller=values['components']['omega-agent']['image']
        self.assertEqual(container['image'],caller['repository']+'@'+caller['digest'])
        for key in ('startupProbe','readinessProbe','livenessProbe'):self.assertEqual(container[key]['tcpSocket'],dict(port='browser'))
        keys=[x['key'] for v in spec['volumes'] if 'secret' in v for x in v['secret']['items']]
        self.assertTrue(all(k=='ca.crt' or k.startswith('browser-') for k in keys));self.assertNotIn('tls.key',keys)
        network=next(x for x in docs if x['kind']=='NetworkPolicy' and x['metadata']['name']=='omega-workbench-ports')
        self.assertEqual(network['spec']['ingress'],[])
        ingress=next(x for x in docs if x['kind']=='NetworkPolicy' and x['metadata']['name']=='omega-agent-ports')
        self.assertIn('omega-workbench',json.dumps(ingress))
    def test_unknown_secret_keys_and_wrong_namespace_refuse(self):
        value=self.overlay();value['pilotWorkbench']['credentials']['omega-agent']['keys']=['operator-token']
        self.assertNotEqual(self.render(value).returncode,0)
        value=self.overlay();value['pilotWorkbench']['configuration']['namespace']='omega-ref-wrong'
        self.assertNotEqual(self.render(value).returncode,0)

    def test_handover_projects_only_separately_selected_readonly_authority(self):
        import yaml
        value=self.overlay();browser=value['pilotWorkbench'];browser['configuration']['handover']=dict(profile='planned-synthetic-writer-handover/1',authority_file='/writer-authority/current.json',deployments=['omega-ref-pilot-chart','omega-ref-pilot-target'])
        self.assertNotEqual(self.render(value).returncode,0)
        browser['existingAuthoritySecret']='pilot-current-writer';result=self.render(value);self.assertEqual(result.returncode,0,result.stderr)
        deployment=next(x for x in yaml.safe_load_all(result.stdout) if x and x['kind']=='Deployment')['spec']['template']['spec']
        mounted=next(x for x in deployment['containers'][0]['volumeMounts'] if x['name']=='writer-authority')
        self.assertTrue(mounted['readOnly']);self.assertEqual(mounted['mountPath'],'/writer-authority')
        volume=next(x for x in deployment['volumes'] if x['name']=='writer-authority')
        self.assertEqual(volume['secret']['items'],[dict(key='current.json',path='current.json')])
