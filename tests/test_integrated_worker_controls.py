"""Real application owner/fences and a process kill; native results are fixtures."""
import multiprocessing,os,signal,unittest,uuid
from fusion.contracts import ContractError
from fusion.resident_workers import Workers,LIMITS
from tests import test_integrated_workers as fixture


def die_after_drain(path,cfg,sid):
    def hook(stage):
        if stage=='after_worker_control_commit':os.kill(os.getpid(),signal.SIGKILL)
    w=Workers(path,lambda *_:None,cfg,LIMITS,clock=lambda:1000,hook=hook)
    w.control('A',sid,'drain','durable-drain')


class WorkerControls(fixture.WorkerEpochTests):
    def test_drain_completes_only_inflight_and_explicit_resume_never_refunds(self):
        one=self.submit();two=self.submit('two');self.call('ready');self.call('next')
        first=self.w.control('A',self.sid,'drain','operator-drain')
        self.assertEqual(self.w.control('A',self.sid,'drain','operator-drain'),first)
        self.call('permit',{'identity':'one'});self.complete()
        self.assertEqual(self.call('next'),{'state':'retire','input':None})
        self.w.retire('A',self.sid,self.epoch)
        with self.assertRaisesRegex(ContractError,'NOT_AVAILABLE'):self.w.register('A',self.sid,str(uuid.uuid4()))
        resumed=self.w.control('A',self.sid,'resume','operator-resume');self.assertEqual(resumed['mode'],'enabled')
        self.assertEqual(self.w.control('A',self.sid,'drain','operator-drain'),first)
        self.assertFalse(self.w.draining(self.sid))
        with self.assertRaisesRegex(ContractError,'CONFLICT'):self.w.control('A',self.sid,'recycle','operator-drain')
        self.epoch=str(uuid.uuid4());self.w.register('A',self.sid,self.epoch);self.call('ready')
        next_=self.call('next')['input'];self.assertEqual(next_['id'],'two');self.assertEqual(next_['deadline'],two['deadline'])
        self.assertEqual(self.w.db.execute('SELECT count(*) FROM native_worker_assignments').fetchone()[0],2)
    def test_fair_rotation_at_committed_boundary_without_new_worker_livelock(self):
        other=self.w.store.allocate('A','other','shared')['session']
        first=self.submit();second=self.submit('two');peer=self.submit('peer',other)
        self.call('ready');self.assertEqual(self.call('next')['input']['id'],'one')
        # Another input cannot preempt an in-flight result.
        self.assertEqual(self.call('next')['input']['id'],'one');self.complete()
        self.assertEqual(self.call('next')['state'],'retire');self.w.retire('A',self.sid,self.epoch)
        epoch=str(uuid.uuid4());self.w.register('A',other,epoch);self.call('ready',sid=other,epoch=epoch)
        self.assertEqual(self.call('next',sid=other,epoch=epoch)['input']['deadline'],peer['deadline'])
        own=self.w.store.observe('A',self.sid)['inputs'];self.assertEqual(own[1]['state'],'accepted');self.assertEqual(own[1]['deadline'],second['deadline'])
    def test_resume_cannot_clear_started_unknown_or_current_revocation(self):
        self.submit();self.call('ready');self.call('next');self.w.control('A',self.sid,'recycle','recycle')
        self.w.retire('A',self.sid,self.epoch);self.w.control('A',self.sid,'resume','resume')
        with self.assertRaisesRegex(ContractError,'NOT_AVAILABLE'):self.w.register('A',self.sid,str(uuid.uuid4()))
        state=self.w.control('A',self.sid,'observe');self.assertEqual(state['unresolved_assignments'],1)
        self.revoked=True
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):self.w.control('A',self.sid,'observe')
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):self.w.control('A',self.sid,'resume','revoked')
    def test_real_kill_after_drain_capture_and_worker_metadata_remains_charged(self):
        before=self.w.store.capacity('A')['logical_bytes'];p=multiprocessing.Process(target=die_after_drain,args=(self.path,self.cfg,self.sid));p.start();p.join(5)
        try:self.assertEqual(p.exitcode,-signal.SIGKILL)
        finally:
            if p.is_alive():p.kill();p.join(2)
        self.assertTrue(self.w.draining(self.sid));one=self.w.control('A',self.sid,'drain','durable-drain')
        self.assertEqual(one,self.w.control('A',self.sid,'drain','durable-drain'))
        self.assertGreater(self.w.store.capacity('A')['logical_bytes'],before)
        self.call('ready');self.assertEqual(self.call('next')['state'],'retire')
        spent=self.w.store.capacity('A')['logical_bytes'];self.w.retire('A',self.sid,self.epoch)
        self.assertGreaterEqual(self.w.store.capacity('A')['logical_bytes'],spent)


def load_tests(loader,tests,pattern):
    return unittest.TestSuite(WorkerControls(n) for n in WorkerControls.__dict__ if n.startswith('test_'))

if __name__=='__main__':unittest.main()
