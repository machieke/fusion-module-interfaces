"""Finite incremental representation of existing quiesced owner exports.

This changes packaging only. It cannot open a live owner, grant restore authority,
run native work, or repair missing bytes. Files are content addressed in the
private packet; manifest identity, not a neighbouring directory name, selects a
base. Flatten reconstructs byte-exact original owner exports.
"""
import argparse
import io
import json
import os
import re
import tarfile
import time
from pathlib import Path

from fusion.contracts import canonical, digest, require
from .backup_payload import MAX_TOTAL, safe_name, synthetic_seal

PROFILE = 'synthetic-incremental-owner-backup/1'
CHUNK = 65536
MAX_DEPTH = 8
MAX_OWNERS = 32
MAX_MANIFEST = 16 * 1024 * 1024
HEX = re.compile(r'[0-9a-f]{64}')


def sha(value):
    require(type(value) is str and HEX.fullmatch(value) is not None, 'CONFLICT')
    return value


def read(path, bound):
    path = Path(path)
    require(not path.is_symlink() and path.is_file(), 'NOT_AVAILABLE')
    with path.open('rb') as stream:
        value = stream.read(bound + 1)
    require(len(value) <= bound, 'OVERLOADED')
    return value


def private_write(path, raw):
    path = Path(path)
    path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    require(not path.is_symlink() and not path.exists(), 'CONFLICT')
    with path.open('xb') as stream:
        os.fchmod(stream.fileno(), 0o600)
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def owner_manifest(raw, role):
    require(len(raw) <= MAX_TOTAL, 'OVERLOADED')
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r:gz') as archive:
        members = archive.getmembers()
        require(len(members) <= 150000 and sum(x.size for x in members) <= MAX_TOTAL, 'OVERLOADED')
        require(all(x.isfile() for x in members) and len({x.name for x in members}) == len(members), 'CONFLICT')
        value = json.loads(archive.extractfile('backup-manifest.json').read())
        require(value['schema'] == 'synthetic-owner-backup/1' and value['role'] == role and value['excluded_authority'] is True, 'CONFLICT')
        synthetic_seal(value['seal'], role)
        require({x.name for x in members} == {'backup-manifest.json'} | {'state/' + x for x in value['files']}, 'CONFLICT')
        for name, item in value['files'].items():
            safe_name(Path(name))
            content = archive.extractfile('state/' + name).read()
            require(item == dict(bytes=len(content), sha256=digest(content)), 'CONFLICT')
        for name, item in value.get('archive_dependencies', {}).items():
            require(name in value['files'] and item['database'] in value['files'], 'CONFLICT')
            require(value['files'][name] == {k: item[k] for k in ('bytes', 'sha256')}, 'CONFLICT')
        return value


