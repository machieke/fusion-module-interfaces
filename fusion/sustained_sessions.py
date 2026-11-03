"""Fresh /3 application inbox: allocation, dispatch fencing and terminal records.

The application remains the only owner. This is not an effect executor or a
cross-owner transaction. A dispatch marker means effects may exist; only the
trusted native worker can report its already committed projection. Reconcile
never launches a child, calls a provider, or treats uncertainty as absence.
"""
import json
import time
import uuid

from .contracts import canonical, digest, require
from .lookup_contracts import identity as uid
from .preview_sessions import SessionStore, MAX_INPUTS, MAX_PENDING, MAX_INPUT_WINDOW_MS

PROFILE = 'omega-native-sessions/3'
ALLOCATION = 'bounded-native-session-allocation/1'
ORDERING = 'causal-session-fence/1'
TERMINAL = ('complete', 'expired-before-start', 'cancelled-before-start', 'rejected')
UNCERTAIN = ('dispatched', 'cancel-requested', 'needs-reconciliation')
MAX_TEMPLATES = 4
MAX_RETAINED = 16
MAX_ACTIONS = 512


def identity(value):
    require(type(value) is str and 1 <= len(value.encode()) <= 128 and '\x00' not in value)
    return value


def allocation_policy(value):
    require(type(value) is dict and set(value) == {'profile', 'owner', 'active', 'retained', 'pending', 'bytes', 'templates'})
    require(value['profile'] == ALLOCATION, 'UNSUPPORTED_PROFILE')
    uid(value['owner'])
    for key, maximum in (('active', 4), ('retained', MAX_RETAINED), ('pending', 32), ('bytes', 8*1024*1024)):
        require(type(value[key]) is int and 1 <= value[key] <= maximum)
    require(value['active'] <= value['retained'])
    require(type(value['templates']) is dict and 1 <= len(value['templates']) <= MAX_TEMPLATES)
    for name, template in value['templates'].items():
        identity(name)
        require(type(template) is dict and set(template) == {'principal', 'scope', 'binding', 'lifetime_ms', 'runtime_digest'})
        identity(template['principal'])
        require(type(template['scope']) is str and template['scope'].startswith('synthetic-'), 'UNAUTHORIZED')
        require(type(template['lifetime_ms']) is int and 1 <= template['lifetime_ms'] <= 7*86400000)
        require(type(template['runtime_digest']) is str and len(template['runtime_digest']) == 64)
        require(all(c in '0123456789abcdef' for c in template['runtime_digest']))
        binding = template['binding']
        require(type(binding) is dict and set(binding) == {'catalogue', 'policy', 'model_boundary', 'limits'})
        require(binding['model_boundary'] in ('RECORDED_FIXTURE', 'LIVE_APPROVAL_REQUIRED'), 'UNSUPPORTED_PROFILE')
        identity(binding['catalogue']); identity(binding['policy'])
        limits = binding['limits']
        require(type(limits) is dict and set(limits) == {'inputs', 'pending', 'timeout_ms'})
        for key, maximum in (('inputs', MAX_INPUTS), ('pending', MAX_PENDING), ('timeout_ms', MAX_INPUT_WINDOW_MS)):
            require(type(limits[key]) is int and 1 <= limits[key] <= maximum)
    require(len(canonical(value)) <= 32768, 'OVERLOADED')
    return value


