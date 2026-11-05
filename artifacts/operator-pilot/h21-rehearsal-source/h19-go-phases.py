"""Task-local final-packet Go phases. Existing owners and qualifiers only.

Called only by the separately frozen H driver inside its clean installed SDK
sandbox. This module never creates a namespace, installs a chart or submits a
native command itself. The H driver invokes the existing bounded qualifier.
"""
import hashlib,importlib.util,json,subprocess,tarfile,time
from pathlib import Path,PurePosixPath
NS='omega-ref-pilot-adopter21-go';SCOPE='synthetic-pilot-adopter21-go'
ARTIFACT='4d08cc94758d475e621e8471ed4dd8150240e9a3c297a93642710e20c9ccb853'
SOURCE='738bdb6ad57aa939545400f3074283f68a9b5343d1d6665a3a5313fd4a44e53a'
CAPACITY_SOURCE='a3b7aeab738d594e11c802b158e8a2f2e92761a33c1f6c3c8a357630dc348bb2'
TOOLCHAIN_BINARY='5f5eb6d0b2fb6aa0bb5d5f8c5f1c944e0de955c925f0111af92a9d8f79680b5b'
GO_PROVIDER='e29991d23c42a00c0f7d4609245ddfa333d8aa59081fdadd0ba0f3b0ef0b9dac'
GO_CLIENT='889aa68f69a853de3728aba0fdc9c2df213840466a49bda93e738d13ba767637'
def check(v,why):
 if not v:raise RuntimeError(why)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_bytes())
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def save(p,v):
 with Path(p).open('xb')as f:f.write(canonical(v))
def remaining(end,limit):
 value=end-time.monotonic();check(value>0,'original H work bound expired');return min(limit,value)
def artifact_path(packet):
 p=Path(packet)/'go-provider/provider-image.json';check(sha(p)==ARTIFACT,'Go04 artifact drift');return p

def prepare(packet):
 from integration.single_node.pilot_go_values import initial
 artifact=artifact_path(packet)
 value,images=initial(load(Path(packet)/'images.json'),artifact,SCOPE,NS)
 check('writer_fence' not in value['preview']['pilot'],'Go writer-fence profile unsupported')
 check(value['preview']['model_boundary']=='RECORDED_FIXTURE','model selection drift')
 return value,images

def replacement(initial_values):
 from integration.single_node.pilot_go_values import replace
 value=replace(initial_values)
 old=json.loads(json.dumps(initial_values));candidate=json.loads(json.dumps(value))
 added=candidate['preview']['inspection'].pop('additional_template')
 check(candidate==old and added['name']=='go-shared' and added['service']=='fusion-inspect-go','replacement changed original/gateway configuration')
 return value

def extract_source(archive,manifest,target):
 check(not target.exists(),'kit destination exists');target.mkdir(mode=0o700)
 expected=manifest['source'];check(len(expected)==19,'kit file-count drift');seen=set()
 with tarfile.open(archive,'r:gz')as tar:
  members=tar.getmembers();check(len(members)<=64 and sum(x.size for x in members)<=1048576,'kit archive bounds')
  for item in members:
   parts=PurePosixPath(item.name).parts
   check(parts and parts[0]=='omega-go-provider-kit' and not PurePosixPath(item.name).is_absolute() and '..' not in parts,'kit escaping member')
   check(item.name not in seen and (item.isfile()or item.isdir()),'kit duplicate/link/special member');seen.add(item.name)
   path=target.joinpath(*parts)
   if item.isdir():path.mkdir(parents=True,exist_ok=True)
   else:
    key=str(PurePosixPath(*parts[1:]));check(key in expected,'unexpected kit file')
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb')as output:output.write(tar.extractfile(item).read())
    check(sha(path)==expected[key],'extracted kit source drift')
 root=target/'omega-go-provider-kit';check({str(p.relative_to(root)):sha(p)for p in root.rglob('*')if p.is_file()}==expected,'extracted source set drift');return root

