import json,time
from pathlib import Path
from unittest.mock import patch
from fusion.contracts import canonical,digest,require
from integration.single_node.reference_ops import Operator
from examples import pilot_go_provider as driver
from examples.pilot_network_edges import go_qualify
root=Path('/data/fusion-operator-pilot-release/qualification-private/workflows-14');packet=Path('/data/fusion-operator-pilot-release/distribution14');priorpath=root/'go-replacement-evidence/native-onboarding';prior=json.loads((priorpath/'report.json').read_bytes());native=json.loads((priorpath/'native/report.json').read_bytes());deadline=1793853080000;remaining=deadline/1000-time.time();require(remaining>240,'DEADLINE_EXCEEDED');end=time.monotonic()+remaining
require(prior['status']=='FAIL' and prior['draining_original']['state']=='draining' and not native['inputs'] and prior['selected'] and prior['session'],'CONFLICT')
class ProgrammeBound(driver.Runner):
 @property
 def end(self):return self._end
 @end.setter
 def end(self,value):self._end=min(value,end)
 def run(self,*args,**kwargs):
  require(time.monotonic()+120<self.end,'DEADLINE_EXCEEDED');return super().run(*args,**kwargs)
def resume(op,plan,artifact,directory,*,original=None):
 out=Path(directory);out.mkdir(parents=True,exist_ok=False);r=driver.Runner(op,out/'native',maximum_inputs=4);r.report=native;r.ids={'omega-agent':[prior['session']]};r.count=0;r.end=end
 report={k:v for k,v in prior.items() if k not in ('failure','status')};report.update(status='RUNNING',recovery_source_sha256=digest(Path(__file__).read_bytes()),resumed_failed_primary_sha256=digest((priorpath/'report.json').read_bytes()),same_allocated_session=True,programme_deadline_ms=deadline,maximum_new_native_inputs=4)
 def save():r.save();(out/'report.json').write_bytes(canonical(report))
 save();sid=prior['session'];old=prior['retained_before']['session'];old_view=prior['retained_before'];frozen=prior['old_selection']
 try:
  current=r.call('omega-agent','observe',sid,'--content');require(not current['inputs'] and driver.provider(r,'selected',session=sid)==prior['selected'],'CONFLICT')
  report['retirement_recovery_probe']=driver.provider(r,'probe','shared-fusion-execution','go13-expired-retirement-readiness-probe');save()
  report['retired_original']=driver.provider(r,'retire','shared-fusion-execution','go-onboarding-retire-original');save()
  try:r.call('omega-agent','submit',old,'--identity','old-selection-refused-new-work','--text','task-context','--assignment','synthetic-task')
  except RuntimeError as error:require('NOT_AVAILABLE' in str(error),'CONFLICT');report['old_new_input_refused']=True
  else:require(False,'CONFLICT')
  require(r.call('omega-agent','observe',old,'--content')['inputs']==old_view['inputs'],'CONFLICT')
  inspection=driver.consume(r,0,report,save);entry=r.report['inputs'][-1];occurrence=entry['observed']['result']['occurrences'][0]
  continuation=r.call('omega-agent','continuation',sid,'--occurrence',occurrence);require(continuation['status']=='return-ready' and continuation['native_consumption']['turn_captured'],'NOT_AVAILABLE');report['continuation']=continuation
  observed=driver.port_observation(op,sid,inspection['job_id'],True);report['provider_observation']=observed;require(observed['wrong_credential']['error']['code']=='UNAUTHORIZED','CONFLICT');save()
  old_pod=json.loads(op.k('get','pod','fusion-inspect-go-0','-o','json'))['metadata']['uid'];op.k('delete','pod','fusion-inspect-go-0','--wait=true',timeout=70);op.k('wait','--for=condition=Ready','pod/fusion-inspect-go-0','--timeout=90s',timeout=100)
  new_pod=json.loads(op.k('get','pod','fusion-inspect-go-0','-o','json'))['metadata']['uid'];require(new_pod!=old_pod,'CONFLICT');after=driver.port_observation(op,sid,inspection['job_id'],True);require(after==observed,'CONFLICT');report['provider_replacement']=dict(old_pod=old_pod,new_pod=new_pod,original_events_and_descriptor_exact=True,after=after);save()
  r.run('task-context');report['next_context']=driver.next_context(op,sid,inspection)
  duplicate=r.call('omega-agent','submit',sid,'--identity',entry['identity'],'--text',entry['command'],'--assignment','synthetic-task');require(duplicate['state']=='complete' and duplicate['deadline']==entry['accepted']['deadline'] and duplicate['accepted']==entry['accepted']['accepted'],'CONFLICT');require(r.call('omega-agent','continuation',sid,'--occurrence',occurrence)==continuation,'CONFLICT')
  report.update(duplicate_receipt=duplicate,capture_replayed_without_new_native_work=True,deadline_renewals=0,reservation_refunds=0)
  old_after=r.call('omega-agent','observe',old,'--content');require(old_after['inputs']==old_view['inputs'] and driver.provider(r,'selected',session=old)==frozen,'CONFLICT');report['retained_after']=old_after
  report['closures']=driver.close_consumed_sessions(r,sid,'go-onboarding-'+sid);report['old_closed']=r.call('omega-agent','close',old,'--identity','go-close-original-'+old)
  report.update(status='PASS',native_operator_inputs=r.count,native_report_sha256=digest((r.root/'report.json').read_bytes()));save()
 except BaseException as error:report.update(status='FAIL',failure=dict(type=type(error).__name__,detail=str(error)[-1500:]));raise
 finally:save()
 return report
op=Operator(root/'kubeconfig','default','omega-ref-pilot-go13')
with patch.object(driver,'Runner',ProgrammeBound),patch.object(driver,'qualify',resume):
 result=go_qualify(op,root/'go-replacement/plan.json',packet/'go-provider/provider-image.json',packet/'deploy/helm/omega-fusion',root/'go-replacement-recovery',root/'go-baseline',root/'go-capacity-authority',packet/'examples/pilot_go_capacity.py')
print(json.dumps(dict(status=result['status'],programme_deadline_ms=deadline,additional_live_generations=0)))
