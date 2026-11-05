#!/usr/bin/env python3
"""Task-local, disabled-by-plan H installation observer using shipped CLIs only."""
import argparse,datetime,hashlib,ipaddress,json,os,re,signal,subprocess,sys,tarfile,time,urllib.parse
from pathlib import Path,PurePosixPath
NS='omega-ref-pilot-adopter19';SCOPE='synthetic-pilot-adopter19';OWNER='omega-asi-single-node-reference-1'
SOURCE='437927520d53825dc9c642df6cc074d6ccccb3ccaec4bd937402e319baacd6fc'
SDK='f902477c74ed25c5753d5903fa3c9071c6a6820172c3cc6cc8bb8ef2fd27ee90'
WHEEL='93350732cbc3294f16e2f8c9d787836dd4503c1ddad5a4cb0448493cde6fc4e9'
ROLES={'omega-agent','omega-agent-b','fusion-execution','fusion-storage','fusion-messaging','fusion-model','fusion-embedding','fusion-search','fusion-episodes','fusion-beliefs','fusion-attention','fusion-relations'}
TOOLS={'/usr/bin/bwrap':'/usr/bin/bwrap','/snap/helm/555/helm':'/tools/helm','/usr/local/bin/k3s':'/tools/kubectl','/usr/bin/openssl':'/tools/openssl'}
def check(ok,why):
 if not ok:raise RuntimeError(why)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def load(p):return json.loads(Path(p).read_bytes())
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def save(p,value,exclusive=True):
 with Path(p).open('xb' if exclusive else 'wb') as out:out.write(canonical(value))
def digest(value):return bool(isinstance(value,str) and re.fullmatch('[0-9a-f]{64}',value))
def validate_plan(p,execute):
 check(execute and p.get('enabled') is True,'H namespace recipe disabled')
 check(p['profile']=='task-local-final-H-namespace-install/1' and p['namespace']==NS and p['scope']==SCOPE,'scope/profile drift')
 check(p['maximum_programme_seconds']==1800 and p['cleanup_reserved_seconds']==300,'original bound drift')
 for field in ('distribution_sha256','chart_archive_sha256','clean_install_PASS_report_sha256','clean_install_launcher_sha256','driver_sha256','selected_kubeconfig_sha256','release_record_sha256','clean_install_driver_sha256','clean_install_executed_plan_sha256'):check(digest(p.get(field)),'unfrozen '+field)
 check(bool(re.fullmatch('[0-9a-f]{40}',p.get('implementation_commit') or '')),'implementation commit missing')
 check(p.get('selected_node_uid') and p.get('selected_node_name') and p['context']=='default','cluster identity missing')
 check(p.get('protected_namespaces')==['omega-demo'],'protected observation scope drift')
 check(p['runtime_source_manifest_sha256']==SOURCE and p['operator_build_manifest_sha256']==SDK and p['operator_wheel_sha256']==WHEEL,'artifact epoch drift')
 check(all(p[k]==0 for k in ('new_native_allocations','new_native_submissions','model_reservations','provider_admission_or_probe_calls','additional_live_generations')),'work authorization refused')
 check(not any(p[k] for k in ('generative_runtime_contact','chain','optional_go','optional_browser_gateway','broad_host_etc_mount')),'placement drift')
 check(p['os_configuration_mounts'][0]['source']=='/etc/ssl/openssl.cnf' and len(p['os_configuration_mounts'])==1,'OS config selection drift')
 check(p['driver_output_subdirectory']=='h19-namespace' and p['expected_owner_workloads']==p['expected_owner_PVCs_retained']==12,'output/owner drift')
 return p

