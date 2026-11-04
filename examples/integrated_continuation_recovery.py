"""Cold native graph recovery on retained owner PVCs; no effect reconstruction.

Two deliberate new inspect occurrences use one previously consumed native task.
A caller pause after acceptance and a lost provider reply each precede real pod
replacement. Captured model proposals stay recorded; no live generation exists.
"""
import argparse,json,time,uuid
from pathlib import Path
import yaml
from fusion.contracts import canonical,require,digest
from integration.single_node.reference_ops import Operator
from integration.single_node.sustained_qualification import Runner
from integration.single_node.preview_recovery_qualification import Recovery


def qualify(op,values,chart,directory,resume_from=None,selected_case=None):
    root=Path(directory);root.mkdir(parents=True,exist_ok=False);r=Runner(op,root/'native');r.end=time.monotonic()+1200
    r.report.update(maximum_operator_inputs=4 if selected_case else 5,scenario='native-fixed-continuation-pod-recovery')
    fault=Recovery.__new__(Recovery);fault.op=op;fault.values_path=Path(values);fault.values=yaml.safe_load(Path(values).read_bytes());fault.chart=chart
    require('resident_worker' not in fault.values['preview']['sustained'],'UNSUPPORTED_PROFILE')
    report=dict(status='RUNNING',additional_live_generations=0,model='RECORDED_PROPOSALS',
        native_worker='historical bounded cold quantum; resident uncertain-assignment gate remains fenced',cases=[])
    def save():(root/'report.json').write_bytes(canonical(report))
    save()
    try:
        op.owned();report['images']={x['metadata']['name']:x['spec']['template']['spec']['containers'][0]['image'] for x in op.workloads()};save()
        require(selected_case in (None,'accepted-caller-kill','lost-acceptance-reply'),'INVALID_ARGUMENT')
        if selected_case=='lost-acceptance-reply':
            # Arm before accepting the parent task. Helm rollout time must not
            # spend most of that task's original120s before the fault occurs.
            # Native remember/delegate do not invoke inspection.submit.
            fault.arm('fusion-execution','drop_response_operation','submit')
            report['lost_reply_armed_before_parent_task']=True;save()
        if resume_from:
            prior=Path(resume_from);raw=(prior/'report.json').read_bytes();saved=json.loads(raw);native=json.loads((prior/'native/report.json').read_bytes())
            require(saved['status']=='FAIL' and native['namespace']==op.namespace and len(native['inputs'])==2 and
                all('accepted' not in x for x in saved['cases']),'CONFLICT')
            allocation=native['allocations'][0];sid=allocation['value']['session'];index=0;r.ids={'omega-agent':[sid]}
            r.report['allocations']=native['allocations'];r.report['inputs']=native['inputs'];r.count=2
            observed=r.call('omega-agent','observe',sid,'--content')
            for original in native['inputs']:
                require(next(x for x in observed['inputs'] if x['id']==original['identity'])==original['observed'],'CONFLICT')
            task=saved['task'];report.update(task=task,task_result=saved['task_result'],resumed_report_sha256=digest(raw),
                original_captures_identical=True,original_operator_inputs_not_repeated=True)
        else:
            index=r.allocate('omega-agent','recovery-A');sid=r.ids['omega-agent'][index]
            r.run('remember The synthetic cedar marker is stored in chest willow',session=index)
            task=r.object(r.run('delegate B synthetic cedar marker storage',session=index));report['task']=task;save()
            until=min(r.end,time.monotonic()+max(0,(task['deadline']-time.time()*1000)/1000)+8)
            while True:
                observed=r.call('omega-agent','observe',sid,'--content')
                results=[x for x in observed['inputs'] if x['assignment']=='delegated-result' and x['deadline']==task['deadline']]
                if results and results[0]['state']=='complete':break
                require(time.monotonic()<until,'NOT_AVAILABLE');time.sleep(.5)
            report['task_result']=results[0]
        save();r.save()
        for name,owner,knob,stage in [('accepted-caller-kill','omega-agent','pause_at','after_inspect_acceptance_capture'),
                ('lost-acceptance-reply','fusion-execution','drop_response_operation','submit')]:
            if selected_case and name!=selected_case:continue
            case=dict(name=name);report['cases'].append(case);save()
            marker=('response-dropped.json' if selected_case=='lost-acceptance-reply' else fault.arm(owner,knob,stage))
            key='continuation-recovery-'+str(uuid.uuid4())
            command='inspect-atom '+task['task'];r.count+=1
            entry=dict(role='omega-agent',session=sid,identity=key,command=command,started_ms=time.time_ns()//1000000)
            r.report['inputs'].append(entry);r.save()
            accepted=r.call('omega-agent','submit',sid,'--identity',key,'--text',command,'--assignment','synthetic-task')
            case['accepted']=accepted;entry['accepted']=accepted;save();r.save()
            until=min(r.end,time.monotonic()+max(0,(accepted['deadline']-time.time()*1000)/1000)+8)
            while True:
                fired=fault.read(owner,marker)
                if fired:break
                require(time.monotonic()<until,'NOT_AVAILABLE');time.sleep(.25)
            case['fault']=fired;case['caller_before']=fault.accounting('omega-agent',sid,key);case['model_before']=fault.model_accounting(sid)
            occurrence=case['caller_before'][0]['id']
            case['continuation_before']=r.call('omega-agent','continuation',sid,'--occurrence',occurrence);save()
            # Replace the caller and executor, retaining each independent PVC.
            case['replacement']=fault.replace(('omega-agent','fusion-execution'));save()
            while True:
                observed=r.call('omega-agent','observe',sid,'--content');row=next(x for x in observed['inputs'] if x['id']==key)
                if row['state']=='complete' or time.monotonic()>until:break
                time.sleep(.5)
            case['observed']=row;entry.update(observed=row,finished_ms=time.time_ns()//1000000);r.save();save()
            case['caller_after']=fault.accounting('omega-agent',sid,key);case['model_after']=fault.model_accounting(sid)
            case['continuation_after']=r.call('omega-agent','continuation',sid,'--occurrence',occurrence);save()
            require(row['state']=='complete' and row['deadline']==accepted['deadline'] and row['accepted']==accepted['accepted'],'NOT_AVAILABLE')
            require(case['model_after']==case['model_before'],'CONFLICT')
            before,after=case['continuation_before'],case['continuation_after']
            require(after['status']=='return-ready' and before['deadline_ms']==after['deadline_ms'] and
                before['relay_calls_spent']<=after['relay_calls_spent']<=32,'CONFLICT')
            require(all(after['steps'][k]==v for k,v in before['steps'].items()),'CONFLICT')
            for old in case['caller_before']:
                current=next(x for x in case['caller_after'] if x['id']==old['id'])
                require(current['deadline']==old['deadline'] and old['attempts']<=current['attempts']<=2,'CONFLICT')
            duplicate=r.call('omega-agent','submit',sid,'--identity',key,'--text',command,'--assignment','synthetic-task')
            require(duplicate['deadline']==accepted['deadline'] and duplicate['sequence']==accepted['sequence'] and duplicate['state']=='complete','CONFLICT')
            case.update(status='PASS',duplicate_receipt=duplicate,inspection=r.object(row['result']['projection']),deadline_renewals=0,model_regenerations=0);save()
        r.run('task-context',session=index)
        report.update(status='PASS',operator_native_inputs=r.count,native_report_sha256=digest((r.root/'report.json').read_bytes()))
    except BaseException as error:report.update(status='FAIL',failure=dict(type=type(error).__name__,code=getattr(error,'code',None)));raise
    finally:r.save();op.quiesce();report['quiesced']=True;save()
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('kubeconfig','context','namespace','directory','values','chart'):p.add_argument('--'+name,required=True)
    p.add_argument('--resume-from')
    p.add_argument('--case',choices=['accepted-caller-kill','lost-acceptance-reply'])
    a=p.parse_args();v=qualify(Operator(a.kubeconfig,a.context,a.namespace),a.values,a.chart,a.directory,a.resume_from,a.case);print(json.dumps(dict(status=v['status'],additional_live_generations=0)))
