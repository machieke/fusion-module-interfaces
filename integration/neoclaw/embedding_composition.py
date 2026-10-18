"""Operator composition: encoder placement is independent of retrieval placement."""
import copy
import json
from pathlib import Path

from fusion import embedding_contracts as c, vector_contracts as v
from fusion.contracts import canonical, digest
from fusion.registry import descriptor_wire
from .memory_composition import configure as memory_configure, ROOT

CALLER_RUNTIME = ROOT/'artifacts/s03_1/caller/caller-runtime.json'
PROVIDER_RUNTIME = ROOT/'artifacts/s03/memory-runtime.json'


def configure(run, corpus, placement, *, caller_runtime=CALLER_RUNTIME, provider_runtime=PROVIDER_RUNTIME, helper_inputs=None):
    caller_runtime = Path(caller_runtime).resolve()
    provider_runtime = Path(provider_runtime).resolve()
    memory = memory_configure(run, corpus, 'real')
    h = run.h
    root = h.root/'encoder'; root.mkdir(mode=0o700)
    caller_canary=h.caller_root/'synthetic-private-canary.txt'
    caller_canary.write_text('S03_1_SYNTHETIC_CALLER_CANARY_DO_NOT_EXPORT')
    provider_canary=root/'synthetic-provider-canary.txt'
    provider_canary.write_text('S03_1_SYNTHETIC_PROVIDER_CANARY_DO_NOT_EXPORT')
    inputs = helper_inputs or {q:q for q in corpus['queries']}
    runtime = json.loads(Path(provider_runtime).read_text())
    cfg = dict(database=str(root/'encoder.db'), runtime=str(provider_runtime), runtime_sha256=digest(Path(provider_runtime).read_bytes()),
        native_source=str(ROOT/'artifacts/s01/native-02/sources/mettaclaw/lib_llm_ext.py'),
        scope='generated-s03', sharing=v.PRIVACY, model=v.EMBEDDING, preprocessing=c.PREPROCESSING,
        approved_helper_inputs=list(inputs.values()), catalogue=[descriptor_wire(c.descriptor())],
        denied_canary=str(caller_canary) if placement=='network' else None)
    for principal in ('A','B'):
        h.config['principals'][principal]['scopes'].setdefault(cfg['scope'], []).extend(['embedding.encode','embedding.disclose'])
    h.save()
    if placement == 'network':
        h.config['embedding'] = cfg
        h.config['memory_read']['denied_paths'] = [str(h.caller_root),str(Path.home()/'work/takopi/mettaclaw')]
        h.stop_server(); h.start_server()
        provider_config = h.config_path
    else:
        provider_config = root/'config.json'
        provider_config.write_bytes(canonical(dict(principals=h.config['principals'],embedding=cfg)))
        provider_config.chmod(0o600)
    client = dict(principal='A', scope=cfg['scope'], sharing=v.PRIVACY, profile=c.PROFILE, model=v.EMBEDDING,
        preprocessing=c.PREPROCESSING, inputs=inputs, catalogue=cfg['catalogue'], placement=placement,
        credential=h.client['credential'], fallback=False)
    if placement == 'network': client['endpoint'] = dict(host='127.0.0.1',port=h.port,ca_file=str(h.caller_root/'ca.pem'))
    else: client['provider_config'] = str(provider_config)
    path = h.caller_root/'embedding.json'; path.write_bytes(canonical(client)); path.chmod(0o600)
    native = json.loads(memory['native_config'].read_text())
    caller = json.loads(Path(caller_runtime).read_text())
    native.update(embedding_boundary='port', runtime=str(caller_runtime), runtime_sha256=digest(Path(caller_runtime).read_bytes()),
                  site=str(Path(caller['sdk'])/'lib/python3.12/site-packages'),helper=caller['helper'])
    for key in ('embedding_source','model','model_hashes'): native.pop(key, None)
    memory['native_config'].write_bytes(canonical(native))
    run.app.update(composition=c.APPLICATION, embedding_config=str(path))
    if placement == 'network':
        # Physical invisibility in addition to the caller SDK lacking all E5 libraries.
        blocked = [root,Path(runtime['sdk']),Path(runtime['model']), ROOT/'artifacts/s03/reproduction-01',
                   Path.home()/'.cache/huggingface',Path.home()/'.cache/uv']
        # Known alternative SDK/model locations from the fresh-target S03 recipe.
        run.app['denied_paths'] = list(dict.fromkeys(run.app.get('denied_paths', [])+[str(p) for p in blocked if p.exists()]))
        run.app['embedding_denied_files'] = [str(provider_canary),str(Path(runtime['model'])/'model.safetensors'),
            str(Path(runtime['model'])/'tokenizer.json'),str(Path(runtime['sdk'])/'lib/python3.12/site-packages/torch/__init__.py')]
    run.save()
    return dict(memory=memory, encoder_config=provider_config, encoder_database=cfg['database'], client=path,
                provider_runtime=provider_runtime, caller_runtime=caller_runtime, placement=placement)
