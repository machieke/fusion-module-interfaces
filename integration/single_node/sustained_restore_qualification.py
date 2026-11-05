"""Fenced Phase 3 observation drill over existing quiesced owner archives.

No old authority is imported. Original and clone finish stopped. Private backup
archives stay in the operator's mode-0700 scratch directory, never evidence.
"""
import argparse,copy,json,time
from pathlib import Path
from fusion.contracts import canonical,digest,require
from .reference_ops import Operator,PYTHON


def clone_values(source):
    value=copy.deepcopy(source);p=value['preview']
    require(p['profile']=='omega-single-node-sustained-preview/1' and p['scope'].startswith('synthetic-'),'UNAUTHORIZED')
    require(not value.get('futureLive',{}).get('activated'),'UNAUTHORIZED')
    value['futureLive']=dict(enabled=False,activated=False);value['testFaultsEnabled']=False
    if 'chain' in p:p['chain'].update(enabled=False,nodeEnabled=False,isolationVerified=False,registration=None)
    for role in ('omega-agent','fusion-execution','fusion-storage','fusion-messaging'):
        value['components'].setdefault(role,{})
    for role,component in value['components'].items():
        component.setdefault('config',{}).update(nativeEnabled=False,workerEnabled=False,test={})
        if role=='f1r3node':component['enabled']=False
    return value


def readonly_pilot_values(selected,original_namespace,clone_namespace,restored,fences):
    """Remove only execution credentials after observing an actual fenced clone.

    This does not create a fence or authorize a writer transition. The caller
    reads every imported owner's existing marker on an otherwise empty clone.
    """
    value=copy.deepcopy(selected);pilot=value['preview'].get('pilot',{})
    require(original_namespace!=clone_namespace and clone_namespace.startswith('omega-ref-pilot-')
        and 'omega-demo' not in clone_namespace,'UNAUTHORIZED')
    require(restored.get('status')=='RESTORED_FENCED' and restored.get('namespace')==clone_namespace
        and restored.get('automatic_resume') is False,'UNAUTHORIZED')
    roles=restored.get('roles',[])
    require(roles and all(x.get('status')=='RESTORED_FENCED' for x in roles)
        and len({x['role'] for x in roles})==len(roles)
        and set(fences)=={x['role'] for x in roles},'UNAUTHORIZED')
    scope=value['preview']['scope']
    require(scope.startswith('synthetic-') and value['futureLive']==dict(enabled=False,activated=False),'UNAUTHORIZED')
    for role,fence in fences.items():
        require(fence.get('mode')=='READ_ONLY_RECONCILIATION' and fence.get('external_effect_authority') is False
            and fence.get('role')==role and fence.get('namespace')==clone_namespace
            and fence.get('original_scope')==scope,'UNAUTHORIZED')
    for component in value['components'].values():
        config=component.get('config',{})
        require(config.get('nativeEnabled') is False and config.get('workerEnabled') is False,'UNAUTHORIZED')
    chain=value['preview'].get('chain',{})
    require(not chain.get('enabled') and not chain.get('nodeEnabled') and chain.get('registration') is None,'UNAUTHORIZED')
    if 'writer_fence' in pilot:
        require(pilot['writer_fence'].get('deployment')==original_namespace,'UNAUTHORIZED')
        pilot.pop('writer_fence')
    pilot.pop('handover',None)
    for component in value['components'].values():component.pop('writerAuthoritySecret',None)
    return value


def observed_restore_fences(clone,backup,restored):
    """Read existing markers through bounded, exclusively mounted owner helpers."""
    require(restored.get('status')=='RESTORED_FENCED' and restored.get('namespace')==clone.namespace,'UNAUTHORIZED')
    require(not json.loads(clone.k('get','pods','-o','json'))['items'],'UNAUTHORIZED')
    require(set(backup['owners'])=={x['role'] for x in restored['roles']},'CONFLICT')
    fences={}
    code="import json;from pathlib import Path;p=Path('/state/restore-fence.json');assert p.is_file() and not p.is_symlink() and p.stat().st_size<=4096;print(json.dumps(json.loads(p.read_bytes())))"
    for role in backup['owners']:
        name=clone.helper(role,backup['maintenance_image'],'state-'+role+'-0',readonly=True)
        try:fences[role]=json.loads(clone.k('exec',name,'--',PYTHON,'-c',code,timeout=30))
        finally:clone.k('delete','pod',name,'--wait=true')
    require(not json.loads(clone.k('get','pods','-o','json'))['items'],'UNAUTHORIZED')
    return fences


