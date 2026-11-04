"""Diagnose disposable copies of real quiesced synthetic owner exports.

No live mounts or executors. Original archives remain byte-identical; corrupted
copies are deleted after bounded diagnosis. Authoritative repair is forbidden.
"""
import argparse,json,sqlite3,tarfile,tempfile
from contextlib import closing
from pathlib import Path
from fusion.contracts import canonical,digest,require
from integration.single_node.backup_payload import safe_name,synthetic_seal
from integration.single_node.integrated_integrity import archive_dependencies,summary


def unpack(path,directory):
    with tarfile.open(path,'r:gz') as archive:
        members=archive.getmembers()
        require(len(members)<=150000 and sum(x.size for x in members)<=64*1024*1024,'OVERLOADED')
        require(all(x.isfile() for x in members) and len({x.name for x in members})==len(members),'UNAUTHORIZED')
        manifest=json.load(archive.extractfile('backup-manifest.json'))
        require(manifest['schema']=='synthetic-owner-backup/1' and manifest['excluded_authority'],'UNAUTHORIZED')
        synthetic_seal(manifest['seal'],manifest['role'])
        require({x.name for x in members}=={'backup-manifest.json'}|{'state/'+x for x in manifest['files']},'CONFLICT')
        for name,pin in manifest['files'].items():
            relative=Path(name);safe_name(relative)
            raw=archive.extractfile('state/'+name).read();require(len(raw)==pin['bytes'] and digest(raw)==pin['sha256'],'CONFLICT')
            target=directory/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
    return manifest


def qualify(backup,output):
    source=Path(backup);target=Path(output);require(not target.exists(),'CONFLICT')
    report=dict(status='RUNNING',classification='REAL_NATIVE_BACKUP_DISPOSABLE_CORRUPTION_COPIES',
        cases=[],additional_live_generations=0,repair='NONE',effect_replay=False,live_state_mutations=0)
    def save():target.write_bytes(canonical(report))
    save()
    def case(role,name,mutate,expected):
        path=source/(role+'.tar.gz');before=digest(path.read_bytes())
        with tempfile.TemporaryDirectory(prefix='fusion-integrity-copy-') as tmp:
            root=Path(tmp);manifest=unpack(path,root)
            baseline=archive_dependencies(root);require(baseline['status']=='PASS','CONFLICT')
            mutate(root,manifest)
            finding=archive_dependencies(root);classes=summary(finding)['finding_classes']
            report['cases'].append(dict(role=role,case=name,source_archive_sha256=before,
                baseline=summary(baseline),diagnosis=summary(finding),expected=expected))
            save()
            require(finding['status']=='REFUSED' and expected in classes,'CONFLICT')
            require(finding['repair']=='NONE' and not finding['effect_replay'],'CONFLICT')
        require(digest(path.read_bytes())==before,'CONFLICT');save()
    def archive_file(root,manifest):
        require(manifest['archive_dependencies'],'NOT_AVAILABLE')
        return root/next(iter(manifest['archive_dependencies']))
    def corrupt_archive(root,manifest):
        path=archive_file(root,manifest);raw=bytearray(path.read_bytes());raw[-1]^=1;path.write_bytes(raw)
    def corrupt_view(root,_):
        candidates=[]
        for path in root.rglob('*.sqlite'):
            with closing(sqlite3.connect(path)) as db:
                if db.execute("SELECT 1 FROM sqlite_master WHERE name='app_read_views'").fetchone() and db.execute('SELECT count(*) FROM app_read_views').fetchone()[0]:candidates.append(path)
        require(candidates,'NOT_AVAILABLE')
        with closing(sqlite3.connect(candidates[0])) as db:
            db.execute("UPDATE app_read_views SET value='{}' WHERE id=(SELECT id FROM app_read_views LIMIT 1)")
            db.commit();require(db.execute('PRAGMA wal_checkpoint(TRUNCATE)').fetchone()[0]==0,'NOT_AVAILABLE')
    try:
        case('fusion-storage','missing-sealed-payload',lambda r,m:archive_file(r,m).unlink(),'MISSING_AUTHORITATIVE_ARCHIVE')
        case('fusion-storage','corrupt-sealed-payload',corrupt_archive,'CORRUPT_AUTHORITATIVE_ARCHIVE')
        case('omega-agent','retained-view-digest',corrupt_view,'CORRUPT_RETAINED_VIEW')
        case('omega-agent','broken-journal-header',lambda r,m:(r/'session-inbox.sqlite').write_bytes(b'corrupt-disposable-copy'),'CORRUPT_AUTHORITATIVE_JOURNAL')
        report.update(status='PASS',original_archives_unchanged=True,corruption_copies_removed=True)
    except BaseException as error:
        report.update(status='FAIL',failure=dict(type=type(error).__name__,code=getattr(error,'code',None)));raise
    finally:save()
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--backup',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();r=qualify(a.backup,a.output);print(json.dumps(dict(status=r['status'],cases=len(r['cases']),additional_live_generations=0)))
