"""Application-owned query encoding stage; independent of retrieval reservations."""
from dataclasses import asdict
import json
import time

from . import embedding_contracts as c, vector_contracts as v
from .contracts import canonical, digest, require
from .embedding_composition import configuration, binding


class QueryEmbedding:
    table = 'app_query_vectors'
    config_key, binding_key, profile = 'embedding_config', 'query_embedding', c.PROFILE

    def __init__(self, application, transport=None):
        self.app, self.db = application, application.db
        self.db.execute(f'''CREATE TABLE IF NOT EXISTS {self.table} (
            id TEXT PRIMARY KEY, intent TEXT NOT NULL, calls INTEGER NOT NULL DEFAULT 0,
            attempts INTEGER NOT NULL DEFAULT 0, result TEXT, measurement TEXT, retrieval_ms REAL)''')
        self.db.commit()
        cfg, chosen = self.settings()
        # Provider readiness happens before model responses/occurrence acceptance.
        self.owns_transport = transport is None
        self.transport = binding(cfg, chosen) if transport is None else transport

    def close(self):
        if self.owns_transport and hasattr(self.transport, 'service'):
            self.transport.service.close(); self.transport.service.encoder.close()

    def settings(self):
        cfg, chosen, frozen = configuration(self.app.config[self.config_key], self.profile)
        require(frozen == self.app.binding[self.binding_key], 'CONFLICT')
        return cfg, chosen

    def state(self, row):
        value = self.db.execute(f'SELECT * FROM {self.table} WHERE id=?', (row['id'],)).fetchone()
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
            self.db.execute(f'UPDATE {self.table} SET calls=calls+1,attempts=attempts+? WHERE id=?', (int(op=='encode'), row['id']))
        if op == 'encode': self.stage('after_encode_reservation')
        req = dict(interface_ref=dict(id=c.INTERFACE, version=c.VERSION), operation=op,
                   intent=json.loads(state['intent']), attempt=state['attempts']+1 if op=='encode' else 0)
        reply = self.transport.invoke(req)
        if op == 'encode': require(time.time_ns()//1_000_000 <= row['deadline'], 'DEADLINE_EXCEEDED')
        return reply

    def authorize(self, row): return self.call(row, 'authorize-disclose')

    def encode(self, helper_input):
        row = self.current(); cfg, _ = self.settings()
        query = json.loads(row['premises'])['arguments']['content' if self.profile==c.MEMORY_PROFILE else 'query']
        require(query in cfg['inputs'] and helper_input == cfg['inputs'][query], 'UNAUTHORIZED')
        accepted = c.intent(asdict(c.EncodeInput(row['id'], cfg['principal'], cfg['scope'], c.text(helper_input),
            digest(helper_input.encode()), row['deadline'], self.app.binding[self.binding_key]['selection'],profile=self.profile)))
        serialized = canonical(accepted).decode()
        with self.db:
            old = self.db.execute(f'SELECT * FROM {self.table} WHERE id=?', (row['id'],)).fetchone()
            require(old is None or old['intent'] == serialized, 'CONFLICT')
            self.db.execute(f'INSERT OR IGNORE INTO {self.table}(id,intent) VALUES(?,?)', (row['id'], serialized))
        self.stage('after_encode_intent')
        state = self.state(row)
        if state['result'] is None:
            self.before_encode(row)
            self.call(row, 'authorize-invoke')
            result = c.result(self.call(row, 'encode'), accepted)
            measurement = getattr(self.transport, 'last_measurement', {})
            self.stage('after_encode_reply')
            self.authorize(row)
            with self.db:
                self.db.execute(f'UPDATE {self.table} SET result=?,measurement=? WHERE id=? AND result IS NULL',
                    (canonical(result).decode(), canonical(measurement).decode(), row['id']))
            self.on_capture(row)
            self.stage('after_vector_capture')
        self.authorize(row)
        return self.selected(row)['vector']

    def current(self): return self.app.memory.current()
    def stage(self, name): self.app.hook(name)
    def before_encode(self, row): pass
    def on_capture(self, row): pass

    def selected(self, row):
        state = self.state(row)
        require(state['result'] is not None, 'NOT_AVAILABLE')
        return c.result(json.loads(state['result']), json.loads(state['intent']))


class MemoryEmbedding(QueryEmbedding):
    """Same capture/reservation lifecycle, separately consented native memory purpose."""
    table = 'app_memory_vectors'
    config_key, binding_key, profile = 'memory_embedding_config', 'memory_embedding', c.MEMORY_PROFILE

    def __init__(self, application):
        cfg, _, _ = configuration(application.config[self.config_key], self.profile)
        query, _ = application.embedding.settings()
        transport = None
        if cfg['placement']==query['placement']=='local' and cfg['provider_config']==query['provider_config']:
            from .embedding_transport import EmbeddingLocal
            transport=EmbeddingLocal(application.embedding.transport.service,cfg['credential'])
        super().__init__(application,transport)

    def current(self): return self.app.write.current()
    def stage(self,name): self.app.hook(name.replace('after_','after_memory_',1))
    def before_encode(self,row): self.app.write.preflight(row)
    def on_capture(self,row): self.app.write.note(row,'vector-captured')
