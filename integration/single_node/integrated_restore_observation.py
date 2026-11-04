"""Read saved continuation evidence in a fenced clone under fresh authority.

Original endpoint/CA/approval bindings remain historical evidence. No client,
executor, workflow initializer or live authority is reconstructed from them.
Only the two known application continuation observers are used, with read-only
SQLite and their original capture validation. Mutation routes stay closed.
"""
import json,sqlite3
from pathlib import Path
from types import SimpleNamespace
from fusion.contracts import canonical,digest,require
from fusion.lookup_contracts import identity as uid
from fusion.policy import Policy
from fusion.sustained_restore import Snapshot
from fusion.inspection_continuation import Continuation as Inspection,PROFILE as INSPECT
from fusion.chain_continuation import Continuation as Chain,PROFILE as CHAIN


def observe_database(db,profile,occurrence,authorize):
    """Already authorized owner-local read; this function cannot perform I/O."""
    authorize('observe');require(profile in (INSPECT,CHAIN),'UNSUPPORTED_PROFILE')
    if profile==INSPECT:
        graph=db.execute('SELECT selection FROM integrated_inspection_continuations WHERE occurrence=?',(occurrence,)).fetchone()
        require(graph is not None,'NOT_FOUND')
        row=db.execute('SELECT * FROM app_occurrences WHERE id=?',(occurrence,)).fetchone();require(row is not None,'NOT_FOUND')
        app=SimpleNamespace(db=db,preview=SimpleNamespace(authorize=authorize))
        value=Inspection(app,json.loads(graph[0]),initialize=False).observe(row)
        turn=db.execute('SELECT projection FROM app_turns WHERE id=?',(row['turn'],)).fetchone()
        value['native_consumption']=dict(occurrence_captured=bool(row['done'] and row['result'] is not None),
            turn_captured=bool(turn and turn[0] is not None),next_context='NOT_INFERRED')
    else:
        row=db.execute('SELECT binding FROM integrated_chain_continuations WHERE occurrence=?',(occurrence,)).fetchone()
        require(row is not None,'NOT_FOUND');binding=json.loads(row[0])
        # Deliberately no call/submit/observe methods: a retained binding is not
        # a network client, even when its old exact approval has not expired.
        client=SimpleNamespace(frozen=row[0].encode(),reg=binding['registration'])
        value=Chain(db,client,authorize,initialize=False).observe(occurrence)
    authorize('observe');return value


def invoke(config,state,credential,q):
    require(type(q) is dict and q.get('operation')=='observe','UNAUTHORIZED')
    require(q.get('profile') in (INSPECT,CHAIN),'UNSUPPORTED_PROFILE')
    if q['profile']==INSPECT:require(set(q)=={'profile','id','operation','session','occurrence','identity'} and q['identity'] is None)
    else:require(set(q)=={'profile','id','operation','session','occurrence','body'} and q['body']=={})
    require(len(canonical(q))<=4096 and type(q['id']) is str and 1<=len(q['id'])<=128)
    uid(q['session']);uid(q['occurrence']);state=Path(state)
    fence=json.loads((state/'restore-fence.json').read_bytes())
    require(fence['mode']=='READ_ONLY_RECONCILIATION' and fence['external_effect_authority'] is False,'UNAUTHORIZED')
    policy=Policy(config);cfg=policy.current()['native_sessions'];actor=policy.authenticate(credential)
    require(actor=='operator','UNAUTHORIZED')
    def authorize(who,scope,action):
        require(policy.authenticate(credential)==actor and who==cfg['principal'],'UNAUTHORIZED')
        for verb in ('observe','disclose'):policy.check(actor,scope,'sessions.'+verb)
    store=Snapshot(cfg['database'],authorize,cfg['allocation'])
    try:allocation=store.allocated(cfg['principal'],q['session'])
    finally:store.close()
    def permit(_):authorize(cfg['principal'],allocation['frozen']['scope'],'observe')
    permit('observe');root=state/'sessions'/q['session'];path=root/'caller.sqlite'
    require(not root.is_symlink() and path.is_file() and not path.is_symlink(),'NOT_AVAILABLE')
    db=sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True,timeout=2)
    try:
        db.row_factory=sqlite3.Row;db.execute('PRAGMA query_only=ON');db.execute('BEGIN')
        value=observe_database(db,q['profile'],q['occurrence'],permit)
        value.update(restore_fenced=True,execution_authorized=False,original_bindings_retained=True,retained_approval_is_current_authority=False)
        require(len(canonical(value))<=65536,'OVERLOADED')
        return dict(profile=q['profile'],id=q['id'],request_digest=digest(canonical(q)),actor=actor,value=value)
    finally:db.close()
