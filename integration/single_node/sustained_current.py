"""Current authorized ports alongside retained application views, never merged."""
import json,sqlite3,time,uuid
from pathlib import Path
from contextlib import closing
from fusion.contracts import require,canonical,digest
from fusion.policy import Policy
from fusion.preview_atoms import client as atoms
from fusion.preview_memory_services import Client as Memory
from fusion.preview_ports import Client as Facet
from fusion import cognitive_services as cs
from fusion.sustained_sessions import SustainedSessionStore
from .sustained_runtime import materialize,template_files


def observation_template(recipe):
    """Read selected restored ports without materializing an executable session.

    Templates retain seed-session paths for later native allocation. Shared and
    private recipes can have the same seed, so those paths must resolve within
    the selected template for fenced reads, not to the shared seed's files.
    """
    directory=Path(recipe['directory']);files=template_files(directory)
    source=Path(files['application.json']['session_config']).parent
    def selected(value):
        if type(value) is str:
            path=Path(value)
            return str(directory/path.name) if path.parent==source and path.name in files else value
        if type(value) is list:return [selected(x) for x in value]
        if type(value) is dict:return {k:selected(v) for k,v in value.items()}
        return value
    return selected(files['application.json'])


def observe(session,owner='/run/fusion/owner.json',state='/state',run='/run/fusion'):
    policy=Policy(owner);cfg=policy.current();selection=cfg['native_sessions'];principal=selection['principal']
    require(selection['profile']=='omega-native-sessions/3','UNSUPPORTED_PROFILE')
    token=cfg['principals']['operator']['credential']
    def authorize(who,scope,op):
        require(policy.authenticate(token)=='operator' and who==principal,'UNAUTHORIZED')
        for verb in ('observe','disclose'):policy.check('operator',scope,'sessions.'+verb)
    fenced=(Path(state)/'restore-fence.json').exists()
    if fenced:
        from fusion.sustained_restore import Snapshot
        store=Snapshot(selection['database'],authorize,selection['allocation'])
    else:store=SustainedSessionStore(selection['database'],authorize,selection['allocation'])
    try:allocation=store.allocated(principal,session)
    finally:store.close()
    scope=allocation['frozen']['scope'];authorize(principal,scope,'observe')
    if fenced:app=observation_template(selection['runtime_templates'][allocation['template']])
    else:app=json.loads(materialize(owner,Path(state),Path(run),session).read_bytes())
    from fusion.preview_tools import SessionAuthority
    raw=json.loads(Path(app['preview']['authority_file']).read_bytes());raw['tools']=frozenset(raw['tools'])
    authority=SessionAuthority(**raw);authority.check(principal,time.time_ns()//1000000)
    require(authority.scope==scope,'UNAUTHORIZED')
    result=dict(observation='CURRENT_OWNER_READS',scope=scope,session=session,observed_ms=time.time_ns()//1000000,
        atomic_cross_owner_snapshot=False,restore_fenced=fenced,retained=dict(observation='APPLICATION_CAPTURE_NOT_CURRENT_OWNER_HEAD'),
        model_boundary=allocation['frozen']['binding']['model_boundary'],generation_execution='NOT_REQUESTED')
    if 'memory_atoms_config' in app:
        a=atoms(json.loads(Path(app['memory_atoms_config']).read_bytes()))
        result.update(source_head=a.head(scope),storage_capacity=a.capacity(scope))
        lifecycle=Memory(app['active_memory_configs']['memory.lifecycle'],'memory.lifecycle')
        head=lifecycle.call('head');result['lifecycle']=dict(head=head,membership=lifecycle.call('activeSet',head))
        result['search']=Memory(app['active_memory_configs']['search'],'search').call('current',head)
    database=Path(state)/'sessions'/session/'caller.sqlite'
    if database.exists():
        with closing(sqlite3.connect(database.resolve().as_uri()+'?mode=ro',uri=True)) as db:
            tables={x[0] for x in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            view=None
            if 'app_active_view' in tables:
                row=db.execute('SELECT id,value FROM app_read_views WHERE id=(SELECT view FROM app_active_view)').fetchone()
                if row:
                    view=json.loads(row[1]);result['retained'].update(view_id=row[0],view=view)
            if 'preview_history_episode' in tables:
                row=db.execute('SELECT value FROM preview_history_episode').fetchone()
                if row:result['history']=Facet(app['facet_configs']['episodic.memory'],'episodic.memory').call('historySnapshot',json.loads(row[0]))
        if view and 'evidence_config' in app:
            selected,_=cs.client_configuration(app['evidence_config']);belief=cs.Remote(selected,'belief.revision')
            result['beliefs']=[belief.call('readBelief',b['claim'],b['context'],None) for b in view.get('beliefs',[])[:4]]
            result['belief_coverage']=dict(observed=len(result['beliefs']),known=len(view.get('beliefs',[])),maximum=4)
    if 'attention_config' in app:
        selected,_=cs.client_configuration(app['attention_config'])
        from fusion.sustained_observation import PROFILE,ROUTE
        from fusion.registry import selection_token
        from fusion.preview_transport import invoke
        descriptor=cs.catalogue(selected)['attention']
        q=dict(profile=PROFILE,id=str(uuid.uuid4()),scope=scope,selection=selection_token(descriptor),interface='attention',context=selected['context'])
        value=invoke(selected['ports']['attention'],ROUTE,q)
        require(type(value) is dict and set(value)=={'profile','id','request_digest','selection','principal','value'},'NOT_AVAILABLE')
        require((value['profile'],value['id'],value['request_digest'],value['selection'],value['principal'])==
            (PROFILE,q['id'],digest(canonical(q)),q['selection'],principal),'NOT_AVAILABLE')
        result['attention']=value['value']
    authorize(principal,scope,'observe')
    raw=json.loads(Path(app['preview']['authority_file']).read_bytes());raw['tools']=frozenset(raw['tools'])
    SessionAuthority(**raw).check(principal,time.time_ns()//1000000)
    require(len(canonical(result))<=98304,'OVERLOADED')
    return result
