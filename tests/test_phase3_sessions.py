"""Application-owner qualification; fake clocks/data, real SQLite/process kills.

These are not deployed/native workflow evidence. All files and children belong
to each test's fresh temporary synthetic owner.
"""
import json
import multiprocessing
from pathlib import Path
import signal
import tempfile
import threading
import time
import unittest
import uuid

from fusion.contracts import ContractError, canonical
from fusion.preview_sessions import SessionStore
from fusion.sustained_sessions import SustainedSessionStore, PROFILE, ALLOCATION
from fusion.preview_session_service import SessionPorts


def policy():
    return dict(profile=ALLOCATION,owner=str(uuid.uuid4()),active=2,retained=4,pending=8,bytes=1048576,
        templates={'shared':dict(principal='A',scope='synthetic-phase3-session-test',lifetime_ms=10000,
            runtime_digest='a'*64,binding=dict(catalogue='catalogue',policy='policy',model_boundary='RECORDED_FIXTURE',
                limits=dict(inputs=8,pending=4,timeout_ms=100)))})


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'inbox.sqlite';self.cfg=policy();self.now=[1000];self.revoked=False

    def auth(self, principal, scope, operation):
        if self.revoked or principal!='A' or scope!='synthetic-phase3-session-test':raise ContractError('UNAUTHORIZED')

    def store(self, **kwargs):
        return SustainedSessionStore(self.path,self.auth,self.cfg,clock=lambda:self.now[0],**kwargs)

    def allocate(self, name='allocation'):
        s=self.store()
        try:return s.allocate('A',name,'shared')['session']
        finally:s.close()

    def test_allocation_lost_reply_stable_identity_and_frozen_expiry(self):
        sid=self.allocate();self.now[0]=1050;s=self.store()
        try:
            result=s.allocate('A','allocation','shared')
            self.assertEqual(result['session'],sid);self.assertEqual(result['allocation']['expires_ms'],11000)
            self.assertEqual(s.capacity('A')['retained'],1)
            self.cfg['templates']['shared']['runtime_digest']='b'*64
            with self.assertRaisesRegex(ContractError,'CONFLICT'):s.allocate('A','allocation','shared')
            with self.assertRaisesRegex(ContractError,'CONFLICT'):s.observe('A',sid)
        finally:s.close()

    def test_three_sequential_allocations_do_not_reclaim_retained_records(self):
        s=self.store()
        try:
            ids=[]
            for i in range(3):
                value=s.allocate('A',str(i),'shared');sid=value['session'];ids.append(sid)
                s.submit('A',sid,'input','pin synthetic','task');s.next_input('A',sid)
                s.complete('A',sid,'input',dict(turn=1,projection='fixture native projection',occurrences=['o']))
                s.control('A',sid,'close','close');s.control('A',sid,'archive','archive')
            self.assertEqual(len(set(ids)),3)
            self.assertEqual(s.capacity('A')['retained'],3);self.assertEqual(s.capacity('A')['active'],0)
            for sid in ids:self.assertEqual(s.observe('A',sid,True)['inputs'][0]['result']['projection'],'fixture native projection')
        finally:s.close()

    def test_active_and_retained_quotas_are_independent(self):
        s=self.store()
        try:
            first=s.allocate('A','one','shared')['session'];second=s.allocate('A','two','shared')['session']
            with self.assertRaisesRegex(ContractError,'OVERLOADED'):s.allocate('A','three','shared')
            s.control('A',first,'close','close');third=s.allocate('A','three','shared')['session']
            s.control('A',second,'close','close');s.control('A',third,'close','close')
            fourth=s.allocate('A','four','shared')['session'];s.control('A',fourth,'close','close')
            with self.assertRaisesRegex(ContractError,'OVERLOADED'):s.allocate('A','five','shared')
            self.assertEqual(s.allocate('A','one','shared')['session'],first)
        finally:s.close()

    def test_wrong_template_principal_and_revocation(self):
        s=self.store()
        try:
            for who,name in [('B','shared'),('A','missing')]:
                with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):s.allocate(who,'bad',name)
            sid=s.allocate('A','ok','shared')['session'];self.revoked=True
            for call in (lambda:s.observe('A',sid),lambda:s.allocate('A','ok','shared'),lambda:s.capacity('A')):
                with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):call()
        finally:s.close()

    def test_expired_undispatched_head_terminalizes_at_equality(self):
        sid=self.allocate();s=self.store()
        try:
            first=s.submit('A',sid,'old','pin first','task');self.now[0]=1100
            s.submit('A',sid,'new','pin second','task')
            selected=s.next_input('A',sid);self.assertEqual(selected['id'],'new');self.assertEqual(selected['state'],'dispatched')
            observed=s.observe('A',sid)
            self.assertEqual(observed['inputs'][0]['state'],'expired-before-start')
            self.assertEqual(observed['inputs'][0]['outcome']['effects'],'NO_DISPATCH')
            replay=s.submit('A',sid,'old','pin first','task');self.assertEqual(replay['deadline'],first['deadline'])
            self.assertEqual(replay['state'],'expired-before-start');self.assertEqual(observed['capacity']['pending'],1)
        finally:s.close()

    def test_expired_dispatched_input_fences_dependent_work_but_not_observation(self):
        sid=self.allocate();s=self.store()
        try:
            s.submit('A',sid,'unknown','write-file x synthetic','task');one=s.next_input('A',sid)
            self.assertEqual(one,s.next_input('A',sid))
            self.now[0]=1100;s.submit('A',sid,'dependent','query synthetic','task')
            with self.assertRaisesRegex(ContractError,'NOT_AVAILABLE'):s.next_input('A',sid)
            observed=s.observe('A',sid)
            self.assertEqual(observed['inputs'][0]['state'],'needs-reconciliation')
            self.assertEqual(observed['inputs'][0]['outcome']['effects'],'UNKNOWN_AFTER_DISPATCH')
            other=s.allocate('A','other','shared')['session'];s.submit('A',other,'independent','pin isolated','task')
            self.assertEqual(s.next_input('A',other)['id'],'independent')
            self.assertEqual(s.capacity('A')['pending'],3)
        finally:s.close()

    def test_completed_projection_reconciles_after_expiry_once(self):
        sid=self.allocate();s=self.store()
        try:
            s.submit('A',sid,'one','pin value','task');s.next_input('A',sid);self.now[0]=1101;s.reconcile('A',sid)
            result=dict(turn=1,projection='already saved native projection fixture',occurrences=['original-occurrence'])
            first=s.complete('A',sid,'one',result);self.now[0]=1200
            self.assertEqual(first,s.complete('A',sid,'one',result))
            self.assertEqual(first['deadline'],1100)
            with self.assertRaisesRegex(ContractError,'CONFLICT'):s.complete('A',sid,'one',{**result,'projection':'replacement'})
            self.assertEqual(s.observe('A',sid)['capacity']['completed'],1)
        finally:s.close()

    def test_no_completion_acknowledgment_for_an_undispatched_input(self):
        sid=self.allocate();s=self.store()
        try:
            s.submit('A',sid,'one','pin value','task')
            with self.assertRaisesRegex(ContractError,'CONFLICT'):s.complete('A',sid,'one',dict(turn=1,projection='fabricated',occurrences=[]))
        finally:s.close()

    def test_cancel_before_dispatch_is_terminal_and_idempotent(self):
        sid=self.allocate();s=self.store()
        try:
            s.submit('A',sid,'one','pin value','task');r=s.cancel('A',sid,'cancel-one','one')
            self.assertEqual(r,s.cancel('A',sid,'cancel-one','one'))
            self.assertEqual(r['outcome']['state'],'cancelled-before-start')
            self.assertIsNone(s.next_input('A',sid))
            s.submit('A',sid,'two','pin value','task');self.assertEqual(s.next_input('A',sid)['id'],'two')
            with self.assertRaisesRegex(ContractError,'CONFLICT'):s.cancel('A',sid,'cancel-one','two')
        finally:s.close()

    def test_cancel_after_dispatch_preserves_uncertainty_and_stops_stage_permission(self):
        sid=self.allocate();s=self.store()
        try:
            s.submit('A',sid,'one','append-file file synthetic','task');s.next_input('A',sid)
            self.assertTrue(s.permit('A',sid,'one')['authorized'])
            result=s.cancel('A',sid,'cancel-one','one')
            self.assertEqual(result['outcome']['effects'],'UNKNOWN_AFTER_DISPATCH')
            self.assertFalse(result['transmitted_effects_retracted'])
            with self.assertRaisesRegex(ContractError,'NOT_AVAILABLE'):s.permit('A',sid,'one')
            with self.assertRaisesRegex(ContractError,'NOT_AVAILABLE'):s.next_input('A',sid)
        finally:s.close()

    def test_clock_rollback_and_original_deadline_are_not_repaired(self):
        sid=self.allocate();s=self.store()
        try:
            before=s.submit('A',sid,'one','pin value','task');self.now[0]=999
            with self.assertRaisesRegex(ContractError,'CONFLICT'):s.next_input('A',sid)
            self.now[0]=1100;s.reconcile('A',sid)
            after=s.observe('A',sid)['inputs'][0];self.assertEqual(after['deadline'],before['deadline'])
        finally:s.close()

    def test_capacity_refuses_before_input_acceptance_without_renewing_prior_input(self):
        self.cfg['pending']=1;sid=self.allocate();s=self.store()
        try:
            accepted=s.submit('A',sid,'one','pin value','task')
            with self.assertRaisesRegex(ContractError,'OVERLOADED'):s.submit('A',sid,'two','pin other','task')
            self.assertEqual(len(s.observe('A',sid)['inputs']),1)
            self.now[0]=1050;self.assertEqual(s.submit('A',sid,'one','pin value','task'),accepted)
        finally:s.close()

    def test_fresh_profile_seal_refuses_both_rollback_and_populated_upgrade(self):
        sid=self.allocate()
        with self.assertRaisesRegex(ContractError,'UNSUPPORTED_PROFILE'):SessionStore(self.path,self.auth)
        old=Path(self.temp.name)/'old.sqlite';s=SessionStore(old,self.auth);s.close()
        with self.assertRaisesRegex(ContractError,'UNSUPPORTED_PROFILE'):SustainedSessionStore(old,self.auth,self.cfg)

    def test_concurrent_allocation_has_one_durable_identity(self):
        # Each connection belongs to the same logical owner; SQLite serializes
        # transactions, not two independently managed journal writers.
        self.store().close();barrier=threading.Barrier(2);results=[];errors=[]
        def work():
            s=self.store()
            try:barrier.wait(timeout=3);results.append(s.allocate('A','same','shared')['session'])
            except BaseException as e:errors.append(e)
            finally:s.close()
        ts=[threading.Thread(target=work) for _ in range(2)]
        for t in ts:t.start()
        for t in ts:t.join(5)
        self.assertFalse(errors);self.assertEqual(len(results),2);self.assertEqual(len(set(results)),1)

    def test_cancel_dispatch_race_never_reports_no_dispatch_after_dispatch_commit(self):
        sid=self.allocate();s=self.store();s.submit('A',sid,'one','pin value','task');s.close()
        barrier=threading.Barrier(2);results={}
        def run(name):
            owner=self.store()
            try:
                barrier.wait(timeout=3)
                results[name]=owner.cancel('A',sid,'cancel','one') if name=='cancel' else owner.next_input('A',sid)
            except ContractError as e:results[name]=e.code
            finally:owner.close()
        threads=[threading.Thread(target=run,args=(name,)) for name in ('cancel','next')]
        for t in threads:t.start()
        for t in threads:t.join(5)
        s=self.store()
        try:
            row=s.observe('A',sid)['inputs'][0];started=s.db.execute('SELECT count(*) FROM sustained_dispatch').fetchone()[0]
            self.assertEqual((row['state'],row['outcome']['effects']),('cancel-requested','UNKNOWN_AFTER_DISPATCH') if started else ('cancelled-before-start','NO_DISPATCH'))
        finally:s.close()

    def kill_at(self, stage, operation):
        self.store().close();parent,child=multiprocessing.Pipe(False)
        def target():
            def hook(name):
                if name==stage:
                    child.send(name)
                    while True:time.sleep(1)
            s=self.store(hook=hook)
            try:operation(s)
            finally:s.close()
        proc=multiprocessing.get_context('fork').Process(target=target);proc.start()
        try:
            self.assertTrue(parent.poll(8),'child failed before committed barrier');self.assertEqual(parent.recv(),stage)
            proc.kill();proc.join(5);self.assertEqual(proc.exitcode,-signal.SIGKILL)
        finally:
            if proc.is_alive():proc.kill();proc.join(5)
            parent.close();child.close()

    def test_real_process_kill_allocation_commit_before_reply(self):
        self.kill_at('after_session_allocation_commit',lambda s:s.allocate('A','lost-reply','shared'))
        s=self.store()
        try:
            replay=s.allocate('A','lost-reply','shared');self.assertEqual(s.capacity('A')['retained'],1)
            self.assertEqual(replay['allocation']['expires_ms'],11000)
        finally:s.close()

    def test_real_process_kill_terminal_commit_before_reply(self):
        sid=self.allocate();s=self.store();s.submit('A',sid,'one','pin value','task');s.close();self.now[0]=1100
        self.kill_at('after_input_terminalization_commit',lambda s:s.reconcile('A',sid))
        s=self.store()
        try:self.assertEqual(s.observe('A',sid)['inputs'][0]['state'],'expired-before-start');self.assertIsNone(s.next_input('A',sid))
        finally:s.close()

    def test_real_process_kill_completion_commit_before_reply(self):
        sid=self.allocate();s=self.store();s.submit('A',sid,'one','pin value','task');s.next_input('A',sid);s.close()
        result=dict(turn=1,projection='saved fixture projection',occurrences=['same'])
        self.kill_at('after_session_completion_commit',lambda s:s.complete('A',sid,'one',result))
        self.now[0]=1200;s=self.store()
        try:self.assertEqual(s.complete('A',sid,'one',result)['state'],'complete');self.assertEqual(s.capacity('A')['pending'],0)
        finally:s.close()


