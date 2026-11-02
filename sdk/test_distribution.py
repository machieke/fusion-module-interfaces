"""Tiny authored assembly inputs; no real build, Helm, image or runtime use."""
import json
import ast
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch
import tarfile
import zipfile

from fusion.contracts import ContractError, canonical, digest
from integration.single_node.reference_artifacts import verify
from sdk.distribution import PUBLIC_FILES, ROOT, assemble
from sdk.inventory import inventory
from sdk.test_preview_distribution import FixtureDistribution


class DistributionAssemblyFixtures(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='fusion-assembly-fixture-')
        self.root = Path(self.temporary.name)
        self.original = FixtureDistribution(self.root / 'build')
        self.build = self.original.root
        self.source = self.root / 'source'
        self.source.mkdir()
        self.wheels = self.build / 'wheelhouse'
        self.output = self.root / 'packet'
        for name in PUBLIC_FILES:
            path = self.source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'explicit non-executable public source fixture\n')
        for role, name in self.original.source_paths.items():
            path = self.source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(self.original.source_bytes[role])
        imported = self.original.read('images.json')
        for item in imported['images']:
            item['source_package'] = 'source/' + item['kind'] + '.json'
            package = self.original.read(item['source_package'])
            package.update(kind=item['kind'], parent='fixture-cache/' + item['kind'] + ':fixture',
                           parent_config='sha256:' + 'a' * 64)
            (self.build / item['source_package']).write_bytes(canonical(package))
        imported.update(source_export_verification='PASS',
                        source_manifest_sha256=digest(canonical(self.original.manifest['tested_source'])),
                        archive_bytes=(self.build / 'images.tar').stat().st_size)
        (self.build / 'images.json').write_bytes(canonical(imported))
        for role in ('client', 'provider', 'operator'):
            record = self.original.build[role]
            path = self.wheels / record['file']
            with zipfile.ZipFile(path, 'a') as archive:
                archive.writestr('fixture_' + role + '-0.0.0.dist-info/METADATA',
                                 'Metadata-Version: 2.1\nName: fixture-' + role + '\nVersion: 0.0.0\n')
            record['sha256'] = digest(path.read_bytes())
        pins = []
        for index in range(5):
            name = 'fixture_extra_' + str(index) + '-0.0.0-py3-none-any.whl'
            path = self.wheels / name
            with zipfile.ZipFile(path, 'w') as archive:
                archive.writestr('fixture_extra_' + str(index) + '-0.0.0.dist-info/METADATA',
                                 'Metadata-Version: 2.1\nName: fixture-extra-' + str(index) + '\nVersion: 0.0.0\n')
            pins.append(dict(file=name, bytes=path.stat().st_size, sha256=digest(path.read_bytes())))
        (self.source / 'sdk/operator-wheel-inputs.json').write_bytes(canonical(dict(files=pins)))
        (self.wheels / 'build-manifest.json').write_bytes(canonical(self.original.build))
        (self.wheels / 'dependency-inventory.json').write_bytes(canonical(inventory(self.wheels.glob('*.whl'))))

    def tearDown(self):
        self.temporary.cleanup()

    def helm(self, command, **kwargs):
        self.assertEqual(command, ['helm', 'package', str(self.source / 'deploy/helm/omega-fusion'),
                                   '--destination', str(self.output)])
        self.assertTrue(kwargs['check'])
        (self.output / 'omega-fusion-0.0.0.tgz').write_bytes(b'authored unused chart fixture')

    def run_assembly(self):
        with patch('sdk.distribution.subprocess.run', side_effect=self.helm) as called:
            with patch('sdk.distribution.shutil.which', return_value=None):
                result = assemble(self.build, self.wheels, self.output, source_root=self.source)
        self.assertEqual(called.call_count, 1)
        return result

    def test_fixture_packet_is_offline_verified_and_positive_listed(self):
        private = self.source / 'private/operator-secret.key'
        private.parent.mkdir(); private.write_bytes(b'fixture secret must remain excluded')
        result = self.run_assembly()
        self.assertEqual(result['status'], 'OFFLINE_VERIFIED')
        self.assertEqual(result['additional_live_generations'], 0)
        value = verify(self.output / 'distribution.json')
        self.assertEqual(value['manifest_sha256'], result['sha256'])
        self.assertEqual((self.output / 'images.tar').stat().st_ino, (self.build / 'images.tar').stat().st_ino)
        manifest = json.loads((self.output / 'distribution.json').read_bytes())
        self.assertEqual(manifest['project_license'], 'NOASSERTION')
        self.assertEqual(set(manifest['images']), {'base', 'caller', 'embedding'})
        self.assertNotIn('generative', manifest['images'])
        with tarfile.open(self.output / 'source.tar.gz') as archive:
            self.assertEqual(set(archive.getnames()), set(PUBLIC_FILES) | set(self.original.source_paths.values()))
            self.assertNotIn('private/operator-secret.key', archive.getnames())
        self.assertFalse((self.output / 'private').exists())
        self.assertEqual(len(list((self.output / 'wheelhouse').glob('*.whl'))), 8)

    def test_profiles_use_existing_generator_with_disabled_native_consumers(self):
        self.run_assembly()
        for mode in ('minimal', 'memory', 'combined'):
            values = json.loads((self.output / 'profiles' / (mode + '.yaml')).read_bytes())
            self.assertEqual(values['preview']['model_boundary'], 'RECORDED_FIXTURE')
            self.assertEqual(values['preview']['scope'], 'synthetic-distribution-' + mode)
            self.assertNotIn('futureLive', values)
            self.assertNotIn('chain', values['preview'])
            for role in ('omega-agent', 'omega-agent-b'):
                self.assertFalse(values['components'][role]['config']['nativeEnabled'])
                self.assertFalse(values['components'][role]['config']['workerEnabled'])
            self.assertEqual('memory' in values['preview'], mode != 'minimal')
            self.assertEqual('cognition' in values['preview'], mode == 'combined')

    def test_source_drift_refuses_before_output_or_helm(self):
        path = self.source / self.original.source_paths['operator']
        path.write_bytes(b'changed source fixture')
        with patch('sdk.distribution.subprocess.run') as helm:
            with self.assertRaises(ContractError):
                assemble(self.build, self.wheels, self.output, source_root=self.source)
        self.assertFalse(self.output.exists()); helm.assert_not_called()

    def test_extra_wheel_and_unlisted_chart_file_refuse(self):
        extra = self.wheels / 'unapproved-0.0.0-py3-none-any.whl'
        extra.write_bytes(b'unapproved fixture')
        with self.assertRaises(ContractError):
            assemble(self.build, self.wheels, self.output, source_root=self.source)
        extra.unlink()
        (self.source / 'deploy/helm/omega-fusion/unlisted.key').write_bytes(b'excluded fixture')
        with self.assertRaises(ContractError):
            assemble(self.build, self.wheels, self.output, source_root=self.source)
        self.assertFalse(self.output.exists())

    def test_changed_wheel_inventory_and_existing_output_refuse(self):
        path = self.wheels / 'dependency-inventory.json'
        value = json.loads(path.read_bytes()); value['hosted_ci'] = 'invented-pass'
        path.write_bytes(canonical(value))
        with self.assertRaises(ContractError):
            assemble(self.build, self.wheels, self.output, source_root=self.source)
        self.assertFalse(self.output.exists())
        self.output.mkdir()
        with self.assertRaises(ContractError):
            assemble(self.build, self.wheels, self.output, source_root=self.source)

    def test_symbolic_public_source_refuses(self):
        path = self.source / 'sdk/README.md'
        path.unlink(); path.symlink_to(self.source / 'sdk/OPERATOR.md')
        with self.assertRaises(ContractError):
            assemble(self.build, self.wheels, self.output, source_root=self.source)
        self.assertFalse(self.output.exists())


