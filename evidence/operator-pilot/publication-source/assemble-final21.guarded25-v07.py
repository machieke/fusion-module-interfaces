#!/usr/bin/env python3
"""Task-local detached publication assembler. Never runs owners/tests/providers.

Input remains disabled until the parent supplies exact terminal artifacts and
reviewed publication selections. Existing verifier semantics are unchanged.
"""
import argparse,ast,copy,hashlib,json,os,re,shutil
from pathlib import Path
from fusion.contracts import canonical,digest,require
from integration.single_node import pilot_evidence as ev

SOURCE='437927520d53825dc9c642df6cc074d6ccccb3ccaec4bd937402e319baacd6fc'
VERIFIER='8cb4278aac8e9dca9dad320998bd7e1645f0b46cc07e6c89ee2a58cb5e60edef'
ARTIFACT_VERIFIER='d64c3bd4a4330871bcf1e219722dd96ec5e119003ca2bf62fcfc6a0e9c445e32'
BASE_EVIDENCE='f07d0ce73e6bc02c1df9aa2d794830d493fb9fca5bbb74dcfea724a547d6f07c'
SDK25='f902477c74ed25c5753d5903fa3c9071c6a6820172c3cc6cc8bb8ef2fd27ee90'
GO04='4d08cc94758d475e621e8471ed4dd8150240e9a3c297a93642710e20c9ccb853'
IMAGES14={'base':'sha256:5ec0bdabf61b8542b2fe285c534d8824f52146c9674d99830bac6e622738cb09',
 'caller':'sha256:3fd959af4dc1b5b4b941d979863355a5e9bebe9df85ddc6147f449fea040860d',
 'embedding':'sha256:77e6501a2bd3810e49408df9e9e4c44ff1470779a8d9b79c0c9a11d37fd80f7b',
 'chain':'sha256:4762a1b69bb57e5e0b47ceb54813f217f1a1dbc6b7d4ae6566925d71c9281fc7'}
REQUIRED={'H-native-adopter','G18-readback-installed25','A14','A15','A16','A17','G18-readback-health','B14','C18','E14','F15','F16','F17','G18','protected-final','H-final-install','implementation-source-reconciliation'}
NEW_AUDITS={'authored-publication02':('historical','STATIC'),
 'authored-attention04':('artifact-only','FIXTURE'),
 'authored-chart01':('historical','FIXTURE'),
 'authored-chart02':('historical','FIXTURE'),
 'authored-chart16':('candidate','FIXTURE'),
 'authored-retirement22':('candidate','FIXTURE'),
 'authored-readiness23':('candidate','FIXTURE'),
 'authored-profile24':('candidate','FIXTURE'),
 'authored-chain25':('candidate','FIXTURE')}

def sha(p):return digest(Path(p).read_bytes())
def load(p):return ev.load(Path(p).read_bytes())
def relative(value):
 require(type(value) is str,'INVALID_ARGUMENT');p=Path(value)
 require(not p.is_absolute() and p.parts and '..' not in p.parts,'UNAUTHORIZED');return p

def frozen(row):
 require(type(row) is dict and set(row)=={'path','sha256'},'INVALID_ARGUMENT')
 ev.pin(row['sha256']);p=Path(row['path']).resolve();require(p.is_file() and sha(p)==row['sha256'],'CONFLICT');return p

