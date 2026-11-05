"""Closed operator provisioning/observation for the independent Go owner.

One fresh existing Secret key; one selected HTTPS GET through the extracted Go
client. No caller credential mounting, owner journal access, execution or retry.
"""
import argparse,base64,copy,json,secrets,socket,subprocess,time
from pathlib import Path
from fusion.contracts import canonical,digest,require
from integration.single_node.reference_ops import Operator
from integration.single_node.placement import compile
from integration.single_node.pilot_provider_image import verify

ROLE='fusion-inspect-go'
KEY='inspect-capacity-token'
PROFILE='go-inspect-capacity-client/1'


def selected(op,plan_path,artifact,chart):
    raw=Path(plan_path).read_bytes();plan=json.loads(raw)
    require(plan['namespace']==op.namespace and plan['scope'].startswith('synthetic-'),'UNAUTHORIZED')
    checked=verify(artifact);objects=compile(plan,chart)['objects'];node=plan['graph']['nodes'][ROLE]
    require(node['image']==checked['repository']+'@'+checked['manifest'],'CONFLICT')
    require(node['secret_refs']==[ROLE+'-tls-auth'] and node['host']==ROLE+'.'+op.namespace+'.svc.cluster.local','UNAUTHORIZED')
    cfg=next(x for x in objects if x['kind']=='ConfigMap' and x['metadata']['name']==ROLE)
    policy=json.loads(cfg['data']['policy.json'])
    require(policy['principals']['capacity-operator']==dict(credential_file='/secrets/'+KEY,scopes={plan['scope']:['execution.capacity']}),'UNAUTHORIZED')
    require(all('execution.capacity' not in permissions for name,p in policy['principals'].items() if name!='capacity-operator' for permissions in p['scopes'].values()),'UNAUTHORIZED')
    return plan,node,checked,digest(raw)


def private(path):
    root=Path(path).resolve();root.mkdir(mode=0o700,parents=True,exist_ok=False);root.chmod(0o700);return root


def provision(op,plan_path,artifact,chart,directory):
    plan,node,checked,plan_hash=selected(op,plan_path,artifact,chart);op.owned()
    # Provision once, before this owner first starts. No credential rotation or
    # inherited accepted workload is expressible by this helper.
    for kind,prefix in (('statefulsets',ROLE),('pods',ROLE+'-'),('pvc','state-'+ROLE+'-')):
        rows=json.loads(op.k('get',kind,'-o','json'))['items']
        require(not any(x['metadata']['name']==prefix or x['metadata']['name'].startswith(prefix) for x in rows),'CONFLICT')
    original=json.loads(op.k('get','secret',ROLE+'-tls-auth','-o','json'))
    require(original['metadata']['namespace']==op.namespace and KEY not in original.get('data',{}) and original.get('immutable') is not True,'CONFLICT')
    ca=base64.b64decode(original['data']['ca.crt'],validate=True)
    require(ca.startswith(b'-----BEGIN CERTIFICATE-----'),'UNAUTHORIZED')
    root=private(directory);token=secrets.token_hex(32).encode()
    (root/'credential').write_bytes(token);(root/'credential').chmod(0o600)
    (root/'ca.crt').write_bytes(ca);(root/'ca.crt').chmod(0o600)
    receipt=dict(profile='go-capacity-provisioning/1',status='PREPARED',namespace=op.namespace,scope=plan['scope'],secret=ROLE+'-tls-auth',key=KEY,
        plan_sha256=plan_hash,artifact_sha256=checked['manifest_sha256'],permission='execution.capacity',credential_values_exported=False,
        caller_permissions_changed=False,owner_starts=0,additional_live_generations=0)
    (root/'receipt.json').write_bytes(canonical(receipt))
    updated=copy.deepcopy(original);updated['data'][KEY]=base64.b64encode(token).decode()
    # resourceVersion is retained for optimistic concurrency. Operator's Secret
    # diagnostic suppression applies to the complete typed Secret document.
    op.k('replace','-f','-',data=json.dumps(updated))
    actual=json.loads(op.k('get','secret',ROLE+'-tls-auth','-o','json'))
    require(actual['metadata']['uid']==original['metadata']['uid'] and actual['data']==updated['data'],'CONFLICT')
    receipt['status']='PROVISIONED';(root/'receipt.json').write_bytes(canonical(receipt));return receipt


