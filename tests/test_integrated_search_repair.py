"""Real Chroma and lifecycle; immutable feed and vectors are labelled fixtures.

The subprocess kill uses the real durable repair journal. No native/E5/DeTTa or
pod claim is made by these contract tests.
"""
from dataclasses import asdict
import json,os,signal,subprocess,sys,time,unittest,uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from fusion import vector_contracts as v,preview_vector_contracts as c
from fusion.contracts import canonical,ContractError,digest
from fusion.ports import Mutation
from fusion.registry import descriptor_wire
from fusion.preview_memory_services import Access,search_owner
from fusion.search_repair import Repair,PROFILE,LIMITS,descriptor
from fusion.search_maintenance import Client,validate_result
from fusion.vector_enrollment import enroll
from tests import test_phase2_active_memory_ports as fixture


class SearchRepair(unittest.TestCase):
    config=fixture.ActivePorts.config
    def setUp(self):
        fixture.ActivePorts.setUp(self)
        cfg=json.loads(self.search.read_bytes());cfg['active_memory']['maintenance_profile']=PROFILE
        cfg['principals']['A']['scopes'][self.scope]+=['search.maintenance.'+x for x in ('planRepair','repair','observeRepair')]
        self.search.write_bytes(canonical(cfg))
        self.client=Client(dict(profile=PROFILE,scope=self.scope,placement='local',fallback=False,principal='A',
            credential='synthetic-token',provider_config=str(self.search),descriptor=descriptor_wire(descriptor())))
        self.deadline=time.time_ns()//1000000+60000;self.vector=[1.]+[0.]*1023
        self.first,self.snap=self.add('first')
        self.query=asdict(c.VectorQuery(str(uuid.uuid4()),self.scope,self.snap,self.vector,2,self.deadline))
        self.original=self.projection.call('query',self.query)
        self.owner=self.repair(self.snap);self.generation=self.owner.search.root/self.snap['generation']
    def add(self,key):
        uid=str(uuid.uuid4());ref=enroll(self.atoms,self.scope,self.corpus,v.EMBEDDING,uid,
            dict(scope=self.scope,corpus=self.corpus,uuid=uid,time='2026-11-04 00:00:00',content='Synthetic '+key),self.vector)
        receipt=self.lifecycle.call('change',Mutation(self.scope,'introduce-'+key),'introduce',dict(logical_id=None,expected_revision=0,enrollment=ref,deadline_ms=self.deadline))
        snap=self.projection.call('build',receipt['source_head'],receipt['at'],'build-'+key,self.deadline)
        return receipt,snap
    def repair(self,snapshot,hook=lambda _:None):
        return Repair(search_owner(self.search,Access(self.search,'synthetic-token','search'),snapshot['lifecycle'],hook))
    def broken(self):
        self.owner.search.sdk.PersistentClient(path=str(self.generation/'index')).delete_collection('memories')
        with self.assertRaisesRegex(ContractError,'NOT_AVAILABLE'):self.projection.call('query',self.query)
        return self.client.call('planRepair',self.snap)
    def test_rebuild_is_authoritative_exact_retained_and_does_not_regress_new_head(self):
        plan=self.broken();_,new=self.add('second')
        source_before=self.atoms.head(self.scope)
        done=self.client.call('repair',plan,'repair-first',self.deadline)
        self.assertEqual(done['state'],'verified');self.assertEqual(done['attempts_spent'],1)
        self.assertEqual(self.projection.call('query',self.query),self.original)
        self.assertEqual(self.projection.call('current',new['lifecycle']),new)
        self.assertEqual(self.atoms.head(self.scope),source_before)
        self.assertEqual(self.client.call('repair',plan,'repair-first',self.deadline),done)
        self.assertEqual(self.client.call('observeRepair',plan,'repair-first'),done)
        with self.assertRaisesRegex(ContractError,'CONFLICT'):self.client.call('repair',plan,'repair-first',self.deadline+1)
        other=self.client.call('planRepair',new)
        with self.assertRaisesRegex(ContractError,'CONFLICT'):self.client.call('repair',other,'repair-first',self.deadline)
    def test_missing_manifest_repaired_from_feed_not_original_query(self):
        (self.generation/'manifest.json').unlink();plan=self.client.call('planRepair',self.snap)
        self.assertEqual(plan['plan']['classification'],'MISSING_DERIVED_MANIFEST')
        self.client.call('repair',plan,'manifest',self.deadline)
        self.assertEqual(self.projection.call('query',self.query),self.original)
    def test_revocation_and_unauthorized_principal_do_not_reserve(self):
        plan=self.broken();cfg=json.loads(self.search.read_bytes())
        cfg['principals']['A']['scopes'][self.scope].remove('search.maintenance.repair');self.search.write_bytes(canonical(cfg))
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):self.client.call('repair',plan,'denied',self.deadline)
        self.assertEqual(self.client.call('observeRepair',plan,'denied')['state'],'absent')
        cfg['principals']['A']['credential']='rotated';self.search.write_bytes(canonical(cfg))
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):self.client.call('planRepair',self.snap)
    def test_source_outage_never_becomes_empty_success(self):
        plan=self.broken()
        with patch.object(self.atoms,'head',side_effect=ContractError('NOT_AVAILABLE')):
            with self.assertRaisesRegex(ContractError,'NOT_AVAILABLE'):self.owner.apply(plan,'outage',self.deadline)
        state=self.owner.observe(plan,'outage');self.assertEqual((state['state'],state['attempts_spent']),('needs-reconciliation',0))
        self.owner.apply(plan,'outage',self.deadline)
        self.assertEqual(self.projection.call('query',self.query),self.original)
    def test_attempts_are_spent_and_deadline_not_renewed(self):
        plan=self.broken()
        with patch.object(self.owner.search,'_project',side_effect=ContractError('NOT_AVAILABLE')):
            for _ in range(LIMITS['attempts']):
                with self.assertRaisesRegex(ContractError,'NOT_AVAILABLE'):self.owner.apply(plan,'spent',self.deadline)
            with self.assertRaisesRegex(ContractError,'OVERLOADED'):self.owner.apply(plan,'spent',self.deadline)
        self.assertEqual(self.owner.observe(plan,'spent')['attempts_spent'],3)
        with patch('fusion.search_repair.time.time_ns',return_value=(self.deadline+1)*1000000):
            with self.assertRaisesRegex(ContractError,'DEADLINE_EXCEEDED'):self.owner.apply(plan,'spent',self.deadline)
    def test_unknown_or_destructive_plan_and_malformed_result_rejected(self):
        plan=self.client.call('planRepair',self.snap)
        changed=json.loads(canonical(plan));changed['plan']['physical_erasure']=True;changed['plan_sha256']=digest(canonical(changed['plan']))
        with self.assertRaises(ContractError):self.client.call('repair',changed,'destructive',self.deadline)
        unknown=json.loads(canonical(self.snap));unknown['generation']=str(uuid.uuid4())
        with self.assertRaisesRegex(ContractError,'NOT_AVAILABLE'):self.client.call('planRepair',unknown)
        with self.assertRaisesRegex(ContractError,'NOT_AVAILABLE'):validate_result(dict(state='verified'), 'repair',[plan,'a',self.deadline],self.scope)
        with self.assertRaisesRegex(ContractError,'NOT_AVAILABLE'):validate_result({**plan,'plan_sha256':'0'*64},'planRepair',[self.snap],self.scope)
    def test_corrupt_container_is_diagnosed_without_automatic_removal(self):
        # Closed disposable copy; never overwrite a live Chroma database.
        import shutil,tempfile
        with tempfile.TemporaryDirectory() as d:
            target=Path(d)/'active';shutil.copytree(self.owner.search.root,target)
            bad=target/self.snap['generation']/'index/chroma.sqlite3';bad.write_bytes(b'corrupt-container')
            self.owner.search.root=target;plan=self.owner.plan(self.snap)
            self.assertEqual(plan['plan']['classification'],'CORRUPT_DERIVED_INDEX');self.assertFalse(plan['plan']['supported'])
            with self.assertRaisesRegex(ContractError,'NOT_AVAILABLE'):self.owner.apply(plan,'corrupt',self.deadline)
            self.assertEqual(bad.read_bytes(),b'corrupt-container')
    def test_real_process_kill_after_reservation_retains_identity_and_spend(self):
        plan=self.broken();args=self.root/'repair-args.json';args.write_bytes(canonical(dict(plan=plan,deadline=self.deadline,config=str(self.search),atoms=str(self.root/'atoms.json'))))
        p=subprocess.run([sys.executable,'-m','tests.test_integrated_search_repair','--kill-repair',str(args)],capture_output=True,timeout=30)
        self.assertEqual(p.returncode,-signal.SIGKILL,p.stderr.decode())
        state=self.owner.observe(plan,'killed');self.assertEqual((state['state'],state['attempts_spent'],state['deadline_ms']),('needs-reconciliation',1,self.deadline))
        done=self.client.call('repair',plan,'killed',self.deadline)
        self.assertEqual(done['attempts_spent'],2);self.assertEqual(self.projection.call('query',self.query),self.original)
    def test_recover_published_projection_after_capture_loss_without_rebuild(self):
        plan=self.broken()
        def stop(stage):
            if stage=='after_publication':raise ContractError('NOT_AVAILABLE')
        with self.assertRaisesRegex(ContractError,'NOT_AVAILABLE'):self.repair(self.snap,stop).apply(plan,'published',self.deadline)
        with patch.object(self.owner.search,'_project',side_effect=AssertionError('must not rebuild captured projection')):
            self.assertEqual(self.owner.apply(plan,'published',self.deadline)['attempts_spent'],1)
        self.assertEqual(self.projection.call('query',self.query),self.original)


def kill_repair(file):
    from fusion.adapters.fixture_feed import FileFeedFixture
    args=json.loads(Path(file).read_bytes());atoms=FileFeedFixture(args['atoms'],SimpleNamespace(authorize=lambda *_:'A'))
    with patch('fusion.vector_composition.ReadService',return_value=SimpleNamespace(atoms=atoms)),patch('fusion.memory_services.SearchPorts',return_value=SimpleNamespace(atoms=lambda:atoms)):
        access=Access(args['config'],'synthetic-token','search')
        def hook(stage):
            if stage=='after_search_repair_reservation':os.kill(os.getpid(),signal.SIGKILL)
        owner=Repair(search_owner(args['config'],access,args['plan']['plan']['snapshot']['lifecycle'],hook))
        owner.apply(args['plan'],'killed',args['deadline'])

if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--kill-repair':kill_repair(sys.argv[2])
    else:unittest.main()
