"""Owner-authorized inspection continuation observations and finite controls.

Only the application's own retained captures are read. This endpoint never
constructs Application, starts native work, contacts a model/provider, changes a
deadline or repairs an outcome. Cancellation fences the next local reservation;
it cannot retract any effect previously reserved at another owner.
"""
import json,sqlite3
from pathlib import Path
from types import SimpleNamespace
from fusion.contracts import canonical,digest,require
from fusion.lookup_contracts import identity as uid
from fusion.policy import Policy
from fusion.sustained_sessions import SustainedSessionStore
from fusion.inspection_continuation import Continuation,PROFILE
from fusion.preview_inspect import Client
from fusion.preview_tools import SessionAuthority


def invoke(config,state,run,credential,q):
    require(type(q) is dict and set(q)=={'profile','id','operation','session','occurrence','identity'} and len(canonical(q))<=4096)
    require(q['profile']==PROFILE,'UNSUPPORTED_PROFILE')
    operation=q['operation'];require(operation in ('observe','cancel','unsubscribe'),'UNSUPPORTED_OPERATION')
    uid(q['session']);uid(q['occurrence']);require(type(q['id']) is str and 1<=len(q['id'])<=128)
    require((q['identity'] is None) if operation=='observe' else type(q['identity']) is str)
    policy=Policy(config);actor=policy.authenticate(credential);cfg=policy.current()['native_sessions']
    def authorize(who,scope,action):
        require(policy.authenticate(credential)==actor and who==cfg['principal'],'UNAUTHORIZED')
        policy.check(actor,scope,'sessions.observe');policy.check(actor,scope,'sessions.disclose')
        if operation!='observe':policy.check(actor,scope,'sessions.cancel')
    store=SustainedSessionStore(cfg['database'],authorize,cfg['allocation'])
    try:allocation=store.allocated(cfg['principal'],q['session'])
    finally:store.close()
    authorize(cfg['principal'],allocation['frozen']['scope'],'observe')
    root=Path(state)/'sessions'/q['session'];database=root/'caller.sqlite';runtime=Path(run)/'sessions'/q['session']
    require(not root.is_symlink() and not database.is_symlink() and not runtime.is_symlink(),'UNAUTHORIZED')
    require(database.is_file(),'NOT_AVAILABLE')
    if not (runtime/'application.json').is_file():
        # Completed sessions are not redispatched after restart. Recover only
        # the accepted source-checked configuration, as for chain observation;
        # no Application, native worker or effect is constructed here.
        from .sustained_runtime import materialize
        materialize(config,Path(state),Path(run),q['session'])
    require((runtime/'application.json').is_file(),'NOT_AVAILABLE')
    app=json.loads((runtime/'application.json').read_bytes())
    require(app['session_id']==q['session'] and app['preview']['scope']==allocation['frozen']['scope'],'CONFLICT')
    def permit(action):
        authorize(cfg['principal'],allocation['frozen']['scope'],'observe')
        raw=json.loads(Path(app['preview']['authority_file']).read_bytes())
        authority=SessionAuthority(**dict(raw,tools=frozenset(raw['tools'])))
        import time
        authority.check(cfg['principal'],time.time_ns()//1000000)
        require(authority.scope==allocation['frozen']['scope'] and 'inspect-atom' in authority.tools,'UNAUTHORIZED')
    permit('inspection');client=Client(app['inspect_config'])
    db=sqlite3.connect(database.resolve().as_uri()+('?mode=ro' if operation=='observe' else '?mode=rw'),uri=True,timeout=2)
    db.row_factory=sqlite3.Row
    try:
        require(db.execute("SELECT 1 FROM sqlite_master WHERE name='integrated_inspection_continuations'").fetchone() is not None,'NOT_AVAILABLE')
        row=db.execute('SELECT * FROM app_occurrences WHERE id=?',(q['occurrence'],)).fetchone();require(row is not None,'NOT_FOUND')
        owner=Continuation(SimpleNamespace(db=db,preview=SimpleNamespace(authorize=permit)),client.frozen,initialize=False)
        result=owner.observe(row) if operation=='observe' else owner.control(row,operation,q['identity'])
        turn=db.execute('SELECT projection FROM app_turns WHERE id=?',(row['turn'],)).fetchone()
        result['native_consumption']=dict(occurrence_captured=bool(row['done'] and row['result'] is not None),
            turn_captured=bool(turn and turn[0] is not None),next_context='NOT_INFERRED')
        permit('inspection')
        return dict(profile=PROFILE,id=q['id'],request_digest=digest(canonical(q)),actor=actor,value=result)
    finally:db.close()
