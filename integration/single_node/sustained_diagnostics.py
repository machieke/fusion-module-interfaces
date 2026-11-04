"""Bounded payload-free stage observations from this pod's own state volume."""
import json,math,statistics
from pathlib import Path
from fusion.contracts import require


def collect(root='/state'):
    root=Path(root);paths=sorted(root.rglob('native-stages.jsonl'))
    require(len(paths)<=40,'OVERLOADED');groups={};files=[];processes=set();errors=[];sizes={};edges=0;unbound=0
    for ordinal,path in enumerate(paths):
        require(not path.is_symlink() and path.stat().st_size<=4194304,'NOT_AVAILABLE')
        truncated=path.with_suffix('.truncated').exists();count=0;rows=[]
        for line in path.read_bytes().splitlines():
            row=json.loads(line);require(row['profile']=='bounded-native-stage-timing/1','UNSUPPORTED_PROFILE')
            require(type(row['duration_ns']) is int and row['duration_ns']>=0,'NOT_AVAILABLE')
            groups.setdefault(row['name'],[]).append(row['duration_ns']);processes.add(row['process']);count+=1
            rows.append(row)
            for field in ('request_bytes','response_bytes'):
                amount=row.get(field);require(amount is None or type(amount) is int and amount>=0,'NOT_AVAILABLE')
                sizes.setdefault(row['name'],{}).setdefault(field,[]).append(amount)
            if row['code']:errors.append(dict(name=row['name'],code=row['code']))
        files.append(dict(file_ordinal=ordinal,bytes=path.stat().st_size,spans=count,truncated=truncated))
        identities={(row['process'],row['span']) for row in rows}
        for row in rows:
            if row['parent'] is not None:
                if (row['process'],row['parent']) in identities:edges+=1
                else:unbound+=1
    summary={name:dict(count=len(values),total_ms=sum(values)/1e6,min_ms=min(values)/1e6,max_ms=max(values)/1e6,
        median_ms=statistics.median(values)/1e6,p95_ms=sorted(values)[math.ceil(.95*len(values))-1]/1e6,
        bytes={field:dict(observed_samples=sum(v is not None for v in samples),unknown_samples=sum(v is None for v in samples),
                         observed_total=sum(v for v in samples if v is not None)) for field,samples in sizes[name].items()}) for name,values in groups.items()}
    return dict(profile='bounded-native-stage-summary/1',status='OBSERVED' if paths and not any(x['truncated'] for x in files) else 'MISSING_OR_TRUNCATED',
        files=files,stages=summary,processes=len(processes),errors=errors[-64:],errors_total=len(errors),nested_durations_are_not_additive=True,
        quantile='nearest-rank',observed_local_parent_edges=edges,missing_parent_spans=unbound,
        cross_process_critical_path='NOT_INFERRED_FROM_LOCAL_CLOCKS_OR_SUMMED_MEDIANS',
        interpretation='sampled executed methods only; no private text, prompt, credentials or authority',
        physical_state_bytes=sum(p.stat().st_size for p in root.rglob('*') if p.is_file() and not p.is_symlink()))

if __name__=='__main__':print(json.dumps(collect()))