class PublicRunbookInputs(unittest.TestCase):
    def test_runbook_python_entrypoints_are_image_sources_or_explicit_public_files(self):
        # Source-package fusion/integration membership is checked again against
        # actual image manifests by assemble(). This static test executes no CLI.
        text = (ROOT/'docs/phase2/runbook.md').read_text()
        modules = set(re.findall(r'-m ((?:examples|integration|sdk)\.[A-Za-z0-9_.]+)', text))
        self.assertTrue(modules)
        for module in modules:
            name = module.replace('.', '/') + '.py'
            with self.subTest(module=module):
                self.assertTrue((ROOT/name).is_file())
                self.assertTrue(name.startswith(('fusion/', 'integration/')) or name in PUBLIC_FILES)
        for name in ('examples/preview_single_agent_values.py',
                     'examples/preview_single_agent_qualification.py',
                     'examples/preview_restore_qualification.py',
                     'examples/preview_shared_source_qualification.py',
                     'examples/preview_storage_layout_qualification.py',
                     'examples/preview_handoff_recovery.py',
                     'examples/preview_chain_observer.py'):
            self.assertIn(name, PUBLIC_FILES)

    def test_selected_example_tests_retain_their_direct_test_dependencies(self):
        selected = ('tests/test_phase2_single_agent_values.py',
                    'tests/test_phase2_single_agent_qualification.py',
                    'tests/test_phase2_restore_qualification.py',
                    'tests/test_phase2_shared_source_qualification.py',
                    'tests/test_phase2_detta_layout.py',
                    'tests/test_phase2_handoff_recovery.py',
                    'tests/test_phase2_chain_observer.py')
        for name in selected:
            self.assertIn(name, PUBLIC_FILES)
            for node in ast.walk(ast.parse((ROOT/name).read_text())):
                if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith('tests.'):
                    dependency = node.module.replace('.', '/') + '.py'
                    self.assertIn(dependency, PUBLIC_FILES, name + ' imports ' + dependency)

    def test_shipped_fast_ci_lanes_keep_their_test_and_profile_source_inputs(self):
        tree = ast.parse((ROOT/'integration/single_node/reference_ci.py').read_text())
        fast = next(ast.literal_eval(node.value) for node in tree.body
                    if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name)
                    and target.id == 'FAST' for target in node.targets))
        selected = {p.relative_to(ROOT).as_posix() for p in (ROOT/'tests').glob('test_phase2_*.py')}
        selected.update(name.replace('.', '/') + '.py' for name in fast)
        pending = list(selected)
        while pending:
            name = pending.pop()
            self.assertIn(name, PUBLIC_FILES)
            for node in ast.walk(ast.parse((ROOT/name).read_text())):
                if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith('tests.'):
                    dependency = node.module.replace('.', '/') + '.py'
                    if (ROOT/dependency).is_file() and dependency not in selected:
                        selected.add(dependency); pending.append(dependency)
        for stem in ('values', 'memory-values', 'workflow-values', 'cognitive-values', 'chain-values'):
            self.assertIn('deploy/single-node/' + stem + '.yaml', PUBLIC_FILES)


if __name__ == '__main__':
    unittest.main()
