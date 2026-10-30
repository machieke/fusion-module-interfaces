"""Explicit synthetic single-node ports for existing cognitive/structural owners.

No private-local profile is relaxed. Transport is restricted to named methods;
C2 alone holds the trusted C1 completion credential. No numerical implementation
or general execution surface lives here.
"""
from dataclasses import asdict,replace,is_dataclass
import http.client,json,uuid
from pathlib import Path
from types import SimpleNamespace
from .contracts import ContractError,canonical,digest,encode,decode,require
from .policy import Policy
from .registry import Descriptor,descriptor_read,descriptor_wire,selection_token
from .ports import Mutation,AtomEnvelope
from .responses import envelope,atom_write,error
from .neoclaw_transport import Network,json_loads
from . import nal_memory_contracts as n,promotion_contracts as p,lookup_contracts as l,delivery_contracts as d

COMPOSITION='synthetic-cognitive-services/1'
APPLICATION='controlled-native-loop/12'
PRIVACY='generated-shareable'
ROUTE='/reference-cognition'
MAX_BYTES=131072
OPERATIONS={
 'atom.storage':('create','get','getMany','availability','head','readCommits'),
 'episodic.memory':('recordEpisode','appendEvent','readEpisode','readEvidence','pendingEvidence','acknowledgeDelivery','occurrenceIdentity','readOccurrence'),
 'belief.revision':('registerPrior','submitEvidence','readBelief','observeDecision','drainEvidence','readDecisions'),
 'attention':p.OPERATIONS,
 'relations':('assertRelation','getRelation','outgoing','incoming'),
 'search':('query','catchUp','beginRebuild')}
PROFILES={'atom.storage':l.FEED,'episodic.memory':n.EPISODE_PROFILE,'belief.revision':n.BELIEF_PROFILE,'attention':p.PROFILE,'relations':l.RELATIONS,'search':l.SEARCH}
ROLES={'atom.storage':'fusion-storage','episodic.memory':'fusion-episodes','belief.revision':'fusion-beliefs','attention':'fusion-attention','relations':'fusion-relations','search':'fusion-exact-search'}

def descriptors(attention='sqlite'):
 require(attention in ('sqlite','file-fixture'),'UNSUPPORTED_PROFILE')
 return [Descriptor('synthetic-'+name+('-'+attention if name=='attention' else ''),name,'1.0.0','1.0.0',frozenset({PROFILES[name],COMPOSITION}),frozenset(ops),frozenset({'process-restart','scoped','idempotent','service-network'}),MAX_BYTES,privacy=PRIVACY,receipt_providers=frozenset({'detta-local-rs/1'}),features=frozenset({n.MODEL,n.RUNTIME}) if name=='belief.revision' else frozenset()) for name,ops in OPERATIONS.items()]

def catalogue(cfg):
 actual=[descriptor_read(x) for x in cfg['catalogue']];expected=descriptors(cfg.get('attention_provider','sqlite'))
 require({selection_token(x) for x in actual}=={selection_token(x) for x in expected},'UNSUPPORTED_PROFILE')
 return {x.interface:x for x in actual}

class Access:
 def __init__(self,path,credential,name):
  self.policy=Policy(path);self.credential=credential;self.name=name
  cfg=self.policy.current();self.descriptor=catalogue(cfg)[name]
  self.identity=self.policy.authenticate(credential);self.principal=cfg['actors'][self.identity]
 def selection(self):return selection_token(self.descriptor)
 def authorize(self,scope,operation):
  cfg=self.policy.current();require(cfg['composition']==COMPOSITION and cfg['privacy']==PRIVACY and cfg['scope']==scope,'UNSUPPORTED_PROFILE')
  require(self.policy.authenticate(self.credential)==self.identity and cfg['actors'][self.identity]==self.principal,'UNAUTHORIZED')
  require(operation in OPERATIONS[self.name] or (self.name=='belief.revision' and operation=='assume'),'UNSUPPORTED_OPERATION')
  require(selection_token(catalogue(cfg)[self.name])==self.selection(),'UNSUPPORTED_PROFILE')
  self.policy.check(self.identity,scope,self.name+'.'+operation)
  self.policy.check(self.principal,scope,self.name+'.'+operation)
  if operation=='acknowledgeDelivery':require(self.identity=='completion-relay','UNAUTHORIZED')
  return self.principal
 def origin(self,scope,source):self.authorize(scope,'appendEvent');return self.policy.current()['origins'].get(source)
 def assumption(self,scope,value):
  self.authorize(scope,'assume');n.independence(value);require(value['model_id'] in self.policy.current()['assumptions'],'UNAUTHORIZED')
 def completionConsumer(self,scope):
  self.authorize(scope,'acknowledgeDelivery');return consumer(self.policy.current())

