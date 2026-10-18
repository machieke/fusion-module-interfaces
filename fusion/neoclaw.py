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
from . import neoclaw_search_contracts as s, neoclaw_operations as ops
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
        require(self.config['profile'] in (c.PROFILE, ops.COMPOSITION) and self.config['sharing'] == 'generated-shareable', 'UNSUPPORTED_PROFILE')
        paths = [Path(self.config[k]).resolve() for k in ('database', 'atoms_database', 'messages_database')]
        require(len(set(paths)) == 3, 'UNSUPPORTED_PROFILE')
        self.policy = Policy(config_path)
        self.chosen = c.selected(c.catalogue(self.config.get('atom_provider', 'detta'), self.config.get('provider', 'neoclaw-native')))
        self.profiles = {c.PROFILE: self.chosen}
        if self.config['profile'] == ops.COMPOSITION:
            self.profiles[s.PROFILE] = s.selected(s.catalogue(self.config.get('atom_provider', 'detta')))
            require(type(self.config['search_queries']) is list, 'UNSUPPORTED_PROFILE')
            for query in self.config['search_queries']: s.arguments(dict(query=query, max_results=10))
        self.hook, self.kernel = hook, kernel
        if self.config.get('atom_provider', 'detta') == 'detta':
            raw_atoms = AtomOwner(self.config['atoms_database'], DettaStorage(self.config['detta_binary'], self.config['da_root']))
        else:
            require(self.config['atom_provider'] == 'fixture-files', 'UNSUPPORTED_PROFILE')
            raw_atoms = FileAtomFixture(self.config['atom_records'], self.config['da_root'])
        self.atoms_for = lambda principal, chosen=None: AuthorizedAtoms(raw_atoms, self.policy, principal,
                                                                      (chosen or self.chosen)['atom.storage'])
        self.mailbox = MessageOwner(self.config['messages_database'], self.policy, self.config.get('capacity', 8))
        self.db = connect(self.config['database'])
        # No migration: only an empty or already S01-owned journal is admitted.
        tables = {r[0] for r in self.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        require(not tables or 's01_work' in tables, 'UNSUPPORTED_PROFILE')
        if self.config['profile'] == ops.COMPOSITION:
            require(not tables or 'neoclaw_composition' in tables, 'UNSUPPORTED_PROFILE')
            self.db.execute('CREATE TABLE IF NOT EXISTS neoclaw_composition (binding TEXT NOT NULL)')
            expected = canonical(dict(profile=ops.COMPOSITION, selections={p:{k:selection_token(v) for k,v in chosen.items()}
                for p,chosen in self.profiles.items()}, search=self.config['search'])).decode()
            with self.db:
                old = self.db.execute('SELECT binding FROM neoclaw_composition').fetchone()
                if old: require(old[0] == expected, 'UNSUPPORTED_PROFILE')
                else: self.db.execute('INSERT INTO neoclaw_composition VALUES(?)', (expected,))
        else:
            require('neoclaw_composition' not in tables, 'UNSUPPORTED_PROFILE')
        self.db.executescript(SCHEMA + WORK_SCHEMA)
        self.execution = NalExecutionOwner(self.db, self.policy, self.atoms_for('worker'), self.mailbox, self.config.get('capacity', 8))

    def close(self):
        self.db.close()

    def selected(self, request):
        require(type(request) is dict and type(request.get('interface_ref')) is dict)
        name = request['interface_ref'].get('id')
        require(type(name) is str and name in ('execution', 'atom.storage', 'agent.messaging'), 'UNSUPPORTED_OPERATION')
        matches = [chosen for chosen in self.profiles.values() if request.get('selection') == selection_token(chosen[name])]
        require(len(matches) == 1, 'UNSUPPORTED_PROFILE')
        chosen = matches[0]
        module = ops.from_chosen(chosen)
        module.validate(request, chosen)
        return module, chosen

    def authorize_search(self, principal, scope, request=None):
        self.policy.check(principal, scope, 'execution.web_search')
        # Fresh local disclosure policy, not the configuration snapshot at startup.
        current = json.loads(self.path.read_text())
        if request is not None:
            require(request['body']['arguments']['query'] in current.get('search_queries', []), 'UNAUTHORIZED')

    def authorize(self, principal, request, module):
        scope = request['scope_ref']
        self.policy.check(principal, scope, 'execution.submit')
        self.policy.route(scope, request['reply_route'], principal)
        if module is s: self.authorize_search(principal, scope, request)

    def invoke(self, credential, request):
        principal = self.policy.authenticate(credential)
        module, chosen = self.selected(request)
        name, op = module.validate(request, chosen)
        scope, body = request['scope_ref'], request['body']
        self.policy.check(principal, scope, name + '.' + op)
        if module is s: self.authorize_search(principal, scope)
        if name == 'execution' and op == 'submit':
            self.authorize(principal, request, module)
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
            row = self.db.execute('SELECT request FROM jobs WHERE id=?', (body['job_id'],)).fetchone()
            if row is not None:
                original = json.loads(row['request'])
                require(original['profile'] == module.PROFILE, 'UNSUPPORTED_PROFILE')
                if module is s: self.authorize_search(principal, scope, original)
            response = self.execution.read(principal, scope, body['job_id'], op == 'result')
            if op == 'status':
                work = self.db.execute('SELECT attempts,failure_reason FROM s01_work WHERE job_id=?', (body['job_id'],)).fetchone()
                response.update(attempts=work['attempts'], failure_reason=work['failure_reason'])
            return response
        if name == 'atom.storage':
            # Check this owner's mapping even on the old storage descriptor: an
            # S01 selection must not bypass S02 operation/disclosure revocation.
            rows = self.db.execute('SELECT owner,request,result FROM jobs WHERE scope=? AND result IS NOT NULL', (scope,))
            source = next((r for r in rows if json.loads(r['result'])['ref'] == body['ref']), None)
            original = json.loads(source['request']) if source else None
            if module is s or (original and original['profile'] == s.PROFILE):
                require(original is not None and original['profile'] == s.PROFILE and module is s, 'UNSUPPORTED_PROFILE')
                require(source['owner'] == principal, 'UNAUTHORIZED')
                self.authorize(principal, original, module)
            value = self.atoms_for(principal, chosen).get(body['ref'])
            return dict(ref=value.ref, content_type=value.content_type, bytes=encode(value.bytes))
        messages = MessagingSession(self.mailbox, self.policy, principal, self.atoms_for(principal, chosen), request['message_id'])
        if op == 'poll':
            delivery = messages.poll(scope, body['route'])
            if delivery:
                row = self.db.execute('SELECT request FROM jobs WHERE id=? AND owner=?', (delivery['delivery_id'], principal)).fetchone()
                original = json.loads(row['request']) if row else None
                if module is s or (original and original['profile'] == s.PROFILE):
                    require(original is not None, 'UNAUTHORIZED')
                    require(original['profile'] == s.PROFILE and module is s, 'UNSUPPORTED_PROFILE')
                    self.authorize(principal, original, module)
            return dict(delivery=delivery)
        row = self.db.execute('SELECT request FROM jobs WHERE id=? AND owner=?', (body['delivery_id'], principal)).fetchone()
        original = json.loads(row['request']) if row else None
        if module is s or (original and original['profile'] == s.PROFILE):
            require(original is not None, 'UNAUTHORIZED')
            require(original['profile'] == s.PROFILE and module is s, 'UNSUPPORTED_PROFILE')
            self.authorize(principal, original, module)
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
        module, chosen = self.selected(request)
        try:
            self.authorize(row['owner'], request, module)
            if module is s: self.authorize_search('worker', scope, request)
            self.policy.check('worker', scope, 'atom.storage.create')
            work = self.db.execute('SELECT * FROM s01_work WHERE job_id=?', (ident,)).fetchone()
            if work['output']:
                output = module.result(json.loads(work['output']), request, chosen)
            else:
                require(time.time()*1000 < request['deadline_ms'], 'DEADLINE_EXCEEDED')
                if work['attempts'] >= request['body']['max_attempts']:
                    reason = 'attempt-budget-exhausted'
                    raise ContractError('NOT_AVAILABLE')
                with self.db:
                    self.db.execute('UPDATE s01_work SET attempts=attempts+1 WHERE job_id=?', (ident,))
                self.hook('after_reservation')
                if module is s:
                    from .adapters.neoclaw_search import NativeWebSearch, SearchFailure
                    try:
                        observation = NativeWebSearch(self.config['search']).observe(request['body']['arguments'], request['deadline_ms'])
                        self.hook('after_compute')
                        observation['captured_ms'] = int(time.time()*1000)
                        output = s.result(dict(profile=s.PROFILE, operation=s.OPERATION, provider=chosen['execution'].provider,
                            selection=selection_token(chosen['execution']), request_digest=c.fingerprint(request), job_id=ident,
                            arguments=request['body']['arguments'], observation=observation,
                            representation=s.render(observation['items'])), request, chosen)
                    except SearchFailure as exc:
                        reason = exc.reason
                        raise
                    except ContractError as exc:
                        reason = 'upstream-timeout' if exc.code == 'DEADLINE_EXCEEDED' else 'invalid-output' if exc.code == 'NOT_AVAILABLE' else None
                        raise
                    except OSError:
                        reason = 'upstream-unavailable'
                        raise ContractError('NOT_AVAILABLE') from None
                    except (KeyError, TypeError, ValueError):
                        reason = 'invalid-output'
                        raise ContractError('NOT_AVAILABLE') from None
                else:
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
                        selection=selection_token(chosen['pln.kernel']), request_digest=c.fingerprint(request),
                        premises=request['body']['premises'], **computed), request, chosen)
                with self.db:
                    self.db.execute('UPDATE s01_work SET output=? WHERE job_id=?', (canonical(output).decode(), ident))
                self.hook('after_output_commit')
                if module is s: self.hook('after_search_capture')
            # Closure of previously persisted numerical work may finish after the
            # deadline; no new computation or reservation is started on that path.
            self.authorize(row['owner'], request, module)
            if module is s: self.authorize_search('worker', scope, request)
            result = self.atoms_for('worker', chosen).create(Mutation(scope, 'nal-result/' + ident),
                                                            ops.content_type(module), canonical(output))
            self.hook('after_result_persist')
        except ContractError as exc:
            if exc.code in {'OVERLOADED', 'NOT_AVAILABLE'} and reason is None:
                return dict(worked=False, pending=True, error=exc.code)
            error = exc.code
        # Current authority is rechecked at the final owner boundary too.
        try:
            self.authorize(row['owner'], request, module)
        except ContractError as exc:
            error, result, reason = exc.code, None, None
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
