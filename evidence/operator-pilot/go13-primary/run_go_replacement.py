import json,time
from pathlib import Path
from unittest.mock import patch
from fusion.contracts import require,canonical,digest
from integration.single_node.reference_ops import Operator
from examples import pilot_go_provider as driver
from examples.pilot_network_edges import go_qualify
root=Path('/data/fusion-operator-pilot-release/qualification-private/workflows-14');packet=Path('/data/fusion-operator-pilot-release/distribution14');plan=json.loads((root/'go-order-reconciliation.json').read_bytes());left=plan['programme_deadline_ms']/1000-time.time();require(left>120,'DEADLINE_EXCEEDED');end=time.monotonic()+left
class ProgrammeBound(driver.Runner):
 @property
 def end(self):return self._end
 @end.setter
 def end(self,value):self._end=min(value,end)
 def run(self,*args,**kwargs):
  require(time.monotonic()+120<self.end,'DEADLINE_EXCEEDED')
  return super().run(*args,**kwargs)
op=Operator(root/'kubeconfig','default','omega-ref-pilot-go13')
with patch.object(driver,'Runner',ProgrammeBound):
 result=go_qualify(op,root/'go-replacement/plan.json',packet/'go-provider/provider-image.json',packet/'deploy/helm/omega-fusion',root/'go-replacement-evidence',root/'go-baseline',root/'go-capacity-authority',packet/'examples/pilot_go_capacity.py')
print(json.dumps(dict(status=result['status'],programme_deadline_ms=plan['programme_deadline_ms'],source_sha256=digest(Path(__file__).read_bytes()),additional_live_generations=0)))