def observe(op,plan_path,artifact,chart,provisioned,directory,deadline_ms):
    require(type(deadline_ms) is int and 0<deadline_ms-int(time.time()*1000)<=120000,'INVALID_ARGUMENT')
    plan,node,checked,plan_hash=selected(op,plan_path,artifact,chart);op.owned()
    auth=Path(provisioned).resolve();receipt=json.loads((auth/'receipt.json').read_bytes())
    require(receipt['status']=='PROVISIONED' and receipt['namespace']==op.namespace and receipt['scope']==plan['scope']
        and receipt['artifact_sha256']==checked['manifest_sha256'],'CONFLICT')
    pod=json.loads(op.k('get','pod',ROLE+'-0','-o','json'))
    require(len(pod['spec']['containers'])==1 and pod['spec']['containers'][0]['image']==node['image'],'CONFLICT')
    statuses=pod['status'].get('containerStatuses',[])
    require(len(statuses)==1 and statuses[0]['ready'] is True and statuses[0]['imageID'].split('@')[-1] in (checked['manifest'],checked['configuration']),'NOT_AVAILABLE')
    root=private(directory)
    client=Path(artifact).resolve().parent/'kit/omega-client'
    # verify() above checks the exact source archive, static ELF and client hash.
    require(client.is_file() and not client.is_symlink(),'UNAUTHORIZED')
    with socket.socket() as listener:
        listener.bind(('127.0.0.1',0));port=listener.getsockname()[1]
    cfg=dict(profile=PROFILE,scope=plan['scope'],provider=checked['contract'],endpoint=dict(url='https://'+node['host']+':'+str(port),ca_file='/operator/ca.crt',credential_file='/operator/credential'))
    (root/'client.json').write_bytes(canonical(cfg));(root/'hosts').write_text('127.0.0.1 '+node['host']+'\n');(root/'nsswitch.conf').write_text('hosts: files\n')
    report=dict(profile='go-capacity-operator-observation/1',status='RUNNING',namespace=op.namespace,scope=plan['scope'],plan_sha256=plan_hash,
        artifact_sha256=checked['manifest_sha256'],source_manifest_sha256=checked['source_manifest_sha256'],provider_image=node['image'],
        observed_image_id=statuses[0]['imageID'],pod_uid=pod['metadata']['uid'],deadline_ms=deadline_ms,
        placement='authenticated HTTPS through explicit private loopback port-forward',client_isolation='static verified kit client; private hosts view; no caller/owner files',
        client_invocations=0,validated_owner_observations=0,maximum_http_calls=1,execution_calls=0,additional_live_generations=0)
    def save():(root/'report.json').write_bytes(canonical(report))
    save();forward=None
    try:
        with (root/'port-forward.log').open('wb') as output:
            argv=['kubectl','--kubeconfig',op.kubeconfig,'--context',op.context,'-n',op.namespace,'port-forward','--address','127.0.0.1','pod/'+ROLE+'-0',str(port)+':'+str(node['port'])]
            forward=subprocess.Popen(argv,stdout=output,stderr=subprocess.STDOUT)
            ready_by=min(time.monotonic()+10,time.monotonic()+max(0,(deadline_ms-time.time()*1000)/1000))
            while time.monotonic()<ready_by:
                require(forward.poll() is None,'NOT_AVAILABLE')
                log=(root/'port-forward.log').read_bytes();require(len(log)<=16384,'OVERLOADED')
                if ('Forwarding from 127.0.0.1:'+str(port)).encode() in log:break
                time.sleep(.05)
            else:require(False,'DEADLINE_EXCEEDED')
            remaining=(deadline_ms-int(time.time()*1000))/1000;require(remaining>0,'DEADLINE_EXCEEDED')
            mounts=[(client,'/omega-client'),(root/'client.json','/config.json'),(root/'hosts','/etc/hosts'),(root/'nsswitch.conf','/etc/nsswitch.conf'),(auth/'ca.crt','/operator/ca.crt'),(auth/'credential','/operator/credential')]
            args=['bwrap','--die-with-parent','--unshare-pid','--unshare-ipc','--unshare-uts']
            for source,target in mounts:require(source.is_file() and not source.is_symlink(),'UNAUTHORIZED');args+=['--ro-bind',str(source),target]
            args+=['--proc','/proc','--dev','/dev','--tmpfs','/tmp','--clearenv','--setenv','HOME','/nonexistent','/omega-client','--action','inspect-capacity','--config','/config.json','--deadline-ms',str(deadline_ms)]
            report['client_invocations']=1;save()
            result=subprocess.run(args,capture_output=True,timeout=remaining)
            (root/'client.stdout').write_bytes(result.stdout);(root/'client.stderr').write_bytes(result.stderr)
            require(result.returncode==0,'NOT_AVAILABLE')
            value=json.loads(result.stdout);require(value['profile']=='go-inspect-capacity/1' and value['provider']==checked['contract'] and value['scope']==plan['scope'] and value['work_executed'] is False,'CONFLICT')
            report.update(status='PASS',capacity=value,validated_owner_observations=1,primary_sha256=digest(result.stdout));save()
    except BaseException as error:
        report.update(status='FAILED',failure=type(error).__name__+': '+str(error)[:300]);save();raise
    finally:
        if forward is not None:
            forward.terminate()
            try:forward.wait(timeout=5)
            except subprocess.TimeoutExpired:forward.kill();forward.wait(timeout=5)
        report['port_forward_stopped']=forward is None or forward.poll() is not None;save()
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=('provision','observe'))
    for name in ('kubeconfig','context','namespace','plan','artifact','chart','directory'):p.add_argument('--'+name,required=True)
    p.add_argument('--provisioned');p.add_argument('--deadline-ms',type=int)
    a=p.parse_args();op=Operator(a.kubeconfig,a.context,a.namespace)
    if a.action=='provision':result=provision(op,a.plan,a.artifact,a.chart,a.directory)
    else:require(a.provisioned is not None and a.deadline_ms is not None);result=observe(op,a.plan,a.artifact,a.chart,a.provisioned,a.directory,a.deadline_ms)
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
