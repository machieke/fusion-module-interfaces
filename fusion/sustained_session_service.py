"""The /3 session operations on the existing authenticated application port."""
from pathlib import Path

from .contracts import ContractError, canonical, digest, require
from .policy import Policy
from .sustained_sessions import PROFILE, SustainedSessionStore


class SustainedSessionPorts:
    def __init__(self, path, wake=lambda session: None, hook=lambda _: None, projections=lambda _: ()):
        self.path, self.wake, self.hook, self.projections = Path(path), wake, hook, projections

    def invoke(self, credential, request):
        require(type(request) is dict and set(request)=={'id','profile','operation','body'})
        require(request['profile']==PROFILE,'UNSUPPORTED_PROFILE')
        require(type(request['id']) is str and 1<=len(request['id'])<=128)
        operation,body=request['operation'],request['body']
        require(type(operation) is str and operation in ('allocate','capacity','list','binding','submit','observe','pause','resume','close','archive','cancel','reconcile','next','permit','complete'),'UNSUPPORTED_OPERATION')
        require(len(canonical(request))<=(98304 if operation=='complete' else 16384))
        require(type(body) is dict)
        policy=Policy(self.path);actor=policy.authenticate(credential);cfg=policy.current()['native_sessions']
        require(cfg['profile']==PROFILE,'UNSUPPORTED_PROFILE'); principal=cfg['principal']
        def authorize(who, scope, action):
            require(policy.authenticate(credential)==actor and who==principal,'UNAUTHORIZED')
            policy.check(actor,scope,'sessions.'+operation)
            if action=='session.disclose':policy.check(actor,scope,'sessions.disclose')
        store=SustainedSessionStore(cfg['database'],authorize,cfg['allocation'],hook=self.hook)
        def fields(names):require(set(body)==set(names.split()))
        try:
            if operation=='allocate':
                fields('identity template');value=store.allocate(principal,body['identity'],body['template'])
            elif operation in ('capacity','list'):
                fields('');value=store.capacity(principal) if operation=='capacity' else store.list_sessions(principal)
            else:
                require(type(body.get('session')) is str);sid=body['session']
                # Frozen template equality and current actor authority precede
                # any observation, mutation, or worker wake after a rollout.
                store.allocated(principal,sid)
                if operation=='binding':
                    fields('session');accepted=store.allocated(principal,sid)
                    observed=store.observe(principal,sid)
                    value=dict(session=sid,principal=principal,scope=accepted['frozen']['scope'],
                        state=observed['state'],expires_ms=accepted['expires_ms'])
                elif operation=='submit':
                    fields('session identity text assignment')
                    require(type(body['assignment']) is str and body['assignment'] in cfg['assignments'],'UNAUTHORIZED')
                    value=store.submit(principal,sid,body['identity'],body['text'],body['assignment'])
                elif operation=='observe':
                    require(set(body) in ({'session','content'},{'session','content','after'}))
                    require(type(body['content']) is bool)
                    value=store.observe(principal,sid,body['content'],after=body.get('after',0))
                elif operation in ('pause','resume','close','archive'):
                    fields('session identity');value=store.control(principal,sid,body['identity'],operation)
                elif operation=='cancel':
                    fields('session identity target');value=store.cancel(principal,sid,body['identity'],body['target'])
                elif operation=='reconcile':
                    fields('session');store.reconcile(principal,sid)
                    # The server's application-owned read-only observer, never
                    # wire-supplied projections, can attest saved native turns.
                    proofs=self.projections(sid);require(type(proofs) in (list,tuple) and len(proofs)<=32,'OVERLOADED')
                    for proof in proofs:
                        require(type(proof) is dict and set(proof)=={'identity','result'},'CONFLICT')
                        worker=policy.current()['principals']['worker']['credential']
                        self.invoke(worker,dict(id='saved-native-projection',profile=PROFILE,operation='complete',
                            body=dict(session=sid,**proof)))
                    value=store.observe(principal,sid)
                elif operation=='next':
                    fields('session');value=store.next_input(principal,sid)
                elif operation=='permit':
                    fields('session identity');value=store.permit(principal,sid,body['identity'])
                else:
                    fields('session identity result');value=store.complete(principal,sid,body['identity'],body['result'])
                if operation in ('submit','resume'):
                    try:self.wake(sid)
                    except (OSError,RuntimeError,ContractError):
                        value=dict(value,worker='NOT_AVAILABLE',acceptance_retained=True)
            return dict(id=request['id'],profile=PROFILE,request_digest=digest(canonical(request)),
                        actor=actor,principal=principal,value=value)
        finally:store.close()
