"""Observe a completed native registered workflow in an authority-free clone.

The existing quiesced owner backup/restore remains the only copy mechanism.
This driver never advances a workflow, refreshes a guard, regenerates a result
or constructs a native runtime. Source and clone finish stopped.
"""
import argparse,json
from pathlib import Path
from fusion.contracts import canonical,digest,require
from integration.single_node.reference_ops import Operator
from integration.single_node.sustained_restore_qualification import drill
from examples.pilot_workflows import call


def retained(before,after):
    require(after.get('restore_fenced') is True and after.get('execution_authorized') is False
        and after.get('observation_only') is True and after.get('guard_refresh_performed') is False
        and after.get('retained_approval_is_current_authority') is False,'CONFLICT')
    require(before.get('status')=='complete' and after.get('status')=='complete','CONFLICT')
    # Only the read-only projection flag changes. Everything accepted, captured,
    # observed or spent is compared, not just an expected final answer.
    require(all(after.get(k)==v for k,v in before.items() if k!='observation_only'),'CONFLICT')
    return dict(exact_historical_workflow=True,original_deadline_ms=after['deadline_ms'],
        reservations_spent=after['reservations_spent'],observations_spent=after['observations_spent'],
        captures_retained=sum(x['result_sha256'] is not None for x in after['steps'].values()),
        checkpoints_retained=len(after['checkpoints']),guard_refresh_performed=False,
        new_native_inputs=0,execution_authorized=False)


def qualify(original,clone,values,chart,directory,native_report,images):
    path=Path(native_report);raw=path.read_bytes();prior=json.loads(raw)
    capture_raw=(path.parent/'workflow-native.json').read_bytes();capture=json.loads(capture_raw)
    require(prior['status']=='PASS' and digest(capture_raw)==prior['native_report_sha256']
        and capture['namespace']==original.namespace and capture['additional_live_generations']==0
        and capture['actual_session_observation']['session']==prior['session'],'CONFLICT')
    require(prior['native_session']['allocation']['template']=='shared','UNAUTHORIZED')
    require(prior['final']['status']=='complete' and prior['final']['session']==prior['session']
        and prior['final']['workflow']==prior['workflow'],'CONFLICT')
    def readback(owner):
        value=call(owner,prior['session'],prior['workflow'],'observe',{})
        checked=retained(prior['final'],value)
        listed=call(owner,prior['session'],None,'list',{})
        require(listed['restore_fenced'] and not listed['execution_authorized'] and
            any(x['workflow']==prior['workflow'] and x['deadline_ms']==prior['final']['deadline_ms']
                and x['reservations_spent']==prior['final']['reservations_spent'] for x in listed['workflows']),'CONFLICT')
        for operation,body in [('advance',dict(version=prior['final']['version'])),
            ('checkpoint',dict(identity='forbidden-clone',version=prior['final']['version'],reason='must refuse'))]:
            try:call(owner,prior['session'],prior['workflow'],operation,body)
            except RuntimeError as error:require('UNAUTHORIZED' in str(error),'CONFLICT')
            else:require(False,'CONFLICT')
        require(call(owner,prior['session'],prior['workflow'],'observe',{})==value,'CONFLICT')
        return dict(checked,source_report_sha256=digest(raw),source_capture_sha256=digest(capture_raw),
            workflow=value,mutation_routes_refused=True,observation_after_refusal_unchanged=True,
            actual_guard_revalidation='NOT_RUN_IN_READ_ONLY_CLONE',additional_live_generations=0)
    caller=next(x for x in images['images'] if x['kind']=='caller')
    return drill(original,clone,values,chart,directory,maintenance_image=caller['repository']+'@'+caller['manifest_digest'],
        images=images,after_restore=readback)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('kubeconfig','context','original','clone','values','chart','directory','native-report','images'):
        p.add_argument('--'+name,required=True)
    a=p.parse_args();value=qualify(Operator(a.kubeconfig,a.context,a.original),Operator(a.kubeconfig,a.context,a.clone),
        a.values,a.chart,a.directory,a.native_report,json.loads(Path(a.images).read_bytes()))
    print(json.dumps(dict(status=value['status'],additional_live_generations=0)))
if __name__=='__main__':main()
