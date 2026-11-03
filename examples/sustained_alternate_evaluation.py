"""Additional native counterexamples on the same retained Phase 3 services.

The finite script runs after the primary qualifier, without resetting state.
Commands are recorded proposals; returned handles, source events and truth are
captured from the actual native application. The scoring code is operator-only.
"""
import argparse,json,time
from pathlib import Path
from fusion.contracts import canonical,digest,require
from integration.single_node.reference_ops import Operator,PYTHON
from integration.single_node.sustained_qualification import Runner


def run(op,native,directory,continuation=None):
    raw=Path(native).read_bytes();prior=json.loads(raw)
    require(prior['status']=='PASS' and prior['namespace']==op.namespace,'NOT_AVAILABLE')
    r=Runner(op,directory);r.end=time.monotonic()+1200
    r.report.update(primary_native_report_sha256=digest(raw),maximum_operator_inputs=14,
        frozen=dict(profile='sustained-alternate-native-evaluation/1',maximum_inputs=14,maximum_wall_seconds=1200,
            fact='The synthetic copper lantern is stored in cupboard willow',query='synthetic copper lantern',
            proposals='RECORDED_COMMANDS_ONLY',independence='EXPLICIT_EXISTING_SYNTHETIC_OPERATOR_ASSUMPTION',live_allowance=0))
    r.save()
    try:
        if continuation:
            previous=Path(continuation).read_bytes();saved=json.loads(previous)
            require(saved['namespace']==op.namespace and len(saved['inputs'])==2 and all(x['observed']['state']=='complete' for x in saved['inputs']),'CONFLICT')
            r.report['prior_report_sha256']=digest(previous);r.report['inputs']=saved['inputs'];r.count=2
            r.ids['omega-agent']=[saved['inputs'][0]['session']];index=0
            written=r.object(saved['inputs'][0]['observed']['result']['projection'])
            page=r.object(saved['inputs'][1]['observed']['result']['projection'])
        else:
            index=r.allocate('omega-agent','alternate-evidence-withdrawal')
            written=r.object(r.run('remember '+r.report['frozen']['fact'],session=index))
            page=r.object(r.run('episodes current',session=index))
        memory=written['memory']['handle']
        events=[x['body']['source']['handle'] for x in page['events'] if x['kind']=='external-observation']
        for _ in range(3):
            if len(set(events))>=2 or not page.get('next_selector'):break
            page=r.object(r.run('episodes '+page['next_selector'],session=index))
            events.extend(x['body']['source']['handle'] for x in page['events'] if x['kind']=='external-observation')
        require(len(set(events))>=2,'NOT_AVAILABLE');source,other=events[0],events[1]
        before=r.current('omega-agent',index)
        support=r.run('support '+memory+' '+source,session=index)
        repeated=r.run('support '+memory+' '+source,session=index)
        contrary=r.run('contradict '+memory+' '+source,session=index)
        same=r.current('omega-agent',index)
        independent=r.run('support '+memory+' '+other,session=index)
        after=r.current('omega-agent',index)
        require('REVISION-SUCCESS' in support and 'retained-alternative' in contrary and 'REVISION-SUCCESS' in independent,'CONFLICT')
        priority=lambda observation: {k:observation['attention'][k] for k in ('revision','stored_values')}
        require(priority(before)==priority(same)==priority(after),'CONFLICT')
        belief=next(b for b in after['beliefs'] if len(b['observations'])>=2)
        require(any(s['kind']=='revision' and s['assumptions'] for s in belief['supports']),'CONFLICT')
        r.report['evidence_comparison']=dict(same_source=[support,repeated,contrary],explicit_independent_source=independent,
            snapshot=belief,priority_unchanged_by_belief=True,empirical_independence_claimed=False);r.save()
        captured=r.run('query '+r.report['frozen']['query'],session=index)
        captured_identity=r.report['inputs'][-1]['identity']
        require('cupboard willow' in captured,'CONFLICT')
        withdrawn=r.run('forget '+memory,session=index)
        current=r.run('query '+r.report['frozen']['query'],session=index)
        require('cupboard willow' not in current,'CONFLICT')
        observed=r.call('omega-agent','observe',r.ids['omega-agent'][index],'--content')
        old=next(x for x in observed['inputs'] if x['id']==captured_identity)
        require(old['result']['projection']==captured,'CONFLICT')
        r.report['withdrawal']=dict(result=withdrawn,current_query=current,old_capture_unchanged=True,physical_erasure=False)
        # Current disclosure checks differ from historical capture retention.
        member=next(x for x in before['lifecycle']['membership']['active'] if x['logical_id']==written['logical_id'])
        target={key:member[key] for key in ('uuid','payload','enrollment')}
        source='''import json
from pathlib import Path
from fusion.contracts import ContractError
from fusion.preview_memory_services import Client
from integration.single_node.sustained_runtime import materialize
app=json.loads(materialize(Path('/run/fusion/owner.json'),Path('/state'),Path('/run/fusion'),SID).read_bytes())
c=Client(app['active_memory_configs']['memory.lifecycle'],'memory.lifecycle')
head=c.call('head');target=TARGET
try:c.call('disclose',LOGICAL,target,head,False)
except ContractError as error:assert error.code in ('UNAUTHORIZED','NOT_AVAILABLE');denied=error.code
else:raise AssertionError('withdrawn payload authorized as current')
value=c.call('disclose',LOGICAL,target,OLD,True)
print(json.dumps(dict(current=denied,historical_authorized=value,physical_erasure=False)))
'''.replace('SID',repr(r.ids['omega-agent'][index])).replace('TARGET',repr(target)).replace('LOGICAL',repr(written['logical_id'])).replace('OLD',repr(before['lifecycle']['head']))
        # The UUID is authority data returned by the lifecycle membership, not
        # inferred from the opaque payload reference.
        r.report['withdrawal_authority']=json.loads(op.k('exec','-i','omega-agent-0','--',PYTHON,'-',data=source,timeout=35))
        foreign=next(x['value']['session'] for x in prior['allocations'] if x['role']=='omega-agent-b')
        try:r.call('omega-agent','observe',foreign,'--content')
        except RuntimeError as error:
            require('UNAUTHORIZED' in str(error) or 'NOT_FOUND' in str(error),'CONFLICT')
            r.report['wrong_agent_session_read']='DENIED'
        else:require(False,'CONFLICT')
        r.close('omega-agent',index);r.report['status']='PASS';r.save()
    except BaseException as error:
        r.report.update(status='FAILED',failure=dict(type=type(error).__name__,code=getattr(error,'code',None),detail=str(error)[-1000:]));r.save();raise
    return r.report

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('kubeconfig','context','namespace','native','directory'):p.add_argument('--'+name,required=True)
    p.add_argument('--continue-report')
    a=p.parse_args();print(json.dumps(run(Operator(a.kubeconfig,a.context,a.namespace),a.native,a.directory,a.continue_report)))
if __name__=='__main__':main()