def validate_clean(p,work):
 report=work/'clean-install-report.json';launch=work/'launcher.json'
 check(sha(report)==p['clean_install_PASS_report_sha256'] and sha(launch)==p['clean_install_launcher_sha256'],'clean-install report drift')
 r=load(report);l=load(launch)
 check(r['status']==l['status']=='PASS' and l['exit_code']==0,'clean installation did not pass')
 check(r['distribution_manifest_sha256']==p['distribution_sha256'] and r['tested_runtime_source_manifest_sha256']==SOURCE and r['sdk_build_manifest_sha256']==SDK,'clean-install artifact mismatch')
 check(r['new_native_allocations']==r['additional_live_generations']==r['cluster_operations']==0 and r['generative_runtime_contact'] is False,'clean-install counter mismatch')
 check(r['artifact_verification']['status']=='OFFLINE_VERIFIED','clean artifact verifier missing')
 check(l['script_sha256']==p['clean_install_driver_sha256'] and l['plan_sha256']==p['clean_install_executed_plan_sha256'],'clean launcher source/plan mismatch')
 return dict(report_sha256=sha(report),launcher_sha256=sha(launch))

def extract_chart(packet,manifest,target,expected):
 name=manifest['chart'];check(isinstance(name,str) and '/' not in name and name.endswith('.tgz'),'chart path refused')
 entry=next((x for x in manifest['files']if x['path']==name),None);check(entry and entry['sha256']==expected==sha(packet/name),'chart archive drift')
 check(not target.exists(),'chart output exists');target.mkdir(mode=0o700)
 with tarfile.open(packet/name,'r:gz') as archive:
  members=archive.getmembers();check(1<=len(members)<=64 and sum(x.size for x in members)<=2*1024*1024,'chart archive bound')
  names=set()
  for m in members:
   parts=PurePosixPath(m.name).parts
   check(parts and parts[0]=='omega-fusion' and not PurePosixPath(m.name).is_absolute() and '..' not in parts,'chart escaping path')
   check(m.name not in names and (m.isdir() or m.isfile()),'chart duplicate/link/special entry');names.add(m.name)
   q=target.joinpath(*parts)
   if m.isdir():q.mkdir(parents=True,exist_ok=True)
   else:
    q.parent.mkdir(parents=True,exist_ok=True)
    with q.open('xb') as out:out.write(archive.extractfile(m).read())
 check((target/'omega-fusion/Chart.yaml').is_file(),'chart missing metadata')
 return target/'omega-fusion'

def capacity_zero(value):
 check(type(value) is dict,'malformed capacity')
 for field in ('retained','active','pending','completion_reserved_bytes'):check(type(value.get(field)) is int and value[field]==0,'unexpected nonzero '+field)
 check(value.get('no_effect_budget_refunds') is True,'capacity accounting flag absent')
 return {k:value[k]for k in ('retained','active','pending','completion_reserved_bytes')}

def resource_selection(value):
 return sorted([dict(kind=x['kind'],name=x['metadata']['name'],uid=x['metadata']['uid'],replicas=x.get('spec',{}).get('replicas'),volume=x.get('spec',{}).get('volumeName'),images=[c['image']for c in x.get('spec',{}).get('template',{}).get('spec',{}).get('containers',[])])for x in value['items']],key=lambda x:(x['kind'],x['name']))

def resource_checks(value,pins,ready):
 items=value['items'];sts={x['metadata']['name']:x for x in items if x['kind']=='StatefulSet'};pods=[x for x in items if x['kind']=='Pod'];pvcs=[x for x in items if x['kind']=='PersistentVolumeClaim'];deploy=[x for x in items if x['kind']=='Deployment']
 check(set(sts)==ROLES and not deploy,'unexpected owner workload set')
 for role,row in sts.items():
  check(row['spec']['persistentVolumeClaimRetentionPolicy']=={'whenDeleted':'Retain','whenScaled':'Retain'},'PVC retention policy drift')
  check(row['spec']['template']['spec']['containers'][0]['image']==pins[role],'StatefulSet image drift')
 if ready:
  check(len(pods)==12 and {p['metadata']['name']for p in pods}=={x+'-0'for x in ROLES},'pod cardinality')
  for pod in pods:
   role=pod['metadata']['name'][:-2];statuses=pod['status'].get('containerStatuses',[])
   check(len(statuses)==1 and statuses[0].get('ready') and statuses[0]['imageID'].endswith(pins[role].split('@')[1]),'actual pod image/readiness mismatch')
   check(pod['spec']['containers'][0]['image']==pins[role],'pod requested image mismatch')
 else:check(not pods and all(x['spec']['replicas']==0 for x in sts.values()),'writers remain')
 check(len(pvcs)==12 and {x['metadata']['name']for x in pvcs}=={'state-'+x+'-0'for x in ROLES},'retained PVC set mismatch')
 return {'pods':len(pods),'pvcs':{x['metadata']['name']:x['metadata']['uid']for x in pvcs},'statefulsets':len(sts)}

