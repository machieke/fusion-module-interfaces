"""Separated S06 channel ports over existing AtomOwner and MessageOwner.

A storage-read credential is bound by configuration to exactly one initiating
actor. Messaging never reads a foreign database or constructs a storage backend.
"""
import json
from pathlib import Path
import sqlite3
from . import channel_contracts as c
from .contracts import canonical,digest,require,decode,PROFILES
from .neoclaw_services import service_hostname
from .policy import Policy
from .registry import descriptors,selection_token
from .service import Service,SCHEMA
from .atoms import AtomOwner,AuthorizedAtoms
from .messaging import MessageOwner,MessagingSession
from .ports import AtomEnvelope,AtomStorage
from .channel_transport import ChannelNetwork
from .responses import envelope

COMPOSITION='neoclaw-channel-services/1'


def placement(cfg):
    require(cfg.get('service_composition')==COMPOSITION and 'endpoint' not in cfg and 'provider_config' not in cfg,'UNSUPPORTED_PROFILE')
    c.fields(cfg['endpoints'],'atom.storage agent.messaging');c.fields(cfg['service_credentials'],'atom.storage agent.messaging')
    for ep in cfg['endpoints'].values():
        c.fields(ep,'host port ca_file');service_hostname(ep['host']);require(type(ep['port']) is int and 1024<=ep['port']<=65535)
    return dict(service_composition=COMPOSITION,endpoints={k:{**v,'ca_sha256':digest(Path(v['ca_file']).read_bytes())} for k,v in cfg['endpoints'].items()})


class ReadDelegation:
    def __init__(self,policy,credential):self.policy,self.credential=policy,credential
    def current(self):return self.policy.current()
    def authenticate(self,credential):
        require(credential==self.credential,'UNAUTHORIZED');source=self.policy.authenticate(credential)
        cfg=self.current();actor=cfg['payload_delegations'].get(source);require(actor in cfg['channel_store']['roles'],'UNAUTHORIZED')
        self.policy.check(source,cfg['channel_store']['scope'],'channel.payload.read');return actor
    def check(self,principal,scope,operation):
        require(principal==self.authenticate(self.credential),'UNAUTHORIZED');self.policy.check(principal,scope,operation)
    def route(self,*args):return self.policy.route(*args)


class RemotePayload:
    def __init__(self,cfg,principal,chosen):
        self.cfg,self.principal,self.chosen=cfg,principal,chosen
        require(principal in cfg['source_credentials'],'UNAUTHORIZED')
        self.port=ChannelNetwork(cfg['source_endpoint'],cfg['source_credentials'][principal],chosen,service_dns=True)
    def get(self,ref):
        request=dict(channel_profile=c.PROFILE,selections=c.selection(self.chosen),principal=self.principal,
            invocation=dict(message_id='get/'+ref['id'],interface_ref=dict(id='atom.storage',version=self.chosen['atom.storage'].version),
                operation='get',scope_ref=self.cfg['channel_store']['scope'],profile=PROFILES['atom.storage'],body=dict(ref=ref)))
        value=self.port.invoke(request);item=AtomEnvelope(value['ref'],value['content_type'],decode(value['bytes']));envelope(item,ref);return item


def owner(path,hook,credential):
    cfg=json.loads(Path(path).read_text());require(cfg.get('service_composition')==COMPOSITION,'UNSUPPORTED_PROFILE')
    role=cfg['channel_role'];policy=Policy(path);principal=policy.authenticate(credential)
    delegated=principal in cfg.get('payload_delegations',{})
    if delegated:policy=ReadDelegation(policy,credential)
    selected=c.selected(descriptors(atom_provider='detta'))
    seal=canonical({k:cfg.get(k) for k in ('service_composition','channel_role','channel_store','atoms_database','messages_database','da_root')}).decode()
    db=sqlite3.connect(cfg['database'],timeout=.2);db.row_factory=sqlite3.Row
    try:
        db.execute('PRAGMA journal_mode=WAL');db.execute('PRAGMA synchronous=FULL')
        tables={x[0] for x in db.execute("SELECT name FROM sqlite_master WHERE type='table'")};require(not tables or 'channel_seal' in tables,'UNSUPPORTED_PROFILE')
        with db:
            if not tables:db.execute('CREATE TABLE channel_seal(binding TEXT NOT NULL)');db.execute('INSERT INTO channel_seal VALUES(?)',(seal,))
            else:require(db.execute('SELECT binding FROM channel_seal').fetchone()[0]==seal,'CONFLICT')
        db.executescript(SCHEMA)
        def forbidden(*_):require(False,'UNSUPPORTED_OPERATION')
        if role=='storage':
            require('messages_database' not in cfg,'UNSUPPORTED_PROFILE')
            from .adapters.detta import DettaStorage
            provider=AtomOwner(cfg['atoms_database'],DettaStorage(cfg['detta_binary'],cfg['da_root']))
            require(isinstance(provider,AtomStorage),'UNSUPPORTED_PROFILE') # Keep owner contract check.
            atoms=lambda p:AuthorizedAtoms(provider,policy,p,selected['atom.storage']);messages=forbidden
        else:
            require(role=='messaging' and not any(k in cfg for k in ('atoms_database','da_root','detta_binary')),'UNSUPPORTED_PROFILE')
            atoms=lambda p:RemotePayload(cfg,p,selected)
            mailbox=MessageOwner(cfg['messages_database'],policy,cfg['capacity'])
            messages=lambda p,ident:MessagingSession(mailbox,policy,p,atoms(p),ident)
        result=Service(db,policy,atoms,messages,forbidden,None,descriptors(atom_provider='detta'),hook)
        return result,policy,delegated
    except BaseException:db.close();raise


class ChannelPorts:
    def __init__(self,path,hook=lambda _:None):self.path,self.hook=path,hook
    def invoke(self,path,credential,request):
        require(path=='/s06-mailbox','UNSUPPORTED_OPERATION')
        chosen=c.selected(descriptors(atom_provider='detta'));name,op=c.wire(request,chosen)
        cfg=Policy(self.path).current();p=Policy(self.path).authenticate(credential)
        if p in cfg.get('payload_delegations',{}):
            require(name=='atom.storage' and op=='get','UNAUTHORIZED')
            require(request['principal']==cfg['payload_delegations'][p],'UNAUTHORIZED')
        from .channel_service import ChannelService
        service,policy,_=owner(self.path,self.hook,credential)
        try:return ChannelService(self.path,self.hook,owner=service,policy=policy).invoke(credential,request)
        finally:service.close()
