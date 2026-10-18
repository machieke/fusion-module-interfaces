"""Closed external observation profile. No internal Search/cognition semantics."""
from dataclasses import replace
import json
import unicodedata

from . import neoclaw_contracts as c
from .contracts import ContractError, canonical, require, label, validate as m1_validate
from .registry import Descriptor, Requirement, descriptors, resolve, selection_token

PROFILE = 'external-web-search/1'
OPERATION = 'web_search'
SDK = 'ddgs-9.16.0-duckduckgo/1'
VERSION = '1.1.0'
MAX_BYTES, MAX_ATTEMPTS = 32768, 1
CONTENT_TYPE = 'application/neoclaw-web-search-result'
LIMITS = frozenset({SDK, 'sdk-invocations:1', 'wall-timeout-ms:10000', 'caller-calls:64',
                    'first-captured-observation', 'no-fallback', 'lifetime-requests:128'})
FAILURES = {'attempt-budget-exhausted': 'NOT_AVAILABLE', 'upstream-rate-limited': 'OVERLOADED',
            'upstream-denied': 'NOT_AVAILABLE', 'upstream-unavailable': 'NOT_AVAILABLE',
            'upstream-empty-unconfirmed': 'NOT_AVAILABLE', 'upstream-timeout': 'DEADLINE_EXCEEDED',
            'invalid-output': 'NOT_AVAILABLE'}
IDENTITY = dict(sdk='ddgs', sdk_version='9.16.0', sdk_profile=SDK,
                backend='duckduckgo', upstream_service='DuckDuckGo HTML', upstream_version=None)


def arguments(value):
    c.fields(value, 'query max_results')
    query = value['query']
    require(type(query) is str and query.strip())
    require(not any(unicodedata.category(x).startswith('C') for x in query))
    require(len(query.encode('utf-8')) <= 2048)
    require(type(value['max_results']) is int and 1 <= value['max_results'] <= 10)
    return json.loads(canonical(value))


def catalogue(atom_provider='detta', provider='neoclaw-web-search'):
    shared = [replace(d, privacy=c.PRIVACY, max_payload_bytes=MAX_BYTES)
              for d in descriptors(atom_provider=atom_provider) if d.interface != 'execution']
    execution = Descriptor(provider, 'execution', VERSION, '0.1.0', frozenset({PROFILE}),
        frozenset({'submit', 'status', 'result'}),
        frozenset({'process-restart', 'scoped', 'idempotent', 'bounded-attempts'}), MAX_BYTES,
        privacy=c.PRIVACY, deterministic=False, features=LIMITS, receipt_providers=shared[0].receipt_providers)
    return [*shared, execution]


def selected(catalogue):
    specs = [('atom.storage', 'immutable-bytes/1', {'get'}),
             ('agent.messaging', 'durable-mailbox/2', {'poll', 'ack'}),
             ('execution', PROFILE, {'submit', 'status', 'result'})]
    chosen = {name: resolve(catalogue, Requirement(name, VERSION if name == 'execution' else '1.0.0',
              '2.0.0', profile, frozenset(ops), frozenset({'process-restart', 'scoped', 'idempotent'}),
              MAX_BYTES, privacy=c.PRIVACY)) for name, profile, ops in specs}
    require(LIMITS <= chosen['execution'].features and
            'bounded-attempts' in chosen['execution'].guarantees, 'UNSUPPORTED_PROFILE')
    return chosen


