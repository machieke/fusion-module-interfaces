"""Private episode owner. No belief, PLN, Hive, messaging or chain dependency."""
from contextlib import closing
import json
import sqlite3

from .contracts import ContractError, canonical, digest, require
from . import memory_contracts as c
from .ports import AtomStorage, PrivateAuthority, Mutation, EpisodeRef, EpisodeEvent, EvidenceRef
from .responses import envelope


class EpisodeOwner:
    def __init__(self, database, atoms: AtomStorage, access: PrivateAuthority, *, hook=lambda stage: None):
        self.database, self.atoms, self.access, self.hook = str(database), atoms, access, hook
        db = self._connect()
        try:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS meta (selection TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS episodes
                  (id TEXT PRIMARY KEY, scope TEXT NOT NULL, owner TEXT NOT NULL, source TEXT NOT NULL, head INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS events
                  (scope TEXT NOT NULL, occurrence TEXT NOT NULL, episode TEXT NOT NULL, sequence INTEGER NOT NULL,
                   fingerprint TEXT NOT NULL, record TEXT NOT NULL, receipt TEXT NOT NULL,
                   PRIMARY KEY(scope, occurrence), UNIQUE(episode, sequence));
                CREATE TABLE IF NOT EXISTS mutations
                  (id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, response TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS deliveries
                  (id TEXT PRIMARY KEY, episode TEXT NOT NULL, sequence INTEGER NOT NULL,
                   evidence TEXT NOT NULL, decision TEXT);
            ''')
            selected = db.execute('SELECT selection FROM meta').fetchone()
            if selected:
                require(selected[0] == access.selection(), 'UNSUPPORTED_PROFILE')
            else:
                db.execute('INSERT INTO meta VALUES(?)', (access.selection(),)); db.commit()
        finally:
            db.close()

    def _connect(self):
        db = sqlite3.connect(self.database, timeout=.2)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA journal_mode=WAL'); db.execute('PRAGMA synchronous=FULL')
        return db

    def _identity(self, principal, command, operation, body):
        return (digest(canonical([principal, command.scope_ref, operation, command.idempotency_key])),
                digest(canonical([body, self.access.selection()])))

    def _replay(self, db, identity, fingerprint):
        row = db.execute('SELECT * FROM mutations WHERE id=?', (identity,)).fetchone()
        if row:
            require(row['fingerprint'] == fingerprint, 'CONFLICT')
            return json.loads(row['response'])

    def _save(self, db, identity, fingerprint, value):
        db.execute('INSERT INTO mutations VALUES(?,?,?)', (identity, fingerprint, canonical(value).decode()))
        return value

    def _episode(self, db, ref, principal):
        row = db.execute('SELECT * FROM episodes WHERE id=? AND scope=?', (ref['id'], ref['scope_ref'])).fetchone()
        require(row is not None, 'NOT_FOUND')
        require(row['owner'] == principal, 'UNAUTHORIZED')
        return row

    @c.boundary
    def recordEpisode(self, command: Mutation, source: str):
        c.mutation(command); c.identifier(source)
        principal = self.access.authorize(command.scope_ref, 'recordEpisode')
        identity, fingerprint = self._identity(principal, command, 'recordEpisode', source)
        with closing(self._connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            old = self._replay(db, identity, fingerprint)
            if old is not None: return old
            ref = {'scope_ref': command.scope_ref, 'id': identity}
            db.execute('INSERT INTO episodes VALUES(?,?,?,?,0)', (identity, command.scope_ref, principal, source))
            return self._save(db, identity, fingerprint,
                {'ref': ref, 'head': 0, 'events': [], 'next_sequence': None, 'complete': True})

    def _record(self, db, ref, principal):
        self._episode(db, ref['episode'], principal)
        row = db.execute('SELECT record FROM events WHERE scope=? AND occurrence=?',
                         (ref['episode']['scope_ref'], ref['occurrence_id'])).fetchone()
        require(row is not None, 'NOT_FOUND')
        value = json.loads(row[0])
        require(value['evidence'] == ref, 'CONFLICT')
        stored = self.atoms.get(ref['event_ref'])
        envelope(stored, ref['event_ref'])
        require(stored.content_type == 'application/fusion-event' and
                json.loads(stored.bytes) == {'event': value['event'], 'lineage_roots': value['lineage_roots']}, 'NOT_AVAILABLE')
        c.response(c.evidence_record, value, ref)
        return value

    @c.boundary
    def appendEvent(self, command: Mutation, episode: EpisodeRef, expected_sequence: int, event: EpisodeEvent):
        episode, event = c.detached(episode), c.detached(event)
        c.episode_ref(episode); c.mutation(command, episode['scope_ref'])
        c.integer(expected_sequence, 0, c.MAX_EVENTS); c.event(event, command.scope_ref)
        principal = self.access.authorize(command.scope_ref, 'appendEvent')
        identity, fingerprint = self._identity(principal, command, 'appendEvent', [episode, expected_sequence, event])
        occurrence_fingerprint = digest(canonical([episode, event]))
        with closing(self._connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            self._episode(db, episode, principal)
            prior = self._replay(db, identity, fingerprint)
            if prior is not None: return prior
            prior = db.execute('SELECT * FROM events WHERE scope=? AND occurrence=?',
                               (command.scope_ref, event['occurrence_id'])).fetchone()
            if prior:
                require(prior['fingerprint'] == occurrence_fingerprint, 'CONFLICT')
                return self._save(db, identity, fingerprint, json.loads(prior['receipt']))
            row = self._episode(db, episode, principal)
            require(row['head'] == expected_sequence, 'CONFLICT')
            require(row['head'] < c.MAX_EVENTS, 'OVERLOADED')
            if event['numerical'] is not None:
                pending = db.execute('SELECT count(*) FROM deliveries WHERE episode=? AND decision IS NULL', (episode['id'],)).fetchone()[0]
                require(pending < c.MAX_PENDING, 'OVERLOADED')
            for ref in [event['payload'], *event['causation']]:
                envelope(self.atoms.get(ref), ref)
            lineage = set()
            if event['provenance']:
                for ref in event['provenance']:
                    value = self._record(db, ref, principal)
                    lineage.update(value['lineage_roots'])
                # Unknown ancestry cannot be repaired with a new source label.
                if any(not self._record(db, ref, principal)['lineage_roots'] for ref in event['provenance']):
                    lineage.clear()
            else:
                origin = self.access.origin(command.scope_ref, event['source'])
                if origin is not None:
                    lineage.add(digest(canonical([command.scope_ref, origin])))
            c.roots(sorted(lineage), allow_empty=True)
            payload = canonical({'event': event, 'lineage_roots': sorted(lineage)})
            stored = self.atoms.create(Mutation(command.scope_ref, 'event/' + occurrence_fingerprint),
                                       'application/fusion-event', payload)
            c.response(c.atom_write, stored, command.scope_ref)
            # Read through the port; an injected provider cannot forge these bytes.
            observed = self.atoms.get(stored['ref']); envelope(observed, stored['ref'])
            require(observed.bytes == payload, 'NOT_AVAILABLE')
            self.hook('after_payload_persist')
            self.access.authorize(command.scope_ref, 'appendEvent')
            sequence = row['head'] + 1
            evidence = {'episode': episode, 'occurrence_id': event['occurrence_id'],
                        'sequence': sequence, 'event_ref': stored['ref']}
            delivery = digest(canonical(evidence)) if event['numerical'] is not None else None
            receipt = {'evidence': evidence, 'head': sequence, 'delivery_id': delivery, 'persistence': 'process-restart'}
            record = {'evidence': evidence, 'event': event, 'lineage_roots': sorted(lineage)}
            db.execute('INSERT INTO events VALUES(?,?,?,?,?,?,?)', (command.scope_ref, event['occurrence_id'],
                       episode['id'], sequence, occurrence_fingerprint, canonical(record).decode(), canonical(receipt).decode()))
            db.execute('UPDATE episodes SET head=? WHERE id=?', (sequence, episode['id']))
            if delivery is not None:
                db.execute('INSERT INTO deliveries VALUES(?,?,?,?,NULL)', (delivery, episode['id'], sequence, canonical(evidence).decode()))
            self._save(db, identity, fingerprint, receipt)
        self.hook('after_episode_commit')
        return receipt

    @c.boundary
    def readEpisode(self, ref: EpisodeRef, start: int, limit: int):
        ref = c.detached(ref)
        c.episode_ref(ref); c.integer(start, 1, c.MAX_EVENTS+1); c.integer(limit, 1, c.MAX_PAGE)
        principal = self.access.authorize(ref['scope_ref'], 'readEpisode')
        with closing(self._connect()) as db, db:
            db.execute('BEGIN')
            head = self._episode(db, ref, principal)['head']
            require(start <= head + 1)
            rows = db.execute('SELECT record FROM events WHERE episode=? AND sequence>=? ORDER BY sequence LIMIT ?',
                              (ref['id'], start, limit)).fetchall()
            values = [json.loads(row[0]) for row in rows]
            for value in values:
                self._record(db, value['evidence'], principal)
            next_sequence = start + len(values)
            complete = next_sequence > head
            return {'ref': ref, 'head': head, 'events': values,
                    'next_sequence': None if complete else next_sequence, 'complete': complete}

    @c.boundary
    def readEvidence(self, ref: EvidenceRef):
        ref = c.detached(ref)
        c.evidence_ref(ref)
        principal = self.access.authorize(ref['episode']['scope_ref'], 'readEvidence')
        with closing(self._connect()) as db, db:
            return self._record(db, ref, principal)

    @c.boundary
    def pendingEvidence(self, ref: EpisodeRef, limit: int):
        ref = c.detached(ref)
        c.episode_ref(ref); c.integer(limit, 1, c.MAX_PENDING)
        principal = self.access.authorize(ref['scope_ref'], 'pendingEvidence')
        with closing(self._connect()) as db, db:
            self._episode(db, ref, principal)
            rows = db.execute('SELECT * FROM deliveries WHERE episode=? AND decision IS NULL ORDER BY sequence LIMIT ?',
                              (ref['id'], limit)).fetchall()
            return tuple({'delivery_id': r['id'], 'evidence': json.loads(r['evidence'])} for r in rows)

    @c.boundary
    def acknowledgeEvidence(self, command: Mutation, delivery_id: str, decision):
        decision = c.detached(decision)
        c.mutation(command); c.identifier(delivery_id)
        principal = self.access.authorize(command.scope_ref, 'acknowledgeEvidence')
        c.response(c.decision, decision, decision['snapshot']['claim'], decision['snapshot']['context'],
                   decision['snapshot']['runtime_selection'])
        identity, fingerprint = self._identity(principal, command, 'acknowledgeEvidence', [delivery_id, decision])
        with closing(self._connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            prior = self._replay(db, identity, fingerprint)
            if prior is not None: return prior
            row = db.execute('SELECT * FROM deliveries WHERE id=?', (delivery_id,)).fetchone()
            require(row is not None, 'NOT_FOUND')
            evidence = json.loads(row['evidence'])
            require(evidence['episode']['scope_ref'] == command.scope_ref, 'UNAUTHORIZED')
            self._episode(db, evidence['episode'], principal)
            require(decision['evidence'] == evidence, 'CONFLICT')
            require(row['decision'] is None or row['decision'] == decision['decision_id'], 'CONFLICT')
            db.execute('UPDATE deliveries SET decision=? WHERE id=?', (decision['decision_id'], delivery_id))
            return self._save(db, identity, fingerprint,
                {'delivery_id': delivery_id, 'decision_id': decision['decision_id'], 'acknowledged': True})
