import copy,json,signal,subprocess,time
from pathlib import Path
from unittest.mock import patch
from fusion.contracts import canonical,digest,require
from fusion.workflow_recipes import native_object
from integration.single_node.reference_ops import Operator
from examples.integrated_sustained import IntegratedRunner
from examples.pilot_workflows import call,native_capture
from examples.pilot_network_edges import chain_qualify
from examples import pilot_recipe_chain
ROOT=Path('/data/fusion-operator-pilot-release/qualification-private/recipe-reference17')
PACKET=Path('/data/fusion-operator-pilot-release/distribution17')
PLAN=json.loads((ROOT/'continuation-plan.json').read_bytes())
for path,sha in PLAN['inputs'].items():require(digest(Path(path).read_bytes())==sha,'CONFLICT')
require(digest(Path(__file__).read_bytes())==PLAN['source_sha256'],'CONFLICT')
END=PLAN['original_programme_end_ms'];require(time.time_ns()//1000000<PLAN['qualification_end_ms'],'DEADLINE_EXCEEDED')
OUT=ROOT/'same-workflow-recovery';OUT.mkdir(mode=0o700,exist_ok=False)
report=dict(status='RUNNING',plan_sha256=digest((ROOT/'continuation-plan.json').read_bytes()),started_ms=time.time_ns()//1000000,original_programme_end_ms=END,additional_live_generations=0)
def save():(OUT/'programme-report.json').write_bytes(canonical(report))
def expired(*_):raise TimeoutError('original programme end; no renewal')
signal.signal(signal.SIGALRM,expired);signal.setitimer(signal.ITIMER_REAL,max(.001,(END-time.time()*1000)/1000))
op=Operator(ROOT/'kubeconfig','default','omega-ref-pilot-recipe17');save()
def resume_qualify(op,directory,recipe,*,retain_for_chain=False,representation='full-projection'):
 require(recipe=='approved-artifact-delivery/1' and retain_for_chain and representation=='reference-document','CONFLICT')
 old=json.loads((ROOT/'chain/registered-recipe/report.json').read_bytes());native=json.loads((ROOT/'chain/registered-recipe/native/report.json').read_bytes())
 root=Path(directory);root.mkdir(parents=True,exist_ok=False);r=IntegratedRunner(op,root/'native',maximum_inputs=12)
 r.report=native;r.ids['omega-agent']=[old['session']];r.count=len(native['inputs']);r.end=time.monotonic()+(PLAN['qualification_end_ms']-time.time()*1000)/1000
 new=copy.deepcopy(old);new.pop('failure',None);new.update(status='RUNNING',previous_failed_report_sha256=digest((ROOT/'chain/registered-recipe/report.json').read_bytes()),continuation_plan_sha256=digest((ROOT/'continuation-plan.json').read_bytes()),new_control_observations=[])
 def snap():r.save();(root/'report.json').write_bytes(canonical(new))
 snap();sid,wid=old['session'],old['workflow'];before=old['observations'][-1]['steps'];current=call(op,sid,wid,'observe',{})
 require(current['version']==2 and current['reservations_spent']==2 and current['steps']==before and current['deadline_ms']==PLAN['workflow_deadline_ms'],'CONFLICT')
 matches=[x for x in current['checkpoints'] if x['identity']=='bounded-review'];require(len(matches)==1,'CONFLICT');cp=matches[0]
 require(cp['binding']['identity']=='bounded-review' and cp['binding']['node']=='inspect' and cp['binding']['version']==2 and cp['decision'] is None,'CONFLICT')
 new['checkpoint']=cp;new['recovery_before']=current;snap()
 current=call(op,sid,wid,'decide',dict(checkpoint='bounded-review',identity='approve-bounded-suffix',binding_sha256=cp['binding_sha256'],action='approve'))
 new['exact_checkpoint_decision']=current;snap();count=len(old['observations'])
 while current['status']!='complete':
  require(count<192 and time.time_ns()//1000000<PLAN['qualification_end_ms'],'DEADLINE_EXCEEDED');count+=1
  try:current=call(op,sid,wid,'advance',dict(version=2))
  except RuntimeError as error:
   new.setdefault('new_control_failures',[]).append(dict(drive=count,detail=str(error)[-1000:]));current=call(op,sid,wid,'observe',{})
  new['new_control_observations'].append(current);snap();time.sleep(.5)
 require(current['reservations_spent']==3 and current['deadline_ms']==PLAN['workflow_deadline_ms'] and all(current['steps'][k]==v for k,v in before.items()),'CONFLICT')
 final=r.call('omega-agent','observe',sid,'--content');captured=next(x for x in final['inputs'] if x['id']==current['steps']['inspect']['input_id'])
 require(captured['state']=='complete' and captured['result'] is not None,'CONFLICT');result=native_object(captured['result'])
 require(result['status']=='INSPECTED_ARTIFACT' and result['caller_acknowledged'] is True and result['chain']=='NOT_SUBMITTED','CONFLICT')
 new.update(status='PASS',final=current,native_session=final,evidence=dict(inspection=result,chain='NOT_SUBMITTED_WITHOUT_SEPARATE_EXACT_RESULT_APPROVAL'),explicit_drives=count,original_results_unchanged=True,deadline_renewals=0,reservation_refunds=0,native_report_sha256=native_capture(root,r,current,final),session_closure='RETAINED_FOR_SEPARATE_EXACT_RESULT_CHAIN_CONTINUATION');snap();return new
try:
 op.owned()
 with (OUT/'helm-resume.log').open('wb') as log:subprocess.run(['/snap/helm/current/helm','upgrade','omega',str(PACKET/'deploy/helm/omega-fusion'),'-f',str(ROOT/'recipe-installed/values.yaml'),'--kubeconfig',op.kubeconfig,'--kube-context',op.context,'--namespace',op.namespace,'--wait','--timeout','150s'],check=True,stdout=log,stderr=subprocess.STDOUT,timeout=160)
 with patch.object(pilot_recipe_chain,'qualify',resume_qualify):
  value=chain_qualify(op,ROOT/'recipe-installed/plan.json',ROOT/'recipe-installed/values.yaml',PACKET/'deploy/helm/omega-fusion',OUT/'chain',PACKET/'examples/preview_chain_observer.py',representation='reference-document')
 report.update(status=value['status'],chain_report_sha256=digest((OUT/'chain/report.json').read_bytes()),finished_ms=time.time_ns()//1000000);save()
except BaseException as error:report.update(status='FAIL',failure=dict(type=type(error).__name__,code=getattr(error,'code',None),detail=str(error)[-1500:]));save();raise
finally:
 signal.setitimer(signal.ITIMER_REAL,0)
 try:op.quiesce();report['cleanup']=dict(pods=json.loads(op.k('get','pods','-o','json')),pvcs=json.loads(op.k('get','pvc','-o','json')),observed_ms=time.time_ns()//1000000)
 except BaseException as error:report['cleanup_failure']=dict(type=type(error).__name__,detail=str(error)[-1000:])
 save()
