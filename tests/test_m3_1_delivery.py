"""Completion trust and bounded delivery; explicit file/guard-only fixtures."""
from dataclasses import replace
import copy
import json
import subprocess
import sys
import unittest
from fusion import delivery_contracts as d
from fusion.contracts import ContractError,canonical,digest
from fusion.ports import Mutation
from fusion.private import open_private,descriptors
from fusion.registry import descriptor_wire
from fusion.adapters.fixture_atoms import FileAtomFixture
from tests.m2_support import MemoryHarness,SCOPE
from tests.m3_1_support import ClosureHarness

class StandaloneEpisode(MemoryHarness):
    def reopen(self):
        consumer={'principal':'owner','provider':'trusted-consumer-fixture','profile':'opaque-completion-fixture/1','selection':'a'*64}
        self.config.update(delivery_closure=d.CONFIG,evidence_consumer=consumer,
            private_descriptors=[descriptor_wire(replace(x,receipt_providers=frozenset({'contract-fixture-files/1'}))) for x in descriptors(closure=True)])
        self.config['principals']['owner']['scopes'][SCOPE].append('episodic.memory.acknowledgeDelivery');self.save()
        self.modules=open_private(self.path,self.credential,SCOPE,with_revision=False,
            atom_fixture=FileAtomFixture(str(self.root/'private/files'),str(self.root/'private/bytes')),completion_consumer=consumer)
        self.atoms,self.episodes=self.modules.atoms,self.modules.episodes
        return self

