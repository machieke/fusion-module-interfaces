"""Trusted S03 composition. Reuses the registry, policy, feed and DeTTa owners.

New shareable descriptors do not reinterpret M5's private-local-only descriptors.
"""
import json
from pathlib import Path
from . import vector_contracts as c, lookup_contracts as a
from .contracts import canonical,digest,require,ContractError,encode,decode
from .registry import Descriptor,Requirement,resolve,descriptor_read,selection_token
from .policy import Policy
from .lookup_composition import AtomSession

OPERATIONS={'atom.storage':('create','get','getMany','availability','head','readCommits'),'search':('query','build')}


def descriptors(embedding,ready=False):
    c.model(embedding)
    return [Descriptor('s03-feed-detta' if name=='atom.storage' else 's03.2-chroma-read' if ready else 's03-chroma',name,'1.1.0' if name=='atom.storage' else '3.1.0' if ready else '3.0.0','0.1.0',
        frozenset({a.FEED if name=='atom.storage' else c.PROFILE}),frozenset((*operations,'ready') if ready and name=='search' else operations),
        frozenset({'process-restart','scoped'}),4096,privacy=c.PRIVACY,deterministic=name=='atom.storage',
        features=frozenset({c.EXTRACTION,embedding,c.INDEX}),receipt_providers=frozenset({'detta-local-rs/1'})) for name,operations in OPERATIONS.items()]


def select(catalogue,embedding,ready=False):
    return {d.interface:resolve(catalogue,Requirement(d.interface,d.version,'1.2.0' if d.interface=='atom.storage' else '3.2.0' if ready else '3.1.0',next(iter(d.profiles)),d.operations,d.guarantees,privacy=c.PRIVACY,features=d.features)) for d in descriptors(embedding,ready)}


class Access:
    def __init__(self,policy,credential,descriptor,scope,embedding):
        self.policy,self.credential,self.descriptor,self.scope,self.embedding=policy,credential,descriptor,scope,embedding
        self.principal=policy.authenticate(credential)
    def authorize(self,scope,operation):
        require(scope==self.scope,'UNAUTHORIZED');require(operation in self.descriptor.operations,'UNSUPPORTED_OPERATION')
        require(self.policy.authenticate(self.credential)==self.principal,'UNAUTHORIZED')
        cfg=self.policy.current()['memory_read']
        require(cfg['sharing']==c.PRIVACY and cfg['scope']==scope and self.principal in cfg['readers'],'UNAUTHORIZED')
        selected=select([descriptor_read(x) for x in cfg['catalogue']],self.embedding,cfg.get('require_ready',False))
        require(selection_token(selected[self.descriptor.interface])==selection_token(self.descriptor),'UNSUPPORTED_PROFILE')
        self.policy.check(self.principal,scope,self.descriptor.interface+'.'+operation)
        return self.principal


class ReadService:
    def __init__(self,config_path,credential,hook=lambda _:None,*,atoms=None):
        self.policy=Policy(config_path);self.config=self.policy.current()['memory_read']
        cfg=self.config;self.credential=credential
        self.chosen=select([descriptor_read(x) for x in cfg['catalogue']],cfg['embedding'],cfg.get('require_ready',False))
        self.access={n:Access(self.policy,credential,d,cfg['scope'],cfg['embedding']) for n,d in self.chosen.items()}
        if atoms is None:
            from .atom_feed import FeedAtomOwner
            from .adapters.detta import DettaStorage
            root=Path(cfg['root'])
            owner=FeedAtomOwner(root/'feed.sqlite',DettaStorage(cfg['detta_binary'],str(root/'payloads')),self.access['atom.storage'],hook)
            atoms=AtomSession(owner,self.access['atom.storage'])
        self.atoms=atoms;self.hook=hook
    def search(self):
        from .adapters.chroma_vector import ChromaVector
        cfg=self.config
        return ChromaVector(Path(cfg['root'])/'search',self.atoms,self.atoms,self.access['search'],cfg['scope'],cfg['corpus'],cfg['embedding'],self.hook)
    def invoke(self,request):
        validate_request(request,self.chosen)
        require(request['scope']==self.config['scope'],'UNAUTHORIZED')
        name=request['interface_ref']['id'];op=request['operation'];body=request['body']
        if op=='ready':
            c.fields(body,'snapshot');value=self.search().ready(request['scope'],body['snapshot'])
        elif op in ('authorize','authorize-ready'):
            self.access['search'].authorize(request['scope'],'query')
            self.access['atom.storage'].authorize(request['scope'],'getMany')
            # Query disclosure also requires a currently approved synthetic query.
            c.fields(body,'query snapshot');c.snapshot(body['snapshot'],request['scope'])
            require(body['snapshot']['embedding']==self.config['embedding'] and body['snapshot']['corpus']==self.config['corpus'],'UNSUPPORTED_PROFILE')
            require(body['query'] in self.config['queries'],'UNAUTHORIZED');value={'authorized':True}
            if op=='authorize-ready':self.search().ready(request['scope'],body['snapshot'])
        elif name=='search':
            require(body['request_id']==request['request_id'] and body['scope']==request['scope'],'CONFLICT')
            require(digest(c.vector_bytes(body['vector'])) in self.config['query_vectors'],'UNAUTHORIZED')
            value=self.search().query(body)
        else:
            c.fields(body,'refs');require(type(body['refs']) is list and 1<=len(body['refs'])<=8)
            for ref in body['refs']:a.ref(ref,request['scope'])
            value=[dict(ref=item.ref,content_type=item.content_type,data=encode(item.bytes)) for item in self.atoms.getMany(tuple(body['refs']))]
        return dict(request_id=request['request_id'],request_digest=digest(canonical(request)),selection=request['selection'],principal=self.access[name].principal,value=value)


def validate_request(request,chosen):
    c.fields(request,'request_id interface_ref operation scope profile selection body')
    a.identity(request['request_id']);c.fields(request['interface_ref'],'id version')
    name=request['interface_ref']['id'];require(name in chosen,'UNSUPPORTED_OPERATION')
    d=chosen[name];require(request['interface_ref']['version']==d.version,'UNSUPPORTED_VERSION')
    require(request['profile'] in d.profiles and request['selection']==selection_token(d),'UNSUPPORTED_PROFILE')
    require((name=='search' and request['operation'] in ('query','authorize')) or
            (name=='search' and request['operation'] in ('authorize-ready','ready') and 'ready' in d.operations) or
            (name=='atom.storage' and request['operation']=='getMany'),'UNSUPPORTED_OPERATION')
    if request['operation']=='query':c.query(request['body'])
    require(len(canonical(request))<=98304)