def preflight(path):
 config=load(path)
 require(config['profile']=='task-local-final-detached-evidence/1' and config['ready'] is True,'NOT_AVAILABLE')
 require(config['additional_live_generations']==0,'UNAUTHORIZED')
 require(re.fullmatch('[0-9a-f]{40}',config['implementation_commit']) is not None,'INVALID_ARGUMENT')
 require(config['implementation_commit']!='e68635af2611263cb7e5f88ebc5bfce9de43bc1f','CONFLICT')
 require(sha(ev.__file__)==VERIFIER,'CONFLICT')
 from integration.single_node import reference_artifacts
 require(sha(reference_artifacts.__file__)==ARTIFACT_VERIFIER,'CONFLICT')
 base=frozen(config['base_evidence']);require(sha(base)==BASE_EVIDENCE,'CONFLICT')
 old=load(base);require(old['release_status']=='PARTIAL','CONFLICT')
 final=frozen(config['final_distribution']);distribution=load(final)
 require(digest(canonical(distribution['tested_source']))==SOURCE,'CONFLICT')
 public_pins=config['frozen_public_sources'];require(type(public_pins) is dict and 1<=len(public_pins)<=256,'NOT_AVAILABLE')
 registered={x['path']:x for x in distribution['files']}
 for name,pin in public_pins.items():
  relative(name);ev.pin(pin);require(name in registered and registered[name]['sha256']==pin and sha(final.parent/name)==pin,'CONFLICT')
 require(config['selected_count_audit_source'] in public_pins,'NOT_AVAILABLE')
 require({k:x['manifest'] for k,x in distribution['images'].items()}==IMAGES14,'CONFLICT')
 require(sha(final.parent/relative(distribution['sdk_build_manifest']))==SDK25,'CONFLICT')
 sdk25_equivalence(load(final.parent/relative(distribution['sdk_build_manifest'])),distribution['tested_source'])
 require(sha(final.parent/relative(distribution['reference_providers']['inspect-go']))==GO04,'CONFLICT')
 ev.pin(config['final_chart_archive_sha256'])
 require(sha(final.parent/relative(distribution['chart']))==config['final_chart_archive_sha256'],'CONFLICT')
 # No private primary hashes, filenames or raw content leave this local guard.
 rows=config['required_terminals'];require(type(rows) is list and {x['id'] for x in rows}==REQUIRED and len(rows)==len(REQUIRED),'NOT_AVAILABLE')
 guard=[]
 for row in rows:
  require(set(row)=={'id','path','visibility','sha256','bytes','pointer','terminal_values'},'INVALID_ARGUMENT')
  p=Path(row['path']);require(p.is_file() and not p.is_symlink(),'NOT_AVAILABLE')
  if row['visibility']=='unavailable-private':require(row['sha256'] is None and row['bytes'] is None,'UNAUTHORIZED')
  else:
   require(row['visibility']=='approved-public','INVALID_ARGUMENT');ev.pin(row['sha256']);require(sha(p)==row['sha256'] and p.stat().st_size==row['bytes'],'CONFLICT')
  value=load(p);ev.counters(value);observed=ev.pointer(value,row['pointer'])
  require(type(row['terminal_values']) is list and row['terminal_values'],'INVALID_ARGUMENT')
  require(all(x not in ('RUNNING','NOT_RUN','PENDING','FROZEN_AWAITING_SERIALIZED_HANDOFF') for x in row['terminal_values']),'INVALID_ARGUMENT')
  require(type(observed) in (str,bool) and any(type(observed) is type(x) and observed==x for x in row['terminal_values']),'NOT_AVAILABLE')
  if row['id']=='implementation-source-reconciliation':
   require(observed=='PASS' and value['implementation_commit']==config['implementation_commit'] and
    value['tested_runtime_source_manifest_sha256']==SOURCE and value['tested_source']==distribution['tested_source'],'CONFLICT')
  if row['id'] in ('H-final-install','H-native-adopter'):
   detached_h_report(p,final);h_terminal_history(row['id'],value,p,final)
  if row['id']=='H-final-install':
   require(value['distribution_manifest_sha256']==sha(final) and value['tested_runtime_source_manifest_sha256']==SOURCE,'CONFLICT')
   require(value['generative_runtime_contact'] is False and value['new_native_allocations']==0,'UNAUTHORIZED')
  if row['id']=='H-native-adopter':
   require(value['profile']=='task-local-final-H-native-rehearsal/1','CONFLICT')
   require(value['distribution_sha256']==sha(final) and value['implementation_commit']==config['implementation_commit'] and value['runtime_source_manifest_sha256']==SOURCE,'CONFLICT')
   require(value['operator_wheel_sha256']=='93350732cbc3294f16e2f8c9d787836dd4503c1ddad5a4cb0448493cde6fc4e9' and value['additional_live_generations']==0,'CONFLICT')
   if observed=='PASS':
    require(value['observed_native_counts']=={'direct_inputs':22,'internal_deliveries':6,'captured_inputs':28},'CONFLICT')
    require(value['classification']=='RECORDED_MODEL_PROPOSALS_REAL_NATIVE_TOOLS_AND_DEPLOYED_PROVIDERS' and value['corpora_shared_between_namespaces'] is False,'CONFLICT')
    require(value['protected_comparison']=='PASS' and 0<value['elapsed_seconds']<=4200,'CONFLICT')
    require(len(value['cleanup'])==2 and {x['namespace'] for x in value['cleanup']}=={'omega-ref-pilot-adopter21','omega-ref-pilot-adopter21-go'} and all(x['status']=='PASS' and x['pods']==0 for x in value['cleanup']),'CONFLICT')
  guard.append(dict(id=row['id'],observed_terminal=observed,visibility=row['visibility'],sha256=None if row['visibility']=='unavailable-private' else row['sha256'],bytes=None if row['visibility']=='unavailable-private' else row['bytes']))
 extensions=load(frozen(config['extensions']));require(extensions['profile']=='task-local-final-evidence-bindings/1','UNSUPPORTED_PROFILE')
 require(all(row['source'] is None or row['source'] in public_pins for row in extensions['artifacts']),'NOT_AVAILABLE')
 # Independent archive/image/source checks run only at the eventual explicit invocation.
 checked=ev.verify_distribution(final)
 require(checked['images'],'NOT_AVAILABLE')
 require(not Path(config['output']).exists(),'CONFLICT')
 supplementary=load(frozen(config['supplemental_public_selection']))
 require(supplementary['profile']=='task-local-reviewed-public-evidence/1' and type(supplementary['files']) is list and len(supplementary['files'])<=64,'INVALID_ARGUMENT')
 approved={}
 for row in supplementary['files']:
  require(set(row)=={'id','path','sha256','bytes'} and row['id'] not in approved,'CONFLICT');ev.name(row['id']);ev.pin(row['sha256'])
  p=Path(row['path']);require(p.is_file() and not p.is_symlink() and sha(p)==row['sha256'] and p.stat().st_size==row['bytes'],'CONFLICT');approved[row['id']]=p
 g18_history(config,extensions,final,approved)
 g25_history(config,extensions,final)
 a16_history(config,extensions,final)
 a17_history(config,extensions,final)
 return config,base,old,final,distribution,extensions,approved,guard


# This is a task-local publication guard for the exact failed G18 history.
# It does not change the shipped verifier or manufacture public primaries.
G18_FILES={
 'programme':'programme-report.json', 'execution':'chain/report.json',
 'reader1':'independent-read-attempts/1/observation.json',
 'reader1_result':'independent-read-attempts/1/independent-reader.json',
 'reader2':'independent-read-attempts/2/observation.json',
 'reader2_result':'independent-read-attempts/2/independent-reader.json',
 'reader3':'independent-read-attempts/3/observation.json',
 'reader3_result':'independent-read-attempts/3/independent-reader.json',
 'preflight':'read-diagnostic/report.json',
 'diagnostic1':'read-diagnostic/continuation-report.json',
 'diagnostic2':'read-diagnostic/source-mount-report.json',
 'diagnostic2_result':'read-diagnostic/observer2-result.json'}

