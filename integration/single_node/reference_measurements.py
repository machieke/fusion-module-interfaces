"""Summarize already captured synthetic observations, never execute workload.

Small samples expose ranges and medians, not reliability or throughput claims.
Publication intervals use application observation timestamps; they include RPC,
native processing and durable commits and are not pure storage engine latency.
"""
import argparse,json,statistics
from pathlib import Path
from .reference_artifacts import sha

def summary(values):
 return dict(n=len(values),minimum=min(values),median=statistics.median(values),maximum=max(values)) if values else dict(n=0,status='UNAVAILABLE')

def extract(path):
 d=json.loads(path.read_text());assert d['case']=='correct' and d['status']=='PASS' and d['workflow_pass']
 final=d['observations']['final'];app=final['omega-agent'];measured=app['measured.sqlite']
 timings={}
 pairs={'storage_acceptance_observed_ms':('vector-captured','enrollment-accepted'),'index_publication_observed_ms':('enrollment-accepted','search-published'),'local_readiness_observed_ms':('search-published','metadata-ready'),'remember_observed_ms':('identity-and-time','native-success-captured')}
 for key,(start,end) in pairs.items():
  timings[key]=[o[end]-o[start] for w in app['app_memory_writes'] if (o:=json.loads(w['observations'])) and start in o and end in o]
 timings['native_e5_ms']=[r['duration_ms'] for r in final['fusion-embedding']['encode_attempts'] if r['finished']]
 vectors=[json.loads(r['measurement']) for r in app['app_memory_vectors']+measured['app_query_vectors'] if r.get('measurement')]
 for key in ('elapsed_ms','request_body_bytes','response_body_bytes'):timings['embedding_rpc_'+key]=[v[key] for v in vectors]
 timings['query_retrieval_ms']=[r['retrieval_ms'] for r in measured['app_query_vectors'] if r.get('retrieval_ms') is not None]
 roles={}
 for role,v in d['resources']['samples'].items():
  if 'error' in v:roles[role]=dict(error=v['error']);continue
  roles[role]=dict(rss_bytes=sum(x['rss_bytes'] for x in v['processes']),process_cpu_seconds=sum(x['cpu_ticks'] for x in v['processes'])/v['cpu_ticks_per_second'],state_bytes=v['state_bytes'],cgroup=v['cgroup'])
 rtt={}
 for role,rows in d['resources']['health_rtt'].items():
  good=[x for x in rows if x.get('http')==200]
  rtt[role]=dict(successes=len(good),errors=[x.get('error',x.get('http')) for x in rows if x not in good],milliseconds=summary([x['ns']/1e6 for x in good]),response_bytes=summary([x['bytes'] for x in good]))
 images={x['metadata']['name']:[c.get('imageID') for c in x.get('status',{}).get('containerStatuses',[])] for x in d['pods']['items']}
 return dict(report=str(path),sha256=sha(path),namespace=d['namespace'],images=images,cold_setup_seconds=d['cold_setup_seconds'],full_workflow_seconds=d['full_workflow_seconds'],operation_observations=timings,roles=roles,health_rtt=rtt,model='two explicitly recorded responses; no live generation')

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('reports',nargs='+',type=Path);a=p.parse_args();runs=[extract(x) for x in a.reports]
 combined={key:summary([v for r in runs for v in r['operation_observations'][key]]) for key in runs[0]['operation_observations']}
 value=dict(schema='reference-resource-baseline/1',samples=len(runs),concurrency=1,memories_per_session=2,percentiles='NOT_ESTIMATED: deliberately small sample',cache='new PVCs and processes; cached images/native/model files on same node',cold_setup_seconds=summary([r['cold_setup_seconds'] for r in runs]),full_workflow_seconds=summary([r['full_workflow_seconds'] for r in runs]),operations=combined,runs=runs,limits=['observer process included in CPU/RSS','cgroup peak includes page cache and native children','health RTT does not submit accepted work','application observation intervals are end-to-end stage bounds, not engine benchmarks','no concurrent or live-model throughput claim','denied non-dependency health edges are retained errors'],additional_live_generations=0)
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(value,indent=2)+'\n');print(json.dumps({k:v for k,v in value.items() if k!='runs'},indent=2))
if __name__=='__main__':main()
