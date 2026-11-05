"""Trusted installed operator observations for planned synthetic handover.

These observations come from the selected k3s API, exact quiesced exports and a
real stale-startup probe. Neither browser booleans nor model text enter the fence
decision. Callers must first provision the chart's external authority Secret.
All inputs/reports are task-private; no credential values are returned.
"""
import base64
import json
import time
from pathlib import Path

from fusion.contracts import canonical, digest, require
from fusion.pilot_writer_fence import Handover
from .pilot_backup import MAX_MANIFEST, MAX_TOTAL, read, owner_manifest

FRESH_LABEL='omega.pilot/task'


class ClusterObserver:
    def __init__(self, original, replacement, *, task, authority, secret, source_backup,
                 dependency_report, replacement_backup, restart_probe):
        require(original.namespace != replacement.namespace and task and secret, 'UNAUTHORIZED')
        self.original, self.replacement, self.task = original, replacement, task
        self.authority, self.secret = Path(authority), secret
        self.source_backup, self.dependency_report = Path(source_backup), Path(dependency_report)
        self.replacement_backup, self.restart_probe = Path(replacement_backup), Path(restart_probe)
        self.uids={op.namespace:self._owned(op)['metadata']['uid'] for op in (original,replacement)}

    def _owned(self, op):
        value=op.owned()
        require(value['metadata'].get('labels',{}).get(FRESH_LABEL)==self.task,'UNAUTHORIZED')
        if hasattr(self,'uids'):require(value['metadata']['uid']==self.uids[op.namespace],'CONFLICT')
        return value

    def _writers(self, op):
        self._owned(op); workloads=op.workloads()
        pods=json.loads(op.k('get','pods','-l','app.kubernetes.io/instance='+op.release,'-o','json'))['items']
        per_role={x['metadata']['name']:dict(desired=x['spec']['replicas'],pods=0,ready=0) for x in workloads}
        for pod in pods:
            role=pod['metadata'].get('labels',{}).get('app.kubernetes.io/name')
            require(role in per_role,'UNAUTHORIZED');per_role[role]['pods']+=1
            per_role[role]['ready']+=int(any(c['type']=='Ready' and c['status']=='True' for c in pod.get('status',{}).get('conditions',[])))
        require(all(x['desired']<=1 and x['pods']<=1 for x in per_role.values()),'UNAUTHORIZED')
        # One writer generation spanning independent single-writer logical
        # owners, not a claim that the namespace contains one physical pod.
        return dict(writers=int(any(x['desired'] or x['pods'] for x in per_role.values())),
                    qualified_writer_generation_count=int(any(x['desired'] or x['pods'] for x in per_role.values())),
                    per_role=per_role)

    def _backup(self, root, op):
        raw=read(root/'manifest.json',MAX_MANIFEST)
        require(digest(raw)==read(root/'manifest.sha256',65).decode().strip(),'CONFLICT')
        value=json.loads(raw)
        require(value['schema']=='synthetic-quiesced-backup/1' and value['authority_excluded'] is True and
                value['original_remains_quiesced'] is True and value['before']['namespace']==op.namespace and
                value['before']['namespace_uid']==self.uids[op.namespace],'UNAUTHORIZED')
        owners={}
        for role,item in value['owners'].items():
            require(item['file']==role+'.tar.gz','CONFLICT')
            blob=read(root/item['file'],MAX_TOTAL)
            require(len(blob)==item['bytes'] and digest(blob)==item['sha256'],'CONFLICT')
            owners[role]=owner_manifest(blob,role)
            require(owners[role].get('integrity',{}).get('status')=='PASS','NOT_AVAILABLE')
        return digest(raw),value,owners

    def _current_cut(self, op, manifest, owners):
        """Compare with fresh exports of the CURRENT stopped PVCs, never labels.

        Read/checkpoint is inside each existing owner maintenance pod. Gzip
        timestamp differences do not change its exact enumerated file hashes.
        No host/database crossing or mutation executor is involved.
        """
        from .reference_ops import PYTHON
        require(self._writers(op)['writers']==0,'UNAUTHORIZED')
        for role,expected in owners.items():
            name=op.helper(role,manifest['maintenance_image'],'state-'+role+'-0')
            try:
                raw=op.k('exec',name,'--',PYTHON,'-m','integration.single_node.backup_payload','export','--role',role,binary=True)
                current=owner_manifest(raw,role)
                require(current['files']==expected['files'] and current['archive_dependencies']==expected['archive_dependencies'],'CONFLICT')
                require(current['dependency_inventory']['head']==expected['dependency_inventory']['head'],'CONFLICT')
            finally:op.k('delete','pod',name,'--wait=true')
        require(self._writers(op)['writers']==0,'UNAUTHORIZED')

    def _cut(self):
        checkpoint,manifest,owners=self._backup(self.source_backup,self.original)
        self._current_cut(self.original,manifest,owners)
        closure=json.loads(read(self.dependency_report,MAX_MANIFEST))
        require(set(closure)==set(owners),'CONFLICT')
        for role,owner in owners.items():
            inventory=owner['dependency_inventory'];proof=closure[role]
            require(proof['status']=='VERIFIED_REFERENCES' and proof['owner']==role and proof['selected_head']==inventory['head'],'NOT_AVAILABLE')
            require(set(inventory['dependencies'])<=set(proof['observations']) and
                    proof['closure_sha256']==digest(canonical([inventory['head'],proof['observations']])),'CONFLICT')
        return checkpoint,digest(canonical(closure)),owners

    def sync_authority(self):
        raw=read(self.authority,262144)
        for op in (self.original,self.replacement):
            self._owned(op)
            op.apply(dict(apiVersion='v1',kind='Secret',metadata=dict(name=self.secret,namespace=op.namespace,
                labels={FRESH_LABEL:self.task}),type='Opaque',data={'current.json':base64.b64encode(raw).decode()}))
            actual=json.loads(op.k('get','secret',self.secret,'-o','json'))
            require(base64.b64decode(actual['data']['current.json'])==raw,'CONFLICT')
        return dict(authority_sha256=digest(raw),namespaces=[self.original.namespace,self.replacement.namespace])

    def fence_network(self):
        op=self.original;self._owned(op);require(self._writers(op)['writers']==0,'UNAUTHORIZED')
        # NetworkPolicy permissions are additive. Replace only this fresh task's
        # Helm-owned allow rules while every source writer is stopped. A deny-all
        # object by itself would not override them.
        policies=json.loads(op.k('get','networkpolicies','-o','json'))['items']
        for item in policies:
            if item['metadata']['name']=='pilot-retired-writer':continue
            annotations=item['metadata'].get('annotations',{})
            require(annotations.get('meta.helm.sh/release-name')==op.release and
                    annotations.get('meta.helm.sh/release-namespace')==op.namespace,'UNAUTHORIZED')
        op.apply(dict(apiVersion='networking.k8s.io/v1',kind='NetworkPolicy',metadata=dict(name='pilot-retired-writer',namespace=op.namespace,
            labels={FRESH_LABEL:self.task}),spec=dict(podSelector={},policyTypes=['Ingress','Egress'],ingress=[],egress=[])))
        for item in policies:
            if item['metadata']['name']!='pilot-retired-writer':op.k('delete','networkpolicy',item['metadata']['name'])
        return self._network_fenced()

    def _network_fenced(self):
        policies=json.loads(self.original.k('get','networkpolicies','-o','json'))['items']
        require(len(policies)==1,'UNAUTHORIZED');p=policies[0]
        require(p['metadata']['name']=='pilot-retired-writer' and p['metadata'].get('labels',{}).get(FRESH_LABEL)==self.task and
                p['spec']['podSelector']=={} and set(p['spec']['policyTypes'])=={'Ingress','Egress'} and
                not p['spec'].get('ingress') and not p['spec'].get('egress'),'UNAUTHORIZED')
        return dict(uid=p['metadata']['uid'],resource_version=p['metadata']['resourceVersion'],
                    configured_deny_all=True,packet_enforcement='SEPARATE_NETWORK_QUALIFICATION')

    def _credential_separation(self):
        sets=[]
        for op in (self.original,self.replacement):
            values=set()
            for secret in json.loads(op.k('get','secrets','-o','json'))['items']:
                if secret['metadata']['name']==self.secret:continue
                for key,value in secret.get('data',{}).items():
                    if key.endswith('-token'): values.add(digest(base64.b64decode(value)))
            require(values,'NOT_AVAILABLE');sets.append(values)
        require(not sets[0]&sets[1],'UNAUTHORIZED')
        return dict(old_token_count=len(sets[0]),replacement_token_count=len(sets[1]),overlap=0)

    def probe_stale_startup(self, role='omega-agent', timeout=45):
        """Actually start normal old entrypoint, observe refusal, then stop it.

        Must follow durable drain and Secret publication. Startup guard precedes
        owner initialization. Never invokes a native input or provider operation.
        """
        require(1<=timeout<=60 and role in ('omega-agent','omega-agent-b'),'INVALID_ARGUMENT')
        op=self.original;self._owned(op);require(self._writers(op)['writers']==0,'UNAUTHORIZED')
        current=json.loads(read(self.authority,262144));require(current['state'] in ('drained','retired'),'UNAUTHORIZED')
        self.sync_authority();self._network_fenced()
        sts=next(x for x in op.workloads() if x['metadata']['name']==role)
        require(any(v.get('secret',{}).get('secretName')==self.secret for v in sts['spec']['template']['spec']['volumes']),'UNAUTHORIZED')
        began=time.monotonic();observed=None
        try:
            op.k('scale','statefulset',role,'--replicas=1')
            while time.monotonic()-began<timeout:
                pods=json.loads(op.k('get','pods','-l','app.kubernetes.io/name='+role,'-o','json'))['items']
                if pods:
                    pod=pods[0];states=pod.get('status',{}).get('containerStatuses',[])
                    failed=any((s.get('state',{}).get('terminated') or s.get('lastState',{}).get('terminated',{})).get('exitCode',0)!=0 for s in states)
                    if failed:
                        raw=op.k('logs',pod['metadata']['name'],'--tail=60')
                        if 'pilot_writer_fence' in raw and 'UNAUTHORIZED' in raw:
                            observed=dict(pod_uid=pod['metadata']['uid'],role=role,image=sts['spec']['template']['spec']['containers'][0]['image'],
                                          startup_refused=True,authority_sha256=digest(read(self.authority,262144)),
                                          log_sha256=digest(raw.encode()),seconds=time.monotonic()-began)
                            break
                time.sleep(.5)
        finally:
            op.k('scale','statefulset',role,'--replicas=0')
            if json.loads(op.k('get','pods','-l','app.kubernetes.io/name='+role,'-o','json'))['items']:
                op.k('wait','--for=delete','pod','-l','app.kubernetes.io/name='+role,'--timeout=60s',timeout=65)
        require(observed is not None,'NOT_AVAILABLE')
        from .pilot_backup import private_write
        private_write(self.restart_probe,canonical(observed));return observed

    def __call__(self, stage, deployment):
        require(deployment in (self.original.namespace,self.replacement.namespace),'UNAUTHORIZED')
        op=self.original if deployment==self.original.namespace else self.replacement
        counts=self._writers(op)
        if stage=='initial':return dict(counts,task_owned=True,fresh_synthetic=True)
        checkpoint,closure,source=self._cut()
        if stage=='drained-current-checkpoint':
            require(counts['writers']==0,'UNAUTHORIZED')
            # All stopped independently owned writers are fenced as unresolved.
            # This observation does not terminalize or retry any historical work.
            return dict(counts,task_owned=True,fresh_synthetic=True,admission_closed=True,unresolved_effects_fenced=True,
                        accounting_verified=True,checkpoint_sha256=checkpoint,closure_sha256=closure)
        if stage=='retired-original':
            network=self._network_fenced();credentials=self._credential_separation()
            probe=json.loads(read(self.restart_probe,8192));require(probe['startup_refused'] is True,'NOT_AVAILABLE')
            current=json.loads(read(self.authority,262144))
            require(current['state'] in ('drained','retired') or current['deployment']!=self.original.namespace,'UNAUTHORIZED')
            return dict(counts,network_fenced=True,network_policy=network,service_credentials_revoked=True,
                        credential_separation=credentials,stale_restart_refused=True,stale_startup_probe=probe,
                        authority_outside_imported_state=True)
        require(stage=='qualified-replacement' and op is self.replacement,'UNSUPPORTED_OPERATION')
        _,target_manifest,target=self._backup(self.replacement_backup,self.replacement)
        self._current_cut(self.replacement,target_manifest,target)
        require(set(source)==set(target),'CONFLICT')
        for role,original in source.items():
            restored=target[role]
            changed={k for k,v in original['files'].items() if restored['files'].get(k)!=v}
            original_tables={x['identity']:x for x in original['dependency_inventory']['entries'] if x['kind']=='owner-table'}
            restored_tables={x['identity']:x for x in restored['dependency_inventory']['entries'] if x['kind']=='owner-table'}
            transformed=workspace_transform(original,restored,checkpoint)
            require(changed<=({'session-inbox.sqlite'} if role in ('omega-agent','omega-agent-b') else set())|transformed['files'],'CONFLICT')
            require(all(restored_tables.get(k)==v for k,v in original_tables.items() if k not in transformed['tables']),'CONFLICT')
            require(set(restored_tables)-set(original_tables)<={'session-inbox.sqlite:pilot_historical_sessions'}|transformed['added'],'CONFLICT')
            require(set(restored['files'])-set(original['files'])<={'restore-fence.json','pilot-activation.json','pilot-activation-intent.json'},'CONFLICT')
            require('restore-fence.json' in restored['files'],'UNAUTHORIZED')
        return dict(counts,task_owned=True,fresh_synthetic=True,checkpoint_sha256=checkpoint,closure_sha256=closure,
                    accounting_verified=True,historical_effects_observation_only=True,execution_authority_imported=False)


