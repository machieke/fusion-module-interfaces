"""Fresh native remember setup and persistent, disabled two-session composition."""
import copy
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import uuid
from fusion import model_contracts as m, neoclaw_retrieval_disclosure as r
from fusion.contracts import canonical, digest
from fusion.registry import descriptor_wire
from . import retrieval_campaign as c
from .channel_composition import ChannelRun, write
from .retrieval_preparation import generated, setup, QUERY, QUESTION, FOLLOWUP, BODIES
from .model_startup import retrieval_scaffold


def port():
    with socket.socket() as s: s.bind(('127.0.0.1',0)); return s.getsockname()[1]


def certificate(root):
    subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(root/'server.key'),
        '-out',str(root/'server.pem'),'-days','365','-subj','/CN=127.0.0.1','-addext','subjectAltName=IP:127.0.0.1'],check=True,capture_output=True)
    (root/'server.key').chmod(0o600)


def channel_handle(ch):
    return dict(root=str(ch.root), placement=ch.placement, denied=ch.denied, port=ch.port,
                irc_port=ch.irc_port, base=ch.base, clients={k:str(v) for k,v in ch.clients.items()})


def attach_channel(value):
    # Reopen exactly the frozen composition, never create credentials/identities.
    ch = ChannelRun.__new__(ChannelRun)
    ch.root=Path(value['root']); ch.temp=None;ch.processes=[];ch.logs=[]
    ch.placement=value['placement'];ch.denied=value['denied'];ch.port=value['port'];ch.irc_port=value['irc_port'];ch.base=value['base']
    for key, name in dict(provider='mailbox',bridge_root='bridge',server_root='irc',peer_root='peer',caller='caller').items(): setattr(ch,key,ch.root/name)
    ch.config_path=ch.provider/'config.json';ch.config=c.read(ch.config_path)
    ch.clients={k:Path(v) for k,v in value['clients'].items()}
    ch.bridge_config_path=ch.bridge_root/'config.json';ch.peer_config_path=ch.peer_root/'config.json'
    ch.bridge_config=c.read(ch.bridge_config_path);ch.host=ch.server=ch.peer=ch.bridge=None
    return ch


