"""Registered application continuation over NativeInspection's existing commits.

No executor, planner, scheduler, transport, native process or cross-owner
transaction lives here. The native handler alone supplies typed captures. A
cursor is only a hint; a result still needs authoritative hydration/validation.
"""
import json
from .contracts import canonical,digest,require

PROFILE='bounded-native-inspection-continuation/1'
STEPS=('artifact','artifact_ref','request','acceptance','result','completion','ack')
DEFINITION=dict(profile=PROFILE,handler='native.inspect-artifact/1',
    nodes=list(STEPS)+['native-return'],edges=[[a,b] for a,b in zip(STEPS,STEPS[1:])]+[['ack','native-return']],
    limits=dict(nodes=8,edges=7,depth=8,inflight=1,relay_calls=32,logical_executions=1,output_bytes=8192),
    mappings='exact-retained-NativeInspection-captures/1',chain_authority='separate-exact-result-approval-required')


class Continuation:
    def __init__(self,app,selection,*,initialize=True):
        self.app,self.db,self.selection=app,app.db,selection
        if not initialize:return
        self.db.executescript('''CREATE TABLE IF NOT EXISTS integrated_inspection_continuations(
            occurrence TEXT PRIMARY KEY,definition TEXT NOT NULL,input TEXT NOT NULL,
            deadline INTEGER NOT NULL,selection TEXT NOT NULL,cancelled INTEGER NOT NULL DEFAULT 0,
            subscription INTEGER NOT NULL DEFAULT 1,cursor TEXT);
            CREATE TABLE IF NOT EXISTS integrated_inspection_steps(
            occurrence TEXT NOT NULL,step TEXT NOT NULL,inputs TEXT NOT NULL,capture_digest TEXT NOT NULL,
            PRIMARY KEY(occurrence,step));
            CREATE TABLE IF NOT EXISTS integrated_inspection_controls(
            occurrence TEXT NOT NULL,operation TEXT NOT NULL,identity TEXT NOT NULL,
            PRIMARY KEY(occurrence,operation));''')

    def admit(self,identity,task,deadline):
        require(self.db.in_transaction,'CONFLICT')
        require(self.db.execute('SELECT count(*) FROM integrated_inspection_continuations').fetchone()[0]<128,'OVERLOADED')
        self.db.execute('INSERT INTO integrated_inspection_continuations(occurrence,definition,input,deadline,selection) VALUES(?,?,?,?,?)',
            (identity,canonical(DEFINITION).decode(),canonical(dict(task=task)).decode(),deadline,canonical(self.selection).decode()))

    def state(self,row):
        self.app.preview.authorize('inspection')
        state=self.db.execute('SELECT * FROM integrated_inspection_continuations WHERE occurrence=?',(row['id'],)).fetchone()
        require(state is not None and state['definition']==canonical(DEFINITION).decode() and
            state['selection']==canonical(self.selection).decode() and state['deadline']==row['deadline'],'CONFLICT')
        return state

    def permit(self,row):
        state=self.state(row)
        require(not state['cancelled'],'NOT_AVAILABLE')

    def capture(self,row,step,value):
        require(step in STEPS and self.db.in_transaction,'CONFLICT')
        self.state(row);index=STEPS.index(step)
        parents={}
        if index:
            prior=self.db.execute('SELECT capture_digest FROM integrated_inspection_steps WHERE occurrence=? AND step=?',
                (row['id'],STEPS[index-1])).fetchone()
            require(prior is not None,'NOT_AVAILABLE');parents[STEPS[index-1]]=prior[0]
        encoded,fingerprint=canonical(parents).decode(),digest(canonical(value))
        old=self.db.execute('SELECT inputs,capture_digest FROM integrated_inspection_steps WHERE occurrence=? AND step=?',(row['id'],step)).fetchone()
        require(old is None or tuple(old)==(encoded,fingerprint),'CONFLICT')
        self.db.execute('INSERT OR IGNORE INTO integrated_inspection_steps VALUES(?,?,?,?)',(row['id'],step,encoded,fingerprint))

    def cursor(self,row):
        state=self.state(row)
        require(state['subscription'],'NOT_AVAILABLE')
        return json.loads(state['cursor']) if state['cursor'] else None

    def observe_commits(self,row,value):
        # Strict wire validation is performed by the client. This is a durable
        # consumption cursor, never permission to start a worker or an effect.
        require(not value['gap'],'NOT_AVAILABLE')
        with self.db:
            self.db.execute('BEGIN IMMEDIATE');state=self.state(row)
            require(state['subscription'],'NOT_AVAILABLE')
            old=json.loads(state['cursor']) if state['cursor'] else None
            require(old is None or (old['source']==value['source'] and old['next']==value['after']),'CONFLICT')
            self.db.execute('UPDATE integrated_inspection_continuations SET cursor=? WHERE occurrence=?',
                (canonical(value).decode(),row['id']))
        self.app.hook('after_inspect_cursor_capture')

    def control(self,row,operation,identity):
        require(operation in ('cancel','unsubscribe'),'UNSUPPORTED_OPERATION')
        require(type(identity) is str and 1<=len(identity)<=128)
        with self.db:
            self.db.execute('BEGIN IMMEDIATE');self.state(row)
            old=self.db.execute('SELECT identity FROM integrated_inspection_controls WHERE occurrence=? AND operation=?',(row['id'],operation)).fetchone()
            require(old is None or old[0]==identity,'CONFLICT')
            self.db.execute('INSERT OR IGNORE INTO integrated_inspection_controls VALUES(?,?,?)',(row['id'],operation,identity))
            self.db.execute('UPDATE integrated_inspection_continuations SET '+('cancelled=1' if operation=='cancel' else 'subscription=0')+' WHERE occurrence=?',(row['id'],))
        return self.observe(row)

    def observe(self,row):
        state=self.state(row)
        steps={x['step']:x['capture_digest'] for x in self.db.execute('SELECT * FROM integrated_inspection_steps WHERE occurrence=?',(row['id'],))}
        inspection=self.db.execute('SELECT * FROM preview_inspections WHERE occurrence=?',(row['id'],)).fetchone()
        for step,hash_value in steps.items():
            require(inspection[step] is not None and digest(canonical(json.loads(inspection[step])))==hash_value,'NOT_AVAILABLE')
        cursor=json.loads(state['cursor']) if state['cursor'] else None
        cancelled=bool(state['cancelled'])
        status='return-ready' if 'ack' in steps else ('needs-reconciliation' if 'request' in steps else 'cancelled-before-submit') if cancelled else 'pending'
        return dict(profile=PROFILE,occurrence=row['id'],task=json.loads(state['input'])['task'],
            definition_digest=digest(state['definition'].encode()),deadline_ms=state['deadline'],steps=steps,
            status=status,relay_calls_spent=inspection['calls'],relay_limit=32,
            subscription=bool(state['subscription']),cursor=cursor,chain_authority='NOT_GRANTED')
