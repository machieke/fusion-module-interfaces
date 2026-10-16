"""Real DeTTa and pinned native PLN; generated inputs and injected timing/receipt faults."""
from dataclasses import replace
import copy
import time
import unittest
from unittest.mock import patch
from fusion.contracts import ContractError,canonical,digest
from fusion.ports import Mutation,Stimulus,FeedbackIntent
from fusion.cognition import CognitionAccess,select
from fusion.policy import Policy
from fusion.registry import descriptor_read
from fusion.adapters.pln_deduction import DeductionRuntime
from tests.m3_1_support import ClosureHarness,SCOPE
from tests import test_m3_1_delivery as delivery_tests
from integration.m3_scenario import run_generated

def feedback(h):
    selected=select([descriptor_read(d) for d in h.config['cognition_descriptors']],'attention',closure=True)
    access=CognitionAccess(Policy(h.path),h.credential,selected,'feedback')
    if h.provider=='sqlite':
        from fusion.attention import AttentionOwner
        return AttentionOwner(h.modules.root/'attention.sqlite',access,h.config['attention_policy'],closure=True)
    from fusion.adapters.fixture_attention import FileAttentionFixture
    return FileAttentionFixture(h.modules.root/'attention.json',access,h.config['attention_policy'],closure=True)

class NativeClosure(unittest.TestCase):
    def test_real_33_events_backpressure_drain_and_reopen(self):delivery_tests.DeliveryTests().run_batches(real=True)

    def test_actual_m3_path_and_deduction_ledger_receipts(self):
        h=ClosureHarness(real=True)
        try:
            result=run_generated(h.modules,SCOPE,'native-closure',42,'b',int(time.time()*1000)+120000)
            self.assertEqual(result['result']['counts']['unique_admissions'],1)
            self.assertEqual(h.episodes.pendingEvidence(result['episode'],16),())
            claim=result['roles'][1]['pr'];before=h.beliefs.readBelief(claim,result['context'],None)
            self.assertEqual(before['supports'][0]['kind'],'deduction')
            # New observation on a ledger already containing deduction must validate the full v3 snapshot.
            event=h.event(claim,'contrary',strength='0.1',context=result['context'])
            h.append(result['episode'],event,12)
            receipt=h.modules.relay.drain(result['episode'])[0]
            self.assertEqual(receipt['numerical'],'retained-alternative')
            self.assertTrue(any(s['kind']=='deduction' for s in receipt['snapshot']['supports']))
            self.assertEqual(len(receipt['snapshot']['observations']),1)
            self.assertEqual(h.episodes.pendingEvidence(result['episode'],16),())
        finally:h.close()

    def test_terminal_reconciliation_malformed_unavailable_revoke_and_no_new_work(self):
        outcomes=[]
        for provider in ('sqlite','atomic-file-fixture'):
            with self.subTest(provider=provider):
                h=ClosureHarness(real=True,provider=provider)
                try:
                    entry,roles,_=h.generated();h.stimulate(entry)
                    request=h.request(h.workset([entry]),candidates=1,deadline=int(time.time()*1000)+120000)
                    fired=[]
                    def hook(stage):
                        if stage=='after_derived_commit' and not fired:
                            fired.append(stage);h.attention.advance(Mutation(SCOPE,'advance'),'generated',0,1)
                    h.hook=hook;h.reopen()
                    original=DeductionRuntime.evaluate;calls=[]
                    def counted(runtime,*args):calls.append(1);return original(runtime,*args)
                    with patch.object(DeductionRuntime,'evaluate',counted):
                        execution=h.controller.step(request)
                        self.assertEqual(execution['status'],'complete');self.assertEqual(execution['reason'],'feedback-unavailable')
                        self.assertEqual(execution['counts']['reserved'],1);self.assertEqual(calls,[1])
                        before=h.controller.readProgress(request);self.assertEqual(before['closure']['counts']['pending'],1)
                        real=h.controller.attention
                        class Fault:
                            def resolveFeedback(self,intent):return {'outcome':'retired'}
                        h.controller.attention=Fault()
                        malformed=h.controller.reconcile(Mutation(SCOPE,'bad-receipt'),request,1)
                        self.assertEqual(malformed['feedback'][0]['reason'],'NOT_AVAILABLE')
                        class Down:
                            def resolveFeedback(self,intent):raise ContractError('NOT_AVAILABLE')
                        h.controller.attention=Down()
                        unavailable=h.controller.reconcile(Mutation(SCOPE,'down'),request,1)
                        self.assertEqual(unavailable['closure']['counts']['pending'],1)
                        h.controller.attention=real
                        h.config['principals']['owner']['scopes'][SCOPE].remove('attention.resolveFeedback');h.save()
                        with self.assertRaises(ContractError):h.controller.readProgress(request)
                        with self.assertRaises(ContractError):h.controller.reconcile(Mutation(SCOPE,'bad-receipt'),request,1)
                        h.config['principals']['owner']['scopes'][SCOPE].append('attention.resolveFeedback');h.save()
                        result=h.controller.reconcile(Mutation(SCOPE,'settle'),request,1)
                        self.assertEqual(result['closure']['counts']['retired'],1)
                        self.assertEqual(result['feedback'][0]['reason'],'obsolete-step')
                        self.assertEqual(result['execution'],execution);self.assertEqual(calls,[1])
                        self.assertEqual(h.controller.step(request),execution)
                        h.reopen();self.assertEqual(h.controller.reconcile(Mutation(SCOPE,'settle'),request,1),result)
                        with self.assertRaises(ContractError):h.controller.reconcile(Mutation(SCOPE,'settle'),request,2)
                        with self.assertRaises(ContractError):h.controller.reconcile(Mutation(SCOPE,'changed'),replace(request,budget=replace(request.budget,deadline_ms=request.budget.deadline_ms+1)),1)
                        for limit in (0,17,True):
                            with self.assertRaises(ContractError):h.controller.reconcile(Mutation(SCOPE,'limit'),request,limit)
                        self.assertEqual(h.attention.readAttention(entry['task'],'generated')['value']['sti'],'9')
                        self.assertEqual(len(h.beliefs.readBelief(roles['pr'],'generated',None)['supports']),1)
                        outcomes.append((result['closure'],execution['counts'],execution['remaining'],len(calls)))
                finally:h.close()
        self.assertEqual(*outcomes)

    def test_applied_receipt_after_deadline_and_decay_execution_stays_immutable(self):
        for provider in ('sqlite','atomic-file-fixture'):
            with self.subTest(provider=provider):
                h=ClosureHarness(real=True,provider=provider)
                try:
                    entry,_,_=h.generated();h.stimulate(entry);request=h.request(h.workset([entry]),candidates=1,deadline=int(time.time()*1000)+120000)
                    real=h.controller.attention
                    class Lost:
                        def profile(self):return real.profile()
                        def select(self,*args):return real.select(*args)
                        def submitFeedback(self,intent):real.submitFeedback(intent);raise ContractError('NOT_AVAILABLE')
                        def resolveFeedback(self,intent):return real.resolveFeedback(intent)
                    h.controller.attention=Lost();execution=h.controller.step(request)
                    self.assertEqual(execution['reason'],'feedback-unavailable')
                    h.attention.advance(Mutation(SCOPE,'decay'),'generated',0,16)
                    with patch('time.time',return_value=(request.budget.deadline_ms+1)/1000),patch.object(DeductionRuntime,'evaluate',side_effect=AssertionError('new native work')):
                        progress=h.controller.reconcile(Mutation(SCOPE,'after-expiry'),request,1)
                        self.assertEqual(progress['closure']['counts']['applied'],1)
                        self.assertEqual(progress['feedback'][0]['receipt']['applied'],'1')
                        self.assertEqual(progress['execution'],execution)
                        self.assertEqual(h.controller.step(request),execution)
                    self.assertEqual(h.attention.readAttention(entry['task'],'generated')['value']['sti'],'0')
                finally:h.close()

    def test_eligible_feedback_remains_pending_until_owner_retires_at_expiry(self):
        for provider in ('sqlite','atomic-file-fixture'):
            with self.subTest(provider=provider):
                h=ClosureHarness(real=True,provider=provider)
                try:
                    entry,_,_=h.generated();h.stimulate(entry);request=h.request(h.workset([entry]),candidates=1,deadline=int(time.time()*1000)+120000)
                    real=h.controller.attention
                    class Down:
                        def profile(self):return real.profile()
                        def select(self,*args):return real.select(*args)
                        def submitFeedback(self,intent):raise ContractError('NOT_AVAILABLE')
                    h.controller.attention=Down();execution=h.controller.step(request);h.controller.attention=real
                    with patch.object(DeductionRuntime,'evaluate',side_effect=AssertionError('new inference')):
                        pending=h.controller.reconcile(Mutation(SCOPE,'eligible'),request,1)
                        self.assertEqual(pending['feedback'][0]['reason'],'eligible')
                        self.assertEqual(h.attention.readAttention(entry['task'],'generated')['value']['sti'],'10')
                        with patch('time.time',return_value=(request.budget.deadline_ms+1)/1000):
                            retired=h.controller.reconcile(Mutation(SCOPE,'expired'),request,1)
                        self.assertEqual(retired['feedback'][0]['reason'],'expired')
                        self.assertEqual(retired['execution'],execution)
                        # Exact replay is an observation at its original version; readProgress is current.
                        self.assertEqual(h.controller.reconcile(Mutation(SCOPE,'eligible'),request,1),pending)
                        self.assertEqual(h.controller.readProgress(request),retired)
                        self.assertEqual(h.attention.readAttention(entry['task'],'generated')['value']['sti'],'10')
                finally:h.close()

if __name__=='__main__':unittest.main()
