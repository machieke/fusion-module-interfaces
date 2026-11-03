"""Instantiate an accepted native configuration in its application owner's PVC.

Only an operator-selected, hashed local template is used. The caller supplies
an allocation identity, never a path or executable. This writes configuration,
not application results, provider data, occurrence deadlines or work budgets.
"""
import copy
import json
import os
from pathlib import Path

from fusion.contracts import canonical, digest, require
from fusion.lookup_contracts import identity as uid
from fusion.sustained_sessions import SustainedSessionStore


def public_config(value):
    """Freeze endpoint/policy selections while permitting current token rotation."""
    if type(value) is dict:
        return {k: ('CURRENT_AUTHORITY_TOKEN' if k=='credential' else
                    {n:'CURRENT_AUTHORITY_TOKEN' for n in v} if k=='service_credentials' else public_config(v))
                for k,v in value.items()}
    if type(value) is list:return [public_config(x) for x in value]
    return value


def template_files(path):
    path=Path(path); require(path.is_dir() and not path.is_symlink(),'NOT_AVAILABLE')
    files={}
    for entry in sorted(path.iterdir()):
        require(entry.is_file() and not entry.is_symlink() and entry.suffix=='.json','UNSUPPORTED_PROFILE')
        require(entry.stat().st_size<=131072,'OVERLOADED')
        files[entry.name]=json.loads(entry.read_bytes())
    require(1<=len(files)<=32 and 'application.json' in files,'NOT_AVAILABLE')
    require(len(canonical(files))<=1048576,'OVERLOADED')
    return files


def frozen_config(filename,value):
    # Trusted qualification failpoints are one-shot observation barriers, not
    # selected business semantics. Consuming the marker or arming another
    # barrier must not rebind an accepted session's endpoints, time policy or
    # numerical profile. Configuration still validates test-fault authority.
    if filename=='application.json':value={k:v for k,v in value.items() if k not in ('pause_at','test_failpoints')}
    if filename=='owner.json' and 'test_failpoints' in value:
        # Private templates also retain the native memory owner recipe. Keep
        # its historical unarmed canonical value so existing /3 allocations
        # remain byte-compatible when a trusted one-shot barrier is armed or
        # consumed. Do not normalize its authority, paths or business policy.
        value={**value,'test_failpoints':False};value.pop('pause_at',None)
    return public_config(value)

def runtime_digest(files, ca_file):
    return digest(canonical(dict(files={name:frozen_config(name,value) for name,value in files.items()}, ca_sha256=digest(Path(ca_file).read_bytes()))))


