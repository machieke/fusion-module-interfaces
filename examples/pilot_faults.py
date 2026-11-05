"""Finite retained-state pilot faults through existing owners and native tools.

The operator selects faults; recorded proposals only select native commands.
Every accepted input retains its deadline. No failed input is replaced here.
"""
import argparse,json,time,uuid
from pathlib import Path
import yaml
from fusion.contracts import canonical,digest,require
from integration.single_node.reference_ops import Operator,PYTHON
from integration.single_node.preview_recovery_qualification import Recovery
from examples.integrated_sustained import IntegratedRunner

PROFILE='operator-pilot-interruption-qualification/2'


def joined_native(runner,report):
    """Join exact persisted receipts without counting replay or internal delivery."""
    rows=[dict(row,origin='native-runner') for row in runner['inputs']]
    for case in report['cases']:
        accepted=case.get('accepted')
        # A case that failed before receiving its acceptance remains in the
        # primary report. Do not manufacture an unknown application identity.
        if accepted is None:continue
        row=dict(role=case['caller'],session=accepted['session'],identity=accepted['id'],
            command=case['command'],accepted=accepted,observed=case.get('observed'),origin='recovery-case')
        if 'failure' in case:row['failure']=case['failure']
        rows.append(row)
    terminal={row['id']:row for row in report.get('terminal_inputs',[])}
    for request in report.get('terminal_requests',[]):
        accepted=request.get('accepted')
        if accepted is None:continue
        row=dict(role='omega-agent',session=accepted['session'],identity=accepted['id'],
            command=request['command'],accepted=accepted,observed=terminal.get(accepted['id']),origin='terminal-before-start')
        if row['observed'] is None:row['failure']=report.get('failure',dict(code='OBSERVATION_NOT_CAPTURED'))
        rows.append(row)
    identities=[(row['role'],row['session'],row['identity']) for row in rows]
    require(len(identities)==len(set(identities)),'CONFLICT')
    return dict(classification='RECORDED_MODEL_REAL_NATIVE_TOOLS',inputs=rows,
        source_manifest_sha256=report['source_manifest_sha256'],additional_live_generations=0,
        internal_deliveries_in_operator_count=False,
        origin_counts={origin:sum(row['origin']==origin for row in rows)
            for origin in ('native-runner','recovery-case','terminal-before-start')})



def check_fenced(accepted,observed,control,before,after,models_before,models_after):
    """Independent safety oracle: an unknown dispatch is not a completion."""
    require(observed['id']==accepted['id'] and observed['accepted']==accepted['accepted']
            and observed['deadline']==accepted['deadline'],'CONFLICT')
    require(observed['state'] in ('dispatched','needs-reconciliation','cancel-requested')
            and observed['result'] is None,'CONFLICT')
    require(control['unresolved_assignments']>=1 and control['current'] is not None
            and control['current']['state']=='uncertain','CONFLICT')
    require(before==after and models_before==models_after,'CONFLICT')
    return dict(safety='PASS',native_completion='NOT_COMPLETED',
                disposition='UNCERTAIN_FENCED_NO_REISSUE',deadline_renewals=0,
                reservation_refunds=0,completion_manufactured=False)


