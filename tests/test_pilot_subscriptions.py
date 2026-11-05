"""Real SQLite commit hints and kill recovery; input contents/results are fixtures."""
import multiprocessing
import os
from pathlib import Path
import signal
import tempfile
import unittest
from fusion.contracts import ContractError
from fusion.sustained_sessions import SustainedSessionStore
from fusion.pilot_subscriptions import install,Subscriptions,usage
from tests.test_phase3_sessions import policy


def kill_after_transition(path,cfg,sid):
    store=SustainedSessionStore(path,lambda *_:None,cfg,clock=lambda:1001)
    store.submit('A',sid,'killed','synthetic fixture','task')
    os.kill(os.getpid(),signal.SIGKILL)


class SubscriptionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='pilot-subscriptions-');self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'owner.sqlite';self.cfg=policy();self.now=[1000]
        self.cfg['templates']['shared']['binding']['limits']['inputs']=24
        self.cfg['templates']['shared']['binding']['limits']['pending']=4
        self.cfg['templates']['shared']['binding']['limits']['timeout_ms']=10000
        self.store=SustainedSessionStore(self.path,lambda *_:None,self.cfg,clock=lambda:self.now[0]);self.addCleanup(self.store.close)
        install(self.store);self.sid=self.store.allocate('A','allocation','shared')['session'];self.revoked=False
        self.owner=Subscriptions(self.store,'browser-alice',self.auth,clock=lambda:self.now[0])
    def auth(self,sid):
        if self.revoked:raise ContractError('UNAUTHORIZED')
        self.assertEqual(sid,self.sid);self.store.allocated('A',sid)
    def create(self):return self.owner.control('create','subscription','create',dict(session=self.sid,lifetime_ms=5000))
    def test_commit_notifications_require_authoritative_read_and_ack_is_cursor_only(self):
        self.create();receipt=self.store.submit('A',self.sid,'input','synthetic fixture','task');self.store.next_input('A',self.sid)
        events=self.owner.read('subscription');self.assertEqual([x['state'] for x in events['events']],['accepted','dispatched'])
        self.assertFalse(events['notifications_are_results']);self.assertEqual(events['cursor'],0)
        self.assertEqual(self.owner.read('subscription'),events)
        body=dict(source=events['source'],cursor=events['next']);self.owner.control('ack','subscription','ack',body)
        self.assertEqual(self.owner.read('subscription')['events'],[])
        with self.assertRaisesRegex(ContractError,'CONFLICT'):self.owner.control('ack','subscription','forged',dict(source=events['source'],cursor=3))
        current=self.store.observe('A',self.sid,True)['inputs'][0]
        self.assertEqual(current['deadline'],receipt['deadline']);self.assertEqual(current['state'],'dispatched')
    def test_pause_renew_close_and_expiry_never_resurrect_or_extend_task(self):
        self.create();before=self.store.submit('A',self.sid,'input','synthetic fixture','task')
        self.owner.control('pause','subscription','pause',{});self.assertEqual(self.owner.read('subscription')['events'],[])
        self.owner.control('resume','subscription','resume',{})
        renewed=self.owner.control('renew','subscription','renew',dict(expires_ms=10000));self.assertEqual(renewed['expires_ms'],10000)
        self.now[0]=10000
        with self.assertRaisesRegex(ContractError,'DEADLINE_EXCEEDED'):self.owner.control('renew','subscription','different',dict(expires_ms=12000))
        replay=self.owner.control('renew','subscription','renew',dict(expires_ms=10000));self.assertEqual(replay['current']['state'],'expired')
        self.assertEqual(self.store.observe('A',self.sid)['inputs'][0]['deadline'],before['deadline'])
        self.owner.control('close','subscription','close',{})
        with self.assertRaisesRegex(ContractError,'DEADLINE_EXCEEDED'):self.owner.read('subscription')
        with self.assertRaisesRegex(ContractError,'CONFLICT'):self.owner.control('create','subscription','new-creation',dict(session=self.sid,lifetime_ms=5000))
    def test_slow_consumer_exact_gap_and_explicit_snapshot_rebase(self):
        self.create()
        for n in range(12):
            iid=str(n);self.store.submit('A',self.sid,iid,'synthetic fixture','task');self.store.next_input('A',self.sid)
            self.store.complete('A',self.sid,iid,dict(turn=n+1,projection='AUTHORED_RESULT_FIXTURE',occurrences=[]))
        value=self.owner.read('subscription');self.assertTrue(value['gap']);self.assertEqual(value['missing'],dict(first=1,last=4));self.assertEqual(value['events'],[])
        with self.assertRaisesRegex(ContractError,'CONFLICT'):self.owner.control('rebase','subscription','forged',dict(source=value['source'],head=36,snapshot_sha256='0'*64))
        snap=self.owner.snapshot('subscription','A');self.assertEqual(len(snap['snapshot']['inputs']),12)
        self.owner.control('rebase','subscription','rebase',snap['rebase'])
        self.assertFalse(self.owner.read('subscription')['gap']);self.assertTrue(self.owner.read('subscription')['stream_complete'])
        self.assertEqual(usage(self.store.db)['retained_hints'],32)
    def test_actor_scope_revocation_and_missing_subscription_do_not_disclose_counts(self):
        self.create();other=Subscriptions(self.store,'browser-bob',self.auth,clock=lambda:self.now[0])
        with self.assertRaisesRegex(ContractError,'NOT_FOUND'):other.read('subscription')
        self.revoked=True
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):self.owner.read('subscription')
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):self.owner.control('close','subscription','close',{})
    def test_process_kill_retains_real_commit_hint_and_original_acceptance(self):
        self.create();proc=multiprocessing.Process(target=kill_after_transition,args=(self.path,self.cfg,self.sid));proc.start();proc.join(5)
        try:self.assertEqual(proc.exitcode,-signal.SIGKILL)
        finally:
            if proc.is_alive():proc.kill();proc.join(2)
        self.now[0]=1002;value=self.owner.read('subscription');self.assertEqual(value['events'][0]['input'],'killed')
        before=self.store.observe('A',self.sid)['inputs'][0]
        self.store.submit('A',self.sid,'killed','synthetic fixture','task')
        self.assertEqual(self.store.observe('A',self.sid)['inputs'][0],before);self.assertEqual(self.owner.read('subscription')['head'],1)
    def test_control_capacity_reserves_final_close_and_keeps_old_receipts(self):
        self.create()
        for n in range(510):self.owner.control('pause' if n%2==0 else 'resume','subscription','control-'+str(n),{})
        with self.assertRaisesRegex(ContractError,'OVERLOADED'):self.owner.control('pause','subscription','over-limit',{})
        self.assertEqual(usage(self.store.db)['closure_reserved_actions'],1)
        self.assertEqual(self.owner.control('close','subscription','final-close',{})['state'],'closed')
        self.assertEqual(usage(self.store.db)['actions'],512);self.assertEqual(usage(self.store.db)['closure_reserved_bytes'],0)
        self.assertEqual(self.owner.control('close','subscription','final-close',{})['state'],'closed')
    def test_install_refuses_populated_unselected_state(self):
        other=SustainedSessionStore(Path(self.temp.name)/'unselected.sqlite',lambda *_:None,self.cfg,clock=lambda:1000)
        try:
            sid=other.allocate('A','unselected','shared')['session'];receipt=other.submit('A',sid,'existing','synthetic fixture','task')
            with self.assertRaisesRegex(ContractError,'CONFLICT'):install(other)
            self.assertEqual(other.observe('A',sid)['inputs'][0],dict(receipt,outcome=None))
            self.assertIsNone(other.db.execute("SELECT 1 FROM sqlite_master WHERE name='pilot_subscription_source'").fetchone())
        finally:other.close()

    def test_clock_regression_and_renewal_replay_conflict(self):
        self.create();self.now[0]=999
        with self.assertRaisesRegex(ContractError,'CONFLICT'):self.owner.read('subscription')
        self.now[0]=1001;self.owner.control('renew','subscription','r',dict(expires_ms=7000))
        with self.assertRaisesRegex(ContractError,'CONFLICT'):self.owner.control('renew','subscription','r',dict(expires_ms=8000))

if __name__=='__main__':unittest.main()
