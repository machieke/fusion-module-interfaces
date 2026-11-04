"""Compatible retained-service implementation rollover with new native selection.

Requires the completed registry qualification's retained installation. Original
provider records and captures are never rewritten. A trusted new record selects
the upgraded service only for a fresh session; old retired selections stay
unavailable for new input. Existing native code and numerical profiles remain.
"""
import argparse,json,time
from pathlib import Path
from fusion.contracts import canonical,digest,require
from integration.single_node.reference_ops import Operator,PYTHON
from integration.single_node.sustained_qualification import Runner
from integration.single_node.placement import verify_installed


def qualify(op,plan,original,directory):
    root=Path(directory);root.mkdir(parents=True,exist_ok=False);r=Runner(op,root/'native');r.end=time.monotonic()+900
    r.report.update(maximum_operator_inputs=2,scenario='compatible-provider-rollover-native-selection')
    prior=Path(original);native=json.loads((prior/'native/report.json').read_bytes());before=json.loads((prior/'report.json').read_bytes())
    require(before['status']=='PASS' and native['namespace']==op.namespace,'CONFLICT')
    old_session=native['allocations'][0]['value']['session'];original_selection=before['selected']
    report=dict(status='RUNNING',additional_live_generations=0,model='RECORDED_PROPOSALS',original_report_sha256=digest((prior/'report.json').read_bytes()))
    def save():(root/'report.json').write_bytes(canonical(report))
    def provider(operation,key=None,identity=None,session=None):
        args=['--provider-action',operation]
        if key:args+=['--provider',key]
        if identity:args+=['--identity',identity]
        return r.call('omega-agent','providers',session,*args)
    save()
    try:
        report['preflight']=verify_installed(plan,op);save()
        require(provider('selected',session=old_session)==original_selection,'CONFLICT')
        observed=r.call('omega-agent','observe',old_session,'--content')
        for entry in native['inputs']:require(next(x for x in observed['inputs'] if x['id']==entry['identity'])==entry['observed'],'CONFLICT')
        report['old_captures_and_selection_exact']=True;save()
        script="import json;from pathlib import Path;v=json.loads(Path('/run/fusion/owner.json').read_bytes())['native_sessions']['provider_registry'];print(json.dumps(v['templates']['shared']))"
        keys=json.loads(op.k('exec','omega-agent-0','--',PYTHON,'-c',script))
        replacement=[k for k in keys if k not in original_selection];require(len(replacement)==2,'CONFLICT');report['replacements']=replacement
        try:r.allocate('omega-agent','rollover-unadmitted')
        except RuntimeError as error:require('NOT_AVAILABLE' in str(error),'CONFLICT');report['unadmitted_refusal']=True
        else:require(False,'CONFLICT')
        report['admissions']=[]
        for key in keys:
            value=provider('inspect',key)
            if not value['admitted']:provider('add',key,'rollover-add-'+key)
            # Each explicit qualification probe is a new bounded health
            # observation. Replaying an old probe cannot renew readiness.
            prefix=digest(str(root).encode())[:12]
            readiness=provider('probe',key,prefix+'-probe-'+key)
            enabled=provider('enable',key,prefix+'-enable-'+key)
            report['admissions'].append(dict(provider=key,prior=value,readiness=readiness,enabled=enabled));save()
        index=r.allocate('omega-agent','rollover-native');sid=r.ids['omega-agent'][index]
        report['new_selected']=provider('selected',session=sid);save()
        require(set(report['new_selected'])==set(keys) and provider('selected',session=old_session)==original_selection,'CONFLICT')
        nal=r.run('metta (Truth_Deduction (stv 0.8 0.9) (stv 0.7 0.8))',session=index)
        require('(stv 0.5599999999999999 0.4032)' in nal,'NOT_AVAILABLE')
        r.run('task-context',session=index)
        try:r.call('omega-agent','submit',old_session,'--identity','rollover-old-retired-refusal','--text','task-context','--assignment','synthetic-task')
        except RuntimeError as error:require('NOT_AVAILABLE' in str(error),'CONFLICT');report['retired_old_selection_refused_new_work']=True
        else:require(False,'CONFLICT')
        # Only the old execution record is drained; new session retains its
        # independently admitted compatible record on the same retained service.
        report['old_execution_drained']=provider('drain','shared-fusion-execution','rollover-drain-old-execution')
        current=r.call('omega-agent','observe',old_session,'--content')
        require(current['inputs']==observed['inputs'],'CONFLICT')
        report.update(status='PASS',native_inputs=2,native_result=nal,old_results_retained=True,
            state_migration=False,automatic_failover=False,new_provider_record_selection=True)
    except BaseException as error:
        report.update(status='FAIL',failure=dict(type=type(error).__name__,code=getattr(error,'code',None),detail=str(error)[:1024]));raise
    finally:r.save();op.quiesce();report['quiesced']=True;save()
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('kubeconfig','context','namespace','plan','original','directory'):p.add_argument('--'+name,required=True)
    a=p.parse_args();v=qualify(Operator(a.kubeconfig,a.context,a.namespace),json.loads(Path(a.plan).read_bytes()),a.original,a.directory)
    print(json.dumps(dict(status=v['status'],additional_live_generations=0)))
