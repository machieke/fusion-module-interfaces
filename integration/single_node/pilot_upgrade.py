"""Copy-only /1 Registry representation upgrade for disposable synthetic exports.

No source database is opened writable. Original wire columns are preserved by
verified canonical reconstruction or separately retained bounded raw bytes.
The output stays restore
fenced; importing bytes cannot grant current writer or historical effect authority.
"""
import argparse
import io
import json
import sqlite3
import sys
from contextlib import closing
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fusion.contracts import canonical, digest, require
from fusion.provider_retention import Retention, LIMITS, PROFILE, present
from .pilot_backup import owner_manifest, read, private_write
from .backup_payload import restore, MAX_TOTAL

TRANSFORM = 'registry-exact-wire-to-interned-copy/1'
OLD = 'trusted-provider-lifecycle/1'
TABLES = {'integrated_providers': ('id', ('record',)),
          'integrated_provider_actions': ('id', ('intent', 'result')),
          'integrated_provider_bindings': ('session', ('selection',))}


def semantic(db):
    compact = present(db)
    from fusion.provider_retention import unpack
    output = {}
    for table, (key, encoded) in TABLES.items():
        names = [x[1] for x in db.execute('PRAGMA table_info(' + table + ')')]
        require(names, 'UNSUPPORTED_PROFILE')
        records = []
        for raw in db.execute('SELECT * FROM ' + table + ' ORDER BY ' + key + ' LIMIT 8193'):
            row = dict(zip(names, raw))
            for column in encoded:
                row[column] = unpack(db, row[column]) if compact else json.loads(row[column])
            records.append(row)
        require(len(records) <= 8192, 'OVERLOADED'); output[table] = records
    return output


def transform(database):
    with closing(sqlite3.connect(database)) as db:
        require(not present(db), 'UNSUPPORTED_PROFILE')
        before = semantic(db)
        originals = []
        all_rows = {}
        for table, (key, encoded) in TABLES.items():
            names = [x[1] for x in db.execute('PRAGMA table_info(' + table + ')')]
            all_rows[table] = (names, db.execute('SELECT * FROM ' + table + ' ORDER BY ' + key).fetchall())
            for raw in all_rows[table][1]:
                row = dict(zip(names, raw))
                for column in encoded:
                    wire=row[column];rebuilt=canonical(json.loads(wire)).decode()
                    originals.append((table,row[key],column,None if rebuilt==wire else wire,digest(wire.encode()),
                                      'canonical-json/1' if rebuilt==wire else 'exact-raw-json/1'))
        require(len(originals)<=1024 and sum(len(x[3].encode()) for x in originals if x[3] is not None)<=2*1024*1024,'OVERLOADED')
        # Retention deliberately refuses populated legacy initialization. A
        # disposable destination clears only these copied representation rows,
        # with every original in memory and in the exact-wire preservation table.
        with db:
            for table in TABLES: db.execute('DELETE FROM ' + table)
        retention = Retention(db, LIMITS)
        with db:
            db.execute('CREATE TABLE pilot_registry_upgrade_originals(table_name TEXT,key_value TEXT,column_name TEXT,wire TEXT,sha256 TEXT NOT NULL,encoding TEXT NOT NULL,PRIMARY KEY(table_name,key_value,column_name))')
            db.executemany('INSERT INTO pilot_registry_upgrade_originals VALUES(?,?,?,?,?,?)', originals)
            for table, (names, rows) in all_rows.items():
                encoded = TABLES[table][1]
                for raw in rows:
                    values = [retention.pack(json.loads(value)) if name in encoded else value for name, value in zip(names, raw)]
                    db.execute('INSERT INTO ' + table + ' VALUES(' + ','.join('?' for _ in names) + ')', values)
            after = semantic(db); require(after == before, 'CONFLICT')
            usage = retention.usage()
            require(all(usage[k] <= LIMITS[k] for k in usage), 'OVERLOADED')
            for table, key, column, wire, h, encoding in db.execute('SELECT * FROM pilot_registry_upgrade_originals'):
                if encoding=='canonical-json/1':
                    require(wire is None,'CONFLICT')
                    record=next(row for row in after[table] if row[TABLES[table][0]]==key);wire=canonical(record[column]).decode()
                else:require(encoding=='exact-raw-json/1' and wire is not None,'CONFLICT')
                require(digest(wire.encode()) == h, 'CONFLICT')
        require(db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok', 'CONFLICT')
        return dict(semantic_sha256=digest(canonical(before)), counts={k: len(v) for k, v in before.items()},
                    original_wire_columns=len(originals), original_wire_sha256=digest(canonical(originals)),
                    raw_wire_bytes=sum(len(x[3].encode()) for x in originals if x[3] is not None),
                    canonical_reconstructed_columns=sum(x[3] is None for x in originals), usage=usage)


def upgrade(source, expected, destination=None, *, role='omega-agent', dry_run=False):
    raw = read(source, MAX_TOTAL); require(digest(raw) == expected, 'CONFLICT')
    source_manifest = owner_manifest(raw, role)
    require(role in ('omega-agent', 'omega-agent-b') and source_manifest['seal'].get('provider_registry') == OLD, 'UNSUPPORTED_PROFILE')
    require('session-inbox.sqlite' in source_manifest['files'], 'UNSUPPORTED_PROFILE')
    plan = dict(profile=TRANSFORM, source_sha256=expected, input_profile=OLD, output_profile=PROFILE,
                source_owner_manifest_sha256=digest(canonical(source_manifest)), original_wire_preserved=True,
                allowed_semantic_differences=['Registry representation only; /1 result profile bytes retained'],
                writable_activation=False, effects_executed=0)
    if dry_run: return dict(plan, status='DRY_RUN', declared_bytes=sum(x['bytes'] for x in source_manifest['files'].values()))
    target = Path(destination); require(not target.exists(), 'CONFLICT')
    target.mkdir(mode=0o700, parents=True)
    # Reuse the exact bounded fenced-restore verifier. Std streams are adapted
    # only at this CLI boundary; no runtime or provider is replaced.
    with patch('sys.stdin', SimpleNamespace(buffer=io.BytesIO(raw))), patch('sys.stdout', io.StringIO()):
        restore(target, role, 'omega-ref-pilot-format-copy')
    result = transform(target / 'session-inbox.sqlite')
    seal = json.loads((target / 'owner-seal.json').read_bytes()); seal['provider_registry'] = PROFILE
    from .configure import write
    write(target / 'owner-seal.json', seal)
    manifest = dict(plan, status='VERIFIED_FENCED_COPY', result=result,
                    destination_database_sha256=digest((target / 'session-inbox.sqlite').read_bytes()))
    private_write(target / 'format-upgrade.json', canonical(manifest))
    require(read(source, MAX_TOTAL) == raw, 'CONFLICT')
    return manifest


def main():
    p = argparse.ArgumentParser(); p.add_argument('--source', required=True); p.add_argument('--sha256', required=True)
    p.add_argument('--destination'); p.add_argument('--role', default='omega-agent'); p.add_argument('--dry-run', action='store_true')
    a = p.parse_args(); print(json.dumps(upgrade(a.source, a.sha256, a.destination, role=a.role, dry_run=a.dry_run), sort_keys=True))


if __name__ == '__main__': main()
