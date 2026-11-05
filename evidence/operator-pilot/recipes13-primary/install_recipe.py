import json,subprocess
from pathlib import Path
import yaml
from fusion.contracts import canonical,digest,require
from integration.single_node.reference_ops import Operator
from integration.single_node.placement import freeze,compile
root=Path('/data/fusion-operator-pilot-release/qualification-private/workflows-14');packet=Path('/data/fusion-operator-pilot-release/distribution14');operator=Path('/data/fusion-operator-pilot-release/operator13')
require(digest((packet/'distribution.json').read_bytes())=='de39c9f69d8024a8fb793279165236953e2bc81254a79efae391fb468af0954d','CONFLICT')
prospective=root/'recipe-chain';require(digest((prospective/'plan.json').read_bytes())=='29bcabd999c52ecb818636a15af8568c5907ee3f02c72ff51c252adf4c212e07','CONFLICT')
selected=root/'recipe-installed';selected.mkdir(mode=0o700,exist_ok=False);values=selected/'values.yaml';values.write_bytes((prospective/'values.yaml').read_bytes());chart=packet/'deploy/helm/omega-fusion'
op=Operator(root/'kubeconfig','default','omega-ref-pilot-recipe13');report=dict(status='RUNNING',namespace=op.namespace,source_manifest_sha256='3ee4c1af77ffc75f1b9e48790d3c8494e9a72ad668b85417779896b8bc46cbc2',prospective_plan_sha256=digest((prospective/'plan.json').read_bytes()),distribution_sha256=digest((packet/'distribution.json').read_bytes()),additional_live_generations=0,steps=[])
def save():(root/'recipe-install-report.json').write_bytes(canonical(report))
save()
try:
 op.create();report['steps'].append('fresh-task-owned-namespace-created');save()
 command=[str(operator/'bin/fusion-create-secrets'),'--preview-values',str(values),'--kubeconfig',op.kubeconfig,'--context',op.context,'--namespace',op.namespace,'--directory',str(root/'recipe-secrets')]
 with (root/'recipe-secret-install.log').open('wb') as log:subprocess.run(command,check=True,stdout=log,stderr=subprocess.STDOUT,timeout=90)
 value=yaml.safe_load(values.read_text());original=yaml.safe_load((prospective/'values.yaml').read_text());public=json.loads((root/'recipe-secrets/chain-public.json').read_bytes());require(set(public)=={'public_key','wallet_address'},'CONFLICT');original['preview']['chain'].update(public);require(value==original,'CONFLICT')
 require(value['preview']['chain']['nodeEnabled'] is False and not value['preview']['chain']['isolationVerified'],'UNAUTHORIZED')
 images=json.loads((prospective/'images.json').read_bytes());plan=freeze(chart,op.namespace,value,images);compile(plan,chart)
 (selected/'plan.json').write_bytes(canonical(plan));(selected/'images.json').write_bytes(canonical(images));report.update(installed_plan_sha256=digest(canonical(plan)),public_identity_bound_before_node_pvc=True,allowed_changes=['preview.chain.public_key','preview.chain.wallet_address'],values_sha256=digest(values.read_bytes()));report['steps'].append('fresh-unfunded-public-identity-bound-and-plan-frozen');save()
 command=['/snap/helm/current/helm','upgrade','--install','omega',str(chart),'-f',str(values),'--kubeconfig',op.kubeconfig,'--kube-context',op.context,'--namespace',op.namespace,'--wait','--timeout','5m']
 with (root/'recipe-helm-install.log').open('wb') as log:subprocess.run(command,check=True,stdout=log,stderr=subprocess.STDOUT,timeout=320)
 report['steps'].append('frozen-chart-installed-with-node-disabled');report['status']='PASS';save()
except BaseException as error:
 report.update(status='FAILED',failure=dict(type=type(error).__name__,detail=str(error)[-1000:]));save();raise
print(json.dumps(dict(status=report['status'],namespace=op.namespace,installed_plan_sha256=report['installed_plan_sha256'],additional_live_generations=0)))
