"""Discoverable operator surface for the bounded single-node distribution.

All cluster access requires explicit kubeconfig/context and task namespace.
Qualification and live execution are separate commands and authorities.
"""
import argparse,json,subprocess,sys
from pathlib import Path
from fusion.contracts import require
from .reference_ops import Operator,PYTHON
from .reference_campaign import install,prepare,freeze,run_live
ROOT=Path(__file__).resolve().parents[2]
PROFILES=('deterministic','memory','workflow','cognitive','chain','live')
def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('action',choices=('preflight','build','verify-artifacts','import','install','prepare-corpus','qualify','status','diagnose','observe','backup','restore','upgrade','freeze-campaign','run-live','stop','cleanup'))
 p.add_argument('--kubeconfig');p.add_argument('--context');p.add_argument('--namespace');p.add_argument('--release',default='omega');p.add_argument('--profile',choices=PROFILES);p.add_argument('--profiles',type=Path);p.add_argument('--chart',type=Path,default=ROOT/'deploy/helm/omega-fusion');p.add_argument('--directory',type=Path);p.add_argument('--manifest');p.add_argument('--image-manifest');p.add_argument('--archive');p.add_argument('--container');p.add_argument('--tag');p.add_argument('--scenarios',nargs='+');p.add_argument('--approval');p.add_argument('--offline-model',type=Path);p.add_argument('--source-package');p.add_argument('--campaign-id');p.add_argument('--fenced',action='store_true');p.add_argument('--preview',action='store_true');p.add_argument('--delete-synthetic',action='store_true');a=p.parse_args()
 if a.action=='build':
  from .reference_build import build
  print(json.dumps(build(a.directory,a.tag),indent=2));return
 if a.action=='verify-artifacts':
  from .reference_artifacts import verify
  print(json.dumps(verify(a.manifest),indent=2));return
 require(a.kubeconfig and a.context and a.namespace,'INVALID_ARGUMENT');op=Operator(a.kubeconfig,a.context,a.namespace,a.release)
 if a.action=='preflight':result=op.preflight()
 elif a.action=='import':
  op.preflight();require(a.container and a.image_manifest and a.archive,'INVALID_ARGUMENT')
  result=op.command([sys.executable,str(ROOT/'deploy/single-node/import_workflow_images.py'),'--container',a.container,'--manifest',a.image_manifest,'--archive',a.archive],timeout=600)
 elif a.action in ('install','upgrade'):
  require(a.profile and a.profiles,'INVALID_ARGUMENT');require(a.profile!='live','UNAUTHORIZED')
  values=a.profiles/(a.profile+'.yaml');require(values.is_file(),'NOT_AVAILABLE')
  if a.action=='install':
   require(a.directory,'INVALID_ARGUMENT');op.create();mode={'memory':['--memory'],'workflow':['--workflow'],'cognitive':['--reference'],'chain':['--chain'],'deterministic':[]}[a.profile]
   op.command([sys.executable,str(ROOT/'deploy/single-node/create_secrets.py'),*mode,'--kubeconfig',op.kubeconfig,'--context',op.context,'--namespace',op.namespace,'--directory',str(a.directory.resolve()/'private-secrets')])
   if a.profile=='chain':
    import yaml
    v=yaml.safe_load(values.read_text());v['reference']['chain'].update(json.loads((a.directory/'private-secrets/chain-public.json').read_text()));values=a.directory/'chain-values.json';values.write_text(json.dumps(v))
  else:op.owned()
  # Secrets are independently provisioned by create_secrets.py or the operator;
  # install cannot silently mint new identity during an upgrade.
  result=install(op,a.chart.resolve(),values.resolve())
 elif a.action=='prepare-corpus':
  require(a.profile=='live' and a.profiles and a.directory and a.offline_model,'INVALID_ARGUMENT')
  result=prepare(op,a.directory.resolve(),a.profiles/'workflow.yaml',a.chart.resolve(),a.offline_model.resolve())
 elif a.action=='qualify':
  require(a.scenarios and a.profiles and a.directory,'INVALID_ARGUMENT')
  command=[sys.executable,'-m','integration.single_node.reference_qualification','--kubeconfig',op.kubeconfig,'--context',a.context,'--prefix',a.namespace,'--output',str(a.directory),'--profiles',str(a.profiles),*a.scenarios]
  raise SystemExit(subprocess.run(command).returncode)
 elif a.action in ('status','diagnose','observe'):
  op.owned();roles=[x['metadata']['name'] for x in op.workloads()];result={}
  for role in roles:
   try:result[role]=json.loads(op.k('exec',role+'-0','--',PYTHON,'-m','integration.single_node.diagnostics'))
   except Exception as e:result[role]=dict(observation='NOT_AVAILABLE',detail=str(e)[-300:])
 elif a.action=='backup':require(a.directory,'INVALID_ARGUMENT');result=op.backup(a.directory)
 elif a.action=='restore':
  require(a.directory and a.fenced,'UNAUTHORIZED');op.create();result=op.restore(a.directory)
 elif a.action=='stop':result=op.quiesce()
 elif a.action=='freeze-campaign':
  require(a.profile=='live' and a.directory and a.offline_model and a.source_package and a.campaign_id,'INVALID_ARGUMENT')
  result=freeze(op,a.directory.resolve(),a.chart.resolve(),a.offline_model.resolve(),a.source_package,a.campaign_id)
 elif a.action=='run-live':
  require(a.profile=='live' and a.directory and a.offline_model and a.approval,'UNAUTHORIZED')
  result=run_live(op,a.directory.resolve(),a.chart.resolve(),a.offline_model.resolve(),a.approval)
 elif a.action=='cleanup':
  namespace=op.owned();require(not namespace['metadata'].get('labels',{}).get('omega.reference/campaign'),'UNAUTHORIZED')
  result=dict(namespace=a.namespace,namespace_uid=namespace['metadata']['uid'],preview=True,objects=json.loads(op.k('get','statefulsets,pvc,services,configmaps','-o','json')))
  if a.delete_synthetic and not a.preview:op.k('delete','namespace',a.namespace,'--wait=false');result.update(preview=False,deletion='requested; PVCs removed only with this explicit namespace deletion')
 print(json.dumps(result,indent=2))
if __name__=='__main__':main()
