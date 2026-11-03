"""Fresh 32-record native quota drill; never clears or raises a spent quota.

Install the selected memory composition with feed_capacity.records=32 before
running. At most three intentional remember inputs are permitted. A continuation
accepts one further intention only after two earlier completed writes are proven.
The refused input may have partial effects; it must not manufacture success.
"""
import argparse,json,time
from pathlib import Path
from fusion.contracts import canonical,digest,require
from integration.single_node.reference_ops import Operator,PYTHON
from integration.single_node.sustained_qualification import Runner
from integration.single_node.preview_recovery_qualification import Recovery

def qualify(op,directory,prior=None):
    r=Runner(op,directory);r.end=time.monotonic()+420
    r.report.update(maximum_operator_inputs=1 if prior else 3,frozen=dict(profile='native-capacity-refusal/1',records=32,inputs=1 if prior else 3,
        deadline_ms=120000,wall_seconds=420,proposals='RECORDED_COMMANDS',live_allowance=0));r.save()
    try:
        if prior:
            raw=Path(prior).read_bytes();old=json.loads(raw)
            require(old['namespace']==op.namespace and len(old['inputs'])==2 and all(x['observed']['state']=='complete' for x in old['inputs']),'CONFLICT')
            sid=old['inputs'][0]['session'];r.ids={'omega-agent':[sid]};i=0
            first=r.object(old['inputs'][0]['observed']['result']['projection'])
            r.report['prior_report_sha256']=digest(raw);r.report['continuation']='one new intentional input; previous assertions and captures retained'
        else:
            i=r.allocate('omega-agent','finite-quota');sid=r.ids['omega-agent'][i]
            first=r.object(r.run('remember The synthetic quota pebble is in box juniper',session=i))
            r.run('remember The synthetic second quota pebble is in box poplar',session=i)
        retained_before=r.call('omega-agent','observe',sid,'--content')
        before=r.current('omega-agent',i);require(before['storage_capacity']['limits']['records']==32,'CONFLICT')
        require(before['source_head']['sequence']<=32,'CONFLICT')
        try:r.run('remember The synthetic third quota pebble is in box alder',session=i)
        except Exception as error:
            require(getattr(error,'code',None)=='NOT_AVAILABLE','CONFLICT')
        else:require(False,'CONFLICT')
        last=r.report['inputs'][-1];require(last['observed']['state']!='complete','CONFLICT')
        after=r.current('omega-agent',i)
        require(after['storage_capacity']['usage']['reserved_records']==32 and after['storage_capacity']['refunds'] is False,'CONFLICT')
        helper=Recovery.__new__(Recovery);helper.op=op
        before_account=helper.accounting('omega-agent',sid,last['identity'])
        replacement=helper.replace(['fusion-storage','omega-agent'])
        observed=r.call('omega-agent','observe',sid,'--content')
        for old_row in retained_before['inputs']:
            require(next(x for x in observed['inputs'] if x['id']==old_row['id'])==old_row,'CONFLICT')
        row=next(x for x in observed['inputs'] if x['id']==last['identity'])
        require(row['deadline']==last['accepted']['deadline'] and row['state']!='complete','CONFLICT')
        after_account=helper.accounting('omega-agent',sid,last['identity'])
        require(before_account==after_account,'CONFLICT')
        source='''import json
from pathlib import Path
from fusion.preview_atoms import client
from fusion.contracts import digest,ContractError
from fusion.ports import Mutation
from integration.single_node.sustained_runtime import materialize
app=json.loads(materialize(Path('/run/fusion/owner.json'),Path('/state'),Path('/run/fusion'),SID).read_bytes())
cfg=json.loads(Path(app['memory_atoms_config']).read_bytes());atoms=client(cfg)
payload=atoms.get(REF)
assert b'synthetic quota pebble' in payload.bytes
before=atoms.capacity(cfg['scope'])
try:atoms.create(Mutation(cfg['scope'],'bounded-capacity-refusal-probe'),'text/plain',b'Approved synthetic quota probe')
except ContractError as error:assert error.code=='OVERLOADED';code=error.code
else:raise AssertionError('full source admitted a new record')
assert atoms.capacity(cfg['scope'])==before
print(json.dumps(dict(reference_digest_verified=digest(payload.bytes)==REF['digest'],authoritative_payload_readable=True,explicit_provider_refusal=code,capacity_unchanged=True)))
'''.replace('SID',repr(sid)).replace('REF',repr(first['memory']['target']['payload']))
        readback=json.loads(op.k('exec','-i','omega-agent-0','--',PYTHON,'-',data=source,timeout=35))
        r.report.update(status='PASS',before=before,after=after,replacement=replacement,readback=readback,
            budget_before=before_account,budget_after=after_account,partial_effects='RETAINED_NOT_ROLLED_BACK',
            old_capture_unchanged=True,deadline_renewals=0,refunds=0);r.save()
    except BaseException as error:
        r.report.update(status='FAILED',failure=dict(type=type(error).__name__,code=getattr(error,'code',None),detail=str(error)[-1000:]));r.save();raise
    finally:op.quiesce();r.report['quiesced']=True;r.save()
    return r.report

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('kubeconfig','context','namespace','directory'):p.add_argument('--'+name,required=True)
    p.add_argument('--prior-report')
    a=p.parse_args();print(json.dumps(qualify(Operator(a.kubeconfig,a.context,a.namespace),a.directory,a.prior_report)))
if __name__=='__main__':main()
