"""X01 completion owner. Each acceptance, reservation and capture commits alone."""
import fcntl
import json
from pathlib import Path
import sqlite3
import time

from . import model_contracts as c
from .contracts import ContractError, canonical, digest, require
from .policy import Policy
from .registry import descriptor_read, selection_token


def now(): return time.time_ns() // 1_000_000


class ModelService:
    @staticmethod
    def inspect(path):
        """Read-only owner observations for the trusted operator, never replay input."""
        cfg=json.loads(Path(path).read_text())['model_completion']; database=Path(cfg['database'])
        if not database.exists():return []
        with sqlite3.connect(database.as_uri()+'?mode=ro',uri=True) as db:
            db.row_factory=sqlite3.Row
            if not db.execute("SELECT 1 FROM sqlite_master WHERE name='model_calls'").fetchone():return []
            return [dict(r) for r in db.execute('SELECT * FROM model_calls ORDER BY rowid')]

    def __init__(self, path, backend, hook=lambda _: None, *, disclosure=None):
        self.policy, self.backend, self.hook = Policy(path), backend, hook
        self.disclosure=disclosure
        self.cfg = self.policy.current()['model_completion']
        cfg = self.cfg
        c.integer(cfg['max_calls'], 1, c.MAX_CALLS)
        c.integer(cfg['expires_ms'], 1)
        require(type(cfg['sessions']) is list and 1 <= len(cfg['sessions']) <= c.MAX_CALLS)
        for session in cfg['sessions']: c.uid(session)
        require(len(set(cfg['sessions'])) == len(cfg['sessions']))
        catalogue = [descriptor_read(d) for d in cfg['catalogue']]
        require(len(catalogue) == 1 and len(catalogue[0].profiles) == 1, 'UNSUPPORTED_PROFILE')
        self.chosen = c.select(catalogue, next(iter(catalogue[0].profiles)))
        self.seal = canonical({k: cfg[k] for k in ('scope', 'sharing', 'sessions', 'max_calls',
                            'expires_ms', 'catalogue', 'disclosure', 'runtime_lock')}).decode()
        path = Path(cfg['database']); path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.lock = open(str(path)+'.lock', 'a')
        try: fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self.lock.close(); require(False, 'OVERLOADED')
        try:
            self.db = sqlite3.connect(path, timeout=.2)
            self.db.row_factory = sqlite3.Row
            tables = {r[0] for r in self.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            require(not tables or tables == {'model_seal', 'model_calls'}, 'UNSUPPORTED_PROFILE')
            if tables: require(self.db.execute('SELECT value FROM model_seal').fetchone()[0] == self.seal, 'CONFLICT')
            self.db.execute('PRAGMA journal_mode=WAL'); self.db.execute('PRAGMA synchronous=FULL')
            self.db.executescript('''CREATE TABLE IF NOT EXISTS model_seal(value TEXT NOT NULL);
              CREATE TABLE IF NOT EXISTS model_calls(id TEXT PRIMARY KEY,session TEXT NOT NULL,
                slot INTEGER NOT NULL,intent TEXT NOT NULL,reserved INTEGER NOT NULL DEFAULT 0,
                response TEXT,captured_ms INTEGER,failure_code TEXT,UNIQUE(session,slot));''')
            if not tables:
                with self.db: self.db.execute('INSERT INTO model_seal VALUES(?)', (self.seal,))
            path.chmod(0o600)
        except BaseException:
            if hasattr(self, 'db'): self.db.close()
            self.lock.close(); raise

    def close(self): self.db.close(); self.lock.close()

    def authorize(self, credential, accepted, operation):
        cfg = self.policy.current()['model_completion']
        require(canonical({k: cfg[k] for k in ('scope','sharing','sessions','max_calls','expires_ms',
                    'catalogue','disclosure','runtime_lock')}).decode() == self.seal, 'CONFLICT')
        principal = self.policy.authenticate(credential)
        require(principal == accepted['principal'] and cfg['scope'] == accepted['scope'], 'UNAUTHORIZED')
        require(cfg['sharing'] == c.PRIVACY and accepted['session'] in cfg['sessions'], 'UNAUTHORIZED')
        require(accepted['selection'] == selection_token(self.chosen), 'UNSUPPORTED_PROFILE')
        from .neoclaw_model_disclosure import disclose
        if self.disclosure is None:disclose(accepted['native_prompt'], cfg['disclosure'], accepted)
        else:self.disclosure(accepted,cfg['disclosure'])
        for method in ('disclose', operation): self.policy.check(principal, accepted['scope'], 'model.'+method)

    def row(self, accepted):
        row = self.db.execute('SELECT * FROM model_calls WHERE id=?', (accepted['id'],)).fetchone()
        if row: require(row['intent'] == canonical(accepted).decode(), 'CONFLICT')
        return row

    def observe(self, accepted):
        row = self.row(accepted)
        captured = row is not None and row['response'] is not None
        value = dict(id=accepted['id'], intent_sha256=digest(canonical(accepted)),
            principal=accepted['principal'], selection=accepted['selection'],
            state='absent' if row is None else 'captured' if captured else 'unknown' if row['reserved'] else 'accepted',
            reserved=0 if row is None else row['reserved'], response=json.loads(row['response']) if captured else None,
            captured_ms=row['captured_ms'] if captured else None,
            late=captured and row['captured_ms'] > accepted['deadline_ms'],
            failure_code=row['failure_code'] if row else None)
        return c.observation(value, accepted)

    def invoke(self, credential, request):
        c.request(request); accepted, op = request['intent'], request['operation']
        self.authorize(credential, accepted, op)
        if op == 'authorize': value = {'authorized': True}
        elif op == 'observe': value = self.observe(accepted)
        else:
            row = self.row(accepted)
            if row is None:
                require(now() < min(accepted['deadline_ms'], self.cfg['expires_ms']), 'DEADLINE_EXCEEDED')
                require(accepted['deadline_ms'] <= now()+c.deadline_limit(accepted['profile']), 'INVALID_ARGUMENT')
                with self.db:
                    self.db.execute('BEGIN IMMEDIATE')
                    require(self.db.execute('SELECT count(*) FROM model_calls').fetchone()[0] < self.cfg['max_calls'], 'OVERLOADED')
                    require(self.db.execute('SELECT 1 FROM model_calls WHERE session=? AND slot=?',
                        (accepted['session'], accepted['slot'])).fetchone() is None, 'CONFLICT')
                    self.db.execute('INSERT INTO model_calls(id,session,slot,intent) VALUES(?,?,?,?)',
                        (accepted['id'], accepted['session'], accepted['slot'], canonical(accepted).decode()))
                self.hook('after_model_acceptance'); row = self.row(accepted)
            if not row['reserved']:
                require(now() < min(accepted['deadline_ms'], self.cfg['expires_ms']), 'DEADLINE_EXCEEDED')
                with self.db: self.db.execute('UPDATE model_calls SET reserved=1 WHERE id=?', (accepted['id'],))
                self.hook('after_model_reservation')
                self.authorize(credential, accepted, 'complete')
                # No retry on exceptions, malformed results or process loss. The
                # durable reservation remains spent, even if no call escaped.
                try: response = c.completion(self.backend.complete(c.CompletionInput(**accepted)))
                except ContractError as exc:
                    code = exc.code if exc.code in ('NOT_AVAILABLE','INVALID_ARGUMENT','UNSUPPORTED_PROFILE','DEADLINE_EXCEEDED') else 'NOT_AVAILABLE'
                    with self.db:self.db.execute('UPDATE model_calls SET failure_code=? WHERE id=?', (code,accepted['id']))
                    raise
                self.hook('after_model_backend_response')
                with self.db: self.db.execute('UPDATE model_calls SET response=?,captured_ms=? WHERE id=?',
                    (canonical(response).decode(), now(), accepted['id']))
                self.hook('after_model_provider_capture')
            value = self.observe(accepted)
        self.authorize(credential, accepted, op)
        return dict(request_sha256=digest(canonical(request)), principal=accepted['principal'], value=value)
