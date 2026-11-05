"""Eighty bounded native inputs on one retained synthetic installation.

Reuses the historical 70-input corpus/cognition/counterfactual qualification,
with archive/read continuity and ten additional warm private/shared inputs.
No answer-generating provider fixtures: recorded models echo proposed commands.
No reset, retiming or hidden resubmission, including when a scenario fails.
"""
import argparse,json,time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from fusion.contracts import canonical,digest,require
from integration.single_node.reference_ops import Operator,PYTHON
from integration.single_node.sustained_qualification import Runner
from integration.single_node.sustained_evaluation import workload,DATASETS
from integration.single_node.placement import verify_installed
from .integrated_archive import ARCHIVE


class IntegratedRunner(Runner):
    def admit_selection(self,role,identity,template='shared'):
        # Trusted operator action before a NEW selection. Readiness is not
        # inferred from pod health or silently renewed for accepted work.
        # Every probe has a fixed explicit identity and creates no business call.
        code='''import json,sys
from pathlib import Path
from fusion.contracts import require
from integration.single_node.integrated_registry import invoke,PROFILE
path=Path('/run/fusion/owner.json');cfg=json.loads(path.read_bytes())
selected=cfg['native_sessions'].get('provider_registry');results=[]
if selected:
 for key in selected['templates'][sys.argv[2]]:
  def call(operation):
   body={'provider':key}
   if operation!='inspect':body['identity']=sys.argv[1]+'/'+key+'/'+operation
   return invoke(path,cfg['principals']['operator']['credential'],dict(profile=selected['profile'],id='sustained-admission',operation=operation,body=body))['value']
  before=call('inspect');new=before['state']=='not-admitted'
  if new:call('add')
  else:require(before['state']=='enabled','NOT_AVAILABLE')
  probe=call('probe')
  if new:call('enable')
  results.append({'provider':key,'before':before,'readiness':probe,'after':call('inspect')})
print(json.dumps(results))'''
        admitted=json.loads(self.op.k('exec',role+'-0','--',PYTHON,'-c',code,identity,template,timeout=70))
        self.report.setdefault('selection_admissions',[]).append(dict(role=role,identity=identity,template=template,providers=admitted));self.save()

    def allocate(self,role,identity,template='shared'):
        self.admit_selection(role,identity,template)
        return super().allocate(role,identity,template)


def frozen():
    return dict(profile='integrated-retained-eighty-native/1',baseline=workload(),maximum_operator_inputs=80,
        maximum_seconds=3600,legacy_record_threshold='OBSERVED_NOT_REQUIRED_FOR_COMPACT_CAPTURE_PROFILE',
        extension=['shared:pin','private:pin','shared:task-context','private:task-context',
            'shared:query private absent fact','private:query shared absent fact','shared:named NAL',
            'shared:write-file','shared:append-file','shared:read-file'],
        maintenance=['copy-verify archive early native payload','storage pod replacement with retained PVC','exact original result readback'],
        private_canary='Q26_PRIVATE_NOTE_ONLY',shared_note='Q26_SHARED_NOTE_ONLY',
        live_generation_authority=0,model='RECORDED_COMMAND_PROPOSALS',physical_payloads='REAL_DETTA',embedding='REAL_E5',
        oracle='independent evaluator substrings and original native NAL; never supplied as provider results')


