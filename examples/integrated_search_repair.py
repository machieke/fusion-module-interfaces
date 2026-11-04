"""Native memory -> owner archive -> retained derived-index loss and repair.

Only the disposable Search projection is removed, while its owner is stopped.
The fault helper never edits authority, captures, receipts or checkpoints. The
supported maintenance port rebuilds from declared storage/lifecycle ports.
"""
import argparse,json,time,uuid
from pathlib import Path
from fusion.contracts import canonical,digest,require
from integration.single_node.reference_ops import Operator,PYTHON
from integration.single_node.sustained_qualification import Runner
from .integrated_archive import ARCHIVE

WORKLOAD=dict(profile='integrated-native-retained-search-repair/1',maximum_native_operator_inputs=7,
    fact='The synthetic amber compass is stored in chest willow',query='synthetic amber compass storage',
    new_fact='The synthetic cobalt token is stored in drawer birch',
    fault='quiesced removal of one derived Chroma index only',repair='bounded-derived-search-repair/1',
    model='RECORDED_PROPOSALS',additional_live_generations=0)


def qualify(op,directory):
    root=Path(directory);root.mkdir(parents=True,exist_ok=False);(root/'workload.json').write_bytes(canonical(WORKLOAD))
    r=Runner(op,root/'native');r.end=time.monotonic()+1200;r.report.update(maximum_operator_inputs=7,frozen=WORKLOAD)
    report=dict(status='RUNNING',additional_live_generations=0,providers='REAL_NATIVE_E5_CHROMA_DETTA_POD_HTTPS',
        model='RECORDED_PROPOSALS',workload_sha256=digest(canonical(WORKLOAD)))
    def save():(root/'report.json').write_bytes(canonical(report))
    def maintain(operation,*args):
        body=dict(scope=scope,operation=operation,args=list(args))
        code='import json,sys;from integration.single_node.integrated_search_operator import request;print(json.dumps(request(json.load(sys.stdin))))'
        return json.loads(op.k('exec','-i','fusion-search-0','--',PYTHON,'-c',code,data=json.dumps(body),timeout=130))
    def ready(snapshot):
        code='''import json,sys
from pathlib import Path
from fusion.preview_memory_services import Client
from fusion.contracts import ContractError
q=json.load(sys.stdin);app=json.loads((Path('/run/fusion/sessions')/q['session']/'application.json').read_bytes())
try:result=Client(app['active_memory_configs']['search'],'search').call('ready',q['snapshot'])
except ContractError as error:result={'error':error.code}
print(json.dumps(result))'''
        return json.loads(op.k('exec','-i','omega-agent-0','--',PYTHON,'-c',code,data=json.dumps(dict(session=sid,snapshot=snapshot))))
    save()
    try:
        op.owned();workloads=op.workloads();report['images']={x['metadata']['name']:x['spec']['template']['spec']['containers'][0]['image'] for x in workloads};save()
        index=r.allocate('omega-agent','retained-repair-A');sid=r.ids['omega-agent'][index]
        first=r.object(r.run('remember '+WORKLOAD['fact'],session=index));report['first']=first
        scope=first['source']['scope_ref'];old=first['snapshot'];save()
        r.evaluate(r.run('query '+WORKLOAD['query'],session=index),dict(required=['chest willow']))
        query_entry=r.report['inputs'][-1];retained=r.current('omega-agent',index);report['retained_before']=retained;save()
        archive=json.loads(op.k('exec','-i','fusion-storage-0','--',PYTHON,'-c',ARCHIVE,data=json.dumps(dict(scope=scope,
            payload=first['memory']['target']['payload'],through=first['source'])),timeout=70))
        refs=[x['ref'] for x in archive['plan']['records']]
        require(all(first['memory']['target'][x] in refs for x in ('payload','enrollment')),'NOT_AVAILABLE')
        report['archive']=archive;save()
        recent=r.object(r.run('remember '+WORKLOAD['new_fact'],session=index));report['recent']=recent;save()
        r.evaluate(r.run('query '+WORKLOAD['query'],session=index),dict(required=['chest willow']))
        current=r.current('omega-agent',index)['search'];require(current['generation']!=old['generation'],'CONFLICT')
        report['current_before_fault']=current;save()
        # One owner only, stopped before the diagnostic helper mounts its PVC.
        op.k('scale','statefulset','fusion-search','--replicas=0')
        op.k('wait','--for=delete','pod/fusion-search-0','--timeout=90s',timeout=100)
        helper=op.helper('fusion-search',report['images']['fusion-search'],'state-fusion-search-0')
        try:
            code='''import json,sys,shutil
from pathlib import Path
from fusion.contracts import require,digest
from fusion.preview_vector_contracts import snapshot
q=json.load(sys.stdin);snapshot(q,q['head']['scope_ref'])
root=Path('/state/memory/active-search');directory=root/q['generation'];index=directory/'index'
require(not root.is_symlink() and not directory.is_symlink() and not index.is_symlink(),'UNAUTHORIZED')
require(json.loads((directory/'manifest.json').read_bytes())['snapshot']==q,'CONFLICT')
before=digest((root/'published.json').read_bytes());manifest=digest((directory/'manifest.json').read_bytes())
require(index.is_dir(),'NOT_AVAILABLE');shutil.rmtree(index)
require(digest((root/'published.json').read_bytes())==before and digest((directory/'manifest.json').read_bytes())==manifest,'CONFLICT')
print(json.dumps({'removed':'one derived index','generation':q['generation'],'publication_sha256':before,'manifest_sha256':manifest,'authoritative_records_changed':False}))'''
            report['fault']=json.loads(op.k('exec','-i',helper,'--',PYTHON,'-c',code,data=json.dumps(old)));save()
        finally:
            op.k('delete','pod',helper,'--wait=true',timeout=30)
            op.k('scale','statefulset','fusion-search','--replicas=1')
        op.k('wait','--for=condition=Ready','pod/fusion-search-0','--timeout=120s',timeout=130)
        require(ready(old)=={'error':'NOT_AVAILABLE'},'CONFLICT');report['missing_not_empty']=True
        plan=maintain('planRepair',old);require(plan['plan']['classification']=='MISSING_DERIVED_INDEX','CONFLICT');report['plan']=plan;save()
        identity='native-old-view-repair';deadline=time.time_ns()//1000000+120000
        report['repair_intent']=dict(identity=identity,deadline_ms=deadline);save()
        result=maintain('repair',plan,identity,deadline);report['repair']=result;save()
        require(result['state']=='verified' and result['result']['snapshot']==old,'NOT_AVAILABLE')
        require(maintain('observeRepair',plan,identity)==result,'CONFLICT')
        require(ready(old)=={'ready':True},'NOT_AVAILABLE')
        after=r.current('omega-agent',index);require(after['search']==current,'CONFLICT')
        report['retained_after']=after;save()
        observed=r.call('omega-agent','observe',sid,'--content')
        captured=next(x for x in observed['inputs'] if x['id']==query_entry['identity'])
        require(captured==query_entry['observed'],'CONFLICT')
        r.evaluate(r.run('query '+WORKLOAD['query'],session=index),dict(required=['chest willow']))
        r.run('episodes current',session=index)
        # Separately selected portable NAL wrapper, same actual native session.
        from tests.neoclaw_support import COMMAND,GOLDEN
        nal=r.run(COMMAND,session=index);require(GOLDEN in nal,'NOT_AVAILABLE');report['portable_nal_projection']=nal
        report.update(status='PASS',operator_native_inputs=r.count,retained_query_exact=True,older_repair_did_not_regress_current=True,
            archive_payload_and_enrollment_replayed=True,original_repair_deadline_ms=deadline,repair_reservations=result['attempts_spent'])
        r.report['status']='PASS'
    except BaseException as error:report.update(status='FAIL',failure=dict(type=type(error).__name__,code=getattr(error,'code',None)));raise
    finally:r.save();op.quiesce();report['quiesced']=True;save()
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('kubeconfig','context','namespace','directory'):p.add_argument('--'+name,required=True)
    a=p.parse_args();r=qualify(Operator(a.kubeconfig,a.context,a.namespace),a.directory);print(json.dumps(dict(status=r['status'],additional_live_generations=0)))
