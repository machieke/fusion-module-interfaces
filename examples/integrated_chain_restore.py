"""Fenced observation of the same native workflow's saved chain continuation.

Reuses the existing authority-free quiesced export. The original node PVC stays
stopped; node cryptographic state is excluded. No node restore/failover claim.
"""
import argparse,json,uuid
from pathlib import Path
from fusion.contracts import canonical,digest,require
from fusion.chain_continuation import PROFILE
from integration.single_node.reference_ops import Operator,PYTHON
from integration.single_node.sustained_restore_qualification import drill


def qualify(original,clone,values,chart,directory,native_report,images):
    raw=Path(native_report).read_bytes();prior=json.loads(raw)
    require(prior['status']=='PASS' and prior['namespace']==original.namespace and
        prior['final_continuation']['status']=='finalized' and prior['final_continuation']['submit_reservations']==1,'CONFLICT')
    def readback(owner):
        request=dict(profile=PROFILE,id=str(uuid.uuid4()),session=prior['session'],
            occurrence=prior['occurrence'],operation='observe',body={})
        code='import json,sys;from integration.single_node.preview_operator import chain_continuation;print(json.dumps(chain_continuation(json.load(sys.stdin))))'
        observed=json.loads(owner.k('exec','-i','omega-agent-0','--',PYTHON,'-c',code,data=json.dumps(request),timeout=30))
        require(observed['restore_fenced'] and not observed['execution_authorized'] and not observed['retained_approval_is_current_authority'],'CONFLICT')
        require(all(observed[k]==v for k,v in prior['final_continuation'].items()),'CONFLICT')
        for operation in ('admit','advance'):
            request['operation']=operation
            try:owner.k('exec','-i','omega-agent-0','--',PYTHON,'-c',code,data=json.dumps(request),timeout=30)
            except RuntimeError as error:require('UNAUTHORIZED' in str(error),'CONFLICT')
            else:require(False,'CONFLICT')
        require(not any(x['metadata']['name'].startswith('f1r3node') for x in json.loads(owner.k('get','pods','-o','json'))['items']),'CONFLICT')
        return dict(source_report_sha256=digest(raw),exact_continuation_retained=True,
            observed=observed,old_approval_not_authority=True,submit_reservations=1,
            new_submissions=0,node_restore='EXCLUDED',node_started=False,mutation_routes_refused=True)
    caller=next(x for x in images['images'] if x['kind']=='caller')
    return drill(original,clone,values,chart,directory,maintenance_image=caller['repository']+'@'+caller['manifest_digest'],
        images=images,after_restore=readback)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('kubeconfig','context','original','clone','values','chart','directory','native-report','images'):p.add_argument('--'+name,required=True)
    a=p.parse_args();r=qualify(Operator(a.kubeconfig,a.context,a.original),Operator(a.kubeconfig,a.context,a.clone),
        a.values,a.chart,a.directory,a.native_report,json.loads(Path(a.images).read_bytes()))
    print(json.dumps(dict(status=r['status'],additional_live_generations=0)))
