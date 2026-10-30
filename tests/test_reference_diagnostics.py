import json,sqlite3,tempfile,unittest
from pathlib import Path
from integration.single_node.diagnostics import inspect,metrics
class Diagnostics(unittest.TestCase):
 def test_missing_state_does_not_create_files(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);self.assertEqual(inspect(root)['tables'],{});self.assertEqual(list(root.iterdir()),[])
 def test_reports_counters_without_sensitive_labels_or_mutation(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);file=root/'caller.sqlite'
   with sqlite3.connect(file) as db:
    db.execute('CREATE TABLE app_occurrences(id TEXT,result TEXT,done INTEGER,calls INTEGER)');db.execute("INSERT INTO app_occurrences VALUES('private-identity','secret contents',1,7)")
   before=file.read_bytes();v=inspect(root);self.assertEqual(file.read_bytes(),before)
   self.assertEqual(v['tables']['caller.sqlite:app_occurrences'],dict(rows=1,done_sum=1,calls_sum=7,result_captured=1))
   self.assertNotIn('secret',json.dumps(v));self.assertNotIn('private-identity',metrics(v))
 def test_native_chain_envelope_reports_finality_without_artifact_identity(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'final-observation.json').write_text(json.dumps(dict(detail=dict(chain=dict(effect_finality='finalized',deploy_id='synthetic-private-label',evidence=dict(value='payload'))))))
   self.assertEqual(inspect(root)['chain'],dict(effect_finality='finalized'))
