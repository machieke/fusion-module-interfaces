"""Real native enrollment while a bounded old-view Search repair is reserved.

Only test barriers and one disposable index are operator controlled. The
native caller creates payloads/vectors/enrollment and publishes its later view.
No answer, new deadline, substitute source or provider result is injected.
"""
import argparse,json,time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import yaml
from fusion.contracts import canonical,require,digest
from integration.single_node.reference_ops import Operator,PYTHON
from integration.single_node.sustained_qualification import Runner
from integration.single_node.preview_recovery_qualification import Recovery
from .integrated_sustained import IntegratedRunner

REMOVE='''import json,sys,shutil
from pathlib import Path
from fusion.contracts import require,digest
from fusion.preview_vector_contracts import snapshot
q=json.load(sys.stdin);snapshot(q,q['head']['scope_ref'])
root=Path('/state/memory/active-search');directory=root/q['generation'];index=directory/'index'
require(not root.is_symlink() and not directory.is_symlink() and not index.is_symlink(),'UNAUTHORIZED')
require(json.loads((directory/'manifest.json').read_bytes())['snapshot']==q,'CONFLICT')
before=digest((root/'published.json').read_bytes());manifest=digest((directory/'manifest.json').read_bytes())
removed=index.is_dir()
if removed:shutil.rmtree(index)
else:require(not index.exists(),'CONFLICT')
require(digest((root/'published.json').read_bytes())==before and digest((directory/'manifest.json').read_bytes())==manifest,'CONFLICT')
print(json.dumps({'removed':'one derived index' if removed else 'already missing derived index; no repeated deletion','generation':q['generation'],'publication_sha256':before,'authoritative_records_changed':False}))
'''

