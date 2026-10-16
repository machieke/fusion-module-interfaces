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
from .ports import EpisodeJournal, BeliefRevision, EvidenceSubmission, Mutation
from . import delivery_contracts as d


class EvidenceRelay:
    def __init__(self, database, episodes: EpisodeJournal, beliefs: BeliefRevision, *, hook=lambda stage: None,
                 consumer=None, access=None, acknowledger=None):
        self.database, self.episodes, self.beliefs, self.hook = str(database), episodes, beliefs, hook
        self.consumer, self.access, self.acknowledger = c.detached(consumer), access, acknowledger
        self.validation = c
        if consumer is not None:
            d.consumer(self.consumer)
            require(access is not None and acknowledger is not None, 'UNSUPPORTED_PROFILE')
            from . import cognition_contracts as derived
            adapters = {c.BELIEF_PROFILE: c, derived.BELIEF_PROFILE: derived}
            require(consumer['profile'] in adapters, 'UNSUPPORTED_PROFILE')
            self.validation = adapters[consumer['profile']]
        else:
            require(access is None and acknowledger is None, 'UNSUPPORTED_PROFILE')
        with closing(self._connect()) as db, db:
            db.execute('''CREATE TABLE IF NOT EXISTS deliveries
                (id TEXT NOT NULL, attempt INTEGER NOT NULL, episode TEXT NOT NULL, semantic TEXT NOT NULL,
                 state TEXT NOT NULL, decision TEXT, PRIMARY KEY(id,attempt))''')
            if consumer is not None:
                db.execute('CREATE TABLE IF NOT EXISTS meta(selection TEXT NOT NULL)')
                prior = db.execute('SELECT selection FROM meta').fetchone()
                identity = canonical(consumer).decode()
                if prior: require(prior[0] == identity, 'UNSUPPORTED_PROFILE')
                else:
                    require(db.execute('SELECT count(*) FROM deliveries').fetchone()[0] == 0, 'UNSUPPORTED_PROFILE')
                    db.execute('INSERT INTO meta VALUES(?)', (identity,))

    def _authorize(self, scope):
        if self.consumer is not None:
            require(self.access.selection() == self.consumer['selection'], 'UNSUPPORTED_PROFILE')
            require(self.access.authorize(scope, 'submitEvidence') == self.consumer['principal'], 'UNAUTHORIZED')

    def _connect(self):
        db = sqlite3.connect(self.database, timeout=.2)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA journal_mode=WAL'); db.execute('PRAGMA synchronous=FULL')
        return db

    @c.boundary
    def drain(self, episode, declarations=None):
        episode, declarations = c.detached(episode), c.detached(declarations)
        c.episode_ref(episode)
        self._authorize(episode['scope_ref'])
        declarations = declarations or {}
        require(type(declarations) is dict and len(declarations) <= c.MAX_PENDING)
        for key, value in declarations.items(): c.identifier(key); c.independence(value)
        decisions = []
        with open(self.database + '.lock', 'a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            pending = self.episodes.pendingEvidence(episode, c.MAX_PENDING)
            require(type(pending) is tuple and len(pending) <= c.MAX_PENDING, 'NOT_AVAILABLE')
            pending = tuple(c.response_copy(d) for d in pending)
            require(len({canonical(d) for d in pending}) == len(pending), 'NOT_AVAILABLE')
            if self.consumer is not None:
                # C1 may already have committed an ack whose response was lost.
                # Reconcile those exact relay intents before reading new work.
                with closing(self._connect()) as db:
                    rows = db.execute("SELECT id,semantic FROM deliveries WHERE episode=? AND state='committed' ORDER BY id LIMIT ?",
                                      (canonical(episode).decode(), c.MAX_PENDING)).fetchall()
                recover = {r['id']: {'delivery_id': r['id'], 'evidence': json.loads(r['semantic'])['evidence']} for r in rows}
                pending = tuple([*recover.values(), *(p for p in pending if p['delivery_id'] not in recover)])[:c.MAX_PENDING]
            for delivery in pending:
                c.response(c.delivery, delivery, episode)
                evidence = c.response_copy(self.episodes.readEvidence(delivery['evidence']))
                c.response(c.evidence_record, evidence, delivery['evidence'])
                numeric = evidence['event']['numerical']
                require(numeric is not None, 'NOT_AVAILABLE')
                decision = self._deliver(episode, delivery, numeric, declarations.get(delivery['delivery_id']))
                self.hook('after_belief_commit')
                if self.consumer is None:
                    receipt = self.episodes.acknowledgeEvidence(Mutation(episode['scope_ref'], 'ack/' + delivery['delivery_id']),
                                                              delivery['delivery_id'], decision)
                    require(receipt == {'delivery_id': delivery['delivery_id'], 'decision_id': decision['decision_id'],
                                        'acknowledged': True}, 'NOT_AVAILABLE')
                else:
                    self._authorize(episode['scope_ref'])
                    completed = self._completion(delivery, decision)
                    receipt = self.acknowledger.acknowledgeDelivery(Mutation(episode['scope_ref'], 'ack/' + delivery['delivery_id']), completed)
                    c.response(d.receipt, receipt, completed)
                with closing(self._connect()) as db, db:
                    db.execute("UPDATE deliveries SET state='acknowledged' WHERE id=? AND decision IS NOT NULL",
                               (delivery['delivery_id'],))
                self.hook('after_relay_ack_commit')
                decisions.append(decision)
        return tuple(decisions)

    def _deliver(self, episode, delivery, numeric, declaration):
        identity = delivery['delivery_id']
        v = self.validation
        for _ in range(3):
            with closing(self._connect()) as db, db:
                prior = db.execute('SELECT * FROM deliveries WHERE id=? ORDER BY attempt DESC LIMIT 1', (identity,)).fetchone()
                if prior is None or prior['state'] == 'conflict':
                    attempt = 0 if prior is None else prior['attempt'] + 1
                    require(attempt < 32, 'OVERLOADED')
                    snapshot = v.snapshot_reply(self.beliefs.readBelief(numeric['claim'], numeric['context'], None),
                                                numeric['claim'], numeric['context'])
                    request = EvidenceSubmission(Mutation(episode['scope_ref'], f'delivery/{identity}/{attempt}'),
                        numeric['claim'], numeric['context'], delivery['evidence'], None, snapshot['revision'],
                        v.BELIEF_PROFILE, snapshot['runtime_selection'], declaration)
                    semantic = v.submission(request)
                    db.execute("INSERT INTO deliveries VALUES(?,?,?,?,'pending',NULL)",
                               (identity, attempt, canonical(episode).decode(), canonical(semantic).decode()))
                else:
                    attempt, semantic = prior['attempt'], json.loads(prior['semantic'])
                    require(semantic['independence'] == declaration, 'CONFLICT')
                    require(semantic['evidence'] == delivery['evidence'], 'CONFLICT')
                    require(semantic['claim'] == numeric['claim'] and semantic['context'] == numeric['context'], 'CONFLICT')
                    request = EvidenceSubmission(**{**semantic, 'command': Mutation(**semantic['command'])})
                    v.submission(request)
            try:
                # Even a saved result is replayed through C2: current authorization first.
                self._authorize(episode['scope_ref'])
                decision = c.response_copy(self.beliefs.submitEvidence(request))
            except ContractError as error:
                if error.code != 'CONFLICT': raise
                # Only a genuine CAS race gets a NEW request identity. Semantic conflicts
                # with unchanged head remain errors; never reinterpret the old attempt.
                current = self.beliefs.readBelief(numeric['claim'], numeric['context'], None)
                c.response(v.snapshot, current, numeric['claim'], numeric['context'], request.runtime_selection)
                require(current['revision'] != request.expected_revision, 'CONFLICT')
                with closing(self._connect()) as db, db:
                    db.execute("UPDATE deliveries SET state='conflict' WHERE id=? AND attempt=?", (identity, attempt))
                continue
            c.response(v.decision, decision, request.claim, request.context, request.runtime_selection)
            require(decision['evidence'] == request.evidence, 'NOT_AVAILABLE')
            if self.consumer is not None:
                require(decision['decision_id'] == digest(canonical([self.consumer['principal'], episode['scope_ref'], request.command.idempotency_key])), 'NOT_AVAILABLE')
            if prior is not None and prior['decision'] is not None:
                require(json.loads(prior['decision']) == decision, 'NOT_AVAILABLE')
            self.hook('after_evidence_decision_commit')
            with closing(self._connect()) as db, db:
                db.execute("UPDATE deliveries SET state='committed',decision=? WHERE id=? AND attempt=?",
                           (canonical(decision).decode(), identity, attempt))
            self.hook('after_relay_decision_commit')
            return decision
        raise ContractError('OVERLOADED')

    def _completion(self, delivery, decision):
        with closing(self._connect()) as db:
            row = db.execute('SELECT semantic,decision FROM deliveries WHERE id=? ORDER BY attempt DESC LIMIT 1',
                             (delivery['delivery_id'],)).fetchone()
        require(row is not None and json.loads(row['decision']) == decision, 'NOT_AVAILABLE')
        semantic = json.loads(row['semantic'])
        return {'profile': d.COMPLETION, 'state': 'committed', 'scope_ref': semantic['command']['scope_ref'],
                'delivery_id': delivery['delivery_id'], 'evidence': delivery['evidence'],
                'claim': semantic['claim'], 'context': semantic['context'], 'consumer': self.consumer,
                'request_key': semantic['command']['idempotency_key'], 'request_digest': digest(canonical(semantic)),
                'decision_id': decision['decision_id'], 'decision_digest': digest(canonical(decision))}

    @c.boundary
    def decisions(self, episode):
        """Bounded audit receipts; every read rechecks C1/C2 authority and history."""
        c.episode_ref(episode)
        self._authorize(episode['scope_ref'])
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
            c.response(self.validation.decision, observed, request.claim, request.context, request.runtime_selection)
            require(observed == json.loads(row['decision']), 'NOT_AVAILABLE')
            values.append(observed)
        return tuple(values)