def consumer(cfg):
 return dict(principal='A',provider=catalogue(cfg)['belief.revision'].provider,profile=n.BELIEF_PROFILE,selection=selection_token(catalogue(cfg)['belief.revision']))

class Connection(Network):
 def __init__(self,endpoint,credential):
  super().__init__(endpoint,credential,None,service_dns=True)
  self.timeout=25 # S01's one-second clamp is unsuitable for bounded synchronous native revision.
 def call(self,request):
  require(len(canonical(request))<=MAX_BYTES,'INVALID_ARGUMENT')
  conn=http.client.HTTPSConnection(self.endpoint['host'],self.endpoint['port'],timeout=self.timeout,context=self.context)
  try:
   conn.request('POST',ROUTE,canonical(request),{'Authorization':'Bearer '+self.credential,'Content-Type':'application/json'})
   response=conn.getresponse();require(response.status==200,'NOT_AVAILABLE');raw=response.read(MAX_BYTES+1);require(len(raw)<=MAX_BYTES,'NOT_AVAILABLE');value=json_loads(raw)
  except (OSError,ValueError,http.client.HTTPException):raise ContractError('NOT_AVAILABLE') from None
  finally:conn.close()
  if set(value)=={'error'}:error(value['error']);raise ContractError(value['error']['code'])
  require(set(value)=={'id','request_digest','selection','principal','value'} and value['id']==request['id'] and value['request_digest']==digest(canonical(request)) and value['selection']==request['selection'] and value['principal']=='A','NOT_AVAILABLE')
  return value['value']

class Remote:
 def __init__(self,cfg,name):self.cfg,self.name=cfg,name;self.descriptor=catalogue(cfg)[name];self.connection=Connection(**cfg['ports'][name])
 def call(self,op,*args):
  require(op in OPERATIONS[self.name] or op=='authorize','UNSUPPORTED_OPERATION')
  wire=[]
  for x in args:
   if isinstance(x,Mutation):x=asdict(x)
   elif isinstance(x,n.Admission):x=n.submission(x)
   elif is_dataclass(x):x=asdict(x)
   elif isinstance(x,bytes):x={'bytes':encode(x)}
   wire.append(x)
  return self.connection.call(dict(id=str(uuid.uuid4()),composition=COMPOSITION,scope=self.cfg['scope'],interface=self.name,selection=selection_token(self.descriptor),operation=op,args=wire))
 def authorize(self,scope,operation=None):
  require(scope==self.cfg['scope'],'UNAUTHORIZED');return self.call('authorize',operation or 'authorize')
 def selection(self):return selection_token(self.descriptor)
 def create(self,c,t,b):
  value=self.call('create',c,t,b);atom_write(value,c.scope_ref,self.descriptor);require(value['ref']['digest']==digest(b),'NOT_AVAILABLE');return value
 def get(self,ref):
  value=self.call('get',ref);item=AtomEnvelope(value['ref'],value['content_type'],decode(value['data']));envelope(item,ref);return item
 def getMany(self,refs):
  values=self.call('getMany',refs);require(type(values) is list and len(values)==len(refs),'NOT_AVAILABLE');items=[]
  for value,ref in zip(values,refs):
   item=AtomEnvelope(value['ref'],value['content_type'],decode(value['data']));envelope(item,ref);items.append(item)
  return tuple(items)
 def availability(self,ref):return self.call('availability',ref)
 def head(self,scope):return self.call('head',scope)
 def readCommits(self,*args):return self.call('readCommits',*args)
 def recordEpisode(self,*args):return self.call('recordEpisode',*args)
 def appendEvent(self,*args):return self.call('appendEvent',*args)
 def readEpisode(self,*args):return self.call('readEpisode',*args)
 def readEvidence(self,*args):return self.call('readEvidence',*args)
 def pendingEvidence(self,*args):return tuple(self.call('pendingEvidence',*args))
 def acknowledgeDelivery(self,*args):return self.call('acknowledgeDelivery',*args)
 def occurrenceIdentity(self,*args):return self.call('occurrenceIdentity',*args)
 def readOccurrence(self,*args):return self.call('readOccurrence',*args)
 def registerPrior(self,*args):return self.call('registerPrior',*args)
 def submitEvidence(self,*args):return self.call('submitEvidence',*args)
 def readBelief(self,*args):return self.call('readBelief',*args)
 def observeDecision(self,*args):return self.call('observeDecision',*args)
 def drain(self,episode,declarations=None):return tuple(self.call('drainEvidence',episode,declarations))
 def decisions(self,episode):return tuple(self.call('readDecisions',episode))
 def bind(self,*args):return self.call('bind',*args)
 def observe(self,*args):return self.call('observe',*args)
 def adjust(self,*args):return self.call('adjust',*args)
 def scores(self,*args):return self.call('scores',*args)
 def rank(self,*args):return self.call('rank',*args)
 def assertRelation(self,*args):return self.call('assertRelation',*args)
 def getRelation(self,*args):return self.call('getRelation',*args)
 def outgoing(self,*args):return self.call('outgoing',*args)
 def incoming(self,*args):return self.call('incoming',*args)
 def query(self,*args):return self.call('query',*args)
 def catchUp(self,*args):return self.call('catchUp',*args)
 def beginRebuild(self,*args):return self.call('beginRebuild',*args)

