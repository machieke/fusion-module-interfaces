import argparse,json
from pathlib import Path
from fusion.contracts import canonical,digest,require
from integration.single_node.reference_ops import Operator
from examples.pilot_workflows import qualify as guarded
from examples.pilot_recipe_qualification import qualify as recipe
root=Path('/data/fusion-operator-pilot-release/qualification-private/workflows-14');packet=Path('/data/fusion-operator-pilot-release/distribution14')
require(digest((packet/'distribution.json').read_bytes())=='de39c9f69d8024a8fb793279165236953e2bc81254a79efae391fb468af0954d','CONFLICT')
p=argparse.ArgumentParser();p.add_argument('case',choices=['unchanged','withdrawn','irrelevant-change','unknown','unauthorized','evidence-review','archived-prerequisite']);a=p.parse_args()
plan=json.loads((root/'workflow-qualification-plan.json').read_bytes());row=next(x for x in plan['cases'] if x['id']==a.case);install=json.loads((root/'recipe-install-report.json').read_bytes());require(install['status']=='PASS' and install['installed_plan_sha256']==digest((root/'recipe-installed/plan.json').read_bytes()),'CONFLICT')
op=Operator(root/'kubeconfig','default',plan['namespace']);directory=root/'workflow-cases'/a.case
if row['entrypoint']=='examples.pilot_workflows.qualify':
 result=guarded(op,directory,row['variant'],maximum_seconds=row['maximum_seconds'],case=row['case'],checkpoint_restart=row.get('checkpoint_restart',False),archive_prerequisite=row.get('archive_prerequisite',False))
else:
 require(row['entrypoint']=='examples.pilot_recipe_qualification.qualify' and row['recipe']=='evidence-aware-review/1','UNSUPPORTED_PROFILE');result=recipe(op,directory,row['recipe'])
print(json.dumps(dict(status=result['status'],case=a.case,report_sha256=digest((directory/'report.json').read_bytes()),additional_live_generations=0)))
