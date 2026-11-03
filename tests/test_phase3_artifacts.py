"""Actual offline verifier over explicit OCI/configuration/wheel fixtures."""
import tempfile,unittest
from pathlib import Path
from fusion.contracts import canonical,ContractError
from integration.single_node.reference_artifacts import verify
from sdk.test_preview_distribution import FixtureDistribution

class SustainedArtifacts(unittest.TestCase):
 def test_only_explicit_recorded_disabled_sustained_examples_are_accepted(self):
  with tempfile.TemporaryDirectory() as directory:
   f=FixtureDistribution(Path(directory)/'packet');f.values['preview'].update(profile='omega-single-node-sustained-preview/1',sustained={})
   f.values['components']={role:dict(config=dict(nativeEnabled=False,workerEnabled=False)) for role in ('omega-agent','omega-agent-b')}
   def save():f.write('profiles/preview.yaml',canonical(f.values));return f.save()
   self.assertEqual(verify(save())['status'],'OFFLINE_VERIFIED')
   for change in ('model','worker'):
    if change=='model':f.values['preview']['sustained']['model_binding']={'mode':'live'}
    else:f.values['components']['omega-agent']['config']['nativeEnabled']=True
    with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):verify(save())
    f.values['preview']['sustained'].pop('model_binding',None)
