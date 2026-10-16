"""C2 owns admission, immutable belief revisions and exact semantic attempts.

Only RevisionMath performs numerical revision. All foreign state uses ports.
The local authority and math provider are trusted, explicit dependencies.
"""
from contextlib import closing
import json
import sqlite3

from . import memory_contracts as c
from .contracts import ContractError, canonical, digest, require, validate_ref
from .ports import AtomStorage, EpisodicMemory, PrivateAuthority, RevisionMath, EvidenceSubmission, Mutation
from .responses import envelope


class BeliefOwner:
    def __init__(self, database, atoms: AtomStorage, episodes: EpisodicMemory,
                 access: PrivateAuthority, math: RevisionMath, *, hook=lambda stage: None, contracts=c):
        self.database, self.atoms, self.episodes, self.access, self.math = str(database), atoms, episodes, access, math
        self.hook, self.c = hook, contracts
        self.runtime_selection = digest(canonical(math.profile()))
        self.selection = digest(canonical([access.selection(), self.runtime_selection]))
        with closing(self._connect()) as db, db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS meta (selection TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS snapshots
                  (belief TEXT NOT NULL, revision INTEGER NOT NULL, value TEXT NOT NULL, PRIMARY KEY(belief,revision));
                CREATE TABLE IF NOT EXISTS attempts
                  (id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, semantic TEXT NOT NULL,
                   state TEXT NOT NULL, decision TEXT);
            ''')
            row = db.execute('SELECT selection FROM meta').fetchone()
            if row: require(row[0] == self.selection, 'UNSUPPORTED_PROFILE')
            else: db.execute('INSERT INTO meta VALUES(?)', (self.selection,))

    def _connect(self):
        db = sqlite3.connect(self.database, timeout=.2)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA journal_mode=WAL'); db.execute('PRAGMA synchronous=FULL')
        return db

    def _authorize(self, scope, operation, assumption=False):
        principal = self.access.authorize(scope, operation)
        if assumption: self.access.authorize(scope, 'assume')
        require(digest(canonical(self.math.profile())) == self.runtime_selection, 'UNSUPPORTED_PROFILE')
        return principal

    def _claim(self, claim):
        validate_ref(claim, claim['scope_ref'])
        value = self.atoms.get(claim); envelope(value, claim)
        require(value.content_type == 'application/fusion-claim', 'INVALID_ARGUMENT')
        self.c.grounded_claim(json.loads(value.bytes))

    def _key(self, claim, context):
        return digest(canonical([claim, context]))

    def _snapshot(self, db, claim, context, revision=None):
        key = self._key(claim, context)
        row = (db.execute('SELECT value FROM snapshots WHERE belief=? ORDER BY revision DESC LIMIT 1', (key,)).fetchone()
               if revision is None else db.execute('SELECT value FROM snapshots WHERE belief=? AND revision=?', (key, revision)).fetchone())
        if row: return json.loads(row[0])
        require(revision in (None, 0), 'NOT_FOUND')
        return {'claim': claim, 'context': context, 'revision': 0, 'truth': None, 'aggregate': None,
                'covered_supports': [], 'alternatives': [], 'supports': [], 'observations': [],
                'model': self.c.MODEL, 'runtime_selection': self.runtime_selection}

    @c.boundary
    def readBelief(self, claim, context, revision=None):
        claim = self.c.detached(claim)
        validate_ref(claim, claim['scope_ref']); self.c.identifier(context)
        if revision is not None: self.c.integer(revision)
        self._authorize(claim['scope_ref'], 'readBelief'); self._claim(claim)
        with closing(self._connect()) as db:
            return self._snapshot(db, claim, context, revision)

    def _replay(self, db, identity, fingerprint):
        row = db.execute('SELECT * FROM attempts WHERE id=?', (identity,)).fetchone()
        if row:
            require(row['fingerprint'] == fingerprint, 'CONFLICT')
            require(row['state'] != 'conflict', 'CONFLICT')
            if row['decision']: return json.loads(row['decision'])

    def _evidence(self, request):
        if request.evidence is None: return None
        record = self.c.response_copy(self.episodes.readEvidence(request.evidence))
        self.c.response(self.c.evidence_record, record, request.evidence)
        immutable = self.atoms.get(request.evidence['event_ref']); envelope(immutable, request.evidence['event_ref'])
        require(immutable.content_type == 'application/fusion-event' and json.loads(immutable.bytes) ==
                {'event': record['event'], 'lineage_roots': record['lineage_roots']}, 'NOT_AVAILABLE')
        numeric = record['event']['numerical']
        require(numeric is not None and numeric['claim'] == request.claim and numeric['context'] == request.context, 'CONFLICT')
        return record

    def _admit(self, snapshot, request, record):
        """Pure ledger transition; retain every distinct admitted observation."""
        if record is None:
            support = next((s for s in snapshot['supports'] if s['id'] == request.support_id), None)
            require(support is not None, 'NOT_FOUND')
            return support, False
        old = next((o for o in snapshot['observations'] if o['evidence'] == request.evidence), None)
        if old:
            return next((s for s in snapshot['supports'] if s['id'] == old['support_id']), None), False
        require(len(snapshot['observations']) < self.c.MAX_SUPPORTS, 'OVERLOADED')
        numeric = record['event']['numerical']
        support = None
        if numeric['truth'] is not None and record['lineage_roots']:
            identity = 'support/' + digest(canonical(record))
            support = {'id': identity, 'claim': request.claim, 'context': request.context,
                       'truth': numeric['truth'], 'evidence_ids': [digest(canonical(request.evidence))],
                       'lineage_roots': record['lineage_roots'], 'coverage': [identity],
                       'premises': [], 'formula': None, 'assumptions': []}
            support = self._observation(support)
            self.c.support(support, request.command.scope_ref)
            snapshot['supports'].append(support)
        snapshot['observations'].append({'evidence': request.evidence, 'relationship': numeric['relationship'],
            'truth': numeric['truth'], 'support_id': support['id'] if support else None,
            'lineage_roots': record['lineage_roots']})
        return support, True

    def _observation(self, support): return support

    def _base_support(self, support): return not support['premises']

    def _calculate(self, snapshot, request, record):
        candidate, added = self._admit(snapshot, request, record)
        changed = added
        numerical, detail = 'no-change', 'already admitted'
        if request.independence:
            known = {s['id'] for s in snapshot['supports']}
            require(set(request.independence['supports']) <= known, 'CONFLICT')
            require(candidate is not None and candidate['id'] in request.independence['supports'], 'CONFLICT')
        if candidate is None:
            numerical, detail = 'model-inapplicable', 'no numeric assessment or no registered lineage origin'
        elif snapshot['aggregate'] is None:
            require(request.independence is None, 'CONFLICT')
            snapshot.update(aggregate=candidate['id'], truth=candidate['truth'], covered_supports=candidate['coverage'])
            numerical, detail, changed = 'initialized', 'first explicit assessment; not a revision', True
        else:
            aggregate = next(s for s in snapshot['supports'] if s['id'] == snapshot['aggregate'])
            if request.independence:
                require(set(request.independence['supports']) == {aggregate['id'], candidate['id']}, 'CONFLICT')
            if candidate['id'] == aggregate['id'] or (not added and request.independence is None):
                numerical, detail = 'no-change', 'already admitted; no new numerical evidence'
            else:
                result = self.c.response_copy(self.math.revise(aggregate, candidate, snapshot['revision'], request.independence))
                self.c.response(self.c.math_result, result, aggregate, candidate, request.independence)
                proposal = result['proposal']
                if proposal is not None:
                    self.hook('after_formula')
                    require(len(snapshot['supports']) < self.c.MAX_SUPPORTS * 2, 'OVERLOADED')
                    snapshot['supports'].append(proposal)
                    snapshot.update(aggregate=proposal['id'], truth=proposal['truth'], covered_supports=proposal['coverage'])
                    numerical, detail, changed = 'revised', 'native guarded Truth_Revision', True
                else:
                    numerical = 'model-inapplicable' if result['status'] == 'FAIL' or 'zero' in result['detail'] else 'retained-alternative'
                    # Upstream diagnostics include only controlled guard descriptions.
                    detail = result['detail']
        snapshot['alternatives'] = sorted(s['id'] for s in snapshot['supports']
            if self._base_support(s) and s['id'] not in snapshot['covered_supports'])
        if changed: snapshot['revision'] += 1
        return candidate, added, numerical, detail, changed

    @c.boundary
    def submitEvidence(self, request: EvidenceSubmission):
        semantic = self.c.submission(request)
        request = EvidenceSubmission(**{**semantic, 'command': Mutation(**semantic['command'])})
        principal = self._authorize(request.command.scope_ref, 'submitEvidence', request.independence is not None)
        require(request.runtime_selection == self.runtime_selection, 'UNSUPPORTED_PROFILE')
        identity = digest(canonical([principal, request.command.scope_ref, request.command.idempotency_key]))
        fingerprint = digest(canonical([semantic, self.selection]))
        # Persist the EXACT attempt before external reads/calculation. No silent CAS rebasing.
        with closing(self._connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            prior = self._replay(db, identity, fingerprint)
            if prior is not None: return prior
            db.execute('INSERT OR IGNORE INTO attempts VALUES(?,?,?,\'pending\',NULL)',
                       (identity, fingerprint, canonical(semantic).decode()))
            base = self._snapshot(db, request.claim, request.context)
            if base['revision'] != request.expected_revision:
                db.execute("UPDATE attempts SET state='conflict' WHERE id=?", (identity,))
                conflict = True
            else: conflict = False
        require(not conflict, 'CONFLICT')
        self._claim(request.claim)
        record = self._evidence(request)
        working = self.c.detached(base)
        candidate, added, numerical, detail, changed = self._calculate(working, request, record)
        decision = {'decision_id': identity, 'evidence': request.evidence,
                    'support_id': candidate['id'] if candidate else None,
                    'admission': 'admitted' if added else 'duplicate', 'numerical': numerical,
                    'detail': detail, 'snapshot': working}
        self.c.response(self.c.decision, decision, request.claim, request.context, self.runtime_selection)
        with closing(self._connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            self._authorize(request.command.scope_ref, 'submitEvidence', request.independence is not None)
            prior = self._replay(db, identity, fingerprint)
            if prior is not None: return prior
            current = self._snapshot(db, request.claim, request.context)
            if current['revision'] != base['revision']:
                db.execute("UPDATE attempts SET state='conflict' WHERE id=?", (identity,))
                conflict = True
            else:
                if changed:
                    db.execute('INSERT INTO snapshots VALUES(?,?,?)', (self._key(request.claim, request.context),
                               working['revision'], canonical(working).decode()))
                db.execute("UPDATE attempts SET state='complete',decision=? WHERE id=?", (canonical(decision).decode(), identity))
        require(not conflict, 'CONFLICT')
        return decision
