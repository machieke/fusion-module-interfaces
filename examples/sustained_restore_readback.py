"""Observe old payloads, history and private denial in an already fenced clone.

The clone must use the installed restore recipe. No native worker, encoder,
query execution, completion relay, channel or chain process is started here.
Every remote read uses current clone credentials and an existing declared port.
"""
import argparse,json
from pathlib import Path
from fusion.contracts import canonical,digest,require
from integration.single_node.reference_ops import Operator,PYTHON

def verify(op,native,directory):
    root=Path(directory);root.mkdir(parents=True,exist_ok=False)
    raw=Path(native).read_bytes();original=json.loads(raw);require(original['status']=='PASS','NOT_AVAILABLE')
    result=dict(status='RUNNING',clone=op.namespace,native_report_sha256=digest(raw),new_native_inputs=0,additional_live_generations=0)
    def save():(root/'report.json').write_bytes(canonical(result))
    save()
    try:
        op.owned()
        roles=[w['metadata']['name'] for w in op.workloads()]
        # Restore Host checks the journal fence before any role startup. These
        # three owners suffice for immutable payload/history reconstruction.
        selected=[r for r in roles if r in ('omega-agent','omega-agent-b','fusion-storage','fusion-episodes')]
        for role in selected:op.k('scale','statefulset',role,'--replicas=1')
        for role in selected:op.k('wait','--for=condition=Ready','pod/'+role+'-0','--timeout=90s',timeout=100)
        shared=original['first_memory']['memory']['target']['payload']
        history=next(x['value']['history'] for x in original['source_observations'] if x['role']=='omega-agent')
        private=next(x for x in original['private_cases'] if x['role']=='omega-agent')['current']
        ref=next(iter(private['retained']['view']['handles'].values()))['envelope']['target']['payload']
        source='''import json
from pathlib import Path
from fusion.contracts import digest
from fusion.preview_atoms import client
from fusion.preview_ports import Client
assert Path('/state/restore-fence.json').exists()
root=Path('/run/fusion/templates');shared=json.loads((root/'shared/memory-atoms.json').read_bytes());private=json.loads((root/'private/memory-atoms.json').read_bytes())
a=client(shared).get(SHARED);b=client(private).get(PRIVATE)
assert digest(a.bytes)==SHARED['digest'] and digest(b.bytes)==PRIVATE['digest']
app=json.loads((root/'shared/application.json').read_bytes());h=Client(app['facet_configs']['episodic.memory'],'episodic.memory')
page=h.call('readHistory',HISTORY,1,8)
assert page['events'] and page['evidence_weight_created'] is False
print(json.dumps(dict(status='PASS',old_shared_payload_verified=True,private_payload_current_authority_verified=True,history_events_verified=len(page['events']),history_weight_created=False,private_bytes_exported=False)))
'''.replace('SHARED',repr(shared)).replace('PRIVATE',repr(ref)).replace('HISTORY',repr(history))
        result['owner_readback']=json.loads(op.k('exec','-i','omega-agent-0','--',PYTHON,'-',data=source,timeout=45));save()
        source='''import json
from pathlib import Path
from fusion.contracts import ContractError
from fusion.preview_atoms import client
assert Path('/state/restore-fence.json').exists()
cfg=json.loads(Path('/run/fusion/templates/shared/memory-atoms.json').read_bytes());cfg['scope']=SCOPE
try:client(cfg).get(REF)
except ContractError as error:assert error.code=='UNAUTHORIZED';code=error.code
else:raise AssertionError('foreign private data exposed by clone')
print(json.dumps(dict(status='PASS',foreign_private_read=code,private_bytes_returned=False)))
'''.replace('SCOPE',repr(private['scope'])).replace('REF',repr(ref))
        result['foreign_private_denial']=json.loads(op.k('exec','-i','omega-agent-b-0','--',PYTHON,'-',data=source,timeout=35))
        result.update(status='PASS',effect_execution='NO_EXECUTOR_OR_EFFECT_PORT_STARTED');save()
    except BaseException as error:
        result.update(status='FAILED',failure=dict(type=type(error).__name__,code=getattr(error,'code',None),detail=str(error)[-1000:]));save();raise
    finally:op.quiesce();result['clone_quiesced']=True;save()
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('kubeconfig','context','namespace','native','directory'):p.add_argument('--'+name,required=True)
    a=p.parse_args();print(json.dumps(verify(Operator(a.kubeconfig,a.context,a.namespace),a.native,a.directory)))
if __name__=='__main__':main()
