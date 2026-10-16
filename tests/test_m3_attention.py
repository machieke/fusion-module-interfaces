"""No graph, DA, belief, PLN, Hive or native runtime is loaded by this suite."""
from dataclasses import replace
import tempfile
from pathlib import Path
import unittest
from fusion.attention import AttentionOwner
from fusion.adapters.fixture_attention import FileAttentionFixture
from fusion import attention_contracts as c
from fusion.contracts import ContractError, digest, require
from fusion.ports import Mutation, Stimulus
from tests.m2_support import PortOnly

class Authority:
    def __init__(self,role='all'): self.allowed=True;self.role=role
    def authorize(self,scope,operation):
        require(self.allowed and scope=='private','UNAUTHORIZED')
        require(operation not in ('feedback','ingress') or self.role in ('all',operation),'UNAUTHORIZED')
        return 'operator'
    def selection(self): return 'attention-test-binding/1'

def ref(name): return {'scope_ref':'private','id':name,'revision':1,'digest':digest(name.encode())}

class AttentionTests(unittest.TestCase):
    def run_case(self, provider):
        with tempfile.TemporaryDirectory() as root:
            access=Authority();parameters={**c.DEFAULT_POLICY,'s_max':'10','budget':'15','decay':'2','max_targets':3}
            path=Path(root)/'state';factory=lambda:provider(path,access,parameters)
            owner=factory();port=PortOnly(owner,('profile','submitStimulus','readAttention','select','advance'))
            policy=port.profile()['policy'];a,b=ref('a'),ref('b')
            def stimulus(key,target=a,amount='8',cause=None,**kw):
                return Stimulus(Mutation('private',key),'ctx',target,amount,cause or key,kw.pop('generation',0),policy,kw.pop('expected_step',0),kw.pop('kind','ingress'),kw.pop('parent',None))
            first=stimulus('first');r=port.submitStimulus(first);c.receipt(r,first,parameters)
            self.assertEqual(port.submitStimulus(replace(first,command=Mutation('private','retry'))),r)
            with self.assertRaises(ContractError):port.submitStimulus(replace(first,amount='9',command=Mutation('private','wrong')))
            with self.assertRaises(ContractError):port.submitStimulus(stimulus('over-budget',b,'8'))
            port.submitStimulus(stimulus('b',b,'7'))
            snapshot=port.select('private','ctx',(b,a),2);c.selection(snapshot,'private','ctx',(b,a),2,parameters)
            self.assertEqual([x['target'] for x in snapshot['ranked']],[a,b])
            self.assertEqual(port.select('private','other',(a,b),2)['ranked'],[])
            advance=port.advance(Mutation('private','clock'),'ctx',0,2)
            self.assertEqual(port.submitStimulus(first),r)
            with self.assertRaises(ContractError):port.submitStimulus(stimulus('late'))
            feedback=stimulus('f1',amount='1',kind='feedback',generation=1,parent='first',expected_step=2)
            port.submitStimulus(feedback)
            port.advance(Mutation('private','clock2'),'ctx',2,10)
            port.submitStimulus(stimulus('new-ingress',expected_step=12))
            self.assertEqual(port.readAttention(a,'ctx')['value']['generation'],1)
            result=factory().select('private','ctx',(a,b),2)
            self.assertEqual(result,port.select('private','ctx',(a,b),2))
            self.assertEqual(factory().advance(Mutation('private','clock'),'ctx',0,2),advance)
            access.allowed=False
            with self.assertRaises(ContractError):factory().submitStimulus(first)
            with self.assertRaises(ContractError):port.select('private','ctx',(a,),1)
            access.allowed=True
            with self.assertRaises(ContractError):provider(path,access,{**parameters,'decay':'3'})
            return result

    def test_independent_same_profile_replacement(self):
        self.assertEqual(self.run_case(AttentionOwner),self.run_case(FileAttentionFixture))

    def test_roles_ties_saturation_and_closed_inputs(self):
        for provider in (AttentionOwner,FileAttentionFixture):
            with self.subTest(provider=provider.__name__),tempfile.TemporaryDirectory() as root:
                access=Authority('ingress');owner=provider(Path(root)/'state',access)
                def request(key,target,amount='100'):
                    return Stimulus(Mutation('private',key),'ctx',target,amount,key,0,owner.policy,0,'ingress')
                b,a=ref('b'),ref('a');owner.submitStimulus(request('b',b));owner.submitStimulus(request('a',a))
                self.assertEqual([x['target'] for x in owner.select('private','ctx',(b,a),2)['ranked']],sorted((a,b),key=c.target_key))
                self.assertEqual(owner.submitStimulus(request('saturated',a))['applied'],'0')
                for amount in ('-1','01','1.0',1,True,'10000000000000000'):
                    with self.assertRaises(ContractError):owner.submitStimulus(request('bad',a,amount))
                with self.assertRaises(ContractError):owner.submitStimulus(replace(request('feedback',a),kind='feedback',generation=1,parent='a'))
                with self.assertRaises(ContractError):owner.select('private','ctx',(a,a),1)

    def test_capacity_rejects_without_eviction(self):
        for provider in (AttentionOwner,FileAttentionFixture):
            with self.subTest(provider=provider.__name__),tempfile.TemporaryDirectory() as root:
                owner=provider(Path(root)/'state',Authority(),{**c.DEFAULT_POLICY,'max_commands':1})
                r=Stimulus(Mutation('private','first'),'ctx',ref('a'),'1','cause',0,owner.policy,0,'ingress')
                receipt=owner.submitStimulus(r)
                with self.assertRaises(ContractError):owner.submitStimulus(replace(r,command=Mutation('private','second')))
                self.assertEqual(owner.submitStimulus(r),receipt)
                self.assertEqual(owner.readAttention(ref('a'),'ctx')['value']['sti'],'1')

    def test_causal_generation_never_resets_across_decay_ingress_or_keys(self):
        for provider in (AttentionOwner,FileAttentionFixture):
            with self.subTest(provider=provider.__name__),tempfile.TemporaryDirectory() as root:
                owner=provider(Path(root)/'state',Authority(),{**c.DEFAULT_POLICY,'max_feedback_generation':2})
                first=Stimulus(Mutation('private','ingress'),'ctx',ref('a'),'1','z-ingress',0,owner.policy,0,'ingress')
                owner.submitStimulus(first)
                f1=replace(first,command=Mutation('private','f1'),cause='f1',kind='feedback',generation=1,parent='z-ingress')
                owner.submitStimulus(f1)
                with self.assertRaises(ContractError):owner.submitStimulus(replace(f1,command=Mutation('private','branch'),cause='branch'))
                f2=replace(f1,command=Mutation('private','f2'),cause='f2',generation=2,parent='f1')
                owner.submitStimulus(f2);owner.advance(Mutation('private','decay'),'ctx',0,10)
                owner.submitStimulus(replace(first,command=Mutation('private','reset'),cause='a-new-ingress',expected_step=10))
                self.assertEqual(owner.readAttention(ref('a'),'ctx')['value']['generation'],2)
                with self.assertRaises(ContractError):owner.submitStimulus(replace(f2,command=Mutation('private','f3'),cause='f3',generation=3,parent='f2',expected_step=10))
                self.assertEqual(owner.submitStimulus(replace(f2,command=Mutation('private','redeliver'))),owner.submitStimulus(f2))

    def test_mutable_caller_dictionary_cannot_change_admitted_stimulus(self):
        for provider in (AttentionOwner,FileAttentionFixture):
            with self.subTest(provider=provider.__name__),tempfile.TemporaryDirectory() as root:
                access=Authority();owner=provider(Path(root)/'state',access)
                original=ref('a');request=Stimulus(Mutation('private','mutable'),'ctx',dict(original),'3','cause',0,owner.policy,0,'ingress')
                authorize=access.authorize
                def mutate(scope,operation):
                    request.target['id']='mutated-after-validation'
                    return authorize(scope,operation)
                access.authorize=mutate
                result=owner.submitStimulus(request)
                self.assertEqual(result['target'],original)
                self.assertEqual(owner.readAttention(original,'ctx')['value']['sti'],'3')

if __name__=='__main__':unittest.main()