def qualify(op,plan,directory,resume_from=None,resume_handoff=None):
    root=Path(directory);root.mkdir(parents=True,exist_ok=False);selected=frozen();(root/'workload.json').write_bytes(canonical(selected))
    require(not (resume_from and resume_handoff),'CONFLICT');maximum=81 if resume_handoff else 80
    r=IntegratedRunner(op,root/'native',maximum_inputs=maximum,legacy_crossing_required=False);r.end=time.monotonic()+selected['maximum_seconds']
    r.report.update(frozen=dict(plan=selected,sha256=digest(canonical(selected))))
    report=dict(status='RUNNING',additional_live_generations=0,model='RECORDED_PROPOSALS',workload_sha256=digest(canonical(selected)))
    def save():r.save();(root/'report.json').write_bytes(canonical(report))
    save()
    try:
        report['preflight']=verify_installed(plan,op);save()
        if resume_handoff:
            previous=Path(resume_handoff);raw=(previous/'report.json').read_bytes();prior=json.loads(raw)
            native_raw=(previous/'native/report.json').read_bytes();native=json.loads(native_raw)
            require(prior['status']=='FAIL' and native['namespace']==op.namespace and len(native['inputs'])==43 and
                all(x['observed']['state']=='complete' for x in native['inputs']) and native['frozen']['plan']==selected,'CONFLICT')
            failed=native['scenarios'][-1];require(failed['scenario']=='two-agent-A-B' and not failed['passed'],'CONFLICT')
            require(time.time_ns()//1000000>=failed['task']['deadline'],'DEADLINE_EXCEEDED')
            original_end=native['inputs'][0]['started_ms']+selected['maximum_seconds']*1000
            remaining=(original_end-time.time_ns()//1000000)/1000;require(remaining>0,'DEADLINE_EXCEEDED')
            r.end=time.monotonic()+remaining;r.report=native;r.count=43;r.ids={}
            r.report.update(status='RUNNING',maximum_operator_inputs=maximum)
            for allocation in native['allocations']:r.ids.setdefault(allocation['role'],[]).append(allocation['value']['session'])
            for field in ('archive','retained_restart'):report[field]=prior[field]
            # The failed asynchronous task stays failed. Its deadline is not
            # replayed; a new operator workload occurrence uses a new sender
            # session, while every old capture and retained charge is preserved.
            report['workload_amendment']=dict(reason='Integrated registry ingress allocation defect; separate new handoff after source fix',
                previous_report_sha256=digest(raw),previous_native_report_sha256=digest(native_raw),original_inputs_not_repeated=43,
                maximum_operator_inputs=maximum,original_experiment_end_ms=original_end,failed_task_deadline=failed['task']['deadline'],
                failed_task_not_retried=True,namespace_reset=False,capacity_refunds=0)
            code='''import json,sqlite3
from pathlib import Path
cfg=json.loads(Path('/run/fusion/owner.json').read_bytes())['task_ingress']
with sqlite3.connect(Path(cfg['database']).as_uri()+'?mode=ro',uri=True) as db:
 rows=[dict(status=s,ack=a,original_deadline=json.loads(o)['record']['deadline'] if o else None) for s,a,o in db.execute('SELECT status,ack,origin FROM task_ingress ORDER BY rowid')]
print(json.dumps(rows))'''
            terminal=json.loads(op.k('exec','omega-agent-b-0','--',PYTHON,'-c',code))
            report['recipient_before_terminal_observation']=terminal;save()
            if len(terminal)==1 and terminal[0]['ack']==0:
                # Startup's single bounded drain may have observed a provider
                # still unavailable. One explicit current-authority hint after
                # preflight drains the original mailbox row; it sends no task
                # and cannot renew its expired business deadline.
                observe='''import json
from pathlib import Path
from fusion.preview_transport import invoke
from fusion.preview_tasks import PROFILE
cfg=json.loads(Path('/run/fusion/templates/shared/tasks.json').read_bytes())
print(json.dumps(invoke(cfg['recipients']['B'],'/preview/task-ingress',dict(profile=PROFILE,id='operator-observe-expired-registry-handoff'))))'''
                report['explicit_expired_handoff_drain']=json.loads(op.k('exec','omega-agent-0','--',PYTHON,'-c',observe,timeout=35));save()
                terminal=json.loads(op.k('exec','omega-agent-b-0','--',PYTHON,'-c',code))
            require(len(terminal)==1 and terminal[0]==dict(status='refused',ack=1,original_deadline=failed['task']['deadline']),'CONFLICT')
            report['retained_failed_handoff']=dict(status='FAIL',recipient_terminalization=terminal[0],
                native_tool_execution=0,original_sender_capture_unchanged=True,old_allocation_not_rebound=True)
            groups={}
            for item in native['inputs']:groups.setdefault((item['role'],item['session']),[]).append(item)
            for (role,sid),items in groups.items():
                observed={x['id']:x for x in r.call(role,'observe',sid,'--content')['inputs']}
                require(all(observed[x['identity']]==x['observed'] for x in items),'CONFLICT')
            # Empty historical allocations are closed, never rebound/deleted.
            for row in r.call('omega-agent-b','list'):
                if row['state']=='active' and row['session'] not in r.ids['omega-agent-b']:
                    observed=r.call('omega-agent-b','observe',row['session'],'--content');require(observed['inputs']==[],'CONFLICT')
                    r.call('omega-agent-b','close',row['session'],'--identity','close-unbound-'+row['session'])
            old_sender=native['inputs'][-1]['session']
            r.call('omega-agent','close',old_sender,'--identity','close-failed-handoff-source')
            a=r.allocate('omega-agent','handoff-after-registry-fix');r.admit_selection('omega-agent-b','peer-after-registry-fix')
            b=len(r.ids['omega-agent-b'])-1
            r.handoffs({'omega-agent':a,'omega-agent-b':b});r.private();r.counterfactual();require(r.count==71,'CONFLICT')
            shared=r.allocate('omega-agent','integrated-interleaved-shared');save()
        elif resume_from:
            previous=Path(resume_from);raw=(previous/'report.json').read_bytes();prior=json.loads(raw)
            native_raw=(previous/'native/report.json').read_bytes();native=json.loads(native_raw)
            require(prior['status']=='FAIL' and native['namespace']==op.namespace and len(native['inputs'])==70
                and all(x['observed']['state']=='complete' for x in native['inputs']) and native['frozen']['plan']==selected,'CONFLICT')
            r.report=native;r.report['status']='RUNNING';r.count=70;r.ids={}
            for allocation in native['allocations']:r.ids.setdefault(allocation['role'],[]).append(allocation['value']['session'])
            original_end=native['inputs'][0]['started_ms']+selected['maximum_seconds']*1000
            remaining=(original_end-time.time_ns()//1000000)/1000;require(remaining>0,'DEADLINE_EXCEEDED')
            r.end=time.monotonic()+remaining
            for field in ('archive','retained_restart'):report[field]=prior[field]
            report['resumed']=dict(report_sha256=digest(raw),native_report_sha256=digest(native_raw),
                original_experiment_end_ms=original_end,original_inputs_not_repeated=70,
                previous_plan_sha256=prior['preflight']['plan_sha256'],
                current_plan_sha256=report['preflight']['plan_sha256'],
                same_placement_plan=prior['preflight']['plan_sha256']==report['preflight']['plan_sha256'],
                current_admission_limits=plan['values']['preview']['sustained']['allocation'])
            groups={}
            for item in native['inputs']:groups.setdefault((item['role'],item['session']),[]).append(item)
            for (role,sid),items in groups.items():
                captured={x['id']:x for x in r.call(role,'observe',sid,'--content')['inputs']}
                require(all(captured[x['identity']]==x['observed'] for x in items),'CONFLICT')
            allocation=r.call('omega-agent','allocate',None,'--identity','integrated-interleaved-shared','--template','shared')
            shared=r.ids['omega-agent'].index(allocation['session']);save()
        else:
            r.sustained();memory=r.report['first_memory'];payload=memory['memory']['target']['payload']
            report['archive']=json.loads(op.k('exec','-i','fusion-storage-0','--',PYTHON,'-c',ARCHIVE,
                data=json.dumps(dict(scope=payload['scope_ref'],payload=payload,through=memory['source'])),timeout=70));save()
            old_pod=json.loads(op.k('get','pod','fusion-storage-0','-o','json'))['metadata']['uid']
            op.k('delete','pod','fusion-storage-0','--wait=true',timeout=70)
            op.k('wait','--for=condition=Ready','pod/fusion-storage-0','--timeout=90s',timeout=100)
            new_pod=json.loads(op.k('get','pod','fusion-storage-0','-o','json'))['metadata']['uid'];require(old_pod!=new_pod,'CONFLICT')
            first=r.report['inputs'][0];old=r.call('omega-agent','observe',first['session'],'--content')
            require(next(x for x in old['inputs'] if x['id']==first['identity'])==first['observed'],'CONFLICT')
            report['retained_restart']=dict(old_pod=old_pod,new_pod=new_pod,first_capture_exact=True,no_reset=True);save()
            indices=r.overlap();r.handoffs(indices);r.private();r.counterfactual();require(r.count==70,'CONFLICT')
            shared=r.allocate('omega-agent','integrated-interleaved-shared')
        # Completion does not implicitly free an active-session slot. Close
        # completed sessions through the existing operator port, retaining all
        # records, before asking for two simultaneously eligible sessions.
        for row in r.call('omega-agent','list'):
            if row['state']=='active' and row['session']!=r.ids['omega-agent'][shared]:
                observed=r.call('omega-agent','observe',row['session'],'--content')
                require(all(x['state']=='complete' for x in observed['inputs']),'NOT_AVAILABLE')
                r.call('omega-agent','close',row['session'],'--identity','close-before-interleave-'+row['session'])
        private=r.allocate('omega-agent','integrated-interleaved-private','private')
        # Same owner, two simultaneously eligible sessions. Only the native
        # supervisor's safe-boundary discipline may choose dispatch order.
        with ThreadPoolExecutor(max_workers=2) as pool:
            pending=[pool.submit(r.run,'pin visible '+selected['shared_note'],session=shared),
                     pool.submit(r.run,'pin isolated '+selected['private_canary'],session=private)]
            for p in pending:p.result()
        with ThreadPoolExecutor(max_workers=2) as pool:
            shared_context=pool.submit(r.run,'task-context',session=shared);private_context=pool.submit(r.run,'task-context',session=private)
            sc,pc=shared_context.result(),private_context.result()
        require(selected['shared_note'] in sc and selected['private_canary'] not in sc,'UNAUTHORIZED')
        require(selected['private_canary'] in pc and selected['shared_note'] not in pc,'UNAUTHORIZED')
        public=r.run('query synthetic private A canary',session=shared)
        require('cabinet birch' not in public and selected['private_canary'] not in public,'UNAUTHORIZED')
        private_result=r.run('query '+DATASETS['changed']['query'],session=private)
        require('crate saffron' not in private_result and 'crate orchid' not in private_result,'UNAUTHORIZED')
        nal=r.run('metta (Truth_Deduction (stv 0.8 0.9) (stv 0.7 0.8))',session=shared)
        require('(stv 0.5599999999999999 0.4032)' in nal,'NOT_AVAILABLE')
        r.run('write-file integration.txt Synthetic retained file',session=shared)
        r.run('append-file integration.txt Appended exactly once',session=shared)
        text=r.run('read-file integration.txt',session=shared)
        require('Synthetic retained file' in text and 'Appended exactly once' in text,'NOT_AVAILABLE')
        report['warm_interleaving']=dict(same_owner_two_sessions=True,private_shared_context_disjoint=True,
            cross_scope_queries_no_fact_disclosure=True,completed_extension_inputs=10,context_boundaries='REAL_NATIVE',new_occurrences=True)
        require(r.count==maximum,'CONFLICT');save()
        report['diagnostics']={};report['timing']={}
        for obj in op.workloads():
            role=obj['metadata']['name']
            report['diagnostics'][role]=json.loads(op.k('exec',role+'-0','--',PYTHON,'-m','integration.single_node.diagnostics',timeout=35))
            report['timing'][role]=json.loads(op.k('exec',role+'-0','--',PYTHON,'-m','integration.single_node.sustained_diagnostics',timeout=35));save()
        for role in ('omega-agent','omega-agent-b'):
            for row in r.call(role,'list'):
                if row['state']=='active':r.call(role,'close',row['session'],'--identity','integrated-eighty-close-'+row['session'])
        r.report['status']='PASS';report.update(status='PASS',operator_native_inputs=r.count,namespace_reset=False,
            model_generations=0,physical_invocation_semantics='NAMED_NATIVE_PROVIDERS_NOT_MODEL_TOOLS',original_bounds_preserved=True)
        report['retained_failed_scenarios']=sum(not x.get('passed',False) for x in r.report['scenarios'])
    except BaseException as error:
        report.update(status='FAIL',failure=dict(type=type(error).__name__,code=getattr(error,'code',None),detail=str(error)[-1500:]));r.report['status']='FAIL';raise
    finally:op.quiesce();report['quiesced']=True;save()
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('kubeconfig','context','namespace','directory','plan'):p.add_argument('--'+name,required=True)
    p.add_argument('--resume-from');p.add_argument('--resume-handoff')
    a=p.parse_args();v=qualify(Operator(a.kubeconfig,a.context,a.namespace),json.loads(Path(a.plan).read_bytes()),a.directory,a.resume_from,a.resume_handoff)
    print(json.dumps(dict(status=v['status'],additional_live_generations=0)))