def g18_history(config,extensions,final,approved):
 spec=config['g18_history']
 require(set(spec)=={'root','artifacts','execution_run','preflight_run','diagnostic_runs','trace_artifact','retained_gate'},'INVALID_ARGUMENT')
 root=Path(spec['root']);require(root.is_dir() and not root.is_symlink(),'NOT_AVAILABLE')
 ids=spec['artifacts'];require(type(ids) is dict and set(ids)==set(G18_FILES) and len(set(ids.values()))==len(ids),'CONFLICT')
 rows={x['id']:x for x in extensions['artifacts']};data={};private=[]
 failures={(x['artifact'],x['pointer'],x['status']) for x in extensions['failure_observations']}
 for name,relative_path in G18_FILES.items():
  original=root/relative_path;require(original.is_file() and not original.is_symlink(),'NOT_AVAILABLE')
  observed=load(original);ev.counters(observed);data[name]=observed
  require(ids[name] in rows,'NOT_AVAILABLE');row=rows[ids[name]]
  if row['visibility']=='unavailable-private':
   require(row['source'] is None and row['supplemental_id'] is None,'UNAUTHORIZED')
   require((row['id'],None,'UNAVAILABLE_PRIVATE') in failures,'NOT_AVAILABLE');private.append(name)
  else:
   require(row['visibility']=='approved-public' and (row['source'] is None)!=(row['supplemental_id'] is None),'INVALID_ARGUMENT')
   exported=final.parent/relative(row['source']) if row['source'] is not None else approved[row['supplemental_id']]
   # Exact original bytes only. Private originals never gain invented hashes.
   require(exported.read_bytes()==original.read_bytes(),'CONFLICT')
   pointer='/observer_status' if name=='diagnostic2' else '/status'
   require((row['id'],pointer,ev.pointer(observed,pointer)) in failures,'NOT_AVAILABLE')
 require(data['programme']['status']==data['execution']['status']=='FAIL','CONFLICT')
 execution=data['execution'];continuation=execution['final_continuation']
 require(continuation['status']=='finalized' and continuation['submit_reservations']==1 and continuation['observations_spent']==3,'CONFLICT')
 require(execution['final_observation']['effect_finality']=='finalized','CONFLICT')
 readers=[]
 for number in (1,2,3):
  row=data['reader'+str(number)];result=data['reader'+str(number)+'_result']
  require(row['status']=='FAIL' and row['attempt']==number and row['additional_native_inputs']==row['additional_submit_reservations']==0,'CONFLICT')
  require(result['status']=='FAILED' and result['error']=='NOT_AVAILABLE' and result['submissions']==0 and result['signing_performed'] is False,'CONFLICT')
  readers.append(row)
 require(data['programme']['independent_read_attempts']==readers,'CONFLICT')
 for name,invocations in (('preflight',0),('diagnostic1',1),('diagnostic2',1)):
  row=data[name]
  require(row['observer_invocations']==invocations and row['native_inputs']==row['submissions']==0 and row['signing_performed'] is False,'CONFLICT')
 require(data['preflight']['status']==data['diagnostic1']['status']=='FAIL','CONFLICT')
 require(data['diagnostic2']['status']=='OBSERVED' and data['diagnostic2']['observer_status']=='FAIL','CONFLICT')
 require(data['diagnostic2_result']['status']=='FAIL' and data['diagnostic2_result']['last_stage']=='artifact-get-started','CONFLICT')
 require(data['diagnostic2']['last_stage']=='artifact-get-started' and data['diagnostic2']['events']==data['diagnostic2_result']['events'],'CONFLICT')
 require([x['stage'] for x in data['diagnostic2']['events']]==['original-observer-started','atom-client-construction','artifact-get-started'],'CONFLICT')
 runs={x['id']:x for x in extensions['runs']+extensions['replace_pending_runs']}
 require(type(spec['diagnostic_runs']) is list and len(spec['diagnostic_runs'])==2 and len(set(spec['diagnostic_runs']))==2,'INVALID_ARGUMENT')
 required=[(spec['execution_run'],'execution'),(spec['preflight_run'],'preflight'),(spec['diagnostic_runs'][0],'diagnostic1'),(spec['diagnostic_runs'][1],'diagnostic2_result')]
 require(len({x[0] for x in required})==4,'CONFLICT')
 for run_id,name in required:
  require(run_id in runs,'NOT_AVAILABLE');run=runs[run_id]
  if name in private:
   require(run['status']=='UNAVAILABLE_PRIVATE' and run['primary'] is None and run['chain'] is None,'UNAUTHORIZED')
  elif name=='execution' and run['kind']=='chain-trace':
   require(run['status']=='FAIL' and run['chain']['execution_report']==ids['execution'] and run['primary']==spec['trace_artifact'],'CONFLICT')
  else:require(run['kind']=='primary-json' and run['status']=='FAIL' and run['primary']==ids[name],'CONFLICT')
 require(spec['retained_gate'] in extensions['gates'],'NOT_AVAILABLE')
 retained=extensions['gates'][spec['retained_gate']]
 require(retained['status']!='PASS' and spec['execution_run'] in retained['runs'],'CONFLICT')
 trace=spec['trace_artifact']
 if trace is not None:
  require(trace in rows,'NOT_AVAILABLE')
  for run in runs.values():
   if run['primary']!=trace:continue
   require('execution' not in private and run['id']==spec['execution_run'] and run['kind']=='chain-trace' and run['status']=='FAIL' and run['chain']['execution_report']==ids['execution'],'CONFLICT')
 # This observation is intentionally separate from programme/package acceptance.
 # Public independent coverage remains unavailable for every withheld original.
 return dict(original_execution_status='FAIL',effect_finality='finalized',failed_independent_readers=3,
  preliminary_diagnostic_failures=1,diagnostic_invocations=2,diagnostic_statuses=['FAIL','FAIL'],
  diagnostic_node_get_reached=False,additional_native_inputs=0,additional_submit_reservations=0,
  private_primary_names=private,private_primary_sha256=None,private_primary_bytes=None,
  scope='Local static history guard only; no operational PASS, exported private identity, read retry or effect replay')


# Additional exact-history guard. It reads retained reports only and performs no
# owner action. Original g18_history and all original reports remain unchanged.
FOLLOWUP_FILES={
 'constructor':'read-deep-diagnostic/report.json',
 'constructor_result':'read-deep-diagnostic/observer-result.json',
 'transport':'read-deep-diagnostic-stdlib/report.json',
 'transport_result':'read-deep-diagnostic-stdlib/observer-result.json',
 'health':'read-health-diagnostic/report.json',
 'health_result':'read-health-diagnostic/observer-result.json',
 'installed':'read-installed-diagnostic/report.json',
 'installed_reader':'read-installed-diagnostic/reader/report.json',
 'installed_result':'read-installed-diagnostic/reader/independent-reader.json'}
FOLLOWUP_PUBLIC={
 'evidence/operator-pilot/recipe18.json':'e94d4fcb4819494fc38f257032dc7903ac40d161cb75bc7beb805e26d49f5011',
 'evidence/operator-pilot/recipe18-readback.json':'9cf3fdc06a108d70adec4926f81d4eb52176f51b6f8ff7fdad4ff4d358cd2c60',
 'evidence/operator-pilot/recipe18-readback-installed25.json':'0f2dbb9aa917fc4edcc884d0892e814e6bbbc0f389a666c1825a6d8570329f5d'}
G25_PLAN='d25289303537b761d588580aa207ea1780278c22953718f20afa77dfbd586561'
G25_ORIGINAL='56c1e909d311b117ce088b93260031868dd283f9477ed7a417c7e855d45e5490'
G25_COMPOSED='cf174dd1933fcd2c6e21859fac6f7bec258517ccfabb5cd4e6cfbca2a9ddb3a1'


def private_registered(extensions,identity):
 rows=[x for x in extensions['artifacts'] if x['id']==identity]
 require(len(rows)==1,'NOT_AVAILABLE');row=rows[0]
 require(row['visibility']=='unavailable-private' and row['source'] is None and row['supplemental_id'] is None,'UNAUTHORIZED')


def followup_documents(root):
 result={}
 for key,name in FOLLOWUP_FILES.items():
  path=Path(root)/name;require(path.is_file() and not path.is_symlink(),'NOT_AVAILABLE')
  result[key]=load(path);ev.counters(result[key])
 return result


