"""Small controlled provider-substitution experiment; generated data, real formula."""
import argparse
import json
from pathlib import Path
import sys
import time
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from fusion.adapters.pln_deduction import DeductionRuntime
from fusion.contracts import canonical
from tests.m3_support import CognitionHarness


def compare(output):
    cases=[];reference=None;deadline=int(time.time()*1000)+300000
    for provider in ('sqlite','atomic-file-fixture'):
        for prefer in ('b','a'):
            h=CognitionHarness(real=True,provider=provider);began=time.monotonic();calls=[]
            original=DeductionRuntime.evaluate
            def counted(self,*args):calls.append(args[0]);return original(self,*args)
            try:
                a,_,_=h.generated('fixed-a');b,_,_=h.generated('fixed-b');entries=[a,b]
                inputs=canonical(entries)
                if reference is None:reference=inputs
                assert inputs==reference,'comparison changed task/evidence bindings'
                h.stimulate(a,'20' if prefer=='a' else '10','a');h.stimulate(b,'20' if prefer=='b' else '10','b')
                request=h.request(h.workset(entries),deadline=deadline)
                prepared=time.monotonic()
                with patch.object(DeductionRuntime,'evaluate',counted):
                    result=h.controller.step(request);ended=time.monotonic()
                    h.reopen();replay=h.controller.step(request)
                assert result==replay and len(calls)==1 and result['counts']['unique_admissions']==1 and result['counts']['feedback_applied']==1
                labels={canonical(a['task']):'a',canonical(b['task']):'b'}
                order=[labels[canonical(v['target'])] for v in result['selection']['ranked']]
                assert order[0]==prefer
                size=sum(p.stat().st_size for p in h.modules.root.rglob('*') if p.is_file())
                cases.append({'attention_provider':provider,'prefer':prefer,'selection_order':order,'counts':result['counts'],
                    'measured_native_formula_invocations':len(calls),'valid_proposals':1,'refused_proposals':0,
                    'successful_replay_new_native_invocations':0,'recovery':'same receipt after reopening all owners',
                    'prepare_seconds':round(prepared-began,6),'step_seconds':round(ended-prepared,6),
                    'private_store_bytes':size,'terminal_reason':result['reason']})
            finally:h.close()
    report={'classification':{'inputs':'generated fixture','sqlite_attention':'persistent reference policy implementation',
        'atomic_file_attention':'independent same-profile fixture','payloads':'real DeTTa','kernel':'guarded native PLN'},
        'fixture_size':{'tasks':2,'premises_per_task':5,'observations':10,'episodes':2,'claim_atoms':12},
        'held_fixed':['exact task and evidence bindings','policy parameters','one-attempt and two-candidate budgets','absolute deadline','logical schedule'],
        'varied':['attention provider in composition','declared initial STI preference in separate controlled cases'],
        'cases':cases,'limitations':['one local run per case; no throughput or cognitive-quality claim','process restart, not live migration']}
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(report,indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);compare(p.parse_args().output)
