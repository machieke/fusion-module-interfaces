"""Owner-local bounded headroom for the existing operator diagnostics.

No central admission authority or cross-owner snapshot. Run only by operator
RBAC in each owner's pod. Scope identities, credentials and payloads never
leave this report; source partitions have numeric labels. Counts unavailable
because of a missing/locked/corrupt file stay unknown, not zero. This helper
opens read-only snapshots and never creates an owner or invokes any provider.
"""
import json,sqlite3
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from fusion.contracts import require,ContractError

PROFILE='bounded-owner-headroom/1'


def bound(category,used,limit,reserved=0,unit='records',basis='lifetime'):
    require(type(category) is str and type(limit) is int and limit>0)
    require(used is None or type(used) is int and used>=0)
    require(type(reserved) is int and reserved>=0)
    remaining=None if used is None else limit-used-reserved
    state='UNKNOWN' if remaining is None else 'EXCEEDED' if remaining<0 else 'FULL' if remaining==0 else 'HIGH_WATER' if (used+reserved)*10>=limit*9 else 'AVAILABLE'
    return dict(category=category,used=used,reserved=reserved,limit=limit,remaining=remaining,unit=unit,basis=basis,state=state,
        authority='OWNER_ENFORCED_NOT_A_PREFLIGHT_PROMISE')


@contextmanager
def snapshot(path):
    require(path.is_file() and not path.is_symlink(),'NOT_AVAILABLE')
    db=sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True,timeout=.2)
    try:
        db.row_factory=sqlite3.Row;db.execute('PRAGMA query_only=ON');db.execute('BEGIN')
        remaining=[5000]
        def progress():remaining[0]-=1;return int(remaining[0]<=0)
        db.set_progress_handler(progress,1000)
        yield db
    finally:db.close()


