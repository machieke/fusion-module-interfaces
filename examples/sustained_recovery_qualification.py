"""Finite real pod-kill scenarios on fresh Phase 3 synthetic owners.

Reuse the published operator's recovery observers and original occurrence
deadlines. The private case is generated test data; raw reports stay private.
An unsuccessful occurrence is retained, never replaced by a new success claim.
"""
import argparse,json,time
from pathlib import Path
import yaml
from fusion.contracts import canonical,digest,require
from integration.single_node.reference_ops import Operator
from integration.single_node.sustained_qualification import Runner
from integration.single_node.preview_recovery_qualification import Recovery

class ScopedRecovery(Recovery):
    def read(self,role,name):
        value=super().read(role,name)
        if value is None and role=='omega-agent' and name=='pause.json':
            value=json.loads(self.code(role,"from pathlib import Path;p=Path('/state/scopes/private-a/pause.json');print(p.read_text() if p.exists() else 'null')"))
        return value

    def model_accounting(self,sid):
        source='''import json,sqlite3,hashlib
from pathlib import Path
out=[]
for base in (Path('/state'),Path('/state/scopes/private-a'),Path('/state/scopes/private-b')):
 p=base/'model.sqlite'
 if not p.exists():continue
 db=sqlite3.connect(p.as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row;db.execute('PRAGMA query_only=ON');db.execute('BEGIN')
 for row in db.execute('SELECT id,slot,reserved,captured_ms,response,failure_code FROM model_calls WHERE session=? ORDER BY slot',(SID,)):
  item=dict(row);response=item.pop('response');item['response_sha256']=None if response is None else hashlib.sha256(response.encode()).hexdigest();out.append(item)
assert len(out)<=64
print(json.dumps(out))
'''.replace('SID',repr(sid))
        return json.loads(self.code('fusion-model',source))


