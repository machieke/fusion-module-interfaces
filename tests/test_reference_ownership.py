import unittest,tempfile,json
from pathlib import Path
from types import SimpleNamespace
from integration.single_node.test_cluster import Cluster
from integration.single_node.reference_ops import Operator
class Ownership(unittest.TestCase):
 def test_failed_create_cannot_delete_or_inspect_preexisting_namespace(self):
  with tempfile.TemporaryDirectory() as root:
   c=Cluster(SimpleNamespace(prefix='omega-ref-owned',output=root,image_tag='test',kubeconfig='unused'),'case')
   c.command=lambda *a,**kw:(_ for _ in ()).throw(RuntimeError('already exists'))
   with self.assertRaises(RuntimeError):c.k('create','namespace',c.name)
   with self.assertRaises(AssertionError):c.k('delete','namespace',c.name)
   with self.assertRaises(AssertionError):c.k('get','pods')
 def stopped_owner(self,remaining):
  op=Operator('unused','default','omega-ref-stop-test');op.owned=lambda:dict(metadata=dict(uid='owned'))
  op.workloads=lambda:[dict(metadata=dict(name='omega-agent',uid='writer'),spec=dict(replicas=1,template=dict(spec=dict(containers=[dict(image='pinned')]))))]
  reads=[]
  def k(*args,**kw):
   if args[:2]==('get','pods'):
    reads.append(args);return json.dumps(dict(items=[dict(name='writer')] if len(reads)<=2 or remaining else []))
   if args[:2]==('get','pvc'):return '{"items":[]}'
   if args[0]=='scale':return ''
   if args[0]=='wait':raise RuntimeError('no matching resources or failed observer')
   raise AssertionError(args)
  op.k=k;return op
 def test_stop_accepts_disappearance_between_list_and_wait(self):
  result=self.stopped_owner(False).quiesce()
  self.assertEqual(result['namespace_uid'],'owned')
 def test_stop_never_accepts_wait_error_with_remaining_writer(self):
  with self.assertRaisesRegex(RuntimeError,'failed observer'):self.stopped_owner(True).quiesce()
if __name__=='__main__':unittest.main()
