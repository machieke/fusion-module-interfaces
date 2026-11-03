"""Installed 0.1/0.2/0.3 package matrix; payload providers remain file fixtures."""
import json,subprocess
from pathlib import Path
from sdk.build import build
from tests import test_phase2_sdk_compatibility as prior
from tests import test_phase2_sdk as provider

class InstalledCurrentCompatibility(prior.InstalledWireCompatibility):
 @classmethod
 def setUpClass(cls):
  super().setUpClass();root=cls.root/'current';manifest=build(root)
  import venv
  env=cls.root/'venv-0.3.0';venv.create(env,with_pip=True);python=env/'bin/python'
  subprocess.run([str(python),'-I','-m','pip','install','--no-index','--no-deps',*[str(root/manifest[k]['file']) for k in ('client','provider','operator')]],cwd=cls.root,env=cls.environment,check=True,capture_output=True)
  cls.pythons['0.3.0']=python
 def test_current_captured_identity_against_previous_provider_and_restart(self):
  root=self.fresh('current-rollout');proc,endpoint=provider.start_installed(self.pythons['0.2.0'],root,self.environment);cfg=self.config(endpoint)
  try:before=self.call('0.3.0',cfg)
  finally:proc.kill();proc.wait(timeout=5)
  proc,endpoint=provider.start_installed(self.pythons['0.3.0'],root,self.environment);cfg['endpoint']=endpoint.__dict__
  try:self.assertEqual(before,self.call('0.3.0',cfg));self.assertEqual(before,self.call('0.2.0',cfg))
  finally:proc.terminate();proc.wait(timeout=5)
 def test_installed_operator_entrypoints_need_no_checkout(self):
  python=self.pythons['0.3.0']
  for module in ('integration.single_node.sustained_cli','integration.single_node.sustained_values','integration.single_node.preview_workbench'):
   result=subprocess.run([str(python),'-I','-m',module,'--help'],cwd=self.root,env=self.environment,capture_output=True,text=True)
   self.assertEqual(result.returncode,0,result.stderr)
