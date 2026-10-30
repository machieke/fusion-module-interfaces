"""Exact generated-inspect commitment transport; signer and journal stay owned."""
from dataclasses import asdict
import http.client,importlib.util,json,time,re
from pathlib import Path
from .contracts import canonical,digest,require,ContractError
from .ports import ApprovedCommitment,ChainObservation,Mutation
from .policy import Policy
from .registry import selection_token
from .responses import error
from .neoclaw_services import PortConnection
from .neoclaw_transport import json_loads
from .adapters.f1r3 import F1R3HTTP
from .adapters.f1r3_m4 import GeneratedCommitments,DESCRIPTOR,PROFILE,chain_identity
from .adapters.f1r3_signing import signer
from .inspect_services import Network
from .client import Peer

COMPOSITION='generated-commitment-service/1'

def observation(value):
 require(type(value) is dict and set(value)=={'deploy_id','inclusion_block','effect_finality','evidence'},'NOT_AVAILABLE')
 require(value['deploy_id'] is None or (type(value['deploy_id']) is str and re.fullmatch('[0-9a-f]{128,144}',value['deploy_id'])),'NOT_AVAILABLE')
 require(value['inclusion_block'] is None or (type(value['inclusion_block']) is str and re.fullmatch('[0-9a-f]{64}',value['inclusion_block'])),'NOT_AVAILABLE')
 require(value['effect_finality'] in ('pending','included','finalized','rejected','not-observed') and type(value['evidence']) is dict,'NOT_AVAILABLE')
 if value['effect_finality'] in ('included','finalized'):
  e=value['evidence'];require(value['deploy_id'] is not None and value['inclusion_block'] is not None and e.get('validation')=='verified','NOT_AVAILABLE')
  require(e.get('inclusion',{}).get('deployId')==value['deploy_id'] and e['inclusion'].get('blockHash')==value['inclusion_block'] and e.get('effect',{}).get('block',{}).get('blockHash')==value['inclusion_block'],'NOT_AVAILABLE')
  if value['effect_finality']=='finalized':require(e.get('deploy_effect_finality',{}).get('state')=='Finalized' and e['inclusion'].get('isFinalized') is True and e['effect']['block'].get('isFinalized') is True,'NOT_AVAILABLE')
 return ChainObservation(**value)

class Remote:
 def __init__(self,registered,approved,binding,authorize):
  self.cfg,self.approved,self.binding,self.authorize=registered,approved,binding,authorize
  self.connection=PortConnection(registered['service_endpoint'],registered['service_credential'])
 def call(self,op,body):
  self.authorize();c=self.connection
  q=dict(composition=COMPOSITION,selection=selection_token(DESCRIPTOR),operation=op,body=body,approved=asdict(self.approved),binding=self.binding)
  client=http.client.HTTPSConnection(c.endpoint['host'],c.endpoint['port'],timeout=25,context=c.context)
  try:
   client.request('POST','/commitment',canonical(q),{'Authorization':'Bearer '+c.credential,'Content-Type':'application/json'})
   response=client.getresponse();require(response.status==200,'NOT_AVAILABLE');raw=response.read(131073);require(len(raw)<=131072,'NOT_AVAILABLE');v=json_loads(raw)
  except (OSError,ValueError,http.client.HTTPException):raise ContractError('NOT_AVAILABLE') from None
  finally:client.close()
  if set(v)=={'error'}:error(v['error']);raise ContractError(v['error']['code'])
  require(set(v)=={'ok','selection','request_digest'} and v['selection']==q['selection'] and v['request_digest']==digest(canonical(q)),'NOT_AVAILABLE');self.authorize();result=observation(v['ok'])
  if result.effect_finality in ('included','finalized'):
   from .adapters.f1r3_m4 import NAMESPACE,expected_expr
   require(result.evidence['value']==dict(namespace=NAMESPACE,operation=self.binding['operation'],digest=self.approved.commitment_digest) and result.evidence['effect']['expr']==expected_expr(self.binding['operation'],self.approved.commitment_digest),'NOT_AVAILABLE')
  return result
 def submit(self,command,commitment):
  require(commitment==self.approved,'UNAUTHORIZED');return self.call('submit',dict(command=asdict(command)))
 def observe(self,deploy_id):return self.call('observe',dict(deploy_id=deploy_id))

class Ports:
 def __init__(self,path,hook=lambda _:None):self.path,self.hook=Path(path),hook
 def invoke(self,path,credential,q):
  require(path=='/commitment' and type(q) is dict and set(q)=={'composition','selection','operation','body','approved','binding'},'INVALID_ARGUMENT')
  require(q['composition']==COMPOSITION and q['selection']==selection_token(DESCRIPTOR),'UNSUPPORTED_PROFILE')
  require(q['operation'] in ('submit','observe'),'UNSUPPORTED_OPERATION')
  policy=Policy(self.path);identity=policy.authenticate(credential);policy.check(identity,'shared-test','consensus.finality.'+q['operation']);cfg=policy.current()
  registration=cfg.get('registration');require(registration is not None,'UNAUTHORIZED')
  # Approval is independently registered by the operator AFTER observing this
  # native caller's completed artifact. A wire approval string cannot grant it.
  require(q['approved']==registration['approved'] and q['binding']==registration['binding'],'UNAUTHORIZED')
  accepted=ApprovedCommitment(**registration['approved']);binding=registration['binding']
  def authorize():
   current=policy.current();require(policy.authenticate(credential)==identity and current.get('registration')==registration,'UNAUTHORIZED')
   policy.check(identity,'shared-test','consensus.finality.'+q['operation'])
   require(time.time_ns()//1000000<binding['authority']['expires_at_ms'],'UNAUTHORIZED')
   peer=Peer(Network(current['inspection']), 'shared-test','reply-A')
   result=peer.result(registration['job_id']);status=peer.status(registration['job_id'])
   require(status['execution']=='succeeded' and status['error'] is None and result==registration['result'],'NOT_AVAILABLE')
   raw=peer.retrieve(accepted.result_ref);source=f"Fusion M1.2 explicitly shareable generated sample {binding['authority']['seed']}\n".encode()
   require(digest(raw)==accepted.commitment_digest and json.loads(raw)==dict(digest=digest(source),length=len(source),operation='inspect_atom',provider_version='0.1.0'),'UNAUTHORIZED')
  def signing(plan):
   require(digest(Path(cfg['protobuf']).read_bytes())==binding['protobuf_sha256'],'UNSUPPORTED_PROFILE')
   spec=importlib.util.spec_from_file_location('reference_signing_pb2',cfg['protobuf']);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
   return signer(cfg['signer_file'],binding['signer'],module.DeployDataProto)(plan)
  authorize();owner=GeneratedCommitments(F1R3HTTP(cfg['node_endpoint']),signing,cfg['journal'],accepted,binding,authorize,self.hook)
  if q['operation']=='submit':
   require(set(q['body'])=={'command'},'INVALID_ARGUMENT');value=owner.submit(Mutation(**q['body']['command']),accepted)
  else:require(set(q['body'])=={'deploy_id'},'INVALID_ARGUMENT');value=owner.observe(q['body']['deploy_id'])
  authorize();return dict(ok=asdict(value),selection=q['selection'],request_digest=digest(canonical(q)))
