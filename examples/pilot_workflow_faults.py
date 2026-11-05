"""Finite task-owned storage outage/current-credential fault for workflow guards.

Only the namespace's declared provider changes. No owner journal or accepted
input is edited. Credentials never leave memory or enter evidence reports.
"""
import base64,json,secrets
from contextlib import contextmanager
from fusion.contracts import require
from integration.single_node.preview_recovery_qualification import Recovery


@contextmanager
def storage_guard_fault(op,variant,report):
    require(variant in ('unknown','unauthorized'),'INVALID_ARGUMENT');op.owned()
    require(op.namespace.startswith('omega-ref-pilot-'),'UNAUTHORIZED')
    role='fusion-storage';q=Recovery.__new__(Recovery);q.op=op
    current=json.loads(op.k('get','statefulset',role,'-o','json'))
    require(current['spec']['replicas']==1,'CONFLICT')
    before=q.pod(role);prior=None;changed=False
    report.update(kind=variant,owner=role,before=before,accepted_inputs_changed=False,
        budgets_refunded=False,deadline_extensions=False,credential_material='NOT_EXPORTED')
    try:
        if variant=='unknown':
            changed=True;op.k('scale','statefulset',role,'--replicas=0')
            op.k('wait','--for=delete','pod/'+role+'-0','--timeout=90s',timeout=100)
            require(json.loads(op.k('get','statefulset',role,'-o','json'))['spec']['replicas']==0,'CONFLICT')
            report['fault']='REAL_STORAGE_OWNER_STOPPED'
        else:
            secret=json.loads(op.k('get','secret',role+'-tls-auth','-o','json'))
            # S01 and memory share principal A in this storage owner. Startup
            # requires both selected aliases to agree; rotating just the memory
            # alias tests startup refusal rather than current authorization.
            aliases=('caller-token','caller-A-token')
            require(all(k in secret['data'] for k in aliases),'CONFLICT')
            prior={k:secret['data'][k] for k in aliases}
            require(len(set(prior.values()))==1,'CONFLICT')
            new=base64.b64encode(secrets.token_hex(32).encode()).decode()
            require(new not in prior.values(),'CONFLICT')
            for key in aliases:secret['data'][key]=new
            changed=True;op.k('replace','-f','-',data=json.dumps(secret))
            report['replacement']=q.replace([role]);report['fault']='REAL_PROVIDER_REJECTS_UNROTATED_CALLER_CREDENTIAL'
        yield
    finally:
        if changed:
            if variant=='unknown':
                op.k('scale','statefulset',role,'--replicas=1')
                op.k('wait','--for=condition=Ready','pod/'+role+'-0','--timeout=90s',timeout=100)
            else:
                restored=json.loads(op.k('get','secret',role+'-tls-auth','-o','json'))
                for key,value in prior.items():restored['data'][key]=value
                op.k('replace','-f','-',data=json.dumps(restored))
                report['restoration_replacement']=q.replace([role])
            after=q.pod(role)
            require(after['images']==before['images'] and after['volumes']==before['volumes'],'CONFLICT')
            report.update(after=after,original_provider_placement_restored=True)
