"""Closed local C1/C2 validation; the M1 wire contract is unchanged."""
from dataclasses import asdict
from decimal import Decimal, InvalidOperation
import json
import math
import re
import sqlite3
from functools import wraps

from .contracts import ContractError, canonical, digest, label, require, validate_ref
from .ports import EvidenceSubmission, Mutation

MODEL = 'trueagi-pln-stv-finite-k1/v1'
RUNTIME = 'fusion-petta-swi-10.1.14-revision/1'
EPISODE_PROFILE = 'episode-local-sequence/2'
BELIEF_PROFILE = 'pln-revision-private/1'
INGESTION = 'explicit-generated-assessment/1'
MAX_PAGE, MAX_PENDING, MAX_EVENTS, MAX_SUPPORTS, MAX_PROVENANCE = 16, 16, 256, 32, 8


def boundary(method):
    """Local owner failures expose stable codes, never private exception bodies."""
    @wraps(method)
    def checked(*args, **kwargs):
        try:
            return method(*args, **kwargs)
        except sqlite3.OperationalError:
            raise ContractError('NOT_AVAILABLE') from None
        except (KeyError, TypeError, ValueError, OverflowError):
            raise ContractError('INVALID_ARGUMENT') from None
    return checked


def detached(value):
    return json.loads(canonical(value))


def fields(value, names):
    require(type(value) is dict and set(value) == set(names.split()))


def integer(value, minimum=0, maximum=2**53-1):
    require(type(value) is int and minimum <= value <= maximum)


def identifier(value):
    require(label(value))


def mutation(command, scope=None):
    require(type(command) is Mutation)
    identifier(command.scope_ref)
    identifier(command.idempotency_key)
    require(command.intent_digest is None)
    if scope is not None:
        require(command.scope_ref == scope, 'UNAUTHORIZED')


def episode_ref(ref, scope=None):
    fields(ref, 'scope_ref id')
    identifier(ref['scope_ref']); identifier(ref['id'])
    if scope is not None:
        require(ref['scope_ref'] == scope, 'UNAUTHORIZED')


def evidence_ref(ref, scope=None):
    fields(ref, 'episode occurrence_id sequence event_ref')
    episode_ref(ref['episode'], scope)
    identifier(ref['occurrence_id'])
    integer(ref['sequence'], 1, MAX_EVENTS)
    validate_ref(ref['event_ref'], ref['episode']['scope_ref'])


def decimal(value, confidence=False):
    require(type(value) is str and len(value) <= 64 and
            re.fullmatch(r'-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?', value) is not None)
    try:
        exact = Decimal(value)
        binary = float(exact)
    except (InvalidOperation, ValueError, OverflowError):
        raise ContractError('INVALID_ARGUMENT') from None
    require(exact.is_finite() and 0 <= exact <= 1 and (not confidence or exact < 1))
    require(math.isfinite(binary) and 0 <= binary <= 1 and (not confidence or binary < 1))
    return binary


def truth(value):
    fields(value, 'model strength confidence evidence_count')
    require(value['model'] == MODEL, 'UNSUPPORTED_PROFILE')
    require(value['evidence_count'] is None)
    decimal(value['strength']); decimal(value['confidence'], True)


def numerical(value, scope):
    fields(value, 'claim context relationship truth ingestion_profile')
    validate_ref(value['claim'], scope); identifier(value['context'])
    require(value['relationship'] in {'supports', 'contradicts', 'reports'})
    require(value['ingestion_profile'] == INGESTION, 'UNSUPPORTED_PROFILE')
    if value['truth'] is not None:
        truth(value['truth'])
    require(value['relationship'] != 'reports' or value['truth'] is None)


def event(value, scope):
    fields(value, 'occurrence_id kind source observed_time payload causation provenance numerical')
    identifier(value['occurrence_id']); identifier(value['source'])
    require(value['kind'] in {'observation', 'action', 'result'})
    # Explicit lexical timestamp; it never determines order.
    require(type(value['observed_time']) is str and len(value['observed_time']) <= 40
            and re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9:.]+Z', value['observed_time']))
    validate_ref(value['payload'], scope)
    for key, validator in [('causation', validate_ref), ('provenance', evidence_ref)]:
        require(type(value[key]) is list and len(value[key]) <= MAX_PROVENANCE)
        for ref in value[key]:
            validator(ref, scope)
        require(len({canonical(x) for x in value[key]}) == len(value[key]))
    if value['numerical'] is not None:
        numerical(value['numerical'], scope)
    require(len(canonical(value)) <= 16384)


