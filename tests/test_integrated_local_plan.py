"""Plan validation is source checked, but causes no native/provider execution."""
import copy,json,unittest
from fusion.contracts import canonical,ContractError
from integration.neoclaw.controlled_run import ControlledRun
from integration.single_node.placement import freeze_local,compile_local

class LocalPlan(unittest.TestCase):
    def setUp(self):
        self.run=ControlledRun('local');self.addCleanup(self.run.close)
    def test_no_occurrence_or_credentials_in_plan_and_compile_is_inert(self):
        plan=freeze_local(self.run.app_path,self.run.h.config_path);value=compile_local(plan)
        self.assertEqual(value['native_argv'],['-m','integration.neoclaw.native_loop',str(self.run.app_path)])
        self.assertFalse(value['effects_started']);self.assertFalse(plan['deadline_started'])
        self.assertNotIn(self.run.h.client['credential'],canonical(plan).decode())
        self.assertFalse(__import__('pathlib').Path(self.run.h.client['database']).exists())
        changed=copy.deepcopy(plan);changed['placement']='pod-https'
        with self.assertRaisesRegex(ContractError,'CONFLICT'):compile_local(changed)
    def test_changed_bounds_profile_and_shared_owner_paths_refuse_before_effects(self):
        plan=freeze_local(self.run.app_path,self.run.h.config_path)
        self.run.h.client['max_attempts']=999;self.run.h.save_client()
        with self.assertRaisesRegex(ContractError,'CONFLICT'):compile_local(plan)
        with self.assertRaises(ContractError):freeze_local(self.run.app_path,self.run.h.config_path)
        self.run.h.client['max_attempts']=3;self.run.h.client['database']=self.run.h.config['database'];self.run.h.save_client()
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):freeze_local(self.run.app_path,self.run.h.config_path)

if __name__=='__main__':unittest.main()