class PortTests(unittest.TestCase):
    def test_authenticated_operator_cannot_complete_and_worker_cannot_allocate(self):
        with tempfile.TemporaryDirectory() as td:
            p=policy();path=Path(td)/'owner.json';scope=p['templates']['shared']['scope']
            cfg=dict(principals={
                'operator':dict(credential='operator-secret',scopes={scope:['sessions.'+x for x in ('allocate','submit','observe','disclose','reconcile','cancel','capacity','list')]}),
                'worker':dict(credential='worker-secret',scopes={scope:['sessions.'+x for x in ('next','permit','complete')]})},
                native_sessions=dict(profile=PROFILE,principal='A',database=str(Path(td)/'inbox.sqlite'),assignments=['task'],allocation=p))
            path.write_bytes(canonical(cfg));ports=SessionPorts(path)
            def call(op,token='operator-secret',**body):return ports.invoke(token,dict(id='wire',profile=PROFILE,operation=op,body=body))['value']
            sid=call('allocate',identity='one',template='shared')['session']
            call('submit',session=sid,identity='input',text='pin value',assignment='task')
            with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):call('complete',session=sid,identity='input',result={})
            with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):call('allocate','worker-secret',identity='two',template='shared')
            self.assertEqual(call('next','worker-secret',session=sid)['state'],'dispatched')
            with self.assertRaisesRegex(ContractError,'INVALID_ARGUMENT'):call('observe',session=sid,content=False,principal='B')
            with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):call('observe','wrong',session=sid,content=False)


if __name__=='__main__':unittest.main()
