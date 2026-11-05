"""Actual planned synthetic cutover and base-plus-two-delta acceptance driver.

Start with an already installed EMPTY fresh pilot namespace. The existing
Operator performs all cluster work. Native tools produce captures; this driver
never writes an answer or owner row. All reports/packets are private local files.
No failure is retried by restarting this driver: its output directory is fresh.
"""
import argparse,base64,copy,json,subprocess,sys,threading,time,uuid
from pathlib import Path
import yaml
from fusion.contracts import canonical,digest,require
from integration.single_node.reference_ops import Operator,PYTHON
from integration.single_node.pilot_backup import pack,flatten,compare,compare_checkpoint,private_write,read
from integration.single_node.pilot_dependency_operator import extract,partition,merge
from integration.single_node.pilot_handover_operator import operator,FRESH_LABEL
from integration.single_node.placement import freeze,verify_installed
from fusion.pilot_writer_fence import PROFILE
from examples.integrated_sustained import IntegratedRunner
from examples.pilot_maintenance_faults import unknown_model,search_cleanup,application_cleanup,diagnostic,historical_refusals,retained_payload_readback,packet_refusal

ALLOWED={'pin','unpin','task-context','episodes','remember','query','read-file','write-file','append-file'}
FACT='The synthetic handover cobalt parcel is stored in chest alder'
QUERY='synthetic handover cobalt parcel location'


PRIVATE_DENIAL=r'''import json,sys
from pathlib import Path
from fusion.preview_atoms import client
from fusion.contracts import ContractError,require
q=json.load(sys.stdin);cfg=json.loads(Path('/run/fusion/templates/shared/history-atoms.json').read_bytes());cfg['scope']=q['scope_ref']
try:client(cfg).get(q)
except ContractError as error:
 require(error.code=='UNAUTHORIZED','CONFLICT');print(json.dumps({'code':error.code,'returned_private_payload':False}))
else:require(False,'CONFLICT')'''


def secret_command():
    """Use the shipped Secret recipe in either supported package layout.

    Installed qualification must not depend on a developer checkout beside
    site-packages. Both layouts execute the existing recipe with this exact
    Python; this selects packaging, never a provider or execution fallback.
    """
    import importlib.util
    try:installed=importlib.util.find_spec('fusion_operator.cli')
    except ModuleNotFoundError:installed=None
    if installed is not None:
        return [sys.executable,'-I','-c','from fusion_operator.cli import create_secrets;create_secrets()']
    recipe=Path(__file__).resolve().parents[1]/'deploy/single-node/create_secrets.py'
    require(recipe.is_file() and not recipe.is_symlink(),'NOT_AVAILABLE')
    return [sys.executable,str(recipe)]


def resume(op,before):
    for role,item in before['workloads'].items():op.k('scale','statefulset',role,'--replicas='+str(item['replicas']))
    for role,item in before['workloads'].items():
        if item['replicas']:op.k('rollout','status','statefulset/'+role,'--timeout=120s',timeout=125)


def helm(op,chart,values):
    return op.command(['helm','upgrade','--install','omega',str(Path(chart).resolve()),'-f',str(values),
        '--kubeconfig',op.kubeconfig,'--kube-context',op.context,'--namespace',op.namespace,'--wait','--timeout','5m'],timeout=310)


def restart_activated_caller(op,runner,plan,sessions,unknown_session):
    """Observe actual Pod replacement without submitting any native work."""
    before={sid:runner.call('omega-agent','observe',sid,'--content') for sid in sessions}
    accounting=diagnostic(op).model_accounting(unknown_session)
    pod=json.loads(op.k('get','pod','omega-agent-0','-o','json'))
    require(pod['metadata']['namespace']==op.namespace and pod['metadata']['labels'].get('app.kubernetes.io/name')=='omega-agent','UNAUTHORIZED')
    require(time.monotonic()<runner.end,'DEADLINE_EXCEEDED')
    op.k('delete','pod','omega-agent-0','--wait=true',timeout=90)
    op.k('rollout','status','statefulset/omega-agent','--timeout=120s',timeout=125)
    placement=verify_installed(plan,op)
    replacement=json.loads(op.k('get','pod','omega-agent-0','-o','json'))
    require(replacement['metadata']['uid']!=pod['metadata']['uid'],'CONFLICT')
    for sid,expected in before.items():require(runner.call('omega-agent','observe',sid,'--content')==expected,'CONFLICT')
    require(diagnostic(op).model_accounting(unknown_session)==accounting,'CONFLICT')
    require(time.monotonic()<runner.end,'DEADLINE_EXCEEDED')
    return dict(status='PASS',previous_pod_uid=pod['metadata']['uid'],pod_uid=replacement['metadata']['uid'],
        sessions=len(before),inputs=sum(len(x['inputs']) for x in before.values()),captures_exact=True,
        unknown_accounting_exact=True,new_native_inputs=0,placement=placement)


