"""Replayable real execution hints and caller unsubscribe after native work.

Uses actual selected ports, not a worker database. No new logical execution,
native input, model call, supplied result, deadline or budget is created.
"""
import argparse,base64,json,secrets
from pathlib import Path
from fusion.contracts import canonical,digest,require
from integration.single_node.reference_ops import Operator,PYTHON
from integration.single_node.preview_qualification import Runner
from integration.single_node.preview_scope_qualification import Qualification

READ='''import json,sys
from pathlib import Path
from fusion.contracts import ContractError,canonical,digest,require
from fusion.preview_inspect import Client,ROUTE,PROFILE
from fusion.registry import selection_token
from fusion.preview_transport import invoke
from integration.single_node.sustained_runtime import materialize
q=json.load(sys.stdin)
path=materialize('/run/fusion/owner.json',Path('/state'),Path('/run/fusion'),q['session'])
cfg=json.loads(path.read_bytes());client=Client(cfg['inspect_config'])
try:
 if q.get('wrong'):
  config=dict(client.cfg['ports']['execution'],credential='wrong-notification-credential')
  body=dict(profile=PROFILE,selection=selection_token(client.selected['execution']),events=dict(job_id=q['job'],source=None,after=0,limit=3))
  invoke(config,ROUTE,body);raise AssertionError('wrong authority accepted')
 value=client.events(q['job'],q.get('source'),q.get('after',0),q.get('limit',3))
 print(json.dumps({'value':value}))
except ContractError as error:print(json.dumps({'error':error.code}))
'''


def qualify(op,directory,material,native_report):
    prior=json.loads(Path(native_report).read_bytes());require(prior['status']=='PASS' and prior['namespace']==op.namespace,'CONFLICT')
    q=Qualification(op,directory,material);q.report.update(synthetic_private_records=0,classification='REAL_EXECUTION_COMMIT_FEED_AND_NATIVE_CALLER_CONTINUATION',new_inputs=0)
    api=Runner.__new__(Runner);api.op=op
    item=next(x for x in prior['inputs'] if x['command'].startswith('inspect-atom '))
    sid=item['session'];occurrence=item['observed']['result']['occurrences'][0]
    job=Runner.object(item['observed']['result']['projection'])['job_id']
    other=next(x['session'] for x in prior['inputs'] if x['role']=='omega-agent-b')
    def read(role='omega-agent',session=sid,**args):
        return json.loads(op.k('exec','-i',role+'-0','--',PYTHON,'-c',READ,data=json.dumps(dict(session=session,job=job,**args)),timeout=30))
    def graph(*args):return api.call('omega-agent','continuation',sid,'--occurrence',occurrence,*args)
    try:
        op.owned();before=graph();require(before['status']=='return-ready' and before['cursor'] is not None,'CONFLICT')
        first=q.case('bounded-first-page',read(limit=1));require(len(first['events'])==1 and first['head']==3,'CONFLICT')
        second=q.case('lost-hint-catchup',read(source=first['source'],after=first['next'],limit=2))
        require([x['kind'] for x in first['events']+second['events']]==['accepted','result-committed','completion-delivered'],'CONFLICT')
        require(q.case('duplicate-page',read(source=first['source'],after=first['next'],limit=2))==second,'CONFLICT')
        q.case('wrong-token',read(wrong=True),'UNAUTHORIZED')
        q.case('wrong-owner-no-count',read('omega-agent-b',other),'NOT_FOUND')
        for name,args in [('foreign-source',dict(source='foreign-source')),('future-cursor',dict(source=first['source'],after=4))]:
            value=q.case(name,read(**args));require(value['gap'] and value['events']==[],'CONFLICT')
        q.report['caller_replacement']=q.replace('omega-agent')
        require(graph()==before,'CONFLICT')
        require(q.case('restarted-cursor-catchup',read(source=first['source'],after=first['next'],limit=2))==second,'CONFLICT')
        # Revoke only this task namespace's execution credential. Existing
        # pooled/captured metadata cannot grant access after the owner reloads.
        owner=q.secret('fusion-execution');caller=q.secret('omega-agent')
        token=base64.b64encode(secrets.token_hex(32).encode()).decode()
        owner['data']['inspect-caller-A-token']=token;q.put_secret(owner)
        q.report['execution_rotation']=q.replace('fusion-execution')
        q.case('revoked-event-metadata',read(),'UNAUTHORIZED')
        caller['data']['inspect-fusion-execution-token']=token;q.put_secret(caller)
        q.report['caller_rotation']=q.replace('omega-agent')
        require(q.case('same-principal-new-credential',read(source=first['source'],after=first['next'],limit=2))==second,'CONFLICT')
        changed=graph('--continuation-action','unsubscribe','--identity','integrated-stop-hints')
        require(not changed['subscription'] and changed['cursor']==before['cursor'] and changed['steps']==before['steps'] and
            changed['relay_calls_spent']==before['relay_calls_spent'] and changed['deadline_ms']==before['deadline_ms'],'CONFLICT')
        require(graph('--continuation-action','unsubscribe','--identity','integrated-stop-hints')==changed,'CONFLICT')
        q.report['unsubscribe_replacement']=q.replace('omega-agent');require(graph()==changed,'CONFLICT')
        observed=api.call('omega-agent','observe',sid,'--content')
        require(next(x for x in observed['inputs'] if x['id']==item['identity'])==item['observed'],'CONFLICT')
        q.report.update(status='PASS',native_result_unchanged=True,cursor_unchanged_after_unsubscribe=True,
            caught_up_events=3,pages=2,late_result='AUTHORITATIVE_CAPTURE_READ_AFTER_ORIGINAL_DEADLINE_NOT_NEW_EXECUTION',
            deadline_ms=before['deadline_ms'],relay_calls_spent=before['relay_calls_spent'],effect_reexecution=0,metadata_revocation='PASS')
    except BaseException as error:
        q.report.update(status='FAIL',failure=dict(type=type(error).__name__,code=getattr(error,'code',None),detail=str(error)[-1200:]));raise
    finally:op.quiesce();q.report['quiesced']=True;q.save()
    return q.report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('kubeconfig','context','namespace','directory','material','native-report'):p.add_argument('--'+name,required=True)
    a=p.parse_args();v=qualify(Operator(a.kubeconfig,a.context,a.namespace),a.directory,a.material,a.native_report)
    print(json.dumps(dict(status=v['status'],additional_live_generations=0)))
