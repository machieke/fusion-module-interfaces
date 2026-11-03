"""Bounded owner-pod process samples when Metrics API/cgroups are unavailable.

No command lines, prompts, filenames or private values are collected. RSS sums
can double-count shared pages. CPU deltas omit processes that exit between the
two samples; neither metric establishes kernel quota enforcement or a peak load.
"""
import argparse,json
from pathlib import Path
from fusion.contracts import canonical,digest,require
from integration.single_node.reference_ops import Operator,PYTHON

SOURCE='''import os,json,time
from pathlib import Path
def sample():
 rows={};unreadable=0
 paths=[p for p in Path('/proc').iterdir() if p.name.isdecimal()];assert len(paths)<=512
 for p in paths:
  try:
   stat=(p/'stat').read_text().rsplit(')',1)[1].split();key=(p.name,stat[19])
   status=(p/'status').read_text();rss=next((int(s.split()[1])*1024 for s in status.splitlines() if s.startswith('VmRSS:')),0)
   rows[key]=dict(ticks=int(stat[11])+int(stat[12]),rss=rss)
  except (OSError,ValueError,IndexError):unreadable+=1
 return rows,unreadable
a,ae=sample();start=time.monotonic();time.sleep(2);b,be=sample();seconds=time.monotonic()-start
common=a.keys()&b.keys();cpu=sum(max(0,b[k]['ticks']-a[k]['ticks']) for k in common)/os.sysconf('SC_CLK_TCK')
print(json.dumps(dict(seconds=seconds,observed_ms=time.time_ns()//1000000,processes_start=len(a),processes_end=len(b),
 process_rss_sum_bytes=sum(v['rss'] for v in b.values()),cpu_seconds_common_processes=cpu,
 cpu_cores_common_processes=cpu/seconds,new_processes=len(b.keys()-a.keys()),exited_processes=len(a.keys()-b.keys()),
 unreadable=[ae,be],cpu_delta_censored_for_churn=True,rss_is_not_kernel_working_set=True,quota_enforcement='NOT_ESTABLISHED')))
'''

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('kubeconfig','context','namespace','output'):p.add_argument('--'+name,required=True)
    a=p.parse_args();op=Operator(a.kubeconfig,a.context,a.namespace);op.owned();path=Path(a.output);assert not path.exists()
    report=dict(namespace=op.namespace,classification='OWNER_POD_PROCESS_OBSERVATIONS_NOT_KERNEL_QUOTA_OR_PEAK_BENCHMARK',
        source_sha256=digest(Path(__file__).read_bytes()),additional_live_generations=0,roles={})
    try:
        pods=json.loads(op.k('get','pods','-l','app.kubernetes.io/instance=omega','-o','json'))['items']
        require(bool(pods),'NOT_AVAILABLE')
        for pod in pods:
            name=pod['metadata']['name']
            if name=='f1r3node-0':continue
            require(pod['status']['phase']=='Running' and any(c['type']=='Ready' and c['status']=='True' for c in pod['status'].get('conditions',[])),'NOT_AVAILABLE')
            report['roles'][name]=json.loads(op.k('exec','-i',name,'--',PYTHON,'-',data=SOURCE,timeout=15))
        require(bool(report['roles']),'NOT_AVAILABLE')
        report['status']='PASS'
    except BaseException as error:
        report.update(status='FAILED',failure=dict(type=type(error).__name__,code=getattr(error,'code',None)));raise
    finally:path.write_bytes(canonical(report))
    print(json.dumps(dict(status=report['status'],roles=len(report['roles']))))
if __name__=='__main__':main()
