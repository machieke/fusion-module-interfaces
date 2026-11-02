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
    selected=cfg['native_sessions'];require(session in selected['session_templates'],'UNAUTHORIZED')
    wire=dict(id=str(uuid.uuid4()),profile=PROFILE,operation=operation,body=dict(session=session,**body))
    transport=dict(endpoint=dict(host=settings['peers'][settings['role']],port=settings['https_port'],ca_file='/secrets/ca.crt'),
                   credential=cfg['principals']['operator']['credential'])
    reply=invoke(transport,'/preview/session',wire)
    require(type(reply) is dict and set(reply)=={'id','profile','request_digest','actor','principal','value'} and reply.get('profile')==PROFILE and reply.get('id')==wire['id'] and reply.get('request_digest')==digest(canonical(wire)),'NOT_AVAILABLE')
    require(reply.get('actor')=='operator' and reply.get('principal')==selected['principal'],'UNAUTHORIZED')
    return reply['value']


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('operation',choices=['inventory','create','submit','observe','pause','resume','close','chain-observe'])
    p.add_argument('--session');p.add_argument('--identity');p.add_argument('--text');p.add_argument('--assignment');p.add_argument('--content',action='store_true');p.add_argument('--after',type=int,default=0)
    a=p.parse_args();body={}
    if a.operation=='chain-observe':
        print(json.dumps(chain_observe()));return
    if a.operation=='inventory':
        print(json.dumps(inventory()))
        return
    require(a.session is not None)
    if a.operation in ('submit','pause','resume','close'):
        require(a.identity is not None);body['identity']=a.identity
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

if __name__=='__main__':main()