class Interrupted(Exception):pass

def inside():
 p=validate_plan(load('/plan.json'),True);check(sha('/entry.py')==p['driver_sha256'],'driver drift')
 root=Path('/work/h19-namespace');packet=Path('/packet');started=float(os.environ['H19_START_MONOTONIC']);end=started+1800;work_end=end-300
 report=dict(profile='task-local-final-H-namespace-observation/1',status='FAIL',namespace=NS,implementation_commit=p['implementation_commit'],distribution_manifest_sha256=p['distribution_sha256'],runtime_source_manifest_sha256=SOURCE,operator_wheel_sha256=WHEEL,started_utc=os.environ['H19_START_UTC'],started_monotonic=started,original_end_monotonic=end,cleanup_reserved_seconds=300,commands=[],new_native_allocations=0,new_native_submissions=0,model_reservations=0,additional_live_generations=0,generative_runtime_contact=False,physical_HTTP_attempts='NOT_INSTRUMENTED',protected_observation_fields=['kind','name','uid','replicas','volumeName','workload_images'],protected_host_campaign_files='NOT_MOUNTED_NOT_CONTENT_AUDITED',classification='SAME_HOST_ARTIFACT_STARTUP_AND_READ_ONLY_OBSERVATION_NOT_A_NATIVE_WALKTHROUGH')
 def checkpoint():save(root/'progress.json',report,False)
 def run(label,args,seconds=60,cleanup=False,as_json=True):
  remaining=(end if cleanup else work_end)-time.monotonic();check(remaining>0,'original observation/cleanup bound expired')
  row=dict(step=label,args=args,started_utc=utc(),started_monotonic=time.monotonic(),timeout_seconds=min(seconds,remaining));report['commands'].append(row);checkpoint()
  out=root/(str(len(report['commands'])).zfill(3)+'-'+label+'.stdout');err=out.with_suffix('.stderr');proc=None
  try:
   with out.open('xb')as stdout,err.open('xb')as stderr:
    proc=subprocess.Popen(args,stdout=stdout,stderr=stderr,start_new_session=True,cwd=root)
    row['spawned_pid']=proc.pid;checkpoint()
    try:code=proc.wait(timeout=row['timeout_seconds'])
    except BaseException:
     # Only this invocation's new process group; no command-line process scan.
     try:os.killpg(proc.pid,signal.SIGTERM)
     except ProcessLookupError:pass
     try:proc.wait(timeout=min(2,max(.1,end-time.monotonic())))
     except subprocess.TimeoutExpired:
      try:os.killpg(proc.pid,signal.SIGKILL)
      except ProcessLookupError:pass
      proc.wait(timeout=2)
     raise
   row['exit_code']=code;check(code==0,label+' failed')
   raw=out.read_bytes();return json.loads(raw) if as_json else raw.decode()
  except BaseException as exc:
   row['failure']=dict(type=type(exc).__name__,message=str(exc)[:800]);raise
  finally:
   row.update(finished_utc=utc(),finished_monotonic=time.monotonic(),stdout=out.name,stderr=err.name,stdout_sha256=sha(out)if out.exists()else None,stderr_sha256=sha(err)if err.exists()else None);checkpoint()
 def cli(label,*args,**kw):return run(label,['/work/operator/bin/fusion-pilot',*args],**kw)
 def kube(label,*args,**kw):return run(label,['/tools/kubectl','--kubeconfig','/credentials/kubeconfig','--context','default',*args],**kw)
 def service(label,action,*args,**kw):return cli(label,'services','--kubeconfig','/credentials/kubeconfig','--context','default','--namespace',NS,action,*args,**kw)
 signal.signal(signal.SIGTERM,lambda *_:(_ for _ in ()).throw(Interrupted('termination requested')))
 attempted=False;ns_uid=None;before=None;pins=None;protected=None;main_ok=False
 try:
  check(sha(packet/'distribution.json')==p['distribution_sha256'],'manifest drift');manifest=load(packet/'distribution.json')
  check(hashlib.sha256(canonical(manifest['tested_source'])).hexdigest()==SOURCE,'runtime source drift');check(sha(packet/'wheelhouse/build-manifest.json')==SDK,'SDK drift');validate_clean(p,Path('/work'))
  build=load(packet/'wheelhouse/build-manifest.json');site=Path('/work/operator/lib/python3.12/site-packages');installed_sources={}
  for kind in ('operator','client','provider'):
   for name,row in build[kind]['sources'].items():
    selected=(site/name).resolve();check(selected.is_relative_to(site) and selected.stat().st_size==row['bytes'] and sha(selected)==row['sha256'],'installed source drift '+name)
   installed_sources[kind]=len(build[kind]['sources'])
  report['installed_sources_rechecked']=installed_sources
  check(sha('/credentials/kubeconfig')==p['selected_kubeconfig_sha256'],'mounted kubeconfig drift')
  for original,target in TOOLS.items():check(sha(target)==p['tools'][original],'tool drift')
  check(sha('/etc/ssl/openssl.cnf')==p['os_configuration_mounts'][0]['sha256'],'OpenSSL config drift');check(not any(x.strip().startswith('.include')for x in Path('/etc/ssl/openssl.cnf').read_text().splitlines()),'OpenSSL external include refused')
  import yaml
  cfg=yaml.safe_load(Path('/credentials/kubeconfig').read_bytes());context=next(x['context']for x in cfg['contexts']if x['name']=='default');cluster=next(x['cluster']for x in cfg['clusters']if x['name']==context['cluster']);user=next(x['user']for x in cfg['users']if x['name']==context['user']);url=urllib.parse.urlsplit(cluster['server']);check(url.scheme=='https','cluster scheme');ipaddress.ip_address(url.hostname);check(cluster.get('certificate-authority-data') and not cluster.get('certificate-authority'),'CA not embedded');check(not any(k in user for k in ('exec','auth-provider','client-certificate','client-key','tokenFile')),'external auth refused')
  checked=cli('verify-artifacts','verify-artifacts','/packet/distribution.json',seconds=900);check(checked['status']=='OFFLINE_VERIFIED','artifact verifier did not pass');report['artifact_verification']='OFFLINE_VERIFIED'
  chart=extract_chart(packet,manifest,root/'chart',p['chart_archive_sha256'])
  source_chart=packet/'deploy/helm/omega-fusion';files={str(x.relative_to(source_chart)):sha(x)for x in source_chart.rglob('*')if x.is_file()};check(hashlib.sha256(canonical(files)).hexdigest()==p['chart16_source_sha256'],'source chart drift')
  actual={str(x.relative_to(chart)):sha(x)for x in chart.rglob('*')if x.is_file()};check(actual.keys()==files.keys(),'packaged chart file set differs')
  for name in actual:
   check((yaml.safe_load((chart/name).read_text())==yaml.safe_load((source_chart/name).read_text())) if name=='Chart.yaml' else actual[name]==files[name],'packaged chart mismatch '+name)
  values=root/'values.yaml';placement=root/'placement.json';cli('values','values','--images','/packet/images.json','--scope',SCOPE,'--namespace',NS,'--output',str(values),as_json=False)
  value=yaml.safe_load(values.read_bytes());check(value['preview']['model_boundary']=='RECORDED_FIXTURE','model boundary');check(not value.get('pilotWorkbench',{}).get('enabled') and not value['preview'].get('chain',{}).get('enabled'),'optional workload refused');check(all(not v.get('config',{}).get('test')for v in value['components'].values()),'test hook armed')
  cli('freeze-placement','placement','freeze','--chart',str(chart),'--images','/packet/images.json','--values',str(values),'--namespace',NS,'--output',str(placement),as_json=False)
  frozen=load(placement);check(set(frozen['graph']['nodes'])==ROLES,'unexpected selected role');pins={k:v['image']for k,v in frozen['graph']['nodes'].items()};report['private_placement_sha256']=sha(placement);checkpoint()
  check(kube('namespace-absent','get','namespace',NS,'--ignore-not-found','-o','json',as_json=False).strip()=='','namespace already exists')
  node=service('preflight','preflight');check(node['node_uid']==p['selected_node_uid'] and node['node']==p['selected_node_name'] and node['context']=='default','node/context mismatch')
  protected=kube('protected-before','-n','omega-demo','get','statefulsets,deployments,pvc','-o','json');report['protected_before']=resource_selection(protected)
  attempted=True;report['install_attempted_utc']=utc();checkpoint()
  service('install','install','--chart',str(chart),'--values',str(values),'--directory',str(root/'private-secrets'),seconds=340,as_json=False)
  ns=kube('namespace-owned','get','namespace',NS,'-o','json');check(ns['metadata'].get('labels',{}).get('omega.reference/owner')==OWNER,'namespace not owned');ns_uid=ns['metadata']['uid'];report['namespace_uid']=ns_uid
  installed=cli('verify-installed','placement','verify-installed','--plan',str(placement),'--kubeconfig','/credentials/kubeconfig','--context','default','--namespace',NS,seconds=300);check(installed['status']=='PASS' and len(installed['providers'])==12 and installed['business_calls']==0,'installed verification failed');report['installed_verification']='PASS'
  report['agent_reads']={}
  for role in ('omega-agent','omega-agent-b'):
   value=cli(role+'-list','services','--kubeconfig','/credentials/kubeconfig','--context','default','--namespace',NS,'--agent',role,'list');check(value==[],'sessions unexpectedly present')
   value=cli(role+'-capacity','services','--kubeconfig','/credentials/kubeconfig','--context','default','--namespace',NS,'--agent',role,'capacity');report['agent_reads'][role]=dict(list_empty=True,capacity=capacity_zero(value))
  resources=kube('ready-resources','-n',NS,'get','pods,pvc,statefulsets,deployments','-o','json');before=resource_checks(resources,pins,True);report['ready_resources']=before
  preview=dict(executed=False,command=['helm','--kubeconfig','/credentials/kubeconfig','--kube-context','default','-n',NS,'uninstall','omega'],retained_pvcs=before['pvcs'],retention='whenDeleted=Retain,whenScaled=Retain',namespace_deleted=False);save(root/'uninstall-preview.json',preview);main_ok=True
 except BaseException as exc:report['primary_failure']=dict(type=type(exc).__name__,message=str(exc)[:1000]);checkpoint()
 finally:
  # Cleanup is a separate result. A primary failure is never overwritten.
  signal.signal(signal.SIGTERM,signal.SIG_IGN);report['cleanup']={'status':'NOT_ATTEMPTED'}
  try:
   if attempted:
    ns=kube('cleanup-namespace','get','namespace',NS,'--ignore-not-found','-o','json',cleanup=True,as_json=False)
    if not ns.strip():report['cleanup']=dict(status='PASS',namespace_absent=True,pods=0,pvcs_retained=0)
    else:
     ns=json.loads(ns);meta=ns['metadata'];check(meta.get('labels',{}).get('omega.reference/owner')==OWNER,'cleanup namespace ownership unproven')
     if ns_uid:check(meta['uid']==ns_uid,'namespace UID changed')
     else:
      # Exact absent namespace, serialized install attempt, fresh creation + owner label.
      check(datetime.datetime.fromisoformat(meta['creationTimestamp'].replace('Z','+00:00')).timestamp()>=int(datetime.datetime.fromisoformat(report['install_attempted_utc']).timestamp()),'namespace predates this install')
      ns_uid=meta['uid'];report['namespace_uid']=ns_uid
     current=kube('cleanup-workloads','-n',NS,'get','statefulsets','-o','json',cleanup=True)
     if current['items']:service('stop','stop',seconds=130,cleanup=True)
     final=kube('final-resources','-n',NS,'get','pods,pvc,statefulsets,deployments','-o','json',cleanup=True)
     check(not [x for x in final['items']if x['kind']=='Pod'],'cleanup leaves pods')
     pvcs={x['metadata']['name']:x['metadata']['uid']for x in final['items']if x['kind']=='PersistentVolumeClaim'}
     if before:check(pvcs==before['pvcs'],'PVC identity changed');resource_checks(final,pins,False)
     report['cleanup']=dict(status='PASS',pods=0,pvcs_retained=len(pvcs),pvc_identities=pvcs,namespace_uid=ns_uid,partial_install=not main_ok)
   else:report['cleanup']=dict(status='NOT_NEEDED_NO_INSTALL_ATTEMPT',cluster_mutations=0)
  except BaseException as exc:
   report['cleanup']=dict(status='FAIL',failure=dict(type=type(exc).__name__,message=str(exc)[:800]))
   # One explicit independent final observation; not a repeated stop or retry.
   try:
    final=kube('failed-stop-final-observation','-n',NS,'get','pods,pvc,statefulsets,deployments','-o','json',seconds=25,cleanup=True)
    report['cleanup']['final_observed_pods']=len([x for x in final['items']if x['kind']=='Pod']);report['cleanup']['final_observed_pvcs']=len([x for x in final['items']if x['kind']=='PersistentVolumeClaim'])
   except BaseException as observation:report['cleanup']['final_observation_failure']=dict(type=type(observation).__name__,message=str(observation)[:500])
  if protected is not None:
   try:
    after=kube('protected-after','-n','omega-demo','get','statefulsets,deployments,pvc','-o','json',cleanup=True);report['protected_after']=resource_selection(after);report['protected_comparison']='PASS'if report['protected_after']==report['protected_before']else 'FAIL'
   except BaseException as exc:report['protected_comparison']='FAIL';report['protected_observation_failure']=dict(type=type(exc).__name__,message=str(exc)[:500])
  report['elapsed_seconds']=time.monotonic()-started;report['finished_utc']=utc();report['agent_read_invocations']=sum(x['step'].endswith(('-list','-capacity'))for x in report['commands']);report['status']='PASS'if main_ok and report['cleanup']['status']=='PASS' and report.get('protected_comparison')=='PASS' and report['elapsed_seconds']<=1800 else 'FAIL';checkpoint();save(root/'report.json',report)
 print(json.dumps({'status':report['status'],'new_native_allocations':0,'additional_live_generations':0}));return 0 if report['status']=='PASS'else 1

