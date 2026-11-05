"""X01 completion owner. Each acceptance, reservation and capture commits alone."""
from .native_telemetry import traced,span
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


def configuration_seal(cfg):
    """Historical seal bytes; configuration changes never migrate owner state."""
    return canonical({k: cfg[k] for k in ('scope', 'sharing', 'sessions', 'max_calls',
        'expires_ms', 'catalogue', 'disclosure', 'runtime_lock')}).decode()


def inspect_journal(path):
    """Startup-only compatibility check, without creating an owner or backend.

    The service's exclusive owner lock surrounds startup. Read only existing
    state; an absent journal does not reserve a call or create an empty database.
    The normal owner checks the same seal again when it acquires its own lock.
    """
    cfg = json.loads(Path(path).read_bytes())['model_completion']
    from .pilot_model_clock import expected_tables, inspect as clock_inspect
    expected_owner_tables=expected_tables(cfg)
    database = Path(cfg['database']).resolve()
    if not database.exists(): return 'ABSENT'
    expected = configuration_seal(cfg)
    with sqlite3.connect(database.as_uri()+'?mode=ro', uri=True, timeout=.2) as db:
        db.execute('PRAGMA query_only=ON')
        tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        require(tables == expected_owner_tables, 'UNSUPPORTED_PROFILE')
        clock_inspect(db,cfg)
        rows = db.execute('SELECT value FROM model_seal LIMIT 2').fetchall()
        require(len(rows) == 1 and rows[0][0] == expected, 'CONFLICT')
    return 'COMPATIBLE'


