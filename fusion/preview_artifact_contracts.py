"""Closed, explicitly shareable application artifact for synthetic retrieval.

This validator does not retrieve, generate, inspect or evaluate anything. The
application must correlate the actual task/result and hydrate observations from
AtomStorage before admission. Content is preserved exactly, without truncation.
An empty observation list truthfully represents an empty retrieval result.
"""
from typing import Literal, TypedDict

from . import lookup_contracts as atoms, preview_vector_contracts as vectors
from .contracts import AtomRef, ContractError, canonical, label, require


PROFILE = 'synthetic-agent-retrieval-artifact/1'
MAX_BYTES = 4096
MAX_OBSERVATIONS = 3
MAX_QUERY_BYTES = 512
MAX_CONTENT_BYTES = 1024


class Observation(TypedDict):
    payload_ref: AtomRef
    content: str


class RetrievalArtifact(TypedDict):
    profile: Literal['synthetic-agent-retrieval-artifact/1']
    scope: str
    task: str
    query: str
    sender: Literal['A', 'B']
    reporter: Literal['A', 'B']
    result_ref: AtomRef
    view: dict
    observations: list[Observation]


def _fields(value, names):
    require(type(value) is dict and all(type(key) is str for key in value))
    require(set(value) == set(names.split()))


def _text(value, maximum):
    require(type(value) is str and 0 < len(value) <= maximum)
    try:
        require(len(value.encode('utf-8')) <= maximum)
    except UnicodeError:
        raise ContractError('INVALID_ARGUMENT') from None


def _ref(value, scope):
    _fields(value, 'scope_ref id revision digest')
    require(all(type(value[key]) is str for key in ('scope_ref', 'id', 'digest')))
    require(type(value['revision']) is int)
    return atoms.ref(value, scope)


def _snapshot(value, scope):
    # Reject non-JSON Python objects before calling the existing profile. The
    # retained-view semantics and supported numerical profiles stay unchanged.
    _fields(value, 'generation logical head corpus embedding index profile lifecycle active_digest')
    require(all(type(value[key]) is str for key in
                ('generation', 'logical', 'corpus', 'embedding', 'index', 'profile', 'active_digest')))
    for name in ('head', 'lifecycle'):
        head = value[name]
        _fields(head, 'source scope_ref sequence profile')
        require(all(type(head[key]) is str for key in ('source', 'scope_ref', 'profile')))
        require(type(head['sequence']) is int)
    return vectors.snapshot(value, scope)


def record(value, scope=None) -> RetrievalArtifact:
    """Validate a closed artifact, optionally bound to an expected scope.

    The limits apply together: three individually valid observations can still
    exceed the complete artifact's byte limit. Ref identity includes owner scope,
    ID and immutable revision; changing a digest does not create a new identity.
    This validates structure, not proof that claimed text matches stored bytes.
    """
    _fields(value, 'profile scope task query sender reporter result_ref view observations')
    require(type(value['profile']) is str and value['profile'] == PROFILE, 'UNSUPPORTED_PROFILE')
    selected = value['scope']
    require(type(selected) is str and label(selected) and selected.startswith('synthetic-')
            and len(selected) > len('synthetic-'), 'UNAUTHORIZED')
    if scope is not None:
        require(type(scope) is str and selected == scope, 'UNAUTHORIZED')
    atoms.identity(value['task'])
    _text(value['query'], MAX_QUERY_BYTES)
    require(type(value['sender']) is str and type(value['reporter']) is str
            and value['sender'] in ('A', 'B') and value['reporter'] in ('A', 'B')
            and value['sender'] != value['reporter'], 'UNAUTHORIZED')
    result = _ref(value['result_ref'], selected)
    _snapshot(value['view'], selected)
    observations = value['observations']
    require(type(observations) is list and len(observations) <= MAX_OBSERVATIONS)
    identities = {(result['scope_ref'], result['id'], result['revision'])}
    for observation in observations:
        _fields(observation, 'payload_ref content')
        ref = _ref(observation['payload_ref'], selected)
        identity = (ref['scope_ref'], ref['id'], ref['revision'])
        require(identity not in identities, 'CONFLICT')
        identities.add(identity)
        _text(observation['content'], MAX_CONTENT_BYTES)
    wire = canonical(value)
    require(len(wire) <= MAX_BYTES, 'OVERLOADED')
    return atoms.copy(value)


def encode(value, scope=None) -> bytes:
    """Return exact canonical bytes of a validated application artifact."""
    return canonical(record(value, scope))
