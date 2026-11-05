"""Explicit same-state continuation after the unused-Registry startup defect.

Retains the original failed activation report and the exact source checkpoint.
Only the one-file runtime repair and image/source pins may differ. No backup,
restore, authority transition, old native input or uncertain model call repeats.
"""
import argparse,base64,copy,json,threading,time
from pathlib import Path
import yaml
from fusion.contracts import canonical,digest,require
from integration.single_node.reference_ops import Operator
from integration.single_node.placement import freeze,verify_installed
from integration.single_node.pilot_backup import private_write
from integration.single_node.pilot_handover_operator import operator,FRESH_LABEL
from examples.integrated_sustained import IntegratedRunner
from examples.pilot_handover import retained_runner,restart_activated_caller,QUERY
from examples.pilot_maintenance_faults import diagnostic,retained_payload_readback,historical_refusals,packet_refusal

REPAIRED='integration/single_node/pilot_activation.py'
OLD='dc2d2722d3247dc0152dd6c3ceb0a2474560a9e1a9aba5f15f3922499cb984f4'
NEW='9a273391a5066649c887fc97786bad1e4f5dbce7b521b4dc8f6929ab98cf35a4'


def repaired_binding(old_values,new_values,old_images,new_images):
    """Exact source maps and config differ only at the declared repair pins."""
    manifests=[]
    for path in (old_images,new_images):
        path=Path(path);value=json.loads(path.read_bytes());require(value['source_export_verification']=='PASS','CONFLICT')
        maps=[]
        for item in value['images']:
            source=json.loads((path.parent/item['source_package']).read_bytes())['source']
            require(digest(canonical(source))==value['source_manifest_sha256'],'CONFLICT');maps.append(source)
        require(maps and all(x==maps[0] for x in maps),'CONFLICT');manifests.append((value,maps[0]))
    before,after=manifests[0][1],manifests[1][1]
    require(set(before)==set(after) and {k for k in before if before[k]!=after[k]}=={REPAIRED} and before[REPAIRED]==OLD and after[REPAIRED]==NEW,'CONFLICT')
    left,right=copy.deepcopy(old_values),copy.deepcopy(new_values)
    for value in (left,right):
        value.pop('image')
        for item in value['components'].values():item.pop('image',None)
        for pin in value['preview']['sustained']['provider_registry']['pins'].values():
            require(set(pin)=={'image','source'},'CONFLICT');pin['image']=None;pin['source']=None
    require(left==right,'CONFLICT')
    return dict(old_source=manifests[0][0]['source_manifest_sha256'],new_source=manifests[1][0]['source_manifest_sha256'],
        source_paths=len(before),changed_source={REPAIRED:dict(before=OLD,after=NEW)},configuration_changes='IMAGE_AND_REGISTRY_IMPLEMENTATION_PINS_ONLY'),manifests[1][0]


