"""Real owner transactions/files/process kills; payload backend is a fixture."""
import json,multiprocessing,os,signal,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from fusion.atom_feed import FeedAtomOwner
from fusion.contracts import ContractError,require
from fusion.ports import Mutation
from fusion.sealed_archive import DEFAULT,RESERVATION_BYTES
from tests import test_phase3_feed as fixture

SCOPE=fixture.SCOPE
class Archive(unittest.TestCase):
    def setUp(self):
        fixture.SustainedFeedTests.setUp(self)
        self.archive=dict(DEFAULT,segments=4,bytes=4*RESERVATION_BYTES)
        self.denied=set()
    def owner(self,hook=lambda _:None):
        def authorize(scope,operation):
            require(not self.revoked and scope==SCOPE and operation not in self.denied,'UNAUTHORIZED');return 'A'
        return FeedAtomOwner(self.root/'feed.sqlite',fixture.FilePayloadFixture(self.root/'bytes'),
                            SimpleNamespace(authorize=authorize),hook,capacity=self.policy,archive=self.archive)
    write=fixture.SustainedFeedTests.write
    def test_sealed_read_uses_archive_no_hot_fallback_source_and_budget_unchanged(self):
        owner=self.owner();refs=[self.write(i,owner)['ref'] for i in range(3)];head=owner.head(SCOPE)
        before=owner.capacity(SCOPE);command=Mutation(SCOPE,'archive-one')
        plan=owner.planArchive(SCOPE,0,head,2);self.assertFalse(plan['admission_reserved'])
        value=owner.publishArchive(command,0,head,2);self.assertEqual(value['state'],'sealed')
        self.assertEqual(owner.publishArchive(command,0,head,2),value)
        self.assertEqual(owner.head(SCOPE),head);self.assertEqual(owner.capacity(SCOPE),before)
        with patch.object(owner.storage,'get',side_effect=AssertionError('hot fallback')):
            self.assertEqual(owner.get(refs[0]).bytes,b'0');self.assertTrue(owner.availability(refs[1])['available'])
        early=owner.readCommits(SCOPE,0,head,3);self.write(4)
        self.assertEqual(owner.readCommits(SCOPE,0,head,3),early)
        path=Path(str(owner.path)+'.archive')/(value['id']+'.json');raw=path.read_bytes();path.write_bytes(b'{}')
        with self.assertRaisesRegex(ContractError,'NOT_AVAILABLE'):owner.get(refs[0])
        path.write_bytes(raw);path.unlink()
        with self.assertRaisesRegex(ContractError,'NOT_AVAILABLE'):owner.get(refs[0])
        self.assertEqual(owner.capacity(SCOPE),dict(before,usage=dict(before['usage'],reserved_records=4,published_records=4,charged_bytes=before['usage']['charged_bytes']+8193,published_payload_bytes=4)))
    def test_authority_quota_overlap_and_unsafe_profile_downgrade(self):
        self.archive.update(segments=1,bytes=RESERVATION_BYTES)
        owner=self.owner();ref=self.write(1,owner)['ref'];self.write(2,owner);head=owner.head(SCOPE)
        command=Mutation(SCOPE,'one');owner.publishArchive(command,0,head,1)
        for action in ('get','availability'):
            self.denied.add('get')
            with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):getattr(owner,action)(ref)
            self.denied.clear()
        with self.assertRaisesRegex(ContractError,'CONFLICT'):owner.publishArchive(command,1,head,1)
        with self.assertRaisesRegex(ContractError,'OVERLOADED'):owner.publishArchive(Mutation(SCOPE,'two'),1,head,1)
        self.assertEqual(owner.observeArchive(command)['capacity']['charged_bytes'],RESERVATION_BYTES)
        with self.assertRaisesRegex(ContractError,'UNSUPPORTED_PROFILE'):
            FeedAtomOwner(owner.path,owner.storage,owner.access,capacity=self.policy)
        self.revoked=True
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):owner.observeArchive(command)
    def test_real_process_kills_preserve_reservation_file_and_activation(self):
        refs=[self.write(i)['ref'] for i in range(3)];through=self.owner().head(SCOPE)
        for index,stage in enumerate(('after_archive_reservation','after_archive_file_publish','after_archive_activation')):
            with self.subTest(stage=stage):
                ctx=multiprocessing.get_context('fork');reader,writer=ctx.Pipe(False)
                command=Mutation(SCOPE,'kill-'+str(index))
                def work():
                    reader.close()
                    def hook(name):
                        if name==stage:writer.send(name);signal.pause()
                    self.owner(hook).publishArchive(command,index,through,1)
                process=ctx.Process(target=work);process.start();writer.close()
                try:
                    self.assertTrue(reader.poll(5));self.assertEqual(reader.recv(),stage)
                    os.kill(process.pid,signal.SIGKILL);process.join(5);self.assertEqual(process.exitcode,-9)
                    owner=self.owner();before=owner.observeArchive(command)
                    sealed=owner.publishArchive(command,index,through,1);after=owner.observeArchive(command)
                    self.assertEqual(before['capacity']['charged_bytes'],after['capacity']['charged_bytes'])
                    self.assertEqual(before['archive']['intent'],sealed['intent'])
                    self.assertEqual(owner.get(refs[index]).bytes,str(index).encode())
                finally:
                    if process.is_alive():process.kill();process.join()
                    reader.close();process.close()
    def test_reserved_segment_fences_overlap_and_revocation_does_not_activate(self):
        owner=self.owner();ref=self.write(1,owner)['ref'];head=owner.head(SCOPE)
        def stop(stage):
            if stage=='after_archive_file_publish':raise InterruptedError('file committed')
        command=Mutation(SCOPE,'reserved')
        with self.assertRaises(InterruptedError):self.owner(stop).publishArchive(command,0,head,1)
        self.assertEqual(owner.observeArchive(command)['archive']['state'],'reserved')
        with self.assertRaisesRegex(ContractError,'CONFLICT'):owner.publishArchive(Mutation(SCOPE,'overlap'),0,head,1)
        self.denied.add('publishArchive')
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):owner.publishArchive(command,0,head,1)
        self.assertEqual(owner.observeArchive(command)['archive']['state'],'reserved')
        self.assertEqual(owner.get(ref).bytes,b'1') # Not activated: original hot placement remains.
        self.denied.clear();owner.publishArchive(command,0,head,1)

    def test_authority_change_after_file_commit_leaves_activation_reserved(self):
        owner=self.owner();self.write(1,owner);through=owner.head(SCOPE);command=Mutation(SCOPE,'raced')
        def revoke(stage):
            if stage=='after_archive_file_publish':self.denied.add('get')
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):self.owner(revoke).publishArchive(command,0,through,1)
        observed=owner.observeArchive(command)
        self.assertEqual(observed['archive']['state'],'reserved')
        self.assertEqual(observed['capacity']['charged_bytes'],RESERVATION_BYTES)


