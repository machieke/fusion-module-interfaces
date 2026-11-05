"""Pure evidence-matching fixtures; these do not claim real chain execution."""
import unittest
from fusion.contracts import ContractError,digest
from examples.pilot_recipe_chain import check_lineage

class RecipeChainEvidence(unittest.TestCase):
    def inputs(self):
        text='fixture captured native projection'
        workspace=dict(profile='synthetic-workspace-files/1',path='review.txt',revision=1,
            digest=digest(text.encode()),bytes=len(text.encode()),outcome='committed',identity='fixture-write')
        readback={k:workspace[k] for k in ('profile','path','revision','digest')};readback['text']=text
        source=dict(projection=text,result_ref={'fixture':'source'},task='fixture-task',artifact_ref={'fixture':'artifact'})
        return workspace,readback,source
    def test_exact_actual_projection_and_workspace_receipt(self):
        value=check_lineage(*self.inputs())
        self.assertTrue(value['workspace_and_inspection_share_captured_task_result'])
        self.assertEqual(value['inspection_boundary'],'IMMUTABLE_TASK_RESULT_ENVELOPE')
    def test_plausible_wrong_workspace_text_is_not_source_lineage(self):
        workspace,readback,source=self.inputs();readback['text']='wrong but permitted fixture text'
        with self.assertRaisesRegex(ContractError,'CONFLICT'):check_lineage(workspace,readback,source)
    def test_mismatched_owner_revision_or_byte_receipt_rejected(self):
        for key,value in [('revision',2),('bytes',1),('digest','0'*64)]:
            with self.subTest(field=key):
                workspace,readback,source=self.inputs();workspace[key]=value
                with self.assertRaisesRegex(ContractError,'CONFLICT'):check_lineage(workspace,readback,source)

if __name__=='__main__':unittest.main()
