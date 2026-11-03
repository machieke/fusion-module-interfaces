"""Bounded payload-free stage observations from this pod's own state volume."""
import json,statistics
from pathlib import Path
from fusion.contracts import require


def collect(root='/state'):
    root=Path(root);paths=sorted(root.rglob('native-stages.jsonl'))
    require(len(paths)<=40,'OVERLOADED');groups={};files=[];processes=set();errors=[]
    for ordinal,path in enumerate(paths):
        require(not path.is_symlink() and path.stat().st_size<=4194304,'NOT_AVAILABLE')
        truncated=path.with_suffix('.truncated').exists();count=0
        for line in path.read_bytes().splitlines():
            row=json.loads(line);require(row['profile']=='bounded-native-stage-timing/1','UNSUPPORTED_PROFILE')
            require(type(row['duration_ns']) is int and row['duration_ns']>=0,'NOT_AVAILABLE')
            groups.setdefault(row['name'],[]).append(row['duration_ns']);processes.add(row['process']);count+=1
            if row['code']:errors.append(dict(name=row['name'],code=row['code']))
        files.append(dict(file_ordinal=ordinal,bytes=path.stat().st_size,spans=count,truncated=truncated))
    summary={name:dict(count=len(values),total_ms=sum(values)/1e6,min_ms=min(values)/1e6,max_ms=max(values)/1e6,
        median_ms=statistics.median(values)/1e6,p95_ms=sorted(values)[min(len(values)-1,int(.95*len(values))) ]/1e6) for name,values in groups.items()}
    return dict(profile='bounded-native-stage-summary/1',status='OBSERVED' if paths and not any(x['truncated'] for x in files) else 'MISSING_OR_TRUNCATED',
        files=files,stages=summary,processes=len(processes),errors=errors[-64:],errors_total=len(errors),nested_durations_are_not_additive=True,
        interpretation='sampled executed methods only; no private text, prompt, credentials or authority',
        physical_state_bytes=sum(p.stat().st_size for p in root.rglob('*') if p.is_file() and not p.is_symlink()))

if __name__=='__main__':print(json.dumps(collect()))
