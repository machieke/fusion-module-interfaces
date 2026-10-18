"""Both local Attention providers, real pinned math, opaque targets only."""
import copy
import json
import multiprocessing
import os
from pathlib import Path
import signal
import tempfile
import threading
import time
import unittest
import uuid
from fusion import promotion_contracts as c
from fusion.contracts import canonical,ContractError
from fusion.registry import descriptor_wire
from fusion.promotion_composition import Access,descriptor,PortOnly
from fusion.promotion import PromotionOwner
from fusion.adapters.file_promotion import FilePromotion
from fusion.adapters.native_promotion import NativePromotion

ROOT=Path(__file__).resolve().parents[2]
RUNTIME=ROOT/'artifacts/s01/native-02/runtime.json'
OUT=Path(os.environ.get('S05_EVIDENCE',ROOT/'artifacts/s05/tests'))

class Harness:
    def __init__(self,kind):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.kind=kind;self.now=2000000000.
        self.policy=self.root/'policy.json';self.d=descriptor(kind)
        self.cfg=dict(profile=c.PROFILE,placement='local',privacy='private-local-only',scopes={'s':'A'},catalogue=[descriptor_wire(self.d)],
            principals={'A':dict(credential='generated-test-A',scopes={'s':['attention.'+x for x in c.OPERATIONS]})})
        self.save();self.access=Access(self.policy,'generated-test-A');self.math=NativePromotion(RUNTIME);self.hook=lambda _:None
        self.target=str(uuid.uuid5(uuid.NAMESPACE_URL,'s05-opaque-target'));self.counter=0
    def save(self):self.policy.write_bytes(canonical(self.cfg))
    def owner(self):
        cls=PromotionOwner if self.kind=='sqlite' else FilePromotion
        return PortOnly(cls(self.root/('state.sqlite' if self.kind=='sqlite' else 'state.json'),self.access,self.math,clock=lambda:self.now,hook=self.hook))
    def request(self,kind='adjust',targets=None,delta=1,deadline=None,id=None):
        self.counter+=1
        return c.request(dict(profile=c.PROFILE,selection=self.access.selection(),principal='A',scope='s',context='opaque',id=id or str(self.counter),
            kind=kind,targets=[self.target] if targets is None else targets,delta=delta if kind=='adjust' else 0,limit=1 if kind=='adjust' else 10,
            deadline_ms=deadline or int(time.time()*1000)+30000))
    def adjust(self,delta=1):
        o=self.owner();b=o.bind(self.request(delta=delta));return c.receipt(o.adjust(b),b)
    def close(self):self.tmp.cleanup()


def killed(root,kind,request,stage):
    path=Path(root);access=Access(path/'policy.json','generated-test-A')
    def hook(where):
        if where==stage:os.kill(os.getpid(),signal.SIGKILL)
    cls=PromotionOwner if kind=='sqlite' else FilePromotion
    owner=cls(path/('state.sqlite' if kind=='sqlite' else 'state.json'),access,NativePromotion(RUNTIME),clock=lambda:2000000000.,hook=hook)
    owner.adjust(owner.bind(request))

