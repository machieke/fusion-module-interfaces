"""Closed deployment composition of the existing memory, channel and X01 owners."""
import json
from pathlib import Path
import time
from fusion import channel_contracts as ch,model_contracts as m,channel_services as cs,retrieval_services as rs
from fusion.contracts import canonical,digest,require
from fusion.registry import descriptor_wire,descriptors
from integration.neoclaw.model_startup import retrieval_scaffold
from .configure import write


def configure(settings,*,live_authority=None):
    role=settings['role'];w=settings['workflow'];state=Path(settings.get('state','/state'));run=Path(settings.get('run','/run/fusion'))
    state.mkdir(parents=True,exist_ok=True);run.mkdir(parents=True,exist_ok=True);secret=Path('/secrets')
    require(w['enabled'] and w['mode'] in ('recorded','live'),'UNAUTHORIZED')
    live=w['mode']=='live'
    require(live or w['liveEnabled'] is False,'UNAUTHORIZED')
    if live and role=='fusion-model':require(live_authority is not None and w['liveEnabled'] is True,'UNAUTHORIZED')
    if live and role=='omega-agent' and w['phase']=='measured':
        from .future_live import authority
        plan,_=authority('/campaign/plan.json','/approval/approval.json')
        require(w['liveEnabled'] is True and w['session']==plan['slots'][0]['session'],'UNAUTHORIZED')
        # The staged caller may remain disabled while the approved provider
        # validates its assets. Every other setting is the exact frozen input.
        bound=dict(settings,native_enabled=True)
        require(digest(canonical(bound))==plan['caller_configuration_sha256'],'CONFLICT')
    def token(name):
        value=(secret/name).read_text().strip();require(32<=len(value)<=256 and value.isascii(),'UNAUTHORIZED');return value
    def endpoint(name):return dict(host=settings['peers'][name],port=settings['https_port'],ca_file='/secrets/ca.crt')
    if role in ('omega-agent','fusion-storage','fusion-search','fusion-embedding'):
        base={k:v for k,v in settings.items() if k!='workflow'};base['service_composition']='neoclaw-memory-services/1'
        write(run/'memory-component.json',base)
        from .configure import configure as memory_base
        _,cfg,_,_=memory_base(run/'memory-component.json')
        if role in ('fusion-storage','fusion-search'):
            methods=['atom.storage.get','atom.storage.getMany','search.query','search.ready']
            cfg['principals']['M']=dict(credential=token('measured-token'),scopes={settings['memory']['scope']:methods})
            cfg['memory_read']['readers'].append('M');write(run/'owner.json',cfg)
        elif role=='fusion-embedding':
            cfg['principals']['M']=dict(credential=token('measured-token'),scopes={settings['memory']['scope']:['embedding.encode','embedding.disclose']});write(run/'owner.json',cfg)
    else:
        cfg=dict(tls_certificate='/secrets/tls.crt',tls_key='/secrets/tls.key')
        test=settings.get('test',{});require(not test or settings['enable_test_faults'],'UNAUTHORIZED')
        cfg.update(test_failpoints=bool(test),failpoint_marker=str(state/'pause.json'))
        if test.get('pause_at') and not (state/'pause.json').exists():cfg['pause_at']=test['pause_at']
    channel=dict(profile=ch.PROFILE,sharing='generated-shareable',scope=w['channelScope'],session=w['session'],bridge=w['bridge'],target=w['target'],ingress_route='in-M',egress_route='out-bridge',approved_inputs=[w['question'],w['followup']],approved_outputs=w['bodies'],catalogue=[descriptor_wire(d) for d in descriptors(atom_provider='detta') if d.interface in ch.OPERATIONS])
    methods=[n+'.'+op for n,ops in ch.OPERATIONS.items() for op in ops]
    if role in ('fusion-storage','fusion-messaging'):
        cc=dict(service_composition=cs.COMPOSITION,channel_role='storage' if role=='fusion-storage' else 'messaging',channel_store=dict(channel,roles={'M':'application','bridge':'bridge'}),database=str(state/'channel-admission.sqlite'),capacity=ch.MAILBOX_CAPACITY,atom_provider='detta',
            routes={'in-M':dict(scope=channel['scope'],owner='M'),'out-bridge':dict(scope=channel['scope'],owner='bridge')},principals={p:dict(credential=token(key),scopes={channel['scope']:methods+['channel.'+r]}) for p,key,r in [('M','channel-caller-token','application'),('bridge','channel-bridge-token','bridge')]})
        if role=='fusion-storage':
            cc.update(atoms_database=str(state/'channel-atoms.sqlite'),da_root=str(state/'channel-data'),detta_binary='/opt/native/fusion-detta-adapter',payload_delegations={'mailbox-M':'M','mailbox-bridge':'bridge'})
            for actor in ('M','bridge'):cc['principals']['mailbox-'+actor]=dict(credential=token('payload-'+actor+'-token'),scopes={channel['scope']:['channel.payload.read']})
        else:cc.update(messages_database=str(state/'channel-messages.sqlite'),source_endpoint=endpoint('fusion-storage'),source_credentials={p:token('payload-'+p+'-token') for p in ('M','bridge')})
        write(run/'channel-owner.json',cc)
    if role in ('omega-agent','fusion-channel-bridge'):
        bridge=role=='fusion-channel-bridge'
        client=dict(channel,principal='bridge' if bridge else 'M',role='bridge' if bridge else 'application',placement='service-network',service_composition=cs.COMPOSITION,fallback=False,
            endpoints={n:endpoint(role) for n,role in [('atom.storage','fusion-storage'),('agent.messaging','fusion-messaging')]},
            service_credentials={n:token('channel-'+role+'-token') for n,role in [('atom.storage','storage'),('agent.messaging','messaging')]})
        write(run/'channel-client.json',client)
        if bridge:
            write(run/'bridge.json',dict(client=str(run/'channel-client.json'),database=str(state/'bridge.sqlite'),server=dict(host=settings['peers']['irc-server'],port=6667,deployment=cs.COMPOSITION),nick='omega',seconds=900,test_failpoints=cfg.get('test_failpoints',False),pause_at=cfg.get('pause_at'),failpoint_marker=str(state/'pause.json')))
    if role=='fusion-model':
        if live:
            plan,approval=live_authority
            require(w['session']==plan['slots'][0]['session'] and w['recipient']==plan['recipient'],'CONFLICT')
            runtime_lock=plan['runtime_lock'];expires=approval['expires_ms']
        else:
            from .recorded_model import BOUNDARY
            fixture=dict(boundary=BOUNDARY,mode='recorded',session=w['session'],responses=w['responses'],log=str(state/'recorded-evaluations.jsonl'))
            write(run/'recorded.json',fixture)
            lifetime=state/'authority-lifetime.json'
            if not lifetime.exists():write(lifetime,dict(expires_ms=time.time_ns()//1000000+900000))
            expires=json.loads(lifetime.read_text())['expires_ms'];runtime_lock=dict(path=str(run/'recorded.json'),sha256=digest(canonical(fixture)))
        disclosure=dict(policy=rs.POLICY,scaffold=retrieval_scaffold(),memories=['()'],users=[str(['HUMAN-MSG:','peer: '+x]) for x in (w['question'],w['followup'])],query=w['query'],recipient=w['recipient'])
        cfg.update(model_completion=dict(database=str(state/'model.sqlite'),scope=w['modelScope'],sharing=m.PRIVACY,sessions=[w['session']],max_calls=2,expires_ms=expires,catalogue=[descriptor_wire(m.descriptor(m.CPU_PROFILE))],disclosure=disclosure,disclosure_issuers=['M'],runtime_lock=runtime_lock),
            principals={p:dict(credential=token(key),scopes={w['modelScope']:['model.'+op for op in ('complete','observe','authorize','disclose','issue')]}) for p,key in [('M','caller-token'),('other','other-token')]})
    if role=='omega-agent':
        # Setup uses the old native memory entrypoint. Measured gets a NEW DB and
        # complete retained view from this application's own setup observation.
        app=json.loads((run/'application.json').read_text())
        if w['phase']=='measured':
            app.pop('model_fixture');app.update(composition='controlled-native-loop/11',turn_limit=2,session_id=w['session'],workdir=str(state/'measured-native'),status_file=str(state/'measured-status.json'),channel_config=str(run/'channel-client.json'),channel_wait_ms=10000,channel_poll_limit=128,channel_irc_probe_port=6667,model_config=str(run/'model-client.json'),preparation_fixture_boundary='RECORDED_MODEL_RESPONSE_FIXTURE',model_denied_files=['/secrets/tls.key','/opt/model/model.safetensors','/opt/generative/ollama','/run/fusion/recorded.json'])
            if live:app.pop('preparation_fixture_boundary')
            caller=json.loads((run/'caller.json').read_text());caller['database']=str(state/'measured.sqlite');write(run/'caller.json',caller)
            for name in ('memory-read-template.json','memory-append.json','embedding.json','memory-embedding.json'):
                v=json.loads((run/name).read_text());v['principal']='M'
                if 'session' in v:v['session']=w['session']
                for n in v['service_credentials']:v['service_credentials'][n]=token('measured-fusion-'+('storage' if n=='atom.storage' else n)+'-token')
                write(run/name,v)
        else:require(w['phase']=='setup','UNSUPPORTED_PROFILE')
        test=settings.get('test',{})
        if test.get('pause_slot'):app['pause_slot']=test['pause_slot']
        write(run/'application.json',app)
    if role=='irc-server':
        (run/'ngircd.conf').write_text('''[Global]
Name = isolated-k3s.local
Info = generated single-node qualification
Listen = 0.0.0.0
Ports = 6667
PidFile = /state/ngircd.pid
[Limits]
MaxConnections = 8
MaxConnectionsIP = 8
MaxJoins = 1
MaxPenaltyTime = 0
[Options]
DNS = no
Ident = no
PAM = no
SyslogFacility = none
''')
    if role=='irc-peer':write(run/'peer.json',dict(host=settings['peers']['irc-server'],port=6667,deployment=cs.COMPOSITION,target=w['target'],log=str(state/'peer-traffic.jsonl'),seconds=900))
    write(run/'owner.json',cfg)
    return settings,cfg,state,run
