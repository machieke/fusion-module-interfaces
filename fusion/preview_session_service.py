"""Bounded authenticated session API over the application owner's inbox.

Operator selection comes from frozen templates. Worker consumption/completion
use separate permissions. Neither reading nor HTTP acceptance runs a tool.
"""
from pathlib import Path
import json

from .contracts import ContractError, canonical, digest, require
from .policy import Policy
from .preview_sessions import SessionStore, PROFILE


class SessionPorts:
    def __init__(self, path, wake=lambda session: None):
        self.path, self.wake = Path(path), wake

    def invoke(self, credential, request):
        require(type(request) is dict and set(request) == {'id', 'profile', 'operation', 'body'})
        require(request['profile'] == PROFILE, 'UNSUPPORTED_PROFILE')
        require(type(request['id']) is str and 1 <= len(request['id']) <= 128)
        require(len(canonical(request)) <= (98304 if request['operation']=='complete' else 16384))
        policy = Policy(self.path)
        actor = policy.authenticate(credential)
        cfg = policy.current()['native_sessions']
        require(cfg['profile'] == PROFILE and cfg['model_boundary'] == 'RECORDED_FIXTURE', 'UNSUPPORTED_PROFILE')
        operation, body = request['operation'], request['body']
        allowed = {'create', 'submit', 'observe', 'pause', 'resume', 'close', 'next', 'complete'}
        require(type(operation) is str and operation in allowed, 'UNSUPPORTED_OPERATION')
        require(type(body) is dict and 'session' in body)
        require(type(body['session']) is str and body['session'] in cfg['session_templates'], 'UNAUTHORIZED')
        policy.check(actor, cfg['scope'], 'sessions.'+operation)
        def authorize(principal, scope, permission):
            # Internal SessionStore calls never accept a principal asserted by
            # the wire. Recheck the authenticated actor on each owner access.
            require(policy.authenticate(credential) == actor and principal == cfg['principal'] and scope == cfg['scope'], 'UNAUTHORIZED')
            policy.check(actor, scope, 'sessions.'+operation)
            if permission == 'session.disclose': policy.check(actor, scope, 'sessions.disclose')
        store = SessionStore(cfg['database'], authorize)
        sid, principal = body['session'], cfg['principal']
        def fields(names): require(set(body) == set(('session '+names).split()))
        try:
            if operation == 'create':
                fields('')
                value = store.create(principal, sid, cfg['scope'], cfg['session_templates'][sid])
            elif operation == 'submit':
                fields('identity text assignment')
                require(type(body['assignment']) is str and body['assignment'] in cfg['assignments'], 'UNAUTHORIZED')
                value = store.submit(principal, sid, body['identity'], body['text'], body['assignment'])
            elif operation == 'observe':
                require(set(body) in ({'session','content'},{'session','content','after'}))
                require(type(body['content']) is bool)
                value = store.observe(principal, sid, body['content'],after=body.get('after',0))
            elif operation in ('pause', 'resume', 'close'):
                fields('identity')
                value = store.control(principal, sid, body['identity'], operation)
            elif operation == 'next':
                fields(''); value = store.next_input(principal, sid)
            else:
                fields('identity result')
                require(type(body['result']) is dict and set(body['result']) == {'turn', 'projection', 'occurrences'})
                require(type(body['result']['turn']) is int and type(body['result']['projection']) is str and type(body['result']['occurrences']) is list)
                value = store.complete(principal, sid, body['identity'], body['result'])
            # Wake is an explicit existing-native worker launch, after durable
            # input acceptance. A failed wake never refunds or hides receipt.
            if operation in ('submit', 'resume'):
                try: self.wake(sid)
                except (OSError, RuntimeError, ContractError):
                    value = dict(value, worker='NOT_AVAILABLE', acceptance_retained=True)
            return dict(id=request['id'], profile=PROFILE, request_digest=digest(canonical(request)),
                        actor=actor, principal=principal, value=value)
        finally: store.close()
