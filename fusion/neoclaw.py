"""S01 fixed-operation execution composition. Existing owners and M1 ports reused.

No changes to the old service/worker, private cognition, or five-premise PLN.
The only numerical dependency is the pure TruthDeduction port.
"""
import fcntl
import json
from pathlib import Path
import sqlite3
import time

from . import neoclaw_contracts as c
from .adapters.detta import DettaStorage
from .adapters.fixture_atoms import FileAtomFixture
from .atoms import AtomOwner, AuthorizedAtoms
from .contracts import ContractError, canonical, digest, encode, require
from .execution import ExecutionOwner, EVIDENCE
from .messaging import MessageOwner, MessagingSession
from .policy import Policy
from .ports import Mutation
from .registry import selection_token
from .service import SCHEMA


WORK_SCHEMA = '''CREATE TABLE IF NOT EXISTS s01_work (
 job_id TEXT PRIMARY KEY, attempts INTEGER NOT NULL DEFAULT 0,
 output TEXT, failure_reason TEXT);'''


def connect(path):
    db = sqlite3.connect(path, timeout=.2)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA journal_mode=WAL')
    db.execute('PRAGMA synchronous=FULL')
    return db


def identity(principal, request):
    return c.mutation_identity(principal, request)


def job_id(principal, request):
    return c.job_id(principal, request)


class NalExecutionOwner(ExecutionOwner):
    """Reuse M1 status/result ownership and completion-outbox delivery; fixed S01 work."""
    def submit_nal(self, principal, request):
        scope = request['scope_ref']
        self.policy.check(principal, scope, 'execution.submit')
        self.policy.route(scope, request['reply_route'], principal)
        self.policy.check('worker', scope, 'atom.storage.create')
        pending = self.db.execute("SELECT count(*) FROM jobs WHERE state='queued'").fetchone()[0]
        pending += self.db.execute('SELECT count(*) FROM outbox WHERE sent=0').fetchone()[0]
        require(pending < self.capacity, 'OVERLOADED')
        require(self.db.execute('SELECT count(*) FROM jobs').fetchone()[0] < c.MAX_REQUESTS, 'OVERLOADED')
        ident = job_id(principal, request)
        self.db.execute('INSERT INTO jobs(id,scope,owner,request,state) VALUES(?,?,?,?,?)',
                        (ident, scope, principal, canonical(request).decode(), 'queued'))
        self.db.execute('INSERT INTO s01_work(job_id) VALUES(?)', (ident,))
        return dict(job_id=ident, execution='queued', acceptance='process-restart', evidence=dict(EVIDENCE),
                    scope_ref=scope, correlation_id=request['correlation_id'], reply_route=request['reply_route'],
                    completion_delivery='not-observed', chain=None)