class PilotRecovery(Recovery):
    """Respect the resident worker's original uncertain-assignment policy."""
    def disarm(self,role):
        # Change only the selected test configuration. Retain every marker,
        # journal, accepted identity and original deadline on the owner's PVC.
        before=self.pod(role)
        # Explicit component configurations (including agent B) require this
        # field. Empty selection retires the hook without changing owner state.
        self.values['components'][role]['config']['test'] = {}
        self.values_path.write_text(yaml.safe_dump(self.values,sort_keys=False))
        self.op.command(['helm','upgrade','omega',self.chart,'--kubeconfig',self.op.kubeconfig,
            '--kube-context',self.op.context,'--namespace',self.op.namespace,'-f',str(self.values_path),
            '--wait','--timeout','180s'],timeout=190)
        return dict(before=before,after=self.pod(role),marker_retained=True)

    def case(self,name,role,session,command,owner,knob,stage,*,expect):
        require(expect in ('completed-projection','uncertain-fenced'),'INVALID_ARGUMENT')
        require(time.monotonic()<self.end and len(self.report['cases'])<8,'OVERLOADED')
        item=dict(name=name,caller=role,owner=owner,command=command,expect=expect,
                  started_ms=time.time_ns()//1000000)
        self.report['cases'].append(item);self.save()
        try:
            marker=self.arm(owner,knob,stage);sid=self.ids[role][session]
            identity='recovery-'+str(uuid.uuid4())
            accepted=self.api.call(role,'submit',sid,'--identity',identity,'--text',command,'--assignment','synthetic-task')
            item['accepted']=accepted;self.save()
            until=min(self.end,time.monotonic()+max(0,(accepted['deadline']-time.time_ns()//1000000)/1000)+8)
            fired=None
            while time.monotonic()<until:
                fired=self.read(owner,marker)
                if fired:break
                time.sleep(.25)
            require(fired is not None,'NOT_AVAILABLE');item['fault_marker']=fired
            item['dispatch_before_replacement']=self.accounting(role,sid,identity)
            item['model_before_replacement']=self.model_accounting(sid);self.save()
            item['replacement']=self.replace(list(dict.fromkeys((owner,role))));self.save()
            # Reconciliation is owner-authoritative observation, never a wake,
            # model replay, missing task publication or refunded reservation.
            self.api.call(role,'reconcile',sid)
            observed=self.observe(role,sid,identity);item['observed']=observed
            after=self.accounting(role,sid,identity);item['dispatch_after_replacement']=after
            models=self.model_accounting(sid);item['model_after_replacement']=models
            require(accepted['deadline']==observed['deadline'] and accepted['accepted']==observed['accepted'],'CONFLICT')
            require(after==item['dispatch_before_replacement'] and models==item['model_before_replacement'],'CONFLICT')
            if expect=='completed-projection':
                require(observed['state']=='complete' and observed['result'] is not None and
                        all(x['done']==1 for x in after) and after,'NOT_AVAILABLE')
                item['native_completion']='COMPLETE'
            else:
                control=self.api.call(role,'worker-control',sid,'--worker-action','observe')
                item['worker_control']=control
                item['outcome']=check_fenced(accepted,observed,control,item['dispatch_before_replacement'],after,
                                            item['model_before_replacement'],models)
            # Exact idempotent submission is an intentional replay probe; it is
            # not a replacement occurrence or authority to resume uncertainty.
            duplicate=self.api.call(role,'submit',sid,'--identity',identity,'--text',command,'--assignment','synthetic-task')
            require(all(duplicate[k]==accepted[k] for k in ('id','deadline','sequence','accepted')),'CONFLICT')
            require(duplicate['state']==observed['state'],'CONFLICT')
            require(self.accounting(role,sid,identity)==after and self.model_accounting(sid)==models,'CONFLICT')
            item.update(duplicate_receipt=duplicate,status='PASS',deadline_renewals=0)
            item['test_configuration_retirement']=self.disarm(owner)
        except Exception as error:
            item.update(status='FAILED',failure=dict(type=type(error).__name__,code=getattr(error,'code',None),detail=str(error)[-1024:]))
        finally:item['finished_ms']=time.time_ns()//1000000;self.save()


def qualify(op,values,chart,directory):
    root=Path(directory);root.mkdir(parents=True,exist_ok=False)
    r=IntegratedRunner(op,root/'native',maximum_inputs=12,legacy_crossing_required=False)
    r.end=time.monotonic()+1800
    fault=PilotRecovery.__new__(PilotRecovery);fault.op=op;fault.values_path=root/'fault-values.yaml'
    fault.values=yaml.safe_load(Path(values).read_bytes());fault.chart=chart;fault.root=root
    fault.api=r;fault.ids=r.ids;fault.end=r.end
    require(fault.values['preview']['sustained']['allocation']['active']==4,'UNSUPPORTED_PROFILE')
    require(fault.values['preview']['sustained']['resident_worker']['profile']=='session-bound-native-worker/1','UNSUPPORTED_PROFILE')
    fault.report=dict(profile=PROFILE,namespace=op.namespace,status='RUNNING',cases=[],
        maximum_new_operator_inputs=12,maximum_seconds=1800,
        uncertain_dispatch_policy='session-bound-native-worker/1: saved final projection only',additional_live_generations=0,
        source_manifest_sha256=fault.values['preview']['sustained']['provider_registry']['pins']['fusion-storage']['source'],
        classification='REAL_NATIVE_REAL_POD_HTTPS_RECORDED_MODEL',
        deadline_renewals=0,reservation_refunds=0,replacement_occurrences=0)
    report=fault.report;fault.save()
    def wait(check,deadline):
        while time.monotonic()<min(r.end,deadline):
            value=check()
            if value:return value
            time.sleep(.5)
        require(False,'NOT_AVAILABLE')
    def call(role,operation,session=None,*args):return r.call(role,operation,session,*args)
    try:
        op.owned()
        report['images']={x['metadata']['labels']['app.kubernetes.io/name']:x['spec']['containers'][0]['image']
            for x in json.loads(op.k('get','pods','-l','app.kubernetes.io/instance=omega','-o','json'))['items']}
        fault.save()
        a=r.allocate('omega-agent','fault-shared-a');b=r.allocate('omega-agent-b','fault-shared-b')
        sid=r.ids['omega-agent'][a]
        memory=r.object(r.run('remember The synthetic fault compass is in drawer willow',session=a))['memory']['handle']
        page=r.object(r.run('episodes current',session=a))
        source=next(x['body']['source']['handle'] for x in page['events'] if x['kind']=='external-observation')
        original=r.report['inputs'][0]
        r.run('query synthetic fault compass',session=a)
        from examples.pilot_incidents import outages,dns_outage,reply_reads
        outages(op,r,fault,sid,original,report,fault.save)
        reply_reads(op,r,fault,sid,original,report,fault.save)
        dns_outage(op,r,sid,original,report,fault.save)
        fault.case('native-committed-projection','omega-agent',a,
            'pin recovery Preserve this exact capture','omega-agent','pause_at',
            'after_application_projection',expect='completed-projection')
        require(report['cases'][-1]['status']=='PASS','NOT_AVAILABLE')
        # Each intentionally uncertain case owns its original session. A new
        # independent scenario never overwrites or retries an earlier failure.
        fault.case('relation-lost-reply','omega-agent',a,'link '+memory+' '+source,
            'fusion-relations','drop_response_operation','assertRelation',expect='uncertain-fenced')
        require(report['cases'][-1]['status']=='PASS','NOT_AVAILABLE')
        storage_session=r.allocate('omega-agent','fault-storage-partial')
        fault.case('storage-accepted-before-feed','omega-agent',storage_session,
            'remember The synthetic fault prism is in chest alder','fusion-storage',
            'pause_at','after_feed_backend_acceptance',expect='uncertain-fenced')
        require(report['cases'][-1]['status']=='PASS','NOT_AVAILABLE')
        sender=r.allocate('omega-agent','fault-task-sender')
        # An asymmetric task return: B captured its actual payload before its
        # pod disappears. Observe its original occurrence; never delegate again.
        fault.arm('omega-agent-b','pause_at','after_task_payload_capture')
        r.admit_selection('omega-agent-b','fault-peer-after-owner-recovery')
        task=r.object(r.run('delegate B synthetic fault compass',session=sender))
        deadline=min(r.end,time.monotonic()+max(0,(task['deadline']-time.time_ns()//1000000)/1000)+8)
        marker=wait(lambda:fault.read('omega-agent-b','pause.json'),deadline)
        require(marker['stage']=='after_task_payload_capture','CONFLICT')
        selected=[]
        for item in call('omega-agent-b','list'):
            observed=call('omega-agent-b','observe',item['session'],'--content')
            for row in observed['inputs']:
                if row['assignment']=='delegated-task' and row['deadline']==task['deadline']:
                    selected.append((item['session'],row))
        require(len(selected)==1,'NOT_AVAILABLE');recipient,incoming=selected[0]
        before=fault.accounting('omega-agent-b',recipient,incoming['id']);model_before=fault.model_accounting(recipient)
        replacement=fault.replace(['omega-agent-b','fusion-messaging'])
        call('omega-agent-b','reconcile',recipient)
        after=fault.accounting('omega-agent-b',recipient,incoming['id'])
        observed=next(x for x in call('omega-agent-b','observe',recipient,'--content')['inputs'] if x['id']==incoming['id'])
        control=call('omega-agent-b','worker-control',recipient,'--worker-action','observe')
        outcome=check_fenced(incoming,observed,control,before,after,model_before,fault.model_accounting(recipient))
        sender_sid=r.ids['omega-agent'][sender]
        returned=[x for x in call('omega-agent','observe',sender_sid,'--content')['inputs']
                  if x['assignment']=='delegated-result' and x['deadline']==task['deadline']]
        require(not returned and all(x['done']==1 for x in before) and before,'CONFLICT')
        report['task_return']=dict(task=task,marker=marker,replacement=replacement,recipient=incoming,
            recipient_observed=observed,worker_control=control,outcome=outcome,
            sender_return='NOT_OBSERVED',original_dispatch_exact=True,captured_model_exact=True)
        report['task_return']['test_configuration_retirement']=fault.disarm('omega-agent-b');fault.save()
        model_session=r.allocate('omega-agent-b','fault-model-capture')
        fault.case('model-captured-response','omega-agent-b',model_session,
            'pin captured Preserve the captured recorded proposal','fusion-model',
            'pause_at','after_model_provider_capture',expect='uncertain-fenced')
        require(report['cases'][-1]['status']=='PASS','NOT_AVAILABLE')
        # The authenticated Registry action makes one real service-health
        # observation during outage. It spends its own observation reservation;
        # it is not an authenticated storage read or a business operation.
        provider='shared-fusion-storage'
        original_pod=fault.pod('fusion-storage')
        op.k('scale','statefulset','fusion-storage','--replicas=0')
        op.k('wait','--for=delete','pod/fusion-storage-0','--timeout=60s',timeout=65)
        unavailable=None
        try:
            unavailable=call('omega-agent','providers',None,'--provider-action','probe','--provider',provider,'--identity','fault-storage-unavailable')
            require(unavailable['status']!='ready','CONFLICT')
            retained=call('omega-agent','observe',sid,'--content')
            require(next(x for x in retained['inputs'] if x['id']==original['identity'])==original['observed'],'CONFLICT')
        finally:
            op.k('scale','statefulset','fusion-storage','--replicas=1')
            op.k('wait','--for=condition=Ready','pod/fusion-storage-0','--timeout=90s',timeout=100)
        report['storage_outage']=dict(before=original_pod,after=fault.pod('fusion-storage'),
            observation=unavailable,retained_application_capture_available=True)
        # A new readiness observation is explicit, never a refreshed old receipt.
        report['storage_recovery_probe']=call('omega-agent','providers',None,'--provider-action','probe','--provider',provider,'--identity','fault-storage-recovered')
        r.allocate('omega-agent','fault-active-capacity')
        try:r.allocate('omega-agent','fault-capacity-refused')
        except RuntimeError as error:
            require('OVERLOADED' in str(error),'CONFLICT')
            report['capacity_refusal']=dict(code='OVERLOADED',new_session_accepted=False)
        else:require(False,'CONFLICT')
        saved=call('omega-agent','observe',sid,'--content')
        require(next(x for x in saved['inputs'] if x['id']==original['identity'])==original['observed'],'CONFLICT')
        report['capacity_refusal']['saved_result_observable']=True
        fault.save()
        # Finish admitted work, close only complete task sessions, then test
        # original expiry/cancellation and capacity access on distinct inputs.
        for role in ('omega-agent','omega-agent-b'):
            for item in call(role,'list'):
                if item['state']!='active':continue
                actual=call(role,'observe',item['session'],'--content')
                if not all(x['state']=='complete' for x in actual['inputs']):continue
                call(role,'close',item['session'],'--identity','fault-close-'+item['session'])
        index=r.allocate('omega-agent','fault-expiry');expired=r.ids['omega-agent'][index]
        call('omega-agent','worker-control',expired,'--worker-action','drain','--identity','fault-drain')
        accepted=[];report['terminal_requests']=[]
        for identity,text in [('fault-expired','pin expired Must never execute'),('fault-cancelled','pin cancelled Must never execute')]:
            request=dict(identity=identity,command=text);report['terminal_requests'].append(request);fault.save()
            receipt=call('omega-agent','submit',expired,'--identity',identity,'--text',text,'--assignment','synthetic-task')
            request['accepted']=receipt;accepted.append(receipt);fault.save()
        report['terminal_inputs_accepted']=accepted;fault.save()
        report['cancel']=call('omega-agent','cancel',expired,'--identity','fault-cancel-receipt','--target',accepted[1]['id'])
        wait(lambda:time.time_ns()//1000000>=accepted[0]['deadline'],time.monotonic()+130)
        call('omega-agent','reconcile',expired)
        observed=call('omega-agent','observe',expired,'--content')['inputs'];require(len(observed)==2,'CONFLICT')
        require([x['state'] for x in observed]==['expired-before-start','cancelled-before-start'],'CONFLICT')
        require(all(x['result'] is None and x['deadline']==a['deadline'] for x,a in zip(observed,accepted)),'CONFLICT')
        report['terminal_inputs']=observed
        call('omega-agent','worker-control',expired,'--worker-action','resume','--identity','fault-resume')
        r.run('pin available Native work continues after original expiry',session=index)
        report['retained_original']=call('omega-agent','observe',sid,'--content')
        require(next(x for x in report['retained_original']['inputs'] if x['id']==original['identity'])==original['observed'],'CONFLICT')
        from examples.pilot_incidents import registry_pressure
        registry_pressure(r,sid,original,report,fault.save)
        from examples.pilot_observations import observe
        report['runtime_observations']=observe(op,root/'runtime-observations.json')
        report.update(status='PASS',native_runner_inputs=r.count,fault_case_inputs=len(report['cases']),
            nonexecuted_terminal_inputs=2)
    except BaseException as error:
        report.update(status='FAIL',failure=dict(type=type(error).__name__,code=getattr(error,'code',None),detail=str(error)[-1000:]));raise
    finally:
        r.save();fault.save()
        try:
            joined_value=joined_native(r.report,report)
            require(len(joined_value['inputs'])<=report['maximum_new_operator_inputs'],'OVERLOADED')
            joined=canonical(joined_value);(root/'all-native-inputs.json').write_bytes(joined)
            report.update(native_runner_report_sha256=digest((r.root/'report.json').read_bytes()),
                native_report_sha256=digest(joined))
        finally:
            fault.save();op.quiesce();report['quiesced_pvcs_retained']=True;fault.save()
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('kubeconfig','context','namespace','values','chart','directory'):p.add_argument('--'+name,required=True)
    a=p.parse_args();v=qualify(Operator(a.kubeconfig,a.context,a.namespace),a.values,a.chart,a.directory)
    print(json.dumps(dict(status=v['status'],additional_live_generations=0)))

if __name__=='__main__':main()
