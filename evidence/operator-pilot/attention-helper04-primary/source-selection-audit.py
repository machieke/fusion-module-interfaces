import ast,copy,hashlib,importlib.util,json,re
from pathlib import Path
B=Path('/data/fusion-operator-pilot-release/evidence-assembly');R=Path('/home/purplezky/work/takopi/fusion-module-interfaces')
def raw(p):return Path(p).read_bytes()
def sha(p):return hashlib.sha256(raw(p)).hexdigest()
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
snap=R/'artifacts/operator-pilot/attention-suspension-repair-source';manifest=json.loads(raw(snap/'manifest.json'))
for n,h in manifest.items():assert sha(snap/n)==h
name='tests/test_pilot_attention_suspension.py';source=raw(snap/name);tree=ast.parse(source)
assert not any(isinstance(x,(ast.FunctionDef,ast.AsyncFunctionDef)) and x.name=='load_tests' for x in tree.body)
assert not any(isinstance(x,ast.ImportFrom) and any(y.name=='*' for y in x.names) for x in tree.body)
classes=[]
for node in tree.body:
 if not isinstance(node,ast.ClassDef):continue
 if any(isinstance(x,ast.Attribute) and isinstance(x.value,ast.Name) and x.value.id=='unittest' and x.attr=='TestCase' for x in node.bases):
  assert len(node.bases)==1 and not node.decorator_list
  classes.append(node)
methods=[]
for node in classes:
 for fn in node.body:
  if isinstance(fn,(ast.FunctionDef,ast.AsyncFunctionDef)) and fn.name.startswith('test'):
   assert isinstance(fn,ast.FunctionDef) and not fn.decorator_list
   methods.append('tests.test_pilot_attention_suspension.'+node.name+'.'+fn.name)
