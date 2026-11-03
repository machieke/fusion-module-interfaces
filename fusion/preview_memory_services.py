"""Explicit active-memory facet and Search profile over existing service owners.

Storage owns lifecycle. Search consumes authenticated lifecycle and immutable
feed ports. Normal retained reads recheck withdrawal; nothing erases payloads.
"""
from dataclasses import asdict
import json
from pathlib import Path
import uuid
from . import lookup_contracts as a, vector_contracts as v, preview_vector_contracts as c
from .contracts import canonical,digest,require
from .policy import Policy
from .ports import Mutation
from .registry import Descriptor,descriptor_read,selection_token
from .preview_lifecycle import MemoryLifecycle,PROFILE as LIFECYCLE

COMPOSITION='omega-active-memory-ports/1'
ROUTE='/preview/memory'
OPS={'memory.lifecycle':{'head':0,'change':3,'readEvents':3,'activeSet':1,'disclose':4},
     'search':{'build':4,'published':3,'current':1,'ready':1,'query':1,'authorize':2}}


def lifecycle_result(value,scope):
    v.fields(value,'profile logical_id revision state operation memory predecessor at source_head projection empirical_weight_transferred priority_transferred payload_erased result')
    require(value['profile']==LIFECYCLE and value['operation'] in ('introduce','supersede','withdraw'),'NOT_AVAILABLE')
    a.identity(value['logical_id']);a.integer(value['revision'],1,256);a.head(value['at'],scope,LIFECYCLE);a.source_head(value['source_head'],scope)
    require(value['projection']=='NOT_OBSERVED' and value['empirical_weight_transferred'] is False and
        value['priority_transferred'] is False and value['payload_erased'] is False,'NOT_AVAILABLE')
    require(value['state']==('withdrawn' if value['operation']=='withdraw' else 'active'),'NOT_AVAILABLE')
    for memory in (value['memory'],value['predecessor']):
        if memory is None:continue
        v.fields(memory,'uuid payload enrollment');a.identity(memory['uuid']);a.ref(memory['payload'],scope);a.ref(memory['enrollment'],scope)
    require(value['memory'] is not None and (value['predecessor'] is None)==(value['operation']=='introduce'),'NOT_AVAILABLE')
    expected={'introduce':'MEMORY-REGISTERED-PENDING-PUBLICATION','supersede':'MEMORY-SUPERSEDED-PENDING-PUBLICATION','withdraw':'WITHDRAWN_FROM_ACTIVE_VIEW_PENDING_PUBLICATION'}
    require(value['result']==expected[value['operation']],'NOT_AVAILABLE');return value


def descriptor(name):
    require(name in OPS,'UNSUPPORTED_OPERATION')
    return Descriptor('preview-active-'+name,name,'1.0.0' if name=='memory.lifecycle' else '3.2.0','1.0.0',
        frozenset({LIFECYCLE if name=='memory.lifecycle' else c.PROFILE}),frozenset(OPS[name]),
        frozenset({'scoped','process-restart','idempotent'}),98304,privacy=v.PRIVACY,
        features=frozenset({v.EXTRACTION,v.EMBEDDING,v.INDEX,COMPOSITION}))


class Access:
    def __init__(self,path,credential,name):
        self.policy,self.credential,self.name=Policy(path),credential,name
        self.principal=self.policy.authenticate(credential)
    def authorize(self,scope,operation):
        cfg=self.policy.current()['active_memory']
        require(cfg['profile']==COMPOSITION and scope==cfg['scope'] and scope.startswith('synthetic-'),'UNAUTHORIZED')
        require(self.policy.authenticate(self.credential)==self.principal,'UNAUTHORIZED')
        require(descriptor_read(cfg['descriptors'][self.name])==descriptor(self.name),'UNSUPPORTED_PROFILE')
        self.policy.check(self.principal,scope,self.name+'.'+operation)
        return self.principal


