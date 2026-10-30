"""Synthetic same-node selections; separate owners and exact native policies."""
import json
from pathlib import Path
from fusion import cognitive_services as c
from fusion.contracts import require
from fusion.registry import descriptor_wire
from .configure import write

EXTRA=('fusion-episodes','fusion-beliefs','fusion-attention','fusion-relations','fusion-exact-search')
ASSUMPTION='generated-source-assessments-independent-with-compatibility-prior/1'

def configure(settings):
 role=settings['role'];r=settings['reference'];require(r['profile'] in ('cognitive','relations') and r['synthetic'] is True,'UNSUPPORTED_PROFILE')
 state=Path(settings.get('state','/state'));run=Path(settings.get('run','/run/fusion'));state.mkdir(exist_ok=True);run.mkdir(exist_ok=True)
 secret=Path(settings.get('secret_directory','/secrets'))
 def token(name):
  value=(secret/name).read_text().strip();require(32<=len(value)<=256 and value.isascii(),'UNAUTHORIZED');return value
 def ep(role):return dict(host=settings['peers'][role],port=settings['https_port'],ca_file=str(secret/'ca.crt'))
 if role in ('omega-agent','fusion-storage','fusion-search','fusion-embedding'):
  base={k:v for k,v in settings.items() if k!='reference'};base['service_composition']='neoclaw-memory-services/1'
  write(run/'memory-component.json',base)
  from .configure import configure as base_configure
  _,cfg,_,_=base_configure(run/'memory-component.json')
 else:
  cfg=dict(tls_certificate=str(secret/'tls.crt'),tls_key=str(secret/'tls.key'))
  test=settings.get('test',{});require(not test or settings['enable_test_faults'],'UNAUTHORIZED');cfg.update(test_failpoints=bool(test),failpoint_marker=str(state/'pause.json'))
  if test.get('pause_at') and not (state/'pause.json').exists():cfg['pause_at']=test['pause_at']
 catalogue=[descriptor_wire(x) for x in c.descriptors(r['attentionProvider'])];scope=r['scope']
 common=dict(composition=c.COMPOSITION,privacy=c.PRIVACY,scope=scope,catalogue=catalogue,attention_provider=r['attentionProvider'])
 methods=[name+'.'+op for name,ops in c.OPERATIONS.items() for op in ops]+['belief.revision.assume']
 if role in ('fusion-storage',*EXTRA):
  own=[name for name,which in c.ROLES.items() if which==role][0]
  cc=dict(common,root=str(state/'cognitive'),runtime='/opt/native/runtime.json',detta_binary='/opt/native/fusion-detta-adapter',origins=r['origins'],assumptions=[ASSUMPTION],actors={'A':'A'},principals={'A':dict(credential=token('cog-caller-token'),scopes={scope:methods})},ports={})
  if r.get('clockFixture') is not None:cc['clock_fixture']=r['clockFixture']
  for identity,operations in r['delegations'].get(role,{}).items():
   cc['actors'][identity]='A';cc['principals'][identity]=dict(credential=token('cog-in-'+identity),scopes={scope:operations})
  for name in ('atom.storage','episodic.memory'):
   dest=c.ROLES[name];key='cog-out-'+dest
   if (secret/key).exists():cc['ports'][name]=dict(endpoint=ep(dest),credential=token(key))
  write(run/'cognitive-owner.json',cc)
  if role=='fusion-storage':cfg['read_source_principals']=['A']
 if role=='omega-agent':
  client=dict(common,placement='service-network',fallback=False,context='synthetic-native-assessment',session=settings['memory']['session'],sources=r['sources'],assumption=ASSUMPTION,ports={name:dict(endpoint=ep(which),credential=token('cog-'+which+'-token')) for name,which in c.ROLES.items()})
  write(run/'evidence-client.json',client)
  write(run/'attention-client.json',dict(client,output=str(state/'promoted-context.metta')))
  app=json.loads((run/'application.json').read_text());app.update(composition=c.APPLICATION,evidence_config=str(run/'evidence-client.json'),attention_config=str(run/'attention-client.json'))
  write(run/'application.json',app)
 write(run/'owner.json',cfg)
 return settings,cfg,state,run