assert len(methods)==len(set(methods))==15
primary=R/'artifacts/operator-pilot/attention-suspension-helper-04.log'
assert re.fullmatch(rb'\.{15}\n-+\nRan 15 tests in 0\.374s\n\nOK\n',raw(primary))
spec=importlib.util.spec_from_file_location('authored_audit',B/'audit_authored_methods.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
index={'files':{name:manifest[name]},'additional_live_generations':0};sources=m.Sources(index,snap,{})
cases={}
for identity in sorted(methods):
 row,reason=sources.resolve(identity);assert reason is None and not row['inherited']
 cases[row['case']]={**row,'raw_identities':[],'source_derived_selection_identities':[identity]}
defs={row['definition']:[case] for case,row in cases.items()}
report={'profile':'source-resolved-authored-test-definitions/1','status':'COMPLETE','classification':'STATIC_WHOLE_MODULE_SELECTION_WITH_AGGREGATE_PRIMARY','audit_source_sha256':sha(__file__),'sources':sources.sources,'counts':{'python_case_identities':15,'python_authored_definitions':15,'inherited_case_identities':0,'unresolved_raw_identities':0,'method_invocations':15,'skipped_invocations':0,'test_runs':1},'cases':cases,'definitions':defs,'unresolved':{},'runs':[{'id':'attention-suspension-helper04','sha256':sha(primary),'status':'PASS','invocations':15,'skips':0,'seconds':.374,'primary_format':'aggregate-unittest','command':'/data/fusion-operator-pilot-release/operator20/bin/python -m unittest tests.test_pilot_attention_suspension > artifacts/operator-pilot/attention-suspension-helper-04.log 2>&1','cwd':str(R),'selection_provenance':'Exact full-module invocation confirmed by executing agent; no method filters. Static module has exactly two direct unittest.TestCase classes, fifteen nondecorated test methods, no load_tests or imported TestCase classes. Reported total and fifteen success dots agree. Identities below are SOURCE_DERIVED, not verbose primary-log observations.'}],'source_snapshot':{'manifest_sha256':sha(snap/'manifest.json'),'timing':'Frozen after final test completion; executing agent supplied final helper/test pins and exact full-module command. No claim of before-test snapshot.'},'raw_log_rewritten':False,'verbose_log_fabricated':False,'verifier_limit':'This supplementary source-selection audit does not make the aggregate primary acceptable to the unchanged verbose-log parser. Preserve it as its own aggregate-method evidence; do not feed invented test lines to pilot_evidence.','runtime_contacts':0,'cluster_writes':0,'additional_live_generations':0}
dst=B/'authored-attention04';dst.mkdir(exist_ok=False);(dst/'report.json').write_bytes(canonical(report));(dst/'report.sha256').write_text(sha(dst/'report.json')+'\n')
prior=B/'authored-runtime14-sdk20-publication02-counts.json';old=json.loads(raw(prior));rows=copy.deepcopy(old['primary_audits']);rows.append({'path':str((dst/'report.json').relative_to(B)),'sha256':sha(dst/'report.json'),'counts':report['counts']})
cases={};definitions=set();before=set();inv=skips=runs=0
for number,row in enumerate(rows):
 p=B/row['path'];assert sha(p)==row['sha256'];v=json.loads(raw(p));assert v['status']=='COMPLETE'
 inv+=v['counts']['method_invocations'];skips+=v['counts']['skipped_invocations'];runs+=v['counts']['test_runs']
 for key,x in v['cases'].items():
  definitions.add(x['definition']);cases.setdefault(key,[]).append({'audit':row['path'],'source_sha256':x['source_sha256'],'definition_ast_sha256':x['definition_ast_sha256']})
  if number<len(rows)-1:before.add(key)
go=old['independent_go04'];out=copy.deepcopy(old)
out.update(prior_count_audit={'path':prior.name,'sha256':sha(prior)},primary_audits=rows,python_counts={'authored_definitions':len(definitions),'case_identities':len(cases),'method_invocations':inv,'skipped_invocations':skips,'test_runs':runs},combined_counts={'authored_definitions':len(definitions)+go['authored_definitions'],'case_identities':len(cases)+go['case_identities'],'method_invocations':inv+go['method_invocations'],'skipped_invocations':skips+go['skipped_invocations'],'test_runs':runs+go['test_runs'],'go_subscenarios':go['subscenarios']},new_case_identities=sorted(set(cases)-before),repeated_case_source_versions=[{'case':k,'versions':v} for k,v in sorted(cases.items()) if len({(x['source_sha256'],x['definition_ast_sha256']) for x in v})>1],increment_explanation='Append15 actual full-module Attention helper fixture invocations from aggregate primary04, with source-derived selection identities. Five new authored definitions/cases and ten repeated cases. No new native/provider/cluster PASS inferred.',attention_helper04={'primary_sha256':sha(primary),'source_manifest_sha256':sha(snap/'manifest.json'),'source_snapshot_timing':'After completion; final source pins supplied by executing agent','source_selection_audit_sha256':sha(dst/'report.json'),'method_invocations':15,'seconds':.374,'new_authored_definitions':5,'identity_provenance':'FULL_MODULE_COMMAND_PLUS_EXACT_STATIC_SOURCE; NOT_VERBOSE_LOG','fixture_classification':'Real SQLite and application-owned allocation/close; fixture authorization/template/CA/config/clocks/container observations. No real pause/provider/native integration in this run.','sqlite_observation_limit':'Authoritative DB/nonempty WAL/config equality; SHM and empty WAL lock/cache sidecars excluded. No full physical-filesystem equality claim.','sdk21_reconciliation':{'path':'evidence/operator-pilot/operator21-source-reconciliation.json','sha256':sha(R/'evidence/operator-pilot/operator21-source-reconciliation.json')},'additional_live_generations':0},attention_helper03_failure={'path':'artifacts/operator-pilot/attention-suspension-helper-03.log','sha256':sha(R/'artifacts/operator-pilot/attention-suspension-helper-03.log'),'status':'FAIL','method_invocations_observed':15,'failures':4,'seconds':.443,'source_version':'UNKNOWN_NOT_SAVED_BEFORE_CORRECTION','included_in_source_qualified_union':False,'reason':'Initial physical sidecar-equality assertions and invalid unknown-session UUID fixture failed; preserve primary without assigning final test source.'},status='COMPLETE')
assert out['combined_counts']=={'authored_definitions':419,'case_identities':425,'method_invocations':1872,'skipped_invocations':1,'test_runs':23,'go_subscenarios':31}
p=B/'authored-runtime14-sdk21-attention04-counts.json';p.write_bytes(canonical(out))
print(json.dumps({'audit':str(dst/'report.json'),'audit_sha256':sha(dst/'report.json'),'union':str(p),'union_sha256':sha(p),'counts':out['combined_counts'],'new_cases':out['new_case_identities']},indent=2))
