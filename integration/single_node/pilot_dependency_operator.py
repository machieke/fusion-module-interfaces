"""Private installed read-only closure tool over existing AtomStorage/Search ports.

Extract uses exact quiesced exports. Verify runs inside a trusted operator caller
with separately selected current per-scope clients. It reads neither provider
journals nor private credentials from the backup. Unsupported/missing clients
refuse closure; observed results never authorize cleanup or writer activation.
"""
import argparse,json,uuid
from pathlib import Path
from fusion.contracts import canonical,digest,require
from .pilot_backup import read,private_write,owner_manifest,MAX_MANIFEST,MAX_TOTAL
from .pilot_dependencies import verify_closure,MAX_BYTES


def extract(full):
    root=Path(full);raw=read(root/'manifest.json',MAX_MANIFEST)
    require(digest(raw)==read(root/'manifest.sha256',65).decode().strip(),'CONFLICT')
    cut=json.loads(raw);require(cut['authority_excluded'] is True and cut['original_remains_quiesced'] is True,'UNAUTHORIZED')
    result={}
    for role,item in cut['owners'].items():
        require(item['file']==role+'.tar.gz','CONFLICT');blob=read(root/item['file'],MAX_TOTAL)
        require(digest(blob)==item['sha256'] and len(blob)==item['bytes'],'CONFLICT')
        result[role]=owner_manifest(blob,role)['dependency_inventory']
    require(len(canonical(result))<=MAX_BYTES,'OVERLOADED');return result


def verify(inventories,ports):
    require(type(ports) is dict and set(ports)=={'profile','scopes'} and ports['profile']=='owner-dependency-read-clients/1','UNSUPPORTED_PROFILE')
    require(type(ports['scopes']) is dict and 1<=len(ports['scopes'])<=3,'OVERLOADED')
    from fusion.preview_atoms import client
    from fusion.preview_memory_services import Client
    class Atoms:
        def get(self,ref):
            scope=ref['scope_ref'];require(scope in ports['scopes'],'UNAUTHORIZED')
            path=ports['scopes'][scope]['atom_client'];cfg=json.loads(read(path,131072))
            require(cfg['scope']==scope and cfg['endpoint']['path']=='/reference-cognition','UNAUTHORIZED')
            return client(cfg).get(ref)
    class Search:
        def ready(self,scope,snapshot):
            require(scope in ports['scopes'],'UNAUTHORIZED')
            selected=ports['scopes'][scope]
            from fusion import vector_contracts as vector,preview_vector_contracts as active
            if snapshot['profile']==active.PROFILE:
                require('search_client' in selected,'NOT_AVAILABLE')
                cfg=json.loads(read(selected['search_client'],131072));require(cfg['scope']==scope,'UNAUTHORIZED')
                return Client(cfg,'search',inline=True).call('ready',snapshot)
            require(snapshot['profile']==vector.PROFILE and 'vector_client' in selected,'UNSUPPORTED_PROFILE')
            from fusion.vector_composition import select
            from fusion.vector_transport import binding
            from fusion.registry import descriptor_read,selection_token
            cfg=json.loads(read(selected['vector_client'],131072));require(cfg['scope']==scope,'UNAUTHORIZED')
            chosen=select([descriptor_read(x) for x in cfg['catalogue']],vector.EMBEDDING,True,cfg.get('feed_profile',vector.a.FEED));d=chosen['search']
            request=dict(request_id=str(uuid.uuid4()),interface_ref=dict(id='search',version=d.version),operation='ready',scope=scope,profile=vector.PROFILE,selection=selection_token(d),body=dict(snapshot=snapshot))
            value=binding(cfg,chosen).invoke(request);require(value=={'ready':True},'NOT_AVAILABLE');return value
    for scope,selected in ports['scopes'].items():
        require(scope.startswith('synthetic-') and type(selected) is dict and {'atom_client'}<=set(selected)<={'atom_client','search_client','vector_client'},'UNAUTHORIZED')
    def authorize(role,operation):
        # The process is launched by the existing installed Operator. Remote
        # current owner permissions are checked on every typed get/ready. Scope
        # allowlisting is an additional refusal boundary, not remote authority.
        require(role in inventories and operation=='dependencies.verify','UNAUTHORIZED')
        for item in inventories[role]['dependencies'].values():
            ref=item['reference'];scope=ref.get('scope_ref',ref.get('head',{}).get('scope_ref'))
            require(scope in ports['scopes'],'UNAUTHORIZED')
    return {role:verify_closure(value,Atoms(),Search(),authorize) for role,value in inventories.items()}


def partition(inventories,scope):
    """Trusted operator selects only authorized opaque refs for one caller."""
    result={}
    for role,value in inventories.items():
        require(digest(canonical({k:v for k,v in value.items() if k!='head'}))==value['head'],'CONFLICT')
        dependencies={k:v for k,v in value['dependencies'].items() if v['reference'].get('scope_ref',v['reference'].get('head',{}).get('scope_ref'))==scope}
        if dependencies:
            selected=dict(profile=value['profile'],owner=role,dependencies=dependencies,original_head=value['head'],scope=scope)
            selected['head']=digest(canonical(selected));result[role]=selected
    return result


def merge(inventories,scoped):
    result={}
    for role,value in inventories.items():
        observations={};partitions={}
        for scope,proofs in scoped.items():
            fragments=partition(inventories,scope)
            if role not in fragments:continue
            require(role in proofs,'NOT_AVAILABLE');proof=proofs[role]
            require(proof['selected_head']==fragments[role]['head'] and proof['status']=='VERIFIED_REFERENCES' and proof['closure_sha256']==digest(canonical([proof['selected_head'],proof['observations']])),'CONFLICT')
            for key,item in proof['observations'].items():
                require(key not in observations or observations[key]==item,'CONFLICT');observations[key]=item
            partitions[scope]=proof['closure_sha256']
        require(set(value['dependencies'])<=set(observations),'NOT_AVAILABLE')
        result[role]=dict(profile=value['profile'],owner=role,selected_head=value['head'],status='VERIFIED_REFERENCES',observations=observations,
            semantic_unknowns_retained=True,admission_reserved=False,closure_sha256=digest(canonical([value['head'],observations])),partition_proofs=partitions)
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=('extract','verify'));p.add_argument('--full');p.add_argument('--inventory');p.add_argument('--ports');p.add_argument('--output',required=True)
    a=p.parse_args()
    if a.action=='extract':value=extract(a.full)
    else:value=verify(json.loads(read(a.inventory,MAX_BYTES)),json.loads(read(a.ports,131072)))
    raw=canonical(value);private_write(a.output,raw)
    print(json.dumps(dict(action=a.action,output_sha256=digest(raw),owners=sorted(value),additional_live_generations=0)))


if __name__=='__main__':main()
