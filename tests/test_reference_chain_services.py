"""Transport boundary negatives; no node or generative runtime."""
import tempfile,json,unittest
from pathlib import Path
from unittest.mock import patch
from fusion import chain_services as c,inspect_services as i
from fusion.contracts import ContractError
from fusion.registry import selection_token
class ChainBoundaries(unittest.TestCase):
 def rejected(self,fn,code):
  with self.assertRaises(ContractError) as e:fn()
  self.assertEqual(e.exception.code,code)
 def test_fabricated_finality_rejected(self):
  for value in ({},dict(deploy_id='x',inclusion_block=None,effect_finality='pending',evidence={}),dict(deploy_id='a'*128,inclusion_block='b'*64,effect_finality='finalized',evidence={})):
   self.rejected(lambda:c.observation(value),'NOT_AVAILABLE')
 def test_missing_registration_and_wrong_credentials(self):
  with tempfile.TemporaryDirectory() as root:
   p=Path(root)/'owner';p.write_text(json.dumps(dict(principals={'A':dict(credential='a'*64,scopes={'shared-test':['consensus.finality.submit']})},registration=None)))
   owner=c.Ports(p);q=dict(composition=c.COMPOSITION,selection=selection_token(c.DESCRIPTOR),operation='submit',body={},approved={},binding={})
   self.rejected(lambda:owner.invoke('/commitment','b'*64,q),'UNAUTHORIZED')
   self.rejected(lambda:owner.invoke('/commitment','a'*64,q),'UNAUTHORIZED')
   self.rejected(lambda:owner.invoke('/commitment','a'*64,{**q,'operation':'arbitrary-deploy'}),'UNSUPPORTED_OPERATION')
 def test_default_chain_consensus_not_overridden(self):
  from integration.single_node.chain_node import CONFIG
  self.assertIn('dev-mode = false',CONFIG)
  for x in ('fault-tolerance','synchrony','phlo','autopropose','gc'):self.assertNotIn(x,CONFIG)
 def test_no_generation_import(self):
  import inspect
  from integration.single_node import chain_node,hive_actor
  for m in (chain_node,hive_actor,c,i):
   for x in ('OllamaCompletion','ModelService','RecordedBackend'):self.assertNotIn(x,inspect.getsource(m))
if __name__=='__main__':unittest.main()