class Ports:
    def __init__(self,path,role,hook=lambda _:None):self.path,self.role,self.hook=Path(path),role,hook
    def invoke(self,credential,q):
        v.fields(q,'id composition scope interface selection operation args');a.identity(q['id'])
        require(q['composition']==COMPOSITION and len(canonical(q))<=98304,'UNSUPPORTED_PROFILE')
        name,op,args=q['interface'],q['operation'],q['args']
        require(type(name) is str and type(op) is str and name in OPS and op in OPS[name],'UNSUPPORTED_OPERATION')
        require(self.role==('fusion-storage' if name=='memory.lifecycle' else 'fusion-search'),'UNSUPPORTED_OPERATION')
        require(type(args) is list and len(args)==OPS[name][op])
        require(q['selection']==selection_token(descriptor(name)),'UNSUPPORTED_PROFILE')
        access=Access(self.path,credential,name);cfg=access.policy.current()['active_memory'];scope=cfg['scope']
        require(scope==q['scope'],'UNAUTHORIZED')
        access.authorize(scope,op)
        if name=='memory.lifecycle':
            from .vector_composition import ReadService
            atoms=ReadService(self.path,credential,self.hook).atoms
            owner=MemoryLifecycle(Path(cfg['root'])/'lifecycle.sqlite',atoms,access,scope,cfg['corpus'],self.hook)
            if op=='change':
                v.fields(args[0],'scope_ref idempotency_key intent_digest');command=Mutation(**args[0])
                require(type(args[2]) is dict and set(args[2])=={'logical_id','expected_revision','enrollment','deadline_ms'})
                value=owner.change(command,args[1],**args[2])
            elif op=='head':value=owner.head()
            elif op=='activeSet':value=owner.activeSet(*args)
            elif op=='readEvents':value=owner.readEvents(*args)
            else:value=owner.disclose(*args)
        else:
            from .memory_services import SearchPorts
            from .adapters.active_chroma import ActiveChroma
            source=SearchPorts(self.path,self.hook).atoms()
            lifecycle=Client(cfg['lifecycle_client'],'memory.lifecycle',inline=True)
            if op=='current':head=args[0]
            elif op in ('build','published'):head=args[1]
            elif op in ('query','ready'):head=args[0]['snapshot']['lifecycle'] if op=='query' else args[0]['lifecycle']
            else:head=args[1]['lifecycle']
            a.head(head,scope,LIFECYCLE)
            class RemoteLifecycle:
                def activeSet(self,through):return lifecycle.call('activeSet',through)
                def disclose(self,logical_id,memory,through,historical=False):return lifecycle.call('disclose',logical_id,memory,through,historical)
            search=ActiveChroma(Path(cfg['root'])/'active-search',source,source,access,scope,cfg['corpus'],v.EMBEDDING,RemoteLifecycle(),head,self.hook)
            if op=='current':
                from .contracts import ContractError
                try:
                    value=search.current()
                    if value['lifecycle']!=head:value=None
                except ContractError as error:
                    if error.code!='NOT_AVAILABLE':raise
                    value=None
            elif op=='build':value=search.build_named(scope,args[0],args[2],args[3])
            elif op=='published':value=search.published(scope,args[0],args[2])
            elif op=='ready':value=search.ready(scope,args[0])
            elif op=='query':value=search.query(c.query(args[0]))
            else:
                from .preview_text import query
                query(access.policy.current()['memory_read'],args[0],access.principal)
                search.ready(scope,args[1])
                for member in search.membership['active']:
                    lifecycle.call('disclose',member['logical_id'],{k:member[k] for k in ('uuid','payload','enrollment')},head,False)
                value={'authorized':True}
        access.authorize(scope,op)
        reply=dict(id=q['id'],request_digest=digest(canonical(q)),selection=q['selection'],principal=access.principal,value=value)
        require(len(canonical(reply))<=98304,'OVERLOADED')
        return reply


