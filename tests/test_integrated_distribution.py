"""Authored OCI byte fixtures; no containers, models or cluster activity."""
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from fusion.contracts import ContractError, canonical, digest
from integration.single_node.reference_artifacts import verify
from sdk.test_preview_distribution import FixtureDistribution
from sdk import test_image_inventory as fixtures
from sdk.image_inventory import inventory


def tar(path, entries):
    with tarfile.open(path, 'w') as stream:
        for name, raw in entries.items():
            member = tarfile.TarInfo(name); member.size = len(raw)
            stream.addfile(member, io.BytesIO(raw))


class LayeredDistribution(unittest.TestCase):
    def test_verifier_requires_exact_declared_base_and_resolves_configs(self):
        with tempfile.TemporaryDirectory() as directory:
            f = FixtureDistribution(Path(directory) / 'dist')
            metadata = f.read('images.json')
            configs = {r['configuration'][7:] for r in f.manifest['images'].values()}
            tar(f.root / 'base.tar', {'blobs/sha256/' + k: v for k, v in f.blobs.items() if k in configs})
            tar(f.root / 'images.tar', {'blobs/sha256/' + k: v for k, v in f.blobs.items() if k not in configs})
            f.register('base.tar'); f.register('images.tar')
            metadata.update(archive_format='verified-oci-layer-set/1',
                archive_sha256=digest((f.root / 'images.tar').read_bytes()),
                base_archive=dict(archive_sha256=digest((f.root / 'base.tar').read_bytes()),
                                  archive_bytes=(f.root / 'base.tar').stat().st_size))
            f.write('images.json', canonical(metadata)); f.manifest['image_base_archive'] = 'base.tar'
            self.assertEqual(verify(f.save())['status'], 'OFFLINE_VERIFIED')
            (f.root / 'base.tar').write_bytes(b'wrong pinned base')
            f.register('base.tar')  # Even rebinding the outer file cannot change the image pin.
            with self.assertRaisesRegex(ContractError, 'CONFLICT'): verify(f.save())

    def test_inventory_scans_base_layers_and_rejects_unbound_substitution(self):
        fixture = fixtures.ImageInventoryTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        raw_layer = fixtures.layer([('var/lib/dpkg/status', fixtures.dpkg())])
        fixture.archive([[raw_layer]])
        original = inventory(fixture.path)
        with tarfile.open(fixture.path) as archive:
            entries = {m.name: archive.extractfile(m).read() for m in archive if m.isfile()}
        base = fixture.path.parent / 'base.tar'
        layer_name = 'blobs/sha256/' + digest(raw_layer)
        tar(base, {layer_name: entries.pop(layer_name)})
        tar(fixture.path, entries)
        expected = dict(archive_format='verified-oci-layer-set/1',
            archive_sha256=digest(fixture.path.read_bytes()), archive_bytes=fixture.path.stat().st_size,
            base_archive=dict(archive_sha256=digest(base.read_bytes()), archive_bytes=base.stat().st_size),
            images=original['images'])
        pin = fixture.path.parent / 'images.json'; pin.write_bytes(canonical(expected))
        value = inventory(fixture.path, expected_images=pin, base_archive=base)
        self.assertEqual(value['images'], original['images'])
        self.assertEqual(value['container_starts'], 0)
        with self.assertRaisesRegex(ValueError, 'required base archive missing'):
            inventory(fixture.path, expected_images=pin)
        with self.assertRaisesRegex(ValueError, 'requires publication binding'):
            inventory(fixture.path, base_archive=base)
        base.write_bytes(base.read_bytes() + b'drift')
        with self.assertRaisesRegex(ValueError, 'base archive binding mismatch'):
            inventory(fixture.path, expected_images=pin, base_archive=base)


if __name__ == '__main__': unittest.main()
