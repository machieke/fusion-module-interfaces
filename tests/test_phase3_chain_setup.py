"""Offline public-key recipe and real Helm rendering; no chain/node execution."""
import importlib.util,json,tempfile,unittest,subprocess
from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[1]
class ChainSetup(unittest.TestCase):
 def test_only_sustained_fresh_install_binds_public_key_before_first_mount(self):
  spec=importlib.util.spec_from_file_location('secrets_recipe',ROOT/'deploy/single-node/create_secrets.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'values.json';q=Path(td)/'public.json';public=dict(public_key='04'+'1'*128,wallet_address='EXPLICIT_PUBLIC_ADDRESS_FIXTURE');q.write_text(json.dumps(public))
   for profile in ('omega-single-node-preview/1','omega-single-node-sustained-preview/1'):
    original=dict(preview=dict(profile=profile,chain=dict(enabled=True,nodeEnabled=False,public_key='04'+'0'*128,wallet_address='')));p.write_text(json.dumps(original));before=p.read_bytes();m.bind_sustained_chain_public(p,q)
    if profile.endswith('sustained-preview/1'):
     actual=yaml.safe_load(p.read_bytes());self.assertEqual({k:actual['preview']['chain'][k] for k in public},public);self.assertFalse(actual['preview']['chain']['nodeEnabled']);self.assertNotIn('private',p.read_text())
    else:self.assertEqual(p.read_bytes(),before)
 def test_fresh_chain_claim_is_explicit_and_old_claim_template_retained(self):
  from integration.single_node.sustained_values import generate
  from tests.test_phase2_operator_values import image_manifest_fixture
  manifest=image_manifest_fixture();manifest['images'].append(dict(kind='chain',repository='fixture.invalid/chain',local_tag='fixture.invalid/chain:fixed',manifest_digest='sha256:'+'a'*64,configuration_digest='sha256:'+'b'*64))
  value=generate(manifest,'synthetic-chain-claim',mode='combined',chain=True)
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'values.json'
   def render():
    p.write_text(json.dumps(value));return subprocess.run(['helm','template','omega',str(ROOT/'deploy/helm/omega-fusion'),'-f',str(p)],capture_output=True,text=True)
   value['components']['f1r3node']['persistence']=dict(storageClass='local-path',size='2Gi',existingClaim='phase3-f1r3node-qualified')
   r=render();self.assertEqual(r.returncode,0,r.stderr);node=next(x for x in yaml.safe_load_all(r.stdout) if x and x['kind']=='StatefulSet' and x['metadata']['name']=='f1r3node')
   spec=node['spec']['template']['spec'];self.assertEqual(next(x for x in spec['containers'][0]['volumeMounts'] if x['mountPath']=='/state')['name'],'selected-state');self.assertEqual(node['spec']['volumeClaimTemplates'][0]['metadata']['name'],'state');self.assertEqual(next(x for x in spec['volumes'] if x['name']=='selected-state')['persistentVolumeClaim']['claimName'],'phase3-f1r3node-qualified')
   value['components']['omega-agent']['persistence']=value['components']['f1r3node']['persistence'];self.assertNotEqual(render().returncode,0)
