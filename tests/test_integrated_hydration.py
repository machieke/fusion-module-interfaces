"""Exact history rendering with declared batch ports and file-backed fixtures."""
import unittest
from unittest.mock import patch
from fusion.contracts import ContractError,canonical
from fusion.ports import Mutation
from fusion.preview_native_history import NativeHistory,write_body,read_body
from tests import test_phase2_history_projection as fixture
from tests.test_phase2_native_relations import NOW,SCOPE

class Hydration(unittest.TestCase):
    setUp=fixture.HistoryProjectionReconstruction.setUp
    reopen=fixture.HistoryProjectionReconstruction.reopen
    atom_client=fixture.HistoryProjectionReconstruction.atom_client
    record=fixture.HistoryProjectionReconstruction.record
    populate=fixture.HistoryProjectionReconstruction.populate
    def test_same_retained_history_bytes_via_four_item_batch_and_current_authority(self):
        self.populate();before=self.history.context()
        self.app.config['history_hydration']='bounded-history-hydration/1';self.history=NativeHistory(self.app,self.port)
        with patch.object(self.atoms,'getMany',wraps=self.atoms.getMany) as batch:
            self.assertEqual(self.history.context(),before);self.assertEqual(batch.call_count,1);self.assertEqual(len(batch.call_args.args[0]),4)
        self.atom_access.denied.add('get')
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):self.history.context()
        self.atom_access.denied.clear();self.record(7);self.assertEqual(self.history.context(),before)
        self.turn=2;self.assertNotEqual(self.history.context(),before)
    def test_large_chunk_batch_is_bounded_ordered_and_digest_validated(self):
        body=dict(text='synthetic'*7000);stored=write_body(self.atoms,SCOPE,'large',canonical(body));ref=stored['ref']
        self.assertEqual(read_body(self.atoms,ref),body)
        with patch.object(self.atoms,'getMany',wraps=self.atoms.getMany) as batch:
            self.assertEqual(read_body(self.atoms,ref,batched=True),body)
            self.assertEqual(batch.call_count,2);self.assertTrue(all(len(x.args[0])<=8 for x in batch.call_args_list))
        original=self.atoms.getMany
        with patch.object(self.atoms,'getMany',side_effect=lambda refs:tuple(reversed(original(refs)))):
            with self.assertRaises(ContractError):read_body(self.atoms,ref,batched=True)

if __name__=='__main__':unittest.main()
