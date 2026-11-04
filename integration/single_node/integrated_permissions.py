"""Metadata-only effective native capability explanation and batch preflight.

Reads this application's selected template/authority and retained provider
bindings. It never materializes an application, probes a service, accepts an
input, resolves a memory handle or executes a tool. Remote owner permission is
explicitly not inferred from this advisory local intersection.
"""
import json,time
from pathlib import Path
from fusion.contracts import canonical,digest,require,ContractError
from fusion.lookup_contracts import identity as uid
from fusion.policy import Policy
from fusion.preview_application import configuration
from fusion.preview_tools import SessionAuthority
from fusion.registry import selection_token
from fusion.sustained_sessions import SustainedSessionStore
from .sustained_current import observation_template

PROFILE='effective-native-capabilities/1'
ROUTE='/preview/capabilities'


def explain(catalogue,authority,principal,scope,now,commands,*,session_state,model_boundary,provider_states=None):
    require(authority.principal==principal and authority.scope==scope,'UNAUTHORIZED')
    require(commands is None or (type(commands) is list and len(canonical(commands))<=8192))
    denied=None
    try:authority.check(principal,now)
    except ContractError as error:denied=error.code
    rows=[]
    for name,tool in sorted(catalogue.tools.items()):
        enabled=denied is None and name in authority.tools
        rows.append(dict(command=name,tool_id=tool.tool_id,profile=tool.profile,
            arguments=[dict(name=x.name,kind=x.kind,max_utf8_bytes=x.max_bytes) for x in tool.arguments],
            effect=tool.effect,timeout_ms=tool.timeout_ms,attempt_limit=tool.attempts,max_result_bytes=tool.max_result_bytes,
            summary=tool.summary,semantics=tool.semantics,selected_scope=scope,
            recipient_rule='other configured agent in the same shared task scope' if name=='delegate' else 'selected owner scope; no new disclosure grant',
            configured=True,local_authority=enabled,denial=None if enabled else denied or 'TOOL_NOT_GRANTED',
            providers=[dict(interface=d.interface,version=d.version,profiles=sorted(d.profiles),selection=selection_token(d)) for d in catalogue.selections[name]]))
    admission=None
    if commands is not None:
        try:
            catalogue.admit(commands,authority,principal,now,catalogue.identity)
            for command in commands:
                if command[0]=='delegate':require(command[1]!=principal,'UNAUTHORIZED')
            admission=dict(admissible=True,reason=None,commands=len(commands))
        except ContractError as error:admission=dict(admissible=False,reason=error.code,commands=len(commands))
    provider_allows=all(x['current']['state']=='enabled' for x in provider_states.values()) if provider_states is not None else None
    if admission:
        admission['command_batch_admissible']=admission['admissible']
        if admission['admissible'] and session_state!='active':admission.update(admissible=False,reason='SESSION_NOT_ACTIVE')
        if admission['admissible'] and provider_allows is False:admission.update(admissible=False,reason='SELECTED_PROVIDER_DISABLED')
        if admission['admissible'] and model_boundary=='LIVE_APPROVAL_REQUIRED':admission.update(admissible=False,reason='MODEL_LIVE_APPROVAL_REQUIRED')
        admission.update(target_authority='NOT_RESOLVED',capacity='NOT_RESERVED',remote_permission='NOT_PROBED')
    return dict(profile=PROFILE,principal=principal,scope=scope,policy_revision=authority.revision,
        observed_ms=now,authority_expires_ms=authority.expires_ms,revoked=authority.revoked,
        catalogue= catalogue.identity,tools=rows,preflight=admission,session_state=session_state,
        model_boundary=model_boundary,live_generation='DISABLED_REQUIRES_SEPARATE_CAMPAIGN_APPROVAL',
        provider_lifecycle=provider_states,remote_owner_authority='RECHECKED_AT_EFFECT_AND_DISCLOSURE_NOT_PROBED',
        advisory=True,acceptance_created=False,deadline_started=False,effect_reserved=False,
        private_target_enumeration=False)


def invoke(path,state,run,credential,q):
    require(type(q) is dict and set(q)=={'profile','id','session','principal','commands'} and len(canonical(q))<=12288)
    require(q['profile']==PROFILE,'UNSUPPORTED_PROFILE');uid(q['id']);uid(q['session'])
    policy=Policy(path);actor=policy.authenticate(credential);cfg=policy.current()['native_sessions'];principal=cfg['principal']
    require(q['principal']==principal,'UNAUTHORIZED')
    def auth(who,scope,action):
        require(policy.authenticate(credential)==actor and who==principal,'UNAUTHORIZED')
        policy.check(actor,scope,'sessions.observe')
    store=SustainedSessionStore(cfg['database'],auth,cfg['allocation'])
    try:
        allocation=store.allocated(principal,q['session']);scope=allocation['frozen']['scope']
        session=store.observe(principal,q['session'])
        bindings=None
        if 'provider_registry' in cfg:
            from fusion.provider_lifecycle import Registry
            def registry_auth(selected,operation):
                auth(principal,selected,operation);policy.check(actor,selected,operation)
            reg=Registry(store,cfg['provider_registry'],registry_auth)
            selected=reg.selected(q['session'])
            bindings={key:dict(selection=value,current=reg.inspect(key)) for key,value in selected.items()}
    finally:store.close()
    directory=Path(run)/'sessions'/q['session'];appfile=directory/'application.json'
    require(not directory.is_symlink() and not appfile.is_symlink(),'UNAUTHORIZED')
    if appfile.exists():
        require(appfile.stat().st_size<=262144,'OVERLOADED');app=json.loads(appfile.read_bytes())
    else:app=observation_template(cfg['runtime_templates'][allocation['template']])
    require(app['preview']['scope']==scope,'CONFLICT');catalogue=configuration(app['preview'])
    require(catalogue.identity==allocation['frozen']['binding']['catalogue'],'CONFLICT')
    authority_file=Path(app['preview']['authority_file']);require(not authority_file.is_symlink() and authority_file.stat().st_size<=16384,'NOT_AVAILABLE')
    raw=json.loads(authority_file.read_bytes());authority=SessionAuthority(**{**raw,'tools':frozenset(raw['tools'])})
    result=explain(catalogue,authority,principal,scope,time.time_ns()//1000000,q['commands'],
        session_state=session['state'],model_boundary=allocation['frozen']['binding']['model_boundary'],provider_states=bindings)
    # No metadata response may survive revocation of the operator's scope while
    # reading it. Session/tool revocation is explained, never bypassed.
    auth(principal,scope,'observe')
    require(json.loads(authority_file.read_bytes())==raw,'CONFLICT')
    require(len(canonical(result))<=98304,'OVERLOADED')
    return dict(profile=PROFILE,id=q['id'],request_digest=digest(canonical(q)),actor=actor,value=result)
