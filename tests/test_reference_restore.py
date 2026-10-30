import unittest
from unittest.mock import patch
from pathlib import Path
from fusion.contracts import ContractError
from integration.single_node.restore_host import allowed
from integration.single_node import future_live
class Fence(unittest.TestCase):
 def test_effects_never_allowed(self):
  for role,path,operation in [('fusion-storage','/s03-append','create'),('fusion-search','/s03-append','build'),('fusion-model','/s07-model','complete'),('fusion-channel-bridge','/send','send'),('fusion-commitment','/commitment','submit'),('fusion-execution','/s01','submit')]:
   with self.assertRaises(ContractError) as e:allowed(role,path,dict(operation=operation))
   self.assertEqual(e.exception.code,'UNAUTHORIZED')
 def test_only_explicit_reads(self):
  allowed('fusion-storage','/memory-source',dict(operation='readCommits'))
  allowed('fusion-search','/s03-read',dict(operation='query'))
 def test_old_approval_cannot_bypass_restored_fence(self):
  with patch.object(Path,'exists',return_value=True):
   with self.assertRaises(ContractError) as e:future_live.approve('/missing-old-plan','/old-approval')
  self.assertEqual(e.exception.code,'UNAUTHORIZED')
if __name__=='__main__':unittest.main()
