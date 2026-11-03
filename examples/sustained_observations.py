"""Bounded operator observations of the retained sustained deployment.

Run after native qualification, with no active native inputs. Diagnostics run
inside each respective owner pod and return counters, never private payloads.
This example neither submits native work nor starts a generative runtime.
"""
import argparse,json,time
from pathlib import Path
from fusion.contracts import canonical,digest,require
from integration.single_node.reference_ops import Operator,PYTHON

LOOKUP = '''import json,sqlite3,time,statistics
from pathlib import Path
p=Path('/state/memory/feed.sqlite')
db=sqlite3.connect(p.as_uri()+'?mode=ro',uri=True);db.execute('PRAGMA query_only=ON');db.execute('BEGIN')
rows=db.execute('SELECT scope,value,payload FROM feed_atoms ORDER BY sequence').fetchall()
assert rows and len(rows)<=4096
chosen=rows[::max(1,len(rows)//12)][-12:];samples={'scan':[],'index':[]}
for repeat in range(3):
 for scope,encoded,payload in chosen:
  ref=json.loads(encoded)['write']['ref']['id']
  for name in (('scan','index') if repeat%2==0 else ('index','scan')):
   start=time.perf_counter_ns()
   if name=='scan':
    result=next((v,p) for v,p in db.execute('SELECT value,payload FROM feed_atoms WHERE scope=?',(scope,)).fetchall() if json.loads(v)['write']['ref']['id']==ref)
   else:
    found=db.execute("SELECT value,payload FROM feed_atoms WHERE scope=? AND json_extract(value,'$.write.ref.id')=?",(scope,ref)).fetchall()
    assert len(found)==1;result=found[0];assert json.loads(result[0])['write']['ref']['id']==ref
   samples[name].append((time.perf_counter_ns()-start)/1e6)
   assert result==(encoded,payload)
print(json.dumps(dict(records=len(rows),samples={k:dict(count=len(v),median_ms=statistics.median(v),total_ms=sum(v)) for k,v in samples.items()},equivalent_results=True,scope='owner-local reference metadata lookup only; no end-to-end speedup inference')))
'''

PROMPTS = '''import json,sqlite3
from pathlib import Path
out=[]
for label,base in [('shared',Path('/state')),('private-a',Path('/state/scopes/private-a')),('private-b',Path('/state/scopes/private-b'))]:
 p=base/'model.sqlite';assert p.exists()
 db=sqlite3.connect(p.as_uri()+'?mode=ro',uri=True);db.execute('PRAGMA query_only=ON');db.execute('BEGIN')
 rows=db.execute('SELECT intent,response,reserved FROM model_calls').fetchall();assert len(rows)<=512
 a=sum('synthetic private A canary' in intent for intent,_,_ in rows)
 b=sum('synthetic private B canary' in intent for intent,_,_ in rows)
 if label=='shared':assert a==b==0
 if label=='private-a':assert a>0 and b==0
 if label=='private-b':assert b>0 and a==0
 out.append(dict(partition=label,calls=len(rows),captured=sum(response is not None for _,response,_ in rows),reserved=sum(n for _,_,n in rows),own_canary_seen=(a>0 or b>0),foreign_canary_seen=False))
print(json.dumps(dict(status='PASS',classification='real captured recorded-model inputs; no live generation',partitions=out,raw_prompts_exported=False)))
'''

RESOURCE = '''import json,time
from pathlib import Path
values={}
for name in ('cpu.max','cpu.stat','memory.max','memory.current','memory.peak','memory.events','pids.current'):
 p=Path('/sys/fs/cgroup')/name
 values[name]=p.read_text()[:2048] if p.exists() else 'UNAVAILABLE'
print(json.dumps(dict(observed_ms=time.time_ns()//1000000,cgroup=values,cpu_quota_enforcement='NOT_ESTABLISHED_BY_CONFIG_OR_COUNTER_READ')))
'''

