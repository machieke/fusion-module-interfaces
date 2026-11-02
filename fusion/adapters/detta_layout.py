"""Fresh opaque-coordinate partitions of the unchanged pinned DeTTa backend.

One owning service/PVC and one outer lock. This is physical storage layout, not
a new logical module/profile or a migration. Every record still commits and
reconstructs its actual DeTTa application DA shares. No semantic partition key,
foreign journal, cache of payload bytes or fallback is used.
"""
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import re

from ..contracts import ContractError, canonical, digest, require

LAYOUT = 'detta-opaque-coordinate-partitions/1'
SEAL = 'layout.json'
HEX = re.compile(r'[0-9a-f]{64}')


def publish_seal(path, value):
    raw = canonical(value)
    if path.exists():
        require(not path.is_symlink() and path.read_bytes() == raw, 'CONFLICT')
        return
    tmp = path.with_suffix('.pending')
    if tmp.exists():
        require(not tmp.is_symlink() and tmp.read_bytes() == raw, 'CONFLICT')
    else:
        with tmp.open('xb') as stream:
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    os.replace(tmp, path)
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try: os.fsync(fd)
    finally: os.close(fd)


class CoordinateStorage:
    def __init__(self, binary, root):
        self.binary, self.root = binary, Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        require(not self.root.is_symlink(), 'UNSUPPORTED_PROFILE')
        with self.lock():
            seal = self.root / SEAL
            value = dict(layout=LAYOUT, locator='scope-coordinate-manifest/1')
            expected = canonical(value)
            if seal.exists():
                require(not seal.is_symlink() and seal.read_bytes() == expected, 'UNSUPPORTED_PROFILE')
            else:
                require({p.name for p in self.root.iterdir()} <= {'.port.lock','layout.pending'}, 'UNSUPPORTED_PROFILE')
                publish_seal(seal, value)

    @contextmanager
    def lock(self):
        try: fd = os.open(self.root / '.port.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        except OSError: raise ContractError('UNSUPPORTED_PROFILE') from None
        with os.fdopen(fd,'a+b') as stream:
            try: fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError: raise ContractError('OVERLOADED') from None
            yield stream.fileno()

    def backend(self, scope_hash, coordinate, owner_fd):
        from .detta import DettaStorage
        require(HEX.fullmatch(scope_hash) and HEX.fullmatch(coordinate), 'NOT_AVAILABLE')
        path = self.root / scope_hash / coordinate
        require(not path.parent.is_symlink() and not path.is_symlink(), 'UNSUPPORTED_PROFILE')
        return DettaStorage(self.binary, str(path), owner_fds=(owner_fd,))

    def put(self, scope, coordinate, data):
        scope_hash = digest(scope.encode()); key = digest(coordinate.encode())
        with self.lock() as owner_fd:
            backend = self.backend(scope_hash, key, owner_fd); path = Path(backend.root)
            path.mkdir(parents=True, exist_ok=True)
            if not (path / 'record.json').exists():
                require({p.name for p in path.iterdir()} <= {'record.pending'}, 'UNSUPPORTED_PROFILE')
            publish_seal(path / 'record.json', dict(layout=LAYOUT, scope=scope_hash,
                coordinate=key, content_hash=digest(data)))
            # Separate binding and actual native commit. An interrupted native
            # put can only be retried with the same opaque accepted bytes.
            manifest, receipt = backend.put(scope, coordinate, data)
            require(type(manifest) is str and HEX.fullmatch(manifest), 'NOT_AVAILABLE')
            publish_seal(path / 'manifest.json', dict(manifest=manifest))
        locator = canonical(dict(layout=LAYOUT, scope=scope_hash, coordinate=key, manifest=manifest)).decode()
        receipt = {**receipt, 'evidence': {**receipt['evidence'], 'storage_layout': LAYOUT}}
        return locator, receipt

    def locate(self, scope, locator, owner_fd):
        require(type(locator) is str and len(locator) <= 512, 'NOT_AVAILABLE')
        try: value = json.loads(locator)
        except ValueError: raise ContractError('NOT_AVAILABLE') from None
        require(type(value) is dict and set(value) == {'layout','scope','coordinate','manifest'}
                and canonical(value).decode() == locator and value['layout'] == LAYOUT, 'NOT_AVAILABLE')
        require(all(type(value[k]) is str and HEX.fullmatch(value[k]) for k in ('scope','coordinate','manifest')), 'NOT_AVAILABLE')
        require(value['scope'] == digest(scope.encode()), 'UNAUTHORIZED')
        # Reads never create a replacement partition for missing native state.
        path = self.root / value['scope'] / value['coordinate']
        require(path.is_dir() and not path.is_symlink() and not path.parent.is_symlink(), 'NOT_AVAILABLE')
        require(not any((path/name).is_symlink() for name in ('record.json','manifest.json')), 'NOT_AVAILABLE')
        try:
            record = json.loads((path / 'record.json').read_bytes())
            committed = json.loads((path / 'manifest.json').read_bytes())
        except (OSError,ValueError): raise ContractError('NOT_AVAILABLE') from None
        require(type(record) is dict and set(record)=={'layout','scope','coordinate','content_hash'}
            and all(record[k]==value[k] for k in ('layout','scope','coordinate'))
            and type(record['content_hash']) is str and HEX.fullmatch(record['content_hash'])
            and committed==dict(manifest=value['manifest']), 'NOT_AVAILABLE')
        return self.backend(value['scope'], value['coordinate'], owner_fd), value['manifest'], record['content_hash']

    def get(self, scope, locator):
        with self.lock() as owner_fd:
            backend, manifest, expected = self.locate(scope, locator, owner_fd)
            data = backend.get(scope, manifest)
            require(digest(data)==expected,'NOT_AVAILABLE')
            return data

    def availability(self, scope, locator):
        with self.lock() as owner_fd:
            backend, manifest, expected = self.locate(scope, locator, owner_fd)
            value = backend.availability(scope, manifest)
            require(value['content_hash']==expected,'NOT_AVAILABLE')
            return value


def storage(binary, root, layout=None):
    """Every source/read/append facade selects the same owner-controlled layout."""
    if layout is None:
        from .detta import DettaStorage
        require(not any((Path(root) / name).exists() for name in (SEAL,'layout.pending')), 'UNSUPPORTED_PROFILE')
        return DettaStorage(binary, str(root))
    require(layout == LAYOUT, 'UNSUPPORTED_PROFILE')
    return CoordinateStorage(binary, root)