def materialize(config, state, run, session):
    """Recover accepted configuration after allocation/reply or supervisor loss."""
    uid(session);cfg=json.loads(Path(config).read_bytes());selected=cfg['native_sessions'];principal=selected['principal']
    # Internal reads are within the application owner. Wire authority was
    # checked by the admitting service; native accesses recheck it separately.
    def authorize(who, scope, action):
        require(who==principal and any(t['principal']==who and t['scope']==scope for t in selected['allocation']['templates'].values()),'UNAUTHORIZED')
    store=SustainedSessionStore(selected['database'],authorize,selected['allocation'])
    try:allocated=store.allocated(principal,session)
    finally:store.close()
    name=allocated['template'];recipe=selected['runtime_templates'].get(name)
    require(type(recipe) is dict and set(recipe)=={'seed_session','directory','ca_file'},'NOT_AVAILABLE')
    uid(recipe['seed_session']);files=template_files(recipe['directory'])
    require(runtime_digest(files,recipe['ca_file'])==allocated['frozen']['runtime_digest'],'CONFLICT')
    own=Path(state)/'sessions'/session;destination=Path(run)/'sessions'/session
    require(not own.is_symlink() and not destination.is_symlink(),'UNAUTHORIZED')
    own.mkdir(parents=True,exist_ok=True,mode=0o700);destination.mkdir(parents=True,exist_ok=True,mode=0o700)
    seed=recipe['seed_session']
    def replace(value):
        if type(value) is str:return value.replace(seed,session)
        if type(value) is list:return [replace(x) for x in value]
        if type(value) is dict:return {replace(k):replace(v) for k,v in value.items()}
        return value
    files=replace(copy.deepcopy(files))
    # A trusted seed selection cannot address another session's mutable root.
    app=files['application.json']
    require(app['session_id']==session and Path(app['workdir'])==own/'native','CONFLICT')
    require(app['session_config']==str(destination/'session.json'),'CONFLICT')
    require(files['session.json']['session']==session and files['session.json']['principal']==principal,'CONFLICT')
    seal=own/'allocation-binding.json';binding=canonical(allocated)
    if seal.exists():require(seal.read_bytes()==binding,'CONFLICT')
    else:
        temporary=own/'allocation-binding.pending';temporary.write_bytes(binding);temporary.chmod(0o600)
        with temporary.open('rb') as stream:os.fsync(stream.fileno())
        os.replace(temporary,seal)
        fd=os.open(own,os.O_DIRECTORY)
        try:os.fsync(fd)
        finally:os.close(fd)
    for filename,value in files.items():
        path=destination/filename
        require(not path.is_symlink(),'UNAUTHORIZED')
        if path.exists():
            # Current credential rotation is allowed; no endpoint/profile or
            # frozen application selection can silently change at restart.
            require(frozen_config(filename,json.loads(path.read_bytes()))==frozen_config(filename,value),'CONFLICT')
        temporary=destination/(filename+'.pending');temporary.write_bytes(canonical(value));temporary.chmod(0o600)
        os.replace(temporary,path)
    return destination/'application.json'


def saved_projections(config, state, session):
    """Bounded read of this application's own journal, without constructing it.

    No native launcher, provider query, effect relay, model, or wake is called.
    In particular a task with missing publication cannot be finished here.
    """
    import sqlite3
    uid(session);cfg=json.loads(Path(config).read_bytes())['native_sessions']
    require(cfg['profile']=='omega-native-sessions/3','UNSUPPORTED_PROFILE')
    root=Path(state)/'sessions'/session;database=root/'caller.sqlite'
    require(not root.is_symlink() and not database.is_symlink(),'UNAUTHORIZED')
    if not database.exists():return []
    result=[]
    with sqlite3.connect(database.resolve().as_uri()+'?mode=ro',uri=True) as db:
        db.row_factory=sqlite3.Row
        tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not {'preview_native_inputs','app_turns','app_occurrences'}<=tables:return []
        rows=db.execute('''SELECT i.*,t.projection FROM preview_native_inputs i JOIN app_turns t ON t.id=i.turn
            WHERE i.acknowledged=0 AND t.projection IS NOT NULL ORDER BY i.turn LIMIT 33''').fetchall()
        require(len(rows)<=32,'OVERLOADED')
        for row in rows:
            source=json.loads(row['source']);require(source['session']==session and source['id']==row['identity'],'CONFLICT')
            import uuid
            require(source['occurrence']==str(uuid.uuid5(uuid.UUID(session),row['identity'])),'CONFLICT')
            origin=source.get('task_origin')
            if origin and origin['record']['kind']=='task':
                if 'preview_task_outbox' not in tables:continue
                published=db.execute('SELECT ref,receipt FROM preview_task_outbox WHERE id=?',('result/'+origin['record']['id'],)).fetchone()
                if published is None or any(x is None for x in published):continue
            occurrences=db.execute('SELECT id,done FROM app_occurrences WHERE turn=? ORDER BY position',(row['turn'],)).fetchall()
            require(all(x['done']==1 for x in occurrences),'CONFLICT')
            proof=dict(identity=row['identity'],result=dict(turn=row['turn'],projection=row['projection'],occurrences=[x['id'] for x in occurrences]))
            require(len(canonical(proof))<=66560,'OVERLOADED');result.append(proof)
    return result
