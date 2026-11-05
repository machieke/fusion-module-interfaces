"""Authored OCI/ELF assembly fixtures, distinct from the actual pilot export."""
import json
import tarfile
import unittest
from unittest.mock import patch
from fusion.contracts import ContractError,canonical
from sdk import test_distribution as baseline
from sdk.distribution import assemble
from integration.single_node.reference_artifacts import verify
from tests.test_pilot_provider_distribution import ProviderBundle


class PilotAssembly(unittest.TestCase):
    def setUp(self):
        self.base=baseline.DistributionAssemblyFixtures();self.base.setUp()
        self.addCleanup(self.base.tearDown);b=self.base
        b.original.build['operator_profile']='operator-pilot-package/1'
        (b.wheels/'build-manifest.json').write_bytes(canonical(b.original.build))
        self.extra='docs/operator-pilot/runbook.md';p=b.source/self.extra;p.parent.mkdir(parents=True);p.write_text('Explicit sanitized fixture documentation')
        (b.source/'sdk/pilot-distribution-inputs.json').write_bytes(canonical(dict(profile='operator-pilot-public-inputs/1',files=[self.extra])))
    def test_exact_extra_profile_and_independent_go_artifact_are_packaged(self):
        b=self.base;provider=ProviderBundle(b.root/'independent')
        with patch('sdk.distribution.subprocess.run',side_effect=b.helm),patch('sdk.distribution.shutil.which',return_value=None):
            result=assemble(b.build,b.wheels,b.output,source_root=b.source,reference_provider=provider.save())
        self.assertEqual(result['status'],'OFFLINE_VERIFIED')
        checked=verify(b.output/'distribution.json');self.assertIn('inspect-go',checked['images'])
        manifest=json.loads((b.output/'distribution.json').read_bytes())
        self.assertEqual(len(manifest['profile_files']),6)
        self.assertEqual(manifest['operator_profile'],'operator-pilot-package/1')
        self.assertEqual((b.output/self.extra).read_bytes(),(b.source/self.extra).read_bytes())
        with tarfile.open(b.output/'source.tar.gz') as archive:self.assertIn(self.extra,archive.getnames())
        # A legacy packet cannot silently select the expanded profile bound.
        manifest.pop('operator_profile');raw=canonical(manifest);(b.output/'distribution.json').write_bytes(raw)
        from fusion.contracts import digest
        (b.output/'distribution.sha256').write_text(digest(raw)+'\n')
        with self.assertRaises(ContractError):verify(b.output/'distribution.json')
    def test_unapproved_public_symlink_and_incomplete_provider_refuse(self):
        b=self.base;outside=b.root/'private';outside.write_bytes(b'fixture secret')
        selected=b.source/self.extra;selected.unlink();selected.symlink_to(outside)
        with self.assertRaises(ContractError):assemble(b.build,b.wheels,b.output,source_root=b.source)
        self.assertFalse(b.output.exists())

    def test_extended_publication_is_explicit_and_retains_all_selected_files(self):
        b=self.base
        names=['evidence/operator-pilot/retained-%04d.json'%i for i in range(513)]
        for name in names:
            path=b.source/name;path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(canonical(dict(classification='AUTHORED_FIXTURE',name=name)))
        selection=b.source/'sdk/pilot-distribution-inputs.json'
        selection.write_bytes(canonical(dict(profile='operator-pilot-public-inputs/1',files=names)))
        with self.assertRaises(ContractError):assemble(b.build,b.wheels,b.output,source_root=b.source)
        self.assertFalse(b.output.exists())
        selection.write_bytes(canonical(dict(profile='operator-pilot-public-inputs/2',files=names)))
        with patch('sdk.distribution.subprocess.run',side_effect=b.helm),patch('sdk.distribution.shutil.which',return_value=None):
            result=assemble(b.build,b.wheels,b.output,source_root=b.source)
        self.assertEqual(result['status'],'OFFLINE_VERIFIED')
        registered={row['path'] for row in json.loads((b.output/'distribution.json').read_bytes())['files']}
        self.assertTrue(set(names)<=registered)
        with tarfile.open(b.output/'source.tar.gz') as archive:
            self.assertTrue(set(names)<=set(archive.getnames()))
        for name in names:self.assertEqual((b.output/name).read_bytes(),(b.source/name).read_bytes())

    def test_extended_publication_refuses_unbounded_or_malformed_selection(self):
        b=self.base;selection=b.source/'sdk/pilot-distribution-inputs.json'
        for value in [
            dict(profile='operator-pilot-public-inputs/2',files=['evidence/%d.json'%i for i in range(2049)]),
            dict(profile='operator-pilot-public-inputs/2',files=[self.extra,self.extra]),
            dict(profile='operator-pilot-public-inputs/2',files=[{'path':self.extra}]),
            dict(profile='operator-pilot-public-inputs/2',files=self.extra),
            dict(profile='operator-pilot-public-inputs/3',files=[self.extra]),
            dict(profile='operator-pilot-public-inputs/2',files=[self.extra],include_directory='private'),
            dict(profile='operator-pilot-public-inputs/2',files=['../private']),
        ]:
            with self.subTest(value=str(value)[:120]):
                selection.write_bytes(canonical(value))
                with self.assertRaises(ContractError):assemble(b.build,b.wheels,b.output,source_root=b.source)
                self.assertFalse(b.output.exists())

if __name__=='__main__':unittest.main()
