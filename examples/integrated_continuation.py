"""Actual native task -> envelope inspection -> next context, over pod HTTPS.

Recorded models propose commands only. All payloads/views/tool results come
from native execution and declared owners. No chain submission or model runtime.
"""
import argparse,json,time
from pathlib import Path
from fusion.contracts import canonical,digest,require
from integration.single_node.reference_ops import Operator,PYTHON
from integration.single_node.sustained_qualification import Runner


def qualify(op,directory):
    root=Path(directory);root.mkdir(parents=True,exist_ok=False);r=Runner(op,root/'native');r.end=time.monotonic()+900
    r.report.update(maximum_operator_inputs=4,scenario='native-bounded-inspection-envelope-continuation')
    report=dict(status='RUNNING',additional_live_generations=0,model='RECORDED_PROPOSALS',
        providers='REAL_NATIVE_E5_CHROMA_DETTA_EXECUTION_MESSAGING_POD_HTTPS',chain='NOT_SUBMITTED')
    def save():(root/'report.json').write_bytes(canonical(report))
    save()
    try:
        op.owned();report['images']={x['metadata']['name']:x['spec']['template']['spec']['containers'][0]['image'] for x in op.workloads()};save()
        index=r.allocate('omega-agent','continuation-A');sid=r.ids['omega-agent'][index]
        report['memory']=r.object(r.run('remember The synthetic amber compass is stored in chest willow',session=index));save()
        task=r.object(r.run('delegate B synthetic amber compass storage',session=index));report['task']=task;save()
        until=min(r.end,time.monotonic()+max(0,(task['deadline']-time.time()*1000)/1000)+8)
        while True:
            observed=r.call('omega-agent','observe',sid,'--content')
            results=[x for x in observed['inputs'] if x['assignment']=='delegated-result' and x['deadline']==task['deadline']]
            if results and results[0]['state']=='complete':break
            require(time.monotonic()<until,'NOT_AVAILABLE');time.sleep(1)
        report['delegated_result']=results[0];save()
        report['inspection']=r.object(r.run('inspect-atom '+task['task'],session=index));save()
        entry=r.report['inputs'][-1];occurrence=entry['observed']['result']['occurrences'][0]
        def observe():return r.call('omega-agent','continuation',sid,'--occurrence',occurrence)
        first=observe();report['continuation']=first;save()
        require(first['status']=='return-ready' and len(first['steps'])==7 and first['cursor']['head']>=2 and
            first['native_consumption']['turn_captured'] and first['native_consumption']['occurrence_captured'],'NOT_AVAILABLE')
        require(observe()==first,'CONFLICT')
        r.run('task-context',session=index)
        # Inspect this application's own saved model input only as evidence.
        # It is never supplied to a tool or used to reconstruct a tool result.
        code="""import json,sqlite3
from pathlib import Path
from fusion.contracts import digest,canonical,require
p=Path('/state/sessions')/SESSION/'caller.sqlite'
with sqlite3.connect(p.as_uri()+'?mode=ro',uri=True) as db:
 db.row_factory=sqlite3.Row
 accepted=json.loads(db.execute('SELECT intent FROM app_model_calls ORDER BY slot DESC LIMIT 1').fetchone()[0])
 prompt=accepted['native_prompt'];require(' LAST_SKILL_USE_RESULTS: ' in prompt,'NOT_AVAILABLE')
 feedback=prompt.split(' LAST_SKILL_USE_RESULTS: ',1)[1].split(' HISTORY: ',1)[0]
 require(all(x in feedback for x in ('INSPECTED_ARTIFACT',JOB_VALUE,ARTIFACT_VALUE)),'NOT_AVAILABLE')
 print(json.dumps({'actual_captured_prompt_sha256':digest(prompt.encode()),'feedback_sha256':digest(feedback.encode()),
  'inspection_job_bound':True,'inspection_artifact_bound':True,'slot':accepted['slot'],
  'source_id':accepted['source_id'],'next_prompt_not_injected':True}))
""".replace('SESSION',repr(sid)).replace('JOB_VALUE',repr(report['inspection']['job_id'])).replace('ARTIFACT_VALUE',repr(report['inspection']['artifact']['digest']))
        report['next_context_evidence']=json.loads(op.k('exec','omega-agent-0','--',PYTHON,'-c',code))
        report.update(status='PASS',operator_native_inputs=r.count,artifact=report['inspection']['artifact'],
            accepted_deadline_retained=first['deadline_ms'],notification_catchup=first['cursor'],
            next_context='ACTUAL_CAPTURED_INSPECTION_IN_NEXT_NATIVE_MODEL_INPUT')
    except BaseException as error:report.update(status='FAIL',failure=dict(type=type(error).__name__,code=getattr(error,'code',None)));raise
    finally:r.save();op.quiesce();report['quiesced']=True;save()
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('kubeconfig','context','namespace','directory'):p.add_argument('--'+name,required=True)
    a=p.parse_args();r=qualify(Operator(a.kubeconfig,a.context,a.namespace),a.directory);print(json.dumps(dict(status=r['status'],additional_live_generations=0)))