def qualify(op,values,chart,directory,continuation=None,task_tail=None):
    root=Path(directory);root.mkdir(parents=True,exist_ok=False)
    native=Runner(op,root/'native');native.end=time.monotonic()+1800
    native.report.update(maximum_operator_inputs=16,frozen=dict(profile='sustained-native-recovery/1',wall_seconds=1800,maximum_operator_inputs=16,
        native_replacements='same accepted occurrence only',live_allowance=0,model_proposals='RECORDED_FIXTURE'));native.save()
    helper=ScopedRecovery.__new__(ScopedRecovery);helper.op=op;helper.values_path=Path(values);helper.chart=str(chart)
    helper.values=yaml.safe_load(Path(values).read_text());helper.root=root;helper.api=native;helper.end=native.end
    helper.report=dict(namespace=op.namespace,status='RUNNING',cases=[],additional_live_generations=0,maximum_fault_cases=7,maximum_operator_inputs=16,
        driver_sha256=digest(Path(__file__).read_bytes()))
    helper.ids=native.ids;helper.save()
    try:
        if task_tail:
            require(continuation is not None,'INVALID_ARGUMENT')
            prior=json.loads(Path(continuation).read_bytes());tail_raw=Path(task_tail).read_bytes();tail=json.loads(tail_raw)
            require(prior['namespace']==tail['namespace']==op.namespace and tail['status']=='FAILED','CONFLICT')
            require(all(x['status']=='PASS' for x in tail['cases']),'CONFLICT')
            native_prior=json.loads((Path(task_tail).parent/'native/report.json').read_bytes())
            failed=native_prior['inputs'][-1];require(failed['command'].startswith('delegate '),'CONFLICT')
            native.call('omega-agent','cancel',failed['session'],'--identity','retain-unobserved-task-dispatch','--target',failed['identity'])
            native.call('omega-agent','close',failed['session'],'--identity','close-unobserved-task-session')
            helper.report['retained_failed_task']=native.call('omega-agent','observe',failed['session'],'--content')
            helper.report['prior_report_sha256']=digest(tail_raw)
            helper.report['continuation']='new explicit remaining task scenario; original source-barrier timeout retained without deadline renewal'
            first=prior['cases'][0];native.ids['omega-agent']=[first['accepted']['session']];a=0
            previous_b=next(x['value']['session'] for x in native_prior['allocations'] if x['role']=='omega-agent-b')
            native.ids['omega-agent-b']=[previous_b];b=0;native.close('omega-agent-b',b)
        elif continuation:
            raw=Path(continuation).read_bytes();prior=json.loads(raw)
            require(prior['namespace']==op.namespace and all(c['status']=='PASS' for c in prior['cases'][:4]),'CONFLICT')
            require(prior['cases'][4]['name']=='workspace-effect' and prior['cases'][4]['status']=='FAILED','CONFLICT')
            helper.report['prior_report_sha256']=digest(raw)
            helper.report['continuation']='independent remaining scenarios; failed append and dependent input retained, not resumed'
            first=prior['cases'][0];private_sid=first['accepted']['session']
            native.ids['omega-agent']=[private_sid];a=0
            # Cancel and close preserve uncertainty and charges. New independent
            # intentions use a different session and a different logical file.
            old_sid=prior['cases'][4]['accepted']['session']
            old=native.call('omega-agent-b','observe',old_sid,'--content')
            for row in old['inputs']:
                if row['state'] not in ('complete','expired-before-start','cancelled-before-start','rejected'):
                    native.call('omega-agent-b','cancel',old_sid,'--identity','retain-failed-'+row['id'],'--target',row['id'])
            native.call('omega-agent-b','close',old_sid,'--identity','close-failed-scope-without-refund')
            helper.report['retained_failed_session']=native.call('omega-agent-b','observe',old_sid,'--content');helper.save()
            b=native.allocate('omega-agent-b','independent-workspace-tail')
            helper.values['components']['fusion-execution']['config']['test']={}
            helper.values_path.write_text(yaml.safe_dump(helper.values,sort_keys=False))
            op.command(['helm','upgrade','omega',str(chart),'--kubeconfig',op.kubeconfig,'--kube-context',op.context,'--namespace',op.namespace,
                '-f',str(helper.values_path),'--wait','--timeout','180s'],timeout=190)
        else:
            a=native.allocate('omega-agent','private-recovery','private');b=native.allocate('omega-agent-b','shared-recovery')
            helper.case('private-source-capture','omega-agent',a,'remember The synthetic private recovery compass is in drawer spruce',
                'omega-agent','pause_at','after_source_acceptance')
            first=helper.report['cases'][-1];require(first['status']=='PASS','NOT_AVAILABLE')
            memory=native.object(first['observed']['result']['projection'])['memory']['handle']
            page=native.object(native.run('episodes current','omega-agent',a))
            source=next(x['body']['source']['handle'] for x in page['events'] if x['kind']=='external-observation')
            helper.case('private-assessment-owner-commit','omega-agent',a,'support '+memory+' '+source,
                'fusion-beliefs','pause_at','after_evidence_decision_commit')
            helper.case('feed-backend-before-source-publication','omega-agent-b',b,'remember The synthetic recovery prism is in cabinet hazel',
                'fusion-storage','pause_at','after_feed_backend_acceptance')
            helper.case('model-captured-response','omega-agent-b',b,'pin captured Preserve the captured recorded proposal',
                'fusion-model','pause_at','after_model_provider_capture')
        private_written=native.object(first['observed']['result']['projection'])
        if not task_tail:
            native.run('write-file recovery-tail.txt Synthetic workspace seed','omega-agent-b',b)
            helper.case('workspace-effect','omega-agent-b',b,'append-file recovery-tail.txt A single synthetic retained append',
                'fusion-execution','pause_at','after_workspace_effect')
            helper.readback('workspace-single-append','omega-agent-b',b,'read-file recovery-tail.txt','A single synthetic retained append')
            helper.readback('source-publication-native-read','omega-agent-b',b,'query synthetic recovery prism','cabinet hazel')
            native.close('omega-agent',a)
        # Hooks are scope-local. Leaving the earlier private source hook armed
        # would intentionally pause a new shared scope before task submission.
        for component in helper.values['components'].values():component.setdefault('config',{})['test']={}
        helper.values_path.write_text(yaml.safe_dump(helper.values,sort_keys=False))
        op.command(['helm','upgrade','omega',str(chart),'--kubeconfig',op.kubeconfig,'--kube-context',op.context,'--namespace',op.namespace,
            '-f',str(helper.values_path),'--wait','--timeout','180s'],timeout=190)
        shared=native.allocate('omega-agent','shared-task-after-barrier-audit' if task_tail else 'shared-task-recovery')
        helper.arm('omega-agent-b','pause_at','after_task_payload_capture')
        task=native.object(native.run('delegate B synthetic recovery prism','omega-agent',shared))
        until=min(native.end,time.monotonic()+max(0,(task['deadline']-time.time()*1000)/1000)+8)
        marker=None
        while time.monotonic()<until:
            marker=helper.read('omega-agent-b','pause.json')
            if marker:break
            time.sleep(.5)
        require(marker and marker['stage']=='after_task_payload_capture','NOT_AVAILABLE')
        # The task is discovered in B's declared session inventory; no injected
        # response or guessed native application identity is used.
        incoming=[]
        for row in native.call('omega-agent-b','list'):
            obs=native.call('omega-agent-b','observe',row['session'],'--content')
            if any(x['assignment']=='delegated-task' and x['deadline']==task['deadline'] for x in obs['inputs']):incoming.append(obs)
        require(len(incoming)==1,'NOT_AVAILABLE');recipient=incoming[0]['session']
        before=helper.accounting('omega-agent-b',recipient,incoming[0]['inputs'][0]['id'])
        model_before=helper.model_accounting(recipient)
        replacement=helper.replace(['omega-agent-b'])
        while time.monotonic()<until:
            observed=native.call('omega-agent','observe',native.ids['omega-agent'][shared],'--content')
            returned=[x for x in observed['inputs'] if x['assignment']=='delegated-result' and x['deadline']==task['deadline']]
            if returned and returned[0]['state']=='complete':break
            time.sleep(1)
        require(returned and returned[0]['state']=='complete','NOT_AVAILABLE')
        after=helper.accounting('omega-agent-b',recipient,incoming[0]['inputs'][0]['id'])
        require(before==after and all(x['done']==1 for x in before),'CONFLICT')
        require(helper.model_accounting(recipient)==model_before,'CONFLICT')
        helper.report['task_captured_result']=dict(status='PASS',task=task,recipient_before=incoming[0],replacement=replacement,
            dispatch_before=before,dispatch_after=after,captured_model_unchanged=True,sender_result_consumed=returned[0])
        helper.report['current_after_rollout']=native.current('omega-agent',shared)
        # Distinct server barrier: private source and approved public receipt
        # have independently committed before this intentional response loss.
        # Re-arm only test instrumentation; preserve the earlier marker bytes
        # in the same owner PVC. This changes no journal, occurrence or budget.
        if task_tail:
            archived=json.loads(helper.code('omega-agent',"import json;from pathlib import Path;p=Path('/state/pause.json');v=json.loads(p.read_bytes());assert v['stage']=='after_source_acceptance';q=Path('/state/test-observations/source-barrier-before-task.json');q.parent.mkdir(exist_ok=True);assert not q.exists();p.rename(q);print(json.dumps(v))"))
            helper.report['archived_test_marker']=dict(marker=archived,authoritative_state_changed=False)
        require(Recovery.read(helper,'omega-agent','pause.json') is None,'CONFLICT')
        helper.values['components']['omega-agent']['config']['test']={'pause_at':'after_private_projection_publication_capture'}
        helper.values_path.write_text(yaml.safe_dump(helper.values,sort_keys=False))
        op.command(['helm','upgrade','omega',str(chart),'--kubeconfig',op.kubeconfig,'--kube-context',op.context,'--namespace',op.namespace,
            '-f',str(helper.values_path),'--wait','--timeout','180s'],timeout=190)
        request=dict(profile='operator-approved-synthetic-projection/1',identity='recovery-approved-excerpt',session=native.ids['omega-agent'][a],
            source=private_written['memory']['target']['payload'],content='drawer spruce',approval_record='phase3-exact-generated-recovery-excerpt',
            recipient_scope=helper.values['preview']['scope'])
        source='''import json
from fusion.contracts import ContractError
from integration.single_node.preview_operator import projection
try:print(json.dumps(dict(value=projection(REQUEST))))
except ContractError as error:print(json.dumps(dict(error=error.code)))
'''.replace('REQUEST',repr(request))
        lost=json.loads(helper.code('omega-agent',source));require(lost=={'error':'NOT_AVAILABLE'},'CONFLICT')
        marker=Recovery.read(helper,'omega-agent','pause.json');require(marker['stage']=='after_private_projection_publication_capture','CONFLICT')
        replacement=helper.replace(['omega-agent'])
        recovered=json.loads(helper.code('omega-agent',source));repeated=json.loads(helper.code('omega-agent',source))
        require('value' in recovered and recovered==repeated and recovered['value']['private_source_disclosed'] is False,'CONFLICT')
        helper.report['private_projection_recovery']=dict(status='PASS',lost_reply=lost,marker=marker,replacement=replacement,
            repeated_result_identical=True,public_ref=recovered['value']['shared'],full_source_disclosed=False,empirical_evidence=False)
        helper.report['status']='PASS' if all(x['status']=='PASS' for x in helper.report['cases']) else 'FAILED_REQUIRED_CASE'
        helper.report['native_setup_report']=str(native.root/'report.json');helper.save()
        require(helper.report['status']=='PASS','NOT_AVAILABLE')
    except BaseException as error:
        helper.report.update(status='FAILED',failure=dict(type=type(error).__name__,code=getattr(error,'code',None),detail=str(error)[-1200:]));helper.save();raise
    finally:op.quiesce();helper.report['quiesced']=True;helper.save()
    return helper.report

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('kubeconfig','context','namespace','values','chart','directory'):p.add_argument('--'+name,required=True)
    p.add_argument('--continue-report')
    p.add_argument('--task-tail-report')
    a=p.parse_args();print(json.dumps(qualify(Operator(a.kubeconfig,a.context,a.namespace),a.values,a.chart,a.directory,a.continue_report,a.task_tail_report)))
if __name__=='__main__':main()
