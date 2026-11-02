"""Offline dependency/license evidence from an OCI image archive; never run images.

Layers are streamed once per digest, with bounded metadata retention. Whiteouts,
opaque directories and replacements are applied before reading each final image.
This is a declared/installed dependency inventory, not a vulnerability assessment,
license determination, proof of runtime availability or dependency closure.
"""
import argparse
from dataclasses import dataclass
from email.parser import BytesParser
import hashlib
import json
from pathlib import Path, PurePosixPath
import posixpath
import re
import tarfile


@dataclass(frozen=True)
class Limits:
    archive_bytes: int = 32 * 1024 ** 3
    layer_bytes: int = 8 * 1024 ** 3
    expanded_layer_bytes: int = 16 * 1024 ** 3
    members: int = 200000
    metadata_file_bytes: int = 8 * 1024 ** 2
    retained_metadata_bytes: int = 256 * 1024 ** 2


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def clean(name):
    if name.startswith('/') or '\x00' in name or '..' in name.split('/'):
        raise ValueError('unsafe archive path')
    value = str(PurePosixPath(name))
    return '' if value == '.' else value


def blob_name(digest):
    if not re.fullmatch(r'sha256:[0-9a-f]{64}', digest):
        raise ValueError('only sha256 blob digests are supported')
    return 'blobs/' + digest.replace(':', '/')


def license_path(path):
    name = PurePosixPath(path).name.lower()
    return (name.startswith(('license', 'copying', 'copyright', 'notice'))
            or '/licenses/' in path.lower()
            or path.startswith('usr/share/common-licenses/'))


def capture(path):
    return (path == 'var/lib/dpkg/status'
            or ('.dist-info/' in path and (path.endswith('/METADATA') or license_path(path)))
            or path.startswith('usr/share/doc/') and path.endswith('/copyright')
            or path.startswith('usr/share/common-licenses/')
            or path.startswith('opt/') and license_path(path)
            or path in ('opt/native/build.json', 'opt/native/original-build.json',
                        'opt/native/runtime.json', 'opt/memory-runtime.json',
                        'opt/chain/source/sources.json')
            or path.startswith('opt/fusion/integration/') and path.endswith(('sources.json', '.lock')))


def hash_file(path):
    return capture(path) or path.startswith(('opt/native/', 'opt/model/', 'opt/sdk/', 'opt/chain/', 'opt/helper/', 'opt/irc/'))


class HashReader:
    def __init__(self, source, maximum):
        self.source, self.maximum = source, maximum
        self.hash, self.size = hashlib.sha256(), 0

    def read(self, size=-1):
        if size < 0:
            size = 1024 ** 2
        raw = self.source.read(size)
        self.size += len(raw)
        if self.size > self.maximum:
            raise ValueError('layer byte bound exceeded')
        self.hash.update(raw)
        return raw


def scan_layer(source, descriptor, limits, retained):
    reader = HashReader(source, limits.layer_bytes)
    operations, removals = [], []
    count, expanded = 0, 0
    with tarfile.open(fileobj=reader, mode='r|*') as layer:
        for member in layer:
            count += 1
            expanded += member.size
            if count > limits.members or expanded > limits.expanded_layer_bytes:
                raise ValueError('layer expansion/member bound exceeded')
            path = clean(member.name)
            if not path:
                continue
            parent, name = posixpath.split(path)
            if name == '.wh..wh..opq':
                removals.append(('opaque', parent))
                continue
            if name.startswith('.wh.'):
                removals.append(('remove', posixpath.join(parent, name[4:])))
                continue
            if member.isdir():
                operations.append(('directory', path, None))
                continue
            value = None
            if member.issym() or member.islnk():
                value = dict(path=path, kind='symlink' if member.issym() else 'hardlink',
                             target=member.linkname, layer=descriptor['digest'])
            elif member.isfile() and hash_file(path):
                keep = capture(path)
                if keep and member.size > limits.metadata_file_bytes:
                    raise ValueError('metadata file bound exceeded: ' + path)
                h, chunks = hashlib.sha256(), []
                with layer.extractfile(member) as stream:
                    while raw := stream.read(1024 ** 2):
                        h.update(raw)
                        if keep:
                            retained[0] += len(raw)
                            if retained[0] > limits.retained_metadata_bytes:
                                raise ValueError('retained metadata bound exceeded')
                            chunks.append(raw)
                value = dict(path=path, kind='file', bytes=member.size,
                             sha256=h.hexdigest(), layer=descriptor['digest'])
                if keep:
                    value['content'] = b''.join(chunks)
            operations.append(('replace', path, value))
    while reader.read(1024 ** 2):
        pass
    if reader.size != descriptor['size'] or 'sha256:' + reader.hash.hexdigest() != descriptor['digest']:
        raise ValueError('layer size/digest mismatch')
    return dict(removals=removals, operations=operations, members=count,
                expanded_file_bytes=expanded, bytes=reader.size, digest=descriptor['digest'])


