"""Real lifecycle owner; file AtomStorage/unit-vector fixtures labelled explicitly."""
import copy,unittest
from fusion.contracts import ContractError,canonical,digest
from fusion.workflow_prerequisites import OwnerObservations,KINDS,condition
from integration.single_node.pilot_workflow_evaluation import freeze,score
from tests import test_phase2_lifecycle as lifecycle_fixture

class Prerequisites(unittest.TestCase):
    def setUp(self):
        self.f=lifecycle_fixture.LifecycleTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.first=self.f.owner.change(self.f.command('initial'),'introduce',enrollment=self.f.enrolled('synthetic initial'))
        self.ports=[];owner=self.f.owner
        class Port:
            def call(inner,op,*args,deadline=None):
                self.ports.append(op)
                if op=='head':return owner.head()
                if op=='activeSet':return owner.activeSet(*args)
                raise AssertionError('non-read prerequisite')
        self.observer=OwnerObservations('synthetic-lifecycle','A',None,{'lifecycle':'reviewed-fixture-port'},lifecycle=Port(),clock=lambda:1000)
        self.condition=dict(id='memory-revision',kind='memory-active',policy=KINDS['memory-active'],scope='synthetic-lifecycle',
            target=dict(logical_id=self.first['logical_id'],revision=1,payload=self.first['memory']['payload']),predicate=None)
        self.oracle=freeze()

    def evaluate(self,variant):
        result=self.observer.observe(self.condition,2000);held=result['state']!='SATISFIED'
        observed=dict(owner_dataflow=True,prerequisite=result['state'],progression='held' if held else 'admitted',
            tool_result=None if held else True,provenance=True,answer_correct=None if held else True,
            external_receipt='NOT_REQUESTED',chain_effect='NOT_REQUESTED',captured_before=self.first,captured_after=self.first)
        return result,score(variant,observed,self.oracle),observed

    def test_unchanged_and_irrelevant_source_change_use_actual_owner_membership(self):
        first,scored,_=self.evaluate('unchanged');self.assertEqual(scored['safety_objective'],'PASS')
        self.f.owner.change(self.f.command('irrelevant'),'introduce',enrollment=self.f.enrolled('unrelated'))
        second,scored,_=self.evaluate('irrelevant-change');self.assertEqual(scored['safety_objective'],'PASS')
        self.assertNotEqual(first['evidence']['at'],second['evidence']['at'])
        self.assertEqual(first['evidence']['selected'],second['evidence']['selected'])
        self.assertEqual(self.ports,['head','activeSet','head','activeSet'])

    def test_actual_withdrawal_denies_same_condition_and_preserves_prior_record(self):
        before=self.f.atoms.get(self.first['memory']['payload']).bytes
        self.f.owner.change(self.f.command('withdraw'),'withdraw',logical_id=self.first['logical_id'],expected_revision=1)
        observed,scored,_=self.evaluate('withdrawn')
        self.assertEqual(observed['state'],'INVALID');self.assertEqual(scored['safety_objective'],'PASS')
        self.assertEqual(scored['positive_task'],'NOT_COMPLETED')
        self.assertEqual(self.f.atoms.get(self.first['memory']['payload']).bytes,before)
        self.assertEqual(self.f.owner.activeSet(self.first['at'])['active'][0]['revision'],1)

    def test_supersession_invalidates_exact_revision_without_truth_reinterpretation(self):
        self.f.owner.change(self.f.command('supersede'),'supersede',logical_id=self.first['logical_id'],
            expected_revision=1,enrollment=self.f.enrolled('synthetic successor'))
        v=self.observer.observe(self.condition,2000);self.assertEqual(v['state'],'INVALID')
        self.assertEqual(v['evidence']['selected']['revision'],2)

    def test_current_revocation_and_missing_port_are_distinct(self):
        self.f.access.revoked=True
        result,scored,_=self.evaluate('unauthorized');self.assertEqual(result['error'],'UNAUTHORIZED')
        self.assertEqual(scored['safety_objective'],'PASS')
        self.f.access.revoked=False;self.observer.lifecycle=None
        result,scored,_=self.evaluate('unknown');self.assertEqual(result['state'],'UNKNOWN')
        self.assertEqual(scored['safety_objective'],'PASS')

    def test_injected_true_unknown_or_wrong_answer_fails_independent_oracle(self):
        _,_,observed=self.evaluate('unchanged');observed['answer_correct']=False
        self.assertEqual(score('unchanged',observed,self.oracle)['positive_task'],'FAIL')
        observed['prerequisite']='SATISFIED';observed['progression']='admitted'
        self.assertEqual(score('withdrawn',observed,self.oracle)['safety_objective'],'FAIL')
        self.assertEqual(score('unknown',observed,self.oracle)['safety_objective'],'FAIL')
        altered=copy.deepcopy(self.oracle);altered['plan']['variants']['withdrawn']['progression']='admitted'
        with self.assertRaisesRegex(ContractError,'CONFLICT'):score('withdrawn',observed,altered)

    def test_condition_cannot_select_sql_paths_functions_or_priority_as_truth(self):
        for extra in ('sql','function','path','endpoint'):
            wrong=dict(self.condition,**{extra:'arbitrary'})
            with self.assertRaises(ContractError):condition(wrong,'synthetic-lifecycle')
        wrong=copy.deepcopy(self.condition);wrong['kind']='attention-truth'
        with self.assertRaisesRegex(ContractError,'UNSUPPORTED_PROFILE'):condition(wrong,'synthetic-lifecycle')
        wrong=copy.deepcopy(self.condition);wrong['scope']='synthetic-other'
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):condition(wrong,'synthetic-lifecycle')

if __name__=='__main__':unittest.main()
