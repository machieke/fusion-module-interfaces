"""Real SQLite/files/fsync/process kill; native overlay and AtomStorage fixtures.

No native/DeTTa/cluster claim. Root bytes and spent rows are retained exactly.
"""
import json,os,signal,sqlite3,subprocess,sys,tempfile,unittest,uuid
from pathlib import Path
from fusion.contracts import canonical,digest,ContractError,encode
from fusion.adapters.fixture_feed import FileFeedFixture
from fusion.preview_native_history import write_body,read_body
from integration.single_node.pilot_derived_maintenance import Cleanup
from tests.test_phase2_native_relations import AuthorityFixture,SCOPE


def overlay(root,key):
    folder=root/'native/prepared'/key;folder.mkdir(parents=True)
    (folder/'code.metta').write_text('fixture-only '+str(folder))
    (folder/'startup.json').write_bytes(canonical(dict(overlay_hashes={'code.metta':digest((folder/'code.metta').read_bytes())})))
    # A startup manifest contains hashes of path-dependent overlay bytes. This
    # fixture keeps source independent like the actual generated code files.
    (folder/'code.metta').write_text('fixture-only-code')
    (folder/'startup.json').write_bytes(canonical(dict(overlay_hashes={'code.metta':digest((folder/'code.metta').read_bytes())})))
    value=dict(profile='verified-native-preparation/1',key=key,files={p.name:digest(p.read_bytes()) for p in folder.iterdir()},command=['native',str(folder/'code.metta')],environment={})
    (folder/'prepared.json').write_bytes(canonical(value))
    for p in folder.iterdir():p.chmod(0o444)
    folder.chmod(0o555);return folder


