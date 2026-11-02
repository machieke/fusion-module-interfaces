"""Explicit active-membership profile; unchanged E5/f32/L2 numerical semantics."""
from dataclasses import dataclass
from . import vector_contracts as v, lookup_contracts as a
from .contracts import canonical, digest, require
from .preview_lifecycle import PROFILE as LIFECYCLE

PROFILE = 'semantic-active-memory-view/1'
INDEX, ENROLLMENT, MAX_RECORDS = v.INDEX, v.ENROLLMENT, v.MAX_RECORDS
model, enrollment, vector_bytes, result = v.model, v.enrollment, v.vector_bytes, v.result
fields,vector,payload,PAYLOAD=v.fields,v.vector,v.payload,v.PAYLOAD


def snapshot(value, scope):
    v.fields(value, 'generation logical head corpus embedding index profile lifecycle active_digest')
    require(value['profile'] == PROFILE, 'UNSUPPORTED_PROFILE')
    a.head(value['lifecycle'], scope, LIFECYCLE)
    require(type(value['active_digest']) is str and len(value['active_digest']) == 64)
    original = {k: value[k] for k in ('generation', 'head', 'corpus', 'embedding', 'index')}
    original['profile'] = v.PROFILE
    original['logical'] = digest(canonical({k: x for k, x in original.items() if k != 'generation'}))
    v.snapshot(original, scope)
    require(value['logical'] == digest(canonical({k: x for k, x in value.items() if k not in ('generation', 'logical')})), 'CONFLICT')
    return a.copy(value)


@dataclass(frozen=True)
class VectorQuery:
    request_id: str
    scope: str
    snapshot: dict
    vector: list
    k: int
    deadline_ms: int
    metric: str = v.METRIC
    profile: str = PROFILE


def query(value):
    v.fields(value, 'request_id scope snapshot vector k deadline_ms metric profile')
    a.identity(value['request_id']); snapshot(value['snapshot'], value['scope'])
    require(value['profile'] == PROFILE and value['metric'] == v.METRIC, 'UNSUPPORTED_PROFILE')
    a.integer(value['k'], 1, v.MAX_K); a.integer(value['deadline_ms'], 1, 2**63-1)
    require(v.vector(value['vector']) == value['vector'])
    return a.copy(value)
