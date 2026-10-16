"""Additional generated real-provider check: processing completion does not assert truth."""
import json,subprocess
from tests.m3_1_support import ClosureHarness,SCOPE
from fusion.ports import Mutation
from fusion.contracts import canonical
report={'source':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        'classification':'generated cases; real DeTTa and selected C2 v3; no numerical formula needed','cases':[]}
for kind in ('report','unregistered-origin'):
    h=ClosureHarness(real=True)
    try:
        claim=h.atoms.create(Mutation(SCOPE,'p'),'application/fusion-claim',canonical({'predicate':'pln:proposition','arguments':['p'],'positive':True}))['ref']
        episode=h.episode();event=h.event(claim,relationship='reports' if kind=='report' else 'supports',source='sensor-a' if kind=='report' else 'unregistered')
        h.append(episode,event);decision=h.modules.relay.drain(episode)[0]
        assert decision['numerical']=='model-inapplicable' and decision['snapshot']['truth'] is None
        assert len(decision['snapshot']['observations'])==1 and h.episodes.pendingEvidence(episode,16)==()
        h.reopen();assert h.modules.relay.drain(episode)==() and len(h.modules.relay.decisions(episode))==1
        report['cases'].append({'case':kind,'processing':'committed-and-acknowledged','numerical':decision['numerical'],'truth':None,'observations':1,'pending':0})
    finally:h.close()
print(json.dumps(report,indent=2))