def collect(root=Path('/state'),run=Path('/run/fusion')):
    root,run=Path(root),Path(run);rows=[];unavailable=[];uncertainty={}
    cfg={};file=run/'owner.json'
    if file.is_file():
        require(not file.is_symlink() and file.stat().st_size<=1048576,'NOT_AVAILABLE')
        cfg=json.loads(file.read_bytes())
    seal=root/'owner-seal.json'
    role=json.loads(seal.read_bytes()).get('role','UNKNOWN') if seal.is_file() else cfg.get('role','UNKNOWN')
    def inspect(label,relative,fn):
        try:
            with snapshot(root/relative) as db:fn(label,db)
        except (sqlite3.Error,ContractError,ValueError,KeyError,TypeError,IndexError) as error:
            unavailable.append(dict(partition=label,status='UNKNOWN',reason=getattr(error,'code',type(error).__name__)))
    def n(db,sql):return db.execute(sql).fetchone()[0]
    def sessions(label,db):
        from fusion.sustained_sessions import SustainedSessionStore,MAX_ACTIONS
        from fusion.provider_lifecycle import MAX_ACTIONS as PROVIDER_ACTIONS,MAX_RECORDS
        from fusion.resident_workers import LIMITS
        usage=SustainedSessionStore._usage(SimpleNamespace(db=db));limits=cfg['native_sessions']['allocation']
        for key in ('retained','active','pending'):rows.append(bound(key+'_sessions' if key!='pending' else 'pending_inputs',usage[key],limits[key],basis='retained' if key=='retained' else 'concurrent'))
        rows.append(bound('application_logical_bytes',usage['logical_bytes'],limits['bytes'],usage['completion_reserved_bytes'],'bytes'))
        rows.append(bound('application_control_actions',n(db,'SELECT count(*) FROM sustained_actions'),MAX_ACTIONS))
        uncertainty['inputs_needing_reconciliation']=n(db,"SELECT count(*) FROM preview_inputs WHERE state IN ('dispatched','cancel-requested','needs-reconciliation')")
        tables={x[0] for x in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        for table,category,limit in [('integrated_providers','provider_records',MAX_RECORDS),('integrated_provider_actions','provider_actions',PROVIDER_ACTIONS),('native_worker_epochs','worker_incarnations',LIMITS['incarnations'])]:
            if table in tables:rows.append(bound(category,n(db,'SELECT count(*) FROM '+table),limit))
    if 'native_sessions' in cfg:inspect('application','session-inbox.sqlite',sessions)
    def feed(label,db):
        from fusion.sustained_feed import usage
        meta=json.loads(n(db,'SELECT value FROM feed_meta'));policy=meta.get('capacity')
        if policy:
            # Only partitions actually owned by this feed; no private name is
            # exported and no aggregate is exposed on a consumer port.
            for index,scope in enumerate(policy['scopes']):
                current=usage(None,db,scope);prefix=label+'-scope-'+str(index+1)+'-'
                rows.extend([bound(prefix+'feed_records',current['reserved_records'],policy['records']),
                    bound(prefix+'feed_charged_bytes',current['charged_bytes'],policy['bytes'],unit='bytes')])
                uncertainty[prefix+'unpublished_reservations']=current['pending_records']
        tables={x[0] for x in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if 'feed_archive_intents' in tables:
            policy=meta['archive']
            for index,scope in enumerate(meta.get('capacity',{}).get('scopes',[])):
                count,charge,pending=db.execute("SELECT count(*),coalesce(sum(charge),0),coalesce(sum(state='reserved'),0) FROM feed_archive_intents WHERE scope=?",(scope,)).fetchone()
                prefix=label+'-scope-'+str(index+1)
                rows.extend([bound(prefix+'-archive_segments',count,policy['segments']),bound(prefix+'-archive_charged_bytes',charge,policy['bytes'],unit='bytes')])
                uncertainty[prefix+'-unsealed_reservations']=pending
    if role=='fusion-storage':
        for label,relative in [('shared','memory/feed.sqlite'),('private-1','scopes/private-a/memory/feed.sqlite'),('private-2','scopes/private-b/memory/feed.sqlite')]:
            if (root/relative).is_file() or label=='shared':inspect(label,relative,feed)
    def model(label,db):
        limit=cfg['model_completion']['max_calls'];rows.append(bound('model_call_occurrences',n(db,'SELECT count(*) FROM model_calls'),limit))
        uncertainty['reserved_model_calls_without_capture']=n(db,'SELECT count(*) FROM model_calls WHERE reserved>0 AND response IS NULL')
    if 'model_completion' in cfg:inspect('model','model.sqlite',model)
    def encoder(label,db):
        from fusion.embedding_contracts import MAX_OCCURRENCES
        rows.append(bound('embedding_occurrences',n(db,'SELECT count(*) FROM encode_intents'),MAX_OCCURRENCES))
        uncertainty['uncaptured_encoder_reservations']=n(db,'SELECT count(*) FROM encode_attempts WHERE finished=0')
    if 'embedding' in cfg:inspect('embedding','encoder.sqlite',encoder)
    def execution(label,db):
        from fusion.neoclaw_contracts import MAX_REQUESTS
        tables={x[0] for x in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        pending=n(db,"SELECT count(*) FROM jobs WHERE state='queued'")+n(db,'SELECT count(*) FROM outbox WHERE sent=0')
        rows.append(bound(label+'-pending_work',pending,cfg['capacity'],basis='concurrent'))
        # Only named NAL enforces the lifetime MAX_REQUESTS ceiling; generic
        # inspect history is reported as usage with unknown lifetime capacity.
        if label=='nal':rows.append(bound('nal_retained_requests',n(db,'SELECT count(*) FROM jobs'),MAX_REQUESTS))
        if 'integrated_execution_events' in tables:rows.append(bound('inspection_notifications',n(db,'SELECT count(*) FROM integrated_execution_events'),384))
        uncertainty[label+'-undelivered_results']=n(db,'SELECT count(*) FROM outbox WHERE sent=0')
    if role=='fusion-execution':
        for label,name in [('nal','execution.sqlite'),('inspect','preview-inspect.sqlite')]:
            if (root/name).is_file():inspect(label,name,execution)
    require(len(rows)<=128 and len(uncertainty)<=64,'OVERLOADED')
    return dict(profile=PROFILE,owner=role,bounds=rows,uncertainty=uncertainty,unavailable=unavailable,
        coverage='SELECTED_APPLICATION_FEED_ARCHIVE_MODEL_EMBEDDING_EXECUTION',other_owner_lifetime_headroom='NOT_OBSERVED',
        authority='CURRENT_OPERATOR_POD_RBAC_OWNER_LOCAL',cross_owner_atomic=False,preflight_reserves=False,
        refunds=False,archive_reclaims_total_quota=False,high_water_policy='90_PERCENT_OBSERVATIONAL; EXACT_OWNER_ADMISSION_LIMITS_UNCHANGED',
        completion_reservations='INCLUDED_IN_APPLICATION_BYTE_HEADROOM',additional_live_generations=0)

if __name__=='__main__':print(json.dumps(collect(),sort_keys=True))