def compose(root, manifest, run, cfg, placement, recorded, responses):
    session=str(uuid.uuid4()); d=root/placement;d.mkdir(mode=0o700)
    caller=d/'caller';caller.mkdir(mode=0o700)
    completion=d/'completion';completion.mkdir(mode=0o700)
    authority=d/'authority';authority.mkdir(mode=0o700)
    receipt=d/'receipts';receipt.mkdir(mode=0o700)
    evaluator=root/'evaluator'
    app=copy.deepcopy(run.app); app.pop('model_fixture',None)
    call=copy.deepcopy(run.h.client); call['database']=str(caller/'application.sqlite')
    write(caller/'client.json',call)
    app.update(caller_config=str(caller/'client.json'),session_id=session,workdir=str(caller/'native'),status_file=str(caller/'status.json'),
               turn_limit=2,composition=r.APPLICATION,preparation_diagnostics=True,writable_paths=[str(root)],test_failpoints=recorded,
               failpoint_marker=str(caller/'pause.json'))
    for name in ('memory_append_config','memory_read_config','memory_native_config'):
        data=c.read(app[name]); dest=caller/Path(app[name]).name
        if name=='memory_append_config':data['session']=session
        if name=='memory_read_config':data.update(snapshot=cfg['view']['snapshot'],metadata_seal=cfg['view']['metadata_seal'])
        if name=='memory_native_config':
            data['metadata_seal']=cfg['view']['metadata_seal'];data['metadata_manifest']=str(caller/'metadata.json')
            write(data['metadata_manifest'],cfg['view']['metadata'])
        write(dest,data);app[name]=str(dest)
    ch=ChannelRun('network',True,root=d/'channel',session=session,inputs=[QUESTION,FOLLOWUP],outputs=BODIES,
                  denied=[str(caller),str(run.h.caller_root),str(run.h.server_root)],defer=True)
    ch.irc_port=port();ch.config['writable_paths']=[str(ch.provider)];write(ch.config_path,ch.config)
    ch.bridge_config=dict(client=str(ch.clients['bridge']),database=str(ch.bridge_root/'bridge.sqlite'),server=dict(host='127.0.0.1',port=ch.irc_port),
        nick='omega',seconds=750,test_failpoints=recorded,failpoint_marker=str(ch.bridge_root/'pause.json'),writable_paths=[str(ch.bridge_root)],
        denied_paths=ch.denied+[str(ch.caller),str(ch.peer_root),str(ch.server_root)])
    write(ch.bridge_config_path,ch.bridge_config)
    write(caller/'channel.json',c.read(ch.clients['application']))
    app.update(channel_config=str(caller/'channel.json'),channel_wait_ms=10000,channel_poll_limit=128,channel_irc_probe_port=ch.irc_port)
    app['denied_paths'] += [str(p) for p in (ch.provider,ch.peer_root,ch.bridge_root,ch.server_root,evaluator)]
    view=cfg['view'];metadata={x['uuid']:x for x in view['metadata']['records']}
    records=[dict(uuid=x['uuid'],time=x['time'],content=x['content'],metadata=metadata[x['uuid']],default=r.PRIOR) for x in cfg['payloads'].values()]
    recipient='retrieval-campaign-'+placement+'-model';consent=dict(recipient=recipient,records=records)
    policy_path=authority/'policy.json'
    disclosure=dict(policy=r.POLICY,scaffold=retrieval_scaffold(),memories=['()'],users=[str(['HUMAN-MSG:','peer: '+x]) for x in (QUESTION,FOLLOWUP)],
        query=QUERY,receipt_root=str(receipt),recipient=recipient,consent_sha256=digest(canonical(consent)),view_sha256=digest(canonical(view)),authority_policy=str(policy_path))
    denied=[str(x) for x in (caller,run.h.root,evaluator,ch.provider,ch.caller,ch.bridge_root,ch.peer_root,root/'setup-evidence.json') if x.is_dir()]
    if recorded:
        fixture=dict(boundary='AUTHORED_MODEL_RESPONSE_FIXTURE',parent_namespace=os.environ['FUSION_PREP_PARENT_NET'],root=str(completion),python=sys.executable,
            responses=responses[placement] if isinstance(responses,dict) else responses,denied_paths=denied,denied_files=[str(manifest),str(root/'corpus.json'),str(root/'setup-evidence.json')])
        write(completion/'fixture.json',fixture);lock=dict(path=str(completion/'fixture.json'),sha256=c.sha(completion/'fixture.json'))
    else:
        from .model_composition import runtime_lock
        lock=runtime_lock(completion,port=48173,asset_root='/usr/share/ollama/.ollama/models')
    owner=dict(database=str(completion/'model.sqlite'),scope='synthetic-retrieval-preparation',sharing=m.PRIVACY,sessions=[session],max_calls=2,
        expires_ms=1,catalogue=[descriptor_wire(m.descriptor(m.CPU_PROFILE))],runtime_lock=lock,disclosure=disclosure)
    credential=secrets.token_hex(24)
    policy=dict(model_completion=owner,principals={'A':dict(credential=credential,scopes={owner['scope']:['model.'+x for x in ('complete','observe','authorize','disclose')]})},
        test_failpoints=recorded,failpoint_marker=str(completion/'pause.json'))
    client={k:owner[k] for k in ('scope','sharing','catalogue','disclosure')}
    client.update(profile=m.CPU_PROFILE,principal='A',session=session,placement=placement,fallback=False,commands=[['query',QUERY]]+[['send',b] for b in BODIES],credential=credential)
    if not recorded:client['backend_port']=48173
    model_port=None
    if placement=='local':client['provider_config']=str(policy_path)
    else:
        certificate(completion);model_port=port();policy.update(tls_certificate=str(completion/'server.pem'),tls_key=str(completion/'server.key'))
        (caller/'model-ca.pem').write_bytes((completion/'server.pem').read_bytes())
        client['endpoint']=dict(host='127.0.0.1',port=model_port,ca_file=str(caller/'model-ca.pem'))
        app['denied_paths'] += [str(completion)];app['model_denied_files']=[str(completion/'server.key')]
    write(policy_path,policy);write(caller/'model-client.json',client)
    selection=dict(mode='recorded' if recorded else 'live',manifest=str(manifest),approval=str(root/'approval.json'),session=session)
    write(authority/'backend.json',selection)
    app.update(model_config=str(caller/'model-client.json'),retrieval=dict(initial_view=view,consent=consent),readonly_paths=[str(authority)],campaign_backend=selection)
    if recorded:app['preparation_fixture_boundary']='AUTHORED_MODEL_RESPONSE_FIXTURE'
    write(caller/'application.json',app)
    return dict(id=session,placement=placement,application=str(caller/'application.json'),caller_database=call['database'],completion_root=str(completion),policy=str(policy_path),
        runtime_lock=lock,backend_selection=str(authority/'backend.json'),channel=channel_handle(ch),model_port=model_port,recipient=recipient,
        principal='A',scope=owner['scope'],profile=m.CPU_PROFILE,descriptors=owner['catalogue'],consent=dict(recipient=recipient,sha256=digest(canonical(consent)),record_count=len(records),fields=['uuid','time','content','metadata.links','metadata.stv','compatibility-prior']),provider_denied_paths=denied,
        provider_denied_files=[str(root/'corpus.json'),str(root/'setup-evidence.json')],
        secret_references=[str(policy_path),str(caller/'model-client.json'),str(ch.config_path)],non_model_placement=dict(mailbox='authenticated-same-host-HTTPS',encoder='local',retrieval='local',cognition='local'))


