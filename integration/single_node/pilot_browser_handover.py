"""Sanitized read of explicitly mounted external handover authority.

No owner journal, Kubernetes client, fencing assertion or mutation is present.
The installed handover operator remains the only plan/retire/activate path.
"""
from pathlib import Path
from fusion.contracts import digest,require,label
from fusion.preview_client import strict_json
from fusion.pilot_writer_fence import PROFILE,LIMIT,hash_value


def selection(value,namespace):
    require(type(value) is dict and set(value)=={'profile','authority_file','deployments'},'UNSUPPORTED_PROFILE')
    require(value['profile']==PROFILE and value['authority_file']=='/writer-authority/current.json','UNSUPPORTED_PROFILE')
    deployments=value['deployments']
    require(type(deployments) is list and 1<=len(deployments)<=2 and len(set(deployments))==len(deployments) and namespace in deployments,'UNAUTHORIZED')
    require(all(type(x) is str and x.startswith('omega-ref-pilot-') and len(x)<=63 for x in deployments),'UNAUTHORIZED')
    return value


def observe(selected,body,*,root=Path('/writer-authority')):
    require(type(body) is dict and set(body)=={'operation','expected_sha256'} and body['operation']=='observe','UNSUPPORTED_OPERATION')
    if body['expected_sha256'] is not None:hash_value(body['expected_sha256'])
    path=root/'current.json'
    require(path.resolve().is_relative_to(root.resolve()) and path.is_file() and path.stat().st_size<=262144,'UNAUTHORIZED')
    raw=path.read_bytes();fingerprint=digest(raw)
    require(body['expected_sha256'] in (None,fingerprint),'CONFLICT')
    value=strict_json(raw)
    require(value['profile']==PROFILE and value['synthetic_only'] is True and value['deployment'] in selected['deployments'],'UNAUTHORIZED')
    require(value['state'] in ('active','drained','retired') and type(value['generation']) is int and 1<=value['generation']<=LIMIT+1,'NOT_AVAILABLE')
    require(label(value['incarnation']),'NOT_AVAILABLE')
    require(type(value['history']) is list and len(value['history'])<=LIMIT,'NOT_AVAILABLE')
    latest=value['handover'] or (value['history'][-1] if value['history'] else None)
    checkpoint=None
    if latest:
        intent=latest['intent'];require(intent['original'] in selected['deployments'] and intent['replacement'] in selected['deployments'],'UNAUTHORIZED')
        checkpoint={k:hash_value(intent[k]) for k in ('checkpoint_sha256','closure_sha256')}
    return dict(profile=PROFILE,observation='EXTERNAL_AUTHORITY_SNAPSHOT_NOT_FENCING_PROOF',authority_sha256=fingerprint,
        deployment=value['deployment'],incarnation=value['incarnation'],generation=value['generation'],state=value['state'],
        checkpoint=checkpoint,operator_control='INSTALLED_HANDOVER_OPERATOR_ONLY',mutations_permitted=False)
