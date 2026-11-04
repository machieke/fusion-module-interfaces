"""One explicit new maintenance action after an expired derived-repair test.

The failed repair and native input remain unchanged. No application input or
model call is created. The existing Search port rebuilds the exact missing old
generation from native-created authoritative hot/archive records. The operator
observes its own Search publication bytes; a consumer never reads a provider DB.
"""
import argparse,json,time
from pathlib import Path
from fusion.contracts import canonical,digest,require
from integration.single_node.reference_ops import Operator,PYTHON
from integration.single_node.preview_qualification import Runner


def qualify(op,directory,native_report,failed_report,identity):
    prior=json.loads(Path(native_report).read_bytes())
    failure=json.loads(Path(failed_report).read_bytes())
    require(prior['status']=='PASS' and prior['namespace']==op.namespace and
            failure['status']=='FAIL' and failure['namespace']==op.namespace,'CONFLICT')
    old=failure['old_snapshot'];scope=old['head']['scope_ref'];old_intent=failure['repair_intent']
    require(time.time_ns()//1000000>old_intent['deadline_ms'] and identity!=old_intent['identity'],'CONFLICT')
    root=Path(directory);root.mkdir(parents=True,exist_ok=False)
    api=Runner.__new__(Runner);api.op=op
    report=dict(status='RUNNING',additional_live_generations=0,new_native_inputs=0,
                new_maintenance_actions=1,original_repair_not_retried=True,
                original_deadline_not_renewed=True,namespace=op.namespace)
    def save():(root/'report.json').write_bytes(canonical(report))
    def maintain(operation,*args):
        source='import json,sys;from integration.single_node.integrated_search_operator import request;print(json.dumps(request(json.load(sys.stdin))))'
        return json.loads(op.k('exec','-i','fusion-search-0','--',PYTHON,'-c',source,
            data=json.dumps(dict(scope=scope,operation=operation,args=list(args))),timeout=130))
    def publication():
        source='from pathlib import Path;from fusion.contracts import digest;print(digest(Path("/state/memory/active-search/published.json").read_bytes()))'
        return op.k('exec','fusion-search-0','--',PYTHON,'-c',source).strip()
    def retained():
        return {role:{row['session']:api.call(role,'observe',row['session'],'--content')
            for row in api.call(role,'list')} for role in ('omega-agent','omega-agent-b')}
    save()
    try:
        op.owned();before=retained();published=publication()
        old_receipt=maintain('observeRepair',failure['plan'],old_intent['identity'])
        require(old_receipt['state']=='needs-reconciliation' and old_receipt['attempts_spent']==1 and
                old_receipt['deadline_ms']==old_intent['deadline_ms'],'CONFLICT')
        plan=maintain('planRepair',old)
        require(plan['plan']['classification']=='MISSING_DERIVED_INDEX','CONFLICT')
        deadline=time.time_ns()//1000000+120000
        report.update(original_repair=old_receipt,plan=plan,
                      new_intent=dict(identity=identity,deadline_ms=deadline));save()
        repaired=maintain('repair',plan,identity,deadline);report['repair']=repaired;save()
        require(repaired['state']=='verified' and repaired['result']['snapshot']==old,'CONFLICT')
        require(maintain('observeRepair',plan,identity)==repaired,'CONFLICT')
        require(maintain('observeRepair',failure['plan'],old_intent['identity'])==old_receipt,'CONFLICT')
        require(publication()==published and retained()==before,'CONFLICT')
        # The original archive's authenticated source has both payload and
        # enrollment. Rebuild itself obtains them only through those ports.
        original=json.loads((Path(native_report).parent.parent/'report.json').read_bytes())
        archived=[x['ref'] for x in original['archive']['plan']['records']]
        target=prior['first_memory']['memory']['target']
        require(all(target[k] in archived for k in ('payload','enrollment')),'CONFLICT')
        report.update(status='PASS',retained_sessions=sum(map(len,before.values())),
            retained_inputs=sum(len(x['inputs']) for rows in before.values() for x in rows.values()),
            original_uncertain_input_unchanged=True,original_repair_reservation_unchanged=True,
            older_repair_did_not_regress_publication=True,archive_payload_and_enrollment=True,
            source='REAL_NATIVE_CREATED_RECORDS_OVER_AUTHENTICATED_STORAGE_FEED',
            capacity_refunds=0,private_report_publication='FORBIDDEN')
    except BaseException as error:
        report.update(status='FAIL',failure=dict(type=type(error).__name__,code=getattr(error,'code',None),detail=str(error)[-1200:]));raise
    finally:op.quiesce();report['quiesced']=True;save()
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('kubeconfig','context','namespace','directory','native-report','failed-report','identity'):
        p.add_argument('--'+name,required=True)
    a=p.parse_args();value=qualify(Operator(a.kubeconfig,a.context,a.namespace),a.directory,a.native_report,a.failed_report,a.identity)
    print(json.dumps(dict(status=value['status'],additional_live_generations=0)))
