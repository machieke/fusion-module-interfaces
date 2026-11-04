"""Opt-in lifecycle records for the installed, operator-selected providers.

No HTTP advertisement can add a provider. Templates, source/image pins and
capabilities come from trusted composition; health does not establish authority
or conformance. Tokens are not stored in these metadata records.
"""
import json,ssl,http.client,time
from pathlib import Path
from fusion.contracts import canonical,digest,require
from fusion.provider_lifecycle import PROFILE,Registry,ACTIONS,configuration
from fusion.registry import descriptor_read
from fusion.policy import Policy
from fusion.sustained_sessions import SustainedSessionStore
from .configure import write

ROUTE='/preview/providers'
ROLES={'atom.storage':'fusion-storage','agent.messaging':'fusion-messaging',
       'execution':'fusion-execution','execution.workspace':'fusion-execution','pln.kernel':'fusion-execution',
       'search':'fusion-search','embedding':'fusion-embedding','memory.lifecycle':'fusion-storage',
       'episodic.memory':'fusion-episodes','belief.revision':'fusion-beliefs','attention':'fusion-attention',
       'relations':'fusion-relations','model.inference':'fusion-model'}


def configure(settings,cfg,run):
    selected=settings['preview']['sustained'].get('provider_registry')
    if selected is None or settings['role'] not in settings['preview']['agents']:return
    require(type(selected) is dict and {'profile','pins','readiness_ms'}<=set(selected)<={'profile','pins','readiness_ms','rollover'} and selected['profile']==PROFILE,'UNSUPPORTED_PROFILE')
    require(type(selected['pins']) is dict)
    rollover=selected.get('rollover')
    if rollover is not None:
        from fusion.contracts import label
        require(type(rollover) is dict and {'identity','pins'}<=set(rollover)<={'identity','pins','retained_records'} and label(rollover['identity']) and
            len(rollover['identity'])<=32 and type(rollover['pins']) is dict,'INVALID_ARGUMENT')
        require(1<=len(rollover['pins'])<=32 and set(rollover['pins'])<=set(selected['pins']),'INVALID_ARGUMENT')
        require(type(rollover.get('retained_records',{})) is dict and len(rollover.get('retained_records',{}))<=32)
    current=cfg['native_sessions'];records={};templates={}
    secret=Path(settings.get('secret_directory','/secrets'));ca=digest((secret/'ca.crt').read_bytes())
    for name,template in current['allocation']['templates'].items():
        recipe=current['runtime_templates'][name]
        app=json.loads((Path(recipe['directory'])/'application.json').read_bytes())
        groups={}
        for raw in app['preview']['providers']:
            descriptor=descriptor_read(raw);role=ROLES.get(descriptor.interface)
            require(role is not None,'UNSUPPORTED_PROFILE')
            # Local application vocabulary/context is not a remotely managed
            # provider; only actual declared interface ports appear here.
            groups.setdefault(role,[]).append(raw)
        # ModelInference has its own explicit descriptor outside tool catalogue.
        model=json.loads((Path(recipe['directory'])/'model.json').read_bytes())
        require(model['placement']=='network' and template['binding']['model_boundary']=='RECORDED_FIXTURE','UNSUPPORTED_PROFILE')
        groups['fusion-model']=model['catalogue']
        templates[name]=[]
        for role,capabilities in groups.items():
            require(role in selected['pins'] and role in settings['peers'],'NOT_AVAILABLE')
            unique={digest(canonical(d)):d for d in capabilities};capabilities=list(unique.values())
            requirements=[]
            for raw in capabilities:
                d=descriptor_read(raw)
                for profile in sorted(d.profiles):
                    requirements.append(dict(interface=d.interface,minimum=d.version,maximum_exclusive=str(int(d.version.split('.')[0])+1)+'.0.0',
                        profile=profile,operations=sorted(d.operations),guarantees=sorted(d.guarantees),privacy=d.privacy,features=sorted(d.features),payload_bytes=d.max_payload_bytes))
            key=name+'-'+role
            records[key]=dict(scope=template['scope'],endpoint=dict(host=settings['peers'][role],port=settings['https_port'],ca_sha256=ca),
                implementation=selected['pins'][role],capabilities=capabilities,requirements=requirements,conformance=[])
            current_record=records[key]
            retained=rollover.get('retained_records',{}).get(key) if rollover else None
            if retained is not None:
                # An operator exports the exact earlier metadata through the
                # registry port. It is not regenerated from this caller's new
                # catalogue or inferred from another owner's state. Pins,
                # endpoint and scope must still match the retained selection.
                require(type(retained) is dict and all(retained.get(k)==current_record[k]
                    for k in ('scope','endpoint','implementation')),'CONFLICT')
                records[key]=retained
            if rollover is not None and role in rollover['pins']:
                # Retain the original trusted record for old selections. Only
                # fresh allocation selects the separately admitted compatible
                # implementation on this explicitly retained service endpoint.
                # This is not state transfer, automatic failover or new authority.
                replacement=rollover['identity']+'-'+key
                records[replacement]={**current_record,'implementation':rollover['pins'][role]}
                key=replacement
            templates[name].append(key)
    if rollover:
        require(set(rollover.get('retained_records',{}))<=set(records),'INVALID_ARGUMENT')
    current['provider_registry']=configuration(dict(profile=PROFILE,records=records,templates=templates,readiness_ms=selected['readiness_ms']))
    for template in current['allocation']['templates'].values():
        scope=template['scope'];cfg['principals']['operator']['scopes'][scope]+=['providers.'+op for op in (*ACTIONS,'probe','inspect','select')]
    if 'task_ingress' in cfg:
        # The trusted ingress may select already admitted shared providers,
        # atomically with its new session. Registration/probing/enablement stay
        # operator-only; neither a sender nor a recorded proposal grants them.
        scope=cfg['task_ingress']['scope']
        cfg['principals']['worker']['scopes'][scope].append('providers.select')
    write(run/'owner.json',cfg)


