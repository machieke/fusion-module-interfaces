"""Disposable populated stores only; no live migration or repair claim."""
import copy,json,shutil,sqlite3,tempfile,time,unittest
from dataclasses import replace
from pathlib import Path
from fusion.contracts import ContractError,canonical
from fusion.cognition import open_cognition
from fusion.adapters.fixture_atoms import FileAtomFixture
from fusion.ports import Mutation
from tests.m3_support import CognitionHarness,SCOPE,RefusingKernelFixture
from tests.m3_1_support import ClosureHarness
from tests.m2_support import GuardOnlyFixture

def contents(root):
    result={}
    for path in root.rglob('*'):
        if not path.is_file() or path.suffix in ('.lock',) or path.name.endswith(('-shm','-wal')):continue
        if path.suffix=='.sqlite':
            with sqlite3.connect(path) as db:result[str(path.relative_to(root))]='\n'.join(db.iterdump())
        else:result[str(path.relative_to(root))]=path.read_bytes()
    return result

class Compatibility(unittest.TestCase):
    def test_old_populated_copies_reject_new_profile_keep_old_replay(self):
        for provider in ('sqlite','atomic-file-fixture'):
            with self.subTest(provider=provider):
                old=CognitionHarness(provider=provider)
                try:
                    entry,_,episode=old.generated();old.stimulate(entry)
                    request=old.request(old.workset([entry]),candidates=1);result=old.controller.step(request)
                    original=contents(old.modules.root)
                    with tempfile.TemporaryDirectory() as temp:
                        destination=Path(temp)/'copy';shutil.copytree(old.root,destination)
                        config=copy.deepcopy(old.config);config['private_root']=str(destination/'private');config['shared_roots']=[str(destination/'shared')]
                        path=destination/'private-config.json';path.write_bytes(canonical(config))
                        def reopen():return open_cognition(path,old.credential,SCOPE,atom_fixture=FileAtomFixture(str(destination/'private/files'),str(destination/'private/bytes')),
                            math_fixture=GuardOnlyFixture(),kernel_fixture=RefusingKernelFixture())
                        compatible=reopen();self.assertEqual(compatible.controller.step(request),result)
                        self.assertEqual(len(compatible.episodes.pendingEvidence(episode,16)),5)
                        before=contents(destination/'private')
                        with self.assertRaises(ContractError) as error:ClosureHarness(destination,provider=provider)
                        self.assertEqual(error.exception.code,'UNSUPPORTED_PROFILE')
                        self.assertEqual(contents(destination/'private'),before)
                        path.write_bytes(canonical(config));self.assertEqual(reopen().controller.step(request),result)
                    self.assertEqual(contents(old.modules.root),original)
                finally:old.close()

    def test_bounded_reconciliation_commands_and_live_descriptor_binding(self):
        h=ClosureHarness()
        try:
            entry,_,_=h.generated();h.stimulate(entry);request=h.request(h.workset([entry]),candidates=1)
            execution=h.controller.step(request)
            for malformed in (None,{},False):
                with self.assertRaises(ContractError):h.controller.readProgress(malformed)
                with self.assertRaises(ContractError):h.controller.reconcile(Mutation(SCOPE,'malformed'),malformed,1)
            for index in range(128):result=h.controller.reconcile(Mutation(SCOPE,'r/'+str(index)),request,1)
            self.assertEqual(result['execution'],execution)
            with self.assertRaises(ContractError) as error:h.controller.reconcile(Mutation(SCOPE,'overflow'),request,1)
            self.assertEqual(error.exception.code,'OVERLOADED')
            self.assertEqual(h.controller.reconcile(Mutation(SCOPE,'r/0'),request,1),result)
            for descriptor in h.config['cognition_descriptors']:
                if descriptor['interface']=='attention':descriptor['implementation_version']='incompatible'
            h.save()
            with self.assertRaises(ContractError):h.controller.reconcile(Mutation(SCOPE,'r/0'),request,1)
        finally:h.close()

if __name__=='__main__':unittest.main()
