"""S03 closed vector Search DTOs. No SDK imports; exact Search is unchanged."""
import math
import struct
from dataclasses import dataclass
from typing import Protocol
from .contracts import canonical, digest, require
from . import lookup_contracts as a


PROFILE = 'semantic-embedding-memory/1'
EMBEDDING = 'neoclaw-e5-large-v2-f169b11-f32-normalized-unprefixed/1'
FIXTURE = 'fixture-unit-vector-1024/1'
EXTRACTION = 'immutable-memory-enrollment/1'
PAYLOAD = 'application/fusion-memory-payload-v1'
VECTOR = 'application/fusion-vector-f32le-v1'
ENROLLMENT = 'application/fusion-memory-enrollment-v1'
PRIVACY = 'generated-shareable-only'
DIMENSION = 1024
MAX_K = 100
MAX_RECORDS = 128
METRIC = 'squared-l2'
INDEX = 'chroma-1.5.5-hnsw-l2-default/1'
APPLICATION = 'controlled-native-loop/3'


def fields(value,names):
    require(type(value) is dict and set(value)==set(names.split()))

def query_text(value):
    require(type(value) is str and 1<=len(value.encode())<=2048)
    return value

def vector(value):
    require(type(value) is list and len(value) == DIMENSION)
    require(all(type(x) in (int,float) and math.isfinite(x) and -1.00001 <= x <= 1.00001 for x in value))
    require(abs(sum(x*x for x in value)-1) <= .00001)
    return list(struct.unpack('<1024f', struct.pack('<1024f', *value)))


def vector_bytes(value): return struct.pack('<1024f', *vector(value))

def from_bytes(data):
    require(type(data) is bytes and len(data) == 4096, 'NOT_AVAILABLE')
    return vector(list(struct.unpack('<1024f', data)))

def model(value):
    require(value in (EMBEDDING, FIXTURE), 'UNSUPPORTED_PROFILE');return value

def payload(value, scope, corpus):
    fields(value, 'scope corpus uuid time content')
    require(value['scope'] == scope, 'UNAUTHORIZED');require(value['corpus'] == corpus, 'CONFLICT')
    a.identity(value['uuid'])
    require(type(value['time']) is str and len(value['time']) == 19)
    require(type(value['content']) is str and 1 <= len(value['content'].encode()) <= 3000)
    require(len(canonical(value)) <= a.MAX_BYTES)
    return a.copy(value)

def enrollment(value, scope, corpus, embedding):
    fields(value, 'profile scope corpus uuid payload vector embedding')
    require(value['profile'] == EXTRACTION and value['embedding'] == model(embedding), 'UNSUPPORTED_PROFILE')
    require(value['scope'] == scope, 'UNAUTHORIZED');require(value['corpus'] == corpus, 'CONFLICT')
    a.identity(value['uuid']);a.ref(value['payload'], scope);a.ref(value['vector'], scope)
    return a.copy(value)

def snapshot(value, scope):
    fields(value, 'generation logical head corpus embedding index profile')
    a.identity(value['generation']);a.head(value['head'], scope)
    require(value['profile'] == PROFILE and value['index'] == INDEX, 'UNSUPPORTED_PROFILE')
    model(value['embedding']);require(type(value['corpus']) is str and 1 <= len(value['corpus']) <= 80)
    expected=digest(canonical({k:value[k] for k in ('head','corpus','embedding','index','profile')}))
    require(value['logical'] == expected, 'CONFLICT');return a.copy(value)

@dataclass(frozen=True)
class VectorQuery:
    request_id: str
    scope: str
    snapshot: dict
    vector: list
    k: int
    deadline_ms: int
    metric: str = METRIC
    profile: str = PROFILE


def query(value):
    fields(value, 'request_id scope snapshot vector k deadline_ms metric profile')
    a.identity(value['request_id']);snapshot(value['snapshot'], value['scope'])
    require(value['profile'] == PROFILE and value['metric'] == METRIC, 'UNSUPPORTED_PROFILE')
    a.integer(value['k'],1,MAX_K);a.integer(value['deadline_ms'],1,2**63-1)
    require(vector(value['vector']) == value['vector'])  # explicit float32 values, no hidden remote rounding
    return a.copy(value)


def result(value, request):
    fields(value, 'request_id request_digest snapshot hits top_k exhaustive')
    require(value['request_id'] == request['request_id'] and value['request_digest'] == digest(canonical(request)), 'NOT_AVAILABLE')
    require(value['snapshot'] == request['snapshot'] and value['top_k'] == request['k'] and value['exhaustive'] is False, 'NOT_AVAILABLE')
    require(type(value['hits']) is list and len(value['hits']) <= request['k'], 'NOT_AVAILABLE')
    seen=set();last=-1.
    for hit in value['hits']:
        fields(hit, 'ref uuid distance');a.ref(hit['ref'],request['scope']);a.identity(hit['uuid'])
        require(hit['uuid'] not in seen,'NOT_AVAILABLE');seen.add(hit['uuid'])
        distance=hit['distance'];require(type(distance) is float and math.isfinite(distance) and 0 <= distance <= 4.0001 and distance >= last,'NOT_AVAILABLE');last=distance
    return a.copy(value)

class VectorSearch(Protocol):
    def query(self, request: VectorQuery) -> dict: ...

class VectorMaintenance(Protocol):
    def build(self, scope: str, through: dict) -> dict: ...

class NamedVectorMaintenance(Protocol):
    """Optional Search 3.1 capability; generation and deadline bind to a logical key."""
    def build_named(self, scope: str, through: dict, key: str, deadline_ms: int) -> dict: ...
    def published(self, scope: str, through: dict, key: str) -> dict | None: ...

class VectorReadiness(Protocol):
    def ready(self, scope: str, snapshot: dict) -> dict: ...
