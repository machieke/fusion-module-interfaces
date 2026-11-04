"""Optional closed maintenance port on the existing vector Search owner.

This profile does not extend the historical query descriptor or grant native
callers maintenance authority. No filesystem paths or arbitrary repairs cross
the port. Operator observations do not initiate a build.
"""
import json,uuid
from pathlib import Path
from .contracts import canonical,digest,require
from .registry import descriptor_read,selection_token
from .preview_memory_services import Access,search_owner
from . import preview_vector_contracts as c,lookup_contracts as a
from .search_repair import PROFILE,LIMITS,Repair,descriptor

ROUTE='/preview/search-maintenance'
OPS={'planRepair':1,'repair':3,'observeRepair':2}


def validate_plan(plan,scope,snapshot=None):
    require(type(plan) is dict and set(plan)=={'plan','plan_sha256'},'NOT_AVAILABLE')
    p=plan['plan'];require(type(p) is dict and set(p)==set('profile scope snapshot manifest_sha256 classification limits authority physical_erasure effect_replay capacity_refund supported'.split()),'NOT_AVAILABLE')
    require(p['profile']==PROFILE and p['scope']==scope and p['limits']==LIMITS and
        p['authority']=='replayable-owner-feed-and-lifecycle' and p['physical_erasure'] is False and
        p['effect_replay'] is False and p['capacity_refund'] is False,'NOT_AVAILABLE')
    c.snapshot(p['snapshot'],scope)
    if snapshot is not None:require(p['snapshot']==snapshot,'NOT_AVAILABLE')
    require(p['classification'] in ('MISSING_DERIVED_INDEX','CORRUPT_DERIVED_INDEX','DERIVED_INDEX_UNVERIFIED','MISSING_DERIVED_MANIFEST'),'NOT_AVAILABLE')
    require(type(p['supported']) is bool and p['supported']==(p['classification']!='CORRUPT_DERIVED_INDEX'),'NOT_AVAILABLE')
    h=p['manifest_sha256'];require(h is None or (type(h) is str and len(h)==64 and all(x in '0123456789abcdef' for x in h)),'NOT_AVAILABLE')
    require(plan['plan_sha256']==digest(canonical(p)),'NOT_AVAILABLE');return plan


def validate_result(value,operation,args,scope):
    if operation=='planRepair':return validate_plan(value,scope,args[0])
    validate_plan(args[0],scope)
    require(type(value) is dict and value.get('state') in ('absent','verified','needs-reconciliation'),'NOT_AVAILABLE')
    expected={'state','identity','plan_sha256'}
    if value['state']!='absent':expected|={'deadline_ms','attempts_spent','result'}
    require(set(value)==expected and value['identity']==args[1] and value['plan_sha256']==args[0]['plan_sha256'],'NOT_AVAILABLE')
    if value['state']=='absent':require(operation=='observeRepair','NOT_AVAILABLE');return value
    a.integer(value['deadline_ms'],1,2**53-1);a.integer(value['attempts_spent'],0,LIMITS['attempts'])
    if operation=='repair':require(value['deadline_ms']==args[2],'NOT_AVAILABLE')
    if value['state']=='needs-reconciliation':require(value['result'] is None,'NOT_AVAILABLE')
    else:
        require(value['result']==dict(profile=PROFILE,identity=args[1],snapshot=args[0]['plan']['snapshot'],
            source='authoritative-feed-replay',captured_queries_rewritten=False,capacity_refund=False,original_generation_retained=True),'NOT_AVAILABLE')
    return value


class Ports:
    def __init__(self,path,hook=lambda _:None):self.path,self.hook=path,hook
    def invoke(self,credential,q):
        require(type(q) is dict and set(q)=={'id','profile','scope','selection','operation','args'} and len(canonical(q))<=16384)
        a.identity(q['id']);require(q['profile']==PROFILE and q['selection']==selection_token(descriptor()),'UNSUPPORTED_PROFILE')
        op=q['operation'];require(type(op) is str and op in OPS,'UNSUPPORTED_OPERATION')
        args=q['args'];require(type(args) is list and len(args)==OPS[op])
        access=Access(self.path,credential,'search');policy=access.policy;cfg=policy.current()['active_memory']
        require(cfg.get('maintenance_profile')==PROFILE,'UNSUPPORTED_PROFILE');scope=cfg['scope']
        require(q['scope']==scope,'UNAUTHORIZED')
        def permit():
            require(policy.authenticate(credential)==access.principal,'UNAUTHORIZED')
            require(policy.current()['active_memory'].get('maintenance_profile')==PROFILE,'UNSUPPORTED_PROFILE')
            policy.check(access.principal,scope,'search.maintenance.'+op)
        original_authorize=access.authorize
        def current_authorize(selected,action):
            permit();return original_authorize(selected,action)
        access.authorize=current_authorize
        permit();access.authorize(scope,'build' if op=='repair' else 'ready')
        snap=args[0] if op=='planRepair' else validate_plan(args[0],scope)['plan']['snapshot']
        c.snapshot(snap,scope)
        owner=Repair(search_owner(self.path,access,snap['lifecycle'],self.hook))
        if op=='planRepair':value=owner.plan(snap)
        elif op=='repair':value=owner.apply(*args)
        else:value=owner.observe(*args)
        permit();validate_result(value,op,args,scope)
        return dict(id=q['id'],profile=PROFILE,selection=q['selection'],request_digest=digest(canonical(q)),principal=access.principal,value=value)


class Client:
    def __init__(self,config):
        self.cfg=config
        require(config['profile']==PROFILE and config['fallback'] is False and config['placement'] in ('local','network'),'UNSUPPORTED_PROFILE')
        require(descriptor_read(config['descriptor'])==descriptor(),'UNSUPPORTED_PROFILE')
        self.ca=digest(Path(config['endpoint']['ca_file']).read_bytes()) if config['placement']=='network' else None
    def call(self,operation,*args):
        cfg=self.cfg;require(operation in OPS and len(args)==OPS[operation],'UNSUPPORTED_OPERATION')
        q=dict(id=str(uuid.uuid4()),profile=PROFILE,scope=cfg['scope'],selection=selection_token(descriptor()),operation=operation,args=list(args))
        if cfg['placement']=='local':reply=Ports(cfg['provider_config']).invoke(cfg['credential'],q)
        else:
            from .preview_transport import invoke
            require(digest(Path(cfg['endpoint']['ca_file']).read_bytes())==self.ca,'CONFLICT')
            reply=invoke(cfg,ROUTE,q,args[2] if operation=='repair' else None)
        require(type(reply) is dict and set(reply)=={'id','profile','selection','request_digest','principal','value'},'NOT_AVAILABLE')
        require((reply['id'],reply['profile'],reply['selection'],reply['request_digest'],reply['principal'])==
            (q['id'],PROFILE,q['selection'],digest(canonical(q)),cfg['principal']),'NOT_AVAILABLE')
        return validate_result(reply['value'],operation,list(args),cfg['scope'])
