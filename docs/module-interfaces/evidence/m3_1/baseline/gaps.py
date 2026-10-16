import sys,json,time
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,'/tmp/fusion-m31-baseline-3b34e00')
from tests.m3_support import CognitionHarness,SCOPE
from fusion.contracts import ContractError,canonical
from fusion.evidence_relay import EvidenceRelay
from fusion.ports import Mutation
from fusion import memory_contracts as m
out={'source':'3b34e00df75055d54a57ba7e38eb8b2d9e82ed7e','classification':'expected baseline limitations; generated inputs, actual local DeTTa and native PLN; clock fixture labelled'}
def code(fn):
 try: fn(); return 'unexpected-success'
 except ContractError as e:return e.code
h=CognitionHarness(real=True)
try:
 def claim(key):return h.atoms.create(Mutation(SCOPE,key),'application/fusion-claim',canonical({'predicate':'pln:proposition','arguments':[key],'positive':True}))['ref']
 ep=h.episode('queue');first=claim('queue-0');r=h.append(ep,h.event(first,'queue-0'));d=h.submit(first,r['evidence'])
 out['acknowledgment_mismatch']=code(lambda:h.episodes.acknowledgeEvidence(Mutation(SCOPE,'ack'),r['delivery_id'],d))
 relay=EvidenceRelay(h.root/'relay.sqlite',h.episodes,h.beliefs)
 out['old_relay_mismatch']=code(lambda:relay.drain(ep))
 for i in range(1,m.MAX_PENDING):h.append(ep,h.event(claim('queue-'+str(i)),'queue-'+str(i)),i)
 out['pending_capacity']=len(h.episodes.pendingEvidence(ep,16))
 out['append_17']=code(lambda:h.append(ep,h.event(claim('overflow'),'overflow'),16))
finally:h.close()
for provider in ('sqlite','atomic-file-fixture'):
 h=CognitionHarness(real=True,provider=provider)
 try:
  entry,roles,_=h.generated();h.stimulate(entry)
  def hook(stage):
   if stage=='after_derived_commit':h.attention.advance(Mutation(SCOPE,'clock'),'generated',0,1)
  h.beliefs.hook=hook
  req=h.request(h.workset([entry]),candidates=1)
  result=h.controller.step(req);h.reopen();replayed=h.controller.step(req)
  with patch('fusion.inference.time.time',return_value=req.budget.deadline_ms/1000+1):terminal=h.controller.step(req)
  h.reopen();after=h.controller.step(req)
  out[provider]={'before':result,'same_stale_retry':replayed==result,'post_deadline':terminal,'terminal_replay_unchanged':after==terminal,'sti':h.attention.readAttention(entry['task'],'generated')['value']['sti']}
 finally:h.close()
assert out['acknowledgment_mismatch']=='NOT_AVAILABLE' and out['old_relay_mismatch']=='NOT_AVAILABLE'
assert out['pending_capacity']==16 and out['append_17']=='OVERLOADED'
for p in ('sqlite','atomic-file-fixture'):
 assert out[p]['same_stale_retry'] and out[p]['terminal_replay_unchanged']
 assert out[p]['post_deadline']['reason']=='deadline' and out[p]['post_deadline']['feedback'][0]['state']=='pending'
Path(sys.argv[1]).write_text(json.dumps(out,indent=2)+'\n')
print('Expected baseline gaps reproduced: incompatible acknowledgment/relay, 16 pending, rejected append 17, stale and post-terminal feedback for both providers.')