class DeliveryTests(unittest.TestCase):
    def test_standalone_c1_trust_closed_dto_and_semantic_replay(self):
        h=StandaloneEpisode(with_revision=False)
        try:
            claim=h.claim();episode=h.episode();ev=h.append(episode,h.event(claim))['evidence']
            request_key='fixture-request'
            completed=dict(profile=d.COMPLETION,state='committed',scope_ref=SCOPE,delivery_id=digest(canonical(ev)),evidence=ev,
                claim=claim,context='generated',consumer=h.config['evidence_consumer'],request_key=request_key,
                request_digest='b'*64,decision_id=digest(canonical(['owner',SCOPE,request_key])),decision_digest='c'*64)
            # A valid caller-built DTO still cannot attest via the ordinary C1 context.
            with self.assertRaises(ContractError) as error:h.episodes.acknowledgeDelivery(Mutation(SCOPE,'untrusted'),completed)
            self.assertEqual(error.exception.code,'UNAUTHORIZED')
            ack=h.modules.completion_episodes.acknowledgeDelivery
            variants=[{**completed,'state':'pending'},{**completed,'profile':'unknown'},
                {**completed,'delivery_id':'d'*64},{**completed,'decision_id':'d'*64},
                {**completed,'context':'wrong'},{**completed,'consumer':{**completed['consumer'],'provider':'wrong'}},
                {**completed,'claim':{**claim,'digest':'d'*64}}, {**completed,'extra':True}]
            for index,value in enumerate(variants):
                with self.subTest(index=index),self.assertRaises(ContractError):ack(Mutation(SCOPE,'bad/'+str(index)),value)
            self.assertEqual(len(h.episodes.pendingEvidence(episode,16)),1)
            receipt=ack(Mutation(SCOPE,'ack'),completed);d.receipt(receipt,completed)
            self.assertEqual(ack(Mutation(SCOPE,'ack-again'),completed),receipt)
            self.assertEqual(h.episodes.pendingEvidence(episode,16),())
            for key in ('ack','different-key'):
                with self.assertRaises(ContractError):ack(Mutation(SCOPE,key),{**completed,'decision_digest':'e'*64})
            with self.assertRaises(ContractError):ack(Mutation('other','cross-scope'),completed)
            h.config['principals']['owner']['credential']='revoked';h.save()
            with self.assertRaises(ContractError) as error:ack(Mutation(SCOPE,'ack'),completed)
            self.assertEqual(error.exception.code,'UNAUTHORIZED')
        finally:h.close()

    def test_c1_can_run_without_c2_pln_or_hive_imports(self):
        code='''from tests.test_m3_1_delivery import StandaloneEpisode
import sys
h=StandaloneEpisode(with_revision=False)
e=h.episode();assert h.episodes.pendingEvidence(e,16)==()
assert 'fusion.beliefs' not in sys.modules and 'fusion.derived_beliefs' not in sys.modules
assert not any(k.startswith(('janus','hive.','fusion.adapters.pln')) for k in sys.modules)
h.close()
'''
        result=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)

    def run_batches(self,real=False):
        h=ClosureHarness(real=real)
        try:
            episode=h.episode();claims=[];evidence=[]
            for index in range(33):
                claim=h.atoms.create(Mutation(SCOPE,'claim/'+str(index)),'application/fusion-claim',canonical({
                    'predicate':'pln:proposition','arguments':['batch-'+str(index)],'positive':True}))['ref'];claims.append(claim)
                event=h.event(claim,'event-'+str(index))
                if index==16:
                    with self.assertRaises(ContractError) as error:h.append(episode,event,index)
                    self.assertEqual(error.exception.code,'OVERLOADED')
                    self.assertEqual(len(h.modules.relay.drain(episode)),16)
                    self.assertEqual(h.episodes.pendingEvidence(episode,16),())
                evidence.append(h.append(episode,event,index)['evidence'])
                if index in (31,32):
                    self.assertEqual(len(h.modules.relay.drain(episode)),16 if index==31 else 1)
                    self.assertEqual(h.episodes.pendingEvidence(episode,16),())
            self.assertEqual(h.episodes.readEpisode(episode,1,16)['head'],33)
            self.assertEqual(len(h.modules.relay.decisions(episode)),33)
            h.reopen();self.assertEqual(h.modules.relay.drain(episode),())
            for claim,ev in zip(claims,evidence):
                snapshot=h.beliefs.readBelief(claim,'generated',None)
                self.assertEqual(len(snapshot['observations']),1);self.assertEqual(snapshot['observations'][0]['evidence'],ev)
            return {'events':33,'logical_observations':33,'pending':0,'batches':[16,16,1]}
        finally:h.close()

    def test_33_events_one_persistent_episode_and_capacity_recovery(self):self.run_batches()

    def test_bad_c2_receipts_never_ack_and_exact_replay_recovers(self):
        for variant in ('decision','evidence','snapshot','pending','unavailable'):
            with self.subTest(variant=variant):
                h=ClosureHarness()
                try:
                    claim=h.atoms.create(Mutation(SCOPE,'p'),'application/fusion-claim',canonical({'predicate':'pln:proposition','arguments':['p'],'positive':True}))['ref']
                    episode=h.episode();h.append(episode,h.event(claim))
                    relay=h.modules.relay;original=relay.beliefs
                    class Bad:
                        def readBelief(self,*args):return original.readBelief(*args)
                        def submitEvidence(self,request):
                            result=copy.deepcopy(original.submitEvidence(request))
                            if variant=='decision':result['decision_id']='wrong'
                            elif variant=='evidence':result['evidence']['sequence']+=1
                            elif variant=='snapshot':result['snapshot']['supports'][0]['ancestors']=['invented']
                            elif variant=='pending':return {'state':'pending'}
                            else:raise ContractError('NOT_AVAILABLE')
                            return result
                    relay.beliefs=Bad()
                    with self.assertRaises(ContractError):relay.drain(episode)
                    self.assertEqual(len(h.episodes.pendingEvidence(episode,16)),1)
                    relay.beliefs=original;self.assertEqual(len(relay.drain(episode)),1)
                    self.assertEqual(h.episodes.pendingEvidence(episode,16),())
                    self.assertEqual(len(h.beliefs.readBelief(claim,'generated',None)['observations']),1)
                    h.config['principals']['owner']['scopes'][SCOPE]=[op for op in h.config['principals']['owner']['scopes'][SCOPE] if op!='belief.revision.submitEvidence'];h.save()
                    with self.assertRaises(ContractError):relay.decisions(episode)
                finally:h.close()

if __name__=='__main__':unittest.main()
