"""Deployed trusted lifecycle over existing native sessions and owner APIs.

Operator admits pinned records/probes health. Recorded model echoes proposed
commands only. Native note/context effects run inside the real interpreter.
"""
import argparse,json,time
from pathlib import Path
from fusion.contracts import canonical,require
from integration.single_node.reference_ops import Operator,PYTHON
from integration.single_node.sustained_qualification import Runner
from integration.single_node.placement import verify_installed


def qualify(op,plan,directory):
    root=Path(directory);root.mkdir(parents=True,exist_ok=False);r=Runner(op,root/'native')
    r.end=time.monotonic()+900;r.report.update(maximum_operator_inputs=4,scenario='trusted-provider-selection-and-retained-observation')
    report=dict(status='RUNNING',additional_live_generations=0,implementation='actual native and deployed providers',model='RECORDED_PROPOSALS')
    def save():(root/'report.json').write_bytes(canonical(report))
    save()
    def provider(operation,key=None,identity=None,session=None):
        args=['--provider-action',operation]
        if key:args+=['--provider',key]
        if identity:args+=['--identity',identity]
        return r.call('omega-agent','providers',session,*args)
    try:
        report['preflight']=verify_installed(plan,op);save()
        script="import json;from pathlib import Path;v=json.loads(Path('/run/fusion/owner.json').read_bytes())['native_sessions']['provider_registry'];print(json.dumps({'profile':v['profile'],'templates':v['templates']}))"
        selected=json.loads(op.k('exec','omega-agent-0','--',PYTHON,'-c',script));keys=selected['templates']['shared']
        report['provider_metadata']=[provider('inspect',key) for key in keys];save()
        # Actual wire admission must be refused before any native work.
        try:r.allocate('omega-agent','premature')
        except RuntimeError as error:require('NOT_AVAILABLE' in str(error),'CONFLICT');report['unadmitted_refusal']='PASS'
        else:require(False,'CONFLICT')
        report['admissions']=[]
        for key in keys:
            report['admissions'].append(dict(provider=key,admission=provider('add',key,key+'-add'),readiness=provider('probe',key,key+'-probe'),enabled=provider('enable',key,key+'-enable')));save()
        index=r.allocate('omega-agent','registry-native');sid=r.ids['omega-agent'][index]
        bound=provider('selected',session=sid);report['selected']=bound;save()
        r.run('pin lifecycle Native provider lifecycle note',session=index)
        result=r.run('task-context',session=index);require('Native provider lifecycle note' in result,'CONFLICT')
        original=r.call('omega-agent','observe',sid,'--content');key=next(k for k in keys if k.endswith('fusion-storage'))
        report['disabled']=provider('disable',key,'storage-disable');save()
        # Observation is still served through the original retained binding.
        require(r.call('omega-agent','observe',sid,'--content')==original,'CONFLICT')
        require(provider('selected',session=sid)==bound,'CONFLICT')
        for name,fn in [('allocation',lambda:r.allocate('omega-agent','blocked')),('input',lambda:r.call('omega-agent','submit',sid,'--identity','blocked','--text','pin forbidden Not dispatched','--assignment','synthetic-task'))]:
            try:fn()
            except RuntimeError as error:require('NOT_AVAILABLE' in str(error),'CONFLICT');report[name+'_disabled_refusal']='PASS'
            else:require(False,'CONFLICT')
        provider('probe',key,'storage-reprobe');report['enabled']=provider('enable',key,'storage-enable')
        r.run('task-context',session=index)
        report['draining']=provider('drain',key,'storage-drain');report['retired']=provider('retire',key,'storage-retire')
        require(provider('selected',session=sid)==bound,'CONFLICT')
        report.update(status='PASS',operator_native_inputs=r.count,old_results_retained=True,provider_shutdown=False,
                      counters_refunded=False,retirement_contract='required retained observations; this action does not stop the provider')
    except BaseException as error:report.update(status='FAIL',failure=dict(type=type(error).__name__,code=getattr(error,'code',None)));raise
    finally:op.quiesce();report['quiesced']=True;r.save();save()
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('kubeconfig','context','namespace','directory','plan'):p.add_argument('--'+name,required=True)
    a=p.parse_args();result=qualify(Operator(a.kubeconfig,a.context,a.namespace),json.loads(Path(a.plan).read_bytes()),a.directory)
    print(json.dumps(dict(status=result['status'],additional_live_generations=0)))
