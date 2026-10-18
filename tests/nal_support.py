"""Generated S04 owner harness; real DeTTa and native NAL, no model calls."""
import json
import os
from pathlib import Path
import tempfile
import time
from fusion import nal_memory_contracts as c
from fusion.contracts import canonical
from fusion.ports import Mutation
from fusion.nal_private import open_local
from integration.neoclaw.evidence_composition import policy,SCOPE,CONTEXT,ASSUMPTION
from tests.neoclaw_support import RUNTIME,ROOT
from tests.m2_support import PortOnly


class Harness:
    def __init__(self,root=None,*,with_revision=True,hook=lambda _:None,hostile=True):
        self.temp=tempfile.TemporaryDirectory(prefix='s04-owner-') if root is None else None
        self.root=Path(root or self.temp.name);self.root.mkdir(parents=True,exist_ok=True)
        self.path=self.root/'policy.json';self.credential='generated-local-test-only';self.hook=hook;self.hostile=hostile;self.with_revision=with_revision
        if not self.path.exists():
            self.config=policy(self.root/'private','A',self.credential,RUNTIME,os.environ.get('S01_DETTA',ROOT/'artifacts/m5/reproduction-01/providers/detta/target/debug/fusion-detta-adapter'))
            self.save()
        else:self.config=json.loads(self.path.read_text())
        self.reopen()
    def save(self):self.path.write_bytes(canonical(self.config))
    def reopen(self):
        self.modules=open_local(self.path,self.credential,SCOPE,hook=self.hook,with_revision=self.with_revision,wrap=PortOnly if self.hostile else lambda obj,names:obj)
        self.atoms,self.episodes,self.beliefs,self.relay=self.modules.atoms,self.modules.episodes,self.modules.beliefs,self.modules.relay
    def close(self):
        if self.temp:self.temp.cleanup()
    def episode(self):return self.episodes.recordEpisode(Mutation(SCOPE,'episode'),'generated-channel')['ref']
    def prior(self,key='memory',deadline=None):
        deadline=deadline or int(time.time()*1000)+30000
        # Direct-port fixture representing the trusted creation-binding boundary.
        payload=self.atoms.create(Mutation(SCOPE,key+'/opaque'),'text/plain',b'generated memory creation') ['ref']
        creation=self.atoms.create(Mutation(SCOPE,key+'/creation'),'application/neoclaw-fresh-creation',canonical(dict(policy=c.PRIOR,
            memory_uuid=key,occurrence=key,time='2031-04-05 06:07:08',payload=payload,enrollment=payload)))['ref']
        claim=self.atoms.create(Mutation(SCOPE,key+'/claim'),'application/fusion-claim',canonical(dict(predicate='neoclaw-memory-assessment',arguments=[creation['digest']],positive=True)))['ref']
        result=self.beliefs.registerPrior(Mutation(SCOPE,key+'/prior'),claim,CONTEXT,creation,deadline)
        return claim,creation,result
    def source(self,key='source',source='controlled-source-a',copy=None,episode=None,deadline=None):
        episode=episode or self.episode();command=Mutation(SCOPE,key);deadline=deadline or int(time.time()*1000)+30000
        occurrence=self.episodes.occurrenceIdentity(command,episode)
        payload=self.atoms.create(Mutation(SCOPE,key+'/payload'),'application/neoclaw-source',canonical(dict(text='same synthetic text',label=key,source=source,observed_time='2031-04-05T06:08:09Z')))['ref']
        event=dict(occurrence_id=occurrence,kind='observation',source=source,observed_time='2031-04-05T06:08:09Z',payload=payload,
            causation=[],provenance=[copy] if copy else [],numerical=None,deadline_ms=deadline)
        head=self.episodes.readEpisode(episode,1,1)['head']
        return self.episodes.appendEvent(command,episode,head,event)
    def assessment(self,claim,source,*,key='assessment',sign=True,deadline=None):
        episode=source['episode'];command=Mutation(SCOPE,key);deadline=deadline or int(time.time()*1000)+30000
        occurrence=self.episodes.occurrenceIdentity(command,episode)
        payload=self.atoms.create(Mutation(SCOPE,key+'/payload'),'text/plain',b'explicit generated assessment')['ref']
        numeric=dict(claim=claim,context=CONTEXT,relationship='supports' if sign else 'contradicts',truth=c.stv('1.0' if sign else '0.0','0.5'),ingestion_profile=c.INGESTION)
        event=dict(occurrence_id=occurrence,kind='action',source='agent',observed_time='2031-04-05T06:08:09Z',payload=payload,causation=[],provenance=[source],numerical=numeric,deadline_ms=deadline)
        head=self.episodes.readEpisode(episode,1,1)['head'];return self.episodes.appendEvent(command,episode,head,event)
    def declaration(self,claim,receipt):
        snapshot=self.beliefs.readBelief(claim,CONTEXT,None);record=self.episodes.readEvidence(receipt['evidence'])
        return dict(model_id=ASSUMPTION,supports=[snapshot['aggregate'],c.contribution(record)],status='assumption')
    def request(self,claim,receipt,*,key='submit',assume=True,deadline=None,revision=None):
        snapshot=self.beliefs.readBelief(claim,CONTEXT,None)
        return c.Admission(Mutation(SCOPE,key),claim,CONTEXT,receipt['evidence'],None,snapshot['revision'] if revision is None else revision,
            c.BELIEF_PROFILE,snapshot['runtime_selection'],self.declaration(claim,receipt) if assume else None,
            work_id=receipt['delivery_id'],deadline_ms=deadline or self.episodes.readEvidence(receipt['evidence'])['event']['deadline_ms'],max_evaluations=c.MAX_EVALUATIONS)
