"""Synthetic preview placement of the existing inspect_atom /2 owner contracts.

This transport creates no interpreter, evaluator, payload store or task worker.
Execution retains its own jobs/outbox; Messaging retains its existing mailbox.
All immutable payloads cross the selected AtomStorage HTTPS port.
"""
import json,sqlite3,uuid
from pathlib import Path
from .contracts import canonical,digest,require,validate,ContractError,label
from .registry import descriptors,select,selection_token
from .policy import Policy
from .service import Service,SCHEMA
from .execution import ExecutionOwner,ExecutionSession
from .messaging import MessageOwner,MessagingSession
from .preview_atoms import client as atoms_client
from .preview_transport import invoke
from .responses import validate_reply,completion_acceptance

PROFILE='synthetic-inspect-placement/1'
ROUTE='/preview/inspection'
COMPLETION='/preview/inspection-completion'
ROLES={'execution':'fusion-execution','agent.messaging':'fusion-messaging'}


class Completion:
    def __init__(self,cfg):self.cfg=cfg
    def accept(self,scope,route,identity,body):
        require(scope==self.cfg['scope'],'UNAUTHORIZED')
        q=dict(profile=PROFILE,id=str(uuid.uuid4()),scope=scope,route=route,delivery_id=identity,completion=body)
        v=invoke(self.cfg['completion_port'],COMPLETION,q)
        require(type(v) is dict and set(v)=={'id','request_digest','value'} and v['id']==q['id'] and v['request_digest']==digest(canonical(q)),'NOT_AVAILABLE')
        completion_acceptance(v['value'],scope,route,identity,body['correlation_id']);return v['value']


