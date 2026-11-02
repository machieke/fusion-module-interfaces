"""Select existing memory owners for fresh multi-session synthetic scopes."""
import json
from pathlib import Path
from fusion import append_contracts as w, embedding_contracts as e, vector_contracts as v
from fusion.contracts import canonical,digest,require
from fusion.registry import descriptor_wire
from fusion.preview_memory_services import COMPOSITION,descriptor,OPS
from fusion.preview_text import PROFILE as TEXT
from .configure import write


def memory_settings(settings,session):
    p=settings['preview']
    return dict(scope=p['scope'],session=session,corpus=p['memory']['corpus'],model=v.EMBEDDING,
        invocation_timeout_ms=30000,inputs={},queries=[],query_vector_hashes=[],responses=[])


def policy(settings):
    p=settings['preview']
    return dict(profile=TEXT,scope=p['scope'],principals=[a['principal'] for a in p['agents'].values()],
        purposes=['remember','query'],max_utf8_bytes=1024,revision=p['policy_revision'])


def client(settings,principal,name,secret,endpoint,credential):
    role='fusion-storage' if name=='memory.lifecycle' else 'fusion-search'
    return dict(composition=COMPOSITION,placement='network',fallback=False,principal=principal,scope=settings['preview']['scope'],
        credential=credential,endpoint=endpoint(role),descriptors={name:descriptor_wire(descriptor(name))})


def provider(settings,cfg,state,run,secret,token,endpoint):
    role=settings['role'];p=settings['preview'];principals=[a['principal'] for a in p['agents'].values()]
    from .memory_configure import configure
    shadow={**settings,'service_composition':'neoclaw-memory-services/1',
        'memory':memory_settings(settings,next(iter(p['agents'].values()))['sessions'][0])}
    _,memory,_,_=configure(shadow,state,run,secret,token,endpoint)
    for name in ('memory_read','memory_append','embedding'):
        if name in memory:memory[name]['text_policy']=policy(settings)
    if role in ('fusion-storage','fusion-search'):
        memory['memory_append']['writers']=principals
        memory['memory_read']['readers']=[*principals,'indexer']
        for who in principals:
            grant=memory['principals'].get(who,memory['principals']['A'])
            memory['principals'][who]={**grant,'credential':token('caller-'+who+'-token')}
        name='memory.lifecycle' if role=='fusion-storage' else 'search'
        memory['active_memory']=dict(profile=COMPOSITION,scope=p['scope'],corpus=p['memory']['corpus'],root=str(state/'memory'),
            descriptors={name:descriptor_wire(descriptor(name))})
        permissions=[name+'.'+op for op in OPS[name]]
        if name=='memory.lifecycle':permissions+=['memory.lifecycle.lifecycle.'+op for op in ('read','project','introduce','supersede','withdraw','history')]
        for who in principals:memory['principals'][who]['scopes'][p['scope']]+=permissions
        if role=='fusion-storage':
            memory['source_delegation']=dict(profile='preview-receipt-delegation/1',principals=principals,scope=p['scope'])
            memory['read_source_principals']=principals
            memory['principals']['indexer']['scopes'][p['scope']]+=['memory.lifecycle.head','memory.lifecycle.activeSet','memory.lifecycle.disclose',
                'memory.lifecycle.lifecycle.read','memory.lifecycle.lifecycle.project','memory.lifecycle.lifecycle.history']
        else:
            memory['active_memory']['lifecycle_client']=client(settings,'indexer','memory.lifecycle',secret,endpoint,token('storage-source-token'))
    else:
        for who in principals:
            memory['principals'][who]=dict(credential=token('caller-'+who+'-token'),scopes={p['scope']:[
                'embedding.encode','embedding.disclose','embedding.memory.encode','embedding.memory.disclose']})
    # A storage process still serves S01 with its historical exact scope. This
    # merges scopes within its own owner; no second process opens its journals.
    prior=cfg.get('principals',{})
    for who,value in prior.items():
        if who in memory['principals']:
            require(value['credential']==memory['principals'][who]['credential'],'CONFLICT')
            memory['principals'][who]['scopes']={**value['scopes'],**memory['principals'][who]['scopes']}
        else:memory['principals'][who]=value
    if role=='fusion-storage':
        memory['service_composition']=cfg['service_composition']
        for name in ('memory_read','memory_append'):
            memory[name]['backend_layout']='detta-opaque-coordinate-partitions/1'
    cfg.update(memory)


def agent(settings,app,current,own,principal,session,secret,token,endpoint):
    from .memory_configure import configure
    shadow={**settings,'role':'omega-agent','service_composition':'neoclaw-memory-services/1',
        'memory':memory_settings(settings,session)}
    # The inherited helper fills the already selected caller/application paths.
    write(current/'application.json',app)
    model_client=json.loads((current/'model.json').read_text())
    configure(shadow,own,current,secret,token,endpoint)
    write(current/'model.json',model_client)
    memory_app=json.loads((current/'application.json').read_text())
    app.update({k:v0 for k,v0 in memory_app.items() if k not in ('composition','model_fixture','turn_limit','preparation_diagnostics')})
    app['preview']['base']=w.APPLICATION
    app['embedding_denied_files']=['/opt/model/model.safetensors','/opt/sdk/lib/python3.12/site-packages/torch/__init__.py']
    for file in ('embedding.json','memory-embedding.json','memory-append.json','memory-read-template.json'):
        value=json.loads((current/file).read_text());value.update(principal=principal,text_policy=policy(settings));write(current/file,value)
    # Scope and session ports remain independent of selected encoder/retrieval.
    selected={}
    for name in OPS:
        file=current/(name+'-active.json')
        write(file,client(settings,principal,name,secret,endpoint,token('fusion-'+('storage' if name=='memory.lifecycle' else 'search')+'-token')))
        selected[name]=str(file)
    app['active_memory_configs']=selected
    return app


def prepare(settings,state,run):
    """Initial empty view only. Later views are selected by accepted app work."""
    from .memory_host import prepare_agent
    app_path=run/'application.json';app=json.loads(app_path.read_text())
    if (run/'memory-read.json').exists():return
    shadow={**settings,'memory':memory_settings(settings,app['session_id'])}
    prepare_agent(shadow,state,run)
    native=json.loads((run/'memory-native.json').read_text())
    native.pop('clock_fixture',None);native.pop('creation_clock_fixture',None)
    write(run/'memory-native.json',native)
