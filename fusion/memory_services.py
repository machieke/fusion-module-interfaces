"""Explicit S03.2 service composition; synchronous ports, no new memory owner.

The Search service receives a read-only indexer credential. Receipt observation
is delegated for exactly the operator-bound application/session/scope, checked
against BOTH current identities. Wire principal strings never grant authority.
"""
import http.client
from pathlib import Path
import uuid

from . import append_contracts as w, vector_contracts as v, lookup_contracts as a
from .contracts import ContractError, canonical, decode, digest, encode, require
from .neoclaw_services import service_hostname
from .neoclaw_transport import Network, json_loads
from .registry import descriptor_read, selection_token
from .policy import Policy
from .ports import AtomEnvelope, Mutation
from .responses import envelope
from .vector_transport import checked
from .vector_composition import ReadService, select as read_select
from .append_composition import AppendService

COMPOSITION='neoclaw-memory-services/1'
SOURCE_PROFILE='neoclaw-memory-source-ports/1'
MAX_BYTES=98304


def freeze_placement(cfg,names):
    require(cfg.get('service_composition')==COMPOSITION and cfg.get('fallback') is False,'UNSUPPORTED_PROFILE')
    require('provider_config' not in cfg and 'endpoint' not in cfg,'UNSUPPORTED_PROFILE')
    v.fields(cfg['endpoints'],' '.join(names));v.fields(cfg['service_credentials'],' '.join(names))
    endpoints={}
    for name,ep in cfg['endpoints'].items():
        v.fields(ep,'host port ca_file');service_hostname(ep['host'])
        a.integer(ep['port'],1024,65535)
        endpoints[name]={**ep,'ca_sha256':digest(Path(ep['ca_file']).read_bytes())}
    return dict(service_composition=COMPOSITION,endpoints=endpoints)


class RoutedMemory:
    def __init__(self,cfg,chosen,transport):
        freeze_placement(cfg,('atom.storage','search'))
        self.routes={name:transport(ep,cfg['service_credentials'][name],chosen,cfg['principal'],service_dns=True)
                     for name,ep in cfg['endpoints'].items()}
    def invoke(self,request):
        name=request['interface_ref']['id'];require(name in self.routes,'UNSUPPORTED_OPERATION')
        return self.routes[name].invoke(request)


def encoder_binding(cfg,chosen):
    from .embedding_transport import EmbeddingNetwork
    freeze_placement(cfg,('embedding',))
    return EmbeddingNetwork(cfg['endpoints']['embedding'],cfg['service_credentials']['embedding'],chosen,service_dns=True)


class SourceConnection(Network):
    def __init__(self,endpoint,credential,principal='indexer'):
        self.principal=principal
        super().__init__(endpoint,credential,None,timeout=1.,service_dns=True)
    def invoke(self,request):
        require(len(canonical(request))<=MAX_BYTES)
        conn=http.client.HTTPSConnection(self.endpoint['host'],self.endpoint['port'],timeout=self.timeout,context=self.context)
        try:
            conn.request('POST','/memory-source',canonical(request),
                         {'Authorization':'Bearer '+self.credential,'Content-Type':'application/json'})
            response=conn.getresponse();require(response.status==200,'NOT_AVAILABLE')
            raw=response.read(MAX_BYTES+1);require(len(raw)<=MAX_BYTES,'NOT_AVAILABLE')
            return checked(request,json_loads(raw),self.principal)
        except (OSError,ValueError,http.client.HTTPException):raise ContractError('NOT_AVAILABLE') from None
        finally:conn.close()


class RemoteSource:
    """Only read ports. Has no create method, DeTTa import or filesystem access."""
    def __init__(self,connection,scope,read_descriptor,append_descriptor,accepted=None):
        self.connection,self.scope=connection,scope
        self.read_descriptor,self.append_descriptor=read_descriptor,append_descriptor
        self.accepted=accepted
    def call(self,op,body,descriptor=None):
        d=descriptor or self.read_descriptor
        request=dict(request_id=str(uuid.uuid4()),profile=SOURCE_PROFILE,scope=self.scope,
                     selection=selection_token(d),operation=op,body=body)
        return self.connection.invoke(request)
    def get(self,ref):
        a.ref(ref,self.scope);value=self.call('get',dict(ref=ref));v.fields(value,'ref content_type data')
        item=AtomEnvelope(value['ref'],value['content_type'],decode(value['data']));envelope(item,ref)
        require(len(item.bytes)<=a.MAX_BYTES,'NOT_AVAILABLE');return item
    def getMany(self,refs):
        # Chroma projection uses get; no parallel fetch or hidden retry.
        require(type(refs) is tuple and 1<=len(refs)<=8)
        return tuple(self.get(r) for r in refs)
    def head(self,scope):
        require(scope==self.scope,'UNAUTHORIZED');return a.head(self.call('head',{}),scope)
    def readCommits(self,scope,after,through,limit):
        require(scope==self.scope,'UNAUTHORIZED');a.head(through,scope);a.integer(after,0,through['sequence']);a.integer(limit,1,a.PAGE)
        return a.commits(self.call('readCommits',dict(after=after,through=through,limit=limit)),scope,after,through,limit)
    def observe(self,command):
        accepted=w.intent(self.accepted);require(command.scope_ref==self.scope,'UNAUTHORIZED')
        roles=[role for role in w.ROLES if w.key(accepted,role)==command.idempotency_key]
        require(len(roles)==1 and command.intent_digest is None,'UNAUTHORIZED')
        return w.observation(self.call('observe',dict(intent=accepted,role=roles[0]),self.append_descriptor),self.scope,self.append_descriptor)


