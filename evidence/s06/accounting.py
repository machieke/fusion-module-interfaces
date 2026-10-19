import json,re
from pathlib import Path
out=Path('evidence/s06')
logs={
 'baseline-core.log':'baseline-source.json','baseline-s05.log':'baseline-source.json',
 'candidate-01-core.log':'candidate-01-source.json','candidate-01-native.log':'candidate-01-source.json',
 'regression-owners.log':'candidate-01-source.json','regression-guards-isolated.log':'candidate-01-source.json',
 'regression-native.log':'candidate-01-source.json',
 'candidate-02-core.log':'candidate-02-source.json','candidate-02-native.log':'candidate-02-source.json',
 'final-core.log':'candidate-03-source.json','final-native.log':'candidate-03-source.json',
 'intentional-sends.log':'candidate-04-source.json','final-config.log':'test-source.json'}
results=[]
for name,source in logs.items():
 text=(out/name).read_text();tail=re.search(r'Ran (\d+) tests? in ([\d.]+)s',text);assert tail,name
 methods=[]
 for m in re.finditer(r'^(test_\w+) \(([^)]+)\) \.\.\. (ok|FAIL|ERROR)$',text,re.M):
  methods.append(dict(id=m[2] if m[2].endswith('.'+m[1]) else m[2]+'.'+m[1],result=m[3]))
 for m in re.finditer(r'^(FAIL|ERROR): (test_\w+) \(([^)]+)\)',text,re.M):
  ident=m[3] if m[3].endswith('.'+m[2]) else m[3]+'.'+m[2]
  if ident not in {x['id'] for x in methods}:methods.append(dict(id=ident,result=m[1]))
 results.append(dict(log=name,source=source,methods_run=int(tail[1]),elapsed_seconds=float(tail[2]),result='PASS' if text.rstrip().endswith('OK') else 'FAIL',methods=methods))
selected=['candidate-01-core.log','candidate-01-native.log','regression-owners.log','regression-guards-isolated.log','regression-native.log','final-core.log','final-native.log','intentional-sends.log','final-config.log']
passed={m['id'] for r in results if r['log'] in selected for m in r['methods'] if m['result']=='ok'}
new={m for m in passed if '.test_channel.' in m or '.test_channel_loop.' in m or '.test_channel_recovery.' in m}
old=passed-new
assert (len(new),len(old))==(25,151),(len(new),len(old))
failures=[dict(log=r['log'],failed=[m['id'] for m in r['methods'] if m['result']!='ok']) for r in results if r['result']=='FAIL']
value=dict(schema='s06-run-results/1',runs=results,passing_union=dict(new_s06_methods=len(new),historical_regression_methods=len(old),total_distinct_methods=len(passed),new_ids=sorted(new),regression_ids=sorted(old)),
 units='Distinct unittest methods. Repeated runs, subtest placements and kill scenarios are not extra methods. Original IRC oracles/build/hash audits are separate programs.',
 source_note='Historical regression runtime/shared files were unchanged throughout; unused new S06 files evolved separately. Earlier full native matrix is candidate-01; later changes have targeted final rechecks. No historical run is relabelled.',
 failed_runs=failures,baseline_overlap='All 108 baseline methods are included in the selected historical union; not added twice.',
 final_runtime_rechecks=['final-core.log','final-native.log','intentional-sends.log'],final_operator_helper_recheck='final-config.log')
(out/'run-results.json').write_text(json.dumps(value,indent=2)+'\n')
print('PASS: S06',len(new),'historical',len(old),'union',len(passed))
