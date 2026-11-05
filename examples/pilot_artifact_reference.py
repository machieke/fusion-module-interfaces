"""Explicit operator amendment to a bounded manifest of an actual task result.

The historical full-projection recipe is unchanged. This opt-in representation
uses only existing write-file/inspect tools and the same workflow effect budget.
No expected answer, excerpt, replacement capture or new execution profile.
"""
import json,time
from fusion.contracts import canonical,digest,require,validate_ref
from integration.single_node.reference_ops import PYTHON

PROFILE='captured-task-result-reference-document/1'

def returned_object(result,command):
    """Read the one actual native return, excluding JSON echoed as arguments."""
    require(type(result) is dict and type(result.get('projection')) is str and type(command) is str,'NOT_AVAILABLE')
    prefix='(RESULTS: ((COMMAND_RETURN: (('+command.replace('"','_quote_')+') '
    raw=result['projection'];require(raw.startswith(prefix),'CONFLICT')
    raw=raw[len(prefix):].replace('_quote_','"')
    try:value,end=json.JSONDecoder().raw_decode(raw)
    except (ValueError,TypeError):require(False,'NOT_AVAILABLE')
    require(type(value) is dict and raw[end:]=='))))','CONFLICT')
    return value

def document(source):
    task,result,ref=source['task'],source['result'],source['result_ref']
    from fusion.preview_tasks import record,correlated
    record(task,task['scope']);record(result,task['scope']);validate_ref(ref,task['scope'])
    correlated(result,task,source['task_ref'])
    require(result['status']=='captured-native-query','NOT_AVAILABLE')
    raw=result['projection'].encode()
    return dict(profile=PROFILE,task=task['id'],task_ref=source['task_ref'],result_ref=ref,
        projection_bytes=len(raw),projection_sha256=digest(raw),
        interpretation='reference-to-full-captured-result-not-answer-or-independent-observation')

def text(source):
    value=canonical(document(source)).decode();require(len(('write-file review.txt '+value).encode())<=4096,'OVERLOADED')
    return value

def retrieved_setup(setup,source):
    """Post-capture evaluator only; never a query argument or provider answer."""
    document(source);require(setup.get('status')=='REMEMBER-SUCCESS','NOT_AVAILABLE')
    expected=setup['memory']['target']['payload'];validate_ref(expected,source['task']['scope'])
    require(expected in source['result']['payloads'],'CONFLICT')
    return dict(remembered_payload=expected,captured_result_ref=source['result_ref'],
        captured_payload_count=len(source['result']['payloads']),remembered_payload_retrieved=True,
        evaluation_after_capture=True,expected_reference_supplied_to_consumer=False)

def verify(workspace,readback,source,inspection):
    expected=text(source);require(readback['path']==workspace['path']=='review.txt' and
        readback['revision']==workspace['revision'] and workspace['outcome']=='committed','CONFLICT')
    require(readback['text']==expected and workspace['digest']==readback['digest']==digest(expected.encode())
        and workspace['bytes']==len(expected.encode()),'CONFLICT')
    expected_artifact=artifact(source,source['observations'])
    require(inspection==expected_artifact,'CONFLICT')
    return dict(representation=PROFILE,workspace_contains_full_projection=False,
        full_projection_retained=True,reference_document=document(source),
        workspace_digest=workspace['digest'],inspected_artifact_result_ref=inspection['result_ref'],
        inspection_boundary='SYNTHETIC_RETRIEVAL_ARTIFACT_ENVELOPE',
        inspected_envelope_bytes=len(canonical(inspection)),inspected_envelope_sha256=digest(canonical(inspection)),
        full_projection_inspected=False,exact_full_result_link=True,projection_truncated=False)

CAPTURE='''import json,sys,time
from pathlib import Path
from fusion.contracts import require
from fusion.ports import Mutation
from fusion.preview_atoms import client
from fusion.preview_native_history import read_body
from fusion.preview_tasks import record,correlated
from integration.single_node.sustained_current import observe
q=json.load(sys.stdin);current=observe(q['recipient_session'])
app=json.loads((Path('/run/fusion/sessions')/q['recipient_session']/'application.json').read_bytes())
require(app['preview']['scope']==q['scope'] and current['scope']==q['scope'],'UNAUTHORIZED')
a=client(json.loads(Path(app['memory_atoms_config']).read_bytes()),q['deadline'])
observed=a.observe(Mutation(q['scope'],'result/'+q['task']))
require(observed['found'],'NOT_AVAILABLE');ref=observed['write']['ref']
result=record(read_body(a,ref)['body'],q['scope']);task=record(read_body(a,q['task_ref'])['body'],q['scope'])
correlated(result,task,q['task_ref']);require(result['id']==q['task'] and result['recipient']=='A' and result['sender']=='B','UNAUTHORIZED')
print(json.dumps(dict(task=task,result=result,task_ref=q['task_ref'],result_ref=ref,observation=observed)))
'''

