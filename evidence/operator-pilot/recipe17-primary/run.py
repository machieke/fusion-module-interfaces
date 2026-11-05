import json,subprocess,sys,time,signal
from pathlib import Path
from unittest.mock import patch
from fusion.contracts import canonical,digest,require
from integration.single_node.reference_ops import Operator,PYTHON
from examples.pilot_network_edges import chain_qualify
from examples.pilot_recipe_chain import RecipeChain
root=Path('/data/fusion-operator-pilot-release/qualification-private/recipe-reference17');packet=Path('/data/fusion-operator-pilot-release/distribution17');operator=Path('/data/fusion-operator-pilot-release/operator19')
plan=json.loads((root/'qualification-plan.json').read_bytes());require(plan['status']=='FROZEN_UNADMITTED' and plan['additional_live_generations']==0,'UNAUTHORIZED')
for path,expected in plan['local_inputs'].items():require(digest(Path(path).read_bytes())==expected,'CONFLICT')
require(not (root/'start.json').exists(),'CONFLICT');start=time.time_ns()//1000000;end=start+plan['maximum_programme_seconds']*1000
(root/'start.json').write_bytes(canonical(dict(start_ms=start,end_ms=end,plan_sha256=digest((root/'qualification-plan.json').read_bytes()),additional_live_generations=0)))
def expired(*_):raise TimeoutError('frozen programme window expired; no resubmission')
signal.signal(signal.SIGALRM,expired);signal.setitimer(signal.ITIMER_REAL,max(0.001,(end-time.time()*1000)/1000))
op=Operator(root/'kubeconfig','default',plan['namespace']);report=dict(status='RUNNING',plan_sha256=digest((root/'qualification-plan.json').read_bytes()),source_sha256=digest(Path(__file__).read_bytes()),start_ms=start,end_ms=end,additional_live_generations=0)
def save():(root/'programme-report.json').write_bytes(canonical(report))
save()
try:
 subprocess.run([str(operator/'bin/python'),'-I',str(root/'verify_installed.py')],check=True,stdout=subprocess.DEVNULL,timeout=30)
 with (root/'install.log').open('wb') as log:subprocess.run([str(operator/'bin/python'),'-I',str(root/'install.py')],check=True,stdout=log,stderr=subprocess.STDOUT,timeout=400)
 require(time.time_ns()//1000000+2100000<end,'NOT_AVAILABLE')
 original=RecipeChain.independent
 def observed(self,observer):
  value=original(self,observer)
  try:
   capacity=json.loads(op.k('exec','fusion-commitment-0','--',PYTHON,'-m','integration.single_node.diagnostics',timeout=40));(root/'commitment-capacity.json').write_bytes(canonical(capacity))
   with (root/'chain-process.log').open('wb') as log:subprocess.run([str(operator/'bin/python'),'-I',str(root/'observe_process.py'),'--kubeconfig',str(root/'kubeconfig'),'--namespace',op.namespace,'--role','f1r3node','--output',str(root/'chain-process.json')],check=True,stdout=log,stderr=subprocess.STDOUT,timeout=90)
   report['supplementary_owner_and_process_observations']='PASS'
  except BaseException as error:report['supplementary_owner_and_process_observations']=dict(status='FAIL',type=type(error).__name__,detail=str(error)[-1000:])
  save();return value
 with patch.object(RecipeChain,'independent',observed):
  result=chain_qualify(op,root/'recipe-installed/plan.json',root/'recipe-installed/values.yaml',packet/'deploy/helm/omega-fusion',root/'chain',packet/'examples/preview_chain_observer.py',representation='reference-document')
 report.update(status=result['status'],chain_report_sha256=digest((root/'chain/report.json').read_bytes()),finished_ms=time.time_ns()//1000000);require(report['finished_ms']<=end,'NOT_AVAILABLE');save()
except BaseException as error:report.update(status='FAIL',failure=dict(type=type(error).__name__,code=getattr(error,'code',None),detail=str(error)[-1500:]));save();raise
finally:
 signal.setitimer(signal.ITIMER_REAL,0)
 try:op.quiesce();report['cleanup']=dict(pods=json.loads(op.k('get','pods','-o','json')),pvcs=json.loads(op.k('get','pvc','-o','json')),observed_ms=time.time_ns()//1000000)
 except BaseException as error:report['cleanup_failure']=dict(type=type(error).__name__,detail=str(error)[-1000:])
 save()
