"""Explicit durable controls for the existing resident native worker owner."""
import uuid
from fusion.contracts import canonical,digest,require
from fusion.lookup_contracts import identity as uid
from fusion.policy import Policy
from fusion.resident_workers import Workers,CONTROL

ROUTE='/preview/worker-control'

def invoke(config,credential,q,wake=lambda _:None):
    require(type(q) is dict and set(q)=={'id','profile','session','operation','identity'} and len(canonical(q))<=4096)
    uid(q['id']);uid(q['session']);require(q['profile']==CONTROL,'UNSUPPORTED_PROFILE')
    op=q['operation'];require(op in ('observe','drain','recycle','resume'),'UNSUPPORTED_OPERATION')
    policy=Policy(config);actor=policy.authenticate(credential);cfg=policy.current()['native_sessions']
    require('resident_worker' in cfg,'UNSUPPORTED_PROFILE')
    permission='sessions.'+('observe' if op=='observe' else 'resume' if op=='resume' else 'pause')
    def auth(principal,scope,action):
        require(principal==cfg['principal'] and policy.authenticate(credential)==actor,'UNAUTHORIZED');policy.check(actor,scope,permission)
    owner=Workers(cfg['database'],auth,cfg['allocation'],cfg['resident_worker'])
    try:value=owner.control(cfg['principal'],q['session'],op,q['identity'])
    finally:owner.close()
    if op=='resume':wake(q['session'])
    return dict(profile=CONTROL,id=q['id'],request_digest=digest(canonical(q)),actor=actor,value=value)
