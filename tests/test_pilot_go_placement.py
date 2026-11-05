"""Static artifact/plan checks with explicitly synthetic OCI bytes and pod ports."""
import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
from fusion.contracts import ContractError
from fusion.registry import selection_token
from fusion.reference_inspect_contracts import descriptor
from integration.single_node.pilot_go_values import initial,replace
from integration.single_node.placement import provider_source
from tests.test_pilot_provider_distribution import ProviderBundle

class GoPlacement(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.bundle=ProviderBundle(Path(self.temp.name)/'fixture')
        self.image=dict(kind='inspect-go',repository=self.bundle.manifest['image']['repository'],
            manifest_digest=self.bundle.manifest['image']['manifest'],source_manifest_sha256=self.bundle.kit['source_manifest_sha256'])
        self.plan=dict(source_manifest_sha256='a'*64)
        self.checked=dict(repository=self.image['repository'],manifest=self.image['manifest_digest'],configuration='sha256:'+'b'*64,
            source_manifest_sha256=self.image['source_manifest_sha256'],contract=selection_token(descriptor()),
            source_package='kit/manifest.json',manifest_sha256='c'*64)
    def test_independent_attestation_never_executes_python_inside_go(self):
        op=Mock();op.k.side_effect=AssertionError('no interpreter in scratch image')
        with patch('integration.single_node.pilot_provider_image.verify',return_value=self.checked):
            source,method=provider_source(op,'fusion-inspect-go',self.image,self.plan,{'inspect-go':self.bundle.save()})
        self.assertEqual(source,self.image['source_manifest_sha256']);self.assertIn('INDEPENDENT_GO',method);op.k.assert_not_called()
    def test_missing_artifact_wrong_source_image_or_contract_refused(self):
        op=Mock()
        with self.assertRaisesRegex(ContractError,'NOT_AVAILABLE'):provider_source(op,'fusion-inspect-go',self.image,self.plan)
        for field,value in [('manifest','sha256:'+'f'*64),('source_manifest_sha256','f'*64),('contract','f'*64)]:
            with self.subTest(field=field),patch('integration.single_node.pilot_provider_image.verify',return_value={**self.checked,field:value}):
                with self.assertRaises(ContractError):provider_source(op,'fusion-inspect-go',self.image,self.plan,{'inspect-go':self.bundle.save()})
        op.k.assert_not_called()
    def test_python_packaged_source_path_preserved(self):
        op=Mock();op.k.return_value='a'*64+'\n'
        source,method=provider_source(op,'omega-agent',dict(kind='caller'),self.plan)
        self.assertEqual(source,'a'*64);self.assertEqual(method,'PACKAGED_SOURCE_AND_POD_IMAGE_ID');op.k.assert_called_once()
    def test_initial_keeps_default_selection_and_replacement_only_changes_composition(self):
        images=dict(source_manifest_sha256='a'*64,source_export_verification='PASS',images=[dict(kind=k,repository='fixture/'+k,
            local_tag='fixture/'+k+':fixture',manifest_digest='sha256:'+str(i)*64) for i,k in enumerate(('base','caller','embedding'),1)])
        with patch('integration.single_node.pilot_go_values.verify',return_value=self.checked):
            values,mixed=initial(images,'fixture-only','synthetic-go-plan-fixture','omega-ref-pilot-go-plan-fixture')
        self.assertNotIn('execution_descriptor',values['preview']['inspection'])
        self.assertIn('immutable-commit-feed/2',values['preview']['inspection']['reference_storage_descriptor']['profiles'])
        self.assertNotIn('writer_fence',values['preview']['pilot'])
        self.assertTrue(all('writerAuthoritySecret' not in x for x in values['components'].values()))
        self.assertEqual(len(images['images']),3);self.assertEqual(len(mixed['images']),4)
        replacement=replace(values)
        self.assertEqual(replacement['preview']['inspection']['additional_template']['service'],'fusion-inspect-go')
        self.assertEqual(replacement['preview']['agents'],values['preview']['agents'])
        self.assertEqual(replacement['components'],values['components'])
        self.assertEqual(replacement['preview']['sustained']['provider_registry'],values['preview']['sustained']['provider_registry'])
        self.assertNotIn('additional_template',values['preview']['inspection'])

if __name__=='__main__':unittest.main()
