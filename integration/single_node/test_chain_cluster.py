"""Real native Hive inspection, split owners and isolated real F1R3node.

Generated, explicitly shareable artifact only. Operator registers exact result
AFTER native receipt consumption. No generative runtime or fixture chain.
"""
import argparse,json,sys,shutil,time,traceback,hashlib
from pathlib import Path
from .test_cluster import ROOT
from .test_memory_cluster import MemoryCluster
from fusion.adapters.f1r3_m4 import DESCRIPTOR,PROFILE
from fusion.registry import descriptor_wire,selection_token
from fusion.contracts import digest,canonical
ROLES=('omega-agent','fusion-execution','fusion-storage','fusion-messaging','fusion-commitment','f1r3node')

class ChainCluster(MemoryCluster):
 def install(self,wrong=False):
  self.k('create','namespace',self.name)
  self.command([sys.executable,str(ROOT/'deploy/single-node/create_secrets.py'),'--chain','--kubeconfig',self.args.kubeconfig,'--namespace',self.name,'--directory',str((self.root/'private-secrets').resolve())])
  self.values['reference']['chain'].update(json.loads((self.root/'private-secrets/chain-public.json').read_text()))
  self.upgrade()
 def observe(self,role):
  return json.loads(self.exec(role,"""import json,sqlite3
from pathlib import Path
out={}
for file in ('process.json','native-status.json','inspection.json','submission.json','final-observation.json','chain-identity.json','node-ready.json','inspect-window.json','commitment-window.json','worker-status.json','last-native-response.json'):
 p=Path('/state')/file
 if p.exists():out[file]=json.loads(p.read_text())
for file in ('execution.sqlite','messages.sqlite','atoms.sqlite','inspect.sqlite','commitments.sqlite','chain-progress.sqlite'):
 p=Path('/state')/file
 if p.exists():
  with sqlite3.connect(p.as_uri()+'?mode=ro',uri=True) as db:
   db.row_factory=sqlite3.Row
   out[file]={r[0]:[dict(x) for x in db.execute('SELECT * FROM '+r[0])] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
print(json.dumps(out))"""))
 def snapshot(self,key):
  data={r:self.observe(r) for r in ROLES};self.report['observations'][key]=data;return data
 def isolation(self):
  # Bind sentinels BEFORE any real node start. A failed policy check cannot
  # activate the chain. Reserved test addresses are not public service targets.
  code="import socket,time;ss=[]\nfor port in (40401,40402,40403,40404,40405):\n s=socket.socket();s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);s.bind(('0.0.0.0',port));s.listen();ss.append(s)\ntime.sleep(35)"
  self.exec('f1r3node',"import subprocess,sys,json;from pathlib import Path;p=subprocess.Popen([sys.executable,'-c',"+repr(code)+"],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True);Path('/run/fusion/sentinel.pid').write_text(str(p.pid));print(p.pid)")
  def probe(role,host,port):
   return json.loads(self.exec(role,"import socket,time,json;s=socket.socket();s.settimeout(1);t=time.monotonic();v=s.connect_ex(("+repr(host)+","+str(port)+"));s.close();print(json.dumps(dict(errno=v,seconds=time.monotonic()-t)))"))
  ip=self.k('get','pod','f1r3node-0','-o','jsonpath={.status.podIP}')
  allowed=probe('fusion-commitment',ip,40403);denied={str(p):probe('fusion-commitment',ip,p) for p in (40401,40402,40404,40405)}
  denied['agent-http']=probe('omega-agent',ip,40403);denied['node-external']=probe('f1r3node','192.0.2.1',443)
  require=allowed['errno']==0 and all(x['errno']!=0 for x in denied.values());assert require,(allowed,denied)
  self.exec('f1r3node',"import os,signal;from pathlib import Path;os.kill(int(Path('/run/fusion/sentinel.pid').read_text()),signal.SIGTERM)")
  self.report['isolation_before_activation']=dict(allowed=allowed,denied=denied,node_started=False)
 def fresh_file(self,role,name):
  return json.loads(self.exec(role,"import json;from pathlib import Path;a=Path('/state/process.json');p=Path('/state/"+name+"');print(p.read_text() if a.exists() and p.exists() and p.stat().st_mtime>=a.stat().st_mtime else 'null')"))
 def reader(self,trace):
  import base64
  data=json.loads((self.root/'private-secrets/fusion-commitment.secret.json').read_text())['data']
  self.k('create','-f','-',input=json.dumps(dict(apiVersion='v1',kind='Secret',metadata=dict(name='chain-read-only-auth'),data={'ca.crt':data['ca.crt'],'storage-token':data['inspect-fusion-storage-token']})))
  code="""from fusion.adapters.f1r3 import F1R3HTTP
from fusion.adapters.f1r3_m4 import observe_effect
from fusion.inspect_services import RemoteAtoms
from fusion.neoclaw_services import PortConnection
from fusion.contracts import digest
from pathlib import Path
from dataclasses import asdict
import json
x=TRACE
atoms=RemoteAtoms(PortConnection(dict(host='fusion-storage.NAMESPACE.svc.cluster.local',port=8443,ca_file='/secrets/ca.crt'),Path('/secrets/storage-token').read_text()))
import time
observations=[];result=dict(signing_key_mounted=False,owner_journals_mounted=False)
for _ in range(30):
 try:
  payload=atoms.get(x['ref']);assert digest(payload.bytes)==x['digest']
  v=observe_effect(F1R3HTTP('http://f1r3node.NAMESPACE.svc.cluster.local:40403'),x['signed'],x['read_name'],x['operation'],x['digest'],x['chain']);observations.append(asdict(v));result.update(observation=asdict(v),payload_sha256=digest(payload.bytes))
  if v.effect_finality=='finalized':break
 except Exception as e:observations.append(dict(error=type(e).__name__,detail=str(e)))
 time.sleep(.5)
result['observations']=observations
print(json.dumps(result),flush=True)
""".replace('TRACE',repr(trace)).replace('NAMESPACE',self.name)
  pod=dict(apiVersion='v1',kind='Pod',metadata=dict(name='chain-independent-reader',labels={'app.kubernetes.io/instance':'omega','app.kubernetes.io/name':'fusion-commitment'}),spec=dict(restartPolicy='Never',automountServiceAccountToken=False,securityContext=dict(runAsNonRoot=True,runAsUser=1000,runAsGroup=1000,fsGroup=1000),containers=[dict(name='read',image=self.values['image']['repository']+':'+self.values['image']['tag'],imagePullPolicy='Never',command=['/opt/native/python/bin/python3.12','-c',code],securityContext=dict(allowPrivilegeEscalation=False,readOnlyRootFilesystem=True,capabilities=dict(drop=['ALL'])),resources=dict(requests=dict(cpu='25m',memory='64Mi'),limits=dict(cpu='500m',memory='256Mi')),volumeMounts=[dict(name='read-only-auth',mountPath='/secrets',readOnly=True)])],volumes=[dict(name='read-only-auth',secret=dict(secretName='chain-read-only-auth'))]))
  self.k('create','-f','-',input=json.dumps(pod));self.wait(lambda:self.k('get','pod','chain-independent-reader','-o','jsonpath={.status.phase}') in ('Succeeded','Failed'),45)
  self.report['independent_reader_pod']=json.loads(self.k('get','pod','chain-independent-reader','-o','json'))
  raw=self.wait(lambda:self.k('logs','chain-independent-reader'),5);self.report['independent_reader_output']=raw
  result=json.loads(raw);assert result['observation']['effect_finality']=='finalized';return result
 def run(self):
  self.report.update(real=['original authenticated native Hive Programs API','inspect_atom execution','DeTTa','separate owner PVCs','authenticated pod HTTPS','isolated F1R3node default consensus','original fixed commitment/signing adapter'],fixtures=['generated synthetic input and operator policy','unconsumed counterparty mailbox'],additional_live_generations=0)
  self.install()
  for role in ROLES:self.wait(lambda:self.file(role,'process.json'),160)
  self.isolation()
  def inspected():
   v=self.file('omega-agent','inspection.json');status=self.file('omega-agent','native-status.json')
   assert v or not status or status['status']!='STOPPED',status
   return v
  inspection=self.wait(inspected,120)
  self.report['inspection']=inspection
  self.values['reference']['chain'].update(nodeEnabled=True,isolationVerified=True);self.upgrade()
  identity=self.wait(lambda:self.file('f1r3node','chain-identity.json'),120)
  chain=self.values['reference']['chain'];detail=inspection['response']['detail'];operation=chain['command']
  approved=dict(scope_ref='shared-test',result_ref=detail['result']['ref'],commitment_digest=detail['result']['ref']['digest'],approval_record='generated-inspect-policy/1:'+operation)
  binding=dict(profile=PROFILE,selection=selection_token(DESCRIPTOR),chain=identity,signer=chain['public_key'],limits=dict(phloPrice=1,phloLimit=10000000,validAfterBlockNumber=0),operation=operation,protobuf_sha256='ba9b8ebd44e73cabac064ec00e4f93d9a08a8681bcb3bce3eb5dca6366ba23e6',owner_journal='/state/commitments.sqlite',authority=dict(principal=inspection['principal'],swarm=inspection['swarm'],original_command=operation,seed=chain['seed'],expires_at_ms=time.time_ns()//1000000+1200000))
  chain.update(descriptor=descriptor_wire(DESCRIPTOR),registration=dict(approved=approved,binding=binding,job_id=detail['job']['job_id'],result=detail['result']))
  if self.args.scenario in ('signed-recovery','uncertain-submission'):
   self.config('fusion-commitment',test=dict(pause_at='after_signed_intent' if self.args.scenario=='signed-recovery' else 'after_node_submission',drop_response_operation='submit'))
  if self.args.scenario=='observation-recovery':self.config('omega-agent',test=dict(pause_at='after_observation_before_progress'))
  self.report['exact_registration']=chain['registration'];self.upgrade()
  if self.args.scenario in ('signed-recovery','uncertain-submission','observation-recovery'):
   role='omega-agent' if self.args.scenario=='observation-recovery' else 'fusion-commitment'
   marker='caller-pause' if role=='omega-agent' else 'pause.json'
   self.wait(lambda:self.exec(role,"from pathlib import Path;print(Path('/state/"+marker+"').exists())").strip()=='True',120)
   self.report['fault_boundary']=self.observe('fusion-commitment')
   targets=list(dict.fromkeys((role,'omega-agent')));uids={r:self.uid(r) for r in targets}
   self.k('delete','pod',*(r+'-0' for r in targets),'--grace-period=1','--wait=false')
   for r in targets:
    uid=self.wait(lambda:(v if (v:=self.uid(r))!=uids[r] else None),25)
    self.report['actions'].append(dict(action='kill-at-independent-commit',role=r,old_uid=uids[r],new_uid=uid))
  final=self.wait(lambda:self.file('omega-agent','final-observation.json'),200)
  assert final['detail']['chain']['effect_finality']=='finalized',final
  before=self.snapshot('finalized');intent=before['fusion-commitment']['commitments.sqlite']['m4_intent'][0]
  assert final['detail']['chain']['evidence']['value']['digest']==approved['commitment_digest']
  assert len(before['fusion-execution']['execution.sqlite']['jobs'])==1 and len(before['fusion-execution']['execution.sqlite']['outbox'])==1
  assert before['omega-agent']['inspect.sqlite']['receipts'][0]['acknowledged']==1
  # Actual owner/caller replacement and same-genesis node recovery. The original
  # committed intent, timestamp, receipt, slots and windows are retained.
  for role in ('omega-agent','fusion-commitment','f1r3node'):
   self.replace(role);self.wait(lambda:self.file(role,'process.json'),120)
  self.wait(lambda:self.fresh_file('f1r3node','node-ready.json'),120)
  self.wait(lambda:self.fresh_file('omega-agent','native-exit.json'),120)
  after=self.snapshot('recovered')
  assert after['fusion-commitment']['commitments.sqlite']['m4_intent'][0]==intent
  assert after['f1r3node']['chain-identity.json']==identity
  assert before['omega-agent']['inspect-window.json']==after['omega-agent']['inspect-window.json']
  signed=json.loads(intent['signed']);trace=dict(signed=signed,read_name=intent['read_name'],operation=operation,digest=approved['commitment_digest'],chain=identity,ref=approved['result_ref'])
  readback=self.reader(trace)
  # Node outage is an observation failure; it does not erase the captured
  # native result or signed intent and does not create a replacement job.
  self.k('scale','statefulset','f1r3node','--replicas=0');self.k('wait','--for=delete','pod/f1r3node-0','--timeout=45s')
  code="import json;from pathlib import Path;from fusion.chain_services import Remote;from fusion.ports import ApprovedCommitment;x="+repr(chain['registration'])+";cfg=dict(service_endpoint=dict(host='fusion-commitment."+self.name+".svc.cluster.local',port=8443,ca_file='/secrets/ca.crt'),service_credential=Path('/secrets/fusion-commitment-token').read_text().strip());from dataclasses import asdict;print(json.dumps(asdict(Remote(cfg,ApprovedCommitment(**x['approved']),x['binding'],lambda:None).observe("+repr(signed['signature'])+"))))"
  outage=json.loads(self.exec('omega-agent',code));self.report['outage']=outage;assert outage['effect_finality']=='not-observed'
  self.k('scale','statefulset','f1r3node','--replicas=1');self.wait(lambda:self.fresh_file('f1r3node','node-ready.json'),120)
  observations=[]
  def observed_again():
   value=json.loads(self.exec('omega-agent',code));observations.append(value);self.report['outage_recovery_observations']=observations
   return value if value['effect_finality']=='finalized' else None
  # HTTP/genesis readiness precedes restoration of the node's effect read path.
  # These bounded read-only observations cannot submit, re-sign or renew intent.
  recovered=self.wait(observed_again,60);assert recovered['deploy_id']==signed['signature']
  self.report.update(readback=readback,same_artifact_trace=trace,outage=outage,after_outage=recovered,status='PASS')

def main():
 p=argparse.ArgumentParser();p.add_argument('--kubeconfig',required=True);p.add_argument('--prefix',required=True);p.add_argument('--output',required=True);p.add_argument('--values',default='deploy/single-node/chain-values.yaml');p.add_argument('--cleanup',action='store_true');p.add_argument('--scenario',default='baseline',choices=['baseline','signed-recovery','uncertain-submission','observation-recovery']);a=p.parse_args();assert a.prefix.startswith('omega-ref-');a.image_tag='unused'
 out=Path(a.output);out.mkdir(parents=True,exist_ok=False);a.chart=out/'chart';shutil.copytree(ROOT/'deploy/helm/omega-fusion',a.chart)
 files={str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for folder in ('fusion','integration','deploy') for f in (ROOT/folder).rglob('*') if f.is_file() and '__pycache__' not in f.parts};(out/'source-manifest.json').write_text(json.dumps(files,indent=2)+'\n')
 test=ChainCluster(a,'chain')
 try:test.run()
 except Exception as e:
  test.report.update(status='FAIL',failure=str(e),traceback=traceback.format_exc())
  try:test.snapshot('failure')
  except Exception as x:test.report['observation_error']=str(x)
 finally:
  for role in ROLES:
   for file in ('native.log','node.log'):
    try:(test.root/(role+'-'+file)).write_text(test.k('exec',role+'-0','--','cat','/state/'+file))
    except Exception:pass
   try:(test.root/(role+'.log')).write_text(test.k('logs',role+'-0'))
   except Exception:pass
  for kind in ('pods','pvcs','networkpolicies'):
   try:test.report[kind]=json.loads(test.k('get',kind,'-o','json'))
   except Exception:pass
  test.finish()
  if a.cleanup:test.k('delete','namespace',test.name,'--wait=false','--ignore-not-found=true')
 print(test.report['status'],test.report.get('failure',''));raise SystemExit(test.report['status']!='PASS')
if __name__=='__main__':main()
