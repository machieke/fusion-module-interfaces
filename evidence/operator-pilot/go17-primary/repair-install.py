import json,subprocess,time,yaml
from pathlib import Path
from fusion.contracts import canonical,digest,require
from integration.single_node.reference_ops import Operator
r=Path('/data/fusion-operator-pilot-release/qualification-private/go-reference17');packet=Path('/data/fusion-operator-pilot-release/distribution17');end=json.loads((r/'start.json').read_bytes())['end_ms'];require(time.time_ns()//1000000<end,'DEADLINE_EXCEEDED');op=Operator(r/'kubeconfig','default','omega-ref-pilot-go17')
old=yaml.safe_load((r/'selected/values.yaml').read_text());new=yaml.safe_load((r/'corrected-selection/values.yaml').read_text());expected=json.loads(json.dumps(old));expected['preview']['sustained']['provider_registry']['pins']['fusion-inspect-go']=dict(image='e2f7505e2ae6d6e3038f5049cfd2a181e3add14db98b388dd05ba8b7ded859cc',source='738bdb6ad57aa939545400f3074283f68a9b5343d1d6665a3a5313fd4a44e53a');require(new==expected,'CONFLICT')
z=json.loads((r/'zero-observation.json').read_bytes());require(z['status']=='PASS' and all(x['database_exists'] is False for x in z['roles'].values()),'CONFLICT');op.owned();require(not json.loads(op.k('get','pods','-o','json'))['items'],'CONFLICT')
report=dict(status='RUNNING',source_sha256=digest(Path(__file__).read_bytes()),zero_observation_sha256=digest((r/'zero-observation.json').read_bytes()),original_end_ms=end,changed=['preview.sustained.provider_registry.pins.fusion-inspect-go'],old_values_sha256=digest((r/'selected/values.yaml').read_bytes()),new_values_sha256=digest((r/'corrected-selection/values.yaml').read_bytes()),additional_native_inputs=0,additional_live_generations=0)
def save():(r/'go-selection-repair-install-report.json').write_bytes(canonical(report))
save()
try:
 with (r/'go-selection-repair-helm.log').open('xb') as log:subprocess.run(['/snap/helm/current/helm','upgrade','omega',str(packet/'deploy/helm/omega-fusion'),'-f',str(r/'corrected-selection/values.yaml'),'--kubeconfig',op.kubeconfig,'--kube-context',op.context,'--namespace',op.namespace,'--wait','--timeout','180s'],check=True,stdout=log,stderr=subprocess.STDOUT,timeout=min(190,(end-time.time()*1000)/1000))
 report['status']='PASS';save()
except BaseException as error:report.update(status='FAIL',failure=dict(type=type(error).__name__,detail=str(error)[-1000:]));save();raise
