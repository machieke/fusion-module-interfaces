"""Only source-validation snippets in disconnected bwrap; never a clean/H entrypoint."""
import ast,hashlib,json,os,subprocess,sys,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
BASE=Path('/data/fusion-operator-pilot-release')
OUT=BASE/'evidence-assembly/h20-isolated-guards02'
OLD=HERE.parent/'h19-clean-install-source/h19-offline.py'
NEW=HERE/'h20-offline.py'
REAL=BASE/'qualification-private/final-H19-clean01'
PACKET=BASE/'distribution19'
PREFIX=Path('/home/purplezky/.local/share/uv/python/cpython-3.12.12-linux-x86_64-gnu')
ROLES={'client':('fusion-module-client','0.3.0'),'provider':('fusion-file-feed-example','0.3.0'),'operator':('fusion-preview-operator','0.4.0')}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_bytes())
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,sort_keys=True));return p
def snippet(path):
 t=ast.parse(path.read_text());n=next(n for n in t.body if isinstance(n,ast.Assign)and any(isinstance(a,ast.Name)and a.id=='CHECK_SOURCES'for a in n.targets));return ast.literal_eval(n.value)
CURRENT=snippet(NEW);HISTORICAL=snippet(OLD)
class SourceIsolation(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  OUT.mkdir(mode=0o700,exist_ok=False);cls.records=[]
  (OUT/'source-before.py').write_bytes(NEW.read_bytes());(OUT/'test-before.py').write_bytes(Path(__file__).read_bytes())
 @classmethod
 def tearDownClass(cls):
  save(OUT/'checks.json',dict(profile='H20-isolated-source-validation/1',source_sha256=sha(NEW),test_sha256=sha(__file__),records=cls.records,actual_H_entrypoints=0,installations=0,native_owner_imports=0,cluster_calls=0,additional_live_generations=0,model_runtime_contact=False,network='BWRAP_UNSHARED_NETWORK'))
  assert sha(NEW)==sha(OUT/'source-before.py') and sha(__file__)==sha(OUT/'test-before.py')
 def run_check(self,wanted,work,packet,*,old=False,prefix='',suffix='',label=''):
  root=OUT/(self._testMethodName+('-'+label if label else ''));root.mkdir()
  code=prefix+(HISTORICAL if old else CURRENT)+suffix
  args=['/usr/bin/bwrap','--unshare-all','--die-with-parent','--new-session','--clearenv','--proc','/proc','--dev','/dev','--tmpfs','/tmp','--dir','/home','--dir','/work','--dir','/packet','--dir','/python']
  for p in ('/usr','/lib','/lib64','/bin','/sbin'):args+=['--ro-bind',p,p]
  args+=['--ro-bind',str(PREFIX),'/python','--ro-bind',str(work),'/work','--ro-bind',str(packet),'/packet','--chdir','/work','--setenv','PATH','/python/bin:/usr/bin:/bin','--setenv','PYTHONDONTWRITEBYTECODE','1']
  python='/work/'+wanted[-1]+'/bin/python' if work==REAL else '/python/bin/python3.12'
  args += [python,'-B','-I','-c',code,json.dumps(wanted)]
  p=subprocess.run(args,capture_output=True,timeout=30)
  (root/'stdout').write_bytes(p.stdout);(root/'stderr').write_bytes(p.stderr)
  self.records.append(dict(case=self._testMethodName,label=label,returncode=p.returncode,source_sha256=sha(OLD if old else NEW),snippet_sha256=hashlib.sha256(code.encode()).hexdigest(),provider='REAL_RETAINED_CLEAN_INSTALL_ENVIRONMENT'if work==REAL else'SYNTHETIC_DISTRIBUTION_FIXTURE',network='UNSHARED',native_owner_module_execution=False))
  return p
 def expect_pass(self,p,operator):
  self.assertEqual(p.returncode,0,p.stderr.decode());v=json.loads(p.stdout);self.assertFalse(v['native_owner_imports']);self.assertFalse(v['inference_libraries_present']);self.assertEqual(v['operator_owner_module_available'],operator);self.assertEqual(v['operator_owner_module_manifest_pinned'],operator);return v
 def expect_refusal(self,p,text=None):
  self.assertNotEqual(p.returncode,0)
  if text:self.assertIn(text,p.stderr.decode())
 def fixture(self,wanted,mutation=None):
  directory=OUT/('data-'+self._testMethodName+('-'+mutation if mutation else ''));site=directory/'work/site';packet=directory/'packet';site.mkdir(parents=True);(packet/'wheelhouse').mkdir(parents=True)
  contents={'client':{'fusion_client/__init__.py':'# fixture client\n'},'provider':{'fixture_provider/__init__.py':'# fixture provider\n'},'operator':{'fusion/__init__.py':"raise AssertionError('OWNER_PACKAGE_EXECUTED')\n",'fusion/preview_application.py':"from pathlib import Path\nPath('/work/owner-executed').write_text('forbidden')\nraise AssertionError('OWNER_EXECUTED')\n"}}
  build={};distributions={}
  for role in wanted:
   name,version=ROLES[role];dist=site/(name.replace('-','_')+'-'+version+'.dist-info');dist.mkdir();(dist/'METADATA').write_text('Metadata-Version: 2.1\nName: '+name+'\nVersion: '+version+'\n')
   rows={}
   for rel,text in contents[role].items():
    q=site/rel;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(text);rows[rel]=dict(bytes=q.stat().st_size,sha256=sha(q),source=rel)
   build[role]={'sources':rows};save(dist/'source-manifest.json',{'sources':rows});distributions[role]=dist
  prefix="import sys\nsys.path.insert(0,'/work/site')\n"
  if mutation=='leaked-owner':
   for rel,text in contents['operator'].items():q=site/rel;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(text)
  elif mutation=='unmanifested':
   del build['operator']['sources']['fusion/preview_application.py'];save(distributions['operator']/'source-manifest.json',{'sources':build['operator']['sources']})
  elif mutation=='tampered':(site/'fusion/preview_application.py').write_text('# altered bytes\n')
  elif mutation=='missing':(site/'fusion/preview_application.py').unlink()
  elif mutation=='shadow':
   shadow=directory/'work/shadow'
   for rel,text in contents['operator'].items():q=shadow/rel;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(text)
   prefix += "sys.path.insert(0,'/work/shadow')\n"
  elif mutation=='outside-work':
   q=site/'fusion/preview_application.py';(packet/'outside-owner.py').write_bytes(q.read_bytes());q.unlink();q.symlink_to('/packet/outside-owner.py')
  elif mutation in ('torch','transformers','chromadb'):
   q=site/mutation;q.mkdir();(q/'__init__.py').write_text("raise AssertionError('INFERENCE_MODULE_EXECUTED')\n")
  elif mutation=='preloaded':prefix += "import types\nsys.modules['fusion.preview_application']=types.ModuleType('fusion.preview_application')\n"
  save(packet/'wheelhouse/build-manifest.json',build)
  return directory/'work',packet,prefix
 def test_source_delta_confined_to_check_sources(self):
  a=ast.parse(OLD.read_text());b=ast.parse(NEW.read_text())
  for t in (a,b):
   for n in t.body:
    if isinstance(n,ast.Assign)and any(isinstance(x,ast.Name)and x.id=='CHECK_SOURCES'for x in n.targets):n.value=ast.Constant('CHECK_SOURCES_DELTA')
  self.assertEqual(ast.dump(a),ast.dump(b));self.assertEqual(sha(OLD),'6084ee910656fdc147d6d824d7b1143b28b07b096fd529d4c6fa8d38fa49c9e5')
 def test_supervisor_only_clean_pin_and_path_change(self):
  old=(HERE.parent/'h19-supervision-source/h19-detached-command-v2.py').read_text();new=(HERE.parent/'h20-supervision-source/h20-detached-command.py').read_text()
  expected=old.replace("'clean': '6084ee910656fdc147d6d824d7b1143b28b07b096fd529d4c6fa8d38fa49c9e5'","'clean': '"+sha(NEW)+"'").replace('h19-clean-install-source/h19-offline.py','h20-clean-install-source/h20-offline.py')
  self.assertEqual(new,expected);self.assertIn("'native': '30165c0fe79f7a5778ef2973d4d91cf8536ae6783f68e74191f693b62665bb28'",new)
 def test_disabled_plan_preserves_scope(self):
  old=load(HERE.parent/'h19-clean-install-source/plan.DISABLED.json');new=load(HERE/'plan.DISABLED.json')
  self.assertFalse(new['enabled']);self.assertEqual(new['script_sha256'],sha(NEW));self.assertEqual(new['max_seconds'],1800)
  self.assertEqual(set(k for k in old if old[k]!=new[k]),{'distribution','output','script_sha256'})
 def test_original_failure_remains_actual_primary(self):
  v=load(REAL/'clean-install-report.json');self.assertEqual(v['status'],'FAIL');self.assertEqual(v['new_native_allocations'],0);self.assertEqual(v['cluster_operations'],0);self.assertEqual(v['failure']['message'],'operator-sources failed')
 def test_original_snippet_rejects_real_operator(self):
  self.expect_refusal(self.run_check(['client','provider','operator'],REAL,PACKET,old=True),'fusion.preview_application')
 def test_real_client_sources_remain_isolated(self):
  v=self.expect_pass(self.run_check(['client'],REAL,PACKET),False);self.assertEqual(v['sources']['client']['source_files'],18)
 def test_real_provider_sources_remain_isolated(self):
  v=self.expect_pass(self.run_check(['client','provider'],REAL,PACKET),False);self.assertEqual(v['sources']['provider']['source_files'],7)
 def test_real_operator_manifest_available_without_import(self):
  v=self.expect_pass(self.run_check(['client','provider','operator'],REAL,PACKET),True);self.assertEqual(v['sources']['operator']['source_files'],271)
 def test_actual_owner_import_attempt_is_blocked(self):
  self.expect_refusal(self.run_check(['client','provider','operator'],REAL,PACKET,suffix="\n__import__('fusion.preview_application')\n"),'native owner import refused')
 def test_fixture_owner_code_is_not_executed(self):
  work,packet,prefix=self.fixture(['operator']);self.expect_pass(self.run_check(['operator'],work,packet,prefix=prefix),True);self.assertFalse((work/'owner-executed').exists())
 def test_client_owner_availability_refused(self):
  work,packet,prefix=self.fixture(['client'],'leaked-owner');self.expect_refusal(self.run_check(['client'],work,packet,prefix=prefix),'fusion.preview_application')
 def test_provider_owner_availability_refused(self):
  work,packet,prefix=self.fixture(['client','provider'],'leaked-owner');self.expect_refusal(self.run_check(['client','provider'],work,packet,prefix=prefix),'fusion.preview_application')
 def test_unmanifested_operator_helper_refused(self):
  work,packet,prefix=self.fixture(['operator'],'unmanifested');self.expect_refusal(self.run_check(['operator'],work,packet,prefix=prefix),'unmanifested')
 def test_tampered_operator_helper_refused(self):
  work,packet,prefix=self.fixture(['operator'],'tampered');self.expect_refusal(self.run_check(['operator'],work,packet,prefix=prefix))
 def test_shadowed_same_bytes_operator_helper_refused(self):
  work,packet,prefix=self.fixture(['operator'],'shadow');self.expect_refusal(self.run_check(['operator'],work,packet,prefix=prefix),'origin mismatch')
 def test_operator_helper_outside_work_refused(self):
  work,packet,prefix=self.fixture(['operator'],'outside-work');self.expect_refusal(self.run_check(['operator'],work,packet,prefix=prefix),'origin mismatch')
 def test_inference_libraries_still_refused(self):
  for library in ('torch','transformers','chromadb'):
   with self.subTest(library=library):
    work,packet,prefix=self.fixture(['operator'],library);self.expect_refusal(self.run_check(['operator'],work,packet,prefix=prefix,label=library),library)
 def test_preloaded_owner_refused(self):
  work,packet,prefix=self.fixture(['operator'],'preloaded');self.expect_refusal(self.run_check(['operator'],work,packet,prefix=prefix),'native owner already imported')
 def test_missing_operator_helper_refused(self):
  work,packet,prefix=self.fixture(['operator'],'missing');self.expect_refusal(self.run_check(['operator'],work,packet,prefix=prefix))
if __name__=='__main__':unittest.main(verbosity=2)
