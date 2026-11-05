"""Explicit operator amendment to a bounded manifest of an actual task result.

The historical full-projection recipe is unchanged. This opt-in representation
uses only existing write-file/inspect tools and the same workflow effect budget.
No expected answer, excerpt, replacement capture or new execution profile.
"""
import json,time,uuid
from fusion.contracts import canonical,digest,require,validate_ref
from fusion.workflow_recipes import native_object
from integration.single_node.reference_ops import PYTHON

PROFILE='captured-task-result-reference-document/1'

def document(source):
    task,result,ref=source['task'],source['result'],source['result_ref']
    from fusion.preview_tasks import record,correlated
    record(task,task['scope']);record(result,task['scope']);validate_ref(ref,task['scope'])
    correlated(result,task,source['task_ref'])
    require(result['status']=='captured-native-query','NOT_AVAILABLE')
    raw=result['projection'].encode()
    return dict(profile=PROFILE,task=task['id'],task_ref=source['task_ref'],result_ref=ref,
        projection_bytes=len(raw),projection_sha256=digest(raw),
        interpretation='reference-to-full-captured-result-not-answer-or-independent-observation')

def text(source):
    value=canonical(document(source)).decode();require(len(('write-file review.txt '+value).encode())<=4096,'OVERLOADED')
    return value

def verify(workspace,readback,source,inspection):
    expected=text(source);require(readback['path']==workspace['path']=='review.txt' and
        readback['revision']==workspace['revision'] and workspace['outcome']=='committed','CONFLICT')
    require(readback['text']==expected and workspace['digest']==readback['digest']==digest(expected.encode())
        and workspace['bytes']==len(expected.encode()),'CONFLICT')
    require(inspection['result_ref']==source['result_ref'] and inspection['task']==source['task']['id'],'CONFLICT')
    return dict(representation=PROFILE,workspace_contains_full_projection=False,
        full_projection_retained=True,reference_document=document(source),
        workspace_digest=workspace['digest'],inspected_artifact_result_ref=inspection['result_ref'],
        exact_full_result_link=True,projection_truncated=False)

CAPTURE='''import json,sys,time
from pathlib import Path
from fusion.contracts import require
from fusion.ports import Mutation
from fusion.preview_atoms import client
from fusion.preview_native_history import read_body
from fusion.preview_tasks import record,correlated
from integration.single_node.sustained_current import observe
q=json.load(sys.stdin);current=observe(q['recipient_session'])
app=json.loads((Path('/run/fusion/sessions')/q['recipient_session']/'application.json').read_bytes())
require(app['preview']['scope']==q['scope'] and current['scope']==q['scope'],'UNAUTHORIZED')
a=client(json.loads(Path(app['memory_atoms_config']).read_bytes()),q['deadline'])
observed=a.observe(Mutation(q['scope'],'result/'+q['task']))
require(observed['found'],'NOT_AVAILABLE');ref=observed['write']['ref']
result=record(read_body(a,ref)['body'],q['scope']);task=record(read_body(a,q['task_ref'])['body'],q['scope'])
correlated(result,task,q['task_ref']);require(result['id']==q['task'] and result['recipient']=='A' and result['sender']=='B','UNAUTHORIZED')
print(json.dumps(dict(task=task,result=result,task_ref=q['task_ref'],result_ref=ref,observation=observed)))
'''