def workspace_transform(original,restored,checkpoint):
    """Validate only the named owner-exported physical-root transformation."""
    empty=dict(files=set(),tables=set(),added=set())
    receipt=restored.get('workspace_root_reattestation')
    if receipt is None:return empty
    from fusion.preview_workspace import ROOT_HANDOVER,ROOT_RECEIPT,PROFILE
    require(original['role']==restored['role']=='fusion-execution' and 'workspace_root_reattestation' not in original,'UNAUTHORIZED')
    require(set(receipt)=={'profile','scope','checkpoint_sha256','generation','previous','current','tables','files'} and
        receipt['profile']==ROOT_HANDOVER and receipt['scope']==original['seal']['scope']==restored['seal']['scope'] and
        receipt['checkpoint_sha256']==checkpoint and receipt['generation']==2,'CONFLICT')
    before,after=receipt['previous'],receipt['current']
    require(type(before) is list and type(after) is list and len(before)==len(after)==4 and before[:2]==after[:2]==[PROFILE,receipt['scope']] and
            all(type(x) is int and x>=0 for x in before[2:]+after[2:]) and before!=after,'CONFLICT')
    tables=lambda value:{x['identity']:x for x in value['dependency_inventory']['entries'] if x['kind']=='owner-table'}
    old,new=tables(original),tables(restored);journal='preview-facets/workspace.sqlite';meta=journal+':workspace_meta';added=journal+':'+ROOT_RECEIPT
    require(set(receipt['tables'])=={'workspace_files','workspace_effects'},'CONFLICT')
    for table,proof in receipt['tables'].items():
        key=journal+':'+table
        require(key in old and new.get(key)==old[key] and proof=={k:old[key][k] for k in ('rows','columns','semantic_head')},'CONFLICT')
    def check_table(entry,columns,rows):
        require(entry['columns']==columns and entry['rows']==len(rows) and entry['semantic_head']==digest(canonical(sorted(digest(canonical(row)) for row in rows))),'CONFLICT')
    require(meta in old and meta in new and added not in old and added in new,'CONFLICT')
    check_table(old[meta],['profile','scope','root_device','root_inode'],[before]);check_table(new[meta],old[meta]['columns'],[after])
    require({k:v for k,v in old[meta].items() if k!='semantic_head'}=={k:v for k,v in new[meta].items() if k!='semantic_head'},'CONFLICT')
    check_table(new[added],['singleton','value'],[[1,canonical(receipt).decode()]])
    actual={k.removeprefix('preview-facets/workspace/'):v for k,v in original['files'].items() if k.startswith('preview-facets/workspace/')}
    require(actual==receipt['files'] and all(restored['files'].get('preview-facets/workspace/'+k)==v for k,v in actual.items()),'CONFLICT')
    return dict(files={journal},tables={meta},added={added})


