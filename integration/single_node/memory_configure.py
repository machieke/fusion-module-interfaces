"""Fresh S03.2 service composition; no operator insertion of target records."""
import json
from pathlib import Path
import uuid

from fusion import append_contracts as w, embedding_contracts as e, vector_contracts as v, neoclaw_search_contracts as s
from fusion.contracts import canonical,digest,require
from fusion.memory_services import COMPOSITION
from fusion.registry import descriptor_wire,selection_token
from fusion.vector_composition import descriptors
from .configure import write

ROLES=('omega-agent','fusion-storage','fusion-search','fusion-embedding')


def configure(settings,state,run,secret,token,endpoint):
    role=settings['role'];m=settings['memory'];scope=m['scope'];session=m['session'];corpus=m['corpus']
    require(role in ROLES and settings['service_composition']==COMPOSITION,'UNSUPPORTED_PROFILE')
    require(m['model']==v.EMBEDDING and m['invocation_timeout_ms']==30000,'UNSUPPORTED_PROFILE')
    inputs=m['inputs'];queries=m['queries'];a_catalogue=[descriptor_wire(d) for d in w.descriptors()]
    read_catalogue=[descriptor_wire(d) for d in descriptors(v.EMBEDDING,True)]
    e_catalogue=[descriptor_wire(e.descriptor(p)) for p in (e.PROFILE,e.MEMORY_PROFILE)]
    root=str(state/'memory')
    append=dict(profile=w.PROFILE,sharing=v.PRIVACY,scope=scope,corpus=corpus,model=v.EMBEDDING,session=session,
        session_principal='A',writers=['A'],inputs=inputs,catalogue=a_catalogue,root=root,
        embedding_selection=selection_token(e.descriptor(e.MEMORY_PROFILE)))
    read=dict(root=root,scope=scope,corpus=corpus,embedding=v.EMBEDDING,sharing=v.PRIVACY,readers=['A','indexer'],
        queries=queries,query_vectors=m['query_vector_hashes'],catalogue=read_catalogue,require_ready=True)
    methods=['atom.storage.'+op for op in ('create','get','getMany','observe','head','readCommits')]+['search.'+op for op in ('query','build','published','ready')]+['memory.append.write','memory.append.disclose']
    def principal(credential,operations):return dict(credential=token(credential),scopes={scope:operations})
    cfg=dict(service_composition=COMPOSITION,tls_certificate=str(secret/'tls.crt'),tls_key=str(secret/'tls.key'))
    test=settings.get('test',{});require(not test or settings.get('enable_test_faults') is True,'UNAUTHORIZED')
    cfg.update(test_failpoints=bool(test),failpoint_marker=str(state/'pause.json'))
    if test.get('pause_at') and not (state/'pause.json').exists():cfg['pause_at']=test['pause_at']
    if role=='fusion-embedding':
        runtime=Path('/opt/memory-runtime.json')
        cfg.update(principals={'A':principal('caller-token',['embedding.encode','embedding.disclose','embedding.memory.encode','embedding.memory.disclose'])},
            embedding=dict(database=str(state/'encoder.sqlite'),runtime=str(runtime),runtime_sha256=digest(runtime.read_bytes()),
                native_source='/opt/native/sources/mettaclaw/lib_llm_ext.py',scope=scope,sharing=v.PRIVACY,
                model=v.EMBEDDING,preprocessing=e.PREPROCESSING,approved_helper_inputs=queries,
                memory_helper_inputs=list(inputs.values()),catalogue=e_catalogue))
    elif role in ('fusion-storage','fusion-search'):
        cfg.update(memory_append=append,memory_read=read,principals={'A':principal('caller-token',methods),
            'indexer':principal('indexer-token',['atom.storage.get','atom.storage.getMany','atom.storage.head','atom.storage.readCommits','memory.source.observe','search.build','search.ready'])})
        if role=='fusion-storage':
            for section in (append,read):section['detta_binary']='/opt/native/fusion-detta-adapter'
            cfg['source_delegation']=dict(principal='A',session=session,scope=scope)
        else:cfg['source']=dict(endpoint=endpoint('fusion-storage'),credential=token('storage-source-token'))
    else:
        # S01/S02 descriptors remain selected for the inherited native lifecycle;
        # this script admits only remember/query and never invokes those owners.
        caller=json.loads((run/'caller.json').read_text());caller.update(composition='neoclaw-tools/2',search_max_attempts=1);caller['search_catalogue']=[descriptor_wire(d) for d in s.catalogue('detta')]
        write(run/'caller.json',caller)
        def client(names):
            return dict(principal='A',sharing=v.PRIVACY,scope=scope,fallback=False,placement='service-network',
                service_composition=COMPOSITION,endpoints={n:endpoint('fusion-'+('storage' if n=='atom.storage' else n)) for n in names},
                service_credentials={n:token('fusion-'+('storage' if n=='atom.storage' else n)+'-token') for n in names})
        encoder=dict(**client(('embedding',)),profile=e.PROFILE,model=v.EMBEDDING,preprocessing=e.PREPROCESSING,
                     inputs={q:q for q in queries},catalogue=[e_catalogue[0]])
        write(run/'embedding.json',encoder)
        write(run/'memory-embedding.json',{**encoder,'profile':e.MEMORY_PROFILE,'inputs':inputs,'catalogue':[e_catalogue[1]]})
        write(run/'memory-append.json',dict(**client(('atom.storage','search')),profile=w.PROFILE,corpus=corpus,session=session,
            model=v.EMBEDDING,inputs=inputs,catalogue=a_catalogue,metadata_root=str(state/'metadata-views')))
        # Snapshot is obtained from Search via an authenticated observation before
        # the application is opened. It is sealed once on this caller's PVC.
        write(run/'memory-read-template.json',dict(**client(('atom.storage','search')),profile=v.PROFILE,
            embedding=v.EMBEDDING,queries=queries,catalogue=read_catalogue,require_ready=True,
            native_config=dict(recall=2,similarity=4,inflation=4)))
        app=json.loads((run/'application.json').read_text());app.update(composition=w.APPLICATION,
            preparation_diagnostics=True,session_id=session,turn_limit=len(m['responses']),invocation_timeout_ms=m['invocation_timeout_ms'],
            embedding_config=str(run/'embedding.json'),memory_embedding_config=str(run/'memory-embedding.json'),
            memory_append_config=str(run/'memory-append.json'),memory_read_config=str(run/'memory-read.json'),
            memory_native_config=str(run/'memory-native.json'),embedding_denied_files=['/secrets/tls.key','/opt/model/model.safetensors',
                '/opt/sdk/lib/python3.12/site-packages/torch/__init__.py'])
        write(run/'application.json',app)
        write(run/'model.json',dict(responses=m['responses'],expected_feedback=m.get('expected_feedback',{}),log=str(state/'model-contexts.jsonl')))
    write(run/'owner.json',cfg)
    return settings,cfg,state,run
