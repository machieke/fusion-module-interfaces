"""Installed bounded native workflow qualification via the normal HTTPS owner.

Only explicit recorded proposals select commands. All captures, memory handles,
withdrawal, delegation and follow-up execution come from actual native tools.
No request contains a reference to the expected retrieval answer.
"""
import argparse,json,time,uuid
from pathlib import Path
from fusion.contracts import canonical,require,digest
from fusion.guarded_continuation import PROFILE
from fusion.workflow_recipes import knowledge_handoff,native_object
from fusion.workflow_prerequisites import KINDS
from integration.single_node.pilot_workflow_evaluation import freeze,score
from integration.single_node.reference_ops import Operator,PYTHON
from examples.integrated_sustained import IntegratedRunner as Runner


def call(op,session,workflow,operation,body):
    q=dict(profile=PROFILE,id=str(uuid.uuid4()),session=session,workflow=workflow,operation=operation,body=body)
    script='import json,sys;from integration.single_node.pilot_workflows import request;print(json.dumps(request(json.load(sys.stdin))))'
    return json.loads(op.k('exec','-i','omega-agent-0','--',PYTHON,'-c',script,data=json.dumps(q),timeout=40))


def await_delegation(r,session,publication,end):
    """Observe the one fresh-session task. Native ingress verifies its lineage.

    This does not drain, replay or submit. The original task deadline bounds
    observation; its fixed eight-second observation margin grants no work.
    """
    until=min(end,time.monotonic()+max(0,(publication['deadline']-time.time()*1000)/1000)+8)
    while True:
        observed=r.call('omega-agent','observe',session,'--content')
        matches=[x for x in observed['inputs'] if x['assignment']=='delegated-result' and x['deadline']==publication['deadline']]
        require(len(matches)<=1,'CONFLICT')
        if matches and matches[0]['state']=='complete':return matches[0],observed
        require(time.monotonic()<until,'NOT_AVAILABLE');time.sleep(.5)



def close_consumed_sessions(r,sender_session,workflow):
    """Explicitly close only this completed sender and its task receiver."""
    results=[]
    sender=r.call('omega-agent','observe',sender_session,'--content')
    require(all(x['state']=='complete' for x in sender['inputs']),'NOT_AVAILABLE')
    results.append(dict(role='omega-agent',session=sender_session,
        receipt=r.call('omega-agent','close',sender_session,'--identity','workflow-close-'+workflow)))
    for row in r.call('omega-agent-b','list'):
        if row['state']!='active':continue
        observed=r.call('omega-agent-b','observe',row['session'],'--content')
        if observed['allocation']['allocation_id']!='incoming/A/'+sender_session:continue
        require(all(x['state']=='complete' for x in observed['inputs']),'NOT_AVAILABLE')
        results.append(dict(role='omega-agent-b',session=row['session'],observation=observed,
            receipt=r.call('omega-agent-b','close',row['session'],'--identity','workflow-close-'+workflow)))
    return results


def native_capture(root,r,current,observed):
    """Export actual owner receipts, distinguishing workflow and direct inputs."""
    rows=list(r.report['inputs']);seen={x['identity'] for x in rows}
    for node,step in current['steps'].items():
        if step['receipt'] is None:continue
        matching=[x for x in observed['inputs'] if x['id']==step['input_id']]
        require(len(matching)==1 and step['input_id'] not in seen,'CONFLICT');row=matching[0]
        require(step['receipt']['accepted']==row['accepted'] and step['deadline_ms']==row['deadline'],'CONFLICT')
        rows.append(dict(role='omega-agent',session=observed['session'],identity=row['id'],
            command=row['payload']['text'],accepted=step['receipt'],observed=row,
            origin=dict(kind='registered-workflow',workflow=current['workflow'],node=node,version=step['version'])))
        seen.add(row['id'])
    value=dict(classification='RECORDED_MODEL_REAL_NATIVE_TOOLS',namespace=r.op.namespace,
        inputs=rows,workflow_native_inputs=len(current['steps']),direct_operator_inputs=len(r.report['inputs']),
        actual_session_observation=observed,additional_live_generations=0)
    raw=canonical(value);(Path(root)/'workflow-native.json').write_bytes(raw);return digest(raw)


