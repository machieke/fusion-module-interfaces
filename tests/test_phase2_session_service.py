import json
from pathlib import Path
import tempfile
import time
import unittest
import uuid

from fusion.contracts import ContractError, canonical
from fusion.preview_session_service import SessionPorts
from fusion.preview_sessions import PROFILE


class SessionServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.path = self.root/'config.json'
        self.sid = str(uuid.uuid4()); self.scope = 'synthetic-service-session'
        self.cfg = dict(principals={
            'operator': dict(credential='operator-secret', scopes={self.scope:['sessions.'+op for op in ('create', 'submit', 'observe', 'disclose', 'pause', 'resume', 'close')]}),
            'worker': dict(credential='worker-secret', scopes={self.scope:['sessions.'+op for op in ('next', 'complete')]}),
        }, native_sessions=dict(profile=PROFILE, model_boundary='RECORDED_FIXTURE', scope=self.scope, principal='A',
            database=str(self.root/'sessions.db'), assignments=['note'], session_templates={self.sid:dict(
                catalogue='selected-source-catalogue', policy='synthetic-notes', model_boundary='RECORDED_FIXTURE',
                limits=dict(inputs=8, pending=4, timeout_ms=30000))}))
        self.save(); self.wakes = []
        self.ports = SessionPorts(self.path, self.wakes.append)

    def save(self): self.path.write_bytes(canonical(self.cfg))

    def call(self, op, token='operator-secret', **body):
        return self.ports.invoke(token, dict(id=str(uuid.uuid4()), profile=PROFILE, operation=op, body=dict(session=self.sid, **body)))['value']

    def test_operator_admission_and_worker_receipt_are_separate(self):
        self.call('create')
        one = self.call('submit', identity='one', text='same', assignment='note')
        two = self.call('submit', identity='two', text='same', assignment='note')
        self.assertNotEqual(one['id'], two['id'])
        self.assertEqual(len(self.wakes), 2)
        with self.assertRaisesRegex(ContractError, 'UNAUTHORIZED'): self.call('next')
        with self.assertRaisesRegex(ContractError, 'UNAUTHORIZED'): self.call('complete', identity='one', result={})
        self.assertEqual(self.call('next', 'worker-secret')['id'], 'one')
        self.assertEqual(self.call('observe', content=False)['inputs'][0]['state'], 'accepted')
        result = dict(turn=1, projection='actual captured native projection fixture', occurrences=['one'])
        self.call('complete', 'worker-secret', identity='one', result=result)
        self.assertEqual(self.call('next', 'worker-secret')['id'], 'two')
        self.assertEqual(self.call('observe', content=True)['inputs'][0]['result'], result)

    def test_current_authority_and_fabricated_assignments(self):
        self.call('create')
        with self.assertRaisesRegex(ContractError, 'UNAUTHORIZED'):
            self.call('submit', identity='one', text='input', assignment='arbitrary-code')
        with self.assertRaisesRegex(ContractError, 'UNAUTHORIZED'): self.call('observe', 'wrong', content=False)
        self.cfg['principals']['operator']['scopes'][self.scope].remove('sessions.submit'); self.save()
        with self.assertRaisesRegex(ContractError, 'UNAUTHORIZED'):
            self.call('submit', identity='one', text='input', assignment='note')
        self.assertEqual(self.wakes, [])


if __name__ == '__main__': unittest.main()