def outer(path,execute):
 planfile=Path(path).resolve();p=validate_plan(load(planfile),execute);check(sha(__file__)==p['driver_sha256'],'driver source mismatch')
 packet_manifest=Path(p['distribution']).resolve();packet=packet_manifest.parent;check(sha(packet_manifest)==p['distribution_sha256'],'final packet mismatch');check(sha(packet/'wheelhouse/build-manifest.json')==SDK,'SDK25 mismatch')
 release=Path(p['release_record']).resolve();check(sha(release)==p['release_record_sha256'],'release record mismatch');released=load(release);check(released['namespace']==NS and released['implementation_commit']==p['implementation_commit'] and released['distribution_sha256']==p['distribution_sha256'] and released['heavy_slot_released'] is True,'release binding refused')
 work=Path(p['clean_install_output']).resolve();validate_clean(p,work)
 prefix=Path(p['python_prefix']).resolve();check(sha(prefix/'bin/python3.12')==p['tools'][str(prefix/'bin/python3.12')],'Python drift')
 for source in TOOLS:check(sha(source)==p['tools'][source],'tool source drift')
 cfg=Path(p['selected_kubeconfig']).resolve();check(sha(cfg)==p['selected_kubeconfig_sha256'],'selected kubeconfig drift');check(sha('/etc/ssl/openssl.cnf')==p['os_configuration_mounts'][0]['sha256'],'OS config drift')
 root=work/p['driver_output_subdirectory'];check(not root.exists(),'prior namespace attempt exists');root.mkdir(mode=0o700)
 home=root/'home';home.mkdir(mode=0o700);started=time.monotonic();start_utc=utc();save(root/'start.json',dict(started_utc=start_utc,started_monotonic=started,end_monotonic=started+1800,plan_sha256=sha(planfile),driver_sha256=sha(__file__),enabled=True))
 args=['/usr/bin/bwrap','--unshare-all','--share-net','--die-with-parent','--new-session','--clearenv','--proc','/proc','--dev','/dev','--tmpfs','/tmp','--dir','/home','--dir','/tools','--dir','/credentials','--dir','/etc','--dir','/etc/ssl']
 for system in ('/usr','/lib','/lib64','/bin','/sbin'):args+=['--ro-bind',system,system]
 args+=['--ro-bind','/etc/ssl/openssl.cnf','/etc/ssl/openssl.cnf','--ro-bind',str(prefix),'/python','--ro-bind',str(packet),'/packet','--ro-bind',str(work),'/work','--bind',str(root),'/work/h19-namespace','--ro-bind',str(cfg),'/credentials/kubeconfig','--ro-bind',str(planfile),'/plan.json','--ro-bind',str(Path(__file__).resolve()),'/entry.py']
 for source,target in TOOLS.items():
  if target!='/usr/bin/bwrap':args+=['--ro-bind',source,target]
 for denied in ('/usr/bin/systemctl','/usr/sbin/service','/usr/bin/docker','/usr/bin/ollama'):
  if Path(denied).exists():args+=['--ro-bind','/dev/null',denied]
 for k,v in {'PATH':'/work/operator/bin:/tools:/python/bin:/usr/bin:/bin','HOME':'/work/h19-namespace/home','PYTHONNOUSERSITE':'1','PYTHONDONTWRITEBYTECODE':'1','H19_START_MONOTONIC':str(started),'H19_START_UTC':start_utc}.items():args+=['--setenv',k,v]
 args+=['--chdir','/work/h19-namespace','/work/operator/bin/python','-I','/entry.py','--inside']
 code=1;failure=None
 with (root/'launcher.stdout').open('xb')as stdout,(root/'launcher.stderr').open('xb')as stderr:
  proc=None
  try:
   proc=subprocess.Popen(args,stdout=stdout,stderr=stderr,start_new_session=True)
   code=proc.wait(timeout=max(.1,started+1800-time.monotonic()))
  except BaseException as exc:
   failure=dict(type=type(exc).__name__,message=str(exc)[:800]);code=124 if isinstance(exc,subprocess.TimeoutExpired) else 1
   if proc is not None:
    try:os.killpg(proc.pid,signal.SIGKILL)
    except ProcessLookupError:pass
    proc.wait(timeout=5)
 save(root/'launcher.json',dict(status='PASS'if code==0 else 'FAIL',exit_code=code,failure=failure,plan_sha256=sha(planfile),driver_sha256=sha(__file__),elapsed_seconds=time.monotonic()-started,report_present=(root/'report.json').exists(),scope='Single trusted same-host namespace install/read/stop; no new native workflow',additional_live_generations=0))
 print(json.dumps({'status':'PASS'if code==0 else 'FAIL','private_output':str(root)}));return code
if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--plan');parser.add_argument('--execute',action='store_true');parser.add_argument('--inside',action='store_true');a=parser.parse_args()
 try:sys.exit(inside()if a.inside else outer(a.plan,a.execute))
 except Exception as exc:print(json.dumps({'status':'REFUSED_BEFORE_LAUNCH','type':type(exc).__name__,'message':str(exc)[:800]}));sys.exit(2)
