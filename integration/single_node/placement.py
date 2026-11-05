"""Executable plans for the existing Helm composition, not an orchestrator.

The only executable deployment recipe is the existing chart. Plans contain
non-secret values, selected artifacts and an exact rendered graph. Compilation
validates and returns these same chart objects. No occurrence or deadline is
created; installation and provider admission remain explicit operator actions.
"""
import argparse,copy,difflib,json,re,subprocess,tempfile
from pathlib import Path
from fusion.contracts import canonical,digest,require

PROFILE='omega-single-node-placement/1'
COMP='omega-single-node-sustained-preview/1'


def files_hash(chart):
    chart=Path(chart)
    require(chart.is_dir() and not chart.is_symlink(),'INVALID_ARGUMENT')
    result={}
    for path in sorted(chart.rglob('*')):
        require(not path.is_symlink(),'UNAUTHORIZED')
        if path.is_file():result[str(path.relative_to(chart))]=digest(path.read_bytes())
    require(1<=len(result)<=64,'OVERLOADED');return digest(canonical(result))


def render(chart,namespace,values):
    import yaml
    require(type(namespace) is str and re.fullmatch(r'omega-ref-[a-z0-9-]{1,48}',namespace),'UNAUTHORIZED')
    with tempfile.TemporaryDirectory(prefix='fusion-placement-') as directory:
        path=Path(directory)/'values.json';path.write_bytes(canonical(values))
        result=subprocess.run(['helm','template','omega',str(chart),'--namespace',namespace,'-f',str(path)],capture_output=True,text=True,timeout=20)
    require(result.returncode==0,'INVALID_ARGUMENT')
    objects=[x for x in yaml.safe_load_all(result.stdout) if x is not None]
    require(1<=len(objects)<=128,'OVERLOADED');return objects


