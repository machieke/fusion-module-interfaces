"""Read existing guarded-workflow captures under fresh fenced-clone authority.

No live observer ports, runtime materialization, guard refresh, initializer,
worker or allocator is constructed. Stored selection/approval remains history.
The existing application's read-only Snapshot and Workflow serializer are reused.
"""
import json,uuid
from pathlib import Path
from types import SimpleNamespace
from fusion.contracts import canonical,digest,require,ContractError
from fusion.lookup_contracts import identity as uid
from fusion.policy import Policy
from fusion.sustained_restore import Snapshot
from fusion.guarded_continuation import Workflow,PROFILE,LIMITS,TABLES,guard_spec
from fusion.workflow_recipes import validate_steps,definition
from fusion.workflow_prerequisites import condition,PROFILE as GUARDS


def saved(raw):
    require(type(raw) is str and len(raw.encode())<=LIMITS['output_bytes'],'NOT_AVAILABLE')
    value=json.loads(raw);require(canonical(value).decode()==raw,'NOT_AVAILABLE');return value


def bounded(db,sql,args,limit):
    rows=db.execute(sql+' LIMIT ?',(*args,limit+1)).fetchall();require(len(rows)<=limit,'OVERLOADED');return rows


def observe(store,principal,session,workflow,authorize):
    row=store.db.execute('SELECT * FROM pilot_workflows WHERE id=? AND session=?',(workflow,session)).fetchone()
    require(row is not None,'NOT_FOUND');authorize('observe',row['scope'])
    selected=saved(row['selection']);require(type(selected) is dict,'NOT_AVAILABLE')
    # Clock affects only the retained status projection; it neither writes nor
    # turns a historic deadline into current execution authority.
    owner=Workflow(store,principal,SimpleNamespace(selections=selected),authorize,
        clock=lambda:row['last_ms'],initialize=False,observation_only=True)
    owner._state(workflow)
    accepted=saved(row['accepted']);recipe=accepted['recipe']['recipe']
    require(set(accepted)=={'profile','session','recipe','steps','deadline_ms','principal','scope','limits','effect_limit'},'NOT_AVAILABLE')
    require(type(row['last_ms']) is int and row['last_ms']>=0 and type(row['deadline']) is int and row['deadline']>0,'NOT_AVAILABLE')
    require(accepted['effect_limit']==len(accepted['steps']) and accepted['recipe']==definition(recipe),'NOT_AVAILABLE')
    validate_steps(recipe,accepted['steps']);require([x['node'] for x in accepted['steps']]==[x['id'] for x in definition(recipe)['nodes']],'NOT_AVAILABLE')
    require(row['status'] in ('ready','inflight','prerequisite-held','operator-held','refused','expired','complete'),'NOT_AVAILABLE')
    require(1<=row['version']<=LIMITS['amendments']+1 and 0<=row['observations']<=LIMITS['observations'] and
        0<=row['reservations']<=accepted['effect_limit'],'NOT_AVAILABLE')
    versions=bounded(store.db,'SELECT * FROM pilot_workflow_versions WHERE workflow=? ORDER BY version',(workflow,),LIMITS['amendments']+1)
    require([x['version'] for x in versions]==list(range(1,row['version']+1)),'NOT_AVAILABLE');plans={}
    for version in versions:
        plan=saved(version['plan']);validate_steps(recipe,plan);seen=[]
        for step in plan:
            for guard in step['guards']:guard_spec(guard,row['scope'],seen)
            seen.append(step['node'])
        plans[version['version']]=plan
        inherited=saved(version['inherited'])
        require(inherited['deadline_ms']==row['deadline'],'NOT_AVAILABLE')
        fingerprint=inherited.get('original_digest') if version['version']==1 else inherited.get('original_sha256')
        require(fingerprint==digest(row['accepted'].encode()),'NOT_AVAILABLE')
    require(plans[1]==accepted['steps'],'NOT_AVAILABLE')
    steps=bounded(store.db,'SELECT * FROM pilot_workflow_steps WHERE workflow=?',(workflow,),LIMITS['steps'])
    require(len(steps)==row['reservations'],'NOT_AVAILABLE')
    for step in steps:
        require(step['input_id']==str(uuid.uuid5(uuid.UUID(workflow),'native/'+step['node'])) and
            0<step['deadline']<=row['deadline'] and step['version'] in plans,'NOT_AVAILABLE')
        prior=next((x for x in plans[step['version']] if x['node']==step['node']),None)
        require(prior is not None and prior==next((x for x in plans[row['version']] if x['node']==step['node']),None),'NOT_AVAILABLE')
        vector=saved(step['vector']);require(type(vector) is dict and vector['profile']==GUARDS and vector['satisfied'] is True,'NOT_AVAILABLE')
        actual=owner._input(row,step)
        if step['receipt'] is not None:
            from fusion.sustained_sessions import TERMINAL,UNCERTAIN
            receipt=saved(step['receipt']);require(actual is not None,'NOT_AVAILABLE');latest=store.receipt(actual)
            require(set(receipt)==set(latest) and all(receipt[k]==v for k,v in latest.items() if k!='state') and
                receipt['state'] in TERMINAL+UNCERTAIN+('accepted',),'NOT_AVAILABLE')
            # Native completion may have committed after the workflow's last
            # receipt observation. Retain that older receipt without capturing
            # or synthesizing its newer result during this read-only operation.
            if receipt['state'] in TERMINAL:require(receipt['state']==latest['state'],'NOT_AVAILABLE')
        if step['result_digest'] is not None:
            require(actual is not None and actual['state']=='complete' and actual['result'] is not None and
                step['result_digest']==digest(canonical(actual['result'])),'NOT_AVAILABLE')
    observations=bounded(store.db,'SELECT * FROM pilot_workflow_observations WHERE workflow=? ORDER BY sequence',(workflow,),LIMITS['observations'])
    require([x['sequence'] for x in observations]==list(range(1,row['observations']+1)),'NOT_AVAILABLE')
    for item in observations:
        declared=saved(item['declared']);condition(declared,row['scope'])
        if item['value'] is not None:
            value=saved(item['value']);require(value['profile']==GUARDS and value['condition']==declared and
                value['condition_sha256']==digest(canonical(declared)) and value['selection_sha256']==digest(row['selection'].encode()) and
                value['state'] in ('SATISFIED','INVALID','UNKNOWN','UNAUTHORIZED') and value['observed_ms']>=value['started_ms'],'NOT_AVAILABLE')
    checkpoints=bounded(store.db,'SELECT * FROM pilot_workflow_checkpoints WHERE workflow=?',(workflow,),LIMITS['checkpoints'])
    require(row['hold'] is None or any(x['identity']==row['hold'] for x in checkpoints),'NOT_AVAILABLE')
    for item in checkpoints:
        binding=saved(item['binding']);require(binding['profile']==PROFILE and binding['workflow']==workflow and
            binding['identity']==item['identity'] and binding['deadline_ms']==row['deadline'] and binding['scope']==row['scope'] and
            binding['principal']==principal and binding['version'] in plans and
            binding['plan_sha256']==digest(canonical(plans[binding['version']])) and
            binding['selection_sha256']==digest(row['selection'].encode()) and binding['grants_authority'] is False,'NOT_AVAILABLE')
        captures={s['node']:s['result_digest'] for s in steps}
        require(all(k in captures and captures[k]==v for k,v in binding['captures'].items()),'NOT_AVAILABLE')
        if item['decision'] is not None:
            decision=saved(item['decision']);require(decision['binding_sha256']==digest(item['binding'].encode()) and
                decision['original_deadline_ms']==row['deadline'] and decision['version']==binding['version'] and
                decision['node']==binding['node'] and decision['action'] in ('approve','refuse') and
                decision['effective']==(decision['observed_ms']<row['deadline']) and decision['grants_authority'] is False,'NOT_AVAILABLE')
    value=owner.observe(workflow);authorize('observe',row['scope'])
    value.update(restore_fenced=True,execution_authorized=False,original_bindings_retained=True,
        retained_approval_is_current_authority=False,guard_refresh_performed=False,
        status_as_of_last_committed_transition_ms=row['last_ms'])
    require(len(canonical(value))<=LIMITS['output_bytes'],'OVERLOADED');return value


