"""Real caller/commitment SQLite, existing signed-intent implementation.

Native captures, chain, signer and network are explicit fixtures inherited from
the historical port tests. SIGKILL is real. This is not real CHAIN evidence.
"""
import copy,json,multiprocessing,os,signal,sqlite3,time,unittest,uuid
from unittest.mock import patch
from fusion.contracts import canonical,digest,ContractError,require
from fusion.chain_continuation import Continuation,PROFILE,LIMITS
from fusion.inspection_continuation import DEFINITION as FIRST,STEPS
from fusion.preview_chain import Client
from tests.test_phase2_chain import PreviewChain


class ChainContinuation(PreviewChain):
    def setUp(self):
        super().setUp();self.occurrence=str(uuid.uuid4());self.turn=str(uuid.uuid4())
        self.now=time.time_ns()//1000000;self.deadline=self.now+300000;self.permitted=True
        self.db_path=self.root/'caller.sqlite';self.db=sqlite3.connect(self.db_path);self.db.row_factory=sqlite3.Row
        self.addCleanup(lambda:self.db.close())
        self.db.executescript('''CREATE TABLE app_occurrences(id TEXT PRIMARY KEY,turn TEXT,deadline INTEGER,done INTEGER,result TEXT);
            CREATE TABLE app_turns(id TEXT PRIMARY KEY,projection TEXT);
            CREATE TABLE preview_inspections(occurrence TEXT PRIMARY KEY,artifact TEXT,artifact_ref TEXT,request TEXT,acceptance TEXT,result TEXT,completion TEXT,ack TEXT);
            CREATE TABLE integrated_inspection_continuations(occurrence TEXT PRIMARY KEY,deadline INTEGER,definition TEXT);
            CREATE TABLE integrated_inspection_steps(occurrence TEXT,step TEXT,capture_digest TEXT);''')
        captures=[self.artifact,self.registration['artifact'],{'explicit':'native-request-fixture'},
            {'job_id':self.registration['job_id']},self.registration['result'],{'delivery_id':'fixture-delivery'}, {'delivery':'acknowledged'}]
        result=dict(status='INSPECTED_ARTIFACT',task=self.artifact['task'],artifact=self.registration['artifact'],
            artifact_bytes=len(self.raw),inspection=self.registration['result'],job_id=self.registration['job_id'],
            completion='fixture-delivery',caller_acknowledged=True,chain='NOT_SUBMITTED',approval='NOT_GRANTED')
        with self.db:
            self.db.execute('INSERT INTO app_occurrences VALUES(?,?,?,?,?)',(self.occurrence,self.turn,self.now-1,1,canonical(result).decode()))
            self.db.execute('INSERT INTO app_turns VALUES(?,?)',(self.turn,'EXPLICIT_NATIVE_TURN_FIXTURE'))
            self.db.execute('INSERT INTO preview_inspections VALUES(?,?,?,?,?,?,?,?)',(self.occurrence,*[canonical(x).decode() for x in captures]))
            self.db.execute('INSERT INTO integrated_inspection_continuations VALUES(?,?,?)',(self.occurrence,self.now-1,canonical(FIRST).decode()))
            self.db.executemany('INSERT INTO integrated_inspection_steps VALUES(?,?,?)',[(self.occurrence,s,digest(canonical(x))) for s,x in zip(STEPS,captures)])
        self.owner=self.open()

    def open(self):
        def authorize(action):require(self.permitted,'UNAUTHORIZED')
        return Continuation(self.db,Client(self.client_path),authorize,clock=lambda:self.now)

    def admit(self):return self.owner.admit(self.occurrence,'approved-result-1',self.deadline,digest(canonical(self.registration)))
    def advance(self):return self.owner.advance(self.occurrence)
    def observe(self):return self.owner.observe(self.occurrence)

    def test_fixed_graph_exact_native_origin_separate_approval_and_single_submit(self):
        first=self.admit();self.assertEqual(first['origin']['original_deadline_ms'],self.now-1)
        self.assertEqual(first['deadline_ms'],self.deadline);self.assertEqual(self.signs,[])
        self.assertEqual(self.admit(),first)
        self.advance();self.finalized();self.advance();value=self.advance()
        self.assertEqual(value['status'],'finalized');self.assertEqual(value['submit_reservations'],1)
        self.assertEqual(value['observations_spent'],2);self.assertEqual(len(self.signs),1)
        before=copy.deepcopy(self.api.calls);self.assertEqual(self.advance(),value);self.assertEqual(self.api.calls,before)

    def test_lost_acceptance_and_signed_response_do_not_resubmit(self):
        def cut(stage):
            if stage=='after_chain_submission_capture':raise RuntimeError('after-capture')
        self.admit();self.owner.hook=cut
        with self.assertRaises(RuntimeError):self.advance()
        self.owner=self.open();self.finalized();self.advance();v=self.advance()
        self.assertEqual(v['status'],'finalized');self.assertEqual(len(self.signs),1)
        self.assertEqual(sum(x[0]=='submit' for x in self.api.calls),1)

    def test_process_kill_after_reservation_never_manufactures_absence_or_refunds(self):
        self.admit()
        def child():
            db=sqlite3.connect(self.db_path);db.row_factory=sqlite3.Row
            def hook(stage):
                if stage=='after_chain_submit_reservation':os.kill(os.getpid(),signal.SIGKILL)
            owner=Continuation(db,Client(self.client_path),lambda _:None,clock=lambda:self.now,hook=hook)
            owner.advance(self.occurrence)
        proc=multiprocessing.get_context('fork').Process(target=child);proc.start();proc.join(10)
        self.assertEqual(proc.exitcode,-signal.SIGKILL)
        v=self.advance();self.assertEqual(v['status'],'needs-reconciliation')
        self.assertEqual(v['submit_reservations'],1);self.assertEqual(v['observations_spent'],1)
        self.assertEqual(self.signs,[])
        self.now=self.deadline
        self.denied('DEADLINE_EXCEEDED',self.advance)
        self.assertEqual(self.observe()['observations_spent'],1)

    def test_cancellation_before_and_after_dispatch_preserves_existing_intent(self):
        self.admit();before=self.owner.cancel(self.occurrence,'cancel-first')
        self.assertEqual(before['status'],'cancelled-before-submit');self.assertEqual(self.advance(),before)
        self.denied('CONFLICT',self.owner.cancel,self.occurrence,'changed-cancel')
        # A distinct test subcase uses a fresh application/owner; cancellation
        # cannot clear a flag on the already accepted graph above.

    def test_cancel_after_signed_intent_allows_only_bounded_reconciliation(self):
        self.admit();self.advance();self.owner.cancel(self.occurrence,'cancel-after-submit')
        self.finalized();self.advance();value=self.advance()
        self.assertEqual(value['status'],'finalized');self.assertTrue(value['cancel_requested'])
        self.assertEqual(sum(x[0]=='submit' for x in self.api.calls),1)

    def test_observation_budget_spent_on_failed_reads_and_original_deadline(self):
        self.admit();self.advance()
        def fail(*args,**kwargs):raise ContractError('NOT_AVAILABLE')
        with patch.object(self.owner.client,'call',side_effect=fail):
            for _ in range(LIMITS['observations']):self.denied('NOT_AVAILABLE',self.advance)
            self.denied('OVERLOADED',self.advance)
        value=self.observe();self.assertEqual(value['observations_spent'],16)
        self.assertEqual(value['submit_reservations'],1);self.assertEqual(value['deadline_ms'],self.deadline)

    def test_approval_drift_current_revocation_and_missing_native_capture_refuse(self):
        self.denied('UNAUTHORIZED',self.owner.admit,self.occurrence,'bad-approval',self.deadline,'0'*64)
        self.admit();self.permitted=False;self.denied('UNAUTHORIZED',self.advance);self.denied('UNAUTHORIZED',self.observe)
        self.permitted=True
        with self.db:self.db.execute('UPDATE preview_inspections SET result=? WHERE occurrence=?',('{}',self.occurrence))
        self.denied('NOT_AVAILABLE',self.advance);self.assertEqual(self.signs,[])

    def test_changed_identity_or_deadline_or_registration_conflicts(self):
        self.admit()
        self.denied('CONFLICT',self.owner.admit,self.occurrence,'approved-result-1',self.deadline+1,digest(canonical(self.registration)))
        self.denied('CONFLICT',self.owner.admit,self.occurrence,'new-key',self.deadline,digest(canonical(self.registration)))
        cfg=json.loads(self.client_path.read_bytes());cfg['registration']['approved']['approval_record']='changed'
        self.client_path.write_bytes(canonical(cfg));changed=self.open()
        self.denied('CONFLICT',changed.observe,self.occurrence)

    def test_malformed_remote_result_retains_reservation_without_capture(self):
        self.admit()
        from fusion import preview_chain
        def wrong(cfg,path,q,deadline=None):return dict(profile=preview_chain.PROFILE,request_digest=digest(canonical(q)),value={'not':'a receipt'})
        with patch.object(preview_chain,'invoke',side_effect=wrong):self.denied('NOT_AVAILABLE',self.advance)
        v=self.observe();self.assertIsNone(v['submission']);self.assertEqual(v['submit_reservations'],1)
        self.assertEqual(v['status'],'needs-reconciliation')

    def test_concurrent_transition_refuses_before_reservation_and_releases_after_kill(self):
        self.admit();context=multiprocessing.get_context('fork');ready=context.Event()
        def child():
            db=sqlite3.connect(self.db_path);db.row_factory=sqlite3.Row
            owner=Continuation(db,Client(self.client_path),lambda _:None,clock=lambda:self.now)
            with owner.gate():ready.set();time.sleep(20)
        proc=context.Process(target=child);proc.start()
        try:
            self.assertTrue(ready.wait(5));self.denied('OVERLOADED',self.advance)
            self.assertEqual(self.observe()['submit_reservations'],0)
        finally:proc.kill();proc.join(5)
        self.assertEqual(proc.exitcode,-signal.SIGKILL)
        self.advance();self.assertEqual(self.observe()['submit_reservations'],1)


def load_tests(loader,tests,pattern):
    return unittest.TestSuite(ChainContinuation(name) for name in ChainContinuation.__dict__ if name.startswith('test_'))
