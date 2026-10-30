"""Synthetic service boundary tests; no numerical provider substituted as real."""
import copy,json,tempfile,unittest,uuid
from pathlib import Path
from fusion import cognitive_services as c
from fusion.contracts import ContractError
from fusion.registry import descriptor_wire,selection_token

class CognitivePorts(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.path=Path(self.tmp.name)/'policy.json'
  self.cfg=dict(composition=c.COMPOSITION,privacy=c.PRIVACY,scope='synthetic-scope',attention_provider='sqlite',catalogue=[descriptor_wire(x) for x in c.descriptors()],actors={'A':'A','completion-relay':'A'},principals={k:dict(credential=(k+'-')*8,scopes={'synthetic-scope':['episodic.memory.readEvidence','episodic.memory.acknowledgeDelivery']}) for k in ('A','completion-relay')})
  self.save();self.port=c.Ports(self.path,'fusion-episodes')
 def save(self):self.path.write_text(json.dumps(self.cfg))
 def q(self,op='authorize',args=None):return dict(id=str(uuid.uuid4()),composition=c.COMPOSITION,scope='synthetic-scope',interface='episodic.memory',selection=selection_token(c.catalogue(self.cfg)['episodic.memory']),operation=op,args=['readEvidence'] if args is None else args)
 def error(self,code,call):
  with self.assertRaises(ContractError) as got:call()
  self.assertEqual(got.exception.code,code)
 def test_named_method_and_role_only(self):
  for op in ('eval','__dict__','execute','import','open'):
   self.error('UNSUPPORTED_OPERATION',lambda:self.port.invoke(c.ROUTE,'A-'*8,self.q(op)))
  q=self.q();q['interface']='belief.revision'
  self.error('UNSUPPORTED_OPERATION',lambda:self.port.invoke(c.ROUTE,'A-'*8,q))
 def test_bound_descriptor_and_current_authority(self):
  self.assertEqual(self.port.invoke(c.ROUTE,'A-'*8,self.q())['principal'],'A')
  q=self.q();q['selection']='0'*64
  self.error('UNSUPPORTED_PROFILE',lambda:self.port.invoke(c.ROUTE,'A-'*8,q))
  self.error('UNAUTHORIZED',lambda:self.port.invoke(c.ROUTE,'wrong-token'*8,self.q()))
  access=c.Access(self.path,'A-'*8,'episodic.memory');self.cfg['principals']['A']['scopes']={};self.save()
  self.error('UNAUTHORIZED',lambda:access.authorize('synthetic-scope','readEvidence'))
 def test_only_relay_can_acknowledge(self):
  self.error('UNAUTHORIZED',lambda:c.Access(self.path,'A-'*8,'episodic.memory').authorize('synthetic-scope','acknowledgeDelivery'))
  self.assertEqual(c.Access(self.path,'completion-relay-'*8,'episodic.memory').authorize('synthetic-scope','acknowledgeDelivery'),'A')
 def test_historical_privacy_not_relabelled(self):
  self.cfg['privacy']='private-local-only';self.save()
  self.error('UNSUPPORTED_PROFILE',lambda:self.port.invoke(c.ROUTE,'A-'*8,self.q()))
 def test_malformed_envelope_rejected_before_owner(self):
  q=self.q();q['arbitrary_path']='/private'
  self.error('UNSUPPORTED_OPERATION',lambda:self.port.invoke(c.ROUTE,'A-'*8,q))
  q=self.q();q['args']=['readEvidence','extra']
  self.error('INVALID_ARGUMENT',lambda:self.port.invoke(c.ROUTE,'A-'*8,q))

 def test_attention_constructs_without_storage_dependency(self):
  from unittest.mock import patch
  cfg=dict(self.cfg,root=self.tmp.name,runtime='unneeded-for-fixture-math',ports={})
  access=type('AccessFixture',(),{'selection':lambda _: 'fixture-selection'})()
  with patch('fusion.adapters.native_promotion.NativePromotion',return_value=object()):
   owner=self.port.owner(cfg,access,'attention')
  self.assertEqual(owner.path,str(Path(self.tmp.name)/'attention.sqlite'))

 def test_cognitive_wait_is_bounded_independently_of_s01(self):
  from types import SimpleNamespace
  from unittest.mock import patch
  with patch('ssl.create_default_context',return_value=SimpleNamespace()):
   port=c.Connection(dict(host='fusion-beliefs.synthetic.svc.cluster.local',port=8443,ca_file='fixture-ca'), 'fixture-token')
  self.assertEqual(port.timeout,25)
