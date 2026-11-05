# SANITIZED NONEXECUTED SOURCE COPY: deliberately wrong test credential redacted.
import importlib.util,json,shutil,subprocess,time
from pathlib import Path
from fusion.contracts import canonical,digest,require
from integration.single_node.reference_ops import Operator
root=Path('/data/fusion-operator-pilot-release/qualification-private/workflows-12');packet=Path('/data/fusion-operator-pilot-release/distribution12')
helper=packet/'examples/pilot_go_capacity.py';s=importlib.util.spec_from_file_location('capacity',helper);module=importlib.util.module_from_spec(s);s.loader.exec_module(module)
op=Operator(root/'kubeconfig','default','omega-ref-pilot-go12')
report=dict(status='RUNNING',source_sha256=digest(Path(__file__).read_bytes()),plan_sha256=digest((root/'go-capacity-plan.json').read_bytes()),observations={},additional_native_inputs=0,additional_live_generations=0)
def save():(root/'go-capacity-final.json').write_bytes(canonical(report))
def observe(name,auth):
 result=module.observe(op,root/'go-replacement/plan.json',packet/'go-provider/provider-image.json',packet/'deploy/helm/omega-fusion',auth,root/('go-capacity-'+name),int(time.time()*1000)+90000)
 report['observations'][name]=dict(report_sha256=digest((root/('go-capacity-'+name)/'report.json').read_bytes()),value=result['capacity']);save();return result['capacity']
save()
try:
 first=observe('completed',root/'go-capacity-authority');require(first['closure']['captured']==first['closure']['delivered']==1 and first['pending']['used']==0,'NOT_AVAILABLE')
 second=observe('repeated-read',root/'go-capacity-authority');require(first==second,'CONFLICT')
 wrong=root/'go-capacity-wrong-authority';wrong.mkdir(mode=0o700)
 for name in ('receipt.json','ca.crt'):shutil.copyfile(root/'go-capacity-authority'/name,wrong/name)
 (wrong/'credential').write_text('REDACTED_WRONG_TEST_CREDENTIAL');(wrong/'credential').chmod(0o600)
 try:observe('wrong-credential',wrong)
 except Exception:
  path=root/'go-capacity-wrong-credential';stderr=(path/'client.stderr').read_text();require(stderr.strip()=='UNAUTHORIZED','CONFLICT')
  primary=json.loads((path/'report.json').read_bytes());require(primary['client_invocations']==1 and primary['validated_owner_observations']==0 and primary['status']=='FAILED','CONFLICT')
  report['observations']['wrong-credential']=dict(expected='UNAUTHORIZED',actual_stderr=stderr,report_sha256=digest((path/'report.json').read_bytes()),status='EXPECTED_REFUSAL');save()
 else:require(False,'CONFLICT')
 cmd=['/data/fusion-operator-pilot-release/operator11/bin/python','-I',str(root/'drain_go.py'),'--kubeconfig',str(root/'kubeconfig'),'--plan',str(root/'go-final-drain-plan.json'),'--replacement',str(root/'go-replacement-evidence/native-onboarding'),'--output',str(root/'go-final-drain')]
 with (root/'go-final-drain.log').open('wb') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
 require(r.returncode==0,'NOT_AVAILABLE');report['drain_report_sha256']=digest((root/'go-final-drain/report.json').read_bytes());save()
 last=observe('drained',root/'go-capacity-authority');require(last==first,'CONFLICT')
 report.update(status='PASS',exact_repeated_read=True,exact_retained_after_registry_drain=True,logical_completion_space_observed=True,physical_capacity='UNKNOWN');save()
except BaseException as error:report.update(status='FAIL',failure=str(error)[-2000:]);save();raise
finally:
 before=op.quiesce();(root/'go-quiesce.json').write_bytes(canonical(before))
 report['quiesced']=True;report['cleanup_pods']=json.loads(op.k('get','pods','-o','json'))['items'];report['retained_pvcs']=len(json.loads(op.k('get','pvc','-o','json'))['items']);save()
print(json.dumps(dict(status=report['status'],quiesced=report['quiesced'],additional_live_generations=0)))