def followup_values(data,original,start,plan,reader_sources,composed):
 for name in ('constructor','transport','health','installed'):
  row=data[name]
  require(row['observer_invocations']==1 and row['native_inputs']==row['submissions']==row['additional_live_generations']==0 and row['signing_performed'] is False,'CONFLICT')
  require(row['cleanup']['pods']==0 and row['cleanup']['pvcs']==14,'CONFLICT')
  require(row['start_ms']<=row['finished_ms']<=row['end_ms'] and 0<row['end_ms']-row['start_ms']<=600000,'CONFLICT')
 for name in ('constructor_result','transport_result','health_result','installed_result'):
  row=data[name];require(row['submissions']==row['additional_live_generations']==0 and row['signing_performed'] is False,'CONFLICT')
 for key in ('constructor','transport'):
  row=data[key];other=data[key+'_result']
  require(row['status']=='OBSERVED' and row['observer_status']==other['status']=='FAIL' and row['events']==other['events'],'CONFLICT')
 require(data['constructor_result']['error']['type']=='TypeError' and not any(x['stage']=='http-request-started' for x in data['constructor_result']['events']),'CONFLICT')
 transport=data['transport_result']['events']
 require(any(x['stage']=='tls-connect-failed' and x.get('error_class')=='ConnectionRefusedError' and x.get('errno')==111 for x in transport),'CONFLICT')
 require(not any(x['stage'] in ('tls-connect-complete','http-headers-complete','artifact-get-complete','node-effect-get-started') for x in transport),'CONFLICT')
 health=data['health'];previous=data['health_result']
 require(health['status']=='OBSERVED' and health['observer_status']==previous['status']=='PASS' and health['events']==previous['events'],'CONFLICT')
 attempts=[x for x in previous['events'] if x['stage']=='storage-path-health']
 require([x['status'] for x in attempts]==['TRANSPORT_FAILED','TRANSPORT_FAILED','READY'] and attempts[-1]['http_status']==200 and attempts[-1]['ready'] is True,'CONFLICT')
 outer=data['installed'];reader=data['installed_reader'];result=data['installed_result']
 require(outer['status']==outer['observer_status']==reader['status']==result['status']=='PASS','CONFLICT')
 require(reader['independent_readback']==result and outer['health']==result['consumer_path_readiness'],'CONFLICT')
 require(start['plan_sha256']==G25_PLAN and start['end_ms']-start['start_ms']==600000 and start['monotonic_end']-start['monotonic_start']==600,'CONFLICT')
 require(outer['start_ms']==start['start_ms'] and outer['end_ms']==start['end_ms'] and outer['start_ms']>plan['historical_chain_deadline_ms'],'CONFLICT')
 require(reader['original_observer_source_sha256']==G25_ORIGINAL and reader['observer_source_sha256']==G25_COMPOSED and digest(composed)==G25_COMPOSED,'CONFLICT')
 for name,pin in plan['installed_sources'].items():
  require(name in reader_sources and reader_sources[name]==pin,'CONFLICT')
 ready=result['consumer_path_readiness']
 require(ready['profile']=='bounded-chain-consumer-readiness/1' and ready['original_reader_sha256']==G25_ORIGINAL,'CONFLICT')
 require(ready['original_reader_invocations']==1 and ready['artifact_retries']==0 and ready['maximum_health_attempts']==8 and ready['maximum_health_seconds']==30,'CONFLICT')
 require([x['status'] for x in ready['health_attempts']]==['TRANSPORT_FAILED','READY'],'CONFLICT')
 require(ready['health_attempts'][0]['errno']==111 and ready['health_attempts'][-1]['http_status']==200 and ready['health_attempts'][-1]['ready'] is True,'CONFLICT')
 require(result['independent_reads'] is True and result['owner_journals_accessed'] is False,'CONFLICT')
 for key in ('trace_sha256','scope','approval_record','artifact_ref','inspect_result_ref','inspect_result_sha256','deploy_id','read_name'):
  require(result[key]==previous['result'][key],'CONFLICT')
 observed=result['observation'];prior=original['final_observation']
 require(original['status']=='FAIL' and original['final_continuation']['submit_reservations']==1 and original['final_continuation']['observations_spent']==3,'CONFLICT')
 require(observed['effect_finality']=='finalized' and observed['evidence']['validation']=='verified','CONFLICT')
 require(observed['inclusion_block']==prior['inclusion_block'] and observed['evidence']['effect']['block']['postStateHash']==prior['evidence']['effect']['block']['postStateHash'],'CONFLICT')
 require(observed['evidence']['deploy_effect_finality']['state']=='Finalized' and observed['evidence']['deploy_effect_finality']['rejection_count']==0,'CONFLICT')
 return dict(scope='Static retained-report validation only; no assembly, node read or owner action',original_readers=3,prior_diagnostic_observers=5,prior_diagnostic_failures=4,prior_diagnostic_passes=1,installed_observers=1,total_observer_invocations=9,installed_health_attempts=2,additional_native_inputs=0,new_signing=0,new_submissions=0,physical_http_attempts=None,public_raw_primary_status='UNAVAILABLE_PRIVATE')


def g25_history(config,extensions,final):
 from examples import pilot_chain_readiness,preview_chain_observer,sustained_chain_qualification
 import importlib
 spec=config['g25_history']
 require(set(spec)=={'root','artifacts','runs','source_reconciliation'},'INVALID_ARGUMENT')
 require(Path(spec['root']).resolve()==Path(config['g18_history']['root']).resolve(),'CONFLICT')
 require(set(spec['artifacts'])==set(FOLLOWUP_FILES),'CONFLICT')
 for name,identity in spec['artifacts'].items():private_registered(extensions,identity)
 runs={x['id']:x for x in extensions['runs']+extensions['replace_pending_runs']}
 require(set(spec['runs'])=={'constructor','transport','health','installed'},'CONFLICT')
 for identity in spec['runs'].values():
  require(identity in runs and runs[identity]['status']=='UNAVAILABLE_PRIVATE' and runs[identity]['primary'] is None and runs[identity]['chain'] is None,'UNAUTHORIZED')
 for name,pin in FOLLOWUP_PUBLIC.items():
  require(config['frozen_public_sources'].get(name)==pin and sha(final.parent/name)==pin,'CONFLICT')
 root=Path(spec['root']);plan_path=root/'read-installed-diagnostic/plan.json'
 require(sha(plan_path)==G25_PLAN,'CONFLICT');plan=load(plan_path)
 sources={name:sha(importlib.import_module(name).__file__) for name in plan['installed_sources']}
 source=Path(preview_chain_observer.__file__).read_text()
 require(digest(source.encode())==G25_ORIGINAL,'CONFLICT')
 result=followup_values(followup_documents(root),load(root/'chain/report.json'),load(root/'read-installed-diagnostic/start.json'),plan,sources,pilot_chain_readiness.compose(source).encode())
 reconciliation=load(frozen(spec['source_reconciliation']))
 require(reconciliation['status']=='INSTALLED_READ_PASS' and reconciliation['runtime_source_sha256']==SOURCE and reconciliation['runtime_native_owner_changes']==0,'CONFLICT')
 require(reconciliation['installed_read_observation']['public_summary_sha256']==FOLLOWUP_PUBLIC['evidence/operator-pilot/recipe18-readback-installed25.json'],'CONFLICT')
 return result


