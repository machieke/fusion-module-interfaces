"""Actual local Workspace copy and atomic maintenance; cluster/model are unrun."""
import copy,json,os,shutil,sqlite3,tempfile,unittest
from contextlib import closing
from pathlib import Path
from fusion.contracts import ContractError,canonical,digest
from fusion.preview_workspace import Workspace,reattest_root,root_handover_observation,ROOT_RECEIPT
from integration.single_node.pilot_activation import install
from integration.single_node.pilot_dependencies import inventory
from integration.single_node.pilot_handover_operator import workspace_transform

class WorkspaceHandover(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.scope='synthetic-root-copy';self.checkpoint='a'*64
        self.source=self.root/'source';self.source.mkdir();self.facets=self.source/'preview-facets';self.facets.mkdir()
        owner=self.owner(self.source);owner.mutate('A',self.scope,'one','write','a.txt','first',0);owner.mutate('A',self.scope,'two','write','a.txt','second',1);owner.close()
        self.target=self.root/'target';shutil.copytree(self.source,self.target)
    def tearDown(self):self.tmp.cleanup()
    def owner(self,root,hook=lambda _:None):
        return Workspace(root/'preview-facets/workspace',root/'preview-facets/workspace.sqlite',lambda *_:None,scope=self.scope,hook=hook)
    def db(self,root):return root/'preview-facets/workspace.sqlite'
    def rows(self,root):
        with closing(sqlite3.connect(self.db(root))) as db:return {table:db.execute('SELECT * FROM '+table).fetchall() for table in ('workspace_files','workspace_effects')}
    def attest(self,**kw):
        return reattest_root(self.target/'preview-facets/workspace',self.db(self.target),scope=self.scope,checkpoint=self.checkpoint,generation=2,**kw)
    def test_actual_copy_refuses_default_then_attested_new_work_preserves_old_receipts(self):
        before=self.rows(self.target);source=self.db(self.source).read_bytes()
        with self.assertRaisesRegex(ContractError,'UNSUPPORTED_PROFILE'):self.owner(self.target)
        receipt=self.attest();self.assertEqual(self.attest(),receipt);self.assertEqual(self.rows(self.target),before);self.assertEqual(self.db(self.source).read_bytes(),source)
        owner=self.owner(self.target)
        try:
            self.assertEqual(owner.read('A',self.scope,'a.txt')['text'],'second')
            self.assertEqual(owner.mutate('A',self.scope,'three','write','b.txt','new epoch',0)['revision'],1)
        finally:owner.close()
        self.assertEqual(self.rows(self.source),before)
    def test_old_committed_bytes_tampering_is_rejected(self):
        (self.target/'preview-facets/workspace/a.txt').write_text('first')
        with self.assertRaisesRegex(ContractError,'CONFLICT'):self.attest()
    def test_pending_effect_bytes_and_uncertain_receipt_remain_unchanged(self):
        def crash(stage):
            if stage=='after_workspace_effect':raise RuntimeError('stopped-after-effect')
        owner=self.owner(self.source,crash)
        try:
            with self.assertRaisesRegex(RuntimeError,'stopped-after-effect'):owner.mutate('A',self.scope,'pending','write','a.txt','pending bytes',2)
        finally:owner.close()
        shutil.rmtree(self.target);shutil.copytree(self.source,self.target);before=self.rows(self.target)
        self.attest();self.assertEqual(self.rows(self.target),before)
        self.assertIsNone(before['workspace_effects'][-1][-1]);self.assertEqual((self.target/'preview-facets/workspace/a.txt').read_text(),'pending bytes')
        owner=self.owner(self.target)
        try:
            with self.assertRaisesRegex(ContractError,'NOT_AVAILABLE'):owner.mutate('A',self.scope,'new-overtake','write','a.txt','no',2)
        finally:owner.close()
    def test_interrupted_transaction_rolls_back_and_postcommit_replay_is_exact(self):
        before=self.rows(self.target)
        def rollback(stage):
            if stage=='after_workspace_root_metadata':raise RuntimeError('rollback')
        with self.assertRaisesRegex(RuntimeError,'rollback'):self.attest(hook=rollback)
        with closing(sqlite3.connect(self.db(self.target))) as db:self.assertIsNone(db.execute("SELECT 1 FROM sqlite_master WHERE name=?",(ROOT_RECEIPT,)).fetchone())
        self.assertEqual(self.rows(self.target),before)
        def committed(stage):
            if stage=='after_workspace_root_commit':raise RuntimeError('committed')
        with self.assertRaisesRegex(RuntimeError,'committed'):self.attest(hook=committed)
        receipt=self.attest();self.assertEqual(self.rows(self.target),before)
        self.assertEqual(root_handover_observation(self.target/'preview-facets/workspace',self.db(self.target)),receipt)
    def test_changed_generation_scope_checkpoint_or_root_refused(self):
        self.attest()
        for change in (dict(generation=3),dict(scope='synthetic-other'),dict(checkpoint='b'*64)):
            args=dict(scope=self.scope,checkpoint=self.checkpoint,generation=2);args.update(change)
            with self.subTest(change=change),self.assertRaises(ContractError):reattest_root(self.target/'preview-facets/workspace',self.db(self.target),**args)
        moved=self.root/'moved';shutil.copytree(self.target,moved)
        with self.assertRaisesRegex(ContractError,'UNSUPPORTED_PROFILE'):self.owner(moved)
        with self.assertRaisesRegex(ContractError,'CONFLICT'):reattest_root(moved/'preview-facets/workspace',self.db(moved),scope=self.scope,checkpoint=self.checkpoint,generation=2)
    def test_links_malformed_rows_and_nonempty_wal_are_closed(self):
        file=self.target/'preview-facets/workspace/a.txt';file.unlink();file.symlink_to(self.source/'preview-facets/workspace/a.txt')
        with self.assertRaises(ContractError):self.attest()
        file.unlink();os.link(self.source/'preview-facets/workspace/a.txt',file)
        with self.assertRaises(ContractError):self.attest()
        file.unlink();file.write_text('second');file.chmod(0o600)
        with closing(sqlite3.connect(self.db(self.target))) as db:
            with db:db.execute('INSERT INTO workspace_meta SELECT * FROM workspace_meta')
        with self.assertRaises(ContractError):self.attest()
        Path(str(self.db(self.target))+'-wal').write_bytes(b'nonempty')
        with self.assertRaisesRegex(ContractError,'NOT_AVAILABLE'):root_handover_observation(file.parent,self.db(self.target))
    def export(self,root):
        with closing(sqlite3.connect(self.db(root))) as db:db.execute('PRAGMA wal_checkpoint(TRUNCATE)')
        files={str(p.relative_to(root)):dict(bytes=p.stat().st_size,sha256=digest(p.read_bytes())) for p in root.rglob('*') if p.is_file() and not p.name.endswith(('-wal','-shm','.lock'))}
        value=dict(role='fusion-execution',seal=dict(scope=self.scope),files=files,dependency_inventory=inventory(root,'fusion-execution',files,lambda *_:None))
        receipt=root_handover_observation(root/'preview-facets/workspace',self.db(root))
        if receipt is not None:value['workspace_root_reattestation']=receipt
        return value
    def test_activation_installs_only_verified_synthetic_copy_and_exact_transform(self):
        original=self.export(self.source)
        (self.target/'restore-fence.json').write_bytes(canonical(dict(mode='READ_ONLY_RECONCILIATION',role='fusion-execution',external_effect_authority=False,original_scope=self.scope,namespace='omega-ref-fixture-copy',backup_manifest_sha256='f'*64)))
        (self.target/'owner-seal.json').write_bytes(canonical(dict(composition='omega-single-node-sustained-preview/1',role='fusion-execution',scope=self.scope)))
        install(self.target,'fusion-execution',self.checkpoint,2);restored=self.export(self.target)
        transform=workspace_transform(original,restored,self.checkpoint)
        self.assertEqual(transform['files'],{'preview-facets/workspace.sqlite'});self.assertEqual(self.rows(self.target),self.rows(self.source))
        for changed in ('checkpoint_sha256','generation','current','tables','files'):
            bad=copy.deepcopy(restored);r=bad['workspace_root_reattestation']
            r[changed]={'checkpoint_sha256':'b'*64,'generation':3,'current':r['previous'],'tables':{},'files':{}}[changed]
            with self.subTest(changed=changed),self.assertRaises(ContractError):workspace_transform(original,bad,self.checkpoint)
        bad=copy.deepcopy(restored);row=next(x for x in bad['dependency_inventory']['entries'] if x.get('identity')=='preview-facets/workspace.sqlite:workspace_effects');row['semantic_head']='b'*64
        with self.assertRaises(ContractError):workspace_transform(original,bad,self.checkpoint)
    def test_activation_refuses_private_partition_or_wrong_scope_workspace_before_writes(self):
        (self.target/'restore-fence.json').write_bytes(canonical(dict(mode='READ_ONLY_RECONCILIATION',role='fusion-execution',external_effect_authority=False,original_scope='synthetic-other',namespace='omega-ref-fixture-copy',backup_manifest_sha256='f'*64)))
        (self.target/'owner-seal.json').write_bytes(canonical(dict(composition='omega-single-node-sustained-preview/1',role='fusion-execution',scope=self.scope)))
        before=self.db(self.target).read_bytes()
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):install(self.target,'fusion-execution',self.checkpoint,2)
        self.assertFalse((self.target/'pilot-activation-intent.json').exists());self.assertEqual(self.db(self.target).read_bytes(),before)
        fence=json.loads((self.target/'restore-fence.json').read_bytes());fence['original_scope']=self.scope;(self.target/'restore-fence.json').write_bytes(canonical(fence))
        private=self.target/'scopes'/'private-a';private.mkdir(parents=True);shutil.move(self.target/'preview-facets',private/'preview-facets')
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):install(self.target,'fusion-execution',self.checkpoint,2)
        self.assertFalse((self.target/'pilot-activation-intent.json').exists())

    def test_activation_requires_observation_only_fence_and_synthetic_scope(self):
        (self.target/'restore-fence.json').write_bytes(canonical(dict(mode='READ_ONLY_RECONCILIATION',role='fusion-execution',external_effect_authority=True)))
        (self.target/'owner-seal.json').write_bytes(canonical(dict(composition='omega-single-node-sustained-preview/1',role='fusion-execution',scope=self.scope)))
        before=self.db(self.target).read_bytes()
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):install(self.target,'fusion-execution',self.checkpoint,2)
        self.assertEqual(self.db(self.target).read_bytes(),before)

if __name__=='__main__':unittest.main()
