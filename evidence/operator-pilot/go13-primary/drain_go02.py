"""Finite post-completion Registry drain, normal APIs only; no native input."""
import argparse,json,time
from pathlib import Path
from fusion.contracts import canonical,digest,require
from integration.single_node.reference_ops import Operator
from examples.integrated_sustained import IntegratedRunner
from examples.pilot_go_provider import provider,port_observation
p=argparse.ArgumentParser();p.add_argument('--kubeconfig',required=True);p.add_argument('--plan',required=True);p.add_argument('--replacement',required=True);p.add_argument('--output',required=True);a=p.parse_args()
planpath=Path(a.plan);raw=planpath.read_bytes();require(digest(raw)=='b4339920a710868e25f9523602ced1e9cfeecb59e2b019367fe49e5097cae8f7','CONFLICT');plan=json.loads(raw)
priorpath=Path(a.replacement)/'report.json';priorraw=priorpath.read_bytes();prior=json.loads(priorraw)
require(prior['status']=='PASS' and prior['stage']=='replacement' and prior['template']=='go-shared','CONFLICT')
root=Path(a.output);root.mkdir(mode=0o700,parents=True,exist_ok=False)
op=Operator(a.kubeconfig,'default',plan['namespace']);r=IntegratedRunner(op,root/'control',maximum_inputs=1)
end=time.monotonic()+min(plan['maximum_observer_seconds'],max(0,1793853080-time.time()));sid=prior['session'];job=prior['inspection']['job_id']
report=dict(status='RUNNING',profile=plan['profile'],namespace=op.namespace,plan_sha256=digest(raw),replacement_report_sha256=digest(priorraw),source_sha256=digest(Path(__file__).read_bytes()),steps=[],native_operator_inputs=0,additional_live_generations=0)
def save():(root/'report.json').write_bytes(canonical(report))
def action(name,fn):
 require(time.monotonic()<end,'DEADLINE_EXCEEDED')
 value=fn();report['steps'].append(dict(action=name,value=value));save();return value
save()
try:
 before=action('observe-before',lambda:r.call('omega-agent','observe',sid,'--content'))
 events=action('events-before',lambda:port_observation(op,sid,job))
 receipt=action('drain',lambda:provider(r,'drain',plan['selected_provider'],'go-final-drain-13'))
 try:
  action('new-allocation',lambda:r.call('omega-agent','allocate',None,'--identity','go-drained-allocation-refusal-13','--template','go-shared'))
 except RuntimeError as error:
  require('NOT_AVAILABLE' in str(error),'CONFLICT')
  report['steps'].append(dict(action='new-allocation',error='NOT_AVAILABLE',detail=str(error)[-1500:]));save()
 else:require(False,'CONFLICT')
 after=action('observe-after',lambda:r.call('omega-agent','observe',sid,'--content'));require(after==before,'CONFLICT')
 later=action('events-after',lambda:port_observation(op,sid,job));require(later==events,'CONFLICT')
 selected=action('selection-after',lambda:provider(r,'selected',session=sid));require(selected==prior['selected'],'CONFLICT')
 require(len(report['steps'])==plan['maximum_control_actions'] and not r.report['inputs'],'CONFLICT')
 report.update(status='PASS',retained_session_exact=True,provider_events_exact=True,retained_selection_exact=True,new_selection='REFUSED_NOT_AVAILABLE',deadline_renewals=0,reservation_refunds=0)
except BaseException as error:
 report.update(status='FAIL',failure=dict(type=type(error).__name__,code=getattr(error,'code',None),detail=str(error)[-1500:]));raise
finally:save()
print(json.dumps(dict(status=report['status'],native_operator_inputs=0,additional_live_generations=0)))
