"""Real feed journals and process kills; physical payloads are explicit fixtures.

Crossing 512 here qualifies contracts only, not the sustained native workload.
"""
from contextlib import closing
from dataclasses import replace
import json,multiprocessing,os,signal,sqlite3,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from fusion import lookup_contracts as c,append_contracts as w,vector_composition as v,cognitive_services as cs
from fusion.atom_feed import FeedAtomOwner
from fusion.contracts import ContractError,canonical,digest,require
from fusion.ports import Mutation
from fusion.sustained_feed import PROFILE,METADATA_RESERVATION,capacity_result

SCOPE='synthetic-sustained-feed-fixture'
class FilePayloadFixture:
    def __init__(self,root):self.root=Path(root);self.root.mkdir(exist_ok=True)
    def put(self,scope,key,data):
        name=digest(canonical([scope,key]));path=self.root/name
        if path.exists():require(path.read_bytes()==data,'CONFLICT')
        else:
            with path.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
        return name,dict(provider='EXPLICIT_PAYLOAD_FIXTURE',evidence='NOT_DETTA')
    def get(self,scope,key):return (self.root/key).read_bytes()

class SustainedFeedTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name);self.revoked=False
        self.policy=dict(profile=PROFILE,records=640,bytes=8*1024*1024,scopes=[SCOPE,SCOPE+'-private'])
    def owner(self,hook=lambda _:None):
        def authorize(scope,operation):
            require(not self.revoked and scope==SCOPE,'UNAUTHORIZED');return 'A'
        return FeedAtomOwner(self.root/'feed.sqlite',FilePayloadFixture(self.root/'bytes'),SimpleNamespace(authorize=authorize),hook,capacity=self.policy)
    def write(self,i,owner=None):return (owner or self.owner()).create(Mutation(SCOPE,'input-'+str(i)),'application/synthetic-fixture',str(i).encode())
    def test_explicit_profile_crossing_preserves_first_refs_heads_and_limits(self):
        owner=self.owner();first=self.write(0,owner);early=owner.head(SCOPE)
        for i in range(1,600):self.write(i,owner)
        last=owner.head(SCOPE);self.assertEqual(last['sequence'],600);self.assertEqual(last['profile'],c.SUSTAINED_FEED)
        self.assertEqual(owner.get(first['ref']).bytes,b'0');self.assertEqual(owner.readCommits(SCOPE,0,early,8)['records'][0]['ref'],first['ref'])
        with self.assertRaisesRegex(ContractError,'INVALID_ARGUMENT|UNSUPPORTED_PROFILE'):c.head(last)
        self.assertEqual(c.source_head(last),last)
        status=capacity_result(owner.capacity(SCOPE),SCOPE)
        self.assertEqual(status['usage']['reserved_records'],600)
        self.assertEqual(status['usage']['published_records'],600)
        self.assertEqual(self.write(0,owner),first)
        self.revoked=True
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):owner.get(first['ref'])
    def test_new_record_limit_refusal_and_pending_charge_do_not_refund(self):
        self.policy['records']=2
        def stop(stage):
            if stage=='after_feed_admission_commit':raise InterruptedError('after admission fixture')
        with self.assertRaises(InterruptedError):self.write(1,self.owner(stop))
        self.write(2);before=self.owner().capacity(SCOPE)
        with self.assertRaisesRegex(ContractError,'OVERLOADED'):self.write(3)
        self.assertEqual(self.owner().capacity(SCOPE),before)
        self.assertEqual(before['usage']['pending_records'],1)
        self.write(1);self.assertEqual(self.owner().capacity(SCOPE)['usage']['reserved_records'],2)
    def test_byte_limit_refuses_before_backend_and_private_counts_are_denied(self):
        self.policy['bytes']=METADATA_RESERVATION+1;self.write(1)
        with self.assertRaisesRegex(ContractError,'OVERLOADED'):self.write(2)
        self.assertEqual(len(list((self.root/'bytes').iterdir())),1)
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):self.owner().capacity(SCOPE+'-private')
    def test_populated_old_new_profiles_cannot_be_reopened_as_each_other(self):
        owner=self.owner();self.write(1,owner);before=(self.root/'feed.sqlite').read_bytes()
        with self.assertRaisesRegex(ContractError,'UNSUPPORTED_PROFILE'):FeedAtomOwner(self.root/'feed.sqlite',None,None)
        self.assertEqual((self.root/'feed.sqlite').read_bytes(),before)
        self.policy['records']+=1
        with self.assertRaisesRegex(ContractError,'CONFLICT'):self.owner()
    def test_same_identity_cannot_change_reserved_bytes(self):
        def stop(stage):
            if stage=='after_feed_admission_commit':raise InterruptedError()
        with self.assertRaises(InterruptedError):self.write(1,self.owner(stop))
        with self.assertRaisesRegex(ContractError,'CONFLICT'):self.owner().create(Mutation(SCOPE,'input-1'),'application/synthetic-fixture',b'different')
    def test_real_sigkill_at_each_independent_durable_boundary(self):
        for number,stage in enumerate(('after_feed_admission_commit','after_feed_backend_acceptance','after_atom_feed_commit')):
            with self.subTest(stage=stage):
                ctx=multiprocessing.get_context('fork');reader,writer=ctx.Pipe(False)
                def work():
                    reader.close()
                    def hook(observed):
                        if observed==stage:writer.send(observed);signal.pause()
                    self.write(number,self.owner(hook))
                process=ctx.Process(target=work);process.start();writer.close()
                try:
                    self.assertTrue(reader.poll(5));self.assertEqual(reader.recv(),stage)
                    os.kill(process.pid,signal.SIGKILL);process.join(5);self.assertEqual(process.exitcode,-signal.SIGKILL)
                    before=self.owner().capacity(SCOPE)['usage'];value=self.write(number)
                    after=self.owner().capacity(SCOPE)['usage'];self.assertEqual(before['charged_bytes'],after['charged_bytes'])
                    self.assertEqual(before['reserved_records'],after['reserved_records'])
                    self.assertEqual(self.owner().get(value['ref']).bytes,str(number).encode())
                finally:
                    if process.is_alive():process.kill();process.join()
                    reader.close();process.close()
    def test_profile_selection_does_not_implicitly_upgrade_old_clients(self):
        new=w.descriptors(c.SUSTAINED_FEED)
        self.assertEqual(c.feed_profile(w.select(new,c.SUSTAINED_FEED)['atom.storage']),c.SUSTAINED_FEED)
        with self.assertRaises(ContractError):w.select(new)
        old=w.descriptors();self.assertEqual(c.feed_profile(w.select(old)['atom.storage']),c.FEED)
        with self.assertRaises(ContractError):w.select(old,c.SUSTAINED_FEED)
        self.assertNotIn('capacity',cs.descriptors()[0].operations)
        self.assertIn('capacity',cs.descriptors(feed_profile=c.SUSTAINED_FEED)[0].operations)

if __name__=='__main__':unittest.main()
