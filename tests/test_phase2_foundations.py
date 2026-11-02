import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
import uuid

from fusion.contracts import ContractError
from fusion.preview_context import WorkingContext, allocate_context
from fusion.preview_sessions import SessionStore
from fusion.preview_tools import Catalogue, SessionAuthority, context_tools


class Foundations(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)
        self.now = 1000
        self.revoked = False

    def authority(self, principal, scope, operation):
        if self.revoked or principal != 'A' or scope != 'synthetic-test':
            raise ContractError('UNAUTHORIZED')

    def error(self, code, callback, *args, **kwargs):
        with self.assertRaises(ContractError) as caught: callback(*args, **kwargs)
        self.assertEqual(caught.exception.code, code)

    def catalogue(self):
        return Catalogue(context_tools(), {t.tool_id for t in context_tools()}, [])

    def test_catalogue_whole_batch_and_principal(self):
        cat = self.catalogue()
        auth = SessionAuthority('A', 'synthetic-test', frozenset({'pin', 'unpin'}), 'policy-1', 5000)
        self.assertEqual(len(cat.skills(auth, 'A', 1000)), 2)
        self.assertEqual(cat.admit([['pin', 'goal', 'Unverified (metta evil)']], auth, 'A', 1000)[0]['arguments']['note'], 'Unverified (metta evil)')
        self.error('UNSUPPORTED_OPERATION', cat.admit, [['pin', 'goal', 'good'], ['shell', 'whoami']], auth, 'A', 1000)
        self.error('UNAUTHORIZED', cat.admit, [['task-context']], auth, 'A', 1000)
        self.error('UNAUTHORIZED', cat.skills, auth, 'B', 1000)
        self.error('UNAUTHORIZED', cat.skills, auth, 'A', 5000)
        self.error('CONFLICT', cat.admit, [['unpin', 'goal']], auth, 'A', 1000, 'stale')
        self.error('NOT_AVAILABLE', Catalogue, context_tools(), set(), [])

    def test_context_replay_retention_capacity_and_cas(self):
        db = sqlite3.connect(self.path/'context.db')
        self.addCleanup(db.close)
        ctx = WorkingContext(db, lambda op: self.authority('A', 'synthetic-test', op))
        first = ctx.change('one', 'goal', 'Keep <script> as data', 0)
        self.assertEqual(ctx.change('one', 'goal', 'Keep <script> as data', 0), first)
        self.error('CONFLICT', ctx.change, 'one', 'goal', 'changed', 0)
        self.error('CONFLICT', ctx.change, 'two', 'goal', 'stale', 0)
        ctx.change('two', 'goal', None, 1)
        self.assertEqual(ctx.read(1), first)
        self.assertEqual(ctx.read()['items'], {})
        for i in range(8): ctx.change(str(i+10), 'n'+str(i), 'x', i+2)
        self.error('OVERLOADED', ctx.change, 'over', 'n8', 'x', 10)
        self.assertEqual(ctx.read()['revision'], 10)
        self.revoked = True
        self.error('UNAUTHORIZED', ctx.read, 1)

    def test_context_after_commit_interruption_and_allocation(self):
        db = sqlite3.connect(self.path/'context.db')
        def kill(stage): raise RuntimeError(stage)
        ctx = WorkingContext(db, lambda _: None, kill)
        with self.assertRaises(RuntimeError): ctx.change('call', 'x', 'note', 0)
        db.close()
        db = sqlite3.connect(self.path/'context.db')
        self.addCleanup(db.close)
        recovered = WorkingContext(db, lambda _: None)
        self.assertEqual(recovered.change('call', 'x', 'note', 0)['revision'], 1)
        value = allocate_context(system='instruction', task=recovered.read(), history='H'*3000,
                                 input_text='new', promoted='small', feedback='actual', maximum_bytes=1024)
        self.assertEqual(value['omitted'], ['history'])
        self.assertEqual(value['feedback'], 'actual')
        self.error('OVERLOADED', allocate_context, system='x'*2000, task={}, history='', input_text='', promoted='', feedback='', maximum_bytes=1024)

    def session(self):
        store = SessionStore(self.path/'sessions.db', self.authority, lambda: self.now)
        self.addCleanup(store.close)
        sid = str(uuid.uuid4())
        store.create('A', sid, 'synthetic-test', dict(catalogue=self.catalogue().binding(), policy='policy-1',
            model_boundary='RECORDED_FIXTURE', limits=dict(inputs=5, pending=2, timeout_ms=1000)))
        return store, sid

    def test_equal_text_replay_queue_and_original_deadline(self):
        store, sid = self.session()
        one = store.submit('A', sid, 'one', 'same text', 'native')
        self.now += 100
        self.assertEqual(store.submit('A', sid, 'one', 'same text', 'native'), one)
        two = store.submit('A', sid, 'two', 'same text', 'native')
        self.assertNotEqual(one['id'], two['id'])
        self.error('CONFLICT', store.submit, 'A', sid, 'one', 'different', 'native')
        self.error('OVERLOADED', store.submit, 'A', sid, 'three', 'same text', 'native')
        accepted = store.next_input('A', sid)
        self.assertEqual(accepted['state'], 'accepted')
        self.assertEqual(store.observe('A', sid)['inputs'][0]['state'], 'accepted')
        self.now = 2000
        self.error('DEADLINE_EXCEEDED', store.next_input, 'A', sid)
        self.assertEqual(store.submit('A', sid, 'one', 'same text', 'native')['deadline'], 2000)

    def test_pause_close_keeps_completion_and_single_worker(self):
        store, sid = self.session()
        store.submit('A', sid, 'one', 'input', 'native')
        lock = store.worker_lock(sid)
        self.addCleanup(lock.close)
        self.error('OVERLOADED', store.worker_lock, sid)
        paused = store.control('A', sid, 'pause1', 'pause')
        self.assertFalse(paused['transmitted_effects_retracted'])
        self.error('NOT_AVAILABLE', store.next_input, 'A', sid)
        self.error('NOT_AVAILABLE', store.submit, 'A', sid, 'new', 'input', 'native')
        store.complete('A', sid, 'one', {'projection': 'captured result'})
        self.assertEqual(store.observe('A', sid, True)['inputs'][0]['result']['projection'], 'captured result')
        store.control('A', sid, 'close1', 'close')
        self.error('CONFLICT', store.control, 'A', sid, 'resume1', 'resume')
        self.revoked = True
        self.error('UNAUTHORIZED', store.observe, 'A', sid, True)


if __name__ == '__main__': unittest.main()
