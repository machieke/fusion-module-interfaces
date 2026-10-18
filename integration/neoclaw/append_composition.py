"""Fresh generated append session; approvals do not enroll future memories."""
import json
from pathlib import Path
import uuid
from fusion import append_contracts as c, embedding_contracts as e
from fusion.contracts import canonical,digest
from fusion.registry import descriptor_wire,selection_token
from fusion.adapters.neoclaw_metadata import collection
from .embedding_composition import configure as read_configure
from .append_oracle import TEXT


def configure(run,corpus,encoder='network',*,inputs=None,caller_runtime=None,provider_runtime=None):
    options={}
    if caller_runtime is not None:options['caller_runtime']=caller_runtime
    if provider_runtime is not None:options['provider_runtime']=provider_runtime
    value=read_configure(run,corpus,encoder,**options)
    h=run.h;inputs=inputs or {TEXT:TEXT};session=str(uuid.uuid4())
    memory_profile=e.descriptor(c.MEMORY_EMBEDDING)
    encoder_path=Path(value['encoder_config'])
    provider=json.loads(encoder_path.read_text())
    provider['embedding'].update(memory_helper_inputs=list(inputs.values()),
        catalogue=provider['embedding']['catalogue']+[descriptor_wire(memory_profile)])
    for principal in ('A','B'):
        provider['principals'][principal]['scopes']['generated-s03']+=['embedding.memory.encode','embedding.memory.disclose']
    encoder_path.write_bytes(canonical(provider))
    if encoder=='network':h.config=provider
    query_client=json.loads(Path(value['client']).read_text())
    memory_encoder={**query_client,'profile':c.MEMORY_EMBEDDING,'inputs':inputs,'catalogue':[descriptor_wire(memory_profile)]}
    memory_encoder_path=h.caller_root/'memory-embedding.json';memory_encoder_path.write_bytes(canonical(memory_encoder));memory_encoder_path.chmod(0o600)
    read=json.loads(value['memory']['read_config'].read_text());root=h.caller_root/'metadata-views'
    from fusion.vector_composition import descriptors as read_descriptors
    read.update(require_ready=True,catalogue=[descriptor_wire(d) for d in read_descriptors(read['embedding'],True)])
    value['memory']['read_config'].write_bytes(canonical(read))
    h.config['memory_read'].update(require_ready=True,catalogue=read['catalogue'])
    native=json.loads(value['memory']['native_config'].read_text())
    manifest=json.loads(Path(native['metadata_manifest']).read_text())
    collection(root,manifest,prepare=True,deadline=__import__('time').time_ns()//1_000_000+30000)
    config=dict(profile=c.PROFILE,sharing=c.v.PRIVACY,scope=read['scope'],corpus=read['snapshot']['corpus'],
        model=read['embedding'],session=session,session_principal='A',writers=['A'],inputs=inputs,catalogue=[descriptor_wire(d) for d in c.descriptors()],
        root=h.config['memory_read']['root'],detta_binary=h.config['detta_binary'],embedding_selection=selection_token(memory_profile))
    h.config['memory_append']=config
    methods=['memory.append.write','memory.append.disclose','atom.storage.observe','search.published','search.ready']
    for principal in ('A','B'):
        h.config['principals'][principal]['scopes'].setdefault(read['scope'],[]).extend(methods)
    h.save()
    client={k:config[k] for k in ('profile','sharing','scope','corpus','model','session','inputs','catalogue')}
    client.update(principal='A',fallback=False,placement=read['placement'],credential=read['credential'],metadata_root=str(root))
    if read['placement']=='network':client['endpoint']=read['endpoint']
    else:client['provider_config']=str(h.config_path)
    path=h.caller_root/'memory-append.json';path.write_bytes(canonical(client));path.chmod(0o600)
    native['creation_clock_fixture']=corpus.get('creation_clock_fixture')
    value['memory']['native_config'].write_bytes(canonical(native))
    run.app.update(composition=c.APPLICATION,memory_append_config=str(path),memory_embedding_config=str(memory_encoder_path),session_id=session)
    run.save()
    if encoder=='network' or read['placement']=='network':h.stop_server();h.start_server()
    value.update(append_client=path,metadata_root=root,session=session)
    return value
