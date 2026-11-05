"""Bounded session commands through authenticated HTTPS, from the operator pod.

The outer reference operator uses kubectl exec with this installed module. It
does not inspect native/provider journals or submit tools on the agent's behalf.
Mounted credentials are never returned. Session content requires disclosure.
"""
import argparse
import json
from pathlib import Path
import uuid
import time
from fusion.contracts import canonical, digest, require
from fusion.preview_sessions import PROFILE
from fusion.preview_transport import invoke


def inventory(owner='/run/fusion/owner.json',run='/run/fusion',state='/state'):
    from fusion.policy import Policy
    from fusion.preview_application import configuration
    from fusion.preview_tools import SessionAuthority
    policy=Policy(owner);full=policy.current();cfg=full['native_sessions']
    if cfg['profile']=='omega-native-sessions/3':
        from .sustained_operator import inventory as sustained_inventory
        return sustained_inventory(owner,run,state)
    require(cfg['profile']==PROFILE and cfg['model_boundary']=='RECORDED_FIXTURE','UNSUPPORTED_PROFILE')
    actor=policy.authenticate(full['principals']['operator']['credential'])
    require(actor=='operator','UNAUTHORIZED');policy.check(actor,cfg['scope'],'sessions.observe')
    tools={};policies={}
    for sid in cfg['session_templates']:
        app=json.loads((Path(run)/'sessions'/sid/'application.json').read_text())['preview']
        selected=configuration(app)
        raw=json.loads(Path(app['authority_file']).read_text())
        require(set(raw)=={'principal','scope','tools','revision','expires_ms','revoked'})
        require(type(raw['tools']) is list and all(type(t) is str for t in raw['tools']) and len(set(raw['tools']))==len(raw['tools']))
        authority=SessionAuthority(**dict(raw,tools=frozenset(raw['tools'])))
        authority.check(cfg['principal'],time.time_ns()//1_000_000)
        require(authority.scope==cfg['scope']==app['scope'],'UNAUTHORIZED')
        binding=selected.binding()
        binding['tools']={k:v for k,v in binding['tools'].items() if k in authority.tools}
        tools[sid]=binding;policies[sid]=raw
    status=Path(state)/'worker-status.json'
    return dict(principal=cfg['principal'],scope=cfg['scope'],sessions=cfg['session_templates'],
        assignments=cfg['assignments'],catalogues=tools,policies=policies,
        worker=json.loads(status.read_text()) if status.exists() else None,
        model_boundary='RECORDED_FIXTURE',additional_live_generations=0)


def request(operation, session, body, owner='/run/fusion/owner.json', component='/config/component.json'):
    cfg=json.loads(Path(owner).read_text());settings=json.loads(Path(component).read_text())
    selected=cfg['native_sessions'];profile=selected['profile']
    if profile==PROFILE:require(session in selected['session_templates'],'UNAUTHORIZED')
    else:require(profile=='omega-native-sessions/3','UNSUPPORTED_PROFILE')
    payload=body if profile=='omega-native-sessions/3' and operation in ('allocate','capacity','list') else dict(session=session,**body)
    wire=dict(id=str(uuid.uuid4()),profile=profile,operation=operation,body=payload)
    transport=dict(endpoint=dict(host=settings['peers'][settings['role']],port=settings['https_port'],ca_file='/secrets/ca.crt'),
                   credential=cfg['principals']['operator']['credential'])
    reply=invoke(transport,'/preview/session',wire)
    require(type(reply) is dict and set(reply)=={'id','profile','request_digest','actor','principal','value'} and reply.get('profile')==profile and reply.get('id')==wire['id'] and reply.get('request_digest')==digest(canonical(wire)),'NOT_AVAILABLE')
    require(reply.get('actor')=='operator' and reply.get('principal')==selected['principal'],'UNAUTHORIZED')
    return reply['value']


def projection(body, owner='/run/fusion/owner.json', component='/config/component.json'):
    """Submit the exact operator-approved projection through its owner port.

    The request file is supplied by the operator inside this owner; it is not
    generated from model arguments or a default consent flag.
    """
    from .sustained_projection import PROFILE as projection_profile
    cfg=json.loads(Path(owner).read_bytes());settings=json.loads(Path(component).read_bytes())
    require(type(body) is dict and body.get('profile')==projection_profile,'UNSUPPORTED_PROFILE')
    transport=dict(endpoint=dict(host=settings['peers'][settings['role']],port=settings['https_port'],ca_file='/secrets/ca.crt'),
                   credential=cfg['principals']['operator']['credential'])
    value=invoke(transport,'/preview/projection',body)
    require(type(value) is dict and set(value)=={'profile','shared','empirical_evidence','private_source_disclosed'}
            and value['profile']==projection_profile and value['empirical_evidence'] is False
            and value['private_source_disclosed'] is False,'NOT_AVAILABLE')
    from fusion.contracts import validate_ref
    validate_ref(value['shared'],body['recipient_scope'])
    return value


def chain_continuation(body,owner='/run/fusion/owner.json',component='/config/component.json'):
    """Explicit transition/read, separate from ordinary refresh and native tools."""
    from .integrated_chain_continuation import PROFILE,ROUTE
    require(type(body) is dict and body.get('profile')==PROFILE,'UNSUPPORTED_PROFILE')
    cfg=json.loads(Path(owner).read_bytes());settings=json.loads(Path(component).read_bytes())
    transport=dict(endpoint=dict(host=settings['peers'][settings['role']],port=settings['https_port'],ca_file='/secrets/ca.crt'),
        credential=cfg['principals']['operator']['credential'])
    reply=invoke(transport,ROUTE,body,time.time_ns()//1000000+30000)
    require(type(reply) is dict and set(reply)=={'profile','id','request_digest','actor','value'} and
        reply['profile']==PROFILE and reply['id']==body['id'] and reply['request_digest']==digest(canonical(body)) and
        reply['actor']=='operator','NOT_AVAILABLE')
    value=reply['value'];require(type(value) is dict and value.get('profile')==PROFILE and
        value.get('occurrence')==body['occurrence'] and value.get('automatic_resubmissions')==0,'NOT_AVAILABLE')
    return value


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('operation',choices=['inventory','create','submit','observe','pause','resume','close','chain-observe','allocate','list','capacity','cancel','reconcile','archive','current','project','providers','continuation','capabilities','worker-control'])
    p.add_argument('--session');p.add_argument('--identity');p.add_argument('--text');p.add_argument('--assignment');p.add_argument('--content',action='store_true');p.add_argument('--after',type=int,default=0)
    p.add_argument('--template');p.add_argument('--target');p.add_argument('--request-file')
    p.add_argument('--provider');p.add_argument('--provider-action',choices=['inspect','selected','probe','add','enable','disable','drain','retire','plan','seal','headroom']);p.add_argument('--retained',choices=['required','explicit-unavailable'],default='required')
    p.add_argument('--head');p.add_argument('--occurrence');p.add_argument('--continuation-action',choices=['observe','cancel','unsubscribe'],default='observe')
    p.add_argument('--worker-action',choices=['observe','drain','recycle','resume'],default='observe')
    a=p.parse_args();body={}
    if a.operation=='worker-control':
        print(json.dumps(worker_control(a.session,a.worker_action,a.identity)));return
    if a.operation=='capabilities':
        print(json.dumps(capabilities(a.session,json.loads(Path(a.request_file).read_bytes()) if a.request_file else None)));return
    if a.operation=='continuation':
        print(json.dumps(continuation(a.session,a.occurrence,a.continuation_action,a.identity)));return
    if a.operation=='providers':
        print(json.dumps(providers(a.provider_action,a.provider,a.identity,a.session,a.retained,head=a.head)));return
    if a.operation=='project':
        require(a.request_file is not None)
        print(json.dumps(projection(json.loads(Path(a.request_file).read_bytes()))));return
    if a.operation=='current':
        require(a.session is not None)
        from .sustained_current import observe
        print(json.dumps(observe(a.session)));return
    if a.operation=='chain-observe':
        print(json.dumps(chain_observe()));return
    if a.operation=='inventory':
        print(json.dumps(inventory()))
        return
    if a.operation not in ('allocate','list','capacity'):require(a.session is not None)
    if a.operation in ('submit','pause','resume','close','archive','cancel','allocate'):
        require(a.identity is not None);body['identity']=a.identity
    if a.operation=='allocate':require(a.template is not None);body['template']=a.template
    if a.operation=='cancel':require(a.target is not None);body['target']=a.target
    if a.operation=='submit':require(a.text is not None and a.assignment is not None);body.update(text=a.text,assignment=a.assignment)
    if a.operation=='observe':body.update(content=a.content,after=a.after)
    print(json.dumps(request(a.operation,a.session,body),sort_keys=True))


def chain_observe(component='/config/component.json'):
    """Explicit bounded observation, never invoked by health or page refresh."""
    import tempfile
    from fusion.preview_chain import Client
    settings=json.loads(Path(component).read_text());p=settings['preview']
    require(p['scope'].startswith('synthetic-'),'UNAUTHORIZED')
    chain=p.get('chain',{})
    if not chain.get('enabled') or chain.get('registration') is None:return dict(state='NOT_REGISTERED',submission='NOT_REQUESTED')
    reg=chain['registration'];cfg=dict(endpoint=dict(host=settings['peers']['fusion-commitment'],port=settings['https_port'],ca_file='/secrets/ca.crt'),
        credential=Path('/secrets/fusion-commitment-token').read_text().strip(),registration=reg)
    with tempfile.TemporaryDirectory(dir='/run/fusion') as directory:
        file=Path(directory)/'observer.json';file.write_bytes(canonical(cfg));file.chmod(0o600);client=Client(file)
        intent=client.call('intent',{})
        observed=client.call('observe',{'deploy_id':intent['deploy_id']}) if intent else None
    return dict(state=observed['effect_finality'] if observed else 'NO_SIGNED_INTENT',registration_sha256=digest(canonical(reg)),
        artifact=reg['artifact'],inspection=reg['result'],intent=intent,observation=observed,submission='NOT_REQUESTED')

def providers(operation,provider=None,identity=None,session=None,retained='required',owner='/run/fusion/owner.json',component='/config/component.json',head=None):
    from fusion.provider_lifecycle import PROFILE as registry_profile
    cfg=json.loads(Path(owner).read_bytes());settings=json.loads(Path(component).read_bytes())
    registry_profile=cfg['native_sessions']['provider_registry']['profile']
    require(operation in ('inspect','selected','probe','add','enable','disable','drain','retire','plan','seal','headroom'),'UNSUPPORTED_OPERATION')
    body={} if operation=='headroom' else {'session':session} if operation=='selected' else {'provider':provider}
    if operation not in ('inspect','selected','plan','headroom'):require(identity is not None);body['identity']=identity
    if operation=='retire':body['retained']=retained
    if operation=='seal':require(type(head) is str and len(head)==64);body['head']=head
    q=dict(id=str(uuid.uuid4()),profile=registry_profile,operation=operation,body=body)
    transport=dict(endpoint=dict(host=settings['peers'][settings['role']],port=settings['https_port'],ca_file=str(Path(cfg['tls_certificate']).parent/'ca.crt')),
                   credential=cfg['principals']['operator']['credential'])
    value=invoke(transport,'/preview/providers',q)
    require(type(value) is dict and set(value)=={'id','profile','request_digest','actor','value'} and
        (value['id'],value['profile'],value['request_digest'],value['actor'])==(q['id'],registry_profile,digest(canonical(q)),'operator'),'NOT_AVAILABLE')
    return value['value']

def continuation(session,occurrence,operation='observe',identity=None,owner='/run/fusion/owner.json',component='/config/component.json'):
    from fusion.inspection_continuation import PROFILE as continuation_profile
    cfg=json.loads(Path(owner).read_bytes());settings=json.loads(Path(component).read_bytes())
    q=dict(profile=continuation_profile,id=str(uuid.uuid4()),operation=operation,session=session,occurrence=occurrence,identity=identity)
    transport=dict(endpoint=dict(host=settings['peers'][settings['role']],port=settings['https_port'],ca_file=str(Path(cfg['tls_certificate']).parent/'ca.crt')),
        credential=cfg['principals']['operator']['credential'])
    value=invoke(transport,'/preview/continuation',q)
    require(type(value) is dict and set(value)=={'profile','id','request_digest','actor','value'} and
        (value['profile'],value['id'],value['request_digest'],value['actor'])==(continuation_profile,q['id'],digest(canonical(q)),'operator'),'NOT_AVAILABLE')
    return value['value']

def capabilities(session,commands=None,owner='/run/fusion/owner.json',component='/config/component.json'):
    from .integrated_permissions import PROFILE,ROUTE
    cfg=json.loads(Path(owner).read_bytes());settings=json.loads(Path(component).read_bytes())
    q=dict(profile=PROFILE,id=str(uuid.uuid4()),session=session,principal=cfg['native_sessions']['principal'],commands=commands)
    transport=dict(endpoint=dict(host=settings['peers'][settings['role']],port=settings['https_port'],ca_file=str(Path(cfg['tls_certificate']).parent/'ca.crt')),
        credential=cfg['principals']['operator']['credential'])
    reply=invoke(transport,ROUTE,q)
    require(type(reply) is dict and set(reply)=={'profile','id','request_digest','actor','value'} and
        (reply['profile'],reply['id'],reply['request_digest'],reply['actor'])==(PROFILE,q['id'],digest(canonical(q)),'operator'),'NOT_AVAILABLE')
    value=reply['value'];require(type(value) is dict and value.get('profile')==PROFILE and value.get('principal')==q['principal'] and
        value.get('advisory') is True and value.get('acceptance_created') is False and value.get('deadline_started') is False and
        value.get('effect_reserved') is False and type(value.get('tools')) is list and len(value['tools'])<=32,'NOT_AVAILABLE')
    return value

def worker_control(session,operation='observe',identity=None,owner='/run/fusion/owner.json',component='/config/component.json'):
    from fusion.resident_workers import CONTROL
    from .integrated_worker_control import ROUTE
    cfg=json.loads(Path(owner).read_bytes());settings=json.loads(Path(component).read_bytes())
    q=dict(profile=CONTROL,id=str(uuid.uuid4()),session=session,operation=operation,identity=identity)
    transport=dict(endpoint=dict(host=settings['peers'][settings['role']],port=settings['https_port'],ca_file=str(Path(cfg['tls_certificate']).parent/'ca.crt')),
        credential=cfg['principals']['operator']['credential'])
    reply=invoke(transport,ROUTE,q)
    require(type(reply) is dict and set(reply)=={'profile','id','request_digest','actor','value'} and
        (reply['profile'],reply['id'],reply['request_digest'],reply['actor'])==(CONTROL,q['id'],digest(canonical(q)),'operator'),'NOT_AVAILABLE')
    value=reply['value'];require(type(value) is dict and value.get('profile')==CONTROL and value.get('session')==session and
        value.get('mode') in ('enabled','draining') and value.get('deadlines_reset') is False and value.get('effect_budget_refund') is False and value.get('automatic_resubmission') is False,'NOT_AVAILABLE')
    if operation!='observe':require(value.get('identity')==identity and value.get('operation')==operation,'NOT_AVAILABLE')
    return value

if __name__=='__main__':main()
