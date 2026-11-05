"""Tools-only supplement guards; local files and declared protocol fixtures.

No deployment, native work, generative runtime, real Secret or approval used.
"""
import copy,hashlib,importlib.util,json,subprocess,sys,tempfile,unittest,uuid
from pathlib import Path
from fusion.contracts import ContractError

PATH=Path(__file__).resolve().parents[1]/'examples/pilot_live_pool_subscription.py'
spec=importlib.util.spec_from_file_location('live_pool_supplement',PATH);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class SupplementalGuards(unittest.TestCase):
 def plan(self):
  return dict(profile=module.PROFILE,identity='post-handover-pool-fixture',subscription='post-handover-pool-fixture',namespace='omega-ref-pilot-browser11',role='omega-agent',user='operator',session=str(uuid.uuid4()),scope='synthetic-fixture',provider='shared-fusion-storage',archive=dict(scope='synthetic-fixture',payload={'scope_ref':'synthetic-fixture'},mutation='existing-archive'),source_sha256='a'*64,runtime_source_sha256='b'*64,packet_sha256='c'*64,images={k:'fixture@sha256:'+'d'*64 for k in ('omega-agent','omega-agent-b','fusion-execution','fusion-storage','fusion-messaging','fusion-embedding','fusion-search','fusion-episodes','fusion-beliefs','fusion-attention','fusion-relations','fusion-model','omega-workbench')},limits=dict(total_seconds=600,secret_projection_seconds=120,subscription_ms=300000,socket_phase_ms=15000,pool_read_sends=22,subscription_and_registry_read_calls=7,closed_session_list_reads=2,control_calls=5,archive_read_calls=4,total_module_calls=40,provider_replacements=1))
 def test_frozen_source_and_original_bounds(self):
  q=self.plan();self.assertIs(module.validate_plan(q,'a'*64),q)
  for field in ('subscription_ms','socket_phase_ms','total_seconds','total_module_calls'):
   changed=copy.deepcopy(q);changed['limits'][field]+=1
   with self.assertRaises(ContractError):module.validate_plan(changed,'a'*64)
  with self.assertRaises(ContractError):module.validate_plan(q,'z'*64)
 def test_other_namespace_actor_profile_refused(self):
  for key,value in [('namespace','omega-demo'),('namespace','omega-ref-pilot-handover11-next'),('user','shared'),('role','omega-agent-b'),('profile','arbitrary')]:
   q=self.plan();q[key]=value
   with self.assertRaises(ContractError):module.validate_plan(q,'a'*64)
 def test_archive_scope_and_unknown_configuration_refused(self):
  q=self.plan();q['archive']['payload']['scope_ref']='private-other'
  with self.assertRaises(ContractError):module.validate_plan(q,'a'*64)
  q=self.plan();q['arbitrary_operation']='submit'
  with self.assertRaises(ContractError):module.validate_plan(q,'a'*64)
 def test_embedded_bounded_programs_compile_without_running_provider(self):
  for name in ('POLICY','CLIENT','ARCHIVE'):compile(getattr(module,name),name,'exec')
 def policy(self,root,operation,old='old-fixture-token',new='new-fixture-token'):
  code=module.POLICY.replace('/run/fusion/',str(root)+'/')
  return subprocess.run([sys.executable,'-I','-c',code],input=json.dumps(dict(operation=operation,actor='browser-operator',old=old,new=new)),text=True,capture_output=True)
 def original(self,root):
  cfg=dict(profile='fixture-owner-only',principals={'browser-operator':dict(credential='old-fixture-token',scopes={'synthetic-fixture':['sessions.observe']})},unrelated={'retained_deadline':123,'spent':2})
  raw=json.dumps(cfg,indent=3).encode()+b'\n';(root/'owner.json').write_bytes(raw);return raw,cfg
 def test_atomic_one_principal_credential_and_exact_original_restore(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);raw,old=self.original(root)
   self.assertEqual(self.policy(root,'prepare').returncode,0)
   self.assertEqual(self.policy(root,'apply').returncode,0)
   actual=json.loads((root/'owner.json').read_bytes());self.assertEqual(actual['principals']['browser-operator']['credential'],'new-fixture-token')
   actual['principals']['browser-operator']['credential']='old-fixture-token';self.assertEqual(actual,old)
   self.assertEqual(self.policy(root,'restore').returncode,0);self.assertEqual((root/'owner.json').read_bytes(),raw);self.assertFalse((root/'pilot-pool-policy-original.json').exists())
 def test_wrong_old_credential_has_no_policy_effect(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);raw,_=self.original(root)
   self.assertNotEqual(self.policy(root,'prepare',old='wrong').returncode,0)
   self.assertEqual((root/'owner.json').read_bytes(),raw);self.assertFalse((root/'pilot-pool-policy-original.json').exists())
 def test_unrelated_policy_drift_refuses_overwrite_and_retains_original(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);raw,cfg=self.original(root);self.assertEqual(self.policy(root,'prepare').returncode,0)
   cfg['unrelated']['spent']=3;changed=json.dumps(cfg).encode();(root/'owner.json').write_bytes(changed)
   self.assertNotEqual(self.policy(root,'apply').returncode,0);self.assertEqual((root/'owner.json').read_bytes(),changed)
   self.assertNotEqual(self.policy(root,'restore').returncode,0);self.assertEqual((root/'owner.json').read_bytes(),changed);self.assertEqual((root/'pilot-pool-policy-original.json').read_bytes(),raw)
 def test_restore_after_prepared_but_unapplied_returns_exact_bytes(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);raw,_=self.original(root);self.assertEqual(self.policy(root,'prepare').returncode,0)
   self.assertEqual(self.policy(root,'restore').returncode,0);self.assertEqual((root/'owner.json').read_bytes(),raw)