def operator(original,replacement,*,authorize,**settings):
    observer=ClusterObserver(original,replacement,**settings)
    owner=Handover(observer.authority,authorize,observer,imported_roots=[observer.source_backup,observer.replacement_backup])
    return owner,observer


def main():
    import argparse
    from .reference_ops import Operator
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=('initialize','plan','fence-network','probe-stale-startup','retire','activate','observe','sync-authority'))
    p.add_argument('--configuration',required=True);p.add_argument('--identity');p.add_argument('--role',default='omega-agent')
    a=p.parse_args();cfg=json.loads(read(a.configuration,32768))
    required={'kubeconfig','context','original','replacement','task','authority','secret','source_backup',
              'dependency_report','replacement_backup','restart_probe','original_incarnation','replacement_incarnation','methods'}
    require(set(cfg)==required,'INVALID_ARGUMENT')
    old=Operator(cfg['kubeconfig'],cfg['context'],cfg['original']);new=Operator(cfg['kubeconfig'],cfg['context'],cfg['replacement'])
    def authorize(_):
        for op in (old,new):require(op.owned()['metadata'].get('labels',{}).get(FRESH_LABEL)==cfg['task'],'UNAUTHORIZED')
    owner,observe=operator(old,new,authorize=authorize,**{k:cfg[k] for k in
        ('task','authority','secret','source_backup','dependency_report','replacement_backup','restart_probe')})
    if a.action=='initialize':value=owner.initialize(old.namespace,cfg['original_incarnation'],cfg['methods'])
    elif a.action=='plan':
        checkpoint,closure,_=observe._cut();value=owner.plan(a.identity,new.namespace,cfg['replacement_incarnation'],checkpoint,closure)
    elif a.action=='fence-network':value=observe.fence_network()
    elif a.action=='probe-stale-startup':value=observe.probe_stale_startup(a.role)
    elif a.action=='retire':value=owner.retire(a.identity)
    elif a.action=='activate':value=owner.activate(a.identity)
    elif a.action=='sync-authority':value=observe.sync_authority()
    else:value=owner.read()
    if a.action in ('initialize','plan','retire','activate'):observe.sync_authority()
    print(json.dumps(value,sort_keys=True))


if __name__=='__main__':main()
