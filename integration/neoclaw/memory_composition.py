"""Disposable generated S03 composition on the existing controlled application."""
import importlib.util
import json
from pathlib import Path
import os
from fusion import vector_contracts as c
from fusion.contracts import canonical,digest
from fusion.registry import descriptor_wire
from fusion.vector_composition import descriptors,ReadService
from fusion.vector_enrollment import enroll
from .memory_corpus import generated,QUERY
from .memory_oracle import HELPER

ROOT=Path(__file__).resolve().parents[2]
SDK=Path(os.environ.get('S03_SDK',ROOT/'artifacts/s03/venv'))
MODEL=Path(os.environ.get('S03_MODEL',ROOT/'artifacts/s03/model'))


def configure(run,corpus=None,embedding='vector-fixture'):
    h=run.h;corpus=generated() if corpus is None else corpus
    runtime_path=Path(os.environ.get('S03_RUNTIME',SDK.parent/'memory-runtime.json'))
    runtime=json.loads(runtime_path.read_text())
    profile=c.EMBEDDING if embedding=='real' else c.FIXTURE
    scope='generated-s03';corpus_id=corpus.get('corpus_id','synthetic-memory-2030')
    config=dict(root=str(h.server_root/'memory'),scope=scope,corpus=corpus_id,embedding=profile,sharing=c.PRIVACY,
        readers=['A','worker'],queries=list(corpus['queries']),query_vectors=[digest(c.vector_bytes(v)) for v in corpus['queries'].values()],
        runtime=str(runtime_path),runtime_sha256=digest(runtime_path.read_bytes()),
        catalogue=[descriptor_wire(d) for d in descriptors(profile)],detta_binary=h.config['detta_binary'])
    if h.client['placement']=='network':
        config['denied_paths']=[str(h.caller_root),str(Path.home()/'work/takopi/mettaclaw')]
    h.config['memory_read']=config
    for principal in ('A','worker'):
        h.config['principals'][principal]['scopes'][scope]=['atom.storage.'+o for o in ('create','get','getMany','availability','head','readCommits')]+['search.query','search.build']
    h.save()
    service=ReadService(h.config_path,h.config['principals']['worker']['credential'])
    for i,row in enumerate(corpus['records']):
        value=dict(scope=scope,corpus=corpus_id,uuid=row['uuid'],time=row['time'],content=row['content'])
        enroll(service.atoms,scope,corpus_id,profile,'generated-'+str(i),value,row['vector'])
    head=service.atoms.head(scope);snapshot=service.search().build(scope,head)
    manifest=dict(records=[{k:r[k] for k in ('uuid','links','stv','promotion')} for r in corpus['records']],promotion_time=corpus['clock']-86400)
    seal=digest(canonical(manifest));metadata=h.caller_root/'metadata.json';metadata.write_bytes(canonical(manifest))
    # The local legacy SQLite owner is generated independently, then reopened read-only.
    source=ROOT/'artifacts/s01/native-02/sources/mettaclaw/src/helper.py'
    spec=importlib.util.spec_from_file_location('generated_promotion_helper',source);helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    promotions=h.caller_root/'promotions.db';helper.promotion_open_map(str(promotions))
    for row in manifest['records']:
        helper.promotion_set_value(row['uuid'],row['promotion']);helper.promotion_set_lasttime(row['uuid'],manifest['promotion_time'])
    helper.promotion_commit();helper.promotion_close_map()
    read_cfg=dict(principal=h.client['principal'],profile=c.PROFILE,sharing=c.PRIVACY,scope=scope,embedding=profile,snapshot=snapshot,
        queries=list(corpus['queries']),catalogue=config['catalogue'],metadata_seal=seal,
        native_config=dict(recall=2,similarity=4,inflation=4),fallback=False,
        placement=h.client['placement'],credential=h.client['credential'])
    if read_cfg['placement']=='network':read_cfg['endpoint']=h.client['endpoint']
    else:read_cfg['provider_config']=str(h.config_path)
    path=h.caller_root/'memory-read.json';path.write_bytes(canonical(read_cfg));path.chmod(0o600)
    native=dict(site=str(SDK/'lib/python3.12/site-packages'),metadata_manifest=str(metadata),metadata_seal=seal,
        runtime=str(runtime_path),runtime_sha256=digest(runtime_path.read_bytes()),helper=runtime['helper'],
        promotions=str(promotions),clock_fixture=corpus['clock'],embedding_boundary=embedding,
        embedding_source=str(source.parent.parent/'lib_llm_ext.py'))
    if embedding=='real':
        native.update(model=str(MODEL),model_hashes=json.loads((ROOT/'integration/neoclaw/memory-model.json').read_text())['files'])
    else:native['fixture_vectors']={q:c.vector(v) for q,v in corpus['queries'].items()}
    native_path=h.caller_root/'memory-native.json';native_path.write_bytes(canonical(native))
    run.app.update(composition=c.APPLICATION,memory_read_config=str(path),memory_native_config=str(native_path))
    run.save()
    if h.client['placement']=='network':
        h.stop_server();h.start_server()
    return dict(source=head,snapshot=snapshot,metadata_seal=seal,read_config=path,native_config=native_path)
