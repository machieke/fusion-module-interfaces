"""Process-only H launcher fixtures; no actual H, sockets, cluster or model calls."""
import ast, ctypes, datetime, hashlib, json, os, signal, subprocess, sys, time, unittest
from pathlib import Path
from unittest import mock
ROOT=Path('/data/fusion-operator-pilot-release/evidence-assembly')
SOURCE=ROOT/'h19-detached-command-v2.py'
REPO=Path('/home/purplezky/work/takopi/fusion-module-interfaces')
OUT=ROOT/'h19-detached-mechanics03'
EXPECTED='34400330527071f74473d90a877f2fb6c835281a6e212babb3714a6b0f165e19'
TEXT=SOURCE.read_text();TREE=ast.parse(TEXT)
LIB=ctypes.CDLL('/lib/x86_64-linux-gnu/libc.so.6',use_errno=True);LIB.syscall.restype=ctypes.c_long
PREFIX=ast.Module(body=TREE.body[:next(i for i,n in enumerate(TREE.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='first' for t in n.targets))],type_ignores=[])
FUNCTIONS=[n for n in TREE.body if (isinstance(n,(ast.Import,ast.ImportFrom,ast.FunctionDef)) and (not isinstance(n,ast.FunctionDef) or n.name in ('check','sha','load','utc','put','ident','descendants','pidfd_open','pidfd_signal'))) or (isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ('LIBC_PATH','LIBC_SHA256') for t in n.targets))]
BODY=TEXT[TEXT.index("check(not directory.exists(), 'launch record already exists; do not relaunch')"):]
CHILD='''import json,os,signal,sys,time
from pathlib import Path
p=json.loads(Path(sys.argv[sys.argv.index('--plan')+1]).read_bytes())
root=Path(p['fixture_root']);mode=p['fixture_mode']
def stat(pid):
 s=Path('/proc',str(pid),'stat').read_text();f=s[s.rfind(')')+2:].split();return dict(pid=pid,start_ticks=int(f[19]),session=int(f[3]))
if mode=='nested':
 child=os.fork()
 if child==0:
  os.setsid();(root/'leaf.json').write_text(json.dumps(stat(os.getpid())))
  time.sleep(30);os._exit(0)
 until=time.monotonic()+5
 while not(root/'leaf.json').exists() and time.monotonic()<until:time.sleep(.01)
 (root/'fixture-ready').write_text('ready');os._exit(0)
if mode=='ignore-term':signal.signal(signal.SIGTERM,signal.SIG_IGN)
(root/'fixture-ready').write_text('ready')
time.sleep(2 if mode=='finish' else 30)
(root/'fixture-finished').write_text('finished')
'''
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,v):p.write_text(json.dumps(v,sort_keys=True));return p
def ident(pid):
 raw=Path('/proc',str(pid),'stat').read_text();f=raw[raw.rfind(')')+2:].split();return dict(pid=pid,start_ticks=int(f[19]),session=int(f[3]))
def signal_exact(row,sig):
 fd=LIB.syscall(ctypes.c_long(434),ctypes.c_int(row['pid']),ctypes.c_uint(0))
 if fd<0:raise OSError(ctypes.get_errno(),'fixture pidfd open')
 try:
  if ident(row['pid'])['start_ticks']!=row['start_ticks']:raise RuntimeError('PID reuse')
  result=LIB.syscall(ctypes.c_long(424),ctypes.c_int(fd),ctypes.c_int(sig),ctypes.c_void_p(),ctypes.c_uint(0))
  if result<0:raise OSError(ctypes.get_errno(),'fixture pidfd signal')
 finally:os.close(fd)
def await_file(path,seconds=10):
 until=time.monotonic()+seconds
 while time.monotonic()<until:
  if path.exists():
   try:return json.loads(path.read_bytes())
   except json.JSONDecodeError:pass
  time.sleep(.05)
 raise AssertionError('bounded fixture report absent: '+str(path))
