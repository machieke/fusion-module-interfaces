"""Bounded owner-local integrity observations for quiesced maintenance.

No effect executor or repair of authoritative records. The operator runs this
inside ONE owner's maintenance pod with exclusive ownership. Public summaries
contain counts/classes; exact affected paths remain in private backup manifests.
"""
import json,sqlite3
from contextlib import closing
from pathlib import Path
from types import SimpleNamespace
from fusion.contracts import canonical,digest,decode,require,ContractError
from fusion import sealed_archive as archive

PROFILE='bounded-owner-integrity/1'
MAX_DATABASES=96
MAX_SEGMENTS=256


def archive_dependencies(root):
    root=Path(root);databases=[]
    # This is backup tooling, not a consumer crossing an owner boundary.
    for path in root.rglob('*'):
        require(not path.is_symlink(),'UNAUTHORIZED')
        if path.is_file() and path.suffix in ('.sqlite','.sqlite3','.db'):databases.append(path)
        require(len(databases)<=MAX_DATABASES,'OVERLOADED')
    results=[];dependencies={};segments=0;charged=0;sealed_bytes=0;reserved=0;local_checks=[]
    for path in databases:
        rel=str(path.relative_to(root))
        try:
            wal=Path(str(path)+'-wal')
            if wal.exists() and wal.stat().st_size:
                results.append(dict(database=rel,classification='OBSERVATION_UNAVAILABLE',error='UNQUIESCED_WAL'));continue
            # Export checkpoints first; restore contains that exact checkpoint.
            # Immutable mode avoids creating/removing WAL/SHM files during
            # verification of an already fenced, quiesced archive. It is never
            # used as a live owner's consistency shortcut.
            with closing(sqlite3.connect(path.resolve().as_uri()+'?mode=ro&immutable=1',uri=True,timeout=.2)) as db:
                db.row_factory=sqlite3.Row
                db.execute('PRAGMA query_only=ON');db.execute('BEGIN')
                # A CPU-work bound prevents hostile/corrupt journals from
                # turning an observation into an unbounded table traversal.
                remaining=[5000]
                def progress():remaining[0]-=1;return int(remaining[0]<=0)
                db.set_progress_handler(progress,1000)
                tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                require(tuple(db.execute('PRAGMA quick_check(1)').fetchone())==('ok',),'CONFLICT')
                from .integrated_journal_integrity import inspect
                checked=inspect(db,tables)
                local_checks.append(dict(database=rel,checked=checked['checked'],unresolved=checked['unresolved']))
                results.extend(dict(database=rel,**finding) for finding in checked['findings'])
                if not archive.TABLES & tables:continue
                require(archive.TABLES<=tables and {'feed_meta','feed_atoms'}<=tables,'CONFLICT')
                meta=json.loads(db.execute('SELECT value FROM feed_meta').fetchone()[0]);selected=archive.policy(meta['archive'])
                require(tuple(db.execute('SELECT value FROM feed_archive_policy').fetchone())==(canonical(selected).decode(),),'CONFLICT')
                owner=SimpleNamespace(path=path,source=meta['source'],archive_policy=selected)
                rows=db.execute('SELECT * FROM feed_archive_intents ORDER BY id LIMIT ?', (MAX_SEGMENTS+1,)).fetchall()
                segments+=len(rows);require(segments<=MAX_SEGMENTS,'OVERLOADED')
                for row in rows:
                    require(row[4] in ('reserved','sealed') and row[7]==archive.RESERVATION_BYTES,'CONFLICT');charged+=row[7]
                    intent=json.loads(row[3]);require(intent['source']==meta['source'] and intent['scope_ref']==row[2],'CONFLICT')
                    members=db.execute('SELECT scope,atom,ordinal FROM feed_archive_members WHERE segment=? ORDER BY ordinal',(row[0],)).fetchall()
                    require([tuple(x) for x in members]==[(row[2],item['value']['write']['ref']['id'],i) for i,item in enumerate(intent['records'])],'CONFLICT')
                    for item in intent['records']:
                        source=db.execute('SELECT value FROM feed_atoms WHERE scope=? AND sequence=?',(row[2],item['sequence'])).fetchone()
                        require(source is not None and tuple(source)==(canonical(item['value']).decode(),),'CONFLICT')
                    if row[4]=='reserved':reserved+=1;continue
                    file=Path(str(path)+'.archive')/(row[0]+'.json')
                    if not file.is_file():
                        results.append(dict(database=rel,classification='MISSING_AUTHORITATIVE_ARCHIVE',segment=row[0]));continue
                    try:
                        value=archive._read(owner,row)
                        for item in value['records']:
                            raw=decode(item['data']);require(len(raw)==item['value']['size'] and digest(raw)==item['value']['write']['ref']['digest'],'CONFLICT')
                    except (ContractError,ValueError,TypeError,KeyError):
                        results.append(dict(database=rel,classification='CORRUPT_AUTHORITATIVE_ARCHIVE',segment=row[0]));continue
                    relative=str(file.relative_to(root));dependencies[relative]=dict(bytes=row[6],sha256=row[5],database=rel)
                    sealed_bytes+=row[6]
                orphans=db.execute('SELECT count(*) FROM feed_archive_members m LEFT JOIN feed_archive_intents i ON i.id=m.segment WHERE i.id IS NULL').fetchone()[0]
                require(orphans==0,'CONFLICT')
        except sqlite3.OperationalError as error:
            # A timeout/interrupt is never evidence that a record is absent.
            results.append(dict(database=rel,classification='OBSERVATION_UNAVAILABLE',error=type(error).__name__))
        except (sqlite3.DatabaseError,ContractError,ValueError,TypeError,KeyError,IndexError) as error:
            results.append(dict(database=rel,classification='CORRUPT_AUTHORITATIVE_JOURNAL',error=type(error).__name__))
    return dict(profile=PROFILE,status='PASS' if not results else 'REFUSED',findings=results,dependencies=dependencies,
        examined_databases=len(databases),local_checks=local_checks,segments=segments,sealed_segments=len(dependencies),reserved_segments=reserved,
        charged_bytes=charged,sealed_bytes=sealed_bytes,hot_deletion=False,repair='NONE',effect_replay=False,
        authority='OPERATOR_OWNER_LOCAL_NOT_CONSUMER_PERMISSION')


def summary(value):
    from collections import Counter
    return {**{k:v for k,v in value.items() if k not in ('findings','dependencies','local_checks')},
            'local_checks':[{'checked':x['checked'],'unresolved':x['unresolved']} for x in value['local_checks']],
            'finding_classes':dict(Counter(x['classification'] for x in value['findings'])),
            'dependency_manifest_sha256':digest(canonical(value['dependencies']))}
