"""Six bounded lifecycle inputs on a retained native qualification installation.

Real native dispatch/kill and original wall-clock expiry. No SQL mutation,
renewal, automatic replay or new model provider. The same owner state is then
quiesced for an observation-only clone with private/archive/graph dependencies.
"""
import argparse,json,time
from pathlib import Path
import yaml
from fusion.contracts import canonical,digest,require
from integration.single_node.reference_ops import Operator,PYTHON
from integration.single_node.preview_qualification import Runner
from integration.single_node.preview_recovery_qualification import Recovery
from integration.single_node.sustained_restore_qualification import drill
from .integrated_archive_restore import READ
from .integrated_sustained import IntegratedRunner


def qualify(op,values,chart,directory,native_report,resume_setup=None):
    prior=json.loads(Path(native_report).read_bytes())
    require(prior['status']=='PASS' and 14<=len(prior['inputs'])<=96 and prior['namespace']==op.namespace,'CONFLICT')
    root=Path(directory);root.mkdir(parents=True,exist_ok=False)
    r=IntegratedRunner(op,root/'native',maximum_inputs=6,legacy_crossing_required=False)
    fault=Recovery.__new__(Recovery);fault.op=op;fault.values_path=root/'fault-values.yaml'
    fault.values=yaml.safe_load(Path(values).read_bytes());fault.chart=chart
    report=dict(status='RUNNING',namespace=op.namespace,maximum_new_inputs=6,maximum_seconds=600,
        native_report_sha256=digest(Path(native_report).read_bytes()),inputs=[],additional_live_generations=0)
    end=time.monotonic()+600
    def save():(root/'report.json').write_bytes(canonical(report))
    def wait(fn,until):
        while time.monotonic()<min(end,until):
            result=fn()
            if result:return result
            time.sleep(.5)
        require(False,'NOT_AVAILABLE')
    def submit(role,sid,key,text):
        require(len(report['inputs'])<6,'OVERLOADED')
        entry=dict(role=role,session=sid,identity=key,text=text);report['inputs'].append(entry);save()
        entry['accepted']=r.call(role,'submit',sid,'--identity',key,'--text',text,'--assignment','synthetic-task');save()
        return entry['accepted']
    def completed(role,sid,accepted):
        until=time.monotonic()+max(0,(accepted['deadline']-time.time()*1000)/1000)+8
        row=wait(lambda:(x if (x:=fault.observe(role,sid,accepted['id']))['state']=='complete' else None),until)
        require(row['deadline']==accepted['deadline'],'CONFLICT');return row
    fault.api=r;save()
    try:
        op.owned()
        if resume_setup:
            raw=(Path(resume_setup)/'report.json').read_bytes();saved=json.loads(raw)
            require(saved['status']=='FAIL' and saved['namespace']==op.namespace and
                    saved['native_report_sha256']==report['native_report_sha256'] and
                    len(saved['inputs'])==3 and 'progress_after_expiry' in saved and 'pause' not in saved,'CONFLICT')
            sid=saved['session'];current=r.call('omega-agent','observe',sid,'--content')
            rows={x['id']:x for x in current['inputs']}
            require(all(rows[x['id']]==x for x in saved['safe_terminalization']['inputs']) and
                    rows[saved['progress_after_expiry']['id']]==saved['progress_after_expiry'],'CONFLICT')
            report.update({k:v for k,v in saved.items() if k not in ('status','failure','quiesced')})
            report.update(status='RUNNING',resumed_setup_sha256=digest(raw),original_three_inputs_not_repeated=True);save()
        else:
            index=r.allocate('omega-agent','integrated-retained-expiry');sid=r.ids['omega-agent'][index]
            report['session']=sid
            report['drain']=r.call('omega-agent','worker-control',sid,'--worker-action','drain','--identity','retained-drain')
            first=submit('omega-agent',sid,'retained-expiry','pin expired This must never dispatch')
            second=submit('omega-agent',sid,'retained-cancel','pin cancelled This must never dispatch')
            report['cancel_before_start']=r.call('omega-agent','cancel',sid,'--identity','retained-cancel-receipt','--target',second['id']);save()
            wait(lambda:time.time_ns()//1000000>=first['deadline'],time.monotonic()+125)
            r.call('omega-agent','reconcile',sid)
            observed=r.call('omega-agent','observe',sid,'--content');rows={x['id']:x for x in observed['inputs']}
            require(rows[first['id']]['state']=='expired-before-start' and rows[second['id']]['state']=='cancelled-before-start','CONFLICT')
            require(rows[first['id']]['deadline']==first['deadline'] and all(x['result'] is None for x in rows.values()),'CONFLICT')
            report['safe_terminalization']=observed;save()
            r.call('omega-agent','worker-control',sid,'--worker-action','resume','--identity','retained-resume')
            third=submit('omega-agent',sid,'retained-after-expiry','pin progress Native work after unchanged expiry')
            report['progress_after_expiry']=completed('omega-agent',sid,third);save()
        # Release an active slot using the supported close operation, retaining
        # every completed input and all retention/accounting. No SQL edit or
        # quota change is used to allocate the intentional uncertain case.
        for selected in r.call('omega-agent-b','list'):
            if selected['state']!='active':continue
            old=r.call('omega-agent-b','observe',selected['session'],'--content')
            if old['inputs'] and all(x['state']=='complete' for x in old['inputs']):
                receipt=r.call('omega-agent-b','close',selected['session'],'--identity','retained-close-complete-'+selected['session'])
                after=r.call('omega-agent-b','observe',selected['session'],'--content')
                require(after['inputs']==old['inputs'],'CONFLICT')
                report['completed_session_close']=receipt;save();break
        fault.arm('omega-agent-b','pause_at','after_input_dispatch_commit')
        index=r.allocate('omega-agent-b','integrated-retained-uncertain');uncertain=r.ids['omega-agent-b'][index]
        started=submit('omega-agent-b',uncertain,'retained-interruption','pin uncertain Keep this input fenced')
        report['pause']=wait(lambda:fault.read('omega-agent-b','pause.json'),time.monotonic()+45)
        report['cancel_after_start']=r.call('omega-agent-b','cancel',uncertain,'--identity','retained-cancel-started','--target',started['id'])
        report['replacement']=fault.replace(['omega-agent-b']);save()
        blocked=submit('omega-agent-b',uncertain,'retained-dependent','pin dependent Never bypass uncertainty')
        r.call('omega-agent-b','reconcile',uncertain)
        observed=r.call('omega-agent-b','observe',uncertain,'--content');rows={x['id']:x for x in observed['inputs']}
        require(rows[started['id']]['state']=='cancel-requested' and rows[blocked['id']]['state']=='accepted','CONFLICT')
        require(all(x['result'] is None for x in rows.values()),'CONFLICT')
        report['uncertain']=observed;save()
        last=submit('omega-agent',sid,'retained-independent','pin independent An eligible session still progresses')
        report['independent_progress']=completed('omega-agent',sid,last);save()
        # Compare the actual old completed records; no new read substitutes for
        # the selected historical result or its deadline/occurrence identity.
        groups={}
        for item in prior['inputs']:groups.setdefault((item['role'],item['session']),[]).append(item)
        for (role,session),items in groups.items():
            old={x['id']:x for x in r.call(role,'observe',session,'--content')['inputs']}
            for item in items:require(old[item['identity']]==item['observed'],'CONFLICT')
        report.update(status='PASS',retained_captures_exact=len(prior['inputs']),deadline_renewals=0,reservation_refunds=0,
            uncertain_effect='NO_COMPLETION_INFERRED_NO_REPLAY',recorded_model_proposals=True)
    except BaseException as error:
        report.update(status='FAIL',failure=dict(type=type(error).__name__,code=getattr(error,'code',None),detail=str(error)[-1400:]));raise
    finally:op.quiesce();report['quiesced']=True;save()
    return report


def restore(op,clone,values,chart,directory,native_report,images):
    prior=json.loads(Path(native_report).read_bytes());require(prior['status']=='PASS','CONFLICT')
    ref=prior['first_memory']['memory']['target']['payload']
    item=next(x for x in prior['inputs'] if x['command'].startswith('inspect-atom '))
    occurrence=item['observed']['result']['occurrences'][0]
    def readback(owner):
        read=json.loads(owner.k('exec','-i','fusion-storage-0','--',PYTHON,'-c',READ,data=json.dumps(dict(ref=ref))))
        require(read['restore_fenced'] and read['ref']==ref,'CONFLICT')
        r=Runner.__new__(Runner);r.op=owner
        graph=r.call(item['role'],'continuation',item['session'],'--occurrence',occurrence)
        require(graph['restore_fenced'] and not graph['execution_authorized'] and graph['status']=='return-ready','CONFLICT')
        require(graph['native_consumption']['turn_captured'] and graph['native_consumption']['occurrence_captured'],'CONFLICT')
        for action in ('cancel','unsubscribe'):
            try:r.call(item['role'],'continuation',item['session'],'--occurrence',occurrence,'--continuation-action',action,'--identity','forbidden-restored-'+action)
            except RuntimeError as error:require('UNAUTHORIZED' in str(error),'CONFLICT')
            else:require(False,'CONFLICT')
        return dict(early_archived_payload=read,continuation=graph,restored_notifications_cannot_drive_continuation=True,
                    mutation_refused=True,model_starts=0,native_executors_started=0)
    caller=next(x for x in images['images'] if x['kind']=='caller')
    return drill(op,clone,values,chart,directory,maintenance_image=caller['repository']+'@'+caller['manifest_digest'],
        images=images,after_restore=readback)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['lifecycle','restore'])
    for name in ('kubeconfig','context','namespace','values','chart','directory','native-report'):p.add_argument('--'+name,required=True)
    p.add_argument('--clone');p.add_argument('--images');p.add_argument('--resume-setup-report');a=p.parse_args();op=Operator(a.kubeconfig,a.context,a.namespace)
    if a.action=='lifecycle':v=qualify(op,a.values,a.chart,a.directory,a.native_report,a.resume_setup_report)
    else:
        require(a.clone and a.images,'INVALID_ARGUMENT')
        v=restore(op,Operator(a.kubeconfig,a.context,a.clone),a.values,a.chart,a.directory,a.native_report,json.loads(Path(a.images).read_bytes()))
    print(json.dumps(dict(status=v['status'],additional_live_generations=0)))
