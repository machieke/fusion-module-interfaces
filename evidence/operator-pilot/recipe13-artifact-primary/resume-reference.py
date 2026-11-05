import importlib.util,json
from pathlib import Path
from fusion.contracts import digest
from integration.single_node.reference_ops import Operator
root=Path('/data/fusion-operator-pilot-release/qualification-private/workflows-14')
spec=importlib.util.spec_from_file_location('pinned_reference',root/'pilot_artifact_reference.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
(root/'reference-source-pin.json').write_text(json.dumps(dict(helper_sha256=digest((root/'pilot_artifact_reference.py').read_bytes()),runner_sha256=digest(Path(__file__).read_bytes()))))
op=Operator(str(root/'kubeconfig'),'default','omega-ref-pilot-recipe13')
m.resume(op,root/'reference-workflow-recovery',root/'recipe-chain-evidence')
