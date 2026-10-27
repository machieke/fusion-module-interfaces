"""S01 service placement: existing AtomStorage and CompletionDelivery ports over TLS.

No new module family, numerical profile, owner journal or execution algorithm.
The caller's published S01 requests are routed by interface. Only execution's
existing private create/completion ports acquire a bounded authenticated wire.
"""
import http.client
import json
from pathlib import Path
import re
import ssl

from . import neoclaw_contracts as c
from .atoms import AtomOwner, AuthorizedAtoms
from .adapters.detta import DettaStorage
from .contracts import ContractError, ERRORS, canonical, decode, digest, encode, label, require
from .messaging import MessageOwner, MessagingSession
from .neoclaw_transport import Network, json_loads
from .policy import Policy
from .ports import Mutation
from .registry import selection_token
from .responses import atom_write, completion_acceptance, error as validate_error

COMPOSITION = 'neoclaw-separated-services/1'
FAMILIES = ('execution', 'atom.storage', 'agent.messaging')


def service_hostname(value):
    require(type(value) is str and re.fullmatch(
        r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.svc\.cluster\.local', value),
        'UNSUPPORTED_PROFILE')
    return value


class RoutedNetwork:
    def __init__(self, config, chosen):
        require(config.get('service_composition') == COMPOSITION and config.get('fallback') is False,
                'UNSUPPORTED_PROFILE')
        require('provider_config' not in config and 'endpoint' not in config, 'UNSUPPORTED_PROFILE')
        c.fields(config['endpoints'], ' '.join(FAMILIES))
        c.fields(config['service_credentials'], ' '.join(FAMILIES))
        self.correlations = {}
        self.routes = {name: Network(config['endpoints'][name], config['service_credentials'][name], chosen,
                                    service_dns=True) for name in FAMILIES}
        for transport in self.routes.values():
            transport.correlations = self.correlations

    def invoke(self, request):
        require(type(request) is dict and type(request.get('interface_ref')) is dict)
        name = request['interface_ref'].get('id')
        require(type(name) is str and name in self.routes, 'UNSUPPORTED_OPERATION')
        return self.routes[name].invoke(request)


class PortConnection:
    def __init__(self, endpoint, credential):
        c.fields(endpoint, 'host port ca_file')
        service_hostname(endpoint['host'])
        require(type(endpoint['port']) is int and 1 <= endpoint['port'] <= 65535)
        self.endpoint, self.credential = endpoint, credential
        self.context = ssl.create_default_context(cafile=endpoint['ca_file'])
        self.context.minimum_version = ssl.TLSVersion.TLSv1_2

    def call(self, path, request):
        conn = http.client.HTTPSConnection(self.endpoint['host'], self.endpoint['port'],
                                          timeout=1, context=self.context)
        try:
            conn.request('POST', path, canonical(request),
                         {'Authorization': 'Bearer '+self.credential, 'Content-Type': 'application/json'})
            response = conn.getresponse()
            require(response.status == 200, 'NOT_AVAILABLE')
            raw = response.read(16385)
            require(len(raw) <= 16384, 'NOT_AVAILABLE')
            value = json_loads(raw)
        except (OSError, ValueError, http.client.HTTPException):
            raise ContractError('NOT_AVAILABLE') from None
        finally:
            conn.close()
        if type(value) is dict and set(value) == {'error'}:
            validate_error(value['error'])
            raise ContractError(value['error']['code'])
        try:
            c.fields(value, 'ok selection request_digest')
            require(value['selection'] == request['selection'] and
                    value['request_digest'] == digest(canonical(request)), 'NOT_AVAILABLE')
        except ContractError:
            raise ContractError('NOT_AVAILABLE') from None
        return value['ok']


class RemoteAtoms:
    """Only the create port used by S01 execution; no local payload fallback."""
    def __init__(self, connection, descriptor):
        self.connection, self.descriptor = connection, descriptor

    def create(self, command, content_type, data):
        request = dict(profile='immutable-bytes/1', selection=selection_token(self.descriptor),
            scope_ref=command.scope_ref, idempotency_key=command.idempotency_key,
            intent_digest=command.intent_digest, content_type=content_type, bytes=encode(data))
        result = self.connection.call('/ports/atom-create', request)
        atom_write(result, command.scope_ref, self.descriptor)
        require(result['ref']['digest'] == digest(data), 'NOT_AVAILABLE')
        return result


class RemoteCompletion:
    def __init__(self, connection, descriptor):
        self.connection, self.descriptor = connection, descriptor

    def accept(self, scope_ref, route, delivery_id, completion):
        request = dict(profile='completion-delivery/1', selection=selection_token(self.descriptor),
                       scope_ref=scope_ref, route=route, delivery_id=delivery_id, completion=completion)
        result = self.connection.call('/ports/completion', request)
        completion_acceptance(result, scope_ref, route, delivery_id, completion['correlation_id'])
        return result


class OwnerService:
    """One owner only: storage never opens mailbox or execution journals, and vice versa."""
    def __init__(self, config_path, role):
        self.config = json.loads(Path(config_path).read_text())
        self.policy, self.role = Policy(config_path), role
        require(self.config['service_composition'] == COMPOSITION and self.config['sharing'] == 'generated-shareable',
                'UNSUPPORTED_PROFILE')
        self.chosen = c.selected(c.catalogue('detta'))
        if role == 'fusion-storage':
            require('messages_database' not in self.config and 'database' not in self.config, 'UNSUPPORTED_PROFILE')
            self.owner = AtomOwner(self.config['atoms_database'], DettaStorage(self.config['detta_binary'], self.config['da_root']))
        else:
            require(role == 'fusion-messaging' and 'atoms_database' not in self.config and 'database' not in self.config,
                    'UNSUPPORTED_PROFILE')
            self.owner = MessageOwner(self.config['messages_database'], self.policy, self.config['capacity'])

    def public(self, credential, request):
        principal = self.policy.authenticate(credential)
        name, op = c.validate(request, self.chosen)
        scope, body = request['scope_ref'], request['body']
        self.policy.check(principal, scope, name+'.'+op)
        if self.role == 'fusion-storage':
            require(name == 'atom.storage' and op == 'get', 'UNSUPPORTED_OPERATION')
            value = AuthorizedAtoms(self.owner, self.policy, principal, self.chosen[name]).get(body['ref'])
            result = dict(ref=value.ref, content_type=value.content_type, bytes=encode(value.bytes))
        else:
            require(name == 'agent.messaging' and op in ('poll', 'ack'), 'UNSUPPORTED_OPERATION')
            session = MessagingSession(self.owner, self.policy, principal, None, request['message_id'])
            result = dict(delivery=session.poll(scope, body['route'])) if op == 'poll' else session.ack(
                Mutation(scope, request['idempotency_key'], c.fingerprint(request)), body['route'], body['delivery_id'])
        return dict(ok=result, provider=request['selection'])

    def private(self, credential, path, request):
        principal = self.policy.authenticate(credential)
        require(principal == 'worker', 'UNAUTHORIZED')
        require(type(request) is dict and len(canonical(request)) <= 8192)
        require(request.get('scope_ref') == c.SCOPE, 'UNAUTHORIZED')
        scope = request['scope_ref']
        if path == '/ports/atom-create':
            require(self.role == 'fusion-storage', 'UNSUPPORTED_OPERATION')
            c.fields(request, 'profile selection scope_ref idempotency_key intent_digest content_type bytes')
            require(request['profile'] == 'immutable-bytes/1' and request['selection'] == selection_token(self.chosen['atom.storage']), 'UNSUPPORTED_PROFILE')
            require(label(request['idempotency_key']) and label(request['content_type']))
            require(request['intent_digest'] is None or (type(request['intent_digest']) is str and re.fullmatch('[0-9a-f]{64}', request['intent_digest'])))
            data = decode(request['bytes']); require(0 < len(data) <= c.MAX_BYTES)
            result = AuthorizedAtoms(self.owner, self.policy, principal, self.chosen['atom.storage']).create(
                Mutation(scope, request['idempotency_key'], request['intent_digest']), request['content_type'], data)
        else:
            require(path == '/ports/completion' and self.role == 'fusion-messaging', 'UNSUPPORTED_OPERATION')
            c.fields(request, 'profile selection scope_ref route delivery_id completion')
            require(request['profile'] == 'completion-delivery/1' and request['selection'] == selection_token(self.chosen['agent.messaging']), 'UNSUPPORTED_PROFILE')
            self.policy.check(principal, scope, 'execution.completion')
            self.policy.route(scope, request['route'])
            body = request['completion']; c.fields(body, 'job_id correlation_id causation_id result error')
            require(label(request['route']) and label(request['delivery_id']) and request['delivery_id'] == body['job_id'])
            require(label(body['correlation_id']) and label(body['causation_id']))
            if body['error'] is None: atom_write(body['result'], scope, self.chosen['atom.storage'])
            else: require(type(body['error']) is str and body['error'] in ERRORS and body['result'] is None)
            result = self.owner.accept(scope, request['route'], request['delivery_id'], body)
        return dict(ok=result, selection=request['selection'], request_digest=digest(canonical(request)))
