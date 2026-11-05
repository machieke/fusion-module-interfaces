"""Explicit workflow controls over the existing application owner's HTTPS port.

No model-selected credentials/endpoints, evaluator answers or new worker. The
normal session owner supplies captures and its supervisor executes native work.
"""
import json,time
from pathlib import Path
from fusion.contracts import canonical,digest,require
from fusion.lookup_contracts import identity as uid
from fusion.policy import Policy
from fusion.guarded_continuation import Workflow,PROFILE
from fusion.workflow_prerequisites import OwnerObservations
from fusion.workflow_recipes import catalogue
from fusion.sustained_sessions import SustainedSessionStore

ROUTE='/preview/workflows'
FIELDS={'admit':{'recipe','steps','deadline_ms'},'advance':{'version'},'observe':set(),
    'amend':{'identity','version','suffix','cause'},'checkpoint':{'identity','version','reason'},
    'decide':{'checkpoint','identity','binding_sha256','action'},'catalogue':set()}


def observers(app,store,principal,scope):
    """Read only this owner's accepted config; use ports for all foreign data."""
    from fusion.preview_memory_services import Client as MemoryClient
    from fusion.preview_ports import Client as FacetClient
    from fusion.preview_atoms import client as atom_client
    life=MemoryClient(app['active_memory_configs']['memory.lifecycle'],'memory.lifecycle') if 'active_memory_configs' in app else None
    relation=FacetClient(app['facet_configs']['relations'],'relations') if 'relations' in app.get('facet_configs',{}) else None
    atom_cfg=json.loads(Path(app['memory_atoms_config']).read_bytes()) if app.get('memory_atoms_config') else None
    selections=dict(session=app['session_id'],scope=scope)
    if life:selections['lifecycle']=life.frozen
    if relation:selections['relations']=relation.frozen
    if atom_cfg:selections['atoms']={k:v for k,v in atom_cfg.items() if k!='credential'}
    beliefs=None
    if app.get('evidence_config'):
        from fusion.cognitive_services import client_configuration,Remote
        cfg,binding=client_configuration(app['evidence_config'])
        selections['beliefs']=binding; beliefs=Remote(cfg,'belief.revision')
    return OwnerObservations(scope,principal,store,selections,lifecycle=life,relations=relation,
        atoms=(lambda deadline:atom_client(atom_cfg,deadline)) if atom_cfg else None,beliefs=beliefs)


def invoke(config,state,run,credential,q,wake=lambda _:None,hook=lambda _:None):
    require(type(q) is dict and set(q)=={'profile','id','session','workflow','operation','body'} and len(canonical(q))<=65536)
    require(q['profile']==PROFILE,'UNSUPPORTED_PROFILE'); uid(q['session']);uid(q['workflow'])
    require(type(q['id']) is str and 1<=len(q['id'])<=128)
    operation=q['operation'];require(operation in FIELDS,'UNSUPPORTED_OPERATION')
    require(type(q['body']) is dict and set(q['body'])==FIELDS[operation])
    policy=Policy(config);actor=policy.authenticate(credential);cfg=policy.current()['native_sessions'];principal=cfg['principal']
    require(cfg.get('workflow_profile')==PROFILE,'UNSUPPORTED_PROFILE')
    require('synthetic-task' in cfg['assignments'],'UNSUPPORTED_PROFILE')
    fenced=(Path(state)/'restore-fence.json').exists()
    require(not fenced or operation in ('observe','catalogue'),'UNAUTHORIZED')
    def session_authority(who,scope,action):
        require(policy.authenticate(credential)==actor and who==principal,'UNAUTHORIZED')
        policy.check(actor,scope,'sessions.observe');policy.check(actor,scope,'sessions.disclose')
        if action=='input.accept':policy.check(actor,scope,'sessions.submit')
        policy.check(actor,scope,'sessions.workflows-'+operation)
    store=SustainedSessionStore(cfg['database'],session_authority,cfg['allocation'])
    try:
        allocation=store.allocated(principal,q['session']);scope=allocation['frozen']['scope']
        session_authority(principal,scope,'observe')
        if operation=='catalogue':value=catalogue()
        else:
            runtime=Path(run)/'sessions'/q['session'];require(not runtime.is_symlink(),'UNAUTHORIZED')
            if not (runtime/'application.json').is_file():
                require(not fenced,'NOT_AVAILABLE')
                from .sustained_runtime import materialize
                materialize(config,Path(state),Path(run),q['session'])
            app=json.loads((runtime/'application.json').read_bytes())
            require(app['session_id']==q['session'] and app['preview']['scope']==scope,'CONFLICT')
            def authorize(action,selected):
                require(selected==scope,'UNAUTHORIZED');session_authority(principal,scope,action)
                current=policy.current()['native_sessions'];require(current.get('workflow_profile')==PROFILE,'UNSUPPORTED_PROFILE')
            observed=observers(app,store,principal,scope)
            if operation!='admit':
                require(store.db.execute("SELECT 1 FROM sqlite_master WHERE name='pilot_workflows'").fetchone(),'NOT_FOUND')
                owned=store.db.execute('SELECT session FROM pilot_workflows WHERE id=?',(q['workflow'],)).fetchone()
                require(owned is not None and owned[0]==q['session'],'UNAUTHORIZED')
            owner=Workflow(store,principal,observed,authorize,wake=wake,hook=hook,
                           initialize=operation=='admit',observation_only=fenced)
            b=q['body'];wid=q['workflow']
            if operation=='admit':value=owner.admit(wid,q['session'],b['recipe'],b['steps'],b['deadline_ms'])
            elif operation=='advance':value=owner.advance(wid,b['version'])
            elif operation=='amend':value=owner.amend(wid,b['identity'],b['version'],b['suffix'],b['cause'])
            elif operation=='checkpoint':value=owner.checkpoint(wid,b['identity'],b['version'],b['reason'])
            elif operation=='decide':value=owner.decide(wid,b['checkpoint'],b['identity'],actor,b['binding_sha256'],b['action'])
            else:value=owner.observe(wid)
            authorize(operation,scope)
        return dict(profile=PROFILE,id=q['id'],request_digest=digest(canonical(q)),actor=actor,principal=principal,value=value)
    finally:store.close()


def request(body,owner='/run/fusion/owner.json',component='/config/component.json'):
    """Installed CLI/browser share the exact request; only transport differs."""
    from fusion.preview_transport import invoke
    cfg=json.loads(Path(owner).read_bytes());settings=json.loads(Path(component).read_bytes())
    require(type(body) is dict and body.get('profile')==PROFILE,'UNSUPPORTED_PROFILE')
    transport=dict(endpoint=dict(host=settings['peers'][settings['role']],port=settings['https_port'],ca_file='/secrets/ca.crt'),
        credential=cfg['principals']['operator']['credential'])
    result=invoke(transport,ROUTE,body,time.time_ns()//1000000+30000)
    require(type(result) is dict and set(result)=={'profile','id','request_digest','actor','principal','value'},'NOT_AVAILABLE')
    require((result['profile'],result['id'],result['request_digest'],result['actor'],result['principal'])==
            (PROFILE,body['id'],digest(canonical(body)),'operator',cfg['native_sessions']['principal']),'NOT_AVAILABLE')
    return result['value']