def a16_values(primary,summary,interruption):
 require(primary['status']==summary['status']=='FAIL' and summary['profile']=='operator-pilot-endurance-development-summary/1' and interruption['qualification']=='A16','CONFLICT')
 require(summary['runtime_source_sha256']==SOURCE and interruption['runtime_source_sha256']==SOURCE,'CONFLICT')
 require(summary['operator_wheel_sha256']==interruption['operator_wheel_sha256']=='cd31dbdde1430807cf6730b1245b85679e8f53e15764ceed17812751a02aa2b3','CONFLICT')
 expected={'ordinary_selected_direct_inputs':156,'ordinary_complete':155,'ordinary_uncertain':1,'recipe_selected_direct_inputs':9,'boundary_separate_direct_inputs':1,'all_selected_direct_inputs':166,'all_completed_direct_captures':165,'completed_internal_capture_observations':10,'identity_bound_complete_capture_observations':175,'aggregate_native_capture_stage_events':173}
 require(all(summary['counts'][k]==v for k,v in expected.items()),'CONFLICT')
 require(interruption['status']=='OBSERVED_INTERRUPTION_CAUSE_UNESTABLISHED' and interruption['primary_status']=='FAIL','CONFLICT')
 require(interruption['failure_observation']['initiating_signal_or_sender']=='UNESTABLISHED' and interruption['last_selected_occurrence']['capture']=='UNOBSERVED' and interruption['last_selected_occurrence']['final_owner_state']=='UNOBSERVED','CONFLICT')
 require(interruption['last_selected_occurrence']['input_was_not_reissued'] is True and interruption['last_selected_occurrence']['original_deadline_not_renewed'] is True,'CONFLICT')
 require(summary['cleanup']['pods']==interruption['cleanup']['pods']==0 and summary['cleanup']['pvcs_retained']==interruption['cleanup']['pvcs_retained']==12,'CONFLICT')
 require(summary['additional_live_generations']==interruption['additional_live_generations']==0,'CONFLICT')
 require(interruption['private_evidence']['sha256'] is None and interruption['private_evidence']['bytes'] is None,'UNAUTHORIZED')
 return dict(primary='FAIL',interruption='OBSERVED_INTERRUPTION_CAUSE_UNESTABLISHED',ordinary_selected=156,ordinary_complete=155,ordinary_uncertain=1,boundary_direct_complete=10,internal_complete=10,identity_bound_captures=175,telemetry_capture_events=173,counts_not_merged=True)


def a16_history(config,extensions,final):
 spec=config['a16_history'];require(set(spec)=={'primary','artifact','public_summary','public_interruption'},'INVALID_ARGUMENT')
 private_registered(extensions,spec['artifact'])
 for key in ('public_summary','public_interruption'):
  require(spec[key] in config['frozen_public_sources'] and sha(final.parent/spec[key])==config['frozen_public_sources'][spec[key]],'CONFLICT')
 summary=load(final.parent/spec['public_summary']);interruption=load(final.parent/spec['public_interruption'])
 require(interruption['sanitized_primary']['sha256']==sha(final.parent/spec['public_summary']),'CONFLICT')
 return a16_values(load(spec['primary']),summary,interruption)


def detached_h_report(report_path,final):
 # Final packet is sealed before H. Detached observations may not be embedded in
 # the packet whose digest they attest. Shipped H recipe source is not a report.
 report=Path(report_path).resolve();require(not report.is_relative_to(final.parent.resolve()),'CONFLICT')
 require(not Path(report_path).is_symlink(),'UNAUTHORIZED')


H_PHASES={'installed_sources','browser_tool_preflight','extracted_go_rebuild','browser_placement','browser_resources','four_initial_owner_reads','browser-story','browser-visual','browser-close','browser_normal_maintenance','browser_forward_stopped','browser_terminal','capacity_provision','provider_placement_initial','provider_resources','capacity_observe','provider_drain_retained','provider_terminal'}
H_PASS_PHASES={'browser_tool_preflight','extracted_go_rebuild','browser_placement','browser-story','browser-visual','browser-close','provider_placement_initial','provider_drain_retained'}
H_PLAN='b7713fdfb8d16179083adabdb42970cbf61cacce97de0d22936a374bcba12cba'

def h_terminal_values(identity,value,launcher,start=None,public_plan=None):
 require(launcher['status'] in ('PASS','FAIL') and launcher['additional_live_generations']==0,'CONFLICT')
 if value['status']!='PASS':return
 require(launcher['status']=='PASS' and launcher['exit_code']==0 and not launcher.get('failure'),'CONFLICT')
 require(not value.get('primary_failure') and not value.get('failure') and not value.get('forward_cleanup_failure'),'CONFLICT')
 if identity=='H-final-install':
  require(value['profile']=='operator-pilot-final-clean-artifact-install/1' and value['sdk_build_manifest_sha256']==SDK25 and value['cluster_operations']==0,'CONFLICT')
  require(value['network_namespace']=='NEW_UNSHARED_NETWORK' and value['author_checkout_available'] is False and value['artifact_verification']['status']=='OFFLINE_VERIFIED','CONFLICT')
  require(value['observations'] and all(x['returncode']==0 for x in value['observations']),'CONFLICT')
 else:
  require(identity=='H-native-adopter','INVALID_ARGUMENT')
  phases={x['name']:x['value'] for x in value['phases']}
  require(len(phases)==len(value['phases']) and set(phases)==H_PHASES,'CONFLICT')
  require(all(phases[x].get('status')=='PASS' for x in H_PASS_PHASES),'CONFLICT')
  require(phases['browser_tool_preflight'].get('network')=='ISOLATED' and type(phases['browser_tool_preflight'].get('native_submissions')) is int and phases['browser_tool_preflight']['native_submissions']==0,'CONFLICT')
  require(start['source_files']==public_plan['source_files'] and start['original_end_monotonic']==start['started_monotonic']+4200,'CONFLICT')
  require(value['started_monotonic']==start['started_monotonic'] and value['original_end_monotonic']==start['original_end_monotonic'],'CONFLICT')


def h_terminal_history(identity,value,path,final):
 launcher=load(Path(path).parent/'launcher.json')
 if identity=='H-native-adopter' and value['status']=='PASS':
  bundle=final.parent/'artifacts/operator-pilot/h21-rehearsal-source';plan_path=bundle/'plan.DISABLED.json'
  require(sha(plan_path)==H_PLAN,'CONFLICT');public_plan=load(plan_path)
  for name,pin in public_plan['source_files'].items():
   require('/' not in name and sha(bundle/name)==pin,'CONFLICT')
  h_terminal_values(identity,value,launcher,load(Path(path).parent/'start.json'),public_plan)
 else:h_terminal_values(identity,value,launcher)