def validate(request, chosen):
    require(type(request) is dict and len(canonical(request)) <= c.MAX_BYTES)
    common = {'message_id', 'interface_ref', 'profile', 'selection', 'operation', 'scope_ref', 'body'}
    require(common <= set(request) <= common | {'idempotency_key', 'correlation_id', 'reply_route', 'deadline_ms'})
    c.fields(request['interface_ref'], 'id version')
    name, op = request['interface_ref']['id'], request['operation']
    require(type(name) is str and name in {'execution', 'atom.storage', 'agent.messaging'}, 'UNSUPPORTED_OPERATION')
    desc = chosen[name]
    require(request['interface_ref']['version'] == desc.version, 'UNSUPPORTED_VERSION')
    require(request['profile'] == (PROFILE if name == 'execution' else
            'immutable-bytes/1' if name == 'atom.storage' else 'durable-mailbox/2'), 'UNSUPPORTED_PROFILE')
    require(request['selection'] == selection_token(desc), 'UNSUPPORTED_PROFILE')
    require(label(request['message_id']) and label(op))
    require(request['scope_ref'] == c.SCOPE, 'UNAUTHORIZED')
    allowed = {'execution': {'submit', 'status', 'result'}, 'atom.storage': {'get'}, 'agent.messaging': {'poll', 'ack'}}
    require(op in allowed[name], 'UNSUPPORTED_OPERATION')
    body = request['body']
    if name != 'execution':
        m1_validate({k: v for k, v in request.items() if k != 'selection'}, check_deadline=False)
    elif op == 'submit':
        c.fields(body, 'operation arguments sharing max_attempts')
        require(body['operation'] == OPERATION, 'UNSUPPORTED_OPERATION')
        require(body['sharing'] == 'generated-shareable', 'UNAUTHORIZED')
        arguments(body['arguments'])
        require(type(body['max_attempts']) is int and body['max_attempts'] == MAX_ATTEMPTS)
        require(set(request) == common | {'idempotency_key', 'correlation_id', 'reply_route', 'deadline_ms'})
        for key in ('idempotency_key', 'correlation_id', 'reply_route'): require(label(request[key]))
        require(type(request['deadline_ms']) is int and 0 < request['deadline_ms'] < 2**53)
    else:
        c.fields(body, 'job_id')
        require(label(body['job_id']) and set(request) == common)
    return name, op


def items(value, maximum):
    require(type(value) is list and len(value) <= maximum)
    for row in value:
        c.fields(row, 'title url snippet')
        for key, limit in [('title', 1024), ('url', 2048), ('snippet', 8192)]:
            require(type(row[key]) is str and len(row[key].encode('utf-8')) <= limit)
    return json.loads(canonical(value))


def visible(text):
    # Preserve printable text, including quotes/parentheses, as a native string.
    # Escape controls/formats for safe terminal/context display, never execute it.
    return ''.join(('\\u%04x' % ord(x)) if unicodedata.category(x).startswith('C') else x for x in text)


def render(rows):
    return '(' + ''.join('(TITLE: ' + visible(x['title']) + ' SNIPPET: ' + visible(x['snippet']) + ') ' for x in rows) + ')'


def result(value, request, chosen):
    try:
        c.fields(value, 'profile operation provider selection request_digest job_id arguments observation representation')
        require(value['profile'] == PROFILE and value['operation'] == OPERATION)
        require(value['provider'] == chosen['execution'].provider)
        require(value['selection'] == selection_token(chosen['execution']))
        require(value['request_digest'] == c.fingerprint(request) and label(value['job_id']))
        require(value['arguments'] == arguments(request['body']['arguments']))
        obs = value['observation']
        c.fields(obs, 'identity items observed_ms captured_ms completeness truncated outcome sdk_invocations http_entries boundary')
        require(obs['identity'] == IDENTITY)
        rows = items(obs['items'], value['arguments']['max_results'])
        require(obs['completeness'] == 'top-k-not-exhaustive' and obs['truncated'] is False)
        require(obs['outcome'] == ('results' if rows else 'empty'))
        require(type(obs['observed_ms']) is int and type(obs['captured_ms']) is int and
                0 < obs['observed_ms'] <= obs['captured_ms'] < 2**53)
        require(type(obs['sdk_invocations']) is int and obs['sdk_invocations'] == 1)
        require(type(obs['http_entries']) is int and obs['boundary'] in ('live', 'recorded-response'))
        require(obs['http_entries'] == (1 if obs['boundary'] == 'live' else 0))
        require(value['representation'] == render(rows) and len(canonical(value)) <= MAX_BYTES)
    except (ContractError, TypeError, ValueError, KeyError, UnicodeError):
        raise ContractError('NOT_AVAILABLE') from None
    return json.loads(canonical(value))
