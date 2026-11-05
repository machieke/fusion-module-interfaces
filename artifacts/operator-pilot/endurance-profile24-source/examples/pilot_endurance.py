"""Four finite operational windows on one retained native installation.

Recorded proposals select commands; real native tools produce every result.
Registry observations are counted separately from meaningful native inputs.
No journal reset, replacement session or failed-input retry is implemented.
"""
import argparse,json,time,uuid
from pathlib import Path
from fusion.contracts import canonical,digest,require
from integration.single_node.reference_ops import Operator,PYTHON
from integration.single_node.placement import verify_installed
from examples.integrated_sustained import IntegratedRunner

PROFILE='four-window-native-operator-pilot/1'
NAL_DEDUCTION='metta (Truth_Deduction (stv 0.8 0.9) (stv 0.7 0.8))'


def frozen():
    return dict(profile=PROFILE,windows=4,native_operator_inputs=160,
        per_window=40,agents=2,concurrent_native_inputs=1,maximum_seconds=7200,
        scopes=['shared','private','shared','private'],
        registry_observation_rounds_per_window=8,registry_maximum_providers_per_role=24,
        model='RECORDED_COMMAND_PROPOSALS',embedding='REAL_E5',vector='REAL_CHROMA',
        payload='REAL_DETTA',additional_live_generations=0,
        commands=['remember','query','episodes','support','support duplicate','contradict',
            'query belief','promote','query priority','demote','link','unlink',
            'write-file','append-file','read-file','pin','task-context','named NAL',
            'retained query','episodes'],
        maintenance=['real readiness observations','exact Registry epoch preview/apply',
            'closed-session derived cache preview/apply','current capacity','early captured reads'],
        private_workspace_substitution=['pin review','task-context','pin countercheck','task-context','unpin countercheck'],
        private_nal_substitution=['task-context','query retained memory'],
        shared_post_delegation=[
            dict(window=0,operation='inspect-atom',profile='synthetic-agent-retrieval-artifact/1'),
            dict(window=2,operation='metta',profile='neoclaw-nal-truth-deduction/1',command=NAL_DEDUCTION)],
        inter_window_recipe=dict(profile='knowledge-handoff/1',variants=['unchanged','withdrawn','unchanged'],
            expected_recipe_native_inputs=9,expected_direct_native_inputs=1,
            internal_completion_inputs='COUNT_ACTUAL_SEPARATELY'),
        refunds=0,original_deadline_changes=0,reset=False)


def registry(r,role,operation,provider=None,identity=None,head=None):
    args=['--provider-action',operation]
    if provider:args+=['--provider',provider]
    if identity:args+=['--identity',identity]
    if head:args+=['--head',head]
    return r.call(role,'providers',None,*args)


def cleanup(op,role,session,programme_end,progress=None):
    script='import json,sys;from integration.single_node.pilot_derived_maintenance import request;print(json.dumps(request(json.load(sys.stdin))))'
    def call(operation,body):
        remaining=(until if operation=='inventory' else programme_end)-time.monotonic()
        require(remaining>0,'DEADLINE_EXCEEDED')
        return json.loads(op.k('exec','-i',role+'-0','--',PYTHON,'-c',script,
            data=json.dumps(dict(operation=operation,session=session,body=body)),timeout=min(40,remaining)))
    # Closing a session commits its state before the resident worker exits.
    # Observe that boundary within the existing run limit; never retry apply.
    until=min(programme_end,time.monotonic()+30)
    observations=0
    while True:
        require(time.monotonic()<until,'DEADLINE_EXCEEDED')
        observations+=1
        try:
            inventory=call('inventory',{})
            break
        except RuntimeError as error:
            if 'NOT_AVAILABLE' not in str(error):raise
            time.sleep(min(.5,max(0,until-time.monotonic())))
    # The owner supplies only reconstructible candidates; never list a foreign
    # database or assume a returned payload is a deletable filesystem path.
    if progress is not None:progress('inventory',inventory)
    selection=inventory['selection']
    if not (selection['overlays'] or selection['materializations'] or selection['duplicate_startup']):
        return dict(inventory=inventory,status='NO_ELIGIBLE_DERIVED_CANDIDATE',
            inventory_observations=observations,apply_calls=0)
    plan=call('plan',selection)
    if progress is not None:progress('plan',plan)
    applied=call('apply',dict(plan=plan,identity='window-cleanup-'+session))
    if progress is not None:progress('apply',applied)
    replay=call('observe',dict(plan=plan,identity='window-cleanup-'+session))
    require(applied==replay,'CONFLICT')
    return dict(inventory=inventory,plan=plan,result=applied,replay_exact=True,
        inventory_observations=observations,apply_calls=1)


