import importlib.util,json,os,subprocess,time
from pathlib import Path
from fusion.contracts import canonical,digest,require
from integration.single_node.reference_ops import Operator
root=Path('/data/fusion-operator-pilot-release/qualification-private/workflows-14');packet=Path('/data/fusion-operator-pilot-release/distribution14');operator=Path('/data/fusion-operator-pilot-release/operator13')
require(digest((packet/'distribution.json').read_bytes())=='de39c9f69d8024a8fb793279165236953e2bc81254a79efae391fb468af0954d','CONFLICT')
plan=root/'go-initial/plan.json';values=root/'go-initial/values.yaml';artifact=packet/'go-provider/provider-image.json';chart=packet/'deploy/helm/omega-fusion'
require(digest(plan.read_bytes())=='4f0ab6fdea62c519f77536b491eb2d178228a0606409bc4c5ef00aa46bf6084d','CONFLICT')
op=Operator(root/'kubeconfig','default','omega-ref-pilot-go13');report=dict(status='RUNNING',namespace=op.namespace,source_manifest_sha256='3ee4c1af77ffc75f1b9e48790d3c8494e9a72ad668b85417779896b8bc46cbc2',plan_sha256=digest(plan.read_bytes()),distribution_sha256=digest((packet/'distribution.json').read_bytes()),additional_live_generations=0,steps=[])
def save():(root/'go-install-report.json').write_bytes(canonical(report))
save()
try:
 op.create();report['steps'].append('fresh-task-owned-namespace-created');save()
 secretcmd=[str(operator/'bin/fusion-create-secrets'),'--preview-values',str(values),'--kubeconfig',op.kubeconfig,'--context',op.context,'--namespace',op.namespace,'--directory',str(root/'go-secrets')]
 with (root/'go-secret-install.log').open('wb') as log:subprocess.run(secretcmd,check=True,stdout=log,stderr=subprocess.STDOUT,timeout=90)
 report['steps'].append('fresh-service-secrets-created');save()
 helper=packet/'examples/pilot_go_capacity.py';require(digest(helper.read_bytes())=='a3b7aeab738d594e11c802b158e8a2f2e92761a33c1f6c3c8a357630dc348bb2','CONFLICT')
 spec=importlib.util.spec_from_file_location('approved_go_capacity',helper);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 report['capacity_provision']=module.provision(op,plan,artifact,chart,root/'go-capacity-authority');save()
 command=['/snap/helm/current/helm','upgrade','--install','omega',str(chart),'-f',str(values),'--kubeconfig',op.kubeconfig,'--kube-context',op.context,'--namespace',op.namespace,'--wait','--timeout','5m']
 with (root/'go-helm-install.log').open('wb') as log:subprocess.run(command,check=True,stdout=log,stderr=subprocess.STDOUT,timeout=320)
 report['steps'].append('frozen-chart-installed');report['status']='PASS';save()
except BaseException as error:
 report.update(status='FAILED',failure=dict(type=type(error).__name__,detail=str(error)[:1000]));save();raise
print(json.dumps(dict(status=report['status'],namespace=op.namespace,additional_live_generations=0)))
