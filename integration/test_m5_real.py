"""Real local DeTTa plus process kills. Requires pinned built adapter; no skips."""
from dataclasses import replace
import json,os,signal,subprocess,sys,time,unittest
from pathlib import Path
from fusion import lookup_contracts as c
from fusion.contracts import ContractError,canonical
from fusion.ports import Mutation
from tests.m5_support import LookupHarness,SCOPE,ROOT

class RealLookup(unittest.TestCase):
    def harness(self,search='sqlite'):
        h=LookupHarness(real=True,search=search);self.addCleanup(h.close);return h
    def kill(self,h,operation,stage):
        marker=h.root/'paused';marker.unlink(missing_ok=True)
        with open(h.root/'driver.log','wb') as log:
            p=subprocess.Popen([sys.executable,'-m','integration.m5_driver',str(h.root),operation,'--stage',stage,'--real'],cwd=ROOT,stdout=log,stderr=log,start_new_session=True)
            try:
                deadline=time.monotonic()+30
                while not marker.exists() and p.poll() is None and time.monotonic()<deadline:time.sleep(.01)
                self.assertTrue(marker.exists(),(h.root/'driver.log').read_text())
            finally:
                if p.poll() is None:os.killpg(p.pid,signal.SIGKILL)
                p.wait(timeout=10)
            self.assertEqual(p.returncode,-signal.SIGKILL)
        h.reopen()
    def test_real_all_operations_rebuild_and_unavailable_payload(self):
        h=self.harness();oracle=h.seed();q=h.query(oracle['head'],kind='task',topic='retrieval-demo')
        h.drain();result=h.consumer().lookup(Mutation(SCOPE,'real-request'),q)
        self.assertEqual(result['roots'],oracle['order']);self.assertEqual(len(result['relations']),15);self.assertEqual(len(result['documents']),8)
        for edge in oracle['edges']:self.assertEqual(h.relations.getRelation(edge['ref']),edge)
        availability=h.atoms.availability(result['roots'][0]);self.assertEqual(availability['content_hash'],result['roots'][0]['digest'])
        # Remove only the entire derived Search owner, preserving authoritative owners.
        first=h.search.query(q);old_generation=first['generation'];at=h.atoms.head(SCOPE)
        for p in h.modules.root.glob('search-*'):p.unlink()
        h.reopen()
        with self.assertRaises(ContractError):h.search.query(q)
        h.drain();rebuilt=h.consumer('rebuilt').lookup(Mutation(SCOPE,'real-request'),q)
        for field in ('roots','relations','documents','search_at','relations_at'):self.assertEqual(result[field],rebuilt[field])
        self.assertNotEqual(old_generation,rebuilt['search_generation']);self.assertEqual(h.atoms.head(SCOPE),at)
        with self.assertRaises(ContractError):h.search.query(replace(q,cursor=first['cursor']))
        # Exact metadata still exists, but the underlying payload is unavailable.
        import shutil
        shutil.rmtree(h.modules.root/'payloads')
        with self.assertRaises(ContractError) as error:h.atoms.get(result['roots'][0])
        self.assertEqual(error.exception.code,'NOT_AVAILABLE')
        with self.assertRaises(ContractError) as error:
            h.relations.assertRelation(Mutation(SCOPE,'unavailable-endpoint'),'requires/1',
                (('dependent',result['roots'][0]),('prerequisite',result['roots'][1])),True)
        self.assertEqual(error.exception.code,'NOT_AVAILABLE')
    def test_feed_commit_lost_ack(self):
        h=self.harness();self.kill(h,'create','after_atom_feed_commit');head=h.atoms.head(SCOPE);self.assertEqual(head['sequence'],1)
        page=h.atoms.readCommits(SCOPE,0,head,2);ref=h.create('lost-ack',kind='task',topic='recovery')
        self.assertEqual(page['records'][0]['ref'],ref);self.assertEqual(h.atoms.head(SCOPE),head)
        self.assertEqual(h.atoms.get(ref).bytes,canonical({'kind':'task','topic':'recovery'}))
    def test_relation_separate_owner_kills(self):
        for stage in ('after_relation_payload','after_relation_commit'):
            with self.subTest(stage=stage):
                h=self.harness();self.kill(h,'relation',stage)
                a=h.create('endpoint-a',kind='task');b=h.create('endpoint-b',kind='prerequisite');head=h.atoms.head(SCOPE)
                self.assertEqual(head['sequence'],3)
                page=h.relations.outgoing(a,2);self.assertEqual(len(page['refs']),int(stage=='after_relation_commit'))
                raw=h.atoms.readCommits(SCOPE,2,head,1)['records'][0]['ref']
                if stage=='after_relation_payload':
                    with self.assertRaises(ContractError) as error:h.relations.getRelation(raw)
                    self.assertEqual(error.exception.code,'NOT_FOUND')
                edge=h.relations.assertRelation(Mutation(SCOPE,'lost-relation-ack'),'requires/1',(('dependent',a),('prerequisite',b)),True)
                self.assertEqual(edge['ref'],raw);self.assertEqual(h.atoms.head(SCOPE),head)
                self.assertEqual(h.relations.outgoing(a,2)['refs'],[raw]);self.assertEqual(h.relations.incoming(b,2)['refs'],[raw])
    def test_projection_kills_both_providers(self):
        for provider in ('sqlite','atomic-file-fixture'):
            for stage in ('before_checkpoint_commit','after_checkpoint_commit','after_rebuild_begin'):
                with self.subTest(provider=provider,stage=stage):
                    h=self.harness(provider);refs=[h.create('a'+str(i),kind='task') for i in range(5)];head=h.atoms.head(SCOPE)
                    if stage=='after_rebuild_begin':h.drain()
                    self.kill(h,'rebuild' if stage=='after_rebuild_begin' else 'catchup',stage)
                    if stage=='after_rebuild_begin':
                        with self.assertRaises(ContractError):h.search.query(h.query(head,kind='task'))
                        # Make one bounded rebuild batch, then restart a second time.
                        h.search.catchUp(SCOPE,2);h.reopen()
                    else:
                        q=h.query({**head,'sequence':0},limit=8,kind='task');page=h.search.query(q)
                        self.assertEqual(page['at']['sequence'],2 if stage=='after_checkpoint_commit' else 0)
                        self.assertEqual(len(page['refs']),page['at']['sequence'])
                    h.drain();self.assertEqual(h.search.query(h.query(head,limit=8,kind='task'))['refs'],refs)
                    self.assertEqual(h.atoms.head(SCOPE),head)
if __name__=='__main__':unittest.main()
