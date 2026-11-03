"""Fresh artifact-kit smoke: installed operator, native remember and peer query.

No repository PYTHONPATH is required. This is a separate installation smoke,
not a replacement for retained-source capacity or recovery qualification.
The generated chain identity is checked while the node stays inert.
"""
import argparse,json,os,subprocess,sys,time
from pathlib import Path
import yaml
from fusion.contracts import canonical,digest,require
from integration.single_node.reference_ops import Operator,PYTHON
from integration.single_node.sustained_qualification import Runner

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for name in ('kubeconfig','context','namespace','values','chart','directory'):p.add_argument('--'+name,required=True)
 a=p.parse_args();root=Path(a.directory);root.mkdir(parents=True,exist_ok=False);op=Operator(a.kubeconfig,a.context,a.namespace)
 report=dict(status='RUNNING',namespace=a.namespace,additional_live_generations=0,classification='RECORDED_COMMANDS_REAL_NATIVE_TOOLS_FINAL_KIT',maximum_native_inputs=2,driver_sha256=digest(Path(__file__).read_bytes()))
 def save():(root/'report.json').write_bytes(canonical(report))
 save();created=False
 try:
  cli=Path(sys.executable).with_name('fusion-sustained');env=dict(os.environ);env.pop('PYTHONPATH',None)
  args=[str(cli),'--kubeconfig',op.kubeconfig,'--context',a.context,'--namespace',a.namespace,'install','--chart',str(Path(a.chart).resolve()),'--values',str(Path(a.values).resolve()),'--directory',str((root/'private-secrets').resolve())]
  created=True
  with (root/'install.log').open('w') as log:subprocess.run(args,cwd='/tmp',env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=360)
  v=yaml.safe_load(Path(a.values).read_text());public=json.loads((root/'private-secrets/chain-public.json').read_bytes())
  require(all(v['preview']['chain'][k]==x for k,x in public.items()),'CONFLICT')
  source="import json;from pathlib import Path;p=json.loads(Path('/state/process.json').read_bytes());s=json.loads(Path('/state/owner-seal.json').read_bytes());assert p['activated'] is False and p['native_pid'] is None;print(json.dumps(dict(inert=True,public=s['public'])))"
  node=json.loads(op.k('exec','-i','f1r3node-0','--',PYTHON,'-c',source));require(node['public']==public['public_key'],'CONFLICT')
  report['fresh_chain_setup']=dict(public_bound_before_owner_seal=True,node_inert=True,chain_submissions=0);save()
  runner=Runner(op,root/'native');runner.end=time.monotonic()+300
  runner.report.update(maximum_operator_inputs=2,frozen=dict(profile='artifact-install-smoke/1',fact='The synthetic amber token is in locker elm',query='synthetic amber token',live_allowance=0));runner.save()
  i=runner.allocate('omega-agent','artifact-smoke-A');j=runner.allocate('omega-agent-b','artifact-smoke-B')
  written=runner.object(runner.run('remember '+runner.report['frozen']['fact'],'omega-agent',i));require(written['status']=='REMEMBER-SUCCESS','CONFLICT')
  result=runner.run('query '+runner.report['frozen']['query'],'omega-agent-b',j);require('locker elm' in result,'CONFLICT')
  runner.close('omega-agent',i);runner.close('omega-agent-b',j);runner.report['status']='PASS';runner.save()
  report.update(status='PASS',native_inputs=2,actual_query_result_scored=True,answers_supplied_to_consumer=False,values_sha256=digest(Path(a.values).read_bytes()),native_report_sha256=digest((root/'native/report.json').read_bytes()))
 except BaseException as error:
  report.update(status='FAILED',failure=dict(type=type(error).__name__,code=getattr(error,'code',None),detail=str(error)[-1200:]));raise
 finally:
  if created:op.quiesce();report['quiesced']=True
  save()
 print(json.dumps(report))
if __name__=='__main__':main()
