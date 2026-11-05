"""Pure typed-source/lineage fixtures; no native, network or chain claim."""
import copy,inspect,json,unittest,uuid
from unittest.mock import Mock
from fusion.contracts import canonical,digest,ContractError
from fusion.lookup_contracts import make_head
from fusion import preview_vector_contracts as active,vector_contracts as vector
from fusion.preview_tasks import PROFILE
from examples.pilot_artifact_reference import document,text,verify,artifact,suffix,inspection_preflight,returned_object,retrieved_setup
class ArtifactReference(unittest.TestCase):
 def source(self):
  scope='synthetic-reference-fixture';uid=lambda:str(uuid.uuid4());ref=lambda:dict(scope_ref=scope,id=uid(),revision=1,digest='a'*64)
  view=dict(generation=uid(),head=make_head(uid(),scope,3),corpus='fixture',embedding=vector.FIXTURE,index=vector.INDEX,profile=active.PROFILE,lifecycle=make_head(uid(),scope,2,'immutable-memory-lifecycle/1'),active_digest='a'*64)
  view['logical']=digest(canonical({k:v for k,v in view.items() if k!='generation'}))
  task=dict(profile=PROFILE,kind='task',scope=scope,id=uid(),sender='A',recipient='B',session=uid(),deadline=1000,parent='fixture-occurrence',limits=dict(queries=1,relay_calls=24,recursive_delegation=False),query='fixture query',minimum=view);taskref=ref()
  result=dict(profile=PROFILE,kind='result',scope=scope,id=task['id'],sender='B',recipient='A',session=uid(),deadline=1000,parent=task['parent'],limits=task['limits'],task=taskref,view=view,projection='fixture large capture '+('x'*10000),payloads=[],status='captured-native-query')
  return dict(task=task,result=result,task_ref=taskref,result_ref=ref(),observations=[])
 def test_large_capture_has_bounded_reference_not_truncated_answer(self):
  s=self.source();before=copy.deepcopy(s);d=document(s);raw=text(s);self.assertLess(len(raw),4096);self.assertEqual(d['projection_bytes'],len(s['result']['projection'].encode()));self.assertEqual(d['projection_sha256'],digest(s['result']['projection'].encode()));self.assertEqual(s,before)
 def test_exact_native_readback_and_inspected_full_result_link(self):
  s=self.source();raw=text(s);w=dict(path='review.txt',revision=1,outcome='committed',digest=digest(raw.encode()),bytes=len(raw.encode()));r=dict(path='review.txt',revision=1,text=raw,digest=w['digest']);inspection=artifact(s,[]);self.assertTrue(verify(w,r,s,inspection)['exact_full_result_link'])
  for wrong in [dict(r,text=raw+' '),dict(r,digest='0'*64)]:
   with self.assertRaisesRegex(ContractError,'CONFLICT'):verify(w,wrong,s,inspection)
  with self.assertRaisesRegex(ContractError,'CONFLICT'):verify(w,r,s,dict(inspection,task=str(uuid.uuid4())))
 def test_uncorrelated_source_refuses_before_render(self):
  s=self.source();s['result']['id']=str(uuid.uuid4())
  with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):text(s)
 def test_actual_return_excludes_echoed_json_argument(self):
  command='write-file review.txt '+text(self.source());receipt=dict(outcome='committed',path='review.txt',bytes=20)
  projection='(RESULTS: ((COMMAND_RETURN: (('+command.replace('"','_quote_')+') '+canonical(receipt).decode().replace('"','_quote_')+'))))'
  self.assertEqual(returned_object(dict(projection=projection),command),receipt)
  for wrong in (projection+' ',projection.replace('write-file','append-file'),projection+projection):
   with self.assertRaisesRegex(ContractError,'CONFLICT'):returned_object(dict(projection=wrong),command)
 def test_native_readback_parses_quoted_manifest_as_text(self):
  raw=text(self.source());receipt=dict(path='review.txt',text=raw,revision=1,digest=digest(raw.encode()))
  projection='(RESULTS: ((COMMAND_RETURN: ((read-file review.txt) '+canonical(receipt).decode().replace('"','_quote_')+'))))'
  self.assertEqual(returned_object(dict(projection=projection),'read-file review.txt')['text'],raw)
 def test_empty_or_wrong_permitted_retrieval_fails_positive_evaluation(self):
  s=self.source();expected=dict(s['result_ref'],id=str(uuid.uuid4()));setup=dict(status='REMEMBER-SUCCESS',memory=dict(target=dict(payload=expected)))
  # Empty results remain valid artifacts; this positive workload still fails.
  self.assertEqual(artifact(s,[])['observations'],[])
  for found in ([],[dict(expected,id=str(uuid.uuid4()))]):
   s['result']['payloads']=found
   with self.assertRaisesRegex(ContractError,'CONFLICT'):retrieved_setup(setup,s)
  s['result']['payloads']=[expected];before=copy.deepcopy(s);value=retrieved_setup(setup,s)
  self.assertTrue(value['remembered_payload_retrieved']);self.assertFalse(value['expected_reference_supplied_to_consumer']);self.assertEqual(s,before)
 def test_inspection_domain_refuses_many_payloads_before_port_call(self):
  s=self.source();s['result']['payloads']=[dict(s['result_ref'],id=str(uuid.uuid4())) for _ in range(4)];op=Mock()
  with self.assertRaisesRegex(ContractError,'OVERLOADED'):inspection_preflight(op,'fixture-session',s,9999999999999)
  op.k.assert_not_called()
 def test_inspection_refuses_payload_mismatch_and_content_limit(self):
  s=self.source();ref=dict(s['result_ref'],id=str(uuid.uuid4()));s['result']['payloads']=[ref]
  with self.assertRaisesRegex(ContractError,'CONFLICT'):artifact(s,[])
  with self.assertRaises(ContractError):artifact(s,[dict(payload_ref=ref,content='x'*1025)])
  self.assertEqual(artifact(s,[dict(payload_ref=ref,content='real-port-content-fixture')])['result_ref'],s['result_ref'])
 def test_complete_envelope_limit_not_just_per_content_limit(self):
  s=self.source();refs=[dict(s['result_ref'],id=str(uuid.uuid4())) for _ in range(3)];s['result']['payloads']=refs
  with self.assertRaisesRegex(ContractError,'OVERLOADED'):artifact(s,[dict(payload_ref=r,content='x'*1024) for r in refs])
 def test_opt_in_suffix_keeps_inspection_and_default_exact(self):
  from fusion.workflow_recipes import artifact_delivery,render
  from examples.pilot_recipe_qualification import qualify
  from examples.pilot_recipe_chain import RecipeChain
  s=self.source();plan=artifact_delivery('fixture query','review.txt');before=copy.deepcopy(plan);changed=suffix(s,plan)
  self.assertEqual(plan,before);self.assertTrue(changed[0]['checkpoint']);self.assertEqual(changed[1],plan[2]);self.assertEqual(changed[0]['arguments'][1],text(s))
  self.assertEqual(inspect.signature(qualify).parameters['representation'].default,'full-projection');self.assertEqual(RecipeChain.representation,'full-projection')
  with self.assertRaisesRegex(ContractError,'NOT_AVAILABLE'):render(plan[1],{'delegate':{'_task_result':s['result']['projection']}})
 def test_real_owner_suffix_checkpoint_keeps_deadline_spend_and_capture(self):
  from tests.test_pilot_workflows import Workflows
  from fusion.workflow_recipes import artifact_delivery
  h=Workflows('test_three_registered_recipes_and_no_new_tool');h.setUp();self.addCleanup(h.doCleanups)
  s=self.source();plan=artifact_delivery('fixture query','review.txt');h.owner.admit(h.wid,h.sid,'approved-artifact-delivery/1',plan,9000)
  h.owner.advance(h.wid,1);pending=h.store.next_input('A',h.sid)
  h.store.complete('A',h.sid,pending['id'],dict(turn=1,projection=json.dumps(dict(status='TASK_PUBLISHED',task=s['task']['id'])),occurrences=['fixture']))
  before=h.owner.advance(h.wid,1);changed=h.owner.amend(h.wid,'reference',1,suffix(s,plan),'explicit operator reference selection')
  self.assertEqual(changed['deadline_ms'],9000);self.assertEqual(changed['reservations_spent'],1);self.assertEqual(changed['steps'],before['steps'])
  with self.assertRaisesRegex(ContractError,'NOT_AVAILABLE'):h.owner.advance(h.wid,2)
  held=h.owner.checkpoint(h.wid,'review',2,'exact reference');cp=held['checkpoints'][-1]
  h.owner.decide(h.wid,'review','approve','fixture-operator',cp['binding_sha256'],'approve');started=h.owner.advance(h.wid,2)
  self.assertEqual(started['reservations_spent'],2);self.assertEqual(started['steps']['delegate'],before['steps']['delegate']);self.assertEqual(started['steps']['artifact']['deadline_ms'],before['steps']['delegate']['deadline_ms']);self.assertEqual(started['deadline_ms'],9000)
  h.now[0]=9000
  with self.assertRaisesRegex(ContractError,'DEADLINE_EXCEEDED'):h.owner.amend(h.wid,'late',2,[plan[-1]],'must not renew')
  self.assertEqual(h.owner.observe(h.wid)['reservations_spent'],2)
 def test_checkpoint_selection_uses_exact_owner_identity_not_order(self):
  from examples.pilot_recipe_qualification import selected_checkpoint
  from tests.test_pilot_workflows import Workflows
  h=Workflows('test_three_registered_recipes_and_no_new_tool');h.setUp();self.addCleanup(h.doCleanups);h.admit()
  first=h.owner.checkpoint(h.wid,'reference-document-review',1,'first exact approval');cp=selected_checkpoint(first,'reference-document-review')
  h.owner.decide(h.wid,cp['identity'],'approve-first','operator',cp['binding_sha256'],'approve');h.owner.advance(h.wid,1);h.complete()
  current=h.owner.checkpoint(h.wid,'bounded-review',1,'second exact approval');before=h.owner.observe(h.wid)
  for rows in (current['checkpoints'],list(reversed(current['checkpoints']))):
   selected=selected_checkpoint(dict(current,checkpoints=rows),'bounded-review');self.assertIsNone(selected['decision']);self.assertEqual(selected['binding']['node'],'delegate')
  selected=selected_checkpoint(current,'bounded-review')
  after=h.owner.decide(h.wid,selected['identity'],'approve-second','operator',selected['binding_sha256'],'approve')
  self.assertEqual(after['reservations_spent'],before['reservations_spent']);self.assertEqual(after['deadline_ms'],before['deadline_ms']);self.assertEqual(after['steps'],before['steps'])
  self.assertEqual(selected_checkpoint(after,'reference-document-review')['decision']['identity'],'approve-first')
 def test_missing_ambiguous_or_misbound_checkpoint_refuses(self):
  from examples.pilot_recipe_qualification import selected_checkpoint
  row=dict(identity='bounded-review',binding=dict(identity='bounded-review'))
  for rows in ([],[row,row],[dict(row,binding=dict(identity='other'))]):
   with self.assertRaisesRegex(ContractError,'CONFLICT'):selected_checkpoint(dict(checkpoints=rows),'bounded-review')
if __name__=='__main__':unittest.main()
