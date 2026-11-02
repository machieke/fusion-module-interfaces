"""Light artifact-only installation tests; no cluster, runtime or owner execution."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import venv

ROOT = Path(__file__).resolve().parents[1]


class OperatorPackage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix='fusion-operator-package-')
        cls.root = Path(cls.temporary.name)
        subprocess.run([sys.executable, str(ROOT/'sdk/build.py'), '--output', str(cls.root/'wheels')],
                       check=True, capture_output=True)
        venv.create(cls.root/'venv', with_pip=True)
        cls.python = cls.root/'venv/bin/python'
        cls.environment = {k:v for k,v in os.environ.items() if k not in ('PYTHONPATH','PYTHONHOME','KUBECONFIG')}
        cls.environment['PYTHONNOUSERSITE'] = '1'
        subprocess.run([str(cls.python), '-I', '-m', 'pip', 'install', '--no-index', '--no-deps',
                        str(next((cls.root/'wheels').glob('fusion_module_client-*.whl'))),
                        str(next((cls.root/'wheels').glob('fusion_preview_operator-*.whl')))],
                       cwd=cls.root, env=cls.environment, capture_output=True, check=True)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def run_installed(self, *args):
        return subprocess.run([str(self.python), '-I', *args], cwd=self.root,
                              env=self.environment, capture_output=True, text=True, check=True)

    def test_installed_entrypoints_and_sources_without_checkout_or_provider(self):
        result = self.run_installed('-c', '''import hashlib,importlib.util,json,sys
from importlib.metadata import distribution
from pathlib import Path
from integration.single_node.reference_ops import Operator
from integration.single_node.preview_workbench import Workbench
from integration.single_node.reference_artifacts import verify
for name in ('fusion.policy','fusion.preview_sessions','fusion.preview_session_service',
 'integration.single_node.preview_operator','integration.single_node.reference_campaign',
 'phase2_provider','torch','chromadb','transformers','yaml'):
 assert importlib.util.find_spec(name) is None,name
d=distribution('fusion-preview-operator')
manifest=json.loads(d.read_text('source-manifest.json'))
for target,row in manifest['sources'].items():
 assert hashlib.sha256(Path(d.locate_file(target)).read_bytes()).hexdigest()==row['sha256']
assert {e.name for e in d.entry_points}=={'fusion-preview-workbench','fusion-verify-artifacts','fusion-create-secrets','fusion-import-images','fusion-preview-values'}
assert 'artifact-verification' in d.metadata.get_all('Provides-Extra')
assert 'PyYAML==6.0.3; extra == "artifact-verification"' in d.requires
print(json.dumps(dict(operator='IMPORTED',sources='EXACT',runtime_imports='ABSENT')))
''')
        self.assertEqual(json.loads(result.stdout),
                         dict(operator='IMPORTED', sources='EXACT', runtime_imports='ABSENT'))
        # The values generator's exact main imports optional PyYAML even for
        # help. Exercise it in the separate preview-install-extra test.
        for command in ('fusion-preview-workbench','fusion-verify-artifacts','fusion-create-secrets','fusion-import-images'):
            result = subprocess.run([str(self.root/'venv/bin'/command), '--help'], cwd=self.root,
                                    env=self.environment, check=True, capture_output=True, text=True)
            self.assertIn('usage:', result.stdout)

    def test_missing_chain_extra_refuses_before_private_material(self):
        destination=self.root/'not-created-private-state'
        for option in ('--chain','--cha'):
            result=subprocess.run([str(self.root/'venv/bin/fusion-create-secrets'),option,
                '--directory',str(destination)],cwd=self.root,env=self.environment,capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('NOT_AVAILABLE',result.stderr)
            self.assertFalse(destination.exists())

    def test_operator_keeps_explicit_selection_and_remote_pod_boundary(self):
        result = self.run_installed('-c', '''import json,subprocess
from unittest.mock import patch
from fusion.contracts import ContractError
from integration.single_node.reference_ops import Operator,PYTHON
from integration.single_node.preview_workbench import Workbench
owner=Operator('/operator-owned/kubeconfig','explicit-context','omega-ref-sdk-qualified')
with patch('integration.single_node.reference_ops.subprocess.run') as run:
 run.return_value=subprocess.CompletedProcess([],0,'{"items":[]}', '')
 assert owner.k('get','pods','-o','json')=='{"items":[]}'
 args=run.call_args.args[0]
 assert args==['kubectl','--kubeconfig','/operator-owned/kubeconfig','--context','explicit-context',
  '-n','omega-ref-sdk-qualified','get','pods','-o','json']
bench=Workbench(owner);bench.agents={'omega-agent':{'sessions':{'synthetic-session':{}}}}
with patch.object(owner,'k',return_value='{"state":"active"}') as call:
 result=bench.observe(dict(role='omega-agent',session='synthetic-session',after=0))
 assert result=={'state':'active'}
 assert call.call_args.args[:6]==('exec','omega-agent-0','--',PYTHON,'-m','integration.single_node.preview_operator')
for namespace in ('omega-demo','not-task-owned'):
 try:Operator('/operator-owned/kubeconfig','explicit-context',namespace)
 except ContractError as exc:assert exc.code=='UNAUTHORIZED'
 else:raise AssertionError('namespace boundary relaxed')
print(json.dumps(dict(command_transport='MOCKED',explicit_selection='PASS',native_or_cluster_calls=0)))
''')
        self.assertEqual(json.loads(result.stdout),
                         dict(command_transport='MOCKED',explicit_selection='PASS',native_or_cluster_calls=0))

    def test_inventory_uses_actual_wheels_and_retains_unknown_licenses(self):
        path = self.root/'inventory.json'
        wheels = sorted((self.root/'wheels').glob('*.whl'))
        subprocess.run([sys.executable, str(ROOT/'sdk/inventory.py'), *map(str,wheels), '--output',str(path)],
                       check=True, capture_output=True)
        value = json.loads(path.read_text())
        self.assertEqual(len(value['packages']),3)
        self.assertEqual(value['vulnerability_scan'],'NOT_RUN')
        self.assertEqual(value['hosted_ci'],'NOT_OBSERVED')
        for package in value['packages']:
            raw=(self.root/'wheels'/package['artifact']).read_bytes()
            self.assertEqual(package['sha256'],hashlib.sha256(raw).hexdigest())
            self.assertEqual(package['license_expression'],'NOASSERTION')
            self.assertTrue(package['files'])
