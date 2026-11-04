"""Bounded authored timing rows. These tests assert no performance outcome."""
import json,tempfile,unittest
from pathlib import Path
from integration.single_node.sustained_diagnostics import collect
from fusion.contracts import ContractError

class Measurements(unittest.TestCase):
    def test_bytes_unknowns_parent_edges_and_nearest_rank_are_distinct(self):
        with tempfile.TemporaryDirectory() as root:
            rows=[dict(profile='bounded-native-stage-timing/1',process='fixture',pid=1,span=i,parent=None if i==1 else 1,
                name='fixture.operation',duration_ns=i*1000000,request_bytes=None if i%2 else 12,response_bytes=4,code=None) for i in range(1,21)]
            path=Path(root)/'native-stages.jsonl';path.write_text(''.join(json.dumps(row)+'\n' for row in rows))
            result=collect(root);value=result['stages']['fixture.operation']
            self.assertEqual(value['p95_ms'],19);self.assertEqual(result['observed_local_parent_edges'],19)
            self.assertEqual(value['bytes']['request_bytes'],dict(observed_samples=10,unknown_samples=10,observed_total=120))
            self.assertTrue(result['nested_durations_are_not_additive'])
            rows[0]['request_bytes']=-1;path.write_text(json.dumps(rows[0])+'\n')
            with self.assertRaises(ContractError):collect(root)

if __name__=='__main__':unittest.main()
