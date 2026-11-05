"""Finite normal-port receipt observation only; no workflow drive or mutation."""
import json,time
from pathlib import Path
from fusion.contracts import canonical,digest,require
from integration.single_node.reference_ops import Operator,PYTHON
root=Path('/data/fusion-operator-pilot-release/qualification-private/workflows-14');op=Operator(root/'kubeconfig','default','omega-ref-pilot-recipe13');path=root/'chain-task-receipts.json'
require(not path.exists(),'CONFLICT');end=time.monotonic()+180;report=dict(status='RUNNING',namespace=op.namespace,source_sha256=digest(Path(__file__).read_bytes()),maximum_seconds=180,maximum_list_calls=24,maximum_observe_calls=32,expected_task_sessions=7,list_calls=0,observe_calls=0,observations={},failures=[],new_native_inputs=0,additional_live_generations=0)
def save():path.write_bytes(canonical(report))
def call(operation,session=None):
 require(time.monotonic()<end,'NOT_AVAILABLE');command=[PYTHON,'-m','integration.single_node.preview_operator',operation]
 if session:command+=['--session',session,'--content']
 return json.loads(op.k('exec','omega-agent-b-0','--',*command,timeout=max(1,min(20,end-time.monotonic()))))
save()
try:
 op.owned()
 for _ in range(24):
  require(time.monotonic()<end,'NOT_AVAILABLE');report['list_calls']+=1;rows=call('list');require(type(rows) is list and len(rows)<=7,'CONFLICT');report['last_list']=rows;save()
  for row in rows:
   prior=report['observations'].get(row['session'])
   if prior and prior['inputs'] and all(x['state']=='complete' for x in prior['inputs']):continue
   require(report['observe_calls']<32,'OVERLOADED');report['observe_calls']+=1;value=call('observe',row['session']);require(value['session']==row['session'],'CONFLICT');report['observations'][row['session']]=value;save()
  if len(rows)==7 and len(report['observations'])==7 and all(v['inputs'] and all(x['state']=='complete' for x in v['inputs']) for v in report['observations'].values()):
   report['status']='OBSERVED_COMPLETE';break
  time.sleep(min(4,max(0,end-time.monotonic())))
 else:report['status']='OBSERVER_TIMEOUT'
except BaseException as error:
 report.update(status='FAILED',failure=dict(type=type(error).__name__,code=getattr(error,'code',None),detail=str(error)[-1000:]));raise
finally:
 report['actual_captured_inputs']=sum(x['state']=='complete' and x.get('result') is not None for v in report['observations'].values() for x in v['inputs']);save()
print(json.dumps(dict(status=report['status'],actual_captured_inputs=report['actual_captured_inputs'],additional_live_generations=0)))
