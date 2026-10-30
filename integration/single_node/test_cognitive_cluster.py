"""Real synthetic native cognitive service qualification; model/input fixtures."""
import argparse,json,sys,traceback,hashlib,shutil
from pathlib import Path
from .test_cluster import ROOT
from .test_memory_cluster import MemoryCluster

ROLES=('omega-agent','fusion-storage','fusion-search','fusion-embedding','fusion-episodes','fusion-beliefs','fusion-attention','fusion-relations','fusion-exact-search')
class CognitiveCluster(MemoryCluster):
 def install(self,wrong=False):
  self.k('create','namespace',self.name)
  self.command([sys.executable,str(ROOT/'deploy/single-node/create_secrets.py'),'--reference','--kubeconfig',self.args.kubeconfig,'--namespace',self.name,'--directory',str((self.root/'private-secrets').resolve())])
  self.upgrade()
 def observe(self,role):return json.loads(self.exec(role,'from integration.single_node.cognitive_observe import observe;import json;print(json.dumps(observe()))'))
 def snapshot(self,key):
  data={r:self.observe(r) for r in ROLES};self.report['observations'][key]=data;return data
 def run(self):
  self.report.update(real=['native Omega loop/parser/remember/query/support/contradict/promote/demote/getContext','E5','Chroma','DeTTa','original NAL Truth_Revision and wall-clock promotion','separate C1/C2/Attention/Relations/Search owners','pod-to-pod HTTPS'],fixtures=['external model commands','synthetic input sources','empty channel/history','creation and promotion clock'])
  if self.case=='attention-file':
   self.values['reference']['attentionProvider']='file-fixture'
   self.report['fixtures'].append('independent file Attention persistence provider; original native math remains real')
  pauses={'source-recovery':('omega-agent','after_source_acceptance'),'belief-recovery':('fusion-beliefs','after_evidence_decision_commit'),'priority-recovery':('fusion-attention','after_priority_commit')}
  if self.case in pauses:
   role,stage=pauses[self.case];self.config(role,test=dict(pause_at=stage))
  self.install()
  for role in ROLES:self.wait(lambda:self.file(role,'process.json'),180)
  if self.case in pauses:
   role,stage=pauses[self.case];self.wait(lambda:self.file(role,'pause.json'),180)
   # Capture the caller identity and interrupted owner's commit, then kill
   # promptly. A nine-pod audit plus transport-timeout wait can consume the
   # original 30-second business deadline; diagnostics do not extend it.
   before={'omega-agent':self.observe('omega-agent')}
   if role!='omega-agent':before[role]=self.observe(role)
   self.report['observations']['at-boundary']=before
   targets=list(dict.fromkeys((role,'omega-agent')));uids={r:self.uid(r) for r in targets}
   self.k('delete','pod',*(r+'-0' for r in targets),'--grace-period=1','--wait=false')
   for r in targets:
    after=self.wait(lambda:(v if (v:=self.uid(r))!=uids[r] else None),20)
    self.report['actions'].append(dict(action='pod-replacement',role=r,old_uid=uids[r],new_uid=after))
   status=self.ended(180);data=self.snapshot('completed');self.same(before,data)
  else:status=self.ended(180);data=self.snapshot('completed')
  assert status['status']=='BOUNDED_STOP',status
  a=data['omega-agent'];assert len(a['app_occurrences'])==10 and all(r['done']==1 for r in a['app_occurrences'])
  assert len(a['app_sources'])==2 and len(a['app_assessments'])==3
  assert len(a['model_contexts'])==11
  b=data['fusion-beliefs']['cognitive']['beliefs.sqlite'];e=data['fusion-episodes']['cognitive']['episodes.sqlite']
  assert len(e['events'])==5 and len(e['deliveries'])==len(e['completions'])==3
  assert all(x['decision'] is not None for x in e['deliveries'])
  assert len(b['snapshots'])==3 and len(b['nal_priors'])==1 and len(b['nal_budgets'])==2
  assert [json.loads(x['decision'])['numerical'] for x in b['attempts']]==['revised','no-change','revised']
  assert all(x['evaluations']==1 for x in b['nal_budgets'])
  views=[json.loads(x['value']) for x in b['snapshots']]
  assert views[0]['observations']==[] and views[0]['supports'][0]['lineage_roots']==[]
  assert len(views[-1]['observations'])==2 and {x['relationship'] for x in views[-1]['observations']}=={'supports','contradicts'}
  assert views[-1]['truth']['strength']=='0.6666666666666666' and views[-1]['truth']['confidence']=='0.75'
  assert len(data['fusion-search']['publications']['generations'])==2
  contexts=a['app_priority_contexts'];assert [x['slot'] for x in contexts if json.loads(x['result'])['selected']]==[8,9]
  for x in contexts:
   if x['slot'] in (8,9):assert 'Synthetic violet beacon' in x['rendered'] and '0.75' in x['rendered']
  assert len(a['app_memory_reads'])==4 and len(a['app_memory_writes'])==1
  self.report['relations']=json.loads(self.exec('omega-agent','from integration.single_node.relations_probe import run;import json;print(json.dumps(run()))'))
  target=self.k('get','service','fusion-storage','-o','jsonpath={.spec.clusterIP}')
  probe="import socket,json,time;s=socket.socket();s.settimeout(1);t=time.monotonic();v=s.connect_ex(("+repr(target)+",8443));s.close();print(json.dumps(dict(connect_errno=v,elapsed=time.monotonic()-t)))"
  allowed=json.loads(self.exec('omega-agent',probe));denied=json.loads(self.exec('fusion-attention',probe))
  assert allowed['connect_errno']==0 and denied['connect_errno']!=0
  self.report['network_policy']=dict(allowed=allowed,denied=denied,enforcement='observed allowed caller and denied unrelated Attention pod -> storage TCP')
  self.report['diagnostics']={role:json.loads(self.exec(role,'from integration.single_node.diagnostics import inspect;import json;print(json.dumps(inspect()))')) for role in ROLES if role!='fusion-embedding'}
  self.report['status']='PASS' 

