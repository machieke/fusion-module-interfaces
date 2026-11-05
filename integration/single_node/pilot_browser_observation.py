"""Narrow current scoped application observations for the provisioned browser.

This executes in the native application owner. It reads its own session index
and existing declared owner ports; foreign journals are never opened.
"""
from fusion.contracts import canonical, digest, require
from fusion.lookup_contracts import identity
from fusion.policy import Policy
from fusion.sustained_sessions import SustainedSessionStore

PROFILE = 'scoped-browser-observation/1'
ROUTE = '/preview/browser'


def invoke(path, state, run, credential, request):
    require(type(request) is dict and set(request) in ({'id', 'profile', 'operation', 'scope', 'session'}, {'id', 'profile', 'operation', 'scope', 'session','navigation'}), 'INVALID_ARGUMENT')
    identity(request['id']); require(request['profile'] == PROFILE, 'UNSUPPORTED_PROFILE')
    require(request['operation'] in ('inventory', 'current','explore'), 'UNSUPPORTED_OPERATION')
    require(('navigation' in request)==(request['operation']=='explore'),'INVALID_ARGUMENT')
    policy = Policy(path); actor = policy.authenticate(credential); cfg = policy.current()['native_sessions']
    require(cfg['profile'] == 'omega-native-sessions/3', 'UNSUPPORTED_PROFILE')
    scope = request['scope']; principal = cfg['principal']
    require(type(scope) is str, 'UNAUTHORIZED')
    def authorize(who, selected, action):
        require(policy.authenticate(credential) == actor and who == principal and selected == scope, 'UNAUTHORIZED')
        policy.check(actor, scope, 'sessions.observe')
        if action == 'session.disclose': policy.check(actor, scope, 'sessions.disclose')
    authorize(principal, scope, 'observe')
    if request['operation'] == 'inventory':
        require(request['session'] is None)
        templates = {k: v for k, v in cfg['allocation']['templates'].items()
                     if v['principal'] == principal and v['scope'] == scope}
        require(templates, 'UNAUTHORIZED')
        store = SustainedSessionStore(cfg['database'], authorize, cfg['allocation'])
        try:
            rows = store.db.execute('SELECT id,state,scope FROM preview_sessions WHERE principal=? AND scope=? ORDER BY created,id', (principal, scope)).fetchall()
            require(len(rows) <= 64, 'OVERLOADED')
            sessions = {r['id']: dict(session=r['id'], state=r['state'], scope=scope) for r in rows}
            for sid in sessions: store.allocated(principal, sid)
        finally: store.close()
        from pathlib import Path
        value = dict(profile=cfg['profile'], principal=principal, scope=scope, sessions=sessions,
            templates=templates, assignments=cfg['assignments'], worker=None,
            capacity=dict(observation='NOT_DISCLOSED_AGGREGATE_CROSSES_SCOPE', admission='OWNER_RECHECKS'),
            model_boundary=sorted({t['binding']['model_boundary'] for t in templates.values()}),
            restore_fenced=(Path(state)/'restore-fence.json').exists(), additional_live_generations=0,
            observation='CURRENT_SCOPED_APPLICATION_OWNER', retained_provider_views='NOT_REFRESHED')
    else:
        identity(request['session'])
        store = SustainedSessionStore(cfg['database'], authorize, cfg['allocation'])
        try: store.allocated(principal, request['session'])
        finally: store.close()
        from .sustained_current import observe
        value = observe(request['session'], owner=path, state=state, run=run, credential=credential,navigation=request.get('navigation'))
        require(value['scope'] == scope, 'UNAUTHORIZED')
    authorize(principal, scope, 'observe')
    require(len(canonical(value)) <= 98304, 'OVERLOADED')
    return dict(profile=PROFILE, id=request['id'], request_digest=digest(canonical(request)), actor=actor, principal=principal, value=value)
