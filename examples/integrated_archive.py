"""Equal fourteen-input native workload followed by explicit owner archival.

The operator tiers captured synthetic references; it never supplies a reference
or answer to the native query. Native results precede maintenance selection.
"""
import argparse,json,time,threading
from pathlib import Path
from fusion.contracts import require,canonical,digest
from integration.single_node.reference_ops import Operator,PYTHON
from .integrated_baseline import qualify,WORKLOAD
from integration.single_node.sustained_qualification import Runner


ARCHIVE='''import json,sys,time
from pathlib import Path
from fusion.preview_client import AtomFeedClient,Endpoint
from fusion.registry import descriptor_read
from fusion.ports import Mutation
from fusion.contracts import require
from fusion.archive_contracts import PROFILE
q=json.load(sys.stdin)
cfg=json.loads(Path('/run/fusion/cognitive-owner.json').read_bytes())
component=json.loads(Path('/config/component.json').read_bytes())
d=next(descriptor_read(x) for x in cfg['catalogue'] if PROFILE in x['profiles'])
client=AtomFeedClient(Endpoint(component['peers']['fusion-storage'],component['https_port'],'/secrets/ca.crt'),
 cfg['principals']['archive-operator']['credential'],'archive-operator',q['scope'],d,
 deadline_ms=time.time_ns()//1000000+60000,composition=cfg['composition'],feed_profile=cfg['feed_profile'])
head=client.head(q['scope']);through=q['through'];require(through['source']==head['source'],'CONFLICT')
after=0;target=None;pages=0
while after<through['sequence']:
 require(pages<256,'OVERLOADED');page=client.readCommits(q['scope'],after,through,8);pages+=1
 for row in page['records']:
  if row['ref']==q['payload']:target=row['sequence']
 after=page['next_after']
 if target is not None:break
require(target is not None,'NOT_FOUND')
after=max(0,target-8);command=Mutation(q['scope'],'archive-native-first-memory')
plan=client.planArchive(q['scope'],after,through,16)
require(q['payload'] in [x['ref'] for x in plan['records']],'CONFLICT')
sealed=client.publishArchive(command,after,through,16)
require(client.publishArchive(command,after,through,16)==sealed,'CONFLICT')
observed=client.observeArchive(command);require(observed['archive']==sealed,'CONFLICT')
item=client.get(q['payload']);require(item.ref==q['payload'],'CONFLICT')
require(client.head(q['scope'])==head,'CONFLICT')
print(json.dumps({'plan':plan,'sealed':sealed,'observation':observed,'source_head_unchanged':True,
 'source_pages':pages,'hydrated_payload':item.ref,'hydrated_bytes':len(item.bytes),'hot_deletion':False}))
'''


def maintenance(runner):
    first=runner.report['inputs'][0];memory=runner.object(first['observed']['result']['projection'])
    payload=memory['memory']['target']['payload'];scope=payload['scope_ref'];sid=first['session']
    request=dict(scope=scope,payload=payload,through=memory['source'])
    result=json.loads(runner.op.k('exec','-i','fusion-storage-0','--',PYTHON,'-c',ARCHIVE,data=json.dumps(request),timeout=70))
    runner.report['archive_maintenance']=result;runner.save()
    # Existing accepted occurrences retain their original view/results. These
    # are new intentional inputs on the same native session/configuration.
    index=runner.ids['omega-agent'].index(sid)
    query=runner.run('query '+WORKLOAD['query'],session=index)
    runner.evaluate(query,dict(required=WORKLOAD['answers_for_evaluator_only']))
    history=runner.run('episodes current',session=index)
    old=runner.call('omega-agent','observe',sid,'--content')
    retained=next(x for x in old['inputs'] if x['id']==first['identity'])
    require(retained==first['observed'],'CONFLICT')
    result.update(native_query_after_archive='PASS',native_history_after_archive='PASS',retained_first_result_exact=True,
                  extra_native_inputs=2,config_edits=0,query_given_answer_refs=False)
    return result


def resume_maintenance(op,directory,previous):
    """Observe the completed baseline, then admit only two new native reads.

    This is not a benchmark rerun or renewal of prior input deadlines. The
    failed baseline report stays immutable. Archive writes use the same named
    maintenance Mutation even if its previous response was lost.
    """
    old=Path(previous);raw=(old/'native/report.json').read_bytes();prior=json.loads(raw)
    require(prior['namespace']==op.namespace and len(prior['inputs'])==14,'CONFLICT')
    require(all(x.get('observed',{}).get('state')=='complete' for x in prior['inputs']),'CONFLICT')
    root=Path(directory);root.mkdir(parents=True,exist_ok=False)
    r=object.__new__(Runner);r.op=op;r.root=root;r.lock=threading.RLock()
    r.end=time.monotonic()+600;r.count=14;r.ids={};r.report=prior
    for row in prior['allocations']:r.ids.setdefault(row['role'],[]).append(row['value']['session'])
    r.report.update(status='RUNNING',resumed_from_sha256=digest(raw),original_operator_inputs=14,
        maximum_operator_inputs=16,original_deadlines_renewed=False)
    r.save()
    try:
        op.owned()
        for row in prior['inputs']:
            observation=r.call(row['role'],'observe',row['session'],'--content')
            actual=next(x for x in observation['inputs'] if x['id']==row['identity'])
            require(actual==row['observed'],'CONFLICT')
        r.report['archive_maintenance']=maintenance(r);r.report['status']='PASS'
    except BaseException as error:
        r.report.update(status='FAIL',maintenance_failure=dict(type=type(error).__name__,code=getattr(error,'code',None)));raise
    finally:
        op.quiesce();r.report['quiesced']=True;r.save()
    return r.report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('kubeconfig','context','namespace','directory'):p.add_argument('--'+name,required=True)
    p.add_argument('--resume-maintenance-from')
    a=p.parse_args();op=Operator(a.kubeconfig,a.context,a.namespace)
    result=resume_maintenance(op,a.directory,a.resume_maintenance_from) if a.resume_maintenance_from else qualify(op,a.directory,
        'dev03 compact immutable captures and owner archive; first14 comparable',maintenance)
    print(json.dumps(dict(status=result['status'],additional_live_generations=0)))
