"""Observation-only application owner over restored /3 records.

The frozen source bindings are returned as history, never rebound to the clone's
endpoints or authorized for execution. Fresh credentials govern read release.
The connection is SQLite read-only and no allocator/worker is constructed.
"""
import json,sqlite3
from pathlib import Path
from .contracts import require,canonical,digest
from .policy import Policy
from .sustained_sessions import SustainedSessionStore,PROFILE


class Snapshot(SustainedSessionStore):
    def __init__(self,path,authorize,allocation):
        self.allocation=allocation;self.authorize=authorize;self.profile=PROFILE
        self.db=sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True,timeout=2)
        self.db.row_factory=sqlite3.Row;self.db.execute('PRAGMA query_only=ON');self.db.execute('BEGIN')
        require(self.db.execute('SELECT profile FROM preview_session_profile').fetchone()[0]==PROFILE,'UNSUPPORTED_PROFILE')
        require(self.db.execute('SELECT owner FROM sustained_seal').fetchone()[0]==allocation['owner'],'CONFLICT')
    def allocated(self,principal,session):
        self._session(principal,session,'session.read')
        row=self.db.execute('SELECT * FROM sustained_allocations WHERE session=?',(session,)).fetchone()
        require(row is not None,'NOT_FOUND')
        frozen=json.loads(row['frozen']);require(frozen['principal']==principal,'UNAUTHORIZED')
        # Selected scopes/principals still require fresh clone authority. The
        # original runtime digest is evidence, never a grant to resume old work.
        require(any(x['principal']==principal and x['scope']==frozen['scope'] for x in self.allocation['templates'].values()),'UNAUTHORIZED')
        return dict(session=session,allocation_id=row['id'],template=row['template'],frozen=frozen,expires_ms=row['expires'])


class Ports:
    def __init__(self,path):self.path=Path(path)
    def invoke(self,credential,q):
        require(type(q) is dict and set(q)=={'id','profile','operation','body'})
        require(q['profile']==PROFILE,'UNSUPPORTED_PROFILE')
        require(q['operation'] in ('observe','list','capacity'),'UNAUTHORIZED')
        require(type(q['body']) is dict and type(q['id']) is str and 1<=len(q['id'])<=128)
        policy=Policy(self.path);cfg=policy.current()['native_sessions'];actor=policy.authenticate(credential)
        require(actor=='operator','UNAUTHORIZED')
        def authorize(principal,scope,op):
            require(policy.authenticate(credential)==actor and principal==cfg['principal'],'UNAUTHORIZED')
            policy.check(actor,scope,'sessions.'+q['operation'])
            if op=='session.disclose':policy.check(actor,scope,'sessions.disclose')
        store=Snapshot(cfg['database'],authorize,cfg['allocation'])
        try:
            if q['operation']=='observe':
                require(set(q['body']) in ({'session','content'},{'session','content','after'}) and type(q['body']['content']) is bool)
                value=store.observe(cfg['principal'],q['body']['session'],q['body']['content'],after=q['body'].get('after',0))
                value.update(restore_fenced=True,execution_authorized=False,original_bindings_retained=True)
            else:
                require(q['body']=={})
                value=store.list_sessions(cfg['principal']) if q['operation']=='list' else dict(store.capacity(cfg['principal']),
                    restore_fenced=True,execution_authorized=False,capacity_is_not_execution_credit=True)
            return dict(id=q['id'],profile=PROFILE,request_digest=digest(canonical(q)),actor=actor,principal=cfg['principal'],value=value)
        finally:store.close()
