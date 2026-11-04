"""Authenticated application facet for the second fixed, approved continuation.

The session operator explicitly drives one transition at a time. Models cannot
register approval or access this endpoint. Signing and finality stay with the
existing commitment owner, contacted only by its declared HTTPS client.
"""
import json,sqlite3,tempfile,time
from pathlib import Path
from fusion.contracts import canonical,digest,require
from fusion.lookup_contracts import identity as uid
from fusion.policy import Policy
from fusion.sustained_sessions import SustainedSessionStore
from fusion.preview_tools import SessionAuthority
from fusion.preview_chain import Client
from fusion.chain_continuation import Continuation,PROFILE

ROUTE='/preview/chain-continuation'


def invoke(config,component,state,run,credential,q,hook=lambda _:None):
    require(type(q) is dict and set(q)=={'profile','id','session','occurrence','operation','body'} and len(canonical(q))<=4096)
    require(q['profile']==PROFILE,'UNSUPPORTED_PROFILE');uid(q['session']);uid(q['occurrence'])
    require(type(q['id']) is str and 1<=len(q['id'])<=128)
    operation=q['operation'];require(operation in ('admit','advance','observe','cancel'),'UNSUPPORTED_OPERATION')
    fields={'admit':{'identity','deadline_ms','approval_sha256'},'cancel':{'identity'},'observe':set(),'advance':set()}
    require(type(q['body']) is dict and set(q['body'])==fields[operation])
    policy=Policy(config);actor=policy.authenticate(credential);cfg=policy.current()['native_sessions']
    settings=json.loads(Path(component).read_bytes());chain=settings['preview'].get('chain',{})
    require(chain.get('continuation')==PROFILE and chain.get('enabled') is True and chain.get('registration') is not None,'UNSUPPORTED_PROFILE')
    reg=chain['registration'];scope=reg['approved']['scope_ref']
    # This release accepts only the explicitly shared scope, never private roots.
    require(scope==settings['preview']['scope'] and reg['principal']==cfg['principal'],'UNAUTHORIZED')
    def session_authority(who,selected,action):
        require(who==cfg['principal'] and selected==scope and policy.authenticate(credential)==actor,'UNAUTHORIZED')
        policy.check(actor,scope,'sessions.observe');policy.check(actor,scope,'sessions.disclose')
        if operation!='observe':policy.check(actor,scope,'sessions.chain-continuation')
    store=SustainedSessionStore(cfg['database'],session_authority,cfg['allocation'])
    try:allocation=store.allocated(cfg['principal'],q['session'])
    finally:store.close()
    require(allocation['frozen']['scope']==scope,'UNAUTHORIZED')
    root=Path(state)/'sessions'/q['session'];database=root/'caller.sqlite';runtime=Path(run)/'sessions'/q['session']
    require(not root.is_symlink() and not database.is_symlink() and not runtime.is_symlink(),'UNAUTHORIZED')
    require(database.is_file(),'NOT_AVAILABLE')
    if not (runtime/'application.json').is_file():
        # A completed session has no pending native input to wake on restart.
        # Recreate only its accepted, hash-checked configuration from the existing
        # owner template. This launches nothing and changes no occurrence bound.
        from .sustained_runtime import materialize
        materialize(config,Path(state),Path(run),q['session'])
    require((runtime/'application.json').is_file(),'NOT_AVAILABLE')
    app=json.loads((runtime/'application.json').read_bytes())
    require(app['session_id']==q['session'] and app['preview']['scope']==scope,'CONFLICT')
    def authorize(action):
        session_authority(cfg['principal'],scope,action)
        current=json.loads(Path(component).read_bytes())
        require(current['preview']['chain']==chain and current['peers']==settings['peers'],'CONFLICT')
        raw=json.loads(Path(app['preview']['authority_file']).read_bytes())
        authority=SessionAuthority(**dict(raw,tools=frozenset(raw['tools'])))
        authority.check(cfg['principal'],time.time_ns()//1000000)
        require(authority.scope==scope and 'inspect-atom' in authority.tools,'UNAUTHORIZED')
    authorize(operation)
    transport=dict(endpoint=dict(host=settings['peers']['fusion-commitment'],port=settings['https_port'],ca_file='/secrets/ca.crt'),
        credential=Path('/secrets/fusion-commitment-token').read_text().strip(),registration=reg)
    db=sqlite3.connect(database.resolve().as_uri()+('?mode=ro' if operation=='observe' else '?mode=rw'),uri=True,timeout=2)
    db.row_factory=sqlite3.Row
    try:
        with tempfile.TemporaryDirectory(prefix='chain-continuation-',dir=run) as directory:
            path=Path(directory)/'client.json';path.write_bytes(canonical(transport));path.chmod(0o600)
            if operation!='admit':require(db.execute("SELECT 1 FROM sqlite_master WHERE name='integrated_chain_continuations'").fetchone() is not None,'NOT_FOUND')
            owner=Continuation(db,Client(path),authorize,hook=hook,initialize=operation=='admit')
            if operation=='admit':value=owner.admit(q['occurrence'],q['body']['identity'],q['body']['deadline_ms'],q['body']['approval_sha256'])
            elif operation=='cancel':value=owner.cancel(q['occurrence'],q['body']['identity'])
            else:value=getattr(owner,operation)(q['occurrence'])
            authorize(operation)
            return dict(profile=PROFILE,id=q['id'],request_digest=digest(canonical(q)),actor=actor,value=value)
    finally:db.close()
