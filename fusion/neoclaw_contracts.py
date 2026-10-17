"""S01 only: two grounded STVs, one native NAL truth deduction.

Separate from the existing five-premise PLN DTOs and numerical profiles. No
expression, path, function selector, inheritance term or private evidence input.
"""
from dataclasses import replace
from decimal import Decimal, InvalidOperation
import json
import re
import uuid
from pathlib import Path
from typing import Protocol

from .contracts import ContractError, canonical, digest, label, require, validate as m1_validate
from .registry import Descriptor, Requirement, descriptors, resolve, selection_token

PROFILE = 'neoclaw-nal-truth-deduction/1'
OPERATION = 'nal_truth_deduction'
RUNTIME = 'neoclaw-petta-swi-10.0.1/1'
PRIVACY = 'generated-shareable-only'
SCOPE = 'generated-s01'
MAX_BYTES, MAX_CALLS, MAX_ATTEMPTS = 4096, 64, 3
MAX_REQUESTS = 128
VERSION = '1.1.0'
EXECUTION_LIMITS = frozenset({'native-attempts:3', 'native-timeout-ms:5000', 'caller-calls:64',
                              'rpc-timeout-ms:1000', 'lifetime-requests:128'})
PINS = json.loads((Path(__file__).resolve().parents[1] / 'integration/neoclaw/sources.json').read_text())
SOURCE = digest(canonical({k: v['commit'] for k, v in PINS['sources'].items()}))
NUMBER = r'(?:0|1|0\.[0-9]{1,17}|1\.0{1,17})'
OUTPUT_NUMBER = r'(?:[0-9]+(?:\.[0-9]+)?(?:e[+-]?[0-9]+)?)'
EXPRESSION = re.compile(r'\(\s*Truth_Deduction\s+\(\s*stv\s+('+NUMBER+r')\s+('+NUMBER+r')\s*\)\s+'
                        r'\(\s*stv\s+('+NUMBER+r')\s+('+NUMBER+r')\s*\)\s*\)')


class TruthDeduction(Protocol):
    def applyTruth(self, premises: list[dict[str, str]], deadline_ms: int) -> dict: ...


def fields(value, names):
    require(type(value) is dict and set(value) == set(names.split()))


def premises(value):
    require(type(value) is list and len(value) == 2)
    for item in value:
        fields(item, 'strength confidence')
        for number in item.values():
            require(type(number) is str and re.fullmatch(NUMBER, number) is not None)
    return json.loads(canonical(value))


def parse_expression(expression):
    require(type(expression) is str and len(expression.encode()) <= MAX_BYTES)
    match = EXPRESSION.fullmatch(expression.strip())
    require(match is not None)
    a, b, c, d = match.groups()
    return premises([dict(strength=a, confidence=b), dict(strength=c, confidence=d)])


def expression(value):
    a, b = premises(value)
    return f'(Truth_Deduction (stv {a["strength"]} {a["confidence"]}) (stv {b["strength"]} {b["confidence"]}))'


def native_truth(representation):
    require(type(representation) is str and len(representation) <= 256, 'NOT_AVAILABLE')
    match = re.fullmatch(r'\(stv ('+OUTPUT_NUMBER+r') ('+OUTPUT_NUMBER+r')\)', representation)
    require(match is not None, 'NOT_AVAILABLE')
    values = match.groups()
    try:
        require(all(Decimal(x).is_finite() and 0 <= Decimal(x) <= 1 for x in values), 'NOT_AVAILABLE')
    except InvalidOperation:
        raise ContractError('NOT_AVAILABLE') from None
    return dict(zip(('strength', 'confidence'), values))


def catalogue(atom_provider='detta', provider='neoclaw-native'):
    base = descriptors(atom_provider=atom_provider)
    shared = [replace(d, privacy=PRIVACY, max_payload_bytes=MAX_BYTES) for d in base if d.interface != 'execution']
    kernel = Descriptor(provider + '-kernel', 'pln.kernel', VERSION, '0.1.0', frozenset({PROFILE}),
        frozenset({'applyTruth'}), frozenset({'pure', 'grounded', 'native-nal'}), MAX_BYTES, privacy=PRIVACY,
        features=frozenset({RUNTIME, 'source:' + SOURCE}))
    execution = Descriptor(provider, 'execution', VERSION, '0.1.0', frozenset({PROFILE}),
        frozenset({'submit', 'status', 'result'}), frozenset({'process-restart', 'scoped', 'idempotent', 'bounded-attempts'}),
        MAX_BYTES, privacy=PRIVACY, features=frozenset({RUNTIME, 'kernel:' + selection_token(kernel)}) | EXECUTION_LIMITS,
        receipt_providers=shared[0].receipt_providers)
    return [*shared, kernel, execution]


