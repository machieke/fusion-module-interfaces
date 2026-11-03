import unittest
from integration.single_node.sustained_evaluation import freeze,score,DATASETS,stopped_premise

class IndependentEvaluation(unittest.TestCase):
 def test_factual_failure_remains_distinct_from_output_permission(self):
  wrong=score('The prism is in crate saffron',DATASETS['new'])
  self.assertEqual(wrong['permission'],'PERMITTED');self.assertEqual(wrong['factual_correctness'],'INCORRECT');self.assertFalse(wrong['task_pass'])
  denied=score('crate orchid',DATASETS['new'],permitted=False)
  self.assertEqual(denied['factual_correctness'],'CORRECT');self.assertFalse(denied['task_pass'])
 def test_counterfactual_and_absence_do_not_share_expected_answers(self):
  self.assertTrue(score('crate saffron',DATASETS['changed'])['task_pass'])
  self.assertFalse(score('crate orchid',DATASETS['changed'])['task_pass'])
  self.assertFalse(score('topaz key is stored in crate alder',DATASETS['absent'])['task_pass'])
 def test_frozen_zero_authority_plan_and_explicit_reassessment(self):
  self.assertEqual(freeze(),freeze());self.assertEqual(freeze()['plan']['held_out_live']['allowance'],0)
  self.assertFalse(stopped_premise('old','new','continue as before')['task_pass'])
  self.assertTrue(stopped_premise('old','new','REASSESS changed source')['task_pass'])