class Mechanics(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  signal_exact(ident(os.getpid()),0)
  OUT.mkdir(mode=0o700,exist_ok=False)
  (OUT/'original-source.py').write_bytes(SOURCE.read_bytes())
  (OUT/'fixture-child.py').write_text(CHILD)
  cls.index=[]
 @classmethod
 def tearDownClass(cls):
  dump(OUT/'fixture-index.json',dict(profile='H-detached-mechanics-fixtures/1',classification='PROCESS_FIXTURES_AND_STATIC_GUARDS_ONLY',source_sha256=sha(SOURCE),extracted_supervisor_body_sha256=hashlib.sha256(BODY.encode()).hexdigest(),cases=cls.index,actual_H_invocations=0,cluster_calls=0,socket_calls=0,additional_live_generations=0))
 def guard(self,stage='native',edit=None,exists=False,source_bad=False):
  root=OUT/(self._testMethodName+'-'+stage+'-'+str(len(list(OUT.iterdir()))));root.mkdir()
  packet=root/'packet';folder=packet/'artifacts/operator-pilot'/('h19-rehearsal-source'if stage=='native'else'h19-clean-install-source');folder.mkdir(parents=True)
  name='h19-native.py'if stage=='native'else'h19-offline.py';source=folder/name
  source.write_bytes((REPO/'artifacts/operator-pilot'/folder.name/name).read_bytes())
  if source_bad:source.write_text('raise AssertionError("MUST NEVER EXECUTE")')
  manifest=dump(packet/'distribution.json',{'fixture_only':True})
  plan=dict(enabled=True,distribution=str(manifest if stage=='native'else packet),distribution_sha256=sha(manifest))
  if stage=='native':
   release=dump(root/'release.json',dict(fixture_only=True,heavy_slot_released=True,distribution_sha256=sha(manifest),implementation_commit='1'*40,namespaces=['fixture-A','fixture-B']))
   plan.update(release_record=str(release),release_record_sha256=sha(release),implementation_commit='1'*40,namespaces=['fixture-A','fixture-B'],maximum_programme_seconds=4200,cleanup_reserved_seconds=300,clean_install_output=str(root/'clean'))
  else:plan.update(max_seconds=1800,output=str(root/'clean'))
  if edit:edit(plan,root)
  plan_path=dump(root/'plan.json',plan);directory=root/'launch'
  if exists:directory.mkdir()
  scope={'__file__':str(SOURCE),'__name__':'fixture_static_guard'}
  with mock.patch.object(sys,'argv',[str(SOURCE),stage,str(source),str(plan_path),str(directory)]),mock.patch.object(os,'fork',side_effect=AssertionError('FORK_FORBIDDEN_IN_STATIC_GUARD')):
   exec(compile(PREFIX,str(SOURCE),'exec'),scope)
  return root,scope
 def harness(self,mode,clock='real'):
  root=OUT/self._testMethodName;root.mkdir();directory=root/'launch'
  script=OUT/'fixture-child.py';plan=dump(root/'plan.json',dict(fixture_mode=mode,fixture_root=str(root),distribution_sha256='0'*64))
  header=ast.unparse(ast.Module(body=FUNCTIONS,type_ignores=[]))+'\n'
  values=f"stage='clean'\nscript=Path({str(script)!r})\nplan_path=Path({str(plan)!r})\ndirectory=Path({str(directory)!r})\nplan=load(plan_path)\nstart_file=None\n"
  shim=''
  if clock!='real':
   shim="_real_time=time\nclass FixtureClock:\n @staticmethod\n def sleep(n):_real_time.sleep(n)\n @staticmethod\n def monotonic():return "+("_real_time.monotonic()*20"if clock=='accelerated'else f"_real_time.monotonic()+(1951 if Path({str(root/'fixture-ready')!r}).exists() else 0)")+"\ntime=FixtureClock\n"
  harness=root/'fixture-supervisor.py';harness.write_text(header+'\n'+values+shim+'\n'+BODY)
  p=subprocess.run([sys.executable,'-B','-I',str(harness)],capture_output=True,timeout=12)
  (root/'launch.stdout').write_bytes(p.stdout);(root/'launch.stderr').write_bytes(p.stderr)
  self.assertEqual(p.returncode,0,p.stderr.decode());ready=await_file(directory/'ready.json')
  self.index.append(dict(case=self._testMethodName,harness_sha256=sha(harness),clock=clock,child=mode,guard_substitution='Static guard stage bypassed ONLY in mechanics harness; tested separately',unchanged_body_sha256=hashlib.sha256(BODY.encode()).hexdigest()))
  self.addCleanup(self.finish_fixture,directory,ready)
  return root,directory,ready
 def finish_fixture(self,directory,ready):
  if(directory/'terminal.json').exists():return
  try:signal_exact(ready['supervisor'],signal.SIGTERM)
  except ProcessLookupError:pass
  await_file(directory/'terminal.json',35)
 def wait_ready_child(self,root):
  until=time.monotonic()+8
  while not(root/'fixture-ready').exists() and time.monotonic()<until:time.sleep(.03)
  self.assertTrue((root/'fixture-ready').exists())
 def terminal(self,directory,seconds=10):
  r=await_file(directory/'terminal.json',seconds);self.assertTrue(r['terminal_barrier']['passed'],r);self.assertTrue(r['terminal_barrier']['no_unreaped_children']);self.assertEqual(r['external_owner_cleanup_calls'],0);return r
 def test_verified_kernel_pidfd_prerequisite(self):
  self.assertEqual(os.uname().machine,'x86_64')
  self.assertEqual(sha('/lib/x86_64-linux-gnu/libc.so.6'),'53b909551f8e581120ddc2d24cfb5df76c52e3c2e2a5dac0d202b25638b3e902')
  signal_exact(ident(os.getpid()),0)
 def test_materialized_source_and_frozen_limits(self):
  self.assertEqual(sha(SOURCE),EXPECTED)
  body=(ROOT/'h19-detached-launch-procedure.md').read_text().split('```python\n',1)[1].split('\n```',1)[0]
  self.assertEqual((ROOT/'h19-detached-command.py').read_text(),body)
  self.assertEqual(sha(ROOT/'h19-detached-command.py'),'318c5060e78a55b6e6c5c8b7d07776e5b111de1c2c843cb57fbaec1939060047')
  self.assertIn("candidate['original_end_monotonic'] == candidate['started_monotonic'] + 4200",TEXT)
  self.assertIn("plan['cleanup_reserved_seconds'] == 300",TEXT)
  self.assertIn("plan['max_seconds'] == 1800",TEXT)
 def test_source_guards_both_phases(self):
  for stage in ('clean','native'):
   with self.subTest(stage=stage),self.assertRaisesRegex(RuntimeError,'source or enabled plan'):self.guard(stage,source_bad=True)
 def test_disabled_guards_both_phases(self):
  for stage in ('clean','native'):
   with self.subTest(stage=stage),self.assertRaisesRegex(RuntimeError,'source or enabled plan'):self.guard(stage,edit=lambda p,r:p.update(enabled=False))
 def test_clean_limit_guard(self):
  with self.assertRaisesRegex(RuntimeError,'clean bounds'):self.guard('clean',edit=lambda p,r:p.update(max_seconds=1801))
 def test_native_limit_guards(self):
  for field,value in [('maximum_programme_seconds',4201),('cleanup_reserved_seconds',301)]:
   with self.subTest(field=field),self.assertRaisesRegex(RuntimeError,'native bounds'):self.guard(edit=lambda p,r:p.update({field:value}))
 def test_native_root_release_guard(self):
  def wrong(p,r):
   release=Path(p['release_record']);v=json.loads(release.read_bytes());v['heavy_slot_released']=False;dump(release,v);p['release_record_sha256']=sha(release)
  with self.assertRaisesRegex(RuntimeError,'separate root release'):self.guard(edit=wrong)
 def test_native_previous_attempt_guard(self):
  def prior(p,r):(Path(p['clean_install_output'])/'h19-native').mkdir(parents=True)
  with self.assertRaisesRegex(RuntimeError,'native attempt already exists'):self.guard(edit=prior)
 def test_packet_digest_guard(self):
  for stage in ('clean','native'):
   with self.subTest(stage=stage),self.assertRaisesRegex(RuntimeError,'final packet mismatch'):self.guard(stage,edit=lambda p,r:p.update(distribution_sha256='f'*64))
 def test_duplicate_launch_guard(self):
  for stage in ('clean','native'):
   with self.subTest(stage=stage),self.assertRaisesRegex(RuntimeError,'launch record already exists'):self.guard(stage,exists=True)
 def test_static_valid_guard_never_forks(self):
  for stage in ('clean','native'):
   root,scope=self.guard(stage);self.assertTrue((root/'launch/launch.json').exists());self.assertNotIn('first',scope)
 def test_detached_parent_exit_survival(self):
  root,directory,ready=self.harness('finish');self.assertFalse((root/'fixture-finished').exists());r=self.terminal(directory)
  self.assertTrue((root/'fixture-finished').exists());self.assertEqual(r['entry_exit_code'],0);self.assertEqual(r['status'],'CHILD_TERMINAL');self.assertEqual(r['child']['session'],r['child']['pid'])
 def test_subreaper_nested_setsid_child(self):
  root,directory,ready=self.harness('nested');r=self.terminal(directory);leaf=json.loads((root/'leaf.json').read_bytes())
  self.assertEqual(leaf['pid'],leaf['session']);self.assertGreaterEqual(len(r['child_exits']),2)
  self.assertTrue(any(x['pid']==leaf['pid']for x in r['child_exits']));self.assertTrue(any(x['process']['pid']==leaf['pid']for x in r['signals_sent']))
 def signal_fixture(self,wrong=False):
  root=OUT/self._testMethodName;root.mkdir();plan=dump(root/'plan.json',dict(fixture_mode='wait',fixture_root=str(root)))
  p=subprocess.Popen([sys.executable,'-B','-I',str(OUT/'fixture-child.py'),'--plan',str(plan),'--execute'],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  try:
   row=ident(p.pid);scope=dict(os=os,signal=signal,Path=Path,ctypes=ctypes,datetime=datetime,libc=LIB,report={'signals_sent':[]})
   defs=[x for x in TREE.body if isinstance(x,ast.FunctionDef)and x.name in ('check','ident','send','pidfd_open','pidfd_signal','utc')]
   exec(compile(ast.Module(body=defs,type_ignores=[]),str(SOURCE),'exec'),scope)
   if wrong:
    with self.assertRaisesRegex(RuntimeError,'PID reuse'):scope['send'](dict(row,start_ticks=row['start_ticks']+1),signal.SIGTERM)
    self.assertIsNone(p.poll());self.assertEqual(scope['report']['signals_sent'],[])
   else:
    scope['send'](row,signal.SIGTERM);p.wait(timeout=5);self.assertEqual(p.returncode,-signal.SIGTERM);self.assertEqual(len(scope['report']['signals_sent']),1)
  finally:
   if p.poll()is None:signal_exact(row,signal.SIGTERM)
   p.wait(timeout=5)
 def test_pidfd_wrong_start_ticks_refused(self):self.signal_fixture(wrong=True)
 def test_pidfd_exact_identity_signal(self):self.signal_fixture()
 def test_timeout_branch_with_declared_clock_fixture(self):
  root,directory,ready=self.harness('wait',clock='jump');r=self.terminal(directory)
  self.assertEqual(r['status'],'FAIL_RETAINED');self.assertEqual(r['interruption'],'finite process envelope expired');self.assertLess(r['entry_exit_code'],0)
 def test_term_signal_barrier(self):
  root,directory,ready=self.harness('wait');self.wait_ready_child(root);signal_exact(ready['supervisor'],signal.SIGTERM);r=self.terminal(directory)
  self.assertEqual(r['status'],'FAIL_RETAINED');self.assertEqual(r['interruption'],'signal:SIGTERM');self.assertLess(r['entry_exit_code'],0)
 def test_term_ignored_then_kill_with_declared_clock_fixture(self):
  root,directory,ready=self.harness('ignore-term',clock='accelerated');self.wait_ready_child(root);signal_exact(ready['supervisor'],signal.SIGTERM);r=self.terminal(directory)
  self.assertEqual(r['entry_exit_code'],-signal.SIGKILL);self.assertTrue(any(x['signal']==signal.SIGKILL for x in r['signals_sent']))
if __name__=='__main__':unittest.main(verbosity=2)