def drill(original,clone,values,chart,directory,*,maintenance_image=None,images=None,after_restore=None):
    import yaml,subprocess,sys
    root=Path(directory);root.mkdir(mode=0o700,parents=True,exist_ok=False)
    original.owned();require(clone.namespace!=original.namespace,'UNAUTHORIZED')
    report=dict(profile='sustained-fenced-restore-qualification/1',original=original.namespace,clone=clone.namespace,
        additional_live_generations=0,status='RUNNING',observations=[],private_archive_publication='FORBIDDEN')
    report['images']={x['metadata']['name']:x['spec']['template']['spec']['containers'][0]['image']
        for x in original.workloads()}
    def save():(root/'report.json').write_bytes(canonical(report))
    def call(op,role,operation,sid=None,*args):
        command=[PYTHON,'-m','integration.single_node.preview_operator',operation]
        if sid:command+=['--session',sid]
        return json.loads(op.k('exec',role+'-0','--',*command,*args,timeout=45))
    original_rows={}
    for role in ('omega-agent','omega-agent-b'):
        rows=call(original,role,'list');original_rows[role]={}
        for row in rows:
            observed=call(original,role,'observe',row['session'],'--content')
            original_rows[role][row['session']]=observed
    save();created=False
    try:
        backup=original.backup(root/'private-backup',**({'maintenance_image':maintenance_image} if maintenance_image else {}));report['backup_manifest_sha256']=digest(canonical(backup));save()
        selected=clone_values(yaml.safe_load(Path(values).read_text()))
        if images is not None:
            require(images.get('source_export_verification')=='PASS','CONFLICT')
            pinned={x['repository']:x for x in images['images']}
            for entry in [selected['image'],*[c['image'] for c in selected['components'].values() if 'image' in c]]:
                require(entry['repository'] in pinned,'NOT_AVAILABLE');pin=pinned[entry['repository']]
                require(pin['kind']!='generative','UNAUTHORIZED')
                entry.update(digest=pin['manifest_digest'],tag=pin['local_tag'].rsplit(':',1)[1],pullPolicy='Never')
            report['restored_runtime_source_manifest_sha256']=images['source_manifest_sha256']
        path=root/'clone-values.yaml';path.write_text(yaml.safe_dump(selected,sort_keys=False))
        clone.create();created=True;report['restore']=clone.restore(root/'private-backup');save()
        if selected['preview'].get('pilot',{}).get('writer_fence'):
            fences=observed_restore_fences(clone,backup,report['restore'])
            selected=readonly_pilot_values(selected,original.namespace,clone.namespace,report['restore'],fences)
            path.write_text(yaml.safe_dump(selected,sort_keys=False))
            report['pilot_clone_selection']=dict(mode='READ_ONLY_RECONCILIATION',owner_markers_observed=sorted(fences),
                writer_authority_selected=False,external_effect_authority=False,source_values_unchanged=True);save()
        # The installed package supplies the same audited secret recipe.
        from fusion_operator.recipes import create_secrets
        old=sys.argv
        try:
            sys.argv=['fusion-create-secrets','--preview-values',str(path),'--kubeconfig',clone.kubeconfig,'--context',clone.context,'--namespace',clone.namespace,'--directory',str(root/'private-secrets')]
            create_secrets.main()
        finally:sys.argv=old
        (root/'clone-install.log').write_text(clone.command(['helm','upgrade','--install','omega',str(chart),'-f',str(path),'--namespace',clone.namespace,'--kubeconfig',clone.kubeconfig,'--kube-context',clone.context,'--wait','--timeout','300s'],timeout=320))
        report['clone_images']={x['metadata']['name']:x['spec']['template']['spec']['containers'][0]['image']
            for x in clone.workloads()};save()
        for role,rows in original_rows.items():
            restored=call(clone,role,'list');require({x['session'] for x in restored}==set(rows),'CONFLICT')
            for sid,before in rows.items():
                after=call(clone,role,'observe',sid,'--content')
                require(after['restore_fenced'] is True and after['execution_authorized'] is False,'CONFLICT')
                for key in ('inputs','binding','allocation','capacity','state'):require(after[key]==before[key],'CONFLICT')
                current=call(clone,role,'current',sid)
                require(current['restore_fenced'] is True,'CONFLICT')
                report['observations'].append(dict(role=role,scope_class='private' if before['allocation']['template']=='private' else 'shared',
                    original_session_digest=digest(sid.encode()),retained_inputs=len(before['inputs']),captured_projection_digest=digest(canonical(before['inputs'])),
                    current_source_sequence=current.get('source_head',{}).get('sequence'),original_allocation_retained=True,
                    original_deadlines_and_accounting_retained=True,current_owner_reads='PASS'))
                save()
            # A disabled UI flag is not the fence: the actual API refuses all
            # executable work, even with the newly issued operator credential.
            for operation,args in [('allocate',['--identity','forbidden-replay','--template','shared']),('reconcile',['--session',next(iter(rows))])]:
                try:call(clone,role,operation,None,*args)
                except RuntimeError:pass
                else:require(False,'CONFLICT')
        if after_restore is not None:report['additional_observation']=after_restore(clone)
        report.update(status='PASS',original_writers_quiesced=True,restored_execution_authority=False,duplicate_effect_execution='NO_EXECUTOR_STARTED');save()
    except BaseException as error:
        report.update(status='FAILED',failure=dict(type=type(error).__name__,code=getattr(error,'code',None),detail=str(error)[-1200:]));save();raise
    finally:
        if created:
            try:clone.quiesce();report['clone_quiesced']=True
            except Exception as error:report['clone_quiesced']=False;report['cleanup_error']=type(error).__name__
        original.quiesce();report['original_quiesced']=True;save()
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('kubeconfig','context','original','clone','values','chart','directory'):p.add_argument('--'+name,required=True)
    a=p.parse_args();value=drill(Operator(a.kubeconfig,a.context,a.original),Operator(a.kubeconfig,a.context,a.clone),a.values,a.chart,a.directory)
    print(json.dumps(value))
if __name__=='__main__':main()
