"""Frozen cold baseline through actual native sessions; no model generation.

Proposals are the literal operator commands. The evaluator owns expected facts;
no expected result or answer reference is supplied to query/delegate consumers.
"""
import argparse,json,time
from pathlib import Path
from fusion.contracts import canonical,digest,require
from integration.single_node.reference_ops import Operator,PYTHON
from integration.single_node.sustained_qualification import Runner

WORKLOAD=dict(profile='integrated-comparator-workload/1',maximum_operator_inputs=14,
    maximum_seconds=1800,deadline_policy='original selected 120000ms per input',
    fact='The synthetic amber compass is stored in chest willow',query='synthetic amber compass storage',
    sequence=['A:remember','A:query','A:episodes','A:support captured-memory captured-source',
              'A:promote captured-memory','A:query','A:write-file','A:append-file','A:read-file',
              'A:pin','A:task-context','B:query','A:delegate B query','A:inspect-atom captured-task'],
    answers_for_evaluator_only=['chest willow'],model='RECORDED_PROPOSALS',additional_live_generations=0)

PROCESS_SAMPLE='''import json
from pathlib import Path
rows=[]
for directory in Path('/proc').iterdir():
 if not directory.name.isdigit():continue
 try:
  name=(directory/'comm').read_text().strip();fields={}
  for line in (directory/'status').read_text().splitlines():
   if line.startswith(('VmRSS:','VmHWM:')):
    key,value,*unit=line.split();fields[key.rstrip(':')]=int(value)*1024
  rows.append(dict(pid=int(directory.name),name=name,**fields))
 except (FileNotFoundError,ProcessLookupError,PermissionError):continue
 if len(rows)>128:raise RuntimeError('bounded pod process observation exceeded')
print(json.dumps(dict(processes=rows,scope='THIS_POD_PID_NAMESPACE',method='proc-status RSS/HWM snapshot; not lifetime cluster peak',cpu_quota='NOT_ESTABLISHED')))
'''

def qualify(op,directory,label='Phase3 dev12 cold per-input',after_workload=None):
    root=Path(directory);root.mkdir(parents=True,exist_ok=False)
    (root/'workload.json').write_bytes(canonical(WORKLOAD))
    r=Runner(op,root/'native');r.end=time.monotonic()+WORKLOAD['maximum_seconds']
    r.report.update(frozen=WORKLOAD,maximum_operator_inputs=14,baseline_profile=label)
    r.save();report=dict(status='RUNNING',workload_sha256=digest(canonical(WORKLOAD)),additional_live_generations=0)
    def save():(root/'report.json').write_bytes(canonical(report))
    save()
    try:
        op.owned()
        report['selected_images']={x['metadata']['name']:x['spec']['template']['spec']['containers'][0]['image'] for x in op.workloads()};save()
        a=r.allocate('omega-agent','baseline-A');b=r.allocate('omega-agent-b','baseline-B')
        memory=r.object(r.run('remember '+WORKLOAD['fact'],session=a))['memory']['handle']
        r.evaluate(r.run('query '+WORKLOAD['query'],session=a),dict(required=WORKLOAD['answers_for_evaluator_only']))
        events=r.object(r.run('episodes current',session=a))['events']
        source=next(x['body']['source']['handle'] for x in events if x['kind']=='external-observation')
        r.run('support '+memory+' '+source,session=a);r.run('promote '+memory,session=a)
        r.evaluate(r.run('query '+WORKLOAD['query'],session=a),dict(required=WORKLOAD['answers_for_evaluator_only']))
        r.run('write-file sample.txt Synthetic baseline workspace',session=a)
        r.run('append-file sample.txt Appended baseline line',session=a)
        r.run('read-file sample.txt',session=a);r.run('pin measurement Preserve captured observations',session=a)
        r.run('task-context',session=a)
        r.evaluate(r.run('query '+WORKLOAD['query'],'omega-agent-b',b),dict(required=WORKLOAD['answers_for_evaluator_only']))
        task=r.object(r.run('delegate B '+WORKLOAD['query'],session=a))
        until=time.monotonic()+max(0,(task['deadline']-time.time()*1000)/1000)+8
        while True:
            observed=r.call('omega-agent','observe',r.ids['omega-agent'][a],'--content')
            results=[x for x in observed['inputs'] if x['assignment']=='delegated-result' and x['deadline']==task['deadline']]
            if results and results[0]['state']=='complete':break
            require(time.monotonic()<until,'NOT_AVAILABLE');time.sleep(1)
        r.report['task_result']=results[0];r.report['inspection']=r.object(r.run('inspect-atom '+task['task'],session=a))
        require(r.count==14,'CONFLICT')
        for role,index in [('omega-agent',a),('omega-agent-b',b)]:r.current(role,index)
        report['telemetry']={};report['process_samples']={}
        for row in op.workloads():
            role=row['metadata']['name']
            report['telemetry'][role]=json.loads(op.k('exec',role+'-0','--',PYTHON,'-m','integration.single_node.sustained_diagnostics',timeout=45));save()
            report['process_samples'][role]=json.loads(op.k('exec',role+'-0','--',PYTHON,'-c',PROCESS_SAMPLE,timeout=20));save()
        report['worker_observations']={}
        observation='''import json,sqlite3
from pathlib import Path
from collections import Counter
cfg=json.loads(Path('/run/fusion/owner.json').read_bytes())['native_sessions']
value={'selected':cfg.get('resident_worker'),'incarnations':[],'native_inputs_by_pid':{}}
with sqlite3.connect(Path(cfg['database']).as_uri()+'?mode=ro',uri=True) as db:
 if db.execute("SELECT 1 FROM sqlite_master WHERE name='native_worker_epochs'").fetchone():
  for epoch,state,count in db.execute('SELECT e.incarnation,e.state,count(a.input) FROM native_worker_epochs e LEFT JOIN native_worker_assignments a ON a.incarnation=e.incarnation GROUP BY e.incarnation ORDER BY e.created LIMIT 256'):
   value['incarnations'].append({'incarnation':epoch,'state':state,'assignments':count})
counts=Counter()
for path in Path('/state/sessions').glob('*/native/native-stages.jsonl'):
 for line in path.read_text().splitlines():
  row=json.loads(line)
  if row['name']=='native.begin':counts[str(row['pid'])]+=1
value['native_inputs_by_pid']=dict(counts)
print(json.dumps(value))'''
        for role in ('omega-agent','omega-agent-b'):
            report['worker_observations'][role]=json.loads(op.k('exec',role+'-0','--',PYTHON,'-c',observation,timeout=30));save()
        report['benchmark_input_count']=r.count;r.report['benchmark_input_count']=r.count
        if after_workload is not None:
            report['after_workload']=after_workload(r);report['maintenance_input_count']=r.count-report['benchmark_input_count']
        r.report['status']='PASS';r.save();report.update(status='PASS',operator_inputs=r.count,native_report_sha256=digest((r.root/'report.json').read_bytes()),provider_local_coverage='Observed stage map; missing active spans remain explicit')
    except BaseException as error:
        r.report.update(status='FAILED',error=dict(type=type(error).__name__,code=getattr(error,'code',None)));r.save()
        report.update(status='FAIL',failure=r.report['error']);raise
    finally:op.quiesce();report['quiesced']=True;save()
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('kubeconfig','context','namespace','directory'):p.add_argument('--'+name,required=True)
    p.add_argument('--label',default='Phase3 dev12 cold per-input')
    a=p.parse_args();print(json.dumps(qualify(Operator(a.kubeconfig,a.context,a.namespace),a.directory,a.label)))
