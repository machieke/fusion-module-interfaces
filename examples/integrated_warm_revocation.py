"""Actual native session with immediate provider-selection revocation.

Six bounded native inputs, plus one refused input that is never accepted.
Revocation uses the existing caller registry port; no policy-file edit, pod
replacement, subprocess restart or result fixture simulates the denial.
"""
import argparse,json,time
from pathlib import Path
from fusion.contracts import canonical,require,digest
from integration.single_node.reference_ops import Operator,PYTHON
from .integrated_sustained import IntegratedRunner

COMMANDS=('remember The synthetic violet dial is in basket cypress','query synthetic violet dial',
          'episodes current','pin security Observe current provider authority','task-context','task-context')

OBSERVE='''import json,sys,sqlite3
from pathlib import Path
from collections import Counter
sid=sys.argv[1];cfg=json.loads(Path('/run/fusion/owner.json').read_bytes())['native_sessions']
with sqlite3.connect(Path(cfg['database']).as_uri()+'?mode=ro',uri=True) as db:
 rows=list(db.execute('SELECT incarnation,count(*) FROM native_worker_assignments WHERE session=? GROUP BY incarnation',(sid,)))
counts=Counter()
for line in (Path('/state/sessions')/sid/'native/native-stages.jsonl').read_text().splitlines():
 row=json.loads(line)
 if row['name']=='native.begin':counts[str(row['pid'])]+=1
print(json.dumps(dict(incarnations=[dict(id=i,assignments=n) for i,n in rows],native_inputs_by_pid=dict(counts))))
'''


def qualify(op,directory):
    root=Path(directory);root.mkdir(parents=True,exist_ok=False)
    r=IntegratedRunner(op,root/'native',maximum_inputs=6,legacy_crossing_required=False);r.end=time.monotonic()+600
    report=dict(status='RUNNING',namespace=op.namespace,maximum_seconds=600,maximum_native_inputs=6,
        commands=list(COMMANDS),workload_sha256=digest(canonical(COMMANDS)),
        additional_live_generations=0,model='RECORDED_PROPOSALS',provider_revocation='TRUSTED_NEW_INPUT_SELECTION_NOT_OLD_CAPTURE_ERASURE')
    def save():(root/'report.json').write_bytes(canonical(report))
    def provider(action,identity):
        return r.call('omega-agent','providers',None,'--provider','shared-fusion-storage',
            '--provider-action',action,'--identity',identity)
    save()
    try:
        op.owned();uid=json.loads(op.k('get','pod','omega-agent-0','-o','json'))['metadata']['uid']
        index=r.allocate('omega-agent','integrated-current-warm-revocation');sid=r.ids['omega-agent'][index]
        for command in COMMANDS[:5]:
            result=r.run(command,session=index)
            if command.startswith('query'):r.evaluate(result,dict(required=['basket cypress']))
        before=r.call('omega-agent','observe',sid,'--content')
        workers=json.loads(op.k('exec','omega-agent-0','--',PYTHON,'-c',OBSERVE,sid))
        require(list(workers['native_inputs_by_pid'].values())==[5] and len(workers['incarnations'])==1,'CONFLICT')
        report['before_revocation']=workers;save()
        report['disabled']=provider('disable','warm-revocation-disable');save()
        try:r.call('omega-agent','submit',sid,'--identity','warm-refused-new-input','--text','pin denied Never execute this command','--assignment','synthetic-task')
        except RuntimeError as error:require('NOT_AVAILABLE' in str(error),'CONFLICT')
        else:require(False,'CONFLICT')
        require(r.call('omega-agent','observe',sid,'--content')==before,'CONFLICT')
        require(json.loads(op.k('exec','omega-agent-0','--',PYTHON,'-c',OBSERVE,sid))==workers,'CONFLICT')
        require(json.loads(op.k('get','pod','omega-agent-0','-o','json'))['metadata']['uid']==uid,'CONFLICT')
        report.update(refused_input_not_accepted=True,captures_unchanged=True,worker_not_restarted_for_denial=True,pod_uid=uid);save()
        report['readiness']=provider('probe','warm-revocation-restored-readiness')
        report['enabled']=provider('enable','warm-revocation-enable');save()
        r.run(COMMANDS[5],session=index);r.close('omega-agent',index)
        r.report['status']='PASS';report.update(status='PASS',operator_native_inputs=6,deadline_renewals=0,
            reservation_refunds=0,source='REAL_NATIVE_OMEGA_E5_CHROMA_DETTA_HTTPS',permission='current caller selection before new acceptance')
    except BaseException as error:
        report.update(status='FAIL',failure=dict(type=type(error).__name__,code=getattr(error,'code',None),detail=str(error)[-1000:]));raise
    finally:r.save();op.quiesce();report['quiesced']=True;save()
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('kubeconfig','context','namespace','directory'):p.add_argument('--'+name,required=True)
    a=p.parse_args();r=qualify(Operator(a.kubeconfig,a.context,a.namespace),a.directory)
    print(json.dumps(dict(status=r['status'],additional_live_generations=0)))