def sdk25_equivalence(manifest,tested_source):
 require(manifest['live_generations']==0 and manifest['operator']['sha256']=='93350732cbc3294f16e2f8c9d787836dd4503c1ddad5a4cb0448493cde6fc4e9','CONFLICT')
 require({k:len(manifest[k]['sources']) for k in ('operator','client','provider')}=={'operator':271,'client':18,'provider':7},'CONFLICT')
 overlap={}
 for package in ('operator','client','provider'):
  for name,row in manifest[package]['sources'].items():
   original=row['source']
   if original in tested_source:
    pin=tested_source[original]
    if type(pin) is dict:pin=pin['sha256']
    require(row['sha256']==pin,'CONFLICT');overlap[original]=pin
 require(overlap,'NOT_AVAILABLE')
 return dict(operator_sources=271,client_sources=18,provider_sources=7,shared_runtime_sources_equal=len(overlap),scope='Byte equality for overlapping owner/client sources; operator-only readiness/endurance changes retain separate execution epochs')


A17_PLAN='91249538d82886a5f0bf7166cf857792a748298152ace1c1f1bdc5b1dc7b43f0'
A17_SUPERVISOR='487923200aacc344ebd6c89628b8fa71fe744a3fe4fc7069e87738bfe719bc30'

def a17_values(supervisor,qualifier,cleanup,public):
 require(supervisor['profile']=='task-local-endurance17-supervisor/1' and supervisor['status'] in ('PASS','FAIL_RETAINED'),'NOT_AVAILABLE')
 require(type(supervisor.get('finished_unix_ms')) is int and supervisor['finished_unix_ms']>=supervisor['started_unix_ms'],'NOT_AVAILABLE')
 require(supervisor['plan_sha256']==A17_PLAN and supervisor['source_sha256']==A17_SUPERVISOR,'CONFLICT')
 require(supervisor['namespace']==qualifier['namespace']=='omega-ref-pilot-endurance17','CONFLICT')
 require(supervisor['additional_live_generations']==qualifier['additional_live_generations']==public['additional_live_generations']==0,'CONFLICT')
 require(public['status']==supervisor['status'] and public['qualifier_primary_status']==qualifier['status'],'CONFLICT')
 require(public['runtime_source_sha256']==SOURCE and public['sdk25_manifest_sha256']==SDK25 and public['operator_wheel_sha256']=='93350732cbc3294f16e2f8c9d787836dd4503c1ddad5a4cb0448493cde6fc4e9','CONFLICT')
 require(type(cleanup['pods']['items']) is list and type(cleanup['pvcs']['items']) is list,'CONFLICT')
 if supervisor['status']=='PASS':
  require(qualifier['status']=='PASS' and supervisor['qualifier_primary_status']=='PASS' and supervisor['qualifier_exit_code']==0,'CONFLICT')
  require(supervisor['child_terminal_barrier']['passed'] is True and supervisor['children'] and all(x['reaped'] is True and type(x['exit_code']) is int for x in supervisor['children']),'CONFLICT')
  require(supervisor['cleanup']['status']=='PASS' and supervisor['cleanup']['exit_code']==0 and supervisor['diagnostic_exit_code']==0,'CONFLICT')
  require(len(cleanup['pods']['items'])==0 and len(cleanup['pvcs']['items'])==12,'CONFLICT')
  require(public['counts']['ordinary_selected_direct_inputs']==public['counts']['ordinary_complete']==160 and public['counts']['ordinary_uncertain']==0,'CONFLICT')
 return dict(supervisor_status=supervisor['status'],qualifier_literal_status=qualifier['status'],private_public_visibility='UNAVAILABLE_PRIVATE',status_not_normalized=True)


def a17_history(config,extensions,final):
 spec=config['a17_history'];require(set(spec)=={'root','artifacts','public_summary'},'INVALID_ARGUMENT')
 root=Path(spec['root']);require(set(spec['artifacts'])=={'supervisor','qualifier','cleanup'},'INVALID_ARGUMENT')
 for identity in spec['artifacts'].values():private_registered(extensions,identity)
 require(spec['public_summary'] in config['frozen_public_sources'],'NOT_AVAILABLE')
 path=final.parent/relative(spec['public_summary']);require(sha(path)==config['frozen_public_sources'][spec['public_summary']],'CONFLICT')
 return a17_values(load(root/'supervisor/report.json'),load(root/'endurance-run/report.json'),load(root/'endurance-terminal-resources.json'),load(path))


def counted(packet,m):
 aliases=ev.test_source_aliases(packet,m['test_sources']);methods=set();invocations=skips=0;subscenarios=set();operator={};captures={};internal={}
 for run in m['runs']:
  if run['phase']!='candidate' or run['primary'] is None:continue
  if run['kind'] in ('unittest-verbose','go-test-json'):
   t=(ev.unittest_log if run['kind']=='unittest-verbose' else ev.go_log)(packet.file(run['primary']).read_bytes());invocations+=t['invocations'];skips+=t['skips']
   subscenarios.update((run['id'],x) for x in t['test_scenarios'])
   for identity in t['methods']:methods.add(ev.test_identity(identity,aliases)[0] if run['kind']=='unittest-verbose' else identity)
  if run['kind']=='native-session':
   document=packet.document(run['native']);ev.native_inputs(document)
   for row in document['inputs']:
    identity=(row['role'],row['session'],row['identity']);accepted=row.get('accepted')
    semantic=canonical(dict(command=row['command'],accepted=accepted))
    if identity in operator:
     previous=ev.load(operator[identity]);require(previous['command']==row['command'] and (previous['accepted'] is None or previous['accepted']==accepted),'CONFLICT')
    operator[identity]=semantic;result=(row.get('observed') or {}).get('result')
    if result is not None:
     captured=digest(canonical(result));require(identity not in captures or captures[identity]==captured,'CONFLICT');captures[identity]=captured
  for ref in run['internal']:
   observed=packet.reference(ref)
   for row in observed['inputs']:
    if row['assignment'] not in ('delegated-task','delegated-result'):continue
    key=(observed['principal'],observed['session'],row['id']);value={k:row[k] for k in ('accepted','deadline','assignment','payload')}
    require(key not in internal or internal[key]==value,'CONFLICT');internal[key]=value
 scenarios=packet.document(m['scenario_plan'])['scenarios'];runs={x['id']:x for x in m['runs']}
 return dict(authored_test_methods=len(methods),test_method_invocations=invocations,test_runs=sum(x['kind'] in ('unittest-verbose','go-test-json') and x['phase']=='candidate' and x['primary'] is not None for x in runs.values()),test_subscenarios=len(subscenarios),test_skipped_invocations=skips,workflow_scenarios=sum(runs[x['run']]['phase']=='candidate' for x in scenarios),native_operator_inputs=len(operator),native_accepted_inputs=sum(ev.load(v)['accepted'] is not None for v in operator.values()),observed_internal_native_inputs=len(internal),native_captures=len(captures),additional_live_generations=0)

