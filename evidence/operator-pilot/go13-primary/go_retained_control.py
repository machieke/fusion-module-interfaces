"""Separate finite owner-control window; no native runtime or session creation."""
import importlib.util,json,subprocess,time
from pathlib import Path
from fusion.contracts import canonical,digest,require
from integration.single_node.reference_ops import Operator,PYTHON
from examples.integrated_sustained import IntegratedRunner
from examples.pilot_go_provider import provider
root=Path('/data/fusion-operator-pilot-release/qualification-private/workflows-14');packet=Path('/data/fusion-operator-pilot-release/distribution14');plan=json.loads((root/'go-retained-control-plan.json').read_bytes());require(plan['source_sha256']==digest(Path(__file__).read_bytes()),'CONFLICT');deadline=plan['deadline_ms'];op=Operator(root/'kubeconfig','default','omega-ref-pilot-go13');out=root/'go-retained-control';out.mkdir(mode=0o700,exist_ok=False)
report=dict(status='RUNNING',profile=plan['profile'],identity=plan['identity'],started_ms=plan['started_ms'],deadline_ms=deadline,source_sha256=plan['source_sha256'],original_window_drain='NOT_COMPLETED',steps=[],new_native_inputs=0,additional_live_generations=0)
def save():(out/'report.json').write_bytes(canonical(report))
def action(name,fn):
 require(time.time()*1000<deadline,'DEADLINE_EXCEEDED');value=fn();report['steps'].append(dict(action=name,value=value));save();return value
save()
try:
 command=['/snap/helm/current/helm','upgrade','--install','omega',str(packet/'deploy/helm/omega-fusion'),'-f',str(root/'go-replacement/values.yaml'),'--kubeconfig',op.kubeconfig,'--kube-context',op.context,'--namespace',op.namespace,'--wait','--timeout','90s']
 with (out/'restart.log').open('wb') as log:subprocess.run(command,check=True,stdout=log,stderr=subprocess.STDOUT,timeout=min(100,(deadline-time.time()*1000)/1000))
 prior=json.loads((root/'go-replacement-recovery/native-onboarding/report.json').read_bytes());require(prior['status']=='PASS','CONFLICT');sid=prior['session'];job=prior['inspection']['job_id'];r=IntegratedRunner(op,out/'control',maximum_inputs=1)
 def events():
  script="""import json,sys
from pathlib import Path
from fusion.preview_inspect import Client
from fusion.contracts import require
cfg=json.loads(Path('/run/fusion/owner.json').read_bytes());t=cfg['native_sessions']['runtime_templates']['go-shared'];path=Path(t['directory'])/'inspection.json'
require(str(path)=='/run/fusion/templates/go-shared/inspection.json','UNAUTHORIZED')
client=Client(path);print(json.dumps({'events':client.events(sys.argv[1])}))"""
  return json.loads(op.k('exec','omega-agent-0','--',PYTHON,'-c',script,job,timeout=min(35,max(1,(deadline-time.time()*1000)/1000))))
 selected=action('selection-before',lambda:provider(r,'selected',session=sid));require(selected==prior['selected'],'CONFLICT')
 before=action('observe-before',lambda:r.call('omega-agent','observe',sid,'--content'));original_events=action('events-before-trusted-template',events)
 require(original_events=={'events':prior['provider_observation']['events']},'CONFLICT')
 action('drain',lambda:provider(r,'drain','go-shared-fusion-inspect-go','go-final-drain-13'))
 try:action('new-allocation',lambda:r.call('omega-agent','allocate',None,'--identity','go-drained-allocation-refusal-13','--template','go-shared'))
 except RuntimeError as error:require('NOT_AVAILABLE' in str(error),'CONFLICT');report['steps'].append(dict(action='new-allocation',error='NOT_AVAILABLE'));save()
 else:require(False,'CONFLICT')
 after=action('observe-after',lambda:r.call('omega-agent','observe',sid,'--content'));require(before==after,'CONFLICT');require(action('events-after-trusted-template',events)==original_events,'CONFLICT');require(action('selection-after',lambda:provider(r,'selected',session=sid))==selected,'CONFLICT')
 require(len(report['steps'])==8 and not r.report['inputs'],'CONFLICT')
 path=packet/'examples/pilot_go_capacity.py';spec=importlib.util.spec_from_file_location('capacity',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 value=module.observe(op,root/'go-replacement/plan.json',packet/'go-provider/provider-image.json',packet/'deploy/helm/omega-fusion',root/'go-capacity-authority',out/'capacity',deadline);expected=json.loads((root/'go-capacity-final02.json').read_bytes())['observations']['completed']['value'];require(value['capacity']==expected,'CONFLICT')
 report.update(status='PASS',completed_ms=int(time.time()*1000),retained_session_exact=True,retained_events_exact=True,retained_selection_exact=True,capacity_exact=True,capacity_report_sha256=digest((out/'capacity/report.json').read_bytes()),control_calls=8,capacity_calls=1);require(report['completed_ms']<deadline,'DEADLINE_EXCEEDED');save()
except BaseException as error:report.update(status='FAIL',failure=dict(type=type(error).__name__,code=getattr(error,'code',None),detail=str(error)[-1200:]));save();raise
finally:
 op.quiesce();report.update(quiesced=True,stopped_ms=int(time.time()*1000),cleanup_pods=len(json.loads(op.k('get','pods','-o','json'))['items']),retained_pvcs=len(json.loads(op.k('get','pvc','-o','json'))['items']));save()
print(json.dumps(dict(status=report['status'],new_native_inputs=0,additional_live_generations=0)))
