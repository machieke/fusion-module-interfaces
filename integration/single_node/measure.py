"""Owner-local bounded resource sample; no operation/admission or model calls."""
import json,os,time
from pathlib import Path

def sample(root=Path('/state'),proc=Path('/proc'),cgroup=Path('/sys/fs/cgroup')):
 processes=[]
 for path in proc.iterdir():
  if not path.name.isdigit():continue
  try:
   stat=(path/'stat').read_text();tail=stat[stat.rfind(')')+2:].split()
   processes.append(dict(pid=int(path.name),ppid=int(tail[1]),cpu_ticks=int(tail[11])+int(tail[12]),rss_bytes=int(tail[21])*os.sysconf('SC_PAGE_SIZE')))
  except (OSError,IndexError,ValueError):continue
 size=0;files=0
 for file in root.rglob('*'):
  if file.is_file() and not file.is_symlink():size+=file.stat().st_size;files+=1
 def read(name):
  p=cgroup/name;return p.read_text().strip() if p.is_file() else 'UNAVAILABLE'
 counters={k:read(k) for k in ('cpu.stat','memory.current','memory.peak','memory.events','cpu.max','memory.max')}
 # This node uses v1, mounted at this container's own group. Resolve the
 # kernel-reported membership relative to the mount root; never sample the
 # host/root group or another owner's group as a fallback.
 if all(v=='UNAVAILABLE' for v in counters.values()):
  memberships={k:v for _,k,v in (x.split(':',2) for x in (proc/'self/cgroup').read_text().splitlines())}
  names={'memory':('memory.usage_in_bytes','memory.max_usage_in_bytes','memory.limit_in_bytes','memory.failcnt'),'cpu,cpuacct':('cpuacct.usage','cpu.stat','cpu.cfs_quota_us','cpu.cfs_period_us')}
  for line in (proc/'self/mountinfo').read_text().splitlines():
   fields=line.split();mount=Path(fields[4]);controller=mount.name
   if controller not in names or controller not in memberships:continue
   try:relative=Path(memberships[controller]).relative_to(fields[3])
   except ValueError:continue
   for name in names[controller]:
    file=mount/relative/name
    if file.is_file():counters['v1.'+name]=file.read_text().strip()
 return dict(observed_unix_ns=time.time_ns(),processes=processes,cpu_ticks_per_second=os.sysconf('SC_CLK_TCK'),state_bytes=size,state_files=files,cgroup=counters,sampling='observer process included explicitly; pid1 is role host; cgroup includes all native children',live_model_throughput='NOT_RUN')
if __name__=='__main__':print(json.dumps(sample()))
