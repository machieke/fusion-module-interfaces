"""New opt-in cleanup selection on the existing authenticated maintenance route."""
import uuid
from pathlib import Path
from .contracts import canonical, digest, require
from .registry import Descriptor, descriptor_read, selection_token
from .preview_memory_services import Access, search_owner
from .preview_lifecycle import PROFILE as LIFECYCLE
from . import lookup_contracts as a
from .pilot_search_cleanup import Cleanup, PROFILE

OPS = {'planCleanup':2, 'applyCleanup':3, 'observeCleanup':3}
ROUTE = '/preview/search-maintenance'


def descriptor():
    return Descriptor('pilot-expired-search-cleanup', 'search', '3.4.0', '1.0.0',
                      frozenset({PROFILE}), frozenset(OPS), frozenset({'scoped','process-restart','idempotent','derived-only'}),
                      131072, privacy='generated-shareable-only')


def validate(value, operation, args, scope):
    require(type(value) is dict, 'NOT_AVAILABLE')
    if operation == 'planCleanup':
        require(set(value) == {'plan','plan_sha256'} and value['plan_sha256'] == digest(canonical(value['plan'])), 'NOT_AVAILABLE')
        p = value['plan']
        require(p['profile'] == PROFILE and p['scope'] == scope and p['projection']['lifecycle'] == args[0], 'NOT_AVAILABLE')
        require([x['generation'] for x in p['candidates']] == sorted(args[1]) and p['authoritative_deletion'] is False and
                p['replay_record_deletion'] is False and p['capacity_refund'] is False, 'NOT_AVAILABLE')
    else:
        require(value['identity'] == args[2] and value['state'] in ('absent','applying','complete'), 'NOT_AVAILABLE')
        if value['state'] == 'absent':
            require(operation == 'observeCleanup' and value['plan_sha256'] == args[1]['plan_sha256'], 'NOT_AVAILABLE')
        else:
            require(value['plan'] == args[1] and value['profile'] == PROFILE and value['capacity_refund'] is False, 'NOT_AVAILABLE')
            if value['state'] == 'complete':
                require(value['unlink_intent'] is None and len(value['removed']) == sum(len(c['files']) for c in args[1]['plan']['candidates']), 'NOT_AVAILABLE')
    return value


class Ports:
    def __init__(self, path, hook=lambda _:None): self.path, self.hook = path, hook
    def invoke(self, credential, q):
        require(type(q) is dict and set(q) == {'id','profile','scope','selection','operation','args'} and len(canonical(q)) <= 131072)
        a.identity(q['id']); require(q['profile'] == PROFILE and q['selection'] == selection_token(descriptor()), 'UNSUPPORTED_PROFILE')
        op = q['operation']; args = q['args']
        require(op in OPS and type(args) is list and len(args) == OPS[op], 'UNSUPPORTED_OPERATION')
        access = Access(self.path, credential, 'search'); cfg = access.policy.current()['active_memory']
        require(cfg.get('cleanup_profile') == PROFILE and q['scope'] == cfg['scope'], 'UNSUPPORTED_PROFILE')
        original=access.authorize
        def current(scope,action):
            require(access.policy.current()['active_memory'].get('cleanup_profile')==PROFILE,'UNSUPPORTED_PROFILE')
            return original(scope,action)
        access.authorize=current
        a.head(args[0], cfg['scope'], LIFECYCLE)
        search = search_owner(self.path, access, args[0], self.hook); cleanup = Cleanup(search)
        if op == 'planCleanup': value = cleanup.plan(args[1])
        elif op == 'applyCleanup': value = cleanup.apply(args[1], args[2])
        else: value = cleanup.observe(args[1], args[2])
        access.authorize(cfg['scope'], 'maintenance.' + op)
        require(access.policy.current()['active_memory'].get('cleanup_profile') == PROFILE, 'UNSUPPORTED_PROFILE')
        validate(value, op, args, cfg['scope'])
        return dict(id=q['id'], profile=PROFILE, selection=q['selection'], request_digest=digest(canonical(q)), principal=access.principal, value=value)


class Client:
    def __init__(self, config):
        require(config['profile'] == PROFILE and config['fallback'] is False and config['placement'] in ('local','network'), 'UNSUPPORTED_PROFILE')
        require(descriptor_read(config['descriptor']) == descriptor(), 'UNSUPPORTED_PROFILE')
        self.cfg = config
        self.ca = digest(Path(config['endpoint']['ca_file']).read_bytes()) if config['placement'] == 'network' else None
    def call(self, operation, *args):
        require(operation in OPS and len(args) == OPS[operation], 'UNSUPPORTED_OPERATION'); cfg = self.cfg
        q = dict(id=str(uuid.uuid4()), profile=PROFILE, scope=cfg['scope'], selection=selection_token(descriptor()), operation=operation, args=list(args))
        if cfg['placement'] == 'local': value = Ports(cfg['provider_config']).invoke(cfg['credential'], q)
        else:
            from .preview_transport import invoke
            require(digest(Path(cfg['endpoint']['ca_file']).read_bytes()) == self.ca, 'CONFLICT')
            value = invoke(cfg, ROUTE, q, None)
        require(type(value) is dict and set(value) == {'id','profile','selection','request_digest','principal','value'}, 'NOT_AVAILABLE')
        require([value[k] for k in ('id','profile','selection','request_digest','principal')] ==
                [q['id'],PROFILE,q['selection'],digest(canonical(q)),cfg['principal']], 'NOT_AVAILABLE')
        return validate(value['value'], operation, list(args), cfg['scope'])