def target_belief(current,handle):
    view=current['retained']['view']
    identities=[key for key,value in view['handles'].items() if value['envelope']['handle']==handle]
    require(len(identities)==1,'NOT_AVAILABLE')
    bindings=[b for b in view['beliefs'] if b['uuid']==identities[0]]
    require(len(bindings)==1,'NOT_AVAILABLE');binding=bindings[0]
    observations=[b for b in current['beliefs'] if b['claim']==binding['claim'] and b['context']==binding['context']]
    require(len(observations)==1,'NOT_AVAILABLE')
    return observations[0]


def dispatch_new_peer_task(r,window,query,role,index):
    # A long native window can outlive an earlier readiness observation. Take
    # a separately identified observation immediately before the NEW peer
    # selection, never refresh a binding or retry an already accepted task.
    r.admit_selection('omega-agent-b','pilot-peer-window-'+str(window),'shared')
    return r.object(r.run('delegate B '+query,role,index))


def post_delegation(r,workload,window,task,role,index):
    # The retained corpus can exceed the existing three-observation artifact
    # domain in later windows. Select the declared operation before execution;
    # never truncate a result, retry an inspection, or fall back after failure.
    choices=workload['shared_post_delegation']
    require(choices==frozen()['shared_post_delegation'],'CONFLICT')
    selected=[item for item in choices if item['window']==window]
    require(len(selected)==1 and role=='omega-agent','UNSUPPORTED_PROFILE')
    selected=selected[0]
    command='inspect-atom '+task if selected['operation']=='inspect-atom' else selected['command']
    return r.run(command,role,index)