def qualify(op,directory,variant='withdrawn',*,maximum_seconds=600,case='default',checkpoint_restart=False,archive_prerequisite=False,checkpoint_decision=None):
    require(variant in ('unchanged','withdrawn','irrelevant-change','unknown','unauthorized'))
    require(type(maximum_seconds) is int and 30<=maximum_seconds<=600,'OVERLOADED')
    require(checkpoint_decision is None or callable(checkpoint_decision),'INVALID_ARGUMENT')
    require(type(checkpoint_restart) is bool and type(archive_prerequisite) is bool and (not archive_prerequisite or variant=='unchanged'),'INVALID_ARGUMENT')
    require(type(case) is str and case and len(case)<=32 and all(c.isalnum() or c=='-' for c in case),'INVALID_ARGUMENT')
    root=Path(directory);root.mkdir(parents=True,exist_ok=False);r=Runner(op,root/'native',maximum_inputs=8)
    report=dict(status='RUNNING',classification='RECORDED_MODEL_REAL_NATIVE_TOOLS',variant=variant,
        maximum_native_operator_inputs=5,maximum_explicit_drives=128,maximum_wall_seconds=maximum_seconds,case=case,oracle=freeze(),
        model='RECORDED_PROPOSALS',additional_live_generations=0,observations=[],effects=[])
    def save():(root/'report.json').write_bytes(canonical(report))
    count=0;end=time.monotonic()+maximum_seconds;accepted_limit=time.time_ns()//1000000+maximum_seconds*1000;save()
    try:
        op.owned();report['images']={x['metadata']['name']:x['spec']['template']['spec']['containers'][0]['image'] for x in op.workloads()};save()
        r.admit_selection('omega-agent-b','recipient-'+str(uuid.uuid4()))
        index=r.allocate('omega-agent','guarded-'+str(uuid.uuid4()));sid=r.ids['omega-agent'][index];wid=str(uuid.uuid4())
        deadline=accepted_limit
        token='synthetic amber parcel '+case
        plan=knowledge_handoff('The '+token+' is held in chest birch',token+' location')
        current=call(op,sid,wid,'admit',dict(recipe='knowledge-handoff/1',steps=plan,deadline_ms=deadline))
        report.update(session=sid,workflow=wid,accepted=current);save()
        while len([x for x in current['steps'].values() if x['result_sha256']])<2:
            require(count<128 and time.monotonic()<end,'OVERLOADED');count+=1
            current=call(op,sid,wid,'advance',dict(version=1));report['observations'].append(current);save();time.sleep(.5)
        before=current['steps'];observed=r.call('omega-agent','observe',sid,'--content')
        memory=native_object(next(x for x in observed['inputs'] if x['id']==before['remember']['input_id'])['result'])
        report['captured_memory']=memory
        publication=native_object(next(x for x in observed['inputs'] if x['id']==before['delegate']['input_id'])['result'])
        returned,observed=await_delegation(r,sid,publication,end)
        report.update(publication=publication,delegated_result=returned,consumption_observation=observed);save()
        consumed=dict(id='delegated-result-consumed',kind='result-captured',policy=KINDS['result-captured'],
            scope=observed['scope'],target=dict(session=sid,input=returned['id'],result_sha256=digest(canonical(returned['result']))),predicate=None)
        guards=[*plan[-1]['guards'],consumed]
        if archive_prerequisite:
            from examples.pilot_workflow_archive import archive
            guard,report['archived_prerequisite']=archive(op,wid,memory);guards.append(guard);save()
        suffix=[{**plan[-1],'guards':guards}]
        current=call(op,sid,wid,'amend',dict(identity='bind-actual-consumption',version=1,suffix=suffix,
            cause='unstarted follow-up requires actual captured delegated result'))
        if variant=='withdrawn':
            report['withdrawal']=r.object(r.run('forget '+memory['memory']['handle'],session=index));save()
        elif variant=='irrelevant-change':
            report['irrelevant_change']=r.object(r.run('remember The unrelated synthetic cobalt prism is held in box alder',session=index));save()
        if variant in ('unknown','unauthorized'):
            from examples.pilot_workflow_faults import storage_guard_fault
            report['provider_fault']={};save()
            with storage_guard_fault(op,variant,report['provider_fault']):
                current=call(op,sid,wid,'advance',dict(version=current['version']))
                expected='UNKNOWN' if variant=='unknown' else 'UNAUTHORIZED'
                require(current['status']=='prerequisite-held' and current['reservations_spent']==2,'CONFLICT')
                require(current['latest_prerequisites']['observations'][0]['state']==expected,'CONFLICT')
                report['counterfactual_hold']=current
                report['counterfactual_evaluation']=score(variant,dict(owner_dataflow=True,prerequisite=expected,
                    progression='held',tool_result=None,provenance=all(current['steps'][k]==v for k,v in before.items()),
                    answer_correct=None,external_receipt='NOT_REQUIRED',chain_effect='NOT_REQUESTED',
                    captured_before=before,captured_after=current['steps']),report['oracle'])
                require(report['counterfactual_evaluation']['safety_objective']=='PASS','CONFLICT');save()
            # Provider restoration is not workflow permission. The same original
            # plan still needs its explicit checkpoint and fresh owner reads.
            save()
        # The guard checks the exact memory revision after the real owner change.
        current=call(op,sid,wid,'advance',dict(version=current['version'])) if variant=='withdrawn' else current
        if variant=='withdrawn':
            require(current['status']=='prerequisite-held' and current['reservations_spent']==2,'CONFLICT')
            require(current['latest_prerequisites']['observations'][0]['state']=='INVALID','CONFLICT')
            report['counterfactual_hold']=current
            report['counterfactual_evaluation']=score('withdrawn',dict(owner_dataflow=True,prerequisite='INVALID',
                progression='held',tool_result=None,provenance=all(current['steps'][k]==v for k,v in before.items()),
                answer_correct=None,external_receipt='NOT_REQUIRED',chain_effect='NOT_REQUESTED',
                captured_before=before,captured_after=current['steps']),report['oracle'])
            require(report['counterfactual_evaluation']['safety_objective']=='PASS','CONFLICT')
            suffix=[dict(node='followup',tool='task-context',arguments=[],guards=[consumed],checkpoint=True)]
            current=call(op,sid,wid,'amend',dict(identity='source-withdrawn-amendment',version=current['version'],suffix=suffix,cause='actual exact memory revision withdrawn'))
        version=current['version']
        current=call(op,sid,wid,'checkpoint',dict(identity='operator-review',version=version,reason='explicit bounded follow-up review'))
        cp=current['checkpoints'][-1]
        report['checkpoint']=cp;save()
        if checkpoint_restart:
            old_uid=json.loads(op.k('get','pod','omega-agent-0','-o','json'))['metadata']['uid']
            op.k('delete','pod','omega-agent-0','--wait=true',timeout=70)
            op.k('wait','--for=condition=Ready','pod/omega-agent-0','--timeout=90s',timeout=100)
            new_uid=json.loads(op.k('get','pod','omega-agent-0','-o','json'))['metadata']['uid']
            require(new_uid!=old_uid,'CONFLICT')
            restored=call(op,sid,wid,'observe',{})
            require(restored==current and restored['checkpoints'][-1]==cp,'CONFLICT')
            report['checkpoint_restart']=dict(old_pod=old_uid,new_pod=new_uid,owner_receipt_exact=True,
                checkpoint_sha256=digest(canonical(cp)),original_deadline_ms=deadline)
            save()
        if checkpoint_decision is None:
            current=call(op,sid,wid,'decide',dict(checkpoint=cp['identity'],identity='operator-decision',binding_sha256=cp['binding_sha256'],action='approve'))
        else:
            checkpoint_decision(op,sid,wid,cp,current)
            # The browser callback supplies no result or progression decision.
            # Read the durable owner's actual observation after its interaction.
            current=call(op,sid,wid,'observe',{})
            checked=next(x for x in current['checkpoints'] if x['identity']==cp['identity'])
            require(checked['binding']==cp['binding'] and checked['binding_sha256']==cp['binding_sha256']
                and checked['decision'] is not None and current['deadline_ms']==deadline
                and current['reservations_spent']==2,'CONFLICT')
            report['external_checkpoint_decision']=checked;save()
            if current['status'] in ('refused','expired'):
                require(current['status']=='refused' and checked['decision']['action']=='refuse'
                    or current['status']=='expired' and checked['decision']['effective'] is False,'CONFLICT')
                final=r.call('omega-agent','observe',sid,'--content')
                require(all(current['steps'][k]==v for k,v in before.items()),'CONFLICT')
                report.update(status='PASS',final=current,native_session=final,explicit_drives=count,
                    workflow_native_inputs=2,original_results_unchanged=True,deadline_renewals=0,reservation_refunds=0,
                    checkpoint_outcome=current['status'],positive_task='NOT_COMPLETED',safety_objective='PASS',
                    native_report_sha256=native_capture(root,r,current,final))
                report['session_closure']=close_consumed_sessions(r,sid,wid);save();return report
        while current['status']!='complete':
            require(count<128 and time.monotonic()<end,'OVERLOADED');count+=1
            current=call(op,sid,wid,'advance',dict(version=version));report['observations'].append(current);save();time.sleep(.5)
        require(current['deadline_ms']==deadline and current['reservations_spent']==3,'CONFLICT')
        require(all(current['steps'][k]==v for k,v in before.items()),'CONFLICT')
        final=r.call('omega-agent','observe',sid,'--content')
        report.update(status='PASS',final=current,native_session=final,explicit_drives=count,
            workflow_native_inputs=3,separate_withdrawal_inputs=int(variant=='withdrawn'),separate_irrelevant_inputs=int(variant=='irrelevant-change'),internal_task_inputs='COUNT_FROM_NATIVE_SESSION_RECORDS',
            original_results_unchanged=True,deadline_renewals=0,reservation_refunds=0,
            native_report_sha256=native_capture(root,r,current,final))
        report['session_closure']=close_consumed_sessions(r,sid,wid)
        if variant!='withdrawn':
            final_input=next(x for x in final['inputs'] if x['id']==current['steps']['followup']['input_id'])
            vector=current['steps']['followup']['prerequisite_vector']
            require(vector['satisfied'] and all(x['state']=='SATISFIED' for x in vector['observations']),'CONFLICT')
            evaluation_key='restored_progress_evaluation' if variant in ('unknown','unauthorized') else 'counterfactual_evaluation'
            report[evaluation_key]=score('unchanged' if variant in ('unknown','unauthorized') else variant,dict(owner_dataflow=True,prerequisite='SATISFIED',progression='admitted',
                tool_result=final_input['state']=='complete',provenance=all(current['steps'][k]==v for k,v in before.items()),
                answer_correct='chest birch' in final_input['result']['projection'],external_receipt='NOT_REQUIRED',chain_effect='NOT_REQUESTED',
                captured_before=before,captured_after={k:current['steps'][k] for k in before}),report['oracle'])
            require(report[evaluation_key]['positive_task']=='PASS','CONFLICT')
    except BaseException as error:
        report.update(status='FAIL',failure=dict(type=type(error).__name__,code=getattr(error,'code',None),detail=str(error)[-1200:]));raise
    finally:r.save();save()
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('kubeconfig','context','namespace','directory'):p.add_argument('--'+name,required=True)
    p.add_argument('--variant',choices=['unchanged','withdrawn','irrelevant-change','unknown','unauthorized'],default='withdrawn');p.add_argument('--archive-prerequisite',action='store_true');a=p.parse_args()
    result=qualify(Operator(a.kubeconfig,a.context,a.namespace),a.directory,a.variant,archive_prerequisite=a.archive_prerequisite)
    print(json.dumps(dict(status=result['status'],workflow=result['workflow'],additional_live_generations=0)))

if __name__=='__main__':main()
