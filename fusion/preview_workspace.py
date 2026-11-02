"""Named bounded file effects, confined to a provider-owned synthetic directory.

Intent commit, atomic file effect and receipt commit remain separate. Recovery
compares exact prior/desired bytes; an ambiguous external edit is not retried.
No shell, imports, arbitrary roots, paths, links or cross-file transactions.
"""
import fcntl
import json
import os
from pathlib import Path
import sqlite3
import stat
import uuid

from .contracts import canonical, digest, require
from .preview_tools import Argument

PROFILE = 'synthetic-workspace-files/1'
MAX_FILES = 16
MAX_BYTES = 16384
MAX_COMMANDS = 128


class Workspace:
    def __init__(self, root, journal, authorize, *, scope, hook=lambda _: None):
        self.root, self.journal = Path(root), Path(journal)
        require(type(scope) is str and scope.startswith('synthetic-'), 'UNAUTHORIZED')
        self.scope, self.authorize, self.hook = scope, authorize, hook
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.journal.parent.mkdir(parents=True, exist_ok=True)
        require(self.root.resolve() not in self.journal.resolve().parents, 'UNSUPPORTED_PROFILE')
        self.dir = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        st = os.fstat(self.dir)
        require(st.st_uid == os.getuid() and not st.st_mode & 0o022, 'UNAUTHORIZED')
        self.lock = open(str(journal)+'.lock', 'a')
        try: fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self.lock.close(); os.close(self.dir)
            require(False, 'OVERLOADED')
        self.db = sqlite3.connect(journal)
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA journal_mode=WAL'); self.db.execute('PRAGMA synchronous=FULL')
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS workspace_meta(profile TEXT NOT NULL, scope TEXT NOT NULL, root_device INTEGER NOT NULL, root_inode INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS workspace_files(name TEXT PRIMARY KEY, revision INTEGER NOT NULL, digest TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS workspace_effects(identity TEXT PRIMARY KEY, intent TEXT NOT NULL,
                name TEXT NOT NULL, previous BLOB, desired BLOB NOT NULL, revision INTEGER NOT NULL, receipt TEXT);
        ''')
        with self.db:
            old = self.db.execute('SELECT * FROM workspace_meta').fetchone()
            if old: require(tuple(old) == (PROFILE, scope, st.st_dev, st.st_ino), 'UNSUPPORTED_PROFILE')
            else: self.db.execute('INSERT INTO workspace_meta VALUES(?,?,?,?)', (PROFILE, scope, st.st_dev, st.st_ino))

    def close(self):
        self.db.close(); self.lock.close(); os.close(self.dir)

    def _read(self, name):
        Argument('path', 'path').validate(name)
        try: fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=self.dir)
        except FileNotFoundError: return None
        except OSError: require(False, 'UNAUTHORIZED')
        try:
            info = os.fstat(fd)
            require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_size <= MAX_BYTES, 'UNAUTHORIZED')
            data = os.read(fd, MAX_BYTES+1)
            require(len(data) <= MAX_BYTES, 'OVERLOADED')
            return data
        finally: os.close(fd)

    def read(self, principal, scope, name):
        require(scope == self.scope, 'UNAUTHORIZED')
        self.authorize(principal, scope, 'workspace.read')
        data = self._read(name)
        require(data is not None, 'NOT_FOUND')
        row = self.db.execute('SELECT revision,digest FROM workspace_files WHERE name=?', (name,)).fetchone()
        require(row is not None and row['digest'] == digest(data), 'NOT_AVAILABLE')
        self.authorize(principal, scope, 'workspace.read')
        return dict(profile=PROFILE, path=name, revision=row['revision'], digest=row['digest'], text=data.decode('utf-8'))

    def version(self, principal, scope, name):
        require(scope == self.scope, 'UNAUTHORIZED')
        self.authorize(principal, scope, 'workspace.read')
        data = self._read(name)
        if data is None:
            require(self.db.execute('SELECT 1 FROM workspace_files WHERE name=?',(name,)).fetchone() is None, 'NOT_AVAILABLE')
            return dict(profile=PROFILE, path=name, revision=0, digest=None)
        value = self.read(principal, scope, name)
        return {k:value[k] for k in ('profile','path','revision','digest')}

    def mutate(self, principal, scope, identity, operation, name, text, expected_revision):
        require(scope == self.scope, 'UNAUTHORIZED')
        self.authorize(principal, scope, 'workspace.'+operation)
        require(operation in ('write', 'append'), 'UNSUPPORTED_OPERATION')
        Argument('path', 'path').validate(name)
        Argument('content', max_bytes=8192).validate(text)
        require(max(map(len, text.splitlines()), default=0) <= 4096)
        require(type(expected_revision) is int and 0 <= expected_revision <= MAX_COMMANDS)
        require(type(identity) is str and 1 <= len(identity) <= 128)
        key = digest(canonical([principal, scope, identity]))
        intent = canonical(dict(operation=operation, path=name, text=text, revision=expected_revision)).decode()
        old = self.db.execute('SELECT * FROM workspace_effects WHERE identity=?', (key,)).fetchone()
        if old:
            require(old['intent'] == intent, 'CONFLICT')
            if old['receipt'] is not None: return json.loads(old['receipt'])
        else:
            # A pending effect is reconciled first; never overtake it on a file.
            require(not self.db.execute('SELECT 1 FROM workspace_effects WHERE name=? AND receipt IS NULL', (name,)).fetchone(), 'NOT_AVAILABLE')
            previous = self._read(name)
            version = self.db.execute('SELECT * FROM workspace_files WHERE name=?', (name,)).fetchone()
            require((version is None and previous is None and expected_revision == 0) or
                    (version is not None and version['revision'] == expected_revision and previous is not None and version['digest'] == digest(previous)), 'CONFLICT')
            require(operation != 'append' or previous is not None, 'NOT_FOUND')
            require(version is not None or self.db.execute('SELECT count(*) FROM workspace_files').fetchone()[0] < MAX_FILES, 'OVERLOADED')
            desired = (previous if operation == 'append' else b'') + text.encode() + (b'\n' if operation == 'append' else b'')
            require(len(desired) <= MAX_BYTES, 'OVERLOADED')
            with self.db:
                require(self.db.execute('SELECT count(*) FROM workspace_effects').fetchone()[0] < MAX_COMMANDS, 'OVERLOADED')
                self.db.execute('INSERT INTO workspace_effects VALUES(?,?,?,?,?,?,NULL)',
                                (key, intent, name, previous, desired, expected_revision+1))
            old = self.db.execute('SELECT * FROM workspace_effects WHERE identity=?', (key,)).fetchone()
            self.hook('after_workspace_intent')
        self.authorize(principal, scope, 'workspace.'+operation)
        observed = self._read(name)
        require(observed in (old['previous'], old['desired']), 'CONFLICT')
        if observed != old['desired']:
            temporary = '.stage-'+uuid.uuid4().hex
            fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=self.dir)
            try:
                with os.fdopen(fd, 'wb') as out:
                    out.write(old['desired']); out.flush(); os.fsync(out.fileno())
                # The directory is private and exclusively owned. Recheck the
                # target immediately before its atomic directory-relative rename.
                require(self._read(name) == old['previous'], 'CONFLICT')
                os.replace(temporary, name, src_dir_fd=self.dir, dst_dir_fd=self.dir)
                os.fsync(self.dir)
            finally:
                try: os.unlink(temporary, dir_fd=self.dir)
                except FileNotFoundError: pass
        self.hook('after_workspace_effect')
        require(self._read(name) == old['desired'], 'NOT_AVAILABLE')
        receipt = dict(profile=PROFILE, path=name, revision=old['revision'],
                       digest=digest(old['desired']), bytes=len(old['desired']), outcome='committed', identity=identity)
        with self.db:
            self.db.execute('INSERT INTO workspace_files VALUES(?,?,?) ON CONFLICT(name) DO UPDATE SET revision=excluded.revision,digest=excluded.digest',
                            (name, old['revision'], receipt['digest']))
            self.db.execute('UPDATE workspace_effects SET receipt=? WHERE identity=?', (canonical(receipt).decode(), key))
        self.hook('after_workspace_receipt')
        self.authorize(principal, scope, 'workspace.'+operation)
        return receipt
