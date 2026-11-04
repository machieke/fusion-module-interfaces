"""Three native sessions: private A, private B and shared A, six inputs total.

Recorded proposals only. Context/history/cognition execute through the retained
native services; the evaluator checks captured actual prompts, never supplies
tool answers. Private observations remain in the operator's artifact directory.
"""
import argparse,json,time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from fusion.contracts import canonical,digest,require
from integration.single_node.reference_ops import Operator,PYTHON
from .integrated_sustained import IntegratedRunner

CASES=(('omega-agent','shared','Q26_TRIPLE_SHARED_NOTE'),
       ('omega-agent','private','Q26_TRIPLE_PRIVATE_A_NOTE'),
       ('omega-agent-b','private','Q26_TRIPLE_PRIVATE_B_NOTE'))


def qualify(op,directory):
    root=Path(directory);root.mkdir(parents=True,exist_ok=False)
    r=IntegratedRunner(op,root/'native',maximum_inputs=6,legacy_crossing_required=False);r.end=time.monotonic()+600
    report=dict(status='RUNNING',namespace=op.namespace,maximum_native_inputs=6,maximum_seconds=600,
        workload_sha256=digest(canonical(CASES)),additional_live_generations=0,
        model='RECORDED_COMMAND_PROPOSALS',private_report_publication='FORBIDDEN',observations=[])
    def save():(root/'report.json').write_bytes(canonical(report))
    save()
    try:
        op.owned();sessions=[]
        for role,template,note in CASES:
            index=r.allocate(role,'triple-'+template+'-'+role,template);sessions.append((role,index,note))
        with ThreadPoolExecutor(max_workers=3) as pool:
            pending=[pool.submit(r.run,'pin isolation '+note,role,index) for role,index,note in sessions]
            for future in pending:future.result()
        with ThreadPoolExecutor(max_workers=3) as pool:
            pending=[pool.submit(r.run,'task-context',role,index) for role,index,note in sessions]
            projections=[future.result() for future in pending]
        for (role,index,note),result in zip(sessions,projections):
            require(note in result and all(other not in result for _,_,other in CASES if other!=note),'UNAUTHORIZED')
            sid=r.ids[role][index]
            # This is the caller's own capture, observed by its operator. No
            # provider database is mounted or queried by an application tool.
            code='''import json,sqlite3,sys
from pathlib import Path
sid,own=sys.argv[1:3];others=json.loads(sys.argv[3])
with sqlite3.connect((Path('/state/sessions')/sid/'caller.sqlite').as_uri()+'?mode=ro',uri=True) as db:
 rows=db.execute('SELECT intent,result FROM app_model_calls ORDER BY slot').fetchall()
 assert len(rows)==2 and all(r[1] is not None for r in rows)
 prompt=json.loads(rows[1][0])['native_prompt']
 assert own in prompt and all(x not in prompt for x in others)
print(json.dumps(dict(captured_model_calls=2,next_prompt_contains_own_note=True,other_scope_notes_absent=True)))'''
            observed=json.loads(op.k('exec',role+'-0','--',PYTHON,'-c',code,sid,note,json.dumps([x[2] for x in CASES if x[2]!=note])))
            report['observations'].append(dict(role=role,scope_class='shared' if note==CASES[0][2] else 'private',**observed));save()
            r.close(role,index)
        r.report['status']='PASS';report.update(status='PASS',operator_native_inputs=6,
            independent_private_owners=2,concurrent_operator_submissions=True,
            native_dispatch='TWO_REAL_AGENTS_WITH_EXISTING_OWNER_SERIALIZATION',deadlines_renewed=0,reservation_refunds=0)
    except BaseException as error:
        report.update(status='FAIL',failure=dict(type=type(error).__name__,code=getattr(error,'code',None),detail=str(error)[-1000:]));raise
    finally:r.save();op.quiesce();report['quiesced']=True;save()
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('kubeconfig','context','namespace','directory'):p.add_argument('--'+name,required=True)
    a=p.parse_args();r=qualify(Operator(a.kubeconfig,a.context,a.namespace),a.directory)
    print(json.dumps(dict(status=r['status'],additional_live_generations=0)))