def graph(objects,namespace,images):
    """Check actual rendered owner mounts/services/config, not an aspirational graph."""
    types={'ConfigMap','StatefulSet','Deployment','Service','NetworkPolicy'}
    require(all(o['kind'] in types for o in objects),'UNSUPPORTED_PROFILE')
    by={(o['kind'],o['metadata']['name']):o for o in objects}
    require(len(by)==len(objects),'CONFLICT')
    pins={row['repository']+'@'+row['manifest_digest']:row['kind'] for row in images['images']}
    nodes={};edges=[]
    for (kind,name),obj in by.items():
        if kind!='StatefulSet':continue
        s=obj['spec'];pod=s['template']['spec'];require(s['replicas']==1 and s['updateStrategy']['type']=='RollingUpdate','UNSUPPORTED_PROFILE')
        require(len(pod['containers'])==1 and not pod.get('initContainers'),'UNSUPPORTED_PROFILE')
        require(pod.get('automountServiceAccountToken') is False and not any(pod.get(k) for k in ('hostNetwork','hostPID','hostIPC')),'UNAUTHORIZED')
        c=pod['containers'][0];require(c['image'] in pins and pins[c['image']]!='generative','UNAUTHORIZED')
        if name.startswith('omega-agent'):require(pins[c['image']]=='caller','UNAUTHORIZED')
        require(c['securityContext'].get('readOnlyRootFilesystem') is True,'UNAUTHORIZED')
        require(set(c['resources'])=={'requests','limits'} and all(set(c['resources'][k])=={'cpu','memory'} for k in c['resources']),'INVALID_ARGUMENT')
        claims=s['volumeClaimTemplates'];require(len(claims)==1 and claims[0]['metadata']['name']=='state','UNAUTHORIZED')
        require(claims[0]['spec']['accessModes']==['ReadWriteOnce'],'UNAUTHORIZED')
        require(s.get('persistentVolumeClaimRetentionPolicy',{})=={'whenDeleted':'Retain','whenScaled':'Retain'},'UNSUPPORTED_PROFILE')
        require(all(set(v)<=({'name','configMap'} if 'configMap' in v else {'name','secret'} if 'secret' in v else {'name','emptyDir'}) for v in pod['volumes']),'UNAUTHORIZED')
        mounts={v['name']:v for v in c['volumeMounts']};require(mounts.get('state',{}).get('mountPath')=='/state' and not mounts['state'].get('readOnly',False),'UNAUTHORIZED')
        require(all(m['mountPath']!='/opt/native' and not any(x in m for x in ('mountPropagation','subPathExpr')) for m in mounts.values()),'UNAUTHORIZED')
        # No pre-existing PVC can be addressed, so ownership cycles/foreign
        # journals cannot be expressed by this selected composition.
        require(not any('persistentVolumeClaim' in v or 'hostPath' in v for v in pod['volumes']),'UNAUTHORIZED')
        svc=by.get(('Service',name));require(svc is not None and svc['spec'].get('type','ClusterIP')=='ClusterIP','UNAUTHORIZED')
        config_name=next(v['configMap']['name'] for v in pod['volumes'] if 'configMap' in v)
        cfg=json.loads(by[('ConfigMap',config_name)]['data']['component.json'])
        require(cfg['role']==name and cfg['service_composition']==COMP and cfg['preview']['model_boundary']=='RECORDED_FIXTURE','UNSUPPORTED_PROFILE')
        require(cfg['state']=='/state' and cfg['run']=='/run/fusion' and cfg['secret_directory']=='/secrets','UNAUTHORIZED')
        require(cfg['preview']['sustained'].get('model_binding',{}).get('kind','recorded')=='recorded','UNAUTHORIZED')
        if 'fusion-model'==name:require('generative' not in pins[c['image']],'UNAUTHORIZED')
        secrets=[v['secret']['secretName'] for v in pod['volumes'] if 'secret' in v]
        nodes[name]=dict(placement='pod-https',image=c['image'],host=name+'.'+namespace+'.svc.cluster.local',port=cfg['https_port'],
            owner_pvc='state-'+name+'-0',secret_refs=sorted(secrets),scope=cfg['preview']['scope'],resources=c['resources'],
            config_sha256=digest(canonical(cfg)),readiness='NOT_OBSERVED',authority='EXISTING_CURRENT_SCOPED_POLICY')
    for (kind,name),obj in by.items():
        if kind!='Deployment':continue
        # Exactly the stateless private browser gateway. It owns no journal and
        # cannot express another PVC, privileged proxy or arbitrary workload.
        require(name=='omega-workbench','UNSUPPORTED_PROFILE')
        s=obj['spec'];pod=s['template']['spec'];require(s['replicas']==1 and s['strategy']=={'type':'Recreate'},'UNSUPPORTED_PROFILE')
        require(len(pod['containers'])==1 and not pod.get('initContainers'),'UNSUPPORTED_PROFILE')
        require(pod.get('automountServiceAccountToken') is False and not any(pod.get(k) for k in ('hostNetwork','hostPID','hostIPC')),'UNAUTHORIZED')
        c=pod['containers'][0];require(pins.get(c['image'])=='caller','UNAUTHORIZED')
        require(c['command']==['/opt/native/python/bin/python3.12','-m','integration.single_node.pilot_browser_cli'] and
            c['args']==['--configuration','/config/browser.json','--port','8878','--listen','0.0.0.0'],'UNSUPPORTED_PROFILE')
        require(c['securityContext']==dict(allowPrivilegeEscalation=False,readOnlyRootFilesystem=True,capabilities=dict(drop=['ALL'])),'UNAUTHORIZED')
        require(set(c['resources'])=={'requests','limits'} and all(set(c['resources'][k])=={'cpu','memory'} for k in c['resources']),'INVALID_ARGUMENT')
        require(all(set(v)<=({'name','configMap'} if 'configMap' in v else {'name','secret'}) for v in pod['volumes']),'UNAUTHORIZED')
        require(all(m.get('readOnly') is True and not any(k in m for k in ('mountPropagation','subPath','subPathExpr')) for m in c['volumeMounts']),'UNAUTHORIZED')
        for v in pod['volumes']:
            if 'secret' not in v:continue
            keys={i['key'] for i in v['secret']['items']}
            require(keys and all(k in ('ca.crt','current.json') or k.startswith('browser-') for k in keys),'UNAUTHORIZED')
            if 'current.json' in keys:require(v['name']=='writer-authority' and keys=={'current.json'},'UNAUTHORIZED')
        svc=by.get(('Service',name));require(svc is not None and svc['spec'].get('type','ClusterIP')=='ClusterIP','UNAUTHORIZED')
        cfg=json.loads(by[('ConfigMap',name)]['data']['browser.json'])
        require(cfg['namespace']==namespace and cfg['profile']=='synthetic-browser-sessions/1','UNSUPPORTED_PROFILE')
        nodes[name]=dict(placement='private-browser-port-forward',image=c['image'],host=name+'.'+namespace+'.svc.cluster.local',port=8878,
            owner_pvc=None,secret_refs=sorted(v['secret']['secretName'] for v in pod['volumes'] if 'secret' in v),
            scope='PER_USER_EXPLICIT_SYNTHETIC_SCOPES',resources=c['resources'],config_sha256=digest(canonical(cfg)),
            readiness='NOT_OBSERVED',authority='EXISTING_CURRENT_SCOPED_POLICY',workload_kind='Deployment')
    require({'omega-agent','fusion-storage','fusion-execution','fusion-messaging','fusion-model'}<=nodes.keys(),'NOT_AVAILABLE')
    for (kind,_),o in by.items():
        if kind!='NetworkPolicy':continue
        source=o['spec']['podSelector'].get('matchLabels',{}).get('app.kubernetes.io/name')
        if source not in nodes:continue
        for rule in o['spec'].get('egress',[]):
            for dest in rule.get('to',[]):
                target=dest.get('podSelector',{}).get('matchLabels',{}).get('app.kubernetes.io/name')
                if target:
                    # Declared but disabled optional services are not active edges.
                    if target not in nodes:continue
                    if source=='fusion-commitment' and target=='f1r3node':
                        # Existing isolated native chain API, not a module
                        # HTTPS port. The separately approved harness enables
                        # the node only after its isolation checks pass.
                        require(rule['ports']==[{'protocol':'TCP','port':40403}],'UNSUPPORTED_PROFILE')
                        transport='isolated-native-http'
                    else:
                        require(rule['ports']==[{'protocol':'TCP','port':nodes[target]['port']}],'UNSUPPORTED_PROFILE')
                        transport='authenticated-https'
                    edges.append(dict(caller=source,provider=target,transport=transport,owner_files=False))
    owners=[n['owner_pvc'] for n in nodes.values() if n['owner_pvc'] is not None]
    require(len(set(owners))==len(owners),'UNAUTHORIZED')
    return dict(nodes=nodes,edges=sorted(edges,key=lambda r:(r['caller'],r['provider'])),ownership_cycles=False,
                communication_cycles='ALLOWED_CALLBACKS_NOT_OWNERSHIP',fallback=False)


