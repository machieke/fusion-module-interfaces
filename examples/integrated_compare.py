"""Offline comparison of captured equal-workload native qualification reports.

Does not run providers, repair failed samples or infer absent telemetry as zero.
The workload/evaluator stays outside the native and provider implementations.
"""
import argparse,json,math,statistics
from pathlib import Path
from fusion.contracts import canonical,digest,require


def samples(values):
    if not values:return dict(n=0,median=None,p95=None,maximum=None,quantile='nearest-rank')
    values=sorted(values)
    return dict(n=len(values),median=statistics.median(values),p95=values[math.ceil(.95*len(values))-1],maximum=max(values),quantile='nearest-rank')


def comparison(directories):
    rows=[]
    for directory in directories:
        root=Path(directory);raw=(root/'report.json').read_bytes();r=json.loads(raw)
        n=json.loads((root/'native/report.json').read_bytes());stages=r.get('telemetry',{})
        count=r.get('benchmark_input_count',r.get('operator_inputs',len(n['inputs'])))
        measured=n['inputs'][:count];complete=[];classes={};failed=[]
        for item in measured:
            if item.get('observed',{}).get('state')!='complete' or 'finished_ms' not in item:
                failed.append(dict(operation=item['command'].split()[0],state=item.get('observed',{}).get('state','UNKNOWN'),
                    accepted=item.get('accepted') is not None,completion_latency='CENSORED_NOT_ZERO'));continue
            elapsed=(item['finished_ms']-item['started_ms'])/1000
            complete.append(elapsed);classes.setdefault(item['command'].split()[0],[]).append(elapsed)
        bytes_by_owner={};counts={};missing=[]
        for role,value in stages.items():
            counts[role]={k:v['count'] for k,v in value.get('stages',{}).items()}
            bytes_by_owner[role]={k:v['bytes'] for k,v in value.get('stages',{}).items() if 'bytes' in v}
            if value.get('status')!='OBSERVED':missing.append(role+':'+value.get('status','UNKNOWN'))
            if not bytes_by_owner[role]:missing.append(role+':BYTE_SAMPLES_UNAVAILABLE')
        workers=r.get('worker_observations',{})
        native_processes=sum(len(v.get('native_inputs_by_pid',{})) for v in workers.values()) if workers else None
        native_inputs=sum(sum(v.get('native_inputs_by_pid',{}).values()) for v in workers.values()) if workers else None
        rows.append(dict(run=root.name,status=r['status'],workload=r['workload_sha256'],images=r.get('selected_images'),
            observations_sha256=digest(raw),attempted_operator_inputs=len(measured),complete_operator_inputs=len(complete),
            completion_seconds=samples(complete),per_operation_seconds={k:samples(v) for k,v in classes.items()},
            censored_or_failed=failed,native_processes=native_processes,native_inputs=native_inputs,
            native_inputs_per_interpreter=native_inputs/native_processes if native_processes else None,
            stage_counts=counts,stage_bytes=bytes_by_owner,provider_local_stages=stages,
            process_samples=r.get('process_samples','NOT_COLLECTED'),missing=missing,
            source_observations=n.get('source_observations',[])))
    require(rows and len({r['workload'] for r in rows})==1,'CONFLICT')
    return dict(profile='equal-native-workload-comparison/2',rows=rows,equal_workload=True,
        additional_live_generations=0,model='RECORDED_COMMAND_PROPOSALS_REAL_NATIVE_TOOLS',
        latency_interval='operator submit start through observed committed native completion; includes polling overhead',
        attribution='Compare explicitly selected combinations. Per-operation sample sizes are shown; no isolated-factor or live-model inference.',
        critical_path='Only local recorded parent relationships are available. Nested spans and cross-owner medians are never added.',
        cpu_quota='NOT_ESTABLISHED',claims=dict(production_sla=False,live_generation_throughput=False,multi_host=False))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('directories',nargs='+');p.add_argument('--output',required=True);a=p.parse_args()
    path=Path(a.output);require(not path.exists(),'CONFLICT');path.write_bytes(canonical(comparison(a.directories)))
