import copy,json,signal,time
from pathlib import Path
from fusion.contracts import canonical,digest,require
from integration.single_node.reference_ops import Operator
from examples.pilot_recipe_chain import RecipeChain
R=Path('/data/fusion-operator-pilot-release/qualification-private/recipe-reference17');P=Path('/data/fusion-operator-pilot-release/distribution17')
plan=json.loads((R/'readback-followup-plan.json').read_bytes())
for path,sha in plan['inputs'].items():require(digest(Path(path).read_bytes())==sha,'CONFLICT')
require(digest(Path(__file__).read_bytes())==plan['source_sha256'],'CONFLICT')
prior=json.loads((R/'same-workflow-recovery/chain/report.json').read_bytes());deadline=prior['separately_approved_chain_deadline_ms']
require(deadline==plan['original_chain_deadline_ms'] and prior['final_continuation']['status']=='finalized' and prior['final_continuation']['submit_reservations']==1,'CONFLICT')
root=R/'readback-followup';root.mkdir(mode=0o700,exist_ok=False)
report=dict(profile='same-finalized-trace-bounded-readback-followup/1',status='RUNNING',start_ms=time.time_ns()//1000000,original_chain_deadline_ms=deadline,previous_failed_report_sha256=digest((R/'same-workflow-recovery/chain/report.json').read_bytes()),plan_sha256=digest((R/'readback-followup-plan.json').read_bytes()),attempts=[],additional_live_generations=0,additional_native_inputs=0,additional_submit_reservations=0,signatures=0)
def save():(root/'report.json').write_bytes(canonical(report))
def expired(*_):raise TimeoutError('original chain deadline expired; readback stops')
signal.signal(signal.SIGALRM,expired);signal.setitimer(signal.ITIMER_REAL,max(.001,(deadline-time.time()*1000)/1000));op=Operator(R/'kubeconfig','default','omega-ref-pilot-recipe17');save()
try:
 op.owned();op.k('scale','statefulset','fusion-storage','f1r3node','--replicas=1')
 for role in ('fusion-storage','f1r3node'):op.k('wait','--for=condition=Ready','pod/'+role+'-0','--timeout=120s',timeout=130)
 report['only_required_read_services']=json.loads(op.k('get','pods','-o','json'));require({p['metadata']['name'] for p in report['only_required_read_services']['items']}=={'fusion-storage-0','f1r3node-0'},'CONFLICT');save()
 for number in range(1,3):
  require(time.time_ns()//1000000<deadline,'DEADLINE_EXCEEDED')
  q=RecipeChain(op,R/'recipe-installed/values.yaml',P/'deploy/helm/omega-fusion',root/('attempt-'+str(number)))
  q.report={k:copy.deepcopy(v) for k,v in prior.items() if k not in ('status','failure','quiesced','observer_pod','independent_readback')}
  q.report.update(readback_only=True,additional_native_inputs=0,additional_chain_submit_reservations=0,readback_attempt=number)
  require(q.read('f1r3node','chain-identity.json')==prior['registration']['binding']['chain'],'CONFLICT');q.save()
  try:q.independent(P/'examples/preview_chain_observer.py');outcome='PASS'
  except BaseException as error:
   outcome='FAIL';q.report.update(status='FAIL',failure=dict(type=type(error).__name__,code=getattr(error,'code',None),detail=str(error)[-1000:]));q.save()
  report['attempts'].append(dict(number=number,status=outcome,report_sha256=digest((q.root/'report.json').read_bytes()),observed_ms=time.time_ns()//1000000));save()
  if outcome=='PASS':report['status']='PASS';break
 else:report['status']='FAIL'
 report['finished_ms']=time.time_ns()//1000000;save()
except BaseException as error:report.update(status='FAIL',failure=dict(type=type(error).__name__,code=getattr(error,'code',None),detail=str(error)[-1000:]));save();raise
finally:
 signal.setitimer(signal.ITIMER_REAL,0)
 try:op.quiesce();report['cleanup']=dict(pods=json.loads(op.k('get','pods','-o','json')),pvcs=json.loads(op.k('get','pvc','-o','json')),observed_ms=time.time_ns()//1000000)
 except BaseException as error:report['cleanup_failure']=dict(type=type(error).__name__,detail=str(error)[-1000:])
 save()
require(report['status']=='PASS','NOT_AVAILABLE')
