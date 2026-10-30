"""HTTPS placement of the existing generated inspect operation and its owners.

Original immutable bytes, mailbox and inspect /2 contracts; closed transport
routes only. This profile cannot select NAL text or arbitrary execution.
"""
from dataclasses import asdict
import http.client,json,sqlite3,uuid
from pathlib import Path
from .contracts import canonical,decode,digest,encode,require,ContractError,validate
from .registry import descriptors,select,selected_for,selection_token
from .responses import validate_reply,envelope,atom_write,completion_acceptance,error
from .neoclaw_services import PortConnection
from .neoclaw_transport import json_loads
from .policy import Policy
from .ports import AtomEnvelope,Mutation
from .atoms import AtomOwner,AuthorizedAtoms
from .adapters.detta import DettaStorage
from .messaging import MessageOwner,MessagingSession
from .execution import ExecutionOwner,ExecutionSession
from .service import Service,SCHEMA

COMPOSITION='generated-inspect-services/1'
ROLES={'atom.storage':'fusion-storage','execution':'fusion-execution','agent.messaging':'fusion-messaging'}
SCOPE='shared-test'

class Network:
 def __init__(self,config,selected=None):
  require(config['service_composition']==COMPOSITION and config['fallback'] is False,'UNSUPPORTED_PROFILE')
  self.config=config;self.selected=select(descriptors()) if selected is None else selected;self.correlations={}
  require(set(config['ports'])==set(ROLES),'UNSUPPORTED_PROFILE')
  self.routes={k:PortConnection(**v) for k,v in config['ports'].items()}
  self.placement_binding=dict(composition=COMPOSITION,ports={k:{**v['endpoint'],'ca_sha256':digest(Path(v['endpoint']['ca_file']).read_bytes())} for k,v in config['ports'].items()})
 def invoke(self,request):
  name,_=validate(request,check_deadline=False);require(request['scope_ref']==SCOPE,'UNAUTHORIZED');conn=self.routes[name];d=self.selected[name]
  wire=dict(request=request,selection=selection_token(d),composition=COMPOSITION)
  client=http.client.HTTPSConnection(conn.endpoint['host'],conn.endpoint['port'],timeout=7,context=conn.context)
  try:
   client.request('POST','/inspect',canonical(wire),{'Content-Type':'application/json','Authorization':'Bearer '+conn.credential})
   response=client.getresponse();require(response.status==200,'NOT_AVAILABLE');raw=response.read(131073);require(len(raw)<=131072,'NOT_AVAILABLE');value=json_loads(raw)
  except (OSError,ValueError,http.client.HTTPException):raise ContractError('NOT_AVAILABLE') from None
  finally:client.close()
  require(set(value)=={'error'} or (value.get('request_digest')==digest(canonical(wire))),'NOT_AVAILABLE')
  return validate_reply(request,{k:v for k,v in value.items() if k!='request_digest'},d,self.correlations)

class RemoteAtoms:
 def __init__(self,connection):self.connection=connection;self.descriptor=select(descriptors())['atom.storage']
 def call(self,op,args):
  return self.connection.call('/inspect-atoms',dict(composition=COMPOSITION,selection=selection_token(self.descriptor),operation=op,args=args))
 def create(self,command,content_type,data):
  v=self.call('create',[asdict(command),content_type,encode(data)]);atom_write(v,command.scope_ref,self.descriptor);require(v['ref']['digest']==digest(data),'NOT_AVAILABLE');return v
 def get(self,ref):
  v=self.call('get',[ref]);a=AtomEnvelope(v['ref'],v['content_type'],decode(v['bytes']));envelope(a,ref);return a
 def getMany(self,refs):return tuple(self.get(r) for r in refs)
 def availability(self,ref):return self.call('availability',[ref])

class RemoteCompletion:
 def __init__(self,connection):self.connection=connection;self.descriptor=select(descriptors())['agent.messaging']
 def accept(self,scope_ref,route,delivery_id,completion):
  v=self.connection.call('/inspect-completion',dict(composition=COMPOSITION,selection=selection_token(self.descriptor),scope_ref=scope_ref,route=route,delivery_id=delivery_id,completion=completion))
  completion_acceptance(v,scope_ref,route,delivery_id,completion['correlation_id']);return v

