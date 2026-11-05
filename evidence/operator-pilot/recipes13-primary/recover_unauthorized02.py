import base64,json,secrets,time,uuid
from pathlib import Path
from fusion.contracts import canonical,digest,require
from integration.single_node.reference_ops import Operator
from integration.single_node.preview_recovery_qualification import Recovery
from examples.integrated_sustained import IntegratedRunner
from examples.pilot_workflows import call,native_capture,close_consumed_sessions
root=Path('/data/fusion-operator-pilot-release/qualification-private/workflows-14');old=json.loads((root/'workflow-cases/unauthorized/report.json').read_bytes());out=root/'workflow-cases/unauthorized-recovery02';out.mkdir(exist_ok=False)
report={'status':'RUNNING','original_report_sha256':digest((root/'workflow-cases/unauthorized/report.json').read_bytes()),'source_sha256':digest(Path(__file__).read_bytes()),'original_deadline_ms':old['accepted']['deadline_ms'],'new_sessions':0,'new_workflows':0,'deadline_renewals':0,'additional_live_generations':0,'steps':[]}
def save():(out/'report.json').write_bytes(canonical(report))
op=Operator(root/'kubeconfig','default','omega-ref-pilot-recipe13');r=IntegratedRunner(op,out/'native',maximum_inputs=1);sid=old['session'];wid=old['workflow'];q=Recovery.__new__(Recovery);q.op=op;prior=None;changed=False
try:
 save();op.owned();require(time.time()*1000+150000<report['original_deadline_ms'],'NOT_AVAILABLE')
 cur=call(op,sid,wid,'observe',{});require(cur['deadline_ms']==report['original_deadline_ms'] and cur['reservations_spent']==2 and len(cur['steps'])==2,'CONFLICT');report['before']=cur;save()
 secret=json.loads(op.k('get','secret','fusion-storage-tls-auth','-o','json'));prior={k:secret['data'][k] for k in ('caller-token','caller-A-token')};require(len(set(prior.values()))==1,'CONFLICT')
 new=base64.b64encode(secrets.token_hex(32).encode()).decode()
 for k in prior:secret['data'][k]=new
 changed=True;op.k('replace','-f','-',data=json.dumps(secret));report['fault_replacement']=q.replace(['fusion-storage']);save()
 held=call(op,sid,wid,'advance',{'version':cur['version']});report['hold']=held;save();require(held['status']=='prerequisite-held' and held['reservations_spent']==2 and held['latest_prerequisites']['observations'][0]['state']=='UNAUTHORIZED','CONFLICT')
 restored=json.loads(op.k('get','secret','fusion-storage-tls-auth','-o','json'))
 for k,v in prior.items():restored['data'][k]=v
 op.k('replace','-f','-',data=json.dumps(restored));report['restoration']=q.replace(['fusion-storage']);changed=False;save()
 require(time.time()*1000+120000<report['original_deadline_ms'],'NOT_AVAILABLE')
 cur=call(op,sid,wid,'checkpoint',{'identity':'operator-review','version':cur['version'],'reason':'explicit bounded follow-up review'});cp=cur['checkpoints'][-1];report['checkpoint']=cp;save()
 cur=call(op,sid,wid,'decide',{'checkpoint':cp['identity'],'identity':'operator-decision','binding_sha256':cp['binding_sha256'],'action':'approve'})
 for i in range(128):
  require(time.time()*1000<report['original_deadline_ms'],'NOT_AVAILABLE')
  if cur['status']=='complete':break
  cur=call(op,sid,wid,'advance',{'version':cur['version']});report['steps'].append(cur);save();time.sleep(.5)
 require(cur['status']=='complete' and cur['deadline_ms']==report['original_deadline_ms'] and cur['reservations_spent']==3,'CONFLICT');report['final']=cur
 observed=r.call('omega-agent','observe',sid,'--content');report['native_session']=observed;report['native_report_sha256']=native_capture(out,r,cur,observed);report['closure']=close_consumed_sessions(r,sid,wid);report['status']='PASS';save()
except BaseException as e:
 report.update(status='FAIL',failure={'type':type(e).__name__,'code':getattr(e,'code',None),'detail':str(e)[-1200:]});save();raise
finally:
 if changed:
  restored=json.loads(op.k('get','secret','fusion-storage-tls-auth','-o','json'))
  for k,v in prior.items():restored['data'][k]=v
  op.k('replace','-f','-',data=json.dumps(restored));report['restoration']=q.replace(['fusion-storage']);report['restored_on_failure']=True
 report['finished_ms']=time.time_ns()//1000000;r.save();save()