def freeze(chart,namespace,values,images):
    require(images.get('source_export_verification')=='PASS','CONFLICT')
    require(type(values) is dict and values.get('preview',{}).get('profile')==COMP,'UNSUPPORTED_PROFILE')
    p=values['preview'];require(p['model_boundary']=='RECORDED_FIXTURE' and p['scope'].startswith('synthetic-'),'UNAUTHORIZED')
    require(not values.get('futureLive') and not p.get('chain',{}).get('nodeEnabled'),'UNAUTHORIZED')
    objects=render(chart,namespace,values);topology=graph(objects,namespace,images)
    registry=p['sustained'].get('provider_registry')
    if registry:
        active={**registry['pins'],**registry.get('rollover',{}).get('pins',{})}
        for role,pin in active.items():
            if role not in topology['nodes']:continue  # no selected port, no admission
            require(pin['image']==topology['nodes'][role]['image'].split('@sha256:')[1], 'CONFLICT')
            # A mixed compatible rollout may retain images from an earlier
            # verified artifact set. The selected image list carries its exact
            # source identity; absent per-image source uses the common manifest.
            item=next(x for x in images['images'] if x['repository']+'@'+x['manifest_digest']==topology['nodes'][role]['image'])
            require(pin['source']==item.get('source_manifest_sha256',images['source_manifest_sha256']),'CONFLICT')
    result=dict(profile=PROFILE,namespace=namespace,scope=p['scope'],chart_sha256=files_hash(chart),source_manifest_sha256=images['source_manifest_sha256'],
        values=values,images=images,graph=topology,objects_sha256=digest(canonical(objects)),additional_live_generations=0)
    require(len(canonical(result))<=1048576,'OVERLOADED');return result