def grounded_claim(value):
    fields(value, 'predicate arguments positive')
    identifier(value['predicate'])
    require(type(value['arguments']) is list and 1 <= len(value['arguments']) <= 8)
    for arg in value['arguments']:
        identifier(arg)
    require(type(value['positive']) is bool)


def atom_write(value, scope):
    fields(value, 'ref receipt')
    validate_ref(value['ref'], scope)
    fields(value['receipt'], 'provider durability evidence')
    identifier(value['receipt']['provider'])
    identifier(value['receipt']['durability'])
    require(type(value['receipt']['evidence']) is dict)


def evidence_record(value, expected):
    fields(value, 'evidence event lineage_roots')
    evidence_ref(value['evidence'])
    require(value['evidence'] == expected)
    event(value['event'], expected['episode']['scope_ref'])
    require(value['event']['occurrence_id'] == expected['occurrence_id'])
    roots(value['lineage_roots'], allow_empty=True)


def roots(values, allow_empty=False):
    require(type(values) is list and (allow_empty or values) and len(values) <= MAX_SUPPORTS)
    for value in values:
        identifier(value)
    require(values == sorted(set(values)))


def independence(value):
    fields(value, 'model_id supports status')
    identifier(value['model_id'])
    require(value['status'] == 'assumption')
    require(type(value['supports']) is list and len(value['supports']) == 2)
    for ref in value['supports']:
        identifier(ref)
    require(value['supports'][0] != value['supports'][1])


def submission(value):
    require(type(value) is EvidenceSubmission)
    mutation(value.command)
    validate_ref(value.claim, value.command.scope_ref)
    identifier(value.context)
    require((value.evidence is None) != (value.support_id is None))
    if value.evidence is not None:
        evidence_ref(value.evidence, value.command.scope_ref)
    else:
        identifier(value.support_id)
    integer(value.expected_revision)
    require(value.profile == BELIEF_PROFILE, 'UNSUPPORTED_PROFILE')
    require(type(value.runtime_selection) is str and re.fullmatch('[a-f0-9]{64}', value.runtime_selection))
    if value.independence is not None:
        independence(value.independence)
    return detached(asdict(value))


def support(value, scope):
    fields(value, 'id claim context truth evidence_ids lineage_roots coverage premises formula assumptions')
    identifier(value['id']); identifier(value['context'])
    validate_ref(value['claim'], scope); truth(value['truth'])
    for key in ('evidence_ids', 'lineage_roots', 'coverage'):
        roots(value[key])
    require(type(value['premises']) is list and len(value['premises']) in {0, 2})
    for item in value['premises']:
        identifier(item)
    require(value['formula'] is None or value['formula'] ==
            'trueagi-pln/4405956947c4b53c7ff01bd565aa3b114bc970a1/Truth_Revision')
    require(type(value['assumptions']) is list and len(value['assumptions']) <= 8)
    for item in value['assumptions']:
        require(type(item) is str and 1 <= len(item) <= 256)


