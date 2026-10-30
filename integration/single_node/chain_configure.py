"""Composition of generated inspection and exact fixed commitment owners."""
import json
from pathlib import Path
from .configure import write
from fusion.contracts import require
from fusion import inspect_services as s
from fusion.registry import descriptor_wire,descriptors

ROLES=('omega-agent','fusion-execution','fusion-storage','fusion-messaging','fusion-commitment','f1r3node')
def configure(settings):
 role=settings['role'];r=settings['reference'];chain=r['chain']
 require(r['profile']=='chain' and r['synthetic'] is True and role in ROLES and r['scope']==s.SCOPE,'UNSUPPORTED_PROFILE')
 state=Path('/state');run=Path('/run/fusion');run.mkdir(exist_ok=True);secret=Path('/secrets')
 def token(name):
  v=(secret/name).read_text().strip();require(32<=len(v)<=256 and v.isascii(),'UNAUTHORIZED');return v
 def ep(role):return dict(host=settings['peers'][role],port=settings['https_port'],ca_file='/secrets/ca.crt')
 def principal(name,ops):return dict(credential=token(name),scopes={s.SCOPE:ops})
 atom_ops=['atom.storage.'+x for x in ('create','get','getMany','availability')]
 exec_ops=['execution.'+x for x in ('submit','status','result')]
 msg_ops=['agent.messaging.'+x for x in ('send','poll','ack')]
 common=dict(service_composition=s.COMPOSITION,sharing='generated-shareable',capacity=settings['capacity'],routes={x:dict(scope=s.SCOPE,owner=p) for x,p in [('reply-A','A'),('reply-B','B')]},tls_certificate='/secrets/tls.crt',tls_key='/secrets/tls.key',actors={})
 cfg=dict(common,database=str(state/('execution.sqlite' if role=='fusion-execution' else 'wire.sqlite')))
 test=settings.get('test',{});require(not test or settings.get('enable_test_faults'),'UNAUTHORIZED')
 if test.get('pause_at') and not (state/'pause.json').exists():cfg.update(test_failpoints=True,pause_at=test['pause_at'])
 ports=lambda key:{name:dict(endpoint=ep(which),credential=token(key(which))) for name,which in s.ROLES.items()}
 if role=='omega-agent':
  client=dict(service_composition=s.COMPOSITION,fallback=False,ports=ports(lambda role:role+'-token'))
  write(run/'inspection-client.json',client)
  caller=dict(service_config=str(run/'inspection-client.json'),receipts='/state/inspect.sqlite',descriptors=[descriptor_wire(d) for d in descriptors()],grants=[])
  if test.get('pause_at') and not (state/'caller-pause').exists():
   fault=dict(test_pause_at=test['pause_at'],test_marker='/state/caller-pause')
   if test['pause_at']=='after_observation_before_progress':caller['chain_test']=fault
   else:caller.update(fault)
  if chain.get('registration'):
   reg=chain['registration'];b=reg['binding'];caller['commitment']=dict(b['authority'],operation=b['operation'],chain=b['chain'],signer=b['signer'],limits=b['limits'],protobuf_sha256=b['protobuf_sha256'],journal=b['owner_journal'],descriptor=chain['descriptor'],progress='/state/chain-progress.sqlite',placement='service-network',service_endpoint=ep('fusion-commitment'),service_credential=token('fusion-commitment-token'))
  write(run/'hive-caller.json',caller)
 elif role=='fusion-storage':
  cfg.update(atoms_database='/state/atoms.sqlite',da_root='/state/da',detta_binary='/opt/native/fusion-detta-adapter',principals={'A':principal('caller-token',atom_ops+['agent.messaging.poll']),'worker':principal('worker-token',atom_ops),'mailbox-A':principal('inspect-mailbox-token',['atom.storage.get']),'commit-observer':principal('inspect-observer-token',atom_ops[1:])},actors={'worker':'worker','mailbox-A':'A','commit-observer':'A'})
 elif role=='fusion-execution':
  cfg.update(principals={'A':principal('caller-token',exec_ops+atom_ops+['agent.messaging.poll']),'worker':principal('worker-token',atom_ops),'commit-observer':principal('inspect-observer-token',['execution.status','execution.result','atom.storage.get'])},actors={'commit-observer':'A'},atom_ports={'worker':dict(endpoint=ep('fusion-storage'),credential=token('fusion-storage-token'))},completion_port=dict(endpoint=ep('fusion-messaging'),credential=token('fusion-messaging-token')))
 elif role=='fusion-messaging':
  cfg.update(messages_database='/state/messages.sqlite',principals={'A':principal('caller-token',msg_ops+['atom.storage.get']),'B':dict(credential=token('counterparty-token'),scopes={s.SCOPE:['agent.messaging.poll']}),'worker':principal('worker-token',['agent.messaging.accept'])},atom_ports={'A':dict(endpoint=ep('fusion-storage'),credential=token('inspect-storage-token'))})
 elif role=='fusion-commitment':
  # Only this role mounts signing authority. The independently registered exact
  # completed artifact is public synthetic data, not a caller-supplied grant.
  cfg.update(principals={'A':principal('caller-token',['consensus.finality.submit','consensus.finality.observe'])},registration=chain.get('registration'),journal='/state/commitments.sqlite',protobuf='/opt/chain/signing/signing_pb2.py',signer_file='/secrets/signer.hex',node_endpoint='http://'+settings['peers']['f1r3node']+':40403',inspection=dict(service_composition=s.COMPOSITION,fallback=False,ports=ports(lambda role:'inspect-'+role+'-token')))
 write(run/'owner.json',cfg)
 return settings,cfg,state,run