class FileState(dict):
    """An overinclusive ancestor index avoids quadratic regular-file replacements."""
    def __init__(self):
        super().__init__()
        self.parents = set()

    def __setitem__(self, path, value):
        parts = path.split('/')
        self.parents.update('/'.join(parts[:i]) for i in range(1, len(parts)))
        super().__setitem__(path, value)


def remove(state, path, descendants_only=False):
    if path and isinstance(state, FileState) and path not in state.parents:
        if not descendants_only:
            state.pop(path, None)
        return
    for key in list(state):
        if (not descendants_only and key == path) or key.startswith(path + '/') or not path:
            del state[key]


def apply_layer(state, layer):
    # OCI whiteouts affect lower layers, regardless of tar member order.
    for kind, path in layer['removals']:
        remove(state, path, kind == 'opaque')
    for kind, path, value in layer['operations']:
        if kind == 'directory':
            state.pop(path, None)
        else:
            remove(state, path)
            if value is not None:
                if value['kind'] == 'hardlink':
                    target, _ = resolve(state, clean(value['target']))
                    if target is not None and target['kind'] == 'file':
                        value = {**target, 'path': path, 'layer': value['layer'],
                                 'hardlink_target': value['target']}
                state[path] = value


def resolve(state, path):
    visited, chain = set(), []
    for _ in range(40):
        if path in visited:
            return None, chain
        visited.add(path)
        parts = path.split('/')
        for i in range(1, len(parts) + 1):
            prefix = '/'.join(parts[:i])
            item = state.get(prefix)
            if item and item['kind'] in ('symlink', 'hardlink'):
                target = item['target']
                base = '' if target.startswith('/') or item['kind'] == 'hardlink' else posixpath.dirname(prefix)
                path = posixpath.normpath(posixpath.join(base, target.lstrip('/'), *parts[i:]))
                if path == '..' or path.startswith('../'):
                    return None, chain
                chain.append({k: v for k, v in item.items() if k != 'content'})
                break
        else:
            return state.get(path), chain
    return None, chain


def evidence(state, path):
    value, links = resolve(state, path)
    if value is None:
        return None
    result = {k: v for k, v in value.items() if k != 'content'}
    if links:
        result.update(requested_path=path, links=links)
    return result


def content(state, path):
    value, _ = resolve(state, path)
    return value.get('content') if value else None


def json_content(state, path):
    raw = content(state, path)
    return json.loads(raw) if raw is not None else None


def paragraphs(raw):
    for block in raw.decode('utf-8', 'replace').strip().split('\n\n'):
        item, key = {}, None
        for line in block.splitlines():
            if line.startswith((' ', '\t')) and key:
                item[key] += '\n' + line[1:]
            elif ':' in line:
                key, value = line.split(':', 1)
                item[key] = value.strip()
        if item:
            yield item


