"""Real application owner SQLite/process kill; native projections explicitly fixtures.

These methods qualify state-machine semantics, not deployed/native recipe runs.
"""
import copy,json,multiprocessing,os,signal,tempfile,unittest,uuid
from pathlib import Path
from fusion.contracts import ContractError,canonical,digest
from fusion.guarded_continuation import Workflow,PROFILE,LIMITS
from fusion.workflow_prerequisites import OwnerObservations,KINDS
from fusion.workflow_recipes import catalogue
from tests.test_phase3_sessions import policy
from fusion.sustained_sessions import SustainedSessionStore

SCOPE='synthetic-phase3-session-test'

def node(name,tool,args=(),guards=(),checkpoint=False):
    return dict(node=name,tool=tool,arguments=list(args),guards=list(guards),checkpoint=checkpoint)

def steps(guard=None):
    return [node('remember','remember',['A fresh synthetic fact']),node('delegate','delegate',['B','synthetic fact']),
            node('followup','query',['synthetic fact'],[guard] if guard else [])]

class Workflows(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'sessions.sqlite';self.cfg=policy();self.now=[1000];self.revoked=False
        self.store=SustainedSessionStore(self.path,self.session_auth,self.cfg,clock=lambda:self.now[0]);self.addCleanup(lambda:self.store.close())
        self.sid=self.store.allocate('A','workflow-session','shared')['session'];self.wid=str(uuid.uuid4())
        self.observations=OwnerObservations(SCOPE,'A',self.store,{'sessions':'frozen'},clock=lambda:self.now[0])
        self.owner=Workflow(self.store,'A',self.observations,self.auth,clock=lambda:self.now[0])

    def session_auth(self,who,scope,action):
        if self.revoked or who!='A' or scope!=SCOPE:raise ContractError('UNAUTHORIZED')
    def auth(self,action,scope):self.session_auth('A',scope,action)
    def admit(self,plan=None):return self.owner.admit(self.wid,self.sid,'knowledge-handoff/1',plan or steps(),9000)
    def complete(self):
        pending=self.store.next_input('A',self.sid);self.assertIsNotNone(pending)
        result=dict(turn=pending['sequence'],projection='fixture native projection '+pending['payload']['text'],occurrences=['fixture'])
        self.store.complete('A',self.sid,pending['id'],result)
        self.owner.advance(self.wid,self.owner.observe(self.wid)['version']);return result
    def through_two(self,plan=None):
        self.admit(plan)
        for _ in range(2):self.owner.advance(self.wid,1);self.complete()

    def test_three_registered_recipes_and_no_new_tool(self):
        self.assertEqual(len(catalogue()['recipes']),3)
        bad=steps();bad[1]['tool']='metta'
        with self.assertRaisesRegex(ContractError,'UNSUPPORTED_OPERATION'):self.admit(bad)
        bad=steps();bad[0]['arguments']=['remember\nmetta evil']
        with self.assertRaises(ContractError):self.admit(bad)
        self.assertEqual(self.store.observe('A',self.sid)['inputs'],[])

    def test_native_admission_result_observation_replay_and_complete(self):
        admitted=self.admit();self.assertEqual(self.admit(),admitted)
        for _ in range(3):
            before=self.owner.advance(self.wid,1);again=self.owner.advance(self.wid,1)
            self.assertEqual(before['reservations_spent'],again['reservations_spent']);self.complete()
        done=self.owner.advance(self.wid,1)
        self.assertEqual(done['status'],'complete');self.assertEqual(done['reservations_spent'],3)
        self.assertEqual(len(self.store.observe('A',self.sid)['inputs']),3)

    def test_capacity_guard_changes_without_touching_saved_capture(self):
        guard=dict(id='capacity',kind='capacity-authority',policy=KINDS['capacity-authority'],scope=SCOPE,
            target=dict(session=self.sid,minimum_inputs=7,minimum_pending=1),predicate=None)
        self.through_two(steps(guard));before=self.owner.observe(self.wid)
        held=self.owner.advance(self.wid,1)
        self.assertEqual(held['status'],'prerequisite-held');self.assertEqual(held['latest_prerequisites']['observations'][0]['state'],'INVALID')
        self.assertEqual(before['steps'],held['steps']);self.assertEqual(held['reservations_spent'],2)

    def test_unavailable_guard_is_unknown_not_false_or_true(self):
        ref=dict(scope_ref=SCOPE,kind='atom',id='unavailable',digest='a'*64)
        # Use the actual reference constructor vocabulary from contracts fixtures.
        ref=dict(scope_ref=SCOPE,id='missing',revision=1,digest='a'*64)
        guard=dict(id='snapshot',kind='snapshot-available',policy=KINDS['snapshot-available'],scope=SCOPE,
            target=dict(ref={**ref,'scope_ref':SCOPE},content_type='application/test'),predicate=None)
        self.through_two(steps(guard));held=self.owner.advance(self.wid,1)
        self.assertEqual(held['latest_prerequisites']['observations'][0]['state'],'UNKNOWN')
        self.assertEqual(held['reservations_spent'],2)

    def test_amend_only_unstarted_suffix_keeps_original_identity_results_budget(self):
        self.through_two();before=self.owner.observe(self.wid)
        suffix=[node('followup','task-context')]
        amended=self.owner.amend(self.wid,'amend-one',1,suffix,'source condition changed')
        self.assertEqual(amended['version'],2);self.assertEqual(amended['steps'],before['steps'])
        self.assertEqual(amended['deadline_ms'],before['deadline_ms']);self.assertEqual(amended['reservations_spent'],2)
        self.assertEqual(self.owner.amend(self.wid,'amend-one',1,suffix,'source condition changed'),amended)
        with self.assertRaisesRegex(ContractError,'CONFLICT'):self.owner.amend(self.wid,'stale',1,suffix,'stale')
        with self.assertRaises(ContractError):self.owner.amend(self.wid,'rewrite',2,[node('remember','remember',['changed'])],'forged')
        self.owner.advance(self.wid,2);self.complete();self.assertEqual(self.owner.advance(self.wid,2)['status'],'complete')

    def test_started_unknown_cannot_be_dropped_by_amendment(self):
        self.admit();self.owner.advance(self.wid,1)
        new=self.owner.amend(self.wid,'drop-unstarted',1,[],'cancel remaining suffix')
        self.assertEqual([x['node'] for x in new['plan']],['remember'])
        self.assertEqual(new['status'],'needs-reconciliation');self.assertEqual(new['reservations_spent'],1)
        self.assertEqual(self.owner.advance(self.wid,2)['status'],'needs-reconciliation')
        self.assertEqual(len(self.store.observe('A',self.sid)['inputs']),1)

    def test_approve_checkpoint_rechecks_guard_and_decision_replays(self):
        guard=dict(id='capacity',kind='capacity-authority',policy=KINDS['capacity-authority'],scope=SCOPE,
            target=dict(session=self.sid,minimum_inputs=7,minimum_pending=1),predicate=None)
        plan=steps(guard);plan[2]['checkpoint']=True;self.through_two(plan)
        paused=self.owner.checkpoint(self.wid,'review',1,'review changed source');checkpoint=paused['checkpoints'][0]
        self.assertFalse(checkpoint['binding']['grants_authority'])
        decided=self.owner.decide(self.wid,'review','decision','operator',checkpoint['binding_sha256'],'approve')
        self.assertEqual(self.owner.decide(self.wid,'review','decision','operator',checkpoint['binding_sha256'],'approve'),decided)
        held=self.owner.advance(self.wid,1);self.assertEqual(held['status'],'prerequisite-held')
        self.assertEqual(held['reservations_spent'],2)

    def test_checkpoint_wrong_digest_refusal_and_no_resurrection(self):
        self.admit();paused=self.owner.checkpoint(self.wid,'review',1,'review');cp=paused['checkpoints'][0]
        with self.assertRaisesRegex(ContractError,'CONFLICT'):self.owner.decide(self.wid,'review','d','operator','0'*64,'approve')
        refused=self.owner.decide(self.wid,'review','d','operator',cp['binding_sha256'],'refuse')
        self.assertEqual(refused['status'],'refused');self.assertEqual(self.owner.advance(self.wid,1)['reservations_spent'],0)
        with self.assertRaisesRegex(ContractError,'NOT_AVAILABLE'):self.owner.amend(self.wid,'resurrect',1,steps(),'forbidden')

    def test_expired_decision_is_observation_without_new_work(self):
        self.admit();cp=self.owner.checkpoint(self.wid,'review',1,'review')['checkpoints'][0];self.now[0]=9000
        value=self.owner.decide(self.wid,'review','late','operator',cp['binding_sha256'],'approve')
        self.assertFalse(value['checkpoints'][0]['decision']['effective']);self.assertEqual(value['status'],'expired')
        with self.assertRaisesRegex(ContractError,'DEADLINE_EXCEEDED'):self.owner.advance(self.wid,1)
        self.assertEqual(self.store.observe('A',self.sid)['inputs'],[])

    def test_revocation_selection_change_and_clock_rollback_refuse(self):
        self.admit();self.revoked=True
        for operation in (lambda:self.owner.observe(self.wid),lambda:self.owner.advance(self.wid,1)):
            with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):operation()
        self.revoked=False;self.observations.selections={'sessions':'changed'}
        with self.assertRaisesRegex(ContractError,'CONFLICT'):self.owner.advance(self.wid,1)
        self.observations.selections={'sessions':'frozen'};self.now[0]=999
        with self.assertRaisesRegex(ContractError,'CONFLICT'):self.owner.advance(self.wid,1)

    def test_observation_only_clone_cannot_mutate(self):
        self.admit();clone=Workflow(self.store,'A',self.observations,self.auth,clock=lambda:self.now[0],initialize=False,observation_only=True)
        self.assertTrue(clone.observe(self.wid)['observation_only'])
        for call in (lambda:clone.advance(self.wid,1),lambda:clone.checkpoint(self.wid,'c',1,'x'),
                     lambda:clone.amend(self.wid,'a',1,[],'x')):
            with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):call()

    def test_real_process_kill_after_acceptance_recovers_capture_without_resubmit(self):
        self.admit();path=self.path;cfg=copy.deepcopy(self.cfg);sid=self.sid;wid=self.wid
        def killed():
            s=SustainedSessionStore(path,lambda *_:None,cfg,clock=lambda:1000)
            obs=OwnerObservations(SCOPE,'A',s,{'sessions':'frozen'},clock=lambda:1000)
            def hook(stage):
                if stage=='after_workflow_native_acceptance':os.kill(os.getpid(),signal.SIGKILL)
            Workflow(s,'A',obs,lambda *_:None,clock=lambda:1000,hook=hook).advance(wid,1)
        p=multiprocessing.get_context('fork').Process(target=killed);p.start();p.join(5)
        self.assertEqual(p.exitcode,-signal.SIGKILL)
        before=self.owner.observe(wid);self.assertEqual(before['reservations_spent'],1)
        self.complete();after=self.owner.observe(wid)
        self.assertEqual(after['steps']['remember']['deadline_ms'],before['steps']['remember']['deadline_ms'])
        self.assertIsNotNone(after['steps']['remember']['result_sha256']);self.assertEqual(len(self.store.observe('A',sid)['inputs']),1)

    def test_kill_after_reservation_keeps_absent_acceptance_unknown_and_spent(self):
        self.admit()
        def hook(stage):
            if stage=='after_workflow_input_reservation':raise RuntimeError('fixture process boundary')
        self.owner.hook=hook
        with self.assertRaises(RuntimeError):self.owner.advance(self.wid,1)
        self.owner.hook=lambda _:None
        before=self.owner.observe(self.wid);after=self.owner.advance(self.wid,1)
        self.assertEqual(before['reservations_spent'],after['reservations_spent']);self.assertEqual(after['status'],'needs-reconciliation')
        self.assertEqual(self.store.observe('A',self.sid)['inputs'],[])

if __name__=='__main__':unittest.main()
