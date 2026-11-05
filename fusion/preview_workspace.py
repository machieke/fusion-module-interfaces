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
        try:
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
        except BaseException:
            if hasattr(self,'db'):self.db.close()
            self.lock.close();os.close(self.dir)
            raise

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


ROOT_HANDOVER = 'synthetic-workspace-root-reattestation/1'
ROOT_RECEIPT = 'pilot_workspace_root_handover'


def _root_inventory(root, db, scope):
    """Bounded physical facts; no reconciliation or receipt completion."""
    require(root.is_absolute() and '..' not in root.parts and root.resolve()==root, 'UNAUTHORIZED')
    for ancestor in (root, *root.parents):require(not ancestor.is_symlink(), 'UNAUTHORIZED')
    st=root.stat();require(stat.S_ISDIR(st.st_mode) and st.st_uid==os.getuid() and not st.st_mode & 0o022, 'UNAUTHORIZED')
    meta=[tuple(row) for row in db.execute('SELECT * FROM workspace_meta')]
    require(len(meta)==1 and meta[0][:2]==(PROFILE,scope), 'UNSUPPORTED_PROFILE')
    require(type(scope) is str and scope.startswith('synthetic-'), 'UNAUTHORIZED')
    tables={};allowed={};required=set();versions={};pending=set()
    for table in ('workspace_files','workspace_effects'):
        columns=[row[1] for row in db.execute('PRAGMA table_info('+table+')')]
        rows=db.execute('SELECT * FROM '+table).fetchall();require(len(rows)<=(MAX_FILES if table=='workspace_files' else MAX_COMMANDS), 'OVERLOADED')
        hashes=[]
        for row in rows:
            values=list(row);encoded=[dict(bytes=len(v),sha256=digest(v)) if isinstance(v,bytes) else v for v in values]
            hashes.append(digest(canonical(encoded)));item=dict(zip(columns,values));name=item['name'];Argument('path','path').validate(name)
            if table=='workspace_files':
                allowed.setdefault(name,set()).add(item['digest']);required.add(name);versions[name]=item
            elif item['receipt'] is None:
                require(name not in pending,'CONFLICT');pending.add(name);version=versions.get(name)
                require((version is None and item['previous'] is None and item['revision']==1) or
                        (version is not None and item['previous'] is not None and digest(item['previous'])==version['digest'] and item['revision']==version['revision']+1),'CONFLICT')
                for key in ('previous','desired'):
                    if item[key] is not None:allowed.setdefault(name,set()).add(digest(item[key]))
        tables[table]=dict(rows=len(rows),columns=columns,semantic_head=digest(canonical(sorted(hashes))))
    files={};entries=list(root.iterdir());require(len(entries)<=MAX_FILES, 'OVERLOADED')
    for path in entries:
        info=path.lstat();require(stat.S_ISREG(info.st_mode) and not path.is_symlink() and info.st_nlink==1 and info.st_uid==os.getuid() and not info.st_mode & 0o022 and info.st_size<=MAX_BYTES, 'UNAUTHORIZED')
        data=path.read_bytes();require(path.name in allowed and digest(data) in allowed[path.name], 'CONFLICT')
        files[path.name]=dict(bytes=len(data),sha256=digest(data))
    require(required<=set(files), 'CONFLICT')
    return dict(meta=list(meta[0]),current=[PROFILE,scope,st.st_dev,st.st_ino],tables=tables,files=files)


def reattest_root(root, journal, *, scope, checkpoint, generation, hook=lambda _:None):
    """Explicit offline synthetic-copy maintenance, never ordinary startup.

    The owning activation helper supplies the verified restore checkpoint.
    Only physical root metadata changes; historical effects stay untouched.
    """
    from contextlib import closing
    root,journal=Path(root),Path(journal)
    require(journal.is_absolute() and journal.resolve()==journal and not journal.is_symlink() and journal.parent==root.parent and journal.name=='workspace.sqlite', 'UNAUTHORIZED')
    require(type(checkpoint) is str and len(checkpoint)==64 and all(c in '0123456789abcdef' for c in checkpoint) and type(generation) is int and 2<=generation<=65, 'INVALID_ARGUMENT')
    require(journal.is_file(), 'NOT_FOUND')
    require(journal.stat().st_nlink==1 and journal.stat().st_uid==os.getuid(), 'UNAUTHORIZED')
    with open(str(journal)+'.lock','a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        with closing(sqlite3.connect(journal)) as db:
            db.execute('PRAGMA synchronous=FULL')
            names={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
            require({'workspace_meta','workspace_files','workspace_effects'}<=names<={'workspace_meta','workspace_files','workspace_effects',ROOT_RECEIPT}, 'CONFLICT')
            before=_root_inventory(root,db,scope)
            if ROOT_RECEIPT in names:
                rows=db.execute('SELECT singleton,value FROM '+ROOT_RECEIPT).fetchall();require(len(rows)==1 and rows[0][0]==1,'CONFLICT')
                receipt=json.loads(rows[0][1]);require(set(receipt)=={'profile','scope','checkpoint_sha256','generation','previous','current','tables','files'},'CONFLICT')
                require(receipt['profile']==ROOT_HANDOVER and receipt['scope']==scope and receipt['checkpoint_sha256']==checkpoint and receipt['generation']==generation and
                        receipt['current']==before['meta']==before['current'] and receipt['tables']==before['tables'] and receipt['files']==before['files'], 'CONFLICT')
                return receipt
            require(before['meta']!=before['current'], 'CONFLICT')
            receipt=dict(profile=ROOT_HANDOVER,scope=scope,checkpoint_sha256=checkpoint,generation=generation,
                         previous=before['meta'],current=before['current'],tables=before['tables'],files=before['files'])
            with db:
                db.execute('BEGIN IMMEDIATE')
                db.execute('CREATE TABLE '+ROOT_RECEIPT+' (singleton INTEGER PRIMARY KEY CHECK(singleton=1),value TEXT NOT NULL)')
                db.execute('UPDATE workspace_meta SET root_device=?,root_inode=?',(before['current'][2],before['current'][3]))
                hook('after_workspace_root_metadata')
                db.execute('INSERT INTO '+ROOT_RECEIPT+' VALUES(1,?)',(canonical(receipt).decode(),))
                after=_root_inventory(root,db,scope)
                require(after['tables']==before['tables'] and after['files']==before['files'] and after['meta']==before['current'], 'CONFLICT')
            hook('after_workspace_root_commit')
            return receipt


def root_handover_observation(root, journal):
    """Owner-exported proof; does not initialize, retarget or complete effects."""
    from contextlib import closing
    root,journal=Path(root),Path(journal)
    if not journal.exists():return None
    wal=Path(str(journal)+'-wal');require(not wal.exists() or wal.stat().st_size==0,'NOT_AVAILABLE')
    with closing(sqlite3.connect(journal.resolve().as_uri()+'?mode=ro&immutable=1',uri=True)) as db:
        db.execute('PRAGMA query_only=ON')
        if not db.execute("SELECT 1 FROM sqlite_master WHERE name=?",(ROOT_RECEIPT,)).fetchone():return None
        rows=db.execute('SELECT singleton,value FROM '+ROOT_RECEIPT).fetchall();require(len(rows)==1 and rows[0][0]==1,'CONFLICT')
        value=json.loads(rows[0][1]);actual=_root_inventory(root,db,value['scope'])
        require(value['profile']==ROOT_HANDOVER and value['current']==actual['meta']==actual['current'], 'CONFLICT')
        # Later new work legitimately changes files/rows. The immutable receipt
        # attests the cut; activation compares it before any new admission.
        return value
