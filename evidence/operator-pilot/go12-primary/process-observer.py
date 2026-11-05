"""Read only exact task-owned container process metadata; no pod exec/owner IO."""
import argparse,json,re,time
from pathlib import Path
from fusion.contracts import canonical,digest,require
from integration.single_node.reference_ops import Operator
p=argparse.ArgumentParser();p.add_argument('--kubeconfig',required=True);p.add_argument('--namespace',required=True);p.add_argument('--role',choices=['fusion-inspect-go','f1r3node'],required=True);p.add_argument('--output',required=True);a=p.parse_args()
op=Operator(a.kubeconfig,'default',a.namespace);out=Path(a.output);require(not out.exists(),'CONFLICT')
report=dict(profile='task-bound-process-observation/1',status='RUNNING',namespace=a.namespace,role=a.role,source_sha256=digest(Path(__file__).read_bytes()),additional_live_generations=0,processes=[],journal_access=False,host_modified=False,root_write_probe='NOT_RUN',cpu_quota_enforcement='NOT_ESTABLISHED')
def save():out.write_bytes(canonical(report))
save()
try:
 ns=op.owned();pod=json.loads(op.k('get','pod',a.role+'-0','-o','json'));workload=json.loads(op.k('get','statefulset',a.role,'-o','json'))
 require(pod['spec']['nodeName']=='omega-fusion-k3s','UNSUPPORTED_PROFILE')
 require(pod['metadata']['namespace']==op.namespace and all(x['metadata']['labels'].get('app.kubernetes.io/instance')=='omega' and x['metadata']['labels'].get('app.kubernetes.io/name')==a.role for x in (pod,workload)),'UNAUTHORIZED')
 require(any(x.get('controller') is True and x['kind']=='StatefulSet' and x['name']==a.role and x['uid']==workload['metadata']['uid'] for x in pod['metadata']['ownerReferences']),'UNAUTHORIZED')
 require(len(pod['status']['containerStatuses'])==1 and len(pod['spec']['containers'])==1,'UNSUPPORTED_PROFILE')
 container=pod['status']['containerStatuses'][0];identity=container['containerID'].removeprefix('containerd://')
 require(re.fullmatch('[0-9a-f]{64}',identity) is not None,'CONFLICT')
 command=['docker','exec','omega-fusion-k3s'];ctr=command+['ctr','-n','k8s.io']
 actual=json.loads(op.command(ctr+['containers','info',identity]));labels=actual['Labels']
 require(labels['io.kubernetes.pod.namespace']==op.namespace and labels['io.kubernetes.pod.uid']==pod['metadata']['uid'] and labels['io.kubernetes.pod.name']==a.role+'-0' and labels['io.kubernetes.container.name']==a.role and actual['Image']==container['image'],'UNAUTHORIZED')
 def processes():
  raw=op.command(ctr+['tasks','ps',identity],timeout=15)
  lines=raw.strip().splitlines();require(lines and lines[0].split()[0]=='PID','CONFLICT')
  ids=[line.split()[0] for line in lines[1:]];require(1<=len(ids)<=32 and all(re.fullmatch('[1-9][0-9]{0,9}',x) for x in ids),'OVERLOADED')
  return raw,ids
 primary,pids=processes()
 report.update(namespace_uid=ns['metadata']['uid'],pod_uid=pod['metadata']['uid'],workload_uid=workload['metadata']['uid'],container_id=identity,image=pod['spec']['containers'][0]['image'],image_id=container['imageID'],task_process_listing=primary,configured_security=pod['spec']['containers'][0]['securityContext'],configured_resources=pod['spec']['containers'][0]['resources'],pod_security=pod['spec'].get('securityContext',{}))
 save()
 for pid in pids:
  before=op.command(command+['cat','/proc/'+pid+'/stat'],timeout=15)
  raw=op.command(command+['cat','/proc/'+pid+'/status'],timeout=15);status={}
  for line in raw.splitlines():
   k,sep,v=line.partition(':')
   if k in ('Name','Pid','PPid','Uid','Gid','CapEff','CapBnd','NoNewPrivs','Seccomp','VmRSS','VmSize','Threads'):status[k]=v.strip()
  cgroup=op.command(command+['cat','/proc/'+pid+'/cgroup'],timeout=15)
  after=op.command(command+['cat','/proc/'+pid+'/stat'],timeout=15)
  require(before.rsplit(')',1)[1].split()[19]==after.rsplit(')',1)[1].split()[19],'CONFLICT')
  report['processes'].append(dict(pid=int(pid),starttime_ticks=before.rsplit(')',1)[1].split()[19],status=status,cgroup_membership=cgroup));save()
 _,later=processes()
 require(set(pids)<=set(later),'CONFLICT')
 current=json.loads(op.k('get','pod',a.role+'-0','-o','json'))
 require(op.owned()['metadata']['uid']==ns['metadata']['uid'] and current['metadata']['uid']==pod['metadata']['uid'] and current['status']['containerStatuses'][0]['containerID']==container['containerID'],'CONFLICT')
 require(all(all(int(v)>0 for v in row['status']['Uid'].split()) and all(int(v)>0 for v in row['status']['Gid'].split()) and int(row['status']['CapEff'],16)==0 and row['status']['NoNewPrivs']=='1' for row in report['processes']),'UNAUTHORIZED')
 report.update(status='PASS',actual_process_uid_and_caps='OBSERVED',memory_enforcement='NOT_ESTABLISHED; RSS and cgroup membership only',limits=['Task-bound read-only Linux process observation; no hostile-host guarantee','Configured resource limits do not establish enforcement','No foreign owner journal, credential or payload access','Root filesystem behavior remains configured-only for scratch/chain image in this observer'])
except BaseException as error:
 report.update(status='FAIL',failure=dict(type=type(error).__name__,code=getattr(error,'code',None),detail=str(error)[-1200:]));raise
finally:save()
print(json.dumps(dict(status=report['status'],role=a.role,processes=len(report['processes']),additional_live_generations=0)))
