"""The narrowly selected test barrier releases no business work by itself."""
import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from fusion.contracts import ContractError,canonical
from integration.single_node.server import search_test_barrier

class Barrier(unittest.TestCase):
    def test_only_named_bounded_release_is_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);file=root/'search-repair-test-release.json'
            file.write_bytes(canonical({'stage':'after_search_repair_reservation'}))
            search_test_barrier(root,'after_search_repair_reservation')
            with self.assertRaisesRegex(ContractError,'UNSUPPORTED_OPERATION'):search_test_barrier(root,'after_socket_reservation')
            file.write_text('{}')
            with self.assertRaisesRegex(ContractError,'CONFLICT'):search_test_barrier(root,'after_search_repair_reservation')
            file.unlink();file.symlink_to(root/'other');(root/'other').write_text('{}')
            with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):search_test_barrier(root,'after_search_repair_reservation')
    def test_expiry_does_not_release_or_create_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch('integration.single_node.server.time.monotonic',side_effect=[0,121]):
                with self.assertRaisesRegex(ContractError,'DEADLINE_EXCEEDED'):search_test_barrier(directory,'after_search_repair_reservation')
            self.assertEqual(list(Path(directory).iterdir()),[])

if __name__=='__main__':unittest.main()
