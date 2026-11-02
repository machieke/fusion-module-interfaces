"""Authored input-command fixture only; native admission remains separate."""
import json,tempfile,unittest
from dataclasses import asdict
from pathlib import Path
from fusion import preview_model_contracts as c
from fusion.contracts import canonical,digest,ContractError
from fusion.preview_recorded_model import RecordedProposals
from tests import test_phase2_model as fixtures

class AuthoredInput(unittest.TestCase):
    setUp=fixtures.PreviewModelTests.setUp
    save=fixtures.PreviewModelTests.save
    close_owners=fixtures.PreviewModelTests.close_owners
    def test_input_command_fixture_only_proposes_exact_operator_text(self):
        self.cfg['model_completion']['recorded_proposals']={self.session+'/1':{'proposal':'input-command'}}
        self.cfg['model_completion']['runtime_lock']=dict(profile=c.PROFILE,generative_runtime='FORBIDDEN',proposals_sha256=digest(canonical(self.cfg['model_completion']['recorded_proposals'])))
        self.save();backend=RecordedProposals(self.path)
        raw="Selected tools and actual feedback:-:-:-:"+str(['HUMAN-MSG:','remember Synthetic bounded fact'])
        accepted={**self.accepted,'native_prompt':raw,'messages':c.messages(raw)}
        result=backend.complete(c.CompletionInput(**accepted))
        self.assertEqual(result['raw_text'],'remember Synthetic bounded fact')
        self.assertTrue(all(x is None for x in result['usage'].values()))
        # The proposal boundary does not decide authority or repair commands.
        raw="Selected tools:-:-:-:"+str(['HUMAN-MSG:','metta (arbitrary-command)'])
        result=backend.complete(c.CompletionInput(**{**accepted,'native_prompt':raw,'messages':c.messages(raw)}))
        self.assertEqual(result['raw_text'],'metta (arbitrary-command)')
        self.assertFalse((self.root/'model.sqlite').exists())
