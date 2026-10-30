"""Explicit recorded responses, real single-node services. Never launches a model.

The operator drives only the independent IRC peer and observes owner state.
The native caller performs every remember/query/model/send operation.
"""
import argparse,json,time,traceback
from pathlib import Path
import sys
from .test_memory_cluster import MemoryCluster
from .test_cluster import ROOT
ROLES=('omega-agent','fusion-storage','fusion-search','fusion-embedding','fusion-messaging','fusion-model','fusion-channel-bridge','irc-server','irc-peer')
class Workflow(MemoryCluster):
 def __init__(self,args,name):
  super().__init__(args,name)
  self.report.update(real=['native Omega parser/loop/remember/query/send','E5 CPU','Chroma','DeTTa','Messaging','ngIRCd/socket peer','pod-to-pod authenticated HTTPS'],fixtures=['explicit model responses','empty promoted/history context','declared metadata clocks'],ADDITIONAL_LIVE_GENERATIONS=0,live_workflow='NOT_RUN')
 def install(self,wrong=False):
  self.k('create','namespace',self.name)
  self.command([sys.executable,str(ROOT/'deploy/single-node/create_secrets.py'),'--workflow','--kubeconfig',self.args.kubeconfig,'--namespace',self.name,'--directory',str((self.root/'private-secrets').resolve())])
  self.upgrade()
 def snapshot(self,key):
  from concurrent.futures import ThreadPoolExecutor
  with ThreadPoolExecutor(max_workers=4) as pool:data=dict(zip(ROLES,pool.map(self.observe,ROLES)))
  self.report['observations'][key]=data
  self.report.setdefault('pvc_identities',{})[key]={v['metadata']['name']:v['metadata']['uid'] for v in json.loads(self.k('get','pvc','-o','json'))['items']}
  return data
 def invariants(self):
  snapshots=list(self.report['observations'].values())
  if len(snapshots)<2:return
  first_pvcs=next(iter(self.report['pvc_identities'].values()))
  assert all(v==first_pvcs for v in self.report['pvc_identities'].values())
  latest=snapshots[-1]
  stable=('context_view','intent','deadline','premises','request','candidates','payloads','enrichment','result','response','view','snapshot','envelope','wait_deadline')
  for before in snapshots[:-1]:
   for role,database in [('omega-agent','measured.sqlite'),('fusion-model','model.sqlite'),('fusion-channel-bridge','bridge.sqlite')]:
    for table,rows in before[role].get(database,{}).items():
     if table in ('app_binding','app_meta','channel_epochs'):continue
     after=latest[role].get(database,{}).get(table,[])
     for old in rows:
      key='id' if 'id' in old and old['id'] is not None else 'slot' if 'slot' in old else None
      if key is None:continue
      new=next((r for r in after if r.get(key)==old[key]),None);assert new is not None,(role,table,key)
      for k in stable:
       if k in old and old[k] is not None:assert new[k]==old[k],(role,table,k)
      for k in ('reserved','calls','polls','put_calls','send_calls','ack_calls','attempts','builds'):
       if k in old:assert new[k]>=old[k],(role,table,k)
  self.report['recovery_invariants']='PASS: retained PVCs, exact existing identities/inputs/views/captures/deadlines; monotonic spent counters'
 def peer(self,text):
  self.exec('irc-peer','import os,json;f=os.open("/state/peer-input",os.O_WRONLY|os.O_NONBLOCK);os.write(f,(json.dumps('+repr(dict(text=text))+')+"\\n").encode());os.close(f)')
 def measured(self):
  return json.loads(self.exec('omega-agent',"""import json
from pathlib import Path
p=Path('/state/process.json');e=Path('/state/native-exit.json');s=Path('/state/measured-status.json')
ready=p.exists() and e.exists() and s.exists() and e.stat().st_mtime>=p.stat().st_mtime and json.loads(p.read_text())['native_pid']==json.loads(e.read_text())['pid']
print(s.read_text() if ready else 'null')"""))
 def rows(self):return self.observe('omega-agent').get('measured.sqlite',{})
 def run(self):
  case=self.case
  if case=='wrong-permitted':self.values['workflow']['responses'][1]='send '+self.values['workflow']['bodies'][1]
  if case in ('altered-corpus','absent-corpus'):
   old='Synthetic violet beacon Ω stores seven paper moons.'
   new='Synthetic copper kettle Ω stores seven paper moons.' if case=='altered-corpus' else 'Synthetic blue box contains folded paper cranes.'
   del self.values['memory']['inputs'][old];self.values['memory']['inputs'][new]=new
   self.values['memory']['responses']=['remember '+x for x in self.values['memory']['inputs']]+['']
  if case=='rejected':self.values['workflow']['responses'][1]='metta (Truth_Deduction (stv 0.8 0.9) (stv 0.7 0.8))'
  pauses={'bridge-capture':('fusion-channel-bridge','after_bridge_capture',None),'input-acceptance':('omega-agent','after_application_input_commit',1),'model-unknown':('fusion-model','after_model_reservation',None),'model-capture':('fusion-model','after_model_provider_capture',None),'revocation':('omega-agent','after_model_provider_reply',1),'service-outage':('omega-agent','after_model_rpc_reservation',1),'query-capture':('omega-agent','after_native_result_capture',1),'send-accepted':('omega-agent','after_occurrence_bind',2),'uncertain-send':('fusion-channel-bridge','after_socket_reservation',None)}
  if case in pauses and pauses[case][0]!='omega-agent':self.config(pauses[case][0],test=dict(pause_at=pauses[case][1]))
  if case=='lost-model':self.config('fusion-model',test=dict(drop_response_operation='complete'))
  self.install()
  for role in ROLES:self.wait(lambda:self.file(role,'process.json'),180)
  self.wait(lambda:self.file('omega-agent','setup-view.json'),120)
  self.wait(lambda:self.file('fusion-channel-bridge','channel-ready.json'),30);self.wait(lambda:self.file('irc-peer','channel-ready.json'),30)
  self.snapshot('setup')
  if case=='bridge-capture':
   self.peer(self.values['workflow']['question']);self.pause('fusion-channel-bridge');self.snapshot('at-boundary');self.replace('fusion-channel-bridge');self.wait(lambda:self.file('fusion-channel-bridge','channel-ready.json'),30)
  before=self.uid('omega-agent');self.values['workflow']['phase']='measured'
  if case in pauses and pauses[case][0]=='omega-agent':self.config('omega-agent',test=dict(pause_at=pauses[case][1],pause_slot=pauses[case][2]))
  self.upgrade()
  self.wait(lambda:self.uid('omega-agent')!=before,30)
  self.wait(lambda:(self.file('omega-agent','process.json') and self.exec('omega-agent','from pathlib import Path;print(Path("/state/measured-native/channel-boundary.json").exists())').strip()=='True'),40)
  if case=='wrong-credential':
   self.exec('omega-agent',"import json;from pathlib import Path;p=Path('/run/fusion/model-client.json');v=json.loads(p.read_text());v['credential']='wrong-credential-'*4;p.write_text(json.dumps(v))")
  if case!='bridge-capture':self.peer(self.values['workflow']['question'])
  if case=='wrong-credential':
   self.wait(self.measured,30);data=self.snapshot('refused');assert data['omega-agent']['measured-status.json']['code']=='UNAUTHORIZED'
   assert not data['fusion-model'].get('model.sqlite',{}).get('model_calls',[])
   self.report.update(status='PASS',workflow_pass=False,negative_safety='wrong provider credential refused before prompt disclosure and model acceptance');return
  if case in ('revocation','service-outage'):
   self.pause('omega-agent');before=self.snapshot('at-boundary')
   if case=='revocation':
    self.exec('fusion-model',"import json;from pathlib import Path;p=Path('/run/fusion/owner.json');v=json.loads(p.read_text());v['principals']['M']['scopes'][v['model_completion']['scope']].remove('model.disclose');p.write_text(json.dumps(v))")
   else:self.k('patch','service','fusion-model','--type=merge','--patch',json.dumps(dict(spec=dict(ports=[dict(name='https',port=8443,targetPort=8444,protocol='TCP')]))))
   self.replace('omega-agent');self.wait(self.measured,40);failed=self.snapshot('refused')
   if case=='revocation':
    assert failed['omega-agent']['measured-status.json']['code']=='UNAUTHORIZED'
    assert len(failed['fusion-model']['recorded-evaluations.jsonl'])==1
    assert not failed['omega-agent']['measured.sqlite']['app_occurrences']
    self.report.update(status='PASS',workflow_pass=False,negative_safety='captured response retained; revoked disclosure blocked caller recovery');return
   assert failed['omega-agent']['measured-status.json']['code']=='NOT_AVAILABLE'
   self.k('patch','service','fusion-model','--type=merge','--patch',json.dumps(dict(spec=dict(ports=[dict(name='https',port=8443,targetPort='https',protocol='TCP')]))));self.replace('omega-agent')
  if case in ('input-acceptance','model-unknown','model-capture','query-capture'):
   role=pauses[case][0];self.pause(role);before=self.snapshot('at-boundary');self.replace(role)
   if role=='fusion-model':
    self.wait(lambda:self.measured(),15);self.replace('omega-agent')
   if case=='model-unknown':
    self.wait(self.measured,30);after=self.snapshot('spent-unknown')
    owner=after['fusion-model']['model.sqlite']['model_calls'];assert len(owner)==1 and owner[0]['reserved']==1 and owner[0]['response'] is None
    assert after['fusion-model'].get('recorded-evaluations.jsonl',[])==[]
    assert not after['omega-agent'].get('measured.sqlite',{}).get('app_occurrences',[])
    self.report.update(status='PASS',workflow_pass=False,negative_safety='unknown reservation was not re-evaluated');return
  if case=='lost-model':
   self.wait(self.measured,30);self.snapshot('lost-reply');self.replace('omega-agent')
  def queried():
   rows=self.rows()
   if (s:=self.measured()) and s['status']!='BOUNDED_STOP':raise AssertionError(s)
   return rows if any(r['done']==1 for r in rows.get('app_occurrences',[])) else None
  self.wait(queried,60)
  self.peer(self.values['workflow']['followup'])
  if case in ('send-accepted','uncertain-send'):
   role=pauses[case][0];self.pause(role);self.snapshot('at-boundary');self.replace(role)
  self.wait(lambda:(x if (x:=self.measured()) and x.get('status')=='BOUNDED_STOP' else None),60) if case!='rejected' else self.wait(self.measured,60)
  if case=='config-restart':
   before=self.snapshot('before-config');old=self.uid('fusion-model');self.config('fusion-model',revision='same-policy-v2');self.upgrade();self.wait(lambda:self.uid('fusion-model')!=old,30);self.wait(lambda:self.file('fusion-model','process.json'),30)
  time.sleep(.5)
  data=self.snapshot('final');app=data['omega-agent'].get('measured.sqlite',{});calls=app.get('app_model_calls',[])
  self.report['capture_count']=sum(r['result'] is not None for r in calls)
  self.report['admissions']=[r['admission'] for r in calls]
  self.report['retrieval']=len(app.get('app_memory_reads',[]))==1
  first=json.loads(calls[0]['intent']);second=json.loads(calls[1]['intent']) if len(calls)>1 else None
  self.report['next_prompt_binding']=bool(second and app['app_turns'][0]['projection'] in second['native_prompt'])
  self.report['answer_absent_initial']='violet beacon' not in first['native_prompt']
  sends=[json.loads(r['proposal'])[0][1] for r in calls if r['admission']=='authorized' and json.loads(r['proposal'])[0][0]=='send']
  peer=data['irc-peer'].get('peer-traffic.jsonl',[])
  observed=[r['received'].split(' :',1)[1] for r in peer if ':omega!' in r.get('received','') and ' PRIVMSG ' in r['received']]
  self.report['admitted_send_bodies']=sends;self.report['peer_bodies']=observed
  import re
  facts=[m.group(1) for r in data['omega-agent']['setup-view.json']['records'] if (m:=re.fullmatch(r'Synthetic (.+) Ω stores seven paper moons[.]',r['content']))]
  assert len(facts)<=1
  expected='Synthetic answer: '+facts[0]+'.' if facts else 'Insufficient retrieved information.'
  self.report['evaluator']=dict(source='application-owned committed setup records',rule='declared synthetic fact grammar; independent of permitted-output list',expected=expected)
  self.report['factual_correctness']=sends==[expected]
  self.report['peer_observation']=bool(sends and observed==sends)
  self.report['workflow_pass']=all(self.report[k] for k in ('retrieval','next_prompt_binding','answer_absent_initial','factual_correctness','peer_observation'))
  assert self.report['capture_count']==2
  assert self.report['retrieval'] and self.report['next_prompt_binding'] and self.report['answer_absent_initial']
  if case not in ('wrong-permitted','altered-corpus','absent-corpus','rejected','uncertain-send'):assert self.report['workflow_pass'],self.report
  elif case in ('wrong-permitted','altered-corpus','absent-corpus'):assert not self.report['factual_correctness'] and self.report['peer_observation']
  elif case=='rejected':assert not sends and not observed and calls[1]['admission'].startswith('rejected:')
  if case=='uncertain-send':
   rows=data['fusion-channel-bridge']['bridge.sqlite']['channel_egress'];assert len(rows)==1 and rows[0]['reserved']==1 and rows[0]['outcome']=='unknown' and not observed
  provider=data['fusion-model']['model.sqlite']['model_calls'];assert len(provider)==2 and all(r['reserved']==1 for r in provider)
  assert len(data['fusion-model']['recorded-evaluations.jsonl'])==2
  self.report['status']='PASS'

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--kubeconfig',required=True);p.add_argument('--prefix',required=True);p.add_argument('--output',required=True);p.add_argument('--values',default=str(ROOT/'deploy/single-node/workflow-values.yaml'));p.add_argument('--chart',default=str(ROOT/'deploy/helm/omega-fusion'));p.add_argument('--cases',nargs='+',default=['correct','wrong-permitted','rejected']);p.add_argument('--keep',action='store_true');a=p.parse_args();a.image_tag='workflow-v1';a.observer_source=(ROOT/'integration/single_node/workflow_observe.py').read_text().replace('from .memory_observe import memory_observe','from integration.single_node.memory_observe import memory_observe')
 assert a.prefix.startswith('omega-mc-') and 'omega-demo' not in a.prefix
 failures=0
 for case in a.cases:
  run=Workflow(a,case)
  try:run.run()
  except Exception:
   run.report.update(status='FAIL',failure=traceback.format_exc());failures+=1
   try:run.snapshot('failure')
   except Exception:pass
   print(run.report['failure'],flush=True)
  finally:
   try:
    run.invariants()
    run.report['pods']=json.loads(run.k('get','pods','-o','json'))
    for role in ROLES:
     try:(run.root/(role+'.log')).write_text(run.k('logs',role+'-0')+'\n'+run.exec(role,'from pathlib import Path;p=Path("/state/native.log");print(p.read_text()[-20000:] if p.exists() else "")'))
     except Exception:pass
   except Exception:
    run.report.update(status='FAIL',audit_failure=traceback.format_exc());failures+=1
   (run.root/'report.json').write_text(json.dumps(run.report,indent=2)+'\n')
   if not a.keep:
    try:run.k('delete','namespace',run.name,'--wait=false');run.report['cleanup']='namespace deletion requested'
    except Exception:pass
   print(case+': '+run.report['status'],flush=True)
 return bool(failures)
if __name__=='__main__':raise SystemExit(main())
