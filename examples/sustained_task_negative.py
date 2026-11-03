"""Adversarial Messaging observations using a real captured native task result.

The operator publishes one labelled synthetic stale-result candidate to existing
AtomStorage, then invokes the non-submitting `published` validator. It must be
rejected before mailbox acceptance. This is a negative contract test, never a
replacement for a native tool result or a successful agent workflow.
"""
import argparse,json
from pathlib import Path
from fusion.contracts import canonical,digest,require
from integration.single_node.reference_ops import Operator,PYTHON

def verify(op,native,directory):
    root=Path(directory);root.mkdir(parents=True,exist_ok=False)
    raw=Path(native).read_bytes();n=json.loads(raw);require(n['namespace']==op.namespace and n['status']=='PASS','NOT_AVAILABLE')
    task=next(x['task']['task'] for x in n['scenarios'] if x['scenario']=='two-agent-A-B')
    source='''import json,sqlite3,copy
from pathlib import Path
from fusion.contracts import canonical,digest,ContractError
from fusion.preview_native_history import read_body,write_body
from fusion.preview_atoms import client
from fusion.preview_tasks import Client
from fusion.preview_vector_contracts import snapshot
from integration.single_node.sustained_runtime import materialize
rows=[]
for directory in Path('/state/sessions').iterdir():
 p=directory/'caller.sqlite'
 if not p.is_file():continue
 db=sqlite3.connect(p.as_uri()+'?mode=ro',uri=True);db.execute('PRAGMA query_only=ON')
 if not db.execute("SELECT 1 FROM sqlite_master WHERE name='preview_task_outbox'").fetchone():continue
 row=db.execute('SELECT ref,record FROM preview_task_outbox WHERE id=?',('result/'+TASK,)).fetchone()
 if row:rows.append((directory.name,row))
assert len(rows)==1
sid,(ref,record)=rows[0];ref=json.loads(ref);body=json.loads(record)
app=json.loads(materialize(Path('/run/fusion/owner.json'),Path('/state'),Path('/run/fusion'),sid).read_bytes())
cfg=json.loads(Path(app['memory_atoms_config']).read_bytes());atoms=client(cfg);port=Client(app['task_config']);assert body['sender']=='B' and body['recipient']=='A'
assert read_body(atoms,ref)['body']==body
def refuse(reference,recipient,expected):
 try:port.call('published','result/'+body['id'],reference,recipient,body['deadline'],body['id'])
 except ContractError as error:assert error.code==expected;return error.code
 raise AssertionError('invalid result passed authoritative Messaging validator')
wrong=refuse(ref,'B','UNAUTHORIZED')
task=read_body(atoms,body['task'])['body'];assert task['minimum']['head']['sequence']>0
stale=copy.deepcopy(body);stale['view']['head']['sequence']=task['minimum']['head']['sequence']-1
stale['view']['logical']=digest(canonical({k:v for k,v in stale['view'].items() if k not in ('generation','logical')}));snapshot(stale['view'],cfg['scope'])
negative=write_body(atoms,cfg['scope'],'negative-stale-result/'+TASK,canonical(dict(body=stale)))['ref']
denied=refuse(negative,'A','NOT_AVAILABLE')
original=port.call('published','result/'+body['id'],ref,'A',body['deadline'],body['id']);assert original is not None
print(json.dumps(dict(status='PASS',wrong_agent=wrong,stale_view=denied,original_mailbox_receipt_retained=True,
 negative_candidate='explicit operator adversarial immutable record; not delivered',submit_calls=0,new_native_inputs=0,additional_live_generations=0)))
'''.replace('TASK',repr(task))
    result=dict(namespace=op.namespace,native_report_sha256=digest(raw),driver_sha256=digest(Path(__file__).read_bytes()),status='RUNNING')
    def save():(root/'report.json').write_bytes(canonical(result))
    save()
    try:result['observation']=json.loads(op.k('exec','-i','omega-agent-b-0','--',PYTHON,'-',data=source,timeout=60));result['status']='PASS';save()
    except BaseException as error:
        result.update(status='FAILED',failure=dict(type=type(error).__name__,detail=str(error)[-1000:]));save();raise
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('kubeconfig','context','namespace','native','directory'):p.add_argument('--'+name,required=True)
    a=p.parse_args();print(json.dumps(verify(Operator(a.kubeconfig,a.context,a.namespace),a.native,a.directory)))
if __name__=='__main__':main()
