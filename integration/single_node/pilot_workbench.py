"""Kubeconfig-free Workbench composition over existing scoped HTTPS ports.

Provisioned synthetic users select existing native agents. This adapter does not
launch tools, query provider databases, retry mutations or renew work deadlines.
"""
from contextlib import contextmanager
from pathlib import Path
import threading
import uuid

from fusion.contracts import canonical, digest, require, ContractError
from fusion.preview_transport import invoke
from .pilot_browser_sessions import configuration
from .pilot_browser_observation import PROFILE as OBSERVATION, ROUTE as OBSERVATION_ROUTE

PROFILE = 'omega-native-sessions/3'
IDENTITY_NAMESPACE = uuid.UUID('d2d68ed6-a0e6-48f9-8327-b3b3293cf9a4')


class ScopedWorkbench:
    def __init__(self, configuration_file):
        self.configuration_file = Path(configuration_file)
        configuration(configuration_file)
        self.lock = threading.Lock(); self.context = threading.local()

    @contextmanager
    def as_user(self, user):
        old = getattr(self.context, 'user', None); self.context.user = user
        try: yield
        finally: self.context.user = old

    def user(self):
        user = getattr(self.context, 'user', None)
        selected = configuration(self.configuration_file)['users'].get(user)
        require(selected is not None and selected['enabled'], 'UNAUTHORIZED')
        return user, selected

    def _target(self, role):
        name, selected = self.user()
        require(type(role) is str and role in selected['targets'], 'UNAUTHORIZED')
        return name, selected['targets'][role]

    def _invoke(self, role, path, request, *, principal=True):
        user, target = self._target(role)
        credential = Path(target['credential_file'])
        require(credential.is_file() and credential.stat().st_size <= 257, 'UNAUTHORIZED')
        transport = dict(endpoint=target['endpoint'], credential=credential.read_text().strip())
        value = invoke(transport, path, request)
        expected = {'profile', 'id', 'request_digest', 'actor', 'value'} | ({'principal'} if principal else set())
        require(type(value) is dict and set(value) == expected and
                (value['profile'], value['id'], value['request_digest'], value['actor']) ==
                (request['profile'], request['id'], digest(canonical(request)), 'browser-'+user), 'NOT_AVAILABLE')
        if principal: require(value['principal'] == target['principal'], 'UNAUTHORIZED')
        # Rotation/revocation in this request cannot be concealed by a pooled
        # connection or a slow upstream. Provider checks its policy separately.
        require(self._target(role)[1] == target and credential.read_text().strip() == transport['credential'], 'UNAUTHORIZED')
        return value['value']

    def _session(self, role, operation, body):
        return self._invoke(role, '/preview/session', dict(id=str(uuid.uuid4()), profile=PROFILE, operation=operation, body=body))

    def _scoped(self, role, operation, session=None):
        _, target = self._target(role)
        return self._invoke(role, OBSERVATION_ROUTE, dict(id=str(uuid.uuid4()), profile=OBSERVATION,
            operation=operation, scope=target['scope'], session=session))

    def selected(self, body):
        require(type(body) is dict and type(body.get('session')) is str, 'INVALID_ARGUMENT')
        _, target = self._target(body.get('role'))
        try:value = self._session(body['role'], 'binding', {'session': body['session']})
        except ContractError as error:
            if error.code in ('NOT_FOUND','UNAUTHORIZED'):raise ContractError('UNAUTHORIZED') from None
            raise
        require(type(value) is dict and value.get('scope') == target['scope'] and
                value.get('principal') == target['principal'] and value.get('session') == body['session'], 'UNAUTHORIZED')

    def _role(self, minimum='developer'):
        user, selected = self.user()
        permitted = {'viewer': {'viewer','developer','operator'}, 'developer': {'developer','operator'}, 'operator': {'operator'}}
        require(selected['role'] in permitted[minimum], 'UNAUTHORIZED')
        return user

    def identity(self, operation, value):
        user, _ = self.user()
        require(type(value) is str and 1 <= len(value.encode()) <= 128, 'INVALID_ARGUMENT')
        # Fresh browser actions get an actor-bound deterministic ID. Retries
        # reconstruct the same ID; pre-existing native occurrence IDs are never
        # rewritten. The actual accepted ID is always returned by its owner.
        return str(uuid.uuid5(IDENTITY_NAMESPACE, canonical([user, operation, value]).decode()))

    def state(self):
        user, selected = self.user()
        agents = {role: self._scoped(role, 'inventory') for role in selected['targets']}
        for role,value in agents.items():
            value['browser_controls']=dict(search_cleanup='search_maintenance' in selected['targets'][role],operator=selected['role']=='operator')
        return dict(namespace=configuration(self.configuration_file)['namespace'], agents=agents, services=[],
            additional_live_generations=0, user=user, role=selected['role'],
            services_observation='NOT_DISCLOSED_OUTSIDE_SELECTED_APPLICATION_SCOPE',
            observer_profile='BOUNDED_EXPLICIT_READ_NO_RESUBMISSION')

    def observe(self, body):
        require(set(body) == {'role','session','after'})
        self.selected(body); after=body['after']; require(type(after) is int and 0 <= after <= 32)
        return self._session(body['role'], 'observe', dict(session=body['session'], content=True, after=after))

    def current(self, body):
        require(set(body) == {'role','session','operation'})
        self.selected(body); require(body['operation'] in ('current','capacity'), 'UNSUPPORTED_OPERATION')
        if body['operation'] == 'capacity':
            value=self._session(body['role'],'observe',dict(session=body['session'],content=False,after=0))
            return dict(scope='SELECTED_SESSION',capacity=value['capacity'],aggregate='NOT_DISCLOSED')
        return self._scoped(body['role'], 'current', body['session'])

    def explore(self,body):
        require(set(body)=={'role','session','operation','body'})
        self.selected(body);_,target=self._target(body['role'])
        require(body['operation'] in ('relations','history'),'UNSUPPORTED_OPERATION')
        return self._invoke(body['role'],OBSERVATION_ROUTE,dict(id=str(uuid.uuid4()),profile=OBSERVATION,operation='explore',
            scope=target['scope'],session=body['session'],navigation={k:body[k] for k in ('operation','body')}))

    def handover(self,body):
        self._role('operator');cfg=configuration(self.configuration_file);selected=cfg.get('handover')
        require(selected is not None,'UNSUPPORTED_PROFILE')
        from .pilot_browser_handover import observe
        value=observe(selected,body)
        require(configuration(self.configuration_file).get('handover')==selected,'UNAUTHORIZED');self._role('operator')
        return value

    def capabilities(self, body):
        require(set(body) in ({'role','session'},{'role','session','commands'}))
        self.selected(body)
        from .integrated_permissions import PROFILE as selected_profile, ROUTE
        commands = body.get('commands')
        require(commands is None or (type(commands) is list and len(canonical(commands))<=8192))
        _, target=self._target(body['role'])
        q=dict(profile=selected_profile,id=str(uuid.uuid4()),session=body['session'],principal=target['principal'],commands=commands)
        value=self._invoke(body['role'],ROUTE,q,principal=False)
        require(type(value) is dict and value.get('principal')==target['principal'] and value.get('scope')==target['scope'] and
                value.get('advisory') is True and value.get('acceptance_created') is False and
                value.get('deadline_started') is False and value.get('effect_reserved') is False and
                type(value.get('tools')) is list and len(value['tools'])<=32, 'NOT_AVAILABLE')
        return value

    def action(self, body):
        self._role()
        require(type(body) is dict and type(body.get('operation')) is str)
        op=body['operation']; require(op in ('submit','allocate','pause','resume','close','archive','cancel','reconcile'), 'UNSUPPORTED_OPERATION')
        fields={'role','session','operation','identity'}|({'text','assignment','catalogue'} if op=='submit' else {'template'} if op=='allocate' else {'target'} if op=='cancel' else set())
        require(set(body)==fields)
        if op=='allocate':
            inventory=self._scoped(body['role'],'inventory')
            require(body['template'] in inventory['templates'], 'UNAUTHORIZED')
            return self._session(body['role'],op,dict(identity=self.identity(op,body['identity']),template=body['template']))
        self.selected(body); request=dict(session=body['session'])
        if op!='reconcile':request['identity']=self.identity(op,body['identity'])
        if op=='submit':
            require(type(body['text']) is str and 0<len(body['text'].encode())<=4096)
            require(type(body['assignment']) is str)
            selected=self.capabilities(dict(role=body['role'],session=body['session']))
            require(body['catalogue']==selected['catalogue'], 'CONFLICT')
            request.update(text=body['text'],assignment=body['assignment'])
        if op=='cancel':require(type(body['target']) is str);request['target']=body['target']
        return self._session(body['role'],op,request)

    def worker_control(self, body):
        require(set(body)=={'role','session','operation','identity'})
        self.selected(body); op=body['operation'];require(op in ('observe','drain','recycle','resume'))
        if op!='observe':self._role('operator')
        else:require(body['identity'] is None)
        from fusion.resident_workers import CONTROL
        return self._invoke(body['role'],'/preview/worker-control',dict(profile=CONTROL,id=str(uuid.uuid4()),
            session=body['session'],operation=op,identity=None if op=='observe' else self.identity('worker-'+op,body['identity'])),principal=False)

    def continuation(self, body):
        require(set(body)=={'role','session','occurrence','operation','identity'})
        self.selected(body); op=body['operation'];require(op in ('observe','cancel','unsubscribe'))
        if op!='observe':self._role()
        from fusion.inspection_continuation import PROFILE as selected_profile
        return self._invoke(body['role'],'/preview/continuation',dict(profile=selected_profile,id=str(uuid.uuid4()),
            session=body['session'],occurrence=body['occurrence'],operation=op,
            identity=None if op=='observe' else self.identity('continuation-'+op,body['identity'])),principal=False)

    def workflow(self, body):
        """Observe or decide an existing owner checkpoint; never advance work."""
        self._role('operator')
        require(type(body) is dict and set(body)=={'role','session','workflow','operation','body'})
        from fusion.lookup_contracts import identity as uid
        from fusion.guarded_continuation import PROFILE as profile,LIMITS
        from .pilot_workflows import ROUTE
        uid(body['workflow']);self.selected(body);_,target=self._target(body['role'])
        operation=body['operation'];request=body['body']
        require(operation in ('observe','decide'),'UNSUPPORTED_OPERATION')
        require(type(request) is dict and set(request)==(set() if operation=='observe' else
            {'checkpoint','identity','binding_sha256','action'}))
        if operation=='decide':
            import re
            require(type(request['checkpoint']) is str and 0<len(request['checkpoint'].encode())<=128)
            require(type(request['binding_sha256']) is str and re.fullmatch('[a-f0-9]{64}',request['binding_sha256']))
            require(request['action'] in ('approve','refuse'),'UNSUPPORTED_OPERATION')
            request=dict(request,identity=self.identity('workflow-decision',request['identity']))
        value=self._invoke(body['role'],ROUTE,dict(profile=profile,id=str(uuid.uuid4()),session=body['session'],
            workflow=body['workflow'],operation=operation,body=request))
        require(type(value) is dict and len(canonical(value))<=LIMITS['output_bytes'] and
            (value.get('profile'),value.get('workflow'),value.get('session'),value.get('scope'))==
            (profile,body['workflow'],body['session'],target['scope']),'NOT_AVAILABLE')
        require(type(value.get('checkpoints')) is list and len(value['checkpoints'])<=LIMITS['checkpoints'],'NOT_AVAILABLE')
        for checkpoint in value['checkpoints']:
            require(type(checkpoint) is dict and set(checkpoint)=={'identity','binding','binding_sha256','decision'},'NOT_AVAILABLE')
            binding=checkpoint['binding']
            require(type(binding) is dict and digest(canonical(binding))==checkpoint['binding_sha256'] and
                (binding.get('profile'),binding.get('workflow'),binding.get('identity'),binding.get('scope'),binding.get('principal'),binding.get('deadline_ms'))==
                (profile,body['workflow'],checkpoint['identity'],target['scope'],target['principal'],value.get('deadline_ms')) and
                binding.get('grants_authority') is False,'NOT_AVAILABLE')
        if operation=='decide':
            checkpoints=[x for x in value['checkpoints'] if x['identity']==request['checkpoint']]
            require(len(checkpoints)==1 and checkpoints[0]['binding_sha256']==request['binding_sha256'],'NOT_AVAILABLE')
            decision=checkpoints[0]['decision']
            require(type(decision) is dict and all(decision.get(k)==request[k] for k in ('identity','binding_sha256','action')) and
                decision.get('actor')=='browser-'+self.user()[0] and decision.get('original_deadline_ms')==value['deadline_ms'] and
                type(decision.get('effective')) is bool and decision.get('grants_authority') is False,'NOT_AVAILABLE')
        return value

    def subscription(self, body):
        require(set(body)=={'role','session','operation','subscription','action','body'})
        self.selected(body)
        from fusion.pilot_subscriptions import PROFILE as profile
        from .pilot_subscription_ports import ROUTE
        require(type(body['body']) is dict)
        if body['operation']=='create':require(body['body'].get('session')==body['session'],'UNAUTHORIZED')
        return self._invoke(body['role'],ROUTE,dict(profile=profile,id=str(uuid.uuid4()),operation=body['operation'],
            subscription=body['subscription'],session=body['session'],action=body['action'],body=body['body']),principal=False)

    def chain(self, role):
        self._target(role)
        return dict(observation='NOT_SELECTED',submission='NOT_REQUESTED',reason='Select an authorized exact continuation; no ambient chain credential.')

    def registry_maintenance(self, body):
        self._role('operator'); self.selected(body)
        require(set(body)=={'role','session','operation','provider','identity','plan'})
        require(body['operation'] in ('plan','seal'),'UNSUPPORTED_OPERATION')
        require(type(body['provider']) is str and 0<len(body['provider'])<=128)
        # The native session's frozen selected provider keys bound the picker;
        # no registry path, endpoint or another scope may be entered here.
        caps=self.capabilities(dict(role=body['role'],session=body['session']))
        require(body['provider'] in (caps.get('provider_lifecycle') or {}),'UNAUTHORIZED')
        if body['operation']=='plan':
            require(body['plan'] is None and body['identity'] is None);request={'provider':body['provider']}
        else:
            require(type(body['plan']) is dict and body['plan'].get('provider')==body['provider'] and
                body['plan'].get('profile')=='trusted-provider-lifecycle/2','CONFLICT')
            request=dict(provider=body['provider'],head=body['plan']['head'],identity=self.identity('registry-seal',body['identity']))
        return self._invoke(body['role'],'/preview/providers',dict(id=str(uuid.uuid4()),profile='trusted-provider-lifecycle/2',
            operation=body['operation'],body=request),principal=False)

    def maintenance(self, body):
        self._role('operator'); self.selected(body)
        require(set(body)=={'role','session','operation','args'} and type(body['args']) is list)
        user,target=self._target(body['role']);selected=target.get('search_maintenance')
        require(selected is not None,'UNSUPPORTED_PROFILE')
        from fusion.pilot_search_maintenance import Client,OPS,descriptor
        from fusion.registry import descriptor_wire
        operation=body['operation'];require(operation in OPS and len(body['args'])==OPS[operation],'UNSUPPORTED_OPERATION')
        args=list(body['args'])
        if operation!='planCleanup':
            require(type(args[1]) is dict and args[1].get('plan',{}).get('scope')==target['scope'],'UNAUTHORIZED')
            args[2]=self.identity('search-cleanup',args[2])
        path=Path(selected['credential_file']);require(path.is_file() and path.stat().st_size<=257,'UNAUTHORIZED')
        credential=path.read_text().strip()
        client=Client(dict(profile=selected['profile'],scope=target['scope'],descriptor=descriptor_wire(descriptor()),
            placement='network',fallback=False,principal='browser-'+user,credential=credential,endpoint=selected['endpoint']))
        result=client.call(operation,*args)
        require(self._target(body['role'])[1]==target and path.read_text().strip()==credential,'UNAUTHORIZED')
        return result
