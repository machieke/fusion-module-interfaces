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
from . import embedding_contracts as e
from . import append_contracts as w
from . import nal_memory_contracts as n
from . import promotion_contracts as p, channel_contracts as ch, model_contracts as m, neoclaw_retrieval_disclosure as r
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
    @staticmethod
    def inspect(path):
        """Operator observation of this owner's committed state; no effect authority.

        May run while the native loop owns its exclusive writer lock. Never
        retrieves another owner's data and never supplies a native tool result.
        """
        config = json.loads(Path(path).read_text())
        caller = json.loads(Path(config['caller_config']).read_text())
        database = Path(caller['database'])
        if not database.exists(): return {}
        tables = ('app_session', 'app_turns', 'app_occurrences', 'app_model_calls',
                  'app_memory_reads', 'app_query_vectors', 'app_query_views',
                  'app_read_views', 'app_priority_contexts', 'app_channel_inputs',
                  'app_channel_outputs')
        with sqlite3.connect(database.as_uri()+'?mode=ro', uri=True) as db:
            db.row_factory = sqlite3.Row
            db.execute('BEGIN')
            available = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            return {name: [dict(r) for r in db.execute('SELECT * FROM '+name+' ORDER BY rowid')]
                    for name in tables if name in available}

    def __init__(self, config_file, hook=lambda _: None):
        self.config = json.loads(Path(config_file).read_text())
        self.hook, self.current = hook, None
        require(self.config['composition'] in ('controlled-native-loop/1', ops.APPLICATION, v.APPLICATION, e.APPLICATION, w.APPLICATION, n.APPLICATION, p.APPLICATION, ch.APPLICATION, m.APPLICATION,r.APPLICATION), 'UNSUPPORTED_PROFILE')
        self.model_enabled = self.config['composition'] in (m.APPLICATION,r.APPLICATION)
        self.channel_enabled = self.config['composition'] in (ch.APPLICATION,m.APPLICATION,r.APPLICATION)
        self.priority_enabled = self.config['composition'] in (p.APPLICATION,ch.APPLICATION,m.APPLICATION,r.APPLICATION)
        self.evidence_enabled = self.config['composition'] in (n.APPLICATION,p.APPLICATION,ch.APPLICATION,m.APPLICATION,r.APPLICATION)
        self.append_enabled = self.config['composition'] in (w.APPLICATION,n.APPLICATION,p.APPLICATION,ch.APPLICATION,m.APPLICATION,r.APPLICATION)
        self.embedding_enabled = self.config['composition'] in (e.APPLICATION,w.APPLICATION,n.APPLICATION,p.APPLICATION,ch.APPLICATION,m.APPLICATION,r.APPLICATION)
        self.memory_enabled = self.config['composition'] in (v.APPLICATION, e.APPLICATION,w.APPLICATION,n.APPLICATION,p.APPLICATION,ch.APPLICATION,m.APPLICATION,r.APPLICATION)
        self.two_operations = self.config['composition'] in (ops.APPLICATION, v.APPLICATION, e.APPLICATION,w.APPLICATION,n.APPLICATION,p.APPLICATION,ch.APPLICATION,m.APPLICATION,r.APPLICATION)
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
            if self.embedding_enabled:
                from .embedding_composition import configuration
                encoder_cfg, _, selected = configuration(self.config['embedding_config'])
                require(encoder_cfg['principal'] == binding['memory']['principal'] and encoder_cfg['scope'] == binding['memory']['scope'], 'UNAUTHORIZED')
                require(binding['memory']['embedding'] == encoder_cfg['model'] == v.EMBEDDING, 'UNSUPPORTED_PROFILE')
                require(set(encoder_cfg['inputs']) == set(binding['memory']['queries']), 'UNSUPPORTED_PROFILE')
                binding.update(composition=e.APPLICATION, query_embedding=selected)
            if self.append_enabled:
                from .append_composition import configuration as append_configuration
                write_cfg,_,write_binding=append_configuration(self.config['memory_append_config'])
                memory_encoder,_,encoder_binding=configuration(self.config['memory_embedding_config'],e.MEMORY_PROFILE)
                require(write_cfg['session']==self.config['session_id'],'CONFLICT')
                require(write_cfg['principal']==memory_encoder['principal']==binding['memory']['principal'] and
                        write_cfg['scope']==memory_encoder['scope']==binding['memory']['scope'],'UNAUTHORIZED')
                require(write_cfg['corpus']==binding['memory']['snapshot']['corpus'] and
                        write_cfg['model']==memory_encoder['model']==binding['memory']['embedding'],'UNSUPPORTED_PROFILE')
                require(write_cfg['inputs']==memory_encoder['inputs'],'UNSUPPORTED_PROFILE')
                require(binding['memory'].get('require_ready') is True,'UNSUPPORTED_PROFILE')
                binding.update(composition=w.APPLICATION,memory_append=write_binding,memory_embedding=encoder_binding)
            if self.evidence_enabled:
                from .neoclaw_evidence import settings
                self.binding=binding
                binding.update(composition=n.APPLICATION,evidence=settings(self)[1])
            if self.priority_enabled:
                from .neoclaw_priority import settings as priority_settings
                self.binding=binding
                binding.update(composition=p.APPLICATION,attention=priority_settings(self)[1])
            if self.channel_enabled:
                from .neoclaw_channel import settings as channel_settings
                self.binding=binding
                binding.update(composition=ch.APPLICATION,channel=channel_settings(self)[1])
            if self.model_enabled:
                from .neoclaw_model import settings as model_settings
                self.binding=binding
                binding.update(composition=self.config['composition'],model=model_settings(self)[2])
                if self.config['composition'] == r.APPLICATION:
                    self.binding=binding
                    binding['retrieval']=r.binding(self)
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
                    self.session = self.config['session_id'] if self.append_enabled else str(uuid.uuid4())
                    self.db.execute('INSERT INTO app_session VALUES(?,?)', (self.session, canonical(binding).decode()))
            if self.memory_enabled:
                from .neoclaw_memory import MemoryRead
                self.memory = MemoryRead(self)
            if self.embedding_enabled:
                from .neoclaw_embedding import QueryEmbedding
                self.embedding = QueryEmbedding(self)
            if self.append_enabled:
                from .neoclaw_append import MemoryAppend
                self.write=MemoryAppend(self)
            if self.evidence_enabled:
                from .neoclaw_evidence import EvidenceAdoption
                self.evidence=EvidenceAdoption(self)
            if self.priority_enabled:
                from .neoclaw_priority import PriorityAdoption
                self.priority=PriorityAdoption(self)
            if self.channel_enabled:
                from .neoclaw_channel import ChannelAdoption
                self.channel=ChannelAdoption(self)
            if self.model_enabled:
                from .neoclaw_model import ModelAdoption
                self.model=ModelAdoption(self)
            pending = self.pending()
            if pending:
                # No replay of arbitrary local effects, even if their old result exists.
                require(all(self.intent(x) is not None for x in json.loads(pending['commands'])), 'UNSUPPORTED_PROFILE')
        except BaseException:
            if hasattr(self,'write'):self.write.close()
            if hasattr(self, 'embedding'): self.embedding.close()
            self.db.close()
            self.lock.close()
            raise

    def close(self):
        if hasattr(self,'write'):self.write.close()
        if hasattr(self, 'embedding'): self.embedding.close()
        self.db.close()
        self.lock.close()

    def pending(self):
        return self.db.execute('SELECT * FROM app_turns WHERE projection IS NULL ORDER BY id LIMIT 1').fetchone()

    def intent(self, command):
        if self.channel_enabled and isinstance(command,list) and command and command[0]=='send':
            return self.channel.intent(command)
        if self.priority_enabled and isinstance(command,list) and command and command[0] in ('promote','demote'):
            return self.priority.intent(command)
        if self.evidence_enabled and isinstance(command,list) and command and command[0] in ('support','contradict'):
            return self.evidence.intent(command)
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
        elif self.append_enabled and isinstance(command,list) and command and command[0]=='remember':
            require(len(command)==2 and type(command[1]) is str)
            from .append_composition import configuration
            cfg,_,frozen=configuration(self.config['memory_append_config'])
            require(frozen==self.binding['memory_append'],'CONFLICT')
            require(command[1] in cfg['inputs'],'UNAUTHORIZED')
            w.text(command[1],cfg['inputs'][command[1]],cfg['scope'],cfg['corpus'])
            return dict(profile=w.PROFILE,operation='remember',arguments=dict(content=command[1]))
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

    def accept(self, response, commands, normalized=None):
        if self.model_enabled:self.model.admit(response,normalized,commands)
        require(type(response) is str and len(response.encode()) <= 20000)
        require(type(commands) is list and len(commands) <= 5)
        if self.channel_enabled:self.channel.accept_turn()
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
                    if self.append_enabled and premises is not None:self.write.admit(key,premises)
                    if self.evidence_enabled and premises is not None:self.evidence.admit(key,premises)
                    if self.priority_enabled and premises is not None:self.priority.admit(key,premises)
                    if self.channel_enabled and premises is not None:self.channel.admit(key,premises,turn,position,deadline)
        self.hook('after_occurrence_bind')
        if self.priority_enabled and any(x and x['profile']==p.PROFILE for x in intents):self.hook('after_priority_acceptance')
        return [[i, command] for i, command in enumerate(commands)]

    def begin(self, position, command):
        pending = self.pending()
        require(pending is not None, 'CONFLICT')
        commands = json.loads(pending['commands'])
        require(type(position) is int and 0 <= position < len(commands) and commands[position] == command, 'CONFLICT')
        require(self.db.execute('SELECT count(*) FROM app_occurrences WHERE turn=? AND position<? AND done=0',
                                (pending['id'], position)).fetchone()[0] == 0, 'CONFLICT')
        self.current = (pending['id'], position)
        if self.is_evidence():self.evidence.begin()

    def _run(self, row):
        intent = json.loads(row['premises'])
        if self.channel_enabled and intent['profile']==ch.PROFILE:return self.channel.replay(row)
        if self.priority_enabled and intent['profile']==p.PROFILE:return self.priority.replay(row)
        if self.evidence_enabled and intent['profile']==n.PROFILE:return self.evidence.replay(row)
        if self.append_enabled and intent['profile']==w.PROFILE:return self.write.replay(row)
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

    def is_append(self):
        if not self.append_enabled or self.current is None:return False
        row=self.db.execute('SELECT premises FROM app_occurrences WHERE turn=? AND position=?',self.current).fetchone()
        return row is not None and row['premises'] is not None and json.loads(row['premises'])['profile']==w.PROFILE

    def is_evidence(self):
        if not self.evidence_enabled or self.current is None:return False
        row=self.db.execute('SELECT premises FROM app_occurrences WHERE turn=? AND position=?',self.current).fetchone()
        return row is not None and row['premises'] is not None and json.loads(row['premises'])['profile']==n.PROFILE
    def input_message(self):return self.channel.receive() if self.channel_enabled else self.evidence.input_message()
    def source(self,text):return self.channel.source(text) if self.channel_enabled else self.evidence.source(text)
    def revise(self,target,source,sign):return self.evidence.revise(target,source,sign)

    def is_priority(self):
        if not self.priority_enabled or self.current is None:return False
        row=self.db.execute('SELECT premises FROM app_occurrences WHERE turn=? AND position=?',self.current).fetchone()
        return row is not None and row[0] is not None and json.loads(row[0])['profile']==p.PROFILE

    def is_channel_send(self):
        if not self.channel_enabled or self.current is None:return False
        row=self.db.execute('SELECT premises FROM app_occurrences WHERE turn=? AND position=?',self.current).fetchone()
        return row is not None and row[0] is not None and json.loads(row[0])['profile']==ch.PROFILE

    def read_captured(self):
        if self.is_channel_send():return self.channel.occurrence()['result'] is not None
        if self.is_priority():return self.priority.current()['result'] is not None
        if self.is_evidence():return self.evidence.current()['result'] is not None
        return self.write.current()['result'] is not None if self.is_append() else self.is_memory() and self.memory.captured()
    def read_replay(self):
        if self.is_channel_send():return self.channel.replay(self.channel.occurrence())
        if self.is_priority():return self.priority.replay()
        if self.is_evidence():return self.evidence.replay()
        return self.write.replay() if self.is_append() else self.memory.replay()
    def read_candidates(self, vector, k):
        start = time.monotonic()
        value = self.memory.retrieve(vector, k)
        if self.embedding_enabled:
            with self.db:
                self.db.execute('UPDATE app_query_vectors SET retrieval_ms=? WHERE id=?',
                    ((time.monotonic()-start)*1000, self.memory.current()['id']))
        return value
    def encode_query(self, text):
        require(self.embedding_enabled, 'UNSUPPORTED_PROFILE')
        return self.write.embedding.encode(text) if self.is_append() else self.embedding.encode(text)
    def read_clock(self, observed): return self.priority.query_clock() if self.priority_enabled else self.memory.clock(observed)
    def capture_native(self, value):
        if self.is_channel_send():return self.channel.capture(value)
        if self.is_priority():return self.priority.capture(value)
        if self.is_evidence():return self.evidence.capture(value)
        if self.is_append():return self.write.capture(value)
        return self.memory.capture(value) if self.is_memory() else value

    def remember_time(self,value):return self.write.clock(value)
    def append_memory(self,content,vector,timestamp):return self.write.append(content,vector,timestamp)
    def creation_link(self,key,timestamp):return self.write.link(key,timestamp)

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

    def priority_adjust(self,alias,delta):return self.priority.adjust(alias,delta)
    def priority_score(self,observed,target):return self.priority.score(observed,target)
    def context_captured(self):return self.priority.context_captured()
    def context_ids(self):return self.priority.context_ids()
    def context_payloads(self,targets):return self.priority.context_payloads(targets)
    def promoted_line(self,value):return self.priority.promoted_line(value)
    def context_capture(self,value):return self.priority.context_capture(value)
    def context_replay(self):return self.priority.context_replay()

    def channel_new(self):return self.channel.new_input()
    def channel_send(self,text):return self.channel.send(text)
    def channel_lastsend(self):return self.channel.lastsend()

    def model_prompt(self,raw):return self.model.prompt(raw)
    def model_complete(self,raw):return self.model.complete(raw)
    def model_parsed(self,normalized,parsed):return self.model.parsed(normalized,parsed)
    def response(self):return self.model.replay() if self.model_enabled else self.pending()['response']