class NalService:
    def __init__(self, config_path, hook=lambda _: None, kernel=None):
        self.path = Path(config_path)
        self.config = json.loads(self.path.read_text())
        require(self.config['profile'] == c.PROFILE and self.config['sharing'] == 'generated-shareable', 'UNSUPPORTED_PROFILE')
        paths = [Path(self.config[k]).resolve() for k in ('database', 'atoms_database', 'messages_database')]
        require(len(set(paths)) == 3, 'UNSUPPORTED_PROFILE')
        self.policy = Policy(config_path)
        self.chosen = c.selected(c.catalogue(self.config.get('atom_provider', 'detta'), self.config.get('provider', 'neoclaw-native')))
        self.hook, self.kernel = hook, kernel
        if self.config.get('atom_provider', 'detta') == 'detta':
            raw_atoms = AtomOwner(self.config['atoms_database'], DettaStorage(self.config['detta_binary'], self.config['da_root']))
        else:
            require(self.config['atom_provider'] == 'fixture-files', 'UNSUPPORTED_PROFILE')
            raw_atoms = FileAtomFixture(self.config['atom_records'], self.config['da_root'])
        self.atoms_for = lambda principal: AuthorizedAtoms(raw_atoms, self.policy, principal, self.chosen['atom.storage'])
        self.mailbox = MessageOwner(self.config['messages_database'], self.policy, self.config.get('capacity', 8))
        self.db = connect(self.config['database'])
        # No migration: only an empty or already S01-owned journal is admitted.
        tables = {r[0] for r in self.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        require(not tables or 's01_work' in tables, 'UNSUPPORTED_PROFILE')
        self.db.executescript(SCHEMA + WORK_SCHEMA)
        self.execution = NalExecutionOwner(self.db, self.policy, self.atoms_for('worker'), self.mailbox, self.config.get('capacity', 8))

    def close(self):
        self.db.close()

    def invoke(self, credential, request):
        principal = self.policy.authenticate(credential)
        name, op = c.validate(request, self.chosen)
        scope, body = request['scope_ref'], request['body']
        self.policy.check(principal, scope, name + '.' + op)
        if name == 'execution' and op == 'submit':
            self.policy.route(scope, request['reply_route'], principal)
            key, fingerprint = identity(principal, request), c.fingerprint(request)
            with self.db:
                self.db.execute('BEGIN IMMEDIATE')
                old = self.db.execute('SELECT * FROM mutations WHERE identity=?', (key,)).fetchone()
                if old:
                    require(old['fingerprint'] == fingerprint, 'CONFLICT')
                    return json.loads(old['response'])
                require(time.time()*1000 < request['deadline_ms'], 'DEADLINE_EXCEEDED')
                accepted = self.execution.submit_nal(principal, request)
                self.db.execute('INSERT INTO mutations VALUES(?,?,?)', (key, fingerprint, canonical(accepted).decode()))
            self.hook('after_acceptance')
            return accepted
        if name == 'execution':
            response = self.execution.read(principal, scope, body['job_id'], op == 'result')
            if op == 'status':
                work = self.db.execute('SELECT attempts,failure_reason FROM s01_work WHERE job_id=?', (body['job_id'],)).fetchone()
                response.update(attempts=work['attempts'], failure_reason=work['failure_reason'])
            return response
        if name == 'atom.storage':
            value = self.atoms_for(principal).get(body['ref'])
            return dict(ref=value.ref, content_type=value.content_type, bytes=encode(value.bytes))
        messages = MessagingSession(self.mailbox, self.policy, principal, self.atoms_for(principal), request['message_id'])
        if op == 'poll':
            return dict(delivery=messages.poll(scope, body['route']))
        return messages.ack(Mutation(scope, request['idempotency_key'], c.fingerprint(request)), body['route'], body['delivery_id'])

    def work(self):
        # Same-host single worker admission: a killed process releases the lock.
        with open(self.config['database'] + '.worker-lock', 'a+b') as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise ContractError('OVERLOADED') from None
            return self._work()

    def _work(self):
        row = self.db.execute("SELECT * FROM jobs WHERE state='queued' ORDER BY seq LIMIT 1").fetchone()
        if row is None:
            return dict(worked=False)
        request, ident, scope = json.loads(row['request']), row['id'], row['scope']
        output, result, error, reason = None, None, None, None
        try:
            c.validate(request, self.chosen)
            self.policy.check(row['owner'], scope, 'execution.submit')
            self.policy.route(scope, request['reply_route'], row['owner'])
            self.policy.check('worker', scope, 'atom.storage.create')
            work = self.db.execute('SELECT * FROM s01_work WHERE job_id=?', (ident,)).fetchone()
            if work['output']:
                output = c.result(json.loads(work['output']), request, self.chosen)
            else:
                require(time.time()*1000 < request['deadline_ms'], 'DEADLINE_EXCEEDED')
                if work['attempts'] >= request['body']['max_attempts']:
                    reason = 'attempt-budget-exhausted'
                    raise ContractError('NOT_AVAILABLE')
                with self.db:
                    self.db.execute('UPDATE s01_work SET attempts=attempts+1 WHERE job_id=?', (ident,))
                self.hook('after_reservation')
                if self.kernel is None:
                    from .adapters.neoclaw_nal import NativeTruthDeduction
                    self.kernel = NativeTruthDeduction(self.config['runtime'])
                computed = self.kernel.applyTruth(request['body']['premises'], request['deadline_ms'])
                self.hook('after_compute')
                try:
                    c.fields(computed, 'representation truth')
                except ContractError:
                    raise ContractError('NOT_AVAILABLE') from None
                output = c.result(dict(profile=c.PROFILE, operation=c.OPERATION, runtime=c.RUNTIME,
                    selection=selection_token(self.chosen['pln.kernel']), request_digest=c.fingerprint(request),
                    premises=request['body']['premises'], **computed), request, self.chosen)
                with self.db:
                    self.db.execute('UPDATE s01_work SET output=? WHERE job_id=?', (canonical(output).decode(), ident))
                self.hook('after_output_commit')
            # Closure of previously persisted numerical work may finish after the
            # deadline; no new computation or reservation is started on that path.
            result = self.atoms_for('worker').create(Mutation(scope, 'nal-result/' + ident),
                                                   'application/neoclaw-nal-result', canonical(output))
            self.hook('after_result_persist')
        except ContractError as exc:
            if exc.code in {'OVERLOADED', 'NOT_AVAILABLE'} and reason is None:
                return dict(worked=False, pending=True, error=exc.code)
            error = exc.code
        # Current authority is rechecked at the final owner boundary too.
        try:
            self.policy.check(row['owner'], scope, 'execution.submit')
            self.policy.route(scope, request['reply_route'], row['owner'])
        except ContractError as exc:
            error, result = exc.code, None
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            self.db.execute('UPDATE jobs SET state=?,result=?,error=? WHERE id=?',
                ('failed' if error else 'succeeded', canonical(result).decode() if result else None, error, ident))
            self.db.execute('UPDATE s01_work SET failure_reason=? WHERE job_id=?', (reason, ident))
            completion = dict(job_id=ident, correlation_id=request['correlation_id'], causation_id=request['message_id'], result=result, error=error)
            self.db.execute('INSERT INTO outbox(id,scope,route,body) VALUES(?,?,?,?)',
                (ident, scope, request['reply_route'], canonical(completion).decode()))
        self.hook('after_completion_commit')
        return dict(worked=True, job_id=ident, execution='failed' if error else 'succeeded')

    def flush(self):
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            return self.execution.flush(self.hook)
