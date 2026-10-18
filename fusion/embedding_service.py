"""Embedding owner: current text disclosure policy and durable physical-call reservations.

An injected encoder owns model evaluation only. There is no corpus or result cache.
"""
import json
from pathlib import Path
import sqlite3
import time

from . import embedding_contracts as c, vector_contracts as v
from .contracts import canonical, digest, require
from .policy import Policy
from .registry import descriptor_read, selection_token


class EmbeddingService:
    def __init__(self, path, encoder, hook=lambda _: None):
        self.policy = Policy(path)
        self.config = self.policy.current()['embedding']
        self.encoder, self.hook = encoder, hook
        self.chosen = c.select([descriptor_read(d) for d in self.config['catalogue']])
        self.selections={c.PROFILE:self.chosen}
        if 'memory_helper_inputs' in self.config:
            self.selections[c.MEMORY_PROFILE]=c.select([descriptor_read(d) for d in self.config['catalogue']],c.MEMORY_PROFILE)
        self.db = sqlite3.connect(self.config['database'], timeout=.2)
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS encode_intents (id TEXT PRIMARY KEY, intent TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS encode_attempts (
                id TEXT NOT NULL, attempt INTEGER NOT NULL, finished INTEGER NOT NULL DEFAULT 0,
                duration_ms REAL, vector_sha256 TEXT, PRIMARY KEY(id, attempt));
        ''')

    def close(self): self.db.close()

    def authorize(self, credential, accepted, mode):
        principal = self.policy.authenticate(credential)
        require(principal == accepted['principal'], 'UNAUTHORIZED')
        cfg = self.policy.current()['embedding']
        require(cfg['sharing'] == v.PRIVACY and cfg['scope'] == accepted['scope'], 'UNAUTHORIZED')
        require(cfg['model'] == accepted['model'] and cfg['preprocessing'] == accepted['preprocessing'], 'UNSUPPORTED_PROFILE')
        require(accepted['profile'] in self.selections,'UNSUPPORTED_PROFILE')
        chosen = c.select([descriptor_read(d) for d in cfg['catalogue']],accepted['profile'])
        require(selection_token(chosen) == accepted['selection'] == selection_token(self.selections[accepted['profile']]), 'UNSUPPORTED_PROFILE')
        # Explicit separate consent for the exact post-native-transformation text.
        memory=accepted['profile']==c.MEMORY_PROFILE
        require(accepted['text'] in cfg.get('memory_helper_inputs' if memory else 'approved_helper_inputs',[]), 'UNAUTHORIZED')
        self.policy.check(principal, accepted['scope'], ('embedding.memory.' if memory else 'embedding.') + mode)

    def invoke(self, credential, request):
        require(type(request) is dict and type(request.get('intent')) is dict)
        profile=request['intent'].get('profile');require(profile in self.selections,'UNSUPPORTED_PROFILE')
        c.request(request, self.selections[profile])
        accepted, op = request['intent'], request['operation']
        self.authorize(credential, accepted, 'disclose' if op == 'authorize-disclose' else 'encode')
        if op != 'encode': value = {'authorized': True}
        else:
            self.authorize(credential, accepted, 'disclose')
            require(time.time_ns()//1_000_000 <= accepted['deadline_ms'], 'DEADLINE_EXCEEDED')
            key, serialized = accepted['occurrence'], canonical(accepted).decode()
            with self.db:
                self.db.execute('BEGIN IMMEDIATE')
                old = self.db.execute('SELECT intent FROM encode_intents WHERE id=?', (key,)).fetchone()
                require(old is None or old['intent'] == serialized, 'CONFLICT')
                if old is None:
                    require(self.db.execute('SELECT count(*) FROM encode_intents').fetchone()[0] < c.MAX_OCCURRENCES, 'OVERLOADED')
                    self.db.execute('INSERT INTO encode_intents VALUES(?,?)', (key, serialized))
                # A duplicate physical send cannot consume the same slot twice.
                require(self.db.execute('SELECT 1 FROM encode_attempts WHERE id=? AND attempt=?',
                        (key, request['attempt'])).fetchone() is None, 'OVERLOADED')
                self.db.execute('INSERT INTO encode_attempts(id,attempt) VALUES(?,?)', (key, request['attempt']))
            self.hook('after_encoder_reservation')
            start = time.monotonic()
            value = c.result(self.encoder.encode(c.EncodeInput(**accepted)), accepted)
            elapsed = (time.monotonic()-start)*1000
            with self.db:
                self.db.execute('UPDATE encode_attempts SET finished=1,duration_ms=?,vector_sha256=? WHERE id=? AND attempt=?',
                    (elapsed, value['vector_sha256'], key, request['attempt']))
            self.hook('after_encoder_evaluation')
            require(time.time_ns()//1_000_000 <= accepted['deadline_ms'], 'DEADLINE_EXCEEDED')
            self.authorize(credential, accepted, 'disclose')
        return dict(request_sha256=digest(canonical(request)), principal=accepted['principal'], value=value)
