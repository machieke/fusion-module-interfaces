"""Source negative controls; native persistence is exercised in test_m11."""
import unittest
from pathlib import Path
from integration.neoclaw.source_compatibility import detta, policy
from fusion.contracts import ContractError

ROOT = Path(__file__).resolve().parents[1]
HISTORICAL = 'c7f9577ce22636d6f75745007dbb095a693c49f4ea5f5e34312a4ba9711148b0'


class Provenance(unittest.TestCase):
    def test_exact_reviewed_identity_and_historical_snapshot(self):
        self.assertEqual(detta(ROOT,HISTORICAL), '99c948919abfbce31450ffae52e4b0be691a711d8ca047a13876514199fa009c')

    def test_unapproved_identity_and_weakened_lock_fail(self):
        current=(ROOT/'fusion/adapters/detta.py').read_bytes()
        for bad in (current+b'\n', current.replace(b', *self.owner_fds', b''),
                    current.replace(b'if digest(data) != result["content_hash"]:',b'if False:'),
                    current.replace(b'timeout=15',b'timeout=150')):
            with self.assertRaisesRegex(ContractError,'CONFLICT'):detta(ROOT,HISTORICAL,bad)

    def test_historical_pin_cannot_be_relabelled(self):
        with self.assertRaisesRegex(ContractError,'CONFLICT'):detta(ROOT,'0'*64)

    def test_writer_fence_addition_preserves_exact_scope_check(self):
        pin='dcab3e306907c163caabf98bedf3be582a8b84b679e8971c4703a0cdf900b18f'
        self.assertEqual(policy(ROOT,pin),'c1bc225750e36b73a7f4fa4bd70859cdf14d078712a8e0bd15f9ab8c01388c91')
        current=(ROOT/'fusion/policy.py').read_bytes()
        for bad in (current+b'\n',current.replace(b'require(method in methods,',b'require(True,'),
                    current.replace(b'check(current,',b'check({},')):
            with self.assertRaisesRegex(ContractError,'CONFLICT'):policy(ROOT,pin,bad)
