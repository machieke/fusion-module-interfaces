import copy,hashlib,importlib.util,json
from pathlib import Path
B=Path('/data/fusion-operator-pilot-release/evidence-assembly');R=Path('/home/purplezky/work/takopi/fusion-module-interfaces')
def raw(p):return Path(p).read_bytes()
def sha(p):return hashlib.sha256(raw(p)).hexdigest()
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
snap=R/'artifacts/operator-pilot/fault-retirement22-source';report=R/'evidence/operator-pilot/fault-retirement22-tests.json';log=R/'artifacts/operator-pilot/fault-retirement22.log';primary=json.loads(raw(report));assert sha(log)==primary['test_log_sha256'] and sha(snap/'manifest.json')==primary['source_snapshot_sha256']
manifest=json.loads(raw(snap/'manifest.json'))
for name,pin in manifest.items():assert sha(snap/name)==pin
spec=importlib.util.spec_from_file_location('authored_audit',B/'audit_authored_methods.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
d=B/'retirement22-index';d.mkdir(exist_ok=False);index={'files':{n:p for n,p in manifest.items() if n.startswith('tests/')},'additional_live_generations':0};(d/'index.json').write_bytes(canonical(index))
new=B/'authored-retirement22';m.audit(d/'index.json',snap,[('fault-retirement22',log)],new)
prior=B/'authored-runtime14-sdk21-chart16-counts.json';old=json.loads(raw(prior));rows=copy.deepcopy(old['primary_audits']);newreport=new/'report.json';v=json.loads(raw(newreport));rows.append({'path':str(newreport.relative_to(B)),'sha256':sha(newreport),'counts':v['counts']})
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
out.update(prior_count_audit={'path':prior.name,'sha256':sha(prior)},primary_audits=rows,python_counts={'authored_definitions':len(definitions),'case_identities':len(cases),'method_invocations':inv,'skipped_invocations':skips,'test_runs':runs},combined_counts={'authored_definitions':len(definitions)+go['authored_definitions'],'case_identities':len(cases)+go['case_identities'],'method_invocations':inv+go['method_invocations'],'skipped_invocations':skips+go['skipped_invocations'],'test_runs':runs+go['test_runs'],'go_subscenarios':go['subscenarios']},new_case_identities=sorted(set(cases)-before),repeated_case_source_versions=[{'case':k,'versions':v} for k,v in sorted(cases.items()) if len({(x['source_sha256'],x['definition_ast_sha256']) for x in v})>1],increment_explanation='Append exact-source retirement22 successful19-method run:19 invocations,1 PASS run,1 new method/case identity. Eighteen other executions retain existing identities; native/deployed failures are separate from unit-test methods.',selected_run_outcomes={**run_outcomes,'PASS':run_outcomes['PASS']+go['test_runs']},passing_run_subset={'authored_definitions':len(passing_definitions)+go['authored_definitions'],'case_identities':len(passing_cases)+go['case_identities'],'method_invocations':passing_inv+go['method_invocations'],'test_runs':passing_runs+go['test_runs'],'meaning':'All-PASS audit groups plus independentGo04; known-source chart01 failure remains in full executed union.'},cases_never_observed_in_a_passing_selected_run=sorted(set(cases)-passing_cases),retirement22={'public_report_sha256':sha(report),'primary_sha256':sha(log),'source_manifest_sha256':sha(snap/'manifest.json'),'audit_sha256':sha(newreport),'method_invocations':19,'seconds':3.004,'status':'PASS','source_snapshot_timing':primary['snapshot_timing'],'source_change':'Operator-only disarm preserves required config.test as explicit empty object rather than deleting it. Runtime14 and chart16 unchanged.','classification':primary['boundaries'],'old_helper_sha256':primary['old_helper_sha256'],'new_helper_sha256':primary['new_helper_sha256'],'sdk22_manifest_sha256':'636546e82026764efa7ed56c8c847ba27ea0861c467120e4b6fe162e7b61ec87','prior_sdk21_manifest_sha256':'a5b5c39e3eb4c4f269be11606daa1a11dcf1ab8e45917fac58dc226b05ee4278','actual_F16':'FAIL_RETAINED_DISTINCT_FROM_REPAIR_TESTS','fresh_F17':'PENDING_AT_AUDIT','additional_live_generations':0},status='COMPLETE')
out['selection_delta']={'new_method_identities':1,'new_authored_definitions':1,'new_invocations':19,'new_pass_runs':1,'new_identity':'tests/test_pilot_operator_package.py::QualifierObservers.test_fault_retirement_keeps_required_empty_selection_and_owner_state','repeated_method_invocations':18,'runtime_code_changes':0,'chart_changes':0}
assert out['combined_counts']=={'authored_definitions':428,'case_identities':434,'method_invocations':1915,'skipped_invocations':1,'test_runs':27,'go_subscenarios':31}
assert out['selected_run_outcomes']=={'PASS':26,'FAIL':1} and out['new_case_identities']==[out['selection_delta']['new_identity']]
p=B/'authored-runtime14-sdk22-chart16-counts.json';p.write_bytes(canonical(out));print(json.dumps({'path':str(p),'sha256':sha(p),'counts':out['combined_counts'],'outcomes':out['selected_run_outcomes'],'new':out['new_case_identities']},indent=2))
