import json,unittest
from pathlib import Path
names=json.loads(Path("evidence/s06/regression-native-spec.json").read_text())["methods"]
r=unittest.TextTestRunner(verbosity=2).run(unittest.TestLoader().loadTestsFromNames(names))
raise SystemExit(not r.wasSuccessful())
