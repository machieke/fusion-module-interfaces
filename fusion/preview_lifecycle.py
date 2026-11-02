"""Storage-owned lifecycle facet for fresh synthetic immutable memories.

This journal owns logical heads and visibility epochs. Search is a projection;
storage acceptance, lifecycle commit and publication are different receipts.
No payload, vector, C1 contribution or C2 state is erased or rewritten here.
"""
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import time
import uuid

from .contracts import canonical, digest, require
from . import lookup_contracts as c, vector_contracts as v
from .vector_enrollment import validate_inputs
from .responses import envelope

PROFILE = 'immutable-memory-lifecycle/1'
MAX_EVENTS = 256


class MemoryLifecycle:
    def __init__(self, database, atoms, access, scope, corpus, hook=lambda _: None, *, embedding=v.EMBEDDING):
        require(scope.startswith('synthetic-'), 'UNAUTHORIZED')
        self.path, self.atoms, self.access = Path(database), atoms, access
        self.scope, self.corpus, self.hook = scope, corpus, hook
        self.embedding = v.model(embedding)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self.connect()) as db, db:
            tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            require(not tables or tables == {'lifecycle_meta', 'lifecycle_events', 'lifecycle_intents'}, 'UNSUPPORTED_PROFILE')
            db.executescript('''
                CREATE TABLE IF NOT EXISTS lifecycle_meta(value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS lifecycle_events(sequence INTEGER PRIMARY KEY, logical_id TEXT NOT NULL, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS lifecycle_intents(identity TEXT PRIMARY KEY, intent TEXT NOT NULL, result TEXT);
            ''')
            row = db.execute('SELECT value FROM lifecycle_meta').fetchone()
            if row:
                self.meta = json.loads(row[0])
                require(self.meta['profile'] == PROFILE and self.meta['scope'] == scope and self.meta['corpus'] == corpus and self.meta['embedding'] == self.embedding, 'UNSUPPORTED_PROFILE')
            else:
                self.meta = dict(profile=PROFILE, scope=scope, corpus=corpus, embedding=self.embedding, source=str(uuid.uuid4()))
                db.execute('INSERT INTO lifecycle_meta VALUES(?)', (canonical(self.meta).decode(),))

    def connect(self):
        db = sqlite3.connect(self.path, timeout=1)
        db.execute('PRAGMA journal_mode=WAL'); db.execute('PRAGMA synchronous=FULL')
        return db

    def _sequence(self, db): return db.execute('SELECT coalesce(max(sequence),0) FROM lifecycle_events').fetchone()[0]

    def _head(self, sequence): return c.make_head(self.meta['source'], self.scope, sequence, PROFILE)

    def head(self):
        self.access.authorize(self.scope, 'lifecycle.read')
        with closing(self.connect()) as db: return self._head(self._sequence(db))

    def _record(self, db, logical_id, through=None):
        require(type(logical_id) is str)
        row = db.execute('SELECT value FROM lifecycle_events WHERE logical_id=? AND sequence<=? ORDER BY sequence DESC LIMIT 1',
                         (logical_id, MAX_EVENTS if through is None else through)).fetchone()
        require(row is not None, 'NOT_FOUND')
        return json.loads(row[0])

    def _enrollment(self, ref):
        c.ref(ref, self.scope)
        item = self.atoms.get(ref); envelope(item, ref)
        require(item.content_type == v.ENROLLMENT, 'UNSUPPORTED_PROFILE')
        entry = v.enrollment(json.loads(item.bytes), self.scope, self.corpus, self.embedding)
        require(canonical(entry) == item.bytes, 'NOT_AVAILABLE')
        payload, _ = validate_inputs(self.atoms, entry)
        return dict(uuid=payload['uuid'], payload=entry['payload'], enrollment=ref)

    def change(self, command, operation, *, logical_id=None, expected_revision=0, enrollment=None, deadline_ms=None):
        c.mutation(command); require(command.scope_ref == self.scope, 'UNAUTHORIZED')
        require(operation in ('introduce', 'supersede', 'withdraw'), 'UNSUPPORTED_OPERATION')
        principal = self.access.authorize(self.scope, 'lifecycle.'+operation)
        c.integer(expected_revision, 0, MAX_EVENTS)
        if operation == 'introduce': require(logical_id is None and expected_revision == 0)
        else: c.identity(logical_id)
        require((enrollment is None) == (operation == 'withdraw'))
        key = digest(canonical([principal, self.scope, command.idempotency_key]))
        bound=dict(operation=operation, logical_id=logical_id, expected_revision=expected_revision, enrollment=enrollment)
        if deadline_ms is not None:
            c.integer(deadline_ms,1,2**63-1);bound['deadline_ms']=deadline_ms
        intent = canonical(bound).decode()
        with closing(self.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            prior = db.execute('SELECT intent,result FROM lifecycle_intents WHERE identity=?', (key,)).fetchone()
            if prior:
                require(prior[0] == intent, 'CONFLICT')
                if prior[1]: return json.loads(prior[1])
            else:
                require(deadline_ms is None or time.time_ns()//1_000_000<deadline_ms,'DEADLINE_EXCEEDED')
                require(db.execute('SELECT count(*) FROM lifecycle_intents').fetchone()[0] < MAX_EVENTS, 'OVERLOADED')
                db.execute('INSERT INTO lifecycle_intents VALUES(?,?,NULL)', (key, intent))
        self.hook('after_lifecycle_intent')
        successor = self._enrollment(enrollment) if enrollment is not None else None
        # Every payload/vector/enrollment is verified before selecting a head.
        source_head = self.atoms.head(self.scope)
        with closing(self.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            prior = db.execute('SELECT result FROM lifecycle_intents WHERE identity=?', (key,)).fetchone()[0]
            if prior: return json.loads(prior)
            require(deadline_ms is None or time.time_ns()//1_000_000<deadline_ms,'DEADLINE_EXCEEDED')
            current = self._record(db, logical_id) if logical_id else None
            if current:
                require(current['revision'] == expected_revision and current['state'] == 'active', 'CONFLICT')
                if successor: require(successor['uuid'] != current['memory']['uuid'], 'CONFLICT')
            if successor:
                # One immutable revision belongs to one logical occurrence.
                previous = [json.loads(r[0]) for r in db.execute('SELECT value FROM lifecycle_events')]
                require(all(x['memory']['uuid'] != successor['uuid'] for x in previous), 'CONFLICT')
            sequence = self._sequence(db)+1
            require(sequence <= MAX_EVENTS, 'OVERLOADED')
            lid = logical_id or str(uuid.uuid5(uuid.UUID(self.meta['source']), key))
            result = dict(profile=PROFILE, logical_id=lid, revision=expected_revision+1,
                state='withdrawn' if operation == 'withdraw' else 'active', operation=operation,
                memory=successor or current['memory'], predecessor=current['memory'] if current else None,
                at=self._head(sequence), source_head=source_head, projection='NOT_OBSERVED',
                empirical_weight_transferred=False, priority_transferred=False, payload_erased=False,
                result='WITHDRAWN_FROM_ACTIVE_VIEW_PENDING_PUBLICATION' if operation == 'withdraw' else
                       'MEMORY-SUPERSEDED-PENDING-PUBLICATION' if operation == 'supersede' else 'MEMORY-REGISTERED-PENDING-PUBLICATION')
            self.access.authorize(self.scope, 'lifecycle.'+operation)
            db.execute('INSERT INTO lifecycle_events VALUES(?,?,?)', (sequence, lid, canonical(result).decode()))
            db.execute('UPDATE lifecycle_intents SET result=? WHERE identity=?', (canonical(result).decode(), key))
        self.hook('after_lifecycle_commit')
        self.access.authorize(self.scope, 'lifecycle.'+operation)
        return result

    def readEvents(self, after, through, limit):
        self.access.authorize(self.scope, 'lifecycle.read')
        c.head(through, self.scope, PROFILE); c.integer(after, 0, through['sequence']); c.integer(limit, 1, c.PAGE)
        with closing(self.connect()) as db:
            require(through['source'] == self.meta['source'] and through['sequence'] <= self._sequence(db), 'CONFLICT')
            rows = db.execute('SELECT value FROM lifecycle_events WHERE sequence>? AND sequence<=? ORDER BY sequence LIMIT ?',
                              (after, through['sequence'], limit)).fetchall()
        values = [json.loads(r[0]) for r in rows]
        next_sequence = after+len(values)
        self.access.authorize(self.scope, 'lifecycle.read')
        return dict(at=through, events=values, next=next_sequence, complete=next_sequence == through['sequence'])

    def activeSet(self, through):
        self.access.authorize(self.scope, 'lifecycle.project')
        c.head(through, self.scope, PROFILE)
        with closing(self.connect()) as db:
            db.execute('BEGIN')
            require(through['source'] == self.meta['source'] and through['sequence'] <= self._sequence(db), 'CONFLICT')
            latest = {}
            for raw, in db.execute('SELECT value FROM lifecycle_events WHERE sequence<=? ORDER BY sequence', (through['sequence'],)):
                record = json.loads(raw); latest[record['logical_id']] = record
        active = [r for _, r in sorted(latest.items()) if r['state'] == 'active']
        self.access.authorize(self.scope, 'lifecycle.project')
        return dict(at=through, active=[dict(logical_id=r['logical_id'], revision=r['revision'], **r['memory']) for r in active])

    def disclose(self, logical_id, memory, through, historical=False):
        require(type(historical) is bool)
        self.access.authorize(self.scope, 'lifecycle.history' if historical else 'lifecycle.read')
        c.head(through, self.scope, PROFILE)
        with closing(self.connect()) as db:
            require(through['source'] == self.meta['source'] and through['sequence'] <= self._sequence(db), 'CONFLICT')
            then = self._record(db, logical_id, through['sequence'])
            require(then['memory'] == memory, 'CONFLICT')
            current = self._record(db, logical_id)
            require(historical or current['state'] != 'withdrawn', 'UNAUTHORIZED')
        envelope(self.atoms.get(memory['payload']), memory['payload'])
        self.access.authorize(self.scope, 'lifecycle.history' if historical else 'lifecycle.read')
        return dict(authorized=True, captured_bytes_rewritten=False, physical_erasure=False)
