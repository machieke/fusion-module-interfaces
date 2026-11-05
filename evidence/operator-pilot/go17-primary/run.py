"""One frozen current-source representative; unchanged native consume function."""
import json,signal,subprocess,time
from pathlib import Path
from fusion.contracts import canonical,digest,require
from integration.single_node.reference_ops import Operator,PYTHON
from integration.single_node.placement import verify_installed
from examples.integrated_sustained import IntegratedRunner
from examples.pilot_go_provider import consume,next_context,port_observation,provider
from examples.pilot_workflows import close_consumed_sessions
from examples.pilot_go_capacity import observe as capacity_observe
root=Path('/data/fusion-operator-pilot-release/qualification-private/go-reference17');packet=Path('/data/fusion-operator-pilot-release/distribution17');operator=Path('/data/fusion-operator-pilot-release/operator19')
plan=json.loads((root/'qualification-plan.json').read_bytes());require(plan['status']=='FROZEN_UNADMITTED' and plan['additional_live_generations']==0,'UNAUTHORIZED')
for filename,pin in plan['local_inputs'].items():require(digest(Path(filename).read_bytes())==pin,'CONFLICT')
require(not (root/'start.json').exists(),'CONFLICT');start=time.time_ns()//1000000;end=start+plan['maximum_programme_seconds']*1000
(root/'start.json').write_bytes(canonical(dict(start_ms=start,end_ms=end,plan_sha256=digest((root/'qualification-plan.json').read_bytes()),additional_live_generations=0)))
def expired(*_):raise TimeoutError('original frozen Go representative window expired')
signal.signal(signal.SIGALRM,expired);signal.setitimer(signal.ITIMER_REAL,(end-time.time()*1000)/1000)
op=Operator(root/'kubeconfig','default',plan['namespace']);report=dict(status='RUNNING',profile=plan['profile'],plan_sha256=digest((root/'qualification-plan.json').read_bytes()),source_sha256=digest(Path(__file__).read_bytes()),start_ms=start,end_ms=end,additional_live_generations=0);r=None

def save():
 if r is not None:r.save()
 (root/'report.json').write_bytes(canonical(report))

def retained_port(job):
 script='''import json,sys
from pathlib import Path
from fusion.preview_inspect import Client
from fusion.client import Peer
from fusion.contracts import require
cfg=json.loads(Path('/run/fusion/owner.json').read_bytes());template=cfg['native_sessions']['runtime_templates']['go-shared'];path=Path(template['directory'])/'inspection.json'
require(str(path)=='/run/fusion/templates/go-shared/inspection.json','UNAUTHORIZED')
client=Client(path);peer=Peer(client,client.cfg['scope'],'inspect-A');job=sys.argv[1]
print(json.dumps(dict(events=client.events(job),status=peer.status(job),result=peer.result(job))))'''
 return json.loads(op.k('exec','omega-agent-0','--',PYTHON,'-c',script,job,timeout=40))

save()
try:
 with (root/'install.log').open('xb') as log:subprocess.run([str(operator/'bin/python'),'-I',str(root/'install.py')],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=420)
 require(time.time_ns()//1000000+plan['native_window_seconds']*1000<end,'NOT_AVAILABLE')
 selected=json.loads((root/'selected/plan.json').read_bytes());artifact=packet/'go-provider/provider-image.json';report['preflight']=verify_installed(selected,op,{'inspect-go':artifact});save()
 r=IntegratedRunner(op,root/'native',maximum_inputs=4);r.end=time.monotonic()+plan['native_window_seconds'];report['native_end_ms']=time.time_ns()//1000000+plan['native_window_seconds']*1000;save()
 r.admit_selection('omega-agent-b','representative-recipient17');index=r.allocate('omega-agent','representative-go17','go-shared');sid=r.ids['omega-agent'][index]
 report.update(session=sid,selected=provider(r,'selected',session=sid));require('go-shared-fusion-inspect-go' in report['selected'],'CONFLICT');save()
 inspection=consume(r,index,report,save);entry=r.report['inputs'][-1];occurrence=entry['observed']['result']['occurrences'][0]
 current=r.call('omega-agent','continuation',sid,'--occurrence',occurrence);require(current['status']=='return-ready' and current['native_consumption']['turn_captured'],'NOT_AVAILABLE');report['continuation']=current
 report['provider_observation']=port_observation(op,sid,inspection['job_id']);save()
 r.run('task-context',session=index);report['next_context']=next_context(op,sid,inspection)
 duplicate=r.call('omega-agent','submit',sid,'--identity',entry['identity'],'--text',entry['command'],'--assignment','synthetic-task');require(duplicate['state']=='complete' and duplicate['deadline']==entry['accepted']['deadline'] and duplicate['accepted']==entry['accepted']['accepted'],'CONFLICT');report['duplicate_receipt']=duplicate
 require(r.call('omega-agent','continuation',sid,'--occurrence',occurrence)==current,'CONFLICT');before=retained_port(inspection['job_id']);require(before['result']==inspection['inspection'] and before['status']['execution']=='succeeded','CONFLICT');report['retained_port_before']=before;save()
 report['closure']=close_consumed_sessions(r,sid,'go-representative17');captured=r.call('omega-agent','observe',sid,'--content');report['closed_capture']=captured;save()
 report['drain']=provider(r,'drain','go-shared-fusion-inspect-go','representative-drain17');save()
 try:r.call('omega-agent','allocate',None,'--identity','representative-drained-allocation17','--template','go-shared')
 except RuntimeError as error:require('NOT_AVAILABLE' in str(error),'CONFLICT');report['new_selection_refused']='NOT_AVAILABLE'
 else:require(False,'CONFLICT')
 after=retained_port(inspection['job_id']);require(after==before,'CONFLICT');require(r.call('omega-agent','observe',sid,'--content')==captured,'CONFLICT');require(provider(r,'selected',session=sid)==report['selected'],'CONFLICT');report['retained_port_after']=after;save()
 report['capacity']=capacity_observe(op,root/'selected/plan.json',artifact,packet/'deploy/helm/omega-fusion',root/'go-capacity-authority',root/'capacity',min(end,time.time_ns()//1000000+60000));save()
 require(r.count==4 and time.time_ns()//1000000<end,'CONFLICT');report.update(status='PASS',finished_ms=time.time_ns()//1000000,native_report_sha256=digest((root/'native/report.json').read_bytes()),selected_native_inputs=4,internal_native_inputs=2,new_effects_after_drain=0,original_receipts_retained=True,deadlines_renewed=0,reservations_refunded=0);save()
except BaseException as error:report.update(status='FAIL',failure=dict(type=type(error).__name__,code=getattr(error,'code',None),detail=str(error)[-1400:]));save();raise
finally:
 signal.setitimer(signal.ITIMER_REAL,0)
 try:op.quiesce();report['cleanup']=dict(pods=json.loads(op.k('get','pods','-o','json')),pvcs=json.loads(op.k('get','pvc','-o','json')),observed_ms=time.time_ns()//1000000)
 except BaseException as error:report['cleanup_failure']=dict(type=type(error).__name__,detail=str(error)[-1000:])
 save()