def selected(catalogue):
    specs = [('atom.storage', '1.0.0', 'immutable-bytes/1', {'get'}, {'process-restart', 'scoped', 'idempotent'}),
             ('agent.messaging', '1.0.0', 'durable-mailbox/2', {'poll', 'ack'}, {'process-restart', 'scoped', 'idempotent'}),
             ('pln.kernel', VERSION, PROFILE, {'applyTruth'}, {'pure', 'grounded', 'native-nal'}),
             ('execution', VERSION, PROFILE, {'submit', 'status', 'result'}, {'process-restart', 'scoped', 'idempotent', 'bounded-attempts'})]
    result = {name: resolve(catalogue, Requirement(name, version, '2.0.0', profile, frozenset(ops),
              frozenset(guarantees), MAX_BYTES, privacy=PRIVACY)) for name, version, profile, ops, guarantees in specs}
    require('kernel:' + selection_token(result['pln.kernel']) in result['execution'].features, 'UNSUPPORTED_PROFILE')
    require(EXECUTION_LIMITS <= result['execution'].features and RUNTIME in result['execution'].features, 'UNSUPPORTED_PROFILE')
    require(RUNTIME in result['pln.kernel'].features and 'source:' + SOURCE in result['pln.kernel'].features, 'UNSUPPORTED_PROFILE')
    return result


def fingerprint(request):
    return digest(canonical({k: v for k, v in request.items() if k != 'message_id'}))


def mutation_identity(principal, request):
    return canonical([principal, request['scope_ref'], 'execution', 'submit', request['idempotency_key']]).decode()


def job_id(principal, request):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, mutation_identity(principal, request)))


def validate(request, chosen):
    require(type(request) is dict and len(canonical(request)) <= MAX_BYTES)
    common = {'message_id', 'interface_ref', 'profile', 'selection', 'operation', 'scope_ref', 'body'}
    require(common <= set(request) <= common | {'idempotency_key', 'correlation_id', 'reply_route', 'deadline_ms'})
    fields(request['interface_ref'], 'id version')
    name, op = request['interface_ref']['id'], request['operation']
    require(type(name) is str and name in {'execution', 'atom.storage', 'agent.messaging'}, 'UNSUPPORTED_OPERATION')
    descriptor = chosen[name]
    require(request['interface_ref']['version'] == descriptor.version, 'UNSUPPORTED_VERSION')
    require(request['profile'] == (PROFILE if name == 'execution' else
            'immutable-bytes/1' if name == 'atom.storage' else 'durable-mailbox/2'), 'UNSUPPORTED_PROFILE')
    require(request['selection'] == selection_token(descriptor), 'UNSUPPORTED_PROFILE')
    require(label(request['message_id']) and label(op))
    require(request['scope_ref'] == SCOPE, 'UNAUTHORIZED')
    allowed = {'execution': {'submit', 'status', 'result'}, 'atom.storage': {'get'}, 'agent.messaging': {'poll', 'ack'}}
    require(op in allowed[name], 'UNSUPPORTED_OPERATION')
    body = request['body']
    if name != 'execution':
        m1_validate({k: v for k, v in request.items() if k != 'selection'}, check_deadline=False)
    elif op == 'submit':
        fields(body, 'operation premises sharing max_attempts')
        require(body['operation'] == OPERATION, 'UNSUPPORTED_OPERATION')
        require(body['sharing'] == 'generated-shareable', 'UNAUTHORIZED')
        premises(body['premises'])
        require(type(body['max_attempts']) is int and 1 <= body['max_attempts'] <= MAX_ATTEMPTS)
        require(set(request) == common | {'idempotency_key', 'correlation_id', 'reply_route', 'deadline_ms'})
        for key in ('idempotency_key', 'correlation_id', 'reply_route'):
            require(label(request[key]))
        require(type(request['deadline_ms']) is int and 0 < request['deadline_ms'] < 2**53)
    else:
        fields(body, 'job_id')
        require(label(body['job_id']))
        require(set(request) == common)
    return name, op


def result(value, request, chosen):
    """Consistency/binding validation, not a cryptographic proof of arithmetic."""
    try:
        fields(value, 'profile operation runtime selection request_digest premises representation truth')
        require(value['profile'] == PROFILE and value['operation'] == OPERATION and value['runtime'] == RUNTIME)
        require(value['selection'] == selection_token(chosen['pln.kernel']))
        require(value['request_digest'] == fingerprint(request))
        require(value['premises'] == request['body']['premises'])
        require(value['truth'] == native_truth(value['representation']))
        require(len(canonical(value)) <= MAX_BYTES)
    except (ContractError, TypeError, ValueError, KeyError):
        raise ContractError('NOT_AVAILABLE') from None
    return json.loads(canonical(value))