def snapshot(value, claim, context, runtime_selection):
    fields(value, 'claim context revision truth aggregate covered_supports alternatives supports observations model runtime_selection')
    require(value['claim'] == claim and value['context'] == context)
    require(value['model'] == MODEL and value['runtime_selection'] == runtime_selection)
    integer(value['revision'])
    require(type(value['supports']) is list and len(value['supports']) <= MAX_SUPPORTS * 2)
    ids = set()
    for item in value['supports']:
        support(item, claim['scope_ref'])
        require(item['claim'] == claim and item['context'] == context and item['id'] not in ids)
        ids.add(item['id'])
    roots(value['covered_supports'], True); roots(value['alternatives'], True)
    require(set(value['covered_supports']) <= ids and set(value['alternatives']) <= ids)
    require(not set(value['covered_supports']) & set(value['alternatives']))
    if value['aggregate'] is None:
        require(value['truth'] is None and not value['covered_supports'])
    else:
        require(value['aggregate'] in ids)
        aggregate = next(s for s in value['supports'] if s['id'] == value['aggregate'])
        require(value['truth'] == aggregate['truth'] and value['covered_supports'] == aggregate['coverage'])
    require(type(value['observations']) is list and len(value['observations']) <= MAX_SUPPORTS)
    observations = set()
    for observation in value['observations']:
        fields(observation, 'evidence relationship truth support_id lineage_roots')
        evidence_ref(observation['evidence'], claim['scope_ref'])
        identity = canonical(observation['evidence'])
        require(identity not in observations)
        observations.add(identity)
        require(observation['relationship'] in {'supports', 'contradicts', 'reports'})
        roots(observation['lineage_roots'], True)
        if observation['truth'] is not None: truth(observation['truth'])
        require(observation['relationship'] != 'reports' or observation['truth'] is None)
        require(observation['support_id'] is None or observation['support_id'] in ids)
    require(len(canonical(value)) <= 262144)


def decision(value, claim, context, runtime_selection):
    fields(value, 'decision_id evidence support_id admission numerical detail snapshot')
    identifier(value['decision_id'])
    if value['evidence'] is not None:
        evidence_ref(value['evidence'], claim['scope_ref'])
    if value['support_id'] is not None:
        identifier(value['support_id'])
    require(value['admission'] in {'admitted', 'duplicate'})
    require(value['numerical'] in {'initialized', 'revised', 'no-change', 'retained-alternative', 'model-inapplicable'})
    require(type(value['detail']) is str and len(value['detail']) <= 256)
    snapshot(value['snapshot'], claim, context, runtime_selection)


def response(validator, *args):
    try:
        validator(*args)
    except (ContractError, KeyError, TypeError, ValueError, StopIteration):
        raise ContractError('NOT_AVAILABLE') from None


def math_result(value, existing, incoming, declaration):
    fields(value, 'status detail proposal')
    require(value['status'] in {'PASS', 'FAIL', 'UNKNOWN'})
    require(type(value['detail']) is str and len(value['detail']) <= 256)
    proposal = value['proposal']
    if proposal is None: return
    require(value['status'] == 'PASS' and declaration is not None)
    require(set(declaration['supports']) == {existing['id'], incoming['id']})
    require(not set(existing['evidence_ids']) & set(incoming['evidence_ids']))
    require(not set(existing['lineage_roots']) & set(incoming['lineage_roots']))
    support(proposal, existing['claim']['scope_ref'])
    require(proposal['claim'] == existing['claim'] and proposal['context'] == existing['context'])
    require(proposal['id'] not in {existing['id'], incoming['id']})
    require(set(proposal['premises']) == {existing['id'], incoming['id']})
    for key in ('coverage', 'evidence_ids', 'lineage_roots'):
        require(proposal[key] == sorted(set(existing[key]) | set(incoming[key])))
    require(proposal['formula'] == 'trueagi-pln/4405956947c4b53c7ff01bd565aa3b114bc970a1/Truth_Revision')
    require(proposal['assumptions'])


def delivery(value, episode):
    fields(value, 'delivery_id evidence')
    identifier(value['delivery_id']); evidence_ref(value['evidence'], episode['scope_ref'])
    require(value['evidence']['episode'] == episode and value['delivery_id'] == digest(canonical(value['evidence'])))


def episode_page(value, ref, start, limit):
    fields(value, 'ref head events next_sequence complete')
    require(value['ref'] == ref)
    integer(value['head'], 0, MAX_EVENTS)
    require(type(value['events']) is list and len(value['events']) <= limit)
    for sequence, record in enumerate(value['events'], start):
        evidence_record(record, record['evidence'])
        require(record['evidence']['episode'] == ref and record['evidence']['sequence'] == sequence)
    next_sequence = start + len(value['events'])
    require(type(value['complete']) is bool and value['complete'] == (next_sequence > value['head']))
    require(value['next_sequence'] == (None if value['complete'] else next_sequence))
    require(value['complete'] or len(value['events']) == limit)