def qualify(original,replacement,chart,old_values,new_values,old_images,new_images,root,authority_file,task,stop_ms,continue_historical_probe=False,continue_packet_probe=False):
    root=Path(root);raw=(root/'report.json').read_bytes();report=json.loads(raw)
    require(not (continue_historical_probe and continue_packet_probe),'CONFLICT')
    continuing_empty=continue_historical_probe or continue_packet_probe
    expected_stage='historical-https-refusals' if continue_packet_probe else ('unknown-restored-accounting' if continue_historical_probe else 'activation')
    require(report['status']=='FAIL' and report['failure']==dict(type='RuntimeError',code=None) and report['steps'][-1]['step']==expected_stage,'CONFLICT')
    require(report['original']==original.namespace and report['replacement']==replacement.namespace,'CONFLICT')
    if continuing_empty:
        prior_native=json.loads((root/'replacement-native/report.json').read_bytes())
        require(not prior_native.get('inputs') and not prior_native.get('allocations') and not prior_native.get('selection_admissions'),'CONFLICT')
    else:require(not (root/'replacement-native').exists(),'CONFLICT')
    require(type(stop_ms) is int and stop_ms==report['conservative_observer_stop_ms'] and time.time_ns()//1000000<stop_ms,'DEADLINE_EXCEEDED')
    old=yaml.safe_load(Path(old_values).read_bytes());new=yaml.safe_load(Path(new_values).read_bytes())
    repair,images=repaired_binding(old,new,old_images,new_images)
    require(report['artifact_binding']['source_manifest_sha256']==repair['old_source'],'CONFLICT')
    require(new['preview']['pilot']['handover']==old['preview']['pilot']['handover'] and new['preview']['pilot']['writer_fence']==old['preview']['pilot']['writer_fence'],'CONFLICT')
    for op in (original,replacement):require(op.owned()['metadata'].get('labels',{}).get(FRESH_LABEL)==task,'UNAUTHORIZED')
    require(all(x['spec'].get('replicas',1)==0 for x in original.workloads()) and not json.loads(original.k('get','pods','-o','json'))['items'],'UNAUTHORIZED')
    authority=Path(authority_file);current=json.loads(authority.read_bytes())
    require(current['state']=='active' and current['generation']==2 and current['deployment']==replacement.namespace,'UNAUTHORIZED')
    for op in (original,replacement):require(base64.b64decode(json.loads(op.k('get','secret','pilot-current-writer','-o','json'))['data']['current.json'])==authority.read_bytes(),'CONFLICT')
    placement=verify_installed(freeze(chart,replacement.namespace,new,images),replacement)
    retained=retained_runner(replacement,root,7);retained.end=min(retained.end,time.monotonic()+(stop_ms-time.time_ns()//1000000)/1000)
    require(time.monotonic()<retained.end,'DEADLINE_EXCEEDED')
    failed='failed-retired-probe-observer' if continue_packet_probe else ('failed-historical-probe-network' if continue_historical_probe else 'failed-empty-registry-startup')
    private_write(root/(failed+'.json'),raw)
    private_write(root/(failed+'-native.json'),(root/('replacement-native' if continuing_empty else 'source-native')/'report.json').read_bytes())
    report.setdefault('historical_failures',[]).append(dict(failed_report=failed+'.json',report_sha256=digest(raw),
        reason='kubectl does not support selected JSONPath wait condition' if continue_packet_probe else ('probe originated from provider without self-egress authority' if continue_historical_probe else 'unused restored caller had no Registry schema'),
        completed_native_inputs_not_repeated=7,activation_not_repeated=True))
    report['status']='RUNNING';report.pop('failure')
    def record(step,value):report['steps'].append(dict(step=step,value=value));save();return value
    def save():
        path=root/'report.json';path.write_bytes(canonical(report));path.chmod(0o600)
    save();record('repaired-target-source-binding',repair);record('target-placement',placement)
    fresh=None
    try:
        sid,private_sid=retained.ids['omega-agent'][:2]
        accepted=next(x['value'] for x in report['steps'] if x['step']=='unknown-accepted')
        unknown=dict(session=accepted['session'],accounting=next(x['value'] for x in report['steps'] if x['step']=='unknown-original-accounting'))
        if continuing_empty:
            fresh=IntegratedRunner.__new__(IntegratedRunner);fresh.op=replacement;fresh.root=root/'replacement-native';fresh.report=prior_native
            fresh.maximum_inputs=8;fresh.legacy_crossing_required=False;fresh.lock=threading.RLock();fresh.count=0;fresh.ids={}
        else:fresh=IntegratedRunner(replacement,root/'replacement-native',maximum_inputs=8,legacy_crossing_required=False)
        fresh.end=retained.end
        expected={x['identity']:x['observed'] for x in retained.report['inputs']}
        for session,label in ((sid,'old-captured-readback'),(private_sid,'old-private-captured-readback')):
            value=fresh.call('omega-agent','observe',session,'--content');require(all(x==expected[x['id']] for x in value['inputs']),'CONFLICT')
            record(label,dict(session=session,inputs=len(value['inputs']),exact=True))
        shared=next(x['value'] for x in report['steps'] if x['step']=='source-memory')['memory']['target']['payload']
        private=retained.object(next(x['value'] for x in report['steps'] if x['step']=='private-memory'))['memory']['target']['payload']
        record('retained-payload-readback',retained_payload_readback(replacement,shared,private))
        accounting=diagnostic(replacement).model_accounting(unknown['session']);require(accounting==unknown['accounting'],'CONFLICT');record('unknown-restored-accounting',accounting)
        record('historical-https-refusals',historical_refusals(original,replacement,unknown['session']))
        record('retired-namespace-packet-refusal',packet_refusal(original,replacement,task))
        try:fresh.call('omega-agent','submit',sid,'--identity','must-refuse-old-epoch','--text','query '+QUERY,'--assignment','synthetic-task')
        except RuntimeError as error:require('UNAUTHORIZED' in str(error),'CONFLICT');record('historical-session-write','REFUSED')
        else:require(False,'CONFLICT')
        index=fresh.allocate('omega-agent','new-generation-memory','g2-shared')
        record('new-memory',fresh.run('remember The synthetic handover coral parcel is stored in chest spruce',session=index))
        answer=fresh.run('query synthetic handover coral parcel location',session=index);require('chest spruce' in answer,'CONFLICT');record('new-query',answer)
        record('new-workspace',fresh.run('write-file handover-new.txt synthetic after cutover',session=index));record('new-history',fresh.run('episodes current',session=index));fresh.close('omega-agent',index)
        record('activated-caller-restart',restart_activated_caller(replacement,fresh,freeze(chart,replacement.namespace,new,images),
            (sid,private_sid,fresh.ids['omega-agent'][index],unknown['session']),unknown['session']))
        require(diagnostic(replacement).model_accounting(unknown['session'])==unknown['accounting'],'CONFLICT')
        record('unknown-after-new-work',dict(session=unknown['session'],old_capture=None,spent_reservation=1,repeated_backend_calls=0))
        owner,observer=operator(original,replacement,authorize=lambda _:require(original.owned()['metadata'].get('labels',{}).get(FRESH_LABEL)==task and replacement.owned()['metadata'].get('labels',{}).get(FRESH_LABEL)==task,'UNAUTHORIZED'),task=task,authority=authority,secret='pilot-current-writer',
            source_backup=root/'full-2',dependency_report=root/'closure.json',replacement_backup=root/'replacement-qualified',restart_probe=root/'stale-startup.json')
        try:owner.rollback()
        except Exception as error:require(getattr(error,'code',None)=='UNSUPPORTED_OPERATION','CONFLICT');record('rollback','REFUSED')
        else:require(False,'CONFLICT')
        require(observer._writers(original)['writers']==0 and time.monotonic()<fresh.end,'UNAUTHORIZED')
        report.update(status='PASS',new_native_inputs=4,original_stays_stopped=True,writer_generation=2,
            historical_external_effects='FENCED_NOT_REPLAYED',private_dependency_workload='ACTUAL_PRIVATE_NATIVE_CAPTURE_AND_SCOPED_CLOSURE',
            packet_enforcement='ACTUAL_RETIRED_NAMESPACE_CONNECTION_REFUSED',repaired_values=str(Path(new_values).resolve()))
    except BaseException as error:report.update(status='FAIL',failure=dict(type=type(error).__name__,code=getattr(error,'code',None)));raise
    finally:
        if fresh is not None:fresh.save()
        save()
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('kubeconfig','context','namespace','replacement','chart','old-values','new-values','old-images','new-images','directory','authority-file','task'):p.add_argument('--'+name,required=True)
    p.add_argument('--conservative-end-ms',type=int,required=True);p.add_argument('--continue-after-historical-probe-network-error',action='store_true');p.add_argument('--continue-after-retired-probe-observer-error',action='store_true');a=p.parse_args()
    value=qualify(Operator(a.kubeconfig,a.context,a.namespace),Operator(a.kubeconfig,a.context,a.replacement),a.chart,a.old_values,a.new_values,a.old_images,a.new_images,a.directory,a.authority_file,a.task,a.conservative_end_ms,a.continue_after_historical_probe_network_error,a.continue_after_retired_probe_observer_error)
    print(json.dumps(dict(status=value['status'],additional_live_generations=0)))

if __name__=='__main__':main()