def os_packages(state):
    raw = content(state, 'var/lib/dpkg/status')
    if raw is None:
        return dict(status='NOT_PRESENT', packages=[])
    packages, excluded = [], 0
    for row in paragraphs(raw):
        if row.get('Status') != 'install ok installed':
            excluded += 1
            continue
        name = row['Package']
        license_file = evidence(state, 'usr/share/doc/' + name + '/copyright')
        packages.append(dict(name=name, version=row.get('Version'), architecture=row.get('Architecture'),
            source=row.get('Source'), depends=row.get('Depends'), pre_depends=row.get('Pre-Depends'),
            provides=row.get('Provides'), license_expression='NOASSERTION', license_evidence=license_file))
    return dict(status='OBSERVED', database=evidence(state, 'var/lib/dpkg/status'),
                packages=sorted(packages, key=lambda p: (p['name'], p['architecture'] or '')),
                non_installed_records=excluded)


def python_packages(state):
    packages = []
    for path in sorted(state):
        if not path.endswith('.dist-info/METADATA'):
            continue
        raw = content(state, path)
        if raw is None:
            continue
        metadata = BytesParser().parsebytes(raw)
        root = path.rsplit('/', 1)[0]
        licenses = [evidence(state, p) for p in sorted(state)
                    if p.startswith(root + '/') and license_path(p)]
        packages.append(dict(name=metadata.get('Name'), version=metadata.get('Version'),
            metadata=evidence(state, path), installation_root=root.rsplit('/', 1)[0],
            scope='VENDORED_METADATA' if '/_vendor/' in path or '/vendor/' in path else 'INSTALLED_METADATA',
            requires_python=metadata.get('Requires-Python'),
            declared_dependencies=metadata.get_all('Requires-Dist', []),
            license_expression=metadata.get('License-Expression') or 'NOASSERTION',
            license_text=metadata.get('License'),
            license_classifiers=[x for x in metadata.get_all('Classifier', []) if x.startswith('License ::')],
            declared_license_files=metadata.get_all('License-File', []), license_evidence=licenses))
    return packages


def verify_files(state, expected, prefix=''):
    missing, mismatched, matched = [], [], 0
    for path, wanted in sorted(expected.items()):
        resolved = posixpath.join(prefix, path.lstrip('/'))
        item, _ = resolve(state, resolved)
        if item is None or 'sha256' not in item:
            missing.append(resolved)
        elif item['sha256'] != wanted:
            mismatched.append(dict(path=resolved, expected=wanted, observed=item['sha256']))
        else:
            matched += 1
    return dict(status='MATCH' if not missing and not mismatched else 'INCOMPLETE_OR_MISMATCH',
                expected=len(expected), matched=matched, missing=missing, mismatched=mismatched)