class Chain:
    """All base locations are explicit caller inputs; no manifest path traversal."""
    def __init__(self, roots):
        require(type(roots) is list and 1 <= len(roots) <= MAX_DEPTH, 'OVERLOADED')
        self.packets = {}
        for root in roots:
            root = Path(root).absolute()
            require(not root.is_symlink(), 'UNAUTHORIZED')
            raw = read(root / 'manifest.json', MAX_MANIFEST)
            identity = sha(read(root / 'manifest.sha256', 65).decode().strip())
            require(digest(raw) == identity and identity not in self.packets, 'CONFLICT')
            value = json.loads(raw)
            require(set(value) == {'profile', 'base', 'depth', 'cut', 'owners', 'stored_chunks', 'authority_excluded', 'same_host_only'}, 'CONFLICT')
            require(value['profile'] == PROFILE and value['authority_excluded'] is True and value['same_host_only'] is True, 'UNSUPPORTED_PROFILE')
            require(type(value['depth']) is int and 1 <= value['depth'] <= MAX_DEPTH, 'OVERLOADED')
            require(type(value['owners']) is dict and 1 <= len(value['owners']) <= MAX_OWNERS, 'OVERLOADED')
            require(type(value['stored_chunks']) is dict and len(value['stored_chunks']) <= MAX_TOTAL // CHUNK + MAX_OWNERS, 'OVERLOADED')
            for h, count in value['stored_chunks'].items():
                sha(h)
                require(type(count) is int and 1 <= count <= CHUNK, 'CONFLICT')
            self.packets[identity] = (root, value)

    def ancestry(self, identity):
        result = []
        while identity is not None:
            sha(identity)
            require(identity in self.packets and identity not in result, 'NOT_AVAILABLE')
            result.append(identity)
            require(len(result) <= MAX_DEPTH, 'OVERLOADED')
            identity = self.packets[identity][1]['base']
        require([self.packets[x][1]['depth'] for x in result] == list(range(len(result), 0, -1)), 'CONFLICT')
        return result

    def chunk(self, identity, h):
        sha(h)
        for candidate in self.ancestry(identity):
            root, value = self.packets[candidate]
            if h in value['stored_chunks']:
                raw = read(root / 'chunks' / h, CHUNK)
                require(len(raw) == value['stored_chunks'][h] and digest(raw) == h, 'CONFLICT')
                return raw
        require(False, 'NOT_AVAILABLE')

    def owner(self, identity, role):
        self.ancestry(identity)
        item = self.packets[identity][1]['owners'][role]
        require(set(item) == {'file', 'sha256', 'bytes', 'chunks', 'owner_manifest', 'image'}, 'CONFLICT')
        require(type(item['bytes']) is int and 1 <= item['bytes'] <= MAX_TOTAL and
                type(item['chunks']) is list and len(item['chunks']) <= MAX_TOTAL // CHUNK + 1, 'OVERLOADED')
        require(re.fullmatch('[a-z][a-z0-9-]{0,63}', role) and item['file'] == role + '.tar.gz', 'CONFLICT')
        raw = b''.join(self.chunk(identity, h) for h in item['chunks'])
        require(len(raw) == item['bytes'] and digest(raw) == item['sha256'], 'CONFLICT')
        require(owner_manifest(raw, role) == item['owner_manifest'], 'CONFLICT')
        return raw

    def verify(self, identity):
        ancestors = self.ancestry(identity)
        value = self.packets[identity][1]
        total = 0
        for role in value['owners']:
            total += len(self.owner(identity, role))
            require(total <= MAX_TOTAL, 'OVERLOADED')
        cut = value['cut']
        require(cut['schema'] == 'synthetic-quiesced-backup/1' and cut['authority_excluded'] is True and
                cut['original_remains_quiesced'] is True and set(cut['owners']) == set(value['owners']), 'CONFLICT')
        for role, item in cut['owners'].items():
            require(item == {k: value['owners'][role][k] for k in ('file', 'sha256', 'bytes', 'image')}, 'CONFLICT')
        return dict(status='VERIFIED', profile=PROFILE, manifest_sha256=identity, depth=len(ancestors),
                    owner_count=len(value['owners']), reconstructed_bytes=total,
                    authority_excluded=True, effects_executed=0, storage_fault_domain='SAME_HOST')


def pack(full, output, bases=(), base=None):
    started = time.monotonic()
    full, output = Path(full), Path(output)
    require(not output.exists(), 'CONFLICT')
    original = read(full / 'manifest.json', MAX_MANIFEST)
    require(digest(original) == read(full / 'manifest.sha256', 65).decode().strip(), 'CONFLICT')
    cut = json.loads(original)
    require(cut['schema'] == 'synthetic-quiesced-backup/1' and cut['authority_excluded'] is True and
            cut['original_remains_quiesced'] is True and 1 <= len(cut['owners']) <= MAX_OWNERS, 'CONFLICT')
    previous = Chain(list(bases)) if base else None
    if previous:
        previous.verify(base)
        depth = len(previous.ancestry(base)) + 1
        require(depth <= MAX_DEPTH, 'OVERLOADED')
    else:
        require(not bases, 'INVALID_ARGUMENT')
        depth = 1
    chunks, owners, total = {}, {}, 0
    for role, entry in cut['owners'].items():
        require(re.fullmatch('[a-z][a-z0-9-]{0,63}', role) and entry['file'] == role + '.tar.gz', 'CONFLICT')
        raw = read(full / entry['file'], MAX_TOTAL)
        require(len(raw) == entry['bytes'] and digest(raw) == entry['sha256'], 'CONFLICT')
        total += len(raw)
        require(total <= MAX_TOTAL, 'OVERLOADED')
        checked = owner_manifest(raw, role)
        ids = []
        for offset in range(0, len(raw), CHUNK):
            part = raw[offset:offset + CHUNK]
            h = digest(part)
            ids.append(h)
            found = previous and any(h in previous.packets[x][1]['stored_chunks'] for x in previous.ancestry(base))
            if found:
                require(previous.chunk(base, h) == part, 'CONFLICT')
            else:
                chunks[h] = part
        owners[role] = dict(entry, chunks=ids, owner_manifest=checked)
    value = dict(profile=PROFILE, base=base, depth=depth, cut=cut, owners=owners,
                 stored_chunks={h: len(b) for h, b in sorted(chunks.items())},
                 authority_excluded=True, same_host_only=True)
    encoded = canonical(value)
    require(len(encoded) <= MAX_MANIFEST, 'OVERLOADED')
    output.mkdir(mode=0o700, parents=True)
    for h, raw in chunks.items():
        private_write(output / 'chunks' / h, raw)
    private_write(output / 'manifest.json', encoded)
    identity = digest(encoded)
    private_write(output / 'manifest.sha256', (identity + '\n').encode())
    result = Chain([str(output), *bases]).verify(identity)
    return dict(result, new_chunk_bytes=sum(map(len, chunks.values())), manifest_bytes=len(encoded),
                seconds=time.monotonic() - started)


def flatten(roots, identity, output):
    started = time.monotonic()
    chain = Chain(list(roots))
    report = chain.verify(identity)  # validate entire closure before any disclosure
    output = Path(output)
    require(not output.exists(), 'CONFLICT')
    value = chain.packets[identity][1]
    output.mkdir(mode=0o700, parents=True)
    for role in value['owners']:
        private_write(output / (role + '.tar.gz'), chain.owner(identity, role))
    raw = canonical(value['cut'])
    private_write(output / 'manifest.json', raw)
    private_write(output / 'manifest.sha256', (digest(raw) + '\n').encode())
    return dict(report, flattened=True, seconds=time.monotonic() - started)


def compare(roots, identity, full):
    chain = Chain(list(roots)); chain.verify(identity)
    raw = read(Path(full) / 'manifest.json', MAX_MANIFEST)
    require(digest(raw) == read(Path(full) / 'manifest.sha256', 65).decode().strip(), 'CONFLICT')
    require(json.loads(raw) == chain.packets[identity][1]['cut'], 'CONFLICT')
    for role in chain.packets[identity][1]['owners']:
        require(chain.owner(identity, role) == read(Path(full) / (role + '.tar.gz'), MAX_TOTAL), 'CONFLICT')
    return dict(status='BYTE_EXACT', compared='original-full-owner-export-bytes', effects_executed=0)


def compare_checkpoint(roots,identity,full):
    """Independent re-export: exact owner bytes, not gzip timestamp equality."""
    chain=Chain(list(roots));chain.verify(identity);value=chain.packets[identity][1]
    root=Path(full);raw=read(root/'manifest.json',MAX_MANIFEST)
    require(digest(raw)==read(root/'manifest.sha256',65).decode().strip(),'CONFLICT');cut=json.loads(raw)
    require(cut['schema']=='synthetic-quiesced-backup/1' and cut['authority_excluded'] is True and cut['original_remains_quiesced'] is True,'UNAUTHORIZED')
    require(set(cut['owners'])==set(value['owners']) and all(cut['before'][k]==value['cut']['before'][k] for k in ('namespace','namespace_uid')),'CONFLICT')
    observed={}
    for role,item in cut['owners'].items():
        require(item['file']==role+'.tar.gz' and item['image']==value['owners'][role]['image'],'CONFLICT')
        blob=read(root/item['file'],MAX_TOTAL);require(len(blob)==item['bytes'] and digest(blob)==item['sha256'],'CONFLICT')
        actual=owner_manifest(blob,role);expected=value['owners'][role]['owner_manifest']
        for key in ('seal','files','archive_dependencies','retained_views'):
            require(actual[key]==expected[key],'CONFLICT')
        require(actual['dependency_inventory']['head']==expected['dependency_inventory']['head'],'CONFLICT')
        observed[role]=dict(files=len(actual['files']),files_sha256=digest(canonical(actual['files'])),inventory_head=actual['dependency_inventory']['head'])
    return dict(status='EXACT_OWNER_CHECKPOINT',compared='separately-exported-quiesced-full-cut',owners=observed,
        independent_manifest_sha256=digest(raw),original_manifest_sha256=digest(canonical(value['cut'])),
        gzip_metadata_identity_required=False,effects_executed=0)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('action', choices=('pack', 'verify', 'flatten', 'compare','compare-checkpoint'))
    p.add_argument('--full'); p.add_argument('--output'); p.add_argument('--packet', action='append', default=[])
    p.add_argument('--manifest'); a = p.parse_args()
    if a.action == 'pack': value = pack(a.full, a.output, a.packet, a.manifest)
    elif a.action == 'verify': value = Chain(a.packet).verify(a.manifest)
    elif a.action == 'flatten': value = flatten(a.packet, a.manifest, a.output)
    elif a.action == 'compare-checkpoint':value=compare_checkpoint(a.packet,a.manifest,a.full)
    else: value = compare(a.packet, a.manifest, a.full)
    print(json.dumps(value, sort_keys=True))


if __name__ == '__main__': main()
