"""Generate fresh bounded developer selections from verified image artifacts.

This writes non-secret Helm values only. It does not contact any runtime,
reserve model calls, start deadlines, or reuse populated journals.
"""
import argparse,json,time,uuid,re
from pathlib import Path
from fusion.contracts import require
from fusion.preview_deployment_contracts import COMPOSITION


def generate(manifest,scope,*,mode='combined',inputs=24,sessions=2,expires_ms=None,chain=False):
    require(type(scope) is str and re.fullmatch(r'synthetic-[a-z0-9][a-z0-9-]{0,53}',scope) is not None,'UNAUTHORIZED')
    require(mode in ('minimal','memory','combined'))
    require(type(inputs) is int and 1<=inputs<=32 and type(sessions) is int and 1<=sessions<=2)
    require(2*inputs*sessions<=128,'OVERLOADED')
    require(type(manifest) is dict and manifest.get('source_export_verification')=='PASS','CONFLICT')
    require(type(manifest.get('source_manifest_sha256')) is str and re.fullmatch(r'[0-9a-f]{64}',manifest['source_manifest_sha256']) is not None,'CONFLICT')
    require(type(manifest.get('images')) is list and 3<=len(manifest['images'])<=6,'CONFLICT')
    kinds=set()
    for item in manifest['images']:
        require(type(item) is dict and {'kind','repository','local_tag','manifest_digest'}<=item.keys(),'CONFLICT')
        require(item['kind'] in ('base','caller','embedding','generative','chain','hive') and item['kind'] not in kinds,'CONFLICT')
        kinds.add(item['kind'])
        require(all(type(item[k]) is str for k in ('repository','local_tag','manifest_digest')),'CONFLICT')
        require(re.fullmatch(r'[a-z0-9][a-z0-9./_-]{0,200}',item['repository']) is not None,'CONFLICT')
        require(item['local_tag'].startswith(item['repository']+':') and re.fullmatch(r'[A-Za-z0-9_.-]{1,128}',item['local_tag'][len(item['repository'])+1:]) is not None,'CONFLICT')
        require(re.fullmatch(r'sha256:[0-9a-f]{64}',item['manifest_digest']) is not None,'CONFLICT')
    if expires_ms is None:expires_ms=time.time_ns()//1_000_000+86400000
    require(type(expires_ms) is int and expires_ms>time.time_ns()//1_000_000,'UNAUTHORIZED')
    images={x['kind']:dict(repository=x['repository'],tag=x['local_tag'].rsplit(':',1)[1],
        digest=x['manifest_digest'],pullPolicy='Never') for x in manifest['images']}
    require({'base','caller','embedding'}<=images.keys(),'NOT_AVAILABLE')
    tools=['pin','unpin','task-context','episodes','read-file','write-file','append-file','metta']
    components={'fusion-model':{'enabled':True},'fusion-episodes':{'enabled':True}}
    facets=['episodic.memory','execution.workspace']
    p=dict(enabled=True,profile=COMPOSITION,scope=scope,model_boundary='RECORDED_FIXTURE',
        policy_revision='preview-'+str(uuid.uuid4()),authority_expires_ms=expires_ms,
        limits=dict(inputs=inputs,pending=4,timeout_ms=120000),assignments=['synthetic-task'],agents={},responses={})
    if mode!='minimal':
        tools+=['remember','query','link','unlink','update','forget','delegate'];facets+=['relations']
        components.update({'fusion-relations':{'enabled':True},'fusion-search':dict(enabled=True,image=images['caller']),
            'fusion-embedding':dict(enabled=True,image=images['embedding'])})
        p.update(memory=dict(enabled=True,corpus='generated-'+scope.removeprefix('synthetic-')),tasks=dict(enabled=True))
    if mode=='combined':
        tools+=['support','contradict','promote','demote','inspect-atom']
        components.update({'fusion-beliefs':{'enabled':True},'fusion-attention':{'enabled':True}})
        p['cognition']=dict(enabled=True,attention_provider='sqlite')
        p['inspection']=dict(enabled=True)
    require(type(chain) is bool)
    if chain:
        require(mode=='combined' and 'chain' in images,'NOT_AVAILABLE')
        p['chain']=dict(enabled=True,nodeEnabled=False,isolationVerified=False,public_key='04'+'0'*128,wallet_address='',registration=None)
        for role in ('fusion-commitment','f1r3node'):components[role]=dict(enabled=True,image=images['chain'])
    for role,principal in [('omega-agent','A'),('omega-agent-b','B')]:
        ids=[str(uuid.uuid4()) for _ in range(sessions)]
        p['agents'][role]=dict(principal=principal,private_scope=scope+'-private-'+principal.lower(),
            sessions=ids,tools=list(tools),facets=list(facets))
        for sid in ids:
            for slot in range(1,inputs+1):p['responses'][sid+'/'+str(slot)]={'proposal':'input-command'}
        components[role]=dict(image=images['caller'])
        if role=='omega-agent-b':components[role].update(existingSecret=role+'-tls-auth',
            persistence=dict(storageClass='local-path',size='256Mi'),
            resources=dict(requests=dict(cpu='100m',memory='128Mi'),limits=dict(cpu='1',memory='512Mi')),
            config=dict(revision='initial',capacity=8,nativeEnabled=True,workerEnabled=False,test={}))
    return dict(image=images['base'],components=components,networkPolicy=dict(enabled=True),preview=p)


def main():
    import yaml
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--images',required=True)
    parser.add_argument('--scope',required=True);parser.add_argument('--output',required=True)
    parser.add_argument('--mode',choices=['minimal','memory','combined'],default='combined')
    parser.add_argument('--chain',action='store_true',help='Package isolated chain roles disabled until fresh keys and isolation are registered')
    a=parser.parse_args();destination=Path(a.output);require(not destination.exists(),'CONFLICT')
    values=generate(json.loads(Path(a.images).read_text()),a.scope,mode=a.mode,chain=a.chain)
    destination.parent.mkdir(parents=True,exist_ok=True);destination.write_text(yaml.safe_dump(values,sort_keys=False))

if __name__=='__main__':main()
