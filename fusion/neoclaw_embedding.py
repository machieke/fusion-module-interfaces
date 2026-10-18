"""Application-owned query encoding stage; independent of retrieval reservations."""
from dataclasses import asdict
import json
import time

from . import embedding_contracts as c, vector_contracts as v
from .contracts import canonical, digest, require
from .embedding_composition import configuration, binding


class QueryEmbedding:
    def __init__(self, application):
        self.app, self.db = application, application.db
        self.db.execute('''CREATE TABLE IF NOT EXISTS app_query_vectors (
            id TEXT PRIMARY KEY, intent TEXT NOT NULL, calls INTEGER NOT NULL DEFAULT 0,
            attempts INTEGER NOT NULL DEFAULT 0, result TEXT, measurement TEXT, retrieval_ms REAL)''')
        self.db.commit()
        cfg, chosen = self.settings()
        # Provider readiness happens before model responses/occurrence acceptance.
        self.transport = binding(cfg, chosen)

    def close(self):
        if hasattr(self.transport, 'service'):
            self.transport.service.close(); self.transport.service.encoder.close()

    def settings(self):
        cfg, chosen, frozen = configuration(self.app.config['embedding_config'])
        require(frozen == self.app.binding['query_embedding'], 'CONFLICT')
        return cfg, chosen

    def state(self, row):
        value = self.db.execute('SELECT * FROM app_query_vectors WHERE id=?', (row['id'],)).fetchone()
        require(value is not None, 'NOT_AVAILABLE')
        return value

    def call(self, row, op):
        cfg, _ = self.settings()
        self.transport.credential = cfg['credential']  # Rotation is allowed; the principal remains frozen.
        if op == 'encode': require(time.time_ns()//1_000_000 <= row['deadline'], 'DEADLINE_EXCEEDED')
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            state = self.state(row)
            require(state['calls'] < c.MAX_CALLS, 'OVERLOADED')
            if op == 'encode': require(state['attempts'] < c.MAX_ATTEMPTS, 'OVERLOADED')
            self.db.execute('UPDATE app_query_vectors SET calls=calls+1,attempts=attempts+? WHERE id=?', (int(op=='encode'), row['id']))
        if op == 'encode': self.app.hook('after_encode_reservation')
        req = dict(interface_ref=dict(id=c.INTERFACE, version=c.VERSION), operation=op,
                   intent=json.loads(state['intent']), attempt=state['attempts']+1 if op=='encode' else 0)
        reply = self.transport.invoke(req)
        if op == 'encode': require(time.time_ns()//1_000_000 <= row['deadline'], 'DEADLINE_EXCEEDED')
        return reply

    def authorize(self, row): return self.call(row, 'authorize-disclose')

    def encode(self, helper_input):
        row = self.app.memory.current(); cfg, _ = self.settings()
        query = json.loads(row['premises'])['arguments']['query']
        require(query in cfg['inputs'] and helper_input == cfg['inputs'][query], 'UNAUTHORIZED')
        accepted = c.intent(asdict(c.EncodeInput(row['id'], cfg['principal'], cfg['scope'], c.text(helper_input),
            digest(helper_input.encode()), row['deadline'], self.app.binding['query_embedding']['selection'])))
        serialized = canonical(accepted).decode()
        with self.db:
            old = self.db.execute('SELECT * FROM app_query_vectors WHERE id=?', (row['id'],)).fetchone()
            require(old is None or old['intent'] == serialized, 'CONFLICT')
            self.db.execute('INSERT OR IGNORE INTO app_query_vectors(id,intent) VALUES(?,?)', (row['id'], serialized))
        self.app.hook('after_encode_intent')
        state = self.state(row)
        if state['result'] is None:
            self.call(row, 'authorize-invoke')
            result = c.result(self.call(row, 'encode'), accepted)
            measurement = getattr(self.transport, 'last_measurement', {})
            self.app.hook('after_encode_reply')
            self.authorize(row)
            with self.db:
                self.db.execute('UPDATE app_query_vectors SET result=?,measurement=? WHERE id=? AND result IS NULL',
                    (canonical(result).decode(), canonical(measurement).decode(), row['id']))
            self.app.hook('after_vector_capture')
        self.authorize(row)
        return self.selected(row)['vector']

    def selected(self, row):
        state = self.state(row)
        require(state['result'] is not None, 'NOT_AVAILABLE')
        return c.result(json.loads(state['result']), json.loads(state['intent']))