def compile(plan,chart):
    require(type(plan) is dict and set(plan)=={'profile','namespace','scope','chart_sha256','source_manifest_sha256','values','images','graph','objects_sha256','additional_live_generations'},'INVALID_ARGUMENT')
    require(plan['profile']==PROFILE and plan['additional_live_generations']==0,'UNSUPPORTED_PROFILE')
    require(files_hash(chart)==plan['chart_sha256'],'CONFLICT')
    expected=freeze(chart,plan['namespace'],plan['values'],plan['images']);require(expected==plan,'CONFLICT')
    return dict(values=copy.deepcopy(plan['values']),objects=render(chart,plan['namespace'],plan['values']),
        plan_sha256=digest(canonical(plan)),business_admission=False,readiness='NOT_CHECKED',
        policy='Only separately admitted trusted records can select new sessions; accepted templates remain frozen')


def diagram(plan):
    lines=['flowchart LR']
    for role,node in sorted(plan['graph']['nodes'].items()):
        safe=role.replace('-','_');lines.append(f'  {safe}["{role}: HTTPS"]')
        if node['owner_pvc'] is not None:lines.append(f'  {safe} --> {safe}_state[("{node["owner_pvc"]}")]')
    for edge in plan['graph']['edges']:lines.append('  '+edge['caller'].replace('-','_')+' --> '+edge['provider'].replace('-','_'))
    return '\n'.join(lines)+'\n'


def provider_source(op,role,image,plan,reference_providers=None,pod_name=None):
    """Two explicit attestations: packaged Python source or verified Go OCI.

    The independent scratch provider intentionally has no Python/exec inspector.
    Its separately verified immutable image archive binds the exact compiled kit
    binary. The caller also checks the live pod's imageID against that same pin.
    """
    expected=image.get('source_manifest_sha256',plan['source_manifest_sha256'])
    if image['kind']=='inspect-go':
        from .pilot_provider_image import verify
        selected=reference_providers or {};require(set(selected)=={'inspect-go'},'NOT_AVAILABLE')
        checked=verify(selected['inspect-go'])
        from fusion.registry import selection_token
        from fusion.reference_inspect_contracts import descriptor
        require(checked['contract']==selection_token(descriptor()),'UNSUPPORTED_PROFILE')
        require(role=='fusion-inspect-go' and checked['repository']==image['repository'] and
            checked['manifest']==image['manifest_digest'] and checked['source_manifest_sha256']==expected,'CONFLICT')
        return expected,'VERIFIED_INDEPENDENT_GO_OCI_AND_POD_IMAGE_ID'
    from .reference_ops import PYTHON
    probe="import json;from pathlib import Path;from fusion.contracts import canonical,digest;print(digest(canonical(json.loads(Path('/opt/fusion-package.json').read_bytes())['source'])))"
    source=op.k('exec',pod_name or role+'-0','--',PYTHON,'-c',probe,timeout=15).strip()
    require(source==expected,'CONFLICT');return source,'PACKAGED_SOURCE_AND_POD_IMAGE_ID'


