"""Bind an inbox occurrence to one actual native turn; acknowledge projection.

Input capture, application projection and inbox acknowledgment are independent
commits. Recovery acknowledges only an already committed native projection.
"""
import json
from .contracts import canonical, require
from .preview_session_client import Client


class NativeInput:
    def __init__(self, app):
        self.app, self.db = app, app.db
        self.client = Client(app.config['session_config'])
        cfg = self.client.binding
        require(cfg['session'] == app.session and cfg['principal'] == app.binding['principal'], 'UNAUTHORIZED')
        self.db.execute('''CREATE TABLE IF NOT EXISTS preview_native_inputs(
            turn INTEGER PRIMARY KEY, identity TEXT UNIQUE NOT NULL, source TEXT NOT NULL,
            acknowledged INTEGER NOT NULL DEFAULT 0)''')

    def reconcile(self):
        rows = self.db.execute('''SELECT i.*,t.projection FROM preview_native_inputs i
            JOIN app_turns t ON t.id=i.turn WHERE i.acknowledged=0 AND t.projection IS NOT NULL ORDER BY i.turn''').fetchall()
        for row in rows:
            ids = [r[0] for r in self.db.execute('SELECT id FROM app_occurrences WHERE turn=? ORDER BY position',(row['turn'],))]
            if self.app.preview.tasks:self.app.preview.tasks.complete(row)
            receipt = self.client.invoke('complete', identity=row['identity'],
                result=dict(turn=row['turn'], projection=row['projection'], occurrences=ids))
            require(receipt['id'] == row['identity'] and receipt['state'] == 'complete', 'NOT_AVAILABLE')
            self.app.hook('after_session_completion_reply')
            with self.db: self.db.execute('UPDATE preview_native_inputs SET acknowledged=1 WHERE turn=?',(row['turn'],))

    def source(self):
        row = self.db.execute('SELECT source FROM preview_native_inputs WHERE turn=?',(self.app.processing_slot(),)).fetchone()
        require(row is not None, 'NOT_AVAILABLE')
        return json.loads(row[0])

    def available(self):
        self.reconcile()
        old = self.db.execute('SELECT source FROM preview_native_inputs WHERE turn=?',(self.app.processing_slot(),)).fetchone()
        # Always recheck current session/worker authority, even for a bound input.
        received = self.client.invoke('next')
        if old:
            require(received is not None and canonical(received).decode() == old[0], 'CONFLICT')
            if self.app.preview.history:self.app.preview.history.input()
            if self.app.preview.memory:self.app.preview.memory.input()
            if self.app.preview.tasks:self.app.preview.tasks.input()
            return True
        if received is None: return False
        require(received['session'] == self.app.session and received['state'] == 'accepted', 'NOT_AVAILABLE')
        selected=received['session_binding']
        require(selected['catalogue']==self.app.preview.catalogue.identity and
                selected['policy']==self.app.preview.authority().revision and
                selected['model_boundary']=='RECORDED_FIXTURE','CONFLICT')
        with self.db:
            self.db.execute('INSERT INTO preview_native_inputs(turn,identity,source) VALUES(?,?,?)',
                (self.app.processing_slot(),received['id'],canonical(received).decode()))
        self.app.hook('after_session_input_capture')
        if self.app.preview.history:self.app.preview.history.input()
        if self.app.preview.memory:self.app.preview.memory.input()
        if self.app.preview.tasks:self.app.preview.tasks.input()
        return True

    def model_source(self):
        value = self.source()
        return dict(message_id=value['occurrence'], deadline_ms=value['deadline'], text=value['payload']['text'])