def capture(r,session,publication,deadline):
    require(publication['status']=='TASK_PUBLISHED' and time.time_ns()//1000000<deadline,'NOT_AVAILABLE')
    found=[]
    for row in r.call('omega-agent-b','list'):
        observed=r.call('omega-agent-b','observe',row['session'],'--content')
        if observed['allocation']['allocation_id']=='incoming/A/'+session:found.append(observed)
    require(len(found)==1 and len(found[0]['inputs'])==1 and found[0]['inputs'][0]['state']=='complete','NOT_AVAILABLE')
    q=dict(recipient_session=found[0]['session'],scope=publication['ref']['scope_ref'],task=publication['task'],task_ref=publication['ref'],deadline=deadline)
    value=json.loads(r.op.k('exec','-i','omega-agent-b-0','--',PYTHON,'-c',CAPTURE,data=json.dumps(q),timeout=40))
    # The caller result and remote body remain separate exact receipts.
    value['recipient_capture']=found[0];document(value);return value

def resume(op,directory,previous):
    """Explicit same-instance continuation; no admission, copied answer or retry."""
    from pathlib import Path
    from examples.integrated_sustained import IntegratedRunner
    from examples.pilot_workflows import call,native_capture
    prior_path=Path(previous)/'registered-recipe/report.json';prior=json.loads(prior_path.read_bytes())
    require(prior['status']=='FAIL' and prior['recipe']=='approved-artifact-delivery/1','CONFLICT')
    root=Path(directory);root.mkdir(parents=True,exist_ok=False);r=IntegratedRunner(op,root/'native',maximum_inputs=1)
    sid,wid=prior['session'],prior['workflow'];end=prior['accepted']['deadline_ms'];r.end=time.monotonic()+max(0,(end-time.time()*1000)/1000);r.ids['omega-agent']=[sid]
    report=dict(status='RUNNING',representation=PROFILE,previous_primary_sha256=digest(prior_path.read_bytes()),
        source_sha256=digest(Path(__file__).read_bytes()),session=sid,workflow=wid,original_deadline_ms=end,
        original_failure_retained=True,new_sessions=0,new_workflows=0,deadline_renewals=0,observations=[],additional_live_generations=0)
    def save():r.save();(root/'report.json').write_bytes(canonical(report))
    try:
        op.owned();require(time.time()*1000+120000<end,'NOT_AVAILABLE');cur=call(op,sid,wid,'observe',{})
        require(cur['reservations_spent']==1 and cur['observations_spent']<=64 and set(cur['steps'])=={'delegate'} and cur['deadline_ms']==end,'CONFLICT')
        before=cur['steps'];observed=r.call('omega-agent','observe',sid,'--content')
        delegated=next(x for x in observed['inputs'] if x['id']==before['delegate']['input_id']);publication=native_object(delegated['result'])
        source=capture(r,sid,publication,end);report.update(before=cur,source=source,reference_document=document(source));save()
        suffix=[dict(node='artifact',tool='write-file',arguments=['review.txt',text(source)],guards=[],checkpoint=True),cur['plan'][-1]]
        cur=call(op,sid,wid,'amend',dict(identity='explicit-reference-representation',version=cur['version'],suffix=suffix,cause='full captured task projection exceeds fixed native command bound; explicitly select reference manifest, no truncation'))
        report['amendment']=cur;save()
        for node in ('artifact','inspect'):
            require(time.time()*1000+120000<end,'NOT_AVAILABLE')
            cur=call(op,sid,wid,'checkpoint',dict(identity='reference-review-'+node,version=cur['version'],reason='explicitly approve '+node+' with exact retained full-result reference'))
            cp=cur['checkpoints'][-1];report.setdefault('checkpoints',[]).append(cp);save()
            cur=call(op,sid,wid,'decide',dict(checkpoint=cp['identity'],identity='reference-approve-'+node,binding_sha256=cp['binding_sha256'],action='approve'))
            for _ in range(128):
                require(time.time()*1000<end,'NOT_AVAILABLE');cur=call(op,sid,wid,'advance',dict(version=cur['version']));report['observations'].append(cur);save()
                if node in cur['steps'] and cur['steps'][node]['result_sha256']:break
                time.sleep(.5)
            else:require(False,'OVERLOADED')
        cur=call(op,sid,wid,'advance',dict(version=cur['version']));require(cur['status']=='complete' and cur['reservations_spent']==3 and cur['deadline_ms']==end and cur['steps']['delegate']==before['delegate'],'CONFLICT')
        final=r.call('omega-agent','observe',sid,'--content');report.update(final=cur,native_session=final)
        report['native_report_sha256']=native_capture(root,r,cur,final)
        require(time.time()*1000+120000<end,'NOT_AVAILABLE')
        readback=r.object(r.run('read-file review.txt'));workspace=native_object(next(x for x in final['inputs'] if x['id']==cur['steps']['artifact']['input_id'])['result']);inspection=native_object(next(x for x in final['inputs'] if x['id']==cur['steps']['inspect']['input_id'])['result'])
        fetch='''import json,sys
from pathlib import Path
from fusion.preview_atoms import client
from fusion.preview_artifact_contracts import record
sid,ref=sys.argv[1:];app=json.loads((Path('/run/fusion/sessions')/sid/'application.json').read_bytes());a=client(json.loads(Path(app['history_atoms_config']).read_bytes()));print(json.dumps(record(json.loads(a.get(json.loads(ref)).bytes),app['preview']['scope'])))'''
        artifact=json.loads(op.k('exec','omega-agent-0','--',PYTHON,'-c',fetch,sid,json.dumps(inspection['artifact']),timeout=40))
        report.update(workspace=workspace,readback=readback,inspection=inspection,artifact=artifact,lineage=verify(workspace,readback,source,artifact),status='PASS');save()
    except BaseException as error:
        report.update(status='FAIL',failure=dict(type=type(error).__name__,code=getattr(error,'code',None),detail=str(error)[-1200:]));save();raise
    finally:save()
    return report
