import json,time
from pathlib import Path
from fusion.contracts import canonical,digest
from integration.single_node.reference_ops import Operator
from examples.pilot_workflows import call
from examples.integrated_sustained import IntegratedRunner
root=Path('/data/fusion-operator-pilot-release/qualification-private/workflows-14');prior=json.loads((root/'reference-workflow-continuation/report.json').read_bytes());op=Operator(str(root/'kubeconfig'),'default','omega-ref-pilot-recipe13');out=root/'reference-final-observation';out.mkdir();r=IntegratedRunner(op,out/'native',maximum_inputs=1);report=dict(status='RUNNING',source_sha256=digest(Path(__file__).read_bytes()),additional_native_inputs=0,additional_workflow_advances=0,additional_live_generations=0)
try:
 report['workflow']=call(op,prior['session'],prior['workflow'],'observe',{});report['session']=r.call('omega-agent','observe',prior['session'],'--content');report['observed_ms']=time.time_ns()//1000000;report['status']='OBSERVED_ONLY'
finally:
 (out/'report.json').write_bytes(canonical(report));op.quiesce();report['quiesced']=True;report['pods']=json.loads(op.k('get','pods','-o','json'));report['pvcs']=json.loads(op.k('get','pvc','-o','json'));(out/'report.json').write_bytes(canonical(report))
