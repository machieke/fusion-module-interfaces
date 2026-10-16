"""Same closure contract, independent SQLite and file transitions; clock/fault fixtures."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
from fusion.attention import AttentionOwner
from fusion.adapters.fixture_attention import FileAttentionFixture
from fusion import attention_contracts as c
from fusion.contracts import ContractError
from fusion.ports import Stimulus,Mutation,FeedbackIntent
from tests.test_m3_attention import Authority,ref

PROVIDERS=(AttentionOwner,FileAttentionFixture)
class AttentionClosure(unittest.TestCase):
    def exercise(self,provider,mode):
        with tempfile.TemporaryDirectory() as root:
            access=Authority();path=Path(root)/'owner';owner=provider(path,access,closure=True)
            ingress=Stimulus(Mutation('private','ingress'),'ctx',ref('a'),'10','parent',0,owner.policy,0,'ingress')
            owner.submitStimulus(ingress)
            for malformed in (None,{},False):
                with self.assertRaises(ContractError):owner.submitStimulus(malformed)
                with self.assertRaises(ContractError):owner.resolveFeedback(malformed)
            request=replace(ingress,command=Mutation('private','feedback'),amount='1',cause='child',kind='feedback',generation=1,parent='parent')
            intent=FeedbackIntent(request,int(time.time()*1000)+60000)
            self.assertEqual(owner.resolveFeedback(intent)['outcome'],'pending')
            if mode=='applied':
                receipt=owner.submitFeedback(intent)
                owner.advance(Mutation('private','advance'),'ctx',0,1)
            elif mode=='clock':owner.advance(Mutation('private','advance'),'ctx',0,1)
            elif mode=='parent':owner.submitFeedback(replace(intent,stimulus=replace(request,command=Mutation('private','sibling'),cause='sibling')))
            with patch('time.time',return_value=(intent.effect_deadline_ms+1)/1000) if mode in ('applied','expired') else patch('time.time',wraps=time.time):
                outcome=owner.resolveFeedback(intent);c.resolution(outcome,intent,owner.parameters)
                if mode=='applied':self.assertEqual(outcome['receipt'],receipt)
                else:self.assertEqual(outcome['outcome'],'retired')
                self.assertEqual(provider(path,access,closure=True).resolveFeedback(intent),outcome)
                late=replace(intent,stimulus=replace(request,command=Mutation('private','delayed')))
                if mode=='applied':self.assertEqual(owner.submitFeedback(late),receipt)
                else:
                    with self.assertRaises(ContractError):owner.submitFeedback(late)
                for changed in (replace(intent,effect_deadline_ms=intent.effect_deadline_ms+1),replace(intent,stimulus=replace(request,amount='2'))):
                    with self.assertRaises(ContractError):owner.resolveFeedback(changed)
                access.allowed=False
                with self.assertRaises(ContractError):owner.resolveFeedback(intent)
            return outcome,owner.parameters

    def test_same_profile_applied_expired_clock_and_parent(self):
        for mode in ('applied','expired','clock','parent'):
            with self.subTest(mode=mode):
                # Wall deadlines differ, so compare semantics except intent fingerprint.
                results=[self.exercise(p,mode)[0] for p in PROVIDERS]
                for r in results:r.pop('intent_digest')
                self.assertEqual(*results)

    def test_serialized_race_orders_and_concurrent_delivery(self):
        for provider in PROVIDERS:
            for first in ('apply','retire','concurrent'):
                with self.subTest(provider=provider.__name__,first=first),tempfile.TemporaryDirectory() as root:
                    path=Path(root)/'state';owner=provider(path,Authority(),closure=True)
                    ingress=Stimulus(Mutation('private','i'),'ctx',ref('a'),'10','parent',0,owner.policy,0,'ingress');owner.submitStimulus(ingress)
                    request=replace(ingress,command=Mutation('private','f'),amount='1',cause='child',kind='feedback',generation=1,parent='parent')
                    intent=FeedbackIntent(request,2000)
                    def apply():
                        try:return provider(path,Authority(),closure=True).submitFeedback(intent)
                        except ContractError as e:return e.code
                    def retire():return provider(path,Authority(),closure=True).resolveFeedback(intent)
                    if first=='apply':
                        with patch('time.time',return_value=1):apply()
                        with patch('time.time',return_value=3):outcome=retire()
                        self.assertEqual(outcome['outcome'],'applied')
                    elif first=='retire':
                        with patch('time.time',return_value=3):outcome=retire()
                        with patch('time.time',return_value=1):self.assertEqual(apply(),'CONFLICT')
                        self.assertEqual(outcome['outcome'],'retired')
                    else:
                        # Race eligible application against a clock advance followed by retirement.
                        # Both contenders use independent facade instances and the same owner lock.
                        def advance_and_retire():
                            other=provider(path,Authority(),closure=True)
                            other.advance(Mutation('private','race-clock'),'ctx',0,1)
                            return other.resolveFeedback(intent)
                        with patch('time.time',return_value=1),ThreadPoolExecutor(2) as pool:
                            futures=[pool.submit(apply),pool.submit(advance_and_retire)];values=[f.result() for f in futures]
                        outcome=values[1];self.assertIn(outcome['outcome'],('applied','retired'))
                        if outcome['outcome']=='applied':self.assertEqual(values[0],outcome['receipt'])
                        else:self.assertEqual(values[0],'CONFLICT')
                        delayed=replace(intent,stimulus=replace(request,command=Mutation('private','race-delayed')))
                        if outcome['outcome']=='retired':
                            with self.assertRaises(ContractError):owner.submitFeedback(delayed)
                        else:self.assertEqual(owner.submitFeedback(delayed),outcome['receipt'])
                    with patch('time.time',return_value=3):self.assertEqual(retire(),outcome)
                    expected=('10' if outcome['outcome']=='applied' else '9') if first=='concurrent' else ('11' if first=='apply' else '10')
                    self.assertEqual(owner.readAttention(ref('a'),'ctx')['value']['sti'],expected)

    def test_capacity_is_pending_then_obsolete_without_credit_or_eviction(self):
        for provider in PROVIDERS:
            with self.subTest(provider=provider.__name__),tempfile.TemporaryDirectory() as root:
                owner=provider(Path(root)/'state',Authority(),closure=True)
                for name in ('a','b','c'):
                    owner.submitStimulus(Stimulus(Mutation('private',name),'ctx',ref(name),'100',name,0,owner.policy,0,'ingress'))
                # A saturated target awards zero; fill global capacity while target a is below its max instead.
                # A separate policy fixture expresses that transient budget conflict without changing production limits.
                params={**c.DEFAULT_POLICY,'budget':'100'}
                limited=provider(Path(root)/'limited',Authority(),params,closure=True)
                for name,amount in [('a','50'),('b','50')]:limited.submitStimulus(Stimulus(Mutation('private',name),'ctx',ref(name),amount,name,0,limited.policy,0,'ingress'))
                req=Stimulus(Mutation('private','f'),'ctx',ref('a'),'1','child',1,limited.policy,0,'feedback','a')
                intent=FeedbackIntent(req,int(time.time()*1000)+60000)
                with self.assertRaises(ContractError):limited.submitFeedback(intent)
                self.assertEqual(limited.resolveFeedback(intent)['outcome'],'pending')
                limited.advance(Mutation('private','tick'),'ctx',0,1)
                self.assertEqual(limited.resolveFeedback(intent)['reason'],'obsolete-step')
                self.assertEqual(limited.readAttention(ref('a'),'ctx')['value']['sti'],'49')
                bounded=provider(Path(root)/'bounded',Authority(),{**c.DEFAULT_POLICY,'max_causes':1},closure=True)
                bounded.submitStimulus(Stimulus(Mutation('private','a'),'ctx',ref('a'),'1','a',0,bounded.policy,0,'ingress'))
                full=FeedbackIntent(replace(req,policy=bounded.policy),1)
                with self.assertRaises(ContractError) as error:bounded.resolveFeedback(full)
                self.assertEqual(error.exception.code,'NOT_AVAILABLE')
                self.assertEqual(bounded.readAttention(ref('a'),'ctx')['value']['sti'],'1')

if __name__=='__main__':unittest.main()
