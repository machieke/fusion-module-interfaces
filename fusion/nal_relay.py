"""NAL selection of the existing trusted relay; no second delivery journal."""
from .evidence_relay import EvidenceRelay
from . import nal_memory_contracts as c
from .ports import Mutation
from .contracts import require


class NalEvidenceRelay(EvidenceRelay):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        require(self.consumer is not None and self.consumer['profile']==c.BELIEF_PROFILE,'UNSUPPORTED_PROFILE')
    def _make_request(self,episode,delivery,numeric,declaration,record,snapshot,attempt):
        return c.Admission(Mutation(episode['scope_ref'],f"delivery/{delivery['delivery_id']}/{attempt}"),
            numeric['claim'],numeric['context'],delivery['evidence'],None,snapshot['revision'],c.BELIEF_PROFILE,
            snapshot['runtime_selection'],declaration,work_id=delivery['delivery_id'],
            deadline_ms=record['event']['deadline_ms'],max_evaluations=c.MAX_EVALUATIONS)
    def _request(self,semantic):return c.request(semantic)
    def _decision(self,request):
        decision=self.beliefs.observeDecision(request)
        return self.beliefs.submitEvidence(request) if decision is None else decision
