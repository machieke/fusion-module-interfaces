"""Extracted operator recipes; real generated TLS, explicit external stubs.

Set FUSION_SDK_OPERATOR_WHEELHOUSE to the exact optional wheels recorded in
operator-wheel-inputs.json. Without that prerequisite these methods are UNRUN,
not fixture substitutions. No Docker daemon, cluster or runtime is contacted.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import venv

ROOT = Path(__file__).resolve().parents[1]
WHEELHOUSE = os.environ.get('FUSION_SDK_OPERATOR_WHEELHOUSE')


@unittest.skipUnless(WHEELHOUSE, 'UNRUN: explicitly selected pinned operator wheelhouse unavailable')
class ExtractedInstallRecipes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pins = json.loads((ROOT/'sdk/operator-wheel-inputs.json').read_text())['files']
        sources = []
        for pin in pins:
            source = Path(WHEELHOUSE).resolve()/pin['file']
            assert source.name == pin['file'] and source.stat().st_size == pin['bytes']
            assert hashlib.sha256(source.read_bytes()).hexdigest() == pin['sha256']
            sources.append(source)
        cls.temporary = tempfile.TemporaryDirectory(prefix='fusion-extracted-install-')
        cls.root = Path(cls.temporary.name)
        subprocess.run([sys.executable,str(ROOT/'sdk/build.py'),'--output',str(cls.root/'artifacts')],
                       check=True,capture_output=True)
        venv.create(cls.root/'venv',with_pip=True)
        cls.python = cls.root/'venv/bin/python'
        cls.environment = {k:v for k,v in os.environ.items() if k not in ('PYTHONPATH','PYTHONHOME','KUBECONFIG')}
        cls.environment['PYTHONNOUSERSITE']='1'
        for source in sources:(cls.root/'artifacts'/source.name).write_bytes(source.read_bytes())
        subprocess.run([str(cls.python),'-I','-m','pip','install','--no-index','--find-links',str(cls.root/'artifacts'),
                        'fusion-module-client==0.2.0','fusion-preview-operator[preview-install,chain-key-setup]==0.2.0'],
                       cwd=cls.root,env=cls.environment,check=True,capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def setUp(self):
        self.path=self.root/self._testMethodName
        self.path.mkdir()
        (self.path/'bin').mkdir()
        self.env=dict(self.environment,PATH=str(self.path/'bin')+os.pathsep+self.environment['PATH'])
        self.env['SDK_RECIPE_TEST_LOG']=str(self.path/'calls.jsonl')

    def stub(self,name,code):
        path=self.path/'bin'/name
        path.write_text('#!'+str(self.python)+'\n'+code)
        path.chmod(0o700)

    def command(self,name,*args):
        return subprocess.run([str(self.root/'venv/bin'/name),*map(str,args)],cwd=self.path,
                              env=self.env,capture_output=True,text=True)

    def calls(self):
        path=Path(self.env['SDK_RECIPE_TEST_LOG'])
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def values(self,chain=False):
        roles=['fusion-model','fusion-episodes','fusion-relations','fusion-search','fusion-embedding',
               'fusion-beliefs','fusion-attention','omega-agent-b']
        if chain:roles+=['fusion-commitment','f1r3node']
        value=dict(preview=dict(enabled=True,model_boundary='RECORDED_FIXTURE',
            agents={'omega-agent':{'principal':'A'},'omega-agent-b':{'principal':'B'}},
            memory={'enabled':True},cognition={'enabled':True},tasks={'enabled':True},
            inspection={'enabled':True},chain={'enabled':chain}),
            components={role:{'enabled':True} for role in roles})
        path=self.path/'selected-values.json';path.write_text(json.dumps(value));return path

    def test_extracted_recipe_generates_real_tls_with_explicit_kubectl_stub(self):
        self.stub('kubectl',r'''import json,os,sys
value=json.load(sys.stdin)
assert value['kind']=='Secret' and value['metadata']['namespace']=='omega-ref-sdk-install'
with open(os.environ['SDK_RECIPE_TEST_LOG'],'a') as log:
 log.write(json.dumps(dict(args=sys.argv[1:],kind=value['kind'],name=value['metadata']['name'],keys=sorted(value['data'])))+'\n')
''')
        private=self.path/'operator-private'
        args=['--preview-values',self.values(),'--kubeconfig',self.path/'operator-selected-kubeconfig',
              '--context','explicit-test-context','--namespace','omega-ref-sdk-install','--directory',private]
        result=self.command('fusion-create-secrets',*args)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(len(self.calls()),12)
        self.assertEqual(private.stat().st_mode & 0o777,0o700)
        self.assertEqual((private/'ca.key').stat().st_mode & 0o777,0o600)
        for call in self.calls():
            self.assertEqual(call['args'],['--kubeconfig',str(self.path/'operator-selected-kubeconfig'),
                '--context','explicit-test-context','create','-f','-'])
        leaf=private/'omega-agent.crt'
        verified=subprocess.run(['openssl','verify','-CAfile',str(private/'ca.crt'),
            '-verify_hostname','omega-agent.omega-ref-sdk-install.svc.cluster.local',str(leaf)],
            check=True,capture_output=True,text=True)
        self.assertIn(': OK',verified.stdout)
        # Existing recipe refuses to remint identity into a populated directory.
        replay=self.command('fusion-create-secrets',*args)
        self.assertNotEqual(replay.returncode,0)
        self.assertEqual(len(self.calls()),12)

    def test_chain_offline_key_setup_has_no_chain_adapter_or_runtime(self):
        self.stub('kubectl',r'''import json,os,sys
value=json.load(sys.stdin)
with open(os.environ['SDK_RECIPE_TEST_LOG'],'a') as log:
 log.write(json.dumps(dict(name=value['metadata']['name'],keys=sorted(value['data'])))+'\n')
''')
        private=self.path/'operator-private'
        result=self.command('fusion-create-secrets','--preview-values',self.values(True),
            '--kubeconfig',self.path/'selected-kubeconfig','--context','explicit-test-context',
            '--namespace','omega-ref-sdk-chain-setup','--directory',private)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(len(self.calls()),14)
        code='''import base64,importlib.util,json,sys
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
from integration.single_node.chain_address import address
p=Path(sys.argv[1]);public=json.loads((p/'chain-public.json').read_text())
commitment=json.loads((p/'fusion-commitment.secret.json').read_text())['data']
node=json.loads((p/'f1r3node.secret.json').read_text())['data']
secret=base64.b64decode(commitment['signer.hex'])
assert secret==base64.b64decode(node['validator.hex'])
key=ec.derive_private_key(int(secret,16),ec.SECP256K1())
encoded=key.public_key().public_bytes(serialization.Encoding.X962,serialization.PublicFormat.UncompressedPoint)
assert public['public_key']==encoded.hex() and public['wallet_address']==address(encoded)
for name in ('scripts.chain_demo','fusion.policy','torch','chromadb'):
 try:found=importlib.util.find_spec(name)
 except ModuleNotFoundError:found=None
 assert found is None,name
assert not any(x.startswith('fusion.adapters') for x in sys.modules)
print('OFFLINE_SYNTHETIC_KEY_SETUP_VALIDATED_NO_CHAIN_PROCESS')
'''
        verified=subprocess.run([str(self.python),'-I','-c',code,str(private)],cwd=self.path,
            env=self.env,check=True,capture_output=True,text=True)
        self.assertIn('NO_CHAIN_PROCESS',verified.stdout)

    def test_fresh_preview_values_from_declared_image_manifest(self):
        help_result=self.command('fusion-preview-values','--help')
        self.assertEqual(help_result.returncode,0,help_result.stderr)
        self.assertIn('usage:',help_result.stdout)
        images=dict(source_export_verification='PASS',source_manifest_sha256='e'*64,
            images=[dict(kind=kind,repository='synthetic.example/'+kind,
                local_tag='synthetic.example/'+kind+':fixture',manifest_digest='sha256:'+digit*64)
                for kind,digit in [('base','a'),('caller','b'),('embedding','c'),('chain','d')]])
        source=self.path/'images.json';source.write_text(json.dumps(images))
        output=self.path/'fresh-values.yaml'
        args=['--images',source,'--scope','synthetic-sdk-artifact-install','--mode','combined','--chain','--output',output]
        result=self.command('fusion-preview-values',*args)
        self.assertEqual(result.returncode,0,result.stderr)
        code='''import importlib.util,sys,yaml
from pathlib import Path
from fusion.preview_deployment_contracts import COMPOSITION
v=yaml.safe_load(Path(sys.argv[1]).read_text());p=v['preview']
assert p['profile']==COMPOSITION and p['model_boundary']=='RECORDED_FIXTURE'
assert p['scope']=='synthetic-sdk-artifact-install' and len(p['agents'])==2
assert p['chain']['nodeEnabled'] is False and p['chain']['isolationVerified'] is False
assert all(c['image']['pullPolicy']=='Never' for c in v['components'].values() if 'image' in c)
assert importlib.util.find_spec('integration.single_node.preview_configure') is None
assert importlib.util.find_spec('fusion.preview_application') is None
print('PURE_VALUES_READY_CHAIN_DISABLED_NO_OWNER_IMPORTS')
'''
        verified=subprocess.run([str(self.python),'-I','-c',code,str(output)],cwd=self.path,
            env=self.env,check=True,capture_output=True,text=True)
        self.assertIn('NO_OWNER_IMPORTS',verified.stdout)
        denied=self.command('fusion-preview-values',*args)
        self.assertNotEqual(denied.returncode,0)
        self.assertIn('CONFLICT',denied.stderr)
        self.assertFalse(self.calls())

    def test_image_import_uses_declared_archive_and_explicit_container_stub(self):
        digest='sha256:'+'a'*64;config='sha256:'+'b'*64
        archive=self.path/'synthetic-image-archive';archive.write_bytes(b'explicit image import fixture bytes')
        manifest=self.path/'images.json';manifest.write_text(json.dumps(dict(
            archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
            images=[dict(local_tag='synthetic.example/provider:fixture',manifest_digest=digest,
                         configuration_digest=config,repository='synthetic.example/provider')])))
        self.stub('docker',r'''import json,os,sys
args=sys.argv[1:]
assert args[:2]==['exec','-i'] or args[:2]==['exec','selected-task-container']
with open(os.environ['SDK_RECIPE_TEST_LOG'],'a') as log:log.write(json.dumps(args)+'\n')
if 'import' in args:assert sys.stdin.buffer.read()==b'explicit image import fixture bytes'
elif args[-2:]==['images','ls']:print('synthetic.example/provider:fixture application/vnd.oci.image.manifest.v1+json sha256:'+'a'*64)
elif 'content' in args:print(json.dumps({'config':{'digest':'sha256:'+'b'*64}}))
elif 'tag' not in args:raise AssertionError(args)
''')
        args=['--container','selected-task-container','--manifest',manifest,'--archive',archive]
        result=self.command('fusion-import-images',*args)
        self.assertEqual(result.returncode,0,result.stderr)
        calls=self.calls();self.assertEqual(len(calls),4)
        self.assertTrue(all('selected-task-container' in command for command in calls))
        self.assertEqual(calls[-1][-1],'synthetic.example/provider@'+digest)
        archive.write_bytes(b'corrupted fixture archive')
        denied=self.command('fusion-import-images',*args)
        self.assertNotEqual(denied.returncode,0)
        self.assertIn('ARCHIVE_HASH_MISMATCH',denied.stderr)
        self.assertEqual(len(self.calls()),4)

    def test_extracted_verifier_accepts_explicit_preview_archive_fixtures(self):
        # Only the test driver imports its fixture constructor. The installed
        # CLI runs outside the checkout with no repository PYTHONPATH.
        from fusion.contracts import canonical
        from sdk.test_preview_distribution import FixtureDistribution
        fixture=FixtureDistribution(self.path/'distribution')
        result=self.command('fusion-verify-artifacts',fixture.save())
        self.assertEqual(result.returncode,0,result.stderr)
        value=json.loads(result.stdout)
        self.assertEqual(value['status'],'OFFLINE_VERIFIED')
        self.assertEqual(value['generative_runtime_availability'],'NOT_CHECKED')
        self.assertEqual(value['additional_live_generations'],0)
        imported=fixture.read('images.json')
        imported['images'][0]['repository']='fixture-only/changed-import-target'
        fixture.write('images.json',canonical(imported))
        denied=self.command('fusion-verify-artifacts',fixture.save())
        self.assertNotEqual(denied.returncode,0)
        self.assertIn('CONFLICT',denied.stderr)
        self.assertFalse(self.calls())
