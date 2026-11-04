"""Pure bounded checks of one quiesced owner's authoritative projections.

Called with the same read-only SQLite snapshot as archive diagnostics. No
foreign files, providers, execution, repairs or opaque payload guesses. A
failed consistency check fences export; private IDs stay in local findings.
"""
import json
from types import SimpleNamespace
from fusion.contracts import canonical,digest,require,ContractError


def inspect(db,tables):
    findings=[];counts={};unresolved={}
    def check(name,fn):
        try:fn()
        except (ContractError,ValueError,KeyError,TypeError,IndexError) as error:
            findings.append(dict(classification=name,error=getattr(error,'code',type(error).__name__)))
    def views():
        rows=db.execute('SELECT id,value FROM app_read_views LIMIT 513').fetchall();require(len(rows)<=512,'OVERLOADED')
        for key,raw in rows:require(digest(canonical(json.loads(raw)))==key,'CONFLICT')
        if 'app_active_view' in tables:
            require(db.execute('SELECT count(*) FROM app_active_view a LEFT JOIN app_read_views v ON a.view=v.id WHERE v.id IS NULL').fetchone()[0]==0,'NOT_AVAILABLE')
        if 'app_query_views' in tables:
            require(db.execute('SELECT count(*) FROM app_query_views q LEFT JOIN app_read_views v ON q.view=v.id WHERE v.id IS NULL').fetchone()[0]==0,'NOT_AVAILABLE')
        counts['retained_view_digests']=len(rows)
    if 'app_read_views' in tables:check('CORRUPT_RETAINED_VIEW',views)
    def inspections():
        from fusion.inspection_continuation import Continuation,STEPS
        require({'app_occurrences','preview_inspections','integrated_inspection_steps'}<=tables,'NOT_AVAILABLE')
        rows=db.execute('SELECT occurrence,selection FROM integrated_inspection_continuations LIMIT 129').fetchall();require(len(rows)<=128,'OVERLOADED')
        for occurrence,selection in rows:
            row=db.execute('SELECT * FROM app_occurrences WHERE id=?',(occurrence,)).fetchone();require(row is not None,'NOT_AVAILABLE')
            owner=Continuation(SimpleNamespace(db=db,preview=SimpleNamespace(authorize=lambda _:None)),json.loads(selection),initialize=False)
            value=owner.observe(row);seen={}
            for step in STEPS:
                saved=db.execute('SELECT inputs,capture_digest FROM integrated_inspection_steps WHERE occurrence=? AND step=?',(occurrence,step)).fetchone()
                if saved is None:continue
                i=STEPS.index(step);parent={} if i==0 else {STEPS[i-1]:seen[STEPS[i-1]]}
                require(json.loads(saved[0])==parent,'CONFLICT');seen[step]=saved[1]
            require(not row['done'] or ('ack' in seen and row['result'] is not None),'NOT_AVAILABLE')
            if value['status']=='needs-reconciliation':unresolved['inspection_effects']=unresolved.get('inspection_effects',0)+1
        counts['inspection_continuations']=len(rows)
    if 'integrated_inspection_continuations' in tables:check('CORRUPT_CONTINUATION_CAPTURE',inspections)
    def chains():
        from .integrated_restore_observation import observe_database,CHAIN
        rows=db.execute('SELECT occurrence FROM integrated_chain_continuations LIMIT 129').fetchall();require(len(rows)<=128,'OVERLOADED')
        for (occurrence,) in rows:
            value=observe_database(db,CHAIN,occurrence,lambda _:None)
            if value['submit_reservations'] and value['status'] not in ('finalized','rejected'):
                unresolved['chain_effects']=unresolved.get('chain_effects',0)+1
        counts['chain_continuations']=len(rows)
    if 'integrated_chain_continuations' in tables:check('CORRUPT_CHAIN_CAPTURE',chains)
    def relations():
        from fusion import lookup_contracts as c
        from fusion.preview_relations import PROFILE
        require({'preview_relation_intents','preview_relation_meta'}<=tables,'NOT_AVAILABLE')
        meta=json.loads(db.execute('SELECT value FROM preview_relation_meta').fetchone()[0]);require(meta['profile']==PROFILE,'CONFLICT')
        rows=db.execute('SELECT * FROM preview_relation_events ORDER BY scope,sequence LIMIT ?',(c.MAX_COMMANDS+1,)).fetchall();require(len(rows)<=c.MAX_COMMANDS,'OVERLOADED')
        heads={};assertions={}
        for row in rows:
            scope=row['scope'];sequence=row['sequence'];require(sequence==heads.get(scope,0)+1,'CONFLICT');heads[scope]=sequence
            value=json.loads(row['value']);prior=db.execute('SELECT result FROM preview_relation_intents WHERE identity=?',(row['identity'],)).fetchone()
            require(prior is not None and prior[0]==row['value'],'CONFLICT')
            if row['kind']=='assert':
                body=value['body'];require(body['assertion_id']==row['assertion']==row['identity'] and body['profile']==PROFILE,'CONFLICT')
                c.ref(value['ref'],scope);require(digest(canonical(body))==value['ref']['digest'],'CONFLICT')
                require(value['asserted_at']==c.make_head(meta['source'],scope,sequence,PROFILE),'CONFLICT');assertions[row['assertion']]=value['ref']
            else:
                require(row['kind']=='retract' and value['ref']==assertions[row['assertion']] and value['at']==c.make_head(meta['source'],scope,sequence,PROFILE),'CONFLICT')
        counts['relation_events']=len(rows)
        unresolved['uncommitted_relation_intents']=db.execute('SELECT count(*) FROM preview_relation_intents WHERE result IS NULL').fetchone()[0]
    if 'preview_relation_events' in tables:check('INCONSISTENT_RELATION_JOURNAL',relations)
    return dict(findings=findings,checked=counts,unresolved=unresolved,repair='NONE',effect_replay=False)
