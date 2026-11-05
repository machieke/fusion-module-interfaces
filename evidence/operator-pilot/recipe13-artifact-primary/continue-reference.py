import json,time
from pathlib import Path
from fusion.contracts import canonical,digest,require
from examples.pilot_workflows import call,native_capture
from examples.integrated_sustained import IntegratedRunner
from integration.single_node.reference_ops import Operator
root=Path('/data/fusion-operator-pilot-release/qualification-private/workflows-14'); prior=json.loads((root/'reference-workflow-recovery/report.json').read_bytes());out=root/'reference-workflow-continuation';out.mkdir();op=Operator(str(root/'kubeconfig'),'default','omega-ref-pilot-recipe13');sid,wid,end=prior['session'],prior['workflow'],prior['original_deadline_ms'];r=IntegratedRunner(op,out/'native',maximum_inputs=1);r.ids['omega-agent']=[sid];r.end=time.monotonic()+max(0,(end-time.time()*1000)/1000)
report=dict(status='RUNNING',session=sid,workflow=wid,original_deadline_ms=end,source_sha256=digest(Path(__file__).read_bytes()),previous_sha256=digest((root/'reference-workflow-recovery/report.json').read_bytes()),observations=[],additional_live_generations=0)
def save():(out/'report.json').write_bytes(canonical(report));r.save()
save()
try:
 cur=call(op,sid,wid,'observe',{});require(cur['version']==2 and cur['reservations_spent']==1 and cur['deadline_ms']==end,'CONFLICT')
 for node in ('artifact','inspect'):
  require(time.time()*1000<end,'NOT_AVAILABLE');cur=call(op,sid,wid,'checkpoint',dict(identity='reference-review-'+node,version=cur['version'],reason='explicit exact retained full-result reference representation'))
  cp=cur['checkpoints'][-1];report.setdefault('checkpoints',[]).append(cp);save()
  cur=call(op,sid,wid,'decide',dict(checkpoint=cp['identity'],identity='reference-approve-'+node,binding_sha256=cp['binding_sha256'],action='approve'))
  for _ in range(64):
   require(time.time()*1000<end,'NOT_AVAILABLE');cur=call(op,sid,wid,'advance',dict(version=cur['version']));report['observations'].append(cur);save()
   if node in cur['steps'] and cur['steps'][node]['result_sha256']:break
   time.sleep(.4)
  else:require(False,'OVERLOADED')
 cur=call(op,sid,wid,'advance',dict(version=cur['version']));report['final']=cur
 final=r.call('omega-agent','observe',sid,'--content');report['native_session']=final;report['native_report_sha256']=native_capture(out,r,cur,final)
 require(cur['status']=='complete' and cur['reservations_spent']==3 and cur['deadline_ms']==end,'CONFLICT')
 report['status']='PASS';save()
except BaseException as e:report.update(status='FAIL',failure=dict(type=type(e).__name__,detail=str(e),code=getattr(e,'code',None)));save();raise
finally:save()
