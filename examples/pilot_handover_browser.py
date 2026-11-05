"""Offline post-handover browser recipe using the installed operator package.

Run this distributed file with the installed operator Python -I. It adds only
separately scoped browser keys and configuration; it never contacts Kubernetes
or changes an owner journal. Outputs contain secrets and stay private. Applying
them is a separate configuration-driven owner rollout, not a fencing action.
"""
import argparse,base64,copy,hashlib,json,os
from pathlib import Path
import yaml
from fusion.contracts import require,canonical
from integration.single_node.pilot_browser_provision import provision


def prepare(values_path,secrets_directory,source_namespace,replacement,output):
    values_path=Path(values_path);secret_root=Path(secrets_directory);out=Path(output)
    require(not out.exists() and values_path.is_file() and values_path.stat().st_size<=1048576,'CONFLICT')
    require(source_namespace!=replacement and all(type(x) is str and x.startswith('omega-ref-pilot-') and
        len(x)<=63 for x in (source_namespace,replacement)),'UNAUTHORIZED')
    values=yaml.safe_load(values_path.read_bytes());original=copy.deepcopy(values);preview=values['preview']
    require(preview['model_boundary']=='RECORDED_FIXTURE' and 'browser' not in preview['pilot'] and 'pilotWorkbench' not in values,'CONFLICT')
    fence=preview['pilot']['writer_fence'];handover=preview['pilot']['handover']
    require(fence['profile']==handover['profile']=='planned-synthetic-writer-handover/1' and
        fence['deployment']==replacement and fence['generation']==handover['generation'] and fence['generation']>=2,'UNAUTHORIZED')
    users={'handover-operator':dict(role='operator',scopes=[preview['scope']],credential_key='browser-handover-operator-token')}
    agents={role:dict(principal=x['principal'],scopes=[preview['scope'],x['private_scope']]) for role,x in preview['agents'].items()}
    prepared=provision(replacement,users,agents,cleanup=True);cfg=prepared['gateway_configuration']
    cfg['handover']=dict(profile='planned-synthetic-writer-handover/1',authority_file='/writer-authority/current.json',deployments=[source_namespace,replacement])
    preview['pilot']['browser']=dict(profile='synthetic-browser-sessions/1',users=users)
    values['pilotWorkbench']=dict(enabled=True,configuration=cfg,existingTrustSecret='omega-agent-tls-auth',existingAuthoritySecret='pilot-current-writer',
        credentials={role:dict(existingSecret=role+'-tls-auth',keys=keys) for role,keys in prepared['required_secret_keys'].items()})
    files={};changes=[]
    for role,keys in prepared['owner_credentials'].items():
        path=secret_root/(role+'.secret.json');require(path.is_file() and not path.is_symlink() and path.stat().st_size<=1048576,'UNAUTHORIZED')
        old=json.loads(path.read_bytes());value=copy.deepcopy(old)
        require(value['metadata']['namespace']==replacement and value['metadata']['name']==role+'-tls-auth','UNAUTHORIZED')
        for key,raw in keys.items():
            require(key not in value['data'],'CONFLICT');value['data'][key]=base64.b64encode(raw.encode()).decode()
        require(all(value['data'][k]==v for k,v in old['data'].items()),'CONFLICT')
        files[role+'.secret.json']=canonical(value)
        changes.append(dict(role=role,added_keys=sorted(keys),old_values_preserved=True,old_material_sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    for user,token in prepared['bootstrap'].items():files[user+'.bootstrap']=(token+'\n').encode()
    files['gateway-values.yaml']=yaml.safe_dump(values,sort_keys=False).encode()
    revert=copy.deepcopy(values);del revert['preview']['pilot']['browser'];del revert['pilotWorkbench'];require(revert==original,'CONFLICT')
    report=dict(profile='post-handover-scoped-browser-provisioning/1',namespace=replacement,source_namespace=source_namespace,changes=changes,
        values_sha256=hashlib.sha256(files['gateway-values.yaml']).hexdigest(),only_value_additions=['preview.pilot.browser','pilotWorkbench'],
        application='SEPARATE_CONFIGURATION_ROLLOUT_REQUIRED',authority_observation='NOT_A_FENCING_PROOF',publication='PRIVATE_OUTPUT_WITHHOLD_SECRET_AND_CHECKPOINT_IDENTITIES',
        cluster_calls=0,live_generations=0)
    files['provision-report.json']=canonical(report)
    previous=os.umask(0o077)
    try:
        out.mkdir(mode=0o700,parents=True,exist_ok=False)
        for name,raw in files.items():
            with (out/name).open('xb') as stream:stream.write(raw)
    finally:os.umask(previous)
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('values','secrets','source-namespace','replacement','output'):parser.add_argument('--'+name,required=True)
    args=parser.parse_args();prepare(args.values,args.secrets,args.source_namespace,args.replacement,args.output)
    print('Prepared new scoped browser credentials only; no cluster calls.')


if __name__=='__main__':main()