def historical_audit_source(base,value,phase):
 # Only already approved historical source bytes may come from the frozen base.
 # Candidate audits and ordinary digest lookups remain final-packet-only.
 require(phase=='historical','NOT_AVAILABLE');ev.pin(value);base=Path(base)
 require(base.is_file() and not base.is_symlink() and sha(base)==BASE_EVIDENCE,'CONFLICT')
 root=base.parent.resolve()
 rows=sorted((x for x in load(base)['artifacts'] if x['visibility']=='approved-public' and x['sha256']==value),key=lambda x:x['path'])
 require(rows,'NOT_AVAILABLE');row=rows[0];parts=relative(row['path']);source=root/parts
 require(type(row['bytes']) is int and row['bytes']>=0,'INVALID_ARGUMENT')
 current=root
 for part in parts.parts:
  current=current/part;require(not current.is_symlink(),'UNAUTHORIZED')
 require(source.resolve().is_relative_to(root),'UNAUTHORIZED')
 require(source.is_file(),'NOT_AVAILABLE')
 require(source.stat().st_size==row['bytes'] and sha(source)==value,'CONFLICT')
 return source

def assemble(path):
 config,base,m,final,distribution,ext,approved,guard=preflight(path)
 out=Path(config['output']);out.mkdir(parents=True,mode=0o700,exist_ok=False)
 # Preserve all tested/historical bytes from preparation18, except its old
 # distribution tree; retained old artifacts under that tree are copied below.
 for p in base.parent.iterdir():
  if p.name in ('distribution','evidence.json','evidence.sha256','verification.json'):continue
  if p.is_dir():shutil.copytree(p,out/p.name,copy_function=os.link)
  else:os.link(p,out/p.name)
 shutil.copytree(final.parent,out/'distribution',copy_function=os.link)
 m=copy.deepcopy(m);artifacts=m['artifacts'];by_id={x['id']:x for x in artifacts}
 for row in artifacts:
  if row['id']=='distribution':row.update(sha256=sha(final),bytes=final.stat().st_size)
  elif row['visibility']=='approved-public' and row['path'].startswith('distribution/'):
   target=out/row['path']
   if not target.is_file() or sha(target)!=row['sha256']:
    previous=base.parent/row['path'];require(sha(previous)==row['sha256'],'CONFLICT');row['path']='history-packet18/'+row['path'];target=out/row['path'];target.parent.mkdir(parents=True,exist_ok=True);os.link(previous,target)
 # Every new public source must be inside the verified final packet, or an
 # explicit reviewed, hash-bound supplemental metadata selection (e.g. H).
 file_index={x['path']:x for x in distribution['files']};digest_index={}
 for name,row in file_index.items():digest_index.setdefault(row['sha256'],[]).append(name)
 def final_source(name):
  relative(name);require(name in file_index,'NOT_AVAILABLE');p=final.parent/name;require(sha(p)==file_index[name]['sha256'],'CONFLICT');return p
 def by_digest(value,phase=None):
  ev.pin(value)
  if value in digest_index:return final_source(sorted(digest_index[value])[0])
  return historical_audit_source(base,value,phase)
 def add(identity,destination,source=None,raw=None,private=False):
  ev.name(identity);relative(destination);require(identity not in by_id and destination not in {x['path'] for x in artifacts},'CONFLICT');p=out/destination
  require(not p.exists() and not p.is_symlink(),'CONFLICT')
  if private:row=dict(id=identity,path=destination,sha256=None,bytes=None,visibility='unavailable-private')
  else:
   require((source is None)!=(raw is None),'INVALID_ARGUMENT');p.parent.mkdir(parents=True,exist_ok=True);data=Path(source).read_bytes() if source is not None else raw
   with p.open('xb') as stream:stream.write(data)
   row=dict(id=identity,path=destination,sha256=sha(p),bytes=p.stat().st_size,visibility='approved-public')
  artifacts.append(row);by_id[identity]=row;return identity
 selected=load(final_source(config['selected_count_audit_source']));require(selected['status']=='COMPLETE','CONFLICT')
 add('final-selected-count-audit','counts/final-selected-count-audit.json',source=final_source(config['selected_count_audit_source']))
 new_test_runs=[];aggregate=[]
 for binding in selected['primary_audits']:
  if binding['sha256'] in {x['sha256'] for x in artifacts if x['visibility']=='approved-public'}:continue
  name=Path(binding['path']).parent.name;require(name in NEW_AUDITS,'UNSUPPORTED_PROFILE');phase,classification=NEW_AUDITS[name]
  audit_source=by_digest(binding['sha256']);audit=load(audit_source);require(audit['status']=='COMPLETE' and not audit['unresolved'],'CONFLICT')
  aid=add(name+'-final-audit','counts/final/'+name+'/audit.json',source=audit_source)
  for logical,pin in audit['sources'].items():
   sid=add(name+'-final-'+logical.replace('/','-'),'counts/final/'+name+'/'+logical,source=by_digest(pin,phase=phase));m['historical'].append(dict(artifact=sid,index=aid,pointer='/sources/'+logical.replace('~','~0').replace('/','~1')))
   if phase=='candidate':m['test_sources'][logical]=sid
  for row in audit['runs']:
   rid=name+'--'+row['id'];pid=add(rid+'-final-log','checks/final-'+rid+'.log',source=by_digest(row['sha256']))
   if phase=='artifact-only':
    aggregate.append(dict(audit=aid,primary=pid,invocations=row['invocations'],reason='Exact aggregate primary preserved; source-derived module identities are supplementary and are not fabricated verbose-log observations.'));continue
   parsed=ev.unittest_log((out/by_id[pid]['path']).read_bytes());require(parsed['status']==row['status'] and parsed['invocations']==row['invocations'],'CONFLICT')
   item=dict(id=rid,kind='unittest-verbose',phase=phase,status=parsed['status'],classification=classification,primary=pid,native=None,internal=[],chain=None,source_manifest_sha256=SOURCE,images={},image_binding=None,components={},depends_on=[],reason='Exact post-runtime14 packaging/chart test epoch; failed preliminary and corrected versions remain separate.' if phase=='historical' else '')
   m['runs'].append(item);new_test_runs.append(rid)
 # Prior source-unknown Attention failure remains raw and uncredited.
 fp=selected['attention_helper03_failure']['sha256']
 add('attention03-source-unknown-failure','history-failures/attention03.log',source=by_digest(fp))
 add('final-count-reconciliation','counts/final-reconciliation.json',raw=canonical(dict(status='STATIC_SOURCE_RECONCILED',selected_executed_union=selected['combined_counts'],selected_run_outcomes=selected['selected_run_outcomes'],aggregate_primary_runs=aggregate,new_verbose_runs=new_test_runs,old_broad_scope='535 definitions/555cases/8runs separate; never add aggregates',meaning='Verifier candidate case counts below differ from cross-epoch AST definition and aggregate-primary supplement. No test/provider/native execution by assembler.',additional_live_generations=0)))
 for row in ext['artifacts']:
  require(set(row)=={'id','path','source','supplemental_id','visibility'},'INVALID_ARGUMENT')
  if row['visibility']=='unavailable-private':require(row['source'] is None and row['supplemental_id'] is None,'UNAUTHORIZED');add(row['id'],row['path'],private=True)
  else:
   require(row['visibility']=='approved-public' and (row['source'] is None)!=(row['supplemental_id'] is None),'INVALID_ARGUMENT')
   source=final_source(row['source']) if row['source'] is not None else approved[row['supplemental_id']]
   add(row['id'],row['path'],source=source)
 existing={x['id']:x for x in m['runs']}
 for item in ext['replace_pending_runs']:
  require(item['id'] in existing and existing[item['id']]['status'] in ('NOT_RUN','UNAVAILABLE_PRIVATE'),'CONFLICT');existing[item['id']]=item
 m['runs']=[existing[x['id']] for x in m['runs']]
 for item in ext['runs']:require(item['id'] not in existing,'CONFLICT');m['runs'].append(item);existing[item['id']]=item
 m['candidate']['image_roles']=ext['image_roles'];m['candidate']['source']=distribution['tested_source']
 m['candidate']['source_manifest_sha256']=SOURCE
 images={k:v['manifest'] for k,v in distribution['images'].items()}
 for kind,p in distribution.get('reference_providers',{}).items():images[kind]=load(final.parent/p)['image']['manifest']
 m['candidate']['images']=images
 m['test_sources'].update(ext['test_sources']);m['historical'].extend(ext['historical'])
 # Reviewed failed observations are asserted against their literal source;
 # unavailable private primaries stay unavailable, never synthetic FAIL/PASS DTOs.
 failures=[]
 require(type(ext['failure_observations']) is list and ext['failure_observations'],'NOT_AVAILABLE')
 for row in ext['failure_observations']:
  require(set(row)=={'artifact','kind','pointer','status','reason'} and row['artifact'] in by_id and row['reason'],'INVALID_ARGUMENT')
  artifact=by_id[row['artifact']]
  if artifact['visibility']=='unavailable-private':
   require(row['status']=='UNAVAILABLE_PRIVATE' and row['pointer'] is None,'UNAUTHORIZED')
  else:
   file=out/artifact['path']
   if row['kind']=='unittest-verbose':require(row['pointer'] is None and ev.unittest_log(file.read_bytes())['status']==row['status']=='FAIL','CONFLICT')
   else:
    require(row['kind']=='json-pointer' and row['status'] in ('FAIL','FAILED','PARTIAL'),'INVALID_ARGUMENT')
    require(ev.pointer(load(file),row['pointer'])==row['status'],'CONFLICT')
  failures.append(row)
 add('final-retained-failure-observations','retained-failure-observations.json',raw=canonical(dict(profile='retained-failure-publication-observations/1',observations=failures,scope='Explicit reviewed selected failures; no claim of unseen private-primary verification',additional_live_generations=0)))
 m['gates']=ext['gates'];m['packages']=ext['packages']
 # Never force PASS in a public packet containing withheld private evidence.
 m['release_status']='PARTIAL'
 m['limitations']=ext['limitations']+[
  'Exact tested packet18 runtime14 remains historical installation identity; final packet is separately reconciled publication with SDK25 and separately pinned final chart16.',
  'Implementation commit is separate from tested working-tree/image source hashes and later evidence-only publication commit.',
  'Composite-status summaries are immutable artifacts, not normalized PASS primaries. All raw available failed runs remain retained.',
  'Restricted raw evidence has null digest/bytes and no fabricated native identity/count proof.',
  'No new tests, native/provider/chain operations, generative runtime contact or damaged-copy controls executed by this assembler.'
 ]
 # Replace only scenario-plan metadata in this detached new packet, never an
 # original primary. Every assertion remains checked against its primary file.
 scenarios={'profile':ev.PLAN,'scenarios':ext['scenarios']};old_scenario=by_id[m['scenario_plan']]
 target=out/'scenarios-final.json';require(not target.exists(),'CONFLICT');target.write_bytes(canonical(scenarios));old_scenario.update(path='scenarios-final.json',sha256=sha(target),bytes=target.stat().st_size)
 add('final-publication-provenance','publication-provenance.json',raw=canonical(dict(profile='detached-final-publication-provenance/1',implementation_commit=config['implementation_commit'],implementation_evidence_separation=True,tested_runtime_source_manifest_sha256=SOURCE,base_preparation_sha256=BASE_EVIDENCE,final_distribution_sha256=sha(final),guard_observations=guard,verifier_sha256=sha(ev.__file__),sidecar_written_after_distribution=True,additional_live_generations=0)))
 packet=object.__new__(ev.Packet);packet.root=out;packet.registry=by_id;packet.private=[x['id'] for x in artifacts if x['visibility']=='unavailable-private'];packet.documents={}
 m['counts']=counted(packet,m)
 path=out/'evidence.json';path.write_bytes(canonical(m));path.with_suffix('.sha256').write_text(sha(path)+'\n')
 # Actual existing installed verifier only; no alternate parser/status coercion.
 checked=ev.verify(path);verification=out/'verification.json';verification.write_bytes(canonical(checked))
 index=dict(profile='detached-publication-index/1',implementation_commit=config['implementation_commit'],final_distribution_sha256=sha(final),evidence_manifest_sha256=sha(path),verification_sha256=sha(verification),verifier_sha256=VERIFIER,publication_commit='RECORDED_AFTER_COMMIT_OUTSIDE_SELF_HASHED_CONTENT',status=checked['status'],additional_live_generations=0)
 (out/'publication-index.json').write_bytes(canonical(index))
 return dict(status=checked['status'],evidence_sha256=sha(path),distribution_sha256=sha(final),counts=checked['counts'],output=str(out),additional_live_generations=0)

if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--inputs',required=True);parser.add_argument('--assemble',action='store_true');args=parser.parse_args()
 require(args.assemble,'NOT_AVAILABLE');print(json.dumps(assemble(args.inputs),sort_keys=True))