class PromotionOwners(unittest.TestCase):
    def each(self):
        for kind in ('sqlite','file-fixture'):
            h=Harness(kind);self.addCleanup(h.close);yield h
    def evidence(self,name,value):OUT.mkdir(parents=True,exist_ok=True);(OUT/(name+'.json')).write_bytes(canonical(value))
    def test_native_policy_domain_caps_floor_decay_and_order(self):
        math=NativePromotion(RUNTIME);cases=[(0,0,0,0),(1,7.25,7.25,0),(1,0,86400,0),(10,0,8640000.5,0),(10,0,0,1),(0,0,0,-1),(3,0,0,-1)]
        values=math.evaluate(cases,int(time.time()*1000)+10000)
        for (v,last,t,delta),actual in zip(cases,values):
            score=v*(1+(t-last)/86400.)**(-.7);expected=min(10.,score+1) if delta==1 else max(0.,score-1) if delta==-1 else score
            self.assertAlmostEqual(expected,actual,places=14)
        for bad in (float('nan'),float('inf'),-1,10**10000,True,'(+ 1 1)'):
            with self.assertRaises(ContractError):math.evaluate([[bad,0,1,0]],int(time.time()*1000)+10000)
        self.evidence('native-policy',dict(cases=cases,values=values,production='pinned source expressions under PeTTa, no NAL import'))
    def test_same_policy_independent_replay_and_intent(self):
        traces=[]
        for h in self.each():
            values=[]
            for delta in [1,1,-1]+[1]*11+[-1]*12:
                r=h.adjust(delta);values.append(r['value']);self.assertEqual(h.owner().observe(r['binding']),r)
                self.assertEqual(h.owner().adjust(r['binding']),r)
            self.assertEqual(values[:3],[1.,2.,1.]);self.assertEqual(max(values),10.);self.assertEqual(values[-1],0.)
            changed=copy.deepcopy(r['binding']);changed['request']['delta']=1
            with self.assertRaises(ContractError):h.owner().adjust(changed)
            traces.append(dict(provider=h.kind,values=values,final_revision=r['revision']))
        self.assertEqual(traces[0]['values'],traces[1]['values']);self.evidence('owner-substitution',traces)
    def test_historical_reads_clock_rollback_and_missing_binding(self):
        for h in self.each():
            r=h.adjust();o=h.owner();request=h.request('scores');b=o.bind(request)
            h.now+=86400.;h.adjust();old=c.result(o.scores(b),b);self.assertEqual(old['scores'][0]['score'],1.)
            h.now-=86401.
            with self.assertRaises(ContractError):o.bind(h.request())
            self.assertEqual(o.scores(b),old)
            missing=copy.deepcopy(b);missing['request']['id']='missing'
            with self.assertRaises(ContractError):o.scores(missing)
    def test_global_ties_positive_filter_zero_and_candidate_correspondence(self):
        for h in self.each():
            zero=str(uuid.uuid4());a=h.target;b=str(uuid.uuid4());o=h.owner()
            for target in (a,b):o.adjust(o.bind(h.request(targets=[target])))
            bound=o.bind(h.request('rank',targets=[b,zero,a]));result=c.result(o.rank(bound),bound)
            self.assertEqual(result['selected'],sorted([a,b]));self.assertEqual([r['target'] for r in result['scores']],[b,zero,a])
            bound=o.bind(h.request('scores',targets=[zero]));self.assertEqual(o.scores(bound)['scores'],[dict(target=zero,score=0.)])
            bound=o.bind(h.request('rank',targets=[]));self.assertEqual(o.rank(bound)['selected'],[])
    def test_live_authority_profile_scope_and_reply_validation(self):
        for h in self.each():
            o=h.owner();r=h.adjust();b=r['binding']
            for key,val in [('scope','other'),('principal','B'),('profile','sti-additive-linear-decay/1'),('selection','wrong')]:
                q=h.request();q[key]=val
                with self.assertRaises(ContractError):o.bind(q)
            h.cfg['principals']['A']['scopes']['s']=[];h.save()
            for fn in (lambda:o.observe(b),lambda:o.adjust(b),lambda:o.bind(h.request())):
                with self.assertRaises(ContractError):fn()
            for mutate in (lambda x:x.update(value=float('nan')),lambda x:x.update(revision=999),lambda x:x.update(target=str(uuid.uuid4()))):
                wrong=copy.deepcopy(r);mutate(wrong)
                with self.assertRaises(ContractError):c.receipt(wrong,b)
    def test_revocation_after_real_native_evaluation_no_commit(self):
        for h in self.each():
            def hook(stage):
                if stage=='after_priority_evaluation':h.cfg['principals']['A']['scopes']['s']=[];h.save()
            h.hook=hook;o=h.owner();b=o.bind(h.request())
            with self.assertRaises(ContractError):o.adjust(b)
            h.cfg['principals']['A']['scopes']['s']=['attention.'+x for x in c.OPERATIONS];h.save()
            self.assertIsNone(o.observe(b))
    def test_concurrent_cas_exactly_one_commit(self):
        for h in self.each():
            o=h.owner();bindings=[o.bind(h.request()) for _ in range(2)];barrier=threading.Barrier(2);results=[]
            def run(b):
                barrier.wait()
                try:results.append(o.adjust(b))
                except ContractError as e:results.append(e.code)
            workers=[threading.Thread(target=run,args=(b,)) for b in bindings]
            for t in workers:t.start()
            for t in workers:t.join(10)
            self.assertEqual(sum(type(x) is dict for x in results),1);self.assertIn('CONFLICT',results)
    def test_expiry_observes_committed_refuses_new_and_missing_read(self):
        for h in self.each():
            o=h.owner();b=o.bind(h.request(deadline=int(time.time()*1000)+1000));r=o.adjust(b)
            read=o.bind(h.request('scores',deadline=int(time.time()*1000)+1000));time.sleep(1.05)
            self.assertEqual(o.adjust(b),r);self.assertEqual(o.observe(b),r)
            with self.assertRaises(ContractError):o.scores(read)
            with self.assertRaises(ContractError):o.bind(h.request(deadline=int(time.time()*1000)-1))
    def test_capacity_without_silent_eviction(self):
        for h in self.each():
            o=h.owner();first=o.bind(h.request('scores'))
            for _ in range(c.MAX_BINDINGS-1):o.bind(h.request('scores'))
            with self.assertRaises(ContractError):o.bind(h.request())
            self.assertEqual(o.bind(first['request']),first)
            with self.assertRaises(ContractError):c.targets([str(uuid.uuid4()) for _ in range(c.MAX_TARGETS+1)])
    def test_real_process_kills_atomic_receipt_time_and_spent_budget(self):
        traces=[]
        for h in self.each():
            for stage in ('after_priority_clock','after_priority_evaluation','after_priority_commit'):
                q=h.request();p=multiprocessing.Process(target=killed,args=(str(h.root),h.kind,q,stage));p.start();p.join(15)
                self.assertEqual(p.exitcode,-signal.SIGKILL);o=h.owner();b=o.bind(q);r=o.adjust(b)
                self.assertEqual(r['time'],2000000000.);self.assertEqual(r,o.observe(b));traces.append(dict(provider=h.kind,stage=stage,receipt=r))
            q=h.request()
            for _ in range(c.MAX_EVALUATIONS):
                p=multiprocessing.Process(target=killed,args=(str(h.root),h.kind,q,'after_priority_evaluation'));p.start();p.join(15);self.assertEqual(p.exitcode,-signal.SIGKILL)
            o=h.owner();b=o.bind(q);self.assertIsNone(o.observe(b))
            with self.assertRaises(ContractError) as e:o.adjust(b)
            self.assertEqual(e.exception.code,'OVERLOADED')
        self.evidence('owner-kills',traces)

if __name__=='__main__':unittest.main()