def verify_installed(plan,op,reference_providers=None):
    """Metadata, certificate and exact-image checks; never sends business work."""
    require(op.namespace==plan['namespace'],'UNAUTHORIZED');op.owned();result=[]
    import base64
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes
    import datetime
    now=datetime.datetime.now(datetime.timezone.utc)
    actual={r['metadata']['name']:r for r in op.workloads()}
    if 'omega-workbench' in plan['graph']['nodes']:
        actual.update({r['metadata']['name']:r for r in op.stateless_workloads()})
    require(set(actual)==set(plan['graph']['nodes']),'CONFLICT')
    for role,node in plan['graph']['nodes'].items():
        sts=actual[role];c=sts['spec']['template']['spec']['containers'][0];require(c['image']==node['image'],'CONFLICT')
        if node.get('workload_kind')=='Deployment':
            pods=json.loads(op.k('get','pods','-l','app.kubernetes.io/name='+role,'-o','json'))['items']
            require(len(pods)==1 and not pods[0]['metadata'].get('deletionTimestamp'),'NOT_AVAILABLE');pod=pods[0]
        else:pod=json.loads(op.k('get','pod',role+'-0','-o','json'))
        statuses=pod['status'].get('containerStatuses',[])
        require(len(statuses)==1 and statuses[0]['ready'] and statuses[0]['imageID'].endswith(node['image'].split('@')[1]),'NOT_AVAILABLE')
        config_name=next(v['configMap']['name'] for v in sts['spec']['template']['spec']['volumes'] if 'configMap' in v)
        key='browser.json' if node.get('workload_kind')=='Deployment' else 'component.json'
        cfg=json.loads(json.loads(op.k('get','configmap',config_name,'-o','json'))['data'][key])
        require(digest(canonical(cfg))==node['config_sha256'],'CONFLICT')
        image=next(x for x in plan['images']['images'] if x['repository']+'@'+x['manifest_digest']==node['image'])
        source,source_verification=provider_source(op,role,image,plan,reference_providers,pod['metadata']['name'])
        if node.get('workload_kind')=='Deployment':
            result.append(dict(role=role,pod_uid=pod['metadata']['uid'],image_id=statuses[0]['imageID'],source_manifest_sha256=source,
                transport='PRIVATE_LOOPBACK_PORT_FORWARD_NO_PUBLIC_INGRESS',configuration='EXACT',source_verification=source_verification))
            continue
        ca_hashes=[]
        for secret in node['secret_refs']:
            data=json.loads(op.k('get','secret',secret,'-o','json'))['data']
            if not {'tls.crt','ca.crt'}<=set(data):continue
            cert=x509.load_pem_x509_certificate(base64.b64decode(data['tls.crt']));ca=x509.load_pem_x509_certificate(base64.b64decode(data['ca.crt']))
            require(node['host'] in cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value.get_values_for_type(x509.DNSName),'UNAUTHORIZED')
            require(cert.not_valid_before_utc<=now<cert.not_valid_after_utc and ca.not_valid_before_utc<=now<ca.not_valid_after_utc,'UNAUTHORIZED')
            cert.verify_directly_issued_by(ca);ca_hashes.append(digest(base64.b64decode(data['ca.crt'])))
        require(len(ca_hashes)==1,'NOT_AVAILABLE')
        result.append(dict(role=role,pod_uid=pod['metadata']['uid'],image_id=statuses[0]['imageID'],source_manifest_sha256=source,ca_sha256=ca_hashes[0],certificate_dns='MATCHED',configuration='EXACT',source_verification=source_verification))
    return dict(status='PASS',providers=result,plan_sha256=digest(canonical(plan)),business_calls=0,readiness='POD_READY_ONLY',additional_live_generations=0)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['freeze','compile','diff','verify-installed','freeze-local','compile-local'])
    for name in ('chart','plan','values','images','namespace','output','previous','kubeconfig','context','application','provider','reference-provider'):p.add_argument('--'+name)
    a=p.parse_args()
    if a.action=='freeze-local':
        require(a.application is not None and a.provider is not None)
        result=freeze_local(a.application,a.provider)
    elif a.action=='compile-local':
        require(a.plan is not None);result=compile_local(json.loads(Path(a.plan).read_bytes()))
    elif a.action=='freeze':
        import yaml
        require(all((a.chart,a.values,a.images,a.namespace,a.output)))
        result=freeze(a.chart,a.namespace,yaml.safe_load(Path(a.values).read_text()),json.loads(Path(a.images).read_bytes()))
    else:
        require(a.plan is not None);plan=json.loads(Path(a.plan).read_bytes())
        if a.action=='compile':result=compile(plan,a.chart)
        elif a.action=='diff':
            previous=json.loads(Path(a.previous).read_bytes())
            print(''.join(difflib.unified_diff(json.dumps(previous,sort_keys=True,indent=2).splitlines(True),json.dumps(plan,sort_keys=True,indent=2).splitlines(True),fromfile=a.previous,tofile=a.plan)));return
        else:
            from .reference_ops import Operator
            result=verify_installed(plan,Operator(a.kubeconfig,a.context,a.namespace),
                {'inspect-go':a.reference_provider} if a.reference_provider else None)
    if a.output:
        path=Path(a.output);require(not path.exists(),'CONFLICT');path.write_bytes(canonical(result))
        if a.action=='freeze':path.with_suffix('.mmd').write_text(diagram(result))
    else:print(json.dumps(result,indent=2))

