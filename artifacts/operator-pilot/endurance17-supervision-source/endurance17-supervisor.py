"""One disabled-until-released, finite task-local qualification supervisor.

No runtime/SDK changes, scheduler, retry, or accepted-input recovery. The launch
process double-forks through setsid; every external child has an independent
process group and is reaped before owner diagnostics/stop may begin.
"""
import argparse,hashlib,json,os,signal,subprocess,sys,time
from pathlib import Path

ROOT=Path('/data/fusion-operator-pilot-release/qualification-private/parent20')
NAMESPACE='omega-ref-pilot-endurance17'
SDK='f902477c74ed25c5753d5903fa3c9071c6a6820172c3cc6cc8bb8ef2fd27ee90'
QUALIFIER='247a7e0945bc6e71c6821a7a7834d5f47e0ad3f1c956a6f2b22a203df5ed5331'
RUNTIME='437927520d53825dc9c642df6cc074d6ccccb3ccaec4bd937402e319baacd6fc'

def require(value,message):
 if not value:raise RuntimeError(message)
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_bytes())
def write(path,value):
 path=Path(path);tmp=path.with_name(path.name+'.tmp');tmp.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n');tmp.chmod(0o600);os.replace(tmp,path)
def identity(pid):
 raw=Path('/proc',str(pid),'stat').read_text();fields=raw[raw.rfind(')')+2:].split()
 return dict(pid=pid,ppid=int(fields[1]),process_group=int(fields[2]),session=int(fields[3]),start_ticks=int(fields[19]))
def same_process(saved):
 try:current=identity(saved['pid'])
 except FileNotFoundError:return False
 return all(current[k]==saved[k]for k in ('pid','start_ticks','process_group','session'))
def receipt_due(path):
 try:value=read(path)
 except (FileNotFoundError,json.JSONDecodeError):return False
 return len(value.get('inputs',[]))>20 and len(value.get('allocations',[]))==2
def absence_command(plan):return [plan['tools']['kubectl']['invoke_path'],'--kubeconfig',plan['kubeconfig'],'--context','default','get','namespace',NAMESPACE,'--ignore-not-found','-o','json']
def cleanup_allowed(children):return all(x['reaped'] and x['exit_code']is not None for x in children)

def validate(plan_path,release_path):
 plan=read(plan_path);release=read(release_path)
 require(plan['profile']=='task-local-endurance17-detached/1' and plan['namespace']==NAMESPACE,'wrong frozen plan')
 require(Path(plan['root']).resolve()==ROOT and plan['additional_live_generations']==0,'scope/counter mismatch')
 require(release==dict(profile='task-local-endurance17-release/1',plan_sha256=sha(plan_path),namespace=NAMESPACE,heavy_slot_released=True,execute_once=True),'separate exact release required')
 require(plan['sources']['supervisor']['path']==str(Path(__file__).resolve()) and plan['sources']['supervisor']['sha256']==sha(__file__),'supervisor drift')
 require(plan['limits']==dict(setup_seconds=600,qualifier_native_seconds=7200,qualifier_process_seconds=7260,receipt_seconds=120,diagnostic_seconds=600,cleanup_seconds=300,termination_seconds=30,outer_seconds=9000),'limit drift')
 require(plan['runtime_source_sha256']==RUNTIME and plan['sdk25_manifest_sha256']==SDK and plan['qualifier_sha256']==QUALIFIER,'artifact binding drift')
 for row in plan['sources'].values():require(sha(row['path'])==row['sha256'],'frozen source/config drift')
 for row in plan['tools'].values():
  require(sha(row['path'])==row['sha256'],'tool drift')
  if 'invoke_path'in row:require(str(Path(row['invoke_path']).resolve())==row['path'] and sha(row['invoke_path'])==row['sha256'],'tool invocation drift')
 require(sha(plan['sdk_manifest'])==SDK,'SDK manifest drift')
 manifest=read(plan['sdk_manifest']);require(manifest['operator']['sources']['examples/pilot_endurance.py']['sha256']==QUALIFIER,'workload consumer drift')
 from importlib.metadata import distribution
 d=distribution('fusion-preview-operator');installed=json.loads(d.read_text('source-manifest.json'))
 require(installed['sources']==manifest['operator']['sources'],'installed SDK manifest mismatch')
 require(all(sha(d.locate_file(k))==v['sha256']for k,v in installed['sources'].items()),'installed source drift')
 from integration.single_node.placement import files_hash
 require(files_hash(plan['chart'])==plan['chart_sha256'],'chart drift')
 images=read(plan['images']);require(images['source_manifest_sha256']==RUNTIME,'runtime drift')
 workload=read(ROOT/'workload.json');require(workload['native_operator_inputs']==160 and workload['maximum_seconds']==7200 and workload['windows']==4,'native work bound drift')
 require([x['operation']for x in workload['shared_post_delegation']]==['inspect-atom','metta'],'domain selection drift')
 return plan

