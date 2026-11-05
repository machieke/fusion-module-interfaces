import copy,hashlib,importlib.util,json
from pathlib import Path
B=Path('/data/fusion-operator-pilot-release/evidence-assembly');R=Path('/home/purplezky/work/takopi/fusion-module-interfaces')
def raw(p):return Path(p).read_bytes()
def sha(p):return hashlib.sha256(raw(p)).hexdigest()
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
snap=R/'artifacts/operator-pilot/endurance-profile24-source';report=R/'evidence/operator-pilot/endurance-profile24-tests.json';log=R/'artifacts/operator-pilot/endurance-profile24.log';primary=json.loads(raw(report));assert sha(log)==primary['primary_sha256'] and sha(snap/'manifest.json')==primary['source_manifest_sha256']
manifest={n:v['sha256'] for n,v in json.loads(raw(snap/'manifest.json'))['files'].items()}
for name,pin in manifest.items():assert sha(snap/name)==pin
spec=importlib.util.spec_from_file_location('authored_audit',B/'audit_authored_methods.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
d=B/'profile24-index';d.mkdir(exist_ok=False);index={'files':{n:p for n,p in manifest.items() if n.startswith('tests/')},'additional_live_generations':0};(d/'index.json').write_bytes(canonical(index))
new=B/'authored-profile24';m.audit(d/'index.json',snap,[('endurance-profile24',log)],new)
prior=B/'authored-runtime14-sdk23-chart16-counts.json';old=json.loads(raw(prior));rows=copy.deepcopy(old['primary_audits']);newreport=new/'report.json';v=json.loads(raw(newreport));rows.append({'path':str(newreport.relative_to(B)),'sha256':sha(newreport),'counts':v['counts']})
cases={};definitions=set();before=set();passing_cases=set();passing_definitions=set();inv=skips=runs=passing_inv=passing_runs=0;run_outcomes={'PASS':0,'FAIL':0}
for number,row in enumerate(rows):
 p=B/row['path'];assert sha(p)==row['sha256'];v=json.loads(raw(p));assert v['status']=='COMPLETE' and not v['unresolved']
 inv+=v['counts']['method_invocations'];skips+=v['counts']['skipped_invocations'];runs+=v['counts']['test_runs'];all_pass=all(x['status']=='PASS' for x in v['runs'])
 for run in v['runs']:
  run_outcomes[run['status']]+=1
  if run['status']=='PASS':passing_inv+=run['invocations'];passing_runs+=1
 for key,x in v['cases'].items():
  definitions.add(x['definition']);cases.setdefault(key,[]).append({'audit':row['path'],'source_sha256':x['source_sha256'],'definition_ast_sha256':x['definition_ast_sha256']})
  if all_pass:passing_cases.add(key);passing_definitions.add(x['definition'])
  if number<len(rows)-1:before.add(key)
go=old['independent_go04'];out=copy.deepcopy(old)
out.update(prior_count_audit={'path':prior.name,'sha256':sha(prior)},primary_audits=rows,python_counts={'authored_definitions':len(definitions),'case_identities':len(cases),'method_invocations':inv,'skipped_invocations':skips,'test_runs':runs},combined_counts={'authored_definitions':len(definitions)+go['authored_definitions'],'case_identities':len(cases)+go['case_identities'],'method_invocations':inv+go['method_invocations'],'skipped_invocations':skips+go['skipped_invocations'],'test_runs':runs+go['test_runs'],'go_subscenarios':go['subscenarios']},new_case_identities=sorted(set(cases)-before),repeated_case_source_versions=[{'case':k,'versions':v} for k,v in sorted(cases.items()) if len({(x['source_sha256'],x['definition_ast_sha256']) for x in v})>1],increment_explanation='Append exact-source profile24 successful11-method run:11 invocations,1 PASS run,1 new method/case identity. Ten other executions retain existing identities; failed A15 native workload remains a separate retained qualification.',selected_run_outcomes={**run_outcomes,'PASS':run_outcomes['PASS']+go['test_runs']},passing_run_subset={'authored_definitions':len(passing_definitions)+go['authored_definitions'],'case_identities':len(passing_cases)+go['case_identities'],'method_invocations':passing_inv+go['method_invocations'],'test_runs':passing_runs+go['test_runs'],'meaning':'All-PASS audit groups plus independentGo04; known-source chart01 failure remains in full executed union.'},cases_never_observed_in_a_passing_selected_run=sorted(set(cases)-passing_cases),profile24={'public_report_sha256':sha(report),'primary_sha256':sha(log),'source_manifest_sha256':sha(snap/'manifest.json'),'audit_sha256':sha(newreport),'method_invocations':11,'seconds':0.879,'status':'PASS','source_snapshot_timing':primary['snapshot_timing'],'source_change':primary['change'],'classification':primary['classification'],'new_helper_sha256':manifest['examples/pilot_endurance.py'],'sdk24_manifest_sha256':'168e22ddae24ac11f2a23ac141421d13ad24dd517e2f35a1dbd5cf5b8ad4ea3b','prior_sdk23_manifest_sha256':'be5d993e6051a317bc892168ca969923ee6374a3aa8bbe84a101b3ca45f1b9ae','actual_A15':'FAIL_RETAINED_DISTINCT_FROM_REPAIR_TESTS','fresh_A16':'PENDING_AT_AUDIT','C18_G18':'Actual SDK22 execution identity retained; unrelated helper change does not relabel these runs.','additional_live_generations':0},status='COMPLETE')
out['selection_delta']={'new_method_identities':1,'new_authored_definitions':1,'new_invocations':11,'new_pass_runs':1,'new_identity':'tests/test_pilot_operator_package.py::QualifierObservers.test_retained_workload_selects_admitted_inspection_then_named_nal_without_fallback','repeated_method_invocations':10,'runtime_code_changes':0,'chart_changes':0}
assert out['combined_counts']=={'authored_definitions':430,'case_identities':436,'method_invocations':1950,'skipped_invocations':1,'test_runs':29,'go_subscenarios':31}
assert out['selected_run_outcomes']=={'PASS':28,'FAIL':1} and out['new_case_identities']==[out['selection_delta']['new_identity']]
p=B/'authored-runtime14-sdk24-chart16-counts.json';p.write_bytes(canonical(out));print(json.dumps({'path':str(p),'sha256':sha(p),'counts':out['combined_counts'],'outcomes':out['selected_run_outcomes'],'new':out['new_case_identities']},indent=2))
