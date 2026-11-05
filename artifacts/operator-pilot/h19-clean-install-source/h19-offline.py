#!/usr/bin/env python3
"""Disabled task-local clean installation proof. No cluster/provider operations."""
import argparse,hashlib,json,os,subprocess,sys,time
from pathlib import Path
SDK='f902477c74ed25c5753d5903fa3c9071c6a6820172c3cc6cc8bb8ef2fd27ee90'
SOURCE='437927520d53825dc9c642df6cc074d6ccccb3ccaec4bd937402e319baacd6fc'
VERIFIER='8cb4278aac8e9dca9dad320998bd7e1645f0b46cc07e6c89ee2a58cb5e60edef'
ARTIFACT_VERIFIER='d64c3bd4a4330871bcf1e219722dd96ec5e119003ca2bf62fcfc6a0e9c445e32'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def load(p):return json.loads(Path(p).read_bytes())
def check(condition,reason):
 if not condition:raise RuntimeError(reason)
def save(p,value):
 with Path(p).open('xb') as stream:stream.write(canonical(value))
CHECK_SOURCES=r'''
import hashlib,importlib.metadata as md,importlib.util,json,sys
from pathlib import Path
build=json.loads(Path('/packet/wheelhouse/build-manifest.json').read_bytes());wanted=json.loads(sys.argv[1]);result={}
for role in wanted:
 name={'client':'fusion-module-client','provider':'fusion-file-feed-example','operator':'fusion-preview-operator'}[role];d=md.distribution(name);m=json.loads(d.read_text('source-manifest.json'))
 assert m['sources']==build[role]['sources']
 for name,row in m['sources'].items():
  p=Path(d.locate_file(name));assert p.is_relative_to('/work') and p.stat().st_size==row['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256']
 result[role]={'source_files':len(m['sources']),'source_manifest_sha256':hashlib.sha256(d.read_text('source-manifest.json').encode()).hexdigest()}
for name in ('torch','transformers','chromadb','fusion.preview_application'):
 try:value=importlib.util.find_spec(name)
 except ModuleNotFoundError:value=None
 assert value is None,name
assert not any('/home/' in p or '/work/takopi/' in p for p in sys.path)
assert not Path('/home/purplezky/work/takopi/fusion-module-interfaces').exists()
if 'operator' not in wanted:
 for name in ('integration.single_node.pilot_cli','fusion_operator'):
  try:value=importlib.util.find_spec(name)
  except ModuleNotFoundError:value=None
  assert value is None,name
print(json.dumps({'sources':result,'isolated':True,'native_owner_imports':False,'inference_libraries_present':False,'additional_live_generations':0},sort_keys=True))
'''
def inside():
 plan=load('/plan.json');check(plan['enabled'] is True and plan['additional_live_generations']==0,'disabled plan');check(sha('/entry.py')==plan['script_sha256'],'script drift');started=time.monotonic();observations=[]
 report={'profile':'operator-pilot-final-clean-artifact-install/1','status':'FAIL','scope':'Fresh same-host offline package installation and exact installed verifier; not browser/native/provider deployment qualification.','distribution_manifest_sha256':plan['distribution_sha256'],'tested_runtime_source_manifest_sha256':SOURCE,'sdk_build_manifest_sha256':SDK,'generative_runtime_contact':False,'new_native_allocations':0,'additional_live_generations':0,'network_namespace':'NEW_UNSHARED_NETWORK','author_checkout_available':False,'cluster_operations':0,'observations':observations}
 def run(label,args,seconds=180):
  remaining=plan['max_seconds']-(time.monotonic()-started);check(remaining>0,'predeclared installation bound expired')
  value=subprocess.run(args,cwd='/work',env={'PATH':'/python/bin:/usr/bin:/bin','PYTHONNOUSERSITE':'1','PIP_NO_INDEX':'1','PIP_DISABLE_PIP_VERSION_CHECK':'1'},capture_output=True,timeout=min(seconds,remaining))
  for kind,data in [('stdout',value.stdout),('stderr',value.stderr)]:
   with Path('/work/'+label+'.'+kind).open('xb') as stream:stream.write(data)
  observations.append({'step':label,'args':args,'returncode':value.returncode,'stdout_sha256':sha('/work/'+label+'.stdout'),'stderr_sha256':sha('/work/'+label+'.stderr')});check(value.returncode==0,label+' failed')
  return value.stdout
 try:
  check(sha('/packet/distribution.json')==plan['distribution_sha256'],'manifest drift');check(hashlib.sha256(canonical(load('/packet/distribution.json')['tested_source'])).hexdigest()==SOURCE,'runtime source drift');check(sha('/packet/wheelhouse/build-manifest.json')==SDK,'SDK drift');build=load('/packet/wheelhouse/build-manifest.json')
  for role in ('client','provider','operator'):check(sha('/packet/wheelhouse/'+build[role]['file'])==build[role]['sha256'],'wheel drift')
  for name,roles,requirements in [
   ('client',['client'],['fusion-module-client==0.3.0']),
   ('provider',['client','provider'],['fusion-module-client==0.3.0','fusion-file-feed-example==0.3.0']),
   ('operator',['client','provider','operator'],['fusion-module-client==0.3.0','fusion-file-feed-example==0.3.0','fusion-preview-operator[preview-install,chain-key-setup]==0.4.0'])]:
   root='/work/'+name;run(name+'-venv',['/python/bin/python3.12','-I','-m','venv',root]);run(name+'-pip',[root+'/bin/python','-I','-m','pip','install','--no-index','--no-cache-dir','--disable-pip-version-check','--retries','0','--find-links','/packet/wheelhouse',*requirements]);value=json.loads(run(name+'-sources',[root+'/bin/python','-I','-c',CHECK_SOURCES,json.dumps(roles)]));report[name+'_installation']=value
  python='/work/operator/bin/python';entry='/work/operator/bin/fusion-pilot'
  for command in ([],['browser']):run('help'+('-browser' if command else ''),[entry,*command,'--help'])
  verified=json.loads(run('verify-artifacts',[entry,'verify-artifacts','/packet/distribution.json'],seconds=900));check(verified['status']=='OFFLINE_VERIFIED','artifact verification failed');report['artifact_verification']=verified
  pins=json.loads(run('verifier-source',[python,'-I','-c','from pathlib import Path;import hashlib,json;from integration.single_node import pilot_evidence,reference_artifacts;print(json.dumps({m.__name__:hashlib.sha256(Path(m.__file__).read_bytes()).hexdigest() for m in (pilot_evidence,reference_artifacts)}))']))
  check(pins=={'integration.single_node.pilot_evidence':VERIFIER,'integration.single_node.reference_artifacts':ARTIFACT_VERIFIER},'verifier drift');report['verifiers']=pins;report['status']='PASS'
 except Exception as exc:report['failure']={'type':type(exc).__name__,'message':str(exc)[:1000]}
 finally:
  report['elapsed_seconds']=time.monotonic()-started;save('/work/clean-install-report.json',report)
 print(json.dumps({'status':report['status'],'report':'clean-install-report.json','additional_live_generations':0}));return 0 if report['status']=='PASS' else 1

