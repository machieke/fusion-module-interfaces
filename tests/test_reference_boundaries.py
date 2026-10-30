"""Reference distribution's supported Protocol/hostile-port boundary."""
import unittest
from fusion.ports import AtomStorage
from fusion.contracts import ContractError
from fusion.private import open_private
from tests.m2_support import MemoryHarness,PortOnly,SCOPE

class Boundaries(unittest.TestCase):
    def test_static_protocol_exposes_only_admitted_methods(self):
        h=MemoryHarness();self.addCleanup(h.close)
        from fusion.adapters.fixture_atoms import FileAtomFixture
        from fusion.private import OPERATIONS
        wrapped=PortOnly(FileAtomFixture(str(h.root/'ports'),str(h.root/'bytes')),OPERATIONS['atom.storage'])
        self.assertIsInstance(wrapped,AtomStorage)
        with self.assertRaises(AssertionError):wrapped.database
        with self.assertRaises(AssertionError):wrapped._methods
        incompatible=PortOnly(wrapped,('get','getMany'))
        self.assertNotIsInstance(incompatible,AtomStorage)
        with self.assertRaises(ContractError) as caught:
            open_private(h.path,h.credential,SCOPE,atom_fixture=incompatible,math_fixture=h.math)
        self.assertEqual(caught.exception.code,'UNSUPPORTED_PROFILE')
