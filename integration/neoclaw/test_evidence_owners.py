"""Real local C1/C2/NAL/DeTTa port tests. Creation attestations are explicit fixtures."""
from dataclasses import replace
import json
from pathlib import Path
import time
import unittest
from unittest.mock import patch
from fusion import nal_memory_contracts as c
from fusion.contracts import ContractError,canonical
from fusion.ports import Mutation
from tests.nal_support import Harness,SCOPE,CONTEXT


class EvidenceOwners(unittest.TestCase):
    def setUp(self):self.h=Harness()
    def tearDown(self):self.h.close()
    def test_prior_native_revision_duplicate_and_contrary(self):
        h=self.h;claim,creation,prior=h.prior();source=h.source()['evidence'];r=h.assessment(claim,source)
        self.assertEqual(prior['observations'],[]);self.assertEqual(prior['supports'][0]['lineage_roots'],[])
        declaration=h.declaration(claim,r);decision=h.relay.drain(source['episode'],{r['delivery_id']:declaration})[0]
        self.assertEqual(decision['numerical'],'revised');self.assertEqual(decision['snapshot']['truth']['strength'],'1.0')
        self.assertAlmostEqual(float(decision['snapshot']['truth']['confidence']),2/3)
        r2=h.assessment(claim,source,key='new-command-same-source');d2=h.relay.drain(source['episode'])[0]
        self.assertEqual(d2['numerical'],'no-change');self.assertEqual(d2['admission'],'duplicate');self.assertEqual(d2['snapshot'],decision['snapshot'])
        r3=h.assessment(claim,source,key='opposite',sign=False);d3=h.relay.drain(source['episode'],{r3['delivery_id']:h.declaration(claim,r3)})[0]
        self.assertEqual(d3['numerical'],'retained-alternative');self.assertEqual(len(d3['snapshot']['observations']),2)
        self.assertEqual(d3['snapshot']['truth'],decision['snapshot']['truth']);self.assertEqual(h.episodes.pendingEvidence(source['episode'],16),())
    def test_identical_text_distinct_occurrences_copy_and_unknown(self):
        h=self.h;claim,_,_=h.prior();a=h.source()['evidence'];b=h.source('b')['evidence'];copy=h.source('copy',copy=a)['evidence'];unknown=h.source('u',source='unregistered')['evidence']
        ar=h.episodes.readEvidence(a);br=h.episodes.readEvidence(b);cr=h.episodes.readEvidence(copy)
        self.assertNotEqual(ar['lineage_roots'],br['lineage_roots']);self.assertEqual(ar['lineage_roots'],cr['lineage_roots'])
        r=h.assessment(claim,a);first=h.relay.drain(a['episode'],{r['delivery_id']:h.declaration(claim,r)})[0]
        r=h.assessment(claim,b,key='b-assess',sign=False);no_assume=h.relay.drain(a['episode'])[0]
        self.assertEqual(no_assume['numerical'],'retained-alternative')
        r=h.assessment(claim,copy,key='copy-assess');dup=h.relay.drain(a['episode'])[0]
        self.assertEqual(dup['admission'],'duplicate')
        r=h.assessment(claim,unknown,key='unknown-assess');u=h.relay.drain(a['episode'])[0]
        self.assertEqual(u['numerical'],'retained-alternative');self.assertIsNone(u['support_id'])
        self.assertEqual(u['snapshot']['truth'],first['snapshot']['truth'])
    def test_pure_c1_without_nal_and_hostile_owner_ports(self):
        with patch('fusion.adapters.neoclaw_revision.NativeTruthRevision',side_effect=AssertionError('must not load NAL')):
            h=Harness(with_revision=False)
            try:
                receipt=h.source();self.assertIsNone(h.modules.beliefs)
                self.assertEqual(h.episodes.readEvidence(receipt['evidence'])['event']['numerical'],None)
                with self.assertRaises(AssertionError):h.episodes.database
            finally:h.close()
    def test_bounds_authority_model_prior_and_exact_replay(self):
        h=self.h;claim,creation,prior=h.prior();source=h.source()['evidence'];r=h.assessment(claim,source);request=h.request(claim,r)
        other_claim=h.prior('other-memory')[0]
        for bad in (replace(request,profile='pln-revision-private/1'),replace(request,runtime_selection='0'*64),
                    replace(request,command=Mutation('wrong','submit')),
                    replace(request,command=Mutation(SCOPE,'wrong-claim'),claim=other_claim,independence=None),
                    replace(request,command=Mutation(SCOPE,'wrong-context'),context='other-context',independence=None),
                    replace(request,evidence=None,support_id='revision/recycled-aggregate')):
            with self.assertRaises(ContractError):h.beliefs.submitEvidence(bad)
        record=h.episodes.readEvidence(r['evidence']);event=record['event']
        with self.assertRaises(ContractError):
            h.episodes.appendEvent(Mutation(SCOPE,'assessment'),source['episode'],r['head']-1,{**event,'observed_time':'2032-01-01T00:00:00Z'})
        with self.assertRaises(ContractError):
            h.episodes.appendEvent(Mutation(SCOPE,'forged-occurrence'),source['episode'],r['head'],event)
        first=h.beliefs.submitEvidence(request);self.assertEqual(h.beliefs.submitEvidence(request),first)
        self.assertEqual(h.beliefs.observeDecision(request),first)
        with self.assertRaises(ContractError):h.beliefs.submitEvidence(replace(request,deadline_ms=request.deadline_ms+1))
        duplicate=h.beliefs.registerPrior(Mutation(SCOPE,'second-prior-request'),claim,CONTEXT,creation,int(time.time()*1000)+10000)
        self.assertEqual(duplicate,first['snapshot'])
        h.config['principals']['A']['scopes'][SCOPE].remove('belief.revision.observeDecision');h.save()
        with self.assertRaises(ContractError):h.beliefs.observeDecision(request)
    def test_credential_substitution_and_assumption_revocation(self):
        import copy
        h=self.h;claim,_,_=h.prior();source=h.source()['evidence'];receipt=h.assessment(claim,source)
        request=h.request(claim,receipt)
        # Existing bound authority may not silently become another principal,
        # even with identical grants and the same credential string.
        original=copy.deepcopy(h.config)
        h.config['principals']['B']=h.config['principals'].pop('A')
        h.config['private_scopes'][SCOPE]='B';h.save()
        with self.assertRaises(ContractError) as error:h.beliefs.submitEvidence(request)
        self.assertEqual(error.exception.code,'UNAUTHORIZED')
        h.config=copy.deepcopy(original);h.save()
        h.config['principals']['A']['scopes'][SCOPE].remove('belief.revision.assume');h.save()
        with self.assertRaises(ContractError) as error:h.beliefs.submitEvidence(request)
        self.assertEqual(error.exception.code,'UNAUTHORIZED');self.assertIsNone(h.beliefs.observeDecision(request))
        h.config=copy.deepcopy(original);h.save()
        def revoke(stage):
            if stage=='after_formula':
                h.config['principals']['A']['scopes'][SCOPE].remove('belief.revision.assume');h.save()
        h.hook=revoke;h.reopen()
        with self.assertRaises(ContractError) as error:h.beliefs.submitEvidence(request)
        self.assertEqual(error.exception.code,'UNAUTHORIZED');self.assertIsNone(h.beliefs.observeDecision(request))
        h.config=original;h.save();h.hook=lambda _:None;h.reopen()
        self.assertEqual(h.beliefs.submitEvidence(request)['numerical'],'revised')

    def test_formula_expiry_retry_budget_and_post_commit_observation(self):
        h=self.h;claim,_,_=h.prior();source=h.source()['evidence'];r=h.assessment(claim,source);request=h.request(claim,r)
        from fusion.adapters.neoclaw_revision import NativeTruthRevision
        with patch.object(NativeTruthRevision,'evaluate',side_effect=ContractError('NOT_AVAILABLE')):
            for _ in range(3):
                with self.assertRaises(ContractError) as e:h.beliefs.submitEvidence(request)
                self.assertEqual(e.exception.code,'NOT_AVAILABLE')
        h.reopen()
        with self.assertRaises(ContractError) as e:h.beliefs.submitEvidence(request)
        self.assertEqual(e.exception.code,'OVERLOADED')
        self.assertIsNone(h.beliefs.observeDecision(request));self.assertEqual(h.beliefs.readBelief(claim,CONTEXT,None)['revision'],1)

    def test_queue_capacity_backpressure_draining_and_reuse_same_episode(self):
        h=self.h;claims=[h.prior('claim-'+str(i))[0] for i in range(3)];episode=h.episode();deliveries=[];decisions=[]
        for batch in range(3):
            receipts=[]
            deadline=int(time.time()*1000)+300000  # Direct-port batch bound, fixed before acceptance.
            for offset in range(16 if batch<2 else 1):
                i=batch*16+offset;source=h.source('source-'+str(i),episode=episode)['evidence']
                receipts.append(h.assessment(claims[i//16],source,key='assessment-'+str(i),sign=i%2==0,deadline=deadline))
            if batch<2:
                source=h.source('overflow-source-'+str(batch),episode=episode)['evidence']
                with self.assertRaises(ContractError) as error:h.assessment(claims[batch],source,key='overflow-'+str(batch))
                self.assertEqual(error.exception.code,'OVERLOADED')
            self.assertEqual(len(h.episodes.pendingEvidence(episode,16)),len(receipts))
            out=h.relay.drain(episode);decisions.extend(out);deliveries.extend(receipts)
            self.assertEqual(len(out),len(receipts));self.assertEqual(h.episodes.pendingEvidence(episode,16),())
            h.reopen();self.assertEqual(h.relay.drain(episode),())
        self.assertEqual(len(decisions),33);self.assertTrue(all(x['numerical']=='retained-alternative' for x in decisions))
        self.assertEqual(len(h.relay.decisions(episode)),33)

    def test_authority_after_formula_cas_and_expired_committed_observation(self):
        h=self.h;claim,_,_=h.prior();source=h.source()['evidence'];r=h.assessment(claim,source);request=h.request(claim,r)
        def revoke(stage):
            if stage=='after_formula':
                h.config['principals']['A']['scopes'][SCOPE].remove('belief.revision.submitEvidence');h.save()
        h.hook=revoke;h.reopen()
        with self.assertRaises(ContractError) as error:h.beliefs.submitEvidence(request)
        self.assertEqual(error.exception.code,'UNAUTHORIZED');self.assertIsNone(h.beliefs.observeDecision(request))
        h.config['principals']['A']['scopes'][SCOPE].append('belief.revision.submitEvidence');h.save();h.hook=lambda _:None;h.reopen()
        decision=h.beliefs.submitEvidence(request)
        with patch('fusion.nal_beliefs.time.time_ns',return_value=(request.deadline_ms+1)*1_000_000):
            self.assertEqual(h.beliefs.observeDecision(request),decision);self.assertEqual(h.beliefs.submitEvidence(request),decision)
            next_r=h.assessment(claim,source,key='fresh-duplicate')
            with self.assertRaises(ContractError):h.beliefs.submitEvidence(h.request(claim,next_r,key='expired',deadline=request.deadline_ms))
        with self.assertRaises(ContractError):h.beliefs.submitEvidence(replace(request,command=Mutation(SCOPE,'wrong-cas'),expected_revision=0))

    def test_malformed_relay_response_never_acknowledges(self):
        h=self.h;claim,_,_=h.prior();source=h.source()['evidence'];receipt=h.assessment(claim,source)
        declaration=h.declaration(claim,receipt)
        from fusion.nal_beliefs import NalBeliefOwner
        original=NalBeliefOwner.submitEvidence
        def malformed(owner,request):
            value=original(owner,request);value['snapshot']['supports'][0]['lineage_roots']=['invented-prior-root'];return value
        with patch.object(NalBeliefOwner,'submitEvidence',malformed):
            h.reopen()  # Hostile ports capture bound methods at composition time.
            with self.assertRaises(ContractError) as error:h.relay.drain(source['episode'],{receipt['delivery_id']:declaration})
        self.assertEqual(error.exception.code,'NOT_AVAILABLE');self.assertEqual(len(h.episodes.pendingEvidence(source['episode'],16)),1)
        # The actual owner decision was committed before corruption; observe it.
        h.reopen()
        out=h.relay.drain(source['episode'],{receipt['delivery_id']:declaration})
        self.assertEqual(out[0]['numerical'],'revised');self.assertEqual(h.episodes.pendingEvidence(source['episode'],16),())

    def test_real_killed_evaluations_remain_spent_across_restart(self):
        import os,signal,subprocess,sys
        h=self.h;claim,_,_=h.prior();source=h.source()['evidence'];receipt=h.assessment(claim,source)
        request=h.request(claim,receipt);path=h.root/'request.json';path.write_bytes(canonical(c.submission(request)))
        processes=[]
        try:
            for _ in range(3):
                marker=h.root/'paused.json';marker.unlink(missing_ok=True)
                process=subprocess.Popen([sys.executable,'-m','integration.neoclaw.evidence_worker',str(h.root),str(path),'--pause','after_formula'],start_new_session=True)
                processes.append(process);end=time.monotonic()+15
                while not marker.exists() and process.poll() is None and time.monotonic()<end:time.sleep(.02)
                self.assertTrue(marker.exists());os.killpg(process.pid,signal.SIGKILL);process.wait(timeout=5)
                self.assertEqual(process.returncode,-signal.SIGKILL)
            h.reopen()
            with self.assertRaises(ContractError) as error:h.beliefs.submitEvidence(request)
            self.assertEqual(error.exception.code,'OVERLOADED');self.assertIsNone(h.beliefs.observeDecision(request))
            self.assertEqual(h.beliefs.readBelief(claim,CONTEXT,None)['revision'],1)
        finally:
            for process in processes:
                if process.poll() is None:os.killpg(process.pid,signal.SIGKILL);process.wait(timeout=5)

    def test_real_cas_conflict_is_a_new_bounded_attempt(self):
        import threading
        h=self.h;claim,_,_=h.prior();a=h.source()['evidence'];b=h.source('other-source')['evidence']
        ra=h.assessment(claim,a);rb=h.assessment(claim,b,key='other-assessment',sign=False)
        request=h.request(claim,ra);other=h.request(claim,rb,key='concurrent',assume=False)
        reached,release=threading.Event(),threading.Event();results=[]
        def hook(stage):
            if stage=='after_formula':reached.set();self.assertTrue(release.wait(15))
        h.hook=hook;h.reopen()
        def work():
            try:results.append(h.beliefs.submitEvidence(request))
            except ContractError as e:results.append(e.code)
        thread=threading.Thread(target=work);thread.start()
        try:
            self.assertTrue(reached.wait(15));second=h.beliefs.submitEvidence(other);self.assertEqual(second['numerical'],'retained-alternative')
        finally:release.set();thread.join(15)
        self.assertEqual(results,['CONFLICT'])
        with self.assertRaises(ContractError):h.beliefs.submitEvidence(replace(request,expected_revision=2))
        h.hook=lambda _:None;h.reopen()
        new=replace(request,command=Mutation(SCOPE,'new-cas-attempt'),expected_revision=2)
        self.assertEqual(h.beliefs.submitEvidence(new)['numerical'],'revised')
