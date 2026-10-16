from dataclasses import replace
import unittest
from fusion.contracts import ContractError
from fusion.ports import Mutation
from tests.m3_support import CognitionHarness, SCOPE

class CognitionFixtures(unittest.TestCase):
    def test_refusing_kernel_budgets_replay_and_swap(self):
        outputs=[]
        for provider in ('sqlite','atomic-file-fixture'):
            h=CognitionHarness(provider=provider)
            try:
                a,_,_=h.generated('a');b,_,_=h.generated('b');h.stimulate(a,'10','a');h.stimulate(b,'20','b')
                request=h.request(h.workset([a,b]),attempts=1)
                result=h.controller.step(request)
                self.assertEqual(result['counts']['reserved'],1);self.assertEqual(result['counts']['refused'],1)
                self.assertEqual(result['results'][0]['task'],b['task']);self.assertEqual(result['reason'],'rule-budget')
                h.reopen();self.assertEqual(h.controller.step(request),result)
                with self.assertRaises(ContractError):h.controller.step(replace(request,budget=replace(request.budget,max_rule_applications=2)))
                outputs.append(result['counts'])
            finally:h.close()
        self.assertEqual(*outputs)

    def test_deadline_is_absolute_and_current_auth_applies_to_replay(self):
        h=CognitionHarness()
        try:
            a,_,_=h.generated();h.stimulate(a);request=h.request(h.workset([a]),deadline=1)
            result=h.controller.step(request);self.assertEqual(result['reason'],'deadline');self.assertEqual(result['counts']['reserved'],0)
            h.reopen();self.assertEqual(result,h.controller.step(request))
            h.config['principals']['owner']['scopes'][SCOPE].remove('inference.control.step');h.save()
            with self.assertRaises(ContractError):h.controller.step(request)
        finally:h.close()

    def test_unresolved_candidate_consumes_candidate_budget(self):
        h=CognitionHarness()
        try:
            a,_,_=h.generated();a['task']={**a['task'],'id':'unresolved'};h.stimulate(a)
            result=h.controller.step(h.request(h.workset([a]),candidates=1))
            self.assertEqual(result['counts']['examined'],1);self.assertEqual(result['counts']['reserved'],0)
            self.assertEqual(result['counts']['refused'],1)
        finally:h.close()

if __name__=='__main__':unittest.main()

class AdversarialContracts(unittest.TestCase):
    def test_malformed_selection_and_unavailable_belief_never_become_empty(self):
        from unittest.mock import patch
        h=CognitionHarness()
        try:
            a,_,_=h.generated();h.stimulate(a);request=h.request(h.workset([a]))
            class BadAttention:
                def profile(self):return h.attention.profile()
                def select(self,*args):return {'ranked':[]}
            h.controller.attention=BadAttention()
            with self.assertRaises(ContractError) as e:h.controller.step(request)
            self.assertEqual(e.exception.code,'NOT_AVAILABLE')
            h.reopen()
            class MissingBeliefs:
                def readBelief(self,*args):raise ContractError('NOT_AVAILABLE')
            h.controller.beliefs=MissingBeliefs();result=h.controller.step(request)
            self.assertEqual(result['reason'],'provider-unavailable');self.assertEqual(result['counts']['reserved'],0)
        finally:h.close()

    def test_descriptor_and_old_journal_incompatibility_fail_closed(self):
        from fusion.cognition import open_cognition
        from fusion.attention import AttentionOwner
        from tests.test_m3_attention import Authority
        h=CognitionHarness()
        try:
            a,_,_=h.generated();h.stimulate(a)
            h.config['cognition_descriptors'][0]['profiles']=['pln-revision-private/1'];h.save()
            with self.assertRaises(ContractError):h.reopen()
        finally:h.close()