# Exact signatures; no imported function names, expressions, file paths or SQL.
ARITY={'create':3,'get':1,'getMany':1,'availability':1,'head':1,'readCommits':4,'recordEpisode':2,'appendEvent':4,'readEpisode':3,'readEvidence':1,'pendingEvidence':2,'acknowledgeDelivery':2,'occurrenceIdentity':2,'readOccurrence':2,'registerPrior':5,'submitEvidence':1,'readBelief':3,'observeDecision':1,'drainEvidence':2,'readDecisions':1,'authorize':1,'bind':1,'observe':1,'adjust':1,'scores':1,'rank':1,'assertRelation':4,'getRelation':1,'outgoing':(2,3,4),'incoming':(2,3,4),'query':1,'catchUp':2,'beginRebuild':1}
MUTATION={'create','recordEpisode','appendEvent','acknowledgeDelivery','occurrenceIdentity','registerPrior','assertRelation','beginRebuild'}

class Ports:
 def __init__(self,path,role,hook=lambda _:None):self.path,self.role,self.hook=Path(path),role,hook
 def invoke(self,path,credential,q):
  require(path==ROUTE and type(q) is dict and set(q)=={'id','composition','scope','interface','selection','operation','args'},'UNSUPPORTED_OPERATION')
  l.identity(q['id']);require(q['composition']==COMPOSITION and len(canonical(q))<=MAX_BYTES,'UNSUPPORTED_PROFILE')
  name=q['interface'];require(name in ROLES and ROLES[name]==self.role,'UNSUPPORTED_OPERATION')
  access=Access(self.path,credential,name);cfg=access.policy.current();require(q['selection']==access.selection() and q['scope']==cfg['scope'],'UNSUPPORTED_PROFILE')
  op=q['operation'];args=q['args'];require(op in OPERATIONS[name] or op=='authorize','UNSUPPORTED_OPERATION');arity=ARITY[op];require(type(args) is list and len(args) in (arity if isinstance(arity,tuple) else (arity,)))
  if op=='authorize':value=access.authorize(q['scope'],args[0])
  else:
   access.authorize(q['scope'],op)
   args=list(args)
   if op in MUTATION:args[0]=Mutation(**args[0]);require(args[0].scope_ref==q['scope'],'UNAUTHORIZED')
   if op in ('submitEvidence','observeDecision'):args[0]=n.request(args[0])
   if name=='search' and op=='query':args[0]=l.AttributeQuery(**args[0])
   if op=='create':require(type(args[2]) is dict and set(args[2])=={'bytes'});args[2]=decode(args[2]['bytes'])
   if op=='assertRelation':args[2]=tuple(tuple(r) for r in args[2])
   if op=='getMany':args[0]=tuple(args[0])
   owner=self.owner(cfg,access,name)
   if op in ('drainEvidence','readDecisions'):
    from .nal_relay import NalEvidenceRelay
    remote=Remote(cfg,'episodic.memory');relay=NalEvidenceRelay(Path(cfg['root'])/'relay.sqlite',remote,owner,hook=self.hook,consumer=consumer(cfg),access=access,acknowledger=remote)
    value=relay.drain(*args) if op=='drainEvidence' else relay.decisions(*args)
   else:value=getattr(owner,op)(*args)
   access.authorize(q['scope'],op)
   if op=='get':value=dict(ref=value.ref,content_type=value.content_type,data=encode(value.bytes))
   if op=='getMany':value=[dict(ref=x.ref,content_type=x.content_type,data=encode(x.bytes)) for x in value]
  reply=dict(id=q['id'],request_digest=digest(canonical(q)),selection=q['selection'],principal=access.principal,value=value);require(len(canonical(reply))<=MAX_BYTES,'NOT_AVAILABLE');return reply
 def owner(self,cfg,access,name):
  root=Path(cfg['root']);root.mkdir(exist_ok=True)
  if name=='atom.storage':
   from .atom_feed import FeedAtomOwner
   from .lookup_composition import AtomSession
   from .adapters.detta import DettaStorage
   return AtomSession(FeedAtomOwner(root/'cognitive-atoms.sqlite',DettaStorage(cfg['detta_binary'],str(root/'cognitive-payloads')),access,self.hook),access)
  atoms=Remote(cfg,'atom.storage') if name!='attention' else None
  if name=='episodic.memory':
   from .nal_episodes import NalEpisodeOwner
   return NalEpisodeOwner(root/'episodes.sqlite',atoms,access,hook=self.hook)
  if name=='belief.revision':
   from .nal_beliefs import NalBeliefOwner
   from .adapters.neoclaw_revision import NativeTruthRevision
   return NalBeliefOwner(root/'beliefs.sqlite',atoms,Remote(cfg,'episodic.memory'),access,NativeTruthRevision(cfg['runtime']),hook=self.hook)
  if name=='attention':
   from .adapters.native_promotion import NativePromotion
   from .promotion import PromotionOwner
   import time
   clock=(lambda:cfg['clock_fixture']) if 'clock_fixture' in cfg else time.time
   if cfg['attention_provider']=='file-fixture':
    from .adapters.file_promotion import FilePromotion
    return FilePromotion(root/'attention.json',access,NativePromotion(cfg['runtime']),clock=clock,hook=self.hook)
   return PromotionOwner(root/'attention.sqlite',access,NativePromotion(cfg['runtime']),clock=clock,hook=self.hook)
  if name=='relations':
   from .relations import RelationOwner
   return RelationOwner(root/'relations.sqlite',atoms,access,l.SCHEMAS,self.hook)
  from .search import SearchOwner
  return SearchOwner(root/'exact-search.sqlite',atoms,atoms,access,cfg['scope'],self.hook)

def client_configuration(path):
 cfg=json.loads(Path(path).read_text());require(cfg['composition']==COMPOSITION and cfg['placement']=='service-network' and cfg['privacy']==PRIVACY and cfg['fallback'] is False,'UNSUPPORTED_PROFILE');chosen=catalogue(cfg)
 require(set(cfg['ports'])==set(OPERATIONS),'UNSUPPORTED_PROFILE')
 frozen={k:cfg[k] for k in ('composition','placement','privacy','scope','context','session','sources','assumption') if k in cfg}
 frozen.update(principal='A',selections={k:selection_token(v) for k,v in chosen.items()},ports={k:{**v['endpoint'],'ca_sha256':digest(Path(v['endpoint']['ca_file']).read_bytes())} for k,v in cfg['ports'].items()})
 return cfg,frozen

def modules(path,root):
 cfg,_=client_configuration(path);ports={name:Remote(cfg,name) for name in OPERATIONS}
 return SimpleNamespace(atoms=ports['atom.storage'],episodes=ports['episodic.memory'],beliefs=ports['belief.revision'],relay=ports['belief.revision'],access=ports,root=Path(root))
