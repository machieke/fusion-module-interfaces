"""Read-only counters over actual SQLite; payload backend and clocks fixtures."""
import json,tempfile,unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from fusion.contracts import canonical,ContractError,require
from fusion.atom_feed import FeedAtomOwner
from fusion.ports import Mutation
from fusion.sustained_feed import PROFILE,METADATA_RESERVATION
from fusion.sustained_sessions import SustainedSessionStore
from integration.single_node.integrated_capacity import collect,bound
from tests.test_phase3_feed import FilePayloadFixture,SCOPE
from tests.test_phase3_sessions import policy

class Capacity(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.state=self.root/'state';self.run=self.root/'run';self.state.mkdir();self.run.mkdir()
    def config(self,role,value):
        (self.state/'owner-seal.json').write_bytes(canonical(dict(role=role)))
        (self.run/'owner.json').write_bytes(canonical(value))
    def test_bounds_preserve_unknown_and_reservations(self):
        self.assertEqual(bound('x',None,10)['state'],'UNKNOWN')
        self.assertIsNone(bound('x',None,10)['remaining'])
        self.assertEqual(bound('x',8,10,1)['state'],'HIGH_WATER')
        self.assertEqual(bound('x',8,10,2)['state'],'FULL')
        self.assertEqual(bound('x',11,10)['state'],'EXCEEDED')
        with self.assertRaises(ContractError):bound('x',True,10)
    def test_application_completion_reservation_survives_full_headroom(self):
        cfg=policy();self.config('omega-agent',dict(native_sessions=dict(allocation=cfg)))
        s=SustainedSessionStore(self.state/'session-inbox.sqlite',lambda *_:None,cfg,clock=lambda:1000)
        self.addCleanup(s.close);sid=s.allocate('A','one','shared')['session']
        before=collect(self.state,self.run);s.submit('A',sid,'one','pin synthetic','task')
        observed=collect(self.state,self.run);rows={x['category']:x for x in observed['bounds']}
        self.assertEqual(rows['application_logical_bytes']['reserved'],66560)
        self.assertEqual(rows['pending_inputs']['used'],1)
        self.assertFalse(observed['preflight_reserves']);self.assertEqual(observed,collect(self.state,self.run))
        s.next_input('A',sid);s.complete('A',sid,'one',dict(turn=1,projection='EXPLICIT_FIXTURE',occurrences=['fixture']))
        after={x['category']:x for x in collect(self.state,self.run)['bounds']}
        self.assertEqual(after['application_logical_bytes']['reserved'],0)
        self.assertEqual(after['retained_sessions']['used'],1)
    def test_concurrent_exact_limit_and_partial_acceptance_keep_identity_and_reads(self):
        cfg=dict(profile=PROFILE,records=2,bytes=3*METADATA_RESERVATION,scopes=[SCOPE])
        self.config('fusion-storage',{});memory=self.state/'memory';memory.mkdir()
        def owner(hook=lambda _:None):return FeedAtomOwner(memory/'feed.sqlite',FilePayloadFixture(memory/'payload'),SimpleNamespace(authorize=lambda *_:'A'),hook,capacity=cfg)
        owner()
        def partial(stage):
            if stage=='after_feed_backend_acceptance':raise InterruptedError('independent backend durable; feed publication missing')
        with self.assertRaises(InterruptedError):owner(partial).create(Mutation(SCOPE,'partial'),'text/plain',b'first')
        report=collect(self.state,self.run)
        self.assertEqual(report['uncertainty']['shared-scope-1-unpublished_reservations'],1)
        def submit(key):
            try:return owner().create(Mutation(SCOPE,key),'text/plain',key.encode())
            except ContractError as e:return e.code
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(submit,['one','two']))
        self.assertEqual(results.count('OVERLOADED'),1)
        full=collect(self.state,self.run);self.assertEqual(full['bounds'][0]['state'],'FULL')
        captured=owner().create(Mutation(SCOPE,'partial'),'text/plain',b'first')
        self.assertEqual(owner().get(captured['ref']).bytes,b'first')
        final=collect(self.state,self.run);self.assertEqual(final['bounds'][0],full['bounds'][0])
        self.assertEqual(final['bounds'][1],full['bounds'][1]);self.assertEqual(final['uncertainty']['shared-scope-1-unpublished_reservations'],0)
        self.assertNotIn(SCOPE,json.dumps(final))
    def test_missing_file_is_unknown_and_never_created(self):
        self.config('fusion-storage',{})
        value=collect(self.state,self.run)
        self.assertEqual(value['unavailable'][0]['status'],'UNKNOWN');self.assertEqual(value['bounds'],[])
        self.assertFalse((self.state/'memory').exists())

if __name__=='__main__':unittest.main()
