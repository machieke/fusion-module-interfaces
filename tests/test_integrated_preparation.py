"""Real filesystem/atomic publication; native validator and overlay builder fixtures."""
import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch,Mock
from fusion.contracts import canonical,ContractError,digest
from integration.neoclaw import prepared_startup as p


class Preparation(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        for name in ('fusion','integration'):(self.root/name).mkdir()
        (self.root/'fusion/source.py').write_text('SOURCE=1\n')
        (self.root/'runtime.json').write_text('{}');(self.root/'build.json').write_text('{}')
        self.package=self.root/'package.json';self.package.write_bytes(canonical(dict(source=p.source_map(self.root))))
        self.client=self.root/'client.json';self.client.write_bytes(canonical(dict(credential='old-token',principal='A')))
        self.app=self.root/'application.json';self.app.write_bytes(canonical(dict(runtime=str(self.root/'runtime.json'),workdir=str(self.root/'native'),caller_config=str(self.client),native_preparation=dict(profile=p.PROFILE,package_file=str(self.package),immutability='native-readonly-mount'))))
        self.builder=Mock(side_effect=self.build)
        self.addCleanup(patch.stopall)
        patch.object(p,'ROOT',self.root).start();patch.object(p,'NativeTruthDeduction',return_value=Mock(runtime={})).start()
    def build(self,config,overlay_directory):
        d=overlay_directory;(d/'start.metta').write_text('SOURCE '+str(d))
        (d/'startup.json').write_bytes(canonical(dict(overlay_hashes={'start.metta':digest((d/'start.metta').read_bytes())})))
        return ['native',str(d/'start.metta')],{'NATIVE_SOURCE':'only'},d
    def run_prepare(self):return p.prepare(self.app,self.builder)
    def test_publication_reuses_exact_readonly_entry_and_current_tokens_are_not_cached(self):
        first=self.run_prepare();target=next((self.root/'native/prepared').iterdir());self.assertTrue((target/'prepared.json').exists())
        original={x.name:x.stat().st_mtime_ns for x in target.iterdir()}
        self.client.write_bytes(canonical(dict(credential='rotated-token',principal='A')))
        second=self.run_prepare();self.assertEqual(first,second);self.assertEqual(self.builder.call_count,1)
        self.assertEqual(original,{x.name:x.stat().st_mtime_ns for x in target.iterdir()})
        self.assertNotIn(b'token',(target/'prepared.json').read_bytes());self.assertIn('--ro-bind',first[0])
    def test_source_or_unexpected_file_refuses_even_with_ready_cache(self):
        self.run_prepare();(self.root/'fusion/unexpected.py').write_text('DRIFT=1')
        with self.assertRaisesRegex(ContractError,'UNSUPPORTED_PROFILE'):self.run_prepare()
        self.assertEqual(self.builder.call_count,1)
    def test_corrupt_or_symlinked_entry_refuses_without_rebuilding(self):
        self.run_prepare();target=next((self.root/'native/prepared').iterdir());path=target/'start.metta'
        path.chmod(0o644);path.write_text('CORRUPTION');path.chmod(0o444)
        with self.assertRaisesRegex(ContractError,'CONFLICT'):self.run_prepare()
        target.chmod(0o755);path.unlink();path.symlink_to(self.root/'fusion/source.py')
        with self.assertRaisesRegex(ContractError,'CONFLICT'):self.run_prepare()
        self.assertEqual(self.builder.call_count,1)
    def test_incomplete_entry_never_becomes_ready(self):
        def fail(*a,**k):raise OSError('injected before publication')
        self.builder.side_effect=fail
        with self.assertRaises(OSError):self.run_prepare()
        self.assertTrue(all(x.name.startswith('.pending-') for x in (self.root/'native/prepared').iterdir()))
        self.builder.side_effect=self.build;self.run_prepare()
        self.assertEqual(len([x for x in (self.root/'native/prepared').iterdir() if not x.name.startswith('.')]),1)

if __name__=='__main__':unittest.main()