class ReceiptAuthority:
    """Read-only receipt delegation, configured by storage, never by a request.

Feed identities belong to the initiating principal. This facade permits only
observing them after validating current indexer AND initiator permissions.
"""
    def __init__(self,policy,credential):self.policy,self.credential=policy,credential
    def current(self):return self.policy.current()
    def authenticate(self,credential):
        require(credential==self.credential and self.policy.authenticate(credential)=='indexer','UNAUTHORIZED')
        cfg=self.current();delegation=cfg['source_delegation'];append=cfg['memory_append']
        require(delegation==dict(principal=append['session_principal'],session=append['session'],scope=append['scope']),'UNAUTHORIZED')
        self.policy.check('indexer',append['scope'],'memory.source.observe')
        return delegation['principal']
    def check(self,principal,scope,operation):
        require(principal==self.authenticate(self.credential),'UNAUTHORIZED')
        require(operation in ('memory.append.disclose','atom.storage.observe'),'UNAUTHORIZED')
        self.policy.check(principal,scope,operation)
        self.policy.check('indexer',scope,'memory.source.observe')


class StoragePorts:
    def __init__(self,path,hook=lambda _:None):self.path,self.hook=path,hook
    def invoke(self,path,credential,request):
        if path=='/s03-append':
            service=AppendService(self.path,credential,self.hook)
            w.request(request,service.chosen)
            require(request['interface_ref']['id']=='atom.storage','UNSUPPORTED_OPERATION')
            return service.invoke(request)
        if path=='/s03-read':
            require(request.get('interface_ref',{}).get('id')=='atom.storage','UNSUPPORTED_OPERATION')
            return ReadService(self.path,credential,self.hook).invoke(request)
        require(path=='/memory-source','UNSUPPORTED_OPERATION')
        v.fields(request,'request_id profile scope selection operation body');a.identity(request['request_id'])
        require(request['profile']==SOURCE_PROFILE,'UNSUPPORTED_PROFILE');require(len(canonical(request))<=MAX_BYTES)
        policy=Policy(self.path);principal=policy.authenticate(credential)
        cfg=policy.current();require(principal=='indexer' or principal in cfg.get('read_source_principals',[]),'UNAUTHORIZED')
        scope=cfg['memory_read']['scope'];require(request['scope']==scope,'UNAUTHORIZED')
        op=request['operation'];body=request['body']
        if op=='observe':
            require(principal=='indexer','UNAUTHORIZED')
            v.fields(body,'intent role');accepted=w.intent(body['intent']);require(body['role'] in w.ROLES)
            service=AppendService(self.path,credential,self.hook,policy=ReceiptAuthority(policy,credential))
            require(request['selection']==selection_token(service.chosen['atom.storage']),'UNSUPPORTED_PROFILE')
            service.authorize(accepted,'disclose')
            if body['role']!='binding':service.bound(accepted)
            value=service.observe(accepted,body['role'])
            if body['role']=='binding' and value['found']:
                require(value['write']['ref']['digest']==digest(w.binding_bytes(accepted)),'CONFLICT')
            service.authorize(accepted,'disclose')
        else:
            service=ReadService(self.path,credential,self.hook)
            require(request['selection']==selection_token(service.chosen['atom.storage']),'UNSUPPORTED_PROFILE')
            if op=='get':
                v.fields(body,'ref');a.ref(body['ref'],scope);item=service.atoms.get(body['ref'])
                value=dict(ref=item.ref,content_type=item.content_type,data=encode(item.bytes))
            elif op=='head':v.fields(body,'');value=service.atoms.head(scope)
            else:
                require(op=='readCommits','UNSUPPORTED_OPERATION');v.fields(body,'after through limit')
                value=service.atoms.readCommits(scope,body['after'],body['through'],body['limit'])
        return dict(request_id=request['request_id'],request_digest=digest(canonical(request)),selection=request['selection'],principal=principal,value=value)


class SearchPorts:
    def __init__(self,path,hook=lambda _:None):
        self.path,self.hook=path,hook;cfg=Policy(path).current()
        # Separation is fail-closed even when a caller supplies a legacy config.
        require('detta_binary' not in cfg and all('detta_binary' not in cfg[k] for k in ('memory_read','memory_append')),'UNSUPPORTED_PROFILE')
        self.source=cfg['source'];self.read=read_select([descriptor_read(x) for x in cfg['memory_read']['catalogue']],v.EMBEDDING,True)
        self.append=w.select([descriptor_read(x) for x in cfg['memory_append']['catalogue']]);self.scope=cfg['memory_read']['scope']
    def atoms(self,accepted=None):
        return RemoteSource(SourceConnection(**self.source),self.scope,self.read['atom.storage'],self.append['atom.storage'],accepted)
    def invoke(self,path,credential,request):
        require(path in ('/s03-append','/s03-read'),'UNSUPPORTED_OPERATION')
        require(request.get('interface_ref',{}).get('id')=='search','UNSUPPORTED_OPERATION')
        if path=='/s03-append':
            service=AppendService(self.path,credential,self.hook,atoms=self.atoms(request.get('intent')))
        else:service=ReadService(self.path,credential,self.hook,atoms=self.atoms())
        return service.invoke(request)
