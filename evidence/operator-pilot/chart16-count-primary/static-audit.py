import copy,hashlib,importlib.util,json
from pathlib import Path
B=Path('/data/fusion-operator-pilot-release/evidence-assembly');R=Path('/home/purplezky/work/takopi/fusion-module-interfaces')
def raw(p):return Path(p).read_bytes()
def sha(p):return hashlib.sha256(raw(p)).hexdigest()
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
report=R/'evidence/operator-pilot/fault-chart16-tests.json';snap=R/'artifacts/operator-pilot/fault-chart16-source';log=R/'artifacts/operator-pilot/fault-chart16.log'
assert sha(report)=='a417ebf9e55f28ab1446431cbd12c330797d84cf30a82ac5ed0e8dacb0cc83ae'
primary=json.loads(raw(report));assert sha(log)==primary['log_sha256'] and sha(snap/'manifest.json')==primary['sources_sha256']
manifest=json.loads(raw(snap/'manifest.json'))
for name,pin in manifest.items():assert sha(snap/name)==pin
spec=importlib.util.spec_from_file_location('authored_audit',B/'audit_authored_methods.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
d=B/'chart16-index';d.mkdir(exist_ok=False);index={'files':{n:p for n,p in manifest.items() if n.startswith('tests/')},'additional_live_generations':0};(d/'index.json').write_bytes(canonical(index))
(d/'provenance.json').write_bytes(canonical({'profile':'static-source-selection-index/1','source_manifest_sha256':sha(snap/'manifest.json'),'timing':'Copied after run; executing parent reports sources unchanged during and after. This derived source-selection index is not a before-test snapshot.','invocation':'Exact primary verbose log is parsed without executing any test/provider module.'}))
new=B/'authored-chart16';m.audit(d/'index.json',snap,[('fault-chart16',log)],new)
prior=B/'authored-runtime14-sdk21-chart02-counts.json';old=json.loads(raw(prior));rows=copy.deepcopy(old['primary_audits']);newreport=new/'report.json';v=json.loads(raw(newreport));rows.append({'path':str(newreport.relative_to(B)),'sha256':sha(newreport),'counts':v['counts']})
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
out.update(prior_count_audit={'path':prior.name,'sha256':sha(prior)},primary_audits=rows,python_counts={'authored_definitions':len(definitions),'case_identities':len(cases),'method_invocations':inv,'skipped_invocations':skips,'test_runs':runs},combined_counts={'authored_definitions':len(definitions)+go['authored_definitions'],'case_identities':len(cases)+go['case_identities'],'method_invocations':inv+go['method_invocations'],'skipped_invocations':skips+go['skipped_invocations'],'test_runs':runs+go['test_runs'],'go_subscenarios':go['subscenarios']},new_case_identities=sorted(set(cases)-before),repeated_case_source_versions=[{'case':k,'versions':v} for k,v in sorted(cases.items()) if len({(x['source_sha256'],x['definition_ast_sha256']) for x in v})>1],increment_explanation='Append exact-source chart16 successful10-method run:10 invocations,1 PASS run,0 new method/case identities. One existing method adds three literal subTest stages; the primary verbose log reports the enclosing method once and does not enumerate successful subtests. No invented method/subscenario count.',selected_run_outcomes={**run_outcomes,'PASS':run_outcomes['PASS']+go['test_runs']},passing_run_subset={'authored_definitions':len(passing_definitions)+go['authored_definitions'],'case_identities':len(passing_cases)+go['case_identities'],'method_invocations':passing_inv+go['method_invocations'],'test_runs':passing_runs+go['test_runs'],'meaning':'All-PASS audit groups plus independentGo04; retained exact-source chart01 failure stays in the full executed union and is not rewritten.'},cases_never_observed_in_a_passing_selected_run=sorted(set(cases)-passing_cases),chart16={'public_report_sha256':sha(report),'primary_sha256':sha(log),'source_manifest_sha256':sha(snap/'manifest.json'),'audit_sha256':sha(newreport),'method_invocations':10,'seconds':2.497,'status':'PASS','source_snapshot_timing':primary['source_snapshot_timing'],'source_change':primary['source_change'],'classification':'Actual offline Helm/schema/configure functions, synthetic fixture configuration; no native/provider/deployed pass inferred.','schema_change':'One existing runtime fault hook after_application_projection added to the chart enum; explicit test fault opt-in and unknown-stage refusal preserved.','previous_chart_versions':'Retain failed01 and passing02 original test/source/report bytes.','runtime_code_changed':False,'additional_live_generations':0},status='COMPLETE')
out['selection_delta']={'new_method_identities':0,'new_authored_definitions':0,'new_invocations':10,'new_pass_runs':1,'source_body_changed_existing_method':'tests/test_phase2_fault_configuration.py::PreviewFaultChartTests.test_exact_deployed_recovery_hooks_render_without_broadening_unknown_operations','added_literal_subtest_stages':['after_application_projection','after_feed_backend_acceptance','after_model_provider_capture'],'subtest_count_semantics':'Three added authored subTest cases are visible statically; successful subtests are not individually counted by this raw verbose log. The selected union retains31 independently reported Go subscenarios only.'}
assert out['combined_counts']=={'authored_definitions':427,'case_identities':433,'method_invocations':1896,'skipped_invocations':1,'test_runs':26,'go_subscenarios':31}
assert out['selected_run_outcomes']=={'PASS':25,'FAIL':1} and not out['new_case_identities']
p=B/'authored-runtime14-sdk21-chart16-counts.json';p.write_bytes(canonical(out))
print(json.dumps({'path':str(p),'sha256':sha(p),'counts':out['combined_counts'],'outcomes':out['selected_run_outcomes'],'passing_subset':out['passing_run_subset'],'new':out['new_case_identities']},indent=2))