class Supervisor:
 def __init__(self,plan,plan_path,release_path,launcher):
  self.plan=plan;self.root=ROOT;self.start=time.monotonic();self.end=self.start+plan['limits']['outer_seconds'];self.abort=None;self.children=[];self.active={};self.receipt=None
  self.report=dict(profile='task-local-endurance17-supervisor/1',status='RUNNING',namespace=NAMESPACE,plan_sha256=sha(plan_path),release_sha256=sha(release_path),source_sha256=sha(__file__),launcher=launcher,supervisor=identity(os.getpid()),started_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),started_unix_ms=int(time.time()*1000),started_monotonic=self.start,outer_end_monotonic=self.end,limits=plan['limits'],signals=[],phases=[],children=self.children,additional_live_generations=0,cleanup=None)
 def save(self):write(self.root/'supervisor/report.json',self.report)
 def signal(self,number,_frame):
  self.report['signals'].append(dict(signal=number,name=signal.Signals(number).name,observed_unix_ms=int(time.time()*1000),observed_monotonic=time.monotonic(),sender='UNAVAILABLE_PYTHON_SIGNAL_HANDLER'))
  self.abort='signal:'+signal.Signals(number).name
 def spawn(self,name,args,deadline):
  require(time.monotonic()<deadline,'phase bound elapsed before child start')
  require(name not in self.active,'duplicate child name')
  out=(self.root/'supervisor'/f'{name}.stdout').open('xb');err=(self.root/'supervisor'/f'{name}.stderr').open('xb')
  env=os.environ.copy();env.pop('PYTHONPATH',None);env.pop('PYTHONHOME',None);env['TMPDIR']=self.plan['temporary_directory'];env['PATH']=self.plan['tool_path']
  try:p=subprocess.Popen(args,stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True,close_fds=True,env=env,cwd='/')
  finally:out.close();err.close()
  process=identity(p.pid);require(process['process_group']==p.pid and process['session']==p.pid,'child not isolated in its own group')
  row=dict(name=name,process=process,parent_supervisor_pid=os.getpid(),started_unix_ms=int(time.time()*1000),deadline_monotonic=deadline,reaped=False,exit_code=None,signals_sent=[])
  self.children.append(row);self.active[name]=(p,row);self.save();return p,row
 def reap(self,name):
  p,row=self.active[name];code=p.poll()
  if code is None:return False
  code=p.wait();row.update(reaped=True,exit_code=code,finished_unix_ms=int(time.time()*1000));del self.active[name];self.save();return True
 def terminate(self,name,reason):
  if name not in self.active:return
  p,row=self.active[name]
  if self.reap(name):return
  if not same_process(row['process']):
   require(self.reap(name),'process identity changed; no signal sent');return
  row['termination_reason']=reason
  for sig,wait in ((signal.SIGTERM,20),(signal.SIGKILL,10)):
   if name not in self.active:break
   if not same_process(row['process']):
    require(self.reap(name),'process identity changed before signal');break
   try:os.killpg(row['process']['process_group'],sig)
   except ProcessLookupError:
    require(self.reap(name),'process disappeared without reaped child');break
   row['signals_sent'].append(dict(signal=sig,unix_ms=int(time.time()*1000)));self.save()
   try:p.wait(timeout=wait)
   except subprocess.TimeoutExpired:continue
   self.reap(name)
  require(name not in self.active,'child could not be reaped; owner cleanup prohibited')
 def phase(self,name,args,seconds,*,monitor=False,allow_abort=False):
  require(allow_abort or self.abort is None,'earlier interruption prevents new work')
  phase_end=self.end if name=='cleanup' else self.end-300
  deadline=min(phase_end,time.monotonic()+seconds);p,row=self.spawn(name,args,deadline)
  try:
   while not self.reap(name):
    if monitor and self.receipt is None and receipt_due(self.root/'endurance-run/window-3/report.json'):
     rp=dict(self.plan['receipt_observer']);rp.update(enabled=True);write(self.root/'receipt-execution-plan.json',rp)
     self.receipt=self.spawn('receipt-snapshot',[self.plan['python'],'-I',self.plan['sources']['receipts']['path'],'--plan',str(self.root/'receipt-execution-plan.json'),'--execute'],min(self.end-300,time.monotonic()+120))
    if self.receipt and 'receipt-snapshot'in self.active:
     if not self.reap('receipt-snapshot') and time.monotonic()>=self.receipt[1]['deadline_monotonic']:self.terminate('receipt-snapshot','receipt observation bound')
    if (self.abort and not allow_abort)or time.monotonic()>=deadline:
     self.terminate(name,self.abort or 'phase bound');break
    time.sleep(.2)
  finally:
   if name in self.active:self.terminate(name,'phase exited before child terminal')
  self.report['phases'].append(dict(name=name,exit_code=row['exit_code'],reaped=row['reaped']));self.save()
  return row['exit_code']
 def run(self):
  for sig in (signal.SIGTERM,signal.SIGINT,signal.SIGHUP,signal.SIGQUIT):signal.signal(sig,self.signal)
  self.save();write(self.root/'supervisor/ready.json',dict(supervisor=self.report['supervisor'],source_sha256=sha(__file__),plan_sha256=self.report['plan_sha256']))
  py=self.plan['python'];cli=[py,'-I','-m','integration.single_node.pilot_cli'];common=['--kubeconfig',self.plan['kubeconfig'],'--context','default','--namespace',NAMESPACE];installed=False;creation_attempted=False
  try:
   # Setup is one fixed shared600-second budget, not600s per command.
   setup_end=min(self.end,time.monotonic()+600)
   absent=absence_command(self.plan)
   require(self.phase('namespace-absence',absent,30)==0 and not(self.root/'supervisor/namespace-absence.stdout').read_bytes().strip(),'fresh namespace is not absent; no mutation authorized')
   creation_attempted=True
   require(self.phase('install',cli+['services',*common,'install','--chart',self.plan['chart'],'--values',str(self.root/'endurance-values.yaml'),'--directory',str(self.root/'endurance-secrets')],max(0,setup_end-time.monotonic()))==0,'installation failed');installed=True
   require(self.phase('placement',cli+['placement','verify-installed','--plan',str(self.root/'endurance-plan.json'),*common,'--output',str(self.root/'endurance-installed.json')],max(0,setup_end-time.monotonic()))==0,'placement failed')
   code=self.phase('qualifier',cli+['qualify-endurance',*common,'--plan',str(self.root/'endurance-plan.json'),'--directory',str(self.root/'endurance-run')],7260,monitor=True)
   self.report['qualifier_exit_code']=code
   raw=read(self.root/'endurance-run/report.json')if(self.root/'endurance-run/report.json').exists()else None
   self.report['qualifier_primary_status']=raw.get('status')if raw else'UNOBSERVED'
   self.report['status']='PASS'if code==0 and raw and raw['status']=='PASS'and not self.abort else'FAIL_RETAINED'
  except BaseException as error:self.report.update(status='FAIL_RETAINED',failure=dict(type=type(error).__name__,message=str(error)[-300:]))
  finally:
   # This barrier is mandatory on normal exit, exceptions and caught signals.
   for name in list(self.active):
    if name=='receipt-snapshot' and self.abort is None:
     while name in self.active and time.monotonic()<self.active[name][1]['deadline_monotonic']:
      if self.reap(name):break
      time.sleep(.2)
    if name in self.active:self.terminate(name,self.abort or 'qualification finished')
   require(cleanup_allowed(self.children),'child not reaped; no diagnostics/owner cleanup')
   self.report['child_terminal_barrier']=dict(passed=True,observed_unix_ms=int(time.time()*1000));self.save()
   if not creation_attempted:
    self.report.update(cleanup=dict(status='NOT_REQUIRED_NO_CREATION_ATTEMPT'),finished_unix_ms=int(time.time()*1000),elapsed_seconds=time.monotonic()-self.start,interruption=self.abort);self.save();return
   # If the final window completed between monitor ticks, the one permitted
   # snapshot can occur here, still before owner stop and never rerun.
   if self.receipt is None and receipt_due(self.root/'endurance-run/window-3/report.json'):
    rp=dict(self.plan['receipt_observer']);rp.update(enabled=True);write(self.root/'receipt-execution-plan.json',rp)
    self.phase('receipt-snapshot',[py,'-I',self.plan['sources']['receipts']['path'],'--plan',str(self.root/'receipt-execution-plan.json'),'--execute'],120,allow_abort=True)
   try:self.report['diagnostic_exit_code']=self.phase('diagnostics',[py,'-I',self.plan['sources']['diagnostic']['path']],600,allow_abort=True)
   except Exception as error:self.report['diagnostic_failure']=dict(type=type(error).__name__,message=str(error)[-300:])
   require(cleanup_allowed(self.children),'post-observation child not reaped')
   try:
    code=self.phase('cleanup',[py,'-I',self.plan['sources']['cleanup']['path']],300,allow_abort=True)
    self.report['cleanup']=dict(exit_code=code,status='PASS'if code==0 else'FAIL_RETAINED')
   except Exception as error:self.report['cleanup']=dict(status='FAIL_RETAINED',failure=type(error).__name__)
   receipt_rows=[x for x in self.children if x['name']=='receipt-snapshot']
   self.report['receipt_observation']=dict(status='OBSERVED'if receipt_rows and receipt_rows[0]['exit_code']==0 else 'FAILED'if receipt_rows else'NOT_RUN',exit_code=receipt_rows[0]['exit_code']if receipt_rows else None)
   self.report.update(finished_unix_ms=int(time.time()*1000),elapsed_seconds=time.monotonic()-self.start,interruption=self.abort)
   if receipt_rows and receipt_rows[0]['exit_code']!=0:self.report['status']='FAIL_RETAINED'
   if self.report.get('diagnostic_exit_code')!=0 or self.report['cleanup']['status']!='PASS':self.report['status']='FAIL_RETAINED'
   self.save()