def qualify(op,plan,directory):
    root=Path(directory);root.mkdir(parents=True,exist_ok=False)
    workload=frozen();(root/'workload.json').write_bytes(canonical(workload))
    report=dict(profile=PROFILE,status='RUNNING',namespace=op.namespace,
        workload_sha256=digest(canonical(workload)),windows=[],native_inputs=0,
        additional_live_generations=0,live_model='NOT_RUN')
    def save():(root/'report.json').write_bytes(canonical(report))
    end=time.monotonic()+workload['maximum_seconds'];early=[];save()
    try:
        report['preflight']=verify_installed(plan,op);save()
        for window,template in enumerate(workload['scopes']):
            require(time.monotonic()<end,'DEADLINE_EXCEEDED')
            r=IntegratedRunner(op,root/('window-'+str(window)),maximum_inputs=40,legacy_crossing_required=False)
            r.end=end;row=dict(window=window,template=template,status='RUNNING',maintenance=[],readiness=[],captures=[])
            report['windows'].append(row);save()
            for role in ('omega-agent','omega-agent-b'):
                index=r.allocate(role,'pilot-window-'+str(window),template);sid=r.ids[role][index]
                providers=[x['provider'] for x in r.report['selection_admissions'][-1]['providers']]
                require(len(providers)<=workload['registry_maximum_providers_per_role'],'OVERLOADED')
                for cycle in range(workload['registry_observation_rounds_per_window']):
                    for key in providers:
                        value=registry(r,role,'probe',key,'window-'+str(window)+'-observation-'+str(cycle)+'-'+key)
                        require(value['status']=='ready','NOT_AVAILABLE')
                        row['readiness'].append(dict(role=role,provider=key,round=cycle,value=value))
                    save()
                token=('amber','cobalt','saffron','violet')[window]+' '+('parcel' if role=='omega-agent' else 'prism')
                box=('birch','cedar','alder','maple')[window]
                query='synthetic '+token+' storage'
                fact='The synthetic '+token+' is stored in chest '+box
                memory=r.object(r.run('remember '+fact,role,index))['memory']['handle']
                answer=r.run('query '+query,role,index);require('chest '+box in answer,'CONFLICT')
                episode=r.object(r.run('episodes current',role,index))
                source=next(x['body']['source']['handle'] for x in episode['events'] if x['kind']=='external-observation')
                revisions=[r.run(command+' '+memory+' '+source,role,index) for command in ('support','support','contradict')]
                require('REVISION-SUCCESS' in revisions[0] and 'retained-alternative' in revisions[2],'CONFLICT')
                before=r.run('query '+query,role,index)
                belief_before=target_belief(r.current(role,index),memory)
                r.run('promote '+memory,role,index)
                after=r.run('query '+query,role,index)
                belief_after=target_belief(r.current(role,index),memory)
                # Promotion may legitimately reorder native query candidates.
                # Compare the exact claim's owned revision, not STV positions.
                require(belief_before==belief_after,'CONFLICT')
                row.setdefault('priority_observations',[]).append(dict(role=role,
                    before_query=before,after_query=after,belief_before=belief_before,
                    belief_after=belief_after,belief_snapshot_exact=True))
                r.run('demote '+memory,role,index)
                relation=r.object(r.run('link '+memory+' '+source,role,index))['relation']['handle']
                r.run('unlink '+relation,role,index)
                local_commands=('write-file window.txt Synthetic '+token+' review',
                        'append-file window.txt Priority and truth remain separately owned',
                        'read-file window.txt','pin review Retain '+token+' original result','task-context') if template=='shared' else (
                        'pin review Retain '+token+' original result','task-context',
                        'pin countercheck Priority is not evidence','task-context','unpin countercheck')
                for command in local_commands:
                    r.run(command,role,index)
                if template=='shared' and role=='omega-agent':
                    task=dispatch_new_peer_task(r,window,query,role,index)
                    until=min(end,time.monotonic()+max(0,(task['deadline']-time.time()*1000)/1000)+8)
                    while True:
                        received=r.call(role,'observe',sid,'--content')
                        returned=[x for x in received['inputs'] if x['assignment']=='delegated-result' and x['deadline']==task['deadline']]
                        if (returned and returned[0]['state']=='complete') or time.monotonic()>until:break
                        time.sleep(1)
                    require(returned and returned[0]['state']=='complete','NOT_AVAILABLE')
                    row.setdefault('delegations',[]).append(dict(task=task,returned=returned[0]))
                    post_delegation(r,workload,window,task['task'],role,index)
                else:
                    r.run(NAL_DEDUCTION if template=='shared' else 'task-context',role,index)
                    r.run('query '+query,role,index)
                r.run('episodes current',role,index)
                require(r.count in (20,40),'CONFLICT')
                row['captures'].append(dict(role=role,session=sid,first=r.report['inputs'][-20],priority_truth_preserved=True))
                if window==0:early.append(dict(role=role,session=sid,first=r.report['inputs'][-20]))
                r.close(role,index)
                row['maintenance'].append(dict(role=role,kind='derived',value=cleanup(op,role,sid,end)))
                seals=[]
                for key in providers:
                    preview=registry(r,role,'plan',key)
                    seals.append(registry(r,role,'seal',key,'window-'+str(window)+'-epoch-'+key,preview['head']))
                row['maintenance'].append(dict(role=role,kind='registry',epochs=seals,headroom=registry(r,role,'headroom')))
                row.setdefault('capacity',[]).append(dict(role=role,value=r.call(role,'capacity')))
                save()
            # Task-created sessions are closed only after their actual work is
            # captured; every input and spent reservation remains retained.
            for role in ('omega-agent','omega-agent-b'):
                for item in r.call(role,'list'):
                    if item['state']!='active':continue
                    actual=r.call(role,'observe',item['session'],'--content')
                    require(all(x['state']=='complete' for x in actual['inputs']),'NOT_AVAILABLE')
                    r.call(role,'close',item['session'],'--identity','window-close-'+item['session'])
            for item in early:
                observation=r.call(item['role'],'observe',item['session'],'--content')
                first=next(x for x in observation['inputs'] if x['id']==item['first']['identity'])
                require(first==item['first']['observed'],'CONFLICT')
            row.update(status='PASS',native_inputs=r.count,early_captures_exact=True,
                report_sha256=digest((r.root/'report.json').read_bytes()))
            report['native_inputs']+=r.count;save()
            if window<3:
                from examples.pilot_window_workflow import between_windows
                report.setdefault('inter_window_workflows',[]).append(between_windows(op,root/('boundary-'+str(window)),window,end))
                save()
        require(report['native_inputs']==160,'CONFLICT')
        final=[m['headroom'] for m in report['windows'][-1]['maintenance'] if m['kind']=='registry']
        require(any(x['baseline_equivalent']['bytes']>1048576 for x in final),'NOT_AVAILABLE')
        report.update(status='PASS',baseline_ceiling_crossed=True,windows_completed=4,
            old_captures_exact=True,no_state_reset=True,refunds=0,deadline_changes=0)
    except BaseException as error:
        report.update(status='FAIL',failure=dict(type=type(error).__name__,code=getattr(error,'code',None)))
        raise
    finally:save()
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('kubeconfig','context','namespace','plan','directory'):p.add_argument('--'+name,required=True)
    a=p.parse_args();result=qualify(Operator(a.kubeconfig,a.context,a.namespace),json.loads(Path(a.plan).read_bytes()),a.directory)
    print(json.dumps(dict(status=result['status'],native_inputs=result['native_inputs'],additional_live_generations=0)))


if __name__=='__main__':main()
