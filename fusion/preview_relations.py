"""Opt-in logical retraction facet of the existing Relations owner.

An assertion occurrence, its immutable payload and a retraction event are
distinct. Historical assertion-only schema-ordered-relations/2 is unchanged.
This implementation extends that owner's storage discipline; it is not an
independent replacement-provider claim.
"""
from contextlib import closing
import json
import secrets
import uuid

from .relations import RelationOwner
from . import lookup_contracts as c
from .contracts import canonical, digest, require
from .ports import Mutation
from .responses import envelope

PROFILE = 'schema-ordered-retractable-relations/1'
CONTENT_TYPE = 'application/omega-structural-assertion-v1'


class RetractableRelations(RelationOwner):
    def __init__(self, path, atoms, access, schemas, hook=lambda _: None):
        from pathlib import Path
        self.path, self.atoms, self.access, self.hook = Path(path), atoms, access, hook
        self.schemas = c.schemas(schemas)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self.connect()) as db, db:
            tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            require(not tables or tables == {'preview_relation_meta', 'preview_relation_intents', 'preview_relation_events'}, 'UNSUPPORTED_PROFILE')
            db.executescript('''
                CREATE TABLE IF NOT EXISTS preview_relation_meta(value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS preview_relation_intents(identity TEXT PRIMARY KEY, intent TEXT NOT NULL, result TEXT);
                CREATE TABLE IF NOT EXISTS preview_relation_events(scope TEXT NOT NULL, sequence INTEGER NOT NULL,
                    identity TEXT NOT NULL UNIQUE, kind TEXT NOT NULL, assertion TEXT NOT NULL, value TEXT NOT NULL,
                    PRIMARY KEY(scope,sequence));
            ''')
            row = db.execute('SELECT value FROM preview_relation_meta').fetchone()
            if row:
                self.meta = json.loads(row[0])
                require(self.meta['profile'] == PROFILE and self.meta['schemas'] == self.schemas, 'UNSUPPORTED_PROFILE')
            else:
                self.meta = dict(profile=PROFILE, schemas=self.schemas, source=str(uuid.uuid4()), secret=secrets.token_hex(32))
                db.execute('INSERT INTO preview_relation_meta VALUES(?)', (canonical(self.meta).decode(),))

    def _intent(self, command, operation, value):
        c.mutation(command)
        principal = self.access.authorize(command.scope_ref, operation)
        key = digest(canonical([principal, command.scope_ref, command.idempotency_key]))
        wire = canonical(dict(operation=operation, value=value)).decode()
        with closing(self.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT * FROM preview_relation_intents WHERE identity=?', (key,)).fetchone()
            if row: require(row[1] == wire, 'CONFLICT')
            else:
                require(db.execute('SELECT count(*) FROM preview_relation_intents').fetchone()[0] < c.MAX_COMMANDS, 'OVERLOADED')
                db.execute('INSERT INTO preview_relation_intents VALUES(?,?,NULL)', (key, wire))
        return key, json.loads(row[2]) if row and row[2] else None

    def _sequence(self, db, scope):
        return db.execute('SELECT coalesce(max(sequence),0) FROM preview_relation_events WHERE scope=?', (scope,)).fetchone()[0]

    def assertRelation(self, command, relation_type, roles, directed):
        structure = c.relation_body(command.scope_ref, relation_type, roles, directed, self.schemas)
        key, old = self._intent(command, 'assertRelation', structure)
        if old:
            self.getRelation(old['ref'], historical=True)
            return old
        for _, endpoint in structure['roles']: envelope(self.atoms.get(endpoint), endpoint)
        body = dict(profile=PROFILE, assertion_id=key, structure=structure)
        data = canonical(body)
        written = self.atoms.create(Mutation(command.scope_ref, 'structural-assertion/'+key), CONTENT_TYPE, data)
        envelope(self.atoms.get(written['ref']), written['ref'])
        require(written['ref']['digest'] == digest(data), 'NOT_AVAILABLE')
        self.hook('after_relation_payload')
        with closing(self.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            prior = db.execute('SELECT result FROM preview_relation_intents WHERE identity=?', (key,)).fetchone()[0]
            if prior: return json.loads(prior)
            seq = self._sequence(db, command.scope_ref)+1
            require(seq <= c.MAX_COMMANDS, 'OVERLOADED')
            result = dict(profile=PROFILE, ref=written['ref'], body=body, asserted_at=c.make_head(self.meta['source'], command.scope_ref, seq, PROFILE), state='asserted')
            self.access.authorize(command.scope_ref, 'assertRelation')
            db.execute('INSERT INTO preview_relation_events VALUES(?,?,?,?,?,?)', (command.scope_ref, seq, key, 'assert', key, canonical(result).decode()))
            db.execute('UPDATE preview_relation_intents SET result=? WHERE identity=?', (canonical(result).decode(), key))
        self.hook('after_relation_commit')
        return result

    def getRelation(self, ref, historical=False):
        require(type(historical) is bool)
        scope = c.scope_of(ref); c.ref(ref, scope)
        self.access.authorize(scope, 'getRelation')
        with closing(self.connect()) as db:
            values = [json.loads(r[0]) for r in db.execute("SELECT value FROM preview_relation_events WHERE scope=? AND kind='assert'", (scope,))]
            found = next((v for v in values if v['ref'] == ref), None)
            require(found is not None, 'NOT_FOUND')
            retraction = db.execute("SELECT sequence FROM preview_relation_events WHERE assertion=? AND kind='retract'", (found['body']['assertion_id'],)).fetchone()
        if retraction:
            require(historical is True, 'NOT_FOUND')
            self.access.authorize(scope, 'history')
        item = self.atoms.get(ref); envelope(item, ref)
        require(item.content_type == CONTENT_TYPE and item.bytes == canonical(found['body']), 'NOT_AVAILABLE')
        self.access.authorize(scope, 'getRelation')
        return dict(found, state='retracted' if retraction else 'asserted', retracted_at=retraction[0] if retraction else None)

    def retract(self, command, ref, expected_asserted_at):
        c.ref(ref, command.scope_ref); c.head(expected_asserted_at, command.scope_ref, PROFILE)
        key, old = self._intent(command, 'retract', dict(ref=ref, expected_asserted_at=expected_asserted_at))
        if old: return old
        asserted = self.getRelation(ref, historical=True)
        require(asserted['asserted_at'] == expected_asserted_at, 'CONFLICT')
        with closing(self.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            prior = db.execute('SELECT result FROM preview_relation_intents WHERE identity=?', (key,)).fetchone()[0]
            if prior: return json.loads(prior)
            identity = asserted['body']['assertion_id']
            require(not db.execute("SELECT 1 FROM preview_relation_events WHERE assertion=? AND kind='retract'", (identity,)).fetchone(), 'CONFLICT')
            seq = self._sequence(db, command.scope_ref)+1
            require(seq <= c.MAX_COMMANDS, 'OVERLOADED')
            result = dict(profile=PROFILE, ref=ref, state='retracted', at=c.make_head(self.meta['source'], command.scope_ref, seq, PROFILE),
                          effect='structural-only', evidence_changed=False, payload_erased=False)
            self.access.authorize(command.scope_ref, 'retract')
            db.execute('INSERT INTO preview_relation_events VALUES(?,?,?,?,?,?)', (command.scope_ref, seq, key, 'retract', identity, canonical(result).decode()))
            db.execute('UPDATE preview_relation_intents SET result=? WHERE identity=?', (canonical(result).decode(), key))
        self.hook('after_retraction_commit')
        return result

    def traverse(self, direction, ref, limit, cursor=None, snapshot=None):
        require(direction in ('outgoing', 'incoming'))
        scope = c.scope_of(ref); c.ref(ref, scope); c.integer(limit, 1, c.PAGE)
        principal = self.access.authorize(scope, direction)
        envelope(self.atoms.get(ref), ref)
        binding = digest(canonical([direction, ref, limit, principal, PROFILE]))
        with closing(self.connect()) as db:
            db.execute('BEGIN')
            seq = self._sequence(db, scope)
            current = c.make_head(self.meta['source'], scope, seq, PROFILE)
            after = 0
            if cursor:
                decoded = c.unseal(self.meta['secret'], cursor)
                require(set(decoded) == {'binding', 'at', 'after'} and decoded['binding'] == binding, 'CONFLICT')
                require(snapshot is None or snapshot == decoded['at'], 'CONFLICT')
                snapshot, after = decoded['at'], decoded['after']
            at = c.head(snapshot, scope, PROFILE) if snapshot is not None else current
            require(at['source'] == current['source'] and at['sequence'] <= seq, 'CONFLICT')
            c.integer(after, 0, at['sequence'])
            if at != current: self.access.authorize(scope, 'history')
            rows = db.execute("SELECT sequence,value FROM preview_relation_events a WHERE scope=? AND kind='assert' AND sequence>? AND sequence<=? AND NOT EXISTS(SELECT 1 FROM preview_relation_events r WHERE r.assertion=a.assertion AND r.kind='retract' AND r.sequence<=?) ORDER BY sequence", (scope, after, at['sequence'], at['sequence'])).fetchall()
            chosen = []
            for number, raw in rows:
                value = json.loads(raw); structure = value['body']['structure']
                indexes = structure['schema']['origins' if direction == 'outgoing' else 'destinations']
                if any(structure['roles'][i][1] == ref for i in indexes): chosen.append((number, value['ref']))
            more = len(chosen) > limit; selected = chosen[:limit]
        self.access.authorize(scope, direction)
        return dict(profile=PROFILE, refs=[r for _, r in selected], sequences=[n for n, _ in selected], at=at,
                    cursor=c.seal(self.meta['secret'], dict(binding=binding, at=at, after=selected[-1][0])) if more else None,
                    page_complete=not more, binding=binding)
