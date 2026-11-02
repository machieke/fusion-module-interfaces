"""Small authored OCI archives only; no image execution or provider claims."""
import gzip
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

from sdk.image_inventory import Limits, inventory, sha


def layer(entries, compressed=False):
    result = io.BytesIO()
    with tarfile.open(fileobj=result, mode='w') as archive:
        for path, value in entries:
            member = tarfile.TarInfo(path)
            if isinstance(value, tuple):
                member.type = tarfile.SYMTYPE if value[0] == 'symlink' else tarfile.LNKTYPE
                member.linkname = value[1]
                archive.addfile(member)
            else:
                member.size = len(value)
                archive.addfile(member, io.BytesIO(value))
    raw = result.getvalue()
    return gzip.compress(raw) if compressed else raw


def dpkg(version='1'):
    return f'Package: example\nVersion: {version}\nArchitecture: amd64\nStatus: install ok installed\nDepends: libc6 (>= 2)\n\n'.encode()


class ImageInventoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'images.tar'

    def archive(self, images, extra=(), corrupt=False):
        blobs, manifests = {}, []

        def add(raw, media):
            digest = 'sha256:' + sha(raw)
            blobs['blobs/' + digest.replace(':', '/')] = raw
            return dict(digest=digest, size=len(raw), mediaType=media)

        for i, layers in enumerate(images):
            config = add(json.dumps(dict(architecture='amd64', os='linux', fixture=i)).encode(),
                         'application/vnd.oci.image.config.v1+json')
            descriptors = [add(raw, 'application/vnd.oci.image.layer.v1.tar' +
                               ('+gzip' if raw.startswith(b'\x1f\x8b') else '')) for raw in layers]
            manifest = add(json.dumps(dict(schemaVersion=2, config=config, layers=descriptors)).encode(),
                           'application/vnd.oci.image.manifest.v1+json')
            manifest['annotations'] = {'io.containerd.image.name': 'fixture:' + str(i)}
            manifests.append(manifest)
        if corrupt:
            name = 'blobs/' + descriptors[0]['digest'].replace(':', '/')
            blobs[name] = blobs[name][:-1] + bytes([blobs[name][-1] ^ 1])
        blobs['index.json'] = json.dumps(dict(schemaVersion=2, manifests=manifests)).encode()
        with tarfile.open(self.path, 'w') as archive:
            for name, value in list(blobs.items()) + list(extra):
                member = tarfile.TarInfo(name)
                member.size = len(value)
                archive.addfile(member, io.BytesIO(value))
        return self.path

    def test_final_dpkg_and_python_metadata_and_licenses(self):
        path = 'opt/sdk/lib/python3.12/site-packages/example-2.dist-info/'
        self.archive([[layer([
            ('var/lib/dpkg/status', dpkg()),
            (path + 'METADATA', b'Name: example\nVersion: 2\nLicense-Expression: MIT\nRequires-Dist: other>=1\nLicense-File: LICENSE\n'),
            (path + 'LICENSE', b'fixture license'),
            ('usr/share/doc/example/copyright', b'fixture copyright')]),
            layer([('var/lib/dpkg/status', dpkg('2'))])]])
        report = inventory(self.path)
        image = report['images'][0]
        package = image['os_dependencies']['packages'][0]
        self.assertEqual((package['version'], package['license_expression']), ('2', 'NOASSERTION'))
        self.assertEqual(package['license_evidence']['sha256'], sha(b'fixture copyright'))
        python = image['python_dependencies'][0]
        self.assertEqual(python['license_expression'], 'MIT')
        self.assertEqual(python['declared_dependencies'], ['other>=1'])
        self.assertEqual(python['license_evidence'][0]['sha256'], sha(b'fixture license'))
        self.assertEqual(report['vulnerability_scan'], 'NOT_RUN')
        self.assertEqual(report['generative_starts'], 0)

    def test_whiteout_removes_lower_metadata(self):
        base = 'opt/sdk/example.dist-info/'
        self.archive([[layer([(base + 'METADATA', b'Name: old\nVersion: 1\n')]),
                       layer([(base + '.wh.METADATA', b'')])]])
        self.assertEqual(inventory(self.path)['images'][0]['python_dependencies'], [])

    def test_opaque_applies_only_to_lower_files_regardless_order(self):
        base = 'opt/sdk/example.dist-info/'
        self.archive([[layer([(base + 'METADATA', b'Name: old\nVersion: 1\n'), (base + 'LICENSE', b'old')]),
                       layer([(base + 'METADATA', b'Name: new\nVersion: 2\n'), (base + '.wh..wh..opq', b'')])]])
        python = inventory(self.path)['images'][0]['python_dependencies'][0]
        self.assertEqual(python['name'], 'new')
        self.assertEqual(python['license_evidence'], [])

    def test_file_replacing_directory_removes_descendants(self):
        self.archive([[layer([('opt/sdk/a.dist-info/METADATA', b'Name: old\nVersion: 1\n')]),
                       layer([('opt/sdk', b'no longer a directory')])]])
        self.assertEqual(inventory(self.path)['images'][0]['python_dependencies'], [])

    def test_final_directory_symlink_resolves_debian_license(self):
        self.archive([[layer([('var/lib/dpkg/status', dpkg()),
                       ('usr/share/doc/base/copyright', b'license'),
                       ('usr/share/doc/example', ('symlink', 'base'))])]])
        evidence = inventory(self.path)['images'][0]['os_dependencies']['packages'][0]['license_evidence']
        self.assertEqual(evidence['sha256'], sha(b'license'))
        self.assertEqual(evidence['requested_path'], 'usr/share/doc/example/copyright')

    def test_hardlink_keeps_original_bytes_on_later_target_replacement(self):
        base = 'opt/sdk/example.dist-info/'
        self.archive([[layer([(base + 'LICENSE', b'old'),
                       (base + 'COPYING', ('hardlink', base + 'LICENSE'))]),
                       layer([(base + 'LICENSE', b'new')])]])
        files = {x['path']: x for x in inventory(self.path)['images'][0]['metadata_and_license_files']}
        self.assertEqual(files[base + 'COPYING']['sha256'], sha(b'old'))

    def test_shared_compressed_layer_is_scanned_once(self):
        raw = layer([('var/lib/dpkg/status', dpkg())], compressed=True)
        self.archive([[raw], [raw]])
        calls = []
        report = inventory(self.path, progress=lambda *args: calls.append(args))
        self.assertEqual(len(calls), 1)
        self.assertEqual(report['scan']['unique_layers'], 1)
        self.assertEqual(report['scan']['layer_applications'], 2)

    def test_packaged_model_pin_is_checked_without_loading(self):
        model = b'not a real model; hash fixture only'
        lock = dict(files={}, packages={}, helper='/opt/helper/lib_chromadb.py', helper_sha256=sha(b'helper'),
                    python='/opt/native/python/bin/python3.12', python_sha256=sha(b'python'),
                    model='/opt/model', model_spec=dict(model='fixture-embedding', revision='fixture-revision',
                    files={'model.safetensors': sha(model)}))
        self.archive([[layer([('opt/memory-runtime.json', json.dumps(lock).encode()),
                       ('opt/model/model.safetensors', model), ('opt/helper/lib_chromadb.py', b'helper'),
                       ('opt/native/python/bin/python3.12', b'python')])]])
        components = inventory(self.path)['images'][0]['native_components']
        self.assertEqual(components[0]['helper_verification']['status'], 'MATCH')
        self.assertEqual(components[1]['file_verification']['matched'], 1)

    def test_corrupt_layer_bytes_fail(self):
        self.archive([[layer([('var/lib/dpkg/status', dpkg())])]], corrupt=True)
        with self.assertRaisesRegex(ValueError, 'digest mismatch'):
            inventory(self.path)

    def test_unsafe_member_and_duplicate_outer_member_fail(self):
        self.archive([[layer([('../escape', b'bad')])]])
        with self.assertRaisesRegex(ValueError, 'unsafe archive path'):
            inventory(self.path)
        self.archive([[layer([])]], extra=[('index.json', b'{}')])
        with self.assertRaisesRegex(ValueError, 'duplicate outer'):
            inventory(self.path)

    def test_metadata_and_expansion_bounds(self):
        self.archive([[layer([('var/lib/dpkg/status', b'x' * 2000)])]])
        with self.assertRaisesRegex(ValueError, 'metadata file bound'):
            inventory(self.path, limits=Limits(metadata_file_bytes=1000))
        self.archive([[layer([('ordinary', b'x' * 2000)], compressed=True)]])
        with self.assertRaisesRegex(ValueError, 'expansion/member bound'):
            inventory(self.path, limits=Limits(expanded_layer_bytes=1000))

    def test_publication_binding_is_checked_and_parent_claim_separate(self):
        self.archive([[layer([('var/lib/dpkg/status', dpkg())])]])
        report = inventory(self.path)
        expected = dict(archive_sha256=report['archive']['sha256'], archive_bytes=report['archive']['bytes'],
                        images=report['images'], source_export_verification='PASS')
        path = Path(self.temp.name) / 'images.json'
        path.write_text(json.dumps(expected))
        actual = inventory(self.path, expected_images=path)
        self.assertEqual(actual['publication_binding']['source_verification'], 'PARENT_EVIDENCE_NOT_REEXECUTED')
        expected['archive_sha256'] = '0' * 64
        path.write_text(json.dumps(expected))
        with self.assertRaisesRegex(ValueError, 'archive binding mismatch'):
            inventory(self.path, expected_images=path)

    def test_vendored_metadata_is_separate_and_unknown_license_explicit(self):
        self.archive([[layer([('opt/sdk/vendor/a.dist-info/METADATA', b'Name: a\nVersion: 1\n')])]])
        package = inventory(self.path)['images'][0]['python_dependencies'][0]
        self.assertEqual(package['scope'], 'VENDORED_METADATA')
        self.assertEqual(package['license_expression'], 'NOASSERTION')


if __name__ == '__main__':
    unittest.main()
