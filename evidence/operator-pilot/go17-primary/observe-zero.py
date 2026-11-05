import json,time
from pathlib import Path
from fusion.contracts import canonical,digest,require
from integration.single_node.reference_ops import Operator,PYTHON
R=Path('/data/fusion-operator-pilot-release/qualification-private/go-reference17');op=Operator(R/'kubeconfig','default','omega-ref-pilot-go17');end=json.loads((R/'start.json').read_bytes())['end_ms'];require(time.time_ns()//1000000<end,'DEADLINE_EXCEEDED')
report=dict(profile='read-only-empty-caller-preconfiguration-observation/1',source_sha256=digest(Path(__file__).read_bytes()),roles={},additional_native_inputs=0,additional_live_generations=0,original_programme_end_ms=end)
(R/'zero-observation-start.json').write_bytes(canonical(dict(source_sha256=report['source_sha256'],roles=['omega-agent','omega-agent-b'],database='/state/session-inbox.sqlite',mode='read-only',start_ms=time.time_ns()//1000000,end_ms=end)))
require(not json.loads(op.k('get','pods','-o','json'))['items'],'CONFLICT')
script='''import json,sqlite3,hashlib
from pathlib import Path
p=Path('/state/session-inbox.sqlite');r={'database_exists':p.exists(),'tables':{},'read_only':True}
if p.exists():
 before={str(x.name):hashlib.sha256(x.read_bytes()).hexdigest() for x in p.parent.glob('session-inbox.sqlite*') if x.is_file()}
 db=sqlite3.connect('file:'+str(p)+'?mode=ro',uri=True);db.execute('PRAGMA query_only=ON');names={x[0] for x in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
 for name in ('sustained_allocations','preview_sessions','preview_inputs','integrated_providers','integrated_provider_actions','integrated_provider_bindings'):
  r['tables'][name]=db.execute('SELECT count(*) FROM '+name).fetchone()[0] if name in names else None
 db.close();after={str(x.name):hashlib.sha256(x.read_bytes()).hexdigest() for x in p.parent.glob('session-inbox.sqlite*') if x.is_file()};assert before==after;r['database_bytes_unchanged']=True
print(json.dumps(r))'''
try:
 for role in ('omega-agent','omega-agent-b'):
  sts=json.loads(op.k('get','statefulset',role,'-o','json'));image=sts['spec']['template']['spec']['containers'][0]['image'];name=op.helper(role,image,'state-'+role+'-0',readonly=True)
  try:
   value=json.loads(op.k('exec',name,'--',PYTHON,'-c',script,timeout=40));require(all(v in (None,0) for v in value['tables'].values()),'CONFLICT');report['roles'][role]=value
  finally:op.k('delete','pod',name,'--wait=true')
 report['status']='PASS';report['observed_ms']=time.time_ns()//1000000
finally:(R/'zero-observation.json').write_bytes(canonical(report))