class ModelService:
    @staticmethod
    def inspect(path):
        """Read-only owner observations for the trusted operator, never replay input."""
        cfg=json.loads(Path(path).read_text())['model_completion']; database=Path(cfg['database'])
        if not database.exists():return []
        with sqlite3.connect(database.as_uri()+'?mode=ro',uri=True) as db:
            db.row_factory=sqlite3.Row
            if not db.execute("SELECT 1 FROM sqlite_master WHERE name='model_calls'").fetchone():return []
            rows=[dict(r) for r in db.execute('SELECT * FROM model_calls ORDER BY rowid')]
            if cfg.get('owner_clock') is not None:
                from .pilot_model_clock import inspect as clock_inspect
                clock=clock_inspect(db,cfg)
                captures={r['id']:dict(raw_ms=json.loads(r['raw_ms']),prior_water_ms=r['prior_water'],valid=bool(r['valid'])) for r in db.execute('SELECT * FROM pilot_model_capture_clocks')}
                for row in rows:row['owner_clock']=dict(clock,capture=captures.get(row['id']))
            return rows

    def __init__(self, path, backend, hook=lambda _: None, *, disclosure=None, contracts=c, execution_authority=None):
        self.c = contracts
        self.policy, self.backend, self.hook = Policy(path), backend, hook
        self.disclosure=disclosure
        self.execution_authority=execution_authority
        self.cfg = self.policy.current()['model_completion']
        cfg = self.cfg
        from .pilot_model_clock import selection as clock_selection
        self.owner_clock=clock_selection(cfg)
        self.c.integer(cfg['max_calls'], 1, self.c.MAX_CALLS)
        self.c.integer(cfg['expires_ms'], 1)
        self.validate_sessions(cfg['sessions'])
        catalogue = [descriptor_read(d) for d in cfg['catalogue']]
        require(len(catalogue) == 1 and len(catalogue[0].profiles) == 1, 'UNSUPPORTED_PROFILE')
        self.chosen = self.c.select(catalogue, next(iter(catalogue[0].profiles)))
        self.seal = configuration_seal(cfg)
        path = Path(cfg['database']); path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.lock = open(str(path)+'.lock', 'a')
        try: fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self.lock.close(); require(False, 'OVERLOADED')
        try:
            self.db = sqlite3.connect(path, timeout=.2)
            self.db.row_factory = sqlite3.Row
            tables = {r[0] for r in self.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            from .pilot_model_clock import expected_tables, initialize as clock_initialize, inspect as clock_inspect
            require(not tables or tables == expected_tables(cfg), 'UNSUPPORTED_PROFILE')
            if tables:
                require(self.db.execute('SELECT value FROM model_seal').fetchone()[0] == self.seal, 'CONFLICT')
                clock_inspect(self.db,cfg)
            self.db.execute('PRAGMA journal_mode=WAL'); self.db.execute('PRAGMA synchronous=FULL')
            self.db.executescript('''CREATE TABLE IF NOT EXISTS model_seal(value TEXT NOT NULL);
              CREATE TABLE IF NOT EXISTS model_calls(id TEXT PRIMARY KEY,session TEXT NOT NULL,
                slot INTEGER NOT NULL,intent TEXT NOT NULL,reserved INTEGER NOT NULL DEFAULT 0,
                response TEXT,captured_ms INTEGER,failure_code TEXT,UNIQUE(session,slot));''')
            if not tables:
                with self.db:
                    self.db.execute('INSERT INTO model_seal VALUES(?)', (self.seal,))
                    clock_initialize(self.db,cfg)
            path.chmod(0o600)
        except BaseException:
            if hasattr(self, 'db'): self.db.close()
            self.lock.close(); raise

    def close(self): self.db.close(); self.lock.close()

    def validate_sessions(self, sessions):
        if type(sessions) is list:
            require(1 <= len(sessions) <= self.c.MAX_CALLS)
            for session in sessions:self.c.uid(session)
            require(len(set(sessions)) == len(sessions))
            return
        require(type(sessions) is dict and set(sessions)=={'profile','principals','max_sessions'},'UNSUPPORTED_PROFILE')
        require(sessions['profile']=='bounded-authenticated-model-sessions/1','UNSUPPORTED_PROFILE')
        require(type(sessions['principals']) is list and 1<=len(sessions['principals'])<=2)
        require(len(set(sessions['principals']))==len(sessions['principals']))
        require(all(type(x) is str and 1<=len(x)<=80 for x in sessions['principals']))
        require(type(sessions['max_sessions']) is int and 1<=sessions['max_sessions']<=16)

    def session_authority(self, accepted, *, admitting=False):
        sessions=self.cfg['sessions']
        if type(sessions) is list:
            require(accepted['session'] in sessions,'UNAUTHORIZED');return
        require(accepted['principal'] in sessions['principals'],'UNAUTHORIZED')
        rows=self.db.execute('SELECT intent FROM model_calls WHERE session=?',(accepted['session'],)).fetchall()
        require(all(json.loads(r[0])['principal']==accepted['principal'] for r in rows),'UNAUTHORIZED')
        if admitting and not rows:
            require(self.db.execute('SELECT count(DISTINCT session) FROM model_calls').fetchone()[0]<sessions['max_sessions'],'OVERLOADED')

    @traced('provider.model.authorize')
    def authorize(self, credential, accepted, operation):
        cfg = self.policy.current()['model_completion']
        require(configuration_seal(cfg) == self.seal and cfg.get('owner_clock') == self.owner_clock, 'CONFLICT')
        principal = self.policy.authenticate(credential)
        require(principal == accepted['principal'] and cfg['scope'] == accepted['scope'], 'UNAUTHORIZED')
        require(cfg['sharing'] == self.c.PRIVACY, 'UNAUTHORIZED')
        self.session_authority(accepted)
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
        if captured and self.owner_clock:
            from .pilot_model_clock import checked_capture
            checked_capture(self.db,accepted['id'])
        value = dict(id=accepted['id'], intent_sha256=digest(canonical(accepted)),
            principal=accepted['principal'], selection=accepted['selection'],
            state='absent' if row is None else 'captured' if captured else 'unknown' if row['reserved'] else 'accepted',
            reserved=0 if row is None else row['reserved'], response=json.loads(row['response']) if captured else None,
            captured_ms=row['captured_ms'] if captured else None,
            late=captured and row['captured_ms'] > accepted['deadline_ms'],
            failure_code=row['failure_code'] if row else None)
        return self.c.observation(value, accepted)

    def clock_guard(self,phase,accepted):
        from .pilot_model_clock import guard
        sampled=guard(self.db,now(),phase,accepted['id'])
        require(sampled < min(accepted['deadline_ms'],self.cfg['expires_ms']),'DEADLINE_EXCEEDED')
        return sampled

    @traced('provider.model.invoke',request=2)
    def invoke(self, credential, request):
        self.c.request(request); accepted, op = request['intent'], request['operation']
        self.authorize(credential, accepted, op)
        if op == 'authorize': value = {'authorized': True}
        elif op == 'observe': value = self.observe(accepted)
        else:
            row = self.row(accepted)
            if self.execution_authority is not None and (row is None or not row['reserved']):
                self.execution_authority(accepted)
            if row is None:
                if self.owner_clock:self.clock_guard('acceptance',accepted)
                require(now() < min(accepted['deadline_ms'], self.cfg['expires_ms']), 'DEADLINE_EXCEEDED')
                require(accepted['deadline_ms'] <= now()+self.c.deadline_limit(accepted['profile']), 'INVALID_ARGUMENT')
                with span('provider.model.acceptance'), self.db:
                    self.db.execute('BEGIN IMMEDIATE')
                    self.session_authority(accepted, admitting=True)
                    require(self.db.execute('SELECT count(*) FROM model_calls').fetchone()[0] < self.cfg['max_calls'], 'OVERLOADED')
                    require(self.db.execute('SELECT 1 FROM model_calls WHERE session=? AND slot=?',
                        (accepted['session'], accepted['slot'])).fetchone() is None, 'CONFLICT')
                    self.db.execute('INSERT INTO model_calls(id,session,slot,intent) VALUES(?,?,?,?)',
                        (accepted['id'], accepted['session'], accepted['slot'], canonical(accepted).decode()))
                self.hook('after_model_acceptance'); row = self.row(accepted)
            if not row['reserved']:
                if self.owner_clock:self.clock_guard('reservation',accepted)
                if self.execution_authority is not None:self.execution_authority(accepted)
                require(now() < min(accepted['deadline_ms'], self.cfg['expires_ms']), 'DEADLINE_EXCEEDED')
                with span('provider.model.reservation'), self.db: self.db.execute('UPDATE model_calls SET reserved=1 WHERE id=?', (accepted['id'],))
                self.hook('after_model_reservation')
                self.authorize(credential, accepted, 'complete')
                # No retry on exceptions, malformed results or process loss. The
                # durable reservation remains spent, even if no call escaped.
                try:
                    if self.owner_clock:self.clock_guard('backend-entry',accepted)
                    with span('provider.model.backend'):
                        response = self.c.completion(self.backend.complete(self.c.CompletionInput(**accepted)))
                except ContractError as exc:
                    code = exc.code if exc.code in ('NOT_AVAILABLE','INVALID_ARGUMENT','UNSUPPORTED_PROFILE','DEADLINE_EXCEEDED') else 'NOT_AVAILABLE'
                    with self.db:self.db.execute('UPDATE model_calls SET failure_code=? WHERE id=?', (code,accepted['id']))
                    raise
                self.hook('after_model_backend_response')
                raw_capture_time=now()
                with span('provider.model.capture'), self.db:
                    self.db.execute('BEGIN IMMEDIATE')
                    self.db.execute('UPDATE model_calls SET response=?,captured_ms=? WHERE id=?',
                        (canonical(response).decode(), raw_capture_time, accepted['id']))
                    if self.owner_clock:
                        from .pilot_model_clock import capture
                        capture(self.db,accepted['id'],raw_capture_time)
                self.hook('after_model_provider_capture')
            value = self.observe(accepted)
        self.authorize(credential, accepted, op)
        return dict(request_sha256=digest(canonical(request)), principal=accepted['principal'], value=value)
