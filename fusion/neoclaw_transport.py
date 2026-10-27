"""S01 composition bindings: local, loopback or explicit service DNS. No fallback."""
import http.client
import json
from pathlib import Path
import ssl
import sqlite3

from .contracts import ContractError, canonical, require
from . import neoclaw_contracts as c
from . import neoclaw_search_contracts as s, neoclaw_operations as ops
from .registry import selection_token
from .responses import validate_reply


def json_loads(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result)
            result[key] = value
        return result
    try:
        value = json.loads(raw, object_pairs_hook=pairs, parse_constant=lambda _: (_ for _ in ()).throw(ContractError('INVALID_ARGUMENT')))
        # Python 3.12's decoder no longer necessarily raises at the old recursion
        # limit. Keep untrusted receipt nesting bounded across packaged runtimes.
        pending = [(value, 0)]
        while pending:
            item, depth = pending.pop()
            require(depth <= 256)
            if type(item) in (dict, list):
                pending.extend((v, depth+1) for v in (item.values() if type(item) is dict else item))
        return value
    except (ValueError, RecursionError):
        raise ContractError('INVALID_ARGUMENT') from None


def checked_reply(request, reply, chosen, correlations):
    # Reuse the existing M1 operation/receipt validators. S01 adds only durable
    # attempt/failure metadata to status, validated before the M1 status shape.
    extra = {}
    module = ops.from_chosen(chosen)
    if request['operation'] == 'status' and type(reply) is dict and 'ok' in reply:
        try:
            value = dict(reply['ok'])
            extra = {k: value.pop(k) for k in ('attempts', 'failure_reason')}
            require(type(extra['attempts']) is int and 0 <= extra['attempts'] <= module.MAX_ATTEMPTS, 'NOT_AVAILABLE')
            reasons = {None, *s.FAILURES} if module is s else {None, 'attempt-budget-exhausted'}
            require(type(extra['failure_reason']) in (str, type(None)) and extra['failure_reason'] in reasons, 'NOT_AVAILABLE')
            reply = {**reply, 'ok': value}
        except (KeyError, TypeError, ValueError):
            raise ContractError('NOT_AVAILABLE') from None
    value = validate_reply(request, reply, chosen[request['interface_ref']['id']], correlations)
    return {**value, **extra} if extra else value


class Local:
    def __init__(self, config, credential, chosen):
        self.config, self.credential, self.chosen = config, credential, chosen
        self.correlations = {}

    def invoke(self, request):
        from .neoclaw import NalService
        ops.from_chosen(self.chosen).validate(request, self.chosen)
        service = NalService(self.config)
        try:
            try:
                reply = dict(ok=service.invoke(self.credential, json_loads(canonical(request))), provider=request['selection'])
            except ContractError as exc:
                reply = dict(error=exc.wire())
            return checked_reply(request, json_loads(canonical(reply)), self.chosen, self.correlations)
        finally:
            service.close()


class Network:
    """Real TLS/TCP, verified certificates; historical placement stays loopback-only."""
    def __init__(self, endpoint, credential, chosen, timeout=1.0, *, service_dns=False):
        require(type(endpoint) is dict and set(endpoint) == {'host', 'port', 'ca_file'})
        if service_dns:
            from .neoclaw_services import service_hostname
            service_hostname(endpoint['host'])
        else:
            require(endpoint['host'] == '127.0.0.1', 'UNSUPPORTED_PROFILE')
        require(type(endpoint['port']) is int and 1 <= endpoint['port'] <= 65535)
        self.endpoint, self.credential, self.chosen = endpoint, credential, chosen
        self.timeout = min(max(timeout, .05), 1.0)
        self.context = ssl.create_default_context(cafile=str(Path(endpoint['ca_file'])))
        self.context.minimum_version = ssl.TLSVersion.TLSv1_2
        self.correlations = {}

    def invoke(self, request):
        ops.from_chosen(self.chosen).validate(request, self.chosen)
        conn = http.client.HTTPSConnection(self.endpoint['host'], self.endpoint['port'],
                                          timeout=self.timeout, context=self.context)
        try:
            conn.request('POST', '/s01', body=canonical(request), headers={
                'Authorization': 'Bearer ' + self.credential, 'Content-Type': 'application/json'})
            response = conn.getresponse()
            require(response.status in (200, 400, 401, 403, 503), 'NOT_AVAILABLE')
            limit = 65536 if ops.from_chosen(self.chosen) is s else 16384
            raw = response.read(limit+1)
            require(len(raw) <= limit, 'NOT_AVAILABLE')
            reply = json_loads(raw)
        except (OSError, http.client.HTTPException, ValueError, ContractError):
            raise ContractError('NOT_AVAILABLE') from None
        finally:
            conn.close()
        return checked_reply(request, reply, self.chosen, self.correlations)


def binding(config, chosen):
    require(config.get('fallback') is False, 'UNSUPPORTED_PROFILE')
    if config['placement'] == 'service-network':
        from .neoclaw_services import RoutedNetwork
        return RoutedNetwork(config, chosen)
    if config['placement'] == 'local':
        return Local(config['provider_config'], config['credential'], chosen)
    require(config['placement'] == 'network', 'UNSUPPORTED_PROFILE')
    require('provider_config' not in config, 'UNSUPPORTED_PROFILE')
    return Network(config['endpoint'], config['credential'], chosen)