# The historical controlled native composition is the other supported recipe.
# It compiles to the existing launcher and operator command, never a scheduler.
LOCAL_PROFILE='omega-controlled-native-placement/1'


def freeze_local(application,provider):
    """Validate the existing named NAL local-library/loopback-HTTPS recipe.

    File references name separately managed operator configuration. Only their
    digests and non-secret selections enter the plan; credentials and mutable
    occurrence records do not. This is not the default/live Omega startup.
    """
    from fusion import neoclaw_contracts as c
    from fusion.registry import descriptor_read,selection_token
    from fusion.adapters.neoclaw_nal import NativeTruthDeduction
    app_path,provider_path=Path(application).absolute(),Path(provider).absolute()
    def read(path):
        require(path.is_file() and not path.is_symlink() and path.stat().st_size<=262144,'NOT_AVAILABLE')
        return json.loads(path.read_bytes())
    app=read(app_path);owner=read(provider_path)
    require(app.get('composition')=='controlled-native-loop/1' and 'model_fixture' in app and 'model_config' not in app,'UNSUPPORTED_PROFILE')
    require(type(app['turn_limit']) is int and 1<=app['turn_limit']<=32 and type(app['invocation_timeout_ms']) is int and 1<=app['invocation_timeout_ms']<=120000)
    require(owner['profile']==c.PROFILE and owner['sharing']=='generated-shareable' and owner['atom_provider']=='detta','UNSUPPORTED_PROFILE')
    runtime=NativeTruthDeduction(app['runtime']) # hashes only, no process/evaluation
    require(Path(owner['runtime']).resolve()==runtime.runtime_file,'CONFLICT')
    caller_path=Path(app['caller_config']);caller=read(caller_path)
    require(not {'request_id','deadline_ms'}&set(caller),'INVALID_ARGUMENT')
    require(caller['scope']==c.SCOPE and caller['sharing']=='generated-shareable' and caller['fallback'] is False,'UNAUTHORIZED')
    require(caller['placement'] in ('local','network'),'UNSUPPORTED_PROFILE')
    chosen=c.selected([descriptor_read(d) for d in caller['catalogue']])
    require(type(caller['max_attempts']) is int and 1<=caller['max_attempts']<=3 and type(caller['max_calls']) is int and 1<=caller['max_calls']<=64)
    principal=caller['principal'];selected=owner['principals'].get(principal)
    require(selected is not None and selected['credential']==caller['credential'] and c.SCOPE in selected['scopes'],'UNAUTHORIZED')
    require(owner['routes'][caller['reply_route']]==dict(scope=c.SCOPE,owner=principal),'UNAUTHORIZED')
    caller_root=Path(caller['database']).absolute().parent;provider_root=Path(owner['database']).absolute().parent
    require(caller_root!=provider_root and caller_root not in provider_root.parents and provider_root not in caller_root.parents,'UNAUTHORIZED')
    owner_files=[owner[k] for k in ('database','atoms_database','messages_database','da_root','atom_records')]
    require(len(set(owner_files))==len(owner_files) and all(Path(p).absolute().is_relative_to(provider_root) for p in owner_files),'UNAUTHORIZED')
    files={'application':app_path,'caller':caller_path,'provider':provider_path,'runtime':runtime.runtime_file,
           'model_fixture':Path(app['model_fixture']),'detta':Path(owner['detta_binary'])}
    endpoint=None
    if caller['placement']=='local':require(Path(caller['provider_config']).resolve()==provider_path.resolve(),'CONFLICT')
    else:
        require('provider_config' not in caller,'UNAUTHORIZED');ep=caller['endpoint']
        require(set(ep)=={'host','port','ca_file'} and ep['host']=='127.0.0.1' and type(ep['port']) is int and 1<=ep['port']<=65535,'UNAUTHORIZED')
        files['ca']=Path(ep['ca_file']);files['certificate']=Path(owner['tls_certificate'])
        require(files['ca'].read_bytes()==files['certificate'].read_bytes(),'UNAUTHORIZED')
        endpoint=dict(host=ep['host'],port=ep['port'],ca_sha256=digest(files['ca'].read_bytes()))
    refs={name:dict(path=str(path.absolute()),sha256=digest(path.read_bytes()),kind='existing-operator-file') for name,path in files.items()}
    return dict(profile=LOCAL_PROFILE,recipe='integration.neoclaw.native_loop',scope=c.SCOPE,
        placement='local-library' if caller['placement']=='local' else 'same-host-authenticated-https',
        selections={k:selection_token(v) for k,v in chosen.items()},numerical_profile=c.PROFILE,
        files=refs,endpoint=endpoint,owner_roots=dict(caller=str(caller_root),provider=str(provider_root)),
        model='RECORDED_FIXTURE',channels='CONTROLLED_FIXTURE',native='PINNED_REAL',storage='REAL_DETTA',
        business_calls=0,deadline_started=False,additional_live_generations=0,fallback=False,
        readiness='NOT_OBSERVED',authority='EXISTING_SCOPED_CALLER_AND_PROVIDER_POLICY')


def compile_local(plan):
    require(type(plan) is dict and plan.get('profile')==LOCAL_PROFILE,'UNSUPPORTED_PROFILE')
    for ref in plan['files'].values():
        require(type(ref) is dict and set(ref)=={'path','sha256','kind'} and ref['kind']=='existing-operator-file')
        file=Path(ref['path']);require(file.is_file() and not file.is_symlink() and digest(file.read_bytes())==ref['sha256'],'CONFLICT')
    expected=freeze_local(plan['files']['application']['path'],plan['files']['provider']['path'])
    require(plan==expected,'CONFLICT')
    return dict(profile=LOCAL_PROFILE,plan_sha256=digest(canonical(plan)),
        native_argv=['-m','integration.neoclaw.native_loop',plan['files']['application']['path']],
        worker_argv=['-m','integration.neoclaw.operator',plan['files']['provider']['path'],'--seconds','120'],
        https_argv=None if plan['placement']=='local-library' else ['-m','integration.neoclaw.host','serve',plan['files']['provider']['path'],'--port',str(plan['endpoint']['port'])],
        effects_started=False,generative_runtime_activity='FORBIDDEN')


if __name__=='__main__':main()
