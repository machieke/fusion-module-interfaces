"""Pure source-selection checks; no supervisor, process or runtime launch."""
import ast,hashlib,json,unittest
from pathlib import Path
HERE=Path(__file__).parent
class Selection(unittest.TestCase):
 def test_only_native_pin_and_packet_path_changed(self):
  old=(HERE.parent/'h20-supervision-source/h20-detached-command.py').read_text()
  new=(HERE/'h21-detached-command.py').read_text()
  actual=hashlib.sha256((HERE.parent/'h21-rehearsal-source/h19-native.py').read_bytes()).hexdigest()
  expected=old.replace('30165c0fe79f7a5778ef2973d4d91cf8536ae6783f68e74191f693b62665bb28',actual).replace('h19-rehearsal-source/h19-native.py','h21-rehearsal-source/h19-native.py')
  self.assertEqual(new,expected);ast.parse(new)
 def test_clean_recipe_and_inner_limits_unchanged(self):
  source=(HERE/'h21-detached-command.py').read_text()
  self.assertIn('6911b2ccc03042c4d0543b25b0881d01a80cf271f5f0608219b2a79b527371e3',source)
  self.assertIn('h20-clean-install-source/h20-offline.py',source)
  self.assertIn("plan['maximum_programme_seconds'] == 4200",source)
  self.assertIn("plan['cleanup_reserved_seconds'] == 300",source)
  self.assertIn("plan['max_seconds'] == 1800",source)
  self.assertIn("/ 'h19-native/start.json'",source)
 def test_public_plan_is_disabled_and_fresh(self):
  root=HERE.parent/'h21-rehearsal-source';p=json.loads((root/'plan.DISABLED.json').read_bytes())
  self.assertIs(p['enabled'],False);self.assertIsNone(p['distribution_sha256'])
  self.assertEqual(p['source_files']['h19-native.py'],hashlib.sha256((root/'h19-native.py').read_bytes()).hexdigest())
  self.assertEqual(p['namespaces'],['omega-ref-pilot-adopter21','omega-ref-pilot-adopter21-go'])
if __name__=='__main__':unittest.main(verbosity=2)