def prepare(root, *, recorded=False, responses=None, variant=0):
    from .preparation_guard import verify
    verify(os.environ['FUSION_PREP_PARENT_NET'])
    root=Path(root).resolve();root.mkdir(mode=0o700,parents=True,exist_ok=False)
    manifest=root/'manifest.json';corpus=generated(variant)
    run,cfg=setup(corpus,root=root/'memory')
    try:
        # Setup write authority is removed once, before the immutable measured
        # composition. Existing owners, identifiers and ready view are retained.
        for name in ('memory.append.write','memory.append.disclose','atom.storage.create','search.build'):
            methods=run.h.config['principals']['A']['scopes']['generated-s03']
            if name in methods:methods.remove(name)
        run.h.save()
        encoder=c.read(cfg['encoder_config']);methods=encoder['principals']['A']['scopes']['generated-s03']
        encoder['principals']['A']['scopes']['generated-s03']=[x for x in methods if not x.startswith('embedding.memory.')];write(cfg['encoder_config'],encoder)
        (root/'evaluator').mkdir(mode=0o700)
        facts=[p['content'] for p in cfg['payloads'].values() if p['content'].startswith('Synthetic project Aster ')]
        write(root/'evaluator/truth.json',dict(target_fact=facts[0] if len(facts)==1 else None))
        write(root/'setup-evidence.json',cfg['setup']);write(root/'corpus.json',corpus)
        write(root/'evaluator/retained-records.json',dict(payloads=cfg['payloads'],source=cfg['setup']['source'],view=cfg['view']))
        sessions=[compose(root,manifest,run,cfg,p,recorded,responses or ['query '+QUERY,'send '+BODIES[0]]) for p in ('local','network')]
    finally:run.close()
    # No measured application/model database exists at freeze; deadlines will
    # be sampled by the original application only when actual input is accepted.
    for s in sessions:c.require(not Path(s['caller_database']).exists() and not (Path(s['completion_root'])/'model.sqlite').exists(),'MEASURED_STATE_EXISTS')
    bindings=[]
    for p in sorted(root.rglob('*')):
        if p.is_file() and (p.suffix in ('.json','.pem','.key') or '/da/' in str(p) or '/records/' in str(p)):
            # Logs and setup audit contain execution observations, not config.
            if p.name.endswith('.json'):
                try: normalized='model_completion' in c.read(p)
                except (ValueError,TypeError):normalized=False
            else:normalized=False
            bindings.append(dict(path=str(p),sha256=c.normalized_config(p) if normalized else c.sha(p),normalized=normalized))
    # Shared executable/runtime inputs live outside this campaign's fresh
    # journals. Bind their actual tested bytes as well as configuration paths.
    from tests.neoclaw_support import RUNTIME, DETTA
    from .channel_composition import SERVER
    from .embedding_composition import CALLER_RUNTIME, PROVIDER_RUNTIME
    native=c.read(RUNTIME);memory=c.read(PROVIDER_RUNTIME)
    shared=[Path(RUNTIME),Path(native['swipl']),Path(DETTA),Path(SERVER),
            Path(CALLER_RUNTIME),Path(PROVIDER_RUNTIME),Path(memory['helper'])]
    for p in shared:
        bindings.append(dict(path=str(p.resolve()),sha256=c.sha(p),normalized=False))
    sources=c.read(c.ROOT/'integration/neoclaw/model-sources.json')
    required=[dict(path=sources['runtime']['binary'],sha256=sources['runtime']['binary_sha256']),
              dict(path=sources['model']['files']['manifest_path'],sha256=sources['model']['files']['manifest_sha256'])]
    required += [dict(path=x['path'],sha256=x['digest'].split(':')[1]) for x in sources['model']['files']['files']]
    loaded=c.read(c.ROOT/'evidence/s07/isolated-runtime/loaded-runner.json')[0]['loaded_runtime_files']
    required += [dict(path=name,sha256=sha) for name,sha in loaded.items()]
    slots=[dict(name=p['placement']+'-'+stage,id=str(uuid.uuid5(uuid.UUID(p['id']),'model/'+str(n))),session=p['id'],slot=n,state='PLANNED_UNRESERVED') for p in sessions for n,stage in ((1,'query'),(2,'reply'))]
    value=dict(schema='retrieval-grounded-campaign/1',campaign_id=root.name,baseline_commit=c.BASELINE,kind='recorded-qualification' if recorded else 'live',
        canonical_encoding='fusion.contracts.canonical: JSON sorted keys, compact separators, UTF-8, ensure_ascii=False; no trailing newline',
        sources=c.sources(),bindings=bindings,runtime_required_files=required,runtime_identity=sources,
        runtime_availability='NOT_CHECKED',execution_root=str(root/'execution'),sessions=sessions,slots=slots,
        corpus=dict(path=str(root/'corpus.json'),retained_records=str(root/'evaluator/retained-records.json'),
            retained_records_sha256=c.sha(root/'evaluator/retained-records.json'),source=cfg['setup']['source'],
            retained_view=cfg['view'],setup_evidence=str(root/'setup-evidence.json')),
        static_inputs=dict(query=QUERY,peer_inputs=[QUESTION,FOLLOWUP],prompt_scaffold=retrieval_scaffold(),equally_eligible_bodies=BODIES),
        evaluator=dict(path=str(root/'evaluator/truth.json'),policy='exact actual admitted body against independently retained Aster fact; permission alone never passes'),
        prompt_rules=dict(first='empty measured history and promoted context; answer absent',second='actual committed query capture in native COMMAND_RETURN; exact retained view and recipient receipt',
            transformations='pinned native parser, source/time construction, model_contracts.messages and native cleaning; no repair',second_prompt_bytes=None),
        limits=dict(sessions=2,total_generations=4,per_session=2,output_tokens=6000,total_output_allowance=24000,model_deadline_ms=300000,tool_deadline_ms=30000,model_rpc_reservations=8,
            backend_evaluations_per_occurrence=1,preparation_observer_ms=60000,query_observer_ms=330000,reply_observer_ms=360000,peer_observer_ms=30000),
        deadline_rule='native input acceptance samples once; replays retain absolute deadlines; no preparation deadline',
        stop_rules=['query missing or nondecisive: no second input','any failure/expiry: stop session, retain all diagnostics; no replacement session or slot transfer',
                    'captured results recover through existing owner; unknown reservation stays spent','uncertain external send never resent'],
        diagnostics=dict(consent='approved synthetic inputs, generated memory content/labels/STVs, actual captured prompts/results, peer traffic, sanitized statuses and timings',
                         secret_exclusions='no credentials/private keys in published evidence; evaluator inaccessible to providers',retention='retain every attempt and failure; no automatic cleanup'),
        state='AWAITING_LIVE_AUTHORIZATION',authorized_live_generations=0)
    manifest.write_bytes(canonical(value));manifest.with_suffix('.sha256').write_text(digest(manifest.read_bytes())+'\n')
    c.initialize(manifest)
    write(root/'approval-request.UNISSUED.json',dict(campaign_id=root.name,manifest_sha256=digest(manifest.read_bytes()),slots=[x['name'] for x in slots],
        max_generations=4,required_authority='EXPLICIT_USER_APPROVAL',not_an_approval=True,execution_window='USER_MUST_SUPPLY',user_statement=None))
    return manifest