def rebuild(packet,toolchain,output,end):
 """Real extracted-source Go build; fixture-port tests, no deployed conformance claim."""
 from integration.single_node.pilot_provider_image import verify
 artifact=artifact_path(packet);checked=verify(artifact);check(checked['source_manifest_sha256']==SOURCE,'independent source drift')
 kit=artifact.parent/'kit';manifest=load(kit/'manifest.json');check(sha(kit/'omega-go-provider-kit-source.tar.gz')==manifest['archive_sha256'],'kit archive drift')
 check(manifest['source_manifest_sha256']==SOURCE and manifest['toolchain']=='go version go1.27.3 linux/amd64','toolchain version drift')
 toolchain=Path(toolchain);check(sha(toolchain/'bin/go')==TOOLCHAIN_BINARY==manifest['toolchain_binary_sha256'],'compiler drift')
 for name,pin in manifest['libraries'].items():check(sha(name)==pin,'toolchain loader prerequisite drift')
 output=Path(output);output.mkdir(parents=True,mode=0o700,exist_ok=False);source=extract_source(kit/'omega-go-provider-kit-source.tar.gz',manifest,output/'source');cache=output/'cache';cache.mkdir();binaries=output/'binaries';binaries.mkdir()
 report=dict(status='FAIL',scope='EXTRACTED_KIT_REAL_GO_FIXTURE_PORT_TESTS_NO_CHECKOUT_PYTHON_OR_NETWORK',artifact_sha256=ARTIFACT,source_manifest_sha256=SOURCE,compiler_sha256=TOOLCHAIN_BINARY,commands=[],additional_live_generations=0)
 try:
  mounts=[part for name in manifest['libraries']for part in ('--ro-bind',str(Path(name).resolve()),name)]
  command=['/usr/bin/bwrap','--die-with-parent','--unshare-pid','--unshare-ipc','--unshare-uts','--unshare-net',*mounts,'--ro-bind',str(source),'/kit','--ro-bind',str(toolchain),'/toolchain','--bind',str(cache),'/cache','--bind',str(binaries),'/output','--tmpfs','/tmp','--proc','/proc','--dev','/dev','--clearenv','--setenv','PATH','/toolchain/bin','--setenv','HOME','/nonexistent','--setenv','GOROOT','/toolchain','--setenv','GOTOOLCHAIN','local','--setenv','GOCACHE','/cache','--setenv','GOENV','off','--setenv','GOPROXY','off','--setenv','GOSUMDB','off','--setenv','CGO_ENABLED','0','--chdir','/kit/go','/toolchain/bin/go']
  for name,args in [('tests',['test','-json','./...','-count=1'])]+[(n,['build','-trimpath','-o','/output/'+n,'./cmd/'+n])for n in ('omega-client','omega-inspect-provider')]:
   timeout=remaining(end,180);row=dict(name=name,args=args,timeout_seconds=timeout);report['commands'].append(row)
   with (output/(name+'.stdout')).open('xb')as stdout,(output/(name+'.stderr')).open('xb')as stderr:
    result=subprocess.run(command+args,stdout=stdout,stderr=stderr,timeout=timeout)
   row.update(exit_code=result.returncode,stdout_sha256=sha(output/(name+'.stdout')),stderr_sha256=sha(output/(name+'.stderr')));check(result.returncode==0,'Go '+name+' failed')
  check(sha(binaries/'omega-client')==GO_CLIENT and sha(binaries/'omega-inspect-provider')==GO_PROVIDER,'rebuilt binary differs from qualified image input')
  report.update(status='PASS',binaries={n:sha(binaries/n)for n in ('omega-client','omega-inspect-provider')},source_files=19,binary_identity_exact=True)
 except BaseException as error:report['failure']={'type':type(error).__name__,'message':str(error)[:500]};raise
 finally:save(output/'report.json',report)
 return report

