"""Bounded synthetic session admission, in the application owner's journal.

This is an inbox for a single native worker, not a scheduler. Accepted inputs
retain assignment, absolute deadline, policy and provider selection. Reading
an input is not acknowledgment. Pause/close never undo accepted effects.
"""
import fcntl
import json
from pathlib import Path
import sqlite3
import time
import uuid

from .contracts import canonical, digest, require
from .lookup_contracts import identity as valid_identity

PROFILE = 'omega-native-sessions/2'
MAX_INPUT_WINDOW_MS = 120000
MAX_SESSIONS = 8
MAX_INPUTS = 32
MAX_PENDING = 4


class SessionStore:
    def __init__(self, path, authorize, clock=lambda: int(time.time()*1000), *, profile=PROFILE):
        self.profile = profile
        self.authorize, self.clock = authorize, clock
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            from contextlib import closing
            with closing(sqlite3.connect(self.path.resolve().as_uri()+'?mode=ro',uri=True)) as existing:
                tables={r[0] for r in existing.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                if 'preview_session_profile' in tables:
                    require(existing.execute('SELECT profile FROM preview_session_profile').fetchone()==(profile,),'UNSUPPORTED_PROFILE')
                elif 'preview_sessions' in tables:
                    require(existing.execute('SELECT count(*) FROM preview_sessions').fetchone()[0]==0,'UNSUPPORTED_PROFILE')
        self.db = sqlite3.connect(path, timeout=2)
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS preview_session_profile(profile TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS preview_sessions (
                id TEXT PRIMARY KEY, principal TEXT NOT NULL, scope TEXT NOT NULL,
                binding TEXT NOT NULL, state TEXT NOT NULL, created INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS preview_inputs (
                session TEXT NOT NULL, id TEXT NOT NULL, sequence INTEGER NOT NULL,
                intent TEXT NOT NULL, assignment TEXT NOT NULL, deadline INTEGER NOT NULL,
                state TEXT NOT NULL, result TEXT, accepted INTEGER NOT NULL,
                PRIMARY KEY(session,id), UNIQUE(session,sequence));
            CREATE TABLE IF NOT EXISTS preview_input_origins(session TEXT NOT NULL,id TEXT NOT NULL,origin TEXT NOT NULL,PRIMARY KEY(session,id));
            CREATE TABLE IF NOT EXISTS preview_controls (
                session TEXT NOT NULL, id TEXT NOT NULL, intent TEXT NOT NULL, result TEXT NOT NULL,
                PRIMARY KEY(session,id));
        ''')
        with self.db:
            if self.db.execute('SELECT profile FROM preview_session_profile').fetchone() is None:
                self.db.execute('INSERT INTO preview_session_profile VALUES(?)',(profile,))

    def close(self): self.db.close()

    def _session(self, principal, session, action):
        row = self.db.execute('SELECT * FROM preview_sessions WHERE id=?', (session,)).fetchone()
        require(row is not None, 'NOT_FOUND')
        require(row['principal'] == principal, 'UNAUTHORIZED')
        self.authorize(principal, row['scope'], action)
        return row

    def create(self, principal, session, scope, binding):
        require(scope.startswith('synthetic-'), 'UNAUTHORIZED')
        valid_identity(session)
        self.authorize(principal, scope, 'session.create')
        require(type(binding) is dict and set(binding) == {'catalogue', 'policy', 'model_boundary', 'limits'})
        require(binding['model_boundary'] == 'RECORDED_FIXTURE', 'UNAUTHORIZED')
        limits = binding['limits']
        require(set(limits) == {'inputs', 'pending', 'timeout_ms'})
        require(type(limits['inputs']) is int and 1 <= limits['inputs'] <= MAX_INPUTS)
        require(type(limits['pending']) is int and 1 <= limits['pending'] <= MAX_PENDING)
        require(type(limits['timeout_ms']) is int and 1 <= limits['timeout_ms'] <= MAX_INPUT_WINDOW_MS)
        wire = canonical(binding).decode()
        require(len(wire.encode())<=4096,'OVERLOADED')
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            old = self.db.execute('SELECT * FROM preview_sessions WHERE id=?', (session,)).fetchone()
            if old:
                require((old['principal'], old['scope'], old['binding']) == (principal, scope, wire), 'CONFLICT')
            else:
                require(self.db.execute('SELECT count(*) FROM preview_sessions').fetchone()[0] < MAX_SESSIONS, 'OVERLOADED')
                self.db.execute('INSERT INTO preview_sessions VALUES(?,?,?,?,?,?)',
                                (session, principal, scope, wire, 'active', self.clock()))
        return self.observe(principal, session)

    def submit(self, principal, session, identity, text, assignment, *, deadline_ms=None):
        row = self._session(principal, session, 'input.accept')
        require(type(identity) is str and 1 <= len(identity) <= 128)
        require(type(text) is str and 0 < len(text.encode()) <= 4096 and '\x00' not in text)
        require(type(assignment) is str and 1 <= len(assignment) <= 128)
        # Assignment is selected by the trusted session API, never from text.
        intent = canonical(dict(text=text, assignment=assignment)).decode()
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            old = self.db.execute('SELECT * FROM preview_inputs WHERE session=? AND id=?', (session, identity)).fetchone()
            if old:
                require(old['intent'] == intent and (deadline_ms is None or old['deadline']==deadline_ms), 'CONFLICT')
                return self.receipt(old)
            row = self._session(principal, session, 'input.accept')
            require(row['state'] == 'active', 'NOT_AVAILABLE')
            limits = json.loads(row['binding'])['limits']
            count = self.db.execute('SELECT count(*) FROM preview_inputs WHERE session=?', (session,)).fetchone()[0]
            pending = self.db.execute("SELECT count(*) FROM preview_inputs WHERE session=? AND state!='complete'", (session,)).fetchone()[0]
            require(count < limits['inputs'] and pending < limits['pending'], 'OVERLOADED')
            now = self.clock()
            deadline=now+limits['timeout_ms'] if deadline_ms is None else deadline_ms
            require(type(deadline) is int and now<deadline<=now+limits['timeout_ms'],'DEADLINE_EXCEEDED')
            self.db.execute('INSERT INTO preview_inputs VALUES(?,?,?,?,?,?,?,NULL,?)',
                            (session, identity, count+1, intent, assignment, deadline, 'accepted', now))
        return self.receipt(self.db.execute('SELECT * FROM preview_inputs WHERE session=? AND id=?', (session, identity)).fetchone())

    @staticmethod
    def receipt(row):
        return {k: row[k] for k in ('session', 'id', 'sequence', 'assignment', 'deadline', 'state', 'accepted')}

    def next_input(self, principal, session):
        owner = self._session(principal, session, 'input.consume')
        require(owner['state'] == 'active', 'NOT_AVAILABLE')
        row = self.db.execute("SELECT * FROM preview_inputs WHERE session=? AND state!='complete' ORDER BY sequence LIMIT 1", (session,)).fetchone()
        if row is None: return None
        require(self.clock() < row['deadline'], 'DEADLINE_EXCEEDED')
        result=dict(**self.receipt(row), payload=json.loads(row['intent']), occurrence=str(uuid.uuid5(uuid.UUID(session), row['id'])),
                    session_binding=json.loads(owner['binding']))
        origin=self.db.execute('SELECT origin FROM preview_input_origins WHERE session=? AND id=?',(session,row['id'])).fetchone()
        if origin is not None:result['task_origin']=json.loads(origin[0])
        return result

    def complete(self, principal, session, identity, result):
        self._session(principal, session, 'input.complete')
        # Actual native application projection is supplied only by its worker.
        wire = canonical(result).decode()
        require(len(wire.encode()) <= 65536)
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            row = self.db.execute('SELECT * FROM preview_inputs WHERE session=? AND id=?', (session, identity)).fetchone()
            require(row is not None, 'NOT_FOUND')
            if row['result'] is not None: require(row['result'] == wire, 'CONFLICT')
            else:
                self.db.execute("UPDATE preview_inputs SET state='complete',result=? WHERE session=? AND id=?", (wire, session, identity))
        return dict(self.receipt(row), state='complete', result_digest=digest(wire.encode()))

    def control(self, principal, session, identity, action):
        self._session(principal, session, 'session.control')
        require(action in ('pause', 'resume', 'close'))
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            old = self.db.execute('SELECT * FROM preview_controls WHERE session=? AND id=?', (session, identity)).fetchone()
            if old:
                require(old['intent'] == action, 'CONFLICT')
                return json.loads(old['result'])
            row = self.db.execute('SELECT state FROM preview_sessions WHERE id=?', (session,)).fetchone()
            require(row[0] != 'closed' or action == 'close', 'CONFLICT')
            state = {'pause': 'paused', 'resume': 'active', 'close': 'closed'}[action]
            result = dict(session=session, state=state, transmitted_effects_retracted=False, accounting_retained=True)
            self.db.execute('UPDATE preview_sessions SET state=? WHERE id=?', (state, session))
            self.db.execute('INSERT INTO preview_controls VALUES(?,?,?,?)', (session, identity, action, canonical(result).decode()))
        return result

    def observe(self, principal, session, include_content=False, *, after=0):
        require(type(after) is int and 0<=after<=32)
        row = self._session(principal, session, 'session.read')
        if include_content: self.authorize(principal, row['scope'], 'session.disclose')
        inputs = []
        totals=self.db.execute("SELECT count(*),sum(CASE WHEN state='complete' THEN 1 ELSE 0 END) FROM preview_inputs WHERE session=?",(session,)).fetchone()
        limits=json.loads(row['binding'])['limits'];accepted=totals[0];completed=totals[1] or 0
        capacity=dict(accepted=accepted,completed=completed,pending=accepted-completed,
            remaining_inputs=limits['inputs']-accepted,remaining_pending=max(0,limits['pending']-accepted+completed))
        base=dict(session=session,principal=principal,scope=row['scope'],state=row['state'],
            binding=json.loads(row['binding']),inputs=inputs,live_generations=0,next_after=None,complete=True)
        complete=True;size=len(canonical(base))+1024  # Reserve RPC envelope and page cursor.
        for item in self.db.execute('SELECT * FROM preview_inputs WHERE session=? AND sequence>? ORDER BY sequence', (session,after)):
            entry = self.receipt(item)
            if include_content:
                entry.update(payload=json.loads(item['intent']), result=json.loads(item['result']) if item['result'] else None)
            amount=len(canonical(entry))+1
            if size+amount>98304:
                complete=False;break
            inputs.append(entry);size+=amount
        return dict(session=session, principal=principal, scope=row['scope'], state=row['state'],
                    binding=json.loads(row['binding']), inputs=inputs, live_generations=0,
                    next_after=inputs[-1]['sequence'] if not complete else None,complete=complete,capacity=capacity)

    def worker_lock(self, session):
        valid_identity(session)
        lock = open(str(self.path)+'.'+session+'.lock', 'a')
        try: fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            lock.close()
            require(False, 'OVERLOADED')
        return lock