def retained_runner(original,root,expected_count):
    """Restore only verified completed observations; never admit or renew work."""
    r=IntegratedRunner.__new__(IntegratedRunner);r.op=original;r.root=root/'source-native';r.report=json.loads(read(r.root/'report.json',8388608))
    require(len(r.report['inputs'])==expected_count and all(x['observed']['state']=='complete' for x in r.report['inputs']),'CONFLICT')
    r.maximum_inputs=12;r.legacy_crossing_required=False;r.lock=threading.RLock();r.count=expected_count;r.ids={}
    for item in r.report['allocations']:r.ids.setdefault(item['role'],[]).append(item['value']['session'])
    remaining=(r.report['inputs'][0]['started_ms']+3600000-time.time_ns()//1000000)/1000;require(remaining>0,'DEADLINE_EXCEEDED');r.end=time.monotonic()+remaining
    for sid0 in r.ids['omega-agent']:
        observed={x['id']:x for x in r.call('omega-agent','observe',sid0,'--content')['inputs']}
        require(all(observed[x['identity']]==x['observed'] for x in r.report['inputs'] if x['session']==sid0),'CONFLICT')
    return r


def closure_observe(op,role,script,body,end,note):
    """Bounded explicit read observations; no admission, mutation or timeout change."""
    until=min(end,time.monotonic()+30);attempt=0
    while True:
        remaining=until-time.monotonic();require(remaining>0,'DEADLINE_EXCEEDED');require(attempt<8,'NOT_AVAILABLE');attempt+=1
        started_ms=time.time_ns()//1000000
        try:
            value=json.loads(op.k('exec','-i',role+'-0','--',PYTHON,'-c',script,data=json.dumps(body),timeout=remaining))
            note(dict(attempt=attempt,status='CAPTURED',mutations=0,started_ms=started_ms,finished_ms=time.time_ns()//1000000));return value
        except RuntimeError as error:
            if 'fusion.contracts.ContractError: NOT_AVAILABLE' not in str(error) or 'UNAUTHORIZED' in str(error):raise
            note(dict(attempt=attempt,status='READ_TRANSPORT_NOT_AVAILABLE',error='NOT_AVAILABLE',mutations=0,started_ms=started_ms,finished_ms=time.time_ns()//1000000))
            remaining=until-time.monotonic();require(remaining>0,'DEADLINE_EXCEEDED');time.sleep(min(.25,remaining))


def qualify(original,replacement,chart,values,images,directory,authority_file,task,continue_search_kill=False,continue_private_probe=False,continue_restored=False,conservative_end_ms=None):
    require(sum((continue_search_kill,continue_private_probe,continue_restored))<=1,'CONFLICT')
    continuing=continue_search_kill or continue_private_probe or continue_restored
    root=Path(directory).resolve();root.mkdir(mode=0o700,parents=True,exist_ok=continuing)
    report=dict(profile='planned-single-writer-native-cutover-acceptance/1',status='RUNNING',original=original.namespace,
        replacement=replacement.namespace,steps=[],additional_live_generations=0,model='RECORDED_COMMAND_PROPOSALS',
        limitations=['trusted intact single host','planned quiescence only','same-host backup storage','no HA or node-loss claim'])
    historical=None
    if continue_search_kill:
        historical=read(root/'report.json',8388608);report=json.loads(historical)
        require(report['status']=='FAIL' and report['failure'] in (dict(code='NOT_AVAILABLE',type='ContractError'),dict(code='UNAUTHORIZED',type='ContractError'),dict(code=None,type='RuntimeError')) and
            report['steps'][-1]['step']=='search-unpublished-pause' and report['original']==original.namespace and report['replacement']==replacement.namespace,'CONFLICT')
        previous=report.setdefault('historical_failures',[]);require(len(previous)<3,'OVERLOADED')
        name='failed-search-stage-'+str(len(previous));require(not (root/(name+'.json')).exists(),'CONFLICT')
        private_write(root/(name+'.json'),historical)
        private_write(root/(name+'-native.json'),read(root/'source-native/report.json',8388608))
        previous.append(dict(report_sha256=digest(historical),reason=(['in-namespace SIGKILL did not kill namespace PID1','current Search read blocked behind deliberately paused owner lock','scope guard required namespace-only owner label on pod'][len(previous)]),
            failed_report=name+'.json',unchanged_search_deadline=True,completed_native_inputs_not_repeated=4))
        report['status']='RUNNING';report.pop('failure')
    if continue_private_probe:
        historical=read(root/'report.json',8388608);report=json.loads(historical)
        require(report['status']=='FAIL' and report['failure']==dict(code=None,type='RuntimeError') and
            report['steps'][-1]['step']=='private-query' and report['original']==original.namespace and report['replacement']==replacement.namespace,'CONFLICT')
        require(not (root/'failed-private-probe.json').exists(),'CONFLICT')
        private_write(root/'failed-private-probe.json',historical)
        private_write(root/'failed-private-probe-native.json',read(root/'source-native/report.json',8388608))
        report.setdefault('historical_failures',[]).append(dict(report_sha256=digest(historical),
            reason='embedded read-only private denial probe indentation error',failed_report='failed-private-probe.json',
            completed_native_inputs_not_repeated=3,original_window_unchanged=True))
        report['status']='RUNNING';report.pop('failure')
    if continue_restored:
        historical=read(root/'report.json',8388608);report=json.loads(historical)
        require(report['status']=='FAIL' and report['failure']==dict(code=None,type='RuntimeError') and
            report['steps'][-1]['step']=='restore' and report['original']==original.namespace and report['replacement']==replacement.namespace,'CONFLICT')
        require(not (root/'failed-restored-closure.json').exists(),'CONFLICT')
        private_write(root/'failed-restored-closure.json',historical)
        private_write(root/'failed-restored-closure-native.json',read(root/'source-native/report.json',8388608))
        report.setdefault('historical_failures',[]).append(dict(report_sha256=digest(historical),
            reason='first restored Search ready read exceeded existing one-second transport timeout',failed_report='failed-restored-closure.json',
            completed_native_inputs_not_repeated=7,backup_restore_not_repeated=True,original_window_unchanged=True))
        report['status']='RUNNING';report.pop('failure')
    def save():
        (root/'report.json').write_bytes(canonical(report));(root/'report.json').chmod(0o600)
    def record(step,value):report['steps'].append(dict(step=step,value=value));save();return value
    save();source=yaml.safe_load(Path(values).read_text());p=source['preview']
    image_bytes=read(images,4194304);image_manifest=json.loads(image_bytes)
    source_plan=freeze(chart,original.namespace,source,image_manifest)
    artifact_binding=dict(image_manifest_sha256=digest(image_bytes),source_manifest_sha256=image_manifest['source_manifest_sha256'])
    require(report.get('artifact_binding',artifact_binding)==artifact_binding,'CONFLICT')
    report['artifact_binding']=artifact_binding;save()
    require(original.namespace.startswith('omega-ref-pilot-') and replacement.namespace.startswith('omega-ref-pilot-') and original.namespace!=replacement.namespace,'UNAUTHORIZED')
    require(original.owned()['metadata'].get('labels',{}).get(FRESH_LABEL)==task,'UNAUTHORIZED')
    require(p['model_boundary']=='RECORDED_FIXTURE' and p['profile']=='omega-single-node-sustained-preview/1','UNAUTHORIZED')
    require(not p.get('chain',{}).get('enabled') and not source.get('workflow',{}).get('enabled'),'UNAUTHORIZED')
    require(not any(x['metadata']['name'] in ('fusion-inspect-go','f1r3node','fusion-channel-bridge','irc-server','irc-peer') for x in original.workloads()),'UNSUPPORTED_PROFILE')
    require(all(set(a['tools'])<=ALLOWED for a in p['agents'].values()) and not p.get('tasks',{}).get('enabled'),'UNSUPPORTED_PROFILE')
    require(p['pilot']['writer_fence']['deployment']==original.namespace and p['pilot']['writer_fence']['generation']==1,'UNAUTHORIZED')
    authority=Path(authority_file).resolve();require(not authority.is_relative_to(root),'UNAUTHORIZED')
    actual=json.loads(original.k('get','secret','pilot-current-writer','-o','json'))
    require(read(authority,262144)==base64.b64decode(actual['data']['current.json']),'CONFLICT')
    current=json.loads(read(authority,262144));require(current['state']=='active' and current['generation']==1 and current['deployment']==original.namespace,'UNAUTHORIZED')
    before_images={x['metadata']['name']:x['spec']['template']['spec']['containers'][0]['image'] for x in original.workloads()}
    source_identity=dict(source_values_sha256=digest(Path(values).read_bytes()),images=before_images,authority_sha256=digest(read(authority,262144)))
    if continuing:
        require(report['steps'][0]==dict(step='sources',value=source_identity),'CONFLICT')
        r=retained_runner(replacement if continue_restored else original,root,7 if continue_restored else (3 if continue_private_probe else 4));r.op=original
        if conservative_end_ms is not None:
            require(type(conservative_end_ms) is int and conservative_end_ms<=r.report['inputs'][0]['started_ms']+3600000,'CONFLICT')
            remaining=(conservative_end_ms-time.time_ns()//1000000)/1000;require(remaining>0,'DEADLINE_EXCEEDED')
            r.end=min(r.end,time.monotonic()+remaining)
            report['conservative_observer_stop_ms']=conservative_end_ms;save()
        require(not continue_restored or conservative_end_ms is not None,'CONFLICT')
        packets=[] if continue_private_probe else [str(root/('packet-'+str(i))) for i in range(3 if continue_restored else 1)]
        identity=None if continue_private_probe else next(x['value']['manifest_sha256'] for x in report['steps'] if x['step']==('incremental-2' if continue_restored else 'incremental-0'))
    else:
        record('sources',source_identity)
        r=IntegratedRunner(original,root/'source-native',maximum_inputs=12,legacy_crossing_required=False)
        packets=[];identity=None
    try:
        if continue_restored:
            sid_index=0;sid=r.ids['omega-agent'][0];private_sid=r.ids['omega-agent'][1]
            source_backup=root/'full-2';inventories=extract(source_backup)
            target_path=root/'replacement-readonly.yaml';target=yaml.safe_load(target_path.read_bytes())
            expected=copy.deepcopy(source);expected['preview']['pilot'].pop('writer_fence');expected['preview']['pilot'].pop('handover',None)
            require(target==expected,'CONFLICT')
            require(all(x['spec'].get('replicas',1)==0 for x in original.workloads()) and not json.loads(original.k('get','pods','-o','json'))['items'],'UNAUTHORIZED')
            require(replacement.owned()['metadata'].get('labels',{}).get(FRESH_LABEL)==task,'UNAUTHORIZED')
            record('continuation-restored-placement',verify_installed(freeze(chart,replacement.namespace,target,image_manifest),replacement))
            accepted=next(x['value'] for x in report['steps'] if x['step']=='unknown-accepted')
            unknown=dict(session=accepted['session'],identity=accepted['identity'],
                accounting=next(x['value'] for x in report['steps'] if x['step']=='unknown-original-accounting'))
        else:
            if continuing:
                sid_index=0;sid=r.ids['omega-agent'][0];private_sid=r.ids['omega-agent'][1];private_index=1
            if continue_private_probe:
                memory_object=next(x['value'] for x in report['steps'] if x['step']=='source-memory')
                private_memory=next(x['value'] for x in report['steps'] if x['step']=='private-memory')
                record('continuation-source-placement',verify_installed(source_plan,original))
            elif not continue_search_kill:
                record('source-placement',verify_installed(source_plan,original))
                require(all(not r.call(role,'list') for role in p['agents']),'CONFLICT')
                sid_index=r.allocate('omega-agent','handover-source');sid=r.ids['omega-agent'][sid_index]
                memory=r.run('remember '+FACT,session=sid_index);memory_object=r.object(memory);record('source-memory',memory_object)
                require(p['sustained'].get('private_scopes') is True and p['sustained'].get('storage_archive') and p['sustained']['provider_registry']['profile']=='trusted-provider-lifecycle/1','UNSUPPORTED_PROFILE')
                private_index=r.allocate('omega-agent','handover-private','private');private_sid=r.ids['omega-agent'][private_index]
                private_memory=r.run('remember The synthetic private handover violet key is stored in drawer oak',session=private_index)
                record('private-memory',private_memory)
                private_answer=r.run('query synthetic private handover violet key',session=private_index);require('drawer oak' in private_answer,'CONFLICT');record('private-query',private_answer)
            if not continue_search_kill:
                attack=PRIVATE_DENIAL
                record('private-cross-owner-denial',json.loads(original.k('exec','-i','omega-agent-b-0','--',PYTHON,'-c',attack,
                    data=json.dumps(r.object(private_memory)['memory']['target']['payload']),timeout=35)))
                r.close('omega-agent',private_index)
                from examples.integrated_archive import ARCHIVE
                payload=memory_object['memory']['target']['payload']
                archived=json.loads(original.k('exec','-i','fusion-storage-0','--',PYTHON,'-c',ARCHIVE,data=json.dumps(dict(scope=payload['scope_ref'],payload=payload,through=memory_object['source'])),timeout=70));record('owner-archive',archived)
            for index,command in enumerate((None,'query '+QUERY,'write-file handover.txt synthetic before cutover')):
                if continue_search_kill and index==0:continue
                if command and not (continue_search_kill and index==1):record('source-native-'+str(index),r.run(command,session=sid_index))
                if index==1:
                    search_cleanup(original,r,sid_index,chart,source,root,helm,record,
                        next(x['value'] for x in report['steps'] if x['step']=='search-build-accepted-input') if continue_search_kill else None)
                    result=r.run('query '+QUERY,session=sid_index);require('chest alder' in result,'CONFLICT');record('native-query-after-rebuild',result)
                if index==2:
                    record('source-history',r.run('episodes current',session=sid_index));r.close('omega-agent',sid_index)
                    application_cleanup(original,sid,record,r.end)
                    unknown=unknown_model(original,r,chart,source,root,helm,record)
                full=root/('full-'+str(index));cut=original.backup(full);record('full-'+str(index),dict(sha256=digest((full/'manifest.json').read_bytes()),owners=len(cut['owners'])))
                packet=root/('packet-'+str(index));packed=pack(full,packet,packets,identity);identity=packed['manifest_sha256'];packets.append(str(packet));record('incremental-'+str(index),packed)
                record('original-full-byte-comparison-'+str(index),compare(packets,identity,full))
                if index<2:resume(original,cut['before'])
            independent=root/'independent-final-full';original.backup(independent)
            record('independent-final-checkpoint',compare_checkpoint(packets,identity,independent))
            flat=root/'flattened';record('flatten',flatten(packets,identity,flat))
            source_backup=root/'full-2';inventories=extract(source_backup)
            from integration.single_node.pilot_upgrade import upgrade
            original_export=source_backup/'omega-agent.tar.gz';export_sha=digest(original_export.read_bytes())
            record('format-copy-dry-run',upgrade(original_export,export_sha,dry_run=True))
            record('format-copy-upgrade',upgrade(original_export,export_sha,root/'format-copy'))
            inventory_file=root/'inventories.json';private_write(inventory_file,canonical(inventories))
            # Fresh TLS/tokens are provisioned independently; no original Secret,
            # old live approval, chain key or egress credential enters the copy.
            replacement.create();replacement.k('label','namespace',replacement.namespace,FRESH_LABEL+'='+task)
            target=copy.deepcopy(source);target['preview']['pilot'].pop('writer_fence');target['preview']['pilot'].pop('handover',None)
            target_path=root/'replacement-readonly.yaml';target_path.write_text(yaml.safe_dump(target,sort_keys=False));target_path.chmod(0o600)
            replacement.command([*secret_command(),'--preview-values',str(target_path),'--kubeconfig',replacement.kubeconfig,'--context',replacement.context,'--namespace',replacement.namespace,'--directory',str(root/'replacement-secrets')],timeout=180)
            record('restore',replacement.restore(flat));helm(replacement,chart,target_path)
        # Resolve every retained dependency through the replacement's declared
        # authenticated read ports; existing restore host cannot execute work.
        scope_clients={p['scope']:('omega-agent','shared')}
        for role,agent in p['agents'].items():scope_clients[agent['private_scope']]=(role,'private')
        scoped={}
        for scope,(role,template) in scope_clients.items():
            fragments=partition(inventories,scope)
            if not fragments:continue
            directory='/run/fusion/templates/'+template+'/'
            ports=dict(profile='owner-dependency-read-clients/1',scopes={scope:dict(atom_client=directory+'history-atoms.json',search_client=directory+'search-active.json',vector_client=directory+'memory-read-template.json')})
            script='import json,sys;from integration.single_node.pilot_dependency_operator import verify;v=json.load(sys.stdin);print(json.dumps(verify(v["inventories"],v["ports"])))'
            scoped[scope]=closure_observe(replacement,role,script,dict(inventories=fragments,ports=ports),r.end,lambda value:record('closure-read-observation',value))
        closure=merge(inventories,scoped)
        closure_file=root/'closure.json';private_write(closure_file,canonical(closure));record('dependency-closure',dict(owners=len(closure),sha256=digest(canonical(closure))))
        replacement.quiesce();checkpoint=digest((source_backup/'manifest.json').read_bytes())
        # Install only identity fences and old-session metadata in stopped copies.
        source_cut=json.loads((source_backup/'manifest.json').read_bytes())
        installed=[]
        for role in source_cut['owners']:
            helper=replacement.helper(role,source_cut['maintenance_image'],'state-'+role+'-0')
            try:installed.append(json.loads(replacement.k('exec',helper,'--',PYTHON,'-m','integration.single_node.pilot_activation','--role',role,'--checkpoint-sha256',checkpoint,'--generation','2')))
            finally:replacement.k('delete','pod',helper,'--wait=true')
        record('activation-fences',installed)
        target_backup=root/'replacement-qualified';replacement.backup(target_backup,maintenance_image=source_cut['maintenance_image'])
        owner,observer=operator(original,replacement,authorize=lambda _:require(original.owned()['metadata'].get('labels',{}).get(FRESH_LABEL)==task and replacement.owned()['metadata'].get('labels',{}).get(FRESH_LABEL)==task,'UNAUTHORIZED'),
            task=task,authority=authority,secret='pilot-current-writer',source_backup=source_backup,dependency_report=closure_file,replacement_backup=target_backup,restart_probe=root/'stale-startup.json')
        handover='planned-'+str(uuid.uuid4());record('drain',owner.plan(handover,replacement.namespace,'replacement-'+str(uuid.uuid4()),checkpoint,digest(canonical(closure))))
        observer.sync_authority();record('network-fence',observer.fence_network());record('stale-startup',observer.probe_stale_startup())
        record('retirement',owner.retire(handover));observer.sync_authority();active=record('activation',owner.activate(handover));observer.sync_authority()
        target['preview']['pilot']['writer_fence']=dict(profile=PROFILE,authority_file='/writer-authority/current.json',deployment=active['deployment'],incarnation=active['incarnation'],generation=2)
        target['preview']['pilot']['handover']=dict(profile=PROFILE,checkpoint_sha256=checkpoint,generation=2)
        for component in target['components'].values():
            if component.get('enabled',True):component['writerAuthoritySecret']='pilot-current-writer'
        active_path=root/'replacement-active.yaml';active_path.write_text(yaml.safe_dump(target,sort_keys=False));active_path.chmod(0o600)
        helm(replacement,chart,active_path)
        # Readiness alone does not bind the installed process to this artifact.
        # Verify actual pod image IDs, packaged source, configuration and TLS
        # before any new native admission in the replacement epoch.
        record('target-placement',verify_installed(freeze(chart,replacement.namespace,target,image_manifest),replacement))
        fresh=IntegratedRunner(replacement,root/'replacement-native',maximum_inputs=8,legacy_crossing_required=False)
        fresh.end=r.end # replacement observations/new inputs do not renew this qualification window
        old=fresh.call('omega-agent','observe',sid,'--content');source_inputs={x['identity']:x['observed'] for x in r.report['inputs']}
        require(all(x==source_inputs[x['id']] for x in old['inputs']),'CONFLICT');record('old-captured-readback',dict(session=sid,inputs=len(old['inputs']),exact=True))
        old_private=fresh.call('omega-agent','observe',private_sid,'--content')
        require(all(x==source_inputs[x['id']] for x in old_private['inputs']),'CONFLICT');record('old-private-captured-readback',dict(session=private_sid,inputs=len(old_private['inputs']),exact=True))
        retained_shared=next(x['value'] for x in report['steps'] if x['step']=='source-memory')['memory']['target']['payload']
        retained_private=r.object(next(x['value'] for x in report['steps'] if x['step']=='private-memory'))['memory']['target']['payload']
        record('retained-payload-readback',retained_payload_readback(replacement,retained_shared,retained_private))
        restored_unknown=diagnostic(replacement).model_accounting(unknown['session'])
        require(restored_unknown==unknown['accounting'],'CONFLICT');record('unknown-restored-accounting',restored_unknown)
        record('historical-https-refusals',historical_refusals(original,replacement,unknown['session']))
        record('retired-namespace-packet-refusal',packet_refusal(original,replacement,task))
        try:fresh.call('omega-agent','submit',sid,'--identity','must-refuse-old-epoch','--text','query '+QUERY,'--assignment','synthetic-task')
        except RuntimeError as error:require('UNAUTHORIZED' in str(error),'CONFLICT');record('historical-session-write','REFUSED')
        else:require(False,'CONFLICT')
        new=fresh.allocate('omega-agent','new-generation-memory','g2-shared')
        record('new-memory',fresh.run('remember The synthetic handover coral parcel is stored in chest spruce',session=new))
        answer=fresh.run('query synthetic handover coral parcel location',session=new);require('chest spruce' in answer,'CONFLICT');record('new-query',answer)
        record('new-workspace',fresh.run('write-file handover-new.txt synthetic after cutover',session=new));record('new-history',fresh.run('episodes current',session=new))
        fresh.close('omega-agent',new)
        record('activated-caller-restart',restart_activated_caller(replacement,fresh,
            freeze(chart,replacement.namespace,target,image_manifest),
            (sid,private_sid,fresh.ids['omega-agent'][new],unknown['session']),unknown['session']))
        require(diagnostic(replacement).model_accounting(unknown['session'])==unknown['accounting'],'CONFLICT')
        record('unknown-after-new-work',dict(session=unknown['session'],old_capture=None,spent_reservation=1,repeated_backend_calls=0))
        try:owner.rollback()
        except Exception as error:require(getattr(error,'code',None)=='UNSUPPORTED_OPERATION','CONFLICT');record('rollback','REFUSED')
        else:require(False,'CONFLICT')
        require(observer._writers(original)['writers']==0,'UNAUTHORIZED')
        report.update(status='PASS',new_native_inputs=4,original_stays_stopped=True,writer_generation=2,
            historical_external_effects='FENCED_NOT_REPLAYED',private_dependency_workload='ACTUAL_PRIVATE_NATIVE_CAPTURE_AND_SCOPED_CLOSURE',packet_enforcement='ACTUAL_RETIRED_NAMESPACE_CONNECTION_REFUSED')
    except BaseException as error:
        report.update(status='FAIL',failure=dict(type=type(error).__name__,code=getattr(error,'code',None)));raise
    finally:r.save();save()
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('kubeconfig','context','namespace','replacement','chart','values','images','directory','authority-file','task'):p.add_argument('--'+name,required=True)
    p.add_argument('--continue-after-inert-search-kill',action='store_true')
    p.add_argument('--continue-after-private-probe-error',action='store_true')
    p.add_argument('--continue-after-restored-closure-timeout',action='store_true')
    p.add_argument('--conservative-end-ms',type=int)
    a=p.parse_args();value=qualify(Operator(a.kubeconfig,a.context,a.namespace),Operator(a.kubeconfig,a.context,a.replacement),a.chart,a.values,a.images,a.directory,a.authority_file,a.task,a.continue_after_inert_search_kill,a.continue_after_private_probe_error,a.continue_after_restored_closure_timeout,a.conservative_end_ms)
    print(json.dumps(dict(status=value['status'],directory=a.directory,additional_live_generations=0)))


if __name__=='__main__':main()
