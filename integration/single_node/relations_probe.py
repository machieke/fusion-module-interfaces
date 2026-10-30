"""Synthetic typed relation workflow inside a caller pod; no native link adoption."""
import json
from pathlib import Path
from dataclasses import replace
from fusion.cognitive_services import client_configuration,Remote
from fusion.lookup import LookupConsumer
from fusion import lookup_contracts as c
from fusion.contracts import ContractError,canonical,digest
from fusion.ports import Mutation
from fusion.registry import selection_token

def run():
 cfg,_=client_configuration('/run/fusion/evidence-client.json');scope=cfg['scope']
 ports={k:Remote(cfg,k) for k in ('atom.storage','relations','search')};a,r,s=[ports[k] for k in ('atom.storage','relations','search')]
 def create(name,kind,topic='synthetic-structural'):
  return a.create(Mutation(scope,'reference-relations/'+name),c.KNOWLEDGE,canonical(dict(kind=kind,topic=topic,label=name)))['ref']
 roots=[create('task-'+str(i),'task') for i in range(3)];pre=[create('prerequisite-'+str(i),'prerequisite') for i in range(3)]
 create('unrelated','note')
 for i,x in enumerate(roots):
  for j,y in enumerate(pre):
   cmd=Mutation(scope,'reference-relations/edge-'+str(i)+'-'+str(j));args=('requires/1',(('dependent',x),('prerequisite',y)),True)
   first=r.assertRelation(cmd,*args);assert first==r.assertRelation(cmd,*args)
 head=a.head(scope);query=c.AttributeQuery(scope,{'all':[{'field':'kind','eq':'task'},{'field':'topic','eq':'synthetic-structural'}]},head,2)
 def drain():
  receipts=[]
  for _ in range(64):
   value=s.catchUp(scope,8);receipts.append(value)
   if value['at']==value['target'] and not value['rebuilding']:return receipts
  raise AssertionError('maintenance bound exhausted')
 initial=drain();first=s.query(query);assert first['cursor'] and not first['page_complete']
 consumer=LookupConsumer('/state/structural-consumer.sqlite',a,r,s,ports,{k:selection_token(v.descriptor) for k,v in ports.items()})
 # This call receives attributes and source head only, never answer references.
 result=consumer.lookup(Mutation(scope,'reference-lookup/1'),query)
 assert len(result['roots'])==3 and len(result['relations'])==9 and len(result['documents'])==6
 assert result['calls']['query']==2 and result['calls']['incoming']>0 and result['calls']['outgoing']>0
 create('late-task','task');newhead=a.head(scope)
 try:s.query(replace(query,minimum=newhead))
 except ContractError as e:assert e.code=='NOT_AVAILABLE'
 else:raise AssertionError('stale projection accepted new minimum')
 drain();retained=s.query(replace(query,cursor=first['cursor']));assert len(retained['refs'])==1 and retained['at']==first['at']
 rebuilt=s.beginRebuild(Mutation(scope,'reference-rebuild/1'));maintenance=drain()
 try:s.query(replace(query,cursor=first['cursor']))
 except ContractError as e:assert e.code=='CONFLICT'
 else:raise AssertionError('old cursor survived new generation')
 new=consumer.lookup(Mutation(scope,'reference-lookup/2'),replace(query,minimum=newhead));assert len(new['roots'])==4
 assert consumer.lookup(Mutation(scope,'reference-lookup/1'),query)==result
 return dict(classification='REAL_TYPED_PROVIDER_NOT_NATIVE_LINK_ADOPTION',source=head,later_source=newhead,initial_maintenance=initial,result=result,retained_page=retained,rebuild=rebuilt,rebuild_maintenance=maintenance,new_result=new,consumer_inputs='query attributes + source minimum; no answer refs',status='PASS')
if __name__=='__main__':print(json.dumps(run()))
