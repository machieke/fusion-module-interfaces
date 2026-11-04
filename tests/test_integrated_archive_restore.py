"""Real owner file/SQLite archive export and fenced import; payload backend fixture.

This does not claim Kubernetes restore or native execution. Those have separate
retained-namespace evidence. No effect executor or global atomicity is inferred.
"""
import io,json,sqlite3,tarfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from fusion.contracts import canonical,ContractError,digest
from fusion.ports import Mutation
from integration.single_node.backup_payload import export,restore,synthetic_seal
from integration.single_node.integrated_integrity import archive_dependencies,summary
from tests.test_integrated_archive import Archive,SCOPE

class ArchiveRestore(unittest.TestCase):
    setUp=Archive.setUp
    owner=Archive.owner
    write=Archive.write
    def seal(self):
        value=dict(role='fusion-storage',scope=SCOPE,composition='omega-single-node-sustained-preview/1',backend_layout='detta-opaque-coordinate-partitions/1',storage_archive=self.archive)
        (self.root/'owner-seal.json').write_bytes(canonical(value));return value
    def segment(self):
        owner=self.owner();ref=self.write(1,owner)['ref'];self.write(2,owner)
        sealed=owner.publishArchive(Mutation(SCOPE,'archive'),0,owner.head(SCOPE),2)
        return owner,ref,Path(str(owner.path)+'.archive')/(sealed['id']+'.json')
    def test_closed_dependency_manifest_and_fenced_roundtrip_with_spent_accounting(self):
        owner,ref,file=self.segment();self.seal();before=owner.observeArchive(Mutation(SCOPE,'archive'))
        output=io.BytesIO()
        with patch('sys.stdout',SimpleNamespace(buffer=output)):export(self.root,'fusion-storage')
        with tarfile.open(fileobj=io.BytesIO(output.getvalue()),mode='r:gz') as tar:
            manifest=json.load(tar.extractfile('backup-manifest.json'))
        self.assertEqual(len(manifest['archive_dependencies']),1);self.assertEqual(manifest['integrity']['status'],'PASS')
        clone=self.root.parent/(self.root.name+'-clone');clone.mkdir();self.addCleanup(lambda:__import__('shutil').rmtree(clone))
        with patch('sys.stdin',SimpleNamespace(buffer=io.BytesIO(output.getvalue()))),patch('sys.stdout',io.StringIO()):restore(clone,'fusion-storage','omega-ref-archive-clone')
        self.assertEqual(archive_dependencies(clone)['dependencies'],manifest['archive_dependencies'])
        self.assertFalse(json.loads((clone/'restore-fence.json').read_bytes())['external_effect_authority'])
        with sqlite3.connect(clone/'feed.sqlite') as db:
            row=db.execute('SELECT charge,state FROM feed_archive_intents').fetchone()
            self.assertEqual(row,(before['archive']['charged_bytes'],'sealed'))
        self.assertEqual((clone/file.relative_to(self.root)).read_bytes(),file.read_bytes())
    def test_missing_and_corrupt_authoritative_archives_refuse_export(self):
        owner,ref,file=self.segment();self.seal();raw=file.read_bytes();file.unlink()
        report=archive_dependencies(self.root);self.assertEqual(report['findings'][0]['classification'],'MISSING_AUTHORITATIVE_ARCHIVE')
        with patch('sys.stdout',SimpleNamespace(buffer=io.BytesIO())):
            with self.assertRaisesRegex(ContractError,'CONFLICT'):export(self.root,'fusion-storage')
        file.write_bytes(b'{}');report=archive_dependencies(self.root)
        self.assertEqual(report['findings'][0]['classification'],'CORRUPT_AUTHORITATIVE_ARCHIVE')
        self.assertNotIn(ref['id'],canonical(summary(report)).decode())
        file.write_bytes(raw);self.assertEqual(archive_dependencies(self.root)['status'],'PASS')
    def test_mutated_authoritative_mapping_is_not_repaired_or_inferred_from_hot_bytes(self):
        owner,ref,file=self.segment();self.seal()
        db=sqlite3.connect(owner.path)
        with db:db.execute('UPDATE feed_archive_members SET ordinal=7 WHERE atom=?',(ref['id'],))
        self.assertEqual(archive_dependencies(self.root)['findings'][0]['classification'],'OBSERVATION_UNAVAILABLE')
        db.close() # Quiesced checkpoint required; observation must not hide WAL.
        before=owner.path.read_bytes();result=archive_dependencies(self.root)
        self.assertEqual(result['findings'][0]['classification'],'CORRUPT_AUTHORITATIVE_JOURNAL')
        self.assertEqual(result['repair'],'NONE');self.assertEqual(owner.path.read_bytes(),before)
    def test_reserved_publication_and_lifecycle_seals_are_explicit(self):
        owner=self.owner();self.write(1,owner)
        def stop(stage):
            if stage=='after_archive_file_publish':raise InterruptedError()
        with self.assertRaises(InterruptedError):self.owner(stop).publishArchive(Mutation(SCOPE,'pending'),0,owner.head(SCOPE),1)
        result=archive_dependencies(self.root);self.assertEqual(result['reserved_segments'],1);self.assertEqual(result['dependencies'],{})
        # Copying an unactivated segment grants neither routing nor new quota.
        self.assertGreater(result['charged_bytes'],0)
        from fusion.resident_workers import LIMITS
        good=dict(role='omega-agent',scope=SCOPE,composition='omega-single-node-sustained-preview/1',resident_worker=LIMITS,history_representation='immutable-administrative-captures/1',provider_registry='trusted-provider-lifecycle/1')
        synthetic_seal(good,'omega-agent')
        with self.assertRaisesRegex(ContractError,'UNSUPPORTED_PROFILE'):synthetic_seal(dict(good,role='fusion-model'),'fusion-model')

if __name__=='__main__':unittest.main()