def outer(path,execute):
 p=Path(path).resolve();plan=load(p);check(execute and plan['enabled'] is True,'H recipe disabled; requires parent handoff and populated frozen plan')
 check(plan['profile']=='task-local-final-H-install/1' and plan['additional_live_generations']==0,'profile/counter refused');check(plan['max_seconds']==1800,'bound drift')
 check(sha(__file__)==plan['script_sha256'],'script drift');packet=Path(plan['distribution']).resolve();check(sha(packet/'distribution.json')==plan['distribution_sha256'],'manifest drift');check(sha(packet/'wheelhouse/build-manifest.json')==SDK,'SDK drift')
 prefix=Path(plan['python_prefix']).resolve();check(sha(prefix/'bin/python3.12')==plan['python_binary_sha256'],'Python prerequisite drift');bwrap=Path(plan['bwrap']).resolve();check(sha(bwrap)==plan['bwrap_sha256'],'bwrap prerequisite drift')
 work=Path(plan['output']).resolve();check(not work.exists(),'output already exists; never overwrite a prior attempt');work.mkdir(parents=True,mode=0o700);os.chmod(work,0o700)
 args=[str(bwrap),'--unshare-all','--die-with-parent','--new-session','--clearenv','--proc','/proc','--dev','/dev','--tmpfs','/tmp','--dir','/home','--dir','/work','--dir','/packet','--dir','/python','--ro-bind','/usr','/usr']
 for system in ('/lib','/lib64','/bin','/sbin'):
  if Path(system).exists():args+=['--ro-bind',system,system]
 args+=['--ro-bind',str(prefix),'/python','--ro-bind',str(packet),'/packet','--bind',str(work),'/work','--ro-bind',str(p),'/plan.json','--ro-bind',str(Path(__file__).resolve()),'/entry.py','--chdir','/work','--setenv','PATH','/python/bin:/usr/bin:/bin']
 for denied in ('/usr/bin/systemctl','/usr/sbin/service','/usr/bin/docker','/usr/bin/ollama'):
  if Path(denied).exists():args+=['--ro-bind','/dev/null',denied]
 args+=['/python/bin/python3.12','-I','/entry.py','--inside']
 try:
  value=subprocess.run(args,capture_output=True,timeout=plan['max_seconds']+30);code=value.returncode;stdout=value.stdout;stderr=value.stderr;failure=None
 except Exception as exc:
  code=124 if isinstance(exc,subprocess.TimeoutExpired) else 1;stdout=getattr(exc,'stdout',None) or b'';stderr=getattr(exc,'stderr',None) or b'';failure={'type':type(exc).__name__,'message':str(exc)[:1000]}
 (work/'launcher.stdout').write_bytes(stdout);(work/'launcher.stderr').write_bytes(stderr)
 save(work/'launcher.json',{'status':'PASS' if code==0 else 'FAIL','exit_code':code,'failure':failure,'script_sha256':sha(__file__),'plan_sha256':sha(p),'isolation':'bwrap new network namespace; no author checkout, home, kubeconfig, Docker socket or generative asset mounts','output_report':'clean-install-report.json' if (work/'clean-install-report.json').exists() else None,'additional_live_generations':0});print(json.dumps({'status':'PASS' if code==0 else 'FAIL','output':str(work)}));return code
if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--plan');parser.add_argument('--execute',action='store_true');parser.add_argument('--inside',action='store_true');a=parser.parse_args();sys.exit(inside() if a.inside else outer(a.plan,a.execute))