def native_components(state):
    components = []
    build_path = 'opt/native/build.json'
    build = json_content(state, build_path)
    if build:
        pins = build.get('source_pins', {})
        for name, item in pins.get('sources', {}).items():
            prefix = 'opt/native/sources/' + name
            # SWI is packaged as a compiled prefix, not its complete source tree.
            present = any(p.startswith(prefix + '/') for p in state)
            components.append(dict(name=name, revision=item.get('commit'), url=item.get('url'),
                license_expression='NOASSERTION', pin_evidence=evidence(state, build_path),
                source_presence='PACKAGED_SELECTED_FILES' if present else 'SOURCE_NOT_PACKAGED',
                file_verification=verify_files(state, item.get('files', {}), prefix) if present else None,
                license_evidence=evidence(state, prefix + '/LICENSE')))
        for name, path, pin, license_file in (
            ('CPython', 'opt/native/python/bin/python3.12', 'python_binary_sha256', 'opt/native/python/lib/python3.12/LICENSE.txt'),
            ('SWI-Prolog', 'opt/native/swipl/bin/swipl', 'binary_sha256', 'opt/native/swipl/lib/swipl/LICENSE')):
            components.append(dict(name=name, license_expression='NOASSERTION',
                version=pins.get('python' if name == 'CPython' else 'swipl_version'),
                binary=evidence(state, path), pin_evidence=evidence(state, build_path),
                file_verification=verify_files(state, {path: build[pin]}) if pin in build else None,
                license_evidence=evidence(state, license_file)))
    detta = evidence(state, 'opt/native/fusion-detta-adapter')
    if detta:
        components.append(dict(name='DeTTa fusion adapter', binary=detta,
            revision='NOT_ASSERTED_BY_PACKAGED_BINARY', license_expression='NOASSERTION',
            limitation='Binary measured directly; external parent build/source evidence is separate.'))
    if irc := evidence(state, 'opt/irc/sbin/ngircd'):
        components.append(dict(name='ngIRCd', binary=irc, revision='NOT_ASSERTED_BY_PACKAGED_BINARY',
            license_expression='NOASSERTION',
            limitation='Binary measured directly; external parent build/source evidence is separate.'))
    memory_path = 'opt/memory-runtime.json'
    memory = json_content(state, memory_path)
    if memory:
        components.append(dict(name='memory SDK', pin_evidence=evidence(state, memory_path),
            declared_packages=memory.get('packages'), license_expression='NOASSERTION',
            file_verification=verify_files(state, memory.get('files', {})),
            helper_verification=verify_files(state, {memory['helper']: memory['helper_sha256']}),
            python_verification=verify_files(state, {memory['python']: memory['python_sha256']})))
        if model := memory.get('model_spec'):
            components.append(dict(name=model['model'], revision=model['revision'],
                license_expression='NOASSERTION', pin_evidence=evidence(state, memory_path),
                file_verification=verify_files(state, model.get('files', {}), memory['model'].lstrip('/')),
                model_files=[evidence(state, memory['model'].lstrip('/') + '/' + p) for p in sorted(model['files'])],
                limitation='Embedding assets inspected as bytes; model was not loaded or run.'))
    chain_path = 'opt/chain/source/sources.json'
    if chain := json_content(state, chain_path):
        components.append(dict(name='F1R3node', revision=chain.get('commit'), url=chain.get('url'),
            toolchain=chain.get('toolchain'), profile=chain.get('profile'),
            license_expression='NOASSERTION', pin_evidence=evidence(state, chain_path),
            binary=evidence(state, 'opt/chain/bin/node'), license_evidence=evidence(state, 'opt/chain/source/LICENSE'),
            limitation='Packaged declaration and binary hash; no new source-to-binary rebuild assertion.'))
    return components


def image_report(state, descriptor, manifest, config):
    records = [evidence(state, p) for p in sorted(state) if capture(p)]
    return dict(name=descriptor.get('annotations', {}).get('io.containerd.image.name'),
        manifest_digest=descriptor['digest'], configuration_digest=manifest['config']['digest'],
        architecture=config.get('architecture'), os=config.get('os'),
        layer_digests=[x['digest'] for x in manifest['layers']],
        os_dependencies=os_packages(state), python_dependencies=python_packages(state),
        native_components=native_components(state),
        copied_shared_libraries=[dict(file=evidence(state, p), license_expression='NOASSERTION')
            for p in sorted(state) if p.startswith('opt/') and '.so' in PurePosixPath(p).name
            and evidence(state, p) is not None],
        metadata_and_license_files=[x for x in records if x is not None],
        unresolved_metadata_links=[p for p in sorted(state) if capture(p) and evidence(state, p) is None])