def launch(plan_path,release_path):
 plan=validate(plan_path,release_path);require(not(ROOT/'endurance-run').exists()and not(ROOT/'endurance-secrets').exists(),'fresh run required')
 directory=ROOT/'supervisor';directory.mkdir(mode=0o700,exist_ok=False)
 parent=identity(os.getpid());write(directory/'launch.json',dict(profile='task-local-setsid-launch/1',launcher=parent,source_sha256=sha(__file__),plan_sha256=sha(plan_path),release_sha256=sha(release_path),additional_live_generations=0))
 first=os.fork()
 if first==0:
  os.setsid();second=os.fork()
  if second:os._exit(0)
  os.umask(0o077);os.chdir('/')
  fd=os.open(os.devnull,os.O_RDONLY);os.dup2(fd,0);os.close(fd)
  for number,name in ((1,'supervisor.stdout'),(2,'supervisor.stderr')):
   fd=os.open(directory/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600);os.dup2(fd,number);os.close(fd)
  try:Supervisor(plan,plan_path,release_path,parent).run()
  except BaseException as error:
   write(directory/'unhandled.json',dict(type=type(error).__name__,message=str(error)[-500:],additional_live_generations=0));os._exit(1)
  os._exit(0)
 _,status=os.waitpid(first,0);require(os.waitstatus_to_exitcode(status)==0,'setsid fork failed')
 until=time.monotonic()+8
 while not(directory/'ready.json').exists()and time.monotonic()<until:time.sleep(.05)
 require((directory/'ready.json').exists(),'launch acknowledgment unavailable; DO NOT relaunch')
 ready=read(directory/'ready.json');require(same_process(ready['supervisor']),'supervisor exited before acknowledgment')
 print(json.dumps(dict(status='LAUNCHED_ONCE',supervisor=ready['supervisor'],plan_sha256=sha(plan_path),report=str(directory/'report.json'),additional_live_generations=0)))

def main():
 p=argparse.ArgumentParser();p.add_argument('--plan',required=True);p.add_argument('--release',required=True);p.add_argument('--execute',action='store_true');a=p.parse_args();require(a.execute,'disabled');launch(Path(a.plan).resolve(),Path(a.release).resolve())
if __name__=='__main__':main()
