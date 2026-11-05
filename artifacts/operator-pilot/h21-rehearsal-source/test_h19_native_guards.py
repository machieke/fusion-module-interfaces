"""Pure selection/denial tests. No cluster, browser, native or model activity."""
import copy,hashlib,importlib.util,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
HERE=Path(__file__).parent
PLAN=HERE/('plan.DISABLED.json'if(HERE/'plan.DISABLED.json').exists()else'h19-native-plan.DISABLED.json')
STORY=HERE/('story.json'if(HERE/'story.json').exists()else'h19-native-story.json')
spec=importlib.util.spec_from_file_location('h19_native_guard_target',HERE/'h19-native.py');N=importlib.util.module_from_spec(spec);spec.loader.exec_module(N)
class Guards(unittest.TestCase):
 def valid(self):
  p=json.loads(PLAN.read_bytes());p['enabled']=True
  for k in ('distribution_sha256','chart_archive_sha256','clean_install_PASS_report_sha256','clean_install_launcher_sha256','clean_install_driver_sha256','clean_install_executed_plan_sha256','release_record_sha256','selected_kubeconfig_sha256','story_plan_sha256','public_plan_sha256'):p[k]='f'*64
  p.update(implementation_commit='e'*40,selected_node_uid='fixture-node',selected_node_name='fixture-node');return p
 def test_disabled_before_any_process(self):
  with patch.object(N.subprocess,'Popen')as launch:
   with self.assertRaisesRegex(RuntimeError,'disabled'):N.outer(PLAN,True)
   launch.assert_not_called()
 def test_explicit_execute_and_complete_bindings(self):
  p=self.valid();self.assertIs(N.validate(p,True),p)
  with self.assertRaisesRegex(RuntimeError,'disabled'):N.validate(p,False)
  for field in ('distribution_sha256','public_plan_sha256','release_record_sha256','selected_kubeconfig_sha256'):
   q=copy.deepcopy(p);q[field]=None
   with self.assertRaisesRegex(RuntimeError,'unfrozen'):N.validate(q,True)
 def test_exact_sources_only(self):
  p=self.valid()
  for name in ('../escaped.py','extra.py'):
   q=copy.deepcopy(p);q['source_files'][name]='a'*64
   with self.assertRaisesRegex(RuntimeError,'source binding'):N.validate(q,True)
  q=copy.deepcopy(p);q['source_files'].pop('h19-go-phases.py')
  with self.assertRaisesRegex(RuntimeError,'source binding'):N.validate(q,True)
 def test_source_drift_refused(self):
  p=self.valid();N.check_sources(p,HERE)
  with tempfile.TemporaryDirectory(prefix='h19-guard-',dir='/dev/shm')as tmp:
   r=Path(tmp)
   for name in N.SOURCES:(r/name).write_bytes((HERE/name).read_bytes())
   (r/'h19-native.py').write_bytes(b'changed')
   with self.assertRaisesRegex(RuntimeError,'source drift'):N.check_sources(p,r)
 def test_no_shared_corpus_or_scope(self):
  p=self.valid()
  for field,value in [('namespaces',[N.NS,N.NS]),('scopes',[N.SCOPE,N.SCOPE]),('provider_state_transfer',True),('corpora_shared_between_namespaces',True)]:
   q=copy.deepcopy(p);q[field]=value
   with self.assertRaises(RuntimeError):N.validate(q,True)
 def test_fixed_counts_original_limits_and_zero_generation(self):
  p=self.valid()
  for field in ('maximum_programme_seconds','cleanup_reserved_seconds','native_direct_ceiling','native_internal_ceiling','native_input_deadline_ms','provider_stage_seconds','browser_story_seconds','additional_live_generations'):
   q=copy.deepcopy(p);q[field]+=1
   with self.assertRaises(RuntimeError):N.validate(q,True)
 def test_no_broad_etc_or_live_placement(self):
  p=self.valid()
  for field,value in [('broad_host_etc_mount',True),('generative_runtime_contact',True),('chain',True),('model_boundary','LIVE')]:
   q=copy.deepcopy(p);q[field]=value
   with self.assertRaises(RuntimeError):N.validate(q,True)
 def test_browser_mounts_only_scoped_bootstrap(self):
  args=N.browser_args('visual',Path('/work/h19-native/browser'),100)
  mounts=[]
  for i,arg in enumerate(args):
   if arg in ('--ro-bind','--bind'):mounts.append(tuple(args[i+1:i+3]))
  for source,target in mounts:
   self.assertNotIn('/credentials',source);self.assertNotIn('/secrets',source)
   self.assertNotEqual(source,'/etc');self.assertNotEqual(target,'/etc')
   self.assertNotEqual(source,'/packet');self.assertNotEqual(source,'/home')
  self.assertIn(('/work/h19-native/browser/user','/user'),mounts)
  self.assertIn(('/work/h19-native/browser/user/hosts','/etc/hosts'),mounts)
  self.assertNotIn('--setenv KUBECONFIG',' '.join(args));self.assertIn('/work/operator/bin/python',args)
 def test_cleanup_recovers_only_fresh_owned_namespace(self):
  row=dict(uid=None,attempted_utc='2026-11-05T12:00:00+00:00');meta=dict(uid='fixture-uid',labels={'omega.reference/owner':N.B.OWNER},creationTimestamp='2026-11-05T12:00:01Z')
  self.assertEqual(N.cleanup_identity(meta,row),'fixture-uid');self.assertEqual(row['uid'],'fixture-uid')
  for changed in [dict(meta,uid='foreign'),dict(meta,labels={})]:
   with self.assertRaises(RuntimeError):N.cleanup_identity(changed,row)
  with self.assertRaisesRegex(RuntimeError,'predates'):N.cleanup_identity(dict(meta,creationTimestamp='2026-11-05T11:59:59Z'),dict(uid=None,attempted_utc='2026-11-05T12:00:00+00:00'))
 def test_exact_assets_and_packet_chart_epoch(self):
  p=self.valid()
  for field,value in [('asset_trees',{}),('source_bundle_relative','/author/tree'),('chart16_source_sha256','0'*64)]:
   q=copy.deepcopy(p);q[field]=value
   with self.assertRaises(RuntimeError):N.validate(q,True)
 def test_story_answer_excluded_from_query(self):
  p=json.loads(STORY.read_bytes())
  self.assertEqual(p['namespace'],N.NS)
  for corpus in p['corpus'].values():
   self.assertIn(corpus['expected'],corpus['remember']);self.assertNotIn(corpus['expected'],corpus['query'])
 def test_source_has_no_fixture_fallback_or_effect_resume(self):
  text=(HERE/'h19-browser-phase.py').read_text();self.assertNotIn('--resume-from',text)
  self.assertIn("'/story.py'",text);self.assertIn("started_proof=True\n            ui('start'",text)
  main=(HERE/'h19-native.py').read_text();self.assertIn("HERE.resolve()==packet/PUBLIC_ROOT",main)
  self.assertIn("finally:\n        signal.signal(signal.SIGTERM,signal.SIG_IGN)",main)
 def provider_fixture(self):
  stages=[];natives=[]
  for name in ('baseline','replacement'):
   sid=name+'-A';recipient=dict(session=name+'-B',allocation={'allocation_id':'incoming/A/'+sid},inputs=[dict(id=name+'-task',assignment='delegated-task',state='complete')])
   stage=dict(status='PASS',stage=name,native_operator_inputs=4,session=sid,delegated_result=dict(id=name+'-return',assignment='delegated-result',state='complete'))
   if name=='baseline':stage['recipient_closures']=[dict(observation=recipient)]
   else:stage.update(closures=[dict(role='omega-agent-b',observation=recipient)],provider_observation={'events':['fixture']},provider_replacement=dict(old_pod='fixture-old',new_pod='fixture-new',original_events_and_descriptor_exact=True,after={'events':['fixture']}))
   stages.append(stage);natives.append(dict(inputs=[dict(session=sid,identity=name+str(i),observed=dict(id=name+str(i),state='complete'))for i in range(4)]))
  return stages,natives
 def test_provider_counts_require_observed_internal_rows(self):
  stages,natives=self.provider_fixture();self.assertEqual(N.provider_counts(stages,natives)['retained_captures'],12)
  stages[0]['recipient_closures']=[]
  with self.assertRaisesRegex(RuntimeError,'internal count'):N.provider_counts(stages,natives)
 def test_provider_counts_reject_duplicate_or_unproven_replacement(self):
  for mutation in ('duplicate','unchanged_pod','wrong_capture'):
   stages,natives=self.provider_fixture()
   if mutation=='duplicate':natives[0]['inputs'][1]=copy.deepcopy(natives[0]['inputs'][0])
   elif mutation=='unchanged_pod':stages[1]['provider_replacement']['new_pod']='fixture-old'
   else:stages[1]['provider_replacement']['after']={'events':[]}
   with self.assertRaises(RuntimeError):N.provider_counts(stages,natives)
 def test_h21_names_are_fresh_and_clean_recipe_is_h20(self):
  p=json.loads(PLAN.read_bytes())
  self.assertEqual(p['namespaces'],['omega-ref-pilot-adopter21','omega-ref-pilot-adopter21-go'])
  self.assertEqual(p['scopes'],['synthetic-pilot-adopter21-browser','synthetic-pilot-adopter21-go'])
  self.assertEqual(p['clean_install_driver_sha256'],'6911b2ccc03042c4d0543b25b0881d01a80cf271f5f0608219b2a79b527371e3')
  self.assertEqual(p['driver_output_subdirectory'],'h19-native')
 def test_exact_executable_selection_refuses_drift(self):
  for field in ('path_in_node','sandbox_path','sha256'):
   p=self.valid();p['browser_executable'][field]+='changed'
   with self.assertRaisesRegex(RuntimeError,'executable selection'):N.validate(p,True)
 def test_regular_executable_mount_precedes_dangling_link(self):
  args=N.browser_args('visual',Path('/work/h19-native/browser'),100)
  mounts=[tuple(args[i+1:i+3])for i,v in enumerate(args)if v=='--ro-bind']
  self.assertIn(('/node/lib/node_modules/agent-browser/bin/agent-browser-linux-x64','/browser-bin/agent-browser'),mounts)
  self.assertNotIn(('/node/bin/agent-browser','/browser-bin/agent-browser'),mounts)
  environment={args[i+1]:args[i+2]for i,v in enumerate(args)if v=='--setenv'}
  self.assertTrue(environment['PATH'].startswith('/browser-bin:/node/bin:'))
  for phase in ('story','close'):
   self.assertNotIn('/browser-bin/agent-browser',N.browser_args(phase,Path('/work/h19-native/browser'),100))
 def test_preflight_is_disconnected_and_has_no_owner_material(self):
  args=N.browser_tool_args();self.assertIn('--unshare-all',args);self.assertNotIn('--share-net',args)
  self.assertEqual(args[-1],'agent-browser --version; /node/bin/proofshot --help; /chrome/chrome --version')
  for denied in ('/credentials','/packet','/work','/helpers','/home/purplezky'):
   self.assertFalse(any(denied in x for x in args))
 def test_preflight_before_go_build_or_cluster_observation(self):
  text=(HERE/'h19-native.py').read_text()
  self.assertLess(text.index("record('browser_tool_preflight'"),text.index("record('extracted_go_rebuild'"))
  self.assertLess(text.index("record('extracted_go_rebuild'"),text.index("protected=json.loads(ops[NS]"))
  self.assertIn("browser_tool_args(),seconds=30",text)
 def test_original_predecessor_and_native_profile_unchanged(self):
  predecessor=HERE.parent/'h19-rehearsal-source/h19-native.py'
  self.assertEqual(hashlib.sha256(predecessor.read_bytes()).hexdigest(),'30165c0fe79f7a5778ef2973d4d91cf8536ae6783f68e74191f693b62665bb28')
  self.assertEqual(N.PROFILE,'task-local-final-H-native-rehearsal/1')
 def test_loopback_fixture_source_compiles_without_external_dependencies(self):
  spec=importlib.util.spec_from_file_location('h21_tools_guard',HERE/'qualify_browser_tools.py');value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value)
  compile(value.FIXTURE,'fixture_server.py','exec')
  self.assertIn("(('127.0.0.1',18081),Handler)",value.FIXTURE)
  self.assertNotIn('fusion',value.FIXTURE)
if __name__=='__main__':unittest.main(verbosity=2)