class DerivedApplication(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.session=str(uuid.uuid4());self.atomfile=self.root/'fixture-atoms.json';self.atoms=FileFeedFixture(self.atomfile,AuthorityFixture('atom.storage'))
        self.dbfile=self.root/'caller.sqlite';self.db=sqlite3.connect(self.dbfile);self.db.row_factory=sqlite3.Row;self.addCleanup(self.db.close)
        self.db.execute('CREATE TABLE app_occurrences(id TEXT,spent INTEGER,result TEXT)');self.db.execute("INSERT INTO app_occurrences VALUES('old-effect',3,'captured-value')")
        self.db.execute('CREATE TABLE preview_history_materializations(key TEXT PRIMARY KEY,binding TEXT,root TEXT,content_type TEXT,body TEXT,body_digest TEXT)')
        body=canonical(dict(result='synthetic captured history'))
        ref=write_body(self.atoms,SCOPE,'root',body)['ref'];self.ref=ref;item=self.atoms.get(ref)
        binding=canonical(dict(session=self.session,payload=ref));self.key=digest(binding)
        self.db.execute('INSERT INTO preview_history_materializations VALUES(?,?,?,?,?,?)',(self.key,binding.decode(),encode(item.bytes),item.content_type,body.decode(),digest(body)));self.db.commit()
        self.current='a'*64;self.stale='b'*64;folder=overlay(self.root,self.current);overlay(self.root,self.stale)
        (self.root/'native/startup.json').write_bytes((folder/'startup.json').read_bytes())
        (self.root/'native/preparation-observation.json').write_bytes(canonical(dict(profile='verified-native-preparation/1',key=self.current)))
        self.allowed=True
        self.clean=Cleanup(self.root,self.session,self.db,self.authorize,self.atoms)
        self.selection=dict(overlays=[self.stale],materializations=[self.key],duplicate_startup=True)
    def authorize(self):
        if not self.allowed:raise ContractError('UNAUTHORIZED')
    def test_derived_bytes_removed_capture_source_and_current_pin_survive(self):
        source=self.atomfile.read_bytes();plan=self.clean.plan(self.selection);result=self.clean.apply(plan,'cleanup-one')
        self.assertEqual(result['state'],'complete');self.assertGreater(result['unlinked_bytes'],0);self.assertGreater(result['cache_body_bytes_removed'],0)
        self.assertFalse((self.root/'native/prepared'/self.stale).exists());self.assertTrue((self.root/'native/prepared'/self.current).is_dir())
        self.assertEqual(self.atomfile.read_bytes(),source);self.assertEqual(read_body(self.atoms,self.ref),{'result':'synthetic captured history'})
        self.assertEqual(tuple(self.db.execute('SELECT * FROM app_occurrences').fetchone()),('old-effect',3,'captured-value'))
        self.assertEqual(self.clean.apply(plan,'cleanup-one'),result)
        self.assertFalse(result['capacity_refund']);self.assertIn('NOT_ESTABLISHED',result['physical_freed_bytes'])
    def test_owner_inventory_selects_only_reconstructible_candidates_without_payloads(self):
        before=self.db.execute('SELECT * FROM app_occurrences').fetchall()
        selected=self.clean.inventory();self.assertEqual(selected['selection'],self.selection)
        self.assertEqual(selected['current_preparation'],self.current)
        self.assertNotIn('synthetic captured history',canonical(selected).decode())
        self.assertEqual(self.db.execute('SELECT * FROM app_occurrences').fetchall(),before)
        self.clean.apply(self.clean.plan(selected['selection']),'inventory-selected')
        self.assertEqual(self.clean.inventory()['selection'],dict(overlays=[],materializations=[],duplicate_startup=False))
        self.allowed=False
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):self.clean.inventory()
    def test_current_pin_authoritative_race_revocation_and_source_loss_refuse(self):
        with self.assertRaisesRegex(ContractError,'CONFLICT'):self.clean.plan(dict(self.selection,overlays=[self.current]))
        plan=self.clean.plan(self.selection);self.allowed=False
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):self.clean.apply(plan,'denied')
        self.allowed=True;self.db.execute("INSERT INTO app_occurrences VALUES('newly-pinned',1,NULL)");self.db.commit()
        with self.assertRaisesRegex(ContractError,'CONFLICT'):self.clean.apply(plan,'stale')
        self.db.execute("DELETE FROM app_occurrences WHERE id='newly-pinned'");self.db.commit()
        self.atoms=FileFeedFixture(self.root/'empty-fixture-atoms.json',AuthorityFixture('atom.storage'));self.clean.atoms=self.atoms
        with self.assertRaisesRegex(ContractError,'NOT_FOUND'):self.clean.plan(self.selection)
    def test_owner_capacity_reserves_before_remove_and_retains_replay_charge(self):
        from fusion.sustained_sessions import SustainedSessionStore
        from integration.single_node.pilot_derived_maintenance import charges,LIMITS
        from tests.test_phase3_sessions import policy
        cfg=policy();store=SustainedSessionStore(self.root/'session-inbox.sqlite',lambda *_:None,cfg,clock=lambda:1000);self.addCleanup(store.close)
        account=charges(store,self.session,self.authorize);self.clean.account=account
        before=store._usage();plan=self.clean.plan(self.selection)
        # Failure after the independent accounting reservation leaves bytes
        # reserved but no removed cache/file. An exact retry consumes that
        # reservation; accepted work/spend rows are never adjusted.
        real_save=self.clean._save
        def fail(*_):raise RuntimeError('after-owner-reservation')
        self.clean._save=fail
        with self.assertRaisesRegex(RuntimeError,'after-owner-reservation'):self.clean.apply(plan,'reserved')
        held=store._usage();self.assertEqual(held['completion_reserved_bytes']-before['completion_reserved_bytes'],LIMITS['result_bytes'])
        self.assertTrue((self.root/'native/prepared'/self.stale).exists())
        self.clean._save=real_save;done=self.clean.apply(plan,'reserved');after=store._usage()
        self.assertEqual(after['completion_reserved_bytes'],before['completion_reserved_bytes']);self.assertGreater(after['logical_bytes'],before['logical_bytes'])
        self.assertEqual(self.clean.apply(plan,'reserved'),done);self.assertEqual(store._usage(),after)
        self.assertEqual(store.db.execute('SELECT count(*) FROM pilot_derived_cleanup_charges').fetchone()[0],1)
        # Capacity exhaustion is rejected before any new deletion receipt.
        cfg2=policy();cfg2['bytes']=20000
        small=SustainedSessionStore(self.root/'small-inbox.sqlite',lambda *_:None,cfg2,clock=lambda:1000);self.addCleanup(small.close)
        with self.assertRaisesRegex(ContractError,'OVERLOADED'):charges(small,self.session,self.authorize)(plan,dict(identity='denied',state='applying'))
        self.assertEqual(small.db.execute('SELECT count(*) FROM pilot_derived_cleanup_charges').fetchone()[0],0)

    def test_different_overlay_and_symlink_never_become_candidates(self):
        target=self.root/'native/prepared'/self.stale;file=target/'code.metta';file.chmod(0o644);file.write_text('changed');file.chmod(0o444)
        with self.assertRaisesRegex(ContractError,'CONFLICT'):self.clean.plan(self.selection)
        target.chmod(0o755);file.unlink();file.symlink_to(self.root/'fixture-atoms.json')
        with self.assertRaisesRegex(ContractError,'CONFLICT'):self.clean.plan(self.selection)
    def test_real_process_kill_after_unlink_recovers_same_identity(self):
        plan=self.clean.plan(self.selection);cfg=self.root/'request.json';cfg.write_bytes(canonical(dict(root=str(self.root),session=self.session,plan=plan)))
        result=subprocess.run([sys.executable,'-m','tests.test_pilot_derived_maintenance','--kill',str(cfg)],capture_output=True)
        self.assertEqual(result.returncode,-signal.SIGKILL,result.stderr.decode())
        interrupted=self.clean.observe(plan,'killed');self.assertEqual(interrupted['state'],'applying');self.assertIsNotNone(interrupted['pending'])
        done=self.clean.apply(plan,'killed');self.assertEqual(done['state'],'complete');self.assertEqual(self.clean.apply(plan,'killed'),done)
        self.assertEqual(self.db.execute('SELECT sum(spent) FROM app_occurrences').fetchone()[0],3)


def kill(path):
    q=json.loads(Path(path).read_bytes());root=Path(q['root']);db=sqlite3.connect(root/'caller.sqlite');db.row_factory=sqlite3.Row
    atoms=FileFeedFixture(root/'fixture-atoms.json',AuthorityFixture('atom.storage'))
    def hook(stage):
        if stage=='after_derived_unlink':os.kill(os.getpid(),signal.SIGKILL)
    Cleanup(root,q['session'],db,lambda:None,atoms,hook=hook).apply(q['plan'],'killed')


if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--kill':kill(sys.argv[2])
    else:unittest.main()
