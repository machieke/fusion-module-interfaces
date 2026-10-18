"""S01 application occurrences, in caller-owned storage; no provider DB access.

Each transaction is independent of Caller and provider commits. No remote
operation/profile changes, model exactly-once claim, or general tool recovery.
"""
import fcntl
import json
from pathlib import Path
import sqlite3
import time
import uuid

from .contracts import canonical, require
from . import neoclaw_contracts as c
from . import neoclaw_search_contracts as s, neoclaw_operations as ops
from .neoclaw_client import Caller
from . import vector_contracts as v
from .registry import selection_token


def selected_expression(command):
    import re
    return (isinstance(command, list) and len(command) >= 2 and command[0] == 'metta'
            and isinstance(command[1], str)
            and re.match(r'^\s*\(\s*Truth_Deduction(?:\s|\))', command[1]) is not None)


def caller_binding(caller):
    value = {k: caller.config[k] for k in ('database', 'principal', 'scope', 'reply_route', 'sharing', 'max_calls', 'max_attempts')}
    value['selections'] = {k: selection_token(v) for k, v in caller.chosen.items()}
    return value


class Application:
    def __init__(self, config_file, hook=lambda _: None):
        self.config = json.loads(Path(config_file).read_text())
        self.hook, self.current = hook, None
        require(self.config['composition'] in ('controlled-native-loop/1', ops.APPLICATION, v.APPLICATION), 'UNSUPPORTED_PROFILE')
        self.memory_enabled = self.config['composition'] == v.APPLICATION
        self.two_operations = self.config['composition'] in (ops.APPLICATION, v.APPLICATION)
        require(type(self.config['turn_limit']) is int and 1 <= self.config['turn_limit'] <= c.MAX_REQUESTS)
        require(type(self.config['invocation_timeout_ms']) is int and 1 <= self.config['invocation_timeout_ms'] <= 30000)
        caller = Caller(self.config['caller_config'])
        try:
            cfg = caller.config
            binding = caller_binding(caller)
            if self.two_operations:
                search_caller = Caller(self.config['caller_config'], profile=s.PROFILE)
                try: binding.update(composition=ops.APPLICATION, search=caller_binding(search_caller))
                finally: search_caller.close()
            if self.memory_enabled:
                from .neoclaw_memory import configuration
                binding.update(composition=v.APPLICATION, memory=configuration(self.config['memory_read_config'])[2])
            binding.update({k: self.config[k] for k in ('turn_limit', 'invocation_timeout_ms')})
            self.lock = open(cfg['database'] + '.application.lock', 'a')
            try: fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                self.lock.close()
                require(False, 'OVERLOADED')
            self.db = sqlite3.connect(cfg['database'], timeout=.2)
        finally:
            caller.close()
        try:
            self.binding = binding
            self.db.row_factory = sqlite3.Row
            self.db.execute('PRAGMA journal_mode=WAL')
            self.db.execute('PRAGMA synchronous=FULL')
            if self.two_operations:
                # No adoption of pre-existing standalone caller rows as app intents.
                has_session = self.db.execute("SELECT 1 FROM sqlite_master WHERE name='app_session'").fetchone()
                require(has_session or self.db.execute('SELECT count(*) FROM caller_requests').fetchone()[0] == 0,
                        'UNSUPPORTED_PROFILE')
            self.db.executescript('''
                CREATE TABLE IF NOT EXISTS app_session (id TEXT PRIMARY KEY, binding TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS app_turns (
                    id INTEGER PRIMARY KEY, response TEXT NOT NULL, commands TEXT NOT NULL, projection TEXT);
                CREATE TABLE IF NOT EXISTS app_occurrences (
                    turn INTEGER NOT NULL, position INTEGER NOT NULL, id TEXT UNIQUE NOT NULL,
                    premises TEXT, deadline INTEGER NOT NULL, result TEXT, done INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY(turn, position));
            ''')
            with self.db:
                old = self.db.execute('SELECT * FROM app_session').fetchone()
                if old:
                    require(old['binding'] == canonical(binding).decode(), 'CONFLICT')
                    self.session = old['id']
                else:
                    self.session = str(uuid.uuid4())
                    self.db.execute('INSERT INTO app_session VALUES(?,?)', (self.session, canonical(binding).decode()))
            if self.memory_enabled:
                from .neoclaw_memory import MemoryRead
                self.memory = MemoryRead(self)
            pending = self.pending()
            if pending:
                # No replay of arbitrary local effects, even if their old result exists.
                require(all(self.intent(x) is not None for x in json.loads(pending['commands'])), 'UNSUPPORTED_PROFILE')
        except BaseException:
            self.db.close()
            self.lock.close()
            raise

    def close(self):
        self.db.close()
        self.lock.close()

    def pending(self):
        return self.db.execute('SELECT * FROM app_turns WHERE projection IS NULL ORDER BY id LIMIT 1').fetchone()

    def intent(self, command):
        module, arguments = c, None
        if selected_expression(command):
            require(len(command) == 2)
            arguments = c.parse_expression(command[1])
        elif self.two_operations and isinstance(command, list) and command and command[0] == 'search':
            require(len(command) == 2)
            module, arguments = s, s.arguments(dict(query=command[1], max_results=10))
            current = json.loads(Path(self.config['caller_config']).read_text())
            require(arguments['query'] in current.get('search_queries', []), 'UNAUTHORIZED')
        elif self.memory_enabled and isinstance(command, list) and command and command[0] == 'query':
            require(len(command) == 2 and type(command[1]) is str)
            from .neoclaw_memory import configuration
            cfg, _, frozen = configuration(self.config['memory_read_config'])
            require(frozen == self.binding['memory'], 'CONFLICT')
            require(command[1] in cfg['queries'], 'UNAUTHORIZED')
            return dict(profile=v.PROFILE, operation='query_with_ids_and_dists', arguments=dict(query=command[1]))
        if self.memory_enabled:
            # The generated read-only installation admits only these three named operations.
            # This excludes mutation via shell/arbitrary MeTTa as well as memory commands.
            require(arguments is not None, 'UNSUPPORTED_OPERATION')
        if arguments is None: return None
        # The legacy column name remains "premises"; /2 fresh journals explicitly
        # store a tagged intent there. Version 1 rows are never reinterpreted.
        return dict(profile=module.PROFILE, operation=module.OPERATION, arguments=arguments) if self.two_operations else arguments

    def more(self):
        if self.pending() is not None:
            return True
        caller = Caller(self.config['caller_config'])
        try: caller.ensure_route_available()
        finally: caller.close()
        return self.db.execute('SELECT count(*) FROM app_turns').fetchone()[0] < self.config['turn_limit']

    def accept(self, response, commands):
        require(type(response) is str and len(response.encode()) <= 20000)
        require(type(commands) is list and len(commands) <= 5)
        # Validate the whole selected batch before any command execution/effect.
        intents = []
        for command in commands:
            require(type(command) is list and command and type(command[0]) is str)
            intents.append(self.intent(command))
        if self.two_operations:
            require(len({x['profile'] for x in intents if x is not None}) <= 1, 'UNSUPPORTED_PROFILE')
            require(sum(x is not None and x['profile'] == s.PROFILE for x in intents) <= 2, 'OVERLOADED')
        encoded = canonical(commands).decode()
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            pending = self.pending()
            if pending:
                require(pending['response'] == response and pending['commands'] == encoded, 'CONFLICT')
                turn = pending['id']
            else:
                require(self.more(), 'OVERLOADED')
                count = self.db.execute('SELECT count(*) FROM app_occurrences WHERE premises IS NOT NULL').fetchone()[0]
                require(count + sum(x is not None for x in intents) <= c.MAX_REQUESTS, 'OVERLOADED')
                turn = self.db.execute('SELECT coalesce(max(id),0)+1 FROM app_turns').fetchone()[0]
                self.db.execute('INSERT INTO app_turns VALUES(?,?,?,NULL)', (turn, response, encoded))
                deadline = int(time.time()*1000) + self.config['invocation_timeout_ms']
                for position, premises in enumerate(intents):
                    key = str(uuid.uuid5(uuid.UUID(self.session), f'{turn}/{position}'))
                    self.db.execute('INSERT INTO app_occurrences VALUES(?,?,?,?,?,NULL,0)',
                        (turn, position, key, canonical(premises).decode() if premises is not None else None, deadline))
        self.hook('after_occurrence_bind')
        return [[i, command] for i, command in enumerate(commands)]

    def begin(self, position, command):
        pending = self.pending()
        require(pending is not None, 'CONFLICT')
        commands = json.loads(pending['commands'])
        require(type(position) is int and 0 <= position < len(commands) and commands[position] == command, 'CONFLICT')
        require(self.db.execute('SELECT count(*) FROM app_occurrences WHERE turn=? AND position<? AND done=0',
                                (pending['id'], position)).fetchone()[0] == 0, 'CONFLICT')
        self.current = (pending['id'], position)

    def _run(self, row):
        intent = json.loads(row['premises'])
        if self.memory_enabled and intent['profile'] == v.PROFILE:
            return self.memory.replay(row)
        module = ops.contract(intent['profile']) if self.two_operations else c
        if self.two_operations:
            c.fields(intent, 'profile operation arguments')
            require(intent['operation'] == module.OPERATION, 'CONFLICT')
            if module is s:
                current = json.loads(Path(self.config['caller_config']).read_text())
                require(intent['arguments']['query'] in current.get('search_queries', []), 'UNAUTHORIZED')
        caller = Caller(self.config['caller_config'], self.hook,
                        invocation=dict(request_id=row['id'], deadline_ms=row['deadline']), profile=module.PROFILE)
        try:
            current = caller_binding(caller)
            expected = self.binding['search'] if module is s else self.binding
            require(all(expected[k] == value for k, value in current.items()), 'CONFLICT')
            return caller.run(intent['arguments'] if self.two_operations else intent)
        finally: caller.close()

    def invoke(self, expression):
        return self._invoke(['metta', expression])

    def search(self, query):
        require(self.two_operations, 'UNSUPPORTED_PROFILE')
        return self._invoke(['search', query])

    def _invoke(self, command):
        require(self.current is not None, 'CONFLICT')
        row = self.db.execute('SELECT * FROM app_occurrences WHERE turn=? AND position=?', self.current).fetchone()
        require(row is not None and row['premises'] == canonical(self.intent(command)).decode(), 'CONFLICT')
        result = self._run(row)  # Includes current authority and receipt/ack checks on replay.
        self.hook('after_caller_completion')
        require(row['result'] is None or row['result'] == result, 'CONFLICT')
        with self.db:
            self.db.execute('UPDATE app_occurrences SET result=?,done=1 WHERE turn=? AND position=?', (result, *self.current))
        return result

    def is_memory(self):
        if not self.memory_enabled or self.current is None: return False
        row = self.db.execute('SELECT premises FROM app_occurrences WHERE turn=? AND position=?', self.current).fetchone()
        return row is not None and row['premises'] is not None and json.loads(row['premises'])['profile'] == v.PROFILE

    def read_captured(self): return self.is_memory() and self.memory.captured()
    def read_replay(self): return self.memory.replay()
    def read_candidates(self, vector, k): return self.memory.retrieve(vector, k)
    def read_clock(self, observed): return self.memory.clock(observed)
    def capture_native(self, value):
        return self.memory.capture(value) if self.is_memory() else value

    def end(self, position):
        require(self.current is not None and self.current[1] == position, 'CONFLICT')
        row = self.db.execute('SELECT * FROM app_occurrences WHERE turn=? AND position=?', self.current).fetchone()
        require(row['premises'] is None or row['done'] == 1, 'NOT_AVAILABLE')
        with self.db:
            self.db.execute('UPDATE app_occurrences SET done=1 WHERE turn=? AND position=?', self.current)
        self.current = None

    def finish(self, projection):
        row = self.pending()
        require(row is not None and type(projection) is str and len(projection.encode()) <= 50000, 'CONFLICT')
        require(self.db.execute('SELECT count(*) FROM app_occurrences WHERE turn=? AND done=0', (row['id'],)).fetchone()[0] == 0, 'NOT_AVAILABLE')
        if self.two_operations:
            for occurrence in self.db.execute('SELECT * FROM app_occurrences WHERE turn=? AND premises IS NOT NULL ORDER BY position', (row['id'],)).fetchall():
                require(self._run(occurrence) == occurrence['result'], 'NOT_AVAILABLE')
        with self.db:
            self.db.execute('UPDATE app_turns SET projection=? WHERE id=?', (projection, row['id']))
        self.hook('after_application_projection')

    def restore(self):
        last = self.db.execute('SELECT * FROM app_turns WHERE projection IS NOT NULL ORDER BY id DESC LIMIT 1').fetchone()
        if not last: return ''
        # Reauthorize through Caller, never treat an application cache as authority.
        for row in self.db.execute('SELECT * FROM app_occurrences WHERE turn=? AND premises IS NOT NULL ORDER BY position', (last['id'],)).fetchall():
            require(self._run(row) == row['result'], 'NOT_AVAILABLE')
        return last['projection']
