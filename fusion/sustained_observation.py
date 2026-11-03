"""Bounded current owner observation, without effect execution or new budgets."""
from pathlib import Path
from .contracts import canonical,digest,require
from . import cognitive_services as cs

PROFILE='bounded-current-owner-observation/1'
ROUTE='/preview/owner-state'


def invoke(path,credential,q):
    require(type(q) is dict and set(q)=={'profile','id','scope','selection','interface','context'})
    require(q['profile']==PROFILE and q['interface']=='attention','UNSUPPORTED_PROFILE')
    cs.l.identity(q['id']);cs.n.identifier(q['context'])
    access=cs.Access(path,credential,'attention');cfg=access.policy.current()
    require(cfg.get('current_observations')==PROFILE and cfg['attention_provider']=='sqlite','UNSUPPORTED_PROFILE')
    require(q['selection']==access.selection(),'UNSUPPORTED_PROFILE')
    from .promotion import PromotionOwner
    value=PromotionOwner.current_state(Path(cfg['root'])/'attention.sqlite',access,q['scope'],q['context'])
    return dict(profile=PROFILE,id=q['id'],request_digest=digest(canonical(q)),selection=q['selection'],
        principal=access.principal,value=value)
