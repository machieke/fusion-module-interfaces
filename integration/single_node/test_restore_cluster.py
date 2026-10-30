"""Real recorded workflow -> quiesced synthetic backup -> fenced clone.

No effect authority is restored. The only maintenance mutation is derived Search
rebuild from authenticated authoritative storage ports under operator control.
"""
import argparse,copy,json,hashlib,shutil,sys,time,traceback,yaml
from pathlib import Path
from .test_cluster import ROOT
from .test_workflow_cluster import Workflow,ROLES
from .reference_ops import Operator

def main():
 p=argparse.ArgumentParser();p.add_argument('--kubeconfig',required=True);p.add_argument('--context',default='default');p.add_argument('--prefix',required=True);p.add_argument('--output',required=True);p.add_argument('--values',required=True);p.add_argument('--resume-from');p.add_argument('--resume-restore');a=p.parse_args();assert a.prefix.startswith('omega-ref-')
 root=Path(a.output);root.mkdir(parents=True,exist_ok=False);a.chart=root/'chart';shutil.copytree(ROOT/'deploy/helm/omega-fusion',a.chart);a.image_tag='unused';a.observer_source=(ROOT/'integration/single_node/workflow_observe.py').read_text().replace('from .memory_observe import memory_observe','from integration.single_node.memory_observe import memory_observe')
 files={str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for folder in ('fusion','integration','deploy') for f in (ROOT/folder).rglob('*') if f.is_file() and '__pycache__' not in f.parts};(root/'source-manifest.json').write_text(json.dumps(files,indent=2)+'\n')
 if a.resume_from:
  previous=Path(a.resume_from);old=json.loads(previous.read_text());assert old['status']=='PASS' and old['workflow_pass'] is True and old['namespace'].startswith('omega-ref-')
  original=Workflow.__new__(Workflow);original.args=a;original.name=old['namespace'];original.case='correct';original.root=previous.parent;original.report=old;original.values=json.loads((previous.parent/'values.json').read_text());original.created_namespace_uid=Operator(a.kubeconfig,a.context,original.name).owned()['metadata']['uid']
 else:original=Workflow(a,'correct')
 clone=None;report=dict(status='RUNNING',live_generations=0,live_model='NOT_RUN',limitations=['quiesced synthetic reference state only','not atomic across owners','observation-only restored clone; no failover authority'])
 try:
  if not a.resume_from:original.run();original.invariants();original.finish()
  else:report['resumed_completed_workflow']=dict(path=str(Path(a.resume_from).resolve()),sha256=hashlib.sha256(Path(a.resume_from).read_bytes()).hexdigest(),no_new_setup_or_model_calls=True)
  assert original.report['status']=='PASS'
  source=Operator(a.kubeconfig,a.context,original.name)
  if a.resume_restore:
   previous=json.loads(Path(a.resume_restore).read_text());report['backup']=previous['backup'];report['restore']=previous['restore'];assert report['restore']['status']=='RESTORED_FENCED'
   clone=Operator(a.kubeconfig,a.context,report['restore']['namespace']);clone.owned();assert all(x['spec']['replicas']==0 for x in source.workloads())
  else:
   manifest=source.backup(root/'backup');report['backup']=manifest
   clone=Operator(a.kubeconfig,a.context,a.prefix+'-restored');clone.create();report['restore']=clone.restore(root/'backup')
   clone.command([sys.executable,str(ROOT/'deploy/single-node/create_secrets.py'),'--workflow','--kubeconfig',a.kubeconfig,'--namespace',clone.namespace,'--directory',str((root/'restored-private-secrets').resolve())])
  values=copy.deepcopy(original.values);values['networkPolicy']=dict(enabled=True);values['components']['omega-agent'].setdefault('config',{})['nativeEnabled']=False
  # Explicit compatible maintenance release; the backup still records the
  # original per-owner images. Never start an old image lacking the fence.
  selected=yaml.safe_load(Path(a.values).read_text());values['image']=selected['image']
  for role,component in selected['components'].items():
   if 'image' in component:values['components'].setdefault(role,{})['image']=component['image']
  file=root/'restored-values.json';file.write_text(json.dumps(values));clone.command(['helm','upgrade','--install','omega',str(a.chart.resolve()),'--kubeconfig',a.kubeconfig,'--kube-context',a.context,'--namespace',clone.namespace,'-f',str(file.resolve())])
  clone.k('rollout','status','statefulset/fusion-storage','--timeout=90s');clone.k('rollout','status','statefulset/fusion-search','--timeout=90s');clone.k('rollout','status','statefulset/omega-agent','--timeout=90s')
  def execute(role,code):
   # This operator-only probe uses the recorded source manifest, never a foreign journal.
   if 'integration.single_node.restore_probe' in code:
    code=code.replace('from integration.single_node.restore_probe import query;', '').replace('from integration.single_node.restore_probe import rebuild;', '')
    code=(ROOT/'integration/single_node/restore_probe.py').read_text()+'\n'+code
   return clone.k('exec',role+'-0','--','/opt/native/python/bin/python3.12','-c',code)
  report['readback']=json.loads(execute('omega-agent','from integration.single_node.restore_probe import query;import json;print(json.dumps(query()))'))
  expected={r['content'] for r in original.report['observations']['final']['omega-agent']['setup-view.json']['records']}
  assert {json.loads(x)['content'] for x in report['readback']['payloads']}==expected
  # Actual fenced HTTPS rejections. None of these requests can enter an owner.
  negatives="""import http.client,ssl,json
from pathlib import Path
cfg=json.loads(Path('/config/component.json').read_text());out={};ctx=ssl.create_default_context(cafile='/secrets/ca.crt')
for role,path,op in [('fusion-model','/s07-model','complete'),('fusion-messaging','/s06-mailbox','send'),('fusion-storage','/s03-append','create'),('fusion-search','/s03-append','build')]:
 c=http.client.HTTPSConnection(role+'.NAMESPACE.svc.cluster.local',8443,context=ctx,timeout=2);c.request('POST',path,json.dumps(dict(operation=op)),{'Content-Type':'application/json','Authorization':'Bearer invalid-authority'});r=c.getresponse();v=json.loads(r.read());assert v['error']['code']=='UNAUTHORIZED';out[role]=v['error']['code'];c.close()
print(json.dumps(out))""".replace('NAMESPACE',clone.namespace)
  report['effect_refusals']=json.loads(execute('omega-agent',negatives))
  before={r:json.loads(execute(r,a.observer_source)) for r in ('omega-agent','fusion-model','fusion-channel-bridge')}
  execute('fusion-search',"import json,shutil;from pathlib import Path;c=json.loads(Path('/run/fusion/owner.json').read_text());p=Path(c['memory_read']['root'])/'search';assert p.is_relative_to('/state');shutil.rmtree(p)")
  clone.k('delete','pod','fusion-search-0','--grace-period=1','--wait=true');clone.k('rollout','status','statefulset/fusion-search','--timeout=60s')
  missing=execute('omega-agent',"from integration.single_node.restore_probe import query;from fusion.contracts import ContractError\ntry:query();raise AssertionError('missing view silently followed latest')\nexcept ContractError as e:assert e.code=='NOT_AVAILABLE';print(e.code)")
  report['missing_old_view']=missing.strip();snapshot=json.loads(execute('fusion-search','from integration.single_node.restore_probe import rebuild;import json;print(json.dumps(rebuild()))'))
  report['rebuilt_readback']=json.loads(execute('omega-agent','from integration.single_node.restore_probe import query;import json;print(json.dumps(query('+repr(snapshot)+')))'))
  assert {json.loads(x)['content'] for x in report['rebuilt_readback']['payloads']}==expected and snapshot['head']==report['readback']['snapshot']['head'] and snapshot['generation']!=report['readback']['snapshot']['generation']
  after={r:json.loads(execute(r,a.observer_source)) for r in before}
  for role,db in (('omega-agent','measured.sqlite'),('fusion-model','model.sqlite'),('fusion-channel-bridge','bridge.sqlite')):assert before[role][db]==after[role][db]
  report.update(status='PASS_BOUNDED_FENCED',preserved_captures_and_spent_accounting=True,new_authority=False,application_old_views_unchanged=True,original_remains_quiesced=True)
 except Exception as e:report.update(status='FAIL',failure=str(e),traceback=traceback.format_exc())
 finally:
  for test in (original,):
   for role in ROLES:
    try:(root/(role+'.log')).write_text(test.k('logs',role+'-0'))
    except Exception:pass
  (root/'report.json').write_text(json.dumps(report,indent=2)+'\n')
 print(report['status'],report.get('failure',''));raise SystemExit(report['status']!='PASS_BOUNDED_FENCED')
if __name__=='__main__':main()