def invoke(config,state,credential,q):
    require(type(q) is dict and q.get('operation') in ('observe','list'),'UNAUTHORIZED')
    require(set(q)=={'profile','id','session','workflow','operation','body'} and q['body']=={},'INVALID_ARGUMENT')
    require(q['profile']==PROFILE,'UNSUPPORTED_PROFILE');uid(q['session'])
    if q['operation']=='observe':uid(q['workflow'])
    else:require(q['workflow'] is None,'INVALID_ARGUMENT')
    require(type(q['id']) is str and 0<len(q['id'])<=128 and len(canonical(q))<=4096,'INVALID_ARGUMENT')
    state=Path(state);fence=json.loads((state/'restore-fence.json').read_bytes())
    require(fence['mode']=='READ_ONLY_RECONCILIATION' and fence['external_effect_authority'] is False,'UNAUTHORIZED')
    policy=Policy(config);cfg=policy.current()['native_sessions'];actor=policy.authenticate(credential)
    require(actor=='operator','UNAUTHORIZED')
    path=Path(cfg['database']);require(path.is_file() and not path.is_symlink() and path.resolve()==(state/'session-inbox.sqlite').resolve(),'UNAUTHORIZED')
    def authority(who,scope,_):
        require(who==cfg['principal'] and policy.authenticate(credential)==actor,'UNAUTHORIZED')
        policy.check(actor,scope,'sessions.observe');policy.check(actor,scope,'sessions.disclose')
        if q['operation']=='list':policy.check(actor,scope,'sessions.list')
    store=Snapshot(path,authority,cfg['allocation'])
    try:
        allocation=store.allocated(cfg['principal'],q['session']);scope=allocation['frozen']['scope']
        def authorize(_,selected):require(selected==scope,'UNAUTHORIZED');authority(cfg['principal'],scope,'observe')
        authorize('observe',scope)
        tables={r[0] for r in store.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        require(set(TABLES)<=tables,'NOT_FOUND')
        rows=bounded(store.db,'SELECT id FROM pilot_workflows WHERE session=? ORDER BY id',(q['session'],),LIMITS['workflows'])
        if q['operation']=='observe':value=observe(store,cfg['principal'],q['session'],q['workflow'],authorize)
        else:
            summaries=[]
            for row in rows:
                item=observe(store,cfg['principal'],q['session'],row['id'],authorize)
                summaries.append({k:item[k] for k in ('workflow','session','scope','version','status','deadline_ms','reservations_spent','observations_spent')})
            value=dict(profile=PROFILE,session=q['session'],workflows=summaries,restore_fenced=True,
                execution_authorized=False,guard_refresh_performed=False,original_bindings_retained=True)
        authorize('observe',scope);require(len(canonical(value))<=LIMITS['output_bytes'],'OVERLOADED')
        return dict(profile=PROFILE,id=q['id'],request_digest=digest(canonical(q)),actor=actor,principal=cfg['principal'],value=value)
    except (KeyError,TypeError,ValueError,IndexError):raise ContractError('NOT_AVAILABLE') from None
    finally:store.close()