def health(record,ca_file):
    require(digest(Path(ca_file).read_bytes())==record['endpoint']['ca_sha256'],'CONFLICT')
    ep=record['endpoint'];context=ssl.create_default_context(cafile=ca_file)
    context.minimum_version=ssl.TLSVersion.TLSv1_2
    conn=http.client.HTTPSConnection(ep['host'],ep['port'],timeout=2,context=context)
    try:
        conn.request('GET','/health/ready');reply=conn.getresponse();raw=reply.read(4097)
        require(len(raw)<=4096,'NOT_AVAILABLE')
        return reply.status==200
    finally:conn.close()


def invoke(path,credential,q,hook=lambda _:None,probe=None):
    require(type(q) is dict and set(q)=={'profile','id','operation','body'} and q['profile']==PROFILE,'UNSUPPORTED_PROFILE')
    require(type(q['id']) is str and 1<=len(q['id'])<=128 and len(canonical(q))<=4096)
    policy=Policy(path);actor=policy.authenticate(credential);cfg=policy.current();selected=cfg['native_sessions']
    require('provider_registry' in selected,'UNSUPPORTED_PROFILE')
    def auth(scope,method):
        require(policy.authenticate(credential)==actor,'UNAUTHORIZED');policy.check(actor,scope,method)
        require(policy.current()['native_sessions'].get('provider_registry')==selected['provider_registry'],'CONFLICT')
    def session_auth(principal,scope,method):
        require(principal==selected['principal'],'UNAUTHORIZED');auth(scope,'providers.inspect')
    store=SustainedSessionStore(selected['database'],session_auth,selected['allocation'])
    try:
        reg=Registry(store,selected['provider_registry'],auth,hook)
        op=q['operation'];b=q['body'];require(type(b) is dict)
        if op=='inspect':require(set(b)=={'provider'});value=reg.inspect(b['provider'])
        elif op=='selected':require(set(b)=={'session'});value=reg.selected(b['session'])
        elif op=='probe':
            require(set(b)=={'provider','identity'})
            ca=str(Path(cfg['tls_certificate']).parent/'ca.crt')
            value=reg.probe(b['identity'],b['provider'],probe or (lambda r:health(r,ca)))
        elif op in ACTIONS:
            require(set(b)==({'provider','identity','retained'} if op=='retire' else {'provider','identity'}))
            value=reg.act(b['identity'],op,b['provider'],b.get('retained','required'))
        else:require(False,'UNSUPPORTED_OPERATION')
        return dict(id=q['id'],profile=PROFILE,request_digest=digest(canonical(q)),actor=actor,value=value)
    finally:store.close()
