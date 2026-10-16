"""Bounded local C1→C2 handoff. Separate commits, no foreign database access.

This is a specific durable delivery cursor, not a scheduler or inference loop.
Only a trusted local composition with acknowledgeEvidence authority may run it.
"""
from contextlib import closing
from dataclasses import asdict
import fcntl
import json
from pathlib import Path
import sqlite3

from . import memory_contracts as c
from .contracts import ContractError, canonical, digest, require
from .ports import EpisodicMemory, BeliefRevision, EvidenceSubmission, Mutation


class EvidenceRelay:
    def __init__(self, database, episodes: EpisodicMemory, beliefs: BeliefRevision, *, hook=lambda stage: None):
        self.database, self.episodes, self.beliefs, self.hook = str(database), episodes, beliefs, hook
        with closing(self._connect()) as db, db:
            db.execute('''CREATE TABLE IF NOT EXISTS deliveries
                (id TEXT NOT NULL, attempt INTEGER NOT NULL, episode TEXT NOT NULL, semantic TEXT NOT NULL,
                 state TEXT NOT NULL, decision TEXT, PRIMARY KEY(id,attempt))''')

    def _connect(self):
        db = sqlite3.connect(self.database, timeout=.2)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA journal_mode=WAL'); db.execute('PRAGMA synchronous=FULL')
        return db

    @c.boundary
    def drain(self, episode, declarations=None):
        c.episode_ref(episode)
        declarations = declarations or {}
        require(type(declarations) is dict and len(declarations) <= c.MAX_PENDING)
        for key, value in declarations.items(): c.identifier(key); c.independence(value)
        decisions = []
        with open(self.database + '.lock', 'a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            pending = self.episodes.pendingEvidence(episode, c.MAX_PENDING)
            require(type(pending) is tuple and len(pending) <= c.MAX_PENDING, 'NOT_AVAILABLE')
            require(len({canonical(d) for d in pending}) == len(pending), 'NOT_AVAILABLE')
            for delivery in pending:
                c.response(c.delivery, delivery, episode)
                evidence = self.episodes.readEvidence(delivery['evidence'])
                c.response(c.evidence_record, evidence, delivery['evidence'])
                numeric = evidence['event']['numerical']
                require(numeric is not None, 'NOT_AVAILABLE')
                decision = self._deliver(episode, delivery, numeric, declarations.get(delivery['delivery_id']))
                self.hook('after_belief_commit')
                receipt = self.episodes.acknowledgeEvidence(Mutation(episode['scope_ref'], 'ack/' + delivery['delivery_id']),
                                                          delivery['delivery_id'], decision)
                require(receipt == {'delivery_id': delivery['delivery_id'], 'decision_id': decision['decision_id'],
                                    'acknowledged': True}, 'NOT_AVAILABLE')
                with closing(self._connect()) as db, db:
                    db.execute("UPDATE deliveries SET state='acknowledged' WHERE id=? AND decision IS NOT NULL",
                               (delivery['delivery_id'],))
                decisions.append(decision)
        return tuple(decisions)

    def _deliver(self, episode, delivery, numeric, declaration):
        identity = delivery['delivery_id']
        for _ in range(3):
            with closing(self._connect()) as db, db:
                prior = db.execute('SELECT * FROM deliveries WHERE id=? ORDER BY attempt DESC LIMIT 1', (identity,)).fetchone()
                if prior is None or prior['state'] == 'conflict':
                    attempt = 0 if prior is None else prior['attempt'] + 1
                    require(attempt < 32, 'OVERLOADED')
                    snapshot = self.beliefs.readBelief(numeric['claim'], numeric['context'], None)
                    c.response(c.snapshot, snapshot, numeric['claim'], numeric['context'], snapshot['runtime_selection'])
                    request = EvidenceSubmission(Mutation(episode['scope_ref'], f'delivery/{identity}/{attempt}'),
                        numeric['claim'], numeric['context'], delivery['evidence'], None, snapshot['revision'],
                        c.BELIEF_PROFILE, snapshot['runtime_selection'], declaration)
                    semantic = c.submission(request)
                    db.execute("INSERT INTO deliveries VALUES(?,?,?,?,'pending',NULL)",
                               (identity, attempt, canonical(episode).decode(), canonical(semantic).decode()))
                else:
                    attempt, semantic = prior['attempt'], json.loads(prior['semantic'])
                    require(semantic['independence'] == declaration, 'CONFLICT')
                    require(semantic['evidence'] == delivery['evidence'], 'CONFLICT')
                    request = EvidenceSubmission(**{**semantic, 'command': Mutation(**semantic['command'])})
            try:
                # Even a saved result is replayed through C2: current authorization first.
                decision = self.beliefs.submitEvidence(request)
            except ContractError as error:
                if error.code != 'CONFLICT': raise
                # Only a genuine CAS race gets a NEW request identity. Semantic conflicts
                # with unchanged head remain errors; never reinterpret the old attempt.
                current = self.beliefs.readBelief(numeric['claim'], numeric['context'], None)
                c.response(c.snapshot, current, numeric['claim'], numeric['context'], request.runtime_selection)
                require(current['revision'] != request.expected_revision, 'CONFLICT')
                with closing(self._connect()) as db, db:
                    db.execute("UPDATE deliveries SET state='conflict' WHERE id=? AND attempt=?", (identity, attempt))
                continue
            c.response(c.decision, decision, request.claim, request.context, request.runtime_selection)
            require(decision['evidence'] == request.evidence, 'NOT_AVAILABLE')
            with closing(self._connect()) as db, db:
                db.execute("UPDATE deliveries SET state='committed',decision=? WHERE id=? AND attempt=?",
                           (canonical(decision).decode(), identity, attempt))
            return decision
        raise ContractError('OVERLOADED')

    @c.boundary
    def decisions(self, episode):
        """Bounded audit receipts; every read rechecks C1/C2 authority and history."""
        c.episode_ref(episode)
        page = self.episodes.readEpisode(episode, 1, 1)
        c.response(c.episode_page, page, episode, 1, 1)
        with closing(self._connect()) as db:
            rows = db.execute('SELECT semantic,decision FROM deliveries WHERE episode=? AND decision IS NOT NULL LIMIT ?',
                              (canonical(episode).decode(), c.MAX_EVENTS + 1)).fetchall()
        require(len(rows) <= c.MAX_EVENTS, 'OVERLOADED')
        values = []
        for row in rows:
            semantic = json.loads(row['semantic'])
            request = EvidenceSubmission(**{**semantic, 'command': Mutation(**semantic['command'])})
            observed = self.beliefs.submitEvidence(request)
            require(observed == json.loads(row['decision']), 'NOT_AVAILABLE')
            values.append(observed)
        return tuple(values)