class RealDeTTaArchive(unittest.TestCase):
    def test_actual_backend_acceptance_then_owner_archive_read_after_reopen(self):
        import tempfile
        from fusion.adapters.detta_layout import storage,LAYOUT
        binary=Path(__file__).resolve().parents[1]/'artifacts/detta-build/target/debug/fusion-detta-adapter'
        if not binary.is_file():self.skipTest('Pinned real DeTTa adapter unavailable')
        with tempfile.TemporaryDirectory(prefix='integrated-real-archive-') as directory:
            root=Path(directory)
            def authorize(scope,operation):require(scope==SCOPE,'UNAUTHORIZED');return 'A'
            def owner():return FeedAtomOwner(root/'feed.sqlite',storage(str(binary),root/'payloads',LAYOUT),SimpleNamespace(authorize=authorize),archive=DEFAULT)
            feed=owner();original=feed.create(Mutation(SCOPE,'native-backend'),'application/synthetic',b'actual DeTTa before sealed archive')
            self.assertEqual(original['receipt']['provider'],'detta-local-rs/1')
            self.assertEqual(feed.get(original['ref']).bytes,b'actual DeTTa before sealed archive')
            head=feed.head(SCOPE);command=Mutation(SCOPE,'sealed');sealed=feed.publishArchive(command,0,head,1)
            reopened=owner()
            with patch.object(reopened.storage,'get',side_effect=AssertionError('archive fallback')):
                self.assertEqual(reopened.get(original['ref']).bytes,b'actual DeTTa before sealed archive')
            self.assertEqual(reopened.publishArchive(command,0,head,1),sealed)
            self.assertEqual(reopened.head(SCOPE),head)

if __name__=='__main__':unittest.main()