class Ports:
 def __init__(self,path,role,hook=lambda _:None):
  self.path,self.role,self.hook=Path(path),role,hook;self.policy=Policy(path);self.cfg=self.policy.current();self.chosen=select(descriptors())
  require(self.cfg['service_composition']==COMPOSITION and self.cfg['sharing']=='generated-shareable','UNSUPPORTED_PROFILE')
 def atoms(self,principal):
  if self.role=='fusion-storage':return AuthorizedAtoms(AtomOwner(self.cfg['atoms_database'],DettaStorage(self.cfg['detta_binary'],self.cfg['da_root'])),self.policy,principal,self.chosen['atom.storage'])
  require(principal in self.cfg['atom_ports'],'UNAUTHORIZED');return RemoteAtoms(PortConnection(**self.cfg['atom_ports'][principal]))
 def service(self):
  db=sqlite3.connect(self.cfg['database'],timeout=2);db.row_factory=sqlite3.Row;db.execute('PRAGMA journal_mode=WAL');db.execute('PRAGMA synchronous=FULL');db.executescript(SCHEMA if self.role=='fusion-execution' else 'CREATE TABLE IF NOT EXISTS mutations(identity TEXT PRIMARY KEY,fingerprint TEXT NOT NULL,response TEXT NOT NULL);')
  mailbox=MessageOwner(self.cfg['messages_database'],self.policy,self.cfg['capacity']) if self.role=='fusion-messaging' else None
  worker=ExecutionOwner(db,self.policy,self.atoms('worker'),RemoteCompletion(PortConnection(**self.cfg['completion_port'])),self.cfg['capacity']) if self.role=='fusion-execution' else None
  def messaging(principal,mid):require(mailbox is not None,'UNSUPPORTED_OPERATION');return MessagingSession(mailbox,self.policy,principal,self.atoms(principal),mid)
  def execution(principal,mid):require(worker is not None,'UNSUPPORTED_OPERATION');return ExecutionSession(worker,principal,mid)
  return Service(db,self.policy,self.atoms,messaging,execution,worker,descriptors(),self.hook)
 def invoke(self,path,credential,q):
  principal=self.policy.authenticate(credential);require(q.get('composition')==COMPOSITION,'UNSUPPORTED_PROFILE')
  if path=='/inspect':
   require(set(q)=={'composition','request','selection'},'INVALID_ARGUMENT');r=q['request'];name,_=validate(r,check_deadline=False)
   require(ROLES[name]==self.role and r['scope_ref']==SCOPE,'UNAUTHORIZED');require(q['selection']==selection_token(self.chosen[name]),'UNSUPPORTED_PROFILE')
   s=self.service()
   actor=self.cfg.get('actors',{}).get(principal,principal)
   if actor!=principal:
    require(principal=='commit-observer' and r['operation'] in ('get','getMany','availability','status','result'),'UNAUTHORIZED')
    self.policy.check(principal,SCOPE,name+'.'+r['operation'])
    underlying=self.policy
    class DelegatedPolicy:
     def authenticate(_,token):require(underlying.authenticate(token)==principal,'UNAUTHORIZED');return actor
     def check(_,who,scope,method):
      underlying.check(who,scope,method)
      if who==actor:underlying.check(principal,scope,method)
     def route(_,scope,route,owner=None):return underlying.route(scope,route,owner)
    s.policy=DelegatedPolicy()
   try:result=s.invoke(credential,r)
   finally:s.close()
   self.policy.check(principal,r['scope_ref'],name+'.'+r['operation'])
   return dict(ok=result,provider=q['selection'],request_digest=digest(canonical(q)))
  if path=='/inspect-atoms':
   require(self.role=='fusion-storage' and principal in ('worker','mailbox-A','commit-observer'),'UNAUTHORIZED')
   require(set(q)=={'composition','selection','operation','args'},'INVALID_ARGUMENT');require(q['selection']==selection_token(self.chosen['atom.storage']),'UNSUPPORTED_PROFILE')
   op=q['operation'];a=q['args'];require(op in ('create','get','availability') and type(a) is list and len(a)==(3 if op=='create' else 1),'UNSUPPORTED_OPERATION')
   actor=self.cfg['actors'][principal];self.policy.check(principal,SCOPE,'atom.storage.'+op);self.policy.check(actor,SCOPE,'atom.storage.'+op)
   owner=self.atoms(actor)
   if op=='create':
    command=Mutation(**a[0]);require(command.scope_ref==SCOPE,'UNAUTHORIZED');result=owner.create(command,a[1],decode(a[2]))
   else:
    require(a[0]['scope_ref']==SCOPE,'UNAUTHORIZED');result=getattr(owner,op)(a[0])
    if op=='get':result=Service._envelope(result)
  elif path=='/inspect-completion':
   require(self.role=='fusion-messaging' and principal=='worker','UNAUTHORIZED')
   require(set(q)=={'composition','selection','scope_ref','route','delivery_id','completion'},'INVALID_ARGUMENT');require(q['selection']==selection_token(self.chosen['agent.messaging']) and q['scope_ref']==SCOPE,'UNSUPPORTED_PROFILE')
   self.policy.check(principal,SCOPE,'agent.messaging.accept')
   result=MessageOwner(self.cfg['messages_database'],self.policy,self.cfg['capacity']).accept(SCOPE,q['route'],q['delivery_id'],q['completion'])
  else:raise ContractError('UNSUPPORTED_OPERATION')
  require(self.policy.authenticate(credential)==principal,'UNAUTHORIZED')
  return dict(ok=result,selection=q['selection'],request_digest=digest(canonical(q)))
