"""Pre-command model occurrences in the existing application-owned journal."""
from dataclasses import asdict
import json
import time
import uuid
from . import model_contracts as c
from .contracts import ContractError, canonical, require
from .model_transport import Client, configuration
from .neoclaw_model_disclosure import disclose
from .registry import selection_token


def settings(app):
    cfg, chosen, frozen = configuration(app.config['model_config'])
    require(cfg['principal'] == app.binding['memory']['principal'] and cfg['session'] == app.config['session_id'], 'UNAUTHORIZED')
    require(1 <= app.config['turn_limit'] <= c.MAX_SESSION_CALLS, 'OVERLOADED')
    require('model_fixture' not in app.config, 'UNSUPPORTED_PROFILE')
    return cfg, chosen, frozen


class ModelAdoption:
    def __init__(self, app):
        self.app, self.db = app, app.db
        self.client = Client(app.config['model_config'])
        self.db.executescript('''CREATE TABLE IF NOT EXISTS app_model_calls(
          slot INTEGER PRIMARY KEY,id TEXT UNIQUE NOT NULL,intent TEXT NOT NULL,context_view TEXT NOT NULL,
          calls INTEGER NOT NULL DEFAULT 0,result TEXT,normalized TEXT,parse_text TEXT,proposal TEXT,admission TEXT);
        ''')

    def current(self):
        cfg, chosen, frozen = settings(self.app)
        require(frozen == self.app.binding['model'], 'CONFLICT')
        return cfg, chosen

    def row(self):
        return self.db.execute('SELECT * FROM app_model_calls WHERE slot=?', (self.app.evidence.slot(),)).fetchone()

    def local_authority(self, intent):
        cfg, _ = self.current()
        parts = disclose(intent['native_prompt'], cfg['disclosure'])
        source = self.app.channel.source_spec()
        require(intent['source_id'] == source['message_id'] and intent['deadline_ms'] == source['deadline_ms'], 'CONFLICT')
        require(parts['feedback'] == self.app.restore() and parts['memories'] == self.app.priority.context_replay(), 'CONFLICT')
        return cfg

    def prompt(self, raw):
        cfg, chosen = self.current(); row = self.row()
        if row is None:
            parts = disclose(raw, cfg['disclosure'])
            source = self.app.channel.source_spec(); slot = self.app.evidence.slot()
            require(time.time_ns()//1_000_000 < source['deadline_ms'], 'DEADLINE_EXCEEDED')
            require(parts['user'] == str(['HUMAN-MSG:', source['text'].replace('"','_quote_').replace("'",'_apostrophe_')]), 'CONFLICT')
            key = str(uuid.uuid5(uuid.UUID(self.app.session), 'model/'+str(slot)))
            accepted = asdict(c.CompletionInput(id=key,session=self.app.session,slot=slot,source_id=source['message_id'],
                principal=cfg['principal'],scope=cfg['scope'],selection=selection_token(chosen),native_prompt=raw,
                messages=c.messages(raw),deadline_ms=source['deadline_ms']))
            c.intent(accepted); self.local_authority(accepted)
            view = self.app.priority.context()['view']
            with self.db: self.db.execute('INSERT INTO app_model_calls(slot,id,intent,context_view) VALUES(?,?,?,?)',
                (slot,key,canonical(accepted).decode(),view))
            self.app.hook('after_model_prompt_bind'); row = self.row()
        accepted = json.loads(row['intent']); self.local_authority(accepted)
        require(row['context_view'] == self.app.priority.context()['view'], 'CONFLICT')
        # First binding is authoritative, including native TIME. Restart may
        # assemble a new time, but it never substitutes it into this occurrence.
        return accepted['native_prompt']

    def invoke(self, operation, accepted):
        row = self.row(); require(row['calls'] < c.MAX_RPC, 'OVERLOADED')
        with self.db: self.db.execute('UPDATE app_model_calls SET calls=calls+1 WHERE slot=?', (row['slot'],))
        self.app.hook('after_model_rpc_reservation')
        return self.client.invoke(operation, accepted)

    def complete(self, prompt):
        row = self.row(); require(row is not None, 'CONFLICT')
        accepted = json.loads(row['intent']); require(prompt == accepted['native_prompt'], 'CONFLICT')
        self.local_authority(accepted)
        if row['result'] is None:
            result = self.invoke('observe', accepted)
            if result['state'] in ('absent','accepted'):
                require(time.time_ns()//1_000_000 < accepted['deadline_ms'], 'DEADLINE_EXCEEDED')
                result = self.invoke('complete', accepted)
            require(result['state'] == 'captured', 'NOT_AVAILABLE')
            self.app.hook('after_model_provider_reply')
            with self.db: self.db.execute('UPDATE app_model_calls SET result=? WHERE slot=?',
                (canonical(result).decode(), row['slot']))
            self.app.hook('after_model_application_capture')
        else: result = c.observation(json.loads(row['result']), accepted)
        self.invoke('authorize', accepted)
        require(not result['late'] and result['response']['outcome'] == 'complete', 'NOT_AVAILABLE')
        return result['response']['native_text']

    def admit(self, response, normalized, commands):
        row = self.row(); require(row is not None and row['result'] is not None, 'CONFLICT')
        accepted = json.loads(row['intent']); cfg = self.local_authority(accepted)
        result = c.observation(json.loads(row['result']), accepted)
        require(response == result['response']['native_text'] and result['response']['outcome'] == 'complete' and not result['late'], 'CONFLICT')
        self.invoke('authorize', accepted)
        c.text(normalized, c.MAX_TEXT)
        encoded = canonical(commands).decode(); require(len(encoded.encode()) <= c.MAX_TEXT)
        require(row['normalized'] is None or row['normalized'] == normalized, 'CONFLICT')
        require(row['proposal'] is None or row['proposal'] == encoded, 'CONFLICT')
        with self.db: self.db.execute('UPDATE app_model_calls SET normalized=?,proposal=? WHERE slot=?',
            (normalized,encoded,row['slot']))
        # Prompt instructions never grant command authority. Match the entire
        # native parsed batch before the original application can execute it.
        try:
            require(type(commands) is list and 1 <= len(commands) <= 5, 'UNSUPPORTED_OPERATION')
            for command in commands: require(command in cfg['commands'], 'UNSUPPORTED_OPERATION')
            require(len({command[0] for command in commands}) == 1, 'UNSUPPORTED_PROFILE')
            self.app.channel.accept_turn()
        except ContractError as exc:
            with self.db: self.db.execute('UPDATE app_model_calls SET admission=? WHERE slot=?',
                ('rejected:'+exc.code,row['slot']))
            raise
        with self.db: self.db.execute('UPDATE app_model_calls SET admission=? WHERE slot=?', ('authorized',row['slot']))

    def parsed(self, normalized, parsed):
        row = self.row(); require(row is not None and row['result'] is not None, 'CONFLICT')
        c.text(normalized,c.MAX_TEXT); c.text(parsed,c.MAX_TEXT)
        require(row['normalized'] is None or row['normalized'] == normalized, 'CONFLICT')
        require(row['parse_text'] is None or row['parse_text'] == parsed, 'CONFLICT')
        with self.db: self.db.execute('UPDATE app_model_calls SET normalized=?,parse_text=? WHERE slot=?',
            (normalized,parsed,row['slot']))
        if parsed.startswith('(Error '):
            with self.db: self.db.execute('UPDATE app_model_calls SET admission=? WHERE slot=?', ('rejected:NATIVE_PARSE_ERROR',row['slot']))
            require(False,'INVALID_ARGUMENT')
        return True

    def replay(self):
        row = self.row(); require(row is not None, 'CONFLICT')
        response = self.complete(json.loads(row['intent'])['native_prompt'])
        require(response == self.app.pending()['response'], 'CONFLICT')
        return response
