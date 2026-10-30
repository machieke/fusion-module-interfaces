"""Named, sequential qualification of the existing reference harnesses.

This is an operator dispatcher, not a runtime scheduler. Every scenario creates
fresh task-owned state; the native workloads perform the operations. No live
model lane exists here. Reports retain failures and distinguish provider classes.
"""
import argparse,hashlib,json,os,subprocess,sys,time
from pathlib import Path
from fusion.contracts import require
from .reference_ops import Operator

SCENARIOS={
 's01':('test_cluster','baseline','deterministic'),
 'memory':('test_memory_cluster','baseline','memory'),
 'memory-storage':('test_memory_cluster','storage-acceptance','memory'),
 'memory-publication':('test_memory_cluster','search-after-publication','memory'),
 'memory-vector':('test_memory_cluster','caller-vector','memory'),
 'memory-enrollment':('test_memory_cluster','enrollment','memory'),
 'memory-rebuild':('test_memory_cluster','rebuild','memory'),
 'recorded':('test_workflow_cluster','correct','workflow'),
 'wrong-answer':('test_workflow_cluster','wrong-permitted','workflow'),
 'prohibited-command':('test_workflow_cluster','rejected','workflow'),
 'changed-fact':('test_workflow_cluster','altered-corpus','workflow'),
 'absent-fact':('test_workflow_cluster','absent-corpus','workflow'),
 'missing-payload':('test_workflow_cluster','missing-payload','workflow'),
 'unready-search':('test_workflow_cluster','unready-search','workflow'),
 'disclosure':('test_workflow_cluster','auth-probes','workflow'),
 'revocation':('test_workflow_cluster','revocation','workflow'),
 'model-spent':('test_workflow_cluster','model-unknown','workflow'),
 'model-capture':('test_workflow_cluster','model-capture','workflow'),
 'application-model-capture':('test_workflow_cluster','application-model-capture','workflow'),
 'lost-model':('test_workflow_cluster','lost-model','workflow'),
 'model-outage':('test_workflow_cluster','service-outage','workflow'),
 'query-capture':('test_workflow_cluster','query-capture','workflow'),
 'input-acceptance':('test_workflow_cluster','input-acceptance','workflow'),
 'bridge-capture':('test_workflow_cluster','bridge-capture','workflow'),
 'uncertain-send':('test_workflow_cluster','uncertain-send','workflow'),
 'cognition-relations':('test_cognitive_cluster','baseline','cognitive'),
 'attention-substitution':('test_cognitive_cluster','attention-file','cognitive'),
 'evidence-recovery':('test_cognitive_cluster','source-recovery','cognitive'),
 'belief-recovery':('test_cognitive_cluster','belief-recovery','cognitive'),
 'priority-recovery':('test_cognitive_cluster','priority-recovery','cognitive'),
 'chain':('test_chain_cluster','baseline','chain'),
 'chain-signed':('test_chain_cluster','signed-recovery','chain'),
 'chain-uncertain':('test_chain_cluster','uncertain-submission','chain'),
 'chain-observation':('test_chain_cluster','observation-recovery','chain'),
 'security-upgrade':('test_security_cluster',None,'deterministic'),
 'restore':('test_restore_cluster',None,'workflow'),
}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--kubeconfig',required=True);p.add_argument('--context',required=True);p.add_argument('--prefix',required=True);p.add_argument('--output',required=True);p.add_argument('--profiles',required=True,help='Directory with memory/workflow/cognitive/chain YAML and deterministic.json');p.add_argument('scenarios',nargs='+',choices=SCENARIOS);a=p.parse_args()
 require(a.prefix.startswith('omega-ref-'),'UNAUTHORIZED');require(a.context=='default','UNSUPPORTED_PROFILE')
 out=Path(a.output).resolve();out.mkdir(parents=True,exist_ok=False);profiles=Path(a.profiles).resolve()
 preflight=Operator(a.kubeconfig,a.context,a.prefix+'-preflight').preflight()
 denial=subprocess.run([sys.executable,'-c',"from integration.single_node.recorded_model import deny_live;print(deny_live('recorded'))"],capture_output=True,text=True);require(denial.returncode==0,'UNAUTHORIZED')
 root=Path(__file__).resolve().parents[2]
 sources={str(f.relative_to(root)):hashlib.sha256(f.read_bytes()).hexdigest() for folder in ('fusion','integration','deploy') for f in (root/folder).rglob('*') if f.is_file() and '__pycache__' not in f.parts}
 report=dict(schema='reference-qualification/1',preflight=preflight,source=sources,additional_live_generations=0,execution='sequential independent namespaces',runs=[])
 for index,name in enumerate(a.scenarios):
  module,case,profile=SCENARIOS[name];dest=out/name;prefix=a.prefix+'-'+str(index)
  command=[sys.executable,'-m','integration.single_node.'+module,'--kubeconfig',a.kubeconfig,'--prefix',prefix,'--output',str(dest)]
  if profile=='deterministic':command+=['--image-tag',json.loads((profiles/'deterministic.json').read_text())['tag']]
  else:command+=['--values',str(profiles/(profile+'.yaml'))]
  if module=='test_workflow_cluster':command+=['--cases',case]
  elif module=='test_chain_cluster':command+=['--scenario',case,'--cleanup']
  elif module in ('test_memory_cluster','test_cognitive_cluster'):command+=['--cleanup',case]
  elif case:command+=[case]
  start=time.time()
  with (out/(name+'.log')).open('w') as log:result=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT)
  reports=[]
  for file in dest.rglob('report.json'):
   value=json.loads(file.read_text());reports.append(dict(path=str(file.relative_to(out)),sha256=hashlib.sha256(file.read_bytes()).hexdigest(),status=value.get('status'),workflow_pass=value.get('workflow_pass'),real=value.get('real'),fixtures=value.get('fixtures')))
  report['runs'].append(dict(name=name,command=command,seconds=time.time()-start,returncode=result.returncode,reports=reports));(out/'qualification.json').write_text(json.dumps(report,indent=2)+'\n')
  print(name, 'PASS' if result.returncode==0 else 'FAIL',flush=True)
 require(all(r['returncode']==0 for r in report['runs']),'NOT_AVAILABLE')
if __name__=='__main__':main()
