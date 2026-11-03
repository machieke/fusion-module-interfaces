import copy,unittest
from integration.single_node.sustained_restore_qualification import clone_values
from integration.single_node.sustained_values import generate
from tests.test_phase2_operator_values import image_manifest_fixture
from fusion.contracts import ContractError

class FencedValues(unittest.TestCase):
 def test_clone_preserves_owner_scope_and_allocation_identity_without_workers(self):
  before=generate(image_manifest_fixture(),'synthetic-restore-phase3');saved=copy.deepcopy(before);after=clone_values(before)
  self.assertEqual(before,saved)
  for key in ('scope','policy_revision','sustained','agents'):self.assertEqual(before['preview'][key],after['preview'][key])
  self.assertFalse(after['futureLive']['enabled'])
  for value in after['components'].values():self.assertFalse(value['config']['nativeEnabled']);self.assertFalse(value['config']['workerEnabled'])
 def test_other_profile_cannot_silently_gain_restore_read_semantics(self):
  value=generate(image_manifest_fixture(),'synthetic-restore-profile');value['preview']['profile']='omega-single-node-developer-preview/1'
  with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):clone_values(value)
