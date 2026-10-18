"""X02: one text, one explicitly compatible vector. No retrieval or SDK dependency."""
from dataclasses import asdict, dataclass
from typing import Protocol

from . import vector_contracts as v, lookup_contracts as a
from .contracts import canonical, digest, require
from .registry import Descriptor, Requirement, resolve, selection_token

INTERFACE = 'embedding'
VERSION = '1.0.0'
PROFILE = 'neoclaw-e5-query-text/1'
MEMORY_PROFILE = 'neoclaw-e5-memory-text/1'
PREPROCESSING = 'native-string-safe-once-utf8/1'
APPLICATION = 'controlled-native-loop/4'
MAX_INPUT_BYTES = 2048
MAX_ATTEMPTS = 3
MAX_CALLS = 32
MAX_OCCURRENCES = 128
MAX_WIRE_BYTES = 65536


def text(value):
    require(type(value) is str)
    try: data = value.encode('utf-8', errors='strict')
    except UnicodeError: require(False)
    require(len(data) <= MAX_INPUT_BYTES)
    return value  # Empty, Unicode, quotes and control characters are data.


def descriptor(profile=PROFILE):
    require(profile in (PROFILE,MEMORY_PROFILE),'UNSUPPORTED_PROFILE')
    return Descriptor('neoclaw-native-e5' if profile==PROFILE else 'neoclaw-native-e5-memory', INTERFACE, VERSION, '0.1.0', frozenset({profile}),
        frozenset({'encode', 'authorize-invoke', 'authorize-disclose'}), frozenset({'scoped', 'bounded-evaluations'}), MAX_WIRE_BYTES,
        privacy=v.PRIVACY, deterministic=False, features=frozenset({v.EMBEDDING, PREPROCESSING, 'f32le-1024-unit'}))


def select(catalogue,profile=PROFILE):
    d = descriptor(profile)
    return resolve(catalogue, Requirement(INTERFACE, VERSION, '1.1.0', profile, d.operations,
        d.guarantees, privacy=v.PRIVACY, features=d.features, payload_bytes=MAX_WIRE_BYTES))


@dataclass(frozen=True)
class EncodeInput:
    occurrence: str
    principal: str
    scope: str
    text: str
    input_sha256: str
    deadline_ms: int
    selection: str
    model: str = v.EMBEDDING
    preprocessing: str = PREPROCESSING
    max_input_bytes: int = MAX_INPUT_BYTES
    profile: str = PROFILE


def intent(value):
    v.fields(value, 'occurrence principal scope text input_sha256 deadline_ms selection model preprocessing max_input_bytes profile')
    a.identity(value['occurrence'])
    for name in ('principal', 'scope'): require(type(value[name]) is str and 1 <= len(value[name]) <= 80)
    text(value['text'])
    require(value['input_sha256'] == digest(value['text'].encode()), 'CONFLICT')
    require(value['model'] == v.EMBEDDING and value['preprocessing'] == PREPROCESSING and
            value['profile'] in (PROFILE,MEMORY_PROFILE) and value['max_input_bytes'] == MAX_INPUT_BYTES, 'UNSUPPORTED_PROFILE')
    a.integer(value['deadline_ms'], 1, 2**63-1)
    require(type(value['selection']) is str and len(value['selection']) == 64)
    return a.copy(value)


def request(value, chosen):
    v.fields(value, 'interface_ref operation intent attempt')
    require(value['interface_ref'] == {'id': INTERFACE, 'version': VERSION}, 'UNSUPPORTED_VERSION')
    intent(value['intent'])
    require(value['intent']['profile'] in chosen.profiles,'UNSUPPORTED_PROFILE')
    require(value['intent']['selection'] == selection_token(chosen), 'UNSUPPORTED_PROFILE')
    require(value['operation'] in ('encode', 'authorize-invoke', 'authorize-disclose'), 'UNSUPPORTED_OPERATION')
    a.integer(value['attempt'], 1 if value['operation'] == 'encode' else 0,
              MAX_ATTEMPTS if value['operation'] == 'encode' else 0)
    require(len(canonical(value)) <= MAX_WIRE_BYTES)
    return a.copy(value)


def result(value, accepted):
    v.fields(value, 'occurrence intent_sha256 principal model preprocessing vector dimension dtype normalization encoding vector_sha256')
    require(value['occurrence'] == accepted['occurrence'] and value['intent_sha256'] == digest(canonical(accepted)), 'NOT_AVAILABLE')
    require(value['principal'] == accepted['principal'], 'UNAUTHORIZED')
    require(value['model'] == accepted['model'] and value['preprocessing'] == PREPROCESSING, 'UNSUPPORTED_PROFILE')
    require(type(value['dimension']) is int and value['dimension'] == 1024 and value['dtype'] == 'float32' and
            value['normalization'] == 'unit-l2' and value['encoding'] == 'f32le', 'NOT_AVAILABLE')
    require(v.vector(value['vector']) == value['vector'], 'NOT_AVAILABLE')
    require(value['vector_sha256'] == digest(v.vector_bytes(value['vector'])), 'NOT_AVAILABLE')
    return a.copy(value)


def encoded(accepted, vector):
    # Validate, never renormalize. Original native .tolist() values are already f32.
    require(v.vector(vector) == vector, 'NOT_AVAILABLE')
    return result(dict(occurrence=accepted['occurrence'], intent_sha256=digest(canonical(accepted)),
        principal=accepted['principal'], model=accepted['model'], preprocessing=PREPROCESSING,
        vector=vector, dimension=1024, dtype='float32', normalization='unit-l2', encoding='f32le',
        vector_sha256=digest(v.vector_bytes(vector))), accepted)


class Embedding(Protocol):
    def encode(self, request: EncodeInput) -> dict: ...
