"""Model-independent, trusted-local evidence completion. No PLN dependency.

Digests bind identity, not trust: only the selected relay acknowledgment context
may attest that it observed a durable consumer decision through authorized ports.
"""
from . import memory_contracts as m
from .contracts import canonical, digest, require, validate_ref

CONFIG = 'fusion-delivery-closure/1'
EPISODE_PROFILE = 'episode-delivery-completion/1'
COMPLETION = 'trusted-evidence-completion/1'


def sha(value):
    require(type(value) is str and len(value) == 64 and all(x in '0123456789abcdef' for x in value))


def consumer(value):
    m.fields(value, 'principal provider profile selection')
    for key in ('principal', 'provider', 'profile'): m.identifier(value[key])
    sha(value['selection'])


def completion(value):
    m.fields(value, 'profile state scope_ref delivery_id evidence claim context consumer request_key request_digest decision_id decision_digest')
    require(value['profile'] == COMPLETION, 'UNSUPPORTED_PROFILE')
    require(value['state'] == 'committed')
    m.identifier(value['scope_ref']); m.evidence_ref(value['evidence'], value['scope_ref'])
    validate_ref(value['claim'], value['scope_ref']); m.identifier(value['context'])
    consumer(value['consumer']); m.identifier(value['request_key'])
    for key in ('delivery_id', 'request_digest', 'decision_id', 'decision_digest'): sha(value[key])
    require(value['delivery_id'] == digest(canonical(value['evidence'])), 'CONFLICT')
    require(value['decision_id'] == digest(canonical([value['consumer']['principal'], value['scope_ref'], value['request_key']])), 'CONFLICT')


def receipt(value, completed):
    m.fields(value, 'delivery_id decision_id completion_digest acknowledged')
    require(value == {'delivery_id': completed['delivery_id'], 'decision_id': completed['decision_id'],
                      'completion_digest': digest(canonical(completed)), 'acknowledged': True})
