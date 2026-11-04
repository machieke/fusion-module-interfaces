"""Real application SQLite and process kills; clock and native projections fixtures."""
import multiprocessing,os,signal,tempfile,time,unittest,uuid
from pathlib import Path
from fusion.contracts import ContractError
from fusion.resident_workers import Workers,LIMITS
from tests.test_phase3_sessions import policy


def die_after_ready(path,cfg,sid,epoch,pipe):
    def hook(stage):
        if stage=='after_worker_ready_commit':pipe.send(stage);os.kill(os.getpid(),signal.SIGSTOP)
    w=Workers(path,lambda *_:None,cfg,LIMITS,clock=lambda:1000,hook=hook)
    w.invoke('A',sid,epoch,'ready',{})

class WorkerEpochTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'inbox.sqlite';self.cfg=policy();self.now=[1000];self.revoked=False
        self.w=Workers(self.path,self.auth,self.cfg,LIMITS,clock=lambda:self.now[0]);self.addCleanup(self.w.close)
        self.sid=self.w.store.allocate('A','session','shared')['session'];self.epoch=str(uuid.uuid4())
        self.w.register('A',self.sid,self.epoch)
    def auth(self,who,scope,operation):
        if self.revoked or who!='A':raise ContractError('UNAUTHORIZED')
    def call(self,op,body=None,epoch=None,sid=None):return self.w.invoke('A',sid or self.sid,epoch or self.epoch,op,body or {})
    def submit(self,id='one',sid=None):return self.w.store.submit('A',sid or self.sid,id,'pin synthetic','notes')
    def complete(self,id='one'):return self.call('complete',dict(identity=id,result=dict(turn=1,projection='explicit native result fixture',occurrences=['one'])))
    def test_ready_before_claim_and_old_incarnation_cannot_advance_replacement(self):
        first=self.submit()
        with self.assertRaisesRegex(ContractError,'NOT_AVAILABLE'):self.call('next')
        self.call('ready');value=self.call('next')['input'];self.assertEqual(value['deadline'],first['deadline'])
        self.assertEqual(self.complete(),self.complete());self.assertEqual(self.w.retire('A',self.sid,self.epoch)['state'],'stopped')
        old=self.epoch;self.epoch=str(uuid.uuid4());self.w.register('A',self.sid,self.epoch);self.call('ready')
        with self.assertRaisesRegex(ContractError,'CONFLICT'):self.call('complete',dict(identity='one',result={}),epoch=old)
        self.assertEqual(self.w.db.execute('SELECT count(*) FROM native_worker_assignments').fetchone()[0],1)
    def test_unknown_assignment_blocks_replacement_in_same_session_not_independent_session(self):
        self.submit();self.call('ready');self.call('next')
        self.assertEqual(self.w.retire('A',self.sid,self.epoch)['state'],'uncertain')
        with self.assertRaisesRegex(ContractError,'NOT_AVAILABLE'):self.w.register('A',self.sid,str(uuid.uuid4()))
        other=self.w.store.allocate('A','independent','shared')['session'];epoch=str(uuid.uuid4())
        self.w.register('A',other,epoch);self.call('ready',epoch=epoch,sid=other);self.submit('other',other)
        self.assertEqual(self.call('next',epoch=epoch,sid=other)['input']['id'],'other')
        self.assertEqual(self.w.store.observe('A',self.sid)['inputs'][0]['state'],'dispatched')
    def test_current_revocation_and_cancellation_fence_even_after_ready(self):
        self.submit();self.call('ready');self.revoked=True
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):self.call('next')
        self.revoked=False;self.call('next');self.w.store.cancel('A',self.sid,'cancel','one')
        with self.assertRaisesRegex(ContractError,'NOT_AVAILABLE'):self.call('permit',dict(identity='one'))
        self.revoked=True
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):self.complete()
    def test_original_deadline_and_nonrefundable_incarnation_limit(self):
        self.call('ready')
        for i in range(8):
            id=str(i);received=self.submit(id);self.assertEqual(self.call('next')['input']['deadline'],received['deadline']);self.complete(id)
        self.assertEqual(self.call('next'),dict(state='retire',input=None))
        self.assertEqual(self.w.db.execute('SELECT count(*) FROM native_worker_assignments').fetchone()[0],8)
    def test_safe_untouched_expiry_and_late_saved_projection(self):
        received=self.submit();self.call('ready');self.now[0]=received['deadline']
        self.assertEqual(self.call('next')['state'],'idle')
        self.assertEqual(self.w.store.observe('A',self.sid)['inputs'][0]['state'],'expired-before-start')
        received=self.submit('two');self.call('next');self.now[0]=received['deadline']+1
        with self.assertRaisesRegex(ContractError,'DEADLINE_EXCEEDED'):self.call('permit',dict(identity='two'))
        self.complete('two')
        self.assertEqual(self.w.store.observe('A',self.sid)['inputs'][1]['deadline'],received['deadline'])
    def test_selection_drift_refuses_old_worker_and_cross_session_identity_refuses(self):
        self.call('ready');other=self.w.store.allocate('A','another','shared')['session']
        with self.assertRaisesRegex(ContractError,'CONFLICT'):self.call('next',sid=other)
        self.w.limits=dict(LIMITS,inputs=7)
        with self.assertRaisesRegex(ContractError,'UNSUPPORTED_PROFILE'):self.call('next')
    def test_real_process_kill_after_ready_does_not_claim_or_refund_input(self):
        received=self.submit();parent,child=multiprocessing.Pipe(duplex=False)
        p=multiprocessing.Process(target=die_after_ready,args=(self.path,self.cfg,self.sid,self.epoch,child));p.start()
        try:
            self.assertTrue(parent.poll(5));self.assertEqual(parent.recv(),'after_worker_ready_commit')
            os.kill(p.pid,signal.SIGKILL);p.join(3);self.assertEqual(p.exitcode,-signal.SIGKILL)
        finally:
            if p.is_alive():p.kill();p.join(3)
            parent.close();child.close()
        self.assertEqual(self.w.store.observe('A',self.sid)['inputs'][0]['state'],'accepted')
        self.w.retire('A',self.sid,self.epoch);self.epoch=str(uuid.uuid4());self.w.register('A',self.sid,self.epoch);self.call('ready')
        self.assertEqual(self.call('next')['input']['deadline'],received['deadline'])

if __name__=='__main__':unittest.main()