def inventory(archive, *, expected_images=None, limits=Limits(), progress=None):
    archive = Path(archive)
    if archive.stat().st_size > limits.archive_bytes:
        raise ValueError('archive byte bound exceeded')
    h = hashlib.sha256()
    with archive.open('rb') as source:
        while block := source.read(1024 ** 2):
            h.update(block)
    archive_digest = h.hexdigest()
    cache, reports, retained = {}, [], [0]
    with tarfile.open(archive, mode='r:') as outer:
        members = {}
        for member in outer:
            path = clean(member.name)
            if path in members:
                raise ValueError('duplicate outer archive member')
            members[path] = member
            if len(members) > limits.members:
                raise ValueError('archive member bound exceeded')

        def read_json(path, descriptor=None):
            member = members[path]
            if not member.isfile() or member.size > limits.metadata_file_bytes:
                raise ValueError('invalid JSON blob')
            raw = outer.extractfile(member).read()
            if descriptor and (sha(raw) != descriptor['digest'].split(':')[1] or len(raw) != descriptor['size']):
                raise ValueError('JSON blob size/digest mismatch')
            return json.loads(raw)

        index = read_json('index.json')
        if index.get('schemaVersion') != 2:
            raise ValueError('OCI schemaVersion 2 required')
        for descriptor in index['manifests']:
            manifest = read_json(blob_name(descriptor['digest']), descriptor)
            config = read_json(blob_name(manifest['config']['digest']), manifest['config'])
            state = FileState()
            for layer in manifest['layers']:
                if layer.get('mediaType') not in ('application/vnd.oci.image.layer.v1.tar',
                        'application/vnd.oci.image.layer.v1.tar+gzip',
                        'application/vnd.docker.image.rootfs.diff.tar',
                        'application/vnd.docker.image.rootfs.diff.tar.gzip'):
                    raise ValueError('unsupported layer media type')
                if layer['digest'] not in cache:
                    member = members[blob_name(layer['digest'])]
                    if not member.isfile() or member.size != layer['size']:
                        raise ValueError('invalid layer blob')
                    if progress:
                        progress(layer['digest'], member.size)
                    with outer.extractfile(member) as stream:
                        cache[layer['digest']] = scan_layer(stream, layer, limits, retained)
                apply_layer(state, cache[layer['digest']])
            reports.append(image_report(state, descriptor, manifest, config))
    binding = None
    if expected_images:
        expected_path = Path(expected_images)
        expected_raw = expected_path.read_bytes()
        expected = json.loads(expected_raw)
        if archive_digest != expected['archive_sha256'] or archive.stat().st_size != expected['archive_bytes']:
            raise ValueError('publication archive binding mismatch')
        actual = {(x['manifest_digest'], x['configuration_digest']) for x in reports}
        wanted = {(x['manifest_digest'], x['configuration_digest']) for x in expected['images']}
        if actual != wanted or len(reports) != len(expected['images']):
            raise ValueError('publication image binding mismatch')
        binding = dict(path=str(expected_path), sha256=sha(expected_raw), status='MATCH',
            source_manifest_sha256=expected.get('source_manifest_sha256'),
            source_verification='PARENT_EVIDENCE_NOT_REEXECUTED',
            recorded_source_verification=expected.get('source_export_verification'))
    return dict(schema='fusion-oci-dependency-license-inventory/1',
        tool=dict(path='sdk/image_inventory.py', sha256=sha(Path(__file__).read_bytes()),
                  method='Python stdlib archive inspection; no subprocess, extraction, network or package import'),
        archive=dict(path=str(archive), bytes=archive.stat().st_size, sha256=archive_digest),
        publication_binding=binding, images=reports,
        scan=dict(unique_layers=len(cache), layer_applications=sum(len(r['layer_digests']) for r in reports),
                  retained_metadata_bytes=retained[0], limits=limits.__dict__,
                  layers=[{k: v for k, v in cache[d].items() if k not in ('operations', 'removals')} for d in sorted(cache)]),
        scope='Final effective dpkg status, Python dist-info metadata, selected native binaries/assets and packaged pin declarations; offline byte inspection only.',
        limitations=['Not an SPDX/CycloneDX certification or license determination.',
                     'Declared dependencies are not resolved imports; native transitive static libraries are not exhaustively identified.',
                     'Copied native system libraries may differ from dpkg ownership; hashes do not establish their licenses.',
                     'Missing license evidence remains NOASSERTION; metadata license text is a publisher declaration.',
                     'Historical source/build manifests inside images are evidence of declarations, not new build execution.'],
        vulnerability_scan='NOT_RUN', licensing='NOASSERTION_WHERE_UNRESOLVED',
        container_starts=0, generative_starts=0, additional_live_generations=0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', required=True)
    parser.add_argument('--images', help='Existing publication images.json to bind, not trusted package input')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    import sys
    result = inventory(args.archive, expected_images=args.images,
                       progress=lambda d, n: print(f'inspecting {d} {n} bytes', file=sys.stderr, flush=True))
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps(dict(output=str(target), sha256=sha(target.read_bytes()),
                         images=len(result['images']), unique_layers=result['scan']['unique_layers'])))


if __name__ == '__main__':
    main()