def main():
 p=argparse.ArgumentParser();p.add_argument('--kubeconfig',required=True);p.add_argument('--prefix',required=True);p.add_argument('--output',required=True);p.add_argument('--values',default='deploy/single-node/cognitive-values.yaml');p.add_argument('--cleanup',action='store_true');p.add_argument('cases',nargs='+',choices=['baseline','attention-file','source-recovery','belief-recovery','priority-recovery']);a=p.parse_args()
 assert a.prefix.startswith('omega-ref-')
 a.image_tag='unused';out=Path(a.output);out.mkdir(parents=True,exist_ok=False);a.chart=out/'frozen-chart';shutil.copytree(ROOT/'deploy/helm/omega-fusion',a.chart)
 files={str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for folder in ('fusion','integration','deploy') for f in (ROOT/folder).rglob('*') if f.is_file() and '__pycache__' not in f.parts}
 (out/'source-manifest.json').write_text(json.dumps(files,indent=2)+'\n');failed=False
 for case in a.cases:
  test=CognitiveCluster(a,case)
  try:test.run()
  except Exception as e:
   failed=True;test.report.update(status='FAIL',failure=str(e),traceback=traceback.format_exc())
   try:test.snapshot('failure')
   except Exception as e:test.report['observation_error']=str(e)
  finally:
   for role in ROLES:
    try:(test.root/(role+'.log')).write_text(test.k('logs',role+'-0'))
    except Exception:pass
   for kind in ('pods','pvcs'):
    try:test.report[kind]=json.loads(test.k('get',kind,'-o','json'))
    except Exception:pass
   test.finish()
   if a.cleanup:test.k('delete','namespace',test.name,'--wait=false','--ignore-not-found=true')
  print(case,test.report['status'],test.report.get('failure',''),flush=True)
 raise SystemExit(int(failed))
if __name__=='__main__':main()
