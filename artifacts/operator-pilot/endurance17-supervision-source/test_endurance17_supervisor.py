"""Task-local process/guard fixtures only; no cluster, native or model calls."""
import importlib.util,json,os,signal,subprocess,sys,tempfile,threading,time,unittest
from pathlib import Path
from unittest.mock import patch
SOURCE=Path('/data/fusion-operator-pilot-release/qualification-private/parent20/endurance17-supervisor.py')
spec=importlib.util.spec_from_file_location('a17',SOURCE);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class SupervisorFixtures(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.patch=patch.object(m,'ROOT',self.root);self.patch.start();self.addCleanup(self.patch.stop)
 def supervisor(self):
  (self.root/'supervisor').mkdir();p=self.root/'plan.json';p.write_text('{}');r=self.root/'release.json';r.write_text('{}')
  plan=dict(limits=dict(outer_seconds=9000),temporary_directory=str(self.root),tool_path='/usr/bin:/bin',python=sys.executable)
  return m.Supervisor(plan,p,r,m.identity(os.getpid()))
 def test_cleanup_barrier_refuses_unreaped_even_with_exit(self):
  self.assertFalse(m.cleanup_allowed([dict(reaped=False,exit_code=0)]));self.assertFalse(m.cleanup_allowed([dict(reaped=True,exit_code=None)]));self.assertTrue(m.cleanup_allowed([dict(reaped=True,exit_code=-15)]))
 def test_process_identity_binds_start_ticks(self):
  x=m.identity(os.getpid());self.assertTrue(m.same_process(x));x['start_ticks']+=1;self.assertFalse(m.same_process(x))
 def test_receipt_trigger_is_final_allocated_window_only(self):
  p=self.root/'window.json';self.assertFalse(m.receipt_due(p));p.write_text('{');self.assertFalse(m.receipt_due(p))
  p.write_text(json.dumps(dict(inputs=[{}]*20,allocations=[{},{}])));self.assertFalse(m.receipt_due(p))
  p.write_text(json.dumps(dict(inputs=[{}]*21,allocations=[{}])));self.assertFalse(m.receipt_due(p))
  p.write_text(json.dumps(dict(inputs=[{}]*21,allocations=[{},{}])));self.assertTrue(m.receipt_due(p))
 def test_real_child_exit_is_reaped_before_cleanup(self):
  s=self.supervisor();code=s.phase('worker',[sys.executable,'-I','-c','raise SystemExit(3)'],5)
  self.assertEqual(code,3);self.assertTrue(m.cleanup_allowed(s.children));self.assertEqual(s.children[0]['process']['session'],s.children[0]['process']['pid'])
  self.assertEqual(s.phase('cleanup',[sys.executable,'-I','-c','pass'],5,allow_abort=True),0)
  self.assertLessEqual(s.children[0]['finished_unix_ms'],s.children[1]['started_unix_ms'])
 def test_signal_causes_term_reap_then_cleanup(self):
  s=self.supervisor();timer=threading.Timer(.25,lambda:s.signal(signal.SIGTERM,None));timer.start();self.addCleanup(timer.join)
  code=s.phase('qualifier',[sys.executable,'-I','-c','import time;time.sleep(60)'],5)
  self.assertEqual(code,-signal.SIGTERM);self.assertEqual(s.report['signals'][0]['name'],'SIGTERM');self.assertTrue(m.cleanup_allowed(s.children));self.assertEqual(s.children[0]['signals_sent'][0]['signal'],signal.SIGTERM)
  self.assertEqual(s.phase('cleanup',[sys.executable,'-I','-c','pass'],5,allow_abort=True),0)
  self.assertLessEqual(s.children[0]['finished_unix_ms'],s.children[1]['started_unix_ms'])
 def test_phase_timeout_retains_failure_without_resubmission(self):
  s=self.supervisor();code=s.phase('qualifier',[sys.executable,'-I','-c','import time;time.sleep(60)'],.1)
  self.assertNotEqual(code,0);self.assertEqual(len(s.children),1);self.assertEqual(s.children[0]['termination_reason'],'phase bound');self.assertTrue(m.cleanup_allowed(s.children))
 def test_cleanup_has_outer_reserve(self):
  s=self.supervisor();s.end=time.monotonic()+301
  s.phase('worker',[sys.executable,'-I','-c','pass'],500)
  self.assertLessEqual(s.children[0]['deadline_monotonic'],s.end-300)
 def test_duplicate_launch_refuses_before_fork(self):
  (self.root/'supervisor').mkdir();plan=self.root/'p';plan.write_text('{}');release=self.root/'r';release.write_text('{}')
  with patch.object(m,'validate',return_value={}),patch.object(m.os,'fork',side_effect=AssertionError('must not fork')):
   with self.assertRaises(FileExistsError):m.launch(plan,release)
 def test_detached_setsid_survives_launcher_exit(self):
  # Only this fixture replaces run()/validation. Production launch() performs
  # its real double-fork, setsid, fd isolation, parent wait and acknowledgment.
  code='''import importlib.util,json,os,time
from pathlib import Path
spec=importlib.util.spec_from_file_location('a17',SOURCE);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
m.ROOT=Path(ROOT)
class Fixture:
 def __init__(self,plan,p,r,parent):self.p=p;self.parent=parent
 def run(self):
  me=m.identity(os.getpid());m.write(m.ROOT/'supervisor/ready.json',dict(supervisor=me,source_sha256=m.sha(SOURCE),plan_sha256=m.sha(self.p)))
  end=time.monotonic()+5
  while m.same_process(self.parent) and time.monotonic()<end:time.sleep(.02)
  m.write(m.ROOT/'survived.json',dict(parent_gone=not m.same_process(self.parent),self_alive=True,separate_session=me['session']!=self.parent['session']))
m.Supervisor=Fixture;m.validate=lambda *_:{}
p=m.ROOT/'p';p.write_text('{}');r=m.ROOT/'r';r.write_text('{}');m.launch(p,r)
'''.replace('SOURCE',repr(str(SOURCE))).replace('ROOT',repr(str(self.root)))
  # Replace only the literal placeholder; m.ROOT must remain an attribute.
  code=code.replace('m.'+repr(str(self.root)),'m.ROOT')
  r=subprocess.run([sys.executable,'-I','-c',code],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=8)
  self.assertEqual(r.returncode,0,r.stderr);end=time.monotonic()+6
  while not(self.root/'survived.json').exists()and time.monotonic()<end:time.sleep(.03)
  self.assertEqual(json.loads((self.root/'survived.json').read_text()),dict(parent_gone=True,self_alive=True,separate_session=True))
 def test_multicall_namespace_read_uses_pinned_kubectl_argv0(self):
  plan=m.read(SOURCE.parent/'supervisor-plan.json');argv=m.absence_command(plan)
  self.assertEqual(argv[0],'/usr/local/bin/kubectl');self.assertEqual(Path(argv[0]).resolve(),Path(plan['tools']['kubectl']['path']));self.assertEqual(m.sha(argv[0]),plan['tools']['kubectl']['sha256']);self.assertEqual(argv[argv.index('get'):],['get','namespace','omega-ref-pilot-endurance17','--ignore-not-found','-o','json'])
 def test_actual_frozen_artifact_guard_and_wrong_release(self):
  plan=SOURCE.parent/'supervisor-plan.json';release=self.root/'fixture-only-release.json';m.write(release,dict(profile='task-local-endurance17-release/1',plan_sha256=m.sha(plan),namespace=m.NAMESPACE,heavy_slot_released=True,execute_once=True))
  with patch.object(m,'ROOT',SOURCE.parent):
   self.assertEqual(m.validate(plan,release)['qualifier_sha256'],m.QUALIFIER)
   bad=m.read(release);bad['plan_sha256']='0'*64;m.write(release,bad)
   with self.assertRaisesRegex(RuntimeError,'separate exact release required'):m.validate(plan,release)
 def test_frozen_native_bounds_and_no_old_state_reuse(self):
  plan=m.read(SOURCE.parent/'supervisor-plan.json');self.assertEqual(plan['limits']['qualifier_native_seconds'],7200);self.assertEqual(plan['limits']['outer_seconds'],9000);self.assertEqual(plan['namespace'],'omega-ref-pilot-endurance17');self.assertEqual(plan['qualifier_sha256'],m.QUALIFIER)
  w=m.read(SOURCE.parent/'workload.json');self.assertEqual(w['native_operator_inputs'],160);self.assertEqual(w['maximum_seconds'],7200)

if __name__=='__main__':unittest.main(verbosity=2)