def observe(op,native,directory):
    root=Path(directory);root.mkdir(parents=True,exist_ok=False)
    raw=Path(native).read_bytes();report=json.loads(raw)
    require(report['namespace']==op.namespace and report['status']=='PASS','NOT_AVAILABLE');op.owned()
    result=dict(status='RUNNING',namespace=op.namespace,native_report_sha256=digest(raw),additional_live_generations=0,stages={},resources={})
    def save():(root/'report.json').write_bytes(canonical(result))
    def code(role,source,timeout=45):return json.loads(op.k('exec','-i',role+'-0','--',PYTHON,'-',data=source,timeout=timeout))
    save()
    try:
        pods=json.loads(op.k('get','pods','-l','app.kubernetes.io/instance=omega','-o','json'))['items']
        for pod in pods:
            role=pod['metadata']['name'].removesuffix('-0')
            if role=='f1r3node':continue  # This observation cannot activate chain or model processes.
            result['resources'][role]=dict(configured=[c.get('resources',{}) for c in pod['spec']['containers']],observed=code(role,RESOURCE))
            result['stages'][role]=json.loads(op.k('exec',role+'-0','--',PYTHON,'-m','integration.single_node.sustained_diagnostics',timeout=45));save()
        result['lookup']=code('fusion-storage',LOOKUP)
        result['private_context']=code('fusion-model',PROMPTS);save()
        a=next(x for x in report['private_cases'] if x['role']=='omega-agent')
        private_sid=next(x['value']['session'] for x in report['allocations'] if x['role']=='omega-agent' and x['template']=='private')
        source='''import json
from pathlib import Path
from fusion.contracts import ContractError,canonical
from integration.single_node.sustained_current import observe
from integration.single_node.preview_operator import request
p=Path('/run/fusion/owner.json');original=p.read_bytes();v=json.loads(original)
scope=SCOPE;sid=SID
assert 'sessions.disclose' in v['principals']['operator']['scopes'][scope]
v['principals']['operator']['scopes'][scope].remove('sessions.disclose');denied=[]
try:
 p.write_bytes(canonical(v))
 for name,call in [('current',lambda:observe(sid)),('retained',lambda:request('observe',sid,dict(content=True)))]:
  try:call()
  except ContractError as error:assert error.code=='UNAUTHORIZED';denied.append(name)
  else:raise AssertionError('revoked disclosure returned content')
finally:p.write_bytes(original)
assert p.read_bytes()==original
print(json.dumps(dict(status='PASS',denied=denied,authority_restored_exactly=True,journals_edited=False)))
'''.replace('SCOPE',repr(a['current']['scope'])).replace('SID',repr(private_sid))
        result['private_operator_revocation']=code('omega-agent',source);save()
        bsid=next(x['value']['session'] for x in report['allocations'] if x['role']=='omega-agent-b' and x['template']=='shared')
        source='''import json
from pathlib import Path
from fusion.preview_atoms import client
from integration.single_node.sustained_runtime import materialize
p=materialize(Path('/run/fusion/owner.json'),Path('/state'),Path('/run/fusion'),SID)
app=json.loads(p.read_bytes());cfg=json.loads(Path(app['memory_atoms_config']).read_bytes())
payload=client(cfg).get(REF);value=json.loads(payload.bytes)
assert value==dict(profile='operator-approved-synthetic-projection/1',content='cabinet birch',evidence='operator-approved-projection-not-independent-observation')
print(json.dumps(dict(status='PASS',content='cabinet birch',private_identifiers_or_roots=False,recipient='B',authoritative_payload_verified=True)))
'''.replace('SID',repr(bsid)).replace('REF',repr(report['approved_projection']['shared']))
        result['approved_projection_recipient']=code('omega-agent-b',source)
        result['status']='PASS';save()
    except BaseException as error:
        result.update(status='FAILED',failure=dict(type=type(error).__name__,code=getattr(error,'code',None),detail=str(error)[-1000:]));save();raise
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('kubeconfig','context','namespace','native','directory'):p.add_argument('--'+name,required=True)
    a=p.parse_args();print(json.dumps(observe(Operator(a.kubeconfig,a.context,a.namespace),a.native,a.directory)))
if __name__=='__main__':main()