def capacity_module(packet):
 path=Path(packet)/'examples/pilot_go_capacity.py';check(sha(path)==CAPACITY_SOURCE,'capacity helper drift')
 spec=importlib.util.spec_from_file_location('exact_final_packet_go_capacity',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def capacity_provision(op,plan,artifact,chart,directory,end,packet=Path('/packet')):
 remaining(end,1);check(op.namespace==NS and sha(artifact)==ARTIFACT,'capacity composition drift')
 return capacity_module(packet).provision(op,plan,artifact,chart,directory)

def capacity_observe(op,plan,artifact,chart,provisioned,directory,end,packet=Path('/packet')):
 check(op.namespace==NS and sha(artifact)==ARTIFACT,'capacity composition drift')
 deadline=time.time_ns()//1000000+int(remaining(end,60)*1000)
 return capacity_module(packet).observe(op,plan,artifact,chart,provisioned,directory,deadline)

READ_TEMPLATE=r'''
import json,sys
from pathlib import Path
from fusion.preview_inspect import Client
from fusion.client import Peer
from fusion.contracts import require
cfg=json.loads(Path('/run/fusion/owner.json').read_bytes());template=cfg['native_sessions']['runtime_templates']['go-shared'];path=Path(template['directory'])/'inspection.json'
require(str(path)=='/run/fusion/templates/go-shared/inspection.json','UNAUTHORIZED')
client=Client(path);peer=Peer(client,client.cfg['scope'],'inspect-A');job=sys.argv[1]
print(json.dumps(dict(events=client.events(job),status=peer.status(job),result=peer.result(job))))
'''
def drain_retained(op,replacement_report,directory,end):
 """Finite normal API controls/readback after successful existing qualifier closes."""
 from integration.single_node.reference_ops import PYTHON
 before_report=load(replacement_report);check(op.namespace==NS and before_report['status']=='PASS' and before_report['stage']=='replacement','replacement not qualified')
 sid=before_report['session'];job=before_report['inspection']['job_id'];directory=Path(directory);directory.mkdir(parents=True,mode=0o700,exist_ok=False)
 report=dict(status='FAIL',new_native_inputs=0,accepted_allocations=0,deadline_renewals=0,reservation_refunds=0,additional_live_generations=0)
 def call(operation,*args):return json.loads(op.k('exec','omega-agent-0','--',PYTHON,'-m','integration.single_node.preview_operator',operation,*args,timeout=remaining(end,35)))
 def read():return json.loads(op.k('exec','omega-agent-0','--',PYTHON,'-c',READ_TEMPLATE,job,timeout=remaining(end,35)))
 try:
  before=read();captured=call('observe','--session',sid,'--content');selected=call('providers','--session',sid,'--provider-action','selected')
  check(before['result']==before_report['inspection']['inspection'] and before['status']['execution']=='succeeded','prior result mismatch')
  report.update(before=before,captured=captured,selected=selected)
  report['drain']=call('providers','--provider-action','drain','--provider','go-shared-fusion-inspect-go','--identity','h19-drain-qualified-go')
  try:report['unexpected_allocation']=call('allocate','--identity','h19-drained-allocation-refusal','--template','go-shared');report['accepted_allocations']=1
  except RuntimeError as error:check('NOT_AVAILABLE' in str(error),'wrong post-drain refusal');report['new_selection_refused']='NOT_AVAILABLE'
  else:raise RuntimeError('drained provider unexpectedly admitted new work')
  after=read();check(after==before and call('observe','--session',sid,'--content')==captured and call('providers','--session',sid,'--provider-action','selected')==selected,'retained capture/selection changed')
  report.update(status='PASS',after=after,old_capture_exact=True)
 except BaseException as error:report['failure']={'type':type(error).__name__,'message':str(error)[-500:]};raise
 finally:save(directory/'report.json',report)
 return report
