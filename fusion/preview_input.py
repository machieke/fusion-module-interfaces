"""Bind an inbox occurrence to one actual native turn; acknowledge projection.

Input capture, application projection and inbox acknowledgment are independent
commits. Recovery acknowledges only an already committed native projection.
"""
from fusion.native_telemetry import traced
import json
from .contracts import canonical, require
from .preview_session_client import Client


class NativeInput:
    def __init__(self, app):
        self.app, self.db = app, app.db
        self.client = Client(app.config['session_config'])
        self.resident=app.config.get('resident_worker');self.worker_ready=False
        if self.resident is not None:
            import os
            from .resident_workers import Client as ResidentClient,selection
            selection(self.resident)
            self.client=ResidentClient(app.config['session_config'],os.environ['NEOCLAW_NATIVE_INCARNATION'])
        self.turns=set()
        self.quantum=app.config.get('native_dispatch_quantum')
        require(self.quantum is None or (self.client.binding['profile']=='omega-native-sessions/3' and type(self.quantum) is int and self.quantum==1),'UNSUPPORTED_PROFILE')
        cfg = self.client.binding
        require(cfg['session'] == app.session and cfg['principal'] == app.binding['principal'], 'UNAUTHORIZED')
        self.db.execute('''CREATE TABLE IF NOT EXISTS preview_native_inputs(
            turn INTEGER PRIMARY KEY, identity TEXT UNIQUE NOT NULL, source TEXT NOT NULL,
            acknowledged INTEGER NOT NULL DEFAULT 0)''')

    @traced('input.reconcile')
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

    @traced('input.prepare')
    def available(self):
        if self.resident is not None and not self.worker_ready:
            self.client.invoke('ready');self.worker_ready=True
        self.reconcile()
        if self.quantum is not None and len(self.turns)>=self.quantum and self.app.processing_slot() not in self.turns:return False
        old = self.db.execute('SELECT source FROM preview_native_inputs WHERE turn=?',(self.app.processing_slot(),)).fetchone()
        # Always recheck current session/worker authority, even for a bound input.
        received = self.client.invoke('next')
        if self.resident is not None:
            import time
            until=time.monotonic()+self.resident['idle_ms']/1000
            while received is None and not self.client.limit_reached and time.monotonic()<until:
                time.sleep(min(.25,max(0,until-time.monotonic())))
                received=self.client.invoke('next')
        if old:
            require(received is not None and canonical(received).decode() == old[0], 'CONFLICT')
            self.turns.add(self.app.processing_slot())
            if self.app.preview.history:self.app.preview.history.input()
            if self.app.preview.memory:self.app.preview.memory.input()
            if self.app.preview.tasks:self.app.preview.tasks.input()
            return True
        if received is None: return False
        expected = 'dispatched' if self.client.binding['profile'] == 'omega-native-sessions/3' else 'accepted'
        require(received['session'] == self.app.session and received['state'] == expected, 'NOT_AVAILABLE')
        selected=received['session_binding']
        from .preview_model_binding import boundary
        from pathlib import Path
        model=json.loads(Path(self.app.config['model_config']).read_bytes())
        require(selected['catalogue']==self.app.preview.catalogue.identity and
                selected['policy']==self.app.preview.authority().revision and
                selected['model_boundary']==boundary(model),'CONFLICT')
        with self.db:
            self.db.execute('INSERT INTO preview_native_inputs(turn,identity,source) VALUES(?,?,?)',
                (self.app.processing_slot(),received['id'],canonical(received).decode()))
        self.app.hook('after_session_input_capture')
        self.turns.add(self.app.processing_slot())
        if self.app.preview.history:self.app.preview.history.input()
        if self.app.preview.memory:self.app.preview.memory.input()
        if self.app.preview.tasks:self.app.preview.tasks.input()
        return True

    def execution_permit(self, source=None):
        """Current /3 cancellation/deadline fence before a new effect stage.

        Saved projection reconciliation uses its own observation path and never
        calls this to reauthorize an effect. Historical /2 behavior is intact.
        """
        if self.client.binding['profile'] != 'omega-native-sessions/3': return
        value = self.source() if source is None else source
        require(value['session']==self.app.session,'UNAUTHORIZED')
        result = self.client.invoke('permit', identity=value['id'])
        require(result == dict(identity=value['id'], deadline=value['deadline'], authorized=True), 'CONFLICT')

    def model_source(self):
        value = self.source()
        return dict(message_id=value['occurrence'], deadline_ms=value['deadline'], text=value['payload']['text'])
