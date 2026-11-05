"""The still-unexecuted capacity read, within the same fixed control window."""
import importlib.util,json,subprocess,time
from pathlib import Path
from fusion.contracts import canonical,digest,require
from integration.single_node.reference_ops import Operator
root=Path('/data/fusion-operator-pilot-release/qualification-private/workflows-14');packet=Path('/data/fusion-operator-pilot-release/distribution14');plan=json.loads((root/'go-retained-control-plan.json').read_bytes());deadline=plan['deadline_ms'];op=Operator(root/'kubeconfig','default','omega-ref-pilot-go13');out=root/'go-retained-capacity';out.mkdir(mode=0o700,exist_ok=False)
prior=json.loads((root/'go-retained-control/report.json').read_bytes());require(prior['status']=='FAIL' and prior['failure']['code']=='INVALID_ARGUMENT' and len(prior['steps'])==8 and not (root/'go-retained-control/capacity').exists(),'CONFLICT')
report=dict(status='RUNNING',source_sha256=digest(Path(__file__).read_bytes()),same_control_window=plan['identity'],deadline_ms=deadline,started_ms=int(time.time()*1000),original_failed_control_report_sha256=digest((root/'go-retained-control/report.json').read_bytes()),control_actions_repeated=0,new_native_inputs=0,additional_live_generations=0)
def save():(out/'report.json').write_bytes(canonical(report))
save()
try:
 require(time.time()*1000<deadline,'DEADLINE_EXCEEDED');cmd=['/snap/helm/current/helm','upgrade','--install','omega',str(packet/'deploy/helm/omega-fusion'),'-f',str(root/'go-replacement/values.yaml'),'--kubeconfig',op.kubeconfig,'--kube-context',op.context,'--namespace',op.namespace,'--wait','--timeout','60s']
 with (out/'restart.log').open('wb') as log:subprocess.run(cmd,check=True,stdout=log,stderr=subprocess.STDOUT,timeout=min(70,max(1,(deadline-time.time()*1000)/1000)))
 path=packet/'examples/pilot_go_capacity.py';spec=importlib.util.spec_from_file_location('capacity',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 value=module.observe(op,root/'go-replacement/plan.json',packet/'go-provider/provider-image.json',packet/'deploy/helm/omega-fusion',root/'go-capacity-authority',out/'capacity',min(deadline,int(time.time()*1000)+90000));expected=json.loads((root/'go-capacity-final02.json').read_bytes())['observations']['completed']['value'];require(value['capacity']==expected,'CONFLICT');report.update(status='PASS',capacity_calls=1,capacity_exact=True,capacity_report_sha256=digest((out/'capacity/report.json').read_bytes()),completed_ms=int(time.time()*1000));require(report['completed_ms']<deadline,'DEADLINE_EXCEEDED');save()
except BaseException as error:report.update(status='FAIL',failure=dict(type=type(error).__name__,code=getattr(error,'code',None),detail=str(error)[-1000:]));save();raise
finally:
 op.quiesce();report.update(quiesced=True,stopped_ms=int(time.time()*1000),cleanup_pods=len(json.loads(op.k('get','pods','-o','json'))['items']),retained_pvcs=len(json.loads(op.k('get','pvc','-o','json'))['items']));save()
print(json.dumps(dict(status=report['status'],additional_live_generations=0)))