def capture(r,session,publication,deadline):
    require(publication['status']=='TASK_PUBLISHED' and time.time_ns()//1000000<deadline,'NOT_AVAILABLE')
    found=[]
    for row in r.call('omega-agent-b','list'):
        observed=r.call('omega-agent-b','observe',row['session'],'--content')
        if observed['allocation']['allocation_id']=='incoming/A/'+session:found.append(observed)
    require(len(found)==1 and len(found[0]['inputs'])==1 and found[0]['inputs'][0]['state']=='complete','NOT_AVAILABLE')
    q=dict(recipient_session=found[0]['session'],scope=publication['ref']['scope_ref'],task=publication['task'],task_ref=publication['ref'],deadline=deadline)
    value=json.loads(r.op.k('exec','-i','omega-agent-b-0','--',PYTHON,'-c',CAPTURE,data=json.dumps(q),timeout=40))
    # The caller result and remote body remain separate exact receipts.
    value['recipient_capture']=found[0];document(value);return value


def artifact(source,observations):
    """Validate the existing inspection domain without creating an artifact."""
    from fusion import preview_artifact_contracts as contract
    document(source);task,result=source['task'],source['result']
    require(len(result['payloads'])<=contract.MAX_OBSERVATIONS,'OVERLOADED')
    require(type(observations) is list and [x['payload_ref'] for x in observations]==result['payloads'],'CONFLICT')
    return contract.record(dict(profile=contract.PROFILE,scope=task['scope'],task=task['id'],
        query=task['query'],sender=task['sender'],reporter=result['sender'],result_ref=source['result_ref'],
        view=result['view'],observations=observations),task['scope'])

HYDRATE='''import json,sys
from pathlib import Path
from fusion.contracts import canonical,require
from fusion.preview_atoms import client
from fusion import vector_contracts as vector
q=json.load(sys.stdin);app=json.loads((Path('/run/fusion/sessions')/q['session']/'application.json').read_bytes())
require(app['preview']['scope']==q['scope'],'UNAUTHORIZED')
a=client(json.loads(Path(app['memory_atoms_config']).read_bytes()),q['deadline']);observations=[]
for ref in q['payloads']:
 item=a.get(ref);require(item.content_type==vector.PAYLOAD,'NOT_AVAILABLE')
 value=vector.payload(json.loads(item.bytes),q['scope'],q['corpus']);require(canonical(value)==item.bytes,'CONFLICT')
 observations.append(dict(payload_ref=ref,content=value['content']))
print(json.dumps(observations))
'''

def inspection_preflight(op,session,source,deadline):
    """Declared AtomStorage reads only; no writes, provider submits or captures."""
    from fusion.preview_artifact_contracts import MAX_OBSERVATIONS
    document(source);require(len(source['result']['payloads'])<=MAX_OBSERVATIONS,'OVERLOADED')
    require(time.time_ns()//1000000<deadline,'NOT_AVAILABLE')
    q=dict(session=session,scope=source['task']['scope'],payloads=source['result']['payloads'],
           corpus=source['result']['view']['corpus'],deadline=deadline)
    observed=json.loads(op.k('exec','-i','omega-agent-0','--',PYTHON,'-c',HYDRATE,data=json.dumps(q),timeout=40))
    value=artifact(source,observed)
    return dict(source,observations=observed,inspection_preflight=value)

def suffix(source,plan):
    """Explicit operator amendment, with a new checkpoint before any write."""
    require(len(plan)==3 and plan[1]['node']=='artifact' and plan[2]['node']=='inspect','CONFLICT')
    artifact(source,source['observations'])
    return [dict(node='artifact',tool='write-file',arguments=['review.txt',text(source)],guards=[],checkpoint=True),plan[2]]
