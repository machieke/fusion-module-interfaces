"""Local embedding and sealed legacy enrichment only. No payload copy or retrieval fallback."""
import json
import os
from pathlib import Path
import sqlite3
import sys
import time
from fusion.contracts import canonical,digest,require
from .memory_oracle import HELPER,HELPER_HASH

_config=None


def clock():
    # Called by the unchanged query composition after vector retrieval. Fixed clock
    # is explicitly a test fixture; absent it, preserve the native wall-clock point.
    return _config.get('clock_fixture',time.time())


def initialize():
    global _config
    app=json.loads(Path(os.environ['NEOCLAW_S01_APPLICATION']).read_text())
    _config=json.loads(Path(app['memory_native_config']).read_text())
    cfg=_config
    from fusion import vector_contracts as c
    selected=json.loads(Path(app['memory_read_config']).read_text())
    require(cfg['metadata_seal']==selected['metadata_seal'],'CONFLICT')
    require((selected['embedding']==c.EMBEDDING and cfg['embedding_boundary'] in ('real','port')) or
            (selected['embedding']==c.FIXTURE and cfg['embedding_boundary']=='vector-fixture'),'UNSUPPORTED_PROFILE')
    if cfg['embedding_boundary']=='port':
        from .embedding_caller_build import validate_runtime
    else:
        from .memory_build import validate_runtime
    runtime_path=Path(cfg.get('runtime',Path(cfg['site']).parents[2].parent/'memory-runtime.json'))
    require(digest(runtime_path.read_bytes())==cfg.get('runtime_sha256',digest(runtime_path.read_bytes())),'CONFLICT')
    runtime=validate_runtime(runtime_path)
    require(Path(cfg['site'])==Path(runtime['sdk'])/'lib/python3.12/site-packages','UNSUPPORTED_PROFILE')
    helper_path=Path(cfg.get('helper',runtime['helper']))
    sys.path.insert(0,cfg['site'])
    sys.path.insert(0,str(helper_path.parent))
    require(digest(helper_path.read_bytes())==HELPER_HASH,'UNSUPPORTED_PROFILE')
    import lib_chromadb,helper,lib_llm_ext
    # The helper's cwd-relative collection is metadata-only and generated here.
    manifest=json.loads(Path(cfg['metadata_manifest']).read_text())
    require(digest(canonical(manifest))==cfg['metadata_seal'],'CONFLICT')
    rows=manifest['records'];collection=lib_chromadb.COLLECTION
    if collection.count()==0:
        for row in rows:
            collection.add(ids=[row['uuid']],embeddings=[[0.]],metadatas=[dict(linkedEpisodes=row['links'],strength=row['stv'][0],confidence=row['stv'][1])])
    got=collection.get(include=['metadatas','documents'])
    expected={r['uuid']:dict(linkedEpisodes=r['links'],strength=r['stv'][0],confidence=r['stv'][1]) for r in rows}
    require(dict(zip(got['ids'],got['metadatas']))==expected and all(x is None for x in got['documents']),'CONFLICT')
    class MetadataOnly:
        def get(self,*,ids,include):
            require(include==['metadatas'],'UNAUTHORIZED')
            require(all(x in expected for x in ids),'NOT_AVAILABLE')
            value=collection.get(ids=ids,include=include)
            require(dict(zip(value['ids'],value['metadatas']))=={x:expected[x] for x in ids},'CONFLICT')
            return value
        def __getattr__(self,name):raise RuntimeError('LEGACY_CANDIDATE_OR_PAYLOAD_ACCESS_FORBIDDEN')
    lib_chromadb.COLLECTION=MetadataOnly()
    def forbidden(*args,**kwargs):raise RuntimeError('LEGACY_RETRIEVAL_FORBIDDEN')
    for name in ('query','query_with_ids','query_with_ids_and_dists','query_by_ids','query_by_id','remember','forget_ids','set_stv','link_episode','unlink_episode'):
        setattr(lib_chromadb,name,forbidden)
    db=Path(cfg['promotions'])
    helper._PROMOTION_CONN=sqlite3.connect(f'file:{db}?mode=ro',uri=True)
    for row in rows:
        require(helper.promotion_get_value(row['uuid'])==row['promotion'] and helper.promotion_get_lasttime(row['uuid'])==manifest['promotion_time'],'CONFLICT')
    require(set(helper.promotion_get_all_keys())=={r['uuid'] for r in rows},'CONFLICT')
    if cfg['embedding_boundary']=='port':
        from fusion import embedding_contracts as e
        from fusion import append_contracts as w
        require(app['composition'] in (e.APPLICATION,w.APPLICATION),'UNSUPPORTED_PROFILE')
        import importlib.util
        absent={name:importlib.util.find_spec(name) is None and name not in sys.modules for name in ('torch','sentence_transformers','transformers')}
        require(all(absent.values()),'UNSUPPORTED_PROFILE')
        # PeTTa imports this bootstrap before its loop bridge. Use the same
        # top-level module identity that its subsequent Python import selects.
        sys.path.insert(0,str(Path(__file__).parent))
        import loop_bridge
        lib_llm_ext.initLocalEmbedding=forbidden
        lib_llm_ext.useLocalEmbedding=loop_bridge.encode_query
        probes={}
        for file in app.get('embedding_denied_files',[]):
            try:
                with open(file,'rb') as stream:stream.read(1)
            except OSError:probes[file]='inaccessible'
            else:require(False,'UNAUTHORIZED')
        try:lib_llm_ext.initLocalEmbedding()
        except RuntimeError:initializer_forbidden=True
        else:require(False,'UNAUTHORIZED')
        Path(app['workdir'],'embedding-boundary.json').write_bytes(canonical(dict(absent=absent,
            denied_file_probes=probes,local_initializer_forbidden=initializer_forbidden,
            source='original native embed/string-safe; query-time helper is the typed port',
            denied_paths_visible=[p for p in app.get('denied_paths',[]) if Path(p).exists() and any(Path(p).iterdir())])))
    elif cfg['embedding_boundary']=='real':
        from .memory_embedding import load
        lib_llm_ext.useLocalEmbedding=load(cfg['embedding_source'],cfg['model'],cfg['model_hashes'])
    else:
        require(cfg['embedding_boundary']=='vector-fixture','UNSUPPORTED_PROFILE')
        vectors=cfg['fixture_vectors']
        lib_llm_ext.useLocalEmbedding=lambda text:vectors[text]
