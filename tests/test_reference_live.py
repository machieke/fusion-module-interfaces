"""Preparation-only checks. No real backend constructor/process is reachable."""
import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from fusion.contracts import canonical,digest,ContractError
from integration.single_node import future_live as live
class Guard(unittest.TestCase):
 def plan(self,root):
  value=dict(schema=live.SCHEMA,kind='live',freeze='COMPLETE',campaign_id='new-reference-denial-test',slots=[dict(name='https-query',id='one',session='test',slot=1),dict(name='https-reply',id='two',session='test',slot=2)],provider_state='/state/live-campaign',runtime_lock=dict(path='/opt/generative/runtime.json'),sources=[],bindings=[],runtime_required_files=[])
  p=root/'plan.json';p.write_bytes(canonical(value));p.with_suffix('.sha256').write_text(digest(p.read_bytes()));return p
 def test_supervisor_denies_before_child_or_host(self):
  with tempfile.TemporaryDirectory() as directory:
   p=self.plan(Path(directory))
   with patch('subprocess.Popen',side_effect=AssertionError('process forbidden')) as child:
    with self.assertRaises(ContractError):live.supervised(p,None,'/config/component.json')
    child.assert_not_called()
 def test_corruption_enabled_flag_and_exhausted_campaign_are_not_approval(self):
  with tempfile.TemporaryDirectory() as directory:
   p=self.plan(Path(directory));a=Path(directory)/'approval.json';a.write_text(json.dumps(dict(enabled=True,manifest_sha256=digest(p.read_bytes()))))
   with self.assertRaises(ContractError):live.approve(p,a)
 def test_live_owner_without_separate_authority_is_refused(self):
  from integration.single_node.workflow_configure import configure
  with tempfile.TemporaryDirectory() as directory:
   cfg=dict(role='fusion-model',workflow=dict(enabled=True,mode='live',liveEnabled=True),state=directory,run=directory)
   with self.assertRaises(ContractError):configure(cfg)
 def test_offline_runtime_symlink_inventory_is_checked_without_execution(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);target=root/'library.1';target.write_bytes(b'non-executable test asset');link=root/'library';link.symlink_to(target.name)
   projected=root/'component.json';projected.symlink_to(target.name)
   value=dict(sources=[],bindings=[dict(path=str(projected),sha256=digest(target.read_bytes()))],runtime_required_files=[dict(path=str(link),symlink=target.name),dict(path=str(target),sha256=digest(target.read_bytes()))])
   with patch.object(live,'authority',return_value=(value,'test')):
    self.assertEqual(live.approve('unused','unused'),(value,'test'))
    target.write_bytes(b'changed')
    with self.assertRaises(ContractError):live.approve('unused','unused')
    target.write_bytes(b'non-executable test asset');link.unlink();link.symlink_to('missing')
    with self.assertRaises(ContractError):live.approve('unused','unused')
if __name__=='__main__':unittest.main()