class ClientProtocolFixture(unittest.TestCase):
 """Run the exact embedded driver against explicit in-process port fixtures."""
 def driver(self,malformed=False):
  import io,time,types
  from unittest.mock import patch
  from fusion import https_pool
  from fusion.contracts import canonical,digest,ContractError
  from fusion import preview_transport
  sid=str(uuid.uuid4());scope='synthetic-fixture';sub='post-handover-pool-fixture';principal='browser-operator';old='old-fixture';new='new-fixture'
  inp=dict(id='immutable-fixture',deadline=123,state='complete',result={'projection':'fixture'})
  baseline=dict(session=sid,scope=scope,principal='A',complete=True,next_after=None,inputs=[inp])
  cfg={'users':{'operator':{'targets':{'omega-agent':dict(scope=scope,principal='A',endpoint=dict(host='omega-agent.omega-ref-pilot-browser11.svc.cluster.local',port=8443,ca_file='fixture'),credential_file='/fixture-token')}}}}
  request=dict(user='operator',role='omega-agent',namespace='omega-ref-pilot-browser11',session=sid,scope=scope,old=old,new=new,subscription=sub,identity=sub,provider='shared-fusion-storage')
  stdin=io.StringIO(json.dumps(request)+'\n'+json.dumps({'operation':'provider-restarted-and-archive-read'})+'\n'+json.dumps({'operation':'original-policy-and-secret-restored'})+'\n');events=[];current=[old];enabled=[False];owner={'created':None,'cursor':0};env={}
  class Socket:
   def fileno(self):return 9
   def getsockname(self):return ('fixture',1)
   def getpeername(self):return ('fixture',2)
  class Output(io.StringIO):
   def write(self,value):
    result=super().write(value)
    if value.startswith('{'):
     e=json.loads(value);events.append(e)
     if e['event']=='OLD_TOKEN_SOCKET_ESTABLISHED':current[0]=new
     if e['event']=='READY_TO_RESTORE':current[0]=old
    return result
  def configure(value):enabled[0]=value is not None;https_pool._entries.clear()
  def close():https_pool._entries.clear()
  def invoke(selected,path,q,deadline):
   isread=q['operation'] in ('binding','observe','read','snapshot','selected','plan','inspect');env['physical']['read_requests' if isread else 'control_requests']+=1
   if enabled[0]:
    if not https_pool._entries:https_pool._entries.append(dict(connection=types.SimpleNamespace(sock=Socket()),count=0))
    row=https_pool._entries[0];row['count']+=1
   if selected['credential']!=current[0]:
    if enabled[0]:row['connection'].sock=None;https_pool._entries.clear()
    raise ContractError('UNAUTHORIZED')
   op=q['operation'];b=q['body']
   if path=='/preview/session':value=baseline if op=='observe' else {'scope':scope}
   elif path=='/preview/providers':
    value={'shared-fusion-storage':{'record':{'scope':scope}}} if op=='selected' else dict(actions=2,head='fixture') if op=='plan' else {'state':'sealed'}
   elif op=='create':owner['created']=time.time_ns()//1000000;value=dict(subscription=sub,session=sid,created_ms=owner['created'],expires_ms=owner['created']+300000)
   elif op=='read':value=dict(subscription=sub,session=sid,expires_ms=owner['created']+300000,cursor=owner['cursor'],head=1,next=1,source='fixture',gap=False,events=[] if owner['cursor'] else [{'sequence':1}])
   elif op=='snapshot':value={'snapshot':baseline}
   elif op=='ack':owner['cursor']=b['cursor'];value={'state':'active'}
   elif op=='close':value={'state':'closed'}
   else:raise AssertionError(op)
   result=dict(id=q['id'],profile=q['profile'],request_digest=digest(canonical(q)),actor=principal,value=value)
   if path=='/preview/session':result['principal']='A'
   if malformed:result['id']='wrong-response-identity'
   return result
  read_bytes=Path.read_bytes;read_text=Path.read_text
  def bytes_(path):return json.dumps(cfg).encode() if str(path)=='/config/browser.json' else read_bytes(path)
  def text_(path,*a,**k):return new if str(path)=='/fixture-token' else read_text(path,*a,**k)
  with patch.object(sys,'stdin',stdin),patch.object(sys,'stdout',Output()),patch.object(Path,'read_bytes',bytes_),patch.object(Path,'read_text',text_),patch.object(preview_transport,'invoke',invoke),patch.object(https_pool,'configure',configure),patch.object(https_pool,'close',close),patch('http.client.HTTPSConnection.request'):
   if malformed:
    with self.assertRaisesRegex(ContractError,'CONFLICT'):exec(compile(module.CLIENT,'CLIENT','exec'),env)
    self.assertEqual(env['controls'],0);return
   exec(compile(module.CLIENT,'CLIENT','exec'),env)
  https_pool._entries.clear();self.assertEqual(events[-1]['event'],'PASS');self.assertEqual(events[-1]['capture_count'],1);self.assertEqual(owner['cursor'],1)
  self.assertTrue(next(e for e in events if e['event']=='READY_TO_RESTORE')['old_socket_retained_across_policy_change'])
  self.assertLessEqual(events[-1]['read_calls']+events[-1]['control_calls']+6,40)

 def test_complete_driver_keeps_old_connection_identity_and_restores_capture(self):self.driver()
 def test_malformed_first_observation_refuses_before_subscription_or_seal(self):self.driver(malformed=True)

if __name__=='__main__':unittest.main()