def qualify(op,values,chart,directory,native_report,resume_setup=None):
    prior=json.loads(Path(native_report).read_bytes());require(prior['status']=='PASS' and prior['namespace']==op.namespace,'CONFLICT')
    root=Path(directory);root.mkdir(parents=True,exist_ok=False)
    r=IntegratedRunner(op,root/'native',maximum_inputs=4,legacy_crossing_required=False);r.end=time.monotonic()+600
    fault=Recovery.__new__(Recovery);fault.op=op;fault.values_path=root/'fault-values.yaml'
    fault.values=yaml.safe_load(Path(values).read_bytes());fault.chart=chart;fault.api=r
    first=prior.get('first_memory')
    if first is None:
        entry=next(x for x in prior['inputs'] if x['command'].startswith('remember '))
        first=r.object(entry['observed']['result']['projection'])
    old=first['snapshot'];scope=old['head']['scope_ref']
    original_query=prior.get('frozen',{}).get('query','synthetic silver prism storage')
    original_answers=prior.get('frozen',{}).get('answers_for_evaluator_only',['crate saffron'])
    report=dict(status='RUNNING',maximum_operator_inputs=4,maximum_seconds=600,namespace=op.namespace,
        additional_live_generations=0,old_snapshot=old,native_report_sha256=digest(Path(native_report).read_bytes()))
    def save():(root/'report.json').write_bytes(canonical(report))
    def wait(fn,until):
        while time.monotonic()<min(r.end,until):
            result=fn()
            if result:return result
            time.sleep(.2)
        require(False,'NOT_AVAILABLE')
    def maintain(operation,*args):
        code='import json,sys;from integration.single_node.integrated_search_operator import request;print(json.dumps(request(json.load(sys.stdin))))'
        return json.loads(op.k('exec','-i','fusion-search-0','--',PYTHON,'-c',code,
            data=json.dumps(dict(scope=scope,operation=operation,args=list(args))),timeout=130))
    save()
    try:
        op.owned();images={x['metadata']['name']:x['spec']['template']['spec']['containers'][0]['image'] for x in op.workloads()};report['images']=images
        # The old generation must actually be older than the current ready
        # view. A one-memory comparison corpus has only one generation.
        if resume_setup:
            previous=Path(resume_setup);raw=(previous/'report.json').read_bytes();saved=json.loads(raw)
            native=json.loads((previous/'native/report.json').read_bytes())
            require(saved['status']=='FAIL' and saved['namespace']==op.namespace and saved['old_snapshot']==old and
                    'newer_ready_view' in saved and 'repair_intent' not in saved and len(native['inputs'])==1,'CONFLICT')
            entry=native['inputs'][0];require(entry['observed']['state']=='complete','CONFLICT')
            sid=entry['session'];observed=r.call('omega-agent','observe',sid,'--content')
            require(next(x for x in observed['inputs'] if x['id']==entry['identity'])==entry['observed'],'CONFLICT')
            r.ids={'omega-agent':[sid]};seed=0;r.count=1
            r.report.update(inputs=native['inputs'],allocations=native['allocations'])
            report.update(newer_ready_view=saved['newer_ready_view'],resumed_setup_sha256=digest(raw),
                          completed_seed_not_reexecuted=True);r.save()
        else:
            seed=r.allocate('omega-agent','integrated-ready-before-old-repair')
            report['newer_ready_view']=r.object(r.run('remember The synthetic blue token is in tray cedar','omega-agent',seed))
        require(report['newer_ready_view']['snapshot']['generation']!=old['generation'],'CONFLICT');save()
        op.k('scale','statefulset','fusion-search','--replicas=0')
        op.k('wait','--for=delete','pod/fusion-search-0','--timeout=90s',timeout=100)
        helper=op.helper('fusion-search',images['fusion-search'],'state-fusion-search-0')
        try:report['index_loss']=json.loads(op.k('exec','-i',helper,'--',PYTHON,'-c',REMOVE,data=json.dumps(old)));save()
        finally:
            op.k('delete','pod',helper,'--wait=true',timeout=30);op.k('scale','statefulset','fusion-search','--replicas=1')
        op.k('wait','--for=condition=Ready','pod/fusion-search-0','--timeout=120s',timeout=130)
        # The native input first selects its retained view through Search.
        # Pause only after that read and command admission, before enrollment.
        fault.arm('omega-agent','pause_at','after_memory_vector_capture')
        fault.arm('fusion-search','pause_at','after_search_repair_reservation')
        index=seed;sid=r.ids['omega-agent'][index]
        plan=maintain('planRepair',old);require(plan['plan']['classification']=='MISSING_DERIVED_INDEX','CONFLICT');report['plan']=plan;save()
        with ThreadPoolExecutor(max_workers=2) as pool:
            deadline=time.time_ns()//1000000+120000;identity='concurrent-old-generation-repair'
            report['repair_intent']=dict(identity=identity,deadline_ms=deadline);save()
            native=pool.submit(r.run,'remember The synthetic copper key is in drawer juniper','omega-agent',index)
            marker=wait(lambda:fault.read('omega-agent','pause.json'),time.monotonic()+50)
            require(marker['stage']=='after_memory_vector_capture','CONFLICT');report['native_pause']=marker;save()
            repair=pool.submit(maintain,'repair',plan,identity,deadline)
            report['search_pause']=wait(lambda:fault.read('fusion-search','pause.json'),time.monotonic()+20);save()
            code='import os,signal,json;from pathlib import Path;p=json.loads(Path("/state/pause.json").read_bytes());assert p["stage"]=="after_memory_vector_capture";os.kill(p["pid"],signal.SIGCONT)'
            op.k('exec','omega-agent-0','--',PYTHON,'-c',code)
            code='''import json,sqlite3,sys
from pathlib import Path
p=Path('/state/sessions')/sys.argv[1]/'caller.sqlite'
with sqlite3.connect(p.as_uri()+'?mode=ro',uri=True) as db:
 row=db.execute('SELECT through_head FROM app_memory_writes ORDER BY rowid DESC LIMIT 1').fetchone()
 print(row[0] if row and row[0] else 'null')
'''
            def enrollment():return json.loads(op.k('exec','omega-agent-0','--',PYTHON,'-c',code,sid))
            head=wait(enrollment,time.monotonic()+25);require(head['sequence']>old['head']['sequence'] and head['source']==old['head']['source'],'CONFLICT')
            require(not repair.done(),'CONFLICT');report['enrollment_during_reserved_rebuild']=head;save()
            release='from pathlib import Path;Path("/state/search-repair-test-release.json").write_text(\'{"stage":"after_search_repair_reservation"}\')'
            op.k('exec','fusion-search-0','--',PYTHON,'-c',release)
            report['repair']=repair.result();save()
            # Publication waits on the existing bounded projection lock. New
            # enrollment is already committed; no caller deadline is renewed.
            report['remember']=r.object(native.result());save()
        require(report['repair']['state']=='verified' and report['repair']['result']['snapshot']==old,'CONFLICT')
        require(report['remember']['snapshot']['head']==head and report['remember']['snapshot']['generation']!=old['generation'],'CONFLICT')
        require(maintain('observeRepair',plan,identity)==report['repair'],'CONFLICT')
        r.evaluate(r.run('query synthetic copper key','omega-agent',index),dict(required=['drawer juniper']))
        r.evaluate(r.run('query '+original_query,'omega-agent',index),dict(required=original_answers))
        original=prior['inputs'][0];observed=r.call(original['role'],'observe',original['session'],'--content')
        require(next(x for x in observed['inputs'] if x['id']==original['identity'])==original['observed'],'CONFLICT')
        report.update(status='PASS',operator_native_inputs=4,retained_original_capture=True,
            publication_order='old fixed head repaired; later native enrollment publishes later exact head',
            catch_up='separate bounded generation replay; no incremental-math change',deadline_renewals=0)
        r.report['status']='PASS'
    except BaseException as error:
        report.update(status='FAIL',failure=dict(type=type(error).__name__,code=getattr(error,'code',None),detail=str(error)[-1400:]));raise
    finally:r.save();op.quiesce();report['quiesced']=True;save()
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('kubeconfig','context','namespace','values','chart','directory','native-report'):p.add_argument('--'+name,required=True)
    p.add_argument('--resume-setup-report')
    a=p.parse_args();value=qualify(Operator(a.kubeconfig,a.context,a.namespace),a.values,a.chart,a.directory,a.native_report,a.resume_setup_report)
    print(json.dumps(dict(status=value['status'],additional_live_generations=0)))
