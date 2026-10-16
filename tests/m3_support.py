"""Generated M3 fixtures and explicit real-provider composition."""
import json
import os
from pathlib import Path
import time
from fusion import cognition_contracts as c
from fusion import attention_contracts as a
from fusion.cognition import descriptors, OPERATIONS, open_cognition
from fusion.contracts import canonical, digest
from fusion.registry import descriptor_wire
from fusion.ports import Mutation, EvidenceSubmission, Stimulus, InferenceRequest, WorkBudget
from fusion.adapters.fixture_atoms import FileAtomFixture
from tests.m2_support import MemoryHarness, PortOnly, SCOPE


class RefusingKernelFixture:
    """No deduction mathematics. All positive numerical gates require native PLN."""
    def profile(self):return {'profile':c.RULE,'provider':'refusing-kernel-fixture'}
    def applyRule(self,task,premises,deadline_ms):return {'status':'UNKNOWN','detail':'fixture refuses; no formula','proposal':None}


class CognitionHarness(MemoryHarness):
    def __init__(self,root=None,*,real=False,provider='sqlite',hook=lambda stage:None):
        self.provider=provider
        # Parent constructs only the original M2 modules, then M3 opens fresh journals.
        super().__init__(root,real=real,with_revision=False,hook=hook)
        self.config.update(cognition_descriptors=[descriptor_wire(d) for d in descriptors(provider)],attention_provider=provider,
            attention_policy=a.DEFAULT_POLICY,deduction_environment=os.environ.get('M3_DEDUCTION_ENV','absent-deduction'))
        methods=self.config['principals']['owner']['scopes'][SCOPE]
        methods.extend(name+'.'+op for name,ops in OPERATIONS.items() for op in ops)
        methods.extend(['attention.ingress','attention.feedback'])
        self.kernel_fixture=None if real else RefusingKernelFixture();self.save();self.reopen()

    def reopen(self):
        if not hasattr(self,'kernel_fixture'):return super().reopen()
        fixture=None if self.real else FileAtomFixture(str(self.root/'private/files'),str(self.root/'private/bytes'))
        self.modules=open_cognition(self.path,self.credential,SCOPE,hook=self.hook,atom_fixture=fixture,
            math_fixture=None if self.real else self.math,kernel_fixture=self.kernel_fixture,wrap=PortOnly)
        self.atoms,self.episodes,self.beliefs,self.attention,self.controller=self.modules.atoms,self.modules.episodes,self.modules.beliefs,self.modules.attention,self.modules.controller
        return self

    def submit(self,claim,evidence=None,support_id=None,key='submit',expected=None,independence=None,context='generated'):
        snapshot=self.beliefs.readBelief(claim,context,None)
        return self.beliefs.submitEvidence(EvidenceSubmission(Mutation(SCOPE,key),claim,context,evidence,support_id,
            snapshot['revision'] if expected is None else expected,c.BELIEF_PROFILE,snapshot['runtime_selection'],independence))

    def generated(self,seed='a',context='generated',strengths=None,source='sensor-a'):
        strengths=strengths or ['0.5','0.5','0.5','0.8','0.8'];roles={}
        for role in ('p','q','r'):
            record={'predicate':'pln:proposition','arguments':[seed+'-'+role],'positive':True}
            roles[role]=self.atoms.create(Mutation(SCOPE,seed+'/'+role),'application/fusion-claim',canonical(record))['ref']
        for role,left,right in [('pq','p','q'),('qr','q','r'),('pr','p','r')]:
            record={'predicate':'pln:implication','arguments':[digest(canonical(roles[left])),digest(canonical(roles[right]))],'positive':True}
            roles[role]=self.atoms.create(Mutation(SCOPE,seed+'/'+role),'application/fusion-claim',canonical(record))['ref']
        task=self.atoms.create(Mutation(SCOPE,seed+'/task'),'application/fusion-task',canonical({'profile':c.RULE,'context':context,'roles':roles}))['ref']
        episode=self.episode(seed+'/episode');bindings=[]
        for index,role in enumerate(c.ROLES[:5]):
            event=self.event(roles[role],seed+'-'+role,source=source,strength=strengths[index],confidence='0.8' if index<3 else '0.7',context=context)
            receipt=self.append(episode,event,index,key=seed+'/append/'+role)
            decision=self.submit(roles[role],receipt['evidence'],key=seed+'/submit/'+role,expected=0,context=context)
            bindings.append({'claim':roles[role],'context':context,'revision':decision['snapshot']['revision'],'support_id':decision['support_id']})
        return {'task':task,'premises':bindings},roles,episode

    def workset(self,entries,key='workset',context='generated'):
        return self.atoms.create(Mutation(SCOPE,key),'application/fusion-workset',canonical({'profile':c.WORKSET,'context':context,'tasks':entries}))['ref']

    def stimulate(self,entry,amount='10',key='ingress',context='generated',step=0):
        request=Stimulus(Mutation(SCOPE,key),context,entry['task'],amount,key,0,self.attention.profile()['policy'],step,'ingress')
        return self.attention.submitStimulus(request)

    def request(self,workset,key='step',attempts=1,candidates=2,generation=3,deadline=None,context='generated'):
        return InferenceRequest(Mutation(SCOPE,key),context,workset,self.modules.selections,
            WorkBudget(candidates,attempts,generation,deadline or int(time.time()*1000)+60000))
