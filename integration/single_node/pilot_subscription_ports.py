"""Existing application owner's scoped finite subscription port."""
from fusion.contracts import canonical,digest,require
from fusion.policy import Policy
from fusion.sustained_sessions import SustainedSessionStore
from fusion.pilot_subscriptions import PROFILE,Subscriptions

ROUTE='/preview/subscriptions'


def invoke(path,credential,q):
    require(type(q) is dict and set(q)=={'id','profile','operation','subscription','session','action','body'} and len(canonical(q))<=4096)
    require(q['profile']==PROFILE,'UNSUPPORTED_PROFILE')
    require(type(q['operation']) is str and type(q['subscription']) is str and 1<=len(q['subscription'])<=128 and
        type(q['session']) is str and type(q['body']) is dict and (q['action'] is None or type(q['action']) is str))
    require(type(q['id']) is str and 1<=len(q['id'])<=128)
    policy=Policy(path);actor=policy.authenticate(credential);cfg=policy.current()['native_sessions']
    require(cfg.get('pilot_subscriptions')==PROFILE,'UNSUPPORTED_PROFILE')
    principal=cfg['principal']
    def authority(who,scope,action):
        require(policy.authenticate(credential)==actor and who==principal,'UNAUTHORIZED')
        policy.check(actor,scope,'sessions.observe')
        if action=='session.disclose':policy.check(actor,scope,'sessions.disclose')
    store=SustainedSessionStore(cfg['database'],authority,cfg['allocation'])
    try:
        def authorize(session):store.allocated(principal,session)
        authorize(q['session']);owner=Subscriptions(store,actor,authorize)
        if q['operation']=='create':require(q['body'].get('session')==q['session'],'UNAUTHORIZED')
        else:require(owner._row(q['subscription'])['session']==q['session'],'UNAUTHORIZED')
        if q['operation']=='read':
            require(q['action'] is None and type(q['body']) is dict and set(q['body'])=={'limit'})
            value=owner.read(q['subscription'],q['body']['limit'])
        elif q['operation']=='snapshot':
            require(q['action'] is None and q['body']=={});value=owner.snapshot(q['subscription'],principal)
        else:value=owner.control(q['operation'],q['subscription'],q['action'],q['body'])
        return dict(profile=PROFILE,id=q['id'],request_digest=digest(canonical(q)),actor=actor,value=value)
    finally:store.close()
