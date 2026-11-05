"""Finite observations of actual pilot pods; no native/effect submission.

The observer inspects each owner's own process/filesystem namespace. It never
mounts a foreign volume, reads journal contents or contacts a model runtime.
Configured controls and observed process/cgroup values remain distinct.
"""
import argparse,json
from pathlib import Path
from fusion.contracts import canonical,digest,require
from integration.single_node.reference_ops import Operator,PYTHON

SOURCE='''import errno,importlib.util,json,os
from pathlib import Path
from integration.single_node.measure import sample
status={}
for line in Path('/proc/self/status').read_text().splitlines():
 key,_,value=line.partition(':')
 if key in ('Uid','Gid','CapEff','CapBnd','NoNewPrivs','Seccomp'):status[key]=value.strip()
probe=Path('/pilot-readonly-probe')
assert not probe.exists()
try:
 fd=os.open(probe,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
except OSError as error:root_write=dict(denied=True,errno=error.errno)
else:
 os.close(fd);probe.unlink();root_write=dict(denied=False,errno=None)
roles=ROLE
is_caller=roles in ('omega-agent','omega-agent-b','omega-workbench')
absent={}
if is_caller:
 for name in ('torch','transformers','sentence_transformers'):
  absent[name]=importlib.util.find_spec(name) is None
 absent['model_weights']=not Path('/opt/model/model.safetensors').exists()
 # Paths of the declared provider-owned storage and vector journal; missing
 # here is corroborated by the live Pod's mount list, not an ACL inference.
 absent['provider_feed']=not Path('/state/memory/feed.sqlite').exists()
 absent['provider_index']=not Path('/state/memory/chroma').exists()
model_isolation=None
if roles=='fusion-model':
 model_isolation=dict(storage_feed_absent=not Path('/state/memory/feed.sqlite').exists(),
  vector_index_absent=not Path('/state/memory/chroma').exists(),
  caller_sessions_absent=not Path('/state/sessions').exists())
print(json.dumps(dict(uid=os.getuid(),gid=os.getgid(),process=status,root_write=root_write,
 service_account_token_absent=not Path('/var/run/secrets/kubernetes.io/serviceaccount/token').exists(),
 caller_absence=absent,model_filesystem_isolation=model_isolation,resources=sample(),
 cpu_quota_enforcement='NOT_ESTABLISHED',memory_limit_enforcement='COUNTERS_ONLY_NOT_STRESS_TESTED')))
'''


def observe(op,destination):
    path=Path(destination);require(not path.exists(),'CONFLICT');op.owned()
    report=dict(profile='operator-pilot-runtime-observation/1',namespace=op.namespace,status='RUNNING',
        source_sha256=digest(Path(__file__).read_bytes()),roles={},additional_live_generations=0,
        journal_contents_collected=False,host_modified=False)
    def save():path.write_bytes(canonical(report))
    try:
        pods=json.loads(op.k('get','pods','-l','app.kubernetes.io/instance=omega','-o','json'))['items']
        require(1<=len(pods)<=16,'OVERLOADED')
        roles={pod['metadata']['labels']['app.kubernetes.io/name'] for pod in pods}
        services=json.loads(op.k('get','services','-o','json'))['items']
        require(bool(services) and all(v['spec'].get('type','ClusterIP')=='ClusterIP' for v in services),'UNAUTHORIZED')
        for service in services:
            name=service['metadata']['name']
            role=name[:-5] if name.endswith('-pods') else name
            require(role in roles and service['spec']['selector']=={
                'app.kubernetes.io/instance':'omega','app.kubernetes.io/name':role},'UNAUTHORIZED')
            require((service['spec'].get('clusterIP')=='None')==name.endswith('-pods'),'UNAUTHORIZED')
            require(not service['spec'].get('externalIPs') and not service['spec'].get('externalName'),'UNAUTHORIZED')
        report['service_exposure']='CLUSTER_IP_ONLY'
        claimed=set()
        for pod in pods:
            name=pod['metadata']['name'];role=pod['metadata']['labels']['app.kubernetes.io/name'];spec=pod['spec']
            require(len(spec['containers'])==1 and not spec.get('initContainers'),'UNSUPPORTED_PROFILE')
            require(pod['status']['phase']=='Running' and any(c['type']=='Ready' and c['status']=='True' for c in pod['status'].get('conditions',[])),'NOT_AVAILABLE')
            require(not any(spec.get(k) for k in ('hostNetwork','hostPID','hostIPC')) and spec.get('automountServiceAccountToken') is False,'UNAUTHORIZED')
            require(not any('hostPath' in v for v in spec.get('volumes',[])),'UNAUTHORIZED')
            container=spec['containers'][0];security=container['securityContext']
            require(security['readOnlyRootFilesystem'] is True and security['allowPrivilegeEscalation'] is False and security['capabilities']['drop']==['ALL'],'UNAUTHORIZED')
            claims=[v['persistentVolumeClaim']['claimName'] for v in spec.get('volumes',[]) if 'persistentVolumeClaim' in v]
            require(not (set(claims)&claimed),'UNAUTHORIZED');claimed.update(claims)
            require(claims==([] if role=='omega-workbench' else ['state-'+role+'-0']),'UNAUTHORIZED')
            row=dict(pod_uid=pod['metadata']['uid'],image=container['image'],image_id=pod['status']['containerStatuses'][0]['imageID'],
                configured_resources=container['resources'],configured_security=security,pod_security=spec.get('securityContext',{}),
                owner_pvc_count=len(claims),foreign_pvc_mounts=False)
            report['roles'][role]=row;save()
            if role in ('f1r3node','fusion-inspect-go'):
                row['process_observation']='NOT_SUPPORTED_BY_THIS_PYTHON_OBSERVER'
                continue
            source=SOURCE.replace('roles=ROLE','roles='+repr(role))
            actual=json.loads(op.k('exec','-i',name,'--',PYTHON,'-',data=source,timeout=40))
            require(actual['uid']!=0 and actual['gid']!=0 and actual['root_write']['denied'] and actual['service_account_token_absent'],'UNAUTHORIZED')
            require(int(actual['process']['CapEff'],16)==0 and actual['process']['NoNewPrivs']=='1','UNAUTHORIZED')
            require(all(actual['caller_absence'].values()),'UNAUTHORIZED')
            if actual['model_filesystem_isolation'] is not None:require(all(actual['model_filesystem_isolation'].values()),'UNAUTHORIZED')
            current=json.loads(op.k('get','pod',name,'-o','json'))
            require(current['metadata']['uid']==row['pod_uid'],'CONFLICT')
            row['observed']=actual;save()
        report.update(status='PASS',cpu_quota_enforcement='NOT_ESTABLISHED',
            limits=['Configured resource requests/limits are not proof of host enforcement',
                'Process RSS may count shared pages more than once; observer process included',
                'Cgroup counters are observations, not a quota stress test',
                'No malicious-host or production multitenancy claim'])
    except BaseException as error:
        report.update(status='FAIL',failure=dict(type=type(error).__name__,code=getattr(error,'code',None)));raise
    finally:save()
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('kubeconfig','context','namespace','output'):p.add_argument('--'+name,required=True)
    a=p.parse_args();v=observe(Operator(a.kubeconfig,a.context,a.namespace),a.output)
    print(json.dumps(dict(status=v['status'],roles=len(v['roles']),additional_live_generations=0)))


if __name__=='__main__':main()
