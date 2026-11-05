"""Installed native execution of the other two registered workflow recipes.

Commands originate only in recorded proposals through the existing application
input port. Captures and references are read from actual owner observations;
operator code never substitutes a tool result or executes the workflow itself.
"""
import argparse,json,time,uuid
from pathlib import Path
from fusion.contracts import canonical,digest,require
from fusion.workflow_recipes import evidence_review,artifact_delivery,native_object,render
from fusion.workflow_prerequisites import KINDS
from integration.single_node.reference_ops import Operator
from examples.integrated_sustained import IntegratedRunner as Runner
from examples.pilot_workflows import call,native_capture,close_consumed_sessions,await_delegation
from integration.single_node.pilot_workflow_evaluation import freeze,score


def selected_checkpoint(current,identity):
    """Owner observations do not promise checkpoint enumeration order."""
    matches=[x for x in current['checkpoints'] if x['identity']==identity]
    require(len(matches)==1 and matches[0]['binding']['identity']==identity,'CONFLICT')
    return matches[0]


def qualify(op,directory,recipe,*,retain_for_chain=False,representation='full-projection'):
    require(recipe in ('evidence-aware-review/1','approved-artifact-delivery/1'))
    require(type(retain_for_chain) is bool and (not retain_for_chain or recipe=='approved-artifact-delivery/1'),'INVALID_ARGUMENT')
    require(representation in ('full-projection','reference-document') and
        (representation=='full-projection' or recipe=='approved-artifact-delivery/1'),'INVALID_ARGUMENT')
    root=Path(directory);root.mkdir(parents=True,exist_ok=False)
    r=Runner(op,root/'native',maximum_inputs=12)
    report=dict(status='RUNNING',recipe=recipe,classification='RECORDED_MODEL_REAL_NATIVE_TOOLS',
        model='RECORDED_PROPOSALS',representation=representation,additional_live_generations=0,observations=[],oracle=freeze(),chain='SEPARATE_EXACT_RESULT_APPROVAL_NOT_IMPLICIT')
    def save():r.save();(root/'report.json').write_bytes(canonical(report))
    end=time.monotonic()+900;r.end=end;count=0
    report['qualification_end_ms']=time.time_ns()//1000000+900000;save()
    try:
        op.owned();report['images']={x['metadata']['name']:x['spec']['template']['spec']['containers'][0]['image'] for x in op.workloads()};save()
        if recipe=='approved-artifact-delivery/1':r.admit_selection('omega-agent-b','recipient-'+str(uuid.uuid4()))
        index=r.allocate('omega-agent','recipe-'+str(uuid.uuid4()));sid=r.ids['omega-agent'][index];wid=str(uuid.uuid4())
        if recipe=='evidence-aware-review/1':
            r.run('task-context',session=index);r.run('task-context',session=index)
            page=r.object(r.run('episodes current',session=index))
            sources=[x['body']['source']['handle'] for x in page['events'] if x['kind']=='external-observation']
            for _ in range(3):
                if len(set(sources))>=2 or not page.get('next_selector'):break
                page=r.object(r.run('episodes '+page['next_selector'],session=index))
                sources.extend(x['body']['source']['handle'] for x in page['events'] if x['kind']=='external-observation')
            sources=list(dict.fromkeys(sources));require(len(sources)>=2,'NOT_AVAILABLE')
            plan=evidence_review('The synthetic silver token is held in case beech',sources[0],sources[1],
                'synthetic silver token location',dict(id='review-memory',from_capture='remember',kind='memory-active'))
            target=2;report['source_handles']=sources[:2]
        else:
            # Actual native setup writes the generated fact; only a query is delegated.
            setup=r.object(r.run('remember The synthetic silver token is held in case beech',session=index))
            report['setup']=setup;plan=artifact_delivery('synthetic silver token location','review.txt');target=2
        deadline=time.time_ns()//1000000+900000
        current=call(op,sid,wid,'admit',dict(recipe=recipe,steps=plan,deadline_ms=deadline))
        report.update(session=sid,workflow=wid,accepted=current);save()
        def advance_until(number,version):
            nonlocal current,count
            while len([x for x in current['steps'].values() if x['result_sha256']])<number:
                require(count<192 and time.monotonic()<end,'OVERLOADED');count+=1
                try:current=call(op,sid,wid,'advance',dict(version=version))
                except RuntimeError:
                    # A bounded observation never creates another native occurrence.
                    # Record the failed control exchange; owner state decides recovery.
                    report.setdefault('control_failures',[]).append(dict(operation='advance',drive=count))
                    current=call(op,sid,wid,'observe',{})
                report['observations'].append(current);save();time.sleep(.5)
        if recipe=='approved-artifact-delivery/1':
            # Stop at the captured delegation. Validate the complete existing
            # inspection domain before admitting either remaining effect.
            from examples.pilot_artifact_reference import capture,inspection_preflight,suffix,retrieved_setup
            advance_until(1,1)
            observed=r.call('omega-agent','observe',sid,'--content')
            delegated=next(x for x in observed['inputs'] if x['id']==current['steps']['delegate']['input_id'])
            publication=native_object(delegated['result'])
            report['delegated_result_consumption'],_=await_delegation(r,sid,publication,end)
            source=capture(r,sid,publication,deadline);report['artifact_source']=source;save()
            report['retrieval_evaluation']=retrieved_setup(report['setup'],source);save()
            source=inspection_preflight(op,sid,source,deadline);report['artifact_source']=source;save()
            if representation=='reference-document':
                current=call(op,sid,wid,'amend',dict(identity='select-explicit-reference-document',version=1,
                    suffix=suffix(source,plan),cause='explicit reference document; full captured projection retained and existing inspection envelope unchanged'))
                report['representation_amendment']=current;save()
                current=call(op,sid,wid,'checkpoint',dict(identity='reference-document-review',version=current['version'],
                    reason='approve exact reference document and validated original inspection envelope'))
                cp=selected_checkpoint(current,'reference-document-review');report['representation_checkpoint']=cp;save()
                current=call(op,sid,wid,'decide',dict(checkpoint=cp['identity'],identity='approve-reference-document',
                    binding_sha256=cp['binding_sha256'],action='approve'))
            else:
                # Historical representation stays exact. Oversize content is
                # a typed refusal, never truncation or repeated opaque drives.
                render(plan[1],{'delegate':dict(delegated['result'],_task_result=source['result']['projection'])})
            advance_until(target,current['version'])
        else:advance_until(target,1)
        before=current['steps']
        if recipe=='evidence-aware-review/1':
            owners=r.current('omega-agent',index);report['cognitive_before_contrary']=owners
            candidates=[x for x in owners.get('beliefs',[]) if x['truth'] is not None and len(x['observations'])==1]
            require(len(candidates)==1,'NOT_AVAILABLE');belief=candidates[0]
            # Freeze the actual owner value before contrary evidence; this is
            # a version predicate, never a replacement numerical computation.
            guard=dict(id='supported-value-still-current',kind='belief-predicate',policy=KINDS['belief-predicate'],
                scope=owners['scope'],target={k:belief[k] for k in ('claim','context','runtime_selection')},
                predicate=dict(field='strength',comparison='eq',value=belief['truth']['strength']))
            suffix=[*plan[2:-1],{**plan[-1],'guards':[guard]}]
            current=call(op,sid,wid,'amend',dict(identity='bind-observed-supported-value',version=1,suffix=suffix,
                cause='freeze actual supported belief as prerequisite before contrary assessment'))
            advance_until(4,current['version']);before=current['steps']
            owners=r.current('omega-agent',index);report['cognitive_after_contrary_and_priority']=owners
            candidates=[x for x in owners.get('beliefs',[]) if x['claim']==belief['claim'] and x['context']==belief['context']]
            require(len(candidates)==1 and len(candidates[0]['observations'])==2,'NOT_AVAILABLE')
            require(candidates[0]['truth']['strength']!=belief['truth']['strength'],'NOT_AVAILABLE')
            current=call(op,sid,wid,'advance',dict(version=current['version']))
            require(current['status']=='prerequisite-held' and current['reservations_spent']==4,'CONFLICT')
            require(current['latest_prerequisites']['observations'][0]['state']=='INVALID','CONFLICT')
            report['counterfactual_hold']=current
            report['counterfactual_evaluation']=score('contradicted',dict(owner_dataflow=True,prerequisite='INVALID',
                progression='held',tool_result=None,provenance=all(current['steps'][k]==v for k,v in before.items()),
                answer_correct=None,external_receipt='NOT_REQUIRED',chain_effect='NOT_REQUESTED',
                captured_before=before,captured_after=current['steps']),report['oracle'])
            require(report['counterfactual_evaluation']['safety_objective']=='PASS','CONFLICT')
            current=call(op,sid,wid,'amend',dict(identity='review-retained-contrary-assessments',version=current['version'],
                suffix=[plan[-1]],cause='explicitly permit query of retained contrary assessments after numerical premise changed'))
        version=current['version']
        current=call(op,sid,wid,'checkpoint',dict(identity='bounded-review',version=version,reason='review exact accepted suffix and owner observations'))
        checkpoint=selected_checkpoint(current,'bounded-review');report['checkpoint']=checkpoint;save()
        current=call(op,sid,wid,'decide',dict(checkpoint=checkpoint['identity'],identity='approve-bounded-suffix',
            binding_sha256=checkpoint['binding_sha256'],action='approve'))
        advance_until(len(plan),version)
        current=call(op,sid,wid,'advance',dict(version=version))
        require(current['status']=='complete' and current['deadline_ms']==deadline and current['reservations_spent']==len(plan),'CONFLICT')
        require(all(current['steps'][k]==v for k,v in before.items()),'CONFLICT')
        final=r.call('omega-agent','observe',sid,'--content')
        final_input=current['steps'][plan[-1]['node']]['input_id'];captured=next(x for x in final['inputs'] if x['id']==final_input)
        require(captured['state']=='complete' and captured['result'] is not None,'CONFLICT')
        if recipe=='evidence-aware-review/1':
            require('case beech' in captured['result']['projection'],'CONFLICT')
            final_evidence=dict(query_result=captured['result'],current_owners=r.current('omega-agent',index))
        else:
            result=native_object(captured['result']);require(result['status']=='INSPECTED_ARTIFACT' and result['caller_acknowledged'] is True and result['chain']=='NOT_SUBMITTED','CONFLICT')
            final_evidence=dict(inspection=result,chain='NOT_SUBMITTED_WITHOUT_SEPARATE_EXACT_RESULT_APPROVAL')
        report.update(status='PASS',final=current,native_session=final,evidence=final_evidence,explicit_drives=count,
            original_results_unchanged=True,deadline_renewals=0,reservation_refunds=0,
            native_report_sha256=native_capture(root,r,current,final))
        report['session_closure']=('RETAINED_FOR_SEPARATE_EXACT_RESULT_CHAIN_CONTINUATION' if retain_for_chain else
            close_consumed_sessions(r,sid,wid) if recipe=='approved-artifact-delivery/1' else [r.close('omega-agent',index)])
    except BaseException as error:
        report.update(status='FAIL',failure=dict(type=type(error).__name__,code=getattr(error,'code',None),detail=str(error)[-1200:]));raise
    finally:save()
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('kubeconfig','context','namespace','directory'):p.add_argument('--'+name,required=True)
    p.add_argument('--recipe',required=True,choices=['evidence-aware-review/1','approved-artifact-delivery/1'])
    p.add_argument('--representation',choices=['full-projection','reference-document'],default='full-projection');a=p.parse_args()
    result=qualify(Operator(a.kubeconfig,a.context,a.namespace),a.directory,a.recipe,representation=a.representation)
    print(json.dumps(dict(status=result['status'],workflow=result['workflow'],additional_live_generations=0)))
if __name__=='__main__':main()