class Client:
    def __init__(self,path,name,*,inline=False):
        self.path,self.name,self.inline=path,name,inline;self.cfg,self.frozen=self.current()
    def current(self):
        cfg=self.path if self.inline else json.loads(Path(self.path).read_text())
        require(cfg['composition']==COMPOSITION and cfg['placement'] in ('local','network') and cfg['fallback'] is False,'UNSUPPORTED_PROFILE')
        require(descriptor_read(cfg['descriptors'][self.name])==descriptor(self.name),'UNSUPPORTED_PROFILE')
        frozen={k:v for k,v in cfg.items() if k!='credential'}
        if cfg['placement']=='network':frozen={**frozen,'ca_sha256':digest(Path(cfg['endpoint']['ca_file']).read_bytes())}
        return cfg,frozen
    def call(self,op,*args,deadline=None):
        cfg,frozen=self.current();require(frozen==self.frozen,'CONFLICT')
        require(type(op) is str and op in OPS[self.name] and len(args)==OPS[self.name][op],'UNSUPPORTED_OPERATION')
        q=dict(id=str(uuid.uuid4()),composition=COMPOSITION,scope=cfg['scope'],interface=self.name,
            selection=selection_token(descriptor(self.name)),operation=op,args=[asdict(x) if isinstance(x,Mutation) else x for x in args])
        if cfg['placement']=='local':reply=Ports(cfg['provider_config'],'fusion-storage' if self.name=='memory.lifecycle' else 'fusion-search').invoke(cfg['credential'],q)
        else:
            from .preview_transport import invoke
            reply=invoke(cfg,ROUTE,q,deadline)
        require(type(reply) is dict and set(reply)=={'id','request_digest','selection','principal','value'},'NOT_AVAILABLE')
        require((reply['id'],reply['request_digest'],reply['selection'],reply['principal'])==
            (q['id'],digest(canonical(q)),q['selection'],cfg['principal']),'NOT_AVAILABLE')
        value=reply['value']
        if self.name=='search':
            if op=='current' and value is not None:
                c.snapshot(value,cfg['scope']);require(value['lifecycle']==args[0],'NOT_AVAILABLE')
            elif op in ('build','published') and value is not None:
                c.snapshot(value,cfg['scope']);require(value['head']==args[0] and value['lifecycle']==args[1],'NOT_AVAILABLE')
            elif op=='query':c.result(value,args[0])
            elif op in ('ready','authorize'):require(value=={'ready' if op=='ready' else 'authorized':True},'NOT_AVAILABLE')
        elif op=='head':a.head(value,cfg['scope'],LIFECYCLE)
        elif op=='change':
            lifecycle_result(value,cfg['scope']);expected=args[2]
            require(value['operation']==args[1] and value['revision']==expected['expected_revision']+1,'NOT_AVAILABLE')
            if expected['logical_id'] is not None:require(value['logical_id']==expected['logical_id'],'NOT_AVAILABLE')
            if expected['enrollment'] is not None:require(value['memory']['enrollment']==expected['enrollment'],'NOT_AVAILABLE')
        elif op=='readEvents':
            v.fields(value,'at events next complete');require(value['at']==args[1] and type(value['events']) is list and len(value['events'])<=args[2],'NOT_AVAILABLE')
            for offset,event in enumerate(value['events']):
                lifecycle_result(event,cfg['scope']);require(event['at']['sequence']==args[0]+offset+1,'NOT_AVAILABLE')
            require(value['next']==args[0]+len(value['events']) and value['complete']==(value['next']==args[1]['sequence']),'NOT_AVAILABLE')
        elif op=='disclose':require(value=={'authorized':True,'captured_bytes_rewritten':False,'physical_erasure':False},'NOT_AVAILABLE')
        elif op=='activeSet':
            v.fields(value,'at active');require(value['at']==args[0] and type(value['active']) is list and len(value['active'])<=256,'NOT_AVAILABLE')
            for item in value['active']:
                v.fields(item,'logical_id revision uuid payload enrollment');a.identity(item['logical_id']);a.identity(item['uuid']);a.integer(item['revision'],1,256)
                a.ref(item['payload'],cfg['scope']);a.ref(item['enrollment'],cfg['scope'])
            require(len({x['logical_id'] for x in value['active']})==len(value['active'])==len({x['uuid'] for x in value['active']}),'NOT_AVAILABLE')
        return value
