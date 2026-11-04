"""Incarnation fencing inside the existing native application inbox owner.

Only the trusted supervisor registers/retires a process. A worker uses its
current scoped credential AND the persisted incarnation. A pid is diagnostic,
never task identity. An interrupted assignment without a saved final projection
remains uncertain; registering a replacement cannot reissue that assignment.
"""
import json,time,uuid
from .contracts import canonical,require,digest
from .sustained_sessions import SustainedSessionStore,TERMINAL

PROFILE='session-bound-native-worker/1'
CONTROL='bounded-native-worker-control/1'
LIMITS=dict(profile=PROFILE,inputs=8,idle_ms=30000,lifetime_ms=900000,incarnations=128)


def selection(value):
    require(type(value) is dict and set(value)==set(LIMITS),'UNSUPPORTED_PROFILE')
    require(value['profile']==PROFILE,'UNSUPPORTED_PROFILE')
    for name,maximum in [('inputs',24),('idle_ms',60000),('lifetime_ms',1800000),('incarnations',256)]:
        require(type(value[name]) is int and 1<=value[name]<=maximum)
    require(value['idle_ms']<=value['lifetime_ms'])
    return value


class Workers:
    def __init__(self,path,authorize,allocation,limits,clock=lambda:time.time_ns()//1000000,hook=lambda _:None):
        self.authorize,self.clock,self.hook=authorize,clock,hook
        self.limits=selection(limits);self.active=None
        self.store=SustainedSessionStore(path,self._authorize,allocation,clock=clock,hook=hook)
        self.db=self.store.db
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS native_worker_epochs(
                incarnation TEXT PRIMARY KEY,session TEXT NOT NULL,state TEXT NOT NULL,
                created INTEGER NOT NULL,expires INTEGER NOT NULL,selection TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS native_worker_current(slot INTEGER PRIMARY KEY,incarnation TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS native_worker_assignments(
                session TEXT NOT NULL,input TEXT NOT NULL,incarnation TEXT NOT NULL,
                PRIMARY KEY(session,input));
            CREATE TABLE IF NOT EXISTS native_worker_controls(
                session TEXT PRIMARY KEY,mode TEXT NOT NULL,revision INTEGER NOT NULL);
        ''')

    def close(self):self.store.close()

    def _authorize(self,principal,scope,operation):
        self.authorize(principal,scope,operation)
        if self.active is not None:self._current(*self.active)

    def _current(self,principal,session,incarnation):
        row=self.db.execute('''SELECT e.* FROM native_worker_epochs e JOIN native_worker_current c
            ON e.incarnation=c.incarnation WHERE c.slot=1''').fetchone()
        require(row is not None and row['incarnation']==incarnation and row['session']==session,'CONFLICT')
        require(row['selection']==canonical(self.limits).decode(),'UNSUPPORTED_PROFILE')
        require(row['state'] not in ('stopped','uncertain'),'NOT_AVAILABLE')
        return row

    def register(self,principal,session,incarnation):
        """Supervisor only, after predecessor termination and before spawn."""
        require(str(uuid.UUID(incarnation))==incarnation)
        self.store.allocated(principal,session)
        with self.db:
            self.db.execute('BEGIN IMMEDIATE');now=self.store._now()
            require(not self.draining(session),'NOT_AVAILABLE')
            current=self.db.execute('''SELECT e.state FROM native_worker_epochs e JOIN native_worker_current c
                ON e.incarnation=c.incarnation WHERE c.slot=1''').fetchone()
            require(current is None or current['state'] in ('stopped','uncertain'),'NOT_AVAILABLE')
            # Neither a new incarnation nor a fresh operator request clears
            # an uncertain original input. Reconcile saved final captures first.
            require(not self.db.execute("SELECT 1 FROM preview_inputs WHERE session=? AND state IN ('dispatched','needs-reconciliation','cancel-requested')",(session,)).fetchone(),'NOT_AVAILABLE')
            require(self.db.execute('SELECT count(*) FROM native_worker_epochs').fetchone()[0]<self.limits['incarnations'],'OVERLOADED')
            allocated=self.store.allocated(principal,session)
            require(now<allocated['expires_ms'],'DEADLINE_EXCEEDED')
            self.db.execute('INSERT INTO native_worker_epochs VALUES(?,?,?,?,?,?)',
                (incarnation,session,'prepared',now,min(now+self.limits['lifetime_ms'],allocated['expires_ms']),canonical(self.limits).decode()))
            self.db.execute('INSERT INTO native_worker_current VALUES(1,?) ON CONFLICT(slot) DO UPDATE SET incarnation=excluded.incarnation',(incarnation,))
            self.store._check_bytes()
        self.hook('after_worker_registration_commit')
        return dict(profile=PROFILE,session=session,incarnation=incarnation,state='prepared')

    def draining(self,session):
        row=self.db.execute('SELECT mode FROM native_worker_controls WHERE session=?',(session,)).fetchone()
        return bool(row and row[0]=='draining')

    def control(self,principal,session,operation,identity=None):
        """Operator-requested fences, never a kill, retry, lease or budget reset."""
        from .sustained_sessions import identity as key,MAX_ACTIONS
        require(operation in ('observe','drain','recycle','resume'),'UNSUPPORTED_OPERATION')
        self.store.allocated(principal,session)
        if operation!='observe':
            key(identity);intent=canonical(dict(profile=CONTROL,operation=operation)).decode()
            with self.db:
                self.db.execute('BEGIN IMMEDIATE');self.store.allocated(principal,session)
                old=self.db.execute('SELECT intent,result FROM sustained_actions WHERE session=? AND id=?',(session,identity)).fetchone()
                if old:require(old[0]==intent,'CONFLICT');return json.loads(old[1])
                require(self.db.execute('SELECT count(*) FROM sustained_actions').fetchone()[0]<MAX_ACTIONS,'OVERLOADED')
                now=self.store._now()
                prior=self.db.execute('SELECT revision FROM native_worker_controls WHERE session=?',(session,)).fetchone()
                revision=1+(prior[0] if prior else 0);mode='enabled' if operation=='resume' else 'draining'
                current=self.db.execute('SELECT e.incarnation FROM native_worker_epochs e JOIN native_worker_current c ON e.incarnation=c.incarnation WHERE e.session=?',(session,)).fetchone()
                self.db.execute('INSERT INTO native_worker_controls VALUES(?,?,?) ON CONFLICT(session) DO UPDATE SET mode=excluded.mode,revision=excluded.revision',(session,mode,revision))
                result=dict(profile=CONTROL,session=session,identity=identity,operation=operation,mode=mode,revision=revision,
                    observed_ms=now,target_incarnation=current[0] if current else None,inflight='PERMITTED_OR_UNCERTAIN_UNTIL_OWNER_CAPTURE',
                    retirement='SAFE_COMMITTED_BOUNDARY_ONLY',deadlines_reset=False,effect_budget_refund=False,automatic_resubmission=False)
                self.db.execute('INSERT INTO sustained_actions VALUES(?,?,?,?)',(session,identity,intent,canonical(result).decode()))
                self.store._check_bytes()
            self.hook('after_worker_control_commit');return result
        require(identity is None)
        row=self.db.execute('SELECT mode,revision FROM native_worker_controls WHERE session=?',(session,)).fetchone()
        current=self.db.execute('SELECT e.incarnation,e.state,e.expires FROM native_worker_epochs e JOIN native_worker_current c ON e.incarnation=c.incarnation WHERE e.session=?',(session,)).fetchone()
        uncertain=self.db.execute("SELECT count(*) FROM preview_inputs WHERE session=? AND state IN ('dispatched','needs-reconciliation','cancel-requested')",(session,)).fetchone()[0]
        return dict(profile=CONTROL,session=session,mode=row[0] if row else 'enabled',revision=row[1] if row else 0,
            current=dict(current) if current else None,unresolved_assignments=uncertain,retirement='SAFE_COMMITTED_BOUNDARY_ONLY',
            deadlines_reset=False,effect_budget_refund=False,automatic_resubmission=False)

    def other_eligible(self,session,now):
        # Same application owner, bounded retained inbox. No other session
        # identity/count crosses the worker port. Rotation only at idle state.
        return self.db.execute("""SELECT 1 FROM preview_inputs i JOIN preview_sessions s ON i.session=s.id
            JOIN sustained_allocations a ON a.session=s.id
            LEFT JOIN native_worker_controls c ON c.session=s.id
            WHERE s.id!=? AND s.state='active' AND i.state='accepted' AND i.deadline>? AND a.expires>?
            AND (c.mode IS NULL OR c.mode='enabled') AND NOT EXISTS
            (SELECT 1 FROM preview_inputs u WHERE u.session=s.id AND u.state IN ('dispatched','needs-reconciliation','cancel-requested')) LIMIT 1""",(session,now,now)).fetchone() is not None

    def retire(self,principal,session,incarnation):
        """Supervisor only, after the actual process has terminated."""
        self.store.allocated(principal,session)
        with self.db:
            self.db.execute('BEGIN IMMEDIATE');self._current(principal,session,incarnation)
            # Include a crash between input dispatch and assignment commits.
            pending=self.db.execute("SELECT 1 FROM preview_inputs WHERE session=? AND state IN ('dispatched','needs-reconciliation','cancel-requested')",(session,)).fetchone()
            state='uncertain' if pending else 'stopped'
            self.db.execute('UPDATE native_worker_epochs SET state=? WHERE incarnation=?',(state,incarnation))
        return dict(state=state,accounting_retained=True)

    def invoke(self,principal,session,incarnation,operation,body):
        try:return self._invoke(principal,session,incarnation,operation,body)
        finally:self.active=None

    def _invoke(self,principal,session,incarnation,operation,body):
        require(type(body) is dict)
        self.active=(principal,session,incarnation)
        self.store.allocated(principal,session)
        row=self._current(principal,session,incarnation)
        if operation=='ready':
            require(not body)
            with self.db:
                self.db.execute('BEGIN IMMEDIATE');row=self._current(principal,session,incarnation)
                require(row['state'] in ('prepared','idle'),'CONFLICT')
                require(self.clock()<row['expires'],'DEADLINE_EXCEEDED')
                self.db.execute("UPDATE native_worker_epochs SET state='idle' WHERE incarnation=?",(incarnation,))
            self.hook('after_worker_ready_commit')
            return dict(incarnation=incarnation,state='idle')
        if operation=='next':
            require(not body and row['state'] in ('idle','running'),'NOT_AVAILABLE')
            now=self.clock();require(type(now) is int and row['created']<=now,'CONFLICT')
            count=self.db.execute('SELECT count(*) FROM native_worker_assignments WHERE incarnation=?',(incarnation,)).fetchone()[0]
            waiting_here=self.db.execute("SELECT 1 FROM preview_inputs WHERE session=? AND state='accepted' AND deadline>? LIMIT 1",(session,now)).fetchone() is not None
            yield_to_other=self.other_eligible(session,now) and (count>0 or not waiting_here)
            if row['state']=='idle' and (now>=row['expires'] or count>=self.limits['inputs'] or self.draining(session) or yield_to_other):
                return dict(state='retire',input=None)
            require(now<row['expires'],'DEADLINE_EXCEEDED')
            value=self.store.next_input(principal,session)
            if value is None:return dict(state='idle',input=None)
            with self.db:
                self.db.execute('BEGIN IMMEDIATE');self._current(principal,session,incarnation)
                previous=self.db.execute('SELECT incarnation FROM native_worker_assignments WHERE session=? AND input=?',(session,value['id'])).fetchone()
                require(previous is None or previous[0]==incarnation,'CONFLICT')
                self.db.execute('INSERT OR IGNORE INTO native_worker_assignments VALUES(?,?,?)',(session,value['id'],incarnation))
                self.db.execute("UPDATE native_worker_epochs SET state='running' WHERE incarnation=?",(incarnation,))
                self.store._check_bytes()
            self.hook('after_worker_assignment_commit')
            return dict(state='running',input=value)
        require(operation in ('permit','complete'),'UNSUPPORTED_OPERATION')
        require(set(body)==({'identity'} if operation=='permit' else {'identity','result'}))
        assigned=self.db.execute('SELECT incarnation FROM native_worker_assignments WHERE session=? AND input=?',(session,body['identity'])).fetchone()
        old=self.db.execute('SELECT state,result FROM preview_inputs WHERE session=? AND id=?',(session,body['identity'])).fetchone()
        saved_replay=operation=='complete' and old is not None and old['state']=='complete' and old['result']==canonical(body['result']).decode()
        require(saved_replay or assigned is not None and assigned[0]==incarnation,'CONFLICT')
        if operation=='permit':
            require(self.clock()<row['expires'],'DEADLINE_EXCEEDED')
            return self.store.permit(principal,session,body['identity'])
        value=self.store.complete(principal,session,body['identity'],body['result'])
        with self.db:
            self.db.execute('BEGIN IMMEDIATE');self._current(principal,session,incarnation)
            self.db.execute("UPDATE native_worker_epochs SET state='idle' WHERE incarnation=?",(incarnation,))
        return value


class Ports:
    def __init__(self,path,hook=lambda _:None):self.path,self.hook=path,hook

    def invoke(self,credential,request):
        from .policy import Policy
        require(type(request) is dict and set(request)=={'id','profile','operation','session','incarnation','body'})
        require(request['profile']==PROFILE,'UNSUPPORTED_PROFILE')
        require(type(request['id']) is str and 1<=len(request['id'])<=128)
        require(request['operation'] in ('ready','next','permit','complete'),'UNSUPPORTED_OPERATION')
        require(len(canonical(request))<=(98304 if request['operation']=='complete' else 16384),'OVERLOADED')
        policy=Policy(self.path);cfg=policy.current()['native_sessions'];actor=policy.authenticate(credential)
        require(actor=='worker','UNAUTHORIZED');limits=selection(cfg['resident_worker']);principal=cfg['principal']
        permission='sessions.worker-ready' if request['operation']=='ready' else 'sessions.'+request['operation']
        def authorize(who,scope,operation):
            require(policy.authenticate(credential)==actor and who==principal,'UNAUTHORIZED')
            policy.check(actor,scope,permission)
        owner=Workers(cfg['database'],authorize,cfg['allocation'],limits,hook=self.hook)
        try:value=owner.invoke(principal,request['session'],request['incarnation'],request['operation'],request['body'])
        finally:owner.close()
        return dict(id=request['id'],profile=PROFILE,request_digest=digest(canonical(request)),actor=actor,principal=principal,value=value)


class Client:
    """Selected resident worker wire; same current credential and TLS checks."""
    def __init__(self,path,incarnation):
        from .preview_session_client import Client as SessionClient
        self.base=SessionClient(path);self.path=self.base.path;self.binding=self.base.binding
        require(self.binding['profile']=='omega-native-sessions/3' and self.binding['actor']=='worker','UNSUPPORTED_PROFILE')
        require(str(uuid.UUID(incarnation))==incarnation)
        self.incarnation=incarnation;self.limit_reached=False

    def invoke(self,operation,**body):
        from pathlib import Path
        cfg=json.loads(self.path.read_bytes());require({k:v for k,v in cfg.items() if k!='credential'}==self.binding,'CONFLICT')
        request=dict(id=str(uuid.uuid4()),profile=PROFILE,operation=operation,session=cfg['session'],incarnation=self.incarnation,body=body)
        if cfg['placement']=='local':reply=Ports(cfg['provider_config']).invoke(cfg['credential'],request)
        else:
            from .preview_transport import invoke
            require(digest(Path(cfg['endpoint']['ca_file']).read_bytes())==self.base.ca_hash,'CONFLICT')
            reply=invoke(cfg,'/preview/worker',request)
        require(type(reply) is dict and set(reply)=={'id','profile','request_digest','actor','principal','value'},'NOT_AVAILABLE')
        require((reply['id'],reply['profile'],reply['request_digest'],reply['actor'],reply['principal'])==
            (request['id'],PROFILE,digest(canonical(request)),cfg['actor'],cfg['principal']),'NOT_AVAILABLE')
        value=reply['value']
        if operation=='next':
            require(type(value) is dict and set(value)=={'state','input'} and value['state'] in ('idle','running','retire'),'NOT_AVAILABLE')
            require((value['input'] is None)==(value['state']!='running'),'NOT_AVAILABLE')
            self.limit_reached=value['state']=='retire';return value['input']
        return value