class SustainedSessionStore(SessionStore):
    def __init__(self, path, authorize, allocation, clock=lambda: time.time_ns()//1000000, hook=lambda _: None):
        self.allocation = allocation_policy(allocation)
        self.hook = hook
        super().__init__(path, authorize, clock, profile=PROFILE)
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS sustained_seal(owner TEXT NOT NULL, clock INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS sustained_allocations(
                principal TEXT NOT NULL, id TEXT NOT NULL, template TEXT NOT NULL,
                frozen TEXT NOT NULL, session TEXT UNIQUE NOT NULL, expires INTEGER NOT NULL,
                PRIMARY KEY(principal,id));
            CREATE TABLE IF NOT EXISTS sustained_dispatch(
                session TEXT NOT NULL, id TEXT NOT NULL, started INTEGER NOT NULL,
                PRIMARY KEY(session,id));
            CREATE TABLE IF NOT EXISTS sustained_outcomes(
                session TEXT NOT NULL, id TEXT NOT NULL, value TEXT NOT NULL,
                PRIMARY KEY(session,id));
            CREATE TABLE IF NOT EXISTS sustained_actions(
                session TEXT NOT NULL, id TEXT NOT NULL, intent TEXT NOT NULL, result TEXT NOT NULL,
                PRIMARY KEY(session,id));
        ''')
        with self.db:
            old = self.db.execute('SELECT owner FROM sustained_seal').fetchone()
            require(old is None or old[0] == allocation['owner'], 'CONFLICT')
            if old is None:
                self.db.execute('INSERT INTO sustained_seal VALUES(?,0)', (allocation['owner'],))

    def create(self, *args, **kwargs):
        require(False, 'UNSUPPORTED_OPERATION')  # /2 remains the exact-ID profile.

    def _now(self):
        now = self.clock()
        old = self.db.execute('SELECT clock FROM sustained_seal').fetchone()[0]
        require(type(now) is int and 0 <= old <= now, 'CONFLICT')
        self.db.execute('UPDATE sustained_seal SET clock=?', (now,))
        return now

    def _usage(self):
        # Logical retained bytes, not a claim about SQLite/PVC physical bytes.
        sizes = [self.db.execute(sql).fetchone()[0] or 0 for sql in (
            'SELECT sum(length(CAST(binding AS BLOB))) FROM preview_sessions',
            'SELECT sum(length(CAST(intent AS BLOB))+coalesce(length(CAST(result AS BLOB)),0)) FROM preview_inputs',
            'SELECT sum(length(CAST(frozen AS BLOB))) FROM sustained_allocations',
            'SELECT sum(length(CAST(value AS BLOB))) FROM sustained_outcomes',
            'SELECT sum(length(CAST(origin AS BLOB))) FROM preview_input_origins',
            'SELECT sum(length(CAST(intent AS BLOB))+length(CAST(result AS BLOB))) FROM sustained_actions')]
        # Reserve the maximum completion/terminal envelope at input acceptance.
        reserved = self.db.execute("SELECT count(*) FROM preview_inputs WHERE state NOT IN ('complete','expired-before-start','cancelled-before-start','rejected')").fetchone()[0]*66560
        return dict(retained=self.db.execute('SELECT count(*) FROM preview_sessions').fetchone()[0],
            active=self.db.execute("SELECT count(*) FROM preview_sessions WHERE state IN ('active','paused')").fetchone()[0],
            pending=self.db.execute("SELECT count(*) FROM preview_inputs WHERE state NOT IN ('complete','expired-before-start','cancelled-before-start','rejected')").fetchone()[0],
            logical_bytes=sum(sizes), completion_reserved_bytes=reserved)

    def allocate(self, principal, request_id, template_name):
        identity(request_id); identity(template_name)
        template = self.allocation['templates'].get(template_name)
        require(template is not None and template['principal'] == principal, 'UNAUTHORIZED')
        self.authorize(principal, template['scope'], 'session.allocate')
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            old = self.db.execute('SELECT * FROM sustained_allocations WHERE principal=? AND id=?', (principal, request_id)).fetchone()
            if old:
                require(old['template'] == template_name and old['frozen'] == canonical(template).decode(), 'CONFLICT')
                session = old['session']
            else:
                now = self._now(); usage = self._usage()
                require(usage['active'] < self.allocation['active'] and usage['retained'] < self.allocation['retained'], 'OVERLOADED')
                require(usage['pending'] < self.allocation['pending'], 'OVERLOADED')
                require(usage['logical_bytes']+usage['completion_reserved_bytes']+2*len(canonical(template))+4096 <= self.allocation['bytes'], 'OVERLOADED')
                session = str(uuid.uuid5(uuid.UUID(self.allocation['owner']), canonical([principal, request_id]).decode()))
                binding = template['binding']
                self.db.execute('INSERT INTO preview_sessions VALUES(?,?,?,?,?,?)',
                    (session, principal, template['scope'], canonical(binding).decode(), 'active', now))
                self.db.execute('INSERT INTO sustained_allocations VALUES(?,?,?,?,?,?)',
                    (principal, request_id, template_name, canonical(template).decode(), session, now+template['lifetime_ms']))
        self.hook('after_session_allocation_commit')
        return self.observe(principal, session)

    def _check_bytes(self):
        usage=self._usage()
        require(usage['logical_bytes']+usage['completion_reserved_bytes']<=self.allocation['bytes'],'OVERLOADED')

    def allocated(self, principal, session):
        self._session(principal, session, 'session.read')
        row = self.db.execute('SELECT * FROM sustained_allocations WHERE session=?', (session,)).fetchone()
        require(row is not None, 'NOT_FOUND')
        frozen = json.loads(row['frozen'])
        require(self.allocation['templates'].get(row['template']) == frozen, 'CONFLICT')
        return dict(session=session, allocation_id=row['id'], template=row['template'],
                    frozen=frozen, expires_ms=row['expires'])

    def capacity(self, principal):
        templates = [t for t in self.allocation['templates'].values() if t['principal'] == principal]
        require(templates, 'UNAUTHORIZED')
        for t in templates: self.authorize(principal, t['scope'], 'session.capacity')
        value = self._usage()
        value.update(limits={k:self.allocation[k] for k in ('active','retained','pending','bytes')},
            physical_bytes='NOT_INFERRED_FROM_LOGICAL_ACCOUNTING', no_effect_budget_refunds=True)
        return value

    def list_sessions(self, principal):
        self.capacity(principal)
        return [dict(session=r['id'], state=r['state'], scope=r['scope']) for r in
                self.db.execute('SELECT * FROM preview_sessions WHERE principal=? ORDER BY created,id', (principal,))]

    def _outcome(self, session, input_id, state, now, knowledge):
        outcome = dict(state=state, observed_ms=now, effects=knowledge, execution_authorized=False,
                       original_accounting_retained=True, ordering=ORDERING)
        self.db.execute('UPDATE preview_inputs SET state=? WHERE session=? AND id=?', (state, session, input_id))
        self.db.execute('INSERT INTO sustained_outcomes VALUES(?,?,?) ON CONFLICT(session,id) DO UPDATE SET value=excluded.value',
                        (session, input_id, canonical(outcome).decode()))
        return outcome

    def _expire(self, principal, session, now):
        self._session(principal, session, 'input.reconcile')
        rows = self.db.execute("SELECT * FROM preview_inputs WHERE session=? AND deadline<=? AND state IN ('accepted','dispatched') ORDER BY sequence", (session, now)).fetchall()
        require(len(rows) <= MAX_INPUTS, 'OVERLOADED')
        for row in rows:
            if row['state'] == 'accepted':
                require(self.db.execute('SELECT 1 FROM sustained_dispatch WHERE session=? AND id=?',(session,row['id'])).fetchone() is None, 'CONFLICT')
                self._outcome(session,row['id'],'expired-before-start',now,'NO_DISPATCH')
            else:
                self._outcome(session,row['id'],'needs-reconciliation',now,'UNKNOWN_AFTER_DISPATCH')

    def reconcile(self, principal, session):
        self._session(principal, session, 'input.reconcile')
        with self.db:
            self.db.execute('BEGIN IMMEDIATE'); self._expire(principal,session,self._now())
        self.hook('after_input_terminalization_commit')
        return self.observe(principal,session)

    def submit(self, principal, session, identity_, text, assignment, *, deadline_ms=None):
        identity(identity_)
        require(type(text) is str and 0 < len(text.encode()) <= 4096 and '\x00' not in text)
        identity(assignment)
        self._session(principal, session, 'input.accept')
        intent = canonical(dict(text=text,assignment=assignment)).decode()
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            old=self.db.execute('SELECT * FROM preview_inputs WHERE session=? AND id=?',(session,identity_)).fetchone()
            if old:
                require(old['intent']==intent and (deadline_ms is None or old['deadline']==deadline_ms),'CONFLICT')
                return self.receipt(old)
            row=self._session(principal,session,'input.accept'); allocated=self.allocated(principal,session)
            now=self._now(); require(row['state']=='active' and now<allocated['expires_ms'],'NOT_AVAILABLE')
            limits=json.loads(row['binding'])['limits']; usage=self._usage()
            count=self.db.execute('SELECT count(*) FROM preview_inputs WHERE session=?',(session,)).fetchone()[0]
            pending=self.db.execute("SELECT count(*) FROM preview_inputs WHERE session=? AND state NOT IN ('complete','expired-before-start','cancelled-before-start','rejected')",(session,)).fetchone()[0]
            require(count<limits['inputs'] and pending<limits['pending'] and usage['pending']<self.allocation['pending'],'OVERLOADED')
            require(usage['logical_bytes']+usage['completion_reserved_bytes']+len(intent.encode())+66560<=self.allocation['bytes'],'OVERLOADED')
            deadline=min(now+limits['timeout_ms'],allocated['expires_ms']) if deadline_ms is None else deadline_ms
            require(type(deadline) is int and now<deadline<=min(now+limits['timeout_ms'],allocated['expires_ms']),'DEADLINE_EXCEEDED')
            self.db.execute('INSERT INTO preview_inputs VALUES(?,?,?,?,?,?,?,NULL,?)',
                (session,identity_,count+1,intent,assignment,deadline,'accepted',now))
        self.hook('after_input_acceptance_commit')
        return self.receipt(self.db.execute('SELECT * FROM preview_inputs WHERE session=? AND id=?',(session,identity_)).fetchone())

    def next_input(self, principal, session):
        self._session(principal,session,'input.consume')
        # Terminal observations commit even when a later unknown effect fences
        # dispatch. Raising the fence inside that transaction would undo them.
        with self.db:
            self.db.execute('BEGIN IMMEDIATE'); self._expire(principal,session,self._now())
        with self.db:
            self.db.execute('BEGIN IMMEDIATE'); now=self._now()
            owner=self._session(principal,session,'input.consume')
            require(owner['state']=='active','NOT_AVAILABLE')
            row=self.db.execute("SELECT * FROM preview_inputs WHERE session=? AND state NOT IN ('complete','expired-before-start','cancelled-before-start','rejected') ORDER BY sequence LIMIT 1",(session,)).fetchone()
            if row is None: return None
            # Unknown effects fence every subsequent context-dependent input.
            # Observation through observe/capacity/reconcile remains available.
            require(row['state'] in ('accepted','dispatched'),'NOT_AVAILABLE')
            require(now<row['deadline'],'DEADLINE_EXCEEDED')
            if row['state']=='accepted':
                self.db.execute('INSERT INTO sustained_dispatch VALUES(?,?,?)',(session,row['id'],now))
                self.db.execute("UPDATE preview_inputs SET state='dispatched' WHERE session=? AND id=?",(session,row['id']))
                row=self.db.execute('SELECT * FROM preview_inputs WHERE session=? AND id=?',(session,row['id'])).fetchone()
            value=dict(**self.receipt(row),payload=json.loads(row['intent']),occurrence=str(uuid.uuid5(uuid.UUID(session),row['id'])),session_binding=json.loads(owner['binding']))
            origin=self.db.execute('SELECT origin FROM preview_input_origins WHERE session=? AND id=?',(session,row['id'])).fetchone()
            if origin is not None:value['task_origin']=json.loads(origin[0])
        self.hook('after_input_dispatch_commit')
        return value

    def permit(self, principal, session, input_id):
        owner=self._session(principal,session,'input.consume')
        row=self.db.execute('SELECT * FROM preview_inputs WHERE session=? AND id=?',(session,input_id)).fetchone()
        require(row is not None,'NOT_FOUND')
        require(owner['state']=='active' and row['state']=='dispatched','NOT_AVAILABLE')
        now=self.clock(); previous=self.db.execute('SELECT clock FROM sustained_seal').fetchone()[0]
        require(type(now) is int and previous<=now,'CONFLICT')
        require(now<row['deadline'],'DEADLINE_EXCEEDED')
        return dict(identity=input_id,deadline=row['deadline'],authorized=True)

    def complete(self, principal, session, input_id, result):
        self._session(principal,session,'input.complete')
        require(type(result) is dict and set(result)=={'turn','projection','occurrences'})
        require(type(result['turn']) is int and 1<=result['turn']<=MAX_INPUTS and type(result['projection']) is str)
        require(type(result['occurrences']) is list and len(result['occurrences'])<=8 and all(type(x) is str for x in result['occurrences']))
        wire=canonical(result).decode(); require(len(wire.encode())<=65536)
        with self.db:
            self.db.execute('BEGIN IMMEDIATE'); now=self._now()
            row=self.db.execute('SELECT * FROM preview_inputs WHERE session=? AND id=?',(session,input_id)).fetchone()
            require(row is not None,'NOT_FOUND')
            require(row['state'] in UNCERTAIN+('complete',),'CONFLICT')
            require(self.db.execute('SELECT 1 FROM sustained_dispatch WHERE session=? AND id=?',(session,input_id)).fetchone() is not None,'CONFLICT')
            if row['result'] is not None:require(row['result']==wire,'CONFLICT')
            else:
                self.db.execute('UPDATE preview_inputs SET result=? WHERE session=? AND id=?',(wire,session,input_id))
                self._outcome(session,input_id,'complete',now,'NATIVE_PROJECTION_COMMITTED')
        self.hook('after_session_completion_commit')
        return dict(self.receipt(row),state='complete',result_digest=digest(wire.encode()))

    def cancel(self, principal, session, request_id, input_id):
        identity(request_id); identity(input_id); self._session(principal,session,'input.cancel')
        intent=canonical(dict(operation='cancel',identity=input_id)).decode()
        with self.db:
            self.db.execute('BEGIN IMMEDIATE'); old=self.db.execute('SELECT * FROM sustained_actions WHERE session=? AND id=?',(session,request_id)).fetchone()
            if old:
                require(old['intent']==intent,'CONFLICT'); return json.loads(old['result'])
            require(self.db.execute('SELECT count(*) FROM sustained_actions').fetchone()[0]<MAX_ACTIONS,'OVERLOADED')
            now=self._now(); row=self.db.execute('SELECT * FROM preview_inputs WHERE session=? AND id=?',(session,input_id)).fetchone()
            require(row is not None,'NOT_FOUND')
            if row['state']=='accepted':outcome=self._outcome(session,input_id,'cancelled-before-start',now,'NO_DISPATCH')
            elif row['state'] in UNCERTAIN:outcome=self._outcome(session,input_id,'cancel-requested',now,'UNKNOWN_AFTER_DISPATCH')
            else:outcome=dict(state=row['state'],effects='TERMINAL_RECORD_RETAINED',execution_authorized=False,original_accounting_retained=True)
            result=dict(session=session,identity=input_id,request_id=request_id,outcome=outcome,transmitted_effects_retracted=False)
            self.db.execute('INSERT INTO sustained_actions VALUES(?,?,?,?)',(session,request_id,intent,canonical(result).decode()))
            self._check_bytes()
        self.hook('after_input_cancellation_commit'); return result

    def control(self, principal, session, request_id, action):
        identity(request_id); require(action in ('pause','resume','close','archive'))
        self._session(principal,session,'session.control')
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            old=self.db.execute('SELECT * FROM sustained_actions WHERE session=? AND id=?',(session,request_id)).fetchone()
            intent=canonical(dict(operation=action)).decode()
            if old:
                require(old['intent']==intent,'CONFLICT');return json.loads(old['result'])
            require(self.db.execute('SELECT count(*) FROM sustained_actions').fetchone()[0]<MAX_ACTIONS,'OVERLOADED')
            now=self._now();row=self._session(principal,session,'session.control')
            if action=='archive':require(row['state']=='closed','CONFLICT')
            else:require(row['state'] not in ('closed','archived') or action=='close' and row['state']=='closed','CONFLICT')
            if action=='resume':
                require(now<self.allocated(principal,session)['expires_ms'],'NOT_AVAILABLE')
            state={'pause':'paused','resume':'active','close':'closed','archive':'archived'}[action]
            result=dict(session=session,state=state,transmitted_effects_retracted=False,accounting_retained=True)
            self.db.execute('UPDATE preview_sessions SET state=? WHERE id=?',(state,session))
            self.db.execute('INSERT INTO sustained_actions VALUES(?,?,?,?)',(session,request_id,intent,canonical(result).decode()))
            self._check_bytes()
        return result

    def observe(self, principal, session, include_content=False, *, after=0):
        value=super().observe(principal,session,include_content,after=after)
        pending=0; terminal=0
        for row in self.db.execute('SELECT state FROM preview_inputs WHERE session=?',(session,)):
            if row[0] in TERMINAL: terminal+=1
            else:pending+=1
        value['capacity'].update(pending=pending,terminal=terminal,
            remaining_pending=max(0,value['binding']['limits']['pending']-pending))
        value.update(profile=PROFILE,ordering=ORDERING,allocation=self.allocated(principal,session),
            observations_do_not_dispatch=True)
        # The allocation snapshot excludes executable paths/credentials by contract.
        for item in value['inputs']:
            row=self.db.execute('SELECT value FROM sustained_outcomes WHERE session=? AND id=?',(session,item['id'])).fetchone()
            item['outcome']=json.loads(row[0]) if row else None
        return value
