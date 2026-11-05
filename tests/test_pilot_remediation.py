"""Real offline package-metadata checks; no provider imports or model runtime."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import venv

from integration.single_node.pilot_remediation import check_dependencies

ROOT = Path(__file__).resolve().parents[1]


class DependencyClosure(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manager_root = tempfile.TemporaryDirectory()
        venv.EnvBuilder(with_pip=True).create(cls.manager_root.name)
        cls.manager = str(Path(cls.manager_root.name) / 'bin/python')

    @classmethod
    def tearDownClass(cls):
        cls.manager_root.cleanup()

    def check(self, version):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            venv.EnvBuilder(with_pip=False).create(root)
            site = root / 'lib' / ('python' + '.'.join(map(str, sys.version_info[:2]))) / 'site-packages'
            first = site / 'pilot_metadata_consumer-1.0.dist-info'
            first.mkdir()
            (first / 'METADATA').write_text(
                'Metadata-Version: 2.1\nName: pilot-metadata-consumer\nVersion: 1.0\n'
                'Requires-Dist: pilot-metadata-provider==2.0\n')
            if version is not None:
                provider = site / ('pilot_metadata_provider-' + version + '.dist-info')
                provider.mkdir()
                (provider / 'METADATA').write_text(
                    'Metadata-Version: 2.1\nName: pilot-metadata-provider\nVersion: ' + version + '\n')
            check_dependencies(self.manager, str(root / 'bin/python'),
                {**os.environ, 'PIP_NO_INDEX': '1', 'PIP_DISABLE_PIP_VERSION_CHECK': '1'})

    def test_matching_installed_metadata_passes_without_importing_packages(self):
        self.check('2.0')

    def test_incompatible_installed_version_refuses(self):
        with self.assertRaises(subprocess.CalledProcessError) as error:
            self.check('1.0')
        self.assertIn('pilot-metadata-consumer', error.exception.output)
        self.assertIn('1.0', error.exception.output)

    def test_missing_dependency_refuses(self):
        with self.assertRaises(subprocess.CalledProcessError) as error:
            self.check(None)
        self.assertIn('pilot-metadata-consumer', error.exception.output)
        self.assertIn('not installed', error.exception.output)

    def test_selected_leaf_requirements_and_historical_mismatch_remain_distinct(self):
        from packaging.requirements import Requirement
        current = json.loads((ROOT / 'integration/neoclaw/pilot-leaf-remediation.json').read_bytes())
        old = json.loads((ROOT / 'integration/neoclaw/provenance/pilot-leaf-remediation09.json').read_bytes())
        selected = {row['name']: row['version'] for row in current['packages']}
        historical = {row['name']: row['version'] for row in old['packages']}
        self.assertEqual({name for name in selected if selected[name] != historical[name]}, {'httpcore2', 'idna'})
        examined = 0
        for row in current['packages']:
            for text in row['requires_dist'] or []:
                requirement = Requirement(text)
                if requirement.name not in selected or (requirement.marker and not requirement.marker.evaluate({'extra': ''})):
                    continue
                examined += 1
                self.assertIn(selected[requirement.name], requirement.specifier)
        self.assertGreaterEqual(examined, 5)
        httpx = next(row for row in old['packages'] if row['name'] == 'httpx2')
        broken = [Requirement(text) for text in httpx['requires_dist']
                  if Requirement(text).name in ('httpcore2', 'idna')]
        self.assertEqual(len(broken), 2)
        self.assertTrue(all(historical[requirement.name] not in requirement.specifier for requirement in broken))


if __name__ == '__main__':
    unittest.main()