class Ports:
    def __init__(self,path,role,hook=lambda _:None):
        self.path,self.role,self.hook=Path(path),role,hook;self.policy=Policy(path)
        self.cfg=self.policy.current();require(self.cfg['profile']==PROFILE and self.cfg['scope'].startswith('synthetic-'),'UNSUPPORTED_PROFILE')
        require(role in ROLES.values(),'UNSUPPORTED_OPERATION');self.chosen=select(descriptors())
    def atoms(self,principal):
        require(principal in self.cfg['atom_clients'],'UNAUTHORIZED')
        return atoms_client(self.cfg['atom_clients'][principal])
    def service(self):
        db=sqlite3.connect(self.cfg['database'],timeout=2);db.row_factory=sqlite3.Row
        db.execute('PRAGMA journal_mode=WAL');db.execute('PRAGMA synchronous=FULL')
        db.executescript(SCHEMA if self.role=='fusion-execution' else 'CREATE TABLE IF NOT EXISTS mutations(identity TEXT PRIMARY KEY,fingerprint TEXT NOT NULL,response TEXT NOT NULL);')
        messages=MessageOwner(self.cfg['messages_database'],self.policy,self.cfg['capacity']) if self.role=='fusion-messaging' else None
        worker=ExecutionOwner(db,self.policy,self.atoms('worker'),Completion(self.cfg),self.cfg['capacity']) if self.role=='fusion-execution' else None
        def mailbox(principal,mid):
            require(messages is not None,'UNSUPPORTED_OPERATION');return MessagingSession(messages,self.policy,principal,None,mid)
        def execution(principal,mid):
            require(worker is not None,'UNSUPPORTED_OPERATION')
            return ExecutionSession(worker,self.cfg.get('actors',{}).get(principal,principal),mid)
        return Service(db,self.policy,self.atoms,mailbox,execution,worker,descriptors(),self.hook)
    def invoke(self,path,credential,q):
        require(type(q) is dict and q.get('profile')==PROFILE,'UNSUPPORTED_PROFILE')
        principal=self.policy.authenticate(credential)
        if path==COMPLETION:
            require(self.role=='fusion-messaging' and principal=='worker','UNAUTHORIZED')
            require(set(q)=={'profile','id','scope','route','delivery_id','completion'})
            require(q['scope']==self.cfg['scope'],'UNAUTHORIZED')
            require(all(label(q[k]) for k in ('id','route','delivery_id')))
            self.policy.check(principal,q['scope'],'agent.messaging.accept')
            # Validate before MessageOwner can commit a malformed mailbox item.
            descriptor=self.chosen['agent.messaging'];body=q['completion']
            poll=dict(interface_ref={'id':'agent.messaging','version':'1.0.0'},profile='durable-mailbox/2',
                operation='poll',scope_ref=q['scope'],body={'route':q['route']})
            validate_reply(poll,dict(provider=selection_token(descriptor),ok={'delivery':dict(delivery_id=q['delivery_id'],
                body=body,order=1,delivery='observed-unacknowledged',scope_ref=q['scope'],route=q['route'])}),descriptor)
            require(type(body) is dict and 'job_id' in body,'INVALID_ARGUMENT')
            value=MessageOwner(self.cfg['messages_database'],self.policy,self.cfg['capacity']).accept(q['scope'],q['route'],q['delivery_id'],q['completion'])
            require(self.policy.authenticate(credential)==principal,'UNAUTHORIZED')
            self.policy.check(principal,q['scope'],'agent.messaging.accept')
            return dict(id=q['id'],request_digest=digest(canonical(q)),value=value)
        require(path==ROUTE and set(q)=={'profile','selection','request'},'UNSUPPORTED_OPERATION')
        request=q['request'];name,op=validate(request,check_deadline=False)
        require(name in ROLES and ROLES[name]==self.role and request['scope_ref']==self.cfg['scope'],'UNAUTHORIZED')
        require(q['selection']==selection_token(self.chosen[name]),'UNSUPPORTED_PROFILE')
        if principal in self.cfg.get('actors',{}):require(name=='execution' and op in ('status','result'),'UNAUTHORIZED')
        # This mailbox transports only inspect completions. Agent task payloads
        # use their existing separately typed route, never this generic send.
        require(name!='agent.messaging' or op in ('poll','ack'),'UNSUPPORTED_OPERATION')
        service=self.service()
        try:value=service.invoke(credential,request)
        finally:service.close()
        require(self.policy.authenticate(credential)==principal,'UNAUTHORIZED')
        self.policy.check(principal,request['scope_ref'],name+'.'+op)
        return dict(ok=value,provider=q['selection'],request_digest=digest(canonical(q)))


class Client:
    def __init__(self,path):
        self.path=Path(path);self.cfg,self.frozen=self.current();self.selected=select(descriptors());self.correlations={}
    def current(self):
        cfg=json.loads(self.path.read_text())
        require(cfg['profile']==PROFILE and cfg['fallback'] is False and cfg['scope'].startswith('synthetic-'),'UNSUPPORTED_PROFILE')
        require(set(cfg['ports'])==set(ROLES),'UNSUPPORTED_PROFILE')
        frozen={k:v for k,v in cfg.items() if k!='ports'}
        frozen['ports']={k:dict(endpoint=v['endpoint'],ca_sha256=digest(Path(v['endpoint']['ca_file']).read_bytes())) for k,v in cfg['ports'].items()}
        return cfg,frozen
    def invoke(self,request):
        cfg,frozen=self.current();require(frozen==self.frozen,'CONFLICT')
        name,op=validate(request,check_deadline=False)
        require(name in ROLES and request['scope_ref']==cfg['scope'],'UNAUTHORIZED')
        chosen=self.selected[name];q=dict(profile=PROFILE,selection=selection_token(chosen),request=request)
        reply=invoke(cfg['ports'][name],ROUTE,q)
        require(type(reply) is dict and reply.get('request_digest')==digest(canonical(q)),'NOT_AVAILABLE')
        return validate_reply(request,{k:v for k,v in reply.items() if k!='request_digest'},chosen,self.correlations)
